from app.broker.dhan import normalise_dhan_chain


def test_normalise_dictionary_chain():
    payload = {
        "data": {
            "last_price": 24300,
            "oc": {
                "24300.000000": {
                    "ce": {
                        "last_price": 100,
                        "top_bid_price": 99.5,
                        "top_ask_price": 100.5,
                        "oi": 100000,
                        "previous_oi": 90000,
                        "volume": 50000,
                        "implied_volatility": 10,
                        "greeks": {"delta": 0.5, "gamma": 0.001, "theta": -10, "vega": 9},
                    },
                    "pe": {
                        "last_price": 110,
                        "top_bid_price": 109.5,
                        "top_ask_price": 110.5,
                        "oi": 120000,
                        "previous_oi": 100000,
                        "volume": 60000,
                        "implied_volatility": 11,
                        "greeks": {"delta": -0.5, "gamma": 0.001, "theta": -10, "vega": 9},
                    },
                }
            },
        }
    }

    snapshot = normalise_dhan_chain(payload, "2026-08-04")
    assert snapshot.spot == 24300
    assert len(snapshot.contracts) == 2
    assert snapshot.contracts[0].last_price > 0
