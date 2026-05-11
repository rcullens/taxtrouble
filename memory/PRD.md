# LIEN/TX — Texas Back Taxes & HOA Liens Property Scraper

## Problem Statement
Develop an AI-driven app that scrapes public records for properties with back taxes or HOA liens in Texas. User wants pre-scraped REAL data for McLennan, Hill, and Bosque counties (no placeholders) plus on-demand scraping for any other Texas county.

## Architecture
- **Frontend**: React 19 + React Router 7 + Tailwind + shadcn/ui + Phosphor icons. Swiss-Brutalist design (sharp edges, IBM Plex Sans / Space Grotesk, Klein Blue #002FA7, Signal Red distress markers).
- **Backend**: FastAPI + Motor (async MongoDB) + JWT auth + emergentintegrations (Claude Sonnet 4.5).
- **Database**: MongoDB. Collections: `users`, `properties`, `saved_searches`, `scrape_jobs`.

## User Personas
1. **Tax-sale investor** — searches distressed properties, filters by county/amount/type, exports to CSV.
2. **Investment analyst** — uses AI scoring + NL search to surface high-grade opportunities.
3. **Researcher** — scrapes specific counties on demand for academic / journalistic work.

## Core Requirements (static)
- Auth (register/login/me) via JWT.
- Pre-supported counties (real data): McLennan (15), Hill (12), Bosque (9) = 36 properties.
- On-demand scraping for any of the 36 Texas counties listed in `seed_data.AVAILABLE_COUNTIES`.
- Filters: county, city, ZIP, property type, tax-owed range, HOA-lien flag, status, free-text.
- AI: Claude-powered investment scoring (A-F + 0-100), NL → filter parsing.
- Saved searches (per-user).
- CSV export of any filtered result set.

## Implemented (2026-02-10)
- All 36 real properties seeded on first startup from public-record extracts.
- Full auth flow with bcrypt + JWT.
- Search API with filters, pagination, sorting.
- AI endpoints (cached per-property after first generation).
- CSV export endpoint.
- Saved-searches CRUD.
- Scrape trigger endpoint (idempotent upsert by parcel_id+county).
- Frontend: Landing, Login, Register, Dashboard (with NL search hero), Property Detail (with AI insights), Scrape Counties, Saved Searches.
- Tested: 22/22 backend tests pass via testing agent.

## P0/P1 Backlog
- **P1**: Background-task scraping (currently synchronous; long counties may hit ingress timeout).
- **P1**: Compute `new_this_week` from `scraped_at` timestamp rather than total count.
- **P2**: Real CSV pagination beyond 5000 rows.
- **P2**: Generic scraper coverage for remaining ~210 TX counties (currently 36 listed, scraper framework supports all).
- **P2**: Property photo integration via Google Street View API.
- **P2**: Migrate FastAPI startup events to lifespan context manager.
- **P3**: Real-time alerts (email/SMS) when new properties match saved searches.
- **P3**: Mapbox map view of properties.

## Data Sources Used
- Hill County: official Oct 7 2025 tax sale list PDF (hilltax.org)
- Bosque County: official July 1 2025 Notice of Sale (bosquecounty.gov)
- McLennan County: McLennan CAD + GovEase online auction parcels + Trustee notices
- Generic scraper: MVBA Law (mvbalaw.com) + LGBS (taxsales.lgbs.com)

## Test Credentials
See `/app/memory/test_credentials.md`

## Update 2026-02-11
### CAD scraping shipped
- 3 new endpoints: `/api/cad/sources`, `/api/properties/{id}/cad-enrich`, `/api/cad/bulk-enrich` (now backgrounded with job_id polling), `/api/cad/jobs`, `/api/cad/jobs/{id}`, `/api/cad/discover/{county}`
- Real deed references pre-populated for all 12 Hill County properties (V917/P8, V1715/P495, etc.)
- McLennan/Bosque properties have year_built, sqft, appraised_value, land_value, improvement_value, exemptions
- `cad_url_for` works for ANY Texas county via heuristic `esearch.{slug}cad.org` fallback
- ArcGIS REST endpoint discovery probes 4 hosting patterns per county
- `enrich_property_from_cad` tries ArcGIS REST first, falls back to Playwright on BIS eSearch

### Comparable Sales + Deal Leaderboard shipped
- `GET /api/properties/{id}/comparables` - returns target + 5 comps with $/sqft & delta; falls back zip → typed → county
- `GET /api/leaderboard?limit=10&period=all|week` - top deals ranked by `discount_pct × (1 + ai_score/100)`
- New `/leaderboard` page in nav; Comparables panel on property detail
- Tests: 45/45 passing (22 base + 10 CAD + 13 leaderboard/comparables)
