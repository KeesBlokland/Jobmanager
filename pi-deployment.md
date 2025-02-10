# Raspberry Pi Job Manager Deployment Guide

## Hardware Requirements
- Raspberry Pi (Model 3B+ or 4 recommended)
- MicroSD card (16GB or larger)
- Power supply
- Optional: Case for the Pi
- Optional: Small display (7" official Pi display works well)

## Initial Setup

### 1. Operating System Installation
```bash
# Download and install Raspberry Pi OS Lite (32-bit)
# Use Raspberry Pi Imager for easiest installation
```

### 2. First Boot Configuration
```bash
# Initial system update
sudo apt update
sudo apt upgrade -y

# Set timezone
sudo timedatectl set-timezone Europe/Amsterdam

# Enable SSH if needed
sudo raspi-config
# Interface Options -> SSH -> Enable
```

### 3. Install Required Packages
```bash
# Install Python and required system packages
sudo apt install -y python3-pip python3-venv git nginx

# Install PostgreSQL for better database performance (optional)
sudo apt install -y postgresql postgresql-contrib
```

### 4. Create Project Directory
```bash
# Create project directory
mkdir -p /home/pi/jobmanager
cd /home/pi/jobmanager

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate
```

### 5. Install Python Dependencies
```bash
# Create requirements.txt
cat > requirements.txt << EOL
Flask==3.0.0
python-dotenv==1.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.9  # If using PostgreSQL
EOL

# Install requirements
pip install -r requirements.txt
```

### 6. Setup Application

```bash
# Clone or copy application files
# Assuming you've copied the files to a USB drive or transferred them somehow
cp -r /path/to/your/files/* /home/pi/jobmanager/

# Create instance directory
mkdir -p instance

# Initialize database
python init_db.py
```

### 7. Create System Service
```bash
# Create systemd service file
sudo nano /etc/systemd/system/jobmanager.service

[Unit]
Description=Job Manager Flask Application
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/jobmanager
Environment="PATH=/home/pi/jobmanager/venv/bin"
ExecStart=/home/pi/jobmanager/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### 8. Configure Nginx
```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/jobmanager

server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable the site
sudo ln -s /etc/nginx/sites-available/jobmanager /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
```

### 9. Start Services
```bash
# Start and enable services
sudo systemctl start jobmanager
sudo systemctl enable jobmanager
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 10. Setup Auto-start Browser (if using display)
```bash
# Install Chromium
sudo apt install -y chromium-browser

# Create autostart directory
mkdir -p /home/pi/.config/autostart

# Create autostart entry
cat > /home/pi/.config/autostart/jobmanager.desktop << EOL
[Desktop Entry]
Type=Application
Name=Job Manager
Exec=chromium-browser --kiosk http://localhost
EOL
```

## Daily Operations

### Backup System
```bash
# Create backup directory
mkdir -p /home/pi/backups

# Add to crontab (backup daily at 1 AM)
(crontab -l 2>/dev/null; echo "0 1 * * * /home/pi/jobmanager/backup.py") | crontab -
```

### Maintenance Commands
```bash
# View logs
sudo journalctl -u jobmanager

# Restart application
sudo systemctl restart jobmanager

# Update system
sudo apt update && sudo apt upgrade -y
```

## Security Considerations

1. Change default password:
```bash
passwd
```

2. Enable firewall:
```bash
sudo apt install -y ufw
sudo ufw allow 80
sudo ufw allow 22  # if you need SSH
sudo ufw enable
```

## Network Access

- Access the application from any device on the same network:
  http://[raspberry-pi-ip-address]

- To find the IP address:
```bash
hostname -I
```

## Troubleshooting

1. If the application doesn't start:
```bash
sudo systemctl status jobmanager
```

2. Check Nginx errors:
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

3. Application logs:
```bash
tail -f /home/pi/jobmanager/logs/jobmanager.log
```

## Backup Strategy

1. Database backups:
- Automated daily backups via cron
- Manual backup through web interface
- Backups stored in /home/pi/backups

2. System backup:
- Periodic full SD card backup recommended
- Use tools like dd or rpi-clone

## Recovery Procedures

1. Database recovery:
```bash
# Stop the service
sudo systemctl stop jobmanager

# Restore from backup
cp /home/pi/backups/[backup-file] /home/pi/jobmanager/instance/jobmanager.db

# Start the service
sudo systemctl start jobmanager
```

2. Full system recovery:
- Keep a backup SD card with working installation
- Document any custom configurations

## Updating the Application

1. Backup current version:
```bash
cd /home/pi/jobmanager
./backup.py
```

2. Update application files:
```bash
# Stop service
sudo systemctl stop jobmanager

# Update files
cp -r /path/to/new/files/* /home/pi/jobmanager/

# Start service
sudo systemctl start jobmanager
```
