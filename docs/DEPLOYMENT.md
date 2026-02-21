# LAC Testnet Deployment Guide

## Quick deploy on Ubuntu 22.04+ VPS

### 1. Server setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip nginx certbot python3-certbot-nginx nodejs npm git

# Clone repo
cd /opt
git clone https://github.com/YOUR_USERNAME/LightAnonChain.git
cd LightAnonChain
```

### 2. Run the node

```bash
cd lac-node
pip3 install -r requirements.txt

# Run in background with systemd (recommended)
sudo tee /etc/systemd/system/lac-node.service << 'EOF'
[Unit]
Description=LAC Blockchain Node
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/LightAnonChain/lac-node
ExecStart=/usr/bin/python3 lac_node.py
Restart=always
RestartSec=5
Environment=LAC_HOST=127.0.0.1
Environment=LAC_PORT=5000

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lac-node
sudo systemctl start lac-node

# Check status
sudo systemctl status lac-node
sudo journalctl -u lac-node -f  # live logs
```

### 3. Build mobile app

```bash
cd /opt/LightAnonChain/lac-mobile
npm install
npm run build
# Built files will be in lac-mobile/dist/
```

### 4. Nginx config

```bash
sudo tee /etc/nginx/sites-available/lac << 'EOF'
# API — proxy to node
server {
    listen 80;
    server_name testnet.YOUR_DOMAIN.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, X-Seed";

        if ($request_method = OPTIONS) {
            return 204;
        }
    }
}

# Mobile App
server {
    listen 80;
    server_name app.YOUR_DOMAIN.com;
    root /opt/LightAnonChain/lac-mobile/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}

# Explorer
server {
    listen 80;
    server_name explorer.YOUR_DOMAIN.com;
    root /opt/LightAnonChain/explorer;
    index explorer.html;
}
EOF

sudo ln -sf /etc/nginx/sites-available/lac /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. SSL (free, via Let's Encrypt)

```bash
sudo certbot --nginx -d testnet.YOUR_DOMAIN.com -d app.YOUR_DOMAIN.com -d explorer.YOUR_DOMAIN.com
# Follow prompts, enter email, agree to terms
# Certificates auto-renew
```

### 6. Firewall

```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 7. Verify

```bash
curl https://testnet.YOUR_DOMAIN.com/api/chain/height
# Should return: {"ok":true,"height":...}
```

## Updating

```bash
cd /opt/LightAnonChain
git pull
sudo systemctl restart lac-node

# If mobile app changed:
cd lac-mobile && npm run build
```

## Monitoring

```bash
# Node logs
sudo journalctl -u lac-node -f

# Check if node is running
curl localhost:5000/api/chain/height

# Disk usage (blockchain data)
du -sh /opt/LightAnonChain/lac-node/data/
```

## Recommended VPS providers

| Provider | Plan | Price | Notes |
|----------|------|-------|-------|
| Hetzner | CX22 | €4.50/mo | 2 vCPU, 4GB RAM, EU |
| Contabo | VPS S | €5.99/mo | 4 vCPU, 8GB RAM, EU |
| DigitalOcean | Basic | $6/mo | 1 vCPU, 1GB RAM, worldwide |
