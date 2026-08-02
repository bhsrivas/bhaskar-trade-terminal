from app.decision.viability import analyse_viability
from app.models.viability import ViabilityRequest
from app.services.demo import demo_chain


def test_viability_response():
    snapshot = demo_chain("2026-08-04")
    response = analyse_viability(
        snapshot,
        ViabilityRequest(
            expiry="2026-08-04",
            strike=24300,
            side="ce",
            lots=4,
            target_net_profit=5000,
            entry_price=106,
            charge_buffer=150,
            expected_range_remaining=80,
        ),
    )
    assert response.quantity == 260
    assert response.required_exit_premium > 106
    assert response.verdict in {"VIABLE", "MARGINAL", "NOT_VIABLE"}
