"""
Plugin Manager - loads and manages plugins dynamically
"""

import importlib
import threading
from typing import List, Dict, Any, Optional
from protobuf import monitoring_pb2
from agent.plugins.base import BasePlugin


class PluginManager:
    """Manages plugin loading and execution"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plugin manager

        Args:
            config: Configuration dictionary containing plugin paths
        """
        self.config = config
        self.plugins: List[BasePlugin] = []
        self._plugins_lock = threading.Lock()

    def load_plugins(self, config: Optional[Dict[str, Any]] = None):
        """
        Load all plugins specified in configuration

        Args:
            config: Optional configuration dictionary (uses self.config if not provided)
        """
        if config is None:
            config = self.config

        plugin_paths = config.get("plugins", [])

        with self._plugins_lock:
            # Finalize existing plugins
            for plugin in self.plugins:
                try:
                    plugin.finalize()
                except Exception as e:
                    print(f"Error finalizing plugin {plugin.__class__.__name__}: {e}")

            # Clear and reload plugins
            self.plugins = []

            for cls_path in plugin_paths:
                plugin_cls = self._resolve_class(cls_path)
                if plugin_cls:
                    plugin = plugin_cls()
                    plugin.initialize(config)
                    self.plugins.append(plugin)
                    print(f"✓ Loaded plugin: {cls_path}")
                else:
                    print(f"✗ Failed to load plugin: {cls_path}")

    def _resolve_class(self, cls_path: str):
        """
        Resolve plugin class from module path

        Args:
            cls_path: Full path to plugin class (e.g., "agent.plugins.deduplication.DeduplicationPlugin")

        Returns:
            Plugin class or None if not found
        """
        try:
            module_name, class_name = cls_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            return getattr(module, class_name, None)
        except Exception as e:
            print(f"Error resolving plugin class {cls_path}: {e}")
            return None

    def process_metrics(
        self, metrics_request: monitoring_pb2.MetricsRequest
    ) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics through all loaded plugins (thread-safe)

        Args:
            metrics_request: The metrics request to process

        Returns:
            Processed MetricsRequest or None if dropped by a plugin
        """
        with self._plugins_lock:
            result = metrics_request

            for plugin in self.plugins:
                if result is None:
                    break
                result = plugin.run(result)

            return result

    def finalize_all(self):
        """Finalize all loaded plugins (thread-safe)"""
        with self._plugins_lock:
            for plugin in self.plugins:
                try:
                    plugin.finalize()
                except Exception as e:
                    print(f"Error finalizing plugin {plugin.__class__.__name__}: {e}")
