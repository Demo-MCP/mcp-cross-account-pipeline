#!/usr/bin/env python3
"""
Operational Risk Rules
"""

import re
from typing import List, Dict, Any

class OperationalRules:
    def analyze_file(self, file_path: str, hunks: List[Dict]) -> List[Dict]:
        """Analyze for operational risks"""
        findings = []
        
        for hunk in hunks:
            for line in hunk["lines"]:
                if line.startswith('+'):  # Only check added lines
                    content = line[1:].strip()
                    
                    # Check for deletion protection
                    findings.extend(self._check_deletion_protection(file_path, hunk, content))
                    
                    # Check for backup settings
                    findings.extend(self._check_backup_settings(file_path, hunk, content))
                    
                    # Check for monitoring
                    findings.extend(self._check_monitoring(file_path, hunk, content))
        
        return findings
    
    def _check_deletion_protection(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for deletion protection settings"""
        findings = []
        
        # Deletion protection disabled
        if re.search(r'DeletionProtection.*false|TerminationProtection.*false', content, re.IGNORECASE):
            findings.append({
                "severity": "medium",
                "category": "ops",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "Deletion protection disabled",
                "risk": "Resource can be accidentally deleted - potential data loss",
                "recommended_fix": "Enable deletion protection for critical resources"
            })
        
        return findings
    
    def _check_backup_settings(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for backup and retention settings"""
        findings = []
        
        # Backup disabled
        if re.search(r'BackupRetentionPeriod.*0|AutomatedBackupRetentionPeriod.*0', content, re.IGNORECASE):
            findings.append({
                "severity": "high",
                "category": "ops",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "Automated backups disabled",
                "risk": "No backup recovery option - potential permanent data loss",
                "recommended_fix": "Enable automated backups with appropriate retention period"
            })
        
        # Short retention periods
        retention_match = re.search(r'RetentionPeriod.*([1-6])\b', content, re.IGNORECASE)
        if retention_match:
            days = int(retention_match.group(1))
            findings.append({
                "severity": "medium",
                "category": "ops",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": f"Backup retention set to {days} days",
                "risk": "Short retention period may not meet recovery requirements",
                "recommended_fix": "Consider longer retention period based on business needs"
            })
        
        return findings
    
    def _check_monitoring(self, file_path: str, hunk: Dict, content: str) -> List[Dict]:
        """Check for monitoring and alerting configurations"""
        findings = []
        
        # Monitoring disabled
        if re.search(r'MonitoringInterval.*0|EnablePerformanceInsights.*false', content, re.IGNORECASE):
            findings.append({
                "severity": "low",
                "category": "ops",
                "file": file_path,
                "lines": hunk["header"],
                "what_changed": "Performance monitoring disabled",
                "risk": "Limited visibility into resource performance and issues",
                "recommended_fix": "Enable monitoring for better operational visibility"
            })
        
        return findings
