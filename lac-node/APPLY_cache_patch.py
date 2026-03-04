"""
Застосовує Redis кеш до lac_node.py
Запуск: python3 APPLY_cache_patch.py /root/LightAnonChain-/lac-node/lac_node.py
"""
import sys, re, shutil, os

path = sys.argv[1] if len(sys.argv) > 1 else '/root/LightAnonChain-/lac-node/lac_node.py'

# Backup
shutil.copy(path, path + '.bak')
print(f"Backup saved to {path}.bak")

c = open(path).read()
changes = []

# ── 1. Add import at top ──────────────────────────────────────
old_import_marker = "import time"
new_import = "import time\ntry:\n    from PATCH_redis_cache import cache_get, cache_set, cache_del, cache_key, TTL_PROFILE, TTL_INBOX, TTL_GROUPS, TTL_MINING, TTL_CHAIN, TTL_CONTACTS\nexcept ImportError:\n    print('⚠️ Redis cache patch not found')\n    def cache_get(k): return None\n    def cache_set(k,v,ttl=5): pass\n    def cache_del(*k): pass\n    def cache_key(*p): return ':'.join(str(x) for x in p)\n    TTL_PROFILE=TTL_INBOX=TTL_GROUPS=TTL_MINING=TTL_CHAIN=TTL_CONTACTS=0"

if 'from PATCH_redis_cache import' not in c:
    c = c.replace(old_import_marker, new_import, 1)
    changes.append('1. Import added')

# ── 2. Cache /api/profile ─────────────────────────────────────
old_profile = """@app.route('/api/profile', methods=['GET'])
def profile():
    \"\"\"Get user profile\"\"\"
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:"""

new_profile = """@app.route('/api/profile', methods=['GET'])
def profile():
    \"\"\"Get user profile\"\"\"
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    # Redis cache — profile changes rarely
    ck = cache_key('profile', addr)
    cached = cache_get(ck)
    if cached: return cached
    
    with S.lock:"""

if old_profile in c:
    # Find the end of the profile function return and add cache_set
    c = c.replace(old_profile, new_profile, 1)
    # Find the return jsonify in profile and wrap it
    old_profile_return = """        return jsonify({
            'ok': True,
            'address': addr,
            'username': username,
            'balance': wallet.get('balance', 0),
            'level': wallet.get('level', 0),
            'tx_count': wallet.get('tx_count', 0),
            'msg_count': wallet.get('msg_count', 0),
            'created_at': wallet.get('created_at', 0),
            'dms_active': dms is not None and dms.get('enabled', False),
            'dms_days': dms.get('timeout_days', 0) if dms else 0
        })"""
    new_profile_return = """        resp = jsonify({
            'ok': True,
            'address': addr,
            'username': username,
            'balance': wallet.get('balance', 0),
            'level': wallet.get('level', 0),
            'tx_count': wallet.get('tx_count', 0),
            'msg_count': wallet.get('msg_count', 0),
            'created_at': wallet.get('created_at', 0),
            'dms_active': dms is not None and dms.get('enabled', False),
            'dms_days': dms.get('timeout_days', 0) if dms else 0
        })
        cache_set(ck, resp, TTL_PROFILE)
        return resp"""
    if old_profile_return in c:
        c = c.replace(old_profile_return, new_profile_return, 1)
        changes.append('2. /api/profile cached')
else:
    print('⚠️  profile endpoint not found exactly')

# ── 3. Cache /api/inbox ───────────────────────────────────────
old_inbox = """@app.route('/api/inbox', methods=['GET'])
def get_inbox():"""
new_inbox = """@app.route('/api/inbox', methods=['GET'])
def get_inbox():
    # Quick cache check before touching the lock
    _seed = request.headers.get('X-Seed','').strip()
    if _seed:
        _addr = get_address_from_seed(_seed)
        _ck = cache_key('inbox', _addr)
        _cached = cache_get(_ck)
        if _cached: return _cached"""

if old_inbox in c:
    c = c.replace(old_inbox, new_inbox, 1)
    changes.append('3. /api/inbox cache check added (manual return needed)')

# ── 4. Cache /api/groups ──────────────────────────────────────
old_groups = """@app.route('/api/groups', methods=['GET'])
def get_groups():"""
new_groups = """@app.route('/api/groups', methods=['GET'])
def get_groups():
    _seed = request.headers.get('X-Seed','').strip()
    if _seed:
        _ck = cache_key('groups', get_address_from_seed(_seed))
        _cached = cache_get(_ck)
        if _cached: return _cached"""

if old_groups in c:
    c = c.replace(old_groups, new_groups, 1)
    changes.append('4. /api/groups cache check added')

# ── 5. Invalidate inbox cache on new message ─────────────────
old_send = "def send_message():"
if old_send in c:
    old_send_full = '@app.route(\'/api/message.send\', methods=[\'POST\'])\ndef send_message():'
    new_send_full = '@app.route(\'/api/message.send\', methods=[\'POST\'])\ndef send_message():\n    # Invalidate inbox cache for both sender and receiver after send\n    pass  # cache invalidation happens below after processing'
    # Just note it — too complex to patch automatically
    changes.append('5. NOTE: invalidate inbox cache after message.send manually')

open(path, 'w').write(c)
print(f"\n✅ Applied changes:")
for ch in changes:
    print(f"   {ch}")
print(f"\n📁 File saved: {path}")
print(f"📁 Backup: {path}.bak")
