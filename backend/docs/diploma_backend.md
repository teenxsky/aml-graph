# Backend Architecture Notes

## Pipeline

```text
CSV -> pandas -> normalized transactions -> NetworkX graph -> detectors -> scoring -> layout -> SSE/API
```

The backend uses FastAPI endpoints, pandas parsing, NetworkX graph algorithms, and an in-memory session store keyed by UUID.

## IBM Normalization

IBM Transactions for AML is treated as the standard input format. The parser validates required columns, empty key fields, timestamps, numeric amounts, and `Is Laundering`.

Normalized transaction schema:

- `transaction_id`
- `timestamp`
- `sender_id`
- `receiver_id`
- `amount`
- `amount_received`
- `receiving_currency`
- `payment_currency`
- `payment_format`
- `is_laundering`

Composite account IDs prevent collisions between accounts from different banks:

```text
sender_id = From Bank + ":" + Account
receiver_id = To Bank + ":" + Account.1
```

## Graph Model

Accounts are graph nodes. Transactions are directed edges. IBM uploads use `nx.MultiDiGraph`, because several payments may exist between the same sender and receiver.

Node attributes include account ID, type, label, flow totals, risk score, and alert IDs.
Edge attributes include transaction ID, amount, timestamp, currencies, payment format, risk score, alert IDs, and `is_laundering` as an evaluation label.

## Detectors

Cycle detector searches directed cycles of length 2-6 and calculates:

- time span;
- total amount;
- amount preservation ratio `rho = min(amount) / max(amount)`;
- optional drain rate when received amounts are available.

Fan-out detector searches one sender paying several receivers in a short window. It uses coefficient of variation:

```text
CV = std(amounts) / mean(amounts)
```

Transit detector searches nodes with both incoming and outgoing edges and balanced flows:

```text
balance_ratio = 1 - abs(F_in - F_out) / max(F_in, F_out)
```

Shared identity detector groups accounts by `device_id` and `ip_address` when those attributes exist.

## Scoring

Risk score is aggregated from alerts:

```text
score = 1 - product(1 - s_i)
```

This keeps the score in `[0, 1]`, makes multiple independent alerts increase risk, and avoids using the `Is Laundering` label as a model feature.

## Layout

The server precomputes node coordinates in `src/graph/layout.py`. The preferred
implementation is NetworkX `forceatlas2_layout`, with `spring_layout` as a
graceful fallback.

ForceAtlas2 is a force-directed layout: connected vertices attract each other,
while unrelated vertices repel each other. For AML visualization this is useful
because suspicious structures often need to be inspected as neighborhoods:
cycles, transit accounts, fan-out clusters, and shared-identity groups become
visually closer. It is not an analytical detector by itself; it is a
visualization step that helps the frontend render a stable graph. For large
graphs, the backend lays out a high-degree subgraph and places remaining nodes
near already positioned neighbors.

## SSE

The stream endpoint emits progress events and graph chunks. The old stream contract is preserved by keeping `graph_meta`, `nodes_chunk`, `edges_chunk`, `detector_result`, and `stream_done`.

## GNN Baseline

The optional GNN baseline is future work, not a production backend feature. It
currently provides only dataset construction for an offline experiment. This is
intentional: PyTorch/PyG are heavy dependencies on Windows/Python 3.14, so they
must not block the FastAPI backend.

The intended baseline treats transactions as nodes in a transaction graph. A
directed edge is added between transaction nodes when money can flow from one
transaction into a later transaction through a shared account within a time
window.

The label is transaction-level `Is Laundering`, so the task is transaction node
classification. Training is offline and not used in the upload path, SSE stream,
detectors, or risk scoring.

## System Limits

- In-memory sessions do not survive restart.
- NetworkX is not suitable for very large production graphs without sampling or distributed processing.
- Global betweenness is expensive, so detector logic avoids making it mandatory for very large graphs.
- Pure IBM data does not contain device/IP identity fields.
- The project is a diploma MVP, not a production AML monitoring system.
