# APFC Monitor Service - Raspberry Pi Deployment

## Quick Start (One Command)

After cloning the repository on your Raspberry Pi, run:

```bash
chmod +x deploy.sh
./deploy.sh
```

This single script will:
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Create .env configuration file
- ✅ Set up systemd service
- ✅ Enable auto-start on boot
- ✅ Start the service

## Manual Steps (if needed)

### 1. Clone Repository
```bash
cd ~
git clone https://github.com/vineet-chelsea/RS485-APFC.git
cd RS485-APFC
```

### 2. Run Deployment Script
```bash
chmod +x deploy.sh
./deploy.sh
```

### 3. Configure Serial Port

Edit the `.env` file to set your correct serial port:

```bash
nano .env
```

Common serial ports on Raspberry Pi:
- `/dev/ttyUSB0` - USB to Serial adapter
- `/dev/ttyAMA0` - GPIO serial (UART)
- `/dev/ttyS0` - Serial port

### 4. Verify Service is Running

```bash
sudo systemctl status apfc-monitor
```

## Service Management

### View Logs
```bash
# Real-time logs
sudo tail -f /var/log/apfc-monitor.log

# Error logs
sudo tail -f /var/log/apfc-monitor-error.log

# Last 50 lines
sudo tail -n 50 /var/log/apfc-monitor.log
```

### Control Service
```bash
# Start service
sudo systemctl start apfc-monitor

# Stop service
sudo systemctl stop apfc-monitor

# Restart service
sudo systemctl restart apfc-monitor

# Check status
sudo systemctl status apfc-monitor

# Disable auto-start
sudo systemctl disable apfc-monitor

# Enable auto-start
sudo systemctl enable apfc-monitor
```

## Troubleshooting

### Service won't start
1. Check logs: `sudo journalctl -u apfc-monitor -n 50`
2. Verify .env file exists and has correct COM_PORT
3. Check serial port permissions: `ls -l /dev/ttyUSB0`
4. Add user to dialout group: `sudo usermod -a -G dialout $USER` (then logout/login)

### Permission denied on serial port
```bash
sudo usermod -a -G dialout $USER
# Logout and login again, or reboot
```

### Service keeps restarting
Check error logs: `sudo tail -f /var/log/apfc-monitor-error.log`

### Test manually (without service)
```bash
cd ~/RS485-APFC
source venv/bin/activate
python3 apfc_monitor.py
```

## Configuration

Edit `.env` file to change:
- `COM_PORT` - Serial port device
- `BAUD_RATE` - Modbus baud rate (default: 9600)
- `SLAVE_ID` - Modbus slave ID (default: 1)

## Files Created

- `venv/` - Python virtual environment
- `.env` - Configuration file (created from .env.example)
- `/etc/systemd/system/apfc-monitor.service` - Systemd service
- `/var/log/apfc-monitor.log` - Service output log
- `/var/log/apfc-monitor-error.log` - Service error log

