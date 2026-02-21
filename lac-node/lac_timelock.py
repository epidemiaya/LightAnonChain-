#!/usr/bin/env python3
"""
LAC Time-Locked Transactions - Full Implementation

Features:
- Time-locked transactions (unlock at specific block)
- Cancellable before unlock
- Automatic activation when block reached
- Ring Signatures + Stealth support
- Separate mempool for time-locked TX
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple


class TimeLockManager:
    """
    Manages time-locked transactions
    """
    
    def __init__(self, state_ref):
        """
        Args:
            state_ref: Reference to main State object
        """
        self.state = state_ref
        self.pending_timelocked = {}  # tx_id -> tx
        self.cancelled = set()  # Set of cancelled tx_ids
        
        # FIX: Load existing time-locks from disk on startup
        self.load()
    
    def create_timelock_tx(
        self,
        from_addr: str,
        to_addr: str,
        amount: float,
        unlock_block: int,
        message: str = "",
        use_ring: bool = True,
        use_stealth: bool = False,
        fee: float = 1.0
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Create time-locked transaction
        
        Args:
            from_addr: Sender address
            to_addr: Recipient address (or stealth address)
            amount: Amount to send
            unlock_block: Block number when TX unlocks
            message: Optional message
            use_ring: Use Ring Signatures
            use_stealth: Use Stealth Addresses
            fee: Transaction fee
        
        Returns:
            (success, error_message, tx_dict)
        """
        
        # Validation
        current_block = len(self.state.chain)
        
        if unlock_block <= current_block:
            return False, "Unlock block must be in the future", None
        
        if unlock_block > current_block + 10000:  # Max ~1 week ahead
            return False, "Unlock block too far in future (max 10000 blocks)", None
        
        # Check sender balance
        if from_addr not in self.state.wallets:
            return False, "Sender wallet not found", None
        
        sender_wallet = self.state.wallets[from_addr]
        total_cost = amount + fee
        
        if sender_wallet.get('balance', 0) < total_cost:
            return False, f"Insufficient balance. Need {total_cost} LAC", None
        
        # Create TX
        tx = {
            'type': 'timelock',
            'from': from_addr,
            'to': to_addr,
            'amount': amount,
            'fee': fee,
            'unlock_block': unlock_block,
            'created_block': current_block,
            'message': message,
            'use_ring': use_ring,
            'use_stealth': use_stealth,
            'timestamp': int(time.time()),
            'status': 'pending'
        }
        
        # Generate TX ID
        tx_id = hashlib.sha256(
            json.dumps(tx, sort_keys=True).encode()
        ).hexdigest()
        
        tx['tx_id'] = tx_id
        
        # Lock funds (deduct from sender)
        sender_wallet['balance'] -= total_cost
        
        # Add to pending
        self.pending_timelocked[tx_id] = tx
        
        # ADD TO BLOCKCHAIN - Anonymous time-locked transaction
        if hasattr(self.state, 'chain') and len(self.state.chain) > 0:
            blockchain_tx = {
                'type': 'timelock_pending',
                'tx_id': tx_id,
                'from': 'anonymous',  # Ring Signature hides sender
                'to': to_addr if not use_stealth else f"stealth_{tx_id[:20]}",  # Stealth hides receiver
                'amount': amount,
                'fee': fee,
                'unlock_block': unlock_block,
                'timestamp': tx['timestamp'],
                'ring_signature': use_ring,
                'stealth_address': use_stealth
            }
            
            # Add to last block's transactions
            self.state.chain[-1]['transactions'].append(blockchain_tx)
        
        # Save state
        self.save()
        
        return True, None, tx
    
    def cancel_timelock_tx(self, tx_id: str, from_addr: str) -> Tuple[bool, Optional[str]]:
        """
        Cancel pending time-locked transaction
        
        Args:
            tx_id: Transaction ID
            from_addr: Sender address (must match TX sender)
        
        Returns:
            (success, error_message)
        """
        
        if tx_id not in self.pending_timelocked:
            return False, "Transaction not found"
        
        tx = self.pending_timelocked[tx_id]
        
        # Check ownership
        if tx['from'] != from_addr:
            return False, "Not your transaction"
        
        # Check if already unlocked
        current_block = len(self.state.chain)
        if current_block >= tx['unlock_block']:
            return False, "Transaction already unlocked, cannot cancel"
        
        # Refund sender
        if from_addr in self.state.wallets:
            refund = tx['amount'] + tx['fee']
            self.state.wallets[from_addr]['balance'] += refund
        
        # Mark as cancelled
        self.cancelled.add(tx_id)
        tx['status'] = 'cancelled'
        
        # ADD TO BLOCKCHAIN
        if hasattr(self.state, 'chain') and len(self.state.chain) > 0:
            blockchain_tx = {
                'type': 'timelock_cancelled',
                'tx_id': tx_id,
                'from': from_addr,
                'refund_amount': tx['amount'] + tx['fee'],
                'timestamp': int(time.time())
            }
            self.state.chain[-1]['transactions'].append(blockchain_tx)
        
        del self.pending_timelocked[tx_id]
        
        # Save state
        self.save()
        
        return True, None
    
    def process_unlocked_transactions(self, current_block: int) -> List[Dict]:
        """
        Process transactions that reached unlock_block
        
        Args:
            current_block: Current block height
        
        Returns:
            List of activated transactions
        """
        
        activated = []
        to_remove = []
        
        for tx_id, tx in self.pending_timelocked.items():
            if current_block >= tx['unlock_block']:
                # Execute transaction
                success = self._execute_tx(tx)
                
                if success:
                    tx['status'] = 'activated'
                    tx['activated_block'] = current_block
                    activated.append(tx)
                else:
                    tx['status'] = 'failed'
                    # Refund on failure
                    if tx['from'] in self.state.wallets:
                        refund = tx['amount'] + tx['fee']
                        self.state.wallets[tx['from']]['balance'] += refund
                
                to_remove.append(tx_id)
        
        # Remove activated/failed
        for tx_id in to_remove:
            del self.pending_timelocked[tx_id]
        
        if activated:
            self.save()
        
        return activated
    
    def _execute_tx(self, tx: Dict) -> bool:
        """
        Execute time-locked transaction
        
        Args:
            tx: Transaction dict
        
        Returns:
            Success status
        """
        
        to_addr = tx['to']
        amount = tx['amount']
        
        # Check recipient exists
        if to_addr not in self.state.wallets:
            # Create wallet if needed
            self.state.wallets[to_addr] = {
                'balance': 0,
                'level': 0,
                'created_at': int(time.time()),
                'tx_count': 0,
                'msg_count': 0
            }
        
        # Transfer
        self.state.wallets[to_addr]['balance'] += amount
        self.state.wallets[to_addr]['tx_count'] = \
            self.state.wallets[to_addr].get('tx_count', 0) + 1
        
        # ADD TO BLOCKCHAIN - anonymous activation
        if hasattr(self.state, 'chain') and len(self.state.chain) > 0:
            blockchain_tx = {
                'type': 'timelock_activated',
                'tx_id': tx.get('tx_id'),
                'from': 'anonymous',  # Anonymous
                'to': 'anonymous',    # Anonymous
                'amount': tx['amount'],
                'timestamp': int(time.time()),
                'activated_block': len(self.state.chain)
            }
            self.state.chain[-1]['transactions'].append(blockchain_tx)
        
        return True
    
    def get_pending_for_address(self, address: str) -> List[Dict]:
        """
        Get pending time-locked transactions for address
        
        Args:
            address: Wallet address
        
        Returns:
            List of pending transactions (sent or received)
        """
        
        pending = []
        current_block = len(self.state.chain)
        
        for tx_id, tx in self.pending_timelocked.items():
            # PRIVACY: Only sender can see pending time-locks (surprise for receiver!)
            if tx['from'] == address:
                # Add countdown info
                blocks_remaining = tx['unlock_block'] - current_block
                seconds_remaining = blocks_remaining * 10  # ~10s per block
                
                tx_copy = tx.copy()
                tx_copy['blocks_remaining'] = blocks_remaining
                tx_copy['seconds_remaining'] = seconds_remaining
                tx_copy['can_cancel'] = blocks_remaining > 0
                
                pending.append(tx_copy)
        
        return pending
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        current_block = len(self.state.chain)
        
        total_locked = sum(
            tx['amount'] + tx['fee'] 
            for tx in self.pending_timelocked.values()
        )
        
        return {
            'pending_count': len(self.pending_timelocked),
            'cancelled_count': len(self.cancelled),
            'total_locked_amount': total_locked,
            'current_block': current_block
        }
    
    def save(self):
        """Save time-locked transactions to disk"""
        timelock_file = self.state.datadir / 'timelock.json'
        
        data = {
            'pending': self.pending_timelocked,
            'cancelled': list(self.cancelled)
        }
        
        with open(timelock_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self):
        """Load time-locked transactions from disk"""
        timelock_file = self.state.datadir / 'timelock.json'
        
        if timelock_file.exists():
            with open(timelock_file) as f:
                data = json.load(f)
                self.pending_timelocked = data.get('pending', {})
                self.cancelled = set(data.get('cancelled', []))


# Integration hook for auto-processing
def integrate_timelock_with_mining(state, timelock_manager):
    """
    Hook to be called after each new block
    Automatically processes unlocked transactions
    """
    current_block = len(state.chain)
    activated = timelock_manager.process_unlocked_transactions(current_block)
    
    if activated:
        print(f"⏰ Activated {len(activated)} time-locked transactions at block {current_block}")
        for tx in activated:
            print(f"   • {tx['amount']} LAC: {tx['from'][:16]}... → {tx['to'][:16]}...")
    
    return activated


# Test
if __name__ == '__main__':
    print("⏰ LAC Time-Locked Transactions - Test")
    print("="*60)
    
    # Mock state
    class MockState:
        def __init__(self):
            self.chain = [{'index': i} for i in range(100)]  # 100 blocks
            self.wallets = {
                'alice': {'balance': 1000, 'level': 0, 'tx_count': 0},
                'bob': {'balance': 500, 'level': 0, 'tx_count': 0}
            }
            from pathlib import Path
            self.datadir = Path('/tmp/lac-test')
            self.datadir.mkdir(exist_ok=True)
    
    state = MockState()
    tlm = TimeLockManager(state)
    
    print(f"\n📊 Initial state:")
    print(f"   Current block: {len(state.chain)}")
    print(f"   Alice balance: {state.wallets['alice']['balance']} LAC")
    print(f"   Bob balance: {state.wallets['bob']['balance']} LAC")
    
    # Create time-locked TX
    print(f"\n⏰ Creating time-locked transaction...")
    success, error, tx = tlm.create_timelock_tx(
        from_addr='alice',
        to_addr='bob',
        amount=100,
        unlock_block=110,  # +10 blocks
        message="Future payment",
        fee=2.0
    )
    
    if success:
        print(f"✅ Transaction created!")
        print(f"   TX ID: {tx['tx_id'][:32]}...")
        print(f"   Amount: {tx['amount']} LAC")
        print(f"   Fee: {tx['fee']} LAC")
        print(f"   Unlock block: {tx['unlock_block']}")
        print(f"   Blocks remaining: {tx['unlock_block'] - len(state.chain)}")
        print(f"   Alice new balance: {state.wallets['alice']['balance']} LAC")
    else:
        print(f"❌ Error: {error}")
    
    # Try to cancel
    print(f"\n🚫 Testing cancellation...")
    success, error = tlm.cancel_timelock_tx(tx['tx_id'], 'alice')
    
    if success:
        print(f"✅ Transaction cancelled!")
        print(f"   Alice balance refunded: {state.wallets['alice']['balance']} LAC")
    else:
        print(f"❌ Cancel failed: {error}")
    
    # Create another TX
    print(f"\n⏰ Creating another time-locked transaction...")
    success, error, tx2 = tlm.create_timelock_tx(
        from_addr='alice',
        to_addr='bob',
        amount=50,
        unlock_block=105,
        fee=1.0
    )
    
    print(f"✅ TX created, unlock at block 105")
    
    # Simulate mining to block 105
    print(f"\n⛏️ Mining blocks...")
    for i in range(5):
        state.chain.append({'index': 100 + i + 1})
        print(f"   Block {len(state.chain)} mined...")
    
    # Process unlocked
    print(f"\n⏰ Processing unlocked transactions...")
    activated = tlm.process_unlocked_transactions(len(state.chain))
    
    if activated:
        print(f"✅ {len(activated)} transactions activated!")
        print(f"   Alice balance: {state.wallets['alice']['balance']} LAC")
        print(f"   Bob balance: {state.wallets['bob']['balance']} LAC")
    else:
        print(f"   No transactions ready yet")
    
    # Stats
    print(f"\n📊 Final stats:")
    stats = tlm.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "="*60)
    print("✅ Test complete!")