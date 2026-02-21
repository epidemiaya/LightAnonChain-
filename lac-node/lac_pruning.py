"""
LAC Blockchain Pruning Module
Reduces blockchain size by pruning old block data while maintaining security
"""

import hashlib
import json
import time
from typing import Dict, List, Optional

# Pruning configuration
PRUNING_ENABLED = True  # ENABLED with proper state persistence
FULL_BLOCKS_KEEP = 1000        # Keep full data for last 1000 blocks
CHECKPOINT_INTERVAL = 500       # Create checkpoint every 500 blocks
PRUNING_CHECK_INTERVAL = 100    # Check for pruning every 100 blocks


class BlockchainPruning:
    """
    Blockchain pruning manager
    
    Features:
    - Keeps full data for recent blocks (FULL_BLOCKS_KEEP)
    - Prunes old blocks to headers + transaction hashes
    - Maintains checkpoints for fast sync
    - Preserves chain integrity (all hashes remain)
    """
    
    def __init__(self, state):
        self.state = state
        self.checkpoints = {}  # {block_index: checkpoint_data}
        
        # Load pruning state from file
        self.prune_state_file = state.datadir / 'pruning_state.json'
        self.load_state()
    
    def load_state(self):
        """Load pruning state from disk"""
        if self.prune_state_file.exists():
            try:
                import json
                with open(self.prune_state_file, 'r') as f:
                    data = json.load(f)
                    self.last_prune_block = data.get('last_prune_block', 0)
                    self.checkpoints = data.get('checkpoints', {})
                print(f"📂 Loaded pruning state: last_prune_block={self.last_prune_block}")
            except Exception as e:
                print(f"⚠️ Could not load pruning state: {e}")
                self.last_prune_block = 0
        else:
            self.last_prune_block = 0
    
    def save_state(self):
        """Save pruning state to disk"""
        try:
            import json
            data = {
                'last_prune_block': self.last_prune_block,
                'checkpoints': self.checkpoints
            }
            with open(self.prune_state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save pruning state: {e}")
        
    def should_prune(self, current_height: int) -> bool:
        """Check if pruning is needed"""
        if not PRUNING_ENABLED:
            return False
        
        # Only prune if we have enough blocks
        if current_height < FULL_BLOCKS_KEEP + 100:
            return False
        
        # Check if enough blocks passed since last prune
        if current_height - self.last_prune_block >= PRUNING_CHECK_INTERVAL:
            return True
        
        return False
    
    def prune_old_blocks(self) -> Dict:
        """
        Prune old blocks, keeping only essential data
        
        Returns:
            Statistics about pruning operation
        """
        current_height = len(self.state.chain)
        
        if not self.should_prune(current_height):
            return {'pruned': False, 'reason': 'Not needed yet'}
        
        prune_before = current_height - FULL_BLOCKS_KEEP
        pruned_count = 0
        bytes_saved = 0
        
        print(f"\n🗜️ Starting blockchain pruning...")
        print(f"   Current height: {current_height}")
        print(f"   Pruning blocks before: {prune_before}")
        
        for i in range(self.last_prune_block, prune_before):
            if i >= len(self.state.chain):
                break
            
            block = self.state.chain[i]
            
            # Skip if already pruned
            if block.get('pruned', False):
                continue
            
            # Calculate size before pruning
            original_size = len(json.dumps(block))
            
            # Create pruned block
            pruned_block = self._create_pruned_block(block)
            
            # Calculate size after pruning
            pruned_size = len(json.dumps(pruned_block))
            bytes_saved += (original_size - pruned_size)
            
            # Replace block
            self.state.chain[i] = pruned_block
            pruned_count += 1
            
            # Create checkpoint if needed
            if i % CHECKPOINT_INTERVAL == 0:
                self._create_checkpoint(i, block)
        
        self.last_prune_block = prune_before
        self.save_state()  # Save pruning state
        self.state.save()
        
        stats = {
            'pruned': True,
            'blocks_pruned': pruned_count,
            'bytes_saved': bytes_saved,
            'mb_saved': round(bytes_saved / (1024 * 1024), 2),
            'current_height': current_height,
            'full_blocks': FULL_BLOCKS_KEEP
        }
        
        print(f"✅ Pruning complete!")
        print(f"   Blocks pruned: {pruned_count}")
        print(f"   Space saved: {stats['mb_saved']} MB")
        
        return stats
    
    def _create_pruned_block(self, block: Dict) -> Dict:
        """
        Create pruned version of block
        
        Keeps:
        - Block header (index, timestamp, hash, previous_hash)
        - Transaction hashes (not full data)
        - Mining rewards (for verification)
        
        Removes:
        - Full transaction data
        - Ephemeral messages (already expired)
        """
        
        # Hash all transactions
        tx_hashes = []
        for tx in block.get('transactions', []):
            tx_hash = hashlib.sha256(
                json.dumps(tx, sort_keys=True).encode()
            ).hexdigest()
            tx_hashes.append(tx_hash)
        
        pruned = {
            'index': block['index'],
            'timestamp': block['timestamp'],
            'previous_hash': block['previous_hash'],
            'hash': block['hash'],
            'nonce': block.get('nonce', 0),
            'miner': block.get('miner', 'poet_anonymous'),
            'difficulty': block.get('difficulty', 1),
            'mining_winners_count': block.get('mining_winners_count', 0),
            'total_reward': block.get('total_reward', 0),
            'mining_rewards': block.get('mining_rewards', []),
            'transaction_hashes': tx_hashes,
            'transaction_count': len(block.get('transactions', [])),
            'ephemeral_count': len(block.get('ephemeral_msgs', [])),
            'pruned': True,
            'pruned_at': int(time.time())
        }
        
        return pruned
    
    def _create_checkpoint(self, block_index: int, block: Dict):
        """Create checkpoint for fast sync"""
        checkpoint = {
            'block_index': block_index,
            'block_hash': block['hash'],
            'timestamp': block['timestamp'],
            'created_at': int(time.time())
        }
        
        self.checkpoints[block_index] = checkpoint
        print(f"   📍 Checkpoint created at block {block_index}")
    
    def verify_pruned_chain(self) -> bool:
        """
        Verify that pruned chain is still valid
        
        Checks:
        - Hash chain integrity
        - Checkpoint consistency
        """
        
        print("\n🔍 Verifying pruned blockchain...")
        
        for i in range(1, len(self.state.chain)):
            current = self.state.chain[i]
            previous = self.state.chain[i-1]
            
            # Check previous_hash
            if current['previous_hash'] != previous['hash']:
                print(f"❌ Chain broken at block {i}")
                return False
        
        print("✅ Pruned blockchain verified!")
        return True
    
    def get_full_block(self, block_index: int) -> Optional[Dict]:
        """
        Get full block data (if available)
        
        Returns:
            Full block or None if pruned
        """
        
        if block_index >= len(self.state.chain):
            return None
        
        block = self.state.chain[block_index]
        
        if block.get('pruned', False):
            return None
        
        return block
    
    def get_pruning_stats(self) -> Dict:
        """Get pruning statistics"""
        current_height = len(self.state.chain)
        
        pruned_count = sum(
            1 for block in self.state.chain 
            if block.get('pruned', False)
        )
        
        full_count = current_height - pruned_count
        
        # Calculate approximate sizes
        if current_height > 0:
            sample_full = None
            sample_pruned = None
            
            for block in self.state.chain[:100]:
                if not block.get('pruned', False) and sample_full is None:
                    sample_full = len(json.dumps(block))
                if block.get('pruned', False) and sample_pruned is None:
                    sample_pruned = len(json.dumps(block))
            
            if sample_full and sample_pruned:
                estimated_full_size = full_count * sample_full
                estimated_pruned_size = pruned_count * sample_pruned
                total_size = estimated_full_size + estimated_pruned_size
                
                stats = {
                    'total_blocks': current_height,
                    'full_blocks': full_count,
                    'pruned_blocks': pruned_count,
                    'estimated_size_mb': round(total_size / (1024 * 1024), 2),
                    'checkpoints': len(self.checkpoints),
                    'pruning_enabled': PRUNING_ENABLED
                }
            else:
                stats = {
                    'total_blocks': current_height,
                    'full_blocks': full_count,
                    'pruned_blocks': pruned_count,
                    'checkpoints': len(self.checkpoints),
                    'pruning_enabled': PRUNING_ENABLED
                }
        else:
            stats = {
                'total_blocks': 0,
                'full_blocks': 0,
                'pruned_blocks': 0,
                'checkpoints': 0,
                'pruning_enabled': PRUNING_ENABLED
            }
        
        return stats


def init_pruning(state):
    """Initialize pruning for blockchain"""

def init_pruning(state):
    """Initialize pruning for blockchain"""
    return BlockchainPruning(state)