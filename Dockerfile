# Professional PDF to JSON Converter
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Create output directory
RUN mkdir -p /app/output

# Set entry point
ENTRYPOINT ["python", "src/cli.py"]

# Default arguments
CMD ["--help"]
