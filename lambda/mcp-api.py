import json
import boto3
import time
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda function that invokes MCP servers running on ECS
    """
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        tool = body.get('tool')
        account_id = body.get('account_id')
        region = body.get('region', 'us-east-1')
        
        # Validate required parameters
        if not tool or not account_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters: tool, account_id'})
            }
        
        start_time = time.time()
        
        # Get running ECS task
        ecs = boto3.client('ecs', region_name=region)
        tasks = ecs.list_tasks(
            cluster='mcp-cluster',
            serviceName='mcp-service',  # We'll create a service
            desiredStatus='RUNNING'
        )
        
        if not tasks['taskArns']:
            return {
                'statusCode': 503,
                'body': json.dumps({'error': 'No MCP servers running'})
            }
        
        task_arn = tasks['taskArns'][0]
        
        # Get task details for network info
        task_details = ecs.describe_tasks(
            cluster='mcp-cluster',
            tasks=[task_arn]
        )
        
        # Get ENI and public IP
        eni_id = None
        for attachment in task_details['tasks'][0]['attachments']:
            if attachment['type'] == 'ElasticNetworkInterface':
                for detail in attachment['details']:
                    if detail['name'] == 'networkInterfaceId':
                        eni_id = detail['value']
                        break
        
        if not eni_id:
            return {
                'statusCode': 503,
                'body': json.dumps({'error': 'Could not find task network interface'})
            }
        
        # Get public IP
        ec2 = boto3.client('ec2', region_name=region)
        eni_details = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
        public_ip = eni_details['NetworkInterfaces'][0]['Association']['PublicIp']
        
        # Call MCP server via HTTP
        import requests
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": {
                    "account_id": account_id,
                    "region": region,
                    **{k: v for k, v in body.items() if k not in ['tool', 'account_id', 'region']}
                }
            }
        }
        
        # Try both ECS and IaC servers (ports 8000 and 8001)
        for port in [8000, 8001]:
            try:
                response = requests.post(
                    f'http://{public_ip}:{port}/mcp',
                    json=mcp_request,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'analysis': result.get('result', {}).get('content', [{}])[0].get('text', 'No result'),
                            'duration_ms': duration_ms,
                            'account_id': account_id,
                            'region': region,
                            'tool': tool
                        })
                    }
            except Exception as e:
                continue
        
        return {
            'statusCode': 503,
            'body': json.dumps({'error': 'MCP servers not responding'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
