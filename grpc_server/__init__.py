"""
gRPC Server module - Receives data from agents and forwards to Kafka
"""

from .server import MonitoringService, serve

__all__ = ["MonitoringService", "serve"]
