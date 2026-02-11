#!/bin/bash
# Startup script for Railway deployment with debugging
set -e  # Exit on error

echo "====================================="
echo "PVP AMM Challenge - Starting Up"
echo "====================================="

# Print environment info
echo "PORT: ${PORT:-8501}"
echo "RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-local}"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo ""

# Ensure data directory exists with proper permissions
echo "Creating data directory..."
mkdir -p /app/data
chmod 755 /app/data
echo "✓ Data directory ready at /app/data"
ls -la /app/data || echo "Directory empty"
echo ""

# Check if Rust simulation engine is installed
echo "Checking Rust simulation engine..."
python -c "import amm_sim_rs; print('✓ amm_sim_rs loaded successfully')" || {
    echo "✗ Failed to import amm_sim_rs"
    echo "Python path:"
    python -c "import sys; print('\n'.join(sys.path))"
    exit 1
}
echo ""

# Verify database module can be imported
echo "Verifying Python modules..."
python -c "from pvp_app.database import Database; print('✓ Database module OK')" || {
    echo "✗ Failed to import Database module"
    exit 1
}
echo ""

# Start Streamlit with port from environment
PORT=${PORT:-8501}
echo "Starting Streamlit on port $PORT..."
echo "Server will bind to 0.0.0.0:$PORT"
echo "Health check endpoint: /_stcore/health"
echo ""

exec streamlit run pvp_app/app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableXsrfProtection=true \
    --server.enableCORS=false
