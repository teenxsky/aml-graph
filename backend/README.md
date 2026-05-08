# AML Graph Backend

FastAPI backend for AML/anti-fraud transaction graph analysis.

## Run

From `backend`:

```powershell
uv sync
uv run pytest
uv run python -m src.main
```

Default local backend URL:

```text
http://127.0.0.1:9090/api/v1
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:9090/api/v1/health
```

## Supported Uploads

### Existing mapped CSV

`POST /api/v1/upload`

This endpoint accepts a file plus `column_mapping` form field and keeps the old project contract.
The mapping schema is:

```json
{
  "sender_id": "sender",
  "receiver_id": "receiver",
  "amount_paid": "amount",
  "timestamp": "timestamp",
  "sender_bank": null,
  "receiver_bank": null,
  "amount_received": null,
  "payment_currency": null,
  "receiving_currency": null,
  "transaction_type": null,
  "device_id": null,
  "ip_address": null,
  "is_laundering": null
}
```

### IBM Transactions for AML CSV

`POST /api/v1/upload/ibm`

Only CSV is enabled in the backend path. Excel is intentionally rejected until
`openpyxl` is added and tested on the target Python/Windows environment.

Required IBM columns:

- `Timestamp`
- `From Bank`
- `Account`
- `To Bank`
- `Account.1`
- `Amount Received`
- `Receiving Currency`
- `Amount Paid`
- `Payment Currency`
- `Payment Format`
- `Is Laundering`

Normalization:

- `sender_id = From Bank + ":" + Account`
- `receiver_id = To Bank + ":" + Account.1`
- `amount = Amount Paid`
- `is_laundering` is stored as a label for evaluation only

Example:

```powershell
curl.exe -X POST http://127.0.0.1:9090/api/v1/upload/ibm `
  -F "file=@data/ibm_sample.csv"
```

## Stream

`GET /api/v1/stream/{session_id}`

The stream keeps the existing events and also emits progress stages:

- `started`
- `parsed`
- `graph_built`
- `layout_done`
- `detectors_done`
- `scoring_done`
- `completed`
- `stream_done`

Existing graph events:

- `graph_meta`
- `nodes_chunk`
- `edges_chunk`
- `detector_result`

## Graph API

- `GET /api/v1/sessions/{session_id}/stats`
- `GET /api/v1/sessions/{session_id}/graph`
- `GET /api/v1/sessions/{session_id}/alerts`
- `GET /api/v1/sessions/{session_id}/filters`
- `GET /api/v1/sessions/{session_id}/subgraph?node_id=...&k=2`

Graph payload nodes include `id`, `type`, `label`, `x`, `y`, `risk_score`, `alerts`, and `attributes`.
Edges include `id`, `source`, `target`, `amount`, `timestamp`, `risk_score`, `alerts`, and `attributes`.

## Algorithms

The backend builds a directed NetworkX graph. IBM uploads use `MultiDiGraph`, because real transaction data can contain multiple transfers between the same accounts.

Detectors:

- cycles of length 2-6 with time delta and amount preservation ratio;
- fan-out from one sender to several receivers in a short time window;
- transit nodes with balanced incoming/outgoing flow and optional betweenness;
- shared identity detector for `device_id` or `ip_address` when such fields exist.

Risk scoring is alert-based:

```text
score = 1 - product(1 - alert_score_i)
```

Nodes and edges without alerts remain at score `0`. `Is Laundering` is not used as a feature.

Layout is implemented in `src/graph/layout.py`. The preferred algorithm is
NetworkX `forceatlas2_layout`; if it fails or is unavailable, the backend falls
back to `spring_layout`. ForceAtlas2 is a force-directed layout designed for
visual exploration: connected and densely related nodes are pulled together,
unrelated regions repel each other, and hubs remain readable. This makes it a
good default for transaction graph visualization, where the frontend needs
stable clusters and readable suspicious neighborhoods rather than exact
geographic coordinates. For large graphs, layout is calculated for a high-degree
subgraph and remaining nodes are placed near already positioned neighbors.

## Optional GNN Baseline

GNN is a future/offline experiment and is not part of the mandatory backend
runtime. The current code builds a transaction-node dataset scaffold only; it
does not train or serve a model from the upload/API path. The intended direction
matches common AML GNN notebooks such as the linked Kaggle reference: transaction
labels are treated as transaction-node labels, not direct account-node labels.

Dataset construction:

```powershell
uv run python -m src.ml.gnn_baseline --input data/ibm_sample.csv --epochs 5 --fast
```

If PyTorch is not installed, the script raises a clear `RuntimeError`. Upload
and API endpoints do not import PyTorch.

## Limitations

- NetworkX and session storage are in-memory.
- Sessions disappear on backend restart.
- No distributed storage or background job queue.
- Layout is limited for very large graphs and uses a subgraph/fallback strategy.
- Pure IBM CSV has no `device_id` or `ip_address`, so shared identity alerts are empty unless such columns are present in normalized data.
- GNN is only a dataset/baseline scaffold for future work; it is not used by rule-based scoring.
