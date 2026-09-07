"""Advisory Execution Planner for Allocation Decisions.

Computes careful lot-rounded share quantity plans for advisory decisions:
- Reference price validation
- Commission fee, sell tax, and slippage estimation
- Available cash limit enforcement
- Board lot rounding (default 100 shares, configurable)
- Post-trade portfolio weight calculation and target error measurement
- Non-persistent, advisory simulation only (never mutates ledger or executes trades)
"""
from __future__ import annotations

import math
from typing import Any, Callable

from .models import AllocationDecision, AllocationExecutionPlan

DEFAULT_LOT_SIZE = 100
DEFAULT_COMMISSION_RATE = 0.001  # 0.1% broker commission
DEFAULT_SELL_TAX_RATE = 0.001     # 0.1% sell PIT tax
DEFAULT_SLIPPAGE_RATE = 0.0005    # 0.05% slippage estimate
DEFAULT_HARD_CAP = 0.20


def compute_execution_plan(
    decision: AllocationDecision,
    *,
    portfolio_nav: float,
    available_cash: float,
    current_quantity: float = 0.0,
    reference_price: float | None = None,
    price_date: str | None = None,
    price_source: str | None = None,
    lot_size: int = DEFAULT_LOT_SIZE,
    commission_rate: float = DEFAULT_COMMISSION_RATE,
    sell_tax_rate: float = DEFAULT_SELL_TAX_RATE,
    slippage_rate: float = DEFAULT_SLIPPAGE_RATE,
    hard_cap: float = DEFAULT_HARD_CAP,
    risk_simulator_fn: Callable[[list[dict]], dict] | None = None,
) -> AllocationExecutionPlan:
    """Compute a practical, lot-rounded share quantity plan for a decision."""
    symbol = decision.symbol
    action = decision.action
    weight = max(0.0, float(decision.current_weight or 0.0))
    nav = max(0.0, float(portfolio_nav or 0.0))
    cash = max(0.0, float(available_cash or 0.0))
    qty = max(0.0, float(current_quantity or 0.0))
    lot = max(1, int(lot_size or DEFAULT_LOT_SIZE))
    comm_rate = max(0.0, float(commission_rate))
    tax_rate = max(0.0, float(sell_tax_rate))
    slip_rate = max(0.0, float(slippage_rate))

    target_mid = decision.post_action_target_weight if decision.post_action_target_weight is not None else decision.target_mid
    target_min = decision.target_min
    target_max = decision.target_max

    # Non-actionable actions (HOLD, WATCH, KEEP_CASH) or missing price
    if action in ("HOLD", "WATCH", "KEEP_CASH"):
        ref_p = reference_price or 0.0
        post_mv = round(qty * ref_p, 2)
        post_w = (post_mv / nav) if nav > 0 else weight
        target_val = round(target_mid * nav, 2) if (target_mid is not None and nav > 0) else None
        return AllocationExecutionPlan(
            symbol=symbol,
            action=action,
            current_quantity=qty,
            current_market_value_vnd=post_mv,
            current_weight=weight,
            target_weight_theoretical=target_mid,
            target_weight_min=target_min,
            target_weight_max=target_max,
            target_weight_band_min=target_min,
            target_weight_band_max=target_max,
            target_value_vnd=target_val,
            reference_price=reference_price,
            reference_price_date=price_date,
            reference_price_source=price_source,
            price_date=price_date,
            price_source=price_source,
            raw_quantity_change=0.0,
            rounded_quantity_change=0.0,
            lot_size=lot,
            gross_trade_value=0.0,
            gross_trade_value_vnd=0.0,
            estimated_fee=0.0,
            estimated_fee_vnd=0.0,
            estimated_tax=0.0,
            estimated_tax_vnd=0.0,
            estimated_slippage=0.0,
            estimated_slippage_vnd=0.0,
            estimated_total_cost=0.0,
            estimated_total_cost_vnd=0.0,
            net_cash_change_vnd=0.0,
            cash_before=cash,
            cash_before_vnd=cash,
            cash_after=cash,
            cash_after_vnd=cash,
            post_trade_quantity=qty,
            post_trade_market_value=post_mv,
            post_trade_market_value_vnd=post_mv,
            post_trade_weight=post_w,
            target_error_pp=round((post_w - target_mid) * 100, 4) if target_mid is not None else None,
            within_target_band=True,
            is_executable=True,
            blocking_reasons=() if action == "HOLD" else ("NO_TRADE_REQUIRED",),
            reason_codes=decision.reason_codes,
        )

    # Missing or invalid reference price
    if reference_price is None or reference_price <= 0:
        target_val = round(target_mid * nav, 2) if (target_mid is not None and nav > 0) else None
        return AllocationExecutionPlan(
            symbol=symbol,
            action=action,
            current_quantity=qty,
            current_market_value_vnd=0.0,
            current_weight=weight,
            target_weight_theoretical=target_mid,
            target_weight_min=target_min,
            target_weight_max=target_max,
            target_weight_band_min=target_min,
            target_weight_band_max=target_max,
            target_value_vnd=target_val,
            reference_price=None,
            reference_price_date=price_date,
            reference_price_source=price_source,
            price_date=price_date,
            price_source=price_source,
            raw_quantity_change=0.0,
            rounded_quantity_change=0.0,
            lot_size=lot,
            cash_before=cash,
            cash_before_vnd=cash,
            cash_after=cash,
            cash_after_vnd=cash,
            post_trade_quantity=qty,
            post_trade_market_value=0.0,
            post_trade_market_value_vnd=0.0,
            post_trade_weight=weight,
            is_executable=False,
            blocking_reasons=("PRICE_UNAVAILABLE",),
            reason_codes=decision.reason_codes,
        )

    price = float(reference_price)
    current_mv = qty * price

    # 1. BUY_MORE Plan
    if action == "BUY_MORE":
        target = target_mid if target_mid is not None else 0.04
        t_min = target_min if target_min is not None else round(target * 0.75, 4)
        t_max = target_max if target_max is not None else min(hard_cap, round(target * 1.25, 4))
        target_val = round(target * nav, 2) if nav > 0 else None

        desired_mv = target * nav
        additional_mv = max(0.0, desired_mv - current_mv)
        effective_unit_cost = price * (1.0 + comm_rate + slip_rate)

        raw_buy = additional_mv / effective_unit_cost if effective_unit_cost > 0 else 0.0
        cash_max_buy = (cash / effective_unit_cost) if effective_unit_cost > 0 else 0.0
        cap_max_mv = t_max * nav
        cap_max_buy = max(0.0, cap_max_mv - current_mv) / price if price > 0 else 0.0

        feasible_buy = max(0.0, min(raw_buy, cash_max_buy, cap_max_buy))
        rounded_buy = math.floor(feasible_buy / lot) * lot

        if rounded_buy < lot:
            blocking = ("CASH_INSUFFICIENT_FOR_LOT",) if raw_buy >= lot and cash_max_buy < lot else ("TRADE_BELOW_MINIMUM_LOT",)
            return AllocationExecutionPlan(
                symbol=symbol, action=action, current_quantity=qty, current_market_value_vnd=round(current_mv, 2), current_weight=weight,
                target_weight_theoretical=target, target_weight_min=t_min, target_weight_max=t_max,
                target_weight_band_min=t_min, target_weight_band_max=t_max, target_value_vnd=target_val,
                reference_price=price, reference_price_date=price_date, reference_price_source=price_source,
                price_date=price_date, price_source=price_source,
                raw_quantity_change=round(raw_buy, 2), rounded_quantity_change=0.0, lot_size=lot,
                gross_trade_value=0.0, gross_trade_value_vnd=0.0, estimated_fee=0.0, estimated_fee_vnd=0.0,
                estimated_tax=0.0, estimated_tax_vnd=0.0, estimated_slippage=0.0, estimated_slippage_vnd=0.0,
                estimated_total_cost=0.0, estimated_total_cost_vnd=0.0, net_cash_change_vnd=0.0,
                cash_before=cash, cash_before_vnd=cash, cash_after=cash, cash_after_vnd=cash,
                post_trade_quantity=qty, post_trade_market_value=round(current_mv, 2), post_trade_market_value_vnd=round(current_mv, 2),
                post_trade_weight=weight, target_error_pp=round((weight - target) * 100, 4), within_target_band=(t_min <= weight <= t_max),
                is_executable=False, blocking_reasons=blocking, reason_codes=decision.reason_codes,
            )

        gross = rounded_buy * price
        fee = gross * comm_rate
        tax = 0.0
        slippage = gross * slip_rate
        total_cost = gross + fee + slippage
        cash_after = max(0.0, cash - total_cost)

        post_qty = qty + rounded_buy
        post_mv = current_mv + gross
        post_w = (post_mv / nav) if nav > 0 else 0.0

        target_err = round((post_w - target) * 100, 4)
        within_band = (t_min <= post_w <= t_max)

        gross_val = round(gross, 2)
        fee_val = round(fee, 2)
        tax_val = round(tax, 2)
        slip_val = round(slippage, 2)
        tot_val = round(total_cost, 2)
        cash_aft = round(cash_after, 2)
        net_cash = round(-total_cost, 2)
        post_mv_val = round(post_mv, 2)
        post_w_val = round(post_w, 4)

        return AllocationExecutionPlan(
            symbol=symbol, action=action, current_quantity=qty, current_market_value_vnd=round(current_mv, 2), current_weight=weight,
            target_weight_theoretical=target, target_weight_min=t_min, target_weight_max=t_max,
            target_weight_band_min=t_min, target_weight_band_max=t_max, target_value_vnd=target_val,
            reference_price=price, reference_price_date=price_date, reference_price_source=price_source,
            price_date=price_date, price_source=price_source,
            raw_quantity_change=round(raw_buy, 2), rounded_quantity_change=rounded_buy, lot_size=lot,
            gross_trade_value=gross_val, gross_trade_value_vnd=gross_val,
            estimated_fee=fee_val, estimated_fee_vnd=fee_val,
            estimated_tax=tax_val, estimated_tax_vnd=tax_val,
            estimated_slippage=slip_val, estimated_slippage_vnd=slip_val,
            estimated_total_cost=tot_val, estimated_total_cost_vnd=tot_val,
            net_cash_change_vnd=net_cash,
            cash_before=cash, cash_before_vnd=cash, cash_after=cash_aft, cash_after_vnd=cash_aft,
            post_trade_quantity=post_qty, post_trade_market_value=post_mv_val, post_trade_market_value_vnd=post_mv_val,
            post_trade_weight=post_w_val, target_error_pp=target_err, within_target_band=within_band,
            is_executable=True, blocking_reasons=(), reason_codes=decision.reason_codes,
        )

    # 2. REDUCE Plan
    if action == "REDUCE":
        target = target_mid if target_mid is not None else 0.05
        t_min = target_min if target_min is not None else round(target * 0.75, 4)
        t_max = target_max if target_max is not None else round(target * 1.25, 4)
        target_val = round(target * nav, 2) if nav > 0 else None

        desired_mv = target * nav
        sell_value = max(0.0, current_mv - desired_mv)
        raw_sell = sell_value / price if price > 0 else 0.0

        floor_sell = min(qty, math.floor(raw_sell / lot) * lot)
        ceil_sell = min(qty, math.ceil(raw_sell / lot) * lot)

        # Candidates must leave position > 0 for REDUCE
        candidates = []
        for s_qty in (ceil_sell, floor_sell):
            if 0 < s_qty < qty:
                p_w = ((qty - s_qty) * price) / nav if nav > 0 else 0.0
                err = abs(p_w - target)
                in_band = (t_min <= p_w <= t_max)
                candidates.append((in_band, -err, s_qty))

        if not candidates:
            # If no lot candidate keeps position > 0, fallback to floor_sell capped at qty - lot
            fallback_sell = max(0.0, min(floor_sell, qty - lot))
            if fallback_sell >= lot:
                p_w = ((qty - fallback_sell) * price) / nav if nav > 0 else 0.0
                candidates.append((t_min <= p_w <= t_max, -abs(p_w - target), fallback_sell))

        if not candidates:
            return AllocationExecutionPlan(
                symbol=symbol, action=action, current_quantity=qty, current_market_value_vnd=round(current_mv, 2), current_weight=weight,
                target_weight_theoretical=target, target_weight_min=t_min, target_weight_max=t_max,
                target_weight_band_min=t_min, target_weight_band_max=t_max, target_value_vnd=target_val,
                reference_price=price, reference_price_date=price_date, reference_price_source=price_source,
                price_date=price_date, price_source=price_source,
                raw_quantity_change=-round(raw_sell, 2), rounded_quantity_change=0.0, lot_size=lot,
                gross_trade_value=0.0, gross_trade_value_vnd=0.0, estimated_fee=0.0, estimated_fee_vnd=0.0,
                estimated_tax=0.0, estimated_tax_vnd=0.0, estimated_slippage=0.0, estimated_slippage_vnd=0.0,
                estimated_total_cost=0.0, estimated_total_cost_vnd=0.0, net_cash_change_vnd=0.0,
                cash_before=cash, cash_before_vnd=cash, cash_after=cash, cash_after_vnd=cash,
                post_trade_quantity=qty, post_trade_market_value=round(current_mv, 2), post_trade_market_value_vnd=round(current_mv, 2),
                post_trade_weight=weight, is_executable=False, blocking_reasons=("TRADE_BELOW_MINIMUM_LOT",), reason_codes=decision.reason_codes,
            )

        candidates.sort(reverse=True)
        chosen_sell = candidates[0][2]

        gross = chosen_sell * price
        fee = gross * comm_rate
        tax = gross * tax_rate
        slippage = gross * slip_rate
        total_cost = fee + tax + slippage
        net_proceeds = max(0.0, gross - total_cost)
        cash_after = cash + net_proceeds

        post_qty = qty - chosen_sell
        post_mv = post_qty * price
        post_w = (post_mv / nav) if nav > 0 else 0.0
        target_err = round((post_w - target) * 100, 4)
        within_band = (t_min <= post_w <= t_max)

        gross_val = round(gross, 2)
        fee_val = round(fee, 2)
        tax_val = round(tax, 2)
        slip_val = round(slippage, 2)
        tot_val = round(total_cost, 2)
        net_cash = round(net_proceeds, 2)
        cash_aft = round(cash_after, 2)
        post_mv_val = round(post_mv, 2)
        post_w_val = round(post_w, 4)

        return AllocationExecutionPlan(
            symbol=symbol, action=action, current_quantity=qty, current_market_value_vnd=round(current_mv, 2), current_weight=weight,
            target_weight_theoretical=target, target_weight_min=t_min, target_weight_max=t_max,
            target_weight_band_min=t_min, target_weight_band_max=t_max, target_value_vnd=target_val,
            reference_price=price, reference_price_date=price_date, reference_price_source=price_source,
            price_date=price_date, price_source=price_source,
            raw_quantity_change=-round(raw_sell, 2), rounded_quantity_change=-chosen_sell, lot_size=lot,
            gross_trade_value=gross_val, gross_trade_value_vnd=gross_val,
            estimated_fee=fee_val, estimated_fee_vnd=fee_val,
            estimated_tax=tax_val, estimated_tax_vnd=tax_val,
            estimated_slippage=slip_val, estimated_slippage_vnd=slip_val,
            estimated_total_cost=tot_val, estimated_total_cost_vnd=tot_val,
            net_cash_change_vnd=net_cash,
            cash_before=cash, cash_before_vnd=cash, cash_after=cash_aft, cash_after_vnd=cash_aft,
            post_trade_quantity=post_qty, post_trade_market_value=post_mv_val, post_trade_market_value_vnd=post_mv_val,
            post_trade_weight=post_w_val, target_error_pp=target_err, within_target_band=within_band,
            is_executable=True, blocking_reasons=(), reason_codes=decision.reason_codes,
        )

    # 3. SELL Plan
    if action == "SELL":
        sell_qty = qty
        if sell_qty <= 0:
            return AllocationExecutionPlan(
                symbol=symbol, action=action, current_quantity=qty, current_market_value_vnd=0.0, current_weight=weight,
                target_weight_theoretical=0.0, target_weight_min=0.0, target_weight_max=0.0,
                target_weight_band_min=0.0, target_weight_band_max=0.0, target_value_vnd=0.0,
                reference_price=price, reference_price_date=price_date, reference_price_source=price_source,
                price_date=price_date, price_source=price_source,
                raw_quantity_change=0.0, rounded_quantity_change=0.0, lot_size=lot,
                cash_before=cash, cash_before_vnd=cash, cash_after=cash, cash_after_vnd=cash,
                post_trade_quantity=0.0, post_trade_market_value=0.0, post_trade_market_value_vnd=0.0, post_trade_weight=0.0,
                is_executable=True, blocking_reasons=(), reason_codes=decision.reason_codes,
            )

        gross = sell_qty * price
        fee = gross * comm_rate
        tax = gross * tax_rate
        slippage = gross * slip_rate
        total_cost = fee + tax + slippage
        net_proceeds = max(0.0, gross - total_cost)
        cash_after = cash + net_proceeds

        gross_val = round(gross, 2)
        fee_val = round(fee, 2)
        tax_val = round(tax, 2)
        slip_val = round(slippage, 2)
        tot_val = round(total_cost, 2)
        net_cash = round(net_proceeds, 2)
        cash_aft = round(cash_after, 2)

        return AllocationExecutionPlan(
            symbol=symbol, action=action, current_quantity=qty, current_market_value_vnd=round(current_mv, 2), current_weight=weight,
            target_weight_theoretical=0.0, target_weight_min=0.0, target_weight_max=0.0,
            target_weight_band_min=0.0, target_weight_band_max=0.0, target_value_vnd=0.0,
            reference_price=price, reference_price_date=price_date, reference_price_source=price_source,
            price_date=price_date, price_source=price_source,
            raw_quantity_change=-sell_qty, rounded_quantity_change=-sell_qty, lot_size=lot,
            gross_trade_value=gross_val, gross_trade_value_vnd=gross_val,
            estimated_fee=fee_val, estimated_fee_vnd=fee_val,
            estimated_tax=tax_val, estimated_tax_vnd=tax_val,
            estimated_slippage=slip_val, estimated_slippage_vnd=slip_val,
            estimated_total_cost=tot_val, estimated_total_cost_vnd=tot_val,
            net_cash_change_vnd=net_cash,
            cash_before=cash, cash_before_vnd=cash, cash_after=cash_aft, cash_after_vnd=cash_aft,
            post_trade_quantity=0.0, post_trade_market_value=0.0, post_trade_market_value_vnd=0.0, post_trade_weight=0.0,
            target_error_pp=0.0, within_target_band=True,
            is_executable=True, blocking_reasons=(), reason_codes=decision.reason_codes,
        )

    # Fallback
    return AllocationExecutionPlan(
        symbol=symbol, action=action, current_quantity=qty, current_market_value_vnd=round(qty * (price if 'price' in locals() else 0.0), 2), current_weight=weight,
        reference_price=price if 'price' in locals() else None, reference_price_date=price_date, reference_price_source=price_source,
        price_date=price_date, price_source=price_source,
        cash_before=cash, cash_before_vnd=cash, cash_after=cash, cash_after_vnd=cash, post_trade_quantity=qty, post_trade_weight=weight,
        is_executable=False, blocking_reasons=("UNSUPPORTED_ACTION",), reason_codes=decision.reason_codes,
    )
