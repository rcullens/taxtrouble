#!/bin/bash
set -e

echo "🚀 Building TaxTrouble Linux Desktop App..."

# Install dependencies
pip install -r requirements.txt pyinstaller

# Build the app
pyinstaller \
  --onefile \
  --windowed \
  --name "taxtrouble" \
  --add-data "../backend:backend" \
  --add-data "../frontend/build:frontend" \
  --icon "../assets/icon.png" \
  --hidden-import "uvicorn.logging" \
  --hidden-import "uvicorn.loops" \
  --hidden-import "uvicorn.loops.auto" \
  app.py

echo "✅ Build complete!"
echo "Binary: dist/taxtrouble"
echo ""
echo "To create AppImage, run:"
echo "  appimagetool dist/taxtrouble taxtrouble-x86_64.AppImage"