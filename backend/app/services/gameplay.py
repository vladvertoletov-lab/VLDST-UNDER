from datetime import datetime, timezone
from sqlalchemy import select
from ..models import User, Quest, QuestProgress, Event, EventProgress, GuildMember, GuildQuest
from .level import level_from_total_xp

async def lock_user(db, uid):
    return (await db.execute(select(User).where(User.id == uid).with_for_update())).scalar_one()

async def award_xp(db, uid, amount):
    if amount <= 0: return
    u = await lock_user(db, uid)
    u.xp += amount
    u.level = level_from_total_xp(u.xp)

async def record_action(db, uid, action: str, amount: int = 1):
    amount = max(1, min(int(amount), 1000))
    quests = (await db.execute(select(Quest).where(Quest.active == True, Quest.quest_type == action))).scalars().all()
    for q in quests:
        p = (await db.execute(select(QuestProgress).where(QuestProgress.user_id == uid, QuestProgress.quest_id == q.id).with_for_update())).scalar_one_or_none()
        if not p:
            p = QuestProgress(user_id=uid, quest_id=q.id, progress=0); db.add(p); await db.flush()
        if not p.claimed:
            if q.parent_id:
                parent = await db.get(Quest, q.parent_id)
                parent_p = await db.scalar(select(QuestProgress).where(QuestProgress.user_id==uid, QuestProgress.quest_id==q.parent_id))
                if not parent_p or not parent_p.claimed: continue
            p.progress = min(q.target, p.progress + amount)
    now = datetime.now(timezone.utc)
    event_ids=(await db.execute(select(Event.id).where(Event.active == True, Event.action_type == action))).scalars().all()
    events=[]
    for eid in event_ids:
        ev=(await db.execute(select(Event).where(Event.id==eid).with_for_update())).scalar_one()
        events.append(ev)
    member = (await db.execute(select(GuildMember).where(GuildMember.user_id == uid))).scalar_one_or_none()
    for e in events:
        if not (e.start_at <= now <= e.end_at): continue
        p = (await db.execute(select(EventProgress).where(EventProgress.user_id == uid, EventProgress.event_id == e.id).with_for_update())).scalar_one_or_none()
        if not p:
            continue
        p.progress = min(e.global_goal or 2_147_483_647, p.progress + amount)
        e.global_progress = min(e.global_goal or 2_147_483_647, e.global_progress + amount)
    if member:
        gqs = (await db.execute(select(GuildQuest).where(GuildQuest.guild_id == member.guild_id, GuildQuest.active == True).with_for_update())).scalars().all()
        for q in gqs: q.progress = min(q.target, q.progress + amount)
