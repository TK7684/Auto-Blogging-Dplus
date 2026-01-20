import hashlib
import json
import os
import time

class CacheManager:
    """
    Manages a simple JSON-based file cache for API responses.
    """
    def __init__(self, cache_file="api_cache.json"):
        self.cache_file = cache_file
        self.cache = {}
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Cache save failed: {e}")

    def _generate_key(self, prompt, model_name):
        """Generates a unique hash for the prompt + model combination."""
        content = f"{model_name}:{prompt}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get(self, prompt, model_name):
        key = self._generate_key(prompt, model_name)
        return self.cache.get(key)

    def set(self, prompt, model_name, response_text):
        key = self._generate_key(prompt, model_name)
        self.cache[key] = {
            "response": response_text,
            "timestamp": time.time()
        }
        self._save_cache()
