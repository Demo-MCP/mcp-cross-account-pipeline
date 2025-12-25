#!/usr/bin/env python3
"""
Generate comprehensive CloudFormation to Python class mappings
for all 112 auto-generated AWS resources.
"""

import os
import re
from pathlib import Path

def generate_comprehensive_mappings():
    """Generate mappings for all converted resources"""
    
    # Common CloudFormation resource type patterns to Python class mappings
    cfn_to_class_mappings = {}
    
    # Get all Python resource files
    aws_resources_dir = Path("aws_resources")
    resource_files = [f for f in aws_resources_dir.glob("*.py") if f.name != "__init__.py"]
    
    print(f"Found {len(resource_files)} resource files")
    
    # Manual mappings for known CloudFormation types
    known_mappings = {
        # EC2
        "AWS::EC2::Instance": "Instance",
        "AWS::EC2::Volume": "EbsVolume", 
        "AWS::EC2::NatGateway": "NatGateway",
        "AWS::EC2::Host": "Ec2Host",
        "AWS::EC2::ClientVpnEndpoint": "Ec2ClientVpnEndpoint",
        "AWS::EC2::ClientVpnNetworkAssociation": "Ec2ClientVpnNetworkAssociation",
        "AWS::EC2::TransitGatewayVpcAttachment": "Ec2TransitGatewayVpcAttachment",
        "AWS::EC2::TransitGatewayPeeringAttachment": "Ec2TransitGatewayPeeringAttachment",
        "AWS::EC2::TrafficMirrorSession": "Ec2TrafficMirrorSession",
        "AWS::EC2::EIP": "Eip",
        
        # ECS
        "AWS::ECS::Service": "EcsService",
        
        # Lambda
        "AWS::Lambda::Function": "LambdaFunction",
        "AWS::Lambda::ProvisionedConcurrencyConfig": "LambdaProvisionedConcurrencyConfig",
        
        # RDS
        "AWS::RDS::DBInstance": "DbInstance",
        "AWS::RDS::DBCluster": "RdsCluster",
        "AWS::RDS::DBClusterInstance": "RdsClusterInstance",
        
        # Load Balancers
        "AWS::ElasticLoadBalancingV2::LoadBalancer": "Lb",
        "AWS::ElasticLoadBalancing::LoadBalancer": "Elb",
        
        # S3
        "AWS::S3::Bucket": "S3Bucket",
        
        # DynamoDB
        "AWS::DynamoDB::Table": "DynamodbTable",
        
        # ElastiCache
        "AWS::ElastiCache::CacheCluster": "ElasticacheCluster",
        "AWS::ElastiCache::ReplicationGroup": "ElasticacheReplicationGroup",
        
        # CloudWatch
        "AWS::CloudWatch::LogGroup": "CloudwatchLogGroup",
        "AWS::CloudWatch::Dashboard": "CloudwatchDashboard",
        "AWS::CloudWatch::MetricAlarm": "CloudwatchMetricAlarm",
        
        # Auto Scaling
        "AWS::AutoScaling::AutoScalingGroup": "AutoscalingGroup",
        "AWS::AutoScaling::LaunchConfiguration": "LaunchConfiguration",
        "AWS::EC2::LaunchTemplate": "LaunchTemplate",
        
        # API Gateway
        "AWS::ApiGateway::RestApi": "ApiGatewayRestApi",
        "AWS::ApiGateway::Stage": "ApiGatewayStage",
        "AWS::ApiGatewayV2::Api": "Apigatewayv2Api",
        
        # KMS
        "AWS::KMS::Key": "KmsKey",
        "AWS::KMS::ExternalKey": "KmsExternalKey",
        
        # SNS/SQS
        "AWS::SNS::Topic": "SnsTopic",
        "AWS::SNS::Subscription": "SnsTopicSubscription",
        "AWS::SQS::Queue": "SqsQueue",
        
        # EKS
        "AWS::EKS::Cluster": "EksCluster",
        "AWS::EKS::NodeGroup": "EksNodeGroup",
        "AWS::EKS::FargateProfile": "EksFargateProfile",
        
        # CloudFront
        "AWS::CloudFront::Distribution": "CloudfrontDistribution",
        "AWS::CloudFront::Function": "CloudfrontFunction",
        
        # EFS
        "AWS::EFS::FileSystem": "EfsFileSystem",
        
        # FSx
        "AWS::FSx::WindowsFileSystem": "FsxWindowsFileSystem",
        "AWS::FSx::OpenZFSFileSystem": "FsxOpenzfsFileSystem",
        
        # Kinesis
        "AWS::Kinesis::Stream": "KinesisStream",
        "AWS::KinesisFirehose::DeliveryStream": "KinesisFirehoseDeliveryStream",
        "AWS::KinesisAnalytics::Application": "KinesisanalyticsApplication",
        "AWS::KinesisAnalyticsV2::Application": "Kinesisanalyticsv2Application",
        "AWS::KinesisAnalyticsV2::ApplicationSnapshot": "Kinesisanalyticsv2ApplicationSnapshot",
        
        # Route53
        "AWS::Route53::HostedZone": "Route53Zone",
        "AWS::Route53::RecordSet": "Route53Record",
        "AWS::Route53::HealthCheck": "Route53HealthCheck",
        "AWS::Route53Resolver::Endpoint": "Route53ResolverEndpoint",
        
        # CloudFormation
        "AWS::CloudFormation::Stack": "CloudformationStack",
        "AWS::CloudFormation::StackSet": "CloudformationStackSet",
        
        # CloudTrail
        "AWS::CloudTrail::Trail": "Cloudtrail",
        
        # CodeBuild
        "AWS::CodeBuild::Project": "CodebuildProject",
        
        # Config
        "AWS::Config::ConfigurationRecorder": "ConfigConfigurationRecorder",
        "AWS::Config::ConfigRule": "ConfigConfigRule",
        
        # DirectConnect
        "AWS::DirectConnect::Connection": "DxConnection",
        "AWS::DirectConnect::GatewayAssociation": "DxGatewayAssociation",
        
        # DocumentDB
        "AWS::DocDB::DBCluster": "DocdbCluster",
        "AWS::DocDB::DBInstance": "DocdbClusterInstance",
        "AWS::DocDB::DBClusterSnapshot": "DocdbClusterSnapshot",
        
        # ElasticBeanstalk
        "AWS::ElasticBeanstalk::Environment": "ElasticBeanstalkEnvironment",
        
        # Elasticsearch
        "AWS::Elasticsearch::Domain": "SearchDomain",
        
        # Glue
        "AWS::Glue::Database": "GlueCatalogDatabase",
        "AWS::Glue::Crawler": "GlueCrawler",
        "AWS::Glue::Job": "GlueJob",
        
        # MSK
        "AWS::MSK::Cluster": "MskCluster",
        
        # MQ
        "AWS::MQ::Broker": "MqBroker",
        
        # Neptune
        "AWS::Neptune::DBCluster": "NeptuneCluster",
        "AWS::Neptune::DBInstance": "NeptuneClusterInstance",
        "AWS::Neptune::DBClusterSnapshot": "NeptuneClusterSnapshot",
        
        # Redshift
        "AWS::Redshift::Cluster": "RedshiftCluster",
        
        # Secrets Manager
        "AWS::SecretsManager::Secret": "SecretsmanagerSecret",
        
        # Step Functions
        "AWS::StepFunctions::StateMachine": "SfnStateMachine",
        
        # SSM
        "AWS::SSM::Parameter": "SsmParameter",
        "AWS::SSM::Activation": "SsmActivation",
        
        # Transfer
        "AWS::Transfer::Server": "TransferServer",
        
        # VPC
        "AWS::EC2::VPCEndpoint": "VpcEndpoint",
        "AWS::EC2::VPNConnection": "VpnConnection",
        
        # WAF
        "AWS::WAF::WebACL": "WafWebAcl",
        "AWS::WAFv2::WebACL": "Wafv2WebAcl",
        
        # ACM
        "AWS::CertificateManager::Certificate": "AcmCertificate",
        "AWS::ACMPCA::CertificateAuthority": "AcmpcaCertificateAuthority",
        
        # Application Auto Scaling
        "AWS::ApplicationAutoScaling::ScalableTarget": "AppAutoscalingTarget",
        
        # Backup
        "AWS::Backup::BackupVault": "BackupVault",
        
        # CloudHSM
        "AWS::CloudHSMV2::Hsm": "CloudhsmV2Hsm",
        
        # DMS
        "AWS::DMS::ReplicationInstance": "DmsReplicationInstance",
        
        # Directory Service
        "AWS::DirectoryService::MicrosoftAD": "DirectoryServiceDirectory",
        
        # ECR
        "AWS::ECR::Repository": "EcrRepository",
        
        # Events
        "AWS::Events::CustomEventBus": "CloudwatchEventBus",
        
        # Global Accelerator
        "AWS::GlobalAccelerator::Accelerator": "GlobalAccelerator",
        "AWS::GlobalAccelerator::EndpointGroup": "GlobalAcceleratorEndpointGroup",
        
        # Grafana
        "AWS::Grafana::Workspace": "GrafanaWorkspace",
        
        # Lightsail
        "AWS::Lightsail::Instance": "LightsailInstance",
        
        # MWAA
        "AWS::MWAA::Environment": "MwaaEnvironment",
        
        # Network Firewall
        "AWS::NetworkFirewall::Firewall": "NetworkfirewallFirewall",
    }
    
    # Generate Python class names from file names for unmapped resources
    for resource_file in resource_files:
        file_stem = resource_file.stem
        
        # Convert snake_case to PascalCase
        class_name = ''.join(word.capitalize() for word in file_stem.split('_'))
        
        # Check if we already have a mapping for this class
        found_mapping = False
        for cfn_type, mapped_class in known_mappings.items():
            if mapped_class.lower() == class_name.lower():
                found_mapping = True
                break
        
        if not found_mapping:
            # Try to guess CloudFormation type from class name
            guessed_cfn_type = guess_cfn_type_from_class(class_name)
            if guessed_cfn_type:
                known_mappings[guessed_cfn_type] = class_name
    
    return known_mappings

def guess_cfn_type_from_class(class_name: str) -> str:
    """Guess CloudFormation resource type from Python class name"""
    
    # Common patterns
    patterns = {
        'S3': 'AWS::S3::',
        'Ec2': 'AWS::EC2::',
        'Ecs': 'AWS::ECS::',
        'Rds': 'AWS::RDS::',
        'Lambda': 'AWS::Lambda::',
        'Cloudwatch': 'AWS::CloudWatch::',
        'Cloudfront': 'AWS::CloudFront::',
        'Apigateway': 'AWS::ApiGateway::',
        'Elasticache': 'AWS::ElastiCache::',
        'Dynamodb': 'AWS::DynamoDB::',
        'Kinesis': 'AWS::Kinesis::',
        'Route53': 'AWS::Route53::',
        'Glue': 'AWS::Glue::',
        'Eks': 'AWS::EKS::',
        'Sns': 'AWS::SNS::',
        'Sqs': 'AWS::SQS::',
        'Kms': 'AWS::KMS::',
    }
    
    for prefix, aws_prefix in patterns.items():
        if class_name.startswith(prefix):
            # Remove prefix and convert to CloudFormation naming
            resource_part = class_name[len(prefix):]
            return f"{aws_prefix}{resource_part}"
    
    return ""

def main():
    """Generate and display comprehensive mappings"""
    mappings = generate_comprehensive_mappings()
    
    print(f"Generated {len(mappings)} CloudFormation to Python class mappings:")
    print()
    
    # Sort by CloudFormation type for readability
    sorted_mappings = dict(sorted(mappings.items()))
    
    # Generate Python code for the mappings
    print("# Comprehensive CloudFormation to Python class mappings")
    print("CFN_TO_CLASS_MAPPINGS = {")
    
    for cfn_type, class_name in sorted_mappings.items():
        print(f'    "{cfn_type}": "{class_name}",')
    
    print("}")
    print()
    print(f"Total mappings: {len(mappings)}")
    
    # Save to file
    with open("cfn_mappings.py", "w") as f:
        f.write("# Auto-generated CloudFormation to Python class mappings\n")
        f.write("# Generated from 112 Infracost AWS resource definitions\n\n")
        f.write("CFN_TO_CLASS_MAPPINGS = {\n")
        
        for cfn_type, class_name in sorted_mappings.items():
            f.write(f'    "{cfn_type}": "{class_name}",\n')
        
        f.write("}\n")
    
    print("Mappings saved to cfn_mappings.py")

if __name__ == "__main__":
    main()
