from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class LatencyPercentiles(BaseModel):
    p50: float = Field(..., example=12.4, description="50th percentile (median) latency in ms")
    p95: float = Field(..., example=45.8, description="95th percentile latency in ms")
    p99: float = Field(..., example=98.2, description="99th percentile latency in ms")
    avg: float = Field(..., example=18.5, description="Average latency in ms")
    min: float = Field(..., example=2.1, description="Minimum latency in ms")
    max: float = Field(..., example=180.0, description="Maximum latency in ms")


class BandwidthMetrics(BaseModel):
    request_bytes: int = Field(..., example=1048576)
    response_bytes: int = Field(..., example=5242880)
    total_bytes: int = Field(..., example=6291456)


class RouteMetrics(BaseModel):
    route: str
    method: str
    count: int
    avg_latency: float
    p95_latency: float
    error_rate: float


class StatusBreakdown(BaseModel):
    status_2xx: int = Field(0, alias="2xx")
    status_4xx: int = Field(0, alias="4xx")
    status_5xx: int = Field(0, alias="5xx")

    class Config:
        populate_by_name = True


class MetricsResponse(BaseModel):
    total_requests: int
    error_count: int
    error_rate_pct: float
    status_breakdown: Dict[str, int]
    latency_percentiles_ms: LatencyPercentiles
    bandwidth_bytes: BandwidthMetrics
    routes_breakdown: List[Dict]
    time_window_seconds: int
