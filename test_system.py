#!/usr/bin/env python3
"""
Comprehensive system test with detailed logging to identify bugs
"""

import os
import sys
import time
import logging
import subprocess
import signal

# Set up comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('test_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test 1: Verify all imports work"""
    logger.info("=" * 60)
    logger.info("TEST 1: Testing imports")
    logger.info("=" * 60)
    
    try:
        logger.debug("Importing shared.monitoring_pb2...")
        from shared import monitoring_pb2
        logger.info("✓ shared.monitoring_pb2 imported successfully")
        
        logger.debug("Importing shared.monitoring_pb2_grpc...")
        from shared import monitoring_pb2_grpc
        logger.info("✓ shared.monitoring_pb2_grpc imported successfully")
        
        logger.debug("Importing shared.config...")
        from shared.config import KafkaTopics
        logger.info(f"✓ KafkaTopics imported: {KafkaTopics.MONITORING_DATA}")
        
        logger.debug("Importing agent modules...")
        from agent import agent, collect, etcd_config, grpc, plugin_manager
        logger.info("✓ All agent modules imported successfully")
        
        logger.debug("Importing server modules...")
        from grpc_server import server, kafka_producer
        logger.info("✓ All server modules imported successfully")
        
        logger.debug("Importing analysis modules...")
        from analysis_app import consumer
        logger.info("✓ Analysis consumer imported successfully")
        
        return True
    except Exception as e:
        logger.error(f"✗ Import test failed: {e}", exc_info=True)
        return False

def test_etcd_connection():
    """Test 2: Verify etcd connection"""
    logger.info("=" * 60)
    logger.info("TEST 2: Testing etcd connection")
    logger.info("=" * 60)
    
    try:
        import etcd3
        logger.debug("Connecting to etcd at localhost:2379...")
        client = etcd3.client(host='localhost', port=2379)
        
        logger.debug("Testing etcd put/get...")
        test_key = "/test/connection"
        test_value = "test-value"
        client.put(test_key, test_value)
        logger.debug(f"Put key: {test_key} = {test_value}")
        
        value, metadata = client.get(test_key)
        logger.debug(f"Got key: {test_key} = {value}")
        
        if value and value.decode('utf-8') == test_value:
            logger.info("✓ etcd connection successful")
            client.delete(test_key)
            return True
        else:
            logger.error(f"✗ etcd value mismatch: expected {test_value}, got {value}")
            return False
            
    except Exception as e:
        logger.error(f"✗ etcd connection test failed: {e}", exc_info=True)
        return False

def test_kafka_connection():
    """Test 3: Verify Kafka connection"""
    logger.info("=" * 60)
    logger.info("TEST 3: Testing Kafka connection")
    logger.info("=" * 60)
    
    try:
        from confluent_kafka import Producer, Consumer, KafkaError
        from shared.config import KafkaTopics
        
        logger.debug("Creating Kafka producer...")
        producer = Producer({'bootstrap.servers': 'localhost:9092'})
        
        logger.debug(f"Producing test message to topic {KafkaTopics.MONITORING_DATA}...")
        test_message = '{"test": "message"}'
        producer.produce(
            KafkaTopics.MONITORING_DATA,
            value=test_message.encode('utf-8'),
            callback=lambda err, msg: logger.debug(f"Delivery callback: err={err}, msg={msg}")
        )
        producer.flush()
        logger.info("✓ Kafka producer works")
        
        logger.debug("Creating Kafka consumer...")
        consumer = Consumer({
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'test-group',
            'auto.offset.reset': 'latest'
        })
        consumer.subscribe([KafkaTopics.MONITORING_DATA])
        logger.info("✓ Kafka consumer works")
        
        consumer.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Kafka connection test failed: {e}", exc_info=True)
        return False

def test_setup_etcd_config():
    """Test 4: Test setup_etcd_config.py"""
    logger.info("=" * 60)
    logger.info("TEST 4: Testing setup_etcd_config.py")
    logger.info("=" * 60)
    
    try:
        logger.debug("Running setup_etcd_config.py for test-agent...")
        result = subprocess.run(
            ['python3', 'setup_etcd_config.py', '--agent-id', 'test-agent', '--interval', '5'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        logger.debug(f"Return code: {result.returncode}")
        logger.debug(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.debug(f"STDERR: {result.stderr}")
        
        if result.returncode == 0:
            logger.info("✓ setup_etcd_config.py executed successfully")
            
            # Verify config was written
            import etcd3
            import json
            client = etcd3.client()
            value, _ = client.get('/monitor/config/test-agent')
            if value:
                config = json.loads(value.decode('utf-8'))
                logger.debug(f"Config written: {config}")
                logger.info("✓ Config verified in etcd")
                return True
            else:
                logger.error("✗ Config not found in etcd")
                return False
        else:
            logger.error(f"✗ setup_etcd_config.py failed with code {result.returncode}")
            return False
            
    except Exception as e:
        logger.error(f"✗ setup_etcd_config test failed: {e}", exc_info=True)
        return False

def test_agent_modules():
    """Test 5: Test agent modules individually"""
    logger.info("=" * 60)
    logger.info("TEST 5: Testing agent modules")
    logger.info("=" * 60)
    
    try:
        # Test metrics collector
        logger.debug("Testing metrics collector...")
        from agent.collect import MetricCollector
        collector = MetricCollector(agent_id='test-agent', active_metrics=['cpu', 'memory'])
        metrics_dict = collector.collect_metrics()
        logger.debug(f"Collected metrics: cpu={metrics_dict['cpu_percent']}%, memory={metrics_dict['memory_percent']}%")
        logger.info("✓ MetricCollector works")
        
        # Test plugin manager
        logger.debug("Testing plugin manager...")
        from agent.plugin_manager import PluginManager
        test_config = {'plugins': ['agent.plugins.deduplication.DeduplicationPlugin']}
        pm = PluginManager(config=test_config)
        logger.debug("Loading plugins...")
        pm.load_plugins()
        logger.debug(f"Loaded plugins: {[p.__class__.__name__ for p in pm.plugins]}")
        logger.info("✓ PluginManager works")
        
        # Test etcd config manager
        logger.debug("Testing etcd config manager...")
        from agent.etcd_config import EtcdConfigManager
        config_mgr = EtcdConfigManager(agent_id='test-agent')
        logger.debug("Getting config from etcd...")
        config = config_mgr.get_config()
        logger.debug(f"Got config: interval={config.get('interval')}, metrics={config.get('metrics')}")
        logger.info("✓ EtcdConfigManager works")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Agent modules test failed: {e}", exc_info=True)
        return False

def test_grpc_protobuf():
    """Test 6: Test protobuf message creation"""
    logger.info("=" * 60)
    logger.info("TEST 6: Testing protobuf messages")
    logger.info("=" * 60)
    
    try:
        from shared import monitoring_pb2
        
        logger.debug("Creating MetricsRequest...")
        request = monitoring_pb2.MetricsRequest(
            agent_id="test-agent",
            timestamp=int(time.time()),
            metrics=monitoring_pb2.SystemMetrics(
                cpu_percent=50.0,
                memory_percent=60.0,
                memory_used_mb=4096.0,
                memory_total_mb=8192.0,
                disk_read_mb=100.0,
                disk_write_mb=50.0,
                net_in_mb=200.0,
                net_out_mb=100.0
            )
        )
        
        logger.debug(f"MetricsRequest created: agent_id={request.agent_id}, cpu={request.metrics.cpu_percent}%")
        logger.info("✓ Protobuf messages work")
        return True
        
    except Exception as e:
        logger.error(f"✗ Protobuf test failed: {e}", exc_info=True)
        return False

def main():
    """Run all tests"""
    logger.info("\n")
    logger.info("*" * 70)
    logger.info("STARTING COMPREHENSIVE SYSTEM TESTS")
    logger.info("*" * 70)
    logger.info("\n")
    
    tests = [
        ("Imports", test_imports),
        ("etcd Connection", test_etcd_connection),
        ("Kafka Connection", test_kafka_connection),
        ("Setup etcd Config", test_setup_etcd_config),
        ("Agent Modules", test_agent_modules),
        ("gRPC Protobuf", test_grpc_protobuf),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}", exc_info=True)
            results[test_name] = False
    
    # Summary
    logger.info("\n")
    logger.info("*" * 70)
    logger.info("TEST SUMMARY")
    logger.info("*" * 70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status:10} - {test_name}")
    
    logger.info("-" * 70)
    logger.info(f"Results: {passed}/{total} tests passed")
    logger.info("*" * 70)
    logger.info("\n")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! System is working correctly.")
        return 0
    else:
        logger.error(f"❌ {total - passed} test(s) failed. Check logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
