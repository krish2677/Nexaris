"""
Solana client — treasury wallet management, deposit verification, reward payouts.
Uses Solana devnet by default with easy mainnet switch.
"""

from __future__ import annotations

import base58
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.message import Message

from app.core.config import settings

logger = logging.getLogger(__name__)

LAMPORTS_PER_SOL = 1_000_000_000

# Config
SOLANA_RPC_URL = getattr(settings, "SOLANA_RPC_URL", "https://api.devnet.solana.com")
TREASURY_KEYPAIR_PATH = getattr(settings, "TREASURY_KEYPAIR_PATH", "")


class SolanaClient:
    """Solana RPC client for treasury operations."""

    def __init__(self) -> None:
        self._client: Optional[AsyncClient] = None
        self._treasury_keypair: Optional[Keypair] = None

    async def get_client(self) -> AsyncClient:
        if not self._client:
            self._client = AsyncClient(SOLANA_RPC_URL)
        return self._client

    def get_treasury_pubkey(self) -> Optional[str]:
        """Get the treasury wallet public key."""
        kp = self._load_treasury_keypair()
        if kp:
            return str(kp.pubkey())
        # Fallback: use env var
        addr = getattr(settings, "TREASURY_WALLET_ADDRESS", "")
        return addr if addr else None

    def _load_treasury_keypair(self) -> Optional[Keypair]:
        """Load treasury keypair from file or env."""
        if self._treasury_keypair:
            return self._treasury_keypair

        # Try keypair file
        if TREASURY_KEYPAIR_PATH and os.path.exists(TREASURY_KEYPAIR_PATH):
            try:
                with open(TREASURY_KEYPAIR_PATH, "r") as f:
                    secret = json.load(f)
                self._treasury_keypair = Keypair.from_bytes(bytes(secret))
                return self._treasury_keypair
            except Exception as e:
                logger.warning(f"Failed to load treasury keypair from file: {e}")

        # Try env var (JSON array or base58 encoded)
        secret_env = getattr(settings, "TREASURY_PRIVATE_KEY", "")
        if secret_env:
            try:
                # First try JSON array format `[1, 2, 3...]`
                if secret_env.startswith("[") and secret_env.endswith("]"):
                    secret_list = json.loads(secret_env)
                    self._treasury_keypair = Keypair.from_bytes(bytes(secret_list))
                else:
                    # Fallback to base58
                    secret_bytes = base58.b58decode(secret_env)
                    self._treasury_keypair = Keypair.from_bytes(secret_bytes)
                return self._treasury_keypair
            except Exception as e:
                logger.warning(f"Failed to load treasury keypair from env: {e}")

        return None

    async def get_balance(self, pubkey_str: str) -> float:
        """Get SOL balance for a wallet address."""
        try:
            client = await self.get_client()
            pubkey = Pubkey.from_string(pubkey_str)
            resp = await client.get_balance(pubkey, commitment=Confirmed)
            lamports = resp.value
            return lamports / LAMPORTS_PER_SOL
        except Exception as e:
            logger.error(f"Failed to get balance for {pubkey_str}: {e}")
            return 0.0

    async def get_treasury_balance(self) -> float:
        """Get the treasury wallet SOL balance."""
        addr = self.get_treasury_pubkey()
        if not addr:
            return 0.0
        return await self.get_balance(addr)

    async def verify_transaction(
        self, signature: str, expected_recipient: Optional[str] = None, min_amount_sol: float = 0.0
    ) -> Dict[str, Any]:
        """Verify an on-chain transaction."""
        try:
            client = await self.get_client()
            from solders.signature import Signature
            sig = Signature.from_string(signature)
            resp = await client.get_transaction(sig, commitment=Confirmed, max_supported_transaction_version=0)

            if not resp.value:
                return {"verified": False, "error": "Transaction not found"}

            tx = resp.value
            meta = tx.transaction.meta
            if meta and meta.err:
                return {"verified": False, "error": f"Transaction failed: {meta.err}"}

            # Extract transfer amount
            pre_balances = meta.pre_balances if meta else []
            post_balances = meta.post_balances if meta else []

            amount_lamports = 0
            if len(pre_balances) >= 2 and len(post_balances) >= 2:
                # Sender loses funds, recipient gains
                amount_lamports = post_balances[1] - pre_balances[1]

            amount_sol = amount_lamports / LAMPORTS_PER_SOL

            result = {
                "verified": True,
                "signature": signature,
                "amount_sol": amount_sol,
                "amount_lamports": amount_lamports,
                "slot": tx.slot,
                "block_time": tx.block_time,
            }

            if min_amount_sol > 0 and amount_sol < min_amount_sol:
                result["verified"] = False
                result["error"] = f"Amount {amount_sol} SOL below minimum {min_amount_sol}"

            return result

        except Exception as e:
            logger.error(f"Transaction verification failed: {e}")
            return {"verified": False, "error": str(e)}

    async def send_reward(
        self, recipient_pubkey: str, amount_sol: float
    ) -> Dict[str, Any]:
        """Send SOL reward from treasury to a contributor."""
        try:
            kp = self._load_treasury_keypair()
            if not kp:
                return {"success": False, "error": "Treasury keypair not configured"}

            client = await self.get_client()
            recipient = Pubkey.from_string(recipient_pubkey)
            lamports = int(amount_sol * LAMPORTS_PER_SOL)

            # Build transfer instruction
            ix = transfer(TransferParams(
                from_pubkey=kp.pubkey(),
                to_pubkey=recipient,
                lamports=lamports,
            ))

            # Get recent blockhash with Finalized commitment to avoid BlockhashNotFound
            from solana.rpc.commitment import Finalized
            blockhash_resp = await client.get_latest_blockhash(commitment=Finalized)
            blockhash = blockhash_resp.value.blockhash

            # Build and sign transaction
            msg = Message.new_with_blockhash([ix], kp.pubkey(), blockhash)
            tx = Transaction.new_unsigned(msg)
            tx.sign([kp], blockhash)

            # Send
            result = await client.send_transaction(tx)
            sig = str(result.value)

            logger.info(f"Reward sent: {amount_sol} SOL to {recipient_pubkey}, sig={sig}")

            return {
                "success": True,
                "signature": sig,
                "amount_sol": amount_sol,
                "recipient": recipient_pubkey,
            }

        except Exception as e:
            logger.error(f"Reward send failed: {e}")
            return {"success": False, "error": str(e)}

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


# Singleton
solana_client = SolanaClient()
