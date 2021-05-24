#!/usr/bin/env python
import boto3
import json
import time

class EcsAnyWhereIpPort(object):
    def __init__(self, cluster):
        self.cluster = cluster
        self.ecs_client = boto3.client('ecs')
        self.ssm_client = boto3.client('ssm')
        self.sqs_client = boto3.client('sqs')
        self.task_cache = {}
        self.container_instance_cache = {}        
        self.instance_cache = {}
    def get_tasks(self,service):
        # TODO
        # returns 100 Arns by default
        tasks = self.ecs_client.list_tasks(
            cluster = self.cluster,
            serviceName = service,
            desiredStatus = 'RUNNING')
        taskArns =  tasks.get('taskArns')
        if not taskArns:
            return []
        return taskArns
    def get_ip_port(self,service,cache=True):
        
        if not cache:
            self.task_cache = {}
            self.container_instance_cache = {}        
            self.instance_cache = {}
            
        taskArns = self.get_tasks(service)
        if not taskArns:
            return []
        # TODO
        # limited to 100 Arns
        # cached tasks
        cached_tasks = list(set(taskArns).intersection(set(self.task_cache.keys())))
        tasks_to_get = list(set(taskArns) - set(self.task_cache.keys()))
        tasks = []
        
        if cached_tasks:
            tasks = [self.task_cache[t] for t in cached_tasks]
            
        if tasks_to_get:
            tasks.extend(self.ecs_client.describe_tasks(
                cluster = self.cluster,
                tasks = tasks_to_get
            ).get('tasks',[]))
            
        containerInstanceArns = [a.get('containerInstanceArn') for a in tasks]

        task_map = {}
        ports = []

        container_instance_ip = {}
        task_ports_map = {}
        
        for task in tasks:
            if task['taskArn'] not in cached_tasks:
                self.task_cache[task['taskArn']] = task
            task_ports = []
            skiptask = False
            for container in task['containers']:
                if 'networkBindings' not in container:
                    print("skipping",task['taskArn'])
                    skiptask = True
                    continue
                    del self.task_cache[task['taskArn']]
                for port in container['networkBindings']:
                    p = {'containerName':container['name'],'containerPort':port['containerPort'],'hostPort':port['hostPort']}
                    if p not in task_ports:
                        task_ports.append(p)
            task_ports_map[task['taskArn']] = task_ports
            if skiptask:
                containerInstanceArns.remove(task['containerInstanceArn'])
                continue
               
            container_instance_ip[task.get('containerInstanceArn')] = {}

        if not containerInstanceArns:
            return []
            
        cached_container_instances = list(set(containerInstanceArns).intersection(set(self.container_instance_cache.keys())))
        container_instances_to_get = list(set(containerInstanceArns) - set(self.container_instance_cache.keys()))
        
        container_instances = []
        
        if cached_container_instances:
            tasks = [self.task_cache[t] for t in cached_tasks]

        
        container_instances.extend(self.ecs_client.describe_container_instances(
            cluster = self.cluster,
            containerInstances = containerInstanceArns
            ).get('containerInstances',[]))

        container_map = {}
        for container_instance in container_instances:
            self.container_instance_cache[container_instance['containerInstanceArn']] = container_instance           
            container_map[container_instance['containerInstanceArn']] = container_instance['ec2InstanceId']
        
        instanceIds = [a.get('ec2InstanceId') for a in container_instances]

        cached_instances = list(set(instanceIds).intersection(set(self.instance_cache.keys())))
        instances_to_get = list(set(instanceIds) - set(self.instance_cache.keys()))
        instances = []
        
        if cached_instances:
            instances = [self.task_cache[t] for t in cached_instances]
            
        if instances_to_get:
            instances.extend(self.ssm_client.describe_instance_information(
            InstanceInformationFilterList=[
                {
                    'key': 'InstanceIds',
                    'valueSet': instanceIds
                }]).get('InstanceInformationList',[]))
        
        instance_map = dict([(a['InstanceId'],a['IPAddress']) for a in instances])
        
        ip_and_ports = []
        
        for task in tasks:
            containerInstanceArn = task.get('containerInstanceArn')
            instance_id = container_map[containerInstanceArn]
            ip_addr = instance_map[instance_id]
            instance_port = task_ports_map[task['taskArn']]
            ip_and_ports.append({'id':instance_id,'ip':ip_addr,'port':instance_port[0]['hostPort'],'ports':instance_port})
        return ip_and_ports
    def wait_service(self, service):
        waiter = self.ecs_client.get_waiter('services_stable')
        waiter.wait(cluster=self.cluster,
                    services = [service])
    def list_services(self):
        serviceArns = []
        nextToken = ''
        while 1:
            services = self.ecs_client.list_services( cluster = self.cluster , nextToken = nextToken )
            nextToken = services.get('nextToken')
            serviceArns.extend(services.get('serviceArns'))
            if not nextToken:
                break
            
        return([a.split('/')[-1] for a in serviceArns])
    def describe_service(self, services):
        svc_batch = services
        details = []
        taskDefinitions = {}
        while 1:
            next_batch = svc_batch[10:]
            svc_batch = svc_batch[:10]
            output = self.ecs_client.describe_services( cluster = self.cluster, services = svc_batch, include = ['TAGS'] )
            details.extend([{'taskDefinition':a['taskDefinition'],'tags':a.get('tags',[])} for a in output.get('services',[])])
            if not next_batch:
                break
            svc_batch = next_batch
        all_services =  dict(zip(services,details))
        for svc,val in all_services.items():
            taskDefinition = val['taskDefinition']
            val['taskDefinition'] = taskDefinitions.get(taskDefinition,self.ecs_client.describe_task_definition(taskDefinition = taskDefinition).get('taskDefinition'))
            if taskDefinition not in taskDefinitions:
                taskDefinitions[taskDefinition] = val['taskDefinition']
        return all_services
    def wait_on_sqs_queue(self, sqs_queue, seconds=10):
        "wait up to X seconds, return True if any messages"
        start_time = time.time()
        update_needed = False
        sqs_wait = seconds
        if sqs_wait > 20:
            sqs_wait = 10
        while ( time.time() - start_time ) < seconds:
            response = self.sqs_client.receive_message(QueueUrl = sqs_queue,
                                                       MaxNumberOfMessages = 10,
                                                       WaitTimeSeconds=sqs_wait)
            messages = response.get('Messages',[])

            for msg in messages:
                update_needed = True
                receipt = msg.get('ReceiptHandle')
                response = self.sqs_client.delete_message(
                    QueueUrl=sqs_queue,
                    ReceiptHandle= receipt
                )
            if update_needed:
                return True
        return update_needed

        
if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='retrieve IP and Port of ECS service')
    parser.add_argument('--cluster',help='name of ECS cluster')
    parser.add_argument('--service',help='name of ECS service')
    parser.add_argument('--sqs-url',help='URL of SQS service',dest="sqs_url")    
    args = parser.parse_args()
    client = EcsAnyWhereIpPort(args.cluster)
#    services = client.list_services()
#    print(client.describe_service(services))
#    print(client.wait_on_sqs_queue(args.sqs_url))
#    print(client.list_services())
#    for svc in client.list_services():
#        print(svc)
#        print(json.dumps(client.get_ip_port(svc),indent=4))        
#    client.wait_service(args.service)
    starttime = time.time()
    print(json.dumps(client.get_ip_port(args.service),indent=4))
#    print(time.time() - starttime)
#    starttime = time.time()    
#    print(json.dumps(client.get_ip_port(args.service),indent=4))    
#    print(time.time() - starttime)
