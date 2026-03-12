class LACDatabaseSafe:
    def __init__(self, *a, **kw):
        self.enabled = False
    def get_height(self): return -1
    def sync_from_json(self, *a, **kw): pass
    def get_stats(self): return {'enabled': False}
