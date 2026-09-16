# Product Architecture

`health-tracker` is a private health/exercise operating system, not a generic dashboard.

## Components

Each integration is a component with one owner module, one runtime state boundary, and one failure mode that can be displayed.

| component | owner | role | status |
|---|---|---|---|
| Health Auto Export | `ingest/hae_rest.py` | live Apple Health JSON ingest | live |
| Apple Health XML | `ingest/apple_export_xml.py` | disaster-recovery and historical backfill | live |
| BodyStats / DEXA | `data/imports/dexa/`, future `ingest/dexa_bundle.py` | ground-truth body composition anchors | staged |
| Labs | `data/templates/labs_template.csv`, future `ingest/labs_csv.py` | semi-annual blood anchors | planned |
| Genome | future `ingest/genome/` | priors and experiment generation | planned |
| API | `api/app.py` | OpenAPI surface over the state model | live, partial |
| Push | `jobs/push.py` | deterministic Telegram/ntfy alerts | live |
| Dashboard | future frontend app | private board of health/exercise statistics | planned |
| Life dashboard widget | `jobs/widget_snapshot.py` + `ops/console/health.py` | small status widget for the existing ops console | live snapshot |

`config/components.yaml` is the registry.

## Dashboard Direction

The private dashboard should be a board of widgets, optimized for scanning:

- freshness: HAE lag, backfill date, DEXA/lab anchor age
- body composition: weight trend, DEXA bands, fat/lean/VAT trajectory
- recovery: HRV/RHR state, sleep debt, illness flags
- activity: steps, exercise minutes, load, workouts, ACWR
- anchors: next DEXA, last lab, calibration state
- experiments: active experiments, predictions, override ledger

The dashboard reads from the API and DuckDB-derived tables. It should not read raw imports, raw DEXA report text, raw genome files, or secrets.

## Life Dashboard Boundary

The existing life dashboard is the zero-token ops console. It should not import DuckDB or health internals directly. Instead:

1. `jobs/widget_snapshot.py` writes `~/.local/state/health-tracker-widget.json`.
2. `ops/console/health.py` reads that JSON and renders a small widget.
3. If the snapshot goes stale or says live ingest is stale, the widget turns warn/bad.

That contract keeps the life dashboard cheap, deterministic, and decoupled.
