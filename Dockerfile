FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# Node.js is required for Security Track: Sensitive Models JavaScript execution
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    postgresql-client \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory and make run scripts executable
RUN mkdir -p /app/logs && \
    chmod +x run run_api_new.sh run_init_db.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port for API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run the API server
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
