#!/usr/bin/env python3
"""
GitHub Client with secure authentication
Handles GitHub API calls without exposing tokens to broker
"""

import os
import re
import json
import time
import boto3
import requests
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from cachetools import TTLCache
import logging

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PR-Context-MCP/1.0"
        })
        
        # Token cache (5 minute TTL for GitHub App tokens)
        self.token_cache = TTLCache(maxsize=10, ttl=300)
        
        # Repository allowlist from environment
        allowlist_env = os.environ.get("ALLOWLIST_REPOS", "Demo-MCP/*")
        self.repo_allowlist = [pattern.strip() for pattern in allowlist_env.split(",")]
        logger.info(f"Repository allowlist: {self.repo_allowlist}")
        
        # GitHub authentication method
        self.auth_method = os.environ.get("GITHUB_AUTH_METHOD", "app")  # "app" or "pat"
        
    def is_repo_allowed(self, repo: str) -> bool:
        """Check if repository is in allowlist"""
        for pattern in self.repo_allowlist:
            if self._match_repo_pattern(pattern, repo):
                return True
        return False
    
    def _match_repo_pattern(self, pattern: str, repo: str) -> bool:
        """Match repository against pattern (supports wildcards)"""
        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*").replace("?", ".")
        return bool(re.match(f"^{regex_pattern}$", repo, re.IGNORECASE))
    
    async def get_access_token(self, repo: str) -> str:
        """Get GitHub access token (cached)"""
        cache_key = f"token_{repo}"
        
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        if self.auth_method == "app":
            token = await self._get_github_app_token(repo)
        else:
            token = await self._get_pat_token()
        
        self.token_cache[cache_key] = token
        return token
    
    async def _get_github_app_token(self, repo: str) -> str:
        """Get GitHub App installation token"""
        try:
            # Get GitHub App credentials from Secrets Manager
            secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
            
            secret_response = secrets_client.get_secret_value(
                SecretId=os.environ.get("GITHUB_APP_SECRET", "github-app-credentials")
            )
            
            credentials = json.loads(secret_response['SecretString'])
            app_id = credentials['app_id']
            private_key = credentials['private_key']
            
            # Generate JWT for GitHub App
            now = int(time.time())
            payload = {
                'iat': now - 60,  # Issued 1 minute ago
                'exp': now + 600,  # Expires in 10 minutes
                'iss': app_id
            }
            
            jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
            
            # Get installation ID for the repository
            org = repo.split('/')[0]
            
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # List installations
            response = requests.get(
                "https://api.github.com/app/installations",
                headers=headers
            )
            response.raise_for_status()
            
            installations = response.json()
            installation_id = None
            
            for installation in installations:
                if installation['account']['login'].lower() == org.lower():
                    installation_id = installation['id']
                    break
            
            if not installation_id:
                raise ValueError(f"No GitHub App installation found for organization: {org}")
            
            # Get installation access token
            response = requests.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers=headers
            )
            response.raise_for_status()
            
            token_data = response.json()
            return token_data['token']
            
        except Exception as e:
            logger.error(f"Failed to get GitHub App token: {e}")
            raise ValueError(f"GitHub authentication failed: {e}")
    
    async def _get_pat_token(self) -> str:
        """Get Personal Access Token from environment or Secrets Manager"""
        # Check for local environment variable first (for testing)
        local_token = os.environ.get("GITHUB_TOKEN")
        if local_token:
            return local_token
            
        try:
            secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
            
            secret_response = secrets_client.get_secret_value(
                SecretId=os.environ.get("GITHUB_PAT_SECRET", "github-pat-token")
            )
            
            return secret_response['SecretString']
            
        except Exception as e:
            logger.error(f"Failed to get GitHub PAT: {e}")
            raise ValueError(f"GitHub authentication failed: {e}")
    
    async def get_pr_diff(self, repo: str, pr_number: int, max_diff_bytes: int = 1500000, max_files: int = 200) -> Dict[str, Any]:
        """Get PR diff and changed files from GitHub API"""
        try:
            token = await self.get_access_token(repo)
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get PR basic info
            pr_response = requests.get(
                f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
                headers=headers
            )
            pr_response.raise_for_status()
            pr_data = pr_response.json()
            
            # Get PR files (paginated)
            changed_files = []
            page = 1
            
            while len(changed_files) < max_files:
                files_response = requests.get(
                    f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files",
                    headers=headers,
                    params={"page": page, "per_page": 100}
                )
                files_response.raise_for_status()
                files_data = files_response.json()
                
                if not files_data:
                    break
                
                for file_data in files_data:
                    if len(changed_files) >= max_files:
                        break
                    
                    changed_files.append({
                        "path": file_data["filename"],
                        "status": file_data["status"],
                        "additions": file_data["additions"],
                        "deletions": file_data["deletions"]
                    })
                
                page += 1
            
            # Get PR diff
            diff_headers = headers.copy()
            diff_headers["Accept"] = "application/vnd.github.v3.diff"
            
            diff_response = requests.get(
                f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
                headers=diff_headers
            )
            diff_response.raise_for_status()
            
            diff_text = diff_response.text
            diff_truncated = False
            
            # Truncate if too large
            if len(diff_text.encode('utf-8')) > max_diff_bytes:
                # Truncate at character boundary
                truncated_bytes = diff_text.encode('utf-8')[:max_diff_bytes]
                diff_text = truncated_bytes.decode('utf-8', errors='ignore')
                diff_truncated = True
            
            return {
                "repo": repo,
                "pr_number": pr_number,
                "base_sha": pr_data["base"]["sha"],
                "head_sha": pr_data["head"]["sha"],
                "changed_files": changed_files,
                "diff": diff_text,
                "diff_truncated": diff_truncated
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            raise ValueError(f"Failed to fetch PR data: {e}")
        except Exception as e:
            logger.error(f"Error getting PR diff: {e}")
            raise ValueError(f"Failed to get PR diff: {e}")
