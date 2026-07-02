"""
BinanceExecution — routes orders to Binance spot API.

dry_run=True  (default): simulates fills locally, no real orders placed.
dry_run=False           : places real market orders; requires BINANCE_API_KEY + BINANCE_SECRET.

Required env vars for live mode:
    BINANCE_API_KEY
    BINANCE_SECRET
"""

import os
import uuid
from datetime import datetime, timezone

from binance.client import Client
from binance.enums import ORDER_TYPE_MARKET, SIDE_BUY, SIDE_SELL

from backend.app.schemas.execution import ExecutionResponse, OrderSide
from backend.app.schemas.live_trading import LiveOrder
from backend.app.services.execution.base_execution import BaseExecution


class BinanceExecution(BaseExecution):

    FEE_PERCENT = 0.10
    SLIPPAGE_PERCENT = 0.05

    def __init__(self, symbol: str, dry_run: bool = True) -> None:
        self.symbol = symbol.upper()
        self.dry_run = dry_run
        self._orders: list[LiveOrder] = []

        if dry_run:
            self._client = Client()
        else:
            api_key = os.getenv("BINANCE_API_KEY")
            secret = os.getenv("BINANCE_SECRET")
            if not api_key or not secret:
                raise RuntimeError(
                    "Live trading requires BINANCE_API_KEY and BINANCE_SECRET env vars"
                )
            self._client = Client(api_key, secret)

    # ------------------------------------------------------------------
    # BaseExecution interface
    # ------------------------------------------------------------------

    def execute(
        self,
        side: OrderSide,
        price: float,
        quantity: float,
    ) -> ExecutionResponse:
        if self.dry_run:
            return self._dry_execute(side, price, quantity)
        return self._live_execute(side, price, quantity)

    # ------------------------------------------------------------------
    # Utility (mirrors SimpleExecution — uses portfolio cash, not exchange balance)
    # ------------------------------------------------------------------

    def calculate_affordable_quantity(
        self,
        cash: float,
        price: float,
        requested_quantity: float,
    ) -> float:
        executed_price = price * (1 + self.SLIPPAGE_PERCENT / 100)
        cost_per_unit = executed_price * (1 + self.FEE_PERCENT / 100)
        if cost_per_unit <= 0:
            return 0.0
        return min(requested_quantity, cash / cost_per_unit)

    # ------------------------------------------------------------------
    # Order history
    # ------------------------------------------------------------------

    def get_orders(self) -> list[LiveOrder]:
        return self._orders

    def cancel_all_open_orders(self) -> int:
        if self.dry_run:
            return 0
        open_orders = self._client.get_open_orders(symbol=self.symbol)
        for order in open_orders:
            self._client.cancel_order(symbol=self.symbol, orderId=order["orderId"])
        return len(open_orders)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _dry_execute(
        self,
        side: OrderSide,
        price: float,
        quantity: float,
    ) -> ExecutionResponse:
        if side == OrderSide.BUY:
            executed_price = price * (1 + self.SLIPPAGE_PERCENT / 100)
        else:
            executed_price = price * (1 - self.SLIPPAGE_PERCENT / 100)

        trade_value = executed_price * quantity
        fee = trade_value * self.FEE_PERCENT / 100
        slippage_cost = abs(executed_price - price) * quantity
        total_cost = trade_value + fee if side == OrderSide.BUY else trade_value - fee

        self._log_order(side, price, executed_price, quantity, fee, "FILLED_DRY")

        return ExecutionResponse(
            side=side,
            requested_price=price,
            executed_price=round(executed_price, 8),
            quantity=quantity,
            trade_value=round(trade_value, 8),
            fee=round(fee, 8),
            slippage_cost=round(slippage_cost, 8),
            total_cost=round(total_cost, 8),
        )

    def _live_execute(
        self,
        side: OrderSide,
        price: float,
        quantity: float,
    ) -> ExecutionResponse:
        binance_side = SIDE_BUY if side == OrderSide.BUY else SIDE_SELL
        qty_rounded = round(quantity, 5)

        order = self._client.create_order(
            symbol=self.symbol,
            side=binance_side,
            type=ORDER_TYPE_MARKET,
            quantity=qty_rounded,
        )

        fills = order.get("fills", [])
        if fills:
            total_qty = sum(float(f["qty"]) for f in fills)
            executed_price = (
                sum(float(f["price"]) * float(f["qty"]) for f in fills) / total_qty
                if total_qty > 0
                else price
            )
            fee = sum(float(f["commission"]) for f in fills)
        else:
            executed_price = price
            fee = float(order.get("cummulativeQuoteQty", 0)) * self.FEE_PERCENT / 100

        filled_qty = float(order.get("executedQty", qty_rounded))
        trade_value = executed_price * filled_qty
        slippage_cost = abs(executed_price - price) * filled_qty
        total_cost = trade_value + fee if side == OrderSide.BUY else trade_value - fee

        self._log_order(
            side, price, executed_price, filled_qty, fee,
            order.get("status", "FILLED"),
            order_id=str(order.get("orderId", "")),
        )

        return ExecutionResponse(
            side=side,
            requested_price=price,
            executed_price=round(executed_price, 8),
            quantity=filled_qty,
            trade_value=round(trade_value, 8),
            fee=round(fee, 8),
            slippage_cost=round(slippage_cost, 8),
            total_cost=round(total_cost, 8),
        )

    def _log_order(
        self,
        side: OrderSide,
        requested_price: float,
        executed_price: float,
        quantity: float,
        fee: float,
        status: str,
        order_id: str = "",
    ) -> None:
        self._orders.append(
            LiveOrder(
                order_id=order_id or str(uuid.uuid4()),
                side=side.value,
                symbol=self.symbol,
                quantity=round(quantity, 6),
                requested_price=round(requested_price, 4),
                executed_price=round(executed_price, 4),
                fee=round(fee, 8),
                status=status,
                timestamp=datetime.now(timezone.utc).isoformat(),
                is_dry_run=self.dry_run,
            )
        )
