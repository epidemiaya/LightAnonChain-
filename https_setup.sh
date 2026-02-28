#!/bin/bash
# LAC HTTPS Setup — запускати коли є домен
# Використання: ./https_setup.sh yourdomain.com

DOMAIN=$1
if [ -z "$DOMAIN" ]; then
  echo "Usage: ./https_setup.sh yourdomain.com"
  exit 1
fi

echo "🔒 Setting up HTTPS for $DOMAIN..."

# 1. Встановити nginx + certbot
apt-get update -qq
apt-get install -y nginx certbot python3-certbot-nginx

# 2. Nginx конфіг (HTTP спочатку для certbot challenge)
cat > /etc/nginx/sites-available/lac << NGINX
server {
    listen 80;
    server_name $DOMAIN;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL (certbot заповнить після запуску)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # LAC Frontend (static)
    root /var/www/lac-mobile;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # LAC Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:38400;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
        
        # WebSocket support (for future use)
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy no-referrer;
}
NGINX

ln -sf /etc/nginx/sites-available/lac /etc/nginx/sites-enabled/lac
rm -f /etc/nginx/sites-enabled/default

# 3. Тест конфігу
nginx -t && echo "✅ Nginx config OK"

# 4. Отримати SSL сертифікат
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect

# 5. Автооновлення сертифікату
echo "0 3 * * * root certbot renew --quiet" > /etc/cron.d/certbot-renew

# 6. Перезапустити nginx
systemctl restart nginx
systemctl enable nginx

echo ""
echo "✅ HTTPS готово!"
echo "   Сайт: https://$DOMAIN"
echo "   API:  https://$DOMAIN/api/"
echo ""
echo "⚠️  Не забудь оновити VITE_API_URL в .env:"
echo "   VITE_API_URL=https://$DOMAIN"
echo "   Потім: npm run build && cp -r dist/* /var/www/lac-mobile/"
