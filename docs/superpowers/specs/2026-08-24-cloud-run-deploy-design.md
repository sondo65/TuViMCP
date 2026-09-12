# TuViMCP on Google Cloud Run — Design

**Date:** 2026-08-24  
**Status:** Draft for review  
**Repos:** TuViMCP (FastAPI REST for TuViAI Flutter)  
**Out of scope:** Public remote MCP (stdio/SSE), Supabase Edge changes, Fly.io / Render

## Goal

Host the existing TuViMCP FastAPI service so the Flutter app can call `POST /v1/horoscope/*` over HTTPS with Supabase JWT verification, starting on Cloud Run’s free/low-cost tier and scaling to paid usage as traffic grows.

## Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Platform | Google Cloud Run | Free monthly quota → pay-as-you-go; Docker-native FastAPI |
| Region | `asia-southeast1` (Singapore) | Latency for VN users; prefer UX over maximizing Always Free regions |
| Phase 1 scaling | `min-instances = 0` | Stay near $0 at low traffic; accept cold start |
| Memory | 1 GiB | Pillow chart PNG is safer than 512 MiB |
| Auth | Unchanged: verify Supabase JWKS via `SUPABASE_URL` | Aligns with TuViAI D-25 / production `TUVI_MCP_ENV=production` |
| Persistence | None | API already encodes PNG in response / temp files; no volumes |

## Architecture

```
Flutter (TuViAI)
  │  Authorization: Bearer <Supabase JWT>
  │  TUVI_MCP_BASE_URL → Cloud Run HTTPS URL
  ▼
Cloud Run service (asia-southeast1)
  │  container: uvicorn tuvi_mcp.api.app:app
  │  GET  /health
  │  POST /v1/horoscope/generate | /chart | /transit | …
  ▼
Supabase Auth JWKS  ({SUPABASE_URL}/auth/v1/.well-known/jwks.json)
```

Supabase continues to own Auth, Postgres, Storage, and Edge Functions (interpret-*). Cloud Run only runs deterministic chart/transit compute + PNG render.

## Components

### 1. Dockerfile (new in TuViMCP)

- Base: Python 3.12 slim
- Install package with `[api]` extra (`fastapi`, `uvicorn[standard]`, `PyJWT[crypto]`) plus core deps (`pillow`, `mcp`)
- Listen on `$PORT` (Cloud Run injects this; default `8080` for local parity)
- Entrypoint:

  ```bash
  uvicorn tuvi_mcp.api.app:app --host 0.0.0.0 --port ${PORT:-8080}
  ```

- No root-owned secrets in the image; no `.env` baked in
- Optional non-root user for runtime

### 2. Cloud Run service

| Setting | Phase 1 (free / low traffic) | Scale-up trigger |
|---|---|---|
| Region | `asia-southeast1` | Keep |
| CPU | 1 | Increase if PNG p95 slow |
| Memory | 1 GiB | 2 GiB if OOM on render |
| Min instances | 0 | Set to 1 when cold starts hurt UX |
| Max instances | 5 | Raise with traffic; hard cap for cost control |
| Concurrency | 40 | Tune after load test |
| Request timeout | 120 s | Keep unless generate needs more |
| Ingress | All (public HTTPS) | Optional load balancer + custom domain later |
| Auth on Cloud Run | Allow unauthenticated invoke | App-level JWT already required on POST routes |

Probes: HTTP `GET /health` (already implemented in `tuvi_mcp/api/routes/health.py`).

### 3. Configuration

| Variable | Required in prod | Notes |
|---|---|---|
| `TUVI_MCP_ENV` | Yes → `production` | Disables auth bypass; requires `SUPABASE_URL` |
| `SUPABASE_URL` | Yes | Same project as Flutter; JWKS only — never `service_role` |
| `TUVI_MCP_AUTH_DISABLED` | Must be unset / ignored | Production ignores this flag |

Store secrets as Cloud Run environment variables (or Secret Manager if team prefers). Do not commit values.

### 4. Flutter (TuViAI)

- Production / staging builds set `--dart-define=TUVI_MCP_BASE_URL=https://<service>-<hash>.a.run.app` (or custom domain)
- Existing `TuviMcpApiClient` + Bearer interceptor unchanged
- No client code changes beyond URL / flavor config

### 5. Deploy workflow

**Phase 1 (manual):**

```bash
gcloud run deploy tuvi-mcp \
  --source . \
  --region asia-southeast1 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --timeout 120 \
  --allow-unauthenticated \
  --set-env-vars "TUVI_MCP_ENV=production,SUPABASE_URL=https://<project>.supabase.co"
```

**Phase 2 (optional CI):** GitHub Actions on TuViMCP `main`: build → Artifact Registry → `gcloud run deploy --image …`.

## Data flow (generate)

1. Flutter obtains Supabase session (anonymous or user) and attaches Bearer token.
2. `POST /v1/horoscope/generate` hits Cloud Run.
3. FastAPI verifies JWT against Supabase JWKS (cached client).
4. Horoscope compute + Pillow render → JSON (incl. PNG base64 as today).
5. Flutter displays / uploads image URL per existing TuViAI flow.

Failures: 401 on bad/missing JWT; 422 on validation; 5xx on render/compute — Flutter maps via existing TuViMCP error mapper.

## Cost model

- **Low traffic + min=0:** Often near $0–few dollars/month in `asia-southeast1` (Always Free quotas are strongest in selected US regions; Singapore usage may bill earlier — acceptable trade-off).
- **Drivers:** CPU/memory-seconds while handling requests, cold starts, egress (PNG-heavy responses), min-instances if later set to 1.
- **Controls:** `max-instances=5`, billing alerts in GCP, keep min=0 until UX requires warm instances.

## Testing / verification

1. Local: `docker build` + run with `TUVI_MCP_ENV=production` and real `SUPABASE_URL` → `GET /health` 200; JWKS probe logs keys > 0.
2. Deploy: curl `/health`; curl `/v1/horoscope/chart` without token → 401; with valid anon JWT → 200.
3. Flutter staging flavor pointed at Cloud Run URL: guest generate + saved chart path still work.
4. Existing TuViMCP pytest suite unchanged (local / CI); no Cloud Run required for unit tests.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Cold start after idle (min=0) | Accept in phase 1; Flutter loading UI already exists; upgrade min=1 when needed |
| 512MB OOM on PNG | Start at 1 GiB |
| Accidental open bill | max-instances=5 + GCP budget alert |
| JWKS empty (HS256 project) | Startup probe already warns; ensure Supabase ES256 keys before prod cutover |
| Region free-tier mismatch | Document that `asia-southeast1` prioritizes latency; monitor billing first week |

## Non-goals

- Hosting MCP protocol transport for Cursor on this Cloud Run service
- Moving interpret-* LLM functions off Supabase Edge
- Multi-region active-active
- Custom domain / CDN (deferred until traffic justifies)

## Implementation checklist (for later plan)

1. Add `Dockerfile` (+ `.dockerignore`) to TuViMCP
2. Verify `/health` and PORT binding locally via Docker
3. Create GCP project / enable Cloud Run + Artifact Registry APIs
4. Deploy with env vars; capture service URL
5. Point TuViAI staging `TUVI_MCP_BASE_URL` at Cloud Run; smoke test
6. Optional: GH Actions deploy; budget alert; custom domain
