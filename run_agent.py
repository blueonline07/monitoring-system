#!/usr/bin/env python3
"""
Entry point for running the monitoring agent
"""
import argparse
import socket
from shared.config import Config
from agent.agent import MonitoringAgent


def main():
    parser = argparse.ArgumentParser(description="Monitoring Agent")
    
    # Get defaults from environment variables
    grpc_server_host = Config.HOST
    grpc_server_port = Config.PORT
    default_server = f"{grpc_server_host}:{grpc_server_port}"
    
    parser.add_argument(
        "--server", type=str, default=default_server, help="gRPC server address"
    )
    parser.add_argument(
        "--etcd-host",
        type=str,
        default=Config.ETCD_HOST,
        help="etcd server hostname (default: ETCD_HOST env var or localhost)",
    )
    parser.add_argument(
        "--etcd-port",
        type=int,
        default=Config.ETCD_PORT,
        help="etcd server port (default: ETCD_PORT env var or 2379)",
    )
    parser.add_argument(
        "--config-key",
        type=str,
        default=None,
        help="Custom etcd config key (default: /monitor/config/<hostname>)",
    )

    args = parser.parse_args()

    # Create and run agent with etcd configuration
    agent = MonitoringAgent(
        hostname=socket.gethostname(),
        server_address=args.server,
        etcd_host=args.etcd_host,
        etcd_port=args.etcd_port,
        config_key=args.config_key,
    )
    agent.initialize()
    agent.run()


if __name__ == "__main__":
    main()
