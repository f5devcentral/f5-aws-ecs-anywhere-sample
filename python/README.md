# Python Examples

## ecs_anywhere_ip_port.py

This script is meant to be a generic method of getting the IP/Port that is associated with
an ECS Service.  It expects that the service is deployed in ECS Anywhere.

## bigip-event-driven.py

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

You can customize the ``template.json`` file to suit your needs.

Example of running the script.

```
 ./bigip-event-driven.py --url https://192.168.1.200 --tenant EcsAnywhere
 INFO:botocore.credentials:Found credentials in environment variables.
INFO:root:updating services
INFO:root:generating templates
INFO:root:updating pools
```
## How it works

The script first lists all of the services associated with the ECS cluster.  It will then look for
any services that have a tag of 'f5-external-ip'.

This information is used to build a AS3 declaration that will define the Load Balancer object on
the BIG-IP device.  It defines the pools/targets as "Event-Driven" endpoints (populated later).

It will next list all the tasks associated with each service and update the associated BIG-IP pool
with the IP/Port of the tasks running in ECS Anywhere.

