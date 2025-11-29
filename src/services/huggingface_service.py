"""
HuggingFace model ingestion service.
Downloads full model packages from HuggingFace Hub.
"""
import os
import shutil
import tempfile
import zipfile
import logging
import json
from typing import Dict, Optional, Tuple, List
from huggingface_hub import snapshot_download, model_info, dataset_info
from huggingface_hub.utils import HfHubHTTPError, RepositoryNotFoundError

logger = logging.getLogger(__name__)


class HuggingFaceIngestionService:
    """Service for ingesting HuggingFace models and datasets."""

    @staticmethod
    def download_model(model_id: str, cache_dir: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Download a complete HuggingFace model package.

        Args:
            model_id: HuggingFace model identifier (e.g., "gpt2", "facebook/bart-large")
            cache_dir: Optional cache directory for downloads

        Returns:
            Tuple of (local_path, metadata_dict)

        Raises:
            ValueError: If model not found or download fails
        """
        try:
            logger.info(f"Fetching metadata for model: {model_id}")

            # Get model info first to validate it exists and get metadata
            info = model_info(model_id)

            logger.info(f"Downloading model: {model_id}")

            # Download the full model snapshot
            # This downloads all files: model weights, config, tokenizer, etc.
            local_path = snapshot_download(
                repo_id=model_id,
                cache_dir=cache_dir,
                repo_type="model"
            )

            logger.info(f"Model downloaded successfully to: {local_path}")

            # Extract metadata
            metadata = {
                "model_id": info.id,
                "author": info.author,
                "sha": info.sha,
                "last_modified": str(info.lastModified) if info.lastModified else None,
                "private": info.private,
                "disabled": info.disabled,
                "downloads": info.downloads,
                "likes": info.likes,
                "tags": info.tags,
                "pipeline_tag": info.pipeline_tag,
                "library_name": info.library_name,
                "model_card": info.cardData if hasattr(info, 'cardData') else None,
            }

            return local_path, metadata

        except RepositoryNotFoundError:
            logger.error(f"Model not found: {model_id}")
            raise ValueError(f"Model '{model_id}' not found on HuggingFace Hub")
        except HfHubHTTPError as e:
            logger.error(f"HTTP error downloading model: {e}")
            raise ValueError(f"Failed to download model '{model_id}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error downloading model: {e}")
            raise ValueError(f"Failed to download model '{model_id}': {str(e)}")

    @staticmethod
    def download_dataset(dataset_id: str, cache_dir: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Download a complete HuggingFace dataset package.

        Args:
            dataset_id: HuggingFace dataset identifier
            cache_dir: Optional cache directory for downloads

        Returns:
            Tuple of (local_path, metadata_dict)

        Raises:
            ValueError: If dataset not found or download fails
        """
        try:
            logger.info(f"Fetching metadata for dataset: {dataset_id}")

            # Get dataset info first
            info = dataset_info(dataset_id)

            logger.info(f"Downloading dataset: {dataset_id}")

            # Download the full dataset snapshot
            local_path = snapshot_download(
                repo_id=dataset_id,
                cache_dir=cache_dir,
                repo_type="dataset"
            )

            logger.info(f"Dataset downloaded successfully to: {local_path}")

            # Extract metadata
            metadata = {
                "dataset_id": info.id,
                "author": info.author,
                "sha": info.sha,
                "last_modified": str(info.lastModified) if info.lastModified else None,
                "private": info.private,
                "disabled": info.disabled,
                "downloads": info.downloads,
                "likes": info.likes,
                "tags": info.tags,
            }

            return local_path, metadata

        except RepositoryNotFoundError:
            logger.error(f"Dataset not found: {dataset_id}")
            raise ValueError(f"Dataset '{dataset_id}' not found on HuggingFace Hub")
        except HfHubHTTPError as e:
            logger.error(f"HTTP error downloading dataset: {e}")
            raise ValueError(f"Failed to download dataset '{dataset_id}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error downloading dataset: {e}")
            raise ValueError(f"Failed to download dataset '{dataset_id}': {str(e)}")

    @staticmethod
    def create_package_zip(source_dir: str, output_path: str) -> int:
        """
        Create a zip file from a directory.

        Args:
            source_dir: Directory to zip
            output_path: Output zip file path

        Returns:
            Size of the created zip file in bytes
        """
        logger.info(f"Creating zip package: {output_path}")

        # Count total files for progress tracking
        total_files = sum(len(files) for _, _, files in os.walk(source_dir))
        logger.info(f"Archiving {total_files} files...")

        # Use ZIP_STORED (no compression) for faster archiving of large model files
        # Model binaries are already optimized and don't compress well anyway
        file_count = 0
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    file_count += 1
                    # Log progress every 5 files
                    if file_count % 5 == 0 or file_count == total_files:
                        logger.info(f"Archived {file_count}/{total_files} files ({file_count*100//total_files}%)")

        size_bytes = os.path.getsize(output_path)
        logger.info(f"Zip package created: {size_bytes} bytes")

        return size_bytes

    @staticmethod
    def get_model_url(model_id: str) -> str:
        """
        Generate HuggingFace model URL from model ID.

        Args:
            model_id: HuggingFace model identifier

        Returns:
            Full URL to the model on HuggingFace
        """
        return f"https://huggingface.co/{model_id}"

    @staticmethod
    def get_dataset_url(dataset_id: str) -> str:
        """
        Generate HuggingFace dataset URL from dataset ID.

        Args:
            dataset_id: HuggingFace dataset identifier

        Returns:
            Full URL to the dataset on HuggingFace
        """
        return f"https://huggingface.co/datasets/{dataset_id}"

    @staticmethod
    def parse_model_name_version(model_id: str) -> Tuple[str, str]:
        """
        Parse model ID into name and version.

        For models like "gpt2", we use the model_id as name and "1.0.0" as default version.
        For models with versions in tags, we try to extract them.

        Args:
            model_id: HuggingFace model identifier

        Returns:
            Tuple of (name, version)
        """
        # For now, use simple strategy:
        # - Name is the model_id with '/' replaced by '-'
        # - Version defaults to "1.0.0" unless we can extract from metadata

        name = model_id.replace('/', '-')
        version = "1.0.0"  # Default version

        return name, version

    @staticmethod
    def extract_parent_models(model_path: str, metadata: Dict) -> List[str]:
        """
        Extract parent model references from HuggingFace model metadata.

        Looks for parent models in:
        1. config.json - "base_model", "_name_or_path", "model_name_or_path"
        2. Model card data - "base_model"
        3. Tags - "adapter" models reference base models

        Args:
            model_path: Local path to downloaded model
            metadata: Model metadata from HuggingFace Hub

        Returns:
            List of parent model IDs (e.g., ["bert-base-uncased", "gpt2"])
        """
        parent_models = []

        # 1. Check config.json for parent model references
        config_path = os.path.join(model_path, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                # Common fields that reference parent models
                parent_fields = [
                    "base_model",
                    "_name_or_path",
                    "model_name_or_path",
                    "base_model_name_or_path",
                ]

                for field in parent_fields:
                    if field in config:
                        parent_ref = config[field]
                        # Skip local paths or invalid references
                        if isinstance(parent_ref, str) and '/' in parent_ref and not parent_ref.startswith('.'):
                            # Clean up the reference (remove version tags, etc.)
                            parent_ref = parent_ref.strip()
                            # Skip if it's a local path
                            if not os.path.exists(parent_ref):
                                parent_models.append(parent_ref)
                                logger.info(f"Found parent model in config.json [{field}]: {parent_ref}")

            except Exception as e:
                logger.warning(f"Failed to parse config.json: {e}")

        # 2. Check model card data from metadata
        if metadata.get("model_card"):
            card_data = metadata["model_card"]
            if isinstance(card_data, dict) and "base_model" in card_data:
                base_model = card_data["base_model"]
                if isinstance(base_model, str):
                    parent_models.append(base_model)
                    logger.info(f"Found parent model in card data: {base_model}")
                elif isinstance(base_model, list):
                    parent_models.extend(base_model)
                    logger.info(f"Found parent models in card data: {base_model}")

        # 3. Check README.md for parent model references (YAML frontmatter)
        readme_path = os.path.join(model_path, "README.md")
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for YAML frontmatter
                if content.startswith('---'):
                    # Extract YAML frontmatter (between first two --- markers)
                    parts = content.split('---', 2)
                    if len(parts) >= 2:
                        import yaml
                        try:
                            frontmatter = yaml.safe_load(parts[1])
                            if isinstance(frontmatter, dict):
                                # Check for base_model field
                                if "base_model" in frontmatter:
                                    base_model = frontmatter["base_model"]
                                    if isinstance(base_model, str):
                                        parent_models.append(base_model)
                                        logger.info(f"Found parent model in README frontmatter: {base_model}")
                                    elif isinstance(base_model, list):
                                        parent_models.extend(base_model)
                                        logger.info(f"Found parent models in README frontmatter: {base_model}")
                        except Exception as e:
                            logger.debug(f"Could not parse YAML frontmatter: {e}")

            except Exception as e:
                logger.warning(f"Failed to parse README.md: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_parents = []
        for parent in parent_models:
            if parent and parent not in seen:
                seen.add(parent)
                unique_parents.append(parent)

        if unique_parents:
            logger.info(f"Extracted {len(unique_parents)} parent model(s): {unique_parents}")
        else:
            logger.info("No parent models found in metadata")

        return unique_parents


# Global instance
hf_service = HuggingFaceIngestionService()