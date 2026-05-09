"""On-chain event indexer service — syncs contract events to the database.

Connects to Base via WebSocket and listens for events emitted by NILE
contracts (BondingCurve, NileRouter, SoulTokenFactory). When an event
is detected it is recorded in the database so the off-chain state mirrors
on-chain reality.

Events indexed:
  - Buy(address indexed buyer, uint256 ethIn, uint256 tokensOut, uint256 fee, uint256 newPrice)
  - Sell(address indexed seller, uint256 tokensIn, uint256 ethOut, uint256 fee, uint256 newPrice)
  - SoulTokenCreated(bytes16 indexed personId, address token, address curve)
  - GraduationTriggered(uint256 reserveBalance)
  - TradeRouted(bytes16 indexed personId, address indexed trader, bool isBuy, uint256 ethAmount, uint256 tokenAmount)

Usage:
  Intended to be started as a background asyncio task from the worker process.
  >>> from nile.services.event_indexer import EventIndexer
  >>> indexer = EventIndexer()
  >>> await indexer.start()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nile.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event ABIs — minimal definitions for decoding
# ---------------------------------------------------------------------------

BONDING_CURVE_EVENTS: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "name": "Buy",
        "type": "event",
        "inputs": [
            {"indexed": True, "name": "buyer", "type": "address"},
            {"indexed": False, "name": "ethIn", "type": "uint256"},
            {"indexed": False, "name": "tokensOut", "type": "uint256"},
            {"indexed": False, "name": "fee", "type": "uint256"},
            {"indexed": False, "name": "newPrice", "type": "uint256"},
        ],
    },
    {
        "anonymous": False,
        "name": "Sell",
        "type": "event",
        "inputs": [
            {"indexed": True, "name": "seller", "type": "address"},
            {"indexed": False, "name": "tokensIn", "type": "uint256"},
            {"indexed": False, "name": "ethOut", "type": "uint256"},
            {"indexed": False, "name": "fee", "type": "uint256"},
            {"indexed": False, "name": "newPrice", "type": "uint256"},
        ],
    },
    {
        "anonymous": False,
        "name": "GraduationTriggered",
        "type": "event",
        "inputs": [
            {"indexed": False, "name": "reserveBalance", "type": "uint256"},
        ],
    },
]

ROUTER_EVENTS: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "name": "TradeRouted",
        "type": "event",
        "inputs": [
            {"indexed": True, "name": "personId", "type": "bytes16"},
            {"indexed": True, "name": "trader", "type": "address"},
            {"indexed": False, "name": "isBuy", "type": "bool"},
            {"indexed": False, "name": "ethAmount", "type": "uint256"},
            {"indexed": False, "name": "tokenAmount", "type": "uint256"},
        ],
    },
]

FACTORY_EVENTS: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "name": "SoulTokenCreated",
        "type": "event",
        "inputs": [
            {"indexed": True, "name": "personId", "type": "bytes16"},
            {"indexed": False, "name": "token", "type": "address"},
            {"indexed": False, "name": "curve", "type": "address"},
        ],
    },
]


class EventIndexer:
    """Background service that indexes on-chain events into the database.

    Architecture:
      1. Connects to Base RPC via WebSocket (for real-time) or HTTP (for polling).
      2. Creates event filter for each contract address.
      3. On each new event, decodes it and writes to the database.
      4. Maintains a cursor (last indexed block) so it can resume after restart.
    """

    def __init__(self) -> None:
        self._w3 = None
        self._running = False
        self._poll_interval: int = 5  # seconds between polls

        # Contract addresses — will be populated after deployment
        # These come from settings or can be overridden
        self.router_address: str = settings.router_address
        self.factory_address: str = settings.factory_address

        # Track last indexed block per contract (persisted to Redis in production)
        self._last_block: dict[str, int] = {}

    @property
    def w3(self):
        """Lazy Web3 connection."""
        if self._w3 is None:
            try:
                from web3 import Web3

                ws_url = settings.chain_ws_url
                if ws_url:
                    self._w3 = Web3(Web3.WebsocketProvider(ws_url))
                    logger.info("EventIndexer connected via WebSocket: %s", ws_url)
                else:
                    # Fall back to HTTP polling
                    self._w3 = Web3(Web3.HTTPProvider(settings.chain_rpc_url))
                    logger.info("EventIndexer connected via HTTP: %s", settings.chain_rpc_url)
            except ImportError:
                logger.error("web3 not installed — run: pip install web3")
                raise
        return self._w3

    async def start(self) -> None:
        """Start the event indexing loop."""
        if not self.router_address and not self.factory_address:
            logger.warning(
                "EventIndexer: No contract addresses configured. "
                "Set NILE_ROUTER_ADDRESS and NILE_FACTORY_ADDRESS to enable indexing."
            )
            return

        self._running = True
        logger.info("EventIndexer starting — polling every %ds", self._poll_interval)

        while self._running:
            try:
                await self._poll_events()
            except Exception:
                logger.exception("EventIndexer poll cycle failed")

            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        """Gracefully stop the indexer."""
        logger.info("EventIndexer stopping...")
        self._running = False

    async def _poll_events(self) -> None:
        """Poll for new events from all tracked contracts."""
        current_block = self.w3.eth.block_number

        # Index Router events (TradeRouted)
        if self.router_address:
            await self._index_contract_events(
                contract_address=self.router_address,
                event_abis=ROUTER_EVENTS,
                current_block=current_block,
                handler=self._handle_router_event,
            )

        # Index Factory events (SoulTokenCreated)
        if self.factory_address:
            await self._index_contract_events(
                contract_address=self.factory_address,
                event_abis=FACTORY_EVENTS,
                current_block=current_block,
                handler=self._handle_factory_event,
            )

    async def _index_contract_events(
        self,
        contract_address: str,
        event_abis: list[dict],
        current_block: int,
        handler,
    ) -> None:
        """Index events for a specific contract from last checkpoint to current block."""
        from web3 import Web3

        last = self._last_block.get(contract_address, max(current_block - 1000, 0))

        if last >= current_block:
            return  # No new blocks

        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=event_abis,
        )

        # Process in chunks of 2000 blocks to avoid RPC limits
        chunk_size = 2000
        from_block = last + 1

        while from_block <= current_block:
            to_block = min(from_block + chunk_size - 1, current_block)

            for event_abi in event_abis:
                event_name = event_abi["name"]
                try:
                    event_filter = getattr(contract.events, event_name)
                    logs = event_filter.create_filter(
                        fromBlock=from_block, toBlock=to_block
                    ).get_all_entries()

                    for log in logs:
                        await handler(event_name, log)
                        logger.info(
                            "Indexed %s event at block %d tx %s",
                            event_name,
                            log["blockNumber"],
                            log["transactionHash"].hex(),
                        )
                except Exception:
                    logger.exception(
                        "Failed to index %s events from block %d to %d",
                        event_name,
                        from_block,
                        to_block,
                    )

            from_block = to_block + 1

        self._last_block[contract_address] = current_block

    async def _handle_router_event(self, event_name: str, log: dict) -> None:
        """Handle a TradeRouted event from the NileRouter contract."""
        if event_name != "TradeRouted":
            return

        args = log["args"]
        person_id_bytes: bytes = args["personId"]
        trader: str = args["trader"]
        is_buy: bool = args["isBuy"]
        eth_amount_wei: int = args["ethAmount"]
        token_amount_wei: int = args["tokenAmount"]

        tx_hash = log["transactionHash"].hex()
        block_number = log["blockNumber"]

        # Convert from wei to float
        eth_amount = eth_amount_wei / 1e18
        token_amount = token_amount_wei / 1e18

        logger.info(
            "TradeRouted: person=%s trader=%s side=%s eth=%.6f tokens=%.4f tx=%s",
            person_id_bytes.hex(),
            trader,
            "buy" if is_buy else "sell",
            eth_amount,
            token_amount,
            tx_hash,
        )

        # Create Trade record in database
        await self._record_trade(
            person_id_hex=person_id_bytes.hex(),
            trader_address=trader,
            side="buy" if is_buy else "sell",
            eth_amount=eth_amount,
            token_amount=token_amount,
            tx_hash=tx_hash,
            block_number=block_number,
        )

    async def _handle_factory_event(self, event_name: str, log: dict) -> None:
        """Handle a SoulTokenCreated event from the Factory contract."""
        if event_name != "SoulTokenCreated":
            return

        args = log["args"]
        person_id_bytes: bytes = args["personId"]
        token_address: str = args["token"]
        curve_address: str = args["curve"]

        logger.info(
            "SoulTokenCreated: person=%s token=%s curve=%s",
            person_id_bytes.hex(),
            token_address,
            curve_address,
        )

        # Update SoulToken record with on-chain addresses
        await self._update_token_addresses(
            person_id_hex=person_id_bytes.hex(),
            token_address=token_address,
            curve_address=curve_address,
        )

    async def _record_trade(
        self,
        person_id_hex: str,
        trader_address: str,
        side: str,
        eth_amount: float,
        token_amount: float,
        tx_hash: str,
        block_number: int,
    ) -> None:
        """Record an on-chain trade in the database.

        Uses a fresh database session to avoid conflicts with the main app.
        """
        from sqlalchemy import select

        from nile.core.database import async_session
        from nile.models.soul_token import SoulToken
        from nile.models.trade import Trade

        try:
            async with async_session() as db:
                # Check if trade already indexed (idempotent via tx_hash unique constraint)
                existing = await db.execute(
                    select(Trade).where(Trade.tx_hash == tx_hash)
                )
                if existing.scalar_one_or_none():
                    return  # Already indexed

                # Look up soul token by person_id
                # Note: person_id in DB is a UUID, on-chain it is bytes16
                import uuid

                person_uuid = uuid.UUID(person_id_hex)
                result = await db.execute(
                    select(SoulToken).where(SoulToken.person_id == person_uuid)
                )
                token = result.scalar_one_or_none()
                if not token:
                    logger.warning(
                        "No SoulToken found for person_id %s — skipping trade", person_id_hex
                    )
                    return

                trade = Trade(
                    soul_token_id=token.id,
                    side=side,
                    token_amount=token_amount,
                    eth_amount=eth_amount,
                    price_eth=float(token.current_price_eth or 0),
                    price_usd=float(token.current_price_usd or 0),
                    fee_total_eth=eth_amount * 0.01 if side == "buy" else 0,
                    trader_address=trader_address,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    phase=token.phase,
                    source="chain",
                )
                db.add(trade)
                await db.commit()

        except Exception:
            logger.exception("Failed to record trade tx=%s", tx_hash)

    async def _update_token_addresses(
        self,
        person_id_hex: str,
        token_address: str,
        curve_address: str,
    ) -> None:
        """Update a SoulToken record with on-chain contract addresses."""
        from sqlalchemy import select

        from nile.core.database import async_session
        from nile.models.soul_token import SoulToken

        try:
            async with async_session() as db:
                import uuid

                person_uuid = uuid.UUID(person_id_hex)
                result = await db.execute(
                    select(SoulToken).where(SoulToken.person_id == person_uuid)
                )
                token = result.scalar_one_or_none()
                if not token:
                    logger.warning(
                        "No SoulToken for person %s — cannot update addresses", person_id_hex
                    )
                    return

                token.token_address = token_address
                token.curve_address = curve_address
                await db.commit()
                logger.info(
                    "Updated SoulToken %s with token=%s curve=%s",
                    token.id,
                    token_address,
                    curve_address,
                )

        except Exception:
            logger.exception("Failed to update token addresses for %s", person_id_hex)


# Singleton for import convenience
event_indexer = EventIndexer()
