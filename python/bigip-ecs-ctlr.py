#!/usr/bin/env python
from icontrol.session import iControlRESTSession
from icontrol.exceptions import iControlUnexpectedHTTPError
from requests.exceptions import HTTPError
from ecs_anywhere_ip_port import EcsAnyWhereIpPort
import os
import json
import sys
import logging
import boto3
import time
import ipaddress

#
# Demo of automating a BIG-IP configuration for ECS AnyWhere services.
#
# Expects that the services are using TLS.  Requests will look for the
# name of the service to send the request
#

ECS_TEMPLATE = """ {
          "class": "Tenant",
          "Anywhere": {
             "class": "Application",
             "template": "generic",
             "frontend": {
                "class": "Service_TCP",
                "virtualAddresses": ["10.1.10.81"],
               "remark":"frontend: f5demo.tcp.v1",
               
               "virtualPort": 80,
                "pool": "svc_pool"
             }}"""

logger = logging.getLogger('bigip-ecs-ctlr')

class BigipEcsController(object):
    def __init__(self, cluster, username,password, bigip_urls, tenant, template_file, interval = 30, sqs_url = None,token=False):
        self.cluster = cluster
        self.username = username
        self.password = password
        self.bigip_urls = bigip_urls
        self.tenant = tenant
        self.client = EcsAnyWhereIpPort(cluster)
        self.template_txt = open(template_file).read()
        self.template_cache = ""
        self.service_map = {}
        self.interval = interval
        self.sqs_url = sqs_url
        self.last_update = time.time()
        self.icrs = {}
        for url in bigip_urls:
            if token:
                self.icrs[url] = iControlRESTSession(username, password, token='tmos')
            else:
                self.icrs[url] = iControlRESTSession(username, password)

    def get(self,uri):
        output = {}
        for (mgmt_url, icr) in self.icrs.items():
            try:
                r = icr.get(mgmt_url + uri)
                output[mgmt_url] = r.json()
            except Exception as exe:
                output[mgmt_url] = exe
                logger.error(exe)
        return output
    def post(self,uri,data):
        output = {}
        save_exe = None
        one_good = False
        for (mgmt_url, icr) in self.icrs.items():
            try:
                r = icr.post(mgmt_url + uri,data=data)
                output[mgmt_url] = r.json()
                one_good = True
            except Exception as exe:
                save_exe = exe
                logger.error(exe)
        if not one_good:
            raise save_exe
        return output        
                
    def check_device(self):
        return self.get("/mgmt/shared/appsvcs/info")
    def update_services(self,cache=False):

        services = self.client.list_services()
        if cache:
            # TODO
            # this is not working well
            services = list(set(services) - set(self.service_map.keys()))
            if not services:
                return
        else:
            self.service_map = {}
        for svc,details in self.client.describe_service(services).items():
            tags = details['tags']
            taskDefinition = details['taskDefinition']
            
            create_config = False
            ip = None
            ports = []
            for tag in tags:
                if tag.get('key') == 'f5-external-ip':
                    ip = tag.get('value')
                    try:
                        ipaddress.ip_address(ip)
                    except Exception as exec:
                        logger.error("bad IP for %s" %(svc))
                        ip = None
                        continue
                    create_config = True
                    logger.info('updating service: %s' %(svc))
                if tag.get('key').startswith('f5-external-port-'):
                    port = tag.get('key')[17:]
                    targetPort = tag.get('value')
                    try:
                        port = int(port)
                        if ':' in targetPort:
                            (containerName,targetPort) = targetPort.split(':')                        
                        targetPort = int(targetPort)
                    except Exception as exe:
                        logger.error("bad port for svc %s" %(svc))
                        continue
                    ports.append((tag.get('key')[17:],tag.get('value')))
            if ip:
                self.service_map[svc] = {'ip':ip }
            if ports:
                self.service_map[svc]['ports'] = ports
            elif ip:
                # expose first container ports
                if not taskDefinition['containerDefinitions'][0]['portMappings']:
                    logger.error("skipping %s, missing portMapping" %(svc))
                    del self.service_map[svc]
                    continue
                containerPort = str(taskDefinition['containerDefinitions'][0]['portMappings'][0]['containerPort'])
                self.service_map[svc]['ports'] = [(containerPort,containerPort)]


    def generate_template(self):
        template = json.loads(self.template_txt)
        app_template = template['declaration']['EcsAnywhere']['{{svc}}']
        del template['declaration']['EcsAnywhere']        
        template['declaration'][self.tenant] = {'class':'Tenant'}
        
        for svc_name,input_params in self.service_map.items():
            #print(input_params)
            #print(generated_app)
            if 'ports' in input_params:
            
                ports = input_params['ports']
                for p in ports:
                    svc_port = "%s_%s" %(svc_name,p[0])
                    generated_app = json.dumps(app_template).replace('{{svc}}',svc_port)                
                    template['declaration'][self.tenant][svc_port] = json.loads(generated_app)
                    template['declaration'][self.tenant][svc_port][svc_port]['virtualAddresses'][0]=input_params['ip']
                    template['declaration'][self.tenant][svc_port][svc_port]['virtualPort']=int(p[0])            
            else:
                template['declaration'][self.tenant][svc_name] = json.loads(generated_app)
                template['declaration'][self.tenant][svc_name][svc_name]['virtualAddresses'][0]=input_params['ip']
                template['declaration'][self.tenant][svc_name][svc_name]['virtualPort']=int(input_params['port'])
            #print(json.dumps(template,indent=4))
            #print(self.service_map)
        rendered_template = json.dumps(template,indent=4)
        #print(template)
        services = self.service_map.keys()

        template_txt = json.dumps(template)        
        logger.debug(json.dumps(template))
        if template_txt != self.template_cache:
            if services:
                logger.info("updated LB config for %s" %(", ".join(services)))
            else:
                logger.info("empty LB config")
                r = self.post("/mgmt/shared/appsvcs/declare",data=rendered_template)
                    
            self.template_cache = template_txt
            
            
        
    def update_pools(self,services=None):

        for svc_name,input_params in self.service_map.items():
            # retrieve instance -> ports
            nodes = self.client.get_ip_port(svc_name)
            # retrieve ports associated with service
            input_ports = input_params['ports']

            for p in input_ports:
                if not nodes:
                    container_ports = []
                    hostPort = -1
                output_nodes = []                
                port = p[0]
                targetPort = p[1]
                containerName = None
                if ':' in targetPort:
                    (containerName,targetPort) = p[1].split(':')
                targetPort = int(targetPort)
                for n in nodes:
                    container_ports = n['ports']
                    hostPort = n['port']
                    for container in container_ports:
                        if containerName and containerName == container['containerName'] and container['containerPort'] == targetPort:
                            hostPort = container['hostPort']
                            output_nodes.append({'ip':n['ip'],'port':hostPort,'id':n['id']})                            
                        elif not containerName and  container['containerPort'] == targetPort:
                            hostPort = container['hostPort']
                            output_nodes.append({'ip':n['ip'],'port':hostPort,'id':n['id']})

                svc_port = "%s_%s" %(svc_name, port)
                logger.info('updating pool: %s' %(svc_port))
                logger.debug(json.dumps(output_nodes))
                for url in self.bigip_urls:
                    try:
                        r = self.post("/mgmt/shared/service-discovery/task/~%s~%s~%s_pool/nodes" %(self.tenant,svc_port,svc_port),data=json.dumps(output_nodes))
                        logger.debug(r)                        
                    except Exception as e:
                        logger.error(e)
                        logger.exception("message")
                        

                r = self.post("/mgmt/tm/sys/config",data="{\"command\":\"save\"}")            
    def wait(self):
        if self.sqs_url:
            time_delta = time.time() - self.last_update
            if time_delta < self.interval:
                time.sleep(self.interval)            
            output =  self.client.wait_on_sqs_queue(self.sqs_url,self.interval)
        else:
            time.sleep(self.interval)
            output = True
            time.sleep(1)
        self.last_update = time.time()
        return output

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Update BIG-IP configuration from ECS Anywhere Cluster')
    parser.add_argument('--cluster',help='name of ECS cluster')
    parser.add_argument('--tenant',help='AS3 tenant')
#    parser.add_argument('--service')
    parser.add_argument('--bigip_urls',help='comma separated address(es) of mgmt / control-plane of BIG-IP device')
    parser.add_argument('--template',default='template.json',help='template of AS3 declaration')
    parser.add_argument("--token",help="use token (remote auth)",action="store_true",default=False)
    parser.add_argument("-u", "--username",default='admin')
    parser.add_argument("-p", "--password",default='admin')
    parser.add_argument("--interval",help="polling cycle",default=30,type=int)
    parser.add_argument("--level",help="log level (default info)",default="info")
    parser.add_argument('--sqs_url',help='sqs queue with task change events')
#    parser.add_argument("--run-once",help="run once",action="store_true",default=False)
    args = parser.parse_args()


    username = args.username
    password = args.password
    cluster = args.cluster
#    service = args.service
    tenant = args.tenant
    if args.bigip_urls:
        bigip_urls = args.bigip_urls.split(',')

    sqs_url = args.sqs_url
    interval = args.interval
    log_level = args.level

    if 'LOG_LEVEL' in os.environ:
        log_level = os.environ['LOG_LEVEL']    
    
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    if log_level == 'debug':
        logger.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    if 'F5_USERNAME' in os.environ:
        username = os.environ['F5_USERNAME']

    if 'F5_PASSWORD' in os.environ:
        password = os.environ['F5_PASSWORD']

    if 'CLUSTER_NAME' in os.environ:
        cluster = os.environ['CLUSTER_NAME']

    if 'BIGIP_URLS' in os.environ:
        bigip_urls = os.environ['BIGIP_URLS'].split(',')

    if 'SQS_URL' in os.environ:
        sqs_url = os.environ['SQS_URL']

    if 'INTERVAL' in os.environ:
        interval = os.environ['INTERVAL']        

    if 'TENANT' in os.environ:
        tenant = os.environ['TENANT']        

    if 'SERVICE_NAME' in os.environ:
        service = os.environ['SERVICE_NAME']    

    controller = BigipEcsController(cluster, username, password, bigip_urls, tenant, args.template,
                                    interval = args.interval,
                                    sqs_url = sqs_url)
    import time
    strike_time = 0
    strike_cnt = 0
    import os
    logger.info("version: 0.0.%d" %(os.stat(__file__)).st_mtime)
    try:
        logger.info("as3: %s" %(controller.check_device()))
    except Exception as e:
        if e.response.status_code == 404:
            logger.error("AS3 not found.  Please ensure BIG-IP is up and AS3 is installed")
            sys.exit(1)            
        logger.error(e)
        logger.exception("message")
        sys.exit(1)
    while 1:
        try:
            controller.update_services()
            controller.generate_template()
            controller.update_pools()
            while not controller.wait():
                pass
        except Exception as e:
            logger.error(e)
            logger.exception("message")
            if (time.time() - strike_time) >= 120:
                strike_time = time.time()
                strike_cnt = 0
            strike_cnt += 1
            logger.error(strike_cnt)
            time.sleep(strike_cnt * 30)
            pass

