"""
LAC Redis Cache Patch
=====================
Кешує найважчі API endpoints:
  /api/profile      — 5 сек
  /api/inbox        — 3 сек  
  /api/groups       — 10 сек
  /api/wallet/mining — 15 сек
  /api/chain/height  — 5 сек

Встановлення:
  pip install redis
  apt install redis-server -y
  systemctl enable redis && systemctl start redis
  
Підключення до lac_node.py:
  Додати на початку файлу (після imports):
  from PATCH_redis_cache import cache_get, cache_set, cache_del, cache_key

Використання в endpoint:
  Замість:
    with S.lock:
        data = compute_expensive_stuff()
        return jsonify(data)
  
  Написати:
    ck = cache_key('profile', addr)
    cached = cache_get(ck)
    if cached: return cached
    with S.lock:
        data = compute_expensive_stuff()
    resp = jsonify(data)
    cache_set(ck, resp, ttl=5)
    return resp
"""

import json
import time
import hashlib
from flask import Response

# ── Redis connection ──────────────────────────────────────────
try:
    import redis
    _r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True,
                     socket_connect_timeout=1, socket_timeout=1)
    _r.ping()
    REDIS_OK = True
    print("✅ Redis cache connected")
except Exception as e:
    _r = None
    REDIS_OK = False
    print(f"⚠️  Redis not available ({e}) — running without cache")

PREFIX = 'lac:'

def cache_key(*parts):
    """Generate cache key from parts"""
    return PREFIX + ':'.join(str(p) for p in parts)

def cache_get(key):
    """Get cached Flask Response or None"""
    if not REDIS_OK or not _r:
        return None
    try:
        raw = _r.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        return Response(
            data['body'],
            status=data['status'],
            mimetype='application/json'
        )
    except Exception:
        return None

def cache_set(key, response, ttl=5):
    """Cache a Flask Response"""
    if not REDIS_OK or not _r:
        return
    try:
        data = json.dumps({
            'body': response.get_data(as_text=True),
            'status': response.status_code,
            'ts': time.time()
        })
        _r.setex(key, ttl, data)
    except Exception:
        pass

def cache_del(*keys):
    """Invalidate cache keys"""
    if not REDIS_OK or not _r:
        return
    try:
        _r.delete(*keys)
    except Exception:
        pass

def cache_del_pattern(pattern):
    """Delete all keys matching pattern (e.g. 'lac:inbox:*')"""
    if not REDIS_OK or not _r:
        return
    try:
        keys = _r.keys(PREFIX + pattern)
        if keys:
            _r.delete(*keys)
    except Exception:
        pass

# ── TTL constants ──────────────────────────────────────────────
TTL_PROFILE   = 5    # seconds — balance/level can change rarely
TTL_INBOX     = 3    # seconds — messages need to feel fast
TTL_GROUPS    = 10   # seconds — groups change rarely
TTL_MINING    = 15   # seconds — mining stats
TTL_CHAIN     = 5    # seconds — block height
TTL_CONTACTS  = 30   # seconds — contacts rarely change
