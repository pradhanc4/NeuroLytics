# NeuroLytics — Phase 81 Ranking Dashboard

## Status
COMPLETE

## Scope
Phase 81 adds a read-only dashboard over the existing ranking stack from
Phases 40–46. It does not replace ranking algorithms or create a second
ranking engine.

## Milestones

### 81.1 Ranking dashboard foundation
- Added `analytics/ranking_dashboard.py`.
- Version: `81.0.0`.
- Boundary: `RANKING_DASHBOARD_BOUNDARY`.
- Read-only dashboard service.

### 81.2 Panel ranking view
Projects Phase 42 panel ranking reports:
- report identity
- observations
- Top-K
- target date and position
- actual panel
- top probability
- probability margin
- top candidates
- panel/jodi family metadata

### 81.3 Jodi ranking view
Projects Phase 43 Jodi ranking reports:
- report identity
- observations
- Top-K
- actual Jodi
- top probability
- probability margin
- top candidates
- family metadata

Leading-zero values remain strings, including values such as `00` and
`05`.

### 81.4 Top-K evaluation
Projects Phase 44 evaluation:
- K values
- evaluated observations
- actual-available observations
- Hit@K rates
- mean reciprocal rank
- report identity

### 81.5 Actual-vs-ranked
Projects Phase 45:
- actual available observations
- missed observations
- mean actual rank
- mean reciprocal rank
- rank distribution
- rank buckets
- Hit@K metrics
- probability metrics

### 81.6 Performance-over-time
Projects Phase 46:
- period size
- periods
- observations
- actual/missed counts
- performance trends
- trend direction and slope

### 81.7 Production API integration
Added read-only GET routes:
- `/v1/ranking/summary`
- `/v1/ranking/panel`
- `/v1/ranking/jodi`
- `/v1/ranking/top-k`
- `/v1/ranking/actual-vs-ranked`
- `/v1/ranking/performance`

All use the existing production authorization and rate-limit boundary.

### 81.8 Frontend Ranking Dashboard
Added Ranking navigation and a dashboard containing:
- available-section KPI
- Panel status
- Jodi status
- Top-K status
- Panel evidence
- Jodi evidence
- Top-K evaluation
- Actual-vs-ranked
- Performance-over-time
- refresh action

### 81.9 Empty-state safety
When a ranking report is not attached, the API returns:
- status: `UNAVAILABLE`
- reason: `REPORT_NOT_ATTACHED`

No ranking metrics are fabricated.

### 81.10 Validation and documentation
- Dedicated Phase 81: 40 passed.
- Phase 76–81 integration validated.
- compileall validated.
- git diff --check validated.

## Architecture

The dashboard is a projection layer:

Phase 40–46 ranking reports
-> RankingDashboardService
-> Production read-only API
-> Frontend Ranking Dashboard

The existing ranking algorithms remain authoritative.

## Output

Phase 81 provides the ranking-facing frontend boundary needed for later
Top-K and performance dashboard phases.

Next official phase: **Phase 82 — Top-K Dashboard**.
