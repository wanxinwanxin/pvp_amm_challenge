# Dockerfile for PVP AMM Challenge - Railway Deployment

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (needed for amm_sim_rs)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies for the base project
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir numpy  # Pre-install numpy for faster build

# Build and install the Rust simulation engine
RUN cd amm_sim_rs && \
    pip install --no-cache-dir maturin && \
    maturin build --release && \
    pip install --no-cache-dir target/wheels/*.whl

# Install Python package and PVP dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir -r requirements-pvp.txt

# Create data directory
RUN mkdir -p /app/data

# Expose Streamlit port (Railway will use dynamic $PORT)
EXPOSE 8501

# Note: Railway handles health checks via railway.toml
# No HEALTHCHECK needed here to avoid port conflicts

# Run Streamlit app via startup script
CMD ["./start.sh"]
