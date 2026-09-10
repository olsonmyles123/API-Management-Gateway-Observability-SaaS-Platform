"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Header } from "@/components/header";
import {
  Terminal,
  Send,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

export default function PlaygroundPage() {
  const [selectedApiKey, setSelectedApiKey] = useState("");
  const [method, setMethod] = useState("GET");
  const [path, setPath] = useState("");
  const [requestBody, setRequestBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [responseState, setResponseState] = useState<any>(null);

  // Fetch API keys for easy selection in playground
  const { data: keysData } = useQuery({
    queryKey: ["keys"],
    queryFn: () => apiClient.getKeys(),
  });

  const keys = keysData?.items || [];

  const handleSendRequest = async () => {
    if (!selectedApiKey) {
      toast.error("Please select or paste an API Key.");
      return;
    }

    setLoading(true);
    try {
      let parsedBody = undefined;
      if (method !== "GET" && requestBody.trim()) {
        try {
          parsedBody = JSON.parse(requestBody);
        } catch {
          toast.error("Invalid JSON body.");
          setLoading(false);
          return;
        }
      }

      const result = await apiClient.sendProxyRequest(path, selectedApiKey, method, parsedBody);
      setResponseState(result);
      if (result.ok) {
        toast.success(`HTTP ${result.status} ${result.statusText} (${result.clientLatencyMs}ms)`);
      } else {
        toast.error(`HTTP ${result.status}: ${result.statusText}`);
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to send request.");
      setResponseState({
        status: 500,
        statusText: "Connection Error",
        data: err.message,
        clientLatencyMs: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Header
        title="Interactive Gateway Proxy Playground"
        subtitle="Test data plane routing, sliding-window rate limits, and latency"
      />

      <div className="p-6 space-y-6 flex-1 max-w-7xl w-full mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Request Configurator */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
              <Terminal className="h-4 w-4 text-zinc-400" />
              <h3 className="text-xs font-medium text-zinc-200 uppercase tracking-wider">HTTP Request Builder</h3>
            </div>

            {/* API Key selector */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1">
                API Key (`X-API-Key`) *
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="ak_live_..."
                  value={selectedApiKey}
                  onChange={(e) => setSelectedApiKey(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-500"
                />
              </div>
              {keys.length > 0 && (
                <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-zinc-500">
                  <span>Quick-select active key:</span>
                  <button
                    type="button"
                    onClick={() => setSelectedApiKey(keys[0].key_prefix)}
                    className="font-mono text-zinc-300 hover:text-white underline cursor-pointer"
                  >
                    {keys[0].key_prefix}... ({keys[0].name})
                  </button>
                </div>
              )}
            </div>

            {/* Method & Path */}
            <div className="flex gap-2">
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-2 text-xs font-mono font-medium text-zinc-200 focus:outline-none focus:border-zinc-500"
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
              </select>
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="/api/endpoint"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
              />
            </div>

            {/* JSON Request Body (for POST/PUT) */}
            {method !== "GET" && (
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  JSON Body Payload
                </label>
                <textarea
                  rows={5}
                  value={requestBody}
                  onChange={(e) => setRequestBody(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md p-3 text-xs font-mono text-zinc-200 focus:outline-none focus:border-zinc-500"
                />
              </div>
            )}

            {/* Send Button */}
            <button
              onClick={handleSendRequest}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs py-2.5 rounded-md disabled:opacity-50 cursor-pointer transition-colors"
            >
              {loading ? (
                <div className="h-3.5 w-3.5 rounded-full border-2 border-zinc-900 border-t-transparent animate-spin"></div>
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              {loading ? "Proxying via Gateway..." : "Execute Proxied Request"}
            </button>
          </div>

          {/* Response Inspector */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5 space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-zinc-400" />
                  <h3 className="text-xs font-medium text-zinc-200 uppercase tracking-wider">Upstream Response</h3>
                </div>
                {responseState && (
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${
                      responseState.status < 400
                        ? "bg-emerald-950/40 text-emerald-400 border border-emerald-800/40"
                        : "bg-rose-950/40 text-rose-400 border border-rose-800/40"
                    }`}
                  >
                    HTTP {responseState.status} {responseState.statusText}
                  </span>
                )}
              </div>

              {responseState ? (
                <div className="mt-4 space-y-4">
                  {/* Gateway Metadata Headers */}
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="p-2 rounded-md bg-zinc-950 border border-zinc-800">
                      <span className="text-[10px] text-zinc-500 block uppercase">Client RTT</span>
                      <span className="font-mono font-medium text-zinc-200 text-xs">
                        {responseState.clientLatencyMs} ms
                      </span>
                    </div>
                    <div className="p-2 rounded-md bg-zinc-950 border border-zinc-800">
                      <span className="text-[10px] text-zinc-500 block uppercase">Gateway RTT</span>
                      <span className="font-mono font-medium text-zinc-200 text-xs">
                        {responseState.gatewayLatencyMs ? `${responseState.gatewayLatencyMs}ms` : "N/A"}
                      </span>
                    </div>
                    <div className="p-2 rounded-md bg-zinc-950 border border-zinc-800">
                      <span className="text-[10px] text-zinc-500 block uppercase">Rate Limit Left</span>
                      <span className="font-mono font-medium text-zinc-200 text-xs">
                        {responseState.rateLimitRemaining || "N/A"}
                      </span>
                    </div>
                  </div>

                  {/* Body Payload Viewer */}
                  <div>
                    <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider block mb-1">
                      Response Body:
                    </span>
                    <pre className="p-3 bg-zinc-950 rounded-md border border-zinc-800 text-xs font-mono text-zinc-200 overflow-x-auto max-h-72">
                      {typeof responseState.data === "object"
                        ? JSON.stringify(responseState.data, null, 2)
                        : String(responseState.data)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="h-56 flex flex-col items-center justify-center text-zinc-500 text-xs space-y-2">
                  <Terminal className="h-7 w-7 text-zinc-600 stroke-[1.5]" />
                  <span>Execute a proxied request to view headers and response body.</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
