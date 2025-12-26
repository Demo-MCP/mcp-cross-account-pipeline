#!/usr/bin/env python3
"""
CloudFormation Template Analyzer
"""

import yaml
import json
import re
from typing import Dict, List, Any, Optional

class CloudFormationAnalyzer:
    def __init__(self, infrastructure_folder: str = "infrastructure"):
        self.infrastructure_folder = infrastructure_folder
        
    def analyze_template_changes(self, file_path: str, status: str, diff_content: str) -> Optional[Dict[str, Any]]:
        """Analyze CloudFormation template changes and extract resource information"""
        if not self._is_cfn_template(file_path):
            return None
            
        try:
            # Extract template content from diff
            template_content = self._extract_template_from_diff(diff_content, file_path)
            if not template_content:
                return {
                    "file_path": file_path,
                    "status": status,
                    "error": "Could not extract template content from diff"
                }
            
            # Clean up the template content - remove any problematic characters
            template_content = template_content.strip()
            
            # Parse template
            template = self._parse_template(template_content)
            if not template:
                # Try to give more specific error info
                lines = template_content.split('\n')
                return {
                    "file_path": file_path,
                    "status": status,
                    "error": f"YAML parsing failed. Template has {len(lines)} lines. Starts with: '{lines[0] if lines else 'empty'}'"
                }
                
            # Analyze resources
            analysis = {
                "file_path": file_path,
                "status": status,
                "template_info": self._get_template_info(template),
                "resources": self._analyze_resources(template.get("Resources", {})),
                "parameters": self._analyze_parameters(template.get("Parameters", {})),
                "outputs": self._analyze_outputs(template.get("Outputs", {}))
            }
            
            return analysis
            
        except Exception as e:
            return {
                "file_path": file_path,
                "status": status,
                "error": f"Exception: {str(e)}"
            }
    
    def _is_cfn_template(self, file_path: str) -> bool:
        """Check if file is a CloudFormation template"""
        path_lower = file_path.lower()
        
        # Must be in infrastructure folder
        if not path_lower.startswith(f"{self.infrastructure_folder.lower()}/"):
            return False
            
        # Must be YAML or JSON
        if not (path_lower.endswith(('.yaml', '.yml', '.json'))):
            return False
            
        return True
    
    def _extract_template_from_diff(self, diff_content: str, file_path: str) -> Optional[str]:
        """Extract template content from diff for new files"""
        lines = diff_content.split('\n')
        template_lines = []
        in_file = False
        
        for line in lines:
            # Look for the file in the diff header
            if line.startswith('diff --git') and file_path in line:
                in_file = True
                continue
            elif line.startswith('diff --git') and in_file:
                # Started a new file, stop processing
                break
            elif in_file:
                # Skip diff metadata lines
                if line.startswith('new file mode') or line.startswith('index ') or line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                    continue
                elif line.startswith('+') and not line.startswith('+++'):
                    # Remove the '+' prefix and add to template
                    template_lines.append(line[1:])
                elif line.startswith(' '):
                    # Context line (unchanged), add without prefix
                    template_lines.append(line[1:])
        
        if template_lines:
            return '\n'.join(template_lines)
        return None
    
    def _parse_template(self, content: str) -> Optional[Dict]:
        """Parse YAML or JSON template content"""
        try:
            # Try YAML first with safe_load
            import yaml
            return yaml.safe_load(content)
        except Exception as yaml_error:
            try:
                # Try JSON as fallback
                import json
                return json.loads(content)
            except Exception as json_error:
                # If both fail, try to extract basic info manually for CloudFormation
                return self._extract_basic_cfn_info(content)
    
    def _extract_basic_cfn_info(self, content: str) -> Optional[Dict]:
        """Extract basic CloudFormation info when YAML parsing fails"""
        try:
            lines = content.split('\n')
            template = {"Resources": {}, "Parameters": {}, "Outputs": {}}
            
            # Extract description
            for line in lines:
                if line.strip().startswith('Description:'):
                    desc = line.split('Description:')[1].strip().strip("'\"")
                    template["Description"] = desc
                    break
            
            # Extract resources by looking for Type: AWS::
            current_resource = None
            for line in lines:
                stripped = line.strip()
                
                # Look for resource definitions (indented resource names)
                if line.startswith('  ') and not line.startswith('    ') and ':' in line and not stripped.startswith('#'):
                    resource_name = stripped.split(':')[0].strip()
                    if resource_name and not resource_name.startswith(('Type', 'Properties', 'Description')):
                        current_resource = resource_name
                        template["Resources"][current_resource] = {}
                
                # Look for resource types
                elif stripped.startswith('Type: AWS::') and current_resource:
                    resource_type = stripped.split('Type:')[1].strip()
                    template["Resources"][current_resource]["Type"] = resource_type
            
            # Only return if we found some resources
            if template["Resources"]:
                return template
            return None
            
        except Exception:
            return None
    
    def _get_template_info(self, template: Dict) -> Dict[str, Any]:
        """Extract basic template information"""
        return {
            "format_version": template.get("AWSTemplateFormatVersion", "Unknown"),
            "description": template.get("Description", "No description provided"),
            "resource_count": len(template.get("Resources", {})),
            "parameter_count": len(template.get("Parameters", {})),
            "output_count": len(template.get("Outputs", {}))
        }
    
    def _analyze_resources(self, resources: Dict) -> List[Dict[str, Any]]:
        """Analyze CloudFormation resources"""
        resource_analysis = []
        
        # Group resources by type for better presentation
        resource_types = {}
        for resource_name, resource_config in resources.items():
            resource_type = resource_config.get("Type", "Unknown")
            if resource_type not in resource_types:
                resource_types[resource_type] = []
            resource_types[resource_type].append({
                "name": resource_name,
                "config": resource_config
            })
        
        # Analyze each resource type
        for resource_type, resource_list in resource_types.items():
            analysis = self._analyze_resource_type(resource_type, resource_list)
            if analysis:
                resource_analysis.append(analysis)
        
        return resource_analysis
    
    def _analyze_resource_type(self, resource_type: str, resources: List[Dict]) -> Optional[Dict[str, Any]]:
        """Analyze specific resource type"""
        count = len(resources)
        
        # Get service and category
        service_info = self._get_service_info(resource_type)
        
        # Get resource-specific details
        details = []
        for resource in resources:
            detail = self._get_resource_details(resource_type, resource)
            if detail:
                details.append(detail)
        
        return {
            "type": resource_type,
            "service": service_info["service"],
            "category": service_info["category"],
            "count": count,
            "resources": [r["name"] for r in resources],
            "details": details,
            "security_impact": self._assess_security_impact(resource_type, resources)
        }
    
    def _get_service_info(self, resource_type: str) -> Dict[str, str]:
        """Get AWS service and category information"""
        service_map = {
            "AWS::ECS::": {"service": "ECS", "category": "Compute"},
            "AWS::EC2::": {"service": "EC2", "category": "Compute"},
            "AWS::Lambda::": {"service": "Lambda", "category": "Compute"},
            "AWS::IAM::": {"service": "IAM", "category": "Security"},
            "AWS::S3::": {"service": "S3", "category": "Storage"},
            "AWS::RDS::": {"service": "RDS", "category": "Database"},
            "AWS::ElasticLoadBalancingV2::": {"service": "ALB/NLB", "category": "Networking"},
            "AWS::ECR::": {"service": "ECR", "category": "Container Registry"},
            "AWS::Logs::": {"service": "CloudWatch Logs", "category": "Monitoring"},
            "AWS::SecretsManager::": {"service": "Secrets Manager", "category": "Security"}
        }
        
        for prefix, info in service_map.items():
            if resource_type.startswith(prefix):
                return info
        
        return {"service": "Unknown", "category": "Other"}
    
    def _get_resource_details(self, resource_type: str, resource: Dict) -> Optional[str]:
        """Get specific details for resource types"""
        name = resource["name"]
        config = resource["config"]
        properties = config.get("Properties", {})
        
        if resource_type == "AWS::ECS::Service":
            cluster = properties.get("Cluster", "default")
            desired_count = properties.get("DesiredCount", 1)
            return f"{name}: {desired_count} tasks on cluster '{cluster}'"
            
        elif resource_type == "AWS::ECS::TaskDefinition":
            cpu = properties.get("Cpu", "unknown")
            memory = properties.get("Memory", "unknown")
            return f"{name}: {cpu} CPU, {memory} MB memory"
            
        elif resource_type == "AWS::IAM::Role":
            policies = properties.get("ManagedPolicyArns", [])
            return f"{name}: {len(policies)} managed policies attached"
            
        elif resource_type == "AWS::ElasticLoadBalancingV2::TargetGroup":
            port = properties.get("Port", "unknown")
            protocol = properties.get("Protocol", "unknown")
            return f"{name}: {protocol} on port {port}"
            
        elif resource_type == "AWS::ECR::Repository":
            repo_name = properties.get("RepositoryName", name)
            return f"{name}: Repository '{repo_name}'"
            
        elif resource_type == "AWS::Logs::LogGroup":
            retention = properties.get("RetentionInDays", "indefinite")
            return f"{name}: {retention} days retention"
        
        return None
    
    def _assess_security_impact(self, resource_type: str, resources: List[Dict]) -> str:
        """Assess security impact of resource type"""
        if resource_type.startswith("AWS::IAM::"):
            return "HIGH - IAM resources affect access permissions"
        elif resource_type in ["AWS::EC2::SecurityGroup", "AWS::ElasticLoadBalancingV2::LoadBalancer"]:
            return "MEDIUM - Network security configuration"
        elif resource_type.startswith("AWS::SecretsManager::"):
            return "HIGH - Secrets and credential management"
        elif resource_type.startswith("AWS::S3::"):
            return "MEDIUM - Data storage and access"
        else:
            return "LOW - Standard resource deployment"
    
    def _analyze_parameters(self, parameters: Dict) -> List[Dict[str, Any]]:
        """Analyze CloudFormation parameters"""
        param_analysis = []
        
        for param_name, param_config in parameters.items():
            param_type = param_config.get("Type", "String")
            description = param_config.get("Description", "No description")
            no_echo = param_config.get("NoEcho", False)
            
            analysis = {
                "name": param_name,
                "type": param_type,
                "description": description,
                "sensitive": no_echo,
                "default": param_config.get("Default")
            }
            param_analysis.append(analysis)
        
        return param_analysis
    
    def _analyze_outputs(self, outputs: Dict) -> List[Dict[str, Any]]:
        """Analyze CloudFormation outputs"""
        output_analysis = []
        
        for output_name, output_config in outputs.items():
            description = output_config.get("Description", "No description")
            export_name = output_config.get("Export", {}).get("Name")
            
            analysis = {
                "name": output_name,
                "description": description,
                "exported": bool(export_name),
                "export_name": export_name
            }
            output_analysis.append(analysis)
        
        return output_analysis
    
    def format_analysis_card(self, analysis: Dict[str, Any]) -> str:
        """Format analysis as a card for PR review"""
        if "error" in analysis:
            return f"❌ **{analysis['file_path']}**: {analysis['error']}"
        
        template_info = analysis["template_info"]
        resources = analysis["resources"]
        parameters = analysis["parameters"]
        
        card_parts = []
        
        # Header
        status_icon = "🆕" if analysis["status"] == "added" else "🔄"
        card_parts.append(f"{status_icon} **CloudFormation Template: {analysis['file_path']}**")
        card_parts.append(f"📋 *{template_info['description']}*")
        
        # Resource summary
        if resources:
            card_parts.append(f"\\n**Resources ({template_info['resource_count']}):**")
            
            # Group by service
            services = {}
            for resource in resources:
                service = resource["service"]
                if service not in services:
                    services[service] = []
                services[service].append(resource)
            
            for service, service_resources in services.items():
                total_count = sum(r["count"] for r in service_resources)
                card_parts.append(f"• **{service}**: {total_count} resources")
                
                # Show high-impact resources
                for resource in service_resources:
                    if resource["security_impact"].startswith("HIGH"):
                        card_parts.append(f"  ⚠️ {resource['type']} ({resource['count']}x) - {resource['security_impact']}")
                    elif resource["details"]:
                        for detail in resource["details"][:2]:  # Limit to 2 details
                            card_parts.append(f"    - {detail}")
        
        # Parameters (sensitive ones)
        sensitive_params = [p for p in parameters if p["sensitive"]]
        if sensitive_params:
            card_parts.append(f"\\n**Sensitive Parameters ({len(sensitive_params)}):**")
            for param in sensitive_params:
                card_parts.append(f"• {param['name']}: {param['description']}")
        
        # Security review note
        high_impact_resources = [r for r in resources if r["security_impact"].startswith("HIGH")]
        if high_impact_resources:
            card_parts.append(f"\\n🔒 **Security Review Required**: {len(high_impact_resources)} high-impact resources")
        
        return "\\n".join(card_parts)
