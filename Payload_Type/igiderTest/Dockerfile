FROM python:3.10-slim-buster

WORKDIR /Mythic/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    gcc \
    g++ \
    make \
    unzip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN echo "mythic-container>=0.2.2\nrequests>=2.28.0\nasyncio>=3.4.3\npybase64>=1.2.3" > requirements.txt

RUN pip install -r requirements.txt

# Now copy the actual code
COPY . .

# Start the service
CMD ["python", "main.py"]