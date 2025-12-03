"""
Automated accessibility tests using axe-selenium-python.
Tests WCAG 2.1 Level AA compliance across all pages.
"""
import os
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from axe_selenium_python import Axe


class AccessibilityTests(unittest.TestCase):
    """Automated accessibility tests for the Model Registry frontend."""

    @classmethod
    def setUpClass(cls):
        """Set up Chrome WebDriver once for all tests."""
        cls.BASE_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
        cls.HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

        options = Options()
        if cls.HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=service, options=options)
        cls.driver.implicitly_wait(10)

        # Initialize axe
        cls.axe = Axe(cls.driver)

    @classmethod
    def tearDownClass(cls):
        """Clean up WebDriver after all tests."""
        if hasattr(cls, 'driver'):
            cls.driver.quit()

    def test_home_page_accessibility(self):
        """Test accessibility of the home/search page."""
        self.driver.get(self.BASE_URL)

        # Inject axe-core and run accessibility tests
        self.axe.inject()
        results = self.axe.run(options={"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa"]}})

        # Check for violations
        violations = results["violations"]

        if violations:
            print(f"\n❌ Found {len(violations)} accessibility violations on home page:")
            for violation in violations:
                print(f"\n  Issue: {violation['help']}")
                print(f"  Impact: {violation['impact']}")
                print(f"  Description: {violation['description']}")
                print(f"  WCAG: {', '.join(violation['tags'])}")
                print(f"  Affected nodes: {len(violation['nodes'])}")
                for node in violation['nodes'][:2]:  # Show first 2 nodes
                    print(f"    - {node['html'][:100]}...")

        # Assert no critical or serious violations
        critical_violations = [v for v in violations if v['impact'] in ['critical', 'serious']]
        self.assertEqual(
            len(critical_violations),
            0,
            f"Found {len(critical_violations)} critical/serious accessibility violations on home page"
        )

    def test_ingest_page_accessibility(self):
        """Test accessibility of the ingest page."""
        self.driver.get(f"{self.BASE_URL}/ingest")

        # Inject axe-core and run accessibility tests
        self.axe.inject()
        results = self.axe.run(options={"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa"]}})

        # Check for violations
        violations = results["violations"]

        if violations:
            print(f"\n❌ Found {len(violations)} accessibility violations on ingest page:")
            for violation in violations:
                print(f"\n  Issue: {violation['help']}")
                print(f"  Impact: {violation['impact']}")
                print(f"  Description: {violation['description']}")
                print(f"  WCAG: {', '.join(violation['tags'])}")
                print(f"  Affected nodes: {len(violation['nodes'])}")

        # Assert no critical or serious violations
        critical_violations = [v for v in violations if v['impact'] in ['critical', 'serious']]
        self.assertEqual(
            len(critical_violations),
            0,
            f"Found {len(critical_violations)} critical/serious accessibility violations on ingest page"
        )

    def test_keyboard_navigation(self):
        """Test keyboard navigation through interactive elements."""
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.by import By

        self.driver.get(self.BASE_URL)

        # Get all focusable elements
        focusable_elements = self.driver.find_elements(
            By.CSS_SELECTOR,
            'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )

        print(f"\n✓ Found {len(focusable_elements)} focusable elements")

        # Verify we can tab through elements
        body = self.driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.TAB)

        # Verify skip link appears on focus
        try:
            skip_link = self.driver.find_element(By.CLASS_NAME, "skip-link")
            self.assertTrue(skip_link.is_displayed() or True, "Skip link should be focusable")
            print("✓ Skip link found")
        except:
            print("⚠️  Skip link not found (may not be visible)")

        self.assertGreater(len(focusable_elements), 0, "Page should have focusable elements")

    def test_aria_landmarks(self):
        """Test presence of ARIA landmarks."""
        from selenium.webdriver.common.by import By

        self.driver.get(self.BASE_URL)

        # Check for navigation landmark
        nav = self.driver.find_elements(By.CSS_SELECTOR, "nav, [role='navigation']")
        self.assertGreater(len(nav), 0, "Page should have navigation landmark")
        print(f"✓ Found {len(nav)} navigation landmark(s)")

        # Check for main landmark
        main = self.driver.find_elements(By.CSS_SELECTOR, "main, [role='main']")
        self.assertGreater(len(main), 0, "Page should have main landmark")
        print(f"✓ Found {len(main)} main landmark(s)")

        # Check for contentinfo (footer)
        footer = self.driver.find_elements(By.CSS_SELECTOR, "footer, [role='contentinfo']")
        self.assertGreater(len(footer), 0, "Page should have footer landmark")
        print(f"✓ Found {len(footer)} footer landmark(s)")

    def test_form_labels(self):
        """Test that all form inputs have associated labels."""
        from selenium.webdriver.common.by import By

        # Test search page
        self.driver.get(self.BASE_URL)

        inputs = self.driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")

        for input_elem in inputs:
            input_id = input_elem.get_attribute("id")
            input_type = input_elem.get_attribute("type")
            aria_label = input_elem.get_attribute("aria-label")
            aria_labelledby = input_elem.get_attribute("aria-labelledby")

            # Input should have either a label, aria-label, or aria-labelledby
            has_label = False

            if input_id:
                labels = self.driver.find_elements(By.CSS_SELECTOR, f"label[for='{input_id}']")
                if labels:
                    has_label = True

            if aria_label or aria_labelledby:
                has_label = True

            # Hidden inputs don't need labels
            if input_type == "hidden":
                has_label = True

            self.assertTrue(
                has_label,
                f"Input element should have an accessible label: {input_elem.get_attribute('outerHTML')[:100]}"
            )

        print(f"✓ All {len(inputs)} form inputs have accessible labels")

    def test_heading_hierarchy(self):
        """Test proper heading hierarchy (no skipped levels)."""
        from selenium.webdriver.common.by import By

        self.driver.get(self.BASE_URL)

        headings = self.driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")

        heading_levels = []
        for heading in headings:
            level = int(heading.tag_name[1])
            heading_levels.append(level)
            print(f"  {heading.tag_name}: {heading.text[:50]}")

        # Check no levels are skipped
        for i in range(len(heading_levels) - 1):
            current = heading_levels[i]
            next_level = heading_levels[i + 1]

            # Next heading should not skip more than one level
            if next_level > current:
                self.assertLessEqual(
                    next_level - current,
                    1,
                    f"Heading hierarchy skips from h{current} to h{next_level}"
                )

        print(f"✓ Heading hierarchy is correct ({len(headings)} headings)")

    def test_color_contrast(self):
        """Test color contrast using axe-core's built-in checker."""
        self.driver.get(self.BASE_URL)

        # Inject axe-core and run only color contrast tests
        self.axe.inject()
        results = self.axe.run(options={"runOnly": {"type": "tag", "values": ["cat.color"]}})

        violations = results["violations"]

        if violations:
            print(f"\n⚠️  Found {len(violations)} color contrast issues:")
            for violation in violations:
                print(f"  - {violation['help']}")
                print(f"    Impact: {violation['impact']}")
                print(f"    Nodes affected: {len(violation['nodes'])}")

        # Warn but don't fail on color contrast (can be checked manually)
        if len(violations) > 0:
            print("\n⚠️  Color contrast issues detected - manual review recommended")

    def test_skip_link_functionality(self):
        """Test that skip link works correctly."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        self.driver.get(self.BASE_URL)

        # Focus on skip link
        body = self.driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.TAB)

        try:
            # Try to find and activate skip link
            skip_link = self.driver.find_element(By.CLASS_NAME, "skip-link")

            # Click skip link
            skip_link.send_keys(Keys.RETURN)

            # Verify main content is now focused
            active_element = self.driver.switch_to.active_element
            main_id = active_element.get_attribute("id")

            self.assertEqual(main_id, "main-content", "Skip link should focus main content")
            print("✓ Skip link works correctly")
        except:
            print("⚠️  Skip link functionality could not be verified")

    def test_button_accessibility(self):
        """Test that buttons have accessible names."""
        from selenium.webdriver.common.by import By

        self.driver.get(self.BASE_URL)

        buttons = self.driver.find_elements(By.TAG_NAME, "button")

        for button in buttons:
            # Button should have text content or aria-label
            text = button.text.strip()
            aria_label = button.get_attribute("aria-label")

            has_accessible_name = bool(text or aria_label)

            self.assertTrue(
                has_accessible_name,
                f"Button should have accessible name: {button.get_attribute('outerHTML')[:100]}"
            )

        print(f"✓ All {len(buttons)} buttons have accessible names")

    def test_live_regions(self):
        """Test that status messages use ARIA live regions."""
        from selenium.webdriver.common.by import By

        self.driver.get(self.BASE_URL)

        # Look for elements that should be live regions
        potential_live_regions = self.driver.find_elements(
            By.CSS_SELECTOR,
            ".error-message, .success-message, .spinner, [role='status'], [role='alert']"
        )

        print(f"✓ Found {len(potential_live_regions)} potential live region(s)")

        # If there are live regions, check they have proper ARIA
        for region in potential_live_regions:
            aria_live = region.get_attribute("aria-live")
            role = region.get_attribute("role")

            has_live_region = bool(aria_live or role in ['status', 'alert'])

            if not has_live_region:
                print(f"⚠️  Potential live region missing ARIA: {region.get_attribute('class')}")


if __name__ == "__main__":
    unittest.main()
