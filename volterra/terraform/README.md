# Volterra and AWS PrivateLink

This will create a VPC that hosts an S3 bucket that is
secured using AWS PrivateLink.

You can then deploy a VoltMesh node into the VPC to provide
access to the S3 PrivateLink endpoint from another site.

## Deploying the sample

Sample TFVARS file

```
aws_region = "us-east-1"
az1        = "a"
az2        = "b"
prefix     = "test-example"
ssh_key    = "test"
trusted_ip = "192.0.2.10/32"
```

This will output

```
...
AWS_ENDPOINT_URL = "*.vpce-1234.s3.us-east-1.vpce.amazonaws.com"
AWS_INSTANCE = "192.0.2.20"
EXTERNAL_SUBNET_ID = "subnet-012"
INTERNAL_SUBNET_ID = "subnet-234"
WORKLOAD_SUBNET_ID = "subnet-567"
_VPC_ID = "vpc-1234"
```

You will next need to deploy an AWS Site in VoltConsole that is attached to the VPC.

Next create a TCP Load Balancer that has an origin pool that points to the bucket endpoint.

i.e. "bucket.vpce-1234.s3.us-east-1.vpce.amazonaws.com" as the DNS name of the origin pool in your AWS site.

Create a TCP LB listener on port 443 that uses the same DNS name (bucket.vpce-1234.s3.us-east-1.vpce.amazonaws.com)
and is deployed on your target site.

You can verify the configuration by testing from another IP to verify that it does not allow access over
the public internet (the "trusted_ip" is allowed to enable terraform to clean-up the S3 bucket).

```
$ aws s3 ls s3://test-example-s3bucket20210603133943929700000001

An error occurred (AccessDenied) when calling the ListObjectsV2 operation: Access Denied
```

From your target site you can use the AWS CLI in a docker container to emulate a connection.

```
# set DNS to the interface where you have exposed the service at your site or update /etc/hosts
$ docker run --rm -it --dns 192.168.131.25 -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN amazon/aws-cli s3 --endpoint-url  https://bucket.vpce-1234.s3.us-east-1.vpce.amazonaws.com ls s3://test-example-s3bucket20210603133943929700000001
2021-06-11 19:52:46         17 top-secret-file.txt
```