# ============================================================================
# Stage 1: Rust Builder (with dependency caching)
# ============================================================================
FROM rust:1.75-slim AS rust-builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests first (cached layer)
COPY amm_sim_rs/Cargo.toml amm_sim_rs/Cargo.lock* ./amm_sim_rs/
COPY amm_sim_rs/pyproject.toml ./amm_sim_rs/

# Create dummy source to build dependencies
RUN mkdir -p amm_sim_rs/src amm_sim_rs/benches && \
    echo "pub fn dummy() {}" > amm_sim_rs/src/lib.rs && \
    echo "fn main() {}" > amm_sim_rs/benches/simulation_bench.rs

# Pre-build dependencies (this layer caches 249 crates)
RUN cd amm_sim_rs && cargo build --profile release-ci

# Remove dummy source
RUN rm -rf amm_sim_rs/src amm_sim_rs/benches

# Copy real source code
COPY amm_sim_rs/src ./amm_sim_rs/src

# Build application (dependencies already compiled)
RUN cd amm_sim_rs && cargo build --profile release-ci

# ============================================================================
# Stage 2: Python Builder (wheel creation)
# ============================================================================
FROM python:3.11-slim AS python-builder

WORKDIR /build

# Install maturin
RUN pip install --no-cache-dir maturin

# Copy built Rust artifacts from Stage 1
COPY --from=rust-builder /build/amm_sim_rs ./amm_sim_rs

# Build wheel from pre-compiled Rust library
RUN cd amm_sim_rs && maturin build --profile release-ci --bindings pyo3

# ============================================================================
# Stage 3: Runtime (minimal final image)
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install wheel from builder
COPY --from=python-builder /build/amm_sim_rs/target/wheels/*.whl /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl

# Install Python dependencies (cached layer)
COPY requirements-pvp.txt .
RUN pip install --no-cache-dir -r requirements-pvp.txt

# Copy application code (changes frequently - last)
COPY pyproject.toml setup.py* ./
COPY amm_competition/ ./amm_competition/
COPY pvp_app/ ./pvp_app/
COPY start.sh ./
RUN chmod +x start.sh

# Install the application package
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run application
CMD ["./start.sh"]
