#!/usr/bin/env python3
"""
Entry point for running the monitoring agent
"""
import os
import dotenv
dotenv.load_dotenv()


import argparse
from agent.agent import MonitoringAgent


def main():
    parser = argparse.ArgumentParser(description="Monitoring Agent")
    parser.add_argument("--agent-id", type=str, default="agent-001", help="Agent ID")
    
    # Get defaults from environment variables
    grpc_server_host = os.getenv("GRPC_SERVER_HOST", "localhost")
    grpc_server_port = os.getenv("GRPC_SERVER_PORT", "50051")
    default_server = f"{grpc_server_host}:{grpc_server_port}"
    
    parser.add_argument(
        "--server", type=str, default=default_server, help="gRPC server address"
    )
    parser.add_argument(
        "--etcd-host",
        type=str,
        default=os.getenv("ETCD_HOST", "localhost"),
        help="etcd server hostname (default: ETCD_HOST env var or localhost)",
    )
    parser.add_argument(
        "--etcd-port",
        type=int,
        default=int(os.getenv("ETCD_PORT", "2379")),
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
        agent_id=args.agent_id,
        server_address=args.server,
        etcd_host=args.etcd_host,
        etcd_port=args.etcd_port,
        config_key=args.config_key,
    )
    agent.initialize()
    agent.run()


if __name__ == "__main__":
    main()
