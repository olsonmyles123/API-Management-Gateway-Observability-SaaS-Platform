# API Gateway & Observability SaaS — Frontend Web App

A modern, high-performance web dashboard built with **Next.js 16 (App Router)**, **React 19**, **Tailwind CSS**, **Lucide Icons**, **Recharts**, and **TanStack React Query**.

---

## ✨ Features

- 🔐 **Authentication & Session Management**: Secure JWT token storage, role-based auth guard, professional login & registration screens.
- 🏢 **Multi-Tenant Management**: Register upstream APIs, configure custom plan tiers, define rate limits (RPM & Burst), and edit tenant configurations.
- 🔑 **API Key Lifecycle**: Generate cryptographically secure API keys with prefixing, rate-limit overrides, copy-to-clipboard, and instant revocation.
- 📊 **Real-Time OLAP Observability**: Live charts for request volume, error rate %, $P_{50}/P_{95}/P_{99}$ latency percentiles, status breakdown (2xx/4xx/5xx), and bandwidth transfer.
- 🚨 **Automated Alert Rules**: Set latency and error rate threshold rules, configure external webhook endpoints, and run live dispatch tests.
- ⚡ **Interactive API Playground**: Built-in test console to send live requests through the API Gateway, view status codes, response headers, rate-limit headers, and latency metrics.
- 🎨 **Modern Dark Aesthetics**: Premium dark theme with glassmorphic cards, smooth micro-interactions, and responsive layout.

---

## 🛠️ Tech Stack

- **Framework**: [Next.js 16 (Turbopack)](https://nextjs.org/)
- **UI Library**: [React 19](https://react.dev/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Data Fetching**: [@tanstack/react-query](https://tanstack.com/query)
- **Charts & Graphs**: [Recharts](https://recharts.org/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Notifications**: [Sonner](https://sonner.emilkowal.ski/)

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js**: v18.17+ or v20+
- **npm**, **pnpm**, or **yarn**

### 2. Install Dependencies
```bash
npm install
```

### 3. Configure Environment
Create a `.env.local` file (optional, defaults to `http://localhost:8000`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Run Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📁 Project Structure

```
frontend/
├── public/              # Static assets, logo, favicons
├── src/
│   ├── app/
│   │   ├── alerts/      # Alert rules & webhook history
│   │   ├── keys/        # API key generation & revocation
│   │   ├── login/       # User authentication page
│   │   ├── playground/  # Interactive live API test console
│   │   ├── register/    # New user onboarding page
│   │   ├── tenants/     # Tenant management & upstream mapping
│   │   ├── globals.css  # Global styles & theme definitions
│   │   ├── layout.tsx   # Root layout & theme providers
│   │   └── page.tsx     # Overview analytics dashboard
│   ├── components/      # Reusable UI components (Sidebar, Header, MetricCard, etc.)
│   ├── context/         # AuthContext & global state
│   └── lib/             # API client, TypeScript definitions, and utility helpers
├── package.json
└── tsconfig.json
```

---

## 📜 Available Scripts

- `npm run dev` — Starts local development server with Turbopack on port 3000.
- `npm run build` — Builds production-optimized bundle.
- `npm run start` — Starts Next.js production server.
- `npm run lint` — Runs ESLint checks.
