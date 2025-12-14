"""
gRPC Server module - Receives data from agents and forwards to Kafka
"""

from .server import MonitoringServicer, serve

__all__ = ["MonitoringServicer", "serve"]
