#!/bin/bash

# Setup script for PVP AMM Challenge (with virtual environment)

echo "🚀 Setting up PVP AMM Challenge..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✨ Activating virtual environment..."
source venv/bin/activate

# Install Rust if needed (for building amm_sim_rs)
if ! command -v rustc &> /dev/null; then
    echo "🦀 Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
fi

# Build Rust simulation engine if needed
if [ ! -f "amm_sim_rs/target/release/libamm_sim_rs.so" ] && [ ! -f "amm_sim_rs/target/release/libamm_sim_rs.dylib" ]; then
    echo "⚙️  Building Rust simulation engine (this takes ~5 minutes)..."
    cd amm_sim_rs
    pip install maturin
    maturin develop --release
    cd ..
else
    echo "✅ Rust engine already built"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -e .
pip install -r requirements-pvp.txt

# Seed database if empty
if [ ! -f "data/strategies.db" ]; then
    echo "🌱 Creating database and seeding with sample strategies..."
    python pvp_app/seed_data.py
else
    echo "✅ Database already exists"
fi

# Run Streamlit app
echo ""
echo "✨ Launching app at http://localhost:8501"
echo "📝 Press Ctrl+C to stop"
echo ""
streamlit run pvp_app/app.py
