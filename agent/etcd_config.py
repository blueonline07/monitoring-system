"""
etcd Configuration Manager - handles reading and watching configuration from etcd
"""

import json
import threading
import time
from typing import Dict, Any, Optional
import etcd3


class EtcdConfigManager:
    """Manages configuration from etcd with real-time updates and thread-safe access"""

    def __init__(
        self,
        hostname: str,
        etcd_host: str,
        etcd_port: int,
        config_key: Optional[str] = None,
    ):
        """
        Initialize etcd configuration manager

        Args:
            hostname: Agent identifier for config key
            etcd_host: etcd server hostname (defaults to ETCD_HOST env var or localhost)
            etcd_port: etcd server port (defaults to ETCD_PORT env var or 2379)
            config_key: Full config key path (if None, uses /monitor/config/<hostname>)
        """
        self.etcd_host = etcd_host
        self.etcd_port = etcd_port
        self.hostname = hostname

        # Default config key format: /monitor/config/<hostname>
        self.config_key = config_key or f"/monitor/config/{hostname}"

        # Thread-safe configuration storage
        self._config: Dict[str, Any] = {}
        self._config_lock = threading.RLock()  # Reader-writer lock for config access
        self._watch_id = None

        # Initialize etcd client
        self.etcd = etcd3.client(host=etcd_host, port=etcd_port)

    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration (thread-safe)

        Returns:
            Current configuration dictionary
        """
        with self._config_lock:
            return self._config.copy()

    def _update_config(self, new_config: Dict[str, Any]):
        """
        Update configuration (thread-safe, internal use)

        Args:
            new_config: New configuration dictionary
        """
        with self._config_lock:
            self._config = new_config.copy()

    def store_config(self, config: Dict[str, Any]) -> bool:
        """
        Store configuration to etcd

        Args:
            config: Configuration dictionary to store

        Returns:
            True if successful, False otherwise
        """
        try:
            self.etcd.put(self.config_key, json.dumps(config, indent=2))
            self._update_config(config)
            print(f"Stored config to etcd: {self.config_key}")
            return True
        except Exception as e:
            print(f"Error storing config to etcd: {e}")
            return False

    def load_initial_config(self, store_defaults: bool = True) -> Dict[str, Any]:
        """
        Load initial configuration from etcd

        Args:
            store_defaults: If True, store default config to etcd when not found

        Returns:
            Configuration dictionary
        """
        try:
            value, _ = self.etcd.get(self.config_key)
            if value:
                config = json.loads(value.decode("utf-8"))
                self._update_config(config)
                print(f"Loaded initial config from etcd: {self.config_key}")
                return config
            else:
                print(f"No config found at {self.config_key}, using defaults")
                default_config = self._get_default_config()
                self._update_config(default_config)
                # Store default config to etcd if requested
                if store_defaults:
                    self.store_config(default_config)
                return default_config
        except Exception as e:
            print(f"Error loading config from etcd: {e}")
            default_config = self._get_default_config()
            self._update_config(default_config)
            # Store default config to etcd if requested (even on error)
            if store_defaults:
                try:
                    self.store_config(default_config)
                except Exception as store_error:
                    print(f"Error storing default config to etcd: {store_error}")
            return default_config

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration

        Returns:
            Default configuration dictionary
        """
        return {
            "interval": 5,
            "metrics": [
                "cpu",
                "memory",
                "disk read",
                "disk write",
                "net in",
                "net out",
            ],
            "plugins": [],
            "thresholds": {
                "cpu_percent": 80.0,
                "memory_percent": 85.0,
                "disk_read_mb": 100.0,
                "disk_write_mb": 100.0,
                "net_in_mb": 50.0,
                "net_out_mb": 50.0,
            },
            "min_cpu": 5.0,
            "min_memory": 5.0,
            "window_size": 5,
        }

    def _watch_config_callback(self, watch_response):
        """
        Callback for etcd watch events

        Args:
            watch_response: etcd watch response
        """
        for event in watch_response.events:
            if isinstance(event, etcd3.events.PutEvent):
                try:
                    new_config = json.loads(event.value.decode("utf-8"))
                    self._update_config(new_config)
                    print(f"Config updated from etcd: {self.config_key}")
                    print(f"  New config: {new_config}")
                except Exception as e:
                    print(f"Error parsing config update: {e}")
            elif isinstance(event, etcd3.events.DeleteEvent):
                print(f"Config deleted from etcd: {self.config_key}, using defaults")
                self._update_config(self._get_default_config())

    def start_watching(self):
        """Start watching for configuration changes in etcd"""
        try:
            self._watch_id = self.etcd.add_watch_callback(
                self.config_key, self._watch_config_callback
            )
            print(f"Started watching config key: {self.config_key}")
        except Exception as e:
            print(f"Error starting config watch: {e}")

    def stop_watching(self):
        """Stop watching for configuration changes"""
        if self._watch_id is not None:
            try:
                self.etcd.cancel_watch(self._watch_id)
                print("Stopped watching config")
            except Exception as e:
                print(f"Error stopping config watch: {e}")
            finally:
                self._watch_id = None

    def save_heartbeat(self) -> bool:
        """
        Save heartbeat signal to etcd

        Returns:
            True if successful, False otherwise
        """
        try:
            heartbeat_key = f"/monitor/heartbeat/{self.hostname}"
            timestamp = str(int(time.time()))
            self.etcd.put(heartbeat_key, timestamp)
            print(
                f"Saved heartbeat to etcd: key: {heartbeat_key} value: {self.etcd.get(heartbeat_key)}"
            )
            return True
        except Exception as e:
            print(f"Error saving heartbeat to etcd: {e}")
            return False

    def close(self):
        """Close etcd connection and cleanup"""
        self.stop_watching()
        # etcd3 client doesn't have an explicit close method, but we can clear references
        try:
            heartbeat_key = f"/monitor/heartbeat/{self.hostname}"
            self.etcd.put(f"/monitor/heartbeat/{self.hostname}", str(-1))
            print(
                f"Saved heartbeat to etcd: key: {heartbeat_key} value: {self.etcd.get(heartbeat_key)}"
            )
        except Exception as e:
            print(f"Error saving heartbeat to etcd: {e}")
        self.etcd = None
