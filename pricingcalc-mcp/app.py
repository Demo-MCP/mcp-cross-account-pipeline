#!/usr/bin/env python3
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import yaml
import json
import boto3
from cfn_mappings import CFN_TO_CLASS_MAPPINGS

app = FastAPI()

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[Dict[str, Any]] = None

# Initialize AWS Pricing client
pricing_client = boto3.client('pricing', region_name='us-east-1')

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/pricingcalc")
async def mcp_endpoint(request: JSONRPCRequest):
    if request.method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": {
                "tools": [
                    {
                        "name": "pricingcalc_estimate_from_cfn",
                        "description": "Estimate AWS costs from CloudFormation template using AWS Pricing API",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "template_content": {"type": "string"}
                            },
                            "required": ["template_content"]
                        }
                    },
                    {
                        "name": "pricingcalc_estimate_with_custom_specs",
                        "description": "Estimate costs with custom resource specifications (e.g., 'ECS with 8 vCPU and 15GB memory')",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "custom_specs": {
                                    "type": "string",
                                    "description": "Custom specifications in human language"
                                }
                            },
                            "required": ["custom_specs"]
                        }
                    },
                    {
                        "name": "pricingcalc_estimate_from_stack",
                        "description": "Estimate AWS costs from existing CloudFormation stack",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "stack_name": {"type": "string"}
                            },
                            "required": ["stack_name"]
                        }
                    }
                ]
            }
        }
    
    elif request.method == "tools/call":
        tool_name = request.params.get("name") if request.params else None
        args = request.params.get("arguments", {}) if request.params else {}
        
        if tool_name == "pricingcalc_estimate_from_cfn":
            template_content = args.get("template_content", "")
            # Get region from metadata context, default to us-east-1
            region = request.params.get("metadata", {}).get("region", "us-east-1") if request.params else "us-east-1"
            
            return estimate_costs(template_content, region, {})
        
        elif tool_name == "pricingcalc_estimate_with_custom_specs":
            custom_specs = args.get("custom_specs", "")
            # Get region from metadata context, default to us-east-1  
            region = request.params.get("metadata", {}).get("region", "us-east-1") if request.params else "us-east-1"
            
            # Parse custom specs and convert to template
            parsed_result = parse_custom_specs(custom_specs)
            
            template_content = ""
            if "template" in parsed_result:
                # Use the generated template
                import json
                template_content = json.dumps(parsed_result["template"])
            
            return estimate_costs(template_content, region, {})
        
        elif tool_name == "pricingcalc_estimate_from_stack":
            stack_name = args.get("stack_name", "")
            # Get account_id and region from metadata context
            metadata = request.params.get("metadata", {}) if request.params else {}
            account_id = metadata.get("account_id", "")
            region = metadata.get("region", "us-east-1")
            
            # Get stack template from CloudFormation
            try:
                import boto3
                
                # Check if we need to assume role for different account
                current_account = boto3.client('sts').get_caller_identity()['Account']
                
                if account_id != current_account:
                    # Assume role in target account
                    sts_client = boto3.client('sts')
                    role_arn = f"arn:aws:iam::{account_id}:role/McpServerTaskRole"
                    
                    assumed_role = sts_client.assume_role(
                        RoleArn=role_arn,
                        RoleSessionName="pricing-calculator-session"
                    )
                    
                    # Create CloudFormation client with assumed role credentials
                    cf_client = boto3.client(
                        'cloudformation',
                        region_name=region,
                        aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                        aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                        aws_session_token=assumed_role['Credentials']['SessionToken']
                    )
                else:
                    # Use current account credentials
                    cf_client = boto3.client('cloudformation', region_name=region)
                
                response = cf_client.get_template(StackName=stack_name)
                template_body = response['TemplateBody']
                
                # Convert template to string if it's a dict
                if isinstance(template_body, dict):
                    template_content = json.dumps(template_body)
                else:
                    template_content = str(template_body)
                
                return estimate_costs(template_content, region, {})
            except Exception as e:
                return {"error": f"Failed to fetch stack template: {str(e)}"}
            
            template_content = args.get("template_content", "")
            region = args.get("region", "us-east-1")
            
            # Parse template with CloudFormation support
            try:
                if template_content.strip().startswith('{'):
                    template = json.loads(template_content)
                else:
                    # Handle CloudFormation YAML with custom loader
                    import yaml
                    
                    # Custom constructor for CloudFormation intrinsic functions
                    def construct_ref(loader, node):
                        return {'Ref': loader.construct_scalar(node)}
                    
                    def construct_getatt(loader, node):
                        if isinstance(node, yaml.ScalarNode):
                            return {'Fn::GetAtt': loader.construct_scalar(node).split('.')}
                        elif isinstance(node, yaml.SequenceNode):
                            return {'Fn::GetAtt': loader.construct_sequence(node)}
                    
                    def construct_sub(loader, node):
                        return {'Fn::Sub': loader.construct_scalar(node)}
                    
                    def construct_join(loader, node):
                        return {'Fn::Join': loader.construct_sequence(node)}
                    
                    # Create custom loader
                    class CFNLoader(yaml.SafeLoader):
                        pass
                    
                    # Add constructors for CloudFormation functions
                    CFNLoader.add_constructor('!Ref', construct_ref)
                    CFNLoader.add_constructor('!GetAtt', construct_getatt)
                    CFNLoader.add_constructor('!Sub', construct_sub)
                    CFNLoader.add_constructor('!Join', construct_join)
                    
                    template = yaml.load(template_content, Loader=CFNLoader)
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "result": {"error": f"Failed to parse template: {e}"}
                }
            
            # Extract resources
            resources = template.get('Resources', {})
            bom = []
            unpriced_resources = []
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get('Type')
                properties = resource_def.get('Properties', {})
                
                if resource_type in CFN_TO_CLASS_MAPPINGS:
                    bom.append({
                        'name': resource_name,
                        'type': resource_type,
                        'class': CFN_TO_CLASS_MAPPINGS[resource_type],
                        'properties': properties
                    })
                else:
                    unpriced_resources.append({
                        'name': resource_name,
                        'type': resource_type,
                        'reason': 'Unsupported resource type'
                    })
            
            # Generate cost estimates using AWS Pricing API
            resource_estimates = []
            total_costs = {"low": 0, "medium": 0, "high": 0}
            
            for resource in bom:
                try:
                    costs = get_aws_pricing(resource, region)
                    
                    resource_estimate = {
                        "name": resource["name"],
                        "type": resource["type"],
                        "service": get_service_name(resource["type"]),
                        "monthly_cost": costs["monthly_cost"],
                        "pricing_details": costs["pricing_details"],
                        "assumptions": costs["assumptions"]
                    }
                    
                    resource_estimates.append(resource_estimate)
                    total_costs["low"] += costs["monthly_cost"]["low"]
                    total_costs["medium"] += costs["monthly_cost"]["medium"]
                    total_costs["high"] += costs["monthly_cost"]["high"]
                    
                except Exception as e:
                    # Don't use fallback - show API error instead
                    resource_estimate = {
                        "name": resource["name"],
                        "type": resource["type"],
                        "service": get_service_name(resource["type"]),
                        "monthly_cost": {
                            "low": 0,
                            "medium": 0,
                            "high": 0
                        },
                        "pricing_details": {"source": "error", "error": str(e)},
                        "assumptions": [f"Pricing API error: {str(e)}"]
                    }
                    resource_estimates.append(resource_estimate)
            
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "resources": resource_estimates,
                    "total_monthly_cost": total_costs,
                    "unpriced_resources": unpriced_resources,
                    "summary": {
                        "total_resources": len(bom),
                        "unpriced_resources": len(unpriced_resources),
                        "coverage": f"{len(bom)}/{len(bom) + len(unpriced_resources)} resources priced",
                        "region": region
                    },
                    "methodology": [
                        "Estimates based on AWS Pricing API for On-Demand pricing",
                        f"Pricing data retrieved for {region} region",
                        "Low usage: 25% utilization for compute, minimal storage/requests",
                        "Medium usage: 75% utilization for compute, moderate storage/requests",
                        "High usage: 100% utilization for compute, high storage/requests",
                        "Costs exclude data transfer, support plans, and reserved instance discounts"
                    ]
                }
            }
    
    return {
        "jsonrpc": "2.0", 
        "id": request.id,
        "result": {"message": "Pricing calculator MCP service"}
    }

def parse_custom_specs(custom_specs: str) -> Dict[str, Dict]:
    """Parse human language custom specifications into CloudFormation template"""
    import re
    
    # Create a template structure with resources
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {}
    }
    
    specs_lower = custom_specs.lower()
    
    # EC2 Instance parsing
    if "ec2" in specs_lower or "instance" in specs_lower:
        vcpu_match = re.search(r'(\d+)\s*vcpu', specs_lower)
        memory_match = re.search(r'(\d+)\s*gb\s*memory', specs_lower)
        
        instance_type = "t3.micro"  # default
        
        if vcpu_match and memory_match:
            vcpu = int(vcpu_match.group(1))
            memory = int(memory_match.group(1))
            
            # Map vCPU/memory to instance types
            if vcpu >= 8 and memory >= 15:
                instance_type = "m5.2xlarge"  # 8 vCPU, 32 GB
            elif vcpu >= 4 and memory >= 8:
                instance_type = "m5.xlarge"   # 4 vCPU, 16 GB
            elif vcpu >= 2 and memory >= 4:
                instance_type = "m5.large"    # 2 vCPU, 8 GB
            elif vcpu >= 1:
                instance_type = "t3.small"    # 2 vCPU, 2 GB
        
        template["Resources"]["CustomEC2Instance"] = {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "InstanceType": instance_type
            }
        }
    
    # RDS Database parsing
    if "rds" in specs_lower or "database" in specs_lower or "mysql" in specs_lower or "postgres" in specs_lower:
        db_class = "db.t3.micro"
        storage = 20
        engine = "mysql"
        
        storage_match = re.search(r'(\d+)\s*gb\s*storage', specs_lower)
        if storage_match:
            storage = int(storage_match.group(1))
        
        if "postgres" in specs_lower:
            engine = "postgres"
        elif "oracle" in specs_lower:
            engine = "oracle-ee"
        
        if "large" in specs_lower:
            db_class = "db.t3.large"
        elif "medium" in specs_lower:
            db_class = "db.t3.medium"
        
        template["Resources"]["CustomRDSInstance"] = {
            "Type": "AWS::RDS::DBInstance",
            "Properties": {
                "DBInstanceClass": db_class,
                "AllocatedStorage": storage,
                "Engine": engine
            }
        }
    
    # Lambda Function parsing
    if "lambda" in specs_lower or "function" in specs_lower:
        memory = 128  # default
        
        memory_match = re.search(r'(\d+)\s*(mb|gb)', specs_lower)
        if memory_match:
            memory_val = int(memory_match.group(1))
            if memory_match.group(2) == 'gb':
                memory_val *= 1024
            memory = memory_val
        
        template["Resources"]["CustomLambdaFunction"] = {
            "Type": "AWS::Lambda::Function",
            "Properties": {
                "MemorySize": memory,
                "Runtime": "python3.9",
                "Handler": "index.handler",
                "Code": {"ZipFile": "def handler(event, context): return 'Hello'"}
            }
        }
    
    # S3 Bucket parsing
    if "s3" in specs_lower or "bucket" in specs_lower or "storage" in specs_lower:
        template["Resources"]["CustomS3Bucket"] = {
            "Type": "AWS::S3::Bucket",
            "Properties": {}
        }
    
    # DynamoDB Table parsing
    if "dynamodb" in specs_lower or "table" in specs_lower or "nosql" in specs_lower:
        read_capacity = 5
        write_capacity = 5
        
        capacity_match = re.search(r'(\d+)\s*(read|write)\s*capacity', specs_lower)
        if capacity_match:
            capacity_val = int(capacity_match.group(1))
            if "read" in capacity_match.group(2):
                read_capacity = capacity_val
            else:
                write_capacity = capacity_val
        
        template["Resources"]["CustomDynamoDBTable"] = {
            "Type": "AWS::DynamoDB::Table",
            "Properties": {
                "AttributeDefinitions": [
                    {"AttributeName": "id", "AttributeType": "S"}
                ],
                "KeySchema": [
                    {"AttributeName": "id", "KeyType": "HASH"}
                ],
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": read_capacity,
                    "WriteCapacityUnits": write_capacity
                }
            }
        }
    
    # ELB/ALB parsing
    if "elb" in specs_lower or "load balancer" in specs_lower or "alb" in specs_lower:
        lb_type = "application"
        if "network" in specs_lower or "nlb" in specs_lower:
            lb_type = "network"
        
        template["Resources"]["CustomLoadBalancer"] = {
            "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
            "Properties": {
                "Type": lb_type,
                "Scheme": "internet-facing"
            }
        }
    
    # ECS Service parsing
    if "ecs" in specs_lower and ("service" in specs_lower or "container" in specs_lower):
        vcpu = 256
        memory = 512
        
        vcpu_match = re.search(r'(\d+)\s*vcpu', specs_lower)
        memory_match = re.search(r'(\d+)\s*gb\s*memory', specs_lower)
        
        if vcpu_match:
            vcpu = int(vcpu_match.group(1)) * 1024  # Convert to CPU units
        if memory_match:
            memory = int(memory_match.group(1)) * 1024  # Convert to MB
        
        template["Resources"]["CustomECSService"] = {
            "Type": "AWS::ECS::Service",
            "Properties": {
                "Cluster": "default",
                "TaskDefinition": {
                    "Cpu": str(vcpu),
                    "Memory": str(memory),
                    "RequiresCompatibilities": ["FARGATE"],
                    "NetworkMode": "awsvpc"
                }
            }
        }
    
    # ElastiCache parsing
    if "elasticache" in specs_lower or "redis" in specs_lower or "memcached" in specs_lower:
        engine = "redis"
        node_type = "cache.t3.micro"
        
        if "memcached" in specs_lower:
            engine = "memcached"
        
        if "large" in specs_lower:
            node_type = "cache.t3.large"
        elif "medium" in specs_lower:
            node_type = "cache.t3.medium"
        
        template["Resources"]["CustomElastiCacheCluster"] = {
            "Type": "AWS::ElastiCache::CacheCluster",
            "Properties": {
                "Engine": engine,
                "CacheNodeType": node_type,
                "NumCacheNodes": 1
            }
        }
    
    # CloudFront parsing
    if "cloudfront" in specs_lower or "cdn" in specs_lower:
        template["Resources"]["CustomCloudFrontDistribution"] = {
            "Type": "AWS::CloudFront::Distribution",
            "Properties": {
                "DistributionConfig": {
                    "Origins": [{
                        "Id": "myOrigin",
                        "DomainName": "example.com",
                        "CustomOriginConfig": {
                            "HTTPPort": 80,
                            "OriginProtocolPolicy": "http-only"
                        }
                    }],
                    "DefaultCacheBehavior": {
                        "TargetOriginId": "myOrigin",
                        "ViewerProtocolPolicy": "redirect-to-https"
                    },
                    "Enabled": True
                }
            }
        }
    
    # API Gateway parsing
    if "api gateway" in specs_lower or "api" in specs_lower:
        template["Resources"]["CustomAPIGateway"] = {
            "Type": "AWS::ApiGateway::RestApi",
            "Properties": {
                "Name": "CustomAPI",
                "Description": "Custom API Gateway"
            }
        }
    
    # SNS Topic parsing
    if "sns" in specs_lower or "topic" in specs_lower or "notification" in specs_lower:
        template["Resources"]["CustomSNSTopic"] = {
            "Type": "AWS::SNS::Topic",
            "Properties": {
                "TopicName": "CustomTopic"
            }
        }
    
    # SQS Queue parsing
    if "sqs" in specs_lower or "queue" in specs_lower:
        template["Resources"]["CustomSQSQueue"] = {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": "CustomQueue"
            }
        }
    
    # Kinesis Stream parsing
    if "kinesis" in specs_lower or "stream" in specs_lower:
        shards = 1
        shard_match = re.search(r'(\d+)\s*shard', specs_lower)
        if shard_match:
            shards = int(shard_match.group(1))
        
        template["Resources"]["CustomKinesisStream"] = {
            "Type": "AWS::Kinesis::Stream",
            "Properties": {
                "ShardCount": shards
            }
        }
    
    # EFS File System parsing
    if "efs" in specs_lower or "file system" in specs_lower:
        template["Resources"]["CustomEFSFileSystem"] = {
            "Type": "AWS::EFS::FileSystem",
            "Properties": {
                "PerformanceMode": "generalPurpose"
            }
        }
    
    # EBS Volume parsing
    if "ebs" in specs_lower or "volume" in specs_lower:
        size = 10
        volume_type = "gp3"
        
        size_match = re.search(r'(\d+)\s*gb', specs_lower)
        if size_match:
            size = int(size_match.group(1))
        
        if "io1" in specs_lower or "io2" in specs_lower:
            volume_type = "io1"
        elif "gp2" in specs_lower:
            volume_type = "gp2"
        
        template["Resources"]["CustomEBSVolume"] = {
            "Type": "AWS::EC2::Volume",
            "Properties": {
                "Size": size,
                "VolumeType": volume_type,
                "AvailabilityZone": "us-east-1a"
            }
        }
    
    # NAT Gateway parsing
    if "nat gateway" in specs_lower or "nat" in specs_lower:
        template["Resources"]["CustomNATGateway"] = {
            "Type": "AWS::EC2::NatGateway",
            "Properties": {
                "AllocationId": "eipalloc-12345",
                "SubnetId": "subnet-12345"
            }
        }
    
    # VPC Endpoint parsing
    if "vpc endpoint" in specs_lower or "endpoint" in specs_lower:
        template["Resources"]["CustomVPCEndpoint"] = {
            "Type": "AWS::EC2::VPCEndpoint",
            "Properties": {
                "VpcId": "vpc-12345",
                "ServiceName": "com.amazonaws.us-east-1.s3"
            }
        }
    
    # CloudWatch Log Group parsing
    if "cloudwatch" in specs_lower or "logs" in specs_lower:
        retention = 7
        retention_match = re.search(r'(\d+)\s*day', specs_lower)
        if retention_match:
            retention = int(retention_match.group(1))
        
        template["Resources"]["CustomLogGroup"] = {
            "Type": "AWS::Logs::LogGroup",
            "Properties": {
                "LogGroupName": "/custom/logs",
                "RetentionInDays": retention
            }
        }
    
    # Redshift Cluster parsing
    if "redshift" in specs_lower or "data warehouse" in specs_lower:
        node_type = "dc2.large"
        nodes = 1
        
        if "large" in specs_lower:
            node_type = "dc2.8xlarge"
        
        nodes_match = re.search(r'(\d+)\s*node', specs_lower)
        if nodes_match:
            nodes = int(nodes_match.group(1))
        
        template["Resources"]["CustomRedshiftCluster"] = {
            "Type": "AWS::Redshift::Cluster",
            "Properties": {
                "NodeType": node_type,
                "NumberOfNodes": nodes,
                "MasterUsername": "admin",
                "MasterUserPassword": "password123",
                "DBName": "mydb"
            }
        }
    
    # EKS Cluster parsing
    if "eks" in specs_lower or "kubernetes" in specs_lower:
        template["Resources"]["CustomEKSCluster"] = {
            "Type": "AWS::EKS::Cluster",
            "Properties": {
                "Name": "custom-cluster",
                "Version": "1.21",
                "RoleArn": "arn:aws:iam::123456789012:role/eks-service-role"
            }
        }
    
    # Step Functions parsing
    if "step functions" in specs_lower or "state machine" in specs_lower:
        template["Resources"]["CustomStateMachine"] = {
            "Type": "AWS::StepFunctions::StateMachine",
            "Properties": {
                "StateMachineName": "CustomStateMachine",
                "DefinitionString": '{"Comment": "A Hello World example"}',
                "RoleArn": "arn:aws:iam::123456789012:role/stepfunctions-role"
            }
        }
    
    # Glue Job parsing
    if "glue" in specs_lower or "etl" in specs_lower:
        template["Resources"]["CustomGlueJob"] = {
            "Type": "AWS::Glue::Job",
            "Properties": {
                "Name": "CustomGlueJob",
                "Role": "arn:aws:iam::123456789012:role/glue-role",
                "Command": {
                    "Name": "glueetl",
                    "ScriptLocation": "s3://my-bucket/script.py"
                }
            }
        }
    
    # CodeBuild Project parsing
    if "codebuild" in specs_lower or "build" in specs_lower:
        template["Resources"]["CustomCodeBuildProject"] = {
            "Type": "AWS::CodeBuild::Project",
            "Properties": {
                "Name": "CustomBuildProject",
                "ServiceRole": "arn:aws:iam::123456789012:role/codebuild-role",
                "Artifacts": {"Type": "NO_ARTIFACTS"},
                "Environment": {
                    "Type": "LINUX_CONTAINER",
                    "ComputeType": "BUILD_GENERAL1_MEDIUM",
                    "Image": "aws/codebuild/standard:5.0"
                },
                "Source": {"Type": "NO_SOURCE"}
            }
        }
    
    # Secrets Manager parsing
    if "secrets manager" in specs_lower or "secret" in specs_lower:
        template["Resources"]["CustomSecret"] = {
            "Type": "AWS::SecretsManager::Secret",
            "Properties": {
                "Name": "CustomSecret",
                "Description": "Custom secret"
            }
        }
    
    # Route53 Zone parsing
    if "route53" in specs_lower or "dns" in specs_lower or "hosted zone" in specs_lower:
        template["Resources"]["CustomHostedZone"] = {
            "Type": "AWS::Route53::HostedZone",
            "Properties": {
                "Name": "example.com"
            }
        }
    
    # CloudTrail parsing
    if "cloudtrail" in specs_lower or "audit" in specs_lower:
        template["Resources"]["CustomCloudTrail"] = {
            "Type": "AWS::CloudTrail::Trail",
            "Properties": {
                "TrailName": "CustomTrail",
                "S3BucketName": "my-cloudtrail-bucket",
                "IsLogging": True
            }
        }
    
    # Config Rule parsing
    if "config" in specs_lower or "compliance" in specs_lower:
        template["Resources"]["CustomConfigRule"] = {
            "Type": "AWS::Config::ConfigRule",
            "Properties": {
                "ConfigRuleName": "CustomConfigRule",
                "Source": {
                    "Owner": "AWS",
                    "SourceIdentifier": "S3_BUCKET_PUBLIC_ACCESS_PROHIBITED"
                }
            }
        }
    
    # Backup Vault parsing
    if "backup" in specs_lower or "vault" in specs_lower:
        template["Resources"]["CustomBackupVault"] = {
            "Type": "AWS::Backup::BackupVault",
            "Properties": {
                "BackupVaultName": "CustomBackupVault"
            }
        }
    
    # MSK Cluster parsing
    if "msk" in specs_lower or "kafka" in specs_lower:
        template["Resources"]["CustomMSKCluster"] = {
            "Type": "AWS::MSK::Cluster",
            "Properties": {
                "ClusterName": "CustomMSKCluster",
                "KafkaVersion": "2.8.0",
                "NumberOfBrokerNodes": 3,
                "BrokerNodeGroupInfo": {
                    "InstanceType": "kafka.m5.large",
                    "ClientSubnets": ["subnet-12345", "subnet-67890"]
                }
            }
        }
    
    # MQ Broker parsing
    if "mq" in specs_lower or "message broker" in specs_lower or "activemq" in specs_lower:
        template["Resources"]["CustomMQBroker"] = {
            "Type": "AWS::AmazonMQ::Broker",
            "Properties": {
                "BrokerName": "CustomMQBroker",
                "EngineType": "ActiveMQ",
                "EngineVersion": "5.15.0",
                "HostInstanceType": "mq.t2.micro",
                "Users": [{
                    "Username": "admin",
                    "Password": "password123"
                }]
            }
        }
    
    # Directory Service parsing
    if "directory service" in specs_lower or "active directory" in specs_lower:
        template["Resources"]["CustomDirectory"] = {
            "Type": "AWS::DirectoryService::MicrosoftAD",
            "Properties": {
                "Name": "corp.example.com",
                "Password": "password123",
                "VpcSettings": {
                    "VpcId": "vpc-12345",
                    "SubnetIds": ["subnet-12345", "subnet-67890"]
                }
            }
        }
    
    # DMS Replication Instance parsing
    if "dms" in specs_lower or "database migration" in specs_lower:
        template["Resources"]["CustomDMSInstance"] = {
            "Type": "AWS::DMS::ReplicationInstance",
            "Properties": {
                "ReplicationInstanceIdentifier": "custom-dms-instance",
                "ReplicationInstanceClass": "dms.t2.micro"
            }
        }
    
    # DocumentDB Cluster parsing
    if "documentdb" in specs_lower or "docdb" in specs_lower or "mongodb" in specs_lower:
        template["Resources"]["CustomDocDBCluster"] = {
            "Type": "AWS::DocDB::DBCluster",
            "Properties": {
                "DBClusterIdentifier": "custom-docdb-cluster",
                "MasterUsername": "admin",
                "MasterUserPassword": "password123"
            }
        }
    
    # Neptune Cluster parsing
    if "neptune" in specs_lower or "graph database" in specs_lower:
        template["Resources"]["CustomNeptuneCluster"] = {
            "Type": "AWS::Neptune::DBCluster",
            "Properties": {
                "DBClusterIdentifier": "custom-neptune-cluster"
            }
        }
    
    # FSx File System parsing
    if "fsx" in specs_lower or "lustre" in specs_lower or "windows file system" in specs_lower:
        fs_type = "LUSTRE"
        if "windows" in specs_lower:
            fs_type = "WINDOWS"
        
        template["Resources"]["CustomFSxFileSystem"] = {
            "Type": "AWS::FSx::FileSystem",
            "Properties": {
                "FileSystemType": fs_type,
                "StorageCapacity": 1200,
                "SubnetIds": ["subnet-12345"]
            }
        }
    
    # Lightsail Instance parsing
    if "lightsail" in specs_lower:
        template["Resources"]["CustomLightsailInstance"] = {
            "Type": "AWS::Lightsail::Instance",
            "Properties": {
                "InstanceName": "custom-lightsail",
                "BlueprintId": "amazon_linux_2",
                "BundleId": "nano_2_0"
            }
        }
    
    # Global Accelerator parsing
    if "global accelerator" in specs_lower or "accelerator" in specs_lower:
        template["Resources"]["CustomGlobalAccelerator"] = {
            "Type": "AWS::GlobalAccelerator::Accelerator",
            "Properties": {
                "Name": "CustomAccelerator",
                "IpAddressType": "IPV4",
                "Enabled": True
            }
        }
    
    # WAF Web ACL parsing
    if "waf" in specs_lower or "web acl" in specs_lower:
        template["Resources"]["CustomWebACL"] = {
            "Type": "AWS::WAFv2::WebACL",
            "Properties": {
                "Name": "CustomWebACL",
                "Scope": "REGIONAL",
                "DefaultAction": {"Allow": {}},
                "Rules": []
            }
        }
    
    # Network Firewall parsing
    if "network firewall" in specs_lower or "firewall" in specs_lower:
        template["Resources"]["CustomNetworkFirewall"] = {
            "Type": "AWS::NetworkFirewall::Firewall",
            "Properties": {
                "FirewallName": "CustomFirewall",
                "FirewallPolicyArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/policy",
                "VpcId": "vpc-12345",
                "SubnetMappings": [{"SubnetId": "subnet-12345"}]
            }
        }
    
    # Transfer Server parsing
    if "transfer" in specs_lower or "sftp" in specs_lower:
        template["Resources"]["CustomTransferServer"] = {
            "Type": "AWS::Transfer::Server",
            "Properties": {
                "EndpointType": "PUBLIC",
                "Protocols": ["SFTP"]
            }
        }
    
    # MWAA Environment parsing
    if "mwaa" in specs_lower or "airflow" in specs_lower:
        template["Resources"]["CustomMWAAEnvironment"] = {
            "Type": "AWS::MWAA::Environment",
            "Properties": {
                "Name": "CustomAirflowEnvironment",
                "SourceBucketArn": "arn:aws:s3:::my-airflow-bucket",
                "DagS3Path": "dags/",
                "ExecutionRoleArn": "arn:aws:iam::123456789012:role/mwaa-role",
                "NetworkConfiguration": {
                    "SubnetIds": ["subnet-12345", "subnet-67890"]
                }
            }
        }
    
    # Grafana Workspace parsing
    if "grafana" in specs_lower or "monitoring dashboard" in specs_lower:
        template["Resources"]["CustomGrafanaWorkspace"] = {
            "Type": "AWS::Grafana::Workspace",
            "Properties": {
                "Name": "CustomGrafanaWorkspace",
                "AccountAccessType": "CURRENT_ACCOUNT",
                "AuthenticationProviders": ["AWS_SSO"]
            }
        }
    
    # Return the template as overrides format
    return {"template": template}

def estimate_costs(template_content: str, region: str, overrides: Dict) -> Dict:
    """Main cost estimation function"""
    # Parse template with CloudFormation support
    try:
        if template_content.strip().startswith('{'):
            template = json.loads(template_content)
        else:
            # Handle CloudFormation YAML with custom loader
            import yaml
            
            # Custom constructor for CloudFormation intrinsic functions
            def construct_ref(loader, node):
                return {'Ref': loader.construct_scalar(node)}
            
            def construct_getatt(loader, node):
                if isinstance(node, yaml.ScalarNode):
                    return {'Fn::GetAtt': loader.construct_scalar(node).split('.')}
                elif isinstance(node, yaml.SequenceNode):
                    return {'Fn::GetAtt': loader.construct_sequence(node)}
            
            def construct_sub(loader, node):
                return {'Fn::Sub': loader.construct_scalar(node)}
            
            def construct_join(loader, node):
                return {'Fn::Join': loader.construct_sequence(node)}
            
            # Create custom loader
            class CFNLoader(yaml.SafeLoader):
                pass
            
            # Add constructors for CloudFormation functions
            CFNLoader.add_constructor('!Ref', construct_ref)
            CFNLoader.add_constructor('!GetAtt', construct_getatt)
            CFNLoader.add_constructor('!Sub', construct_sub)
            CFNLoader.add_constructor('!Join', construct_join)
            
            template = yaml.load(template_content, Loader=CFNLoader)
    except Exception as e:
        return {"error": f"Failed to parse template: {e}"}
    
    # Handle empty or None template
    if template is None:
        template = {"Resources": {}}
    
    # Extract resources
    resources = template.get('Resources', {})
    bom = []
    unpriced_resources = []
    
    for resource_name, resource_def in resources.items():
        resource_type = resource_def.get('Type')
        properties = resource_def.get('Properties', {})
        
        if resource_type in CFN_TO_CLASS_MAPPINGS:
            bom.append({
                'name': resource_name,
                'type': resource_type,
                'class': CFN_TO_CLASS_MAPPINGS[resource_type],
                'properties': properties
            })
        else:
            unpriced_resources.append({
                'name': resource_name,
                'type': resource_type,
                'reason': 'Unsupported resource type'
            })
    
    # Generate cost estimates
    resource_estimates = []
    total_costs = {"low": 0, "medium": 0, "high": 0}
    
    for resource in bom:
        try:
            # Pass overrides to pricing functions
            if resource["type"] == "AWS::ECS::Service":
                costs = get_ecs_pricing(resource.get("properties", {}), region, overrides)
            else:
                costs = get_aws_pricing(resource, region)
            
            resource_estimate = {
                "name": resource["name"],
                "type": resource["type"],
                "service": get_service_name(resource["type"]),
                "monthly_cost": costs["monthly_cost"],
                "pricing_details": costs["pricing_details"],
                "assumptions": costs["assumptions"]
            }
            
            resource_estimates.append(resource_estimate)
            total_costs["low"] += costs["monthly_cost"]["low"]
            total_costs["medium"] += costs["monthly_cost"]["medium"]
            total_costs["high"] += costs["monthly_cost"]["high"]
            
        except Exception as e:
            resource_estimate = {
                "name": resource["name"],
                "type": resource["type"],
                "service": get_service_name(resource["type"]),
                "monthly_cost": {"low": 0, "medium": 0, "high": 0},
                "pricing_details": {"source": "error", "error": str(e)},
                "assumptions": [f"Pricing API error: {str(e)}"]
            }
            resource_estimates.append(resource_estimate)
    
    return {
        "resources": resource_estimates,
        "total_monthly_cost": total_costs,
        "unpriced_resources": unpriced_resources,
        "summary": {
            "total_resources": len(bom),
            "unpriced_resources": len(unpriced_resources),
            "coverage": f"{len(bom)}/{len(bom) + len(unpriced_resources)} resources priced",
            "region": region
        },
        "methodology": [
            "Estimates based on AWS Pricing API for On-Demand pricing",
            f"Pricing data retrieved for {region} region",
            "Low usage: 25% utilization for compute, minimal storage/requests",
            "Medium usage: 75% utilization for compute, moderate storage/requests", 
            "High usage: 100% utilization for compute, high storage/requests",
            "Costs exclude data transfer, support plans, and reserved instance discounts"
        ]
    }

def get_service_name(resource_type: str) -> str:
    """Extract AWS service name from resource type"""
    return resource_type.split("::")[1] if "::" in resource_type else "Unknown"

def get_location_name(region: str) -> str:
    """Convert AWS region to location name for Pricing API"""
    region_map = {
        'us-east-1': 'US East (N. Virginia)',
        'us-east-2': 'US East (Ohio)', 
        'us-west-1': 'US West (N. California)',
        'us-west-2': 'US West (Oregon)',
        'eu-west-1': 'Europe (Ireland)',
        'eu-central-1': 'Europe (Frankfurt)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)'
    }
    return region_map.get(region, region)

def get_aws_pricing(resource: Dict, region: str) -> Dict:
    """Get actual AWS pricing using Pricing API"""
    resource_type = resource["type"]
    properties = resource.get("properties", {})
    
    if resource_type == "AWS::EC2::Instance":
        return get_ec2_pricing(properties, region)
    elif resource_type == "AWS::RDS::DBInstance":
        return get_rds_pricing(properties, region)
    elif resource_type == "AWS::Lambda::Function":
        return get_lambda_pricing(properties, region)
    elif resource_type == "AWS::S3::Bucket":
        return get_s3_pricing(properties, region)
    elif resource_type == "AWS::ElasticLoadBalancingV2::LoadBalancer":
        return get_alb_pricing(properties, region)
    elif resource_type == "AWS::ECS::Service":
        return get_ecs_pricing(properties, region)
    elif resource_type == "AWS::DynamoDB::Table":
        return get_dynamodb_pricing(properties, region)
    elif resource_type == "AWS::EC2::Volume":
        return get_ebs_pricing(properties, region)
    elif resource_type == "AWS::AutoScaling::AutoScalingGroup":
        return get_asg_pricing(properties, region)
    elif resource_type == "AWS::EC2::NatGateway":
        return get_nat_gateway_pricing(properties, region)
    elif resource_type == "AWS::EKS::Cluster":
        return get_eks_pricing(properties, region)
    elif resource_type == "AWS::ElastiCache::ReplicationGroup":
        return get_elasticache_pricing(properties, region)
    elif resource_type == "AWS::Redshift::Cluster":
        return get_redshift_pricing(properties, region)
    elif resource_type == "AWS::Neptune::DBCluster":
        return get_neptune_pricing(properties, region)
    elif resource_type == "AWS::DocDB::DBCluster":
        return get_docdb_pricing(properties, region)
    elif resource_type == "AWS::EFS::FileSystem":
        return get_efs_pricing(properties, region)
    elif resource_type == "AWS::FSx::WindowsFileSystem":
        return get_fsx_pricing(properties, region)
    elif resource_type == "AWS::Backup::BackupVault":
        return get_backup_pricing(properties, region)
    elif resource_type == "AWS::ElasticLoadBalancing::LoadBalancer":
        return get_classic_elb_pricing(properties, region)
    elif resource_type == "AWS::EC2::VPCEndpoint":
        return get_vpc_endpoint_pricing(properties, region)
    elif resource_type == "AWS::Route53::HostedZone":
        return get_route53_pricing(properties, region)
    elif resource_type == "AWS::CloudFront::Distribution":
        return get_cloudfront_pricing(properties, region)
    elif resource_type == "AWS::GlobalAccelerator::Accelerator":
        return get_global_accelerator_pricing(properties, region)
    elif resource_type == "AWS::DirectConnect::Connection":
        return get_directconnect_pricing(properties, region)
    elif resource_type == "AWS::ApiGateway::RestApi":
        return get_apigateway_pricing(properties, region)
    elif resource_type == "AWS::StepFunctions::StateMachine":
        return get_stepfunctions_pricing(properties, region)
    elif resource_type == "AWS::Events::CustomEventBus":
        return get_eventbridge_pricing(properties, region)
    elif resource_type == "AWS::Kinesis::Stream":
        return get_kinesis_pricing(properties, region)
    elif resource_type == "AWS::KinesisFirehose::DeliveryStream":
        return get_firehose_pricing(properties, region)
    elif resource_type == "AWS::Glue::Job":
        return get_glue_pricing(properties, region)
    elif resource_type == "AWS::MSK::Cluster":
        return get_msk_pricing(properties, region)
    elif resource_type == "AWS::Elasticsearch::Domain":
        return get_elasticsearch_pricing(properties, region)
    elif resource_type == "AWS::KinesisAnalytics::Application":
        return get_kinesisanalytics_pricing(properties, region)
    elif resource_type == "AWS::MWAA::Environment":
        return get_mwaa_pricing(properties, region)
    elif resource_type == "AWS::Grafana::Workspace":
        return get_grafana_pricing(properties, region)
    elif resource_type == "AWS::KMS::Key":
        return get_kms_pricing(properties, region)
    elif resource_type == "AWS::SecretsManager::Secret":
        return get_secretsmanager_pricing(properties, region)
    elif resource_type == "AWS::WAFv2::WebACL":
        return get_wafv2_pricing(properties, region)
    elif resource_type == "AWS::NetworkFirewall::Firewall":
        return get_networkfirewall_pricing(properties, region)
    elif resource_type == "AWS::CertificateManager::Certificate":
        return get_acm_pricing(properties, region)
    elif resource_type == "AWS::ACMPCA::CertificateAuthority":
        return get_acmpca_pricing(properties, region)
    elif resource_type == "AWS::CloudWatch::LogGroup":
        return get_cloudwatch_logs_pricing(properties, region)
    elif resource_type == "AWS::CloudTrail::Trail":
        return get_cloudtrail_pricing(properties, region)
    elif resource_type == "AWS::Config::ConfigRule":
        return get_config_pricing(properties, region)
    elif resource_type == "AWS::SSM::Parameter":
        return get_ssm_pricing(properties, region)
    else:
        # Return error for unsupported services
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": "Service not yet supported by pricing API"},
            "assumptions": ["This service is not yet supported by the pricing calculator"]
        }

def get_ec2_pricing(properties: Dict, region: str) -> Dict:
    """Get EC2 instance pricing from AWS Pricing API"""
    instance_type = properties.get("InstanceType", "t3.micro")
    
    try:
        # Simplified filters - get On-Demand Linux instance pricing
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': f'BoxUsage:{instance_type}'}
            ],
            MaxResults=1
        )
        
        if response['PriceList'] and len(response['PriceList']) > 0:
            price_data = json.loads(response['PriceList'][0])
            
            # Navigate to OnDemand pricing
            on_demand_terms = price_data['terms']['OnDemand']
            if on_demand_terms:
                # Get first term
                first_term_key = list(on_demand_terms.keys())[0]
                first_term = on_demand_terms[first_term_key]
                
                # Get price dimensions
                price_dimensions = first_term['priceDimensions']
                if price_dimensions:
                    # Get first price dimension
                    first_dim_key = list(price_dimensions.keys())[0]
                    first_dimension = price_dimensions[first_dim_key]
                    
                    # Extract hourly price
                    hourly_price = float(first_dimension['pricePerUnit']['USD'])
                    
                    # Calculate monthly costs
                    monthly_hours_low = 24 * 30 * 0.25
                    monthly_hours_medium = 24 * 30 * 0.75
                    monthly_hours_high = 24 * 30
                    
                    return {
                        "monthly_cost": {
                            "low": round(hourly_price * monthly_hours_low, 2),
                            "medium": round(hourly_price * monthly_hours_medium, 2),
                            "high": round(hourly_price * monthly_hours_high, 2)
                        },
                        "pricing_details": {
                            "source": "AWS Pricing API",
                            "hourly_rate": hourly_price,
                            "instance_type": instance_type,
                            "region": region
                        },
                        "assumptions": [
                            f"Low: {instance_type} running 25% of the time (6 hours/day)",
                            f"Medium: {instance_type} running 75% of the time (18 hours/day)",
                            f"High: {instance_type} running 100% of the time (24/7)",
                            "Pricing from AWS Pricing API for Linux On-Demand instances"
                        ]
                    }
        
        # If we get here, API call succeeded but no data found
        raise Exception("No pricing data found in API response")
        
    except Exception as e:
        print(f"DEBUG: EC2 pricing API error: {e}")
        # Return error instead of fallback
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"AWS Pricing API error: {str(e)}"]
        }

def get_rds_pricing(properties: Dict, region: str) -> Dict:
    """Get RDS pricing from AWS Pricing API"""
    instance_class = properties.get("DBInstanceClass", "db.t3.micro")
    engine = properties.get("Engine", "postgres")
    
    try:
        # Map engine names to API values
        engine_map = {
            "postgres": "PostgreSQL",
            "mysql": "MySQL", 
            "mariadb": "MariaDB",
            "oracle-ee": "Oracle",
            "sqlserver-ex": "SQL Server"
        }
        api_engine = engine_map.get(engine, "PostgreSQL")
        
        response = pricing_client.get_products(
            ServiceCode='AmazonRDS',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_class},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': api_engine},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'}
            ],
            MaxResults=1
        )
        
        if response['PriceList'] and len(response['PriceList']) > 0:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            
            if on_demand_terms:
                first_term = list(on_demand_terms.values())[0]
                price_dimensions = first_term['priceDimensions']
                first_dimension = list(price_dimensions.values())[0]
                hourly_price = float(first_dimension['pricePerUnit']['USD'])
                
                return {
                    "monthly_cost": {
                        "low": round(hourly_price * 24 * 30 * 0.5, 2),
                        "medium": round(hourly_price * 24 * 30 * 0.8, 2),
                        "high": round(hourly_price * 24 * 30, 2)
                    },
                    "pricing_details": {
                        "source": "AWS Pricing API",
                        "hourly_rate": hourly_price,
                        "instance_class": instance_class,
                        "engine": engine
                    },
                    "assumptions": [
                        f"Low: {instance_class} running 50% of the time",
                        f"Medium: {instance_class} running 80% of the time", 
                        f"High: {instance_class} running 24/7"
                    ]
                }
        
        raise Exception("No RDS pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"RDS Pricing API error: {str(e)}"]
        }

def get_lambda_pricing(properties: Dict, region: str) -> Dict:
    """Get Lambda pricing from AWS Pricing API"""
    memory_mb = properties.get("MemorySize", 128)
    
    try:
        gb_second_rate = None
        request_rate = None
        
        # Get Lambda GB-Second pricing
        gb_response = pricing_client.get_products(
            ServiceCode='AWSLambda',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Lambda-GB-Second'}
            ],
            MaxResults=1
        )
        
        if gb_response['PriceList']:
            price_data = json.loads(gb_response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            # Get the first tier pricing (0-6B GB-seconds)
            for dimension in price_dimensions.values():
                if dimension.get('beginRange') == '0':
                    gb_second_rate = float(dimension['pricePerUnit']['USD'])
                    break
        
        # Get Lambda Request pricing
        req_response = pricing_client.get_products(
            ServiceCode='AWSLambda',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'Request'}
            ],
            MaxResults=1
        )
        
        if req_response['PriceList']:
            price_data = json.loads(req_response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            request_rate = float(first_dimension['pricePerUnit']['USD'])
        
        if gb_second_rate is not None and request_rate is not None:
            # Calculate costs based on usage patterns
            gb_memory = memory_mb / 1024
            
            # Usage scenarios with free tier consideration
            scenarios = [
                {"requests": 10000, "duration_s": 1},    # Low
                {"requests": 100000, "duration_s": 1},   # Medium  
                {"requests": 1000000, "duration_s": 1}   # High
            ]
            
            costs = []
            for scenario in scenarios:
                gb_seconds = scenario["requests"] * scenario["duration_s"] * gb_memory
                
                # Apply free tier (1M requests and 400,000 GB-seconds per month)
                billable_requests = max(0, scenario["requests"] - 1000000)
                billable_gb_seconds = max(0, gb_seconds - 400000)
                
                compute_cost = billable_gb_seconds * gb_second_rate
                request_cost = billable_requests * request_rate
                total_cost = compute_cost + request_cost
                costs.append(round(total_cost, 2))
            
            return {
                "monthly_cost": {"low": costs[0], "medium": costs[1], "high": costs[2]},
                "pricing_details": {
                    "source": "AWS Pricing API",
                    "gb_second_rate": gb_second_rate,
                    "request_rate": request_rate,
                    "memory_mb": memory_mb
                },
                "assumptions": [
                    f"Low: 10K requests/month, {memory_mb}MB, 1s duration (free tier applied)",
                    f"Medium: 100K requests/month, {memory_mb}MB, 1s duration (free tier applied)", 
                    f"High: 1M requests/month, {memory_mb}MB, 1s duration (free tier applied)"
                ]
            }
        
        raise Exception("No Lambda pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Lambda Pricing API error: {str(e)}"]
        }
    
    return {
        "monthly_cost": {
            "low": round(calculate_lambda_cost(low_requests, avg_duration_ms), 2),
            "medium": round(calculate_lambda_cost(medium_requests, avg_duration_ms), 2),
            "high": round(calculate_lambda_cost(high_requests, avg_duration_ms), 2)
        },
        "pricing_details": {
            "source": "AWS Pricing Calculator",
            "memory_mb": memory_mb,
            "pricing_model": "GB-second + requests"
        },
        "assumptions": [
            f"Low: 10K requests/month, {memory_mb}MB, 1s duration",
            f"Medium: 100K requests/month, {memory_mb}MB, 1s duration",
            f"High: 1M requests/month, {memory_mb}MB, 1s duration"
        ]
    }

def get_s3_pricing(properties: Dict, region: str) -> Dict:
    """Get S3 pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonS3',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': 'General Purpose'}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            gb_monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            # Storage scenarios
            storage_scenarios = [100, 1000, 10000]  # GB
            costs = [gb_monthly_rate * gb for gb in storage_scenarios]
            
            return {
                "monthly_cost": {
                    "low": round(costs[0], 2),
                    "medium": round(costs[1], 2),
                    "high": round(costs[2], 2)
                },
                "pricing_details": {
                    "source": "AWS Pricing API",
                    "gb_monthly_rate": gb_monthly_rate,
                    "storage_class": "Standard"
                },
                "assumptions": [
                    "Low: 100GB storage",
                    "Medium: 1TB storage", 
                    "High: 10TB storage"
                ]
            }
        
        raise Exception("No S3 pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"S3 Pricing API error: {str(e)}"]
        }
    
    return {
        "monthly_cost": {
            "low": round(storage_gb_low * price_per_gb, 2),
            "medium": round(storage_gb_medium * price_per_gb, 2),
            "high": round(storage_gb_high * price_per_gb, 2)
        },
        "pricing_details": {
            "source": "AWS Pricing Calculator",
            "storage_class": "Standard",
            "price_per_gb": price_per_gb
        },
        "assumptions": [
            f"Low: {storage_gb_low}GB Standard storage",
            f"Medium: {storage_gb_medium}GB Standard storage",
            f"High: {storage_gb_high}GB Standard storage"
        ]
    }

def get_alb_pricing(properties: Dict, region: str) -> Dict:
    """Get ALB pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSELB',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Load Balancer-Application'}
            ],
            MaxResults=5
        )
        
        if response['PriceList']:
            base_hourly_rate = None
            lcu_hourly_rate = None
            
            # Parse pricing for base hours and LCU hours
            for price_item in response['PriceList']:
                price_data = json.loads(price_item)
                product = price_data.get('product', {})
                attributes = product.get('attributes', {})
                
                on_demand_terms = price_data['terms']['OnDemand']
                first_term = list(on_demand_terms.values())[0]
                price_dimensions = first_term['priceDimensions']
                first_dimension = list(price_dimensions.values())[0]
                
                unit = first_dimension.get('unit', '')
                rate = float(first_dimension['pricePerUnit']['USD'])
                usage_type = attributes.get('usagetype', '')
                
                if unit == 'Hrs' and usage_type == 'LoadBalancerUsage':
                    base_hourly_rate = rate
                elif unit == 'LCU-Hr':
                    lcu_hourly_rate = rate
            
            # If we only have base rate, estimate LCU rate
            if base_hourly_rate is not None:
                if lcu_hourly_rate is None:
                    lcu_hourly_rate = 0.008  # Standard ALB LCU rate
                
                hours_per_month = 24 * 30
                
                # LCU usage scenarios
                lcu_scenarios = [1, 3, 10]  # Low, Medium, High LCU usage
                
                costs = []
                for lcu_count in lcu_scenarios:
                    monthly_cost = (base_hourly_rate + lcu_hourly_rate * lcu_count) * hours_per_month
                    costs.append(round(monthly_cost, 2))
                
                return {
                    "monthly_cost": {"low": costs[0], "medium": costs[1], "high": costs[2]},
                    "pricing_details": {
                        "source": "AWS Pricing API",
                        "base_hourly_rate": base_hourly_rate,
                        "lcu_hourly_rate": lcu_hourly_rate
                    },
                    "assumptions": [
                        "Low: 1 LCU usage",
                        "Medium: 3 LCU usage", 
                        "High: 10 LCU usage"
                    ]
                }
        
        raise Exception("No ALB pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"ALB Pricing API error: {str(e)}"]
        }

def get_ecs_pricing(properties: Dict, region: str, overrides: Dict = None) -> Dict:
    """Get ECS Fargate pricing with optional overrides"""
    desired_count = properties.get("DesiredCount", 1)
    
    # Use overrides if provided, otherwise use defaults
    if overrides and 'ecs' in overrides:
        vcpu_high = overrides['ecs'].get('vcpu', 2)
        memory_gb_high = overrides['ecs'].get('memory_gb', 4)
    else:
        vcpu_high = 2
        memory_gb_high = 4
    
    # Get Fargate pricing from AWS Pricing API - use working approach
    try:
        # Use the same approach as other working services
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=50
        )
        
        vcpu_hourly_rate = None
        memory_hourly_rate = None
        
        if response['PriceList']:
            # Look for Fargate pricing in EC2 service
            for price_item in response['PriceList']:
                price_data = json.loads(price_item)
                product = price_data.get('product', {})
                attributes = product.get('attributes', {})
                
                usage_type = attributes.get('usagetype', '')
                
                # Look for Fargate usage types
                if 'Fargate-vCPU' in usage_type:
                    on_demand_terms = price_data['terms']['OnDemand']
                    first_term = list(on_demand_terms.values())[0]
                    price_dimensions = first_term['priceDimensions']
                    first_dimension = list(price_dimensions.values())[0]
                    vcpu_hourly_rate = float(first_dimension['pricePerUnit']['USD'])
                
                elif 'Fargate-GB' in usage_type:
                    on_demand_terms = price_data['terms']['OnDemand']
                    first_term = list(on_demand_terms.values())[0]
                    price_dimensions = first_term['priceDimensions']
                    first_dimension = list(price_dimensions.values())[0]
                    memory_hourly_rate = float(first_dimension['pricePerUnit']['USD'])
                
                # Break if we found both rates
                if vcpu_hourly_rate is not None and memory_hourly_rate is not None:
                    break
        
        if vcpu_hourly_rate is None or memory_hourly_rate is None:
            raise Exception("No ECS Fargate pricing data found in AWS Pricing API")
            
        def calculate_fargate_cost(vcpu, memory_gb, count, utilization=1.0):
            vcpu_cost = vcpu * vcpu_hourly_rate * 24 * 30 * utilization
            memory_cost = memory_gb * memory_hourly_rate * 24 * 30 * utilization
            return (vcpu_cost + memory_cost) * count
            
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"ECS Pricing API error: {str(e)}"]
        }
    
    # Scale for different usage patterns
    vcpu_low = vcpu_high * 0.25
    memory_gb_low = memory_gb_high * 0.25
    vcpu_medium = vcpu_high * 0.5
    memory_gb_medium = memory_gb_high * 0.5
    
    return {
        "monthly_cost": {
            "low": round(calculate_fargate_cost(vcpu_low, memory_gb_low, desired_count, 0.5), 2),
            "medium": round(calculate_fargate_cost(vcpu_medium, memory_gb_medium, desired_count, 0.8), 2),
            "high": round(calculate_fargate_cost(vcpu_high, memory_gb_high, desired_count, 1.0), 2)
        },
        "pricing_details": {
            "source": "AWS Pricing Calculator",
            "desired_count": desired_count,
            "pricing_model": "Fargate vCPU + memory",
            "vcpu_high": vcpu_high,
            "memory_gb_high": memory_gb_high
        },
        "assumptions": [
            f"Low: {desired_count}x ({vcpu_low} vCPU, {memory_gb_low}GB) 50% utilization",
            f"Medium: {desired_count}x ({vcpu_medium} vCPU, {memory_gb_medium}GB) 80% utilization", 
            f"High: {desired_count}x ({vcpu_high} vCPU, {memory_gb_high}GB) 100% utilization"
        ]
    }

def get_dynamodb_pricing(properties: Dict, region: str) -> Dict:
    """Get DynamoDB pricing from AWS Pricing API"""
    try:
        # Try multiple approaches for DynamoDB pricing
        response = pricing_client.get_products(
            ServiceCode='AmazonDynamoDB',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'TimedStorage-ByteHrs'}
            ],
            MaxResults=5
        )
        
        if not response['PriceList']:
            # Try with different usage type
            response = pricing_client.get_products(
                ServiceCode='AmazonDynamoDB',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                    {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'Storage'}
                ],
                MaxResults=5
            )
        
        if not response['PriceList']:
            # Try without specific filters
            response = pricing_client.get_products(
                ServiceCode='AmazonDynamoDB',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
                ],
                MaxResults=20
            )
        
        if response['PriceList']:
            storage_rate = None
            
            # Parse pricing for storage
            for price_item in response['PriceList']:
                price_data = json.loads(price_item)
                product = price_data.get('product', {})
                attributes = product.get('attributes', {})
                
                # Look for storage pricing
                usage_type = attributes.get('usagetype', '')
                if 'Storage' in usage_type or 'ByteHrs' in usage_type:
                    on_demand_terms = price_data['terms']['OnDemand']
                    first_term = list(on_demand_terms.values())[0]
                    price_dimensions = first_term['priceDimensions']
                    first_dimension = list(price_dimensions.values())[0]
                    
                    unit = first_dimension.get('unit', '')
                    rate = float(first_dimension['pricePerUnit']['USD'])
                    
                    # Convert ByteHrs to GB-Month if needed
                    if 'ByteHrs' in unit:
                        # Convert from ByteHrs to GB-Month (1 GB-Month = 1073741824 ByteHrs)
                        storage_rate = rate * 1073741824 / (24 * 30)
                    elif 'GB' in unit:
                        storage_rate = rate
                    
                    if storage_rate:
                        break
            
            if storage_rate is not None:
                # Usage scenarios
                storage_scenarios = [1, 10, 100]  # GB
                
                costs = []
                for storage_gb in storage_scenarios:
                    storage_cost = storage_gb * storage_rate
                    costs.append(round(storage_cost, 2))
                
                return {
                    "monthly_cost": {"low": costs[0], "medium": costs[1], "high": costs[2]},
                    "pricing_details": {
                        "source": "AWS Pricing API",
                        "storage_rate": storage_rate
                    },
                    "assumptions": [
                        "Low: 1GB storage",
                        "Medium: 10GB storage", 
                        "High: 100GB storage"
                    ]
                }
        
        raise Exception("No DynamoDB pricing data found in AWS Pricing API")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"DynamoDB Pricing API error: {str(e)}"]
        }
    
    return {
        "monthly_cost": {
            "low": round(calculate_dynamodb_cost(storage_gb_low, read_requests_low, write_requests_low), 2),
            "medium": round(calculate_dynamodb_cost(storage_gb_medium, read_requests_medium, write_requests_medium), 2),
            "high": round(calculate_dynamodb_cost(storage_gb_high, read_requests_high, write_requests_high), 2)
        },
        "pricing_details": {
            "source": "AWS Pricing Calculator",
            "pricing_model": "On-Demand"
        },
        "assumptions": [
            f"Low: {storage_gb_low}GB storage, 100K reads, 10K writes",
            f"Medium: {storage_gb_medium}GB storage, 1M reads, 100K writes",
            f"High: {storage_gb_high}GB storage, 10M reads, 1M writes"
        ]
    }
    """Convert AWS region to location name used in Pricing API"""
    region_map = {
        "us-east-1": "US East (N. Virginia)",
        "us-west-2": "US West (Oregon)",
        "eu-west-1": "Europe (Ireland)",
        "ap-southeast-1": "Asia Pacific (Singapore)"
    }
    return region_map.get(region, "US East (N. Virginia)")

def get_fallback_pricing(resource_type: str) -> Dict:
    """Fallback pricing when AWS Pricing API is unavailable"""
    
    # Conservative estimates based on typical AWS costs
    pricing_map = {
        "AWS::EC2::Instance": {"low": 7.50, "medium": 37.50, "high": 150.00},
        "AWS::RDS::DBInstance": {"low": 15.00, "medium": 75.00, "high": 300.00},
        "AWS::S3::Bucket": {"low": 2.30, "medium": 23.00, "high": 230.00},
        "AWS::Lambda::Function": {"low": 0.20, "medium": 20.00, "high": 200.00},
        "AWS::DynamoDB::Table": {"low": 1.25, "medium": 25.00, "high": 250.00},
        "AWS::ElasticLoadBalancingV2::LoadBalancer": {"low": 16.20, "medium": 32.40, "high": 64.80},
    }
    
    costs = pricing_map.get(resource_type, {"low": 5.00, "medium": 25.00, "high": 100.00})
    
    return {
        "monthly_cost": costs,
        "pricing_details": {"source": "fallback_estimates"},
        "assumptions": [
            "Low: Minimal development/testing usage",
            "Medium: Standard production usage", 
            "High: High-traffic production usage",
            "Fallback estimates used - AWS Pricing API unavailable"
        ]
    }
def get_ebs_pricing(properties: Dict, region: str) -> Dict:
    """Get EBS volume pricing from AWS Pricing API"""
    volume_type = properties.get("VolumeType", "gp3")
    size = properties.get("Size", 20)
    
    try:
        # Map volume types to AWS Pricing API values
        volume_type_map = {
            "gp3": "General Purpose-GP3", "gp2": "General Purpose",
            "io1": "Provisioned IOPS", "io2": "Provisioned IOPS-io2",
            "st1": "Throughput Optimized HDD", "sc1": "Cold HDD"
        }
        
        api_volume_type = volume_type_map.get(volume_type, "General Purpose-GP3")
        
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'volumeApiName', 'Value': volume_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if not response['PriceList']:
            # Try alternative filter
            response = pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                    {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': f'EBS:VolumeUsage.{volume_type}'}
                ],
                MaxResults=1
            )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            gb_monthly_price = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = gb_monthly_price * size
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "gb_monthly_rate": gb_monthly_price, "volume_type": volume_type, "size_gb": size},
                "assumptions": [f"{volume_type} volume, {size}GB, pricing from AWS API"]
            }
        
        # Use standard EBS pricing as fallback
        pricing_map = {"gp3": 0.08, "gp2": 0.10, "io1": 0.125, "io2": 0.125, "st1": 0.045, "sc1": 0.015}
        gb_rate = pricing_map.get(volume_type, 0.08)
        monthly_cost = gb_rate * size
        
        return {
            "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
            "pricing_details": {"source": "Standard pricing", "gb_monthly_rate": gb_rate, "volume_type": volume_type, "size_gb": size},
            "assumptions": [f"{volume_type} volume, {size}GB, standard AWS pricing"]
        }
        
    except Exception as e:
        # Use standard EBS pricing as fallback
        pricing_map = {"gp3": 0.08, "gp2": 0.10, "io1": 0.125, "io2": 0.125, "st1": 0.045, "sc1": 0.015}
        gb_rate = pricing_map.get(volume_type, 0.08)
        monthly_cost = gb_rate * size
        
        return {
            "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
            "pricing_details": {"source": "Standard pricing", "gb_monthly_rate": gb_rate, "volume_type": volume_type, "size_gb": size},
            "assumptions": [f"{volume_type} volume, {size}GB, standard AWS pricing"]
        }

def get_nat_gateway_pricing(properties: Dict, region: str) -> Dict:
    """Get NAT Gateway pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'NAT Gateway'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if not response['PriceList']:
            # Try alternative filter
            response = pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                    {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'NatGateway-Hours'}
                ],
                MaxResults=1
            )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            
            hourly_rate = None
            for dimension in price_dimensions.values():
                if 'hour' in dimension['unit'].lower():
                    hourly_rate = float(dimension['pricePerUnit']['USD'])
                    break
            
            if hourly_rate:
                monthly_cost = hourly_rate * 24 * 30
                
                return {
                    "monthly_cost": {
                        "low": monthly_cost + 5 * 0.045,    # +5GB data processing
                        "medium": monthly_cost + 50 * 0.045,  # +50GB data processing  
                        "high": monthly_cost + 500 * 0.045    # +500GB data processing
                    },
                    "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate},
                    "assumptions": ["Low: 5GB/month data", "Medium: 50GB/month", "High: 500GB/month"]
                }
        
        # Use standard NAT Gateway pricing
        hourly_rate = 0.045  # Standard NAT Gateway pricing
        monthly_cost = hourly_rate * 24 * 30
        
        return {
            "monthly_cost": {
                "low": monthly_cost + 5 * 0.045,
                "medium": monthly_cost + 50 * 0.045,
                "high": monthly_cost + 500 * 0.045
            },
            "pricing_details": {"source": "Standard pricing", "hourly_rate": hourly_rate},
            "assumptions": ["NAT Gateway standard pricing: $0.045/hour + data processing"]
        }
        
    except Exception as e:
        # Use standard NAT Gateway pricing
        hourly_rate = 0.045
        monthly_cost = hourly_rate * 24 * 30
        
        return {
            "monthly_cost": {
                "low": monthly_cost + 2.25,
                "medium": monthly_cost + 22.5,
                "high": monthly_cost + 225
            },
            "pricing_details": {"source": "Standard pricing", "hourly_rate": hourly_rate},
            "assumptions": ["NAT Gateway standard pricing with data processing estimates"]
        }

def get_eks_pricing(properties: Dict, region: str) -> Dict:
    """Get EKS cluster pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonEKS',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate},
                "assumptions": ["EKS control plane only", "Worker nodes priced separately"]
            }
        
        raise Exception("No EKS pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"EKS Pricing API error: {str(e)}"]
        }

def get_asg_pricing(properties: Dict, region: str) -> Dict:
    """Get Auto Scaling Group pricing (based on EC2 instances)"""
    # Extract instance type from launch template or launch configuration
    instance_type = "t3.micro"  # default
    
    if "LaunchTemplate" in properties:
        lt = properties["LaunchTemplate"]
        if isinstance(lt, dict) and "LaunchTemplateSpecification" in lt:
            instance_type = lt["LaunchTemplateSpecification"].get("InstanceType", "t3.micro")
    elif "LaunchConfigurationName" in properties:
        # Would need to look up launch config, use default for now
        pass
    
    min_size = properties.get("MinSize", 1)
    max_size = properties.get("MaxSize", 3)
    
    # Use EC2 pricing API for underlying instances
    try:
        ec2_cost = get_ec2_pricing({"InstanceType": instance_type}, region)
        
        return {
            "monthly_cost": {
                "low": ec2_cost["monthly_cost"]["low"] * min_size,
                "medium": ec2_cost["monthly_cost"]["medium"] * ((min_size + max_size) // 2),
                "high": ec2_cost["monthly_cost"]["high"] * max_size
            },
            "pricing_details": {"source": "AWS Pricing API (EC2)", "instance_type": instance_type, "min_size": min_size, "max_size": max_size},
            "assumptions": [f"Low: {min_size} instances", f"Medium: {(min_size + max_size) // 2} instances", f"High: {max_size} instances"]
        }
    except Exception as e:
        # Use standard EC2 pricing as fallback
        hourly_rates = {"t3.micro": 0.0104, "t3.small": 0.0208, "t3.medium": 0.0416}
        hourly_rate = hourly_rates.get(instance_type, 0.0104)
        monthly_cost_per_instance = hourly_rate * 24 * 30
        
        return {
            "monthly_cost": {
                "low": monthly_cost_per_instance * min_size,
                "medium": monthly_cost_per_instance * ((min_size + max_size) // 2),
                "high": monthly_cost_per_instance * max_size
            },
            "pricing_details": {"source": "Standard pricing", "instance_type": instance_type, "hourly_rate": hourly_rate},
            "assumptions": [f"ASG with {instance_type} instances, standard pricing"]
        }

def get_elasticache_pricing(properties: Dict, region: str) -> Dict:
    """Get ElastiCache pricing from AWS Pricing API"""
    node_type = properties.get("CacheNodeType", "cache.t3.micro")
    num_nodes = properties.get("NumCacheNodes", 1)
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonElastiCache',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': node_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30 * num_nodes
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate, "node_type": node_type, "num_nodes": num_nodes},
                "assumptions": [f"{num_nodes}x {node_type} nodes, pricing from AWS API"]
            }
        
        raise Exception("No ElastiCache pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"ElastiCache Pricing API error: {str(e)}"]
        }
def get_redshift_pricing(properties: Dict, region: str) -> Dict:
    """Get Redshift cluster pricing from AWS Pricing API"""
    node_type = properties.get("NodeType", "dc2.large")
    num_nodes = properties.get("NumberOfNodes", 1)
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonRedshift',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': node_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30 * num_nodes
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate, "node_type": node_type, "num_nodes": num_nodes},
                "assumptions": [f"{num_nodes}x {node_type} nodes, 24/7 operation"]
            }
        
        raise Exception("No Redshift pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Redshift Pricing API error: {str(e)}"]
        }

def get_neptune_pricing(properties: Dict, region: str) -> Dict:
    """Get Neptune cluster pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonNeptune',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate},
                "assumptions": ["Neptune cluster, 24/7 operation"]
            }
        
        raise Exception("No Neptune pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Neptune Pricing API error: {str(e)}"]
        }

def get_docdb_pricing(properties: Dict, region: str) -> Dict:
    """Get DocumentDB cluster pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonDocDB',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate},
                "assumptions": ["DocumentDB cluster, 24/7 operation"]
            }
        
        raise Exception("No DocumentDB pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"DocumentDB Pricing API error: {str(e)}"]
        }
def get_efs_pricing(properties: Dict, region: str) -> Dict:
    """Get EFS pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonEFS',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': 'General Purpose'}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            gb_monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": gb_monthly_rate * 10,    # 10GB
                    "medium": gb_monthly_rate * 100,  # 100GB
                    "high": gb_monthly_rate * 1000    # 1TB
                },
                "pricing_details": {"source": "AWS Pricing API", "gb_monthly_rate": gb_monthly_rate},
                "assumptions": ["Low: 10GB storage", "Medium: 100GB storage", "High: 1TB storage"]
            }
        
        raise Exception("No EFS pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"EFS Pricing API error: {str(e)}"]
        }

def get_fsx_pricing(properties: Dict, region: str) -> Dict:
    """Get FSx Windows pricing from AWS Pricing API"""
    storage_capacity = properties.get("StorageCapacity", 32)  # GB
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonFSx',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'fileSystemType', 'Value': 'Windows'}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            gb_monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = gb_monthly_rate * storage_capacity
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "gb_monthly_rate": gb_monthly_rate, "storage_capacity": storage_capacity},
                "assumptions": [f"FSx Windows, {storage_capacity}GB storage"]
            }
        
        raise Exception("No FSx pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"FSx Pricing API error: {str(e)}"]
        }

def get_backup_pricing(properties: Dict, region: str) -> Dict:
    """Get AWS Backup pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSBackup',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            gb_monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": gb_monthly_rate * 50,     # 50GB backups
                    "medium": gb_monthly_rate * 500,   # 500GB backups
                    "high": gb_monthly_rate * 5000     # 5TB backups
                },
                "pricing_details": {"source": "AWS Pricing API", "gb_monthly_rate": gb_monthly_rate},
                "assumptions": ["Low: 50GB backups", "Medium: 500GB backups", "High: 5TB backups"]
            }
        
        raise Exception("No Backup pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Backup Pricing API error: {str(e)}"]
        }
def get_classic_elb_pricing(properties: Dict, region: str) -> Dict:
    """Get Classic ELB pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Load Balancer'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate},
                "assumptions": ["Classic ELB, 24/7 operation"]
            }
        
        raise Exception("No Classic ELB pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Classic ELB Pricing API error: {str(e)}"]
        }

def get_vpc_endpoint_pricing(properties: Dict, region: str) -> Dict:
    """Get VPC Endpoint pricing from AWS Pricing API"""
    try:
        # Try different approaches to find VPC Endpoint pricing
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': f'VpcEndpoint-Hours'}
            ],
            MaxResults=1
        )
        
        if not response['PriceList']:
            # Try alternative filter
            response = pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                    {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'VpcEndpoint'}
                ],
                MaxResults=1
            )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate},
                "assumptions": ["VPC Interface Endpoint, 24/7 operation"]
            }
        
        # If no pricing found, use known estimate
        hourly_rate = 0.01  # ~$7.20/month
        monthly_cost = hourly_rate * 24 * 30
        
        return {
            "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
            "pricing_details": {"source": "Standard estimate", "hourly_rate": hourly_rate},
            "assumptions": ["VPC Interface Endpoint standard pricing (~$7.20/month)"]
        }
        
    except Exception as e:
        # Fallback to standard VPC Endpoint pricing
        hourly_rate = 0.01  # $0.01/hour = ~$7.20/month
        monthly_cost = hourly_rate * 24 * 30
        
        return {
            "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
            "pricing_details": {"source": "Standard estimate", "hourly_rate": hourly_rate},
            "assumptions": ["VPC Interface Endpoint standard pricing (~$7.20/month)"]
        }

def get_route53_pricing(properties: Dict, region: str) -> Dict:
    """Get Route53 hosted zone pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonRoute53',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'DNS Zone'}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {"low": monthly_rate, "medium": monthly_rate, "high": monthly_rate},
                "pricing_details": {"source": "AWS Pricing API", "monthly_rate": monthly_rate},
                "assumptions": ["Hosted zone monthly fee, excludes query charges"]
            }
        
        raise Exception("No Route53 pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Route53 Pricing API error: {str(e)}"]
        }

def get_cloudfront_pricing(properties: Dict, region: str) -> Dict:
    """Get CloudFront distribution pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonCloudFront',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Data Transfer'}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            gb_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": gb_rate * 10,      # 10GB transfer
                    "medium": gb_rate * 100,   # 100GB transfer
                    "high": gb_rate * 1000     # 1TB transfer
                },
                "pricing_details": {"source": "AWS Pricing API", "gb_rate": gb_rate},
                "assumptions": ["Low: 10GB transfer", "Medium: 100GB transfer", "High: 1TB transfer"]
            }
        
        raise Exception("No CloudFront pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"CloudFront Pricing API error: {str(e)}"]
        }

def get_global_accelerator_pricing(properties: Dict, region: str) -> Dict:
    """Get Global Accelerator pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSGlobalAccelerator',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate},
                "assumptions": ["Global Accelerator, 24/7 operation"]
            }
        
        raise Exception("No Global Accelerator pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Global Accelerator Pricing API error: {str(e)}"]
        }

def get_directconnect_pricing(properties: Dict, region: str) -> Dict:
    """Get Direct Connect pricing from AWS Pricing API"""
    port_speed = properties.get("Bandwidth", "1Gbps")
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSDirectConnect',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'portSpeed', 'Value': port_speed}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate, "port_speed": port_speed},
                "assumptions": [f"Direct Connect {port_speed}, 24/7 operation"]
            }
        
        raise Exception("No Direct Connect pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Direct Connect Pricing API error: {str(e)}"]
        }
def get_apigateway_pricing(properties: Dict, region: str) -> Dict:
    """Get API Gateway pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonApiGateway',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            per_million_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": per_million_rate * 0.1,    # 100K requests
                    "medium": per_million_rate * 1,    # 1M requests
                    "high": per_million_rate * 10      # 10M requests
                },
                "pricing_details": {"source": "AWS Pricing API", "per_million_rate": per_million_rate},
                "assumptions": ["Low: 100K requests", "Medium: 1M requests", "High: 10M requests"]
            }
        
        raise Exception("No API Gateway pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"API Gateway Pricing API error: {str(e)}"]
        }

def get_stepfunctions_pricing(properties: Dict, region: str) -> Dict:
    """Get Step Functions pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSStepFunctions',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=5
        )
        
        if not response['PriceList']:
            # Try with different service code
            response = pricing_client.get_products(
                ServiceCode='AmazonStates',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
                ],
                MaxResults=5
            )
        
        if response['PriceList']:
            # Parse pricing for state transitions
            for price_item in response['PriceList']:
                price_data = json.loads(price_item)
                
                on_demand_terms = price_data['terms']['OnDemand']
                first_term = list(on_demand_terms.values())[0]
                price_dimensions = first_term['priceDimensions']
                first_dimension = list(price_dimensions.values())[0]
                
                unit = first_dimension.get('unit', '')
                rate = float(first_dimension['pricePerUnit']['USD'])
                
                if 'Request' in unit or 'Transition' in unit:
                    # Usage scenarios
                    transition_scenarios = [10000, 100000, 1000000]  # transitions
                    
                    costs = []
                    for transitions in transition_scenarios:
                        cost = transitions * rate
                        costs.append(round(cost, 2))
                    
                    return {
                        "monthly_cost": {"low": costs[0], "medium": costs[1], "high": costs[2]},
                        "pricing_details": {"source": "AWS Pricing API", "per_transition_rate": rate},
                        "assumptions": ["Low: 10K transitions", "Medium: 100K transitions", "High: 1M transitions"]
                    }
        
        raise Exception("No Step Functions pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Step Functions Pricing API error: {str(e)}"]
        }

def get_eventbridge_pricing(properties: Dict, region: str) -> Dict:
    """Get EventBridge pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonEventBridge',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            per_million_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": per_million_rate * 0.1,    # 100K events
                    "medium": per_million_rate * 1,    # 1M events
                    "high": per_million_rate * 10      # 10M events
                },
                "pricing_details": {"source": "AWS Pricing API", "per_million_rate": per_million_rate},
                "assumptions": ["Low: 100K events", "Medium: 1M events", "High: 10M events"]
            }
        
        raise Exception("No EventBridge pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"EventBridge Pricing API error: {str(e)}"]
        }

def get_kinesis_pricing(properties: Dict, region: str) -> Dict:
    """Get Kinesis Stream pricing from AWS Pricing API"""
    shard_count = properties.get("ShardCount", 1)
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonKinesis',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            shard_hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = shard_hourly_rate * 24 * 30 * shard_count
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "shard_hourly_rate": shard_hourly_rate, "shard_count": shard_count},
                "assumptions": [f"{shard_count} shards, 24/7 operation"]
            }
        
        raise Exception("No Kinesis pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Kinesis Pricing API error: {str(e)}"]
        }

def get_firehose_pricing(properties: Dict, region: str) -> Dict:
    """Get Kinesis Firehose pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonKinesisFirehose',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            gb_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": gb_rate * 10,      # 10GB
                    "medium": gb_rate * 100,   # 100GB
                    "high": gb_rate * 1000     # 1TB
                },
                "pricing_details": {"source": "AWS Pricing API", "gb_rate": gb_rate},
                "assumptions": ["Low: 10GB ingested", "Medium: 100GB ingested", "High: 1TB ingested"]
            }
        
        raise Exception("No Firehose pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Firehose Pricing API error: {str(e)}"]
        }

def get_glue_pricing(properties: Dict, region: str) -> Dict:
    """Get Glue Job pricing from AWS Pricing API"""
    try:
        # Get standard ETL job pricing
        response = pricing_client.get_products(
            ServiceCode='AWSGlue',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'Jobrun'},
                {'Type': 'TERM_MATCH', 'Field': 'group', 'Value': 'ETL Job run'}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            dpu_hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": round(dpu_hourly_rate * 10, 2),      # 10 DPU-hours
                    "medium": round(dpu_hourly_rate * 100, 2),   # 100 DPU-hours
                    "high": round(dpu_hourly_rate * 1000, 2)     # 1000 DPU-hours
                },
                "pricing_details": {"source": "AWS Pricing API", "dpu_hourly_rate": dpu_hourly_rate},
                "assumptions": ["Low: 10 DPU-hours", "Medium: 100 DPU-hours", "High: 1000 DPU-hours"]
            }
        
        raise Exception("No Glue pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Glue Pricing API error: {str(e)}"]
        }
def get_msk_pricing(properties: Dict, region: str) -> Dict:
    """Get MSK cluster pricing from AWS Pricing API"""
    instance_type = properties.get("BrokerNodeGroupInfo", {}).get("InstanceType", "kafka.m5.large")
    num_brokers = properties.get("NumberOfBrokerNodes", 3)
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonMSK',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30 * num_brokers
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate, "instance_type": instance_type, "num_brokers": num_brokers},
                "assumptions": [f"{num_brokers}x {instance_type} brokers, 24/7 operation"]
            }
        
        raise Exception("No MSK pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"MSK Pricing API error: {str(e)}"]
        }

def get_elasticsearch_pricing(properties: Dict, region: str) -> Dict:
    """Get Elasticsearch domain pricing from AWS Pricing API"""
    instance_type = properties.get("ElasticsearchClusterConfig", {}).get("InstanceType", "t3.small.elasticsearch")
    instance_count = properties.get("ElasticsearchClusterConfig", {}).get("InstanceCount", 1)
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonES',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30 * instance_count
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate, "instance_type": instance_type, "instance_count": instance_count},
                "assumptions": [f"{instance_count}x {instance_type} instances, 24/7 operation"]
            }
        
        raise Exception("No Elasticsearch pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Elasticsearch Pricing API error: {str(e)}"]
        }

def get_kinesisanalytics_pricing(properties: Dict, region: str) -> Dict:
    """Get Kinesis Analytics pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonKinesisAnalytics',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            kpu_hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": kpu_hourly_rate * 24 * 30 * 1,    # 1 KPU
                    "medium": kpu_hourly_rate * 24 * 30 * 2,  # 2 KPUs
                    "high": kpu_hourly_rate * 24 * 30 * 4     # 4 KPUs
                },
                "pricing_details": {"source": "AWS Pricing API", "kpu_hourly_rate": kpu_hourly_rate},
                "assumptions": ["Low: 1 KPU", "Medium: 2 KPUs", "High: 4 KPUs"]
            }
        
        raise Exception("No Kinesis Analytics pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Kinesis Analytics Pricing API error: {str(e)}"]
        }

def get_mwaa_pricing(properties: Dict, region: str) -> Dict:
    """Get MWAA environment pricing from AWS Pricing API"""
    environment_class = properties.get("EnvironmentClass", "mw1.small")
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonMWAA',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'environmentClass', 'Value': environment_class}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate, "environment_class": environment_class},
                "assumptions": [f"MWAA {environment_class}, 24/7 operation"]
            }
        
        raise Exception("No MWAA pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"MWAA Pricing API error: {str(e)}"]
        }

def get_grafana_pricing(properties: Dict, region: str) -> Dict:
    """Get Grafana workspace pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonGrafana',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {"low": monthly_rate, "medium": monthly_rate, "high": monthly_rate},
                "pricing_details": {"source": "AWS Pricing API", "monthly_rate": monthly_rate},
                "assumptions": ["Grafana workspace monthly fee"]
            }
        
        raise Exception("No Grafana pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Grafana Pricing API error: {str(e)}"]
        }
def get_kms_pricing(properties: Dict, region: str) -> Dict:
    """Get KMS key pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='awskms',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {"low": monthly_rate, "medium": monthly_rate, "high": monthly_rate},
                "pricing_details": {"source": "AWS Pricing API", "monthly_rate": monthly_rate},
                "assumptions": ["KMS key monthly fee, excludes API requests"]
            }
        
        raise Exception("No KMS pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"KMS Pricing API error: {str(e)}"]
        }

def get_secretsmanager_pricing(properties: Dict, region: str) -> Dict:
    """Get Secrets Manager pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSSecretsManager',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {"low": monthly_rate, "medium": monthly_rate, "high": monthly_rate},
                "pricing_details": {"source": "AWS Pricing API", "monthly_rate": monthly_rate},
                "assumptions": ["Secret monthly fee, excludes API requests"]
            }
        
        raise Exception("No Secrets Manager pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Secrets Manager Pricing API error: {str(e)}"]
        }

def get_wafv2_pricing(properties: Dict, region: str) -> Dict:
    """Get WAFv2 WebACL pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSWAF',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {"low": monthly_rate, "medium": monthly_rate, "high": monthly_rate},
                "pricing_details": {"source": "AWS Pricing API", "monthly_rate": monthly_rate},
                "assumptions": ["WAFv2 WebACL monthly fee, excludes request charges"]
            }
        
        raise Exception("No WAFv2 pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"WAFv2 Pricing API error: {str(e)}"]
        }

def get_networkfirewall_pricing(properties: Dict, region: str) -> Dict:
    """Get Network Firewall pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSNetworkFirewall',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            hourly_rate = float(first_dimension['pricePerUnit']['USD'])
            monthly_cost = hourly_rate * 24 * 30
            
            return {
                "monthly_cost": {"low": monthly_cost, "medium": monthly_cost, "high": monthly_cost},
                "pricing_details": {"source": "AWS Pricing API", "hourly_rate": hourly_rate},
                "assumptions": ["Network Firewall endpoint, 24/7 operation"]
            }
        
        raise Exception("No Network Firewall pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Network Firewall Pricing API error: {str(e)}"]
        }

def get_acm_pricing(properties: Dict, region: str) -> Dict:
    """Get ACM certificate pricing - ACM certificates are free"""
    return {
        "monthly_cost": {"low": 0, "medium": 0, "high": 0},
        "pricing_details": {"source": "AWS Documentation", "monthly_rate": 0},
        "assumptions": ["ACM certificates are free for AWS services"]
    }

def get_acmpca_pricing(properties: Dict, region: str) -> Dict:
    """Get ACM Private CA pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSCertificateManager',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {"low": monthly_rate, "medium": monthly_rate, "high": monthly_rate},
                "pricing_details": {"source": "AWS Pricing API", "monthly_rate": monthly_rate},
                "assumptions": ["Private CA monthly fee, excludes certificate issuance"]
            }
        
        raise Exception("No ACM Private CA pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"ACM Private CA Pricing API error: {str(e)}"]
        }
def get_cloudwatch_logs_pricing(properties: Dict, region: str) -> Dict:
    """Get CloudWatch Logs pricing from AWS Pricing API"""
    try:
        # Get standard log ingestion pricing
        response = pricing_client.get_products(
            ServiceCode='AmazonCloudWatch',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'operation', 'Value': 'PutLogEvents'},
                {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': 'DataProcessing-Bytes'}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            gb_rate = float(first_dimension['pricePerUnit']['USD'])
            
            # Apply free tier (5GB per month)
            scenarios = [1, 10, 100]  # GB per month
            costs = []
            for gb_usage in scenarios:
                billable_gb = max(0, gb_usage - 5)  # 5GB free tier
                cost = billable_gb * gb_rate
                costs.append(round(cost, 2))
            
            return {
                "monthly_cost": {
                    "low": costs[0],       # 1GB logs (free)
                    "medium": costs[1],    # 10GB logs (5GB billable)
                    "high": costs[2]       # 100GB logs (95GB billable)
                },
                "pricing_details": {"source": "AWS Pricing API", "gb_rate": gb_rate},
                "assumptions": [
                    "Low: 1GB logs/month (free tier applied)",
                    "Medium: 10GB logs/month (free tier applied)",
                    "High: 100GB logs/month (free tier applied)"
                ]
            }
        
        raise Exception("No CloudWatch Logs pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"CloudWatch Logs Pricing API error: {str(e)}"]
        }
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"CloudWatch Logs Pricing API error: {str(e)}"]
        }

def get_cloudtrail_pricing(properties: Dict, region: str) -> Dict:
    """Get CloudTrail pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSCloudTrail',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            event_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": event_rate * 100000,     # 100K events
                    "medium": event_rate * 1000000,  # 1M events
                    "high": event_rate * 10000000    # 10M events
                },
                "pricing_details": {"source": "AWS Pricing API", "per_100k_events": event_rate},
                "assumptions": ["Low: 100K events", "Medium: 1M events", "High: 10M events"]
            }
        
        raise Exception("No CloudTrail pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"CloudTrail Pricing API error: {str(e)}"]
        }

def get_config_pricing(properties: Dict, region: str) -> Dict:
    """Get AWS Config pricing from AWS Pricing API"""
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSConfig',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            config_item_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {
                    "low": config_item_rate * 1000,    # 1K config items
                    "medium": config_item_rate * 10000,  # 10K config items
                    "high": config_item_rate * 100000   # 100K config items
                },
                "pricing_details": {"source": "AWS Pricing API", "per_config_item": config_item_rate},
                "assumptions": ["Low: 1K config items", "Medium: 10K config items", "High: 100K config items"]
            }
        
        raise Exception("No Config pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"Config Pricing API error: {str(e)}"]
        }

def get_ssm_pricing(properties: Dict, region: str) -> Dict:
    """Get SSM Parameter pricing from AWS Pricing API"""
    parameter_type = properties.get("Type", "String")
    
    # Standard parameters (String, StringList, SecureString) are free
    if parameter_type in ["String", "StringList", "SecureString"]:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "AWS Documentation", "monthly_rate": 0},
            "assumptions": ["Standard SSM parameters are free"]
        }
    
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonSSM',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_location_name(region)}
            ],
            MaxResults=1
        )
        
        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            on_demand_terms = price_data['terms']['OnDemand']
            first_term = list(on_demand_terms.values())[0]
            price_dimensions = first_term['priceDimensions']
            first_dimension = list(price_dimensions.values())[0]
            
            monthly_rate = float(first_dimension['pricePerUnit']['USD'])
            
            return {
                "monthly_cost": {"low": monthly_rate, "medium": monthly_rate, "high": monthly_rate},
                "pricing_details": {"source": "AWS Pricing API", "monthly_rate": monthly_rate, "parameter_type": parameter_type},
                "assumptions": [f"Advanced SSM parameter ({parameter_type})"]
            }
        
        raise Exception("No SSM pricing data found")
        
    except Exception as e:
        return {
            "monthly_cost": {"low": 0, "medium": 0, "high": 0},
            "pricing_details": {"source": "error", "error": str(e)},
            "assumptions": [f"SSM Pricing API error: {str(e)}"]
        }
