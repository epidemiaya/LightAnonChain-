"""
LAC Username State Manager
Децентралізована система username registry
"""

from typing import Dict, Optional, Tuple


class UsernameStateManager:
    """Manages username registry state"""
    
    def __init__(self):
        self.usernames = {}  # username → info
        self.reserved = {'lac', 'admin', 'system', 'root', 'moderator', 'support'}
        self.burned = set()
    
    def is_valid_username(self, username: str) -> Tuple[bool, Optional[str]]:
        """Validate username format"""
        username = username.lstrip('@')
        
        if len(username) < 3:
            return False, "Username too short (min 3 chars)"
        
        if len(username) > 32:
            return False, "Username too long (max 32 chars)"
        
        if not username.replace('_', '').replace('-', '').isalnum():
            return False, "Username must be alphanumeric (a-z, 0-9, _, -)"
        
        if username.lower() in self.reserved:
            return False, "Username is reserved"
        
        return True, None
    
    def calculate_price(self, username: str) -> int:
        """
        Calculate registration price based on length
        
        Нова ціноутворення (децентралізація):
        - 7+ символів: 10 LAC (доступно всім)
        - 6 символів: 100 LAC
        - 5 символів: 1,000 LAC
        - 4 символи: 10,000 LAC
        - 3 символи: 100,000 LAC
        """
        username = username.lstrip('@')
        
        if username.lower() in self.reserved or username in self.burned:
            return -1  # Not available
        
        length = len(username)
        
        if length >= 7:
            return 10
        elif length == 6:
            return 100
        elif length == 5:
            return 1000
        elif length == 4:
            return 10000
        elif length == 3:
            return 100000
        else:
            return -1  # Invalid
    
    def resolve_username(self, username: str) -> Optional[str]:
        """Resolve username to stealth address"""
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        info = self.usernames.get(username)
        if info:
            return info.get('stealth_address')
        return None
    
    def register_username(
        self,
        username: str,
        stealth_address: str,
        block_height: int,
        metadata: Dict = None,
        key_id: str = None
    ) -> bool:
        """Register a username"""
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        if username in self.usernames:
            return False
        
        # Remove key_id from old username if exists (one wallet = one username)
        if key_id:
            for old_username, info in list(self.usernames.items()):
                if info.get('key_id') == key_id:
                    print(f"⚠️  Removing key_id from old username: {old_username}")
                    info.pop('key_id', None)
        
        self.usernames[username] = {
            'stealth_address': stealth_address,
            'block_height': block_height,
            'registered_at': block_height,
            'metadata': metadata or {},
            'for_sale': False,
            'sale_price': 0
        }
        
        # Add key_id if provided
        if key_id:
            self.usernames[username]['key_id'] = key_id
            print(f"✅ Registered {username} with key_id: {key_id[:16]}...")
        
        return True
    
    
    def get_username_info(self, username: str) -> Optional[Dict]:
        """Get username info"""
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        return self.usernames.get(username)
    
    def get_stats(self) -> Dict:
        """Get registry statistics"""
        total = len(self.usernames)
        for_sale = sum(1 for u in self.usernames.values() if u.get('for_sale', False))
        burned = len(self.burned)
        
        return {
            'total_registered': total,
            'active': total - burned,
            'for_sale': for_sale,
            'burned': burned
        }
    
    def transfer_username(self, username: str, new_stealth: str) -> bool:
        """Transfer username to new owner"""
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        if username not in self.usernames:
            return False
        
        self.usernames[username]['stealth_address'] = new_stealth
        self.usernames[username]['for_sale'] = False
        self.usernames[username]['sale_price'] = 0
        
        return True
    
    def burn_username(self, username: str) -> bool:
        """Burn (destroy) username"""
        username = username.lstrip('@')
        if not username.startswith('@'):
            username = '@' + username
        
        if username not in self.usernames:
            return False
        
        self.burned.add(username)
        del self.usernames[username]
        
        return True

    
    def get_username_by_key_id(self, key_id: str) -> Optional[str]:
        """Get username by key_id"""
        for username, info in self.usernames.items():
            if info.get('key_id') == key_id:
                return username
        return None