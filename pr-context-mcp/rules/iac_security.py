#!/usr/bin/env python3
"""
Infrastructure as Code Security Rules
"""

import re
from typing import List, Dict, Any

class IaCSecurityRules:
    def analyze_file(self, file_path: str, hunks: List[Dict]) -> List[Dict]:
        """Analyze IaC file for security issues"""
        findings = []
        
        # Only analyze IaC files
        if not self._is_iac_file(file_path):
            return findings
        
        for hunk in hunks:
            for line in hunk["lines"]:
                if line.startswith('+'):  # Only check added lines
                    content = line[1:].strip()
                    
                    # Check for public access patterns
                    findings.extend(self._check_public_access(file_path, hunk, content))
                    
                    # Check for encryption settings
                    findings.extend(self._check_encryption(file_path, hunk, content))
                    
                    # Check for logging/monitoring
                    findings.extend(self._check_logging(file_path, hunk, content))
        
        return findings
    
    def _is_iac_file(self, file_path: str) -> bool:
        """Check if file is Infrastructure as Code"""
        iac_extensions = ['.yaml', '.yml', '.json', '.tf', '.template']
        iac_patterns = ['cloudformation', 'terraform', 'template', 'infra']
        
        # Check extension
        for ext in iac_extensions:
            if file_path.lower().endswith(ext):
                return True
        
        # Check path patterns
        for pattern in iac_patterns:
            if pattern in file_path.lower():
                return True
        
        return False
    
    def _check_public_access(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for public access configurations"""
        findings = []
        
        # S3 public access
        if re.search(r'PublicReadAccess.*true|PublicRead|public-read', content, re.IGNORECASE):
            findings.append({
                "severity": "high",
                "category": "public-exposure",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "S3 bucket configured with public read access",
                "risk": "Data exposure - bucket contents may be publicly accessible",
                "recommended_fix": "Use bucket policies with specific principals instead of public access"
            })
        
        # RDS public access
        if re.search(r'PubliclyAccessible.*true', content, re.IGNORECASE):
            findings.append({
                "severity": "critical",
                "category": "public-exposure", 
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "RDS instance configured as publicly accessible",
                "risk": "Database exposure - RDS instance accessible from internet",
                "recommended_fix": "Set PubliclyAccessible to false and use VPC security groups"
            })
        
        return findings
    
    def _check_encryption(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for encryption settings"""
        findings = []
        
        # Unencrypted storage
        if re.search(r'Encrypted.*false|StorageEncrypted.*false', content, re.IGNORECASE):
            findings.append({
                "severity": "high",
                "category": "encryption",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "Storage encryption disabled",
                "risk": "Data at rest not encrypted - compliance and security risk",
                "recommended_fix": "Enable encryption for all storage resources"
            })
        
        return findings
    
    def _check_logging(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for logging and monitoring"""
        findings = []
        
        # CloudTrail logging disabled
        if re.search(r'EnableLogging.*false|IsLogging.*false', content, re.IGNORECASE):
            findings.append({
                "severity": "medium",
                "category": "ops",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "Logging disabled for audit trail",
                "risk": "Reduced visibility into API calls and security events",
                "recommended_fix": "Enable logging for compliance and security monitoring"
            })
        
        return findings
