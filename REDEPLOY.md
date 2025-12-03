# How to Redeploy on Raspberry Pi

## Quick Redeploy (After Code Updates)

If you've updated the code and want to redeploy:

### Option 1: Simple Restart (if only .env changed)
```bash
# Edit .env if needed
nano .env

# Restart the service
sudo systemctl restart apfc-monitor
```

### Option 2: Full Redeploy (after git pull)
```bash
# Navigate to project directory
cd ~/RS485-APFC

# Pull latest changes
git pull

# Restart service (it will use new code)
sudo systemctl restart apfc-monitor

# Check status
sudo systemctl status apfc-monitor
```

### Option 3: Complete Fresh Deploy
```bash
# Navigate to project directory
cd ~/RS485-APFC

# Pull latest changes
git pull

# Stop existing service
sudo systemctl stop apfc-monitor
sudo systemctl disable apfc-monitor

# Remove old virtual environment (optional, for clean install)
rm -rf venv

# Run deployment script again
./deploy.sh
```

## After Changing Serial Port

If you changed the serial port (e.g., to /dev/ttyACM0):

1. **Edit .env file:**
   ```bash
   nano .env
   ```
   Change `COM_PORT=/dev/ttyACM0` (or your port)

2. **Restart service:**
   ```bash
   sudo systemctl restart apfc-monitor
   ```

3. **Check logs to verify:**
   ```bash
   sudo tail -f /var/log/apfc-monitor.log
   ```

## Verify Serial Port

To check what serial ports are available:
```bash
ls -l /dev/ttyACM* /dev/ttyUSB* /dev/ttyAMA*
```

To check if your port exists:
```bash
ls -l /dev/ttyACM0
```

## Troubleshooting

If service fails to start after port change:
1. Check port exists: `ls -l /dev/ttyACM0`
2. Check permissions: User should be in `dialout` group
3. Check logs: `sudo journalctl -u apfc-monitor -n 50`

