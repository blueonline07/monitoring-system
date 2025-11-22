"""
Base plugin class for monitoring agent plugins
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from shared import monitoring_pb2


class BasePlugin(ABC):
    """Base class for all monitoring agent plugins"""
    
    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin with optional configuration
        
        Args:
            config: Optional configuration dictionary
        """
        pass
    
    @abstractmethod
    def run(self, metrics_request: monitoring_pb2.MetricsRequest) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics request. Can modify, filter, or return None to drop.
        
        Args:
            metrics_request: The metrics request to process
            
        Returns:
            Modified MetricsRequest or None to drop the request
        """
        pass
    
    @abstractmethod
    def finalize(self):
        """
        Cleanup resources and finalize plugin execution
        """
        pass

