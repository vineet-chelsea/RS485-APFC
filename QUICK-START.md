# Quick Start - Raspberry Pi Deployment

## One Command Setup

After cloning the repository, simply run:

```bash
chmod +x deploy.sh && ./deploy.sh
```

That's it! The script will:
1. ✅ Set up Python virtual environment
2. ✅ Install all dependencies  
3. ✅ Create configuration file
4. ✅ Install and start the service
5. ✅ Enable auto-start on boot

## After Deployment

### Check if it's running:
```bash
sudo systemctl status apfc-monitor
```

### View live logs:
```bash
sudo tail -f /var/log/apfc-monitor.log
```

### Edit configuration (if needed):
```bash
nano .env
# Then restart: sudo systemctl restart apfc-monitor
```

## That's All!

Your APFC monitor service is now running and will automatically start on every boot.

