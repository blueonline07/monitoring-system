"""
Base plugin class for monitoring agent plugins
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from shared import monitoring_pb2


class BasePlugin(ABC):
    """Base class for all monitoring agent plugins"""
    
    def __init__(self):
        """Initialize stats tracking"""
        self.stats = {
            'processed': 0,
            'passed': 0,
            'dropped': 0
        }
    
    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin with optional configuration
        
        Args:
            config: Optional configuration dictionary
        """
        pass
    
    def run(self, metrics_request: monitoring_pb2.MetricsRequest) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics request. Can modify, filter, or return None to drop.
        Automatically tracks stats (processed/passed/dropped).
        
        Subclasses should override process() instead of this method.
        
        Args:
            metrics_request: The metrics request to process
            
        Returns:
            Modified MetricsRequest or None to drop the request
        """
        self.stats['processed'] += 1
        result = self.process(metrics_request)
        
        if result is None:
            self.stats['dropped'] += 1
        else:
            self.stats['passed'] += 1
        
        return result
    
    @abstractmethod
    def process(self, metrics_request: monitoring_pb2.MetricsRequest) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics request. Can modify, filter, or return None to drop.
        
        This method should be overridden by subclasses to implement plugin logic.
        
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

