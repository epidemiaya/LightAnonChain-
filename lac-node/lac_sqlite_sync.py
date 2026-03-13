#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAC SQLite Sync - безпечна фонова синхронізація.
НІКОЛИ не тримає S.lock під час запису в SQLite.
JSON залишається основним сховищем.
"""
import threading
import time

try:
    from lac_database_safe import LACDatabaseSafe
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False


def init_sqlite_sync(state):
    if not _DB_AVAILABLE:
        print("[SQLite] lac_database_safe not found — disabled")
        return None

    db_path = state.datadir / "lac_cache.db"
    db = LACDatabaseSafe(str(db_path))

    if not db.enabled:
        print("[SQLite] Disabled")
        return None

    print(f"[SQLite] Initialized: {db_path}")

    # Патчимо save() — після запису JSON, синкаємо в фоні
    original_save = state.save

    def save_with_sqlite():
        # 1. Спочатку зберігаємо JSON (оригінал)
        original_save()

        # 2. Знімок даних БЕЗ утримання S.lock під час запису в SQLite
        try:
            with state.lock:
                chain_snapshot = list(state.chain[-50:])  # тільки останні 50 блоків
                wallets_snapshot = dict(state.wallets)

            # Пишемо в SQLite поза lock
            def _bg():
                try:
                    db.sync_from_json(chain_snapshot, wallets_snapshot)
                except Exception as e:
                    print(f"[SQLite] Incremental sync error (non-fatal): {e}")

            threading.Thread(target=_bg, daemon=True).start()
        except Exception as e:
            print(f"[SQLite] Sync skipped (non-fatal): {e}")

    state.save = save_with_sqlite
    state.db = db

    # Початкова повна синхронізація — знімок даних, потім фонова обробка
    def _initial_sync():
        try:
            # Чекаємо поки нода повністю стартує
            time.sleep(10)

            # Знімок ПІСЛЯ init (S.lock вже відпущений)
            with state.lock:
                chain_snapshot = list(state.chain)
                wallets_snapshot = dict(state.wallets)

            current = db.get_height()
            total = len(chain_snapshot)

            if current < total - 1:
                print(f"[SQLite] Background sync: {current} -> {total-1} blocks...")
                db.sync_from_json(chain_snapshot, wallets_snapshot, show_progress=True)
                print("[SQLite] Initial sync complete!")
            else:
                print(f"[SQLite] Already up to date ({total} blocks)")
        except Exception as e:
            print(f"[SQLite] Initial sync error (non-fatal): {e}")

    threading.Thread(target=_initial_sync, daemon=True).start()
    print("[SQLite] Ready — initial sync in background, API available immediately")
    return db


def add_sqlite_api_endpoints(app, state):
    from flask import jsonify, request

    if not hasattr(state, 'db') or not state.db or not state.db.enabled:
        print("[SQLite] API endpoints skipped (disabled)")
        return

    @app.route('/api/sqlite/transaction/<tx_hash>', methods=['GET'])
    def get_sqlite_transaction(tx_hash):
        tx = state.db.get_transaction(tx_hash)
        return jsonify(tx) if tx else (jsonify({'error': 'Not found'}), 404)

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
        return jsonify(block) if block else (jsonify({'error': 'Not found'}), 404)

    print("[SQLite] API endpoints registered")
