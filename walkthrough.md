# API Gateway & Observability SaaS — Full-Stack Walkthrough

We have completed the implementation and refined the UI/UX into a **classic, high-density enterprise dashboard design** (aligned with modern SaaS benchmarks like Linear, Vercel, and Stripe), alongside secure JWT-based Control Plane authentication.

---

## 🌟 Architecture & Key Highlights

### 1. Classic Enterprise UI / UX Redesign
- **Neutral Dark Design System**: Swapped saturated neon glowing gradients and high-contrast rainbow accents for a refined `zinc-950` / `zinc-900` palette, subtle `1px` borders (`border-zinc-800`), crisp typographic hierarchy, and clean monochromatic interactive states.
- **Fixed Browser Autofill Artifacts**: Resolved Chrome/Safari/Edge webkit autofill styling issues where input elements were turning bright baby-blue. Inputs now retain a crisp, dark background with high-contrast text.
- **Cohesive Observability Visualizations**: Recharts distributions updated with unified, professional telemetry colorways, subtle gridlines, and clean dark tooltips.
- **Enterprise Controls**: Clean buttons, streamlined modal dialogs, and low-profile scrollbars.

---

### 2. Full-Stack Platform Features

| Domain | Description |
| :--- | :--- |
| **Authentication** | Secure JWT authentication with HttpOnly cookies, native bcrypt password hashing, and CSRF/XSS protection. |
| **Telemetry & Overview (`/`)** | Real-time ClickHouse OLAP metrics, 5s live polling, P50/Avg/P95/P99 latency distribution, and route breakdown. |
| **Tenants & Routing (`/tenants`)** | Multi-tenant upstream routing, plan tier quotas (`free`, `pro`, `enterprise`), and burst configurations. |
| **API Keys (`/keys`)** | Cryptographic SHA-256 token generation with a secure **One-Time Secret Copy Modal** and instant Redis revocation. |
| **Alert Engine (`/alerts`)** | Automated threshold evaluation (`p95_latency`, `error_rate`, `req_count`) and webhook dispatch logging. |
| **Playground (`/playground`)** | Live HTTP request runner through the proxy data plane to benchmark upstream latency and rate limits. |

---

## 🚀 How to Run the Platform

### 1. Start Backend Services (Docker Fleet)
```powershell
docker compose up -d
```
- Gateway Data Plane & Control Plane: [http://localhost:8000](http://localhost:8000)
- OpenAPI Interactive Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Start Frontend Dashboard (Next.js)
```powershell
cd frontend
npm run dev
```
- Dashboard UI: [http://localhost:3000](http://localhost:3000)
- Sign In / Register: [http://localhost:3000/login](http://localhost:3000/login) / [http://localhost:3000/register](http://localhost:3000/register)
