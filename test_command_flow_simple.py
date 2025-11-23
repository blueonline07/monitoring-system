#!/usr/bin/env python3
"""
Simple Command Flow Test - Assumes server and agent are already running
Usage:
  Terminal 1: python run_server.py
  Terminal 2: python run_agent.py --agent-id test-cmd-agent
  Terminal 3: python test_command_flow_simple.py
"""

import os
import sys
import time
import subprocess
from datetime import datetime

# Set protobuf environment variable for etcd3 compatibility
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

def log(message):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] {message}")

def run_command(description, command):
    """Run a shell command and return result"""
    log(f"{description}...")
    result = subprocess.run(
        command,
        shell=True,
        executable='/bin/bash',
        capture_output=True,
        text=True,
        timeout=10
    )
    return result

def main():
    log("="*70)
    log("COMMAND FLOW TEST - Simple Version")
    log("="*70)
    log("Prerequisites:")
    log("  1. Docker/Kafka running: docker compose up -d")
    log("  2. gRPC Server running: python run_server.py")
    log("  3. Agent running: python run_agent.py --agent-id test-cmd-agent")
    log("="*70)
    
    agent_id = "test-cmd-agent"
    tests_passed = []
    tests_failed = []
    
    try:
        # Wait a moment for things to stabilize
        log("\nWaiting 2 seconds for connections to stabilize...")
        time.sleep(2)
        
        # Test 1: Send STATUS command
        log("\n[TEST 1] Sending STATUS command...")
        result = run_command(
            "Sending STATUS",
            f"source venv/bin/activate && python run_analysis.py send-command {agent_id} STATUS"
        )
        
        if result.returncode == 0:
            log("✓ STATUS command sent successfully")
            log(f"Output: {result.stdout.strip()}")
            tests_passed.append("STATUS command")
        else:
            log(f"✗ Failed to send STATUS command")
            log(f"Error: {result.stderr.strip()}")
            tests_failed.append("STATUS command")
        
        time.sleep(2)
        
        # Test 2: Send STOP command
        log("\n[TEST 2] Sending STOP command...")
        result = run_command(
            "Sending STOP",
            f"source venv/bin/activate && python run_analysis.py send-command {agent_id} STOP"
        )
        
        if result.returncode == 0:
            log("✓ STOP command sent successfully")
            log(f"Output: {result.stdout.strip()}")
            tests_passed.append("STOP command")
        else:
            log(f"✗ Failed to send STOP command")
            log(f"Error: {result.stderr.strip()}")
            tests_failed.append("STOP command")
        
        time.sleep(3)
        
        # Test 3: Check if metrics stopped (should see fewer/no metrics)
        log("\n[TEST 3] Checking metrics after STOP (should be paused)...")
        result = run_command(
            "Getting metrics",
            f"source venv/bin/activate && timeout 5 python run_analysis.py get-metrics"
        )
        log(f"Metrics output: {result.stdout[:200]}...")
        
        # Test 4: Send START command
        log("\n[TEST 4] Sending START command...")
        result = run_command(
            "Sending START",
            f"source venv/bin/activate && python run_analysis.py send-command {agent_id} START"
        )
        
        if result.returncode == 0:
            log("✓ START command sent successfully")
            log(f"Output: {result.stdout.strip()}")
            tests_passed.append("START command")
        else:
            log(f"✗ Failed to send START command")
            log(f"Error: {result.stderr.strip()}")
            tests_failed.append("START command")
        
        time.sleep(3)
        
        # Test 5: Check if metrics resumed (should see metrics flowing)
        log("\n[TEST 5] Checking metrics after START (should be flowing)...")
        result = run_command(
            "Getting metrics",
            f"source venv/bin/activate && timeout 5 python run_analysis.py get-metrics"
        )
        
        if result.returncode in [0, 124]:  # 124 is timeout, which is OK
            if "CPU:" in result.stdout or "agent_id" in result.stdout:
                log("✓ Metrics are flowing after START")
                tests_passed.append("Metrics resumed")
            else:
                log("⚠ No metrics found after START")
                tests_failed.append("Metrics resumed")
        else:
            log(f"✗ Failed to get metrics")
            tests_failed.append("Metrics resumed")
        
        log(f"Metrics output: {result.stdout[:300]}...")
        
        # Test 6: Send UPDATE_CONFIG command
        log("\n[TEST 6] Sending UPDATE_CONFIG command...")
        result = run_command(
            "Sending UPDATE_CONFIG",
            f"source venv/bin/activate && python run_analysis.py send-command {agent_id} UPDATE_CONFIG"
        )
        
        if result.returncode == 0:
            log("✓ UPDATE_CONFIG command sent successfully")
            log(f"Output: {result.stdout.strip()}")
            tests_passed.append("UPDATE_CONFIG command")
        else:
            log(f"✗ Failed to send UPDATE_CONFIG command")
            log(f"Error: {result.stderr.strip()}")
            tests_failed.append("UPDATE_CONFIG command")
        
        time.sleep(2)
        
        # Test 7: Send RESTART command
        log("\n[TEST 7] Sending RESTART command...")
        result = run_command(
            "Sending RESTART",
            f"source venv/bin/activate && python run_analysis.py send-command {agent_id} RESTART"
        )
        
        if result.returncode == 0:
            log("✓ RESTART command sent successfully")
            log(f"Output: {result.stdout.strip()}")
            tests_passed.append("RESTART command")
        else:
            log(f"✗ Failed to send RESTART command")
            log(f"Error: {result.stderr.strip()}")
            tests_failed.append("RESTART command")
        
        time.sleep(3)
        
        # Summary
        log("\n" + "="*70)
        log("TEST SUMMARY")
        log("="*70)
        log(f"✓ Passed: {len(tests_passed)}")
        for test in tests_passed:
            log(f"  ✓ {test}")
        
        log(f"\n✗ Failed: {len(tests_failed)}")
        for test in tests_failed:
            log(f"  ✗ {test}")
        
        log("="*70)
        
        if len(tests_failed) == 0:
            log("\n🎉 ALL TESTS PASSED! Command flow is working correctly.")
            log("\nNext steps:")
            log("  1. Check Terminal 1 (server) for [COMMAND] logs")
            log("  2. Check Terminal 2 (agent) for command handling logs")
            log("  3. Verify logs show proper command flow")
            return 0
        else:
            log(f"\n❌ {len(tests_failed)} TEST(S) FAILED.")
            log("\nDebugging steps:")
            log("  1. Check Terminal 1 (server) for errors")
            log("  2. Check Terminal 2 (agent) for errors")
            log("  3. Verify Kafka is running: docker compose ps")
            return 1
            
    except KeyboardInterrupt:
        log("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        log(f"\n\nTest error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
