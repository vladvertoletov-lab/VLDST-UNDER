from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Balance, Transaction, Operation

async def get_balance(db, user_id, *, for_update=False):
    if for_update:
        row = (await db.execute(select(Balance).where(Balance.user_id==user_id).with_for_update())).scalar_one_or_none()
    else:
        row = await db.get(Balance, user_id)
    if not row:
        row = Balance(user_id=user_id)
        db.add(row)
        await db.flush()
    return row

async def change_vld(db: AsyncSession, user_id: int, amount: int, kind: str, reference=None):
    balance = await get_balance(db, user_id, for_update=True)
    new_value = balance.vld + amount
    if new_value < 0:
        raise ValueError("Недостаточно VLD")
    balance.vld = new_value
    db.add(Transaction(user_id=user_id, kind=kind, currency="VLD", amount=amount,
                       balance_after=new_value, reference=reference))
    return new_value

async def change_scrap(db, user_id, amount, kind="SCRAP"):
    b = await get_balance(db, user_id, for_update=True)
    b.scrap += amount
    if b.scrap < 0: raise ValueError("Недостаточно SCRAP")
    return b.scrap

async def idempotent(db, user_id, key):
    result = await db.execute(select(Operation).where(Operation.user_id==user_id, Operation.key==key))
    return result.scalar_one_or_none()
