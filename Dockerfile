FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY dependencies.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r dependencies.txt

# Copy application code
COPY . .

# Make run script executable
RUN chmod +x run

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (if running as a web service)
EXPOSE 8000

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "main.py"]