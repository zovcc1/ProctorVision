import json
import os
from pathlib import Path
from typing import Any, Dict
import threading

class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self._config_path = config_path or os.path.join(
            os.path.dirname(__file__), 'config.json'
        )
        self._config: Dict[str, Any] = {}
        self._listeners = []
        self._config_lock = threading.RLock()
        self._load()

    def _load(self):
        with self._config_lock:
            base_dir = Path(__file__).resolve().parent.parent.parent
            config_file = Path(self._config_path)
            if not config_file.is_absolute():
                config_file = base_dir / config_file
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Failed to load config: {e}")
                self._config = {}

    def reload(self):
        self._load()
        for listener in self._listeners:
            try:
                listener(self._config)
            except Exception as e:
                print(f"Config listener error: {e}")

    def get(self, key: str = None, default: Any = None) -> Any:
        with self._config_lock:
            if key is None:
                return dict(self._config)
            keys = key.split('.')
            val = self._config
            for k in keys:
                if isinstance(val, dict) and k in val:
                    val = val[k]
                else:
                    return default
            return val

    def set(self, key: str, value: Any):
        with self._config_lock:
            keys = key.split('.')
            cfg = self._config
            for k in keys[:-1]:
                if k not in cfg or not isinstance(cfg[k], dict):
                    cfg[k] = {}
                cfg = cfg[k]
            cfg[keys[-1]] = value
        self._save()

    def update(self, updates: Dict[str, Any]):
        with self._config_lock:
            self._deep_update(self._config, updates)
        self._save()
        self.reload()

    def _deep_update(self, base: Dict, updates: Dict):
        for k, v in updates.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

    def _save(self):
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_file = Path(self._config_path)
        if not config_file.is_absolute():
            config_file = base_dir / config_file
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def add_listener(self, callback):
        self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

# Global instance
config = ConfigManager()
