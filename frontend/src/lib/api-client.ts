import {
  Tenant,
  TenantCreateInput,
  ApiKey,
  ApiKeyCreateInput,
  ApiKeyCreatedResponse,
  TelemetryMetrics,
  AlertRule,
  AlertRuleCreateInput,
  AlertHistoryItem,
  User,
  AuthResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options?.headers as Record<string, string>),
  };

  const res = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
    credentials: "include", // Sends HttpOnly cookie automatically
  });

  if (!res.ok) {
    let errorDetail = "An unexpected error occurred.";
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorJson.error || JSON.stringify(errorJson);
    } catch {
      errorDetail = await res.text();
    }
    throw new Error(errorDetail || `HTTP Error ${res.status}`);
  }

  return res.json();
}

export const apiClient = {
  // --- Authentication ---
  register: (payload: { email: string; password: string; full_name?: string }) =>
    fetchJson<AuthResponse>("/admin/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (payload: { email: string; password: string }) =>
    fetchJson<AuthResponse>("/admin/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getMe: () => fetchJson<User>("/admin/auth/me"),
  logout: () =>
    fetchJson<{ message: string }>("/admin/auth/logout", {
      method: "POST",
    }),

  // --- Tenants ---
  getTenants: async (): Promise<Tenant[]> => {
    const data = await fetchJson<{ tenants?: Tenant[]; items?: Tenant[]; total?: number } | Tenant[]>("/admin/tenants");
    if (Array.isArray(data)) return data;
    return data.tenants || data.items || [];
  },
  createTenant: (payload: TenantCreateInput) =>
    fetchJson<Tenant>("/admin/tenants", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTenant: (id: string) => fetchJson<Tenant>(`/admin/tenants/${id}`),
  deleteTenant: (id: string) =>
    fetchJson<{ message: string }>(`/admin/tenants/${id}`, {
      method: "DELETE",
    }),

  // --- API Keys ---
  getKeys: (tenantId?: string) => {
    const url = tenantId ? `/admin/keys?tenant_id=${tenantId}` : "/admin/keys";
    return fetchJson<{ items: ApiKey[]; total: number }>(url);
  },
  createKey: (payload: ApiKeyCreateInput) =>
    fetchJson<ApiKeyCreatedResponse>("/admin/keys", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  revokeKey: (keyId: string) =>
    fetchJson<{ message: string }>(`/admin/keys/${keyId}`, {
      method: "DELETE",
    }),

  // --- Metrics & Analytics ---
  getMetrics: (tenantId?: string, timeWindowSeconds: number = 3600, route?: string) => {
    const params = new URLSearchParams();
    if (tenantId) params.append("tenant_id", tenantId);
    params.append("time_window_seconds", timeWindowSeconds.toString());
    if (route) params.append("route", route);
    return fetchJson<TelemetryMetrics>(`/admin/metrics?${params.toString()}`);
  },

  // --- Alerts ---
  getAlertRules: (tenantId?: string) => {
    const url = tenantId ? `/admin/alerts?tenant_id=${tenantId}` : "/admin/alerts";
    return fetchJson<{ items: AlertRule[]; total: number }>(url);
  },
  createAlertRule: (payload: AlertRuleCreateInput) =>
    fetchJson<AlertRule>("/admin/alerts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteAlertRule: (ruleId: string) =>
    fetchJson<{ message: string }>(`/admin/alerts/${ruleId}`, {
      method: "DELETE",
    }),
  getAlertHistory: (tenantId?: string) => {
    const url = tenantId ? `/admin/alerts/history?tenant_id=${tenantId}` : "/admin/alerts/history";
    return fetchJson<{ items: AlertHistoryItem[]; total: number }>(url);
  },

  // --- Gateway Live Request Proxy Tester ---
  sendProxyRequest: async (
    path: string,
    apiKey: string,
    method: string = "GET",
    bodyPayload?: any
  ) => {
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const startTime = performance.now();
    const res = await fetch(`${API_BASE_URL}${cleanPath}`, {
      method,
      headers: {
        "X-API-Key": apiKey,
        ...(bodyPayload ? { "Content-Type": "application/json" } : {}),
      },
      body: bodyPayload ? JSON.stringify(bodyPayload) : undefined,
    });
    const clientLatencyMs = Math.round(performance.now() - startTime);

    let data = null;
    try {
      data = await res.json();
    } catch {
      data = await res.text();
    }

    const responseHeaders: Record<string, string> = {};
    res.headers.forEach((val, key) => {
      responseHeaders[key] = val;
    });

    return {
      status: res.status,
      statusText: res.statusText,
      ok: res.ok,
      data,
      headers: responseHeaders,
      clientLatencyMs,
      gatewayLatencyMs: res.headers.get("x-gateway-latency-ms"),
      rateLimitLimit: res.headers.get("x-ratelimit-limit"),
      rateLimitRemaining: res.headers.get("x-ratelimit-remaining"),
    };
  },
};
