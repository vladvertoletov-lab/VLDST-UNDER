import secrets
from ..models import Case, Item, Inventory, User, CasePity, Vault
from .economy import change_vld, idempotent
from sqlalchemy import select, func

RANKS = ["COMMON","RARE","EPIC","LEGENDARY","MYTHIC","SECRET"]

def choose_rarity(weights):
    n = secrets.randbelow(1_000_000) / 1_000_000
    acc = 0
    for rarity in RANKS:
        acc += float(weights.get(rarity, 0))
        if n <= acc: return rarity
    return "COMMON"

async def open_case(db, user_id, case_id, op_key):
    old = await idempotent(db,user_id,op_key)
    if old: return old.result
    # Global lock order: user -> balance. This prevents races and deadlocks.
    await db.execute(select(User).where(User.id==user_id).with_for_update())
    from ..models import Balance
    await db.execute(select(Balance).where(Balance.user_id==user_id).with_for_update())
    old = await idempotent(db,user_id,op_key)
    if old: return old.result
    case = await db.get(Case, case_id)
    if not case or not case.active: raise ValueError("Кейс больше недоступен")
    vault=(await db.execute(select(Vault).where(Vault.user_id==user_id).with_for_update())).scalar_one_or_none()
    if not vault:
        vault=Vault(user_id=user_id,level=1,slots=50);db.add(vault);await db.flush()
    used=(await db.execute(select(func.count(Inventory.id)).where(Inventory.user_id==user_id))).scalar() or 0
    if used>=vault.slots: raise ValueError("Vault переполнен")
    await change_vld(db,user_id,-case.price,"CASE_PURCHASE",f"case:{case_id}")
    pity=(await db.execute(select(CasePity).where(CasePity.user_id==user_id,CasePity.case_id==case.id).with_for_update())).scalar_one_or_none()
    if not pity:
        pity=CasePity(user_id=user_id,case_id=case.id);db.add(pity);await db.flush()
    pity.openings += 1; pity.since_epic += 1; pity.since_legendary += 1
    rarity = choose_rarity(case.weights)
    if pity.since_legendary >= 20: rarity="LEGENDARY" if rarity in {"COMMON","RARE","EPIC"} else rarity
    if pity.since_epic >= 10 and rarity in {"COMMON","RARE"}: rarity="EPIC"
    if rarity in {"EPIC","LEGENDARY","MYTHIC","SECRET"}: pity.since_epic=0
    if rarity in {"LEGENDARY","MYTHIC","SECRET"}: pity.since_legendary=0
    q = await db.execute(select(Item).where(Item.rarity==rarity))
    items = q.scalars().all()
    if not items: raise ValueError("Для этой редкости нет предметов")
    item = secrets.choice(items)
    inv = Inventory(user_id=user_id,item_id=item.id)
    db.add(inv)
    result={"case_id":case.id,"item_id":item.id,"item_name":item.name,"rarity":item.rarity,"image":item.image,"pity_openings":pity.openings,"pity_since_epic":pity.since_epic,"pity_since_legendary":pity.since_legendary}
    from ..models import Operation
    db.add(Operation(user_id=user_id,key=op_key,result=result))
    return result
