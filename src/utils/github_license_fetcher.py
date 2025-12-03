"""
GitHub License Fetcher for Model Registry.
Fetches license information from GitHub repositories.
"""

import requests
import logging
from typing import Optional, Dict, Any
import re

logger = logging.getLogger(__name__)


class GitHubLicenseFetcher:
    """
    Fetches license information from GitHub repositories.
    Uses the GitHub API to retrieve license data.
    """

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub license fetcher.

        Args:
            github_token: Optional GitHub personal access token for higher rate limits
        """
        self.github_token = github_token
        self.session = requests.Session()

        if github_token:
            self.session.headers.update(
                {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
        else:
            self.session.headers.update({"Accept": "application/vnd.github.v3+json"})

    def extract_repo_from_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extract owner and repo name from a GitHub URL.

        Args:
            url: GitHub URL (e.g., https://github.com/owner/repo)

        Returns:
            Dict with "owner" and "repo" or None if invalid
        """
        # Handle various GitHub URL formats
        patterns = [
            r"github\.com/([^/]+)/([^/\.]+)",  # https://github.com/owner/repo
            r"github\.com/([^/]+)/([^/]+)\.git",  # https://github.com/owner/repo.git
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return {
                    "owner": match.group(1),
                    "repo": match.group(2).replace(".git", ""),
                }

        logger.warning(f"Could not extract repo info from URL: {url}")
        return None

    def get_license_from_repo(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """
        Fetch license information from a GitHub repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dict containing license information or None:
            {
                "license": str,  # License identifier (e.g., "MIT", "Apache-2.0")
                "name": str,     # Full license name
                "url": str,      # License URL
                "spdx_id": str   # SPDX identifier
            }
        """
        url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}"

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 404:
                logger.warning(f"Repository not found: {owner}/{repo}")
                return None
            elif response.status_code == 403:
                logger.error(f"GitHub API rate limit exceeded or access denied")
                return None
            elif response.status_code != 200:
                logger.error(
                    f"GitHub API error {response.status_code}: {response.text}"
                )
                return None

            data = response.json()

            if "license" in data and data["license"]:
                license_data = data["license"]
                return {
                    "license": license_data.get("key", "unknown"),
                    "name": license_data.get("name", "Unknown"),
                    "url": license_data.get("url", ""),
                    "spdx_id": license_data.get("spdx_id", "NOASSERTION"),
                }
            else:
                logger.info(f"No license information found for {owner}/{repo}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching license for {owner}/{repo}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching license for {owner}/{repo}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching license: {e}")
            return None

    def get_license_from_url(self, github_url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch license information from a GitHub URL.

        Args:
            github_url: GitHub repository URL

        Returns:
            License information dict or None
        """
        repo_info = self.extract_repo_from_url(github_url)
        if not repo_info:
            return None

        return self.get_license_from_repo(repo_info["owner"], repo_info["repo"])

    def check_compatibility_with_github(
        self, project_license: str, github_url: str
    ) -> Dict[str, Any]:
        """
        Check if a project license is compatible with a GitHub repository's license.

        Args:
            project_license: License of the project
            github_url: GitHub repository URL to check against

        Returns:
            Dict with compatibility results:
            {
                "compatible": bool,
                "github_license": str,
                "reason": str
            }
        """
        from src.utils.license_compatibility import license_checker

        # Fetch GitHub license
        github_license_info = self.get_license_from_url(github_url)

        if not github_license_info:
            return {
                "compatible": None,
                "github_license": "unknown",
                "reason": "Could not fetch license from GitHub repository",
            }

        github_license = github_license_info["license"]

        # Check compatibility
        is_compatible, reason = license_checker.are_compatible(
            project_license, github_license
        )

        return {
            "compatible": is_compatible,
            "github_license": github_license,
            "github_license_name": github_license_info["name"],
            "spdx_id": github_license_info["spdx_id"],
            "reason": reason,
        }


# Global instance (without token by default)
github_license_fetcher = GitHubLicenseFetcher()
