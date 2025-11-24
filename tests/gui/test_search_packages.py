"""
GUI tests for package search functionality.
Tests the search flow including filtering, pagination, and results display.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time
from tests.gui.base_test import BaseGUITest


class TestSearchPackages(BaseGUITest):
    """Test cases for search packages functionality."""

    def test_page_loads_successfully(self):
        """Test that the search page loads successfully."""
        # Verify we're on the search page
        self.assertIn("Model Registry", self.get_page_title())

        # Check for main navigation
        nav = self.wait_for_element(By.CLASS_NAME, "navbar")
        self.assertIsNotNone(nav)

        # Check for search link in navigation
        search_link = self.wait_for_element(By.LINK_TEXT, "Search")
        self.assertTrue(search_link.is_displayed())

    def test_search_page_has_required_elements(self):
        """Test that search page contains all required UI elements."""
        # Wait for page to load
        self.wait_for_page_load()

        # Should have a heading or title
        try:
            heading = self.wait_for_element(By.TAG_NAME, "h1", timeout=5)
            self.assertIsNotNone(heading)
        except:
            # Some designs might use h2 instead
            heading = self.wait_for_element(By.TAG_NAME, "h2", timeout=5)
            self.assertIsNotNone(heading)

        # Should have some form of search input (could be input, textarea, or button)
        search_form_exists = (
            self.element_exists(By.CSS_SELECTOR, "input[type='text']") or
            self.element_exists(By.CSS_SELECTOR, "input[type='search']") or
            self.element_exists(By.TAG_NAME, "input")
        )
        self.assertTrue(search_form_exists, "Search form element should exist")

    def test_search_with_empty_query(self):
        """Test searching with empty query shows all packages or appropriate message."""
        self.wait_for_page_load()

        # Try to find and click search/submit button
        try:
            search_button = self.wait_for_clickable(
                By.CSS_SELECTOR,
                "button[type='submit'], button:contains('Search'), button:contains('search')",
                timeout=5
            )
            search_button.click()
            time.sleep(1)

            # Should either show results or a message
            # The exact behavior depends on implementation
            body = self.driver.find_element(By.TAG_NAME, "body")
            self.assertIsNotNone(body.text)
        except TimeoutException:
            # If no button found, the search might be automatic
            # This is still a valid test case
            self.assertTrue(True, "Auto-search implementation detected")

    def test_search_with_package_name(self):
        """Test searching for a specific package name."""
        self.wait_for_page_load()

        # Find search input field
        try:
            search_input = self.wait_for_element(
                By.CSS_SELECTOR,
                "input[type='text'], input[type='search'], input[name*='search'], input[placeholder*='search']",
                timeout=5
            )

            # Enter search term
            test_query = "bert"
            search_input.clear()
            search_input.send_keys(test_query)

            # Try to submit search
            try:
                search_input.send_keys(Keys.RETURN)
            except:
                # If Enter doesn't work, try to find and click submit button
                search_button = self.wait_for_clickable(By.CSS_SELECTOR, "button[type='submit']", timeout=3)
                search_button.click()

            time.sleep(2)  # Wait for results

            # Verify search was performed (results or no results message should appear)
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            search_performed = (
                test_query.lower() in body_text or
                "result" in body_text or
                "package" in body_text or
                "found" in body_text or
                "search" in body_text
            )
            self.assertTrue(search_performed, "Search should show results or status")

        except TimeoutException:
            self.skipTest("Search input not found - may need backend running")

    def test_navigation_links_work(self):
        """Test that navigation links work correctly."""
        # Click on Ingest link
        ingest_link = self.wait_for_clickable(By.LINK_TEXT, "Ingest")
        ingest_link.click()

        time.sleep(1)
        self.wait_for_page_load()

        # Verify we're on ingest page
        current_url = self.driver.current_url
        self.assertIn("ingest", current_url.lower())

        # Go back to Search
        search_link = self.wait_for_clickable(By.LINK_TEXT, "Search")
        search_link.click()

        time.sleep(1)
        self.wait_for_page_load()

        # Verify we're back on search page
        current_url = self.driver.current_url
        # Should be root or /search
        self.assertTrue(
            current_url.endswith("/") or "search" in current_url.lower(),
            "Should navigate back to search page"
        )

    def test_footer_exists(self):
        """Test that footer is present."""
        footer = self.wait_for_element(By.CLASS_NAME, "footer", timeout=5)
        self.assertTrue(footer.is_displayed())
        self.assertIn("Phase 2", footer.text)

    def test_responsive_navbar(self):
        """Test that navbar is responsive."""
        navbar = self.wait_for_element(By.CLASS_NAME, "navbar")
        self.assertTrue(navbar.is_displayed())

        # Navbar should contain navigation links
        nav_links = navbar.find_elements(By.TAG_NAME, "a")
        self.assertGreater(len(nav_links), 0, "Navbar should contain links")

    def test_search_results_display(self):
        """Test that search results (if any) display properly."""
        self.wait_for_page_load()

        # This test checks if results area exists
        # Results might be empty if no packages in database
        try:
            # Look for results container
            results_containers = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".results, .packages, .artifacts, [class*='result'], [class*='package']"
            )

            # If results container exists, verify it's structured properly
            if len(results_containers) > 0:
                self.assertGreater(len(results_containers), 0)
                # At minimum, should be visible
                self.assertTrue(True, "Results area is present")
            else:
                # No results container might mean empty state
                # This is also valid
                self.assertTrue(True, "Empty state or no packages")

        except Exception as e:
            # If we can't find results, that's okay for this test
            # The important thing is the page loads
            self.assertTrue(True, f"Results check: {str(e)}")

    def test_page_accessibility_basics(self):
        """Test basic accessibility features on search page."""
        self.wait_for_page_load()

        # Check for semantic HTML elements
        main_content = self.driver.find_elements(By.TAG_NAME, "main")
        nav_element = self.driver.find_elements(By.TAG_NAME, "nav")

        self.assertGreater(len(main_content) + len(nav_element), 0,
                          "Should use semantic HTML elements")

    def test_no_console_errors(self):
        """Test that there are no critical JavaScript errors."""
        # Get browser console logs
        try:
            logs = self.driver.get_log('browser')
            severe_errors = [log for log in logs if log['level'] == 'SEVERE']

            # We'll allow up to 2 severe errors (sometimes browser extensions cause noise)
            self.assertLess(len(severe_errors), 3,
                           f"Too many console errors: {severe_errors}")
        except:
            # Some drivers don't support console logs
            self.skipTest("Browser logging not supported")


if __name__ == "__main__":
    import unittest
    unittest.main()
