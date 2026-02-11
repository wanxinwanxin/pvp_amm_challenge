# Multi-stage Dockerfile for PVP AMM Challenge - Railway Deployment
# This reduces final image size by ~2GB and speeds up deployment

# ============================================================================
# Stage 1: Build Rust wheel
# ============================================================================
FROM python:3.11-slim AS rust-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /build

# Copy only Rust project files
COPY amm_sim_rs ./amm_sim_rs

# Build Rust wheel
RUN pip install --no-cache-dir maturin && \
    cd amm_sim_rs && \
    maturin build --release

# ============================================================================
# Stage 2: Final runtime image
# ============================================================================
FROM python:3.11-slim

# Install only runtime dependencies (curl for health checks)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files (excluding Rust source since we have the wheel)
COPY requirements.txt requirements-pvp.txt pyproject.toml setup.py ./
COPY amm_competition ./amm_competition
COPY contracts ./contracts
COPY pvp_app ./pvp_app
COPY .streamlit ./.streamlit
COPY start.sh ./start.sh

# Make startup script executable
RUN chmod +x start.sh

# Copy pre-built Rust wheel from builder stage
COPY --from=rust-builder /build/amm_sim_rs/target/wheels/*.whl /tmp/

# Install all Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy && \
    pip install --no-cache-dir /tmp/*.whl && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -r requirements-pvp.txt && \
    rm -rf /tmp/*.whl

# Create data directory with proper permissions
RUN mkdir -p /app/data && chmod 755 /app/data

# Expose Streamlit port (Railway will use dynamic $PORT)
EXPOSE 8501

# Run Streamlit app via startup script
CMD ["./start.sh"]
