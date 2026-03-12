#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAC SQLite Sync Integration - SAFE
Background initial sync — never blocks API requests.
"""

from lac_database_safe import LACDatabaseSafe
import threading


def init_sqlite_sync(state):
    db_path = state.datadir / "lac_cache.db"
    db = LACDatabaseSafe(str(db_path))

    if not db.enabled:
        print("[SQLite] Disabled - running on JSON only")
        return None

    print(f"[SQLite] Initialized: {db_path}")

    # Wrap save() to sync after each JSON save
    original_save = state.save

    def save_with_sqlite():
        original_save()
        try:
            db.sync_from_json(state.chain, state.wallets, show_progress=False)
        except Exception as e:
            print(f"[SQLite] Sync failed (non-fatal): {e}")

    state.save = save_with_sqlite
    state.db = db

    # Initial sync in BACKGROUND — never blocks API
    current_height = db.get_height()
    chain_height = len(state.chain) - 1

    if current_height < chain_height:
        print(f"[SQLite] Starting background sync ({current_height} → {chain_height})...")
        db._syncing = True

        def background_sync():
            try:
                db.sync_from_json(state.chain, state.wallets, show_progress=True)
            finally:
                db._syncing = False
                print("[SQLite] Background sync complete!")

        t = threading.Thread(target=background_sync, daemon=True)
        t.start()
    else:
        print(f"[SQLite] Up to date ({chain_height} blocks)")

    print("[SQLite] Integration complete — API ready immediately!")
    return db


def add_sqlite_api_endpoints(app, state):
    from flask import jsonify, request

    if not hasattr(state, 'db') or not state.db.enabled:
        print("[SQLite] API endpoints not added (database disabled)")
        return

    @app.route('/api/sqlite/transaction/<tx_hash>', methods=['GET'])
    def get_sqlite_transaction(tx_hash):
        tx = state.db.get_transaction(tx_hash)
        if tx:
            return jsonify(tx)
        return jsonify({'error': 'Transaction not found'}), 404

    @app.route('/api/sqlite/wallet/<address>/transactions', methods=['GET'])
    def get_sqlite_wallet_txs(address):
        limit = request.args.get('limit', 100, type=int)
        txs = state.db.get_transactions_by_address(address, limit)
        return jsonify({'transactions': txs, 'count': len(txs)})

    @app.route('/api/sqlite/stats', methods=['GET'])
    def get_sqlite_stats():
        return jsonify(state.db.get_stats())

    @app.route('/api/sqlite/block/<int:height>', methods=['GET'])
    def get_sqlite_block(height):
        block = state.db.get_block(height)
        if block:
            return jsonify(block)
        return jsonify({'error': 'Block not found'}), 404

    print("[SQLite] API endpoints added")
