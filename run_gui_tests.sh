#!/bin/bash

# Script to run GUI tests locally with Docker stack
# Usage: ./run_gui_tests.sh [options]
#   --no-docker     Run without Docker (expects services already running)
#   --visible       Run tests with visible browser (not headless)
#   --test FILE     Run specific test file
#   --verbose       Show verbose output

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
USE_DOCKER=true
HEADLESS=true
TEST_FILE=""
VERBOSE=false
FRONTEND_URL="http://localhost:5173"
API_URL="http://localhost:8000"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        --visible)
            HEADLESS=false
            shift
            ;;
        --test)
            TEST_FILE="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --no-docker     Run without Docker (expects services already running)"
            echo "  --visible       Run tests with visible browser (not headless)"
            echo "  --test FILE     Run specific test file (e.g., test_search_packages.py)"
            echo "  --verbose, -v   Show verbose output"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to check if service is ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1

    echo -e "${BLUE}Waiting for $name to be ready at $url...${NC}"

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $name is ready!${NC}"
            return 0
        fi
        echo -e "${YELLOW}⏳ Waiting for $name... ($attempt/$max_attempts)${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}✗ $name failed to start${NC}"
    return 1
}

# Function to cleanup on exit
cleanup() {
    if [ "$USE_DOCKER" = true ]; then
        echo -e "\n${YELLOW}Cleaning up Docker services...${NC}"
        docker-compose down > /dev/null 2>&1
        echo -e "${GREEN}✓ Docker services stopped${NC}"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Main execution
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}  GUI Test Runner for Model Registry${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"
if ! command -v python &> /dev/null; then
    echo -e "${RED}✗ Python not found${NC}"
    exit 1
fi

if ! python -c "import selenium" &> /dev/null; then
    echo -e "${YELLOW}⚠ Selenium not installed. Installing...${NC}"
    pip install selenium webdriver-manager pytest-asyncio
fi

echo -e "${GREEN}✓ Dependencies OK${NC}"
echo ""

# Start services
if [ "$USE_DOCKER" = true ]; then
    echo -e "${BLUE}Starting Docker stack...${NC}"

    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Creating .env file...${NC}"
        cat > .env << EOF
POSTGRES_DB=model_registry
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql://postgres:postgres@db:5432/model_registry
SECRET_KEY=test-secret-key
LOG_LEVEL=INFO
VITE_API_URL=http://localhost:8000
EOF
    fi

    # Start Docker services
    docker-compose up -d

    # Wait for services
    if ! wait_for_service "$API_URL/health" "Backend API"; then
        echo -e "${RED}Failed to start backend${NC}"
        docker-compose logs backend
        exit 1
    fi

    if ! wait_for_service "$FRONTEND_URL" "Frontend"; then
        echo -e "${RED}Failed to start frontend${NC}"
        docker-compose logs frontend
        exit 1
    fi
else
    echo -e "${BLUE}Using existing services (no Docker)${NC}"
    echo -e "${YELLOW}Verifying services are running...${NC}"

    if ! wait_for_service "$API_URL/health" "Backend API"; then
        echo -e "${RED}Backend not responding. Please start it manually.${NC}"
        exit 1
    fi

    if ! wait_for_service "$FRONTEND_URL" "Frontend"; then
        echo -e "${RED}Frontend not responding. Please start it manually.${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✓ All services ready!${NC}"
echo ""

# Set environment variables for tests
export FRONTEND_URL="$FRONTEND_URL"
export API_URL="$API_URL"
export HEADLESS="$HEADLESS"
export PYTHONPATH="."

# Build pytest command
PYTEST_CMD="python -m pytest tests/gui/"

if [ -n "$TEST_FILE" ]; then
    PYTEST_CMD="python -m pytest tests/gui/$TEST_FILE"
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add additional pytest options
PYTEST_CMD="$PYTEST_CMD --tb=short --color=yes"

# Run tests
echo -e "${BLUE}Running GUI tests...${NC}"
echo -e "${YELLOW}Command: $PYTEST_CMD${NC}"
echo -e "${YELLOW}Headless: $HEADLESS${NC}"
echo ""

if $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}  ✓ All GUI tests passed!${NC}"
    echo -e "${GREEN}===========================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}===========================================${NC}"
    echo -e "${RED}  ✗ Some GUI tests failed${NC}"
    echo -e "${RED}===========================================${NC}"

    # Show screenshots directory if tests failed
    if [ -d "tests/gui/screenshots" ]; then
        echo -e "${YELLOW}Screenshots saved in: tests/gui/screenshots/${NC}"
    fi

    # Offer to show logs
    if [ "$USE_DOCKER" = true ]; then
        echo ""
        echo -e "${YELLOW}To view service logs:${NC}"
        echo -e "  Backend: ${BLUE}docker-compose logs backend${NC}"
        echo -e "  Frontend: ${BLUE}docker-compose logs frontend${NC}"
    fi

    exit 1
fi
