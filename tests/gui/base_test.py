"""
Base test class for GUI tests with Selenium.
Provides common setup, teardown, and utility methods.
"""
import unittest
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


class BaseGUITest(unittest.TestCase):
    """Base class for all GUI tests."""

    # Configuration
    BASE_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    API_URL = os.getenv("API_URL", "http://localhost:8000")
    IMPLICIT_WAIT = 10
    EXPLICIT_WAIT = 15
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    BROWSER = os.getenv("BROWSER", "firefox").lower()  # chrome or firefox

    @classmethod
    def setUpClass(cls):
        """Set up browser driver once for all tests in the class."""

        # Try Firefox first (since user has it), fallback to Chrome
        browsers_to_try = ["firefox", "chrome"] if cls.BROWSER == "firefox" else ["chrome", "firefox"]

        for browser in browsers_to_try:
            try:
                if browser == "firefox":
                    print(f"🔧 Attempting to initialize Firefox...")
                    cls.driver = cls._setup_firefox()
                    print(f"✅ Using Firefox for GUI tests")
                    break
                elif browser == "chrome":
                    print(f"🔧 Attempting to initialize Chrome...")
                    cls.driver = cls._setup_chrome()
                    print(f"✅ Using Chrome for GUI tests")
                    break
            except Exception as e:
                print(f"⚠️ Could not initialize {browser}: {str(e)[:200]}")
                if browser == browsers_to_try[-1]:
                    raise Exception(f"No browser available for testing. Last error: {str(e)[:300]}")

        cls.driver.implicitly_wait(cls.IMPLICIT_WAIT)

    @classmethod
    def _setup_firefox(cls):
        """Set up Firefox driver."""
        firefox_options = FirefoxOptions()

        if cls.HEADLESS:
            firefox_options.add_argument("--headless")

        firefox_options.add_argument("--window-size=1920,1080")
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")

        # Set preferences to avoid marionette issues
        firefox_options.set_preference("dom.disable_beforeunload", True)
        firefox_options.set_preference("dom.webnotifications.enabled", False)
        firefox_options.set_preference("geo.enabled", False)

        # Create service with log output
        service = FirefoxService(
            GeckoDriverManager().install(),
            log_output=os.devnull
        )

        return webdriver.Firefox(
            service=service,
            options=firefox_options
        )

    @classmethod
    def _setup_chrome(cls):
        """Set up Chrome driver."""
        chrome_options = ChromeOptions()

        if cls.HEADLESS:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")

        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        return webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options
        )

    @classmethod
    def tearDownClass(cls):
        """Quit driver after all tests."""
        if hasattr(cls, 'driver'):
            cls.driver.quit()

    def setUp(self):
        """Navigate to base URL before each test."""
        self.driver.get(self.BASE_URL)
        self.wait = WebDriverWait(self.driver, self.EXPLICIT_WAIT)

    def wait_for_element(self, by, value, timeout=None):
        """Wait for element to be present."""
        timeout = timeout or self.EXPLICIT_WAIT
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.fail(f"Element not found: {by}={value}")

    def wait_for_clickable(self, by, value, timeout=None):
        """Wait for element to be clickable."""
        timeout = timeout or self.EXPLICIT_WAIT
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            self.fail(f"Element not clickable: {by}={value}")

    def wait_for_text(self, by, value, text, timeout=None):
        """Wait for element to contain specific text."""
        timeout = timeout or self.EXPLICIT_WAIT
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.text_to_be_present_in_element((by, value), text)
            )
        except TimeoutException:
            self.fail(f"Text '{text}' not found in element: {by}={value}")

    def element_exists(self, by, value):
        """Check if element exists without waiting."""
        try:
            self.driver.find_element(by, value)
            return True
        except NoSuchElementException:
            return False

    def get_page_title(self):
        """Get current page title."""
        return self.driver.title

    def take_screenshot(self, name):
        """Take screenshot for debugging."""
        screenshot_dir = "tests/gui/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        filepath = os.path.join(screenshot_dir, f"{name}.png")
        self.driver.save_screenshot(filepath)
        print(f"Screenshot saved: {filepath}")

    def scroll_to_element(self, element):
        """Scroll element into view."""
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)

    def wait_for_page_load(self, timeout=None):
        """Wait for page to finish loading."""
        timeout = timeout or self.EXPLICIT_WAIT
        WebDriverWait(self.driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
