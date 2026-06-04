#!/bin/bash
# Warframe Relic Tracker - Linux/macOS Build Script
set -e

echo "========================================="
echo "  Warframe Relic Tracker - Build Script"
echo "========================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found."
    exit 1
fi

# Install dependencies
echo "Installing build dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt 2>/dev/null || true
python3 -m pip install pyinstaller

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf build/ dist/

# Build
echo ""
echo "Building standalone executable..."
python3 -m PyInstaller \
    installer/warframe-relic-tracker.spec \
    --onefile \
    --name RelicTracker \
    --clean

echo ""
echo "========================================="
echo "  Build complete!"
echo "  Output: dist/RelicTracker"
echo "========================================="
echo ""
echo "Run with: ./dist/RelicTracker"
echo "The app will be available at http://127.0.0.1:8420"
