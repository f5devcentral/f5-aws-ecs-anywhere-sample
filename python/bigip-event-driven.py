#!/usr/bin/env python
from icontrol.session import iControlRESTSession
from icontrol.exceptions import iControlUnexpectedHTTPError
from requests.exceptions import HTTPError
from ecs_anywhere_ip_port import EcsAnyWhereIpPort
import os
import json
import sys
import logging
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

class BigipController(object):
    def __init__(self, cluster, username,password, url, tenant, template_file, token=False):
        self.cluster = cluster
        self.username = username
        self.password = password
        self.url = url
        self.tenant = tenant
        self.client = EcsAnyWhereIpPort(cluster)
        self.template_txt = open(template_file).read()
        self.service_map = {}
        if token:
            self.icr = iControlRESTSession(username, password, token='tmos')
        else:
            self.icr = iControlRESTSession(username, password)
        
    def update_services(self,cache=True):

        services = self.client.list_services()
        if cache:
            services = list(set(services) - set(self.service_map.keys()))

        for svc,details in self.client.describe_service(services).items():
            tags = details['tags']
            taskDefinition = details['taskDefinition']
            
            create_config = False
            ip = None
            ports = []
            for tag in tags:
                if tag.get('key') == 'f5-external-ip':
                    ip = tag.get('value')
                    create_config = True
                if tag.get('key').startswith('f5-external-port-'):
                    ports.append((tag.get('key')[17:],tag.get('value')))
            if ip:
                self.service_map[svc] = {'ip':ip }
            if ports:

                self.service_map[svc]['ports'] = ports
            elif ip:
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
        template = json.dumps(template,indent=4)
        #print(template)
        r = self.icr.post(self.url + "/mgmt/shared/appsvcs/declare",data=json.dumps(template))

    def update_pools(self,services=None):

        for svc_name,input_params in self.service_map.items():
            nodes = self.client.get_ip_port(svc_name)
            input_ports = input_params['ports']
            container_ports = nodes[0]['ports']
            hostPort = nodes[0]['port']

            for p in input_ports:
                output_nodes = []                
                port = p[0]
                targetPort = p[1]
                containerName = None
                if ':' in targetPort:
                    (containerName,targetPort) = p[1].split(':')
                targetPort = int(targetPort)
                for container in container_ports:
                    if containerName and containerName == container['containerName'] and container['containerPort'] == targetPort:
                        hostPort = container['hostPort']
                    elif container['containerPort'] == targetPort:
                        hostPort = container['hostPort']
                for n in nodes:
                    output_nodes.append({'ip':n['ip'],'port':hostPort,'id':n['id']})

                svc_port = "%s_%s" %(svc_name, port)
                #print(svc_port)
                #print(output_nodes)                
                r = self.icr.post(self.url + "/mgmt/shared/service-discovery/task/~%s~%s~%s_pool/nodes" %(self.tenant,svc_port,svc_port),data=json.dumps(output_nodes))
                #print(r)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Update BIG-IP configuration from ECS Anywhere Cluster')
    parser.add_argument('--cluster',help='name of ECS cluster')
    parser.add_argument('--tenant',help='AS3 tenant')
#    parser.add_argument('--service')
    parser.add_argument('--url',help='address of mgmt / control-plane of BIG-IP device')
    parser.add_argument('--template',default='template.json',help='template of AS3 declaration')
    parser.add_argument("--token",help="use token (remote auth)",action="store_true",default=False)
    parser.add_argument("-u", "--username",default='admin')
    parser.add_argument("-p", "--password",default='admin')
    parser.add_argument("--interval",help="polling cycle",default=10,type=int)
    parser.add_argument("--level",help="log level (default info)",default="info")
#    parser.add_argument("--run-once",help="run once",action="store_true",default=False)
    args = parser.parse_args()


    username = args.username
    password = args.password
    cluster = args.cluster
    service = args.service
    tenant = args.tenant

    if args.level == 'debug':
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    if 'F5_USERNAME' in os.environ:
        username = os.environ['F5_USERNAME']

    if 'F5_PASSWORD' in os.environ:
        password = os.environ['F5_PASSWORD']

    if 'CLUSTER_NAME' in os.environ:
        cluster = os.environ['CLUSTER_NAME']

    if 'SERVICE_NAME' in os.environ:
        service = os.environ['SERVICE_NAME']    

    controller = BigipController(cluster, username, password, args.url, tenant, args.template)
    import time
    while 1:
        logging.info('updating services')
        controller.update_services()
        logging.info('generating templates')        
        controller.generate_template()
        logging.info('updating pools')                
        controller.update_pools()
        time.sleep(args.interval)
