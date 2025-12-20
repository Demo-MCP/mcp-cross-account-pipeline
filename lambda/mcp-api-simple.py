import json
import boto3
import time

def lambda_handler(event, context):
    """
    Simple Lambda to test cross-account AssumeRole functionality
    """
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        account_id = body.get('account_id', '500330120558')
        region = body.get('region', 'us-east-1')
        tool = body.get('tool', 'test')
        
        start_time = time.time()
        
        # Test AssumeRole
        sts = boto3.client('sts', region_name=region)
        
        # Get current identity
        current_identity = sts.get_caller_identity()
        
        # Assume the McpReadOnlyRole
        role_arn = f"arn:aws:iam::{account_id}:role/McpReadOnlyRole"
        
        assume_response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="MCP-API-Test"
        )
        
        # Test CloudFormation access with assumed role
        cf_client = boto3.client(
            'cloudformation',
            region_name=region,
            aws_access_key_id=assume_response['Credentials']['AccessKeyId'],
            aws_secret_access_key=assume_response['Credentials']['SecretAccessKey'],
            aws_session_token=assume_response['Credentials']['SessionToken']
        )
        
        # Try to list stacks
        stacks = cf_client.list_stacks(StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE'])
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'analysis': f"✅ Cross-account access successful!\n\n**Current Identity**: {current_identity['Arn']}\n**Assumed Role**: {assume_response['AssumedRoleUser']['Arn']}\n**CloudFormation Access**: Found {len(stacks['StackSummaries'])} stacks\n**Tool**: {tool}\n**Account**: {account_id}\n**Region**: {region}",
                'duration_ms': duration_ms,
                'account_id': account_id,
                'region': region,
                'tool': tool,
                'success': True
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f"❌ Error: {str(e)}",
                'success': False
            })
        }
