from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, RequestError
import json


class ElasticsearchClient:
    """Client for indexing and searching agent metrics in Elasticsearch"""

    def __init__(self, host: str = "localhost", port: int = 9200, index_name: str = "agent-metrics"):
        """
        Initialize Elasticsearch client

        Args:
            host: Elasticsearch host (default: localhost)
            port: Elasticsearch port (default: 9200)
            index_name: Name of the index to use (default: agent-metrics)
        """
        self.host = host
        self.port = port
        self.es = Elasticsearch([f"http://{host}:{port}"])
        self.index_name = index_name
        self._ensure_index_exists()

    def _ensure_index_exists(self):
        """Create index if it doesn't exist with proper mapping"""
        if not self.es.indices.exists(index=self.index_name):
            try:
                mapping = {
                    "mappings": {
                        "properties": {
                            "agent": {"type": "keyword"},
                            "agent_id": {"type": "integer"},
                            "timestamp": {"type": "date"},
                            "cpu": {"type": "float"},
                            "memory": {"type": "float"},
                            "disk_read": {"type": "float"},
                            "disk_write": {"type": "float"},
                            "net_in": {"type": "float"},
                            "net_out": {"type": "float"},
                        }
                    }
                }
                self.es.indices.create(index=self.index_name, body=mapping)
                print(f"Created index: {self.index_name}")
            except RequestError as e:
                print(f"Error creating index: {e}")

    def index_metric(
        self,
        agent: str,
        agent_id: int,
        timestamp: int,
        cpu: float,
        memory: float,
        disk_read: float,
        disk_write: float,
        net_in: float,
        net_out: float,
    ) -> bool:
        """
        Index a single metric document

        Args:
            agent: Agent name/identifier
            agent_id: Agent ID
            timestamp: Unix timestamp
            cpu: CPU usage percentage
            memory: Memory usage percentage
            disk_read: Disk read rate (MB/s)
            disk_write: Disk write rate (MB/s)
            net_in: Network input rate (MB/s)
            net_out: Network output rate (MB/s)

        Returns:
            True if successful, False otherwise
        """
        try:
            doc = {
                "agent": agent,
                "agent_id": agent_id,
                "timestamp": datetime.fromtimestamp(timestamp),
                "cpu": cpu,
                "memory": memory,
                "disk_read": disk_read,
                "disk_write": disk_write,
                "net_in": net_in,
                "net_out": net_out,
            }
            self.es.index(index=self.index_name, document=doc)
            return True
        except Exception as e:
            print(f"Error indexing metric: {e}")
            return False

    def index_metrics_batch(self, metrics: List[Dict[str, Any]]) -> int:
        """
        Index multiple metrics in a batch

        Args:
            metrics: List of metric dictionaries

        Returns:
            Number of successfully indexed documents
        """
        from elasticsearch.helpers import bulk

        actions = []
        for metric in metrics:
            doc = {
                "_index": self.index_name,
                "_source": {
                    "agent": metric.get("agent", ""),
                    "agent_id": metric.get("agent_id", 0),
                    "timestamp": datetime.fromtimestamp(metric.get("timestamp", datetime.now().timestamp())),
                    "cpu": metric.get("cpu", 0.0),
                    "memory": metric.get("memory", 0.0),
                    "disk_read": metric.get("disk_read", 0.0),
                    "disk_write": metric.get("disk_write", 0.0),
                    "net_in": metric.get("net_in", 0.0),
                    "net_out": metric.get("net_out", 0.0),
                },
            }
            actions.append(doc)

        try:
            success, failed = bulk(self.es, actions, raise_on_error=False)
            print(f"Indexed {success} documents, {len(failed)} failed")
            return success
        except Exception as e:
            print(f"Error bulk indexing: {e}")
            return 0

    def search_all(self, size: int = 100) -> List[Dict[str, Any]]:
        """
        Search all documents

        Args:
            size: Maximum number of results to return

        Returns:
            List of search results
        """
        try:
            response = self.es.search(index=self.index_name, body={"query": {"match_all": {}}}, size=size)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def search_by_agent(self, agent: str, size: int = 100) -> List[Dict[str, Any]]:
        """
        Search metrics by agent name

        Args:
            agent: Agent name to search for
            size: Maximum number of results to return

        Returns:
            List of search results
        """
        try:
            query = {"query": {"term": {"agent": agent}}}
            response = self.es.search(index=self.index_name, body=query, size=size)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            print(f"Error searching by agent: {e}")
            return []

    def search_by_time_range(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search metrics within a time range

        Args:
            start_time: Start datetime (default: 1 hour ago)
            end_time: End datetime (default: now)
            size: Maximum number of results to return

        Returns:
            List of search results
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        try:
            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": start_time.isoformat(),
                            "lte": end_time.isoformat(),
                        }
                    }
                },
                "sort": [{"timestamp": {"order": "asc"}}],
            }
            response = self.es.search(index=self.index_name, body=query, size=size)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            print(f"Error searching by time range: {e}")
            return []

    def search_by_threshold(
        self,
        metric_name: str,
        threshold: float,
        operator: str = "gt",
        size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search metrics that exceed a threshold

        Args:
            metric_name: Name of the metric (cpu, memory, disk_read, etc.)
            threshold: Threshold value
            operator: Comparison operator (gt, gte, lt, lte)
            size: Maximum number of results to return

        Returns:
            List of search results
        """
        try:
            query = {
                "query": {
                    "range": {
                        metric_name: {
                            operator: threshold,
                        }
                    }
                },
                "sort": [{metric_name: {"order": "desc"}}],
            }
            response = self.es.search(index=self.index_name, body=query, size=size)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            print(f"Error searching by threshold: {e}")
            return []

    def search_aggregated_stats(
        self,
        agent: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics (avg, min, max) for all metrics

        Args:
            agent: Optional agent name to filter by
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            Dictionary with aggregated statistics
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": start_time.isoformat(),
                                    "lte": end_time.isoformat(),
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "cpu_stats": {"stats": {"field": "cpu"}},
                "memory_stats": {"stats": {"field": "memory"}},
                "disk_read_stats": {"stats": {"field": "disk_read"}},
                "disk_write_stats": {"stats": {"field": "disk_write"}},
                "net_in_stats": {"stats": {"field": "net_in"}},
                "net_out_stats": {"stats": {"field": "net_out"}},
            },
        }

        if agent:
            query["query"]["bool"]["must"].append({"term": {"agent": agent}})

        try:
            response = self.es.search(index=self.index_name, body=query, size=0)
            aggs = response["aggregations"]
            return {
                "cpu": aggs["cpu_stats"],
                "memory": aggs["memory_stats"],
                "disk_read": aggs["disk_read_stats"],
                "disk_write": aggs["disk_write_stats"],
                "net_in": aggs["net_in_stats"],
                "net_out": aggs["net_out_stats"],
            }
        except Exception as e:
            print(f"Error getting aggregated stats: {e}")
            return {}

    def get_index_info(self) -> Dict[str, Any]:
        """
        Get information about the index

        Returns:
            Dictionary with index information
        """
        try:
            stats = self.es.indices.stats(index=self.index_name)
            count = self.es.count(index=self.index_name)
            return {
                "index_name": self.index_name,
                "document_count": count["count"],
                "size": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
            }
        except Exception as e:
            print(f"Error getting index info: {e}")
            return {}

    def delete_index(self) -> bool:
        """
        Delete the index (use with caution!)

        Returns:
            True if successful
        """
        try:
            self.es.indices.delete(index=self.index_name)
            print(f"Deleted index: {self.index_name}")
            return True
        except Exception as e:
            print(f"Error deleting index: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = ElasticsearchClient(host="localhost", port=9200)

    # Check connection
    try:
        if client.es.ping():
            print("Connected to Elasticsearch!")
        else:
            print("Failed to connect to Elasticsearch")
            exit(1)
    except ConnectionError:
        print("Cannot connect to Elasticsearch. Make sure it's running.")
        exit(1)

    # Example: Index a single metric
    print("\n--- Indexing a metric ---")
    client.index_metric(
        agent="agent-1",
        agent_id=1,
        timestamp=int(datetime.now().timestamp()),
        cpu=45.5,
        memory=60.2,
        disk_read=10.5,
        disk_write=5.3,
        net_in=2.1,
        net_out=1.8,
    )

    # Example: Search all metrics
    print("\n--- Searching all metrics ---")
    results = client.search_all(size=10)
    print(f"Found {len(results)} metrics")
    for result in results[:3]:
        print(json.dumps(result, indent=2, default=str))

    # Example: Search by agent
    print("\n--- Searching by agent ---")
    agent_results = client.search_by_agent("agent-1", size=5)
    print(f"Found {len(agent_results)} metrics for agent-1")

    # Example: Search by time range
    print("\n--- Searching by time range (last hour) ---")
    time_results = client.search_by_time_range(size=10)
    print(f"Found {len(time_results)} metrics in the last hour")

    # Example: Search by threshold
    print("\n--- Searching metrics with CPU > 50% ---")
    high_cpu = client.search_by_threshold("cpu", 50.0, "gt", size=10)
    print(f"Found {len(high_cpu)} metrics with CPU > 50%")

    # Example: Get aggregated statistics
    print("\n--- Aggregated statistics ---")
    stats = client.search_aggregated_stats()
    print(json.dumps(stats, indent=2, default=str))

    # Example: Get index info
    print("\n--- Index information ---")
    info = client.get_index_info()
    print(json.dumps(info, indent=2, default=str))

