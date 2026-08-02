from __future__ import annotations

import math

from app.core.config import settings
from app.models.market import ChainSnapshot, OptionContract
from app.models.viability import ViabilityRequest, ViabilityResponse


def solve_required_move(premium_gain: float, delta: float, gamma: float) -> float:
    delta_abs = max(abs(delta), 0.01)
    gamma_abs = max(abs(gamma), 0.0)

    if gamma_abs > 0.000001:
        disc = delta_abs * delta_abs + 2 * gamma_abs * premium_gain
        return max(0.0, (-delta_abs + math.sqrt(disc)) / gamma_abs)

    return premium_gain / delta_abs


def _liquidity_score(contract: OptionContract) -> float:
    score = 100.0
    if contract.last_price <= 0:
        return 0.0

    spread_pct = contract.spread_pct
    if spread_pct > 4:
        score -= 45
    elif spread_pct > 2:
        score -= 25
    elif spread_pct > 1:
        score -= 10

    if contract.volume <= 0:
        score -= 35
    elif contract.volume < 1000:
        score -= 20

    if contract.oi <= 0:
        score -= 25
    elif contract.oi < 10000:
        score -= 10

    return max(0.0, min(100.0, score))


def _oi_signal(contract: OptionContract) -> str:
    change = contract.oi_change
    if change > 0:
        return "OI_BUILDUP"
    if change < 0:
        return "OI_UNWINDING"
    return "FLAT"


def _score_contract(
    contract: OptionContract,
    required_move: float,
    expected_range_remaining: float | None,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 50.0

    delta = abs(contract.greeks.delta)
    if delta >= 0.65:
        score += 22
        reasons.append("Strong Delta efficiency.")
    elif delta >= 0.45:
        score += 12
        reasons.append("Acceptable Delta efficiency.")
    elif delta >= 0.30:
        score += 2
        reasons.append("Moderate Delta; target needs more spot travel.")
    else:
        score -= 18
        reasons.append("Low Delta makes the target movement inefficient.")

    liquidity = _liquidity_score(contract)
    score += (liquidity - 50) * 0.35
    reasons.append(f"Liquidity score {liquidity:.0f}/100.")

    if contract.spread_pct > 3:
        score -= 18
        reasons.append("Bid-ask spread is too wide.")
    elif contract.spread_pct <= 1:
        score += 8
        reasons.append("Bid-ask spread is efficient.")

    if contract.greeks.gamma > 0.001:
        score += 8
        reasons.append("Gamma can accelerate premium expansion.")
    elif contract.greeks.gamma <= 0:
        score -= 5

    if contract.oi_change > 0:
        score += 4
        reasons.append("Open interest is building.")
    elif contract.oi_change < 0:
        reasons.append("Open interest is unwinding.")

    if expected_range_remaining is not None:
        if required_move <= expected_range_remaining * 0.65:
            score += 18
            reasons.append("Required move fits comfortably inside the expected remaining range.")
        elif required_move <= expected_range_remaining:
            score += 4
            reasons.append("Required move is possible but consumes most of the expected range.")
        else:
            score -= 32
            reasons.append("Required move exceeds the expected remaining NIFTY range.")

    if required_move > 120:
        score -= 18
        reasons.append("Required NIFTY move is large for an intraday target.")
    elif required_move <= 35:
        score += 12
        reasons.append("Required NIFTY move is compact.")

    return max(0.0, min(100.0, score)), reasons


def _find_contract(snapshot: ChainSnapshot, strike: float, side: str) -> OptionContract:
    for contract in snapshot.contracts:
        if contract.side == side and abs(contract.strike - strike) < 0.01:
            return contract
    raise ValueError("Selected strike/side is not present in the option chain.")


def analyse_viability(
    snapshot: ChainSnapshot,
    request: ViabilityRequest,
) -> ViabilityResponse:
    contract = _find_contract(snapshot, request.strike, request.side)

    quantity = request.lots * settings.lot_size
    required_gross = request.target_net_profit + request.charge_buffer
    premium_gain = required_gross / quantity
    required_exit = request.entry_price + premium_gain
    required_move = solve_required_move(
        premium_gain,
        contract.greeks.delta,
        contract.greeks.gamma,
    )

    score, reasons = _score_contract(
        contract,
        required_move,
        request.expected_range_remaining,
    )

    if score >= 72:
        verdict = "VIABLE"
    elif score >= 52:
        verdict = "MARGINAL"
    else:
        verdict = "NOT_VIABLE"

    direction = 1 if request.side == "ce" else -1
    target_spot = snapshot.spot + direction * required_move

    best_contract = contract
    best_score = score

    for candidate in snapshot.contracts:
        if candidate.side != request.side:
            continue
        if abs(candidate.strike - request.strike) > 150:
            continue

        candidate_move = solve_required_move(
            premium_gain,
            candidate.greeks.delta,
            candidate.greeks.gamma,
        )
        candidate_score, _ = _score_contract(
            candidate,
            candidate_move,
            request.expected_range_remaining,
        )

        # Penalise very expensive/deep ITM substitutions slightly.
        candidate_score -= min(8.0, abs(candidate.strike - request.strike) / 50 * 1.5)

        if candidate_score > best_score + 4:
            best_contract = candidate
            best_score = candidate_score

    return ViabilityResponse(
        verdict=verdict,
        score=round(score, 1),
        selected_strike=contract.strike,
        side=request.side,
        lots=request.lots,
        quantity=quantity,
        entry_price=round(request.entry_price, 2),
        current_ltp=round(contract.last_price, 2),
        current_bid=round(contract.bid, 2),
        current_ask=round(contract.ask, 2),
        required_exit_premium=round(required_exit, 2),
        premium_gain_required=round(premium_gain, 2),
        required_nifty_move=round(required_move, 2),
        estimated_spot_target=round(target_spot, 2),
        delta_efficiency=round(abs(contract.greeks.delta), 3),
        gamma_support=round(abs(contract.greeks.gamma), 6),
        spread_pct=round(contract.spread_pct, 2),
        liquidity_score=round(_liquidity_score(contract), 1),
        oi_signal=_oi_signal(contract),
        expected_range_remaining=request.expected_range_remaining,
        reasons=reasons,
        better_strike=(
            best_contract.strike if best_contract.strike != contract.strike else None
        ),
        better_strike_score=(
            round(best_score, 1) if best_contract.strike != contract.strike else None
        ),
    )
