# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
from typing import Optional, Dict, Any, List
from dataclasses import asdict

from fastmcp import FastMCP
from fastmcp.server.proxy import ProxyClient
from loguru import logger

from awslabs.aws_iac_mcp_server.client.aws_knowledge_client import KNOWLEDGE_MCP_ENDPOINT
from awslabs.aws_iac_mcp_server.client.mcp_proxy import create_local_proxied_tool, get_remote_proxy_server_tool
from awslabs.aws_iac_mcp_server.sanitizer import sanitize_tool_response
from awslabs.aws_iac_mcp_server.tools.cloudformation_compliance_checker import check_compliance, initialize_guard_rules
from awslabs.aws_iac_mcp_server.tools.cloudformation_deployment_troubleshooter import DeploymentTroubleshooter
from awslabs.aws_iac_mcp_server.tools.cloudformation_pre_deploy_validation import cloudformation_pre_deploy_validation
from awslabs.aws_iac_mcp_server.tools.cloudformation_validator import validate_template
from awslabs.aws_iac_mcp_server.tools.iac_tools import (
    SupportedLanguages,
    cdk_best_practices_tool,
    search_cdk_documentation_tool,
    search_cdk_samples_and_constructs_tool,
    search_cloudformation_documentation_tool,
)

# Initialize FastMCP server
mcp = FastMCP(
    name='aws-iac-mcp-server',
    instructions="""
                # AWS IaC MCP Server
                This server provides tools for AWS Infrastructure as Code development, including CloudFormation template validation, compliance checking, deployment troubleshooting, and AWS CDK documentation access.
              """,
)

# Initialize guard rules on server startup
initialize_guard_rules()

async def _create_read_tool_proxy():
    try:
        aws_knowledge_mcp_read_tool = await get_remote_proxy_server_tool(
            remote_proxy_client=ProxyClient(KNOWLEDGE_MCP_ENDPOINT),
            remote_tool_name='aws___read_documentation',
        )
        local_tool_description = aws_knowledge_mcp_read_tool.description
        proxied_read_tool = await create_local_proxied_tool(
            remote_tool=aws_knowledge_mcp_read_tool,
            local_tool_name='read_iac_documentation_page',
            local_tool_description=local_tool_description,
        )
        mcp.add_tool(proxied_read_tool)
    except Exception as e:
        logger.warning(f"Failed to initialize read tool proxy: {e}")

@mcp.tool()
def validate_cloudformation_template(
    template_content: str,
    regions: Optional[list[str]] = None,
    ignore_checks: Optional[list[str]] = None,
) -> str:
    """Validate CloudFormation template syntax and schema."""
    result = validate_template(
        template_content=template_content,
        regions=regions,
        ignore_checks=ignore_checks,
    )
    return sanitize_tool_response(json.dumps(result, indent=2))

@mcp.tool()
def check_cloudformation_template_compliance(
    template_content: str, rules_file_path: str = 'default_guard_rules.guard'
) -> str:
    """Validate CloudFormation template against security rules using cfn-guard."""
    result = check_compliance(
        template_content=template_content,
        rules_file_path=rules_file_path,
    )
    return sanitize_tool_response(json.dumps(result, indent=2))

@mcp.tool()
def troubleshoot_cloudformation_deployment(
    stack_name: str,
    region: str,
    include_cloudtrail: bool = True,
    account_id: str = "",
    # UPDATED: Explicitly handle _metadata to prevent Pydantic validation crashes
    _metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Troubleshoot CloudFormation deployment failures with root cause analysis.
    
    Args:
        stack_name: Name of the failed CloudFormation stack
        region: AWS region where the stack deployment failed
        include_cloudtrail: Whether to include CloudTrail analysis
        account_id: AWS account ID for cross-account access
        _metadata: Optional metadata for request tracking (actor, repo, etc.)
    """
    account_context = None
    if account_id:
        account_context = {
            "account_id": account_id,
            "region": region,
            "metadata": _metadata or {} # Pass metadata to internal handler
        }
    
    troubleshooter = DeploymentTroubleshooter(region=region, account_context=account_context)
    result = troubleshooter.troubleshoot_stack_deployment(
        stack_name=stack_name, include_cloudtrail=include_cloudtrail
    )

    if isinstance(result, dict):
        result['_instruction'] = (
            f'ALWAYS include this CloudFormation console deeplink in your response: '
            f'[View Stack](https://console.aws.amazon.com/cloudformation/home?region={region}'
            f'#/stacks/stackinfo?stackId={stack_name})'
        )

    return sanitize_tool_response(json.dumps(result, indent=2, default=str))

@mcp.tool()
def get_cloudformation_pre_deploy_validation_instructions() -> str:
    """Get instructions for CloudFormation pre-deployment validation."""
    result = cloudformation_pre_deploy_validation()
    return sanitize_tool_response(result)

@mcp.tool()
async def search_cdk_documentation(query: str) -> str:
    """Searches AWS CDK documentation knowledge bases."""
    result = await search_cdk_documentation_tool(query)
    return sanitize_tool_response(json.dumps(asdict(result)))

@mcp.tool()
async def search_cloudformation_documentation(query: str) -> str:
    """Searches AWS CloudFormation documentation knowledge bases."""
    result = await search_cloudformation_documentation_tool(query)
    return sanitize_tool_response(json.dumps(asdict(result)))

@mcp.tool()
async def search_cdk_samples_and_constructs(
    query: str,
    language: SupportedLanguages = 'typescript',
) -> str:
    """Searches CDK code samples and constructs."""
    result = await search_cdk_samples_and_constructs_tool(query, language)
    return sanitize_tool_response(json.dumps(asdict(result)))

@mcp.tool()
async def cdk_best_practices() -> str:
    """Returns CDK best practices and security guidelines."""
    result = await cdk_best_practices_tool()
    return sanitize_tool_response(json.dumps(asdict(result)))

def main():
    import asyncio
    try:
        asyncio.run(_create_read_tool_proxy())
    except Exception as e:
        logger.warning(f"Failed to initialize read tool proxy: {e}")
    mcp.run()

if __name__ == '__main__':
    main()
