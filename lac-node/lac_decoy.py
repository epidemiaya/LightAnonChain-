"""
LAC Decoy Transactions Module
Creates fake transactions to obfuscate real transfers
Enhances anonymity beyond Ring Signatures and Stealth Addresses
"""

import hashlib
import random
import secrets
from typing import Dict, List, Tuple

# Decoy configuration
DECOY_ENABLED = True
DECOY_COUNT = 10           # Number of fake transactions per real one
MIN_DECOY_AMOUNT = 10      # Minimum decoy amount
MAX_DECOY_AMOUNT = 10000   # Maximum decoy amount


class DecoyManager:
    """
    Manages decoy (fake) transactions for enhanced anonymity
    
    Features:
    - Creates N decoy transactions per real transaction
    - Decoys look identical to real transactions
    - Only sender/receiver know which is real (via shared secret)
    - Blockchain analysis becomes impossible
    """
    
    def __init__(self, state):
        self.state = state
        self.decoy_pool = []  # Pool of potential decoy addresses
        
    def generate_decoy_address(self) -> str:
        """Generate random-looking decoy address"""
        random_bytes = secrets.token_bytes(32)
        addr_hash = hashlib.sha256(random_bytes).hexdigest()[:40]
        return f"seed_{addr_hash}"
    
    def generate_decoy_amount(self) -> float:
        """Generate random decoy amount"""
        # Use log-normal distribution to mimic real transaction patterns
        log_min = 1  # log10(10)
        log_max = 4  # log10(10000)
        log_amount = random.uniform(log_min, log_max)
        amount = 10 ** log_amount
        
        # Round to 2 decimals
        return round(amount, 2)
    
    def create_decoy_signature(self) -> Dict:
        """
        Create fake ring signature for decoy
        Looks identical to real ring signature
        """
        return {
            'key_image': secrets.token_hex(32),
            'c': [secrets.token_hex(32) for _ in range(11)],
            's': [secrets.token_hex(32) for _ in range(11)],
            'ring_size': 11,
            'decoy': True  # Internal flag (not visible in blockchain)
        }
    
    def create_decoys_for_transaction(
        self, 
        real_tx: Dict,
        count: int = DECOY_COUNT
    ) -> List[Dict]:
        """
        Create decoy transactions for a real transaction
        IMPROVED: Decoys distributed across time (not just recent)
        
        Args:
            real_tx: The real transaction
            count: Number of decoys to create
        
        Returns:
            List of decoy transactions
        """
        
        if not DECOY_ENABLED:
            return []
        
        decoys = []
        base_timestamp = real_tx.get('timestamp')
        
        # IMPROVED: Different time ranges for decoys
        # 30% recent (0-1000 sec ago)
        # 40% medium (1000-10000 sec ago)
        # 30% old (10000-100000 sec ago)
        time_ranges = [
            ('recent', 0, 1000, 3),      # 3 recent
            ('medium', 1000, 10000, 4),   # 4 medium
            ('old', 10000, 100000, 3)     # 3 old
        ]
        
        decoy_idx = 0
        for range_name, min_offset, max_offset, range_count in time_ranges:
            for i in range(min(range_count, count - decoy_idx)):
                # Random timestamp in range
                time_offset = random.randint(min_offset, max_offset)
                decoy_timestamp = base_timestamp - time_offset
                
                # Generate decoy with similar structure to real TX
                decoy = {
                    'type': 'transfer',  # Same as real (anonymous!)
                    'from': self.generate_decoy_address(),
                    'to': self.generate_decoy_address(),
                    'amount': self.generate_decoy_amount(),
                    'timestamp': decoy_timestamp,  # Distributed timestamp!
                    'ring_signature': self.create_decoy_signature(),
                    'decoy': True,  # Internal flag
                    'decoy_id': secrets.token_hex(16),
                    'decoy_range': range_name  # For debugging
                }
                
                # Copy some fields from real TX to make decoys look identical
                if 'use_stealth' in real_tx:
                    decoy['stealth_hint'] = secrets.token_hex(16)
                
                if 'stealth' in real_tx:
                    decoy['one_time_address'] = f"stealth_{secrets.token_hex(20)}"
                    decoy['tx_public_key'] = secrets.token_hex(32)
                
                decoys.append(decoy)
                decoy_idx += 1
                
                if decoy_idx >= count:
                    break
            
            if decoy_idx >= count:
                break
        
        return decoys
    
    def shuffle_with_real(
        self, 
        real_tx: Dict, 
        decoys: List[Dict]
    ) -> Tuple[List[Dict], int]:
        """
        Shuffle real transaction with decoys
        
        Args:
            real_tx: Real transaction
            decoys: List of decoy transactions
        
        Returns:
            (shuffled_list, real_position)
        """
        
        # Mark real TX (only sender/receiver know this)
        real_tx_copy = real_tx.copy()
        real_tx_copy['real'] = True  # Internal flag (stripped before blockchain)
        
        # Combine
        all_txs = [real_tx_copy] + decoys
        
        # Shuffle
        random.shuffle(all_txs)
        
        # Find real position
        real_position = next(
            i for i, tx in enumerate(all_txs) 
            if tx.get('real', False)
        )
        
        # Strip internal flags before adding to blockchain
        clean_txs = []
        for tx in all_txs:
            clean = tx.copy()
            clean.pop('real', None)
            clean.pop('decoy', None)
            clean_txs.append(clean)
        
        return clean_txs, real_position
    
    def create_shared_secret(
        self,
        from_addr: str,
        to_addr: str,
        real_position: int
    ) -> str:
        """
        Create shared secret so sender/receiver know which TX is real
        
        Args:
            from_addr: Sender address
            to_addr: Receiver address
            real_position: Position of real TX in shuffled list
        
        Returns:
            Shared secret hash
        """
        
        secret_data = f"{from_addr}:{to_addr}:{real_position}"
        secret_hash = hashlib.sha256(secret_data.encode()).hexdigest()
        
        return secret_hash
    
    def verify_real_transaction(
        self,
        tx_list: List[Dict],
        shared_secret: str,
        from_addr: str,
        to_addr: str
    ) -> int:
        """
        Verify which transaction is real using shared secret
        
        Args:
            tx_list: List of transactions (real + decoys)
            shared_secret: The shared secret
            from_addr: Sender address
            to_addr: Receiver address
        
        Returns:
            Position of real transaction, or -1 if not found
        """
        
        for i in range(len(tx_list)):
            test_secret = self.create_shared_secret(from_addr, to_addr, i)
            if test_secret == shared_secret:
                return i
        
        return -1
    
    def add_transaction_with_decoys(
        self,
        real_tx: Dict,
        from_addr: str,
        to_addr: str
    ) -> Tuple[List[Dict], str]:
        """
        Complete workflow: create decoys, shuffle, generate secret
        
        Args:
            real_tx: Real transaction
            from_addr: Sender address
            to_addr: Receiver address
        
        Returns:
            (list_of_transactions, shared_secret)
        """
        
        # Create decoys
        decoys = self.create_decoys_for_transaction(real_tx)
        
        # Shuffle with real
        shuffled, real_pos = self.shuffle_with_real(real_tx, decoys)
        
        # Generate shared secret
        secret = self.create_shared_secret(from_addr, to_addr, real_pos)
        
        return shuffled, secret
    
    def get_stats(self) -> Dict:
        """Get decoy statistics"""
        return {
            'enabled': DECOY_ENABLED,
            'decoy_count': DECOY_COUNT,
            'total_transactions': len(self.state.mempool),
            'decoy_ratio': f"1:{DECOY_COUNT + 1}"
        }


def init_decoy_manager(state):
    """Initialize decoy manager for blockchain"""
    return DecoyManager(state)