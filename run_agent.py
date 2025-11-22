#!/usr/bin/env python3
"""
Entry point for running the monitoring agent
"""
import argparse
from agent.agent import MonitoringAgent


def main():
    parser = argparse.ArgumentParser(description="Monitoring Agent")
    parser.add_argument("--agent-id", type=str, default="agent-001", help="Agent ID")
    parser.add_argument(
        "--server", type=str, default="localhost:50051", help="gRPC server address"
    )
    parser.add_argument(
        "--interval", type=int, default=5, help="Metrics collection interval (seconds)"
    )
    
    args = parser.parse_args()
    
    # Configuration - should be loaded from etcd in production
    # Format matches the specification from the lab document
    config = {
        "interval": args.interval,
        "metrics": [
            "cpu",
            "memory",
            "disk read",
            "disk write",
            "net in",
            "net out",
        ],
        "plugins": [
            "agent.plugins.deduplication.DeduplicationPlugin",
        ],
    }
    
    # Create and run agent
    agent = MonitoringAgent(args.agent_id, args.server, config)
    agent.initialize()
    agent.run()


if __name__ == "__main__":
    main()
