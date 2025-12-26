#!/usr/bin/env python3
"""
IAM Security Rules
"""

import re
from typing import List, Dict, Any

class IAMRules:
    def analyze_file(self, file_path: str, hunks: List[Dict]) -> List[Dict]:
        """Analyze IAM configurations for security issues"""
        findings = []
        
        for hunk in hunks:
            for line in hunk["lines"]:
                if line.startswith('+'):  # Only check added lines
                    content = line[1:].strip()
                    
                    # Check for overly broad permissions
                    findings.extend(self._check_broad_permissions(file_path, hunk, content))
                    
                    # Check for admin access
                    findings.extend(self._check_admin_access(file_path, hunk, content))
                    
                    # Check for resource wildcards
                    findings.extend(self._check_resource_wildcards(file_path, hunk, content))
        
        return findings
    
    def _check_broad_permissions(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for overly broad IAM permissions"""
        findings = []
        
        # Action wildcards
        if re.search(r'Action.*\*|"Action":\s*"\*"', content, re.IGNORECASE):
            findings.append({
                "severity": "critical",
                "category": "iam",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "IAM policy with wildcard (*) action",
                "risk": "Grants all possible permissions - violates least privilege principle",
                "recommended_fix": "Specify explicit actions needed for the use case"
            })
        
        # Service-level wildcards
        service_wildcards = [
            r's3:\*', r'ec2:\*', r'iam:\*', r'lambda:\*', 
            r'dynamodb:\*', r'rds:\*', r'cloudformation:\*'
        ]
        
        for pattern in service_wildcards:
            if re.search(pattern, content, re.IGNORECASE):
                service = pattern.split(':')[0].replace('r\'', '')
                findings.append({
                    "severity": "high",
                    "category": "iam",
                    "file": file_path,
                    "lines": hunk["header"],
                    "what_changed": f"IAM policy grants all {service.upper()} permissions",
                    "risk": f"Overly broad {service.upper()} access - potential for privilege escalation",
                    "recommended_fix": f"Limit to specific {service.upper()} actions required"
                })
        
        return findings
    
    def _check_admin_access(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for administrative access patterns"""
        findings = []
        
        # AWS managed admin policies
        admin_policies = [
            'AdministratorAccess',
            'PowerUserAccess', 
            'IAMFullAccess',
            'SecurityAudit'
        ]
        
        for policy in admin_policies:
            if policy in content:
                severity = "critical" if policy == "AdministratorAccess" else "high"
                findings.append({
                    "severity": severity,
                    "category": "iam",
                    "file": file_path,
                    "lines": hunk["header"],
                    "what_changed": f"Attached AWS managed policy: {policy}",
                    "risk": f"Grants broad administrative permissions via {policy}",
                    "recommended_fix": "Create custom policy with minimal required permissions"
                })
        
        return findings
    
    def _check_resource_wildcards(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for resource wildcards in IAM policies"""
        findings = []
        
        # Resource wildcards
        if re.search(r'Resource.*\*|"Resource":\s*"\*"', content, re.IGNORECASE):
            findings.append({
                "severity": "high",
                "category": "iam",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "IAM policy with wildcard (*) resource",
                "risk": "Grants access to all resources - violates least privilege",
                "recommended_fix": "Specify explicit resource ARNs or use resource patterns"
            })
        
        return findings
