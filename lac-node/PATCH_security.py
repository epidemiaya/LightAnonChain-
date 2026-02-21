# SECURITY HARDENING PATCHES

import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta

# ============================================================================
# 1. RATE LIMITING
# ============================================================================

class RateLimiter:
    """
    Rate limiting для API endpoints та mining
    """
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            'api': (100, 60),        # 100 requests per 60 seconds
            'mining': (10, 60),      # 10 mining attempts per 60 seconds
            'transaction': (20, 60), # 20 transactions per 60 seconds
            'message': (30, 60),     # 30 messages per 60 seconds
            'username': (5, 3600),   # 5 username purchases per hour
        }
    
    def check_rate_limit(self, identifier, action='api'):
        """
        Перевірити чи не перевищено rate limit
        
        identifier: IP address, wallet address, etc.
        action: тип дії
        """
        max_requests, window = self.limits.get(action, (100, 60))
        now = time.time()
        
        # Очистити старі requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < window
        ]
        
        # Перевірити limit
        if len(self.requests[identifier]) >= max_requests:
            return False, f"Rate limit exceeded: {action}"
        
        # Додати новий request
        self.requests[identifier].append(now)
        return True, None
    
    def get_remaining(self, identifier, action='api'):
        """
        Скільки requests залишилось
        """
        max_requests, window = self.limits.get(action, (100, 60))
        now = time.time()
        
        recent = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < window
        ]
        
        return max(0, max_requests - len(recent))


# ============================================================================
# 2. INPUT VALIDATION
# ============================================================================

class InputValidator:
    """
    Валідація всіх inputs
    """
    
    @staticmethod
    def validate_username(username):
        """
        Валідація username
        """
        if not username:
            return False, "Username cannot be empty"
        
        if not isinstance(username, str):
            return False, "Username must be string"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(username) > 32:
            return False, "Username must be max 32 characters"
        
        # Тільки alphanumeric + underscore
        if not username.replace('_', '').isalnum():
            return False, "Username can only contain letters, numbers, underscore"
        
        # Не може починатись з цифри
        if username[0].isdigit():
            return False, "Username cannot start with number"
        
        # Reserved usernames
        reserved = ['admin', 'root', 'system', 'lac', 'null', 'undefined']
        if username.lower() in reserved:
            return False, "Username is reserved"
        
        return True, None
    
    @staticmethod
    def validate_message(message):
        """
        Валідація message
        """
        if not isinstance(message, str):
            return False, "Message must be string"
        
        if len(message) > 10000:  # 10KB max
            return False, "Message too long (max 10KB)"
        
        # Перевірка на suspicious patterns
        suspicious = ['<script>', 'javascript:', 'eval(', 'exec(']
        for pattern in suspicious:
            if pattern.lower() in message.lower():
                return False, f"Suspicious pattern detected: {pattern}"
        
        return True, None
    
    @staticmethod
    def validate_amount(amount):
        """
        Валідація transaction amount
        """
        if not isinstance(amount, (int, float)):
            return False, "Amount must be number"
        
        if amount <= 0:
            return False, "Amount must be positive"
        
        if amount > 1e15:  # Максимальний розумний amount
            return False, "Amount too large"
        
        return True, None
    
    @staticmethod
    def validate_address(address):
        """
        Валідація wallet address
        """
        if not isinstance(address, str):
            return False, "Address must be string"
        
        # LAC addresses are hex strings
        if not all(c in '0123456789abcdefABCDEF' for c in address):
            return False, "Invalid address format"
        
        if len(address) != 64:  # SHA256 hash length
            return False, "Address must be 64 characters"
        
        return True, None


# ============================================================================
# 3. ANTI-SYBIL PROTECTION
# ============================================================================

class SybilProtection:
    """
    Захист від Sybil attacks
    """
    
    def __init__(self):
        self.account_scores = {}
        self.network_graph = defaultdict(set)
    
    def calculate_trust_score(self, address, blockchain):
        """
        Розрахувати trust score для address
        """
        if address in self.account_scores:
            return self.account_scores[address]
        
        score = 0.0
        
        # 1. Age of account (max 30 points)
        first_tx = blockchain.get_first_transaction(address)
        if first_tx:
            age_days = (time.time() - first_tx['timestamp']) / 86400
            score += min(30, age_days / 10)  # 10 дні = 10 points
        
        # 2. Transaction volume (max 25 points)
        tx_count = blockchain.get_transaction_count(address)
        score += min(25, tx_count / 10)
        
        # 3. Balance (max 20 points)
        balance = blockchain.get_balance(address)
        score += min(20, balance / 1000)  # 1000 LAC = 20 points
        
        # 4. Network connections (max 15 points)
        unique_peers = len(self.network_graph[address])
        score += min(15, unique_peers)
        
        # 5. Referrals (max 10 points)
        referral_count = blockchain.get_referral_count(address)
        score += min(10, referral_count * 2)
        
        self.account_scores[address] = score
        return score
    
    def is_likely_sybil(self, address, blockchain):
        """
        Перевірити чи схоже на Sybil attack
        """
        score = self.calculate_trust_score(address, blockchain)
        
        # Low trust score
        if score < 20:
            return True
        
        # Suspicious patterns
        # 1. Багато transactions за короткий час
        recent_tx = blockchain.get_recent_transactions(address, hours=1)
        if len(recent_tx) > 100:
            return True
        
        # 2. Все mining rewards йдуть на один address
        mining_rewards = blockchain.get_mining_rewards(address)
        outgoing_tx = blockchain.get_outgoing_transactions(address)
        if len(outgoing_tx) < 5 and len(mining_rewards) > 50:
            return True
        
        # 3. Identical transaction patterns
        if self._has_identical_patterns(address, blockchain):
            return True
        
        return False
    
    def _has_identical_patterns(self, address, blockchain):
        """
        Перевірити на identical transaction patterns
        """
        # Simplified check
        tx_list = blockchain.get_transactions(address)
        if len(tx_list) < 10:
            return False
        
        # Check if all transactions have same amount/timing
        amounts = [tx['amount'] for tx in tx_list]
        if len(set(amounts)) == 1:  # All same amount
            return True
        
        return False


# ============================================================================
# 4. DDoS PROTECTION
# ============================================================================

class DDoSProtection:
    """
    Захист від DDoS attacks
    """
    
    def __init__(self):
        self.connection_counts = defaultdict(int)
        self.request_sizes = defaultdict(list)
        self.banned_ips = set()
        self.temp_banned = {}  # IP -> unban_time
    
    def check_connection(self, ip_address):
        """
        Перевірити чи можна приймати connection
        """
        # Check if permanently banned
        if ip_address in self.banned_ips:
            return False, "IP is permanently banned"
        
        # Check if temp banned
        if ip_address in self.temp_banned:
            if time.time() < self.temp_banned[ip_address]:
                return False, "IP is temporarily banned"
            else:
                del self.temp_banned[ip_address]
        
        # Check connection limit
        if self.connection_counts[ip_address] > 100:
            self.temp_ban(ip_address, duration=3600)  # 1 hour
            return False, "Too many connections"
        
        self.connection_counts[ip_address] += 1
        return True, None
    
    def temp_ban(self, ip_address, duration=3600):
        """
        Тимчасово забанити IP
        """
        self.temp_banned[ip_address] = time.time() + duration
        logger.warning(f"Temp banned IP: {ip_address} for {duration}s")
    
    def permanent_ban(self, ip_address):
        """
        Назавжди забанити IP
        """
        self.banned_ips.add(ip_address)
        logger.warning(f"Permanently banned IP: {ip_address}")
    
    def check_request_size(self, ip_address, size):
        """
        Перевірити розмір request
        """
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        
        if size > MAX_SIZE:
            self.temp_ban(ip_address, duration=3600)
            return False, "Request too large"
        
        # Track average request size
        self.request_sizes[ip_address].append(size)
        if len(self.request_sizes[ip_address]) > 100:
            self.request_sizes[ip_address].pop(0)
        
        # Detect if sending unusually large requests
        avg_size = sum(self.request_sizes[ip_address]) / len(self.request_sizes[ip_address])
        if size > avg_size * 10 and size > 1024 * 1024:  # 10x average and >1MB
            logger.warning(f"Suspicious large request from {ip_address}: {size} bytes")
        
        return True, None


# ============================================================================
# 5. SECURE KEY STORAGE
# ============================================================================

class SecureKeyStorage:
    """
    Безпечне зберігання private keys
    """
    
    def __init__(self, storage_file='wallet.enc'):
        self.storage_file = storage_file
    
    def save_key(self, private_key, password):
        """
        Зберегти key зашифрованим
        """
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
        import base64
        
        # Generate salt
        salt = secrets.token_bytes(32)
        
        # Derive encryption key from password
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Encrypt private key
        f = Fernet(key)
        encrypted = f.encrypt(private_key.encode())
        
        # Save salt + encrypted key
        with open(self.storage_file, 'wb') as file:
            file.write(salt + encrypted)
        
        logger.info("✅ Private key saved securely")
    
    def load_key(self, password):
        """
        Завантажити і розшифрувати key
        """
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
        import base64
        
        # Read salt + encrypted key
        with open(self.storage_file, 'rb') as file:
            data = file.read()
        
        salt = data[:32]
        encrypted = data[32:]
        
        # Derive encryption key from password
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Decrypt private key
        f = Fernet(key)
        try:
            private_key = f.decrypt(encrypted).decode()
            logger.info("✅ Private key loaded")
            return private_key
        except:
            logger.error("❌ Wrong password")
            return None


# ============================================================================
# 6. SECURITY AUDIT LOG
# ============================================================================

class SecurityAuditLog:
    """
    Log всіх security events
    """
    
    def __init__(self, log_file='security_audit.log'):
        self.log_file = log_file
        self.logger = logging.getLogger('SecurityAudit')
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [SECURITY] %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_event(self, event_type, details):
        """
        Залогувати security event
        """
        self.logger.info(f"{event_type}: {details}")
    
    def log_suspicious_activity(self, ip_address, activity):
        """
        Залогувати suspicious activity
        """
        self.log_event('SUSPICIOUS', f"IP {ip_address}: {activity}")
    
    def log_attack_attempt(self, attack_type, source):
        """
        Залогувати attack attempt
        """
        self.log_event('ATTACK', f"{attack_type} from {source}")
    
    def log_ban(self, ip_address, reason):
        """
        Залогувати ban
        """
        self.log_event('BAN', f"IP {ip_address} banned: {reason}")


# ============================================================================
# INTEGRATION
# ============================================================================

class SecurityManager:
    """
    Інтеграція всіх security mechanisms
    """
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.validator = InputValidator()
        self.sybil_protection = SybilProtection()
        self.ddos_protection = DDoSProtection()
        self.audit_log = SecurityAuditLog()
    
    def check_api_request(self, ip_address, endpoint, data):
        """
        Комплексна перевірка API request
        """
        # 1. Rate limiting
        allowed, msg = self.rate_limiter.check_rate_limit(ip_address, 'api')
        if not allowed:
            self.audit_log.log_suspicious_activity(ip_address, msg)
            return False, msg
        
        # 2. DDoS protection
        allowed, msg = self.ddos_protection.check_connection(ip_address)
        if not allowed:
            return False, msg
        
        # 3. Input validation
        if 'username' in data:
            valid, msg = self.validator.validate_username(data['username'])
            if not valid:
                return False, msg
        
        if 'message' in data:
            valid, msg = self.validator.validate_message(data['message'])
            if not valid:
                return False, msg
        
        return True, None


# TESTING
def test_security():
    """
    Тест security mechanisms
    """
    print("Testing security mechanisms...")
    
    # Test 1: Rate limiter
    limiter = RateLimiter()
    for i in range(150):
        allowed, msg = limiter.check_rate_limit('test_user', 'api')
        if not allowed:
            print(f"✅ Rate limiter blocked at request {i+1}")
            break
    
    # Test 2: Input validator
    validator = InputValidator()
    
    valid, msg = validator.validate_username("alice")
    assert valid, "Valid username rejected"
    
    valid, msg = validator.validate_username("ab")
    assert not valid, "Too short username accepted"
    
    valid, msg = validator.validate_username("<script>alert()</script>")
    assert not valid, "Suspicious username accepted"
    
    print("✅ Input validator works")
    
    # Test 3: DDoS protection
    ddos = DDoSProtection()
    for i in range(150):
        allowed, msg = ddos.check_connection('192.168.1.100')
        if not allowed:
            print(f"✅ DDoS protection blocked at connection {i+1}")
            break
    
    print("✅ All security tests passed!")


if __name__ == '__main__':
    test_security()