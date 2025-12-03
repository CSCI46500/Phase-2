"""
License Compatibility Checker for Model Registry.
Implements compatibility logic based on standard open source license rules.

License Categories:
1. Permissive: MIT, BSD, Apache-2.0 (allow proprietary derivatives)
2. Weakly Protective: LGPL, MPL (middle ground)
3. Strongly Protective: GPL, AGPL (require open source derivatives)

Compatibility Rules:
- Permissive licenses can combine with any license
- Weakly protective licenses can combine upward (to stronger protection)
- Strongly protective licenses require all combined code to be under same license
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """License categories by strength of protection."""

    PERMISSIVE = "permissive"
    WEAK_COPYLEFT = "weak_copyleft"
    STRONG_COPYLEFT = "strong_copyleft"
    PROPRIETARY = "proprietary"
    UNKNOWN = "unknown"


class LicenseCompatibility:
    """
    License compatibility checker following standard OSS compatibility rules.
    Based on FSF and OSI compatibility guidelines.
    """

    # License categorization
    LICENSE_CATEGORIES = {
        # Permissive licenses - most compatible
        "mit": LicenseType.PERMISSIVE,
        "bsd": LicenseType.PERMISSIVE,
        "bsd-2-clause": LicenseType.PERMISSIVE,
        "bsd-3-clause": LicenseType.PERMISSIVE,
        "apache-2.0": LicenseType.PERMISSIVE,
        "apache": LicenseType.PERMISSIVE,
        "isc": LicenseType.PERMISSIVE,
        "unlicense": LicenseType.PERMISSIVE,
        "0bsd": LicenseType.PERMISSIVE,
        # Weakly protective (copyleft with linking exceptions)
        "lgpl": LicenseType.WEAK_COPYLEFT,
        "lgpl-2.1": LicenseType.WEAK_COPYLEFT,
        "lgpl-3.0": LicenseType.WEAK_COPYLEFT,
        "mpl": LicenseType.WEAK_COPYLEFT,
        "mpl-2.0": LicenseType.WEAK_COPYLEFT,
        # Strongly protective (strong copyleft)
        "gpl": LicenseType.STRONG_COPYLEFT,
        "gpl-2.0": LicenseType.STRONG_COPYLEFT,
        "gpl-3.0": LicenseType.STRONG_COPYLEFT,
        "agpl": LicenseType.STRONG_COPYLEFT,
        "agpl-3.0": LicenseType.STRONG_COPYLEFT,
        # Proprietary
        "proprietary": LicenseType.PROPRIETARY,
        "closed": LicenseType.PROPRIETARY,
    }

    # Specific incompatibilities (overrides general rules)
    INCOMPATIBLE_PAIRS = {
        ("gpl-2.0", "apache-2.0"),  # GPLv2 incompatible with Apache 2.0
        ("mpl", "gpl"),  # MPL incompatible with GPL (general)
        ("mpl-2.0", "gpl-2.0"),  # MPL 2.0 incompatible with GPLv2
    }

    def __init__(self):
        """Initialize compatibility checker."""
        self.compatibility_cache = {}

    def normalize_license(self, license_str: str) -> str:
        """Normalize license string for comparison."""
        if not license_str:
            return "unknown"

        normalized = license_str.lower().strip()

        # Handle common variations
        normalized = normalized.replace("license", "").strip()
        normalized = normalized.replace("licence", "").strip()
        normalized = normalized.replace("_", "-")
        normalized = normalized.replace(" ", "-")

        # Handle version aliases
        if normalized in ["gplv2", "gnu-gpl-2.0"]:
            normalized = "gpl-2.0"
        elif normalized in ["gplv3", "gnu-gpl-3.0"]:
            normalized = "gpl-3.0"
        elif normalized in ["lgplv2.1", "lgplv2", "gnu-lgpl-2.1"]:
            normalized = "lgpl-2.1"
        elif normalized in ["lgplv3", "gnu-lgpl-3.0"]:
            normalized = "lgpl-3.0"
        elif normalized in ["apache2", "apache-2", "apache2.0"]:
            normalized = "apache-2.0"
        elif normalized in ["bsd2", "bsd-2"]:
            normalized = "bsd-2-clause"
        elif normalized in ["bsd3", "bsd-3"]:
            normalized = "bsd-3-clause"

        return normalized

    def get_license_type(self, license_str: str) -> LicenseType:
        """Get the category/type of a license."""
        normalized = self.normalize_license(license_str)
        return self.LICENSE_CATEGORIES.get(normalized, LicenseType.UNKNOWN)

    def check_specific_incompatibility(self, license1: str, license2: str) -> bool:
        """Check if two licenses have a specific known incompatibility."""
        norm1 = self.normalize_license(license1)
        norm2 = self.normalize_license(license2)

        # Check both orderings
        if (norm1, norm2) in self.INCOMPATIBLE_PAIRS or (
            norm2,
            norm1,
        ) in self.INCOMPATIBLE_PAIRS:
            return True

        return False

    def are_compatible(self, license1: str, license2: str) -> Tuple[bool, str]:
        """
        Check if two licenses are compatible for combination.

        Args:
            license1: First license identifier
            license2: Second license identifier

        Returns:
            Tuple of (is_compatible: bool, reason: str)
        """
        # Normalize licenses
        norm1 = self.normalize_license(license1)
        norm2 = self.normalize_license(license2)

        # Check cache
        cache_key = tuple(sorted([norm1, norm2]))
        if cache_key in self.compatibility_cache:
            return self.compatibility_cache[cache_key]

        # Same license is always compatible
        if norm1 == norm2:
            result = (True, f"Both use the same license: {norm1}")
            self.compatibility_cache[cache_key] = result
            return result

        # Check for unknown licenses
        type1 = self.get_license_type(norm1)
        type2 = self.get_license_type(norm2)

        if type1 == LicenseType.UNKNOWN or type2 == LicenseType.UNKNOWN:
            result = (
                False,
                f"Unknown license(s): {norm1 if type1 == LicenseType.UNKNOWN else norm2}",
            )
            self.compatibility_cache[cache_key] = result
            return result

        # Check for proprietary
        if type1 == LicenseType.PROPRIETARY or type2 == LicenseType.PROPRIETARY:
            result = (False, "Proprietary licenses are not compatible with open source")
            self.compatibility_cache[cache_key] = result
            return result

        # Check specific incompatibilities
        if self.check_specific_incompatibility(norm1, norm2):
            result = (False, f"{norm1} and {norm2} have known incompatibilities")
            self.compatibility_cache[cache_key] = result
            return result

        # Apply general compatibility rules
        result = self._apply_compatibility_rules(norm1, type1, norm2, type2)
        self.compatibility_cache[cache_key] = result
        return result

    def _apply_compatibility_rules(
        self, license1: str, type1: LicenseType, license2: str, type2: LicenseType
    ) -> Tuple[bool, str]:
        """Apply general license compatibility rules."""

        # Permissive licenses can combine with anything
        if type1 == LicenseType.PERMISSIVE and type2 == LicenseType.PERMISSIVE:
            return (True, f"Both {license1} and {license2} are permissive licenses")

        if type1 == LicenseType.PERMISSIVE and type2 == LicenseType.WEAK_COPYLEFT:
            return (
                True,
                f"{license1} (permissive) can be combined with {license2} (weak copyleft)",
            )

        if type1 == LicenseType.WEAK_COPYLEFT and type2 == LicenseType.PERMISSIVE:
            return (
                True,
                f"{license1} (weak copyleft) can be combined with {license2} (permissive)",
            )

        if type1 == LicenseType.PERMISSIVE and type2 == LicenseType.STRONG_COPYLEFT:
            return (
                True,
                f"{license1} (permissive) can be combined with {license2} (strong copyleft). Result must be {license2}",
            )

        if type1 == LicenseType.STRONG_COPYLEFT and type2 == LicenseType.PERMISSIVE:
            return (
                True,
                f"{license1} (strong copyleft) can be combined with {license2} (permissive). Result must be {license1}",
            )

        # Weak copyleft licenses
        if type1 == LicenseType.WEAK_COPYLEFT and type2 == LicenseType.WEAK_COPYLEFT:
            return (True, f"Both {license1} and {license2} are weak copyleft licenses")

        if type1 == LicenseType.WEAK_COPYLEFT and type2 == LicenseType.STRONG_COPYLEFT:
            return (
                True,
                f"{license1} (weak copyleft) can be combined with {license2} (strong copyleft). Result must be {license2}",
            )

        if type1 == LicenseType.STRONG_COPYLEFT and type2 == LicenseType.WEAK_COPYLEFT:
            return (
                True,
                f"{license1} (strong copyleft) can be combined with {license2} (weak copyleft). Result must be {license1}",
            )

        # Strong copyleft licenses
        if (
            type1 == LicenseType.STRONG_COPYLEFT
            and type2 == LicenseType.STRONG_COPYLEFT
        ):
            # Different strong copyleft licenses are generally incompatible
            return (
                False,
                f"{license1} and {license2} are both strong copyleft licenses and may be incompatible",
            )

        # Default case
        return (False, f"Compatibility between {license1} and {license2} is unclear")

    def check_project_compatibility(
        self, project_license: str, dependency_licenses: List[str]
    ) -> Dict[str, any]:
        """
        Check if a project's license is compatible with all its dependencies.

        Args:
            project_license: The license of the main project
            dependency_licenses: List of dependency licenses

        Returns:
            Dict with compatibility results:
            {
                "compatible": bool,
                "project_license": str,
                "incompatible_dependencies": List[Dict],
                "warnings": List[str]
            }
        """
        result = {
            "compatible": True,
            "project_license": self.normalize_license(project_license),
            "incompatible_dependencies": [],
            "warnings": [],
        }

        for dep_license in dependency_licenses:
            is_compatible, reason = self.are_compatible(project_license, dep_license)

            if not is_compatible:
                result["compatible"] = False
                result["incompatible_dependencies"].append(
                    {"license": self.normalize_license(dep_license), "reason": reason}
                )
            else:
                # Check if there's a warning (e.g., result license must be stronger)
                if "must be" in reason.lower():
                    result["warnings"].append(reason)

        return result


# Global instance for easy import
license_checker = LicenseCompatibility()
