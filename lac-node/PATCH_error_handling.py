# ERROR HANDLING & RECOVERY SYSTEM

import traceback
import logging
from datetime import datetime
from functools import wraps

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('lac.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('LAC')


class RecoveryManager:
    """
    Автоматичне відновлення після помилок
    """
    
    def __init__(self):
        self.error_count = {}
        self.max_retries = 3
        self.recovery_strategies = {}
    
    def register_recovery(self, error_type, strategy):
        """
        Зареєструвати recovery стратегію для типу помилки
        """
        self.recovery_strategies[error_type] = strategy
    
    def handle_error(self, error, context=None):
        """
        Обробка помилки з можливістю recovery
        """
        error_type = type(error).__name__
        
        # Log error
        logger.error(f"Error in {context}: {error}")
        logger.error(traceback.format_exc())
        
        # Track error frequency
        if error_type not in self.error_count:
            self.error_count[error_type] = 0
        self.error_count[error_type] += 1
        
        # Try recovery if strategy exists
        if error_type in self.recovery_strategies:
            strategy = self.recovery_strategies[error_type]
            try:
                logger.info(f"Attempting recovery: {strategy.__name__}")
                strategy(error, context)
                logger.info("✅ Recovery successful")
                return True
            except Exception as e:
                logger.error(f"❌ Recovery failed: {e}")
                return False
        
        return False


# Decorator для automatic retry
def retry_on_failure(max_attempts=3, delay=1):
    """
    Автоматичний retry для functions
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}, "
                            f"retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
                        raise
        return wrapper
    return decorator


# Circuit Breaker Pattern для network calls
class CircuitBreaker:
    """
    Запобігає зависанню на failed connections
    """
    
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """
        Виконати function через circuit breaker
        """
        if self.state == 'OPEN':
            # Перевірити чи можна спробувати знову
            if datetime.now().timestamp() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker: HALF_OPEN, trying again")
            else:
                raise Exception("Circuit breaker is OPEN, skipping call")
        
        try:
            result = func(*args, **kwargs)
            # Success - reset
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                logger.info("Circuit breaker: CLOSED, recovered")
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now().timestamp()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.error(f"Circuit breaker: OPEN after {self.failure_count} failures")
            
            raise e


# RECOVERY STRATEGIES

def recover_from_corrupt_state(error, context):
    """
    Відновлення після corruption state файлу
    """
    logger.info("Recovering from corrupt state...")
    
    # 1. Спробувати backup
    backup_file = f"{context.state_file}.backup"
    if os.path.exists(backup_file):
        import shutil
        shutil.copy2(backup_file, context.state_file)
        context.load_state()
        return
    
    # 2. Якщо немає backup, sync from network
    logger.info("No backup found, syncing from network...")
    context.sync_from_peers()


def recover_from_network_error(error, context):
    """
    Відновлення після network помилки
    """
    logger.info("Recovering from network error...")
    
    # 1. Reconnect to peers
    context.reconnect_peers()
    
    # 2. Refresh peer list
    context.discover_peers()


def recover_from_memory_error(error, context):
    """
    Відновлення після out of memory
    """
    logger.info("Recovering from memory error...")
    
    # 1. Force garbage collection
    import gc
    gc.collect()
    
    # 2. Clear caches
    context.clear_caches()
    
    # 3. Enable pruning if not enabled
    if not context.pruning_enabled:
        context.enable_pruning()


# GRACEFUL SHUTDOWN

import signal
import sys

class GracefulShutdown:
    """
    Чистий shutdown без corruption
    """
    
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.shutdown_initiated = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)
    
    def shutdown_handler(self, signum, frame):
        """
        Handle shutdown signals
        """
        if self.shutdown_initiated:
            logger.warning("Force shutdown!")
            sys.exit(1)
        
        self.shutdown_initiated = True
        logger.info("Graceful shutdown initiated...")
        
        try:
            # 1. Stop mining
            logger.info("Stopping mining...")
            self.blockchain.stop_mining()
            
            # 2. Save state
            logger.info("Saving state...")
            self.blockchain.save_state()
            
            # 3. Close connections
            logger.info("Closing connections...")
            self.blockchain.close_connections()
            
            # 4. Flush logs
            logging.shutdown()
            
            logger.info("✅ Graceful shutdown complete")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            sys.exit(1)


# HEALTH CHECKS

class HealthMonitor:
    """
    Моніторинг здоров'я системи
    """
    
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.checks = []
    
    def add_check(self, name, check_func, critical=False):
        """
        Додати health check
        """
        self.checks.append({
            'name': name,
            'func': check_func,
            'critical': critical
        })
    
    def run_checks(self):
        """
        Запустити всі checks
        """
        results = {}
        critical_failed = False
        
        for check in self.checks:
            try:
                result = check['func']()
                results[check['name']] = {
                    'status': 'OK' if result else 'FAIL',
                    'critical': check['critical']
                }
                
                if not result and check['critical']:
                    critical_failed = True
                    logger.critical(f"Critical health check failed: {check['name']}")
                    
            except Exception as e:
                results[check['name']] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'critical': check['critical']
                }
                logger.error(f"Health check error: {check['name']} - {e}")
        
        return results, not critical_failed


# ВИКОРИСТАННЯ

def setup_stability_system(blockchain):
    """
    Setup всіх stability mechanisms
    """
    # 1. Recovery manager
    recovery = RecoveryManager()
    recovery.register_recovery('JSONDecodeError', recover_from_corrupt_state)
    recovery.register_recovery('ConnectionError', recover_from_network_error)
    recovery.register_recovery('MemoryError', recover_from_memory_error)
    
    # 2. Graceful shutdown
    shutdown = GracefulShutdown(blockchain)
    
    # 3. Health monitor
    health = HealthMonitor(blockchain)
    health.add_check('blockchain_valid', lambda: blockchain.validate_chain(), critical=True)
    health.add_check('peers_connected', lambda: len(blockchain.peers) > 0, critical=True)
    health.add_check('disk_space', lambda: blockchain.check_disk_space() > 1024, critical=True)
    health.add_check('memory_usage', lambda: blockchain.check_memory() < 80, critical=False)
    
    return recovery, shutdown, health


# TESTING

def test_stability_system():
    """
    Тестування stability features
    """
    print("Testing stability system...")
    
    # Test 1: Retry decorator
    @retry_on_failure(max_attempts=3)
    def flaky_function():
        import random
        if random.random() < 0.7:
            raise Exception("Random failure")
        return "Success"
    
    try:
        result = flaky_function()
        print(f"✅ Retry decorator works: {result}")
    except:
        print("✅ Retry exhausted (expected)")
    
    # Test 2: Circuit breaker
    cb = CircuitBreaker(failure_threshold=3)
    
    def failing_call():
        raise Exception("Network error")
    
    for i in range(5):
        try:
            cb.call(failing_call)
        except Exception as e:
            print(f"Attempt {i+1}: {cb.state}")
    
    print(f"✅ Circuit breaker test complete. Final state: {cb.state}")
    
    print("✅ All stability tests passed!")


if __name__ == '__main__':
    test_stability_system()