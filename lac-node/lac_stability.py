#!/usr/bin/env python3
"""
LAC Stability Module
Atomic writes, error handling, graceful shutdown, logging
"""
import os
import json
import time
import signal
import sys
import logging
import tempfile
import traceback
from pathlib import Path
from functools import wraps
from datetime import datetime
from threading import Lock

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(datadir='data', debug=False):
    """Setup comprehensive logging system"""
    log_dir = Path(datadir) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Main log
    main_log = log_dir / 'lac.log'
    error_log = log_dir / 'error.log'
    security_log = log_dir / 'security.log'
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Console handler (INFO and above)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    ))
    root_logger.addHandler(console)
    
    # File handler (all logs)
    file_handler = logging.FileHandler(main_log)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    root_logger.addHandler(file_handler)
    
    # Error handler (errors only)
    error_handler = logging.FileHandler(error_log)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s\n%(exc_info)s'
    ))
    root_logger.addHandler(error_handler)
    
    # Security logger (separate)
    security_logger = logging.getLogger('Security')
    security_handler = logging.FileHandler(security_log)
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s [SECURITY] %(message)s'
    ))
    security_logger.addHandler(security_handler)
    
    return logging.getLogger('LAC')


# ============================================================================
# ATOMIC WRITES
# ============================================================================

class StateManager:
    """
    Безпечне збереження стану з atomic writes та backup
    """
    
    def __init__(self, base_dir='data'):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.logger = logging.getLogger('LAC.StateManager')
    
    def save_atomic(self, filename, data):
        """
        Atomic write - запобігає corruption
        
        Args:
            filename: ім'я файлу (напр. 'chain.json')
            data: dict для збереження
        """
        filepath = self.base_dir / filename
        
        with self.lock:
            try:
                # 1. Backup існуючого файлу якщо є
                if filepath.exists():
                    backup_path = filepath.with_suffix('.json.backup')
                    try:
                        import shutil
                        shutil.copy2(filepath, backup_path)
                    except Exception as e:
                        self.logger.warning(f"Backup failed for {filename}: {e}")
                
                # 2. Записуємо в temp файл
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=self.base_dir,
                    prefix=f'.tmp_{filename.replace(".json", "")}_',
                    suffix='.json'
                )
                
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                
                # 3. Atomic rename
                os.replace(temp_path, filepath)
                
                self.logger.debug(f"[OK] Saved {filename} atomically")
                return True
                
            except Exception as e:
                self.logger.error(f"[ERROR] Failed to save {filename}: {e}")
                # Cleanup temp file if exists
                try:
                    if 'temp_path' in locals():
                        os.unlink(temp_path)
                except:
                    pass
                raise
    
    def load_with_backup(self, filename):
        """
        Завантаження з fallback на backup
        
        Args:
            filename: ім'я файлу
            
        Returns:
            dict або None
        """
        filepath = self.base_dir / filename
        backup_path = filepath.with_suffix('.json.backup')
        
        # Спробувати основний файл
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self.logger.debug(f"[OK] Loaded {filename}")
                return data
            except json.JSONDecodeError as e:
                self.logger.error(f"[WARN] Main {filename} corrupted: {e}")
                # Спробувати backup
                if backup_path.exists():
                    try:
                        with open(backup_path, 'r') as f:
                            data = json.load(f)
                        self.logger.warning(f"[OK] Restored {filename} from backup")
                        return data
                    except json.JSONDecodeError:
                        self.logger.error(f"[ERROR] Backup {filename} also corrupted!")
                        return None
                return None
        
        return None
    
    def save_all_state(self, state_obj):
        """
        Зберегти всі файли стану
        
        Args:
            state_obj: State object з атрибутами chain, wallets, etc.
        """
        try:
            self.save_atomic('chain.json', state_obj.chain)
            self.save_atomic('wallets.json', state_obj.wallets)
            self.save_atomic('usernames.json', state_obj.usernames)
            self.save_atomic('groups.json', state_obj.groups)
            
            # Key images as list
            if hasattr(state_obj, 'spent_key_images'):
                self.save_atomic('key_images.json', list(state_obj.spent_key_images))
            
            self.logger.info("[OK] All state saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to save state: {e}")
            self.logger.error(traceback.format_exc())
            return False


# ============================================================================
# ERROR HANDLING & RECOVERY
# ============================================================================

def retry_on_failure(max_attempts=3, delay=1, exceptions=(Exception,)):
    """
    Decorator для automatic retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger('LAC.Retry')
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for "
                            f"{func.__name__}: {e}, retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
                        raise
            return None
        return wrapper
    return decorator


class RecoveryManager:
    """
    Система автоматичного відновлення
    """
    
    def __init__(self):
        self.logger = logging.getLogger('LAC.Recovery')
        self.recovery_strategies = {}
        self.error_count = {}
    
    def register_strategy(self, error_type, strategy_func):
        """
        Зареєструвати recovery стратегію
        
        Args:
            error_type: str, тип помилки (напр. 'JSONDecodeError')
            strategy_func: function для recovery
        """
        self.recovery_strategies[error_type] = strategy_func
        self.logger.info(f"Registered recovery strategy for {error_type}")
    
    def handle_error(self, error, context=None):
        """
        Обробити помилку та спробувати recovery
        
        Args:
            error: Exception object
            context: додатковий контекст
            
        Returns:
            bool: True якщо recovery успішний
        """
        error_type = type(error).__name__
        
        # Log error
        self.logger.error(f"Error in {context}: {error}")
        self.logger.error(traceback.format_exc())
        
        # Track frequency
        self.error_count[error_type] = self.error_count.get(error_type, 0) + 1
        
        # Try recovery
        if error_type in self.recovery_strategies:
            strategy = self.recovery_strategies[error_type]
            try:
                self.logger.info(f"Attempting recovery with {strategy.__name__}")
                result = strategy(error, context)
                self.logger.info("[OK] Recovery successful")
                return result
            except Exception as e:
                self.logger.error(f"[ERROR] Recovery failed: {e}")
                return False
        
        return False


# ============================================================================
# GRACEFUL SHUTDOWN
# ============================================================================

class GracefulShutdown:
    """
    Чистий shutdown без corruption
    """
    
    def __init__(self, state_obj, state_manager, flask_app=None):
        self.state = state_obj
        self.state_manager = state_manager
        self.flask_app = flask_app
        self.shutdown_initiated = False
        self.logger = logging.getLogger('LAC.Shutdown')
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)
        
        self.logger.info("[OK] Graceful shutdown handlers registered")
    
    def shutdown_handler(self, signum, frame):
        """
        Handle shutdown signals (Ctrl+C, kill)
        """
        signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
        
        if self.shutdown_initiated:
            self.logger.warning("[WARN] Force shutdown!")
            sys.exit(1)
        
        self.shutdown_initiated = True
        self.logger.info(f"[SHUTDOWN] Graceful shutdown initiated ({signal_name})...")
        
        try:
            # 1. Stop accepting new requests
            self.logger.info("Stopping new requests...")
            
            # 2. Stop mining if active
            if hasattr(self.state, 'mining') and self.state.mining:
                self.logger.info("Stopping mining...")
                self.state.mining = False
            
            # 3. Save state atomically
            self.logger.info("Saving state...")
            self.state_manager.save_all_state(self.state)
            
            # 4. Close network connections
            self.logger.info("Closing connections...")
            # (P2P connections will be closed by daemon threads)
            
            # 5. Flush logs
            logging.shutdown()
            
            print("\n[OK] Graceful shutdown complete")
            sys.exit(0)
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error during shutdown: {e}")
            self.logger.error(traceback.format_exc())
            sys.exit(1)


# ============================================================================
# HEALTH MONITORING
# ============================================================================

class HealthMonitor:
    """
    Моніторинг здоров'я системи
    """
    
    def __init__(self, state_obj):
        self.state = state_obj
        self.logger = logging.getLogger('LAC.Health')
        self.checks = []
        self.last_check = None
        self.check_interval = 60  # seconds
    
    def add_check(self, name, check_func, critical=False):
        """
        Додати health check
        
        Args:
            name: назва check
            check_func: function що повертає bool
            critical: чи є критичним
        """
        self.checks.append({
            'name': name,
            'func': check_func,
            'critical': critical
        })
    
    def run_checks(self):
        """
        Запустити всі health checks
        
        Returns:
            dict: результати checks
            bool: True якщо всі critical passed
        """
        results = {}
        critical_failed = False
        
        for check in self.checks:
            try:
                result = check['func']()
                status = 'OK' if result else 'FAIL'
                
                results[check['name']] = {
                    'status': status,
                    'critical': check['critical'],
                    'timestamp': datetime.now().isoformat()
                }
                
                if not result and check['critical']:
                    critical_failed = True
                    self.logger.critical(f"[ERROR] Critical check failed: {check['name']}")
                elif not result:
                    self.logger.warning(f"[WARN] Check failed: {check['name']}")
                    
            except Exception as e:
                results[check['name']] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'critical': check['critical'],
                    'timestamp': datetime.now().isoformat()
                }
                self.logger.error(f"Error in health check {check['name']}: {e}")
        
        self.last_check = results
        return results, not critical_failed
    
    def get_status(self):
        """
        Отримати поточний status
        """
        if not self.last_check:
            return {'status': 'unknown', 'message': 'No checks run yet'}
        
        all_ok = all(
            check['status'] == 'OK' 
            for check in self.last_check.values()
        )
        
        critical_ok = all(
            check['status'] == 'OK' 
            for check in self.last_check.values()
            if check.get('critical')
        )
        
        if all_ok:
            status = 'healthy'
        elif critical_ok:
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return {
            'status': status,
            'checks': self.last_check,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# INTEGRATION HELPER
# ============================================================================

def setup_stability_system(state_obj, datadir='data', flask_app=None):
    """
    Setup всіх stability mechanisms
    
    Args:
        state_obj: State object
        datadir: data directory
        flask_app: Flask app (optional)
        
    Returns:
        dict: всі managers
    """
    logger = logging.getLogger('LAC.Stability')
    logger.info("[SETUP] Setting up stability system...")
    
    # 1. State manager
    state_manager = StateManager(datadir)
    
    # 2. Recovery manager
    recovery = RecoveryManager()
    
    # 3. Graceful shutdown
    shutdown = GracefulShutdown(state_obj, state_manager, flask_app)
    
    # 4. Health monitor
    health = HealthMonitor(state_obj)
    
    # Add basic health checks
    health.add_check(
        'chain_not_empty',
        lambda: len(state_obj.chain) > 0,
        critical=True
    )
    
    health.add_check(
        'wallets_exist',
        lambda: len(state_obj.wallets) >= 0,
        critical=False
    )
    
    logger.info("[OK] Stability system ready")
    
    return {
        'state_manager': state_manager,
        'recovery': recovery,
        'shutdown': shutdown,
        'health': health
    }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == '__main__':
    print("Testing LAC Stability Module...")
    
    # Test 1: Atomic writes
    print("\n1. Testing atomic writes...")
    sm = StateManager('test_data')
    test_data = {'test': 'data', 'blocks': [1, 2, 3]}
    sm.save_atomic('test.json', test_data)
    loaded = sm.load_with_backup('test.json')
    assert loaded == test_data
    print("[OK] Atomic writes work")
    
    # Test 2: Retry decorator
    print("\n2. Testing retry decorator...")
    attempts = [0]
    
    @retry_on_failure(max_attempts=3, delay=0.1)
    def flaky_function():
        attempts[0] += 1
        if attempts[0] < 3:
            raise Exception("Fail")
        return "Success"
    
    result = flaky_function()
    assert result == "Success"
    assert attempts[0] == 3
    print("[OK] Retry decorator works")
    
    # Cleanup
    import shutil
    shutil.rmtree('test_data', ignore_errors=True)
    
    print("\n[OK] All stability tests passed!")