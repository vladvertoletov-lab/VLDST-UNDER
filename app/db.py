from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column,BigInteger,Integer,String,Boolean,DateTime,JSON,UniqueConstraint,ForeignKey
from datetime import datetime,timezone
from .config import settings
engine=create_async_engine(settings.DATABASE_URL.replace("postgresql://","postgresql+asyncpg://",1).replace("postgres://","postgresql+asyncpg://",1),pool_pre_ping=True)
Session=async_sessionmaker(engine,expire_on_commit=False,class_=AsyncSession)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True)
    telegram_id=Column(BigInteger,unique=True,index=True,nullable=False)
    username=Column(String); first_name=Column(String)
    coins=Column(BigInteger,default=5000,nullable=False)
    stars=Column(Integer,default=0,nullable=False)
    xp=Column(BigInteger,default=0,nullable=False)
    level=Column(Integer,default=1,nullable=False)
    energy=Column(Integer,default=100,nullable=False)
    streak=Column(Integer,default=0,nullable=False)
    referral_code=Column(String,unique=True)
    referred_by=Column(BigInteger)
    premium_until=Column(DateTime(timezone=True))
    banned=Column(Boolean,default=False,nullable=False)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Case(Base):
    __tablename__="cases"
    id=Column(Integer,primary_key=True); name=Column(String,unique=True)
    price=Column(BigInteger); stars_price=Column(Integer,default=0)
    image=Column(String); active=Column(Boolean,default=True)
class Item(Base):
    __tablename__="items"
    id=Column(Integer,primary_key=True); name=Column(String); rarity=Column(String)
    collection=Column(String); value=Column(BigInteger); image=Column(String)
class Inventory(Base):
    __tablename__="inventory"
    id=Column(Integer,primary_key=True); telegram_id=Column(BigInteger,index=True)
    item_id=Column(Integer,ForeignKey("items.id")); level=Column(Integer,default=1)
    locked=Column(Boolean,default=False); sold=Column(Boolean,default=False)
class Transaction(Base):
    __tablename__="transactions"
    id=Column(Integer,primary_key=True); telegram_id=Column(BigInteger,index=True)
    kind=Column(String); amount=Column(BigInteger); balance=Column(BigInteger); meta=Column(JSON)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Quest(Base):
    __tablename__="quests"
    id=Column(Integer,primary_key=True); title=Column(String); description=Column(String)
    kind=Column(String); target=Column(Integer); reward=Column(BigInteger); xp=Column(Integer)
class QuestClaim(Base):
    __tablename__="quest_claims"
    id=Column(Integer,primary_key=True); telegram_id=Column(BigInteger); quest_id=Column(Integer)
    __table_args__=(UniqueConstraint("telegram_id","quest_id"),)
class Referral(Base):
    __tablename__="referrals"
    id=Column(Integer,primary_key=True); inviter=Column(BigInteger); invitee=Column(BigInteger,unique=True)
class Achievement(Base):
    __tablename__="achievements"
    id=Column(Integer,primary_key=True); code=Column(String,unique=True); title=Column(String)
    reward=Column(BigInteger); xp=Column(Integer)
class AchievementUser(Base):
    __tablename__="achievement_users"
    id=Column(Integer,primary_key=True); telegram_id=Column(BigInteger); achievement_id=Column(Integer)
    __table_args__=(UniqueConstraint("telegram_id","achievement_id"),)
class Guild(Base):
    __tablename__="guilds"
    id=Column(Integer,primary_key=True); name=Column(String,unique=True); owner=Column(BigInteger)
    level=Column(Integer,default=1); xp=Column(BigInteger,default=0); vault=Column(BigInteger,default=0)
class GuildMember(Base):
    __tablename__="guild_members"
    id=Column(Integer,primary_key=True); guild_id=Column(Integer); telegram_id=Column(BigInteger); role=Column(String,default="member")
class Gift(Base):
    __tablename__="gifts"
    id=Column(Integer,primary_key=True); sender=Column(BigInteger); receiver=Column(BigInteger)
    inventory_id=Column(Integer); created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
async def init_db():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)

        # Migration for existing Render PostgreSQL database.
        # Old versions of the project may contain columns that
        # are not used by the current SQLAlchemy models.

        await c.exec_driver_sql("""
            ALTER TABLE cases
            ADD COLUMN IF NOT EXISTS stars_price INTEGER DEFAULT 0
        """)

        await c.exec_driver_sql("""
            ALTER TABLE cases
            ADD COLUMN IF NOT EXISTS description TEXT
        """)

        # Existing rows may have NULL description.
        # Give them a safe default before applying NOT NULL.
        await c.exec_driver_sql("""
            UPDATE cases
            SET description = ''
            WHERE description IS NULL
        """)

        await c.exec_driver_sql("""
            ALTER TABLE cases
            ALTER COLUMN description SET DEFAULT ''
        """)

        await c.exec_driver_sql("""
            ALTER TABLE cases
            ALTER COLUMN description SET NOT NULL
        """)

        await c.exec_driver_sql("""
            ALTER TABLE cases
            ALTER COLUMN stars_price SET DEFAULT 0
        """)


async def get_db():
    async with Session() as s:
        yield s



async def get_db():
    async with Session() as s:
        yield s
