"""
Shared module - Contains protocol definitions and configuration
"""

from . import monitoring_pb2
from . import monitoring_pb2_grpc

__all__ = [
    "monitoring_pb2",
    "monitoring_pb2_grpc",
]
