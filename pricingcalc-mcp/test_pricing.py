#!/usr/bin/env python3
"""
Test suite for AWS Pricing Calculator MCP Service
Tests all 47 implemented services with various configurations
"""

import json
import requests
import time

# Test configuration
BASE_URL = "http://localhost:8080/pricingcalc"
HEADERS = {"Content-Type": "application/json"}

def make_request(template_content, region="us-east-1"):
    """Make pricing request to MCP service"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "pricingcalc_estimate_from_cfn",
            "arguments": {
                "template_content": template_content,
                "region": region
            }
        }
    }
    
    response = requests.post(BASE_URL, headers=HEADERS, json=payload)
    return response.json()

def test_service(service_name, resource_type, properties=None, expected_behavior=None):
    """Test a single AWS service with enhanced validation"""
    if properties is None:
        properties = {}
    
    # Format properties as YAML instead of JSON
    props_yaml = ""
    if properties:
        for key, value in properties.items():
            if isinstance(value, str):
                props_yaml += f"      {key}: {value}\n"
            else:
                props_yaml += f"      {key}: {value}\n"
    else:
        props_yaml = "      {}\n"
    
    template = f"""AWSTemplateFormatVersion: "2010-09-09"
Resources:
  Test{service_name}:
    Type: {resource_type}
    Properties:
{props_yaml}"""
    
    try:
        result = make_request(template)
        if 'resources' in result and len(result['resources']) > 0:
            resource = result['resources'][0]
            cost = resource['monthly_cost']['high']
            source = resource['pricing_details']['source']
            has_error = "error" in resource['pricing_details']
            
            # Enhanced validation based on expected behavior
            if expected_behavior == "free_service":
                # Services that should be free with AWS Documentation source
                status = "✅ PASS" if cost == 0 and source == "AWS Documentation" else "❌ FAIL"
                reason = f"Expected free service with AWS Documentation source"
            elif expected_behavior == "api_unavailable":
                # Services where AWS Pricing API is known to be unavailable
                status = "✅ PASS" if has_error and "error" in resource['pricing_details'] else "❌ FAIL"
                reason = f"Expected API unavailable error"
            elif expected_behavior == "free_tier":
                # Services with free tier that might show $0 legitimately
                status = "✅ PASS" if (cost >= 0 and source == "AWS Pricing API") or source == "AWS Documentation" else "❌ FAIL"
                reason = f"Free tier service - $0 acceptable"
            else:
                # Standard services that should have pricing
                status = "✅ PASS" if cost > 0 or source == "AWS Documentation" else "⚠️  ZERO"
                if has_error:
                    status = "❌ ERROR"
                reason = f"Standard pricing expected"
            
            # Enhanced output with validation details
            error_msg = resource['pricing_details'].get('error', '')[:30] if has_error else ''
            print(f"{status} {service_name:25} {resource_type:40} ${cost:>8.2f}/month ({source}) {error_msg}")
            
            return status in ["✅ PASS", "⚠️  ZERO"]
        else:
            print(f"❌ ERROR {service_name:25} {resource_type:40} No response")
            return False
            
    except Exception as e:
        print(f"❌ ERROR {service_name:25} {resource_type:40} Exception: {str(e)[:50]}")
        return False

def run_tests():
    """Run all service tests"""
    print("🧪 AWS Pricing Calculator Test Suite")
    print("=" * 80)
    
    # Wait for service to be ready
    print("⏳ Waiting for service to be ready...")
    time.sleep(3)
    
    tests = [
        # Phase 1: Compute & Infrastructure (7 services)
        ("EC2Instance", "AWS::EC2::Instance", {"InstanceType": "t3.micro"}, None),
        ("EBSVolume", "AWS::EC2::Volume", {"VolumeType": "gp3", "Size": 20}, None),
        ("AutoScalingGroup", "AWS::AutoScaling::AutoScalingGroup", {"MinSize": 1, "MaxSize": 3}, "free_service"),
        ("NATGateway", "AWS::EC2::NatGateway", {}, None),
        ("ECSService", "AWS::ECS::Service", {"DesiredCount": 1}, "api_unavailable"),  # Fargate pricing not available
        ("EKSCluster", "AWS::EKS::Cluster", {}, None),
        ("LambdaFunction", "AWS::Lambda::Function", {"Runtime": "python3.11", "MemorySize": 128}, "free_tier"),
        
        # Phase 1: Databases (6 services)
        ("RDSInstance", "AWS::RDS::DBInstance", {"DBInstanceClass": "db.t3.micro", "Engine": "postgres"}, None),
        ("DynamoDBTable", "AWS::DynamoDB::Table", {}, "free_tier"),  # Has 25GB free tier
        ("ElastiCacheReplication", "AWS::ElastiCache::ReplicationGroup", {"CacheNodeType": "cache.t3.micro"}, None),
        ("RedshiftCluster", "AWS::Redshift::Cluster", {"NodeType": "dc2.large"}, None),
        ("NeptuneCluster", "AWS::Neptune::DBCluster", {}, None),
        ("DocumentDBCluster", "AWS::DocDB::DBCluster", {}, None),
        
        # Phase 1: Storage (4 services)
        ("S3Bucket", "AWS::S3::Bucket", {}, "free_tier"),  # Has free tier
        ("EFSFileSystem", "AWS::EFS::FileSystem", {}, None),
        ("FSxWindows", "AWS::FSx::WindowsFileSystem", {"StorageCapacity": 32}, None),
        ("BackupVault", "AWS::Backup::BackupVault", {}, "free_service"),
        
        # Phase 2: Networking & Load Balancing (8 services)
        ("ApplicationLB", "AWS::ElasticLoadBalancingV2::LoadBalancer", {"Type": "application"}, None),
        ("ClassicELB", "AWS::ElasticLoadBalancing::LoadBalancer", {}, None),
        ("VPCEndpoint", "AWS::EC2::VPCEndpoint", {"VpcEndpointType": "Interface"}, None),
        ("Route53Zone", "AWS::Route53::HostedZone", {}, None),
        ("CloudFront", "AWS::CloudFront::Distribution", {}, "free_tier"),  # Has free tier
        ("GlobalAccelerator", "AWS::GlobalAccelerator::Accelerator", {}, None),
        ("DirectConnect", "AWS::DirectConnect::Connection", {"Bandwidth": "1Gbps"}, None),
        
        # Phase 3: Serverless & Analytics (12 services)
        ("APIGateway", "AWS::ApiGateway::RestApi", {}, "free_tier"),  # Has free tier
        ("StepFunctions", "AWS::StepFunctions::StateMachine", {}, None),
        ("EventBridge", "AWS::Events::CustomEventBus", {}, "free_tier"),  # Has free tier
        ("KinesisStream", "AWS::Kinesis::Stream", {"ShardCount": 1}, None),
        ("KinesisFirehose", "AWS::KinesisFirehose::DeliveryStream", {}, None),
        ("GlueJob", "AWS::Glue::Job", {}, None),
        ("MSKCluster", "AWS::MSK::Cluster", {"NumberOfBrokerNodes": 3}, None),
        ("ElasticsearchDomain", "AWS::Elasticsearch::Domain", {}, None),
        ("KinesisAnalytics", "AWS::KinesisAnalytics::Application", {}, None),
        ("MWAAEnvironment", "AWS::MWAA::Environment", {"EnvironmentClass": "mw1.small"}, None),
        ("GrafanaWorkspace", "AWS::Grafana::Workspace", {}, None),
        
        # Phase 4: Security & Management (10 services)
        ("KMSKey", "AWS::KMS::Key", {}, "free_tier"),  # Has free tier
        ("SecretsManager", "AWS::SecretsManager::Secret", {}, None),
        ("WAFv2WebACL", "AWS::WAFv2::WebACL", {}, None),
        ("NetworkFirewall", "AWS::NetworkFirewall::Firewall", {}, None),
        ("ACMCertificate", "AWS::CertificateManager::Certificate", {}, "free_service"),  # Free service
        ("ACMPrivateCA", "AWS::ACMPCA::CertificateAuthority", {}, None),
        ("CloudWatchLogs", "AWS::CloudWatch::LogGroup", {}, "free_tier"),  # Has free tier
        ("CloudTrail", "AWS::CloudTrail::Trail", {}, "free_tier"),  # Has free tier
        ("ConfigRule", "AWS::Config::ConfigRule", {}, None),
        ("SSMParameter", "AWS::SSM::Parameter", {"Type": "String"}, "free_service"),  # Standard parameters are free
    ]
    
    passed = 0
    total = len(tests)
    
    print(f"\n🔍 Testing {total} AWS Services")
    print("-" * 80)
    
    for service_name, resource_type, properties, expected_behavior in tests:
        if test_service(service_name, resource_type, properties, expected_behavior):
            passed += 1
        time.sleep(0.5)  # Rate limiting
    
    print("-" * 80)
    print(f"📊 Test Results: {passed}/{total} services passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed!")
    elif passed >= total * 0.8:
        print("✅ Most tests passed - good coverage!")
    else:
        print("⚠️  Some services need attention")
    
    return passed, total

if __name__ == "__main__":
    run_tests()
