"""
Lineage Parser for Model Registry.
Parses config.json and other metadata files to detect parent model relationships.
"""

import json
import zipfile
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class LineageParser:
    """
    Parses model packages to extract lineage information.
    Looks for parent model references in config.json and other metadata files.
    """

    # Common keys in config.json that might reference parent models
    PARENT_MODEL_KEYS = [
        "_name_or_path",  # HuggingFace models often use this
        "model_name_or_path",
        "base_model",
        "parent_model",
        "base_model_name_or_path",
        "pretrained_model_name_or_path",
    ]

    def __init__(self):
        """Initialize lineage parser."""
        pass

    def parse_zip_file(self, zip_path: str) -> Dict[str, Any]:
        """
        Parse a zip file to extract lineage information.

        Args:
            zip_path: Path to the zip file

        Returns:
            Dict containing lineage information:
            {
                "parent_models": List[str],  # List of parent model identifiers
                "relationship_type": str,    # Type of relationship
                "metadata": Dict             # Additional metadata
            }
        """
        result = {
            "parent_models": [],
            "relationship_type": "derived_from",
            "metadata": {},
        }

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Look for config.json
                config_data = self._find_and_parse_config(zf)
                if config_data:
                    result["metadata"]["config"] = config_data
                    parents = self._extract_parents_from_config(config_data)
                    result["parent_models"].extend(parents)

                # Look for model_card.md or README.md
                readme_data = self._find_and_parse_readme(zf)
                if readme_data:
                    result["metadata"]["readme"] = readme_data

        except zipfile.BadZipFile:
            logger.error(f"Invalid zip file: {zip_path}")
        except Exception as e:
            logger.error(f"Error parsing lineage from {zip_path}: {e}")

        logger.info(
            f"Parsed lineage from {zip_path}: found {len(result['parent_models'])} parent(s)"
        )
        return result

    def _find_and_parse_config(self, zf: zipfile.ZipFile) -> Optional[Dict[str, Any]]:
        """
        Find and parse config.json from the zip file.

        Args:
            zf: ZipFile object

        Returns:
            Parsed config dict or None
        """
        # Common locations for config.json
        config_paths = ["config.json", "model/config.json", "*/config.json"]

        for file_info in zf.namelist():
            if file_info.endswith("config.json"):
                try:
                    with zf.open(file_info) as f:
                        config_data = json.load(f)
                        logger.debug(f"Found config.json at {file_info}")
                        return config_data
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in {file_info}: {e}")
                except Exception as e:
                    logger.warning(f"Error reading {file_info}: {e}")

        return None

    def _find_and_parse_readme(self, zf: zipfile.ZipFile) -> Optional[str]:
        """
        Find and parse README.md or model_card.md from the zip file.

        Args:
            zf: ZipFile object

        Returns:
            README content or None
        """
        readme_files = ["README.md", "readme.md", "model_card.md", "MODEL_CARD.md"]

        for file_info in zf.namelist():
            if any(file_info.endswith(readme) for readme in readme_files):
                try:
                    with zf.open(file_info) as f:
                        content = f.read().decode("utf-8", errors="ignore")
                        logger.debug(f"Found README at {file_info}")
                        return content
                except Exception as e:
                    logger.warning(f"Error reading {file_info}: {e}")

        return None

    def _extract_parents_from_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Extract parent model identifiers from config.json.

        Args:
            config: Parsed config.json dict

        Returns:
            List of parent model identifiers
        """
        parents = []

        for key in self.PARENT_MODEL_KEYS:
            if key in config:
                value = config[key]
                if isinstance(value, str) and value:
                    # Filter out local paths and non-model references
                    if not self._is_local_path(value):
                        parents.append(value)
                        logger.debug(f"Found parent model in config['{key}']: {value}")

        # Remove duplicates while preserving order
        return list(dict.fromkeys(parents))

    def _is_local_path(self, path: str) -> bool:
        """
        Check if a string looks like a local file path rather than a model identifier.

        Args:
            path: String to check

        Returns:
            True if it looks like a local path
        """
        # Absolute paths
        if path.startswith("/") or path.startswith("\\"):
            return True

        # Relative paths
        if path.startswith("./") or path.startswith(".\\"):
            return True

        # Windows drive letters
        if len(path) >= 2 and path[1] == ":":
            return True

        # Very short strings are likely not model identifiers
        if len(path) < 3:
            return True

        return False

    def parse_huggingface_model_id(self, model_id: str) -> Dict[str, str]:
        """
        Parse a HuggingFace model ID into components.

        Args:
            model_id: HuggingFace model identifier (e.g., "bert-base-uncased" or "google/bert-base-uncased")

        Returns:
            Dict with parsed components: {"organization": str, "model": str, "full_id": str}
        """
        parts = model_id.strip().split("/")

        if len(parts) == 2:
            return {"organization": parts[0], "model": parts[1], "full_id": model_id}
        else:
            return {"organization": None, "model": model_id, "full_id": model_id}


# Global instance
lineage_parser = LineageParser()
