"""Money flow tracing and aggregation for journalism investigations.

Functions for traversing transaction chains, aggregating money flows,
and detecting circular flows between entities.
"""

from collections import defaultdict
from typing import Any

from .utils import parse_meta, strip_wikilink


def _get_all_transactions(
    db: Any, kb_name: str, *, from_date: str = "", to_date: str = ""
) -> list[dict[str, Any]]:
    """Load all transaction entries, optionally filtered by date range."""
    results = db.list_entries(kb_name=kb_name, entry_type="transaction", limit=5000)
    txns = []
    for r in results:
        date = str(r.get("date", ""))
        if from_date and date < from_date:
            continue
        if to_date and date > to_date:
            continue
        meta = parse_meta(r)
        sender_raw = meta.get("sender", "")
        receiver_raw = meta.get("receiver", "")
        if not sender_raw or not receiver_raw:
            continue
        txns.append({
            "id": r.get("id", ""),
            "title": r.get("title", ""),
            "date": date,
            "sender": strip_wikilink(sender_raw),
            "receiver": strip_wikilink(receiver_raw),
            "amount": meta.get("amount", ""),
            "currency": meta.get("currency", ""),
            "transaction_type": meta.get("transaction_type", ""),
        })
    return txns


def _get_entity_info(db: Any, kb_name: str, entity_id: str) -> dict[str, str]:
    """Get basic info for an entity. Returns id and title."""
    entries = db.list_entries(kb_name=kb_name, limit=5000)
    for e in entries:
        if e.get("id") == entity_id:
            return {"id": entity_id, "title": e.get("title", entity_id)}
    return {"id": entity_id, "title": entity_id}


def _build_txn_step(txn: dict[str, Any]) -> dict[str, Any]:
    """Build a path step dict from a transaction."""
    return {
        "id": txn["id"],
        "title": txn["title"],
        "amount": txn["amount"],
        "currency": txn["currency"],
        "date": txn["date"],
        "transaction_type": txn["transaction_type"],
    }


def _compute_total(path: list[dict[str, Any]]) -> str:
    """Compute total amount along a path. Uses the minimum amount in the chain."""
    amounts = []
    for step in path:
        amt = step.get("amount", "")
        if amt:
            try:
                amounts.append(float(amt))
            except (ValueError, TypeError):
                pass
    if not amounts:
        return "0.0"
    # For a single-hop, it's just the amount. For multi-hop, report the last step.
    # Actually, for flow tracing, total_amount = sum of first-hop amounts for
    # single-hop flows, or the flow path total. We'll use sum for single-hop
    # and the minimum (bottleneck) for multi-hop to represent max passthrough.
    if len(path) == 1:
        return str(amounts[0])
    return str(min(amounts))


def trace_money_flow(
    db: Any,
    kb_name: str,
    entity_id: str,
    *,
    direction: str = "both",
    max_hops: int = 3,
    from_date: str = "",
    to_date: str = "",
) -> dict[str, Any]:
    """Trace money flows starting from an entity.

    Args:
        db: Database instance.
        kb_name: Knowledge base name.
        entity_id: Starting entity ID.
        direction: "outbound" (sender), "inbound" (receiver), or "both".
        max_hops: Maximum number of hops to follow.
        from_date: Start date filter (YYYY-MM-DD).
        to_date: End date filter (YYYY-MM-DD).

    Returns:
        Dict with entity info, flows, circular_flows, and summary.
    """
    entity_info = _get_entity_info(db, kb_name, entity_id)
    txns = _get_all_transactions(db, kb_name, from_date=from_date, to_date=to_date)

    # Index transactions by sender and receiver
    by_sender: dict[str, list[dict]] = defaultdict(list)
    by_receiver: dict[str, list[dict]] = defaultdict(list)
    for t in txns:
        by_sender[t["sender"]].append(t)
        by_receiver[t["receiver"]].append(t)

    flows: list[dict[str, Any]] = []
    circular_flows: list[dict[str, Any]] = []

    def _trace_outbound(current_entity: str, path: list[dict], visited_txns: set):
        """Follow outbound flows: current_entity sent money to someone."""
        if len(path) > 0:
            # Record this path as a flow
            flow = {
                "path": list(path),
                "total_amount": _compute_total(path),
            }
            # Check if circular: does the last receiver == origin entity?
            last_txn = txns_by_id.get(path[-1]["id"])
            if last_txn and last_txn["receiver"] == entity_id:
                circular_flows.append(flow)
            else:
                flows.append(flow)

        if len(path) >= max_hops:
            return

        for t in by_sender.get(current_entity, []):
            if t["id"] in visited_txns:
                continue
            step = _build_txn_step(t)
            new_path = path + [step]
            new_visited = visited_txns | {t["id"]}
            _trace_outbound(t["receiver"], new_path, new_visited)

    def _trace_inbound(current_entity: str, path: list[dict], visited_txns: set):
        """Follow inbound flows: someone sent money to current_entity."""
        if len(path) > 0:
            flow = {
                "path": list(path),
                "total_amount": _compute_total(path),
            }
            last_txn = txns_by_id.get(path[-1]["id"])
            if last_txn and last_txn["sender"] == entity_id:
                circular_flows.append(flow)
            else:
                flows.append(flow)

        if len(path) >= max_hops:
            return

        for t in by_receiver.get(current_entity, []):
            if t["id"] in visited_txns:
                continue
            step = _build_txn_step(t)
            new_path = path + [step]
            new_visited = visited_txns | {t["id"]}
            _trace_inbound(t["sender"], new_path, new_visited)

    # Build ID lookup
    txns_by_id = {t["id"]: t for t in txns}

    if direction in ("outbound", "both"):
        _trace_outbound(entity_id, [], set())

    if direction in ("inbound", "both"):
        _trace_inbound(entity_id, [], set())

    summary_parts = [f"Traced {direction} flows for {entity_info['title']}"]
    summary_parts.append(f"{len(flows)} flow path(s) found")
    if circular_flows:
        summary_parts.append(f"{len(circular_flows)} circular flow(s) detected")
    summary = "; ".join(summary_parts)

    return {
        "entity": entity_info,
        "direction": direction,
        "flows": flows,
        "circular_flows": circular_flows,
        "summary": summary,
    }


def aggregate_flows(
    db: Any,
    kb_name: str,
    entity_id: str,
    *,
    from_date: str = "",
    to_date: str = "",
) -> dict[str, Any]:
    """Aggregate inflows and outflows by counterparty.

    Args:
        db: Database instance.
        kb_name: Knowledge base name.
        entity_id: Entity ID to aggregate flows for.
        from_date: Start date filter (YYYY-MM-DD).
        to_date: End date filter (YYYY-MM-DD).

    Returns:
        Dict with entity info, inflows, outflows, net_flow, and period.
    """
    entity_info = _get_entity_info(db, kb_name, entity_id)
    txns = _get_all_transactions(db, kb_name, from_date=from_date, to_date=to_date)

    # Aggregate outflows (entity is sender)
    outflow_totals: dict[str, float] = defaultdict(float)
    outflow_counts: dict[str, int] = defaultdict(int)
    # Aggregate inflows (entity is receiver)
    inflow_totals: dict[str, float] = defaultdict(float)
    inflow_counts: dict[str, int] = defaultdict(int)

    for t in txns:
        amt_str = t.get("amount", "")
        try:
            amt = float(amt_str) if amt_str else 0.0
        except (ValueError, TypeError):
            amt = 0.0

        if t["sender"] == entity_id:
            counterparty = t["receiver"]
            outflow_counts[counterparty] += 1
            outflow_totals[counterparty] += amt

        if t["receiver"] == entity_id:
            counterparty = t["sender"]
            inflow_counts[counterparty] += 1
            inflow_totals[counterparty] += amt

    def _build_flow_list(totals, counts):
        items = []
        for cp_id in sorted(totals.keys()):
            cp_info = _get_entity_info(db, kb_name, cp_id)
            items.append({
                "counterparty": cp_info,
                "total": str(totals[cp_id]),
                "count": counts[cp_id],
            })
        return items

    outflows_list = _build_flow_list(outflow_totals, outflow_counts)
    inflows_list = _build_flow_list(inflow_totals, inflow_counts)

    total_in = sum(inflow_totals.values())
    total_out = sum(outflow_totals.values())
    net = float(total_in - total_out)

    return {
        "entity": entity_info,
        "inflows": inflows_list,
        "outflows": outflows_list,
        "net_flow": str(net),
        "period": {
            "from": from_date,
            "to": to_date,
        },
    }
