"""Tests for money flow tracing and aggregation."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB

from pyrite_journalism_investigation.money_flow import aggregate_flows, trace_money_flow


@pytest.fixture
def db(tmp_path):
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name="test", path=kb_path, kb_type="journalism-investigation")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb("test", "journalism-investigation", str(kb_path))
    yield db
    db.close()


def _create_entity(db, entity_id, title="", entity_type="person"):
    db.upsert_entry({
        "id": entity_id,
        "kb_name": "test",
        "title": title or entity_id.replace("-", " ").title(),
        "entry_type": entity_type,
        "metadata": {},
    })


def _create_txn(db, txn_id, sender, receiver, amount="10000", currency="USD",
                date="2024-01-15", txn_type="payment"):
    db.upsert_entry({
        "id": txn_id,
        "kb_name": "test",
        "title": f"Payment from {sender} to {receiver}",
        "entry_type": "transaction",
        "date": date,
        "metadata": {
            "sender": f"[[{sender}]]",
            "receiver": f"[[{receiver}]]",
            "amount": amount,
            "currency": currency,
            "transaction_type": txn_type,
        },
    })


class TestTraceMoneyFlowSingleHop:
    """Test 1: Simple single-hop flow (A->B)."""

    def test_single_hop_outbound(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000")

        result = trace_money_flow(db, "test", "entity-a", direction="outbound")

        assert result["entity"]["id"] == "entity-a"
        assert result["direction"] == "outbound"
        assert len(result["flows"]) >= 1
        flow = result["flows"][0]
        assert len(flow["path"]) == 1
        assert flow["path"][0]["amount"] == "50000"
        assert flow["total_amount"] == "50000.0"

    def test_single_hop_inbound(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000")

        result = trace_money_flow(db, "test", "entity-b", direction="inbound")

        assert result["direction"] == "inbound"
        assert len(result["flows"]) >= 1
        flow = result["flows"][0]
        assert flow["path"][0]["amount"] == "50000"


class TestTraceMoneyFlowMultiHop:
    """Test 2: Multi-hop chain (A->B->C) with 2 hops."""

    def test_two_hop_chain(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_entity(db, "entity-c", "Entity C")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000", date="2024-01-10")
        _create_txn(db, "txn-2", "entity-b", "entity-c", "30000", date="2024-01-20")

        result = trace_money_flow(db, "test", "entity-a", direction="outbound", max_hops=2)

        # Should find a flow that goes A->B->C
        multi_hop_flows = [f for f in result["flows"] if len(f["path"]) == 2]
        assert len(multi_hop_flows) >= 1
        path = multi_hop_flows[0]["path"]
        assert path[0]["amount"] == "50000"
        assert path[1]["amount"] == "30000"


class TestDirectionFilter:
    """Tests 3 and 4: Direction filtering."""

    def test_outbound_only(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_entity(db, "entity-c", "Entity C")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000")
        _create_txn(db, "txn-2", "entity-c", "entity-a", "20000")

        result = trace_money_flow(db, "test", "entity-a", direction="outbound")

        # Should only have outbound flows (A->B), not inbound (C->A)
        for flow in result["flows"]:
            first_txn = flow["path"][0]
            # The first transaction's sender should be entity-a or downstream
            assert first_txn["id"] == "txn-1"

    def test_inbound_only(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_entity(db, "entity-c", "Entity C")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000")
        _create_txn(db, "txn-2", "entity-c", "entity-a", "20000")

        result = trace_money_flow(db, "test", "entity-a", direction="inbound")

        # Should only have inbound flows (C->A), not outbound (A->B)
        for flow in result["flows"]:
            first_txn = flow["path"][0]
            assert first_txn["id"] == "txn-2"

    def test_both_direction(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_entity(db, "entity-c", "Entity C")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000")
        _create_txn(db, "txn-2", "entity-c", "entity-a", "20000")

        result = trace_money_flow(db, "test", "entity-a", direction="both")

        # Should have both inbound and outbound
        txn_ids = {txn["id"] for flow in result["flows"] for txn in flow["path"]}
        assert "txn-1" in txn_ids
        assert "txn-2" in txn_ids


class TestDateFiltering:
    """Test 5: Date range filtering."""

    def test_from_date_filter(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000", date="2024-01-15")
        _create_txn(db, "txn-2", "entity-a", "entity-b", "30000", date="2024-06-15")

        result = trace_money_flow(db, "test", "entity-a", direction="outbound",
                                  from_date="2024-03-01")

        txn_ids = {txn["id"] for flow in result["flows"] for txn in flow["path"]}
        assert "txn-2" in txn_ids
        assert "txn-1" not in txn_ids

    def test_to_date_filter(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000", date="2024-01-15")
        _create_txn(db, "txn-2", "entity-a", "entity-b", "30000", date="2024-06-15")

        result = trace_money_flow(db, "test", "entity-a", direction="outbound",
                                  to_date="2024-03-01")

        txn_ids = {txn["id"] for flow in result["flows"] for txn in flow["path"]}
        assert "txn-1" in txn_ids
        assert "txn-2" not in txn_ids

    def test_date_range_filter(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "10000", date="2024-01-15")
        _create_txn(db, "txn-2", "entity-a", "entity-b", "20000", date="2024-03-15")
        _create_txn(db, "txn-3", "entity-a", "entity-b", "30000", date="2024-06-15")

        result = trace_money_flow(db, "test", "entity-a", direction="outbound",
                                  from_date="2024-02-01", to_date="2024-05-01")

        txn_ids = {txn["id"] for flow in result["flows"] for txn in flow["path"]}
        assert txn_ids == {"txn-2"}


class TestCircularFlowDetection:
    """Test 6: Circular flow detection (A->B->C->A)."""

    def test_circular_flow_detected(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_entity(db, "entity-c", "Entity C")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000", date="2024-01-10")
        _create_txn(db, "txn-2", "entity-b", "entity-c", "40000", date="2024-01-20")
        _create_txn(db, "txn-3", "entity-c", "entity-a", "35000", date="2024-01-30")

        result = trace_money_flow(db, "test", "entity-a", direction="outbound", max_hops=3)

        assert len(result["circular_flows"]) >= 1
        circular = result["circular_flows"][0]
        assert len(circular["path"]) == 3


class TestMaxHopsLimit:
    """Test 7: Max hops limit respected."""

    def test_max_hops_limits_depth(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_entity(db, "entity-c", "Entity C")
        _create_entity(db, "entity-d", "Entity D")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000", date="2024-01-10")
        _create_txn(db, "txn-2", "entity-b", "entity-c", "40000", date="2024-01-20")
        _create_txn(db, "txn-3", "entity-c", "entity-d", "30000", date="2024-01-30")

        result = trace_money_flow(db, "test", "entity-a", direction="outbound", max_hops=1)

        # With max_hops=1, should only find A->B, not A->B->C or deeper
        for flow in result["flows"]:
            assert len(flow["path"]) <= 1


class TestAggregateFlows:
    """Test 8: Aggregate inflows/outflows with multiple transactions."""

    def test_aggregate_multiple_transactions(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_entity(db, "entity-c", "Entity C")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000", date="2024-01-10")
        _create_txn(db, "txn-2", "entity-a", "entity-b", "30000", date="2024-02-10")
        _create_txn(db, "txn-3", "entity-c", "entity-a", "20000", date="2024-03-10")

        result = aggregate_flows(db, "test", "entity-a")

        assert result["entity"]["id"] == "entity-a"
        # Outflows: 50000 + 30000 = 80000 to entity-b
        assert len(result["outflows"]) == 1
        outflow = result["outflows"][0]
        assert outflow["counterparty"]["id"] == "entity-b"
        assert outflow["total"] == "80000.0"
        assert outflow["count"] == 2

        # Inflows: 20000 from entity-c
        assert len(result["inflows"]) == 1
        inflow = result["inflows"][0]
        assert inflow["counterparty"]["id"] == "entity-c"
        assert inflow["total"] == "20000.0"
        assert inflow["count"] == 1

        # Net flow: inflows - outflows = 20000 - 80000 = -60000
        assert result["net_flow"] == "-60000.0"

    def test_aggregate_with_date_filter(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000", date="2024-01-10")
        _create_txn(db, "txn-2", "entity-a", "entity-b", "30000", date="2024-06-10")

        result = aggregate_flows(db, "test", "entity-a",
                                 from_date="2024-05-01", to_date="2024-12-31")

        assert len(result["outflows"]) == 1
        assert result["outflows"][0]["total"] == "30000.0"
        assert result["outflows"][0]["count"] == 1
        assert result["period"]["from"] == "2024-05-01"
        assert result["period"]["to"] == "2024-12-31"


class TestNoTransactions:
    """Test 9: Entity with no transactions."""

    def test_trace_no_transactions(self, db):
        _create_entity(db, "entity-a", "Entity A")

        result = trace_money_flow(db, "test", "entity-a")

        assert result["entity"]["id"] == "entity-a"
        assert result["flows"] == []
        assert result["circular_flows"] == []

    def test_aggregate_no_transactions(self, db):
        _create_entity(db, "entity-a", "Entity A")

        result = aggregate_flows(db, "test", "entity-a")

        assert result["entity"]["id"] == "entity-a"
        assert result["inflows"] == []
        assert result["outflows"] == []
        assert result["net_flow"] == "0.0"


class TestMissingAmounts:
    """Test 10: Amount aggregation handles missing amounts."""

    def test_missing_amount_in_trace(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000")
        # Transaction with no amount
        db.upsert_entry({
            "id": "txn-2",
            "kb_name": "test",
            "title": "Payment without amount",
            "entry_type": "transaction",
            "date": "2024-01-20",
            "metadata": {
                "sender": "[[entity-a]]",
                "receiver": "[[entity-b]]",
                "currency": "USD",
                "transaction_type": "payment",
            },
        })

        result = trace_money_flow(db, "test", "entity-a", direction="outbound")

        # Should still produce flows; missing amount doesn't crash
        assert len(result["flows"]) >= 1

    def test_missing_amount_in_aggregate(self, db):
        _create_entity(db, "entity-a", "Entity A")
        _create_entity(db, "entity-b", "Entity B")
        _create_txn(db, "txn-1", "entity-a", "entity-b", "50000")
        db.upsert_entry({
            "id": "txn-2",
            "kb_name": "test",
            "title": "Payment without amount",
            "entry_type": "transaction",
            "date": "2024-01-20",
            "metadata": {
                "sender": "[[entity-a]]",
                "receiver": "[[entity-b]]",
                "currency": "USD",
                "transaction_type": "payment",
            },
        })

        result = aggregate_flows(db, "test", "entity-a")

        # Should count both transactions but only sum the one with amount
        assert len(result["outflows"]) == 1
        assert result["outflows"][0]["count"] == 2
        assert result["outflows"][0]["total"] == "50000.0"
