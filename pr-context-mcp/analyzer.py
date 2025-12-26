#!/usr/bin/env python3
"""
PR Analyzer - Security and operational risk analysis
"""

import re
from typing import Dict, List, Any, Optional
import logging

from rules.iac_security import IaCSecurityRules
from rules.iam import IAMRules
from rules.networking import NetworkingRules
from rules.secrets import SecretsRules
from rules.ops import OperationalRules

logger = logging.getLogger(__name__)

class PRAnalyzer:
    def __init__(self):
        self.iac_security = IaCSecurityRules()
        self.iam_rules = IAMRules()
        self.networking_rules = NetworkingRules()
        self.secrets_rules = SecretsRules()
        self.ops_rules = OperationalRules()
        self.iam_rules = IAMRules()
        self.networking_rules = NetworkingRules()
        self.secrets_rules = SecretsRules()
        self.ops_rules = OperationalRules()
    
    async def analyze_pr(self, repo: str, pr_number: int, diff: str, changed_files: List[Dict], 
                        include_security: bool = True, include_operational_risk: bool = True, 
                        max_findings: int = 20) -> Dict[str, Any]:
        """Analyze PR diff for security and operational risks"""
        
        findings = []
        
        # Check if we have IaC files to determine if security analysis should run
        iac_extensions = {'.yaml', '.yml', '.json', '.tf', '.py', '.js', '.ts'}
        iac_keywords = {'cloudformation', 'terraform', 'cdk', 'infrastructure', 'template', 'stack'}
        
        has_iac_files = False
        for file_info in changed_files:
            file_path = file_info.get('path', '').lower()
            # Check file extension
            if any(file_path.endswith(ext) for ext in iac_extensions):
                # Check if it's likely IaC content
                if any(keyword in file_path for keyword in iac_keywords):
                    has_iac_files = True
                    break
                # Check for common IaC directories
                if any(dir_name in file_path for dir_name in ['infrastructure', 'iac', 'cloudformation', 'terraform', 'cdk']):
                    has_iac_files = True
                    break
        
        # Parse diff into file hunks
        file_hunks = self._parse_diff(diff)
        
        # Only run security analysis if IaC files are present
        run_security_analysis = has_iac_files and include_security
        run_operational_analysis = has_iac_files and include_operational_risk
        
        # Analyze each file
        for file_path, hunks in file_hunks.items():
            file_findings = []
            
            if run_security_analysis:
                # Security analysis
                file_findings.extend(self.iac_security.analyze_file(file_path, hunks))
                file_findings.extend(self.iam_rules.analyze_file(file_path, hunks))
                file_findings.extend(self.networking_rules.analyze_file(file_path, hunks))
                file_findings.extend(self.secrets_rules.analyze_file(file_path, hunks))
            
            if run_operational_analysis:
                # Operational risk analysis
                file_findings.extend(self.ops_rules.analyze_file(file_path, hunks))
            
            findings.extend(file_findings)
        
        # Sort by severity and limit findings
        findings.sort(key=lambda x: self._severity_weight(x["severity"]), reverse=True)
        findings = findings[:max_findings]
        
        # Generate summary and approval considerations
        summary = self._generate_summary(changed_files, findings, has_iac_files)
        approval_considerations = self._generate_approval_considerations(findings)
        
        # Calculate stats
        stats = {
            "files_changed": len(changed_files),
            "additions": sum(f.get("additions", 0) for f in changed_files),
            "deletions": sum(f.get("deletions", 0) for f in changed_files),
            "has_iac_files": has_iac_files
        }
        
        return {
            "summary": summary,
            "approval_considerations": approval_considerations,
            "findings": findings,
            "stats": stats
        }
    
    def _parse_diff(self, diff: str) -> Dict[str, List[Dict]]:
        """Parse unified diff into file hunks"""
        file_hunks = {}
        current_file = None
        current_hunk = None
        
        for line in diff.split('\n'):
            # File header
            if line.startswith('diff --git'):
                current_file = None
                current_hunk = None
            elif line.startswith('+++'):
                # Extract file path
                match = re.match(r'\+\+\+ b/(.+)', line)
                if match:
                    current_file = match.group(1)
                    file_hunks[current_file] = []
            elif line.startswith('@@'):
                # Hunk header
                if current_file:
                    match = re.match(r'@@ -(\d+),?\d* \+(\d+),?\d* @@(.*)', line)
                    if match:
                        current_hunk = {
                            "header": line,
                            "old_start": int(match.group(1)),
                            "new_start": int(match.group(2)),
                            "context": match.group(3).strip(),
                            "lines": []
                        }
                        file_hunks[current_file].append(current_hunk)
            elif current_hunk is not None:
                # Hunk content
                current_hunk["lines"].append(line)
        
        return file_hunks
    
    def _severity_weight(self, severity: str) -> int:
        """Convert severity to numeric weight for sorting"""
        weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return weights.get(severity.lower(), 0)
    
    def _generate_summary(self, changed_files: List[Dict], findings: List[Dict], has_iac_files: bool) -> str:
        """Generate human-readable summary with file details"""
        file_count = len(changed_files)
        finding_count = len(findings)
        
        # Generate file-by-file summary
        file_summaries = []
        for file_info in changed_files:
            path = file_info.get('path', 'unknown')
            status = file_info.get('status', 'unknown')
            additions = file_info.get('additions', 0)
            deletions = file_info.get('deletions', 0)
            
            # Determine file type and purpose
            file_type = self._classify_file_type(path)
            
            if status == 'added':
                summary = f"➕ **{path}** - New {file_type} (+{additions} lines)"
            elif status == 'removed':
                summary = f"➖ **{path}** - Deleted {file_type} (-{deletions} lines)"
            elif status == 'modified':
                summary = f"📝 **{path}** - Modified {file_type} (+{additions}/-{deletions} lines)"
            else:
                summary = f"🔄 **{path}** - {status.title()} {file_type}"
            
            file_summaries.append(summary)
        
        # Build main summary
        summary_parts = [
            f"PR modifies {file_count} files with {finding_count} security/operational findings."
        ]
        
        # Add file details
        if file_summaries:
            summary_parts.append("\\n\\n**File Changes:**")
            summary_parts.extend(file_summaries)
        
        # Add security analysis note
        if has_iac_files:
            summary_parts.append("\\n\\n*Security analysis performed on Infrastructure as Code files.*")
        else:
            summary_parts.append("\\n\\n*No Infrastructure as Code files detected - security analysis skipped.*")
        
        return "\\n".join(summary_parts)
    
    def _classify_file_type(self, path: str) -> str:
        """Classify file type based on path and extension"""
        path_lower = path.lower()
        
        if path_lower.endswith(('.yaml', '.yml')):
            if any(keyword in path_lower for keyword in ['cloudformation', 'template', 'stack']):
                return "CloudFormation template"
            elif 'workflow' in path_lower or '.github' in path_lower:
                return "GitHub Actions workflow"
            else:
                return "YAML configuration"
        elif path_lower.endswith('.json'):
            if 'task' in path_lower:
                return "ECS task definition"
            elif 'policy' in path_lower:
                return "IAM policy"
            else:
                return "JSON configuration"
        elif path_lower.endswith('.py'):
            return "Python script"
        elif path_lower.endswith('.js'):
            return "JavaScript file"
        elif path_lower.endswith('.ts'):
            return "TypeScript file"
        elif path_lower.endswith('.tf'):
            return "Terraform configuration"
        elif path_lower.endswith('.md'):
            return "documentation"
        elif path_lower.endswith('dockerfile'):
            return "Docker configuration"
        elif 'requirements.txt' in path_lower:
            return "Python dependencies"
        elif '.github/workflows' in path_lower:
            return "GitHub Actions workflow"
        elif 'infrastructure' in path_lower:
            return "infrastructure configuration"
        else:
            return "file"
    
    def _generate_approval_considerations(self, findings: List[Dict]) -> List[str]:
        """Generate approval considerations based on findings"""
        considerations = []
        
        # Group findings by category
        categories = {}
        for finding in findings:
            category = finding["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(finding)
        
        # Generate considerations per category
        if "iam" in categories:
            iam_findings = categories["iam"]
            critical_iam = [f for f in iam_findings if f["severity"] in ["critical", "high"]]
            if critical_iam:
                considerations.append("Review IAM permissions carefully - overly broad permissions detected")
        
        if "network" in categories:
            net_findings = categories["network"]
            public_exposure = [f for f in net_findings if "public" in f["risk"].lower()]
            if public_exposure:
                considerations.append("Verify public network exposure is intentional and properly secured")
        
        if "secrets" in categories:
            considerations.append("Ensure no secrets or credentials are exposed in the changes")
        
        if "ops" in categories:
            ops_findings = categories["ops"]
            deletion_protection = [f for f in ops_findings if "deletion" in f["risk"].lower()]
            if deletion_protection:
                considerations.append("Consider data protection implications of disabling safeguards")
        
        if not considerations:
            considerations.append("Standard code review practices apply")
        
        return considerations
