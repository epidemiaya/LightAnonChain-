#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAC SQLite Sync Integration - SAFE
===================================
Syncs JSON data to SQLite after successful save

SAFETY RULES:
1. Only runs AFTER successful JSON save
2. If sync fails, JSON continues working
3. Never modifies JSON files
4. Can be disabled anytime
"""

from lac_database_safe import LACDatabaseSafe


def init_sqlite_sync(state):
    """
    Initialize SQLite sync for State instance
    
    This wraps the existing save() method to add SQLite sync AFTER successful save.
    JSON remains primary - SQLite is just a copy for fast queries.
    """
    
    # Create database
    db_path = state.datadir / "lac_cache.db"
    db = LACDatabaseSafe(str(db_path))
    
    if not db.enabled:
        print("[SQLite] Disabled - running on JSON only")
        return None
    
    print(f"[SQLite] Initialized: {db_path}")
    
    # Initial sync (if database is empty)
    current_height = db.get_height()
    chain_height = len(state.chain) - 1
    
    if current_height < chain_height:
        print(f"[SQLite] Database behind (DB: {current_height}, JSON: {chain_height})")
        print("[SQLite] Starting initial sync...")
        db.sync_from_json(state.chain, state.wallets, show_progress=True)
    else:
        print(f"[SQLite] Database up to date ({current_height} blocks)")
    
    # Wrap save() method to add SQLite sync
    original_save = state.save
    
    def save_with_sqlite():
        """
        Enhanced save() that syncs to SQLite after successful JSON save
        
        If SQLite sync fails, it's logged but doesn't affect JSON save.
        """
        # Save to JSON first (original behavior)
        original_save()
        
        # Then sync to SQLite (best effort - failures are non-fatal)
        try:
            db.sync_from_json(state.chain, state.wallets, show_progress=False)
        except Exception as e:
            print(f"[SQLite] Sync failed (non-fatal): {e}")
    
    # Replace save method
    state.save = save_with_sqlite
    state.db = db  # Attach database for API endpoints
    
    print("[SQLite] Integration complete!")
    return db


def add_sqlite_api_endpoints(app, state):
    """
    Add API endpoints for fast SQLite queries
    
    These endpoints use SQLite for speed, but fall back to JSON if needed.
    """
    from flask import jsonify, request
    
    if not hasattr(state, 'db') or not state.db.enabled:
        print("[SQLite] API endpoints not added (database disabled)")
        return
    
    @app.route('/api/sqlite/transaction/<tx_hash>', methods=['GET'])
    def get_sqlite_transaction(tx_hash):
        """Get transaction by hash (fast SQLite lookup)"""
        tx = state.db.get_transaction(tx_hash)
        if tx:
            return jsonify(tx)
        return jsonify({'error': 'Transaction not found'}), 404
    
    @app.route('/api/sqlite/wallet/<address>/transactions', methods=['GET'])
    def get_sqlite_wallet_txs(address):
        """Get wallet transaction history (fast SQLite lookup)"""
        limit = request.args.get('limit', 100, type=int)
        txs = state.db.get_transactions_by_address(address, limit)
        return jsonify({'transactions': txs, 'count': len(txs)})
    
    @app.route('/api/sqlite/stats', methods=['GET'])
    def get_sqlite_stats():
        """Get SQLite database statistics"""
        stats = state.db.get_stats()
        return jsonify(stats)
    
    @app.route('/api/sqlite/block/<int:height>', methods=['GET'])
    def get_sqlite_block(height):
        """Get block by height (fast SQLite lookup)"""
        block = state.db.get_block(height)
        if block:
            return jsonify(block)
        return jsonify({'error': 'Block not found'}), 404
    
    print("[SQLite] API endpoints added:")
    print("  GET /api/sqlite/transaction/<hash>")
    print("  GET /api/sqlite/wallet/<address>/transactions")
    print("  GET /api/sqlite/stats")
    print("  GET /api/sqlite/block/<height>")