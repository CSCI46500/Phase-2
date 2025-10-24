import requests
import re
from typing import Optional, Dict
from huggingface_hub import HfApi, ModelInfo
from strip import strip_html, strip_markdown
from datetime import datetime, timedelta

class Model:
    def __init__(self, code_url: str, dataset_url:str , model_url:str):
        self.code_url: str = code_url
        self.dataset_url: str = dataset_url
        self.model_url: str = model_url
        self.model_name: str = self.get_name(model_url, "model")

        self.file_size_types: tuple[str, ...] = (".bin", ".safetensors")
        self.metadata: Optional[ModelInfo] = None
        self.api = HfApi()

        self.code_dict: Dict[str, str] = {
            "name": self.get_name(code_url, "code"),
            "url": self.code_url,
            "type": "code"}
        
        self.dataset_dict: Dict[str, str] = {
            "name": self.get_name(dataset_url, "dataset"),
            "url": self.dataset_url,
            "type": "dataset"}
        
        self.model_full_repo, name = self.get_name(model_url, "model")
        self.model_dict: Dict[str, str] = {
            "name": name,
            "url": self.model_url,
            "type": "model"}

        self.datasets: list[str] = []
        if dataset_url:
            self.add_dataset(dataset_url)

        self.fetch_metadata()

    # Extract name from URL
    def get_name(self, url: str, type: str) -> tuple[str, str]:
        if not url:
            return "", ""

        url = url.rstrip("/")

        if type == "code":
            name = url.split("github.com/")[-1].replace("tree/main", "").strip("/")
            return name, name.split("/")[-1]
        elif type == "model":
            full_repo = url.split("huggingface.co/")[-1].replace("/tree/main", "").strip("/")
            name = full_repo.split("/")[-1]
            return full_repo, name
        elif type == "dataset":
            if "huggingface.co" in url:
                full_repo = url.split("huggingface.co/datasets")[-1].replace("/tree/main", "").strip("/")
            else:
                full_repo = url.split("/")[-1]
            name = full_repo.split("/")[-1]
            return full_repo, name

        return "unknown"

    # HF API fetch
    def fetch_metadata(self) -> None:
        try:
            self.metadata = self.api.model_info(self.model_full_repo)
        except Exception as e:
            print(f"Error fetching metadata for {self.model_name}: {e}")
            self.metadata = None

    # README raw text data
    def fetch_readme(self, url_type: str) -> str:
        readme_text = ""
        readme_url = ""

        url_map = {
            "code": self.code_url,
            "dataset": self.dataset_url,
            "model": self.model_url,
        }

        url = url_map.get(url_type)
        if not url:
            return ""

        if url_type in ["model", "dataset"] and "huggingface.co" in url:
            if self.metadata and getattr(self.metadata, "cardData", None):
                readme_text = self.metadata.cardData.get("readme", "")
                if readme_text:
                    # Strip HTML/Markdown
                    clean_text = strip_html(readme_text)
                    clean_text = strip_markdown(clean_text)
                    return clean_text
        
        if "github.com" in url:
            readme_url = url.replace("tree/main", "raw/main/README.md")
        else:
            # External dataset / other sites
            readme_text = "External"
            return readme_text

        try:
            res = requests.get(readme_url, timeout=10)
            readme_text = res.text
            clean_text = strip_html(readme_text)
            clean_text = strip_markdown(clean_text)
            return clean_text
        except Exception as e:
            print(f"Error fetching readme: {e}")
            return ""

    # Model licenses
    def get_license(self) -> str:
        # First try Hugging Face metadata
        card_data = getattr(self.metadata, "cardData", None)
        if card_data:
            license_name = card_data.get("license_name") or card_data.get("license")
            if license_name:
                return license_name

        # Fall back to GitHub API if code_url is a repo
        if self.code_url and "github.com" in self.code_url:
            try:
                repo_url = self.code_url.replace("tree/main", "").rstrip("/")
                parts = repo_url.split("/")
                owner, repo = parts[-2], parts[-1]
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                res = requests.get(api_url, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("license", {}).get("name", "Unknown")
            except Exception as e:
                print(f"Error fetching GitHub license: {e}")

        return "Unknown"

    # Size of model
    def get_size(self) -> float:
        total_bytes = 0
        for f in getattr(self.metadata, "siblings", []):
            filename = getattr(f, "rfilename", "")
            if filename.endswith(self.file_size_types):
                file_url = f"{self.model_url}/resolve/main/{filename}"
                try:
                    res = requests.head(file_url, timeout=15, allow_redirects=True)
                    size = int(res.headers.get("Content-Length", 0) or 0)
                    total_bytes += size
                except Exception as e:
                    print(f"Error fetching size for {filename}: {e}")

        return total_bytes / (1024**3)

    # Check README for keywords
    def kw_check(self, kw: list[str], readme_type: str) -> bool:
        text = self.fetch_readme(readme_type).lower()
        if not text.strip() or text == "External":
            return False
        
        for k in kw:
            word = r"\b" + re.escape(k.lower()) + r"\b"
            if re.search(word, text):
                return True
            
        return False
    
    # Number of words in README
    def len_readme(self, readme_type: str) -> int:
        text = self.fetch_readme(readme_type)
        if not text or text == "External":
            return 0
        
        return len(text.split())

    # Add dataset url to list for tracking
    def add_dataset(self, dataset_url: str) -> None:
        if dataset_url and dataset_url not in self.datasets:
            self.datasets.append(dataset_url)

    # Check for last modified
    def last_modified(self, type: str, days: int) -> bool:
        if type == "huggingface":
            if not self.metadata or not getattr(self.metadata, "lastModified", None):
                return False
            date = datetime.fromisoformat(self.metadata.lastModified.replace("Z", "+00:00"))
            return datetime.now(date.tzinfo) - date < timedelta(days = days)
        elif type == "github":
            if not self.code_url or "github.com" not in self.code_url:
                return False

            try:
                parts = self.code_url.rstrip("/").split("/")
                owner = parts[-2]
                repo = parts[-1]
                api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"

                res = requests.get(api_url, timeout = 10)
                if res.status_code != 200:
                    return False

                data = res.json()
                if not data:
                    return False

                last_commit_date = datetime.fromisoformat(data[0]["commit"]["committer"]["date"].replace("Z", "+00:00"))
                return datetime.now(last_commit_date.tzinfo) - last_commit_date < timedelta(days = days)
            except Exception as e:
                print(f"Error checking GitHub last modified: {e}")
                return False
        
    # Get num of downloads
    def get_downloads(self) -> int:
        try:
            down = getattr(self.metadata, "downloads", 0)
            return down
        except Exception as e:
            print(f"Error fetching downloads: {e}")
            return 0
            
    # Get num of contributors
    def get_contrib(self) -> int:
        if not self.code_url or "github.com" not in self.code_url:
            return 0
        try:
            parts = self.code_url.rstrip("/").split("/")
            owner = parts[-2]
            repo = parts[-1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=100"

            res = requests.get(api_url, timeout=10)
            if res.status_code != 200:
                return 0

            data = res.json()
            return len(data)
        except Exception as e:
            print(f"Error fetching contributors: {e}")
            return 0

    # Get stats for GitHub stars and forks through GitHub API
    def get_git_stats(self) -> Dict[str, int]:
        if not self.code_url or "github.com" not in self.code_url:
            return {"stars": 0, "forks": 0}

        try:
            repo_url = self.code_url.replace("tree/main", "").replace("blob/main", "").rstrip("/")
            parts = repo_url.split("/")
            if len(parts) < 5:
                print(f"Invalid GitHub URL: {repo_url}")
                return {"stars": 0, "forks": 0}

            owner, repo = parts[-2], parts[-1]

            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            res = requests.get(api_url, timeout = 10)

            if res.status_code == 200:
                data = res.json()
                return {
                    "stars": data.get("stargazers_count", 0),
                    "forks": data.get("forks_count", 0)
                }
            else:
                print(f"GitHub API returned status {res.status_code}")
                return {"stars": 0, "forks": 0}

        except Exception as e:
            print(f"Error fetching GitHub stats: {e}")
            return {"stars": 0, "forks": 0}