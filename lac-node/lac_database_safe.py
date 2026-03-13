#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAC Database Safe - SQLite WAL cache layer.
Read-only cache — JSON is always primary storage.
Thread-safe: per-thread connections, no shared state.
"""
import sqlite3
import threading
import time
import logging

logger = logging.getLogger(__name__)


class LACDatabaseSafe:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.enabled = False
        self._local = threading.local()
        try:
            conn = self._get_conn()
            self._init_schema(conn)
            self.enabled = True
            logger.info(f"[SQLite] Ready: {db_path}")
        except Exception as e:
            logger.warning(f"[SQLite] Init failed (non-fatal): {e}")

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self, conn):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS blocks (
                height      INTEGER PRIMARY KEY,
                hash        TEXT,
                timestamp   REAL,
                data        TEXT
            );
            CREATE TABLE IF NOT EXISTS transactions (
                tx_hash     TEXT PRIMARY KEY,
                block_height INTEGER,
                sender      TEXT,
                recipient   TEXT,
                amount      REAL,
                timestamp   REAL,
                data        TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tx_sender    ON transactions(sender);
            CREATE INDEX IF NOT EXISTS idx_tx_recipient ON transactions(recipient);
            CREATE INDEX IF NOT EXISTS idx_tx_block     ON transactions(block_height);
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        conn.commit()

    def get_height(self) -> int:
        if not self.enabled:
            return -1
        try:
            conn = self._get_conn()
            row = conn.execute("SELECT MAX(height) FROM blocks").fetchone()
            return row[0] if row and row[0] is not None else -1
        except Exception as e:
            logger.warning(f"[SQLite] get_height error: {e}")
            return -1

    def sync_from_json(self, chain: list, wallets: dict = None, show_progress: bool = False):
        """Sync blocks into SQLite cache. Safe to call from any thread."""
        if not self.enabled:
            return
        try:
            import json
            conn = self._get_conn()
            current_height = self.get_height()
            new_blocks = [b for b in chain if b.get('index', 0) > current_height]

            if not new_blocks:
                return

            total = len(new_blocks)
            batch = []
            tx_batch = []

            for i, block in enumerate(new_blocks):
                height = block.get('index', 0)
                batch.append((
                    height,
                    block.get('hash', ''),
                    block.get('timestamp', 0),
                    json.dumps(block)
                ))

                # Extract transactions
                for tx in block.get('transactions', []):
                    tx_hash = tx.get('id') or tx.get('hash') or tx.get('tx_id', '')
                    if tx_hash:
                        tx_batch.append((
                            tx_hash,
                            height,
                            tx.get('sender') or tx.get('from', ''),
                            tx.get('recipient') or tx.get('to', ''),
                            float(tx.get('amount', 0)),
                            float(tx.get('timestamp', block.get('timestamp', 0))),
                            json.dumps(tx)
                        ))

                # Write in batches of 500
                if len(batch) >= 500:
                    conn.executemany(
                        "INSERT OR REPLACE INTO blocks(height,hash,timestamp,data) VALUES(?,?,?,?)",
                        batch
                    )
                    if tx_batch:
                        conn.executemany(
                            "INSERT OR REPLACE INTO transactions(tx_hash,block_height,sender,recipient,amount,timestamp,data) VALUES(?,?,?,?,?,?,?)",
                            tx_batch
                        )
                    conn.commit()
                    batch.clear()
                    tx_batch.clear()
                    if show_progress and total > 1000:
                        logger.info(f"[SQLite] Synced {i+1}/{total} blocks...")

            # Final batch
            if batch:
                conn.executemany(
                    "INSERT OR REPLACE INTO blocks(height,hash,timestamp,data) VALUES(?,?,?,?)",
                    batch
                )
            if tx_batch:
                conn.executemany(
                    "INSERT OR REPLACE INTO transactions(tx_hash,block_height,sender,recipient,amount,timestamp,data) VALUES(?,?,?,?,?,?,?)",
                    tx_batch
                )
            conn.commit()

            if show_progress:
                logger.info(f"[SQLite] Synced {total} new blocks")

        except Exception as e:
            logger.warning(f"[SQLite] sync_from_json error (non-fatal): {e}")
            try:
                self._local.conn = None  # Reset connection on error
            except Exception:
                pass

    def get_block(self, height: int) -> dict:
        if not self.enabled:
            return None
        try:
            import json
            conn = self._get_conn()
            row = conn.execute("SELECT data FROM blocks WHERE height=?", (height,)).fetchone()
            return json.loads(row['data']) if row else None
        except Exception as e:
            logger.warning(f"[SQLite] get_block error: {e}")
            return None

    def get_transaction(self, tx_hash: str) -> dict:
        if not self.enabled:
            return None
        try:
            import json
            conn = self._get_conn()
            row = conn.execute("SELECT data FROM transactions WHERE tx_hash=?", (tx_hash,)).fetchone()
            return json.loads(row['data']) if row else None
        except Exception as e:
            logger.warning(f"[SQLite] get_transaction error: {e}")
            return None

    def get_transactions_by_address(self, address: str, limit: int = 100) -> list:
        if not self.enabled:
            return []
        try:
            import json
            conn = self._get_conn()
            rows = conn.execute(
                """SELECT data FROM transactions
                   WHERE sender=? OR recipient=?
                   ORDER BY timestamp DESC LIMIT ?""",
                (address, address, limit)
            ).fetchall()
            return [json.loads(r['data']) for r in rows]
        except Exception as e:
            logger.warning(f"[SQLite] get_transactions_by_address error: {e}")
            return []

    def get_stats(self) -> dict:
        if not self.enabled:
            return {'enabled': False}
        try:
            conn = self._get_conn()
            block_count = conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
            tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            max_height = self.get_height()
            return {
                'enabled': True,
                'db_path': self.db_path,
                'block_count': block_count,
                'tx_count': tx_count,
                'max_height': max_height
            }
        except Exception as e:
            logger.warning(f"[SQLite] get_stats error: {e}")
            return {'enabled': False, 'error': str(e)}
