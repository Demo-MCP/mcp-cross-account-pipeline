#!/usr/bin/env python3
"""
Secrets and Credentials Security Rules
"""

import re
from typing import List, Dict, Any

class SecretsRules:
    def analyze_file(self, file_path: str, hunks: List[Dict]) -> List[Dict]:
        """Analyze for exposed secrets and credentials"""
        findings = []
        
        for hunk in hunks:
            for line in hunk["lines"]:
                if line.startswith('+'):  # Only check added lines
                    content = line[1:].strip()
                    
                    # Check for hardcoded secrets
                    findings.extend(self._check_hardcoded_secrets(file_path, hunk, content))
                    
                    # Check for API keys
                    findings.extend(self._check_api_keys(file_path, hunk, content))
                    
                    # Check for database credentials
                    findings.extend(self._check_db_credentials(file_path, hunk, content))
        
        return findings
    
    def _check_hardcoded_secrets(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for hardcoded secrets and passwords"""
        findings = []
        
        # Common secret patterns
        secret_patterns = [
            (r'password.*["\']([^"\']{8,})["\']', "password"),
            (r'secret.*["\']([^"\']{16,})["\']', "secret"),
            (r'key.*["\']([A-Za-z0-9+/]{20,})["\']', "key"),
            (r'token.*["\']([A-Za-z0-9_-]{20,})["\']', "token")
        ]
        
        for pattern, secret_type in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # Skip obvious placeholders
                if any(placeholder in content.lower() for placeholder in 
                       ['placeholder', 'example', 'changeme', 'password123', 'your-', 'my-']):
                    continue
                
                findings.append({
                    "severity": "critical",
                    "category": "secrets",
                    "file": file_path,
                    "lines": hunk["header"],
                    "what_changed": f"Hardcoded {secret_type} in configuration",
                    "risk": "Credentials exposed in code - security breach risk",
                    "recommended_fix": f"Use AWS Secrets Manager or environment variables for {secret_type}"
                })
        
        return findings
    
    def _check_api_keys(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for API keys and tokens"""
        findings = []
        
        # AWS access keys
        if re.search(r'AKIA[0-9A-Z]{16}', content):
            findings.append({
                "severity": "critical",
                "category": "secrets",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "AWS access key ID exposed",
                "risk": "AWS credentials compromised - potential account takeover",
                "recommended_fix": "Remove access key and use IAM roles instead"
            })
        
        # GitHub tokens
        if re.search(r'gh[ps]_[A-Za-z0-9_]{36,}', content):
            findings.append({
                "severity": "critical",
                "category": "secrets",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "GitHub token exposed",
                "risk": "GitHub access compromised - potential repository access",
                "recommended_fix": "Revoke token and use GitHub Apps or environment variables"
            })
        
        return findings
    
    def _check_db_credentials(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for database credentials"""
        findings = []
        
        # Database connection strings
        db_patterns = [
            r'mysql://.*:.*@',
            r'postgresql://.*:.*@',
            r'mongodb://.*:.*@'
        ]
        
        for pattern in db_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                findings.append({
                    "severity": "high",
                    "category": "secrets",
                    "file": file_path,
                    "lines": hunk["header"],
                    "what_changed": "Database connection string with embedded credentials",
                    "risk": "Database credentials exposed - unauthorized data access",
                    "recommended_fix": "Use environment variables or AWS Secrets Manager for DB credentials"
                })
        
        return findings
