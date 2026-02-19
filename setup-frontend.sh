#!/bin/bash
# Quick Start Script for Frontend Development

echo "Installing frontend dependencies..."
cd frontend
npm install

echo ""
echo "Building frontend..."
npm run build

cd ..
echo ""
echo "Frontend built successfully!"
echo "Static files are in the 'static' directory"
echo ""
echo "To start the backend, run: python dashboard.py"
