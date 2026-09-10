export interface Tenant {
  id: string;
  name: string;
  slug: string;
  upstream_url: string;
  plan_tier: "free" | "pro" | "enterprise";
  rate_limit_rpm: number;
  burst_limit: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TenantCreateInput {
  name: string;
  slug: string;
  upstream_url: string;
  plan_tier?: string;
  rate_limit_rpm?: number;
  burst_limit?: number;
}

export interface ApiKey {
  id: string;
  tenant_id: string;
  name: string;
  key_prefix: string;
  full_key?: string | null;
  rate_limit_override_rpm?: number | null;
  is_active: boolean;
  expires_at?: string | null;
  created_at: string;
  last_used_at?: string | null;
}

export interface ApiKeyCreatedResponse {
  id: string;
  tenant_id: string;
  name: string;
  key_prefix: string;
  raw_key: string;
  created_at: string;
}

export interface ApiKeyCreateInput {
  tenant_id: string;
  name?: string;
  rate_limit_override_rpm?: number;
  expires_in_days?: number;
}

export interface TelemetryMetrics {
  total_requests: number;
  error_count: number;
  error_rate_pct: number;
  status_breakdown: {
    "2xx": number;
    "4xx": number;
    "5xx": number;
  };
  latency_percentiles_ms: {
    p50: number;
    p95: number;
    p99: number;
    avg: number;
    min: number;
    max: number;
  };
  bandwidth_bytes: {
    request_bytes: number;
    response_bytes: number;
    total_bytes: number;
  };
  routes_breakdown: Array<{
    route: string;
    method: string;
    count: number;
    avg_latency: number;
    p95_latency: number;
    error_rate: number;
  }>;
  time_window_seconds: number;
}

export interface AlertRule {
  id: string;
  tenant_id: string;
  name: string;
  metric_type: "p95_latency" | "error_rate" | "req_count";
  threshold: number;
  window_minutes: number;
  webhook_url: string;
  is_active: boolean;
  created_at: string;
}

export interface AlertRuleCreateInput {
  tenant_id: string;
  name: string;
  metric_type: "p95_latency" | "error_rate" | "req_count";
  threshold: number;
  window_minutes?: number;
  webhook_url: string;
}

export interface AlertHistoryItem {
  id: string;
  rule_id: string;
  tenant_id: string;
  metric_type: string;
  triggered_value: number;
  threshold: number;
  status: "sent" | "failed";
  payload?: string;
  triggered_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  is_active: boolean;
  created_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
