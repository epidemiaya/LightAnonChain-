#!/bin/bash
# LAC Performance Deploy — запускати на сервері
set -e
echo "🚀 LAC Performance upgrade..."

# ── 1. Gunicorn ────────────────────────────────────────────────────────────
echo "📦 Installing gunicorn..."
/root/LightAnonChain-/lac-node/.venv/bin/pip install gunicorn --quiet

cat > /root/LightAnonChain-/lac-node/run.sh << 'EOF'
#!/usr/bin/env bash
set -e
cd /root/LightAnonChain-/lac-node
exec .venv/bin/gunicorn lac_node:app \
  --workers 3 \
  --worker-class gthread \
  --threads 8 \
  --bind 0.0.0.0:38400 \
  --timeout 120 \
  --keep-alive 5 \
  --log-level warning \
  --access-logfile - \
  -- --datadir /root/LightAnonChain-/lac-node/data --port 38400
EOF
chmod +x /root/LightAnonChain-/lac-node/run.sh
echo "✅ Gunicorn configured (3 workers × 8 threads = 24 parallel requests)"

# ── 2. Nginx — медіа напряму з диску, без Python ─────────────────────────
echo "🌐 Configuring nginx..."
CONF=$(grep -rl "lac-beta\|38400" /etc/nginx/ 2>/dev/null | head -1)
if [ -z "$CONF" ]; then
  echo "❌ Nginx config not found — add manually"
else
  cp "$CONF" "${CONF}.bak"
  
  # Додаємо media location перед location /api/
  if ! grep -q "location /api/media/" "$CONF"; then
    sed -i '/location \/api\//i\
    # Serve media files directly — bypasses Python completely\
    location /api/media/ {\
        alias /root/LightAnonChain-/lac-node/data/media/;\
        expires 5m;\
        add_header Cache-Control "public, max-age=300";\
        add_header X-Content-Type-Options nosniff;\
        try_files $uri =404;\
    }\
' "$CONF"
    echo "✅ Nginx media route added (direct from disk)"
  else
    echo "ℹ️ Media route already exists"
  fi

  # client_max_body_size якщо немає
  if ! grep -q "client_max_body_size" "$CONF"; then
    sed -i '/server_name/a\    client_max_body_size 30m;' "$CONF"
    echo "✅ client_max_body_size 30m added"
  fi

  # proxy timeouts якщо немає
  if ! grep -q "proxy_read_timeout" "$CONF"; then
    sed -i '/proxy_pass http.*38400/a\        proxy_read_timeout 120s;\n        proxy_buffering off;' "$CONF"
    echo "✅ proxy timeouts added"
  fi

  nginx -t && systemctl reload nginx && echo "✅ Nginx reloaded"
fi

# ── 3. Deploy new code ─────────────────────────────────────────────────────
echo "📥 Deploying code..."
cd /opt/LightAnonChain-
git pull

cp lac-node/lac_node.py /root/LightAnonChain-/lac-node/
cp lac-mobile/src/App.jsx /root/LightAnonChain-/lac-mobile/src/

# Build frontend
cd /root/LightAnonChain-/lac-mobile
npm run build --silent
cp -r dist/* /var/www/lac-mobile/
echo "✅ Frontend built"

# ── 4. Restart ────────────────────────────────────────────────────────────
systemctl restart lac-node
sleep 3
systemctl is-active lac-node && echo "✅ lac-node running" || echo "❌ lac-node failed — check: journalctl -u lac-node -n 30"

echo ""
echo "✅ Done! Expected improvement:"
echo "   • API: 1 thread → 24 parallel (gunicorn)"  
echo "   • Images: Python → nginx direct (10x faster)"
echo "   • Inbox: 33KB → ~1KB per poll"
