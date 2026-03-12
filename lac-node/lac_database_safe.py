#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAC Database Safe — SQLite cache layer
=======================================
JSON is PRIMARY. SQLite is read-only cache for fast queries.
If SQLite fails at any point — JSON continues working normally.
"""

import sqlite3
import json
import time
import os
from pathlib import Path


class LACDatabaseSafe:
    """
    Safe SQLite cache for LAC Node.
    - JSON stays primary storage
    - SQLite is just a fast-query cache
    - Any failure is non-fatal
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.enabled = False
        self._conn = None

        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA cache_size=-32000")  # 32MB cache
            self._conn.execute("PRAGMA temp_store=MEMORY")
            self._create_tables()
            self.enabled = True
            print(f"[SQLite] WAL mode enabled: {db_path}")
        except Exception as e:
            print(f"[SQLite] Init failed (non-fatal): {e}")
            self.enabled = False

    def _create_tables(self):
        c = self._conn
        c.executescript("""
            CREATE TABLE IF NOT EXISTS blocks (
                height      INTEGER PRIMARY KEY,
                hash        TEXT,
                timestamp   INTEGER,
                miner       TEXT,
                tx_count    INTEGER,
                data_json   TEXT
            );

            CREATE TABLE IF NOT EXISTS transactions (
                tx_hash     TEXT PRIMARY KEY,
                block_height INTEGER,
                tx_type     TEXT,
                from_addr   TEXT,
                to_addr     TEXT,
                amount      REAL,
                timestamp   INTEGER,
                data_json   TEXT
            );

            CREATE TABLE IF NOT EXISTS wallets (
                address     TEXT PRIMARY KEY,
                balance     REAL,
                level       INTEGER,
                username    TEXT,
                tx_count    INTEGER,
                msg_count   INTEGER,
                last_seen   INTEGER,
                data_json   TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tx_from    ON transactions(from_addr);
            CREATE INDEX IF NOT EXISTS idx_tx_to      ON transactions(to_addr);
            CREATE INDEX IF NOT EXISTS idx_tx_block   ON transactions(block_height);
            CREATE INDEX IF NOT EXISTS idx_tx_type    ON transactions(tx_type);
            CREATE INDEX IF NOT EXISTS idx_block_ts   ON blocks(timestamp);
        """)
        c.commit()

    def get_height(self) -> int:
        """Return highest synced block height, or -1 if empty."""
        if not self.enabled:
            return -1
        try:
            row = self._conn.execute("SELECT MAX(height) FROM blocks").fetchone()
            return row[0] if row and row[0] is not None else -1
        except Exception:
            return -1

    def sync_from_json(self, chain: list, wallets: dict, show_progress: bool = False):
        """
        Sync chain + wallets into SQLite.
        Only inserts missing blocks (incremental).
        """
        if not self.enabled:
            return

        try:
            current_height = self.get_height()
            new_blocks = [b for b in chain if b.get('index', -1) > current_height]

            if not new_blocks and not show_progress:
                return

            if show_progress and new_blocks:
                print(f"[SQLite] Syncing {len(new_blocks)} new blocks...")

            inserted_blocks = 0
            inserted_txs = 0

            for i, block in enumerate(new_blocks):
                try:
                    height = block.get('index', 0)
                    self._conn.execute(
                        "INSERT OR REPLACE INTO blocks VALUES (?,?,?,?,?,?)",
                        (
                            height,
                            block.get('hash', ''),
                            block.get('timestamp', 0),
                            block.get('miner', ''),
                            len(block.get('transactions', [])),
                            json.dumps(block),
                        )
                    )
                    inserted_blocks += 1

                    for tx in block.get('transactions', []):
                        tx_hash = tx.get('hash') or tx.get('tx_hash') or tx.get('id', '')
                        if not tx_hash:
                            continue
                        self._conn.execute(
                            "INSERT OR IGNORE INTO transactions VALUES (?,?,?,?,?,?,?,?)",
                            (
                                tx_hash,
                                height,
                                tx.get('type', 'transfer'),
                                tx.get('from', tx.get('from_addr', '')),
                                tx.get('to', tx.get('to_addr', '')),
                                float(tx.get('amount', 0) or 0),
                                block.get('timestamp', 0),
                                json.dumps(tx),
                            )
                        )
                        inserted_txs += 1

                    # Commit every 500 blocks to avoid huge transactions
                    if inserted_blocks % 500 == 0:
                        self._conn.commit()
                        if show_progress:
                            pct = int((i + 1) / len(new_blocks) * 100)
                            print(f"[SQLite] Progress: {pct}% ({inserted_blocks} blocks)")

                except Exception as e:
                    # Skip bad block, continue
                    continue

            # Sync wallets
            for addr, w in wallets.items():
                try:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO wallets VALUES (?,?,?,?,?,?,?,?)",
                        (
                            addr,
                            float(w.get('balance', 0) or 0),
                            int(w.get('level', 0) or 0),
                            w.get('username', ''),
                            int(w.get('tx_count', 0) or 0),
                            int(w.get('msg_count', 0) or 0),
                            int(w.get('last_activity', 0) or 0),
                            json.dumps(w),
                        )
                    )
                except Exception:
                    continue

            self._conn.commit()

            if show_progress and (inserted_blocks or inserted_txs):
                print(f"[SQLite] Sync complete: +{inserted_blocks} blocks, +{inserted_txs} txs")

        except Exception as e:
            print(f"[SQLite] Sync error (non-fatal): {e}")
            try:
                self._conn.rollback()
            except Exception:
                pass

    def get_block(self, height: int) -> dict | None:
        """Get block by height."""
        if not self.enabled:
            return None
        try:
            row = self._conn.execute(
                "SELECT data_json FROM blocks WHERE height=?", (height,)
            ).fetchone()
            return json.loads(row[0]) if row else None
        except Exception:
            return None

    def get_transaction(self, tx_hash: str) -> dict | None:
        """Get transaction by hash."""
        if not self.enabled:
            return None
        try:
            row = self._conn.execute(
                "SELECT data_json FROM transactions WHERE tx_hash=?", (tx_hash,)
            ).fetchone()
            return json.loads(row[0]) if row else None
        except Exception:
            return None

    def get_transactions_by_address(self, address: str, limit: int = 100) -> list:
        """Get transactions for an address (sent or received)."""
        if not self.enabled:
            return []
        try:
            rows = self._conn.execute(
                """SELECT data_json FROM transactions
                   WHERE from_addr=? OR to_addr=?
                   ORDER BY block_height DESC LIMIT ?""",
                (address, address, limit)
            ).fetchall()
            return [json.loads(r[0]) for r in rows]
        except Exception:
            return []

    def get_stats(self) -> dict:
        """Get database statistics."""
        if not self.enabled:
            return {'enabled': False}
        try:
            blocks = self._conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
            txs = self._conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            wallets = self._conn.execute("SELECT COUNT(*) FROM wallets").fetchone()[0]
            size_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            return {
                'enabled': True,
                'blocks': blocks,
                'transactions': txs,
                'wallets': wallets,
                'db_size_mb': round(size_bytes / 1024 / 1024, 2),
                'db_path': self.db_path,
            }
        except Exception as e:
            return {'enabled': True, 'error': str(e)}

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
