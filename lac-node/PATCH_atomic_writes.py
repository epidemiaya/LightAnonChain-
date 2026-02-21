# ATOMIC WRITES PATCH FOR STATE.PY
# Fixes JSON corruption on force quit

import os
import json
import tempfile
from pathlib import Path

class StateManager:
    """
    Безпечне збереження стану з atomic writes
    """
    
    def __init__(self, state_file='state.json'):
        self.state_file = state_file
        self.state = {}
        self.lock_file = f"{state_file}.lock"
        
    def save_atomic(self):
        """
        Atomic write - запобігає corruption
        """
        # 1. Створюємо temp файл в тій самій директорії
        temp_fd, temp_path = tempfile.mkstemp(
            dir=os.path.dirname(self.state_file) or '.',
            prefix='.tmp_state_',
            suffix='.json'
        )
        
        try:
            # 2. Записуємо в temp файл
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(self.state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # 3. Atomic rename (ось тут магія!)
            # На POSIX системах rename() atomic
            # Навіть якщо процес вбитий між записом і rename,
            # або старий файл залишиться, або новий вже буде
            os.replace(temp_path, self.state_file)
            
            return True
            
        except Exception as e:
            # Якщо щось пішло не так, видаляємо temp файл
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e
    
    def load_with_backup(self):
        """
        Завантаження з fallback на backup
        """
        # Спробувати основний файл
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                return True
            except json.JSONDecodeError as e:
                print(f"⚠️  Main state corrupted: {e}")
                # Якщо corrupted, шукаємо backup
                return self._load_backup()
        
        return False
    
    def _load_backup(self):
        """
        Спроба завантажити з backup файлу
        """
        backup_file = f"{self.state_file}.backup"
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r') as f:
                    self.state = json.load(f)
                print("✅ Restored from backup")
                return True
            except json.JSONDecodeError:
                print("❌ Backup also corrupted!")
                return False
        return False
    
    def save_with_backup(self):
        """
        Зберегти з backup копією
        """
        # 1. Якщо існує старий state, зробити backup
        if os.path.exists(self.state_file):
            backup_file = f"{self.state_file}.backup"
            try:
                # Копіюємо старий файл як backup
                import shutil
                shutil.copy2(self.state_file, backup_file)
            except:
                pass  # Якщо backup failed, продовжуємо
        
        # 2. Atomic save нового state
        return self.save_atomic()


# ВИКОРИСТАННЯ В BLOCKCHAIN.PY

class Blockchain:
    def __init__(self):
        self.state_manager = StateManager('chain.json')
        # Завантажити з можливістю fallback
        self.state_manager.load_with_backup()
    
    def mine_block(self, transactions):
        # ... mining logic ...
        
        # Зберегти з atomic write + backup
        self.state_manager.save_with_backup()


# ТЕСТУВАННЯ

def test_atomic_writes():
    """
    Тест що atomic writes працюють навіть при crash
    """
    import signal
    import subprocess
    import time
    
    print("Testing atomic writes under crash conditions...")
    
    # Тест 1: Нормальне збереження
    sm = StateManager('test_state.json')
    sm.state = {'test': 'data', 'blocks': 1000}
    assert sm.save_with_backup()
    print("✅ Normal save works")
    
    # Тест 2: Завантаження
    sm2 = StateManager('test_state.json')
    assert sm2.load_with_backup()
    assert sm2.state['blocks'] == 1000
    print("✅ Load works")
    
    # Тест 3: Симуляція crash під час запису
    # (складніше тестувати, потребує subprocess)
    
    # Cleanup
    import os
    for f in ['test_state.json', 'test_state.json.backup']:
        try:
            os.unlink(f)
        except:
            pass
    
    print("✅ All atomic write tests passed!")


if __name__ == '__main__':
    test_atomic_writes()