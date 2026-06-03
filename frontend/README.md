# Open Water Platform — Dashboard

The React dashboard for the platform. It calls the API backend for device
data and (eventually) configuration changes. See
[`docs/system_architecture.md`](../docs/system_architecture.md#dashboard)
for where this component sits in the overall system, and
[`docs/stack.md`](../docs/stack.md) for the chosen frontend stack.

> **Status.** Base layout, routing, and device views are implemented with a
> mock API layer for local UI development. Wiring to the live backend
> (`/api/v1`) and removing placeholder dashboard content are follow-ups.

The dashboard never talks to PostgreSQL, the MQTT broker, or the ingestion
service directly.

## Requirements

- Node.js 20 or newer (LTS recommended).
- npm (ships with Node).

For live API data during development, the backend should be running and
reachable at the URL configured in `VITE_API_BASE_URL` (see
[`backend/README.md`](../backend/README.md)). The app still runs without
the backend while mocks are in use.

## Install

From the repository root:

```bash
cd frontend
npm ci
```

Use `npm install` instead of `npm ci` only when you are intentionally
updating `package-lock.json`.

## Run

Copy [`.env.example`](.env.example) to `.env` and adjust if needed:

```bash
cp .env.example .env   # Windows: copy .env.example .env
npm run dev
```

The dev server listens at `http://127.0.0.1:5173` by default (Vite).
Open that URL in a browser.

Production build and preview:

```bash
npm run build
npm run preview
```

## License

Apache-2.0 — see the repository [`LICENSE`](../LICENSE).
