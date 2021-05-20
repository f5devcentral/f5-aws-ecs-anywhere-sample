# Python Examples
## Creating a F5 BIG-IP Controller for ECS

This directory contains Python code for automating the configuration of a BIG-IP device based on the service definitions in ECS Anywhere.

### Building the Controller

To create the controller you will first need to build your own Docker container.  For example

```
$ docker build -t bigip-ecs-ctrl .
```

Once you have built the container you can either run it locally or in ECS.  

### Running the controller in ECS

Before you can run the controller in ECS you need to have appropriate taskExecution and taskRoles configured.

In general the controller will need read-only access to ECS/SSM and a specific AWS Secret (BIG-IP password)

See [external-task-definition-bigip-ecs-ctrl.json](external-task-definition-bigip-ecs-ctrl.json) for an example of how to create a task definition.

You will want to modify the input variables to match your environment.  

## Python files

### ecs_anywhere_ip_port.py

This script is meant to be a generic method of getting the IP/Port that is associated with
an ECS Service.  It expects that the service is deployed in ECS Anywhere.

### bigip-ecs-ctrl.py

This script is used with ``ecs_anywhere_ip_port.py``.  It will run in the foreground and query
the AWS APIs to update a BIG-IP configuration with ECS Services.

To use this script you will first need to have sufficient IAM privileges to read the ECS/SSM APIs.

You will also need to have "admin" privileges on a BIG-IP device and installed Application Services
Extension 3 (AS3) version 3.26.0 or newer.

The script expects that a tag is added to the ECS Service.  The most basic tag is

- f5-external-ip: 192.0.2.10

In this example it will create a TCP Virtual Server using the first port that is exposed with
the associated task.

The script can also handle more complex examples of mapping to specific ports/containers.

- f5-external-ip: 192.0.2.11
- f5-external-port-80: 8080
- f5-external-port-443: nginx:8443

You can customize the [template.json](template.json) file to suit your needs.

There are some environment variables you will want to set.

```
# AWS credentials or via task/instance role
export AWS_DEFAULT_REGION=us-east-1
export CLUSTER_NAME=[name of ECS cluster]
export F5_PASSWORD="[password]"
```

Example of running the script.

```
 ./bigip-ecs-ctrl.py --url https://192.168.1.245 --tenant EcsAnywhere
 2021-05-19 21:06:14,749 - bigip_ecs_controller - INFO - updating service: chen-ecs-anywhere-svc
2021-05-19 21:06:14,749 - bigip_ecs_controller - INFO - generating templates
2021-05-19 21:06:15,894 - bigip_ecs_controller - INFO - updating pool: chen-ecs-anywhere-svc_8080
2021-05-19 21:06:26,115 - bigip_ecs_controller - INFO - updating service: chen-ecs-anywhere-svc
```
## How it works

The script first lists all of the services associated with the ECS cluster.  It will then look for
any services that have a tag of 'f5-external-ip'.

This information is used to build a AS3 declaration that will define the Load Balancer object on
the BIG-IP device.  It defines the pools/targets as "Event-Driven" endpoints (populated later).

It will next list all the tasks associated with each service and update the associated BIG-IP pool
with the IP/Port of the tasks running in ECS Anywhere.

