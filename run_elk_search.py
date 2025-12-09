import sys
import json
import argparse
from datetime import datetime, timedelta
from elk.elk_search import ElasticsearchClient
from elasticsearch.exceptions import ConnectionError


def format_metric(result: dict) -> str:
    """Format một metric result để hiển thị"""
    agent = result.get("agent", "unknown")
    timestamp = result.get("timestamp", "")
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except:
            pass
    
    if isinstance(timestamp, datetime):
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    else:
        timestamp_str = str(timestamp)
    
    return f"""
[{agent}] {timestamp_str}
  CPU: {result.get('cpu', 0):.2f}% | Memory: {result.get('memory', 0):.2f}%
  Disk: R={result.get('disk_read', 0):.2f}MB/s W={result.get('disk_write', 0):.2f}MB/s
  Network: In={result.get('net_in', 0):.2f}MB/s Out={result.get('net_out', 0):.2f}MB/s"""


def search_all(client: ElasticsearchClient, args):
    """Search tất cả metrics"""
    results = client.search_all(size=args.size)
    print(f"\n✓ Found {len(results)} metrics\n")
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for result in results:
            print(format_metric(result))


def search_by_agent(client: ElasticsearchClient, args):
    """Search theo agent"""
    results = client.search_by_agent(args.agent, size=args.size)
    print(f"\n✓ Found {len(results)} metrics for agent '{args.agent}'\n")
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for result in results:
            print(format_metric(result))


def search_by_time(client: ElasticsearchClient, args):
    """Search theo khoảng thời gian"""
    # Parse time range
    end_time = datetime.now()
    if args.end:
        try:
            end_time = datetime.fromisoformat(args.end)
        except ValueError as e:
            print(f"Error: Invalid end time format: '{args.end}'")
            print(f"  Expected format: YYYY-MM-DDTHH:MM:SS (e.g., 2025-12-09T12:50:00)")
            print(f"  Error details: {e}")
            return
    
    if args.hours:
        start_time = end_time - timedelta(hours=args.hours)
    elif args.start:
        try:
            start_time = datetime.fromisoformat(args.start)
        except ValueError as e:
            print(f"Error: Invalid start time format: '{args.start}'")
            print(f"  Expected format: YYYY-MM-DDTHH:MM:SS (e.g., 2025-12-09T12:42:00)")
            print(f"  Error details: {e}")
            return
    else:
        start_time = end_time - timedelta(hours=1)  # Default: last hour
    
    results = client.search_by_time_range(start_time, end_time, size=args.size)
    print(f"\n✓ Found {len(results)} metrics from {start_time} to {end_time}\n")
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for result in results:
            print(format_metric(result))


def search_by_threshold(client: ElasticsearchClient, args):
    """Search metrics vượt ngưỡng"""
    results = client.search_by_threshold(
        args.metric, args.threshold, args.operator, size=args.size
    )
    operator_symbol = {
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
    }.get(args.operator, args.operator)
    
    print(f"\n✓ Found {len(results)} metrics with {args.metric} {operator_symbol} {args.threshold}\n")
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for result in results:
            print(format_metric(result))


def get_stats(client: ElasticsearchClient, args):
    """Lấy thống kê tổng hợp"""
    start_time = None
    end_time = None
    
    if args.hours:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=args.hours)
    elif args.start or args.end:
        if args.start:
            try:
                start_time = datetime.fromisoformat(args.start)
            except ValueError as e:
                print(f"Error: Invalid start time format: '{args.start}'")
                print(f"  Expected format: YYYY-MM-DDTHH:MM:SS (e.g., 2025-12-09T12:42:00)")
                print(f"  Error details: {e}")
                return
        if args.end:
            try:
                end_time = datetime.fromisoformat(args.end)
            except ValueError as e:
                print(f"Error: Invalid end time format: '{args.end}'")
                print(f"  Expected format: YYYY-MM-DDTHH:MM:SS (e.g., 2025-12-09T12:50:00)")
                print(f"  Error details: {e}")
                return
    
    stats = client.search_aggregated_stats(
        agent=args.agent, start_time=start_time, end_time=end_time
    )
    
    if not stats:
        print("No statistics available")
        return
    
    print("\n=== Aggregated Statistics ===\n")
    
    for metric_name, metric_stats in stats.items():
        print(f"{metric_name.upper()}:")
        print(f"  Count: {metric_stats.get('count', 0)}")
        print(f"  Min: {metric_stats.get('min', 0):.2f}")
        print(f"  Max: {metric_stats.get('max', 0):.2f}")
        print(f"  Avg: {metric_stats.get('avg', 0):.2f}")
        print(f"  Sum: {metric_stats.get('sum', 0):.2f}")
        print()


def get_info(client: ElasticsearchClient, args):
    """Lấy thông tin về index"""
    info = client.get_index_info()
    
    if args.json:
        print(json.dumps(info, indent=2, default=str))
    else:
        print("\n=== Index Information ===\n")
        print(f"Index Name: {info.get('index_name', 'N/A')}")
        print(f"Document Count: {info.get('document_count', 0):,}")
        size_bytes = info.get('size', 0)
        size_mb = size_bytes / (1024 * 1024)
        print(f"Size: {size_mb:.2f} MB ({size_bytes:,} bytes)")


def main():
    parser = argparse.ArgumentParser(
        description="Elasticsearch Search CLI - Tìm kiếm metrics từ Elasticsearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search tất cả metrics
  python run_elk_search.py search-all --size 10

  # Search theo agent
  python run_elk_search.py search-agent --agent agent-1

  # Search theo thời gian (last 2 hours)
  python run_elk_search.py search-time --hours 2

  # Search metrics với CPU > 50%
  python run_elk_search.py search-threshold --metric cpu --threshold 50 --operator gt

  # Search metrics với CPU < 20% (bé hơn)
  python run_elk_search.py search-threshold --metric cpu --threshold 20 --operator lt

  # Search metrics với Memory <= 30% (bé hơn hoặc bằng)
  python run_elk_search.py search-threshold --metric memory --threshold 30 --operator lte

  # Lấy thống kê tổng hợp
  python run_elk_search.py stats --hours 24

  # Lấy thông tin index
  python run_elk_search.py info
        """,
    )

    parser.add_argument(
        "--es-host",
        type=str,
        default="localhost",
        help="Elasticsearch host (default: localhost)",
    )
    parser.add_argument(
        "--es-port",
        type=int,
        default=9200,
        help="Elasticsearch port (default: 9200)",
    )
    parser.add_argument(
        "--index",
        type=str,
        default="agent-metrics",
        help="Elasticsearch index name (default: agent-metrics)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Commands")

    # Search all
    search_all_parser = subparsers.add_parser("search-all", help="Search tất cả metrics")
    search_all_parser.add_argument("--size", type=int, default=100, help="Số lượng kết quả")

    # Search by agent
    search_agent_parser = subparsers.add_parser("search-agent", help="Search theo agent")
    search_agent_parser.add_argument("--agent", type=str, required=True, help="Tên agent")
    search_agent_parser.add_argument("--size", type=int, default=100, help="Số lượng kết quả")

    # Search by time
    search_time_parser = subparsers.add_parser("search-time", help="Search theo thời gian")
    search_time_parser.add_argument(
        "--hours", type=float, help="Số giờ trước (ví dụ: 2.5 cho 2.5 giờ)"
    )
    search_time_parser.add_argument(
        "--start", type=str, help="Thời gian bắt đầu (ISO format: YYYY-MM-DDTHH:MM:SS)"
    )
    search_time_parser.add_argument(
        "--end", type=str, help="Thời gian kết thúc (ISO format: YYYY-MM-DDTHH:MM:SS)"
    )
    search_time_parser.add_argument("--size", type=int, default=100, help="Số lượng kết quả")

    # Search by threshold
    search_threshold_parser = subparsers.add_parser(
        "search-threshold", help="Search metrics vượt ngưỡng"
    )
    search_threshold_parser.add_argument(
        "--metric",
        type=str,
        required=True,
        choices=["cpu", "memory", "disk_read", "disk_write", "net_in", "net_out"],
        help="Tên metric",
    )
    search_threshold_parser.add_argument(
        "--threshold", type=float, required=True, help="Ngưỡng giá trị"
    )
    search_threshold_parser.add_argument(
        "--operator",
        type=str,
        default="gt",
        choices=["gt", "gte", "lt", "lte"],
        help="Toán tử so sánh (default: gt)",
    )
    search_threshold_parser.add_argument("--size", type=int, default=100, help="Số lượng kết quả")

    # Get stats
    stats_parser = subparsers.add_parser("stats", help="Lấy thống kê tổng hợp")
    stats_parser.add_argument(
        "--hours", type=float, help="Số giờ trước (ví dụ: 24 cho 24 giờ)"
    )
    stats_parser.add_argument(
        "--start", type=str, help="Thời gian bắt đầu (ISO format: YYYY-MM-DDTHH:MM:SS)"
    )
    stats_parser.add_argument(
        "--end", type=str, help="Thời gian kết thúc (ISO format: YYYY-MM-DDTHH:MM:SS)"
    )
    stats_parser.add_argument("--agent", type=str, help="Lọc theo agent (optional)")

    # Get info
    info_parser = subparsers.add_parser("info", help="Lấy thông tin về index")

    args = parser.parse_args()

    # Initialize client
    try:
        client = ElasticsearchClient(
            host=args.es_host, port=args.es_port, index_name=args.index
        )
        if not client.es.ping():
            print("ERROR: Cannot connect to Elasticsearch!")
            return 1
    except ConnectionError as e:
        print(f"ERROR: Cannot connect to Elasticsearch: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    # Execute command
    try:
        if args.command == "search-all":
            search_all(client, args)
        elif args.command == "search-agent":
            search_by_agent(client, args)
        elif args.command == "search-time":
            search_by_time(client, args)
        elif args.command == "search-threshold":
            search_by_threshold(client, args)
        elif args.command == "stats":
            get_stats(client, args)
        elif args.command == "info":
            get_info(client, args)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

