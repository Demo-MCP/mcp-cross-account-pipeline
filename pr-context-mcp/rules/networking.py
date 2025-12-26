#!/usr/bin/env python3
"""
Networking Security Rules
"""

import re
from typing import List, Dict, Any

class NetworkingRules:
    def analyze_file(self, file_path: str, hunks: List[Dict]) -> List[Dict]:
        """Analyze networking configurations for security issues"""
        findings = []
        
        for hunk in hunks:
            for line in hunk["lines"]:
                if line.startswith('+'):  # Only check added lines
                    content = line[1:].strip()
                    
                    # Check for open security groups
                    findings.extend(self._check_security_groups(file_path, hunk, content))
                    
                    # Check for public subnets
                    findings.extend(self._check_public_subnets(file_path, hunk, content))
                    
                    # Check for internet gateways
                    findings.extend(self._check_internet_access(file_path, hunk, content))
        
        return findings
    
    def _check_security_groups(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for overly permissive security group rules"""
        findings = []
        
        # 0.0.0.0/0 ingress
        if re.search(r'0\.0\.0\.0/0|CidrIp.*0\.0\.0\.0/0', content):
            findings.append({
                "severity": "critical",
                "category": "network",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "Security group allows ingress from 0.0.0.0/0",
                "risk": "Unrestricted internet access - potential for unauthorized access",
                "recommended_fix": "Restrict source to specific IP ranges or security groups"
            })
        
        # SSH/RDP from anywhere
        ssh_patterns = [
            r'FromPort.*22.*ToPort.*22.*0\.0\.0\.0/0',
            r'port.*22.*cidr.*0\.0\.0\.0/0',
            r'FromPort.*3389.*ToPort.*3389.*0\.0\.0\.0/0'
        ]
        
        for pattern in ssh_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                port = "22 (SSH)" if "22" in pattern else "3389 (RDP)"
                findings.append({
                    "severity": "critical",
                    "category": "network",
                    "file": file_path,
                    "lines": hunk["header"],
                    "what_changed": f"Security group allows port {port} from anywhere",
                    "risk": "Remote access exposed to internet - high risk of compromise",
                    "recommended_fix": "Restrict SSH/RDP access to specific IP ranges or use bastion hosts"
                })
        
        return findings
    
    def _check_public_subnets(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for public subnet configurations"""
        findings = []
        
        # Public IP assignment
        if re.search(r'AssignPublicIp.*true|MapPublicIpOnLaunch.*true', content, re.IGNORECASE):
            findings.append({
                "severity": "medium",
                "category": "network",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "Resource configured to assign public IP addresses",
                "risk": "Resources will be directly accessible from internet",
                "recommended_fix": "Use private subnets with NAT Gateway for outbound access"
            })
        
        return findings
    
    def _check_internet_access(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for internet gateway and routing configurations"""
        findings = []
        
        # Internet gateway routes
        if re.search(r'DestinationCidrBlock.*0\.0\.0\.0/0.*GatewayId', content, re.IGNORECASE):
            findings.append({
                "severity": "low",
                "category": "network",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "Route table configured with internet gateway",
                "risk": "Enables internet access for associated subnets",
                "recommended_fix": "Ensure only public subnets use internet gateway routes"
            })
        
        return findings
