# Remote Installation System

## Server-Side Setup (/var/www/html/jobmanager/)

### 1. Version Control File
```bash
# versions.json
{
    "latest": "1.0.0",
    "versions": {
        "1.0.0": {
            "file": "jobmanager_1.0.0.zip",
            "md5": "CHECKSUM_HERE",
            "release_date": "2025-02-09",
            "description": "Initial release"
        }
    }
}
```

### 2. Installation Script
```bash
#!/bin/bash
# install.sh - Place this on your server

# Configuration
REPO_URL="https://your-server.com/jobmanager"
INSTALL_DIR="/home/pi/jobmanager"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Job Manager Installation Script"
echo "------------------------------"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Function to show progress
show_progress() {
    echo -n "Installing: "
    while :; do
        echo -n "."
        sleep 1
    done
}

# Start progress indicator in background
show_progress &
PROGRESS_PID=$!

# Ensure clean state
cleanup() {
    kill $PROGRESS_PID 2>/dev/null
    echo -e "\nCleaning up..."
}
trap cleanup EXIT

# Create installation directory
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Download version info
echo "Checking for latest version..."
curl -s $REPO_URL/versions.json > versions.json

LATEST_VERSION=$(jq -r '.latest' versions.json)
DOWNLOAD_URL="$REPO_URL/jobmanager_${LATEST_VERSION}.zip"

# Download and verify package
echo "Downloading version ${LATEST_VERSION}..."
curl -O $DOWNLOAD_URL

# Verify checksum
EXPECTED_MD5=$(jq -r ".versions.\"$LATEST_VERSION\".md5" versions.json)
ACTUAL_MD5=$(md5sum jobmanager_${LATEST_VERSION}.zip | cut -d' ' -f1)

if [ "$EXPECTED_MD5" != "$ACTUAL_MD5" ]; then
    echo -e "${RED}Checksum verification failed${NC}"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
apt update
apt install -y python3-pip python3-venv nginx

# Extract package
unzip -o jobmanager_${LATEST_VERSION}.zip
rm jobmanager_${LATEST_VERSION}.zip

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize database
python init_db.py

# Setup services
cp systemd/jobmanager.service /etc/systemd/system/
systemctl enable jobmanager
systemctl start jobmanager

# Configure nginx
cp nginx/jobmanager /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/jobmanager /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

# Kill progress indicator and show completion
kill $PROGRESS_PID
echo -e "\n${GREEN}Installation complete!${NC}"
echo "Access your Job Manager at: http://$(hostname -I | awk '{print $1}')"
```

### 3. Update Script
```bash
#!/bin/bash
# update.sh - Include this in the application package

REPO_URL="https://your-server.com/jobmanager"
INSTALL_DIR="/home/pi/jobmanager"

echo "Checking for updates..."

# Get current version
CURRENT_VERSION=$(cat version.txt)
curl -s $REPO_URL/versions.json > versions.json

LATEST_VERSION=$(jq -r '.latest' versions.json)

if [ "$CURRENT_VERSION" == "$LATEST_VERSION" ]; then
    echo "Already running latest version ($CURRENT_VERSION)"
    exit 0
fi

echo "New version available: $LATEST_VERSION"
echo "Current version: $CURRENT_VERSION"
read -p "Update now? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Backup current installation
    ./backup.py
    
    # Download new version
    curl -O $REPO_URL/jobmanager_${LATEST_VERSION}.zip
    
    # Verify checksum
    EXPECTED_MD5=$(jq -r ".versions.\"$LATEST_VERSION\".md5" versions.json)
    ACTUAL_MD5=$(md5sum jobmanager_${LATEST_VERSION}.zip | cut -d' ' -f1)
    
    if [ "$EXPECTED_MD5" != "$ACTUAL_MD5" ]; then
        echo "Checksum verification failed"
        exit 1
    fi
    
    # Stop services
    sudo systemctl stop jobmanager
    
    # Extract update
    unzip -o jobmanager_${LATEST_VERSION}.zip
    rm jobmanager_${LATEST_VERSION}.zip
    
    # Update dependencies
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Run any migrations
    python migrate.py
    
    # Start services
    sudo systemctl start jobmanager
    
    echo "Update complete!"
fi
```

## Setup Instructions

1. On your server:
```bash
# Create directory structure
sudo mkdir -p /var/www/html/jobmanager
cd /var/www/html/jobmanager

# Add version control file
sudo nano versions.json  # Add content from above

# Add installation script
sudo nano install.sh     # Add content from above
sudo chmod +x install.sh

# Create initial package
zip -r jobmanager_1.0.0.zip /path/to/your/jobmanager/*
md5sum jobmanager_1.0.0.zip  # Update checksum in versions.json
```

2. On the Raspberry Pi (one-line installation):
```bash
curl -s https://your-server.com/jobmanager/install.sh | sudo bash
```

## Distribution Process

1. For new versions:
- Update application files
- Create new zip package
- Update versions.json with new version info
- Upload to server

2. Users can update by:
- Using built-in update checker in web interface
- Running update.sh manually

## Security Considerations

1. Use HTTPS for file distribution
2. Sign packages with GPG
3. Verify server SSL certificate
4. Add checksum verification
5. Consider adding authentication for updates

## Monitoring

You could add simple monitoring to your server:
```python
# monitor.py - Basic installation monitoring
from flask import Flask, request
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/report', methods=['POST'])
def report():
    data = request.json
    with open('installations.json', 'a') as f:
        data['timestamp'] = datetime.now().isoformat()
        json.dump(data, f)
        f.write('\n')
    return {"status": "ok"}
```

This would let you track:
- Number of installations
- Versions in use
- Update success rate
- Usage patterns

