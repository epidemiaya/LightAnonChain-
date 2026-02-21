"""
LAC Username Transactions
=========================
Transaction types for username registry operations.
Integrates with lac_node.py and lac_username_state.py
"""

import json
import hashlib
import time
from typing import Dict, Optional, Tuple


# Transaction type constants
TX_TYPE_TRANSFER = 'transfer'
TX_TYPE_MESSAGE = 'message'
TX_TYPE_USERNAME_REGISTER = 'username_register'
TX_TYPE_USERNAME_TRANSFER = 'username_transfer'
TX_TYPE_USERNAME_BURN = 'username_burn'
TX_TYPE_USERNAME_UPDATE = 'username_update'
TX_TYPE_USERNAME_LIST = 'username_list'


class UsernameTransactionBuilder:
    """
    Build username transactions for LAC blockchain.
    Integrates with stealth addresses and ring signatures.
    """
    
    def __init__(self, stealth_module=None):
        """
        Initialize transaction builder.
        
        Args:
            stealth_module: LACStealthAddress instance (optional)
        """
        self.stealth_module = stealth_module
    
    def create_register_transaction(
        self,
        username: str,
        owner_seed: str,
        spend_public: bytes,
        view_public: bytes,
        registration_fee: int,
        metadata: Dict = None
    ) -> Dict:
        """
        Create username registration transaction.
        
        Args:
            username: Username to register (with or without @)
            owner_seed: Owner's seed (for signing)
            spend_public: Owner's spend public key
            view_public: Owner's view public key  
            registration_fee: Registration fee in LAC
            metadata: Optional metadata dict
        
        Returns:
            Transaction dict ready for mempool
        """
        # Normalize username
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        # Generate stealth address for this username
        if self.stealth_module:
            stealth_addr, tx_public_key, _ = self.stealth_module.generate_one_time_address(
                spend_public, view_public
            )
        else:
            # Fallback: simple stealth address
            stealth_addr = self._generate_simple_stealth(spend_public, view_public)
        
        # Create transaction
        tx = {
            'type': TX_TYPE_USERNAME_REGISTER,
            'username': username,
            'stealth_address': stealth_addr,
            'registration_fee': registration_fee,
            'metadata': metadata or {},
            'timestamp': int(time.time()),
            'owner_hash': hashlib.sha256(owner_seed.encode()).hexdigest()[:16]  # proof of ownership (partial)
        }
        
        # Sign transaction
        tx['signature'] = self._sign_transaction(tx, owner_seed)
        
        return tx
    
    def create_transfer_transaction(
        self,
        username: str,
        current_owner_seed: str,
        new_spend_public: bytes,
        new_view_public: bytes,
        price: int = 0
    ) -> Dict:
        """
        Create username transfer transaction.
        
        Args:
            username: Username to transfer
            current_owner_seed: Current owner's seed (for signing)
            new_spend_public: New owner's spend public key
            new_view_public: New owner's view public key
            price: Transfer price (0 = gift, >0 = sale)
        
        Returns:
            Transaction dict
        """
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        # Generate new stealth address
        if self.stealth_module:
            new_stealth, _, _ = self.stealth_module.generate_one_time_address(
                new_spend_public, new_view_public
            )
        else:
            new_stealth = self._generate_simple_stealth(new_spend_public, new_view_public)
        
        tx = {
            'type': TX_TYPE_USERNAME_TRANSFER,
            'username': username,
            'new_stealth_address': new_stealth,
            'price': price,
            'timestamp': int(time.time()),
            'current_owner_hash': hashlib.sha256(current_owner_seed.encode()).hexdigest()[:16]
        }
        
        tx['signature'] = self._sign_transaction(tx, current_owner_seed)
        
        return tx
    
    def create_burn_transaction(
        self,
        username: str,
        owner_seed: str,
        burn_forever: bool = True
    ) -> Dict:
        """
        Create username burn transaction.
        
        Args:
            username: Username to burn
            owner_seed: Owner's seed (for signing)
            burn_forever: If True, username can never be re-registered
        
        Returns:
            Transaction dict
        """
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        tx = {
            'type': TX_TYPE_USERNAME_BURN,
            'username': username,
            'burn_forever': burn_forever,
            'timestamp': int(time.time()),
            'owner_hash': hashlib.sha256(owner_seed.encode()).hexdigest()[:16]
        }
        
        tx['signature'] = self._sign_transaction(tx, owner_seed)
        
        return tx
    
    def create_update_transaction(
        self,
        username: str,
        owner_seed: str,
        metadata: Dict = None,
        price: int = None
    ) -> Dict:
        """
        Create username metadata update transaction.
        
        Args:
            username: Username to update
            owner_seed: Owner's seed (for signing)
            metadata: New metadata dict (optional)
            price: New sale price (optional, None = no change)
        
        Returns:
            Transaction dict
        """
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        tx = {
            'type': TX_TYPE_USERNAME_UPDATE,
            'username': username,
            'timestamp': int(time.time()),
            'owner_hash': hashlib.sha256(owner_seed.encode()).hexdigest()[:16]
        }
        
        if metadata is not None:
            tx['metadata'] = metadata
        if price is not None:
            tx['price'] = price
        
        tx['signature'] = self._sign_transaction(tx, owner_seed)
        
        return tx
    
    def _generate_simple_stealth(self, spend_public: bytes, view_public: bytes) -> str:
        """Generate simple stealth address (fallback)"""
        combined = hashlib.sha256(spend_public + view_public).digest()
        return f"stealth_{combined.hex()[:40]}"
    
    def _sign_transaction(self, tx: Dict, seed: str) -> str:
        """
        Sign transaction with seed.
        Simple signature for now - can be upgraded to Ring Signatures later.
        """
        # Create message from transaction data
        tx_copy = tx.copy()
        tx_copy.pop('signature', None)  # Remove signature if exists
        
        message = json.dumps(tx_copy, sort_keys=True)
        
        # Sign with seed
        signature_hash = hashlib.sha256(f"{message}{seed}".encode()).hexdigest()
        
        return signature_hash
    
    def verify_transaction_signature(self, tx: Dict, expected_owner_hash: str) -> bool:
        """
        Verify transaction signature.
        
        Args:
            tx: Transaction dict
            expected_owner_hash: Expected owner hash from username state
        
        Returns:
            True if signature valid
        """
        if 'signature' not in tx:
            return False
        
        # For now, just check that signature exists and owner_hash matches
        # In production, this would verify cryptographic signature
        return tx.get('owner_hash') == expected_owner_hash or tx.get('current_owner_hash') == expected_owner_hash


class UsernameTransactionProcessor:
    """
    Process username transactions in blocks.
    Integrates with UsernameStateManager.
    """
    
    def __init__(self, state_manager):
        """
        Initialize processor.
        
        Args:
            state_manager: UsernameStateManager instance
        """
        self.state = state_manager
    
    def process_transaction(
        self,
        tx: Dict,
        block_height: int,
        wallets: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Process a username transaction.
        
        Args:
            tx: Transaction dict
            block_height: Current block height
            wallets: Blockchain wallets state
        
        Returns:
            (success, error_message)
        """
        tx_type = tx.get('type')
        
        try:
            if tx_type == TX_TYPE_USERNAME_REGISTER:
                return self._process_register(tx, block_height, wallets)
            
            elif tx_type == TX_TYPE_USERNAME_TRANSFER:
                return self._process_transfer(tx, block_height, wallets)
            
            elif tx_type == TX_TYPE_USERNAME_BURN:
                return self._process_burn(tx, block_height)
            
            elif tx_type == TX_TYPE_USERNAME_UPDATE:
                return self._process_update(tx, block_height)
            
            else:
                return False, f"Unknown username transaction type: {tx_type}"
        
        except Exception as e:
            return False, f"Transaction processing error: {e}"
    
    def _process_register(
        self,
        tx: Dict,
        block_height: int,
        wallets: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Process username registration"""
        username = tx['username']
        stealth_address = tx['stealth_address']
        registration_fee = tx.get('registration_fee', 0)
        metadata = tx.get('metadata', {})
        
        # Validate username
        is_valid, error = self.state.is_valid_username(username)
        if not is_valid:
            return False, error
        
        # Check if already registered
        if self.state.resolve_username(username):
            return False, f"Username {username} already registered"
        
        # Check price
        expected_price = self.state.calculate_price(username)
        if expected_price < 0:
            return False, f"Username {username} not available for registration"
        
        if registration_fee < expected_price:
            return False, f"Insufficient registration fee: {registration_fee} < {expected_price} LAC"
        
        # Get key_id from wallet BEFORE registration
        key_id = None
        try:
            from_address = tx.get('from')
            if from_address and from_address in wallets:
                wallet = wallets[from_address]
                key_id = wallet.get('key_id')
        except Exception as e:
            print(f"⚠️ Failed to get key_id: {e}")
        
        # Register username WITH key_id (will remove from old username if exists)
        success = self.state.register_username(
            username=username,
            stealth_address=stealth_address,
            block_height=block_height,
            metadata=metadata,
            key_id=key_id
        )
        
        if not success:
            return False, "Registration failed"
        
        # Burn registration fee (reduce total supply)
        # This is handled in the main transaction processing
        
        return True, None
    
    def _process_transfer(
        self,
        tx: Dict,
        block_height: int,
        wallets: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Process username transfer"""
        username = tx['username']
        new_stealth = tx['new_stealth_address']
        price = tx.get('price', 0)
        
        # Check username exists
        if not self.state.resolve_username(username):
            return False, f"Username {username} not found"
        
        # Get username info
        info = self.state.get_username_info(username)
        if not info:
            return False, f"Username {username} not found"
        
        # If price > 0, handle payment
        if price > 0:
            # Payment should be handled in main transaction processing
            # Here we just transfer the username
            pass
        
        # Transfer username
        success = self.state.transfer_username(
            username=username,
            new_stealth_address=new_stealth,
            block_height=block_height
        )
        
        if not success:
            return False, "Transfer failed"
        
        return True, None
    
    def _process_burn(
        self,
        tx: Dict,
        block_height: int
    ) -> Tuple[bool, Optional[str]]:
        """Process username burn"""
        username = tx['username']
        burn_forever = tx.get('burn_forever', True)
        
        # Check username exists
        if not self.state.resolve_username(username):
            return False, f"Username {username} not found"
        
        # Burn username
        success = self.state.burn_username(
            username=username,
            block_height=block_height,
            burn_forever=burn_forever
        )
        
        if not success:
            return False, "Burn failed"
        
        return True, None
    
    def _process_update(
        self,
        tx: Dict,
        block_height: int
    ) -> Tuple[bool, Optional[str]]:
        """Process username metadata update"""
        username = tx['username']
        
        # Check username exists
        if not self.state.resolve_username(username):
            return False, f"Username {username} not found"
        
        # Update metadata
        if 'metadata' in tx:
            # Get current info
            info = self.state.get_username_info(username)
            if info:
                # Update metadata (would need to add this method to state manager)
                pass
        
        # Update price
        if 'price' in tx:
            success = self.state.list_for_sale(username, tx['price'])
            if not success:
                return False, "Failed to update price"
        
        return True, None


# === Helper functions for integration ===

def is_username_transaction(tx: Dict) -> bool:
    """Check if transaction is username-related"""
    tx_type = tx.get('type')
    return tx_type in [
        TX_TYPE_USERNAME_REGISTER,
        TX_TYPE_USERNAME_TRANSFER,
        TX_TYPE_USERNAME_BURN,
        TX_TYPE_USERNAME_UPDATE
    ]


def get_username_transaction_fee(tx: Dict) -> float:
    """Get fee for username transaction"""
    tx_type = tx.get('type')
    
    if tx_type == TX_TYPE_USERNAME_REGISTER:
        # Registration fee is included in transaction
        return tx.get('registration_fee', 0)
    
    elif tx_type == TX_TYPE_USERNAME_TRANSFER:
        # Transfer fee (5% of price, min 0.1 LAC)
        price = tx.get('price', 0)
        if price > 0:
            return max(0.1, price * 0.05)
        return 0.1  # Gift transfer fee
    
    elif tx_type == TX_TYPE_USERNAME_BURN:
        return 0  # Free to burn
    
    elif tx_type == TX_TYPE_USERNAME_UPDATE:
        return 0.1  # Small update fee
    
    return 0


if __name__ == "__main__":
    print("🧪 Testing Username Transactions...")
    
    # Test transaction builder
    builder = UsernameTransactionBuilder()
    
    # Mock keys
    spend_pub = b"spend_public_key_12345678901234567890"
    view_pub = b"view_public_key_123456789012345678901"
    
    # Test register
    print("\n1. Create register transaction:")
    tx_reg = builder.create_register_transaction(
        username="@alice",
        owner_seed="test seed phrase for alice wallet keys",
        spend_public=spend_pub,
        view_public=view_pub,
        registration_fee=10
    )
    print(f"✅ Register TX: {tx_reg['username']} → {tx_reg['stealth_address'][:32]}...")
    print(f"   Fee: {tx_reg['registration_fee']} LAC")
    print(f"   Signature: {tx_reg['signature'][:32]}...")
    
    # Test transfer
    print("\n2. Create transfer transaction:")
    new_spend_pub = b"new_spend_public_key_098765432109876543"
    new_view_pub = b"new_view_public_key_098765432109876543"
    
    tx_transfer = builder.create_transfer_transaction(
        username="@alice",
        current_owner_seed="test seed phrase for alice wallet keys",
        new_spend_public=new_spend_pub,
        new_view_public=new_view_pub,
        price=50
    )
    print(f"✅ Transfer TX: {tx_transfer['username']}")
    print(f"   New stealth: {tx_transfer['new_stealth_address'][:32]}...")
    print(f"   Price: {tx_transfer['price']} LAC")
    
    # Test burn
    print("\n3. Create burn transaction:")
    tx_burn = builder.create_burn_transaction(
        username="@alice",
        owner_seed="test seed phrase for alice wallet keys",
        burn_forever=True
    )
    print(f"✅ Burn TX: {tx_burn['username']}")
    print(f"   Forever: {tx_burn['burn_forever']}")
    
    print("\n✅ All transaction tests completed!")