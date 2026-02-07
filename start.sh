#!/bin/bash
# Startup script for Railway deployment with debugging

echo "====================================="
echo "PVP AMM Challenge - Starting Up"
echo "====================================="

# Print environment info
echo "PORT: ${PORT:-8501}"
echo "RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-local}"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo ""

# Ensure data directory exists
echo "Creating data directory..."
mkdir -p /app/data
echo "✓ Data directory ready"
echo ""

# Check if Rust simulation engine is installed
echo "Checking Rust simulation engine..."
python -c "import amm_sim_rs; print('✓ amm_sim_rs loaded successfully')" || {
    echo "✗ Failed to import amm_sim_rs"
    exit 1
}
echo ""

# Start Streamlit with port from environment
PORT=${PORT:-8501}
echo "Starting Streamlit on port $PORT..."
echo "Health check will be available at: http://localhost:$PORT/_stcore/health"
echo ""

exec streamlit run pvp_app/app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableXsrfProtection=true \
    --server.enableCORS=false
