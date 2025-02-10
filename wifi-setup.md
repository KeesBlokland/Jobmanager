# Raspberry Pi Auto-Hotspot Configuration

## Overview
This setup creates a fallback system where:
1. Pi tries to connect to configured WiFi
2. If no connection possible, creates its own hotspot
3. Provides web interface for WiFi configuration
4. Auto-switches between modes as needed

## Installation Steps

### 1. Install Required Packages
```bash
sudo apt update
sudo apt install -y hostapd dnsmasq netfilter-persistent iptables-persistent
```

### 2. Configure Hostapd (Access Point)
```bash
# Create hostapd configuration
sudo nano /etc/hostapd/hostapd.conf

interface=wlan0
driver=nl80211
ssid=JobManager
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=jobmanager123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

### 3. Configure DNSMASQ (DHCP Server)
```bash
# Backup original configuration
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig

# Create new configuration
sudo nano /etc/dnsmasq.conf

interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=wlan
address=/jobmanager.local/192.168.4.1
```

### 4. Create Auto-Hotspot Script
```bash
# Create script
sudo nano /usr/local/bin/auto_hotspot.sh

#!/bin/bash

# Function to start access point
start_ap() {
    sudo systemctl stop dhcpcd
    sudo ip link set dev wlan0 down
    sudo ip addr add 192.168.4.1/24 dev wlan0
    sudo ip link set dev wlan0 up
    sudo systemctl start hostapd
    sudo systemctl start dnsmasq
}

# Function to start client mode
start_client() {
    sudo systemctl stop hostapd
    sudo systemctl stop dnsmasq
    sudo systemctl start dhcpcd
}

# Check if we can connect to configured WiFi
if iwlist wlan0 scan | grep -q "ESSID:\"$WIFI_SSID\""; then
    start_client
else
    start_ap
fi

# Make script executable
sudo chmod +x /usr/local/bin/auto_hotspot.sh
```

### 5. Create WiFi Configuration Web Interface

```python
# wifi_config.py
from flask import Blueprint, render_template, request, redirect, url_for
import subprocess
import os

bp = Blueprint('wifi', __name__)

@bp.route('/wifi', methods=['GET', 'POST'])
def wifi_config():
    if request.method == 'POST':
        ssid = request.form['ssid']
        password = request.form['password']
        
        # Update wpa_supplicant configuration
        with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f:
            f.write(f'''
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=DE

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
''')
        
        # Reboot system to apply changes
        subprocess.run(['sudo', 'reboot'])
        return "System is rebooting..."
        
    # Scan for available networks
    networks = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan'])
    networks = networks.decode('utf-8')
    ssids = []
    for line in networks.split('\n'):
        if 'ESSID' in line:
            ssid = line.split(':')[1].strip('"')
            if ssid: ssids.append(ssid)
            
    return render_template('wifi_config.html', networks=ssids)
```

### 6. Create WiFi Configuration Template

```html
<!-- wifi_config.html -->
{% extends "base.html" %}

{% block content %}
<div class="form-container">
    <h2>WiFi Configuration</h2>
    <form method="post">
        <div class="form-group">
            <label>Select Network</label>
            <select name="ssid" required>
                {% for network in networks %}
                <option value="{{ network }}">{{ network }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit" class="action-btn save-btn">Connect</button>
    </form>
</div>
{% endblock %}
```

### 7. Auto-start Configuration

```bash
# Create systemd service for auto-hotspot
sudo nano /etc/systemd/system/auto-hotspot.service

[Unit]
Description=Auto Hotspot Service
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/auto_hotspot.sh

[Install]
WantedBy=multi-user.target

# Enable service
sudo systemctl enable auto-hotspot.service
```

### 8. Network Interface Configuration
```bash
# Configure static fallback IP
sudo nano /etc/dhcpcd.conf

interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
```

## Usage Instructions

1. On first boot, Pi will create hotspot named "JobManager"
2. Connect to hotspot using password "jobmanager123"
3. Access http://192.168.4.1 or http://jobmanager.local
4. Go to WiFi configuration page
5. Select your network and enter password
6. System will reboot and try to connect to your network
7. If connection fails, it will fall back to hotspot mode

## Troubleshooting

1. Check hotspot status:
```bash
sudo systemctl status hostapd
sudo systemctl status dnsmasq
```

2. Check WiFi connection:
```bash
iwconfig wlan0
```

3. View connection logs:
```bash
sudo journalctl -u auto-hotspot
```

## Security Notes

1. Change default hotspot password in hostapd.conf
2. Consider adding authentication to WiFi configuration page
3. Use HTTPS for configuration interface if possible
4. Regularly update system for security patches

