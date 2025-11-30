"""
Size Analyzer for Model Registry.
Analyzes package contents and calculates size breakdowns for different components.
"""

import zipfile
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class SizeAnalyzer:
    """
    Analyzes model packages to provide detailed size information.
    Breaks down package size by component type (model weights, code, data, etc.)
    """

    # File extensions categorization
    MODEL_WEIGHT_EXTENSIONS = {
        ".bin",
        ".pt",
        ".pth",
        ".ckpt",
        ".safetensors",
        ".h5",
        ".pb",
        ".onnx",
        ".tflite",
        ".pkl",
        ".pickle",
    }

    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".sh",
        ".bat",
        ".r",
        ".scala",
        ".go",
        ".rs",
    }

    DATA_EXTENSIONS = {
        ".csv",
        ".json",
        ".jsonl",
        ".txt",
        ".tsv",
        ".parquet",
        ".arrow",
        ".feather",
        ".hdf5",
        ".npy",
        ".npz",
    }

    CONFIG_EXTENSIONS = {".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg", ".xml"}

    DOCUMENTATION_EXTENSIONS = {".md", ".rst", ".txt", ".pdf", ".html", ".tex"}

    def __init__(self):
        """Initialize size analyzer."""
        pass

    def analyze_zip(self, zip_path: str) -> Dict[str, Any]:
        """
        Analyze a zip file and return detailed size breakdown.

        Args:
            zip_path: Path to the zip file

        Returns:
            Dict containing size analysis:
            {
                "total_bytes": int,
                "total_mb": float,
                "file_count": int,
                "components": {
                    "model_weights": {"bytes": int, "mb": float, "files": int},
                    "code": {"bytes": int, "mb": float, "files": int},
                    "data": {"bytes": int, "mb": float, "files": int},
                    "config": {"bytes": int, "mb": float, "files": int},
                    "documentation": {"bytes": int, "mb": float, "files": int},
                    "other": {"bytes": int, "mb": float, "files": int}
                },
                "largest_files": List[{"name": str, "bytes": int, "mb": float}]
            }
        """
        result = {
            "total_bytes": 0,
            "total_mb": 0.0,
            "file_count": 0,
            "components": {
                "model_weights": {"bytes": 0, "mb": 0.0, "files": 0},
                "code": {"bytes": 0, "mb": 0.0, "files": 0},
                "data": {"bytes": 0, "mb": 0.0, "files": 0},
                "config": {"bytes": 0, "mb": 0.0, "files": 0},
                "documentation": {"bytes": 0, "mb": 0.0, "files": 0},
                "other": {"bytes": 0, "mb": 0.0, "files": 0},
            },
            "largest_files": [],
        }

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                all_files = []

                for file_info in zf.filelist:
                    # Skip directories
                    if file_info.is_dir():
                        continue

                    file_size = file_info.file_size
                    file_name = file_info.filename
                    file_ext = Path(file_name).suffix.lower()

                    # Track all files for "largest files" list
                    all_files.append(
                        {
                            "name": file_name,
                            "bytes": file_size,
                            "mb": file_size / (1024 * 1024),
                        }
                    )

                    # Categorize by extension
                    category = self._categorize_file(file_ext, file_name)
                    result["components"][category]["bytes"] += file_size
                    result["components"][category]["files"] += 1

                    result["total_bytes"] += file_size
                    result["file_count"] += 1

                # Calculate MB for all components
                for component in result["components"].values():
                    component["mb"] = round(component["bytes"] / (1024 * 1024), 2)

                result["total_mb"] = round(result["total_bytes"] / (1024 * 1024), 2)

                # Get top 10 largest files
                all_files.sort(key=lambda x: x["bytes"], reverse=True)
                result["largest_files"] = all_files[:10]

        except zipfile.BadZipFile:
            logger.error(f"Invalid zip file: {zip_path}")
        except Exception as e:
            logger.error(f"Error analyzing size for {zip_path}: {e}")

        logger.info(
            f"Size analysis for {zip_path}: {result['total_mb']} MB, {result['file_count']} files"
        )
        return result

    def _categorize_file(self, extension: str, filename: str) -> str:
        """
        Categorize a file by its extension and name.

        Args:
            extension: File extension (including dot)
            filename: Full filename

        Returns:
            Category name: "model_weights", "code", "data", "config", "documentation", or "other"
        """
        # Check by extension first
        if extension in self.MODEL_WEIGHT_EXTENSIONS:
            return "model_weights"
        elif extension in self.CODE_EXTENSIONS:
            return "code"
        elif extension in self.DATA_EXTENSIONS:
            return "data"
        elif extension in self.CONFIG_EXTENSIONS:
            return "config"
        elif extension in self.DOCUMENTATION_EXTENSIONS:
            return "documentation"

        # Check by filename patterns
        filename_lower = filename.lower()

        if any(
            pattern in filename_lower
            for pattern in ["readme", "license", "changelog", "authors"]
        ):
            return "documentation"

        if any(pattern in filename_lower for pattern in ["config", "setting"]):
            return "config"

        if any(
            pattern in filename_lower for pattern in ["model", "weight", "checkpoint"]
        ):
            return "model_weights"

        # Default category
        return "other"

    def get_download_options(
        self, size_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate download options based on size analysis.

        Args:
            size_analysis: Result from analyze_zip()

        Returns:
            List of download options with size estimates:
            [
                {"option": "full", "description": "Complete package", "size_mb": float},
                {"option": "weights_only", "description": "Model weights only", "size_mb": float},
                ...
            ]
        """
        options = []

        # Full package
        options.append(
            {
                "option": "full",
                "description": "Complete package (all files)",
                "size_mb": size_analysis["total_mb"],
                "size_bytes": size_analysis["total_bytes"],
            }
        )

        # Weights only
        weights_size = size_analysis["components"]["model_weights"]["bytes"]
        if weights_size > 0:
            options.append(
                {
                    "option": "weights_only",
                    "description": "Model weights only",
                    "size_mb": round(weights_size / (1024 * 1024), 2),
                    "size_bytes": weights_size,
                }
            )

        # Code only
        code_size = size_analysis["components"]["code"]["bytes"]
        if code_size > 0:
            options.append(
                {
                    "option": "code_only",
                    "description": "Code files only",
                    "size_mb": round(code_size / (1024 * 1024), 2),
                    "size_bytes": code_size,
                }
            )

        # Weights + Config (common for model deployment)
        config_size = size_analysis["components"]["config"]["bytes"]
        if weights_size > 0 and config_size > 0:
            combined_size = weights_size + config_size
            options.append(
                {
                    "option": "weights_and_config",
                    "description": "Model weights and configuration files",
                    "size_mb": round(combined_size / (1024 * 1024), 2),
                    "size_bytes": combined_size,
                }
            )

        # Documentation only
        doc_size = size_analysis["components"]["documentation"]["bytes"]
        if doc_size > 0:
            options.append(
                {
                    "option": "docs_only",
                    "description": "Documentation files only",
                    "size_mb": round(doc_size / (1024 * 1024), 2),
                    "size_bytes": doc_size,
                }
            )

        return options


# Global instance
size_analyzer = SizeAnalyzer()
