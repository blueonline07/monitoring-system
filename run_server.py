#!/usr/bin/env python3
"""
Entry point for running the gRPC server
"""

from config import Config

if __name__ == "__main__":
    from grpc_server.server import serve

    serve(port=Config.PORT)
