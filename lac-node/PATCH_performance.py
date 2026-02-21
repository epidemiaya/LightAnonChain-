# PERFORMANCE OPTIMIZATION PATCHES

import time
import hashlib
from functools import lru_cache, wraps
from collections import OrderedDict
import threading

# ============================================================================
# 1. CACHING SYSTEM
# ============================================================================

class LRUCache:
    """
    LRU Cache для blocks та transactions
    """
    
    def __init__(self, max_size=1000, maxsize=None):
        # Support both max_size and maxsize for compatibility
        if maxsize is not None:
            max_size = maxsize
        self.cache = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.lock = threading.Lock()
    
    def get(self, key):
        """
        Отримати з cache
        """
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
            return None
    
    def put(self, key, value):
        """
        Додати в cache
        """
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # Remove least recently used
                    self.cache.popitem(last=False)
            self.cache[key] = value
    
    def clear(self):
        """
        Очистити cache
        """
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def stats(self):
        """
        Cache statistics
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.2f}%",
            'size': len(self.cache)
        }


class BlockchainCache:
    """
    Multi-layer caching для blockchain
    """
    
    def __init__(self):
        self.blocks = LRUCache(max_size=1000)  # Last 1000 blocks
        self.transactions = LRUCache(max_size=5000)  # Last 5000 tx
        self.balances = LRUCache(max_size=10000)  # 10K addresses
        self.usernames = {}  # Small enough to keep all in memory
    
    def get_block(self, block_hash):
        """Get block from cache"""
        return self.blocks.get(block_hash)
    
    def cache_block(self, block_hash, block):
        """Cache block"""
        self.blocks.put(block_hash, block)
    
    def get_balance(self, address):
        """Get balance from cache"""
        return self.balances.get(address)
    
    def cache_balance(self, address, balance):
        """Cache balance"""
        self.balances.put(address, balance)
    
    def clear_all(self):
        """Clear all caches"""
        self.blocks.clear()
        self.transactions.clear()
        self.balances.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        return {
            'blocks': self.blocks.stats(),
            'transactions': self.transactions.stats(),
            'balances': self.balances.stats()
        }


# ============================================================================
# 2. DATABASE INDEXING
# ============================================================================

class DatabaseOptimizer:
    """
    Оптимізація database queries
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.indexed_fields = set()
    
    def create_indexes(self):
        """
        Створити індекси для швидких lookups
        """
        indexes = [
            # Blocks
            ('blocks', 'block_hash'),
            ('blocks', 'block_height'),
            ('blocks', 'timestamp'),
            
            # Transactions
            ('transactions', 'tx_hash'),
            ('transactions', 'sender'),
            ('transactions', 'receiver'),
            ('transactions', 'block_height'),
            ('transactions', 'timestamp'),
            
            # Usernames
            ('usernames', 'username'),
            ('usernames', 'address'),
            
            # Balances
            ('balances', 'address'),
        ]
        
        for table, field in indexes:
            if (table, field) not in self.indexed_fields:
                self._create_index(table, field)
                self.indexed_fields.add((table, field))
    
    def _create_index(self, table, field):
        """
        Створити один index
        """
        index_name = f"idx_{table}_{field}"
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({field})"
        
        try:
            self.db.execute(query)
            logger.info(f"✅ Created index: {index_name}")
        except Exception as e:
            logger.error(f"❌ Failed to create index {index_name}: {e}")
    
    def optimize_query(self, query):
        """
        Аналізувати та оптимізувати query
        """
        # EXPLAIN QUERY PLAN
        explain = f"EXPLAIN QUERY PLAN {query}"
        result = self.db.execute(explain).fetchall()
        
        # Check if using index
        using_index = any('INDEX' in str(row) for row in result)
        if not using_index:
            logger.warning(f"Query not using index: {query}")
        
        return result


# ============================================================================
# 3. BATCH PROCESSING
# ============================================================================

class BatchProcessor:
    """
    Batch processing для transactions
    """
    
    def __init__(self, batch_size=100):
        self.batch_size = batch_size
        self.pending_transactions = []
        self.lock = threading.Lock()
    
    def add_transaction(self, tx):
        """
        Додати transaction до batch
        """
        with self.lock:
            self.pending_transactions.append(tx)
            
            if len(self.pending_transactions) >= self.batch_size:
                return self.flush()
        
        return None
    
    def flush(self):
        """
        Обробити всі pending transactions
        """
        with self.lock:
            if not self.pending_transactions:
                return None
            
            batch = self.pending_transactions.copy()
            self.pending_transactions.clear()
            
            return batch
    
    def process_batch(self, blockchain, batch):
        """
        Обробити batch of transactions
        """
        start_time = time.time()
        
        # Validate all transactions
        valid_txs = []
        for tx in batch:
            if blockchain.validate_transaction(tx):
                valid_txs.append(tx)
        
        # Process valid transactions
        if valid_txs:
            blockchain.add_transactions_batch(valid_txs)
        
        elapsed = time.time() - start_time
        tps = len(valid_txs) / elapsed if elapsed > 0 else 0
        
        logger.info(
            f"Processed batch: {len(valid_txs)}/{len(batch)} valid, "
            f"{tps:.2f} TPS"
        )
        
        return valid_txs


# ============================================================================
# 4. PARALLEL PROCESSING
# ============================================================================

import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

class ParallelValidator:
    """
    Parallel validation для transactions
    """
    
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
    
    def validate_transactions_parallel(self, transactions, blockchain):
        """
        Валідувати transactions паралельно
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all validation tasks
            futures = [
                executor.submit(blockchain.validate_transaction, tx)
                for tx in transactions
            ]
            
            # Collect results
            results = [future.result() for future in futures]
        
        # Return valid transactions
        return [tx for tx, valid in zip(transactions, results) if valid]
    
    def mine_blocks_parallel(self, num_processes=None):
        """
        Mining паралельно (CPU-intensive)
        """
        if num_processes is None:
            num_processes = multiprocessing.cpu_count()
        
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            # Each process tries different nonces
            futures = []
            for i in range(num_processes):
                start_nonce = i * 1000000
                end_nonce = (i + 1) * 1000000
                futures.append(
                    executor.submit(self._mine_range, start_nonce, end_nonce)
                )
            
            # Return first found block
            for future in futures:
                result = future.result()
                if result:
                    return result
        
        return None
    
    def _mine_range(self, start_nonce, end_nonce):
        """
        Mine в specific nonce range
        """
        # Mining logic here
        pass


# ============================================================================
# 5. MEMORY OPTIMIZATION
# ============================================================================

class MemoryOptimizer:
    """
    Оптимізація використання пам'яті
    """
    
    def __init__(self):
        self.compressed_blocks = {}
    
    def compress_old_blocks(self, blockchain, threshold=10000):
        """
        Compress blocks старші за threshold
        """
        import gzip
        import pickle
        
        current_height = blockchain.get_height()
        
        for height in range(current_height - threshold):
            block = blockchain.get_block_by_height(height)
            
            if block and height not in self.compressed_blocks:
                # Serialize and compress
                serialized = pickle.dumps(block)
                compressed = gzip.compress(serialized)
                
                self.compressed_blocks[height] = compressed
                
                # Remove from memory
                blockchain.remove_from_memory(height)
    
    def decompress_block(self, height):
        """
        Decompress block коли потрібен
        """
        import gzip
        import pickle
        
        if height in self.compressed_blocks:
            compressed = self.compressed_blocks[height]
            serialized = gzip.decompress(compressed)
            block = pickle.loads(serialized)
            return block
        
        return None
    
    def get_memory_usage(self):
        """
        Отримати memory usage
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        return {
            'rss': mem_info.rss / 1024 / 1024,  # MB
            'vms': mem_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
    
    def trigger_gc(self):
        """
        Force garbage collection
        """
        import gc
        collected = gc.collect()
        logger.info(f"Garbage collected: {collected} objects")
        return collected


# ============================================================================
# 6. NETWORK OPTIMIZATION
# ============================================================================

class NetworkOptimizer:
    """
    Оптимізація network передачі
    """
    
    def __init__(self):
        self.connection_pool = {}
        self.keepalive_timeout = 300  # 5 minutes
    
    def compress_data(self, data):
        """
        Compress data перед відправкою
        """
        import gzip
        import json
        
        json_data = json.dumps(data)
        compressed = gzip.compress(json_data.encode())
        
        compression_ratio = len(json_data) / len(compressed)
        logger.debug(f"Compression ratio: {compression_ratio:.2f}x")
        
        return compressed
    
    def decompress_data(self, compressed):
        """
        Decompress received data
        """
        import gzip
        import json
        
        decompressed = gzip.decompress(compressed)
        data = json.loads(decompressed.decode())
        
        return data
    
    def use_connection_pooling(self, peer_url):
        """
        Reuse connections замість створення нових
        """
        if peer_url in self.connection_pool:
            conn = self.connection_pool[peer_url]
            if conn.is_alive():
                return conn
        
        # Create new connection
        import requests
        session = requests.Session()
        session.headers.update({'Connection': 'keep-alive'})
        
        self.connection_pool[peer_url] = session
        return session
    
    def batch_network_requests(self, requests_list):
        """
        Batch multiple requests в один
        """
        # Combine multiple small requests into one large request
        batched = {
            'type': 'batch',
            'requests': requests_list
        }
        
        return batched


# ============================================================================
# 7. PROFILING & MONITORING
# ============================================================================

class PerformanceMonitor:
    """
    Моніторинг performance
    """
    
    def __init__(self):
        self.metrics = {
            'block_validation_time': [],
            'transaction_processing_time': [],
            'sync_speed': [],
            'cache_hit_rate': []
        }
    
    def profile_function(self, func):
        """
        Decorator для profiling functions
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            
            logger.debug(f"{func.__name__} took {elapsed:.4f}s")
            
            return result
        return wrapper
    
    def measure_tps(self, transactions, elapsed_time):
        """
        Виміряти TPS
        """
        tps = len(transactions) / elapsed_time if elapsed_time > 0 else 0
        self.metrics['tps'] = tps
        return tps
    
    def get_bottlenecks(self):
        """
        Знайти performance bottlenecks
        """
        bottlenecks = []
        
        # Check each metric
        for metric_name, values in self.metrics.items():
            if values:
                avg = sum(values) / len(values)
                max_val = max(values)
                
                # If max is much higher than average
                if max_val > avg * 2:
                    bottlenecks.append({
                        'metric': metric_name,
                        'avg': avg,
                        'max': max_val,
                        'ratio': max_val / avg
                    })
        
        return bottlenecks


# ============================================================================
# INTEGRATION
# ============================================================================

class PerformanceManager:
    """
    Інтеграція всіх performance optimizations
    """
    
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.cache = BlockchainCache()
        self.batch_processor = BatchProcessor(batch_size=100)
        self.parallel_validator = ParallelValidator(max_workers=4)
        self.memory_optimizer = MemoryOptimizer()
        self.network_optimizer = NetworkOptimizer()
        self.monitor = PerformanceMonitor()
    
    def optimize_all(self):
        """
        Застосувати всі optimizations
        """
        logger.info("Applying performance optimizations...")
        
        # 1. Create database indexes
        if hasattr(self.blockchain, 'db'):
            db_optimizer = DatabaseOptimizer(self.blockchain.db)
            db_optimizer.create_indexes()
        
        # 2. Enable caching
        self.blockchain.cache = self.cache
        
        # 3. Enable batch processing
        self.blockchain.batch_processor = self.batch_processor
        
        # 4. Compress old blocks
        self.memory_optimizer.compress_old_blocks(self.blockchain)
        
        # 5. Force GC
        self.memory_optimizer.trigger_gc()
        
        logger.info("✅ Performance optimizations applied")
    
    def get_performance_report(self):
        """
        Отримати performance report
        """
        return {
            'cache_stats': self.cache.get_stats(),
            'memory_usage': self.memory_optimizer.get_memory_usage(),
            'bottlenecks': self.monitor.get_bottlenecks()
        }


# TESTING
def test_performance():
    """
    Тест performance optimizations
    """
    print("Testing performance optimizations...")
    
    # Test 1: Cache
    cache = LRUCache(max_size=100)
    for i in range(150):
        cache.put(f"key_{i}", f"value_{i}")
    
    # Should have 100 items (LRU)
    assert len(cache.cache) == 100
    
    # Test hit/miss
    cache.get("key_149")  # Hit
    cache.get("key_0")    # Miss (evicted)
    
    stats = cache.stats()
    print(f"✅ Cache stats: {stats}")
    
    # Test 2: Batch processor
    batch = BatchProcessor(batch_size=10)
    for i in range(25):
        result = batch.add_transaction({'tx': i})
        if result:
            print(f"✅ Batch flushed with {len(result)} transactions")
    
    # Test 3: Memory optimizer
    mem_opt = MemoryOptimizer()
    usage = mem_opt.get_memory_usage()
    print(f"✅ Memory usage: {usage['rss']:.2f} MB")
    
    print("✅ All performance tests passed!")


if __name__ == '__main__':
    test_performance()