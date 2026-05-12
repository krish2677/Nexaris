import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.campaign import IncentiveCampaign
from app.models.competition import CampaignParticipant
from app.services.competition import competition_engine
from app.solana.client import solana_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_e2e():
    logger.info("Starting E2E Campaign & Treasury Test...")
    
    # 1. Generate a new recipient wallet
    recipient_kp = Keypair()
    recipient_pubkey = str(recipient_kp.pubkey())
    logger.info(f"Generated recipient wallet: {recipient_pubkey}")
    
    async with AsyncSessionLocal() as db:
        # 2. Check Treasury Balance
        sol_balance = await solana_client.get_treasury_balance()
        logger.info(f"Treasury Balance: {sol_balance} SOL")
        if sol_balance < 0.005:
            logger.error("Treasury balance too low for testing. Airdrop some SOL to the treasury address.")
            return

        # 3. Create dummy user
        test_email = f"test_{uuid4().hex[:8]}@test.com"
        user = User(
            email=test_email,
            hashed_password="hashed",
            wallet_address=recipient_pubkey
        )
        db.add(user)
        await db.flush()
        logger.info(f"Created test user {user.email}")
        
        # 4. Create an Incentive Campaign that ends immediately
        campaign = IncentiveCampaign(
            name="E2E Test Campaign",
            campaign_type="experimental",
            status="active",
            reward_pool=0.005, # Total reward 0.005 SOL (above rent limit)
            max_per_user=0.005,
            duration_hours=1,
            start_time=datetime.now(timezone.utc) - timedelta(hours=2),
            end_time=datetime.now(timezone.utc) - timedelta(seconds=1), # Expired!
            torque_primitives_json=json.dumps(["leaderboard"])
        )
        db.add(campaign)
        await db.flush()
        logger.info(f"Created test campaign {campaign.id}")
        
        # 5. Make user join and score points
        participant = CampaignParticipant(
            campaign_id=campaign.id,
            user_id=user.id,
            contribution_score=100.0,
            validated_units=5
        )
        db.add(participant)
        await db.commit()
        logger.info(f"User joined campaign with score 100")
        
        # 6. Complete Campaign (Trigger payouts)
        logger.info("Triggering campaign completion...")
        result = await competition_engine.complete_campaign(db, campaign.id)
        
        logger.info(f"Campaign Complete Result: {result}")
        
        # 7. Check recipient balance on-chain
        # Wait a few seconds for transaction to finalize
        logger.info("Waiting 10 seconds for transaction finalization...")
        await asyncio.sleep(10)
        
        async with AsyncClient("https://api.devnet.solana.com") as client:
            resp = await client.get_balance(recipient_kp.pubkey())
            lamports = resp.value
            logger.info(f"Recipient Wallet Balance on Devnet: {lamports / 1e9} SOL")
            
        logger.info("E2E Test Finished!")

if __name__ == "__main__":
    asyncio.run(run_e2e())
