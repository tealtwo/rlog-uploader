#!/bin/bash
# Quick deployment script for Rlog Uploader

set -e

echo "================================================"
echo "Comma 3X Rlog Auto-Uploader - Docker Deployment"
echo "================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed!"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed!"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker found: $(docker --version)"
echo "✓ Docker Compose found: $(docker-compose --version)"
echo ""

# Check if SSH keys exist
if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "WARNING: No SSH keys found in ~/.ssh/"
    echo "You'll need to add your SSH key to access the Comma 3X"
    echo ""
fi

# Build and start
echo "Building Docker image..."
docker-compose build

echo ""
echo "Starting container..."
docker-compose up -d

echo ""
echo "Waiting for service to start..."
sleep 3

# Check if container is running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "================================================"
    echo "SUCCESS! Rlog Uploader is running!"
    echo "================================================"
    echo ""
    echo "Web Interface: http://localhost:3445"
    echo ""
    echo "Useful commands:"
    echo "  View logs:      docker-compose logs -f"
    echo "  Stop service:   docker-compose down"
    echo "  Restart:        docker-compose restart"
    echo "  View status:    docker-compose ps"
    echo ""
    echo "The service will auto-start on system reboot."
else
    echo ""
    echo "ERROR: Container failed to start!"
    echo "Check logs with: docker-compose logs"
    exit 1
fi
