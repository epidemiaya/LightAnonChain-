#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAC Anonymous Groups Plugin
Registers endpoints without modifying main node code
"""

def register_anonymous_groups(app, state):
    """
    Register Anonymous Groups endpoints
    Call this from main() in lac_node.py
    """
    
    # Import module
    try:
        from lac_anonymous_groups import LACAnonymousGroups
    except ImportError:
        print("⚠️ Anonymous Groups module not found")
        return False
    
    # Initialize
    if not hasattr(state, 'anon_groups') or state.anon_groups is None:
        try:
            state.anon_groups = LACAnonymousGroups()
            print("✅ Anonymous Groups initialized")
        except Exception as e:
            print(f"⚠️ Anonymous Groups init failed: {e}")
            return False
    
    # Import helpers from main module
    import sys
    main_module = sys.modules['__main__']
    S = getattr(main_module, 'S')  # State object
    get_client_ip = getattr(main_module, 'get_client_ip')
    rate_limit_check = getattr(main_module, 'rate_limit_check')
    validate_seed = getattr(main_module, 'validate_seed')
    get_address_from_seed = getattr(main_module, 'get_address_from_seed')
    get_username_by_key_id = getattr(main_module, 'get_username_by_key_id')
    jsonify = getattr(main_module, 'jsonify')
    request = getattr(main_module, 'request')
    
    # ==================== ENDPOINTS ====================
    
    @app.route('/api/anon_groups/create', methods=['POST'])
    def create_anonymous_group():
        """Create anonymous group with Ring Signatures"""
        ip = get_client_ip()
        if not rate_limit_check(ip, max_requests=10, window=3600):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        stealth = data.get('stealth', True)
        
        if not name:
            return jsonify({'error': 'Group name required'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            if from_addr not in state.wallets:
                return jsonify({'error': 'Wallet not found'}), 404
            
            from_wallet = state.wallets[from_addr]
            
            # Check balance for group creation fee (10 LAC)
            if from_wallet.get('balance', 0) < 10:
                return jsonify({'error': 'Insufficient balance (need 10 LAC)'}), 400
            
            success, message, group_id = state.anon_groups.create_group(
                name=name,
                creator=from_addr,
                stealth=stealth
            )
            
            if not success:
                return jsonify({'error': message}), 400
            
            # Create transaction for L1 blockchain (permanent record)
            import time
            group_tx = {
                'type': 'anon_group_create',
                'group_id': group_id,
                'name': name,
                'creator': from_addr,
                'stealth': stealth,
                'timestamp': int(time.time()),
                'fee': 10  # 10 LAC fee for group creation
            }
            
            # Add to mempool (will be included in next block)
            S.mempool.append(group_tx)
            
            # Charge fee
            if from_addr in state.wallets:
                from_wallet = state.wallets[from_addr]
                from_wallet['balance'] -= 10
            
            # Save groups to disk
            state.save()
            
            return jsonify({
                'ok': True,
                'group_id': group_id,
                'name': name,
                'stealth': stealth
            })
    
    @app.route('/api/anon_groups/join', methods=['POST'])
    def join_anonymous_group():
        """Join anonymous group"""
        ip = get_client_ip()
        if not rate_limit_check(ip, max_requests=10, window=3600):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json() or {}
        group_id = data.get('group_id', '').strip()
        
        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            if from_addr not in state.wallets:
                return jsonify({'error': 'Wallet not found'}), 404
            
            success, message = state.anon_groups.join_group(group_id, from_addr)
            
            if not success:
                return jsonify({'error': message}), 400
            
            return jsonify({'ok': True, 'message': message})
    
    @app.route('/api/anon_groups/leave', methods=['POST'])
    def leave_anonymous_group():
        """Leave anonymous group"""
        ip = get_client_ip()
        if not rate_limit_check(ip, max_requests=10, window=3600):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json() or {}
        group_id = data.get('group_id', '').strip()
        
        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            success, message = state.anon_groups.leave_group(group_id, from_addr)
            
            if not success:
                return jsonify({'error': message}), 400
            
            return jsonify({'ok': True, 'message': message})
    
    @app.route('/api/anon_groups/post', methods=['POST'])
    def post_anonymous_message():
        """Post anonymous message to group"""
        ip = get_client_ip()
        if not rate_limit_check(ip, max_requests=30, window=60):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json() or {}
        group_id = data.get('group_id', '').strip()
        text = data.get('text', '').strip()
        
        if not group_id or not text:
            return jsonify({'error': 'Group ID and text required'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            success, message, msg_data = state.anon_groups.post_message(
                group_id=group_id,
                sender=from_addr,
                text=text
            )
            
            if not success:
                return jsonify({'error': message}), 400
            
            # Add to L2 ephemeral blockchain
            if msg_data and from_addr in state.wallets:
                from_wallet = state.wallets[from_addr]
                key_id = from_wallet.get('key_id')
                from_username = get_username_by_key_id(key_id) or 'Anonymous'
                
                ephemeral_msg = {
                    'type': 'anon_group_message',
                    'group_id': group_id,
                    'from': from_username,
                    'text': text,
                    'timestamp': msg_data.get('timestamp'),
                    'ttl': 300,  # 5 minutes
                    'anonymous': True
                }
                S.ephemeral_msgs.append(ephemeral_msg)
                
                # Charge fee
                from_wallet['balance'] -= 1  # 1 LAC fee
                from_wallet['msg_count'] = from_wallet.get('msg_count', 0) + 1
                
                state.save()
            
            return jsonify({
                'ok': True,
                'message': msg_data
            })
    
    @app.route('/api/anon_groups/messages', methods=['GET'])
    def get_anonymous_messages():
        """Get messages from anonymous group"""
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        group_id = request.args.get('group_id', '').strip()
        limit = int(request.args.get('limit', 50))
        
        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            success, message, messages = state.anon_groups.get_messages(
                group_id=group_id,
                requester=from_addr,
                limit=limit
            )
            
            if not success:
                return jsonify({'error': message}), 400
            
            return jsonify({
                'ok': True,
                'messages': messages,
                'count': len(messages)
            })
    
    @app.route('/api/anon_groups/my', methods=['GET'])
    def get_my_anonymous_groups():
        """Get user's anonymous groups"""
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            groups = state.anon_groups.list_my_groups(from_addr)
            
            return jsonify({
                'ok': True,
                'groups': groups,
                'count': len(groups)
            })
    
    @app.route('/api/anon_groups/public', methods=['GET'])
    def get_public_anonymous_groups():
        """Get public anonymous groups"""
        with state.lock:
            groups = state.anon_groups.get_public_groups()
            
            return jsonify({
                'ok': True,
                'groups': groups,
                'count': len(groups)
            })
    
    @app.route('/api/anon_groups/info', methods=['GET'])
    def get_anonymous_group_info():
        """Get anonymous group info"""
        group_id = request.args.get('group_id', '').strip()
        
        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400
        
        with state.lock:
            info = state.anon_groups.get_group_info(group_id)
            
            if not info:
                return jsonify({'error': 'Group not found'}), 404
            
            return jsonify({
                'ok': True,
                'group': info
            })
    
    # ==================== POLL ENDPOINTS ====================
    
    @app.route('/api/anon_groups/poll/create', methods=['POST'])
    def create_anonymous_poll():
        """Create anonymous poll in group"""
        ip = get_client_ip()
        if not rate_limit_check(ip, max_requests=20, window=3600):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json() or {}
        group_id = data.get('group_id', '').strip()
        question = data.get('question', '').strip()
        options = data.get('options', [])
        ring_signature = data.get('ring_signature', {})
        
        if not group_id or not question:
            return jsonify({'error': 'Group ID and question required'}), 400
        
        if not isinstance(options, list) or len(options) < 2:
            return jsonify({'error': 'Need at least 2 options'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            if from_addr not in state.wallets:
                return jsonify({'error': 'Wallet not found'}), 404
            
            success, message, poll_id = state.anon_groups.create_poll(
                group_id=group_id,
                creator=from_addr,
                question=question,
                options=options,
                ring_signature=ring_signature
            )
            
            if not success:
                return jsonify({'error': message}), 400
            
            return jsonify({
                'ok': True,
                'poll_id': poll_id,
                'question': question,
                'options': options,
                'expires_in': 300
            })
    
    @app.route('/api/anon_groups/poll/vote', methods=['POST'])
    def vote_on_anonymous_poll():
        """Vote anonymously on poll"""
        ip = get_client_ip()
        if not rate_limit_check(ip, max_requests=50, window=3600):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json() or {}
        poll_id = data.get('poll_id', '').strip()
        option_index = data.get('option_index')
        ring_signature = data.get('ring_signature', {})
        
        if not poll_id or option_index is None:
            return jsonify({'error': 'Poll ID and option required'}), 400
        
        if not isinstance(option_index, int):
            return jsonify({'error': 'Invalid option index'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            if from_addr not in state.wallets:
                return jsonify({'error': 'Wallet not found'}), 404
            
            success, message = state.anon_groups.vote_on_poll(
                poll_id=poll_id,
                voter=from_addr,
                option_index=option_index,
                ring_signature=ring_signature
            )
            
            if not success:
                return jsonify({'error': message}), 400
            
            return jsonify({
                'ok': True,
                'message': message
            })
    
    @app.route('/api/anon_groups/poll/get', methods=['GET'])
    def get_anonymous_poll():
        """Get poll with results"""
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        poll_id = request.args.get('poll_id', '').strip()
        
        if not poll_id:
            return jsonify({'error': 'Poll ID required'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            if from_addr not in state.wallets:
                return jsonify({'error': 'Wallet not found'}), 404
            
            success, message, poll_data = state.anon_groups.get_poll(
                poll_id=poll_id,
                requester=from_addr
            )
            
            if not success:
                return jsonify({'error': message}), 404
            
            return jsonify({
                'ok': True,
                'poll': poll_data
            })
    
    @app.route('/api/anon_groups/polls', methods=['GET'])
    def list_group_polls():
        """List all polls in group"""
        seed = request.headers.get('X-Seed', '').strip()
        if not validate_seed(seed):
            return jsonify({'error': 'Unauthorized'}), 401
        
        group_id = request.args.get('group_id', '').strip()
        
        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400
        
        from_addr = get_address_from_seed(seed)
        
        with state.lock:
            if from_addr not in state.wallets:
                return jsonify({'error': 'Wallet not found'}), 404
            
            success, message, polls = state.anon_groups.list_group_polls(
                group_id=group_id,
                requester=from_addr
            )
            
            if not success:
                return jsonify({'error': message}), 404
            
            return jsonify({
                'ok': True,
                'polls': polls,
                'count': len(polls)
            })
    
    print("✅ Anonymous Groups endpoints registered")
    print("✅ Anonymous Polls endpoints registered")
    return True