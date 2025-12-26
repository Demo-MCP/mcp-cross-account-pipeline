#!/usr/bin/env python3
"""
Checkov Security Scanner Integration
"""

import json
import os
import subprocess
import tempfile
from typing import Dict, List, Any, Optional

class CheckovScanner:
    def __init__(self):
        self.checkov_available = self._check_checkov_installed()
    
    def _check_checkov_installed(self) -> bool:
        """Check if Checkov is available"""
        try:
            subprocess.run(['checkov', '--version'], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False
    
    def scan_template(self, template_content: str, file_path: str) -> Dict[str, Any]:
        """Scan CloudFormation template with Checkov"""
        if not self.checkov_available:
            return {
                "error": "Checkov not available - install with: pip install checkov",
                "findings": []
            }
        
        # Write template to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_file.write(template_content)
            temp_file_path = temp_file.name
        
        try:
            # Run Checkov
            cmd = ['checkov', '-f', temp_file_path, '--framework', 'cloudformation', '--output', 'json']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.stdout:
                checkov_results = json.loads(result.stdout)
                return self._parse_checkov_results(checkov_results, file_path)
            else:
                return {"error": "No Checkov output", "findings": []}
                
        except Exception as e:
            return {"error": f"Checkov scan failed: {str(e)}", "findings": []}
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def _parse_checkov_results(self, checkov_results: Dict, file_path: str) -> Dict[str, Any]:
        """Parse Checkov results into our format"""
        findings = []
        
        # Extract failed checks
        results = checkov_results.get("results", {})
        failed_checks = results.get("failed_checks", [])
        
        for check in failed_checks:
            severity = self._map_severity(check.get("severity", "MEDIUM"))
            
            finding = {
                "severity": severity,
                "category": "security",
                "file": file_path,
                "check_id": check.get("check_id", ""),
                "check_name": check.get("check_name", ""),
                "what_changed": check.get("check_name", "Security check failed"),
                "risk": check.get("description", "Security vulnerability detected"),
                "recommended_fix": check.get("guideline", "Review and fix security issue"),
                "resource": check.get("resource", ""),
                "line_range": check.get("file_line_range", [])
            }
            findings.append(finding)
        
        # Summary
        summary = results.get("summary", {})
        
        return {
            "findings": findings,
            "summary": {
                "total_checks": summary.get("passed", 0) + summary.get("failed", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0)
            }
        }
    
    def _map_severity(self, checkov_severity: str) -> str:
        """Map Checkov severity to our format"""
        severity_map = {
            "CRITICAL": "critical",
            "HIGH": "high", 
            "MEDIUM": "medium",
            "LOW": "low"
        }
        return severity_map.get(checkov_severity.upper() if checkov_severity else "MEDIUM", "medium")
    
    def format_security_card(self, scan_results: Dict, file_path: str) -> str:
        """Format Checkov results as security card"""
        if "error" in scan_results:
            return f"⚠️ **Security Scan Error**: {scan_results['error']}"
        
        findings = scan_results.get("findings", [])
        summary = scan_results.get("summary", {})
        
        if not findings:
            return f"✅ **Security Scan Passed**: {summary.get('total_checks', 0)} checks passed"
        
        # Group by severity
        critical = [f for f in findings if f["severity"] == "critical"]
        high = [f for f in findings if f["severity"] == "high"]
        medium = [f for f in findings if f["severity"] == "medium"]
        low = [f for f in findings if f["severity"] == "low"]
        
        card_parts = [f"🔒 **Checkov Security Scan for {file_path}**"]
        
        if critical:
            card_parts.append(f"🚨 **Critical Issues ({len(critical)}):**")
            for finding in critical[:3]:  # Show top 3
                card_parts.append(f"  • {finding['check_name']}")
        
        if high:
            card_parts.append(f"⚠️ **High Issues ({len(high)}):**")
            for finding in high[:3]:  # Show top 3
                card_parts.append(f"  • {finding['check_name']}")
        
        if medium:
            card_parts.append(f"📋 **Medium Issues ({len(medium)}):**")
            for finding in medium[:3]:  # Show top 3
                card_parts.append(f"  • {finding['check_name']}")
        
        if low:
            card_parts.append(f"📝 **Low Issues ({len(low)}):**")
            for finding in low[:2]:  # Show top 2
                card_parts.append(f"  • {finding['check_name']}")
        
        # Summary
        total_failed = summary.get("failed", len(findings))
        total_passed = summary.get("passed", 0)
        card_parts.append(f"\\n**Summary**: {total_failed} failed, {total_passed} passed")
        
        if critical or high:
            card_parts.append("\\n🔒 **Security Review Required**: Critical/High issues found")
        
        return "\\n".join(card_parts)
