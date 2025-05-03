FROM itsafeaturemythic/mythic_python_go:latest

# Core Python dependencies (cross-platform)
RUN pip3 install \
    python-dotenv \
    mythic_container==0.5.25 \
    psutil \
    requests \
    cryptography \
    pefile \
    python-magic

# Platform-specific dependencies
RUN if [ "$(uname)" = "Darwin" ]; then \
    # macOS requirements
    pip3 install \
        pyobjc-core \
        pyobjc-framework-Cocoa \
        xattr; \
    else \
    # Linux requirements
    apt-get update && apt-get install -y \
        file \
        libmagic1 && \
    rm -rf /var/lib/apt/lists/* ; \
    fi

COPY . /Mythic/

WORKDIR /Mythic/

CMD ["python3", "main.py"]