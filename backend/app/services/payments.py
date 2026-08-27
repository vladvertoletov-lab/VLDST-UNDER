from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import StarsProduct, StarsPurchase, Premium, UserCosmetic, Season, SeasonProgress

async def grant_stars_entitlement(db: AsyncSession, purchase: StarsPurchase, product: StarsProduct, charge_id: str):
    """Idempotently grant the digital entitlement after Telegram successful_payment."""
    if purchase.status == "paid":
        return False
    if not charge_id:
        raise ValueError("Missing Telegram charge id")
    purchase.status = "paid"
    purchase.telegram_charge_id = charge_id
    if product.category.upper() == "PREMIUM":
        days = 7 if product.code.upper().endswith("_7") else 30
        now = datetime.now(timezone.utc)
        cur = (await db.execute(select(Premium).where(Premium.user_id == purchase.user_id))).scalar_one_or_none()
        if cur:
            cur.expires_at = max(cur.expires_at, now) + timedelta(days=days)
        else:
            db.add(Premium(user_id=purchase.user_id, expires_at=now + timedelta(days=days)))
    elif product.category.upper() == "SEASON_PASS":
        now = datetime.now(timezone.utc)
        season=(await db.execute(select(Season).where(Season.start_at<=now,Season.end_at>=now).order_by(Season.id.desc()))).scalars().first()
        if season:
            progress=(await db.execute(select(SeasonProgress).where(SeasonProgress.user_id==purchase.user_id,SeasonProgress.season_id==season.id).with_for_update())).scalar_one_or_none()
            if not progress:
                progress=SeasonProgress(user_id=purchase.user_id,season_id=season.id,xp=0,level=1,claimed_levels=[],premium_pass=True);db.add(progress)
            else: progress.premium_pass=True
        db.add(UserCosmetic(user_id=purchase.user_id,product_id=product.id))
    else:
        exists = (await db.execute(select(UserCosmetic).where(
            UserCosmetic.user_id == purchase.user_id,
            UserCosmetic.product_id == product.id,
        ))).scalar_one_or_none()
        if not exists:
            db.add(UserCosmetic(user_id=purchase.user_id, product_id=product.id))
    return True
