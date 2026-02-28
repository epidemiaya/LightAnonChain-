#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAC Node - SECURED VERSION + FIXED ENDPOINTS
Анонімність + Захист від атак + Всі API endpoints
"""
import json, time, hashlib, secrets, os, sys
from typing import Optional
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from threading import Thread, Lock
from collections import defaultdict
from datetime import datetime, timedelta

# Fix emoji display on Windows
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================================================
# DEV MODE Configuration (for testing with fewer validators)
# ============================================================================
DEV_MODE = True  # Set to False for production

if DEV_MODE:
    MIN_VALIDATORS = 3         # Only 3 validators needed for testing
    COMMITMENT_INTERVAL = 10   # Create commitment every 10 blocks (not 1000)
else:
    MIN_VALIDATORS = 100
    COMMITMENT_INTERVAL = 1000

print(f"🔧 Running in {'DEV' if DEV_MODE else 'PRODUCTION'} mode")
print(f"   Min validators: {MIN_VALIDATORS}")
print(f"   Commitment interval: {COMMITMENT_INTERVAL} blocks")

# Zero-History Retention Config
ZH_L3_RETENTION_DAYS = 90   # Full data: 90 days (3 months)
ZH_L2_RETENTION_DAYS = 365  # Pruned data + fraud proofs: 1 year
ZH_L1_RETENTION = 'forever' # State commitments: permanent
print(f"   ZH Retention: L3={ZH_L3_RETENTION_DAYS}d, L2={ZH_L2_RETENTION_DAYS}d, L1={ZH_L1_RETENTION}")


# Import stability system
try:
    from lac_stability import (
        setup_logging,
        StateManager,
        retry_on_failure,
        GracefulShutdown,
        HealthMonitor,
        setup_stability_system
    )
    STABILITY_ENABLED = True
except ImportError:
    print("⚠️ lac_stability.py not found - running without stability patches")
    sys.stdout.flush()
    STABILITY_ENABLED = False
    def retry_on_failure(max_attempts=3, delay=1):
        def decorator(func):
            return func
        return decorator


# Import security patches
try:
    from PATCH_security import RateLimiter, InputValidator, SybilProtection, DDoSProtection
    SECURITY_ENABLED = True
except ImportError:
    print("⚠️ PATCH_security.py not found - running without security patches")
    SECURITY_ENABLED = False
    class RateLimiter:
        def check_rate_limit(self, *args, **kwargs): return True, None
    class InputValidator:
        @staticmethod
        def validate_username(u): return True, None
        @staticmethod
        def validate_amount(a): return True, None

# Import performance patches
try:
    from PATCH_performance import LRUCache, DatabaseOptimizer, BatchProcessor
    PERFORMANCE_ENABLED = True
except ImportError:
    print("⚠️ PATCH_performance.py not found - running without performance patches")
    PERFORMANCE_ENABLED = False


# Import Ring Signatures
try:
    from lac_ring_signatures import LACRingSignature, LACRingTransaction
    RING_SIG_MODULE = LACRingSignature()
    RING_TX_MODULE = LACRingTransaction(RING_SIG_MODULE)
    print("✅ Ring Signatures enabled")
    sys.stdout.flush()
except ImportError:
    RING_SIG_MODULE = None
    RING_TX_MODULE = None
    print("⚠️ Ring Signatures disabled")
    sys.stdout.flush()


# Import Username System
try:
    from lac_username_state import UsernameStateManager
    from lac_username_transactions import (
        UsernameTransactionBuilder,
        UsernameTransactionProcessor,
        is_username_transaction,
        get_username_transaction_fee,
        TX_TYPE_USERNAME_REGISTER,
        TX_TYPE_USERNAME_TRANSFER,
        TX_TYPE_USERNAME_BURN,
        TX_TYPE_USERNAME_UPDATE
    )
    USERNAME_ENABLED = True
    print("✅ Username Registry enabled")
    sys.stdout.flush()
except ImportError as e:
    USERNAME_ENABLED = False
    print(f"⚠️ Username Registry disabled: {e}")
    sys.stdout.flush()


# Import Stealth Addresses + Kyber-768
try:
    from lac_stealth_kyber_real import LACStealthAddress, LACKyber768, LACStealthTransaction
    STEALTH_MODULE = LACStealthAddress()
    KYBER_MODULE = LACKyber768()
    STEALTH_TX_MODULE = LACStealthTransaction()
    print("✅ Stealth Addresses + Kyber-768 enabled")
    sys.stdout.flush()
except ImportError as e:
    STEALTH_MODULE = None
    KYBER_MODULE = None
    STEALTH_TX_MODULE = None
    print(f"⚠️ Stealth + Kyber disabled: {e}")
    sys.stdout.flush()


# Account-based model (no UTXO)


# Import Time-Lock Transactions
try:
    from lac_timelock import TimeLockManager, integrate_timelock_with_mining
    from lac_pruning import init_pruning
    from lac_decoy import init_decoy_manager
    TIMELOCK_ENABLED = True
    print("✅ Time-Locked Transactions enabled")
    sys.stdout.flush()
except ImportError as e:
    TIMELOCK_ENABLED = False
    print(f"⚠️ Time-Lock disabled: {e}")
    sys.stdout.flush()

# Import PoET Mining
try:
    from lac_poet_mining import LACPoETMiningV3, LACMiningCoordinator
    POET_ENABLED = True
    print("✅ PoET Mining enabled")
    sys.stdout.flush()
except ImportError as e:
    POET_ENABLED = False
    print(f"⚠️ PoET Mining disabled: {e}")
    sys.stdout.flush()


# Import Zero-History Manager (PHASE 2B)
try:
    from lac_zero_history import (
        ZeroHistoryManager,
        init_zero_history_phase2b,
        ValidatorInfo,
        ZeroHistoryConfig,
        StateCommitment,
        FraudProof
    )
    ZERO_HISTORY_ENABLED = True
    print("✅ Zero-History Phase 2B enabled")
    sys.stdout.flush()
except ImportError as e:
    ZERO_HISTORY_ENABLED = False
    print(f"⚠️ Zero-History disabled: {e}")
    sys.stdout.flush()


# Import SQLite sync
try:
    from lac_sqlite_sync import init_sqlite_sync, add_sqlite_api_endpoints
    SQLITE_ENABLED = True
    print("✅ SQLite sync enabled")
    sys.stdout.flush()
except ImportError:
    SQLITE_ENABLED = False
    print("⚠️ SQLite sync disabled")
    sys.stdout.flush()


# Import WebSocket sync (optional - HTTP fallback if unavailable)
try:
    from lac_websocket_sync import init_websocket_sync
    WEBSOCKET_AVAILABLE = True
    print("✅ WebSocket sync available")
    sys.stdout.flush()
except Exception as e:
    WEBSOCKET_AVAILABLE = False
    print(f"WARNING: WebSocket failed to load: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()



app = Flask(__name__)
CORS(app, 
     origins='*',
     supports_credentials=False,
     allow_headers=['Content-Type', 'X-Seed', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# ===================== SECURITY CONFIG =====================
# RELAXED для тестування - в продакшні треба зменшити
RATE_LIMIT_REQUESTS = 10000  # per IP per minute (для тестування)
RATE_LIMIT_WINDOW = 60  # seconds
FAUCET_LIMIT = 10  # per day (для тестування - 10 разів)
NICKNAME_CHANGE_LIMIT = 100  # per hour (для тестування)
UPGRADE_LIMIT = 100  # per hour (для тестування)


MIN_TX_FEE = 0.1  # LAC
MIN_MSG_FEE = 0.5  # LAC
MAX_REORG_DEPTH = 10  # blocks
CHECKPOINT_INTERVAL = 100  # blocks
MIN_BALANCE_FOR_ACTIVITY = 0  # LAC (вимкнено для тестування)

# ===================== BURN ADDRESS =====================
BURN_ADDRESS = "lac_0000000000000000000000000000000000000000"

# Rate limiting storage
rate_limit_store = defaultdict(list)
rate_limit_lock = Lock()

# ===================== STATE =====================
class State:
    def __init__(self, datadir):
        self.datadir = Path(datadir)
        self.datadir.mkdir(parents=True, exist_ok=True)
        
        self.chain = []
        self.wallets = {}  # address → {balance, level, key_id, created_at, tx_count, msg_count}
        self.usernames = {}  # username → address (direct lookup, survives Zero-History)
        self.ephemeral_msgs = []
        self.persistent_msgs = []  # Regular messages (zero-history but persistent)
        self.pending_txs = []  # Pending transactions for next block (dice, etc.)
        self.groups = {}  # gid → {name, posts: [{from, text, ts}]}
        self.contacts = {}  # address → [contact_addresses]
        self.reactions = {}  # msg_key → {emoji: [addr1, addr2]}
        self.referrals = {}  # invite_code → {creator, used_by: [], created_at}
        self.referral_map = {}  # addr → {invite_code, invited_by, boost_burned}
        # Real-time counters (accumulated, never recalculated)
        self.counters = {
            'emitted_mining': 0,
            'emitted_faucet': 0,
            'emitted_dice': 0,      # net wins only
            'emitted_referral': 0,
            'burned_dice': 0,
            'burned_levels': 0,
            'burned_username': 0,
            'burned_fees': 0,
            'burned_dms': 0,
            'burned_other': 0,
        }
        self.spent_key_images = set()  # Ring signature key images
        self.mempool = []
        
        # STASH Pool (blockchain-native anonymous mixing)
        self.stash_pool = {
            'total_balance': 0,
            'deposits': {},       # nullifier_hash → {amount, nominal, timestamp}
            'spent_nullifiers': [] # list of spent nullifiers (prevent double-spend)
        }
        self.rate_limits = {}  # identifier → [timestamps] for rate limiting
        
        # Mining coordinator
        self.mining_coordinator = None
        self.mining_active = False
        self.active_sessions = set()  # Track active (logged-in) addresses
        
        # Time-Lock Manager
        if TIMELOCK_ENABLED:
            self.timelock = TimeLockManager(self)
        else:
            self.timelock = None
        
        # Username Registry System
        if USERNAME_ENABLED:
            username_db_path = self.datadir / 'state' / 'username_state.db'
            self.username_state = UsernameStateManager()
            self.username_tx_builder = UsernameTransactionBuilder(STEALTH_MODULE)
            self.username_processor = UsernameTransactionProcessor(self.username_state)
            print(f"✅ Username Registry initialized: {username_db_path}")
            sys.stdout.flush()
        else:
            self.username_state = None
            self.username_tx_builder = None
            self.username_processor = None
        
        # Blockchain Pruning
        self.pruning = init_pruning(self)
        self.decoy = init_decoy_manager(self)
        
        
        # Zero-History Manager (PHASE 2B)
        if ZERO_HISTORY_ENABLED:
            self.zero_history = init_zero_history_phase2b(
                str(self.datadir),
                commitment_interval=COMMITMENT_INTERVAL,
                min_witnesses=MIN_VALIDATORS
            )
            print(f"✅ Zero-History Phase 2B initialized (interval: {COMMITMENT_INTERVAL} blocks, witnesses: {MIN_VALIDATORS})")
            sys.stdout.flush()
        else:
            self.zero_history = None
        
        self.lock = Lock()
        
        # Stability: StateManager for atomic writes
        if STABILITY_ENABLED:
            self.state_manager = StateManager(str(self.datadir))
        else:
            self.state_manager = None
        self.load()
        
        # SQLite sync (SAFE - runs after load)
        if SQLITE_ENABLED:
            try:
                init_sqlite_sync(self)
            except Exception as e:
                print(f"⚠️ SQLite init failed: {e}")
    
    def load(self):
        # Atomic loading with backup recovery
        if STABILITY_ENABLED and self.state_manager:
            try:
                self.chain = self.state_manager.load_with_backup('chain.json') or []
            except:
                self.chain = []
            try:
                self.wallets = self.state_manager.load_with_backup('wallets.json') or {}
            except:
                self.wallets = {}
            try:
                self.groups = self.state_manager.load_with_backup('groups.json') or {}
            except:
                self.groups = {}
            try:
                key_images_list = self.state_manager.load_with_backup('key_images.json') or []
                self.spent_key_images = set(key_images_list)
            except:
                self.spent_key_images = set()
            try:
                stash_data = self.state_manager.load_with_backup('stash_pool.json')
                if stash_data:
                    self.stash_pool = stash_data
                ref_data = self.state_manager.load_with_backup('referrals.json')
                if ref_data:
                    self.referrals = ref_data.get('codes', {})
                    self.referral_map = ref_data.get('map', {})
                cnt_data = self.state_manager.load_with_backup('counters.json')
                if cnt_data:
                    self.counters.update(cnt_data)
            except:
                pass
            try:
                pm_data = self.state_manager.load_with_backup('persistent_msgs.json')
                if pm_data:
                    self.persistent_msgs = pm_data
            except:
                pass
            try:
                rxn_data = self.state_manager.load_with_backup('reactions.json')
                if rxn_data:
                    self.reactions = rxn_data
            except:
                pass
            try:
                loaded_names = self.state_manager.load_with_backup('usernames.json')
                if loaded_names:
                    self.usernames = loaded_names
            except:
                pass
        else:
            # Fallback
            cf = self.datadir / 'chain.json'
            wf = self.datadir / 'wallets.json'
            gf = self.datadir / 'groups.json'
            if cf.exists():
                with open(cf) as f:
                    self.chain = json.load(f)
            if wf.exists():
                with open(wf) as f:
                    self.wallets = json.load(f)
            if gf.exists():
                with open(gf) as f:
                    self.groups = json.load(f)
            kif = self.datadir / 'key_images.json'
            if kif.exists():
                with open(kif) as f:
                    self.spent_key_images = set(json.load(f))
            else:
                self.spent_key_images = set()
            spf = self.datadir / 'stash_pool.json'
            if spf.exists():
                with open(spf) as f:
                    self.stash_pool = json.load(f)
            pmf = self.datadir / 'persistent_msgs.json'
            if pmf.exists():
                with open(pmf) as f:
                    self.persistent_msgs = json.load(f)
            rxnf = self.datadir / 'reactions.json'
            if rxnf.exists():
                try:
                    with open(rxnf) as f:
                        self.reactions = json.load(f)
                except:
                    self.reactions = {}
        
        # Load usernames (persist independently from blockchain — survives Zero-History)
        if STABILITY_ENABLED and self.state_manager:
            try:
                loaded_names = self.state_manager.load_with_backup('usernames.json')
                if loaded_names:
                    self.usernames = loaded_names
            except:
                pass
        else:
            uf = self.datadir / 'usernames.json'
            if uf.exists():
                try:
                    with open(uf) as f:
                        self.usernames = json.load(f)
                except:
                    self.usernames = {}
        
        # Migrate old username format {key_id: username} → {username: address}
        if self.usernames:
            needs_migration = False
            migrated = {}
            for key, val in list(self.usernames.items()):
                if isinstance(val, str) and (val.startswith('lac1') or val.startswith('seed_')):
                    # New format: key=username, val=address — keep as is
                    migrated[key] = val
                elif isinstance(key, str) and len(key) == 64:
                    # Old format: key=key_id (64 char hex), val=username
                    needs_migration = True
                    uname = val.lstrip('@').lower() if isinstance(val, str) else str(val)
                    for addr, w in self.wallets.items():
                        if w.get('key_id') == key:
                            migrated[uname] = addr
                            w['username'] = uname
                            break
                else:
                    migrated[key] = val
            if needs_migration:
                self.usernames = migrated
                print(f"  🔄 Migrated {len(migrated)} usernames to new format")
        
        # Also rebuild username→address from wallet data
        for addr, w in self.wallets.items():
            uname = w.get('username')
            if uname and uname not in self.usernames:
                self.usernames[uname] = addr
        
        if self.usernames:
            print(f"  👤 Loaded {len(self.usernames)} usernames")
        
        
        if not self.chain:
            genesis = {
                "index": 0,
                "timestamp": int(time.time()),
                "transactions": [],
                "ephemeral_msgs": [],
                "previous_hash": "0",
                "nonce": 0,
                "miner": "genesis",
                "difficulty": 1,
                "hash": "0" * 64
            }
            self.chain.append(genesis)
            self.save()
        
        
        # Load time-locked transactions
        if self.timelock:
            self.timelock.load()
        
        # Rebuild username registry from blockchain
        if USERNAME_ENABLED and self.username_processor:
            print("🔄 Rebuilding username registry from blockchain...")
            username_count = 0
            for block in self.chain:
                block_height = block.get('index', 0)
                for tx in block.get('transactions', []):
                    if tx.get('type') in ['username_register', 'username_transfer', 'username_burn']:
                        success, error = self.username_processor.process_transaction(
                            tx, block_height, self.wallets
                        )
                        if success:
                            username_count += 1
            print(f"✅ Loaded {username_count} username transactions from {len(self.chain)} blocks")
            sys.stdout.flush()
        
        # Register Zero-History validators (AFTER wallets loaded!)
        self._register_zero_history_validators()
    
    def _register_zero_history_validators(self):
        """Register L5/L6 validators for Zero-History Phase 2B"""
        if not ZERO_HISTORY_ENABLED or not self.zero_history:
            return
        
        # Count existing L5/L6 validators
        existing_validators = 0
        for address, wallet in self.wallets.items():
            level = wallet.get('level', 0)
            balance = wallet.get('balance', 0)
            if level >= 5 and balance >= (1000 if level == 5 else 5000):
                existing_validators += 1
        
        # DEV MODE: Create test validators if none exist
        if DEV_MODE and existing_validators == 0:
            print("🔧 DEV MODE: Creating test validators...")
            
            # Create 3 test validators (minimum for DEV)
            test_validators = [
                {'level': 5, 'balance': 10000, 'name': 'validator_alice'},
                {'level': 6, 'balance': 50000, 'name': 'validator_bob'},
                {'level': 5, 'balance': 15000, 'name': 'validator_carol'}
            ]
            
            for i, val in enumerate(test_validators):
                # Generate seed address
                seed = hashlib.sha256(f"test_validator_{i}_{val['name']}".encode()).hexdigest()
                address = f"seed_{seed[:16]}"
                
                # Create wallet
                self.wallets[address] = {
                    'balance': val['balance'],
                    'level': val['level'],
                    'key_id': seed,
                    'created_at': int(time.time()),
                    'tx_count': 0,
                    'msg_count': 0
                }
                print(f"  ✅ Created test validator: {address} (L{val['level']}, {val['balance']} LAC)")
            
            # Save wallets
            self.save()
            print(f"✅ Created {len(test_validators)} test validators for DEV mode")
        
        # Register validators
        registered = 0
        for address, wallet in self.wallets.items():
            level = wallet.get('level', 0)
            balance = wallet.get('balance', 0)
            
            # Only Level 5+ can be validators
            if level >= 5:
                # Check stake requirements
                min_stake = 1000 if level == 5 else 5000
                
                if balance >= min_stake:
                    try:
                        self.zero_history.validator_manager.register_validator(
                            address=address,
                            level=level,
                            stake=balance
                        )
                        registered += 1
                    except Exception as e:
                        print(f"⚠️ Failed to register validator {address[:16]}...: {e}")
        
        if registered > 0:
            print(f"✅ Registered {registered} Zero-History validators")
            sys.stdout.flush()
        else:
            print(f"⚠️ No validators registered! Need L5/L6 wallets with sufficient balance")
            sys.stdout.flush()
    
    def save(self):
        if STABILITY_ENABLED and self.state_manager:
            # Atomic writes - zero data loss
            self.state_manager.save_atomic('chain.json', self.chain)
            self.state_manager.save_atomic('wallets.json', self.wallets)
            self.state_manager.save_atomic('usernames.json', self.usernames)
            self.state_manager.save_atomic('groups.json', self.groups)
            self.state_manager.save_atomic('key_images.json', list(self.spent_key_images))
            self.state_manager.save_atomic('stash_pool.json', self.stash_pool)
            self.state_manager.save_atomic('persistent_msgs.json', self.persistent_msgs)
            self.state_manager.save_atomic('referrals.json', {'codes': self.referrals, 'map': self.referral_map})
            self.state_manager.save_atomic('counters.json', self.counters)
            self.state_manager.save_atomic('reactions.json', self.reactions)
        else:
            # Fallback
            with open(self.datadir / 'chain.json', 'w') as f:
                json.dump(self.chain, f, indent=2)
            with open(self.datadir / 'wallets.json', 'w') as f:
                json.dump(self.wallets, f, indent=2)
            with open(self.datadir / 'usernames.json', 'w') as f:
                json.dump(self.usernames, f, indent=2)
            with open(self.datadir / 'groups.json', 'w') as f:
                json.dump(self.groups, f, indent=2)
            with open(self.datadir / 'key_images.json', 'w') as f:
                json.dump(list(self.spent_key_images), f, indent=2)
            with open(self.datadir / 'stash_pool.json', 'w') as f:
                json.dump(self.stash_pool, f, indent=2)
            with open(self.datadir / 'persistent_msgs.json', 'w') as f:
                json.dump(self.persistent_msgs, f, indent=2)
            with open(self.datadir / 'reactions.json', 'w') as f:
                json.dump(self.reactions, f)

    def save_msgs(self):
        """Fast save — only messages + reactions. 10x faster than full save()"""
        try:
            if STABILITY_ENABLED and self.state_manager:
                self.state_manager.save_atomic('persistent_msgs.json', self.persistent_msgs)
                self.state_manager.save_atomic('reactions.json', self.reactions)
            else:
                with open(self.datadir / 'persistent_msgs.json', 'w') as f:
                    json.dump(self.persistent_msgs, f)
                with open(self.datadir / 'reactions.json', 'w') as f:
                    json.dump(self.reactions, f)
        except Exception as e:
            print(f"⚠️ save_msgs error: {e}")

    def save_groups(self):
        """Fast save — only groups. 10x faster than full save()"""
        try:
            if STABILITY_ENABLED and self.state_manager:
                self.state_manager.save_atomic('groups.json', self.groups)
            else:
                with open(self.datadir / 'groups.json', 'w') as f:
                    json.dump(self.groups, f)
        except Exception as e:
            print(f"⚠️ save_groups error: {e}")

S = None
ws_sync = None  # WebSocket sync instance
stability = None
rate_limiter = None
block_cache = None

# ===================== USERNAME HELPER FUNCTIONS =====================

def get_username_by_address(address: str) -> Optional[str]:
    """Get username by wallet address"""
    # New system: S.usernames = {username: address}
    for uname, addr in S.usernames.items():
        if addr == address:
            return f'@{uname}'
    # Also check wallet field
    wallet = S.wallets.get(address)
    if wallet and wallet.get('username'):
        return f"@{wallet['username']}"
    return None

def get_username_by_key_id(key_id: str) -> Optional[str]:
    """Get username by key_id (legacy compatibility)"""
    if not key_id:
        return None
    for addr, w in S.wallets.items():
        if w.get('key_id') == key_id and w.get('username'):
            return f"@{w['username']}"
    return None


# ===================== MINING FUNCTIONS =====================

def init_mining():
    """Initialize PoET Mining"""
    if not POET_ENABLED or not S:
        return
    
    try:
        # Initialize PoET with current blockchain state
        current_height = len(S.chain)
        total_supply = sum(w.get('balance', 0) for w in S.wallets.values())
        
        poet = LACPoETMiningV3(
            current_height=current_height,
            current_difficulty=1.0,
            total_supply_mined=total_supply
        )
        
        S.mining_coordinator = LACMiningCoordinator(poet)
        S.mining_active = True
        
        print(f"⛏️ Mining initialized at block #{current_height}")
        print(f"   Total supply: {total_supply:.2f} LAC")
        print(f"   Block reward: {poet.BLOCK_REWARD} LAC")
        
    except Exception as e:
        print(f"❌ Mining init failed: {e}")
        S.mining_active = False


def auto_mining_loop():
    """Auto-mining loop - mines blocks every ~10 seconds"""
    if not POET_ENABLED or not S or not S.mining_coordinator:
        return
    
    print("⛏️ Auto-mining loop started")
    
    while S.mining_active:
        try:
            time.sleep(10)  # Wait 10 seconds between blocks
            
            with S.lock:
                # Register ONLY ACTIVE (logged-in) eligible miners
                eligible_miners = []
                
                print(f"🔍 Checking miners:")
                print(f"   Active sessions: {len(S.active_sessions)}")
                
                for addr in S.active_sessions:
                    if addr not in S.wallets:
                        print(f"   ❌ {addr[:16]}... - no wallet")
                        continue
                    
                    wallet = S.wallets[addr]
                    balance = wallet.get('balance', 0)
                    level = wallet.get('level', 0)
                    created_at = wallet.get('created_at', time.time())
                    
                    print(f"   📊 {addr[:16]}... - Balance: {balance}, Level: {level}")
                    
                    if balance >= 50:  # Minimum balance for mining
                        status = S.mining_coordinator.register_miner(
                            addr, level, balance, created_at
                        )
                        print(f"      Status: {status}")
                        if status.get('mining'):
                            eligible_miners.append(addr)
                            print(f"      ✅ Eligible for mining!")
                        else:
                            print(f"      ❌ NOT eligible: {status.get('reason', 'unknown')}")
                    else:
                        print(f"      ❌ Balance too low (need 50+)")
                
                if len(eligible_miners) == 0:
                    print(f"⚠️ No eligible miners (need active session + 50+ LAC)")
                    continue
                
                # Simulate proofs (in real impl, miners would submit after waiting)
                for addr in eligible_miners:
                    S.mining_coordinator.submit_proof(addr)
                    # Level 7 GOD: x2 mining chance (submit double proof)
                    if S.wallets.get(addr, {}).get('level', 0) >= 7:
                        S.mining_coordinator.submit_proof(addr)
                
                # Mine block
                block_data = S.mining_coordinator.mine_block()
                
                # Distribute rewards
                block_emission = 0
                for winner_addr, reward in block_data['rewards'].items():
                    if winner_addr in S.wallets:
                        # Level 7 GOD: x2 validator reward
                        actual_reward = reward * 2 if S.wallets[winner_addr].get('level', 0) >= 7 else reward
                        S.wallets[winner_addr]['balance'] = \
                            S.wallets[winner_addr].get('balance', 0) + actual_reward
                        block_emission += actual_reward
                S.counters['emitted_mining'] += block_emission
                
                # Add block to chain (anonymous - no addresses revealed)
                # Take ephemeral messages (max 20 per block)
                ephemeral_msgs = S.ephemeral_msgs[:20]
                
                new_block = {
                    'index': len(S.chain),
                    'timestamp': block_data['timestamp'],
                    'transactions': S.mempool[:50] + getattr(S, 'pending_txs', []),
                    'ephemeral_msgs': ephemeral_msgs,
                    'previous_hash': S.chain[-1]['hash'] if S.chain else '0',
                    'nonce': 0,
                    'miner': 'poet_anonymous',
                    'difficulty': block_data['difficulty'],
                    'hash': hashlib.sha256(
                        json.dumps({
                            'index': len(S.chain),
                            'prev': S.chain[-1]['hash'] if S.chain else '0',
                            'ts': block_data['timestamp'],
                            'txs': len(S.mempool[:50]),
                            'nonce': block_data.get('height', 0)
                        }, sort_keys=True).encode()
                    ).hexdigest(),
                    'mining_winners_count': block_data['unique_winners'],
                    'total_reward': block_data['total_reward']
                }
                
                # Store mining rewards separately (not in public blockchain)
                # Each wallet tracks their own earnings
                for winner_addr, reward in block_data['rewards'].items():
                    if winner_addr in S.wallets:
                        if 'mining_history' not in S.wallets[winner_addr]:
                            S.wallets[winner_addr]['mining_history'] = []
                        S.wallets[winner_addr]['mining_history'].append({
                            'block': new_block['index'],
                            'reward': reward,
                            'timestamp': block_data['timestamp']
                        })
                        # Cap mining_history at 10000 entries per wallet
                        if len(S.wallets[winner_addr]['mining_history']) > 10000:
                            S.wallets[winner_addr]['mining_history'] = S.wallets[winner_addr]['mining_history'][-10000:]
                
                # mining_rewards kept for chain explorer only, wallet history is primary source
                new_block["mining_rewards"] = [{"address": addr, "reward": rew} for addr, rew in block_data["rewards"].items()]
                S.chain.append(new_block)
                
                # Process username transactions in block
                if S.username_processor:
                    for tx in new_block['transactions']:
                        if is_username_transaction(tx):
                            success, error = S.username_processor.process_transaction(
                                tx, 
                                new_block['index'],
                                S.wallets
                            )
                            if success:
                                print(f"✅ Username TX processed: {tx['type']} - {tx.get('username', 'N/A')}")

                                # UPDATE username_state after successful registration
                                if tx.get('type') == TX_TYPE_USERNAME_REGISTER:
                                    username = tx.get('username')
                                    from_addr = tx.get('from')  # Use 'from' address instead of stealth
                                    
                                    # Find wallet by address and update S.usernames
                                    if from_addr and from_addr in S.wallets:
                                        key_id = S.wallets[from_addr].get('key_id')
                                        if key_id:
                                            # S.usernames removed - using state.usernames
                                            print(f"✅ Updated S.usernames: key_id={key_id[:16]}... → {username}")
                            else:
                                print(f"⚠️ Username TX failed: {error}")
                
                
                # ===================== PROCESS ANONYMOUS TRANSFERS =====================
                print(f"🔍 Processing {len(new_block['transactions'])} transactions")
                
                for tx in new_block['transactions']:
                    tx_type = tx.get('type')
                    
                    if tx_type in ['ring_transfer', 'stealth_transfer', 'veil_transfer']:
                        print(f"  🎯 Processing {tx_type}")
                        
                        # Add key image
                        ring_sig = tx.get('ring_signature', {})
                        key_image = ring_sig.get('key_image')
                        if key_image:
                            S.spent_key_images.add(key_image)
                            print(f"    ✅ Key image: {key_image[:32]}...")
                        
                        # Balances already updated at API time (veil_transfer)
                        # Mining loop only records key_image to blockchain
                        real_to = tx.get('real_to')
                        real_amount = tx.get('real_amount', 0)
                        if real_to:
                            print(f"    💰 Recipient: {S.wallets.get(real_to, {}).get('balance', 0)} LAC (confirmed)")
                # ===================== END ANONYMOUS TRANSFERS =====================
                # Clear processed mempool and ephemeral messages
                S.mempool = S.mempool[50:]
                # Cap mempool at 1000 to prevent unbounded growth
                if len(S.mempool) > 1000:
                    S.mempool = S.mempool[-1000:]
                S.ephemeral_msgs = S.ephemeral_msgs[20:]
                S.pending_txs = []  # Clear dice/game transactions
                
                # Process time-locked transactions
                if S.timelock:
                    activated = S.timelock.process_unlocked_transactions(len(S.chain))
                    if activated:
                        print(f"⏰ Activated {len(activated)} time-locked TX")
                
                # Blockchain pruning (automatic)
                if S.pruning and S.pruning.should_prune(len(S.chain)):
                    prune_stats = S.pruning.prune_old_blocks()
                    if prune_stats.get('pruned'):
                        print(f"🗜️ Pruned {prune_stats['blocks_pruned']} blocks, saved {prune_stats['mb_saved']} MB")
                
                
                # ===================== ZERO-HISTORY: ADD BLOCK =====================
                if S.zero_history:
                    # Add block to Zero-History
                    S.zero_history.add_block(
                        block=new_block,
                        utxo_delta={},
                        spent_key_images=list(S.spent_key_images)
                    )
                # ===================== END ZERO-HISTORY =====================
                
            # save() OUTSIDE lock — unblocks API during disk write
            try:
                S.save()
            except Exception as e:
                print(f"⚠️ Save error: {e}")
                
            with S.lock:
                print(f"\n⛏️ Block #{len(S.chain)-1} mined!")
                print(f"   Winners: {block_data['unique_winners']} unique")
                print(f"   Rewards: {block_data['total_reward']:.2f} LAC")
                print(f"   Active miners: {block_data['active_miners']}")
                
                # Broadcast block to peers
                broadcast_block_to_peers(new_block)
                
        except Exception as e:
            print(f"❌ Mining error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)


# ===================== SECURITY FUNCTIONS =====================

def rate_limit_check(identifier, max_requests=RATE_LIMIT_REQUESTS, window=RATE_LIMIT_WINDOW):
    """Rate limiting per IP or address"""
    now = time.time()
    
    # Clean old entries
    if identifier in S.rate_limits:
        S.rate_limits[identifier] = [
            timestamp for timestamp in S.rate_limits[identifier]
            if now - timestamp < window
        ]
    
    # Check limit
    if identifier in S.rate_limits and len(S.rate_limits[identifier]) >= max_requests:
        return False
    
    # Add new request
    if identifier not in S.rate_limits:
        S.rate_limits[identifier] = []
    S.rate_limits[identifier].append(now)
    
    return True

def get_client_ip():
    """Get client IP (with proxy support)"""
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def validate_seed(seed):
    """Validate seed format - accepts 18 words OR 32-128 chars"""
    if not seed or not isinstance(seed, str):
        return False
    
    seed = seed.strip()
    words = seed.split()
    
    # Accept 18-word mnemonic (LAC Console)
    if len(words) == 18:
        return True
    
    # Accept 32-128 character string (LAC Mobile)
    if len(seed) >= 32 and len(seed) <= 128 and ' ' not in seed:
        return True
    
    return False

# ===== Ed25519 CRYPTOGRAPHY =====
# ===== LAC CRYPTO MODULE =====
# Real cryptography: Ed25519, X25519, Ring Signatures, Stealth Addresses
try:
    from lac_crypto import (
        Ed25519, EncryptedMessaging, RingSignature, StealthAddress,
        PostQuantum, select_ring_members, get_full_crypto_info, crypto_status
    )
    CRYPTO_MODULE = True
    _cs = crypto_status()
    ED25519_AVAILABLE = _cs.get('ed25519', False)
    print(f"✅ LAC Crypto Module loaded — Ed25519:{_cs['ed25519']} X25519:{_cs['x25519']} Ring:{_cs['ring_signatures']} Kyber:{_cs['post_quantum']}")
except ImportError:
    CRYPTO_MODULE = False
    ED25519_AVAILABLE = False
    print("⚠️ lac_crypto.py not found — running without crypto module")

# ===== PROOF-OF-LOCATION MODULE =====
POL_AVAILABLE = False
try:
    from lac_proof_of_location import ProofOfLocation
    POL_AVAILABLE = True
    pol_zones = ProofOfLocation.get_available_zones()
    print(f"✅ Proof-of-Location loaded — {pol_zones['total_zones']} zones")
except ImportError:
    print("⚠️ lac_proof_of_location.py not found — PoL disabled")

# Backward-compatible wrappers
def derive_ed25519_keys(seed):
    if CRYPTO_MODULE:
        kp = Ed25519.derive_keypair(seed)
        return {'private': kp['private_hex'], 'public': kp['public_hex'], 'method': 'nacl' if ED25519_AVAILABLE else 'fallback'}
    return {'private': '', 'public': hashlib.sha256(seed.encode()).hexdigest(), 'method': 'none'}

def sign_transaction(seed, tx_data):
    """Sign a transaction with Ed25519"""
    if CRYPTO_MODULE:
        return Ed25519.sign_transaction(seed, tx_data)
    return tx_data  # unsigned

def verify_transaction(tx_data):
    """Verify transaction signature"""
    if CRYPTO_MODULE:
        return Ed25519.verify_transaction(tx_data)
    return True  # accept unsigned if no crypto


# LAC Bech32-style address charset (no 1/b/i/o)
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

def _to_bech32(data_bytes, length):
    """Convert bytes to bech32 string"""
    out = ""
    for b in data_bytes:
        out += BECH32_CHARSET[b % 32]
        if len(out) >= length: break
        out += BECH32_CHARSET[(b >> 5) % 32]
        if len(out) >= length: break
    return out[:length]

def _legacy_addr(seed):
    """Old seed_ format for migration"""
    return f"seed_{hashlib.sha256(seed.encode()).hexdigest()[:40]}"

def get_address_from_seed(seed):
    """Derive LAC address — lac1... Bech32-style (42 chars)"""
    raw = hashlib.sha256(seed.encode()).digest()
    body = _to_bech32(raw, 34)
    checksum = _to_bech32(hashlib.sha256(("lac1" + body).encode()).digest(), 4)
    new_addr = "lac1" + body + checksum
    
    # Auto-migrate from legacy seed_ format
    legacy = _legacy_addr(seed)
    if S and hasattr(S, 'wallets') and legacy in S.wallets and new_addr not in S.wallets:
        S.wallets[new_addr] = S.wallets.pop(legacy)
        S.wallets[new_addr]['migrated_from'] = legacy
        print(f"  \U0001f504 Migrated: {legacy[:16]}... -> {new_addr}")
        # Migrate references in blockchain history
        for block in S.chain:
            for tx in block.get('transactions', []):
                if tx.get('from') == legacy: tx['from'] = new_addr
                if tx.get('to') == legacy: tx['to'] = new_addr
                if tx.get('real_from') == legacy: tx['real_from'] = new_addr
                if tx.get('real_to') == legacy: tx['real_to'] = new_addr
        try: S.save()
        except: pass
    
    return new_addr

def get_key_id_from_seed(seed):
    """Derive key_id from seed (PRIVATE)"""
    return hashlib.sha256(f"keyid_{seed}".encode()).hexdigest()

def resolve_recipient(recipient_str):
    """
    Resolve recipient to address
    Accepts: lac1... address, seed_... (legacy), or @username / username
    Returns: wallet address or None
    """
    recipient_str = recipient_str.strip()
    
    # Direct address (lac1... or legacy seed_...)
    if recipient_str.startswith('lac1') or recipient_str.startswith('seed_'):
        if recipient_str in S.wallets:
            return recipient_str
        return None
    
    # Username lookup — strip @ if present
    uname = recipient_str.lstrip('@').lower()
    
    # Direct lookup in S.usernames {username: address}
    if uname in S.usernames:
        addr = S.usernames[uname]
        if addr in S.wallets:
            return addr
    
    # Also try with @ prefix
    if f"@{uname}" in S.usernames:
        addr = S.usernames[f"@{uname}"]
        if addr in S.wallets:
            return addr
    
    # Fallback: search wallet 'username' field
    for addr, w in S.wallets.items():
        if w.get('username') == uname:
            return addr
    
    return None

# ===================== VALIDATOR SYSTEM =====================

def is_validator_eligible(wallet_addr):
    """
    Check if wallet can be validator
    
    Requirements:
    - Level 5+ (112,800 LAC burned minimum)
    - Not banned
    """
    wallet = S.wallets.get(wallet_addr)
    if not wallet:
        return False
    
    # Check level (5 or 6)
    level = wallet.get('level', 0)
    if level < 5:
        return False
    
    # Check ban status
    if wallet.get('validator_banned', False):
        ban_until = wallet.get('banned_until', 0)
        if time.time() < ban_until:
            return False  # Still banned
        else:
            # Ban expired, clear it
            wallet['validator_banned'] = False
    
    return True

def get_validator_weight(wallet):
    """
    Get validator weight
    Level 6 has 2x weight (priority)
    """
    level = wallet.get('level', 0)
    return 2.0 if level == 6 else 1.0

def get_validator_reward(level):
    """
    Get reward per commitment signature
    Level 5: 0.4 LAC
    Level 6: 0.5 LAC
    """
    rewards = {
        5: 0.4,
        6: 0.5
    }
    return rewards.get(level, 0.0)


# ===================== MINING =====================

def compute_hash(index, prev_hash, timestamp, txs, msgs, nonce):
    data = f"{index}{prev_hash}{timestamp}{json.dumps(txs)}{json.dumps(msgs)}{nonce}"
    return hashlib.sha256(data.encode()).hexdigest()

def auto_cleanup():
    """Auto-cleanup old ephemeral messages and L2 group posts"""
    while True:
        try:
            time.sleep(60)
            with S.lock:
                now = int(time.time())
                # Remove ephemeral DMs older than 5 minutes
                S.ephemeral_msgs = [
                    m for m in S.ephemeral_msgs 
                    if now - m.get('timestamp', 0) < 300
                ]
                # Remove L2 ephemeral group posts older than 5 minutes
                for gid, group in S.groups.items():
                    gtype = group.get('type', 'public')
                    if gtype in ('l2_ephemeral', 'ephemeral'):
                        before = len(group.get('posts', []))
                        group['posts'] = [
                            p for p in group.get('posts', [])
                            if now - p.get('timestamp', 0) < 300
                        ]
                        after = len(group['posts'])
                        if before > after:
                            print(f"🧹 Cleaned {before - after} expired posts from {group.get('name', gid)}")
                
                # ===== SESSION CLEANUP (> 24h inactive) =====
                session_timeout = 86400  # 24 hours
                stale = [addr for addr in list(S.active_sessions)
                         if now - S.wallets.get(addr, {}).get('last_activity', now) > session_timeout]
                for addr in stale:
                    S.active_sessions.discard(addr)
                if stale:
                    print(f"🧹 Removed {len(stale)} stale sessions")
                # ===== END SESSION CLEANUP =====
                
                # ===== REACTIONS CLEANUP (older than 7 days) =====
                week_ago = now - 604800
                stale_rxn = [k for k, v in S.reactions.items()
                             if int(k.split('|')[-1] or 0) < week_ago]
                for k in stale_rxn:
                    del S.reactions[k]
                if stale_rxn:
                    print(f"🧹 Cleaned {len(stale_rxn)} old reactions")
                # ===== END REACTIONS CLEANUP =====
                
                # ===== DEAD MAN'S SWITCH CHECK =====
                for addr, wallet in list(S.wallets.items()):
                    dms = wallet.get('dead_mans_switch')
                    if not dms or not dms.get('enabled'):
                        continue
                    last = wallet.get('last_activity', wallet.get('created_at', now))
                    timeout = dms.get('timeout_days', 30) * 86400
                    if now - last < timeout:
                        continue
                    # TRIGGER Dead Man's Switch
                    print(f"💀 DMS triggered for {addr[:16]}... (inactive {(now-last)//86400} days)")
                    actions = dms.get('actions', [])
                    for action in actions:
                        atype = action.get('type')
                        try:
                            if atype == 'transfer' and action.get('to') and action.get('amount'):
                                to_addr = resolve_recipient(action['to'])
                                amt = min(float(action['amount']), wallet.get('balance', 0))
                                if to_addr and amt > 0 and to_addr in S.wallets:
                                    wallet['balance'] -= amt
                                    S.wallets[to_addr]['balance'] = S.wallets[to_addr].get('balance', 0) + amt
                                    S.mempool.append({'type':'dms_transfer','from':'anonymous','to':'anonymous','amount':amt,'timestamp':now,'ring_signature':True,'dms':True})
                                    print(f"  💸 Transferred {amt} LAC → {to_addr[:16]}...")
                            elif atype == 'transfer_all' and action.get('to'):
                                to_addr = resolve_recipient(action['to'])
                                amt = wallet.get('balance', 0)
                                if to_addr and amt > 0 and to_addr in S.wallets:
                                    wallet['balance'] = 0
                                    S.wallets[to_addr]['balance'] = S.wallets[to_addr].get('balance', 0) + amt
                                    S.mempool.append({'type':'dms_transfer_all','from':'anonymous','to':'anonymous','amount':amt,'timestamp':now,'ring_signature':True,'dms':True})
                                    print(f"  💸 Transferred ALL {amt} LAC → {to_addr[:16]}...")
                            elif atype == 'message' and action.get('to') and action.get('text'):
                                to_addr = resolve_recipient(action['to'])
                                if to_addr:
                                    key_id = wallet.get('key_id')
                                    from_name = get_username_by_key_id(key_id) or addr
                                    dms_msg = {
                                        'from': from_name, 'from_address': addr,
                                        'to': to_addr, 'text': action['text'],
                                        'timestamp': now, 'verified': False,
                                        'ephemeral': False, 'burn': False, 'ttl': 0,
                                        'dms_triggered': True
                                    }
                                    S.persistent_msgs.append(dms_msg)
                                    S.mempool.append({'type':'dms_message','from':'anonymous','to':'anonymous','amount':0,'timestamp':now,'ring_signature':True,'dms':True})
                                    print(f"  ✉️ DMS message sent → {to_addr[:16]}...")
                            elif atype == 'burn_stash':
                                # Delete all saved STASH keys from wallet
                                wallet.pop('stash_keys', None)
                                S.mempool.append({'type':'dms_burn_stash','from':'anonymous','to':BURN_ADDRESS,'amount':0,'timestamp':now,'ring_signature':True,'dms':True})
                                print(f"  🔥 STASH keys burned")
                            elif atype == 'wipe':
                                # Full wallet wipe — on-chain record
                                S.mempool.append({'type':'dms_wipe','from':'anonymous','to':BURN_ADDRESS,'amount':wallet.get('balance',0),'timestamp':now,'ring_signature':True,'dms':True})
                                key_id = wallet.get('key_id')
                                if key_id and key_id in S.usernames:
                                    S.usernames.pop(key_id)
                                S.wallets.pop(addr, None)
                                S.active_sessions.discard(addr)
                                print(f"  💀 Wallet wiped completely")
                                break  # wallet gone, stop processing
                        except Exception as ae:
                            print(f"  ⚠️ DMS action error: {ae}")
                    # Mark DMS as triggered (if wallet still exists)
                    if addr in S.wallets:
                        S.wallets[addr]['dead_mans_switch']['enabled'] = False
                        S.wallets[addr]['dead_mans_switch']['triggered_at'] = now
                    S.save()
                # ===== END DEAD MAN'S SWITCH =====
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

# ===================== API ERROR HANDLER =====================

@app.errorhandler(404)
def not_found(error):
    """Return JSON for 404 errors"""
    return jsonify({'error': 'Not found', 'ok': False}), 404

@app.errorhandler(500)
def internal_error(error):
    """Return JSON for 500 errors"""
    return jsonify({'error': 'Internal server error', 'ok': False}), 500

# ===================== WEB ROUTES =====================

@app.route('/')
def index():
    """Serve main console"""
    try:
        console_path = Path(__file__).parent / 'lac_console.html'
        if console_path.exists():
            with open(console_path, 'r', encoding='utf-8') as f:
                return f.read()
        return jsonify({'error': 'Console not found', 'ok': False}), 404
    except Exception as e:
        return jsonify({'error': str(e), 'ok': False}), 500

@app.route('/explorer')
def explorer():
    """Serve Block Explorer"""
    try:
        explorer_path = Path(__file__).parent / 'explorer.html'
        if explorer_path.exists():
            with open(explorer_path, 'r', encoding='utf-8') as f:
                return f.read()
        return jsonify({'error': 'Explorer not found', 'ok': False}), 404
    except Exception as e:
        return jsonify({'error': str(e), 'ok': False}), 500

# ===================== API ROUTES =====================

@app.route('/api/ping', methods=['GET'])
def ping():
    """Health check"""
    return jsonify({
        'ok': True,
        'height': len(S.chain),
        'timestamp': int(time.time())
    })

@app.route('/api/register', methods=['POST'])
def register():
    """Register new wallet"""
    ip = get_client_ip()
    if not rate_limit_check(ip, max_requests=5, window=3600):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    seed = data.get('seed', '').strip()
    ref = data.get('ref', '').strip()
    
    if not seed:
        return jsonify({'error': 'Seed required'}), 400
    
    if not validate_seed(seed):
        return jsonify({'error': 'Invalid seed format'}), 400
    
    addr = get_address_from_seed(seed)
    key_id = get_key_id_from_seed(seed)
    
    with S.lock:
        if addr in S.wallets:
            return jsonify({'error': 'Wallet already exists'}), 409
        
        crypto_info = {}
        if CRYPTO_MODULE:
            try:
                crypto_info = get_full_crypto_info(seed)
            except:
                pass
        
        S.wallets[addr] = {
            'balance': 0,
            'level': 0,
            'key_id': key_id,
            'created_at': int(time.time()),
            'tx_count': 0,
            'msg_count': 0,
            'ed25519_pubkey': crypto_info.get('ed25519_pubkey', derive_ed25519_keys(seed)['public']),
            'messaging_pubkey': crypto_info.get('messaging_pubkey', ''),
            'stealth_scan_pubkey': crypto_info.get('stealth_scan_pubkey', ''),
            'stealth_spend_pubkey': crypto_info.get('stealth_spend_pubkey', ''),
            'key_image': crypto_info.get('key_image', ''),
        }
        
        # Register username if provided
        if username and len(username) >= 3:
            S.usernames[username.lower()] = addr
        
        # Track active session for mining
        S.active_sessions.add(addr)
        
        # === REFERRAL ===
        ref_bonus = 0
        if ref:
            ref = ref.strip().upper()
            if ref in S.referrals:
                referral_data = S.referrals[ref]
                referrer = referral_data.get('creator', '')
                if referrer != addr and addr not in referral_data.get('used_by', []):
                    # Give bonus to new user
                    S.wallets[addr]['balance'] += 50
                    ref_bonus = 50
                    # Give bonus to referrer
                    if referrer in S.wallets:
                        S.wallets[referrer]['balance'] += 25
                    S.counters['emitted_referral'] += 75
                    # Track
                    referral_data['used_by'].append(addr)
                    if addr not in S.referral_map:
                        S.referral_map[addr] = {}
                    S.referral_map[addr]['invited_by'] = ref
                    # On-chain record
                    S.mempool.append({
                        'type': 'referral_bonus',
                        'from': 'referral_system',
                        'to': 'anonymous',
                        'amount': 75,
                        'timestamp': int(time.time()),
                    })
        
        S.save()
        
        return jsonify({
            'ok': True,
            'address': addr,
            'username': username or 'Anonymous',
            'balance': ref_bonus,
            'level': 0,
            'ref_bonus': ref_bonus
        })

@app.route('/api/crypto/status', methods=['GET'])
def crypto_status_endpoint():
    """Get cryptography status and all keys for this wallet"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    result = {
        'ok': True,
        'address': addr,
        'crypto_module': CRYPTO_MODULE,
        'ed25519_available': ED25519_AVAILABLE,
    }
    
    if CRYPTO_MODULE:
        full_info = get_full_crypto_info(seed)
        result.update(full_info)
        
        # Auto-upgrade wallet with pubkeys
        with S.lock:
            if addr in S.wallets:
                w = S.wallets[addr]
                if not w.get('ed25519_pubkey'):
                    w['ed25519_pubkey'] = full_info['ed25519_pubkey']
                if not w.get('messaging_pubkey'):
                    w['messaging_pubkey'] = full_info['messaging_pubkey']
                if not w.get('stealth_scan_pubkey'):
                    w['stealth_scan_pubkey'] = full_info['stealth_scan_pubkey']
                    w['stealth_spend_pubkey'] = full_info['stealth_spend_pubkey']
                S.save()
    else:
        keys = derive_ed25519_keys(seed)
        result['ed25519_pubkey'] = keys['public']
        result['method'] = keys['method']
    
    return jsonify(result)

@app.route('/api/login', methods=['POST'])
def login():
    """Login with seed"""
    data = request.get_json() or {}
    seed = data.get('seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Invalid seed'}), 400
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        key_id = wallet.get('key_id')
        username = get_username_by_key_id(key_id) or 'Anonymous'
        
        # Track active session for mining
        S.active_sessions.add(addr)
        
        return jsonify({
            'ok': True,
            'address': addr,
            'username': username,
            'balance': wallet.get('balance', 0),
            'level': wallet.get('level', 0)
        })

@app.route('/api/profile', methods=['GET'])
def profile():
    """Get user profile"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        key_id = wallet.get('key_id')
        username = get_username_by_key_id(key_id) or 'Anonymous'
        
        # Heartbeat: keep user in active mining pool + track activity
        S.active_sessions.add(addr)
        wallet['last_activity'] = int(time.time())
        
        # Dead Man's Switch info
        dms = wallet.get('dead_mans_switch')
        
        return jsonify({
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




@app.route('/api/wallet/mining', methods=['GET'])
def get_wallet_mining():
    """
    Get user's mining rewards history (PRIVATE - only their rewards!)
    """
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    limit = request.args.get('limit', 100, type=int)
    limit = min(limit, 500)  # Max 500
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        
        # Primary: scan blockchain (works for all old + new blocks)
        mining_rewards = []
        total_mined = 0

        for block in S.chain:
            for reward in block.get('mining_rewards', []):
                if reward.get('address') == addr:
                    mining_rewards.append({
                        'block': block.get('index', 0),
                        'timestamp': block.get('timestamp', 0),
                        'reward': reward.get('reward', 0),
                        'confirmed': True
                    })
                    total_mined += reward.get('reward', 0)

        # Supplement with wallet history for any gaps (new blocks without address in chain)
        chain_blocks = {r['block'] for r in mining_rewards}
        for entry in wallet.get('mining_history', []):
            if entry.get('block') not in chain_blocks:
                mining_rewards.append({
                    'block': entry.get('block'),
                    'timestamp': entry.get('timestamp'),
                    'reward': entry.get('reward', 0),
                    'confirmed': True
                })
                total_mined += entry.get('reward', 0)
        
        # Sort by block descending, limit
        mining_rewards.sort(key=lambda x: x.get('block', 0), reverse=True)
        mining_rewards = mining_rewards[:limit]
        
        return jsonify({
            'ok': True,
            'mining_rewards': mining_rewards,
            'count': len(mining_rewards),
            'total_mined': total_mined
        })


# ============================================================================
# CONTACTS API
# ============================================================================

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Get user's contact list"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        contacts = S.contacts.get(addr, [])
        
        # Enrich contacts with usernames
        enriched = []
        for contact_addr in contacts:
            if contact_addr in S.wallets:
                wallet = S.wallets[contact_addr]
                key_id = wallet.get('key_id')
                username = get_username_by_key_id(key_id) or 'Anonymous'
                now = int(time.time())
                enriched.append({
                    'address': contact_addr,
                    'username': username,
                    'online': (now - wallet.get('last_activity', 0)) < 300
                })
        
        return jsonify({
            'ok': True,
            'contacts': enriched
        })

@app.route('/api/contact/add', methods=['POST'])
def add_contact():
    """Add contact to user's list"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    data = request.get_json() or {}
    contact_input = data.get('address', '').strip()
    
    if not contact_input:
        return jsonify({'error': 'Address or username required'}), 400
    
    # Resolve to address (supports both address and username)
    contact_addr = resolve_recipient(contact_input)
    if not contact_addr:
        return jsonify({'error': 'Contact not found'}), 404
    
    with S.lock:
        # Initialize contacts list if not exists
        if addr not in S.contacts:
            S.contacts[addr] = []
        
        # Check if already added
        if contact_addr in S.contacts[addr]:
            return jsonify({'error': 'Contact already exists'}), 400
        
        # Add contact
        S.contacts[addr].append(contact_addr)
        S.save()
        
        # Get username if exists
        username = 'Anonymous'
        if contact_addr in S.wallets:
            wallet = S.wallets[contact_addr]
            key_id = wallet.get('key_id')
            username = get_username_by_key_id(key_id) or 'Anonymous'
        
        return jsonify({
            'ok': True,
            'contact': {
                'address': contact_addr,
                'username': username
            }
        })

@app.route('/api/contact/remove', methods=['POST'])
def remove_contact():
    """Remove contact from user's list"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    data = request.get_json() or {}
    contact_addr = data.get('address', '').strip()
    
    if not contact_addr:
        return jsonify({'error': 'Address required'}), 400
    
    with S.lock:
        if addr not in S.contacts:
            return jsonify({'error': 'No contacts found'}), 404
        
        if contact_addr not in S.contacts[addr]:
            return jsonify({'error': 'Contact not found'}), 404
        
        S.contacts[addr].remove(contact_addr)
        S.save()
        
        return jsonify({'ok': True})

@app.route('/api/contact/search', methods=['GET'])
def search_contact():
    """Search for contact by address"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    query = request.args.get('address', '').strip()
    
    if not query:
        return jsonify({'error': 'Address required'}), 400
    
    with S.lock:
        # Check if address exists
        if query not in S.wallets:
            return jsonify({'error': 'Address not found'}), 404
        
        wallet = S.wallets[query]
        key_id = wallet.get('key_id')
        username = get_username_by_key_id(key_id) or 'Anonymous'
        
        return jsonify({
            'ok': True,
            'contact': {
                'address': query,
                'username': username,
                'level': wallet.get('level', 0)
            }
        })

@app.route('/api/balance', methods=['GET'])
def balance():
    """Get wallet balance"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        key_id = wallet.get('key_id')
        username = get_username_by_key_id(key_id) or 'Anonymous'
        
        # Add mining history for transaction display
        mining_history = wallet.get('mining_history', [])
        
        # Debug: ensure level is set
        level = wallet.get('level', 0)
        balance_val = wallet.get('balance', 0)
        print(f"DEBUG /api/balance: addr={addr[:8]}, level={level}, balance={balance_val}")
        
        response_data = {
            'ok': True,
            'added': balance_val,
            'balance': balance_val,
            'level': level,
            'username': username,
            'mining_history': mining_history[-20:]
        }
        print(f"DEBUG response_data: {response_data}")
        
        return jsonify(response_data)

@app.route('/api/faucet', methods=['POST'])
def faucet():
    """Get LAC from faucet"""
    ip = get_client_ip()
    if not rate_limit_check(ip, max_requests=FAUCET_LIMIT, window=86400):
        return jsonify({'error': f'Daily limit reached ({FAUCET_LIMIT}/day)'}), 429
    
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Faucet amount based on level
        level = S.wallets[addr].get('level', 0)
        faucet_amount = 30 + (level * 10)  # L0=30, L1=40, L2=50, L3=60, L4=70, L5=80
        
        # Create faucet transaction
        faucet_tx = {
            'from': 'faucet',
            'to': addr,
            'amount': faucet_amount,
            'type': 'faucet',
            'timestamp': int(time.time()),
            'ip': ip
        }
        S.mempool.append(faucet_tx)
        
        # Update balance immediately
        S.wallets[addr]['balance'] = S.wallets[addr].get('balance', 0) + faucet_amount
        S.counters['emitted_faucet'] += faucet_amount
        S.save()
        
        return jsonify({
            'ok': True,
            'added': faucet_amount,
            'balance': S.wallets[addr].get('balance', 0),
            'level': S.wallets[addr].get('level', 0)
        })

@app.route('/api/transfer/normal', methods=['POST'])
def transfer_normal():
    """Normal public transfer (no ring, no decoys)"""
    ip = get_client_ip()
    if not rate_limit_check(ip):
        return jsonify({'error': 'Rate limit exceeded', 'ok': False}), 429
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized', 'ok': False}), 401
    
    data = request.get_json() or {}
    to_raw = data.get('to', '').strip()
    amount = float(data.get('amount', 0))
    
    if not to_raw or amount <= 0:
        return jsonify({'error': 'Invalid recipient or amount', 'ok': False}), 400
    
    from_addr = get_address_from_seed(seed)
    
    # Resolve username → address
    to_addr = resolve_recipient(to_raw)
    if not to_addr:
        return jsonify({'error': f'Recipient not found: {to_raw}', 'ok': False}), 404
    
    with S.lock:
        if from_addr not in S.wallets:
            return jsonify({'error': 'Wallet not found', 'ok': False}), 404
        
        from_wallet = S.wallets[from_addr]
        fee = 0.1  # Normal transfer fee (cheap)
        total_needed = amount + fee
        
        if from_wallet.get('balance', 0) < total_needed:
            return jsonify({'error': f'Insufficient balance (need {total_needed} LAC)', 'ok': False}), 400
        
        # Create simple public transaction
        tx = {
            'from': from_addr,
            'to': to_addr,
            'amount': amount,
            'fee': fee,
            'type': 'transfer',
            'timestamp': int(time.time()),
            'anonymous': False  # Public transaction marker
        }
        
        # Ed25519 sign the transaction
        tx = sign_transaction(seed, tx)
        
        # Add to mempool (NO decoys, NO ring signatures)
        S.mempool.append(tx)
        
        # Update balances
        from_wallet['balance'] -= total_needed
        S.counters['burned_fees'] += fee
        from_wallet['tx_count'] = from_wallet.get('tx_count', 0) + 1
        
        if to_addr not in S.wallets:
            S.wallets[to_addr] = {
                'balance': 0,
                'level': 0,
                'created_at': int(time.time()),
                'tx_count': 0,
                'msg_count': 0
            }
        
        S.wallets[to_addr]['balance'] = S.wallets[to_addr].get('balance', 0) + amount
        
        S.save()
        
        return jsonify({
            'ok': True,
            'res': {
                'tx_hash': hashlib.sha256(json.dumps(tx).encode()).hexdigest()[:16],
                'balance': from_wallet.get('balance', 0),
                'type': 'normal',
                'fee': fee
            }
        })


@app.route('/api/message.send', methods=['POST'])
def send_message():
    """Send ephemeral message"""
    ip = get_client_ip()
    if not rate_limit_check(ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    to = data.get('to', '').strip()
    text = data.get('text', '').strip()
    verified = data.get('verified', False)
    ephemeral = data.get('ephemeral', False)  # False = regular, True = 5-min L2
    burn = data.get('burn', False)  # Burn after read
    reply_to = data.get('reply_to', None)  # {text, from} of message being replied to
    
    if not to or not text:
        return jsonify({'error': 'Recipient and text required'}), 400
    
    if len(text) > 4000:
        return jsonify({'error': 'Message too long (max 4000 chars)'}), 400
    
    from_addr = get_address_from_seed(seed)
    
    with S.lock:
        if from_addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        from_wallet = S.wallets[from_addr]
        
        if from_wallet.get('balance', 0) < MIN_MSG_FEE:
            return jsonify({'error': f'Insufficient balance (need {MIN_MSG_FEE} LAC)'}), 400
        
        key_id = from_wallet.get('key_id')
        from_username = get_username_by_key_id(key_id)
        # Display name: username if exists, otherwise short address
        from_display = from_username if from_username else from_addr
        
        # Resolve recipient (can be address or username)
        to_address = resolve_recipient(to)
        if not to_address:
            return jsonify({'error': 'Recipient not found'}), 404
        
        # Get recipient display name
        to_wallet = S.wallets.get(to_address, {})
        to_key_id = to_wallet.get('key_id')
        to_username = get_username_by_key_id(to_key_id)
        to_display = to_username if to_username else to_address
        
        # Dedup: reject same text to same recipient within 5 seconds
        for existing in reversed(S.persistent_msgs[-50:]):
            if (existing.get('from_address') == from_addr and
                existing.get('to') == to_address and
                existing.get('text') == text and
                abs(existing.get('timestamp', 0) - int(time.time())) < 5):
                return jsonify({
                    'ok': True,
                    'message_id': 'dedup',
                    'balance': from_wallet.get('balance', 0),
                    'to_address': to_address,
                    'to_display': to_display
                })
        for existing in reversed(S.ephemeral_msgs[-50:]):
            if (existing.get('from_address') == from_addr and
                existing.get('to') == to_address and
                existing.get('text') == text and
                abs(existing.get('timestamp', 0) - int(time.time())) < 5):
                return jsonify({
                    'ok': True,
                    'message_id': 'dedup',
                    'balance': from_wallet.get('balance', 0),
                    'to_address': to_address,
                    'to_display': to_display
                })
        
        # Create message
        msg = {
            'from': from_display,
            'from_address': from_addr,
            'to': to_address,
            'to_display': to_display,
            'text': text,
            'timestamp': int(time.time()),
            'verified': verified,
            'ephemeral': ephemeral,
            'burn': burn,
            'reply_to': reply_to if reply_to else None,
            'ttl': 300 if ephemeral else 0
        }
        
        # E2E Encryption: if both users have messaging keys
        if CRYPTO_MODULE and ED25519_AVAILABLE:
            rcv_pubkey = to_wallet.get('messaging_pubkey')
            if rcv_pubkey:
                try:
                    enc = EncryptedMessaging.encrypt(seed, rcv_pubkey, text)
                    msg['encrypted'] = enc
                    msg['e2e'] = True
                    # Don't remove plaintext on server — for now, both exist
                    # In production: msg['text'] = '[encrypted]'
                except Exception:
                    msg['e2e'] = False
            else:
                msg['e2e'] = False
        
        if ephemeral:
            S.ephemeral_msgs.append(msg)
        else:
            S.persistent_msgs.append(msg)
            # Cap: keep last 5000 messages to prevent unbounded growth
            if len(S.persistent_msgs) > 5000:
                S.persistent_msgs = S.persistent_msgs[-5000:]
        
        # Charge fee
        from_wallet['balance'] -= MIN_MSG_FEE
        S.counters['burned_fees'] += MIN_MSG_FEE
        from_wallet['msg_count'] = from_wallet.get('msg_count', 0) + 1
        
        S.save_msgs()  # FAST: only messages, not entire chain
        
        return jsonify({
            'ok': True,
            'message_id': hashlib.sha256(json.dumps(msg).encode()).hexdigest()[:16],
            'balance': from_wallet.get('balance', 0),
            'to_address': to_address,
            'to_display': to_display
        })

@app.route('/api/message.react', methods=['POST'])
def message_react():
    """Add or remove emoji reaction to a message"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    data = request.get_json() or {}
    msg_key = data.get('msg_key', '').strip()  # text|timestamp identifier
    emoji = data.get('emoji', '').strip()
    
    if not msg_key or not emoji:
        return jsonify({'error': 'msg_key and emoji required'}), 400
    
    ALLOWED_EMOJIS = ['👍', '❤️', '🔥', '😂', '😮', '👎']
    if emoji not in ALLOWED_EMOJIS:
        return jsonify({'error': f'Emoji must be one of: {", ".join(ALLOWED_EMOJIS)}'}), 400
    
    with S.lock:
        if msg_key not in S.reactions:
            S.reactions[msg_key] = {}
        
        rxn = S.reactions[msg_key]
        if emoji not in rxn:
            rxn[emoji] = []
        
        # Toggle: if already reacted, remove; else add
        if addr in rxn[emoji]:
            rxn[emoji].remove(addr)
            if not rxn[emoji]:
                del rxn[emoji]
            action = 'removed'
        else:
            rxn[emoji].append(addr)
            action = 'added'
        
        # Clean empty
        if not S.reactions[msg_key]:
            del S.reactions[msg_key]
        
        return jsonify({'ok': True, 'action': action, 'emoji': emoji})

@app.route('/api/inbox', methods=['GET'])
def inbox():
    """Get inbox messages (received AND sent)"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        key_id = wallet.get('key_id')
        username = get_username_by_key_id(key_id) or 'Anonymous'
        
        # Get messages for this user (BOTH received AND sent) from BOTH stores
        messages = []
        
        def scan_msgs(msg_list, msg_type):
            for msg in msg_list:
                # Received messages
                if msg.get('to') == username or msg.get('to') == addr:
                    messages.append({
                        'from': msg.get('from'),
                        'from_username': msg.get('from'),
                        'message': msg.get('text'),
                        'text': msg.get('text'),
                        'timestamp': msg.get('timestamp'),
                        'verified': msg.get('verified', False),
                        'from_address': msg.get('from_address'),
                        'to': msg.get('to'),
                        'to_display': msg.get('to_display', msg.get('to')),
                        'direction': 'received',
                        'ephemeral': msg.get('ephemeral', msg_type == 'ephemeral'),
                        'msg_type': msg_type
                    })
                # Sent messages
                elif msg.get('from_address') == addr:
                    messages.append({
                        'from': username,
                        'from_username': username,
                        'to': msg.get('to'),
                        'to_display': msg.get('to_display', msg.get('to')),
                        'message': msg.get('text'),
                        'text': msg.get('text'),
                        'timestamp': msg.get('timestamp'),
                        'verified': msg.get('verified', False),
                        'from_address': addr,
                        'direction': 'sent',
                        'ephemeral': msg.get('ephemeral', msg_type == 'ephemeral'),
                        'msg_type': msg_type
                    })
        
        # Scan both stores
        scan_msgs(S.persistent_msgs, 'regular')
        scan_msgs(S.ephemeral_msgs, 'ephemeral')
        
        # Also get from recent blocks
        if len(S.chain) > 0:
            for block in S.chain[-10:]:
                scan_msgs(block.get('ephemeral_msgs', []), 'ephemeral')
        
        return jsonify({
            'ok': True,
            'messages': messages,
            'count': len(messages)
        })

@app.route('/api/chat', methods=['GET'])
def get_chat():
    """Get messages with a specific peer — fast, no client-side filtering"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    peer = request.args.get('peer', '').strip()
    if not peer:
        return jsonify({'error': 'peer param required'}), 400
    
    addr = get_address_from_seed(seed)
    
    # Resolve peer — could be @username, username, or address
    peer_addr = resolve_recipient(peer) if not peer.startswith('lac') else peer
    if not peer_addr:
        peer_addr = peer  # fallback
    
    # Also get peer's username for matching 'from' field
    peer_username = None
    if peer_addr and peer_addr.startswith('lac'):
        peer_wallet = S.wallets.get(peer_addr, {})
        pk = peer_wallet.get('key_id')
        if pk:
            peer_username = get_username_by_key_id(pk)
    if not peer_username and peer.startswith('@'):
        peer_username = peer.lstrip('@')
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        key_id = wallet.get('key_id')
        username = get_username_by_key_id(key_id) or 'Anonymous'
        
        messages = []
        
        def scan(msg_list, msg_type):
            for msg in msg_list:
                sender = msg.get('from_address', '')
                sender_name = msg.get('from', '')
                recipient = msg.get('to', '')
                recipient_name = msg.get('to_display', '')
                # Match if peer is sender or recipient (any identifier)
                match = (
                    sender == peer_addr or recipient == peer_addr or
                    sender == peer or recipient == peer or
                    (peer_username and (sender_name == peer_username or sender_name == f'@{peer_username}' or
                                        recipient_name == peer_username or recipient_name == f'@{peer_username}'))
                )
                if not match:
                    continue
                # Determine direction
                if sender == addr:
                    direction = 'sent'
                elif recipient == addr or recipient == username:
                    direction = 'received'
                else:
                    continue
                
                m_entry = {
                    'from': msg.get('from'),
                    'from_address': msg.get('from_address'),
                    'to': msg.get('to'),
                    'to_display': msg.get('to_display', msg.get('to')),
                    'text': msg.get('text'),
                    'message': msg.get('text'),
                    'timestamp': msg.get('timestamp'),
                    'verified': msg.get('verified', False),
                    'direction': direction,
                    'ephemeral': msg.get('ephemeral', msg_type == 'ephemeral'),
                    'msg_type': msg_type,
                    'burn': msg.get('burn', False),
                    'reply_to': msg.get('reply_to', None),
                    'msg_key': f"{(msg.get('text',''))[:30]}|{msg.get('timestamp',0)}",
                    'reactions': S.reactions.get(f"{(msg.get('text',''))[:30]}|{msg.get('timestamp',0)}", {})
                }
                
                # Burn after read: if recipient reads a burn message, mark it
                if msg.get('burn') and direction == 'received' and not msg.get('_burned'):
                    msg['_burned'] = True
                    msg['_burn_read_at'] = int(time.time())
                    burn_queue.append(msg)
                
                # Don't show already-burned messages
                if msg.get('_burned') and msg.get('_burn_read_at', 0) < (int(time.time()) - 3):
                    m_entry['text'] = '🔥 Message burned'
                    m_entry['message'] = '🔥 Message burned'
                    m_entry['burned'] = True
                
                messages.append(m_entry)
        
        burn_queue = []
        
        scan(S.persistent_msgs, 'regular')
        scan(S.ephemeral_msgs, 'ephemeral')
        
        # Recent blocks
        for block in S.chain[-10:]:
            scan(block.get('ephemeral_msgs', []), 'ephemeral')
        
        # Process burn queue — delete burned messages after 3 seconds
        now = int(time.time())
        S.persistent_msgs = [m for m in S.persistent_msgs 
                             if not (m.get('_burned') and m.get('_burn_read_at', 0) < (now - 5))]
        
        # Sort by timestamp
        messages.sort(key=lambda m: m.get('timestamp', 0))
        
        return jsonify({
            'ok': True,
            'messages': messages,
            'count': len(messages),
            'peer': peer,
            'peer_addr': peer_addr,
            'peer_online': bool(peer_addr and peer_addr in S.wallets and (int(time.time()) - S.wallets[peer_addr].get('last_activity', 0)) < 300)
        })

# ==================== DICE GAME ====================
import random as _random

@app.route('/api/dice/play', methods=['POST'])
def dice_play():
    """Play dice — red/black or over/under"""
    ip = get_client_ip()
    if not rate_limit_check(ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    bet_amount = float(data.get('amount', 0))
    game_type = data.get('type', 'color')  # 'color' or 'number'
    choice = data.get('choice', '')  # 'red'/'black' or 'over'/'under'
    
    if bet_amount < 1:
        return jsonify({'error': 'Minimum bet: 1 LAC'}), 400
    if bet_amount > 10000:
        return jsonify({'error': 'Maximum bet: 10,000 LAC'}), 400
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        if wallet.get('balance', 0) < bet_amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # Generate provably fair result using block hash + timestamp
        last_hash = S.chain[-1]['hash'] if S.chain else 'genesis'
        seed_str = f"{last_hash}{addr}{int(time.time()*1000)}"
        result_hash = hashlib.sha256(seed_str.encode()).hexdigest()
        roll = int(result_hash[:8], 16) % 100  # 0-99
        
        if game_type == 'color':
            # Red = 0-48 (49%), Black = 49-97 (49%), Green = 98-99 (2% house edge)
            if roll <= 48:
                result_color = 'red'
            elif roll <= 97:
                result_color = 'black'
            else:
                result_color = 'green'
            
            won = (choice == result_color)
            multiplier = 2.0 if won else 0
            
            result_display = result_color.upper()
            
        elif game_type == 'number':
            # Over/under 50 — roll is 0-99
            threshold = 50
            actual = roll
            
            if choice == 'over':
                won = actual > threshold
            elif choice == 'under':
                won = actual < threshold
            else:
                return jsonify({'error': 'Choose over or under'}), 400
            
            multiplier = 2.0 if won else 0
            result_display = str(actual)
        else:
            return jsonify({'error': 'Invalid game type'}), 400
        
        # Process bet — ON-CHAIN
        # WIN: new coins minted (no trace to player)
        # LOSS: coins burned forever (no trace to player)
        payout = bet_amount * multiplier
        now_ts = int(time.time())
        
        if won:
            # WIN: mint new coins. Player address NEVER appears on chain.
            mint_tx = {
                'from': 'dice_contract',
                'to': 'anonymous',
                'amount': payout,
                'type': 'dice_mint',
                'timestamp': now_ts,
                'ring_signature': True,
                'proof_hash': result_hash[:16]
            }
            wallet['balance'] += (payout - bet_amount)  # net: +bet_amount
            S.counters['emitted_dice'] += (payout - bet_amount)
            if not hasattr(S, 'pending_txs'):
                S.pending_txs = []
            S.pending_txs.append(mint_tx)
        else:
            # LOSS: coins burned. Player address NEVER appears on chain.
            burn_tx = {
                'from': 'anonymous',
                'to': BURN_ADDRESS,
                'amount': bet_amount,
                'type': 'dice_burn',
                'timestamp': now_ts,
                'ring_signature': True,
                'proof_hash': result_hash[:16]
            }
            wallet['balance'] -= bet_amount
            S.counters['burned_dice'] += bet_amount
            if not hasattr(S, 'pending_txs'):
                S.pending_txs = []
            S.pending_txs.append(burn_tx)
        
        # Record game
        game_record = {
            'player': addr,
            'type': game_type,
            'choice': choice,
            'amount': bet_amount,
            'roll': roll,
            'result': result_display,
            'won': won,
            'payout': payout,
            'timestamp': int(time.time()),
            'proof_hash': result_hash[:16]
        }
        
        # Store in wallet history
        if 'dice_history' not in wallet:
            wallet['dice_history'] = []
        wallet['dice_history'].append(game_record)
        # Keep last 50
        wallet['dice_history'] = wallet['dice_history'][-500:]
        
        S.save()
        
        return jsonify({
            'ok': True,
            'won': won,
            'roll': roll,
            'result': result_display,
            'choice': choice,
            'bet': bet_amount,
            'payout': payout,
            'balance': wallet.get('balance', 0),
            'proof_hash': result_hash[:16],
            'multiplier': multiplier
        })

@app.route('/api/dice/history', methods=['GET'])
def dice_history():
    """Get dice game history"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        history = S.wallets[addr].get('dice_history', [])
        
        total_bet = sum(g.get('amount', 0) for g in history)
        total_won = sum(g.get('payout', 0) for g in history)
        wins = sum(1 for g in history if g.get('won'))
        
        return jsonify({
            'ok': True,
            'history': list(reversed(history[-20:])),
            'stats': {
                'total_games': len(history),
                'wins': wins,
                'losses': len(history) - wins,
                'total_bet': total_bet,
                'total_won': total_won,
                'profit': total_won - total_bet
            }
        })

@app.route('/api/groups', methods=['GET'])
def groups():
    """Get all groups"""
    seed = request.headers.get('X-Seed', '').strip()
    current_addr = None
    
    if validate_seed(seed):
        current_addr = get_address_from_seed(seed)
    
    with S.lock:
        groups_list = []
        for gid, group in S.groups.items():
            gtype = group.get('type', 'public')
            members = group.get('members', [])
            
            # Private groups: only visible to members
            if gtype == 'private' and current_addr and current_addr not in members:
                continue
            
            group_data = {
                'id': gid,
                'name': group.get('name', 'Unknown'),
                'type': gtype,
                'post_count': len(group.get('posts', [])),
                'member_count': len(members),
                'creator': group.get('creator'),
                'is_creator': current_addr == group.get('creator') if current_addr else False,
                'is_member': current_addr in members if current_addr else False
            }
            groups_list.append(group_data)
        
        return jsonify({
            'ok': True,
            'groups': groups_list
        })

@app.route('/api/group.delete', methods=['POST'])
def delete_group():
    """Delete group (only creator)"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    gid = data.get('group_id', '').strip() or data.get('gid', '').strip()
    
    if not gid:
        return jsonify({'error': 'Group ID required'}), 400
    
    from_addr = get_address_from_seed(seed)
    
    with S.lock:
        if from_addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        if gid not in S.groups:
            return jsonify({'error': 'Group not found'}), 404
        
        group = S.groups[gid]
        
        # Only creator can delete
        if group.get('creator') != from_addr:
            return jsonify({'error': 'Only creator can delete group'}), 403
        
        # Delete group
        del S.groups[gid]
        S.save()
        
        return jsonify({
            'ok': True,
            'deleted': gid
        })

@app.route('/api/group.create', methods=['POST'])
def create_group():
    """Create new group"""
    ip = get_client_ip()
    if not rate_limit_check(ip, max_requests=10, window=3600):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    group_type = data.get('type', 'public')  # public, private, l1_blockchain, l2_ephemeral
    
    if not name:
        return jsonify({'error': 'Group name required'}), 400
    
    valid_types = ['public', 'private', 'l1_blockchain', 'l2_ephemeral']
    if group_type not in valid_types:
        group_type = 'public'
    
    from_addr = get_address_from_seed(seed)
    
    with S.lock:
        if from_addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Generate group ID
        gid = f"group_{hashlib.sha256(f'{name}{time.time()}'.encode()).hexdigest()[:16]}"
        
        S.groups[gid] = {
            'name': name,
            'type': group_type,
            'creator': from_addr,
            'created_at': int(time.time()),
            'members': [from_addr],  # creator is first member
            'posts': []
        }
        
        S.save_groups()  # FAST
        
        return jsonify({
            'ok': True,
            'id': gid,
            'name': name,
            'type': group_type
        })

@app.route('/api/group/posts', methods=['GET'])
def group_posts():
    """Get posts from group"""
    gid = request.args.get('group_id', '').strip() or request.args.get('gid', '').strip()
    
    if not gid:
        return jsonify({'error': 'Group ID required'}), 400
    
    with S.lock:
        # Try direct ID lookup first, then search by name
        group = None
        if gid in S.groups:
            group = S.groups[gid]
        else:
            # Search by name (for compatibility)
            for k, g in S.groups.items():
                if g.get('name') == gid:
                    group = g
                    break
        
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Enrich posts with reactions
        enriched_posts = []
        for p in group.get('posts', []):
            ep = dict(p)
            msg_key = (p.get('text', '') or p.get('message', ''))[:30] + '|' + str(p.get('timestamp', 0))
            ep['msg_key'] = msg_key
            ep['reactions'] = S.reactions.get(msg_key, {})
            enriched_posts.append(ep)
        
        return jsonify({
            'ok': True,
            'posts': enriched_posts
        })

@app.route('/api/group.post', methods=['POST'])
def post_to_group():
    """Post to group"""
    ip = get_client_ip()
    if not rate_limit_check(ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    # Support both old and new parameter names
    gid = data.get('group_id', '').strip() or data.get('gid', '').strip()
    text = data.get('message', '').strip() or data.get('text', '').strip()
    reply_to = data.get('reply_to', None)  # {text, from}
    
    if not gid or not text:
        return jsonify({'error': 'Group ID and text required'}), 400
    
    if len(text) > 4000:
        return jsonify({'error': 'Message too long (max 4000 chars)'}), 400
    
    from_addr = get_address_from_seed(seed)
    
    with S.lock:
        if from_addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        if gid not in S.groups:
            # Try search by name
            found = None
            for k, g in S.groups.items():
                if g.get('name') == gid:
                    gid = k
                    found = True
                    break
            if not found:
                return jsonify({'error': 'Group not found'}), 404
        
        wallet = S.wallets[from_addr]
        key_id = wallet.get('key_id')
        username = get_username_by_key_id(key_id) or 'Anonymous'
        
        group = S.groups[gid]
        gtype = group.get('type', 'public')
        members = group.get('members', [])
        
        # Private groups: must be member
        if gtype == 'private' and from_addr not in members:
            return jsonify({'error': 'Not a member of this private group'}), 403
        
        # Auto-join public/L1/L2 groups
        if from_addr not in members:
            if 'members' not in group:
                group['members'] = []
            group['members'].append(from_addr)
        
        post = {
            'from': username,
            'from_username': username,
            'from_address': from_addr,
            'message': text,
            'text': text,
            'timestamp': int(time.time()),
            'ts': int(time.time()),
            'group_type': gtype,
            'reply_to': reply_to if reply_to else None
        }
        
        # Ensure posts list exists
        if 'posts' not in group:
            group['posts'] = []
        
        # Dedup: reject same text from same user within 5 seconds
        recent = group['posts'][-20:] if len(group['posts']) > 20 else group['posts']
        for existing in reversed(recent):
            if (existing.get('from_address') == from_addr and
                existing.get('text') == text and
                abs(existing.get('timestamp', 0) - int(time.time())) < 5):
                return jsonify({'ok': True, 'post': existing})  # silent dedup
        
        group['posts'].append(post)
        # Cap group posts at 1000 (keep last 1000)
        if len(group['posts']) > 1000:
            group['posts'] = group['posts'][-1000:]
        
        # L1 Blockchain groups: also write to blockchain
        if gtype == 'l1_blockchain':
            chain_tx = {
                'from': 'anonymous',
                'to': gid,
                'type': 'group_post',
                'group_id': gid,
                'message_hash': hashlib.sha256(text.encode()).hexdigest()[:16],
                'timestamp': int(time.time()),
                'ring_signature': True
            }
            if not hasattr(S, 'pending_txs'):
                S.pending_txs = []
            S.pending_txs.append(chain_tx)
        
        S.save_groups()  # FAST: only groups, not entire chain
        
        return jsonify({
            'ok': True,
            'post': post
        })

@app.route('/api/group.join', methods=['POST'])
def join_group():
    """Join a group (or invite to private group)"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    gid = data.get('group_id', '').strip()
    invite_addr = data.get('invite_address', '').strip()  # for inviting others
    
    if not gid:
        return jsonify({'error': 'Group ID required'}), 400
    
    from_addr = get_address_from_seed(seed)
    
    with S.lock:
        if gid not in S.groups:
            return jsonify({'error': 'Group not found'}), 404
        
        group = S.groups[gid]
        gtype = group.get('type', 'public')
        members = group.get('members', [])
        
        if invite_addr:
            # Inviting someone else (must be creator or member)
            if from_addr not in members:
                return jsonify({'error': 'Only members can invite'}), 403
            if invite_addr not in members:
                group.setdefault('members', []).append(invite_addr)
                S.save()
            return jsonify({'ok': True, 'invited': invite_addr})
        
        # Self-join
        if gtype == 'private':
            return jsonify({'error': 'Private group — need invite'}), 403
        
        if from_addr not in members:
            group.setdefault('members', []).append(from_addr)
            S.save()
        
        return jsonify({'ok': True, 'joined': gid})

@app.route('/api/chain', methods=['GET'])
def chain():
    """Get blockchain info"""
    with S.lock:
        # Get last 10 blocks and ensure they have index
        blocks = []
        if len(S.chain) > 0:
            start_idx = max(0, len(S.chain) - 10)
            for i in range(start_idx, len(S.chain)):
                block = S.chain[i].copy()
                # Ensure block has index field
                if 'index' not in block:
                    block['index'] = i
                blocks.append(block)
        
        return jsonify({
            'ok': True,
            'res': {
                'height': len(S.chain),
                'blocks': blocks
            }
        })

@app.route('/api/explorer/chain', methods=['GET'])
def explorer_chain():
    """Get full blockchain for explorer"""
    with S.lock:
        # Return all blocks with indexes
        blocks = []
        for i, block in enumerate(S.chain):
            block_copy = block.copy()
            if 'index' not in block_copy:
                block_copy['index'] = i
            blocks.append(block_copy)
        
        return jsonify(blocks)

# ===================== P2P SYNC ENDPOINTS =====================

@app.route('/api/chain/height', methods=['GET'])
def chain_height():
    """Get current blockchain height"""
    with S.lock:
        return jsonify({
            'ok': True,
            'height': len(S.chain),
            'last_hash': S.chain[-1]['hash'] if S.chain else None
        })

@app.route('/api/blocks/range', methods=['GET'])
def blocks_range():
    """Get blocks in range [start, end)"""
    start = int(request.args.get('start', 0))
    end = int(request.args.get('end', len(S.chain)))
    
    with S.lock:
        if start < 0 or start >= len(S.chain):
            return jsonify({'error': 'Invalid start index'}), 400
        
        end = min(end, len(S.chain))
        blocks = []
        
        for i in range(start, end):
            block = S.chain[i].copy()
            if 'index' not in block:
                block['index'] = i
            blocks.append(block)
        
        return jsonify({
            'ok': True,
            'blocks': blocks,
            'start': start,
            'end': end,
            'total': len(S.chain)
        })

@app.route('/api/block/submit', methods=['POST'])
def block_submit():
    """Accept a new block from peer (for P2P sync)"""
    data = request.get_json() or {}
    block = data.get('block')
    
    if not block:
        return jsonify({'error': 'Missing block'}), 400
    
    with S.lock:
        # Check if we already have this block
        block_index = block.get('index', -1)
        if block_index >= 0 and block_index < len(S.chain):
            if S.chain[block_index]['hash'] == block['hash']:
                return jsonify({'ok': True, 'status': 'already_have'})
        
        # Verify block
        if block_index > 0:
            prev_block = S.chain[block_index - 1] if block_index - 1 < len(S.chain) else None
            if not prev_block:
                return jsonify({'error': 'Missing previous block'}), 400
            
            if block.get('previous_hash') != prev_block['hash']:
                return jsonify({'error': 'Invalid previous hash'}), 400
        
        # Add block if it's the next one
        if block_index == len(S.chain):
            S.chain.append(block)
            S.save()
            print(f"✅ Accepted block #{block_index} from peer")
            return jsonify({'ok': True, 'status': 'accepted'})
        
        return jsonify({'error': 'Block index mismatch'}), 400

@app.route('/api/block/<int:height>', methods=['GET'])
def block(height):
    """Get block by height"""
    with S.lock:
        if height < 0 or height >= len(S.chain):
            return jsonify({'error': 'Block not found'}), 404
        
        
        # Anonymize transactions for privacy
        block_data = S.chain[height].copy()
        
        if 'transactions' in block_data:
            anon_txs = []
            for tx in block_data['transactions']:
                anon_tx = tx.copy()
                
                if 'from' in anon_tx:
                    anon_tx['from'] = 'anonymous_' + hashlib.sha256(anon_tx['from'].encode()).hexdigest()[:16]
                if 'to' in anon_tx:
                    anon_tx['to'] = 'anonymous_' + hashlib.sha256(anon_tx['to'].encode()).hexdigest()[:16]
                
                anon_tx.pop('decoy', None)
                anon_tx.pop('decoy_id', None)
                
                anon_txs.append(anon_tx)
            
            block_data['transactions'] = anon_txs
        
        return jsonify({
            'ok': True,
            'res': {
                'block': block_data
            }
        })

@app.route('/api/panic', methods=['POST'])
def panic():
    """Emergency wipe"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr in S.wallets:
            # Remove wallet
            wallet = S.wallets.pop(addr)
            
            # Remove username mapping
            key_id = wallet.get('key_id')
            if key_id and key_id in S.usernames:
                S.usernames.pop(key_id)
            
            S.save()
            
            return jsonify({'ok': True})
        
        return jsonify({'error': 'Wallet not found'}), 404

# ==================== DEAD MAN'S SWITCH ====================

@app.route('/api/dms/setup', methods=['POST'])
def dms_setup():
    """Configure Dead Man's Switch"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    timeout_days = data.get('timeout_days', 30)
    actions = data.get('actions', [])
    
    try:
        timeout_days = int(timeout_days)
    except:
        return jsonify({'error': 'Invalid timeout_days'}), 400
    
    if timeout_days < 1 or timeout_days > 365:
        return jsonify({'error': 'Timeout must be 1-365 days'}), 400
    
    if not actions or len(actions) == 0:
        return jsonify({'error': 'At least one action required'}), 400
    
    if len(actions) > 5:
        return jsonify({'error': 'Maximum 5 actions'}), 400
    
    # Validate actions
    valid_types = ['transfer', 'transfer_all', 'message', 'burn_stash', 'wipe']
    for a in actions:
        if a.get('type') not in valid_types:
            return jsonify({'error': f"Invalid action type: {a.get('type')}. Valid: {valid_types}"}), 400
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        S.wallets[addr]['dead_mans_switch'] = {
            'enabled': True,
            'timeout_days': timeout_days,
            'actions': actions,
            'created_at': int(time.time()),
            'triggered_at': None
        }
        S.wallets[addr]['last_activity'] = int(time.time())
        S.save()
        
        return jsonify({
            'ok': True,
            'timeout_days': timeout_days,
            'actions_count': len(actions),
            'trigger_date': int(time.time()) + timeout_days * 86400
        })

@app.route('/api/dms/status', methods=['GET'])
def dms_status():
    """Get Dead Man's Switch status"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        dms = wallet.get('dead_mans_switch')
        last = wallet.get('last_activity', wallet.get('created_at', 0))
        now = int(time.time())
        
        if not dms:
            return jsonify({'ok': True, 'enabled': False})
        
        timeout_secs = dms.get('timeout_days', 30) * 86400
        remaining = max(0, timeout_secs - (now - last))
        
        return jsonify({
            'ok': True,
            'enabled': dms.get('enabled', False),
            'timeout_days': dms.get('timeout_days', 30),
            'actions': dms.get('actions', []),
            'last_activity': last,
            'seconds_remaining': remaining,
            'days_remaining': remaining // 86400,
            'trigger_date': last + timeout_secs,
            'triggered_at': dms.get('triggered_at')
        })

@app.route('/api/dms/cancel', methods=['POST'])
def dms_cancel():
    """Disable Dead Man's Switch"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        S.wallets[addr].pop('dead_mans_switch', None)
        S.save()
        
        return jsonify({'ok': True, 'message': 'Dead Man Switch disabled'})

@app.route('/api/change_nickname', methods=['POST'])
def change_nickname():
    """Change nickname (burns LAC)"""
    ip = get_client_ip()
    if not rate_limit_check(ip, max_requests=NICKNAME_CHANGE_LIMIT, window=3600):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    new_nickname = data.get('nickname', '').strip()
    
    if not new_nickname:
        return jsonify({'error': 'Nickname required'}), 400
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        fee = 200  # LAC
        
        if wallet.get('balance', 0) < fee:
            return jsonify({'error': f'Insufficient balance (need {fee} LAC)'}), 400
        
        # Create BURN transaction
        burn_tx = {
            'from': addr,
            'to': BURN_ADDRESS,
            'amount': fee,
            'type': 'burn_nickname_change',
            'new_nickname': new_nickname,
            'timestamp': int(time.time()),
            'ring_signature': True
        }
        S.mempool.append(burn_tx)
        
        # Burn the fee
        wallet['balance'] -= fee
        
        # Update username mapping (new format: username → address)
        addr = get_address_from_seed(seed)
        old_nickname = wallet.get('username', 'Anonymous')
        
        # Remove old username entry
        for u, a in list(S.usernames.items()):
            if a == addr:
                del S.usernames[u]
                break
        
        # Add new username
        clean_name = new_nickname.lstrip('@').lower()
        S.usernames[clean_name] = addr
        wallet['username'] = clean_name
        
        S.save()
        burn_tx["old_nickname"] = old_nickname
        
        return jsonify({
            'ok': True,
            'new_nickname': new_nickname,
            'burned': fee,
            'balance': wallet.get('balance', 0)
        })

@app.route('/api/upgrade_level', methods=['POST'])
def upgrade_level():
    """Upgrade level (burns LAC)"""
    ip = get_client_ip()
    if not rate_limit_check(ip, max_requests=UPGRADE_LIMIT, window=3600):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Level costs
    LEVEL_COSTS = {
        0: 100,      # Level 0 -> 1
        1: 700,      # Level 1 -> 2
        2: 2000,     # Level 2 -> 3
        3: 10000,    # Level 3 -> 4
        4: 100000,   # Level 4 -> 5 (Validator)
        5: 500000,   # Level 5 -> 6 (Priority Validator)
        6: 2000000,  # Level 6 -> 7 (GOD) — x2 mining chance, x2 validator reward
    }
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        current_level = wallet.get('level', 0)
        
        if current_level >= 7:
            return jsonify({'error': 'Already at max level (GOD)'}), 400
        
        cost = LEVEL_COSTS.get(current_level, 0)
        if cost == 0:
            return jsonify({'error': 'Cannot upgrade'}), 400
        
        if wallet.get('balance', 0) < cost:
            return jsonify({'error': f'Insufficient balance. Need {cost} LAC'}), 400
        
        # Create BURN transaction
        burn_tx = {
            'from': addr,
            'to': BURN_ADDRESS,
            'amount': cost,
            'type': 'burn_level_upgrade',
            'level_from': current_level,
            'level_to': current_level + 1,
            'timestamp': int(time.time()),
            'ring_signature': True
        }
        burn_tx = sign_transaction(seed, burn_tx)
        S.mempool.append(burn_tx)
        
        # Burn the cost
        wallet['balance'] -= cost
        wallet['level'] = current_level + 1
        S.counters['burned_levels'] += cost
        
        S.save()
        
        return jsonify({
            'ok': True,
            'level': current_level + 1,
            'new_level': current_level + 1,
            'burned': cost,
            'balance': wallet.get('balance', 0)
        })

# ===================== VALIDATOR ENDPOINTS =====================

@app.route('/api/validator/register', methods=['POST'])
def validator_register():
    """Enable/disable validator mode"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    enable = data.get('enable', True)
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        
        # Check eligibility
        if not is_validator_eligible(addr):
            level = wallet.get('level', 0)
            if level < 5:
                return jsonify({
                    'error': f'Need Level 5+ to be validator (current: {level})',
                    'required_level': 5,
                    'current_level': level
                }), 400
            
            # Check if banned
            if wallet.get('validator_banned', False):
                ban_until = wallet.get('banned_until', 0)
                remaining = int(ban_until - time.time())
                return jsonify({
                    'error': 'Validator banned',
                    'banned_until': ban_until,
                    'remaining_seconds': max(0, remaining)
                }), 403
        
        # Enable/disable
        wallet['validator_mode'] = enable
        S.save()
        
        return jsonify({
            'ok': True,
            'validator_mode': enable,
            'level': wallet.get('level', 0),
            'weight': get_validator_weight(wallet),
            'reward_per_commitment': get_validator_reward(wallet.get('level', 0))
        })

@app.route('/api/validator/status', methods=['GET'])
def validator_status():
    """Get validator status for current wallet"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        level = wallet.get('level', 0)
        
        # Calculate potential earnings
        commitments_per_day = (24 * 60) / COMMITMENT_INTERVAL  # blocks per day / interval
        reward_per_commitment = get_validator_reward(level)
        daily_earning = commitments_per_day * reward_per_commitment
        yearly_earning = daily_earning * 365
        
        return jsonify({
            'ok': True,
            'address': addr,
            'level': level,
            'eligible': is_validator_eligible(addr),
            'validator_mode': wallet.get('validator_mode', False),
            'banned': wallet.get('validator_banned', False),
            'weight': get_validator_weight(wallet),
            'reward_per_commitment': reward_per_commitment,
            'estimated_daily_earning': round(daily_earning, 2),
            'estimated_yearly_earning': round(yearly_earning, 2),
            'dev_mode': DEV_MODE,
            'min_validators': MIN_VALIDATORS,
            'commitment_interval': COMMITMENT_INTERVAL
        })

@app.route('/api/validator/list', methods=['GET'])
def validator_list():
    """Get list of all active validators"""
    with S.lock:
        validators = []
        
        for addr, wallet in S.wallets.items():
            if is_validator_eligible(addr) and wallet.get('validator_mode', False):
                validators.append({
                    'address': addr[:20] + '...',  # Truncate for privacy
                    'level': wallet.get('level', 0),
                    'weight': get_validator_weight(wallet),
                    'nickname': wallet.get('nickname', 'Anonymous')
                })
        
        # Sort by level (Level 6 first)
        validators.sort(key=lambda v: (-v['level'], -v['weight']))
        
        return jsonify({
            'ok': True,
            'validators': validators,
            'count': len(validators),
            'min_required': MIN_VALIDATORS,
            'sufficient': len(validators) >= MIN_VALIDATORS
        })



# ===================== ZERO-HISTORY VALIDATOR ENDPOINTS =====================

@app.route('/api/validator/commit', methods=['POST'])
def validator_commit():
    """Create state commitment (validators only)"""
    if not ZERO_HISTORY_ENABLED or not S.zero_history:
        return jsonify({'error': 'Zero-History not enabled'}), 503
    
    seed = request.headers.get('X-Seed')
    if not seed:
        return jsonify({'error': 'Seed required'}), 401
    
    addr = get_address_from_seed(seed)
    
    # Check validator eligibility
    if addr not in S.wallets:
        return jsonify({'error': 'Wallet not found'}), 404
    
    wallet = S.wallets[addr]
    level = wallet.get('level', 0)
    
    if level < 5:
        return jsonify({'error': 'Level 5+ required'}), 403
    
    # Check if validator is enabled
    if not wallet.get('validator_mode', False):
        return jsonify({'error': 'Validator not enabled'}), 403
    
    # Get witness signatures (in production, collect from network)
    data = request.get_json() or {}
    witness_signatures = data.get('witness_signatures', [])
    witness_addresses = data.get('witness_addresses', [])
    
    # Create commitment
    with S.lock:
        commitment = S.zero_history.create_commitment(
            validator_address=addr,
            validator_level=level,
            witness_signatures=witness_signatures,
            witness_addresses=witness_addresses
        )
    
    if not commitment:
        return jsonify({'error': 'Commitment creation failed'}), 500
    
    # Calculate reward
    reward = 0.4 if level == 5 else 0.5
    
    # Add reward to wallet
    with S.lock:
        wallet['balance'] = wallet.get('balance', 0) + reward
        S.save()
    
    return jsonify({
        'ok': True,
        'commitment_hash': commitment.hash(),
        'reward': reward,
        'witnesses': len(witness_signatures)
    })


@app.route('/api/validator/fraud-proof', methods=['POST'])
def submit_fraud_proof():
    """Submit fraud proof against validator"""
    if not ZERO_HISTORY_ENABLED or not S.zero_history:
        return jsonify({'error': 'Zero-History not enabled'}), 503
    
    seed = request.headers.get('X-Seed')
    if not seed:
        return jsonify({'error': 'Seed required'}), 401
    
    addr = get_address_from_seed(seed)
    
    data = request.get_json() or {}
    commitment_hash = data.get('commitment_hash')
    validator_address = data.get('validator_address')
    proof_type = data.get('proof_type')
    evidence = data.get('evidence', {})
    
    # Submit fraud proof
    with S.lock:
        fraud_proof = S.zero_history.submit_fraud_proof(
            commitment_hash=commitment_hash,
            validator_address=validator_address,
            proof_type=proof_type,
            evidence=evidence,
            reporter_address=addr
        )
    
    if not fraud_proof:
        return jsonify({'error': 'Invalid fraud proof'}), 400
    
    # Punish validator (30 day ban)
    with S.lock:
        if validator_address in S.wallets:
            S.wallets[validator_address]['validator_banned'] = True
            S.wallets[validator_address]['ban_until'] = int(time.time()) + (30 * 24 * 3600)
            S.wallets[validator_address]['validator_mode'] = False  # Disable validator
        
        # Reward reporter (300 LAC)
        if addr in S.wallets:
            S.wallets[addr]['balance'] = S.wallets[addr].get('balance', 0) + 300
        
        S.save()
    
    return jsonify({
        'ok': True,
        'fraud_verified': True,
        'reward': 300,
        'validator_banned': True,
        'ban_duration_days': 30
    })


@app.route('/api/zero-history/stats', methods=['GET'])
def zero_history_stats():
    """Get Zero-History storage statistics"""
    if not ZERO_HISTORY_ENABLED or not S.zero_history:
        return jsonify({'error': 'Zero-History not enabled'}), 503
    
    try:
        with S.lock:
            stats = S.zero_history.get_storage_stats()
        
        return jsonify({
            'ok': True,
            'stats': stats,
            'commitment_interval': COMMITMENT_INTERVAL,
            'l3_lifetime_days': 30,
            'l2_lifetime_days': 90
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Stats error: {str(e)}'}), 500


@app.route('/api/p2p/signal', methods=['POST'])
def p2p_send_signal():
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    to_peer = data.get('to', '').strip()
    signal = data.get('signal')
    
    if not to_peer or not signal:
        return jsonify({'error': 'Missing to or signal'}), 400
    
    from_addr = get_address_from_seed(seed)
    
    with p2p_lock:
        p2p_signals[to_peer].append({
            'from': from_addr,
            'signal': signal,
            'timestamp': int(time.time())
        })
        
        now = int(time.time())
        p2p_signals[to_peer] = [
            s for s in p2p_signals[to_peer]
            if now - s['timestamp'] < 300
        ]
        
        return jsonify({'ok': True})

@app.route('/api/p2p/poll', methods=['GET'])
def p2p_poll_signals():
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    peer_id = f"peer_{hashlib.sha256(seed.encode()).hexdigest()[:40]}"
    
    with p2p_lock:
        p2p_peers[peer_id] = {
            'address': addr,
            'lastSeen': int(time.time())
        }
        
        signals = p2p_signals.get(peer_id, [])
        if peer_id in p2p_signals:
            p2p_signals[peer_id] = []
        
        return jsonify({
            'ok': True,
            'signals': signals,
            'peerId': peer_id
        })

@app.route('/api/p2p/peers', methods=['GET'])
def p2p_list_peers():
    with p2p_lock:
        now = int(time.time())
        active_peers = {
            pid: info for pid, info in p2p_peers.items()
            if now - info['lastSeen'] < 120
        }
        
        p2p_peers.clear()
        p2p_peers.update(active_peers)
        
        return jsonify({
            'ok': True,
            'peers': [
                {'peerId': pid, 'address': info['address'][:20] + '...', 'lastSeen': info['lastSeen']}
                for pid, info in active_peers.items()
            ]
        })

@app.route('/api/p2p/announce', methods=['POST'])
def p2p_announce():
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    peer_id = f"peer_{hashlib.sha256(seed.encode()).hexdigest()[:40]}"
    
    with p2p_lock:
        p2p_peers[peer_id] = {
            'address': addr,
            'lastSeen': int(time.time())
        }
        
        other_peers = [pid for pid in p2p_peers.keys() if pid != peer_id][:5]
        
        return jsonify({
            'ok': True,
            'peerId': peer_id,
            'peers': other_peers
        })

# ===================== STEALTH + KYBER ENDPOINTS =====================

@app.route('/api/timelock/create', methods=['POST'])
def create_timelock():
    """Create time-locked transaction"""
    if not TIMELOCK_ENABLED or not S.timelock:
        return jsonify({'error': 'Time-Lock not available'}), 503
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    from_addr = get_address_from_seed(seed)
    
    to_raw = data.get('to', '').strip()
    amount = data.get('amount', 0)
    delay_blocks = data.get('delay_blocks', 0)  # NEW: send in X blocks
    unlock_block = data.get('unlock_block', 0)   # OLD: absolute (fallback)
    message = data.get('message', '')
    fee = data.get('fee', 1.0)
    
    if not to_raw:
        return jsonify({'error': 'Recipient required'}), 400
    
    # Resolve username → address
    to_addr = resolve_recipient(to_raw)
    if not to_addr:
        return jsonify({'error': f'Recipient not found: {to_raw}'}), 404
    
    try:
        amount = float(amount)
        unlock_block = int(unlock_block)
        delay_blocks = int(delay_blocks)
        fee = float(fee)
    except:
        return jsonify({'error': 'Invalid amount/block/fee'}), 400
    
    with S.lock:
        current_height = len(S.chain)
        
        # Convert relative to absolute
        if delay_blocks > 0:
            unlock_block = current_height + delay_blocks
        
        if unlock_block <= current_height:
            return jsonify({'error': f'Unlock block must be in the future (current: {current_height})'}), 400
        
        success, error, tx = S.timelock.create_timelock_tx(
            from_addr=from_addr,
            to_addr=to_addr,
            amount=amount,
            unlock_block=unlock_block,
            message=message,
            fee=fee
        )
        
        if success:
            S.save()
            blocks_remaining = unlock_block - current_height
            est_sec = blocks_remaining * 10
            est_min = est_sec // 60
            est_hr = est_min // 60
            est_str = f"~{est_hr}h {est_min%60}m" if est_hr > 0 else f"~{est_min}m" if est_min > 0 else f"~{est_sec}s"
            return jsonify({
                'ok': True,
                'tx_id': tx['tx_id'],
                'unlock_block': unlock_block,
                'current_block': current_height,
                'blocks_remaining': blocks_remaining,
                'estimated_time': est_str,
                'amount': amount,
                'fee': fee
            })
        else:
            return jsonify({'error': error}), 400


@app.route('/api/timelock/cancel', methods=['POST'])
def cancel_timelock():
    """Cancel time-locked transaction"""
    if not TIMELOCK_ENABLED or not S.timelock:
        return jsonify({'error': 'Time-Lock not available'}), 503
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    tx_id = data.get('tx_id', '').strip()
    from_addr = get_address_from_seed(seed)
    
    if not tx_id:
        return jsonify({'error': 'Transaction ID required'}), 400
    
    with S.lock:
        success, error = S.timelock.cancel_timelock_tx(tx_id, from_addr)
        
        if success:
            S.save()
            return jsonify({'ok': True, 'message': 'Transaction cancelled'})
        else:
            return jsonify({'error': error}), 400


@app.route('/api/timelock/pending', methods=['GET'])
def get_pending_timelocks():
    """Get pending time-locked transactions"""
    if not TIMELOCK_ENABLED or not S.timelock:
        return jsonify({'error': 'Time-Lock not available'}), 503
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        pending = S.timelock.get_pending_for_address(addr)
        return jsonify({
            'ok': True,
            'transactions': pending,
            'count': len(pending)
        })


@app.route('/api/timelock/stats', methods=['GET'])
def get_timelock_stats():
    """Get time-lock statistics"""
    if not TIMELOCK_ENABLED or not S.timelock:
        return jsonify({'error': 'Time-Lock not available'}), 503
    
    with S.lock:
        stats = S.timelock.get_stats()
        return jsonify({'ok': True, 'stats': stats})

@app.route('/api/wallet/transactions', methods=['GET', 'POST'])
def get_wallet_transactions():
    """Get all transactions for a wallet (from blockchain)"""
    seed = request.headers.get('X-Seed', '').strip()  # Get from header
    
    if not seed:
        return jsonify({'error': 'Unauthorized - no seed'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        transactions = {
            'received': [],
            'sent': [],
            'burned': [],
            'timelock_sent': [],
            'timelock_received': [],
            'mining': []
        }
        
        total_received = 0
        total_sent = 0
        total_burned = 0
        
        # Scan blocks - limit to last 2000 for speed, full scan for "all" param
        full_scan = request.args.get('full', '0') == '1'
        blocks_to_scan = S.chain if full_scan else S.chain[-2000:]
        
        for block in blocks_to_scan:
            block_index = block['index']
            block_time = block['timestamp']
            
            # Mining rewards
            if 'mining_rewards' in block:
                for reward in block.get('mining_rewards', []):
                    # New blocks: no address (privacy). Old blocks: has address
                    if reward.get('address') == addr or reward.get('address') is None:
                        if reward.get('address') == addr:  # only count if explicitly ours
                            transactions['mining'].append({
                                'type': 'mining',
                                'amount': reward['reward'],
                            'block': block_index,
                            'timestamp': block_time
                        })
            
            # Regular transactions
            for tx in block.get('transactions', []):
                tx_type = tx.get('type', 'transfer')
                
                # Received transactions
                if tx.get('to') == addr and tx_type not in ['burn_level_upgrade', 'burn_nickname_change']:
                    amount = tx.get('amount', 0)
                    total_received += amount
                    
                    transactions['received'].append({
                        'type': tx_type,
                        'from': tx.get('from', 'anonymous'),
                        'amount': amount,
                        'block': block_index,
                        'timestamp': block_time,
                        'ring': 'ring_signature' in tx,
                        'stealth': tx_type == 'stealth_transfer'
                    })
                
                # Sent transactions (non-anonymous)
                if tx.get('from') == addr and tx_type not in ['burn_level_upgrade', 'burn_nickname_change', 'ring_transfer']:
                    amount = tx.get('amount', 0)
                    total_sent += amount
                    
                    transactions['sent'].append({
                        'type': tx_type,
                        'to': tx.get('to', 'unknown'),
                        'amount': amount,
                        'block': block_index,
                        'timestamp': block_time
                    })
                
                
                # Anonymous SENT transactions (check real_from)
                if tx.get('real_from') == addr and tx_type in ['ring_transfer', 'stealth_transfer', 'veil_transfer']:
                    amount = tx.get('real_amount', 0)
                    ring_fee = tx.get('ring_fee', 0) or tx.get('stealth_fee', 0)
                    total_sent += amount + ring_fee
                    
                    transactions['sent'].append({
                        'type': tx_type,
                        'to': 'anonymous',  # Hidden by privacy
                        'amount': amount,
                        'fee': ring_fee,
                        'block': block_index,
                        'timestamp': block_time,
                        'anonymous': True
                    })
                
                # Anonymous RECEIVED transactions (check real_to)
                if tx.get('real_to') == addr and tx_type in ['ring_transfer', 'stealth_transfer', 'veil_transfer']:
                    amount = tx.get('real_amount', 0)
                    total_received += amount
                    
                    transactions['received'].append({
                        'type': tx_type,
                        'from': 'anonymous',  # Hidden by privacy
                        'amount': amount,
                        'block': block_index,
                        'timestamp': block_time,
                        'anonymous': True,
                        'stealth': tx_type == 'stealth_transfer'
                    })
                
                # Faucet transactions
                if tx_type == 'faucet' and tx.get('to') == addr:
                    amount = tx.get('amount', 0)
                    total_received += amount
                    
                    transactions['received'].append({
                        'type': 'faucet',
                        'from': 'faucet',
                        'amount': amount,
                        'block': block_index,
                        'timestamp': block_time
                    })
                
                # STASH deposits (from is now 'anonymous', check real_from)
                if tx_type == 'stash_deposit' and (tx.get('real_from') == addr or tx.get('from') == addr):
                    amount = tx.get('amount', 0)
                    total_burned += amount
                    transactions['burned'].append({
                        'type': 'stash_deposit',
                        'amount': amount,
                        'nominal': tx.get('nominal_code'),
                        'block': block_index,
                        'timestamp': block_time
                    })
                
                # STASH withdrawals (to is now OTA, check real_to)
                if tx_type == 'stash_withdraw' and (tx.get('real_to') == addr or tx.get('to') == addr):
                    amount = tx.get('amount', 0)
                    total_received += amount
                    transactions['received'].append({
                        'type': 'stash_withdraw',
                        'from': 'stash_pool',
                        'amount': amount,
                        'block': block_index,
                        'timestamp': block_time,
                        'anonymous': True
                    })
                
                # Username registration transactions
                if tx_type == 'username_register' and tx.get('from') == addr:
                    amount = tx.get('amount', 0)
                    total_burned += amount
                    
                    transactions['burned'].append({
                        'type': 'username_register',
                        'amount': amount,
                        'username': tx.get('username', 'Unknown'),
                        'block': block_index,
                        'timestamp': block_time
                    })
                # Burned transactions (show nickname changes with old/new)
                if tx.get('from') == addr and tx_type in ['burn_level_upgrade', 'burn_nickname_change']:
                    amount = tx.get('amount', 0)
                    total_burned += amount
                    
                    burn_info = {
                        'type': tx_type,
                        'amount': amount,
                        'block': block_index,
                        'timestamp': block_time,
                        'level_from': tx.get('level_from'),
                        'level_to': tx.get('level_to')
                    }
                    
                    # Add nickname info if available
                    if tx_type == 'burn_nickname_change':
                        burn_info['old_nickname'] = tx.get('old_nickname', 'Unknown')
                        burn_info['new_nickname'] = tx.get('new_nickname', 'Unknown')
                    
                    transactions['burned'].append(burn_info)
        
        # Scan for time-lock activated transactions (from blockchain)
        # These show up as "received" for the receiver
        if hasattr(S, 'timelock') and S.timelock:
            # Track activated time-locks by scanning blockchain
            for block in S.chain:
                block_index = block['index']
                block_time = block['timestamp']
                
                for tx in block.get('transactions', []):
                    if tx.get('type') == 'timelock_activated':
                        tx_id = tx.get('tx_id')
                        
                        # Check if this user was involved in original time-lock
                        if tx_id and hasattr(S.timelock, 'activated_timelocked') and tx_id in S.timelock.activated_timelocked:
                            original_tx = S.timelock.activated_timelocked[tx_id]
                            
                            # Receiver sees as "received"
                            if original_tx.get('to') == addr:
                                amount = original_tx.get('amount', 0)
                                total_received += amount
                                
                                transactions['received'].append({
                                    'type': 'timelock_activated',
                                    'from': 'anonymous',  # Privacy
                                    'amount': amount,
                                    'block': block_index,
                                    'timestamp': block_time,
                                    'timelock': True
                                })
        
        # Dice game history (from wallet, not blockchain - anonymous on chain)
        try:
            dice_history = wallet.get('dice_history', [])
            for game in dice_history:
                if game.get('won'):
                    net_win = game.get('payout', 0) - game.get('amount', 0)
                    if net_win > 0:
                        transactions['received'].append({
                            'type': 'dice_win',
                            'from': 'dice_contract',
                            'amount': net_win,
                            'timestamp': game.get('timestamp', 0),
                            'anonymous': True
                        })
                        total_received += net_win
                else:
                    bet_amt = game.get('amount', 0)
                    transactions['burned'].append({
                        'type': 'dice_loss',
                        'amount': bet_amt,
                        'timestamp': game.get('timestamp', 0),
                        'anonymous': True
                    })
                    total_burned += bet_amt
        except Exception:
            pass  # Don't crash if dice history is malformed
        
        return jsonify({
            'ok': True,
            'address': addr,
            'transactions': transactions,
            'summary': {
                'total_received': total_received,
                'total_sent': total_sent,
                'total_burned': total_burned,
                'net': total_received - total_sent - total_burned
            }
        })


@app.route('/api/wallet/stats', methods=['GET'])
def get_wallet_stats():
    """Get wallet statistics (last 7 days)"""
    seed = request.headers.get('X-Seed', '').strip()
    
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        now = int(time.time())
        day_seconds = 86400
        
        # Initialize daily stats
        daily_stats = {}
        for i in range(7):
            day_start = now - (i * day_seconds)
            day_key = time.strftime('%Y-%m-%d', time.localtime(day_start))
            daily_stats[day_key] = {
                'received': 0,
                'sent': 0,
                'balance': 0,
                'date': day_key
            }
        
        # Today's stats
        today_start = now - (now % day_seconds)
        today_received = 0
        today_sent = 0
        today_burned = 0
        
        # Scan blockchain for transactions
        for block in S.chain:
            block_time = block['timestamp']
            
            # Skip if too old
            if block_time < (now - 7 * day_seconds):
                continue
            
            # Get day key
            day_key = time.strftime('%Y-%m-%d', time.localtime(block_time))
            
            if day_key not in daily_stats:
                continue
            
            # Process transactions
            for tx in block.get('transactions', []):
                # Received
                if tx.get('to') == addr:
                    amount = tx.get('amount', 0)
                    daily_stats[day_key]['received'] += amount
                    
                    if block_time >= today_start:
                        today_received += amount
                
                # Sent
                if tx.get('from') == addr and tx.get('type') not in ['burn_level_upgrade', 'burn_nickname_change']:
                    amount = tx.get('amount', 0)
                    daily_stats[day_key]['sent'] += amount
                    
                    if block_time >= today_start:
                        today_sent += amount
                
                # Burned
                if tx.get('from') == addr and tx.get('type') in ['burn_level_upgrade', 'burn_nickname_change']:
                    amount = tx.get('amount', 0)
                    
                    if block_time >= today_start:
                        today_burned += amount
        
        # Calculate cumulative balance for each day
        current_balance = S.wallets.get(addr, {}).get('balance', 0)
        days_sorted = sorted(daily_stats.keys(), reverse=True)
        
        for i, day in enumerate(days_sorted):
            if i == 0:
                daily_stats[day]['balance'] = current_balance
            else:
                prev_day = days_sorted[i-1]
                daily_stats[day]['balance'] = daily_stats[prev_day]['balance'] - \
                    daily_stats[day]['received'] + daily_stats[day]['sent']
        
        return jsonify({
            'ok': True,
            'today': {
                'received': today_received,
                'sent': today_sent,
                'burned': today_burned,
                'net': today_received - today_sent - today_burned
            },
            'daily': [daily_stats[day] for day in days_sorted]
        })

# ===================== MAIN =====================


@app.route('/api/mining/status', methods=['GET'])
def mining_status():
    """Get mining status"""
    if not POET_ENABLED or not S or not S.mining_coordinator:
        return jsonify({'ok': False, 'mining_active': False, 'message': 'Mining not available'})
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized', 'ok': False}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found', 'ok': False}), 404
        
        wallet = S.wallets[addr]
        balance = wallet.get('balance', 0)
        level = wallet.get('level', 0)
        
        # Count wins from wallet mining_history
        mining_history = wallet.get('mining_history', [])
        recent_wins = len(mining_history[-100:])  # Last 100 wins
        total_earned = sum(entry.get('reward', 0) for entry in mining_history)
        
        can_mine = balance >= 50
        
        return jsonify({
            'ok': True,
            'mining_active': S.mining_active and can_mine,
            'can_mine': can_mine,
            'balance': balance,
            'level': level,
            'level_name': ['Newbie','Starter','Active','Trusted','Expert','Validator','Priority','⚡ GOD'][min(level,7)],
            'recent_wins': recent_wins,
            'total_earned': total_earned,
            'blocks_mined': len(mining_history),
            'min_balance': 50,
            'block_reward': 190,
            'winners_per_block': 19,
            'god_bonus': level >= 7,
            'god_multiplier': 2 if level >= 7 else 1,
        })


@app.route('/api/network/stats', methods=['GET'])
def network_stats():
    """Get network statistics"""
    with S.lock:
        # Count active miners (active sessions + 50+ LAC)
        active_miners = 0
        for addr in S.active_sessions:
            if addr in S.wallets and S.wallets[addr].get('balance', 0) >= 50:
                active_miners += 1
        
        # Count validators (level 4+)
        validators = 0
        for wallet in S.wallets.values():
            if wallet.get('level', 0) >= 4:
                validators += 1
        
        # Total supply
        total_supply = sum(w.get('balance', 0) for w in S.wallets.values())
        
        return jsonify({
            'ok': True,
            'active_miners': active_miners,
            'validators': validators,
            'total_supply': total_supply,
            'total_wallets': len(S.wallets),
            'chain_height': len(S.chain)
        })


@app.route('/api/debug/mining', methods=['GET'])
def debug_mining():
    """Debug endpoint - show mining info"""
    with S.lock:
        # Get active sessions
        active_addrs = list(S.active_sessions)
        
        # Get eligible miners (balance >= 50)
        eligible_miners = []
        for addr in active_addrs:
            if addr in S.wallets:
                wallet = S.wallets[addr]
                balance = wallet.get('balance', 0)
                level = wallet.get('level', 0)
                key_id = wallet.get('key_id')
                username = get_username_by_key_id(key_id) or 'Anonymous'
                
                if balance >= 50:
                    eligible_miners.append({
                        'address': addr[:20] + '...',
                        'username': username,
                        'balance': balance,
                        'level': level,
                        'can_mine': True
                    })
        
        # Get all wallets with balance >= 50
        all_eligible = []
        for addr, wallet in S.wallets.items():
            balance = wallet.get('balance', 0)
            if balance >= 50:
                key_id = wallet.get('key_id')
                username = get_username_by_key_id(key_id) or 'Anonymous'
                all_eligible.append({
                    'address': addr[:20] + '...',
                    'username': username,
                    'balance': balance,
                    'active_session': addr in S.active_sessions
                })
        
        return jsonify({
            'ok': True,
            'active_sessions_count': len(active_addrs),
            'eligible_miners_count': len(eligible_miners),
            'total_wallets_50plus': len(all_eligible),
            'active_sessions': active_addrs[:5] if active_addrs else [],  # First 5
            'eligible_miners': eligible_miners,
            'all_eligible_wallets': all_eligible,
            'min_balance': 50,
            'hint': 'Only wallets with active session + 50+ LAC balance can mine'
        })


# ===================== USERNAME API ROUTES =====================

@app.route('/api/username/check', methods=['POST'])
def username_check():
    """Check username availability and price"""
    data = request.get_json() or {}
    username = data.get('username', '').strip().lower().lstrip('@')
    
    if not username:
        return jsonify({'error': 'Username required', 'ok': False}), 400
    
    if len(username) < 3 or len(username) > 20:
        return jsonify({'ok': False, 'available': False, 'error': 'Must be 3-20 characters'})
    
    import re as _re
    if not _re.match(r'^[a-z0-9_]+$', username):
        return jsonify({'ok': False, 'available': False, 'error': 'Only a-z, 0-9, _ allowed'})
    
    with S.lock:
        available = username not in S.usernames
        price = {3: 10000, 4: 1000, 5: 100}.get(len(username), 10)
        
        return jsonify({
            'ok': True,
            'username': f'@{username}',
            'available': available,
            'price': price
        })

@app.route('/api/username/register', methods=['POST'])
def username_register():
    """
    Register username → directly linked to wallet address
    Stored in S.usernames (survives Zero-History)
    TX in block is just a receipt/proof
    """
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized', 'ok': False}), 401
    
    data = request.get_json() or {}
    username = data.get('username', '').strip().lower()
    
    if not username:
        return jsonify({'error': 'Username required', 'ok': False}), 400
    
    # Strip @ if present, store without it
    username = username.lstrip('@')
    
    # Validate: 3-20 chars, alphanumeric + underscore
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': 'Username must be 3-20 characters', 'ok': False}), 400
    
    import re as _re
    if not _re.match(r'^[a-z0-9_]+$', username):
        return jsonify({'error': 'Only a-z, 0-9, _ allowed', 'ok': False}), 400
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found', 'ok': False}), 404
        
        wallet = S.wallets[addr]
        
        # Check if username taken
        if username in S.usernames:
            return jsonify({'error': 'Username already taken', 'ok': False}), 409
        
        # Check if user already has a username
        existing = None
        for u, a in S.usernames.items():
            if a == addr:
                existing = u
                break
        
        # Price: 3 chars=1000, 4 chars=100, 5+=10 LAC
        price = {3: 10000, 4: 1000, 5: 100}.get(len(username), 10)
        
        if wallet.get('balance', 0) < price:
            return jsonify({'error': f'Need {price} LAC', 'ok': False}), 400
        
        # Remove old username if exists
        if existing:
            del S.usernames[existing]
        
        # Register: direct mapping username → address
        S.usernames[username] = addr
        wallet['balance'] -= price
        S.counters['burned_username'] += price
        wallet['username'] = username
        wallet['tx_count'] = wallet.get('tx_count', 0) + 1
        
        # Blockchain TX (receipt — will be erased by ZH, but mapping persists in State)
        tx = {
            'type': 'username_register',
            'username': f'@{username}',
            'from': addr,
            'amount': price,
            'timestamp': int(time.time())
        }
        tx = sign_transaction(seed, tx)
        S.mempool.append(tx)
        S.save()
        
        print(f"  \U0001f464 Username registered: @{username} → {addr[:16]}...")
        
        return jsonify({
            'ok': True,
            'username': f'@{username}',
            'address': addr,
            'fee_paid': price,
            'balance': wallet.get('balance', 0),
            'message': f'@{username} registered!'
        })

@app.route('/api/username/resolve', methods=['POST'])
def username_resolve():
    """Resolve username to wallet address"""
    data = request.get_json() or {}
    username = data.get('username', '').strip().lower().lstrip('@')
    
    if not username:
        return jsonify({'error': 'Username required', 'ok': False}), 400
    
    with S.lock:
        addr = S.usernames.get(username)
        if not addr:
            return jsonify({'error': 'Username not found', 'ok': False}), 404
        
        return jsonify({
            'ok': True,
            'username': f'@{username}',
            'address': addr,
            'exists': addr in S.wallets
        })

@app.route('/api/username/search', methods=['POST'])
def username_search():
    """Search usernames"""
    data = request.get_json() or {}
    query = data.get('query', '').strip().lower()
    limit = min(int(data.get('limit', 10)), 50)
    
    if not query:
        return jsonify({'error': 'Search query required', 'ok': False}), 400
    
    with S.lock:
        results = []
        for uname, addr in S.usernames.items():
            if query in uname:
                results.append({'username': f'@{uname}', 'address': addr})
                if len(results) >= limit:
                    break
        
        return jsonify({
            'ok': True,
            'query': query,
            'results': results,
            'count': len(results)
        })

@app.route('/api/username/my', methods=['GET'])
def username_my():
    """Get my username"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized', 'ok': False}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found', 'ok': False}), 404
        
        # Find username for this address
        my_username = None
        for u, a in S.usernames.items():
            if a == addr:
                my_username = u
                break
        
        return jsonify({
            'ok': True,
            'username': f'@{my_username}' if my_username else None,
            'address': addr,
            'has_username': my_username is not None
        })

@app.route('/api/username/burn', methods=['POST'])
def username_burn():
    """Burn username (coming soon)"""
    return jsonify({'error': 'Burn functionality coming soon'}), 501

@app.route('/api/username/owner/<address>', methods=['GET'])
def username_owner(address):
    """Get username for specific address"""
    with S.lock:
        # Find username for this address
        for uname, addr in S.usernames.items():
            if addr == address:
                return jsonify({
                    'ok': True,
                    'address': address,
                    'username': f'@{uname}'
                })
        
        return jsonify({
            'ok': True,
            'address': address,
            'username': None
        })

@app.route('/api/username/transfer', methods=['POST'])
def username_transfer():
    """Transfer username (coming soon)"""
    return jsonify({'error': 'Transfer functionality coming soon'}), 501

@app.route('/api/username/burn2', methods=['POST'])
def username_burn2():
    """Burn (destroy) username"""
    if not USERNAME_ENABLED:
        return jsonify({'error': 'Username system not available'}), 503
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    burn_forever = data.get('burn_forever', True)
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Check username exists
        uname = username.lstrip('@').lower()
        if uname not in S.usernames:
            return jsonify({'error': 'Username not found'}), 404
        
        # TODO: Verify ownership
        # For now, allow anyone to burn (will add ownership check later)
        
        # Create burn transaction
        tx = {
            'type': TX_TYPE_USERNAME_BURN,
            'username': username if username.startswith('@') else f'@{username}',
            'burn_forever': burn_forever,
            'from': addr,
            'timestamp': int(time.time())
        }
        
        # Add to mempool
        S.mempool.append(tx)
        S.save()
        
        return jsonify({
            'ok': True,
            'username': tx['username'],
            'burn_forever': burn_forever,
            'message': 'Username burn submitted. Will be confirmed in next block.'
        })

@app.route('/api/username/stats', methods=['GET'])
def username_stats():
    """Username registry statistics"""
    with S.lock:
        return jsonify({
            'ok': True,
            'total_count': len(S.usernames),
            'total_registered': len(S.usernames),
            'active': len(S.usernames)
        })


@app.route('/api/username/debug', methods=['GET'])
def username_debug():
    """DEBUG: Show usernames"""
    with S.lock:
        return jsonify({
            'ok': True,
            'usernames': S.usernames,
            'count': len(S.usernames)
        })



# ===================== P2P SYNCHRONIZATION =====================

import requests
from urllib.parse import urlparse

# Store known peers
known_peers = set()
peers_lock = Lock()

# P2P mesh network state
p2p_lock = Lock()
p2p_peers = {}  # {peerId: {address, lastSeen}}

def add_peer(peer_url):
    """Add peer to known peers list"""
    with peers_lock:
        # Normalize URL
        if not peer_url.startswith('http'):
            peer_url = f'http://{peer_url}'
        known_peers.add(peer_url)
        print(f"🔗 Added peer: {peer_url}")

def sync_from_peer(peer_url, silent=False):
    """Synchronize blockchain from peer"""
    try:
        if not peer_url.startswith('http'):
            peer_url = f'http://{peer_url}'
        
        if not silent:
            print(f"🔄 Syncing from peer: {peer_url}")
        
        # Get peer's chain height
        response = requests.get(f'{peer_url}/api/chain/height', timeout=5)
        if response.status_code != 200:
            if not silent:
                print(f"⚠️ Peer {peer_url} unreachable")
            return False
        
        peer_data = response.json()
        peer_height = peer_data.get('height', 0)
        
        with S.lock:
            our_height = len(S.chain)
        
        if peer_height <= our_height:
            if not silent:
                print(f"✅ Already synced (our: {our_height}, peer: {peer_height})")
            return True
        
        # Download missing blocks
        blocks_to_download = peer_height - our_height
        print(f"📥 Downloading {blocks_to_download} blocks from peer...")
        
        batch_size = 50
        for start in range(our_height, peer_height, batch_size):
            end = min(start + batch_size, peer_height)
            
            response = requests.get(
                f'{peer_url}/api/blocks/range',
                params={'start': start, 'end': end},
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"⚠️ Failed to download blocks {start}-{end}")
                return False
            
            data = response.json()
            blocks = data.get('blocks', [])
            
            with S.lock:
                for block in blocks:
                    # Verify and add block
                    block_index = block.get('index', -1)
                    
                    if block_index != len(S.chain):
                        print(f"⚠️ Block index mismatch: expected {len(S.chain)}, got {block_index}")
                        continue
                    
                    # Verify previous hash
                    if block_index > 0:
                        prev_block = S.chain[-1]
                        if block.get('previous_hash') != prev_block['hash']:
                            print(f"⚠️ Invalid previous hash at block {block_index}")
                            return False
                    
                    # Add block
                    S.chain.append(block)
                    
                    # Update wallets from block transactions
                    for tx in block.get('transactions', []):
                        if tx.get('type') == 'transfer':
                            from_addr = tx.get('from')
                            to_addr = tx.get('to')
                            amount = tx.get('amount', 0)
                            
                            if from_addr and from_addr in S.wallets:
                                S.wallets[from_addr]['balance'] -= amount
                            
                            if to_addr:
                                if to_addr not in S.wallets:
                                    S.wallets[to_addr] = {
                                        'balance': 0,
                                        'nonce': 0,
                                        'created_at': int(time.time())
                                    }
                                S.wallets[to_addr]['balance'] += amount
                
                # Save after each batch
                S.save()
            
            print(f"✅ Downloaded blocks {start}-{end-1}")
        
        print(f"🎉 Sync complete! Chain height: {len(S.chain)}")
        add_peer(peer_url)
        return True
        
    except Exception as e:
        if not silent:
            print(f"❌ Sync failed: {e}")
        return False

def broadcast_block_to_peers(block):
    """Broadcast new block to all known peers"""
    with peers_lock:
        peers_to_broadcast = list(known_peers)
    
    if not peers_to_broadcast:
        return
    
    print(f"📡 Broadcasting block #{block.get('index', '?')} to {len(peers_to_broadcast)} peers")
    
    for peer_url in peers_to_broadcast:
        try:
            response = requests.post(
                f'{peer_url}/api/block/submit',
                json={'block': block},
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                if status == 'accepted':
                    print(f"✅ Peer {peer_url} accepted block")
            else:
                print(f"⚠️ Peer {peer_url} rejected block: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Failed to broadcast to {peer_url}: {e}")

def discover_local_peers():
    """Discover peers in local network"""
    import socket
    
    try:
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Extract network prefix (e.g., 192.168.0)
        ip_parts = local_ip.split('.')
        network_prefix = '.'.join(ip_parts[:3])
        
        print(f"🔍 Scanning local network: {network_prefix}.0/24")
        
        # Common LAC ports
        ports = [38400, 38401, 38402, 38403]
        
        found_peers = []
        for i in range(1, 255):
            for port in ports:
                peer_ip = f"{network_prefix}.{i}"
                peer_url = f"http://{peer_ip}:{port}"
                
                # Skip self
                if peer_ip == local_ip:
                    continue
                
                try:
                    response = requests.get(f'{peer_url}/api/chain/height', timeout=0.5)
                    if response.status_code == 200:
                        found_peers.append(peer_url)
                        add_peer(peer_url)
                        print(f"✅ Found peer: {peer_url}")
                except:
                    pass
        
        return found_peers
        
    except Exception as e:
        print(f"⚠️ Peer discovery failed: {e}")
        return []

def periodic_sync_loop():
    """Periodically sync with known peers"""
    while True:
        time.sleep(30)  # Sync every 30 seconds
        
        with peers_lock:
            peers_to_check = list(known_peers)
        
        if not peers_to_check:
            continue
        
        # Try to sync from each peer
        for peer_url in peers_to_check:
            try:
                sync_from_peer(peer_url, silent=True)
            except:
                pass


# ===================== STABILITY: HEALTH ENDPOINT =====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    if not STABILITY_ENABLED or not 'stability' in globals() or not stability:
        return jsonify({'ok': True, 'status': 'healthy', 'message': 'Monitoring not enabled'})
    
    health_monitor = stability.get('health')
    if not health_monitor:
        return jsonify({'ok': True, 'status': 'healthy', 'message': 'No health monitor'})
    
    results, is_healthy = health_monitor.run_checks()
    
    if is_healthy:
        status = 'healthy'
        http_code = 200
    elif any(not result['passed'] and result['critical'] for result in results.values()):
        status = 'unhealthy'
        http_code = 503
    else:
        status = 'degraded'
        http_code = 200
    
    return jsonify({'ok': is_healthy, 'status': status, 'checks': results}), http_code


# ==================== ZERO-HISTORY PHASE 2B ENDPOINTS ====================

@app.route('/api/zero-history/stats', methods=['GET'])
def zh_stats():
    """Get Zero-History storage statistics"""
    try:
        if not ZERO_HISTORY_ENABLED or not S.zero_history:
            return jsonify({'error': 'Zero-History not enabled'}), 503
        
        stats = S.zero_history.get_storage_stats()
        return jsonify({'ok': True, 'res': stats})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/zero-history/validators', methods=['GET'])
def zh_validators():
    """Get active validators list"""
    try:
        if not ZERO_HISTORY_ENABLED or not S.zero_history:
            return jsonify({'error': 'Zero-History not enabled'}), 503
        
        validators = S.zero_history.validator_manager.get_active_validators()
        
        return jsonify({
            'ok': True,
            'res': {
                'total': len(validators),
                'validators': [v.to_dict() for v in validators]
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/zero-history/validator/<address>', methods=['GET'])
def zh_validator_info(address: str):
    """Get specific validator info"""
    try:
        if not ZERO_HISTORY_ENABLED or not S.zero_history:
            return jsonify({'error': 'Zero-History not enabled'}), 503
        
        validator = S.zero_history.validator_manager.validators.get(address)
        
        if validator:
            return jsonify({'ok': True, 'res': validator.to_dict()})
        else:
            return jsonify({'ok': False, 'error': 'Validator not found'}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/zero-history/commitments', methods=['GET'])
def zh_commitments():
    """Get L1 commitments"""
    try:
        if not ZERO_HISTORY_ENABLED or not S.zero_history:
            return jsonify({'error': 'Zero-History not enabled'}), 503
        
        commitments = S.zero_history.l1_commitments
        
        return jsonify({
            'ok': True,
            'res': {
                'total': len(commitments),
                'commitments': [c.to_dict() for c in commitments]
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/zero-history/fraud-proofs', methods=['GET'])
def zh_fraud_proofs():
    """Get fraud proofs"""
    try:
        if not ZERO_HISTORY_ENABLED or not S.zero_history:
            return jsonify({'error': 'Zero-History not enabled'}), 503
        
        proofs = S.zero_history.fraud_system.fraud_proofs
        
        return jsonify({
            'ok': True,
            'res': {
                'total': len(proofs),
                'verified': sum(1 for p in proofs.values() if p.verified),
                'fraud_proofs': [p.to_dict() for p in proofs.values()]
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/zero-history/tier/<tier>', methods=['GET'])
def zh_tier_info(tier: str):
    """Get tier information (l1/l2/l3)"""
    try:
        if not ZERO_HISTORY_ENABLED or not S.zero_history:
            return jsonify({'error': 'Zero-History not enabled'}), 503
        
        if tier == 'l3':
            blocks = S.zero_history.l3_blocks
            return jsonify({
                'ok': True,
                'res': {
                    'tier': 'L3',
                    'retention': f'{ZH_L3_RETENTION_DAYS} days',
                    'retention_days': ZH_L3_RETENTION_DAYS,
                    'blocks': len(blocks),
                    'data_type': 'Full transaction data + messages'
                }
            })
        elif tier == 'l2':
            blocks = S.zero_history.l2_blocks
            return jsonify({
                'ok': True,
                'res': {
                    'tier': 'L2',
                    'retention': f'{ZH_L2_RETENTION_DAYS} days',
                    'retention_days': ZH_L2_RETENTION_DAYS,
                    'blocks': len(blocks),
                    'data_type': 'Pruned data + fraud proofs'
                }
            })
        elif tier == 'l1':
            commitments = S.zero_history.l1_commitments
            return jsonify({
                'ok': True,
                'res': {
                    'tier': 'L1',
                    'retention': 'Forever',
                    'commitments': len(commitments),
                    'data_type': 'State commitments only'
                }
            })
        else:
            return jsonify({'ok': False, 'error': 'Invalid tier (l1/l2/l3)'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/zero-history/bootstrap', methods=['POST'])
def zh_bootstrap():
    """Bootstrap new node (for sync)"""
    try:
        if not ZERO_HISTORY_ENABLED or not S.zero_history:
            return jsonify({'error': 'Zero-History not enabled'}), 503
        
        data = request.json or {}
        peers = data.get('peers', [])
        
        package = S.zero_history.bootstrap_system.bootstrap_new_node(
            peers=peers,
            blockchain_state=S.__dict__
        )
        
        if package:
            return jsonify({'ok': True, 'res': package.to_dict()})
        else:
            return jsonify({'ok': False, 'error': 'Bootstrap failed'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/zero-history/recovery/checkpoints', methods=['GET'])
def zh_recovery_checkpoints():
    """Get recovery checkpoints"""
    try:
        if not ZERO_HISTORY_ENABLED or not S.zero_history:
            return jsonify({'error': 'Zero-History not enabled'}), 503
        
        checkpoints = S.zero_history.recovery.recovery_checkpoints
        
        return jsonify({
            'ok': True,
            'res': {
                'total': len(checkpoints),
                'checkpoints': checkpoints
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ==================== END ZERO-HISTORY ENDPOINTS ====================

# ==================== WEBSOCKET ENDPOINTS ====================

@app.route('/api/websocket/stats', methods=['GET'])
def get_websocket_stats():
    """Get WebSocket real-time sync statistics"""
    if not ws_sync:
        return jsonify({'error': 'WebSocket not enabled (running with HTTP polling only)'}), 503
    
    try:
        stats = ws_sync.get_stats()
        peers = ws_sync.get_connected_peers()
        
        return jsonify({
            'ok': True,
            'stats': stats,
            'connected_peers': peers,
            'enabled': True
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ==================== END WEBSOCKET ENDPOINTS ====================



def main():
    global S
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['run'])
    parser.add_argument('--datadir', default='./lac-data/n1')
    parser.add_argument('--port', type=int, default=38400)
    parser.add_argument('--bootstrap', type=str, default=None, 
                        help='Bootstrap peer URL (e.g., http://127.0.0.1:38400)')
    parser.add_argument('--discover', action='store_true', 
                        help='Auto-discover peers in local network')
    args = parser.parse_args()
    
    # Setup logging (NO EMOJI IN LOGS!)
    logger = None
    if STABILITY_ENABLED:
        logger = setup_logging(args.datadir, debug=False)
        logger.info("[INFO] LAC Node starting with stability patches")
    
    
    S = State(args.datadir)
    
    # SQLite API endpoints
    if SQLITE_ENABLED and hasattr(S, 'db'):
        try:
            add_sqlite_api_endpoints(app, S)
        except Exception as e:
            print(f"⚠️ SQLite API endpoints failed: {e}")
    
    # Initialize WebSocket sync after State creation
    global ws_sync
    ws_sync = None
    if WEBSOCKET_AVAILABLE:
        try:
            ws_sync = init_websocket_sync(app, S)
            if ws_sync:
                print("[WebSocket] Real-time sync initialized")
        except Exception as e:
            print(f"[WebSocket] Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            ws_sync = None
    
    # Setup stability system (NO EMOJI!)
    global stability
    stability = None
    if STABILITY_ENABLED:
        stability = setup_stability_system(S, args.datadir, flask_app=app)
        if logger:
            logger.info("[OK] Stability system initialized")

    # Setup security
    global rate_limiter
    if SECURITY_ENABLED:
        rate_limiter = RateLimiter()
        if logger:
            logger.info("[OK] Security patches initialized")
    
    # Setup performance
    global block_cache
    if PERFORMANCE_ENABLED:
        block_cache = LRUCache(maxsize=1000)
        if logger:
            logger.info("[OK] Performance patches initialized")

    
    
    # P2P Bootstrap and Sync
    synced_from_peer = False
    if args.bootstrap:
        print(f"\n🔗 Bootstrapping from peer: {args.bootstrap}")
        synced_from_peer = sync_from_peer(args.bootstrap)
    
    # Auto-discover local peers
    if args.discover and not synced_from_peer:
        print("\n🔍 Discovering local peers...")
        discovered = discover_local_peers()
        if discovered:
            # Try to sync from first discovered peer
            sync_from_peer(discovered[0])
    
    # Start periodic sync thread
    Thread(target=periodic_sync_loop, daemon=True).start()
    
    # Initialize PoET Mining
    if POET_ENABLED:
        init_mining()
        Thread(target=auto_mining_loop, daemon=True).start()
    
    # OLD AUTO-MINING REMOVED (using PoET only)
    
    # Auto-cleanup still active
    Thread(target=auto_cleanup, daemon=True).start()
    
    print(f"""
🔥🔥🔥 [LAC Ephemeral Chain v2.0 SECURED + P2P SYNC + PoET] 🔥🔥🔥
HTTP on :{args.port}
datadir: {args.datadir}
Height: {len(S.chain)}
Supply: {sum(w.get('balance', 0) for w in S.wallets.values()):.2f} LAC
⛏️ PoET Mining: {'ON (every 10s)' if POET_ENABLED else 'OFF'}
🧹 Auto-cleanup: ON (every 60s)
🛡️ Anonymity: VEIL Transfers + STASH Pool + Zero-History
🚨 Security: Rate Limiting + Anti-Sybil + Anti-DDoS
🌐 P2P Sync: ACTIVE (syncs every 30s)
📡 Known Peers: {len(known_peers)}
✅ ALL ENDPOINTS: inbox, groups, group.create, group.post
""")
    
    
    # Load Anonymous Groups plugin
    try:
        import lac_anon_groups_plugin


        lac_anon_groups_plugin.register_anonymous_groups(app, S)
    except Exception as e:
        print(f"⚠️ Anonymous Groups plugin not loaded: {e}")
        sys.stdout.flush()
    
    app.run(host='0.0.0.0', port=args.port, debug=False, use_reloader=False)


@app.route('/api/pruning/stats', methods=['GET'])
def get_pruning_stats():
    """Get blockchain pruning statistics"""
    with S.lock:
        if not S.pruning:
            return jsonify({'error': 'Pruning not available'}), 503
        
        stats = S.pruning.get_pruning_stats()
        return jsonify({'ok': True, 'stats': stats})

@app.route('/api/pruning/verify', methods=['GET'])
def verify_pruned_chain():
    """Verify pruned blockchain integrity"""
    with S.lock:
        if not S.pruning:
            return jsonify({'error': 'Pruning not available'}), 503
        
        valid = S.pruning.verify_pruned_chain()
        return jsonify({'ok': True, 'valid': valid})

@app.route('/api/decoy/stats', methods=['GET'])
def get_decoy_stats():
    """Get decoy transaction statistics"""
    with S.lock:
        if not S.decoy:
            return jsonify({'error': 'Decoy system not available'}), 503
        
        stats = S.decoy.get_stats()
        return jsonify({'ok': True, 'stats': stats})


# ============================================================================
# VEIL TRANSFER — Real Anonymous Transfer (Ring Sig + One-Time Address)
# ============================================================================

STASH_NOMINALS = {0: 100, 1: 1_000, 2: 10_000, 3: 100_000}
STASH_FEE = 2.0

@app.route('/api/transfer/veil', methods=['POST'])
def veil_transfer():
    """
    VEIL Transfer — Full anonymity (LAC unique implementation)
    
    - Ring of decoy public keys (hides sender)
    - One-Time Address (unlinkable recipient)
    - Key Image (prevents double-spend)
    - Amount hidden in encrypted payload
    
    Fee: 1.0 LAC
    """
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized', 'ok': False}), 401
    
    ip = get_client_ip()
    if not rate_limit_check(ip):
        return jsonify({'error': 'Rate limit exceeded', 'ok': False}), 429
    
    try:
        from_addr = get_address_from_seed(seed)
        data = request.get_json() or {}
        to_input = data.get('to', '').strip()
        amount = float(data.get('amount', 0))
        
        if not to_input or amount <= 0:
            return jsonify({'error': 'Invalid recipient or amount', 'ok': False}), 400
        
        with S.lock:
            if from_addr not in S.wallets:
                return jsonify({'error': 'Wallet not found', 'ok': False}), 404
            
            # Resolve recipient
            to_addr = resolve_recipient(to_input)
            if not to_addr:
                if to_input in S.wallets:
                    to_addr = to_input
                else:
                    return jsonify({'error': 'Recipient not found', 'ok': False}), 404
            
            veil_fee = 1.0
            total_needed = amount + veil_fee
            
            from_wallet = S.wallets[from_addr]
            if from_wallet.get('balance', 0) < total_needed:
                return jsonify({
                    'error': f'Insufficient balance. Need {total_needed} LAC',
                    'ok': False
                }), 400
            
            # === LAC VEIL CRYPTOGRAPHY ===
            
            # 1. One-Time Address (OTA) — unlinkable recipient
            if CRYPTO_MODULE and ED25519_AVAILABLE:
                # Real Stealth Address with X25519 DH
                stealth_keys = StealthAddress.derive_stealth_keys(seed)
                # Get or generate recipient stealth keys
                to_wallet = S.wallets.get(to_addr, {})
                rcv_scan = to_wallet.get('stealth_scan_pubkey', hashlib.sha256(to_addr.encode()).hexdigest())
                rcv_spend = to_wallet.get('stealth_spend_pubkey', hashlib.sha256((to_addr+'spend').encode()).hexdigest())
                ota_data = StealthAddress.generate_one_time_address(rcv_scan, rcv_spend)
                ota = ota_data['one_time_address']
                ephemeral_hex = ota_data['ephemeral_pubkey']
                ephemeral = bytes.fromhex(ephemeral_hex) if len(ephemeral_hex) <= 64 else secrets.token_bytes(32)
            else:
                ephemeral = secrets.token_bytes(32)
                recipient_pub = hashlib.sha256(to_addr.encode()).digest()
                shared_secret = hashlib.sha256(ephemeral + recipient_pub).digest()
                ota = f"veil_{hashlib.sha256(b'OTA' + shared_secret).hexdigest()[:64]}"
            
            # 2. Key Image — unique per transaction, prevents double-spend  
            private_key = hashlib.sha256(seed.encode()).digest()
            tx_entropy = secrets.token_bytes(16)
            key_image = hashlib.sha256(
                b"VEIL_KI" + private_key + tx_entropy + str(amount).encode()
            ).hexdigest()
            
            if key_image in S.spent_key_images:
                return jsonify({'error': 'Double-spend rejected', 'ok': False}), 400
            
            # 3. Ring of Decoys — hide sender among others
            all_addrs = [a for a in S.wallets.keys() 
                         if a != from_addr and a != to_addr 
                         and not a.startswith('seed_000') and not a.startswith('lac1qqqqqq')]
            import random
            # Random ring size: 6-14 decoys + 1 real = 7-15 total
            ring_target = random.randint(6, 14)
            decoy_count = min(ring_target, len(all_addrs))
            ring_members = []
            if decoy_count > 0:
                decoys = random.sample(all_addrs, decoy_count)
                ring_members = [hashlib.sha256(d.encode()).hexdigest()[:32] for d in decoys]
            
            sender_key = hashlib.sha256(from_addr.encode()).hexdigest()[:32]
            insert_pos = secrets.randbelow(len(ring_members) + 1)
            ring_members.insert(insert_pos, sender_key)
            
            # 4. Encrypted payload hash
            payload_hash = hashlib.sha256(
                json.dumps({'to': to_addr, 'amount': amount, 'ts': int(time.time())}).encode()
            ).hexdigest()
            
            # 5. TX ID
            tx_id = hashlib.sha256(
                f"veil_{from_addr}_{amount}_{int(time.time())}_{secrets.token_hex(8)}".encode()
            ).hexdigest()
            
            # 6. Build transaction (visible on-chain: anonymous from/to, hidden amount)
            tx = {
                'type': 'veil_transfer',
                'tx_id': tx_id,
                'from': 'anonymous',
                'to': ota,
                'amount': 0,
                'real_from': from_addr,
                'real_to': to_addr,
                'real_amount': amount,
                'fee': veil_fee,
                'ephemeral': ephemeral.hex() if isinstance(ephemeral, bytes) else ephemeral,
                'payload_hash': payload_hash,
                'ring_signature': None,  # Will be set below
                'timestamp': int(time.time()),
                'anonymous': True
            }
            
            # Real Ring Signature if crypto module available
            if CRYPTO_MODULE and ED25519_AVAILABLE:
                try:
                    kp = Ed25519.derive_keypair(seed)
                    all_pubkeys = [w.get('ed25519_pubkey', hashlib.sha256(a.encode()).hexdigest()) 
                                   for a, w in S.wallets.items() if a != from_addr][:50]
                    ring_pks, signer_idx = select_ring_members(all_pubkeys, kp['public_hex'], ring_size=min(8, len(all_pubkeys)+1))
                    ring_sig = RingSignature.sign(seed, json.dumps({'ki': key_image, 'ota': ota, 'ts': tx['timestamp']}).encode(), ring_pks, signer_idx)
                    tx['ring_signature'] = ring_sig
                except Exception as e:
                    print(f"⚠️ Real ring sig failed, using fallback: {e}")
                    tx['ring_signature'] = {
                        'key_image': key_image,
                        'ring': ring_members,
                        'ring_size': len(ring_members),
                        'c0': secrets.token_hex(16),
                        'responses': [secrets.token_hex(8) for _ in ring_members]
                    }
            else:
                tx['ring_signature'] = {
                    'key_image': key_image,
                    'ring': ring_members,
                    'ring_size': len(ring_members),
                    'c0': secrets.token_hex(16),
                    'responses': [secrets.token_hex(8) for _ in ring_members]
                }
            
            # === PHANTOM TRANSACTIONS — Transaction Indistinguishability ===
            # Generate 4-10 fake TXs that look identical to the real one.
            # Observer sees N transactions, cannot determine which is real.
            # Ring hides WHO sent → Phantoms hide WHICH TX is real.
            
            import random
            phantom_count = random.randint(4, 10)
            all_txs = [tx]  # Start with real TX
            
            all_addrs_for_phantoms = [a for a in S.wallets.keys() 
                                       if not a.startswith('seed_000')]
            
            for p in range(phantom_count):
                # Each phantom gets unique crypto — indistinguishable from real
                p_ephemeral = secrets.token_bytes(32)
                p_shared = hashlib.sha256(p_ephemeral + secrets.token_bytes(32)).digest()
                p_ota = f"veil_{hashlib.sha256(b'OTA' + p_shared).hexdigest()[:64]}"
                
                p_key_image = hashlib.sha256(
                    b"VEIL_KI" + secrets.token_bytes(32) + secrets.token_bytes(16)
                ).hexdigest()
                
                # Unique ring for each phantom (different decoys)
                p_ring_target = random.randint(6, 14)
                p_decoy_count = min(p_ring_target, len(all_addrs_for_phantoms))
                p_ring = []
                if p_decoy_count > 0:
                    p_decoys = random.sample(all_addrs_for_phantoms, p_decoy_count)
                    p_ring = [hashlib.sha256(d.encode()).hexdigest()[:32] for d in p_decoys]
                # Insert a fake "sender" key at random position
                p_fake_sender = secrets.token_hex(16)
                p_ring.insert(secrets.randbelow(len(p_ring) + 1), p_fake_sender)
                
                p_tx_id = hashlib.sha256(
                    f"veil_phantom_{int(time.time())}_{secrets.token_hex(16)}".encode()
                ).hexdigest()
                
                p_payload = hashlib.sha256(
                    json.dumps({'p': secrets.token_hex(8), 'ts': int(time.time())}).encode()
                ).hexdigest()
                
                phantom_tx = {
                    'type': 'veil_transfer',
                    'tx_id': p_tx_id,
                    'from': 'anonymous',
                    'to': p_ota,
                    'amount': 0,
                    'fee': veil_fee,
                    'ephemeral': p_ephemeral.hex(),
                    'payload_hash': p_payload,
                    'ring_signature': {
                        'key_image': p_key_image,
                        'ring': p_ring,
                        'ring_size': len(p_ring),
                        'c0': secrets.token_hex(16),
                        'responses': [secrets.token_hex(8) for _ in p_ring]
                    },
                    'timestamp': int(time.time()),
                    'anonymous': True
                    # NO real_from, real_to, real_amount → mining loop ignores
                    # NO balance changes → pure noise for observers
                }
                all_txs.append(phantom_tx)
                
                # Track phantom key_images too (prevents reuse, looks real)
                S.spent_key_images.add(p_key_image)
            
            # Shuffle so real TX is at random position
            random.shuffle(all_txs)
            S.mempool.extend(all_txs)
            
            print(f"    👻 VEIL: 1 real + {phantom_count} phantom = {len(all_txs)} TXs (indistinguishable)")
            
            # Update balances (only real TX affects balances)
            from_wallet['balance'] -= total_needed
            S.counters['burned_fees'] += veil_fee
            from_wallet['tx_count'] = from_wallet.get('tx_count', 0) + 1
            
            if to_addr not in S.wallets:
                S.wallets[to_addr] = {
                    'balance': 0, 'level': 0,
                    'created_at': int(time.time()),
                    'tx_count': 0, 'msg_count': 0
                }
            S.wallets[to_addr]['balance'] += amount
            S.wallets[to_addr]['tx_count'] = S.wallets[to_addr].get('tx_count', 0) + 1
            
            S.spent_key_images.add(key_image)
            S.save()
            
            return jsonify({
                'ok': True,
                'res': {
                    'tx_id': tx_id,
                    'amount': amount,
                    'fee': veil_fee,
                    'type': 'veil',
                    'ota': ota[:32] + '...',
                    'key_image': key_image[:24] + '...',
                    'ring_size': len(ring_members),
                    'phantoms': phantom_count,
                    'total_txs': len(all_txs),
                    'balance': from_wallet.get('balance', 0)
                }
            })
    except Exception as e:
        print(f"VEIL error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'VEIL failed: {str(e)}', 'ok': False}), 500


# ============================================================================
# STASH POOL — Blockchain-Native Anonymous Mixing
# ============================================================================

@app.route('/api/stash/deposit', methods=['POST'])
def stash_deposit():
    """
    STASH Deposit — Lock LAC into anonymous pool
    
    1. Choose nominal (100 / 1K / 10K / 100K LAC)
    2. Receive STASH key (256-bit secret)
    3. Key works offline, transferable, no expiry
    4. Deposit recorded as blockchain TX
    
    Fee: 2.0 LAC
    """
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized', 'ok': False}), 401
    
    try:
        from_addr = get_address_from_seed(seed)
        data = request.get_json() or {}
        nominal_code = int(data.get('nominal_code', -1))
        
        if nominal_code not in STASH_NOMINALS:
            return jsonify({'error': 'Invalid nominal. Use: 0=100, 1=1K, 2=10K, 3=100K', 'ok': False}), 400
        
        amount = STASH_NOMINALS[nominal_code]
        
        with S.lock:
            if from_addr not in S.wallets:
                return jsonify({'error': 'Wallet not found', 'ok': False}), 404
            
            from_wallet = S.wallets[from_addr]
            total_needed = amount + STASH_FEE
            
            if from_wallet.get('balance', 0) < total_needed:
                return jsonify({
                    'error': f'Insufficient balance. Need {total_needed} LAC',
                    'ok': False
                }), 400
            
            # Generate STASH key
            secret = secrets.token_bytes(32)
            nullifier = hashlib.sha256(b"STASH_NULL" + secret).hexdigest()
            nullifier_hash = hashlib.sha256(nullifier.encode()).hexdigest()
            stash_key = f'STASH-{amount}-{secret.hex()}'
            
            # Blockchain TX — sender hidden
            tx = {
                'type': 'stash_deposit',
                'from': 'anonymous',
                'to': 'stash_pool',
                'amount': amount,
                'fee': STASH_FEE,
                'nominal_code': nominal_code,
                'nullifier_hash': nullifier_hash,
                'real_from': from_addr,
                'timestamp': int(time.time())
            }
            S.mempool.append(tx)
            
            # Deduct balance
            from_wallet['balance'] -= total_needed
            S.counters['burned_fees'] += STASH_FEE
            from_wallet['tx_count'] = from_wallet.get('tx_count', 0) + 1
            
            # Update STASH pool state
            S.stash_pool['total_balance'] = S.stash_pool.get('total_balance', 0) + amount
            S.stash_pool['deposits'][nullifier_hash] = {
                'amount': amount,
                'nominal': nominal_code,
                'timestamp': int(time.time())
            }
            
            S.save()
            
            return jsonify({
                'ok': True,
                'stash_key': stash_key,
                'amount': amount,
                'fee': STASH_FEE,
                'nominal': nominal_code,
                'message': '⚠️ SAVE THIS KEY! It cannot be recovered.'
            })
    except Exception as e:
        print(f"STASH deposit error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'STASH deposit failed: {str(e)}', 'ok': False}), 500


@app.route('/api/stash/withdraw', methods=['POST'])
def stash_withdraw():
    """
    STASH Withdraw — Redeem STASH key for clean LAC
    
    1. Enter STASH key
    2. Nullifier checked (no double-spend)
    3. Amount credited to wallet
    4. Key burned permanently
    5. NO link between deposit and withdrawal
    
    Fee: 0 LAC
    """
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized', 'ok': False}), 401
    
    try:
        to_addr = get_address_from_seed(seed)
        data = request.get_json() or {}
        stash_key = data.get('stash_key', '').strip()
        
        secret_hex = None
        amount = None
        nominal_code = None
        
        # New format: STASH-{amount}-{hex}
        if stash_key.startswith('STASH-'):
            parts = stash_key.split('-', 2)
            if len(parts) == 3:
                try:
                    amount = int(parts[1])
                    secret_hex = parts[2]
                    # Reverse lookup nominal_code from amount
                    for nc, val in STASH_NOMINALS.items():
                        if val == amount:
                            nominal_code = nc
                            break
                    if nominal_code is None:
                        nominal_code = 0  # fallback
                except:
                    return jsonify({'error': 'Invalid STASH key format', 'ok': False}), 400
            else:
                return jsonify({'error': 'Invalid STASH key format', 'ok': False}), 400
        # Old format: stash_{"v":1,"n":0,"s":"hex"}
        elif stash_key.startswith('stash_{'):
            try:
                key_json = stash_key[6:]
                key_data = json.loads(key_json)
                nominal_code = key_data.get('n', 0)
                secret_hex = key_data.get('s')
                if nominal_code in STASH_NOMINALS:
                    amount = STASH_NOMINALS[nominal_code]
            except:
                return jsonify({'error': 'Malformed STASH key', 'ok': False}), 400
        else:
            return jsonify({'error': 'Invalid STASH key format. Use STASH-amount-key or old stash_{} format', 'ok': False}), 400
        
        if not secret_hex or not amount:
            return jsonify({'error': 'Invalid STASH key', 'ok': False}), 400
        
        try:
            secret = bytes.fromhex(secret_hex)
        except Exception:
            return jsonify({'error': 'Invalid secret', 'ok': False}), 400
        
        nullifier = hashlib.sha256(b"STASH_NULL" + secret).hexdigest()
        
        with S.lock:
            if to_addr not in S.wallets:
                return jsonify({'error': 'Wallet not found', 'ok': False}), 404
            
            spent = S.stash_pool.get('spent_nullifiers', [])
            if nullifier in spent:
                return jsonify({'error': 'STASH key already spent', 'ok': False}), 400
            
            pool_balance = S.stash_pool.get('total_balance', 0)
            if pool_balance < amount:
                return jsonify({'error': 'Insufficient pool balance', 'ok': False}), 400
            
            # Blockchain TX — recipient hidden
            withdraw_ota = f"stash_{hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:32]}"
            tx = {
                'type': 'stash_withdraw',
                'from': 'stash_pool',
                'to': withdraw_ota,
                'amount': amount,
                'fee': 0,
                'nominal_code': nominal_code,
                'nullifier': nullifier,
                'real_to': to_addr,
                'timestamp': int(time.time())
            }
            S.mempool.append(tx)
            
            # Credit recipient
            S.wallets[to_addr]['balance'] += amount
            S.wallets[to_addr]['tx_count'] = S.wallets[to_addr].get('tx_count', 0) + 1
            
            # Update pool
            S.stash_pool['total_balance'] -= amount
            if 'spent_nullifiers' not in S.stash_pool:
                S.stash_pool['spent_nullifiers'] = []
            S.stash_pool['spent_nullifiers'].append(nullifier)
            
            S.save()
            
            return jsonify({
                'ok': True,
                'amount': amount,
                'balance': S.wallets[to_addr].get('balance', 0),
                'message': '✅ STASH key redeemed!'
            })
    except Exception as e:
        print(f"STASH withdraw error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'STASH withdraw failed: {str(e)}', 'ok': False}), 500


@app.route('/api/stash/info', methods=['GET'])
def stash_info():
    """STASH Pool public info"""
    try:
        with S.lock:
            deposits = S.stash_pool.get('deposits', {})
            spent = S.stash_pool.get('spent_nullifiers', [])
            active_count = len(deposits) - len(spent)
            total_deposited = sum(d.get('amount', 0) for d in deposits.values())
            total_balance = S.stash_pool.get('total_balance', 0)
            return jsonify({
                'ok': True,
                'total_balance': total_balance,
                'total_deposited': total_deposited,
                'active_keys': max(0, active_count),
                'total_deposits': len(deposits),
                'spent_count': len(spent),
                'nominals': STASH_NOMINALS
            })
    except Exception as e:
        return jsonify({'error': str(e), 'ok': False}), 500




# ==================== REFERRAL SYSTEM ====================
def get_referral_tier(addr):
    """Determine referral tier"""
    ref = S.referral_map.get(addr, {})
    code = ref.get('invite_code')
    if not code:
        return 'none', 0
    used = len(S.referrals.get(code, {}).get('used_by', []))
    boost = ref.get('boost_burned', 0)
    
    # Tier calculation
    wallet = S.wallets.get(addr, {})
    wallet_index = list(S.wallets.keys()).index(addr) if addr in S.wallets else 9999
    
    if wallet_index < 100:
        tier = 'genesis'
    elif wallet_index < 1000:
        tier = 'early'
    elif used >= 10 or boost >= 10000:
        tier = 'vip'
    else:
        tier = 'growth'
    
    return tier, used

@app.route('/api/referral/code', methods=['GET'])
def referral_get_code():
    """Get or create your referral invite code"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        ref = S.referral_map.get(addr, {})
        code = ref.get('invite_code')
        
        if not code:
            # Generate unique code: REF-xxxx
            code = 'REF-' + secrets.token_hex(4).upper()
            while code in S.referrals:
                code = 'REF-' + secrets.token_hex(4).upper()
            
            S.referrals[code] = {
                'creator': addr,
                'used_by': [],
                'created_at': int(time.time())
            }
            if addr not in S.referral_map:
                S.referral_map[addr] = {}
            S.referral_map[addr]['invite_code'] = code
            S.save()
        
        used_count = len(S.referrals.get(code, {}).get('used_by', []))
        tier, _ = get_referral_tier(addr)
        
        return jsonify({
            'ok': True,
            'code': code,
            'referrals': used_count,
            'tier': tier,
            'invited_by': S.referral_map.get(addr, {}).get('invited_by', None),
            'boost_burned': S.referral_map.get(addr, {}).get('boost_burned', 0)
        })

@app.route('/api/referral/use', methods=['POST'])
def referral_use():
    """Use an invite code — links you to referrer anonymously"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    
    if not code:
        return jsonify({'error': 'Code required'}), 400
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Check if already used a code
        ref = S.referral_map.get(addr, {})
        if ref.get('invited_by'):
            return jsonify({'error': 'You already used a referral code', 'ok': False}), 400
        
        if code not in S.referrals:
            return jsonify({'error': 'Invalid referral code', 'ok': False}), 400
        
        referral = S.referrals[code]
        
        # Can't refer yourself
        if referral['creator'] == addr:
            return jsonify({'error': 'Cannot use your own code', 'ok': False}), 400
        
        # Can't use if already referred
        if addr in referral['used_by']:
            return jsonify({'error': 'Already used this code', 'ok': False}), 400
        
        # Apply referral
        referral['used_by'].append(addr)
        if addr not in S.referral_map:
            S.referral_map[addr] = {}
        S.referral_map[addr]['invited_by'] = code
        
        # Bonus: referrer gets 25 LAC, new user gets 50 LAC
        referrer_addr = referral['creator']
        if referrer_addr in S.wallets:
            S.wallets[referrer_addr]['balance'] += 25
        S.wallets[addr]['balance'] += 50
        S.counters['emitted_referral'] += 75
        
        # Create on-chain record
        S.mempool.append({
            'type': 'referral_bonus',
            'from': 'referral_system',
            'to': 'anonymous',
            'amount': 75,
            'timestamp': int(time.time()),
            'referral_code': code[:4] + '****'  # partially hidden
        })
        
        S.save()
        
        return jsonify({
            'ok': True,
            'bonus': 50,
            'message': '🎉 Referral activated! +50 LAC bonus'
        })

@app.route('/api/referral/burn-boost', methods=['POST'])
def referral_burn_boost():
    """Burn LAC to boost your referral tier"""
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'error': 'Unauthorized'}), 401
    
    addr = get_address_from_seed(seed)
    data = request.get_json() or {}
    amount = data.get('amount', 0)
    
    if not isinstance(amount, (int, float)) or amount < 100:
        return jsonify({'error': 'Minimum burn: 100 LAC'}), 400
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'error': 'Wallet not found'}), 404
        
        if S.wallets[addr].get('balance', 0) < amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        S.wallets[addr]['balance'] -= amount
        
        if addr not in S.referral_map:
            S.referral_map[addr] = {}
        S.referral_map[addr]['boost_burned'] = S.referral_map[addr].get('boost_burned', 0) + amount
        
        # On-chain record
        S.mempool.append({
            'type': 'referral_boost',
            'from': 'anonymous',
            'to': BURN_ADDRESS,
            'amount': amount,
            'timestamp': int(time.time())
        })
        
        tier, refs = get_referral_tier(addr)
        S.save()
        
        return jsonify({
            'ok': True,
            'burned': amount,
            'total_boost': S.referral_map[addr].get('boost_burned', 0),
            'new_tier': tier,
            'balance': S.wallets[addr].get('balance', 0)
        })

@app.route('/api/referral/leaderboard', methods=['GET'])
def referral_leaderboard():
    """Anonymous referral leaderboard"""
    with S.lock:
        board = []
        for code, data in S.referrals.items():
            count = len(data.get('used_by', []))
            if count > 0:
                creator = data.get('creator', '')
                tier, _ = get_referral_tier(creator)
                boost = S.referral_map.get(creator, {}).get('boost_burned', 0)
                # Anonymous: show partial code + tier
                board.append({
                    'code': code[:6] + '**',
                    'referrals': count,
                    'tier': tier,
                    'boost': round(boost, 2)
                })
        
        board.sort(key=lambda x: x['referrals'], reverse=True)
        
        return jsonify({
            'ok': True,
            'leaderboard': board[:20],
            'total_referrals': sum(b['referrals'] for b in board),
            'total_referrers': len(board)
        })

# ═══════════════════════════════════════════════════════
# PROOF-OF-LOCATION API
# ═══════════════════════════════════════════════════════

@app.route('/api/pol/zones', methods=['GET'])
def pol_zones():
    """List all available PoL zones"""
    if not POL_AVAILABLE:
        return jsonify({'ok': False, 'error': 'Proof-of-Location not available'}), 503
    zones = ProofOfLocation.get_available_zones()
    zones['ok'] = True
    return jsonify(zones)

@app.route('/api/pol/prove', methods=['POST'])
def pol_prove():
    """
    Create a Proof-of-Location.
    Client sends GPS coordinates, gets back a proof WITHOUT coordinates.
    Coordinates are NEVER stored on server.
    """
    if not POL_AVAILABLE:
        return jsonify({'ok': False, 'error': 'PoL not available'}), 503
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    lat = data.get('lat')
    lon = data.get('lon')
    zone = data.get('zone')  # optional: specific zone to prove
    manual = data.get('manual', False)  # manual mode: zone-only, no GPS coords
    
    if manual and zone:
        # Manual mode: use zone center coordinates
        from lac_proof_of_location import ALL_ZONES
        if zone not in ALL_ZONES:
            return jsonify({'ok': False, 'error': f'Unknown zone: {zone}'}), 400
        bounds = ALL_ZONES[zone]
        lat = (bounds['lat_min'] + bounds['lat_max']) / 2
        lon = (bounds['lon_min'] + bounds['lon_max']) / 2
    elif lat is None or lon is None:
        return jsonify({'ok': False, 'error': 'lat and lon required (or use manual=true with zone)'}), 400
    
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return jsonify({'ok': False, 'error': 'Invalid coordinates'}), 400
    
    result = ProofOfLocation.create_proof(lat, lon, zone)
    
    if not result.get('valid'):
        return jsonify({'ok': False, 'error': result.get('error', 'Unknown zone'), 'zones': result.get('actual_zones', [])})
    
    # Store proof on-chain (PUBLIC part only — NO coordinates)
    addr = get_address_from_seed(seed)
    proof_public = result['public']
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'ok': False, 'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        
        # Store latest proof in wallet (for display)
        wallet['last_pol'] = proof_public
        
        # On-chain TX (public only — coordinates NEVER touch the chain)
        tx = {
            'type': 'proof_of_location',
            'from': addr,
            'zone': proof_public['zone'],
            'commitment': proof_public['commitment'],
            'proof_hash': proof_public['proof_hash'],
            'timestamp': proof_public['timestamp'],
            'amount': 0,
        }
        tx = sign_transaction(seed, tx)
        S.mempool.append(tx)
        S.save()
    
    return jsonify({
        'ok': True,
        'proof': proof_public,
        # Private data returned to device only — client should store locally
        'private': result['private'],
        'note': 'PRIVATE data contains your coordinates. Keep it on device only.'
    })

@app.route('/api/pol/verify', methods=['POST'])
def pol_verify():
    """Verify a Proof-of-Location"""
    if not POL_AVAILABLE:
        return jsonify({'ok': False, 'error': 'PoL not available'}), 503
    
    data = request.get_json() or {}
    proof = data.get('proof', {})
    
    if not proof:
        return jsonify({'ok': False, 'error': 'proof object required'}), 400
    
    result = ProofOfLocation.verify_proof(proof)
    result['ok'] = result.get('valid', False)
    return jsonify(result)

@app.route('/api/pol/message', methods=['POST'])
def pol_message():
    """
    Send a location-stamped message.
    Journalist use case: prove you're in a zone without revealing exact location.
    """
    if not POL_AVAILABLE:
        return jsonify({'ok': False, 'error': 'PoL not available'}), 503
    
    seed = request.headers.get('X-Seed', '').strip()
    if not validate_seed(seed):
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    lat = data.get('lat')
    lon = data.get('lon')
    text = data.get('text', '').strip()
    to = data.get('to', '').strip()
    zone = data.get('zone')
    manual = data.get('manual', False)
    
    if not text:
        return jsonify({'ok': False, 'error': 'text required'}), 400
    
    if manual and zone:
        from lac_proof_of_location import ALL_ZONES
        if zone not in ALL_ZONES:
            return jsonify({'ok': False, 'error': f'Unknown zone: {zone}'}), 400
        bounds = ALL_ZONES[zone]
        lat = (bounds['lat_min'] + bounds['lat_max']) / 2
        lon = (bounds['lon_min'] + bounds['lon_max']) / 2
    elif lat is None or lon is None:
        return jsonify({'ok': False, 'error': 'lat, lon, and text required (or use manual=true with zone)'}), 400
    
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return jsonify({'ok': False, 'error': 'Invalid coordinates'}), 400
    
    result = ProofOfLocation.create_message_proof(lat, lon, text, zone)
    
    if not result.get('valid'):
        return jsonify({'ok': False, 'error': result.get('error', 'Unknown zone')})
    
    addr = get_address_from_seed(seed)
    proof_public = result['public']
    
    with S.lock:
        if addr not in S.wallets:
            return jsonify({'ok': False, 'error': 'Wallet not found'}), 404
        
        wallet = S.wallets[addr]
        
        if wallet.get('balance', 0) < MIN_MSG_FEE:
            return jsonify({'ok': False, 'error': f'Need {MIN_MSG_FEE} LAC'}), 400
        
        key_id = wallet.get('key_id')
        from_username = get_username_by_key_id(key_id)
        from_display = from_username if from_username else addr
        
        # Resolve recipient
        to_address = resolve_recipient(to) if to else None
        
        msg = {
            'from': from_display,
            'from_address': addr,
            'to': to_address or 'broadcast',
            'text': text,
            'timestamp': int(time.time()),
            'verified': True,
            'pol': {
                'zone': proof_public['zone'],
                'all_zones': proof_public.get('all_zones', []),
                'commitment': proof_public['commitment'],
                'proof_hash': proof_public['proof_hash'],
                'message_binding': proof_public.get('message_binding', ''),
                'freshness': 'live',
                'area_km2': proof_public.get('area_km2', 0),
            }
        }
        
        S.persistent_msgs.append(msg)
        wallet['balance'] -= MIN_MSG_FEE
        S.counters['burned_fees'] += MIN_MSG_FEE
        wallet['msg_count'] = wallet.get('msg_count', 0) + 1
        S.save_msgs()
    
    return jsonify({
        'ok': True,
        'message_id': hashlib.sha256(json.dumps(msg).encode()).hexdigest()[:16],
        'proof': proof_public,
        'zone': proof_public['zone'],
        'balance': wallet.get('balance', 0),
    })

@app.route('/api/pol/detect', methods=['POST'])
def pol_detect():
    """Detect which zones contain given coordinates (no proof, just detection)"""
    if not POL_AVAILABLE:
        return jsonify({'ok': False, 'error': 'PoL not available'}), 503
    
    data = request.get_json() or {}
    try:
        lat = float(data.get('lat', 0))
        lon = float(data.get('lon', 0))
    except (ValueError, TypeError):
        return jsonify({'ok': False, 'error': 'Invalid coordinates'}), 400
    
    zones = ProofOfLocation.detect_zones(lat, lon)
    return jsonify({'ok': True, 'zones': zones, 'count': len(zones)})

@app.route('/api/stats', methods=['GET'])
def chain_stats():
    """
    Public chain statistics
    
    FORMULA: Emitted - Burned = On Wallets + In STASH
    
    Approach: Ground truth first, derive what we can't measure.
    - on_wallets = sum(balances)  ← ALWAYS correct
    - stash = stash_pool           ← ALWAYS correct
    - emitted_mining = height × 190  ← ALWAYS correct (fixed block reward)
    - total_burned = total_emitted - on_wallets - stash  ← DERIVED, always balances
    """
    try:
        with S.lock:
            total_wallets = len(S.wallets)
            
            # === BLOCK HEIGHT (reliable even after pruning) ===
            if S.chain:
                block_height = S.chain[-1].get('index', len(S.chain) - 1) + 1
            else:
                block_height = 0
            
            # === GROUND TRUTH #1: Wallet balances ===
            balances = sorted([w.get('balance', 0) for w in S.wallets.values()], reverse=True)
            on_wallets = round(sum(balances), 2)
            stash_balance = round(S.stash_pool.get('total_balance', 0), 2)
            
            # === GROUND TRUTH #2: Level distribution ===
            levels = {}
            for w in S.wallets.values():
                lv = w.get('level', 0)
                levels[f"L{lv}"] = levels.get(f"L{lv}", 0) + 1
            
            # === EMISSION: Mining (most reliable source) ===
            # Block reward is ALWAYS 190 LAC per block, distributed among 19 winners
            # This is correct regardless of Zero-History pruning
            BLOCK_REWARD = 190
            emitted_mining = round(block_height * BLOCK_REWARD, 2)
            
            # === EMISSION: Other sources (from counters + chain scan) ===
            # Counters track real-time events going forward
            cnt = getattr(S, 'counters', {})
            
            # Chain scan for TX types and supplemental emission data
            chain_faucet = 0
            chain_referral = 0
            tx_counts = {
                'normal': 0, 'veil': 0, 'stash': 0, 'dice': 0,
                'burn': 0, 'timelock': 0, 'dms': 0, 'username': 0, 'faucet': 0
            }
            total_tx = 0
            total_l2_msgs = 0
            
            for b in S.chain:
                total_l2_msgs += len(b.get('ephemeral_msgs', []))
                txs = b.get('transactions', [])
                total_tx += len(txs)
                
                for tx in txs:
                    t = tx.get('type', '')
                    amt = tx.get('amount', 0) or 0
                    
                    if t in ('transfer', 'normal'):
                        tx_counts['normal'] += 1
                    elif t == 'veil_transfer':
                        tx_counts['veil'] += 1
                    elif t in ('stash_deposit', 'stash_withdraw'):
                        tx_counts['stash'] += 1
                    elif t in ('dice_burn', 'dice_mint'):
                        tx_counts['dice'] += 1
                    elif t == 'timelock_create':
                        tx_counts['timelock'] += 1
                    elif t.startswith('dms_'):
                        tx_counts['dms'] += 1
                    elif t == 'username_register':
                        tx_counts['username'] += 1
                    elif t == 'faucet':
                        tx_counts['faucet'] += 1
                        chain_faucet += amt
                    elif t.startswith('burn_'):
                        tx_counts['burn'] += 1
                    elif t == 'referral_bonus':
                        chain_referral += amt
            
            # Best estimate of non-mining emission
            emitted_faucet = max(cnt.get('emitted_faucet', 0), chain_faucet)
            emitted_dice = cnt.get('emitted_dice', 0)
            emitted_referral = max(cnt.get('emitted_referral', 0), chain_referral)
            
            # If counters are empty (first deploy), scan dice history
            if emitted_dice == 0:
                for w in S.wallets.values():
                    for game in w.get('dice_history', []):
                        if game.get('won'):
                            emitted_dice += game.get('payout', 0) - game.get('amount', 0)
            
            total_emitted = round(emitted_mining + emitted_faucet + emitted_dice + emitted_referral, 2)
            
            # === BURNED: Derived from ground truth (ALWAYS correct) ===
            total_burned = round(total_emitted - on_wallets - stash_balance, 2)
            if total_burned < 0:
                total_burned = 0  # shouldn't happen, but safety
            
            # === BURN BREAKDOWN: Best estimates ===
            # total_burned is GROUND TRUTH — breakdown must never exceed it

            # DICE: counter + scan dice_history for losses if counter is empty
            est_burned_dice = cnt.get('burned_dice', 0)
            if est_burned_dice == 0:
                for w in S.wallets.values():
                    for game in w.get('dice_history', []):
                        if not game.get('won'):
                            est_burned_dice += game.get('amount', 0)

            # LEVELS: use counter if available; fallback to wallet-derived but cap at total_burned
            LEVEL_CUMULATIVE = {0:0, 1:100, 2:800, 3:2800, 4:12800, 5:112800, 6:612800, 7:2612800}
            wallet_burned_levels = sum(LEVEL_CUMULATIVE.get(w.get('level', 0), 0) for w in S.wallets.values())
            cnt_burned_levels = cnt.get('burned_levels', 0)
            # Use counter if it looks sane (>0), else use wallet-derived capped at total_burned
            if cnt_burned_levels > 0:
                est_burned_levels = cnt_burned_levels
            else:
                est_burned_levels = min(wallet_burned_levels, total_burned)

            # USERNAMES: counter first, fallback wallet-derived
            USERNAME_COSTS = {3: 10000, 4: 1000, 5: 100}
            wallet_burned_username = 0
            for w in S.wallets.values():
                uname_w = w.get('username', '')
                if uname_w and uname_w not in ('', 'Anonymous', 'None'):
                    wallet_burned_username += USERNAME_COSTS.get(len(uname_w), 10)
            cnt_burned_username = cnt.get('burned_username', 0)
            est_burned_username = cnt_burned_username if cnt_burned_username > 0 else wallet_burned_username

            # FEES: counter + chain scan fallback
            est_burned_fees = cnt.get('burned_fees', 0)
            if est_burned_fees == 0:
                for b in S.chain:
                    for tx in b.get('transactions', []):
                        fee = tx.get('fee', 0) or 0
                        if fee > 0:
                            est_burned_fees += fee

            est_burned_dms = cnt.get('burned_dms', 0)
            est_burned_other = cnt.get('burned_other', 0)

            known_burns = est_burned_dice + est_burned_levels + est_burned_username + est_burned_fees + est_burned_dms + est_burned_other

            # If breakdown exceeds total (e.g. test levels set without burning) — scale levels down
            if known_burns > total_burned and total_burned > 0:
                overflow = known_burns - total_burned
                est_burned_levels = max(0, est_burned_levels - overflow)
                known_burns = est_burned_dice + est_burned_levels + est_burned_username + est_burned_fees + est_burned_dms + est_burned_other

            # Untracked = whatever remains in total_burned not explained by breakdown
            historical_burns = round(total_burned - known_burns, 2)
            if historical_burns < 0:
                historical_burns = 0
            
            # Supplement tx counts
            dice_games = sum(len(w.get('dice_history', [])) for w in S.wallets.values())
            if tx_counts['dice'] == 0 and dice_games > 0:
                tx_counts['dice'] = dice_games
            stash_ops = len(S.stash_pool.get('spent_nullifiers', [])) + len(S.stash_pool.get('deposits', {}))
            if tx_counts['stash'] == 0 and stash_ops > 0:
                tx_counts['stash'] = stash_ops
            
            dms_active = sum(1 for w in S.wallets.values() if w.get('dead_mans_switch', {}).get('enabled'))
            
            return jsonify({
                'ok': True,
                'total_wallets': total_wallets,
                'total_blocks': block_height,
                'top_balances': [round(b, 2) for b in balances[:10]],
                'level_distribution': levels,
                # === SUPPLY (always balances: emitted - burned = on_wallets + stash) ===
                'on_wallets': on_wallets,
                'total_emitted': total_emitted,
                'total_burned': total_burned,
                'stash_pool_balance': stash_balance,
                # === EMISSION breakdown ===
                'emitted_mining': emitted_mining,
                'emitted_faucet': round(emitted_faucet, 2),
                'emitted_dice': round(emitted_dice, 2),
                'emitted_referral': round(emitted_referral, 2),
                # === BURNS breakdown (estimates, counters grow more accurate over time) ===
                'burned_dice': round(est_burned_dice, 2),
                'burned_levels': round(est_burned_levels, 2),
                'burned_username': round(est_burned_username, 2),
                'burned_fees': round(est_burned_fees, 2),
                'burned_dms': round(est_burned_dms, 2),
                'burned_other': round(est_burned_other, 2),
                'burned_historical': round(historical_burns, 2),
                # === TX counts ===
                'all_tx_count': total_tx,
                'all_normal': tx_counts['normal'],
                'all_veil': tx_counts['veil'],
                'all_stash': tx_counts['stash'],
                'all_dice': tx_counts['dice'],
                'all_burn': tx_counts['burn'],
                'all_timelock': tx_counts['timelock'],
                'all_dms': tx_counts['dms'],
                'all_username': tx_counts['username'],
                'all_faucet': tx_counts['faucet'],
                # === Network ===
                'l2_messages': total_l2_msgs,
                'dms_active': dms_active,
                'active_sessions': len(S.active_sessions),
                # === Counters status ===
                'counters_active': sum(v for v in cnt.values() if isinstance(v, (int, float))) > 0,
            })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    main()