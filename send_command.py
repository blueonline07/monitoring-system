"""
Command Sender - Send START/STOP commands to agents via gRPC server
"""

import sys

from shared import monitoring_pb2
from grpc_server.server import get_server_servicer


def send_command(agent_id: str, command_type: str):
    """
    Send START or STOP command to an agent

    Args:
        agent_id: Target agent ID
        command_type: "start" or "stop"
    """
    servicer = get_server_servicer()

    if servicer is None:
        print("✗ Server not running")
        return False

    # Parse command type
    command_type = command_type.lower()
    if command_type == "start":
        cmd_type = monitoring_pb2.START
    elif command_type == "stop":
        cmd_type = monitoring_pb2.STOP
    else:
        print(f"✗ Invalid command type: {command_type} (must be 'start' or 'stop')")
        return False

    print(f"📤 Sending {command_type.upper()} command to agent: {agent_id}")

    # Send command
    success = servicer.send_command_to_agent(agent_id, cmd_type)

    if success:
        print("✓ Command sent successfully")
        return True
    else:
        print("✗ Failed to send command (agent may not be connected)")
        return False


def main():
    """Main entry point for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Send START/STOP commands to agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start an agent
  python3 send_command.py --agent-id agent-001 --command start

  # Stop an agent
  python3 send_command.py --agent-id agent-001 --command stop
        """,
    )

    parser.add_argument(
        "--agent-id",
        type=str,
        required=True,
        help="Target agent ID",
    )
    parser.add_argument(
        "--command",
        type=str,
        required=True,
        choices=["start", "stop"],
        help="Command to send (start or stop)",
    )

    args = parser.parse_args()

    # Send command
    success = send_command(
        agent_id=args.agent_id,
        command_type=args.command,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
