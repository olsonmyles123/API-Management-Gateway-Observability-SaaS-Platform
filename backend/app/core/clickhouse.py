import re
import datetime
import logging
import math
from typing import List, Dict, Any, Optional
import clickhouse_connect
from app.config import settings

logger = logging.getLogger("gateway.clickhouse")

_client = None
_use_mock = False

# In-Memory fallback telemetry buffer when ClickHouse server is offline
_in_memory_telemetry_log: List[Dict[str, Any]] = []


def get_clickhouse_client():
    """
    Returns ClickHouse client.
    Connects to configured host/port or falls back to robust in-memory OLAP simulation.
    """
    global _client, _use_mock
    if _client is not None:
        return _client

    if not _use_mock:
        try:
            client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                database=settings.CLICKHOUSE_DB,
                secure=settings.CLICKHOUSE_SECURE,
                connect_timeout=2,
                send_receive_timeout=5,
            )
            client.ping()
            _client = client
            logger.info(f"Connected to ClickHouse at {settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}")
            init_clickhouse_schema(_client)
            return _client
        except Exception as e:
            logger.warning(f"ClickHouse server unreachable ({e}). Using in-memory OLAP analytics engine for local environment.")
            _use_mock = True

    return None


def init_clickhouse_schema(client):
    """Provisions the api_telemetry table in ClickHouse."""
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {settings.CLICKHOUSE_TABLE} (
        timestamp DateTime64(3),
        tenant_id String,
        key_id String,
        method LowCardinality(String),
        route String,
        status_code UInt16,
        latency_ms Float64,
        client_ip String,
        request_size_bytes UInt32,
        response_size_bytes UInt32,
        user_agent String,
        error_message String
    ) ENGINE = MergeTree()
    ORDER BY (tenant_id, timestamp, route);
    """
    try:
        client.command(ddl)
        logger.info(f"ClickHouse table '{settings.CLICKHOUSE_TABLE}' verified/created")
    except Exception as e:
        logger.error(f"Error initializing ClickHouse DDL: {e}")


async def insert_telemetry_batch(rows: List[Dict[str, Any]]) -> bool:
    """
    Flushes a batch of telemetry records into ClickHouse api_telemetry table.
    """
    if not rows:
        return True

    client = get_clickhouse_client()
    if client is not None:
        try:
            columns = [
                "timestamp", "tenant_id", "key_id", "method", "route",
                "status_code", "latency_ms", "client_ip", "request_size_bytes",
                "response_size_bytes", "user_agent", "error_message"
            ]
            data = []
            for r in rows:
                ts = r.get("timestamp")
                if isinstance(ts, (int, float)):
                    ts_val = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                elif isinstance(ts, str):
                    try:
                        ts_val = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        ts_val = datetime.datetime.now(datetime.timezone.utc)
                else:
                    ts_val = datetime.datetime.now(datetime.timezone.utc)

                data.append([
                    ts_val,
                    str(r.get("tenant_id", "")),
                    str(r.get("key_id", "")),
                    str(r.get("method", "GET")),
                    str(r.get("route", "/")),
                    int(r.get("status_code", 200)),
                    float(r.get("latency_ms", 0.0)),
                    str(r.get("client_ip", "")),
                    int(r.get("request_size_bytes", 0)),
                    int(r.get("response_size_bytes", 0)),
                    str(r.get("user_agent", "")),
                    str(r.get("error_message", "")),
                ])
            client.insert(settings.CLICKHOUSE_TABLE, data, column_names=columns)
            return True
        except Exception as e:
            logger.error(f"Failed to batch insert to ClickHouse: {e}")

    # Fallback in-memory storage
    for r in rows:
        ts = r.get("timestamp")
        if isinstance(ts, (int, float)):
            ts_float = float(ts)
        elif isinstance(ts, str):
            try:
                ts_float = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except Exception:
                ts_float = datetime.datetime.now(datetime.timezone.utc).timestamp()
        else:
            ts_float = datetime.datetime.now(datetime.timezone.utc).timestamp()

        _in_memory_telemetry_log.append({
            "timestamp": ts_float,
            "tenant_id": str(r.get("tenant_id", "")),
            "key_id": str(r.get("key_id", "")),
            "method": str(r.get("method", "GET")),
            "route": str(r.get("route", "/")),
            "status_code": int(r.get("status_code", 200)),
            "latency_ms": float(r.get("latency_ms", 0.0)),
            "client_ip": str(r.get("client_ip", "")),
            "request_size_bytes": int(r.get("request_size_bytes", 0)),
            "response_size_bytes": int(r.get("response_size_bytes", 0)),
            "user_agent": str(r.get("user_agent", "")),
            "error_message": str(r.get("error_message", "")),
        })
    return True


def get_telemetry_metrics(
    tenant_id: Optional[str] = None,
    time_window_seconds: int = 3600,
    route_filter: Optional[str] = None,
    tenant_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Computes high-cardinality aggregations:
    - Total requests
    - Error rates (%)
    - Latency percentiles (P50, P95, P99, avg, min, max)
    - Payload bandwidth (request bytes, response bytes)
    - Route breakdown
    - Time-series buckets
    """
    client = get_clickhouse_client()
    now = datetime.datetime.now(datetime.timezone.utc)
    from_time = now - datetime.timedelta(seconds=time_window_seconds)

    # Input validation to prevent injection or malicious inputs
    clean_tenant_id = None
    if tenant_id:
        if re.match(r"^[a-zA-Z0-9_\-]{1,64}$", str(tenant_id).strip()):
            clean_tenant_id = str(tenant_id).strip()
        else:
            logger.warning(f"Rejected malicious or malformed tenant_id: {tenant_id}")

    clean_tenant_ids = []
    if tenant_ids:
        for tid in tenant_ids:
            if re.match(r"^[a-zA-Z0-9_\-]{1,64}$", str(tid).strip()):
                clean_tenant_ids.append(str(tid).strip())

    clean_route = None
    if route_filter:
        # Route should start with / and only contain valid path/query characters without SQL comments/quotes
        rf = str(route_filter).strip()
        if re.match(r"^/[a-zA-Z0-9_\-./%?=&]*$", rf) and not any(c in rf for c in ("'", '"', ";", "--", "/*", "*/")):
            clean_route = rf
        else:
            logger.warning(f"Rejected malicious or malformed route_filter: {route_filter}")

    if client is not None:
        try:
            where_clauses = ["timestamp >= {from_time:DateTime64(3)}"]
            params: Dict[str, Any] = {"from_time": from_time}

            if clean_tenant_id:
                where_clauses.append("tenant_id = {tenant_id:String}")
                params["tenant_id"] = clean_tenant_id
            elif clean_tenant_ids:
                where_clauses.append("tenant_id IN ({tenant_ids:Array(String)})")
                params["tenant_ids"] = clean_tenant_ids

            if clean_route:
                where_clauses.append("route = {route:String}")
                params["route"] = clean_route

            where_sql = " AND ".join(where_clauses)

            # 1. Main summary query
            summary_query = f"""
            SELECT
                count(*) AS total_requests,
                countIf(status_code >= 200 AND status_code < 300) AS status_2xx,
                countIf(status_code >= 400 AND status_code < 500) AS status_4xx,
                countIf(status_code >= 500) AS status_5xx,
                quantile(0.50)(latency_ms) AS p50_latency,
                quantile(0.95)(latency_ms) AS p95_latency,
                quantile(0.99)(latency_ms) AS p99_latency,
                avg(latency_ms) AS avg_latency,
                min(latency_ms) AS min_latency,
                max(latency_ms) AS max_latency,
                sum(request_size_bytes) AS total_request_bytes,
                sum(response_size_bytes) AS total_response_bytes
            FROM {settings.CLICKHOUSE_TABLE}
            WHERE {where_sql}
            """
            res = client.query(summary_query, parameters=params)
            named_res = list(res.named_results())
            row = named_res[0] if len(named_res) > 0 else {}

            total_reqs = row.get("total_requests", 0)
            status_4xx = row.get("status_4xx", 0)
            status_5xx = row.get("status_5xx", 0)
            error_count = status_4xx + status_5xx
            error_rate = (error_count / total_reqs * 100) if total_reqs > 0 else 0.0

            # 2. Route breakdown query
            routes_query = f"""
            SELECT
                route,
                method,
                count(*) AS count,
                avg(latency_ms) AS avg_latency,
                quantile(0.95)(latency_ms) AS p95_latency,
                countIf(status_code >= 400) / count(*) * 100 AS error_rate
            FROM {settings.CLICKHOUSE_TABLE}
            WHERE {where_sql}
            GROUP BY route, method
            ORDER BY count DESC
            LIMIT 15
            """
            route_res = client.query(routes_query, parameters=params)
            routes_breakdown = list(route_res.named_results())

            return {
                "total_requests": total_reqs,
                "error_count": error_count,
                "error_rate_pct": round(error_rate, 2),
                "status_breakdown": {
                    "2xx": row.get("status_2xx", 0),
                    "4xx": status_4xx,
                    "5xx": status_5xx,
                },
                "latency_percentiles_ms": {
                    "p50": round(float(row.get("p50_latency", 0.0) or 0.0), 2),
                    "p95": round(float(row.get("p95_latency", 0.0) or 0.0), 2),
                    "p99": round(float(row.get("p99_latency", 0.0) or 0.0), 2),
                    "avg": round(float(row.get("avg_latency", 0.0) or 0.0), 2),
                    "min": round(float(row.get("min_latency", 0.0) or 0.0), 2),
                    "max": round(float(row.get("max_latency", 0.0) or 0.0), 2),
                },
                "bandwidth_bytes": {
                    "request_bytes": row.get("total_request_bytes", 0),
                    "response_bytes": row.get("total_response_bytes", 0),
                    "total_bytes": (row.get("total_request_bytes", 0) or 0) + (row.get("total_response_bytes", 0) or 0),
                },
                "routes_breakdown": routes_breakdown,
                "time_window_seconds": time_window_seconds,
            }
        except Exception as e:
            logger.error(f"ClickHouse query error: {e}")

    # In-memory evaluation fallback
    from_ts = from_time.timestamp()
    filtered = [
        r for r in _in_memory_telemetry_log
        if r["timestamp"] >= from_ts
        and (clean_tenant_id is None or r["tenant_id"] == clean_tenant_id)
        and (not clean_tenant_ids or r["tenant_id"] in clean_tenant_ids)
        and (clean_route is None or r["route"] == clean_route)
    ]

    total = len(filtered)
    if total == 0:
        return {
            "total_requests": 0,
            "error_count": 0,
            "error_rate_pct": 0.0,
            "status_breakdown": {"2xx": 0, "4xx": 0, "5xx": 0},
            "latency_percentiles_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0},
            "bandwidth_bytes": {"request_bytes": 0, "response_bytes": 0, "total_bytes": 0},
            "routes_breakdown": [],
            "time_window_seconds": time_window_seconds,
        }

    status_2xx = sum(1 for r in filtered if 200 <= r["status_code"] < 300)
    status_4xx = sum(1 for r in filtered if 400 <= r["status_code"] < 500)
    status_5xx = sum(1 for r in filtered if r["status_code"] >= 500)
    error_count = status_4xx + status_5xx
    error_rate = (error_count / total * 100) if total > 0 else 0.0

    latencies = sorted([r["latency_ms"] for r in filtered])

    def calc_percentile(data: List[float], p: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        d0 = data[int(f)] * (c - k)
        d1 = data[int(c)] * (k - f)
        return d0 + d1

    p50 = calc_percentile(latencies, 0.50)
    p95 = calc_percentile(latencies, 0.95)
    p99 = calc_percentile(latencies, 0.99)
    avg_lat = sum(latencies) / total if total > 0 else 0.0
    min_lat = latencies[0] if latencies else 0.0
    max_lat = latencies[-1] if latencies else 0.0

    req_bytes = sum(r["request_size_bytes"] for r in filtered)
    res_bytes = sum(r["response_size_bytes"] for r in filtered)

    # Route breakdown
    route_map: Dict[str, Dict[str, Any]] = {}
    for r in filtered:
        key = f"{r['method']} {r['route']}"
        if key not in route_map:
            route_map[key] = {
                "route": r["route"],
                "method": r["method"],
                "count": 0,
                "latencies": [],
                "errors": 0,
            }
        route_map[key]["count"] += 1
        route_map[key]["latencies"].append(r["latency_ms"])
        if r["status_code"] >= 400:
            route_map[key]["errors"] += 1

    routes_breakdown = []
    for item in route_map.values():
        cnt = item["count"]
        item_lats = sorted(item["latencies"])
        routes_breakdown.append({
            "route": item["route"],
            "method": item["method"],
            "count": cnt,
            "avg_latency": round(sum(item_lats) / cnt, 2) if cnt > 0 else 0.0,
            "p95_latency": round(calc_percentile(item_lats, 0.95), 2),
            "error_rate": round(item["errors"] / cnt * 100, 2) if cnt > 0 else 0.0,
        })
    routes_breakdown.sort(key=lambda x: x["count"], reverse=True)

    return {
        "total_requests": total,
        "error_count": error_count,
        "error_rate_pct": round(error_rate, 2),
        "status_breakdown": {
            "2xx": status_2xx,
            "4xx": status_4xx,
            "5xx": status_5xx,
        },
        "latency_percentiles_ms": {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "avg": round(avg_lat, 2),
            "min": round(min_lat, 2),
            "max": round(max_lat, 2),
        },
        "bandwidth_bytes": {
            "request_bytes": req_bytes,
            "response_bytes": res_bytes,
            "total_bytes": req_bytes + res_bytes,
        },
        "routes_breakdown": routes_breakdown[:15],
        "time_window_seconds": time_window_seconds,
    }


def clear_in_memory_telemetry():
    """Helper for test cleanups."""
    global _in_memory_telemetry_log
    _in_memory_telemetry_log.clear()
