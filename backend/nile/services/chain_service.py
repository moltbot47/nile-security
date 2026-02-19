"""Chain integration service — Web3 interactions for Soul Token ecosystem on Base."""

import json
import logging
from pathlib import Path

from nile.config import settings

logger = logging.getLogger(__name__)

# ABI paths (loaded from Foundry build output)
ABI_DIR = Path(__file__).resolve().parent.parent.parent.parent / "contracts" / "out"


def _load_abi(contract_name: str) -> list[dict]:
    """Load ABI from Foundry build artifacts."""
    abi_path = ABI_DIR / f"{contract_name}.sol" / f"{contract_name}.json"
    if not abi_path.exists():
        logger.warning("ABI not found: %s", abi_path)
        return []
    data = json.loads(abi_path.read_text())
    return data.get("abi", [])


class ChainService:
    """Handles all Web3 interactions with Base L2."""

    def __init__(self) -> None:
        self._w3 = None
        self._factory = None
        self._router = None
        self._treasury = None
        self._oracle = None

    @property
    def w3(self):
        """Lazy Web3 connection."""
        if self._w3 is None:
            try:
                from web3 import Web3

                self._w3 = Web3(Web3.HTTPProvider(settings.chain_rpc_url))
            except ImportError:
                logger.error("web3 not installed — run: pip install web3")
                raise
        return self._w3

    @property
    def factory(self):
        if self._factory is None and settings.factory_address:
            abi = _load_abi("SoulTokenFactory")
            self._factory = self.w3.eth.contract(
                address=self.w3.to_checksum_address(settings.factory_address),
                abi=abi,
            )
        return self._factory

    @property
    def router(self):
        if self._router is None and settings.router_address:
            abi = _load_abi("NileRouter")
            self._router = self.w3.eth.contract(
                address=self.w3.to_checksum_address(settings.router_address),
                abi=abi,
            )
        return self._router

    @property
    def oracle(self):
        if self._oracle is None and settings.oracle_address:
            abi = _load_abi("NileOracle")
            self._oracle = self.w3.eth.contract(
                address=self.w3.to_checksum_address(settings.oracle_address),
                abi=abi,
            )
        return self._oracle

    # --- Read Operations ---

    async def get_token_pair(self, person_id: bytes) -> tuple[str, str] | None:
        """Look up token/curve addresses for a person."""
        if not self.factory:
            return None
        try:
            result = self.factory.functions.getTokenPair(person_id).call()
            return (result[0], result[1])
        except Exception:
            logger.exception("Failed to get token pair for %s", person_id.hex())
            return None

    async def get_quote_buy(
        self, person_id: bytes, eth_amount_wei: int
    ) -> tuple[int, int] | None:
        """Get a buy quote: (tokens_out, fee) in wei."""
        if not self.router:
            return None
        try:
            result = self.router.functions.quoteBuy(
                person_id, eth_amount_wei
            ).call()
            return (result[0], result[1])
        except Exception:
            logger.exception("quoteBuy failed")
            return None

    async def get_quote_sell(
        self, person_id: bytes, token_amount_wei: int
    ) -> tuple[int, int] | None:
        """Get a sell quote: (eth_out, fee) in wei."""
        if not self.router:
            return None
        try:
            result = self.router.functions.quoteSell(
                person_id, token_amount_wei
            ).call()
            return (result[0], result[1])
        except Exception:
            logger.exception("quoteSell failed")
            return None

    async def get_curve_state(self, curve_address: str) -> dict | None:
        """Read bonding curve state."""
        abi = _load_abi("BondingCurve")
        if not abi:
            return None
        try:
            curve = self.w3.eth.contract(
                address=self.w3.to_checksum_address(curve_address),
                abi=abi,
            )
            return {
                "reserve_balance": curve.functions.reserveBalance().call(),
                "graduation_threshold": curve.functions.graduationThreshold().call(),
                "active": curve.functions.active().call(),
                "price": curve.functions.currentPrice().call(),
            }
        except Exception:
            logger.exception("Failed to read curve state: %s", curve_address)
            return None

    async def get_eth_price_usd(self) -> float | None:
        """Get ETH/USD price from Chainlink on Base."""
        chainlink_abi = [
            {
                "inputs": [],
                "name": "latestRoundData",
                "outputs": [
                    {"name": "roundId", "type": "uint80"},
                    {"name": "answer", "type": "int256"},
                    {"name": "startedAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "answeredInRound", "type": "uint80"},
                ],
                "stateMutability": "view",
                "type": "function",
            }
        ]
        try:
            feed = self.w3.eth.contract(
                address=self.w3.to_checksum_address(settings.eth_price_feed),
                abi=chainlink_abi,
            )
            result = feed.functions.latestRoundData().call()
            # Chainlink ETH/USD has 8 decimals
            return result[1] / 1e8
        except Exception:
            logger.exception("Failed to get ETH price")
            return None

    # --- Write Operations (require deployer key) ---

    def _get_account(self):
        """Get deployer account from private key."""
        if not settings.deployer_private_key:
            raise ValueError("NILE_DEPLOYER_PRIVATE_KEY not set")
        return self.w3.eth.account.from_key(settings.deployer_private_key)

    async def deploy_soul_token(
        self, person_id: bytes, name: str, symbol: str
    ) -> tuple[str, str] | None:
        """Deploy a new SoulToken + BondingCurve pair."""
        if not self.factory:
            logger.error("Factory address not configured")
            return None

        account = self._get_account()
        try:
            tx = self.factory.functions.createSoulToken(
                person_id, name, symbol
            ).build_transaction(
                {
                    "from": account.address,
                    "nonce": self.w3.eth.get_transaction_count(account.address),
                    "chainId": settings.chain_id,
                }
            )
            signed = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] == 1:
                # Parse SoulTokenCreated event for addresses
                pair = await self.get_token_pair(person_id)
                logger.info("Deployed soul token for %s: %s", person_id.hex(), pair)
                return pair
            logger.error("Soul token deploy tx reverted: %s", tx_hash.hex())
            return None
        except Exception:
            logger.exception("Failed to deploy soul token")
            return None

    async def authorize_oracle_agent(self, agent_address: str) -> bool:
        """Authorize an oracle agent on-chain."""
        if not self.oracle:
            return False
        account = self._get_account()
        try:
            tx = self.oracle.functions.authorizeAgent(
                self.w3.to_checksum_address(agent_address)
            ).build_transaction(
                {
                    "from": account.address,
                    "nonce": self.w3.eth.get_transaction_count(account.address),
                    "chainId": settings.chain_id,
                }
            )
            signed = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt["status"] == 1
        except Exception:
            logger.exception("Failed to authorize oracle agent")
            return False


# Singleton instance
chain_service = ChainService()
