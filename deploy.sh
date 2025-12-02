#!/bin/bash

# APFC Monitor Service - Raspberry Pi Deployment Script
# This script automates the complete setup and deployment

set -e  # Exit on error

echo "=========================================="
echo "APFC Monitor Service - Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root for systemd setup
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Note: Some operations require sudo. You may be prompted for password.${NC}"
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}[1/8] Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 is not installed. Please install it first.${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "Found: $PYTHON_VERSION"

echo -e "${GREEN}[2/8] Creating Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

echo -e "${GREEN}[3/8] Activating virtual environment and installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Dependencies installed"

echo -e "${GREEN}[4/8] Creating .env file if it doesn't exist...${NC}"
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Modbus Configuration
COM_PORT=/dev/ttyUSB0
BAUD_RATE=9600
SLAVE_ID=1
EOF
    echo ".env file created with default values"
    echo -e "${YELLOW}Please edit .env file to match your hardware configuration${NC}"
else
    echo ".env file already exists"
fi

echo -e "${GREEN}[5/8] Creating systemd service file...${NC}"
SERVICE_FILE="/etc/systemd/system/apfc-monitor.service"
CURRENT_USER=${SUDO_USER:-$USER}
sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=APFC Relay Monitoring Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin"
ExecStart=$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/apfc_monitor.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/apfc-monitor.log
StandardError=append:/var/log/apfc-monitor-error.log

[Install]
WantedBy=multi-user.target
EOF
echo "Systemd service file created at $SERVICE_FILE"

echo -e "${GREEN}[6/8] Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload
echo "Systemd daemon reloaded"

echo -e "${GREEN}[7/8] Enabling service to start on boot...${NC}"
sudo systemctl enable apfc-monitor.service
echo "Service enabled"

echo -e "${GREEN}[8/8] Starting service...${NC}"
sudo systemctl start apfc-monitor.service
echo "Service started"

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Service Status:"
sudo systemctl status apfc-monitor.service --no-pager -l || true
echo ""
echo "Useful commands:"
echo "  Check status:    sudo systemctl status apfc-monitor"
echo "  View logs:       sudo tail -f /var/log/apfc-monitor.log"
echo "  Stop service:    sudo systemctl stop apfc-monitor"
echo "  Start service:   sudo systemctl start apfc-monitor"
echo "  Restart service: sudo systemctl restart apfc-monitor"
echo "  Disable service: sudo systemctl disable apfc-monitor"
echo ""
echo -e "${YELLOW}Important: Make sure to edit .env file with your correct COM_PORT${NC}"
echo ""

