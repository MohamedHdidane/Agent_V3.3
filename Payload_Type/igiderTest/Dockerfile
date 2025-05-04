FROM python:3.9-slim

# Set working directory
WORKDIR /Mythic/

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    mythic-payloadtype-container \
    aiohttp \
    pyinstaller

# Copy payload type files
COPY . /Mythic/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Start payload container when container starts
ENTRYPOINT ["python", "main.py"]