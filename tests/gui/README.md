# GUI Automated Tests with Selenium

## Overview

This directory contains automated GUI tests for the Model Registry frontend using Selenium WebDriver. These tests validate the user interface, user workflows, and end-to-end functionality.

## Test Files

1. **`base_test.py`** - Base test class with common setup, teardown, and utility methods
2. **`test_search_packages.py`** - Tests for package search functionality
3. **`test_upload_package.py`** - Tests for package upload workflows
4. **`test_ingest_huggingface.py`** - Tests for HuggingFace model ingestion
5. **`test_authentication.py`** - Tests for login/logout and authentication (when implemented)

## Prerequisites

### Required Packages

```bash
pip install selenium webdriver-manager pytest-asyncio
```

### Browser Requirements

- **Chrome/Chromium** browser installed
- Tests use `webdriver-manager` to automatically download ChromeDriver

## Configuration

### Environment Variables

Set these environment variables to configure test behavior:

```bash
# Frontend URL (default: http://localhost:5173)
export FRONTEND_URL="http://localhost:5173"

# Backend API URL (default: http://localhost:8000)
export API_URL="http://localhost:8000"

# Run in headless mode (default: true)
export HEADLESS="true"
```

### Running the Application

Before running GUI tests, ensure both frontend and backend are running:

**Terminal 1 - Backend:**
```bash
cd /path/to/Phase-2
./run_api_new.sh
```

**Terminal 2 - Frontend:**
```bash
cd front-end/model-registry-frontend
npm install
npm run dev
```

## Running Tests

### Run All GUI Tests

```bash
# From project root
PYTHONPATH=. python -m pytest tests/gui/ -v

# In headless mode (default)
HEADLESS=true PYTHONPATH=. python -m pytest tests/gui/ -v

# With visible browser (for debugging)
HEADLESS=false PYTHONPATH=. python -m pytest tests/gui/ -v
```

### Run Specific Test File

```bash
# Test search functionality
PYTHONPATH=. python -m pytest tests/gui/test_search_packages.py -v

# Test ingestion
PYTHONPATH=. python -m pytest tests/gui/test_ingest_huggingface.py -v

# Test upload
PYTHONPATH=. python -m pytest tests/gui/test_upload_package.py -v

# Test authentication
PYTHONPATH=. python -m pytest tests/gui/test_authentication.py -v
```

### Run Specific Test

```bash
PYTHONPATH=. python -m pytest tests/gui/test_search_packages.py::TestSearchPackages::test_page_loads_successfully -v
```

## Test Features

### Base Test Class (`BaseGUITest`)

The base class provides:

- **Automatic browser setup/teardown**
- **Implicit and explicit waits**
- **Utility methods:**
  - `wait_for_element(by, value)` - Wait for element to be present
  - `wait_for_clickable(by, value)` - Wait for element to be clickable
  - `wait_for_text(by, value, text)` - Wait for text in element
  - `element_exists(by, value)` - Check if element exists
  - `take_screenshot(name)` - Capture screenshot for debugging
  - `scroll_to_element(element)` - Scroll element into view
  - `wait_for_page_load()` - Wait for page to fully load

### Headless Mode

By default, tests run in headless mode for CI/CD pipelines. To see the browser during test execution:

```bash
HEADLESS=false PYTHONPATH=. python -m pytest tests/gui/test_search_packages.py -v
```

### Screenshots

Screenshots are automatically saved to `tests/gui/screenshots/` when using the `take_screenshot()` method. This is useful for debugging test failures.

## Test Coverage

### Search Tests (10 tests)
- ✅ Page loads successfully
- ✅ Required UI elements present
- ✅ Search with empty query
- ✅ Search with package name
- ✅ Navigation links work
- ✅ Footer exists
- ✅ Responsive navbar
- ✅ Search results display
- ✅ Basic accessibility
- ✅ No critical console errors

### Upload/Ingest Tests (11 tests)
- ✅ Page navigation
- ✅ Form elements present
- ✅ File input exists
- ✅ URL input validation
- ✅ Submit button exists
- ✅ Form validation
- ✅ Multiple input fields
- ✅ Back navigation
- ✅ Page title
- ✅ Form styling
- ✅ Responsive design

### HuggingFace Ingestion Tests (10 tests)
- ✅ Navigate to ingest page
- ✅ HuggingFace URL input
- ✅ Valid URL format
- ✅ Multiple URL formats
- ✅ Ingest button clickable
- ✅ Form submission flow
- ✅ Invalid URL handling
- ✅ Page instructions
- ✅ Page layout
- ✅ Responsive design

### Authentication Tests (10 tests)
- ✅ Check for login elements
- ✅ Application loads without auth
- ✅ Protected routes handling
- ✅ Login form (if exists)
- ✅ Logout functionality (if exists)
- ✅ Session persistence
- ✅ Unauthorized access handling
- ✅ Default admin credentials
- ✅ Auth token storage
- ✅ Auth headers in requests

**Total: 41 GUI Tests**

## CI/CD Integration

### GitHub Actions Example

```yaml
name: GUI Tests

on: [push, pull_request]

jobs:
  gui-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install selenium webdriver-manager

      - name: Install Chrome
        run: |
          wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
          sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
          sudo apt-get update
          sudo apt-get install google-chrome-stable

      - name: Start backend
        run: |
          ./run_api_new.sh &
          sleep 10

      - name: Start frontend
        run: |
          cd front-end/model-registry-frontend
          npm install
          npm run dev &
          sleep 15

      - name: Run GUI tests
        run: |
          HEADLESS=true PYTHONPATH=. python -m pytest tests/gui/ -v
```

## Docker Integration

### Quick Start with Helper Script

The easiest way to run GUI tests with Docker:

```bash
# Run tests with Docker (default - headless mode)
./run_gui_tests.sh

# Run with visible browser (for debugging)
./run_gui_tests.sh --visible

# Run specific test file
./run_gui_tests.sh --test test_search_packages.py

# Run without Docker (use existing services)
./run_gui_tests.sh --no-docker

# Show verbose output
./run_gui_tests.sh --verbose

# Get help
./run_gui_tests.sh --help
```

### Manual Docker Setup

To run tests against Docker stack manually:

```bash
# 1. Create .env file (if not exists)
cat > .env << EOF
POSTGRES_DB=model_registry
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql://postgres:postgres@db:5432/model_registry
SECRET_KEY=test-secret-key
LOG_LEVEL=INFO
VITE_API_URL=http://localhost:8000
EOF

# 2. Start Docker stack
docker-compose up -d

# 3. Wait for services to be ready (check health)
docker-compose ps

# Wait for backend
until curl -f http://localhost:8000/health; do
  echo "Waiting for backend..."
  sleep 2
done

# Wait for frontend
until curl -f http://localhost:5173; do
  echo "Waiting for frontend..."
  sleep 2
done

# 4. Run tests
FRONTEND_URL="http://localhost:5173" \
API_URL="http://localhost:8000" \
HEADLESS=true \
PYTHONPATH=. python -m pytest tests/gui/ -v

# 5. Cleanup
docker-compose down -v
```

### Docker Services

The `docker-compose.yml` includes:

- **PostgreSQL Database** (port 5432)
- **Backend API** (port 8000) - FastAPI with auto-reload
- **Frontend** (port 5173) - React + Vite dev server
- **Selenium Chrome** (optional, port 4444) - For remote WebDriver

### Using Selenium Grid (Optional)

To run tests using Docker's Selenium container:

```bash
# Start services including Selenium
docker-compose --profile testing up -d

# Run tests using remote WebDriver
FRONTEND_URL="http://localhost:5173" \
API_URL="http://localhost:8000" \
SELENIUM_REMOTE_URL="http://localhost:4444/wd/hub" \
PYTHONPATH=. python -m pytest tests/gui/ -v

# View tests running (VNC)
# Open http://localhost:7900 in browser (password: secret)
```

### Docker Troubleshooting

**Services not starting:**
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs db

# Restart specific service
docker-compose restart backend
```

**Port conflicts:**
```bash
# Stop conflicting services
sudo lsof -ti:8000 | xargs kill -9  # Backend
sudo lsof -ti:5173 | xargs kill -9  # Frontend

# Or use different ports in docker-compose.yml
```

**Database issues:**
```bash
# Reset database
docker-compose down -v  # Removes volumes
docker-compose up -d
```

## Troubleshooting

### Common Issues

**1. ChromeDriver not found**
- Solution: `webdriver-manager` should auto-download. If issues persist, install manually.

**2. Tests timeout**
- Ensure frontend and backend are running
- Check `FRONTEND_URL` and `API_URL` environment variables
- Increase timeout values in `base_test.py` if needed

**3. Element not found**
- Run with `HEADLESS=false` to see what's happening
- Use `take_screenshot()` to debug
- Check if page loaded successfully

**4. Permission denied on ChromeDriver**
- Run: `chmod +x /path/to/chromedriver`

## Best Practices

1. **Always wait for elements** - Use `wait_for_element()` instead of `find_element()`
2. **Use explicit waits** - Better than `time.sleep()`
3. **Test user workflows** - Not just individual elements
4. **Handle dynamic content** - Wait for AJAX/async operations
5. **Clean up test data** - Use tearDown to remove test data
6. **Run in CI/CD** - Automate testing on every push
7. **Take screenshots on failures** - Helps with debugging

## Future Enhancements

- [ ] Add visual regression testing
- [ ] Test on multiple browsers (Firefox, Edge)
- [ ] Add performance monitoring
- [ ] Test mobile responsiveness more thoroughly
- [ ] Add accessibility testing with axe-selenium
- [ ] Implement page object pattern for better maintainability
