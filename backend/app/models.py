from datetime import datetime, timezone
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, ForeignKey, Text, Float, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str|None] = mapped_column(String(64))
    nickname: Mapped[str] = mapped_column(String(32), default="VLDST")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    energy: Mapped[int] = mapped_column(Integer, default=10)
    energy_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    referral_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_daily: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    banned: Mapped[bool] = mapped_column(Boolean, default=False)
    session_version: Mapped[int] = mapped_column(Integer, default=1)
    selected_title: Mapped[str] = mapped_column(String(80), default="NEWCOMER")
    selected_frame: Mapped[str|None] = mapped_column(String(80))
    selected_background: Mapped[str|None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Balance(Base):
    __tablename__="user_balances"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    vld: Mapped[int] = mapped_column(BigInteger, default=0)
    scrap: Mapped[int] = mapped_column(BigInteger, default=0)
    core: Mapped[int] = mapped_column(BigInteger, default=0)
    season_xp: Mapped[int] = mapped_column(Integer, default=0)

class Transaction(Base):
    __tablename__="transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    currency: Mapped[str] = mapped_column(String(20), default="VLD")
    amount: Mapped[int] = mapped_column(BigInteger)
    balance_after: Mapped[int] = mapped_column(BigInteger)
    reference: Mapped[str|None] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Operation(Base):
    __tablename__="operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(128))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__=(UniqueConstraint("user_id","key",name="uq_operation_user_key"),)

class Case(Base):
    __tablename__="cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column(BigInteger)
    image: Mapped[str] = mapped_column(String(255))
    weights: Mapped[dict] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CasePity(Base):
    __tablename__="case_pity"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    openings: Mapped[int] = mapped_column(Integer, default=0)
    since_epic: Mapped[int] = mapped_column(Integer, default=0)
    since_legendary: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__=(UniqueConstraint("user_id","case_id",name="uq_case_pity_user_case"),)


class CaseItem(Base):
    __tablename__="case_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    __table_args__=(UniqueConstraint("case_id","item_id",name="uq_case_item"),)

class Item(Base):
    __tablename__="items"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    rarity: Mapped[str] = mapped_column(String(20), index=True)
    collection: Mapped[str] = mapped_column(String(80))
    base_value: Mapped[int] = mapped_column(BigInteger)
    max_level: Mapped[int] = mapped_column(Integer, default=10)
    image: Mapped[str] = mapped_column(String(255))
    animation: Mapped[str] = mapped_column(String(64), default="none")
    effect: Mapped[str] = mapped_column(String(128), default="none")
    craftable: Mapped[bool] = mapped_column(Boolean, default=True)
    upgradeable: Mapped[bool] = mapped_column(Boolean, default=True)
    tradable: Mapped[bool] = mapped_column(Boolean, default=True)
    recycle_value: Mapped[int] = mapped_column(BigInteger)

class Inventory(Base):
    __tablename__="inventory"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    level: Mapped[int] = mapped_column(Integer, default=1)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)

class Collection(Base):
    __tablename__="collections"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(Text)


class CollectionItem(Base):
    __tablename__="collection_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    __table_args__=(UniqueConstraint("collection_id","item_id",name="uq_collection_item"),)

class Achievement(Base):
    __tablename__="achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(40))
    reward_vld: Mapped[int] = mapped_column(BigInteger, default=0)
    reward_xp: Mapped[int] = mapped_column(Integer, default=0)
    requirement: Mapped[dict] = mapped_column(JSON, default=dict)
    title_reward: Mapped[str|None] = mapped_column(String(80))

class UserAchievement(Base):
    __tablename__="user_achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__=(UniqueConstraint("user_id","achievement_id",name="uq_user_achievement"),)

class Quest(Base):
    __tablename__="quests"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    quest_type: Mapped[str] = mapped_column(String(40))
    target: Mapped[int] = mapped_column(Integer, default=1)
    reward_vld: Mapped[int] = mapped_column(BigInteger, default=0)
    reward_xp: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    period: Mapped[str] = mapped_column(String(20), default="daily")
    expires_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[int|None] = mapped_column(ForeignKey("quests.id"))
    sequence: Mapped[int] = mapped_column(Integer, default=0)

class QuestProgress(Base):
    __tablename__="quest_progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    quest_id: Mapped[int] = mapped_column(ForeignKey("quests.id"))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__=(UniqueConstraint("user_id","quest_id",name="uq_quest_progress_user_quest"),)

class Game(Base):
    __tablename__="games"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    energy_cost: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class GameSession(Base):
    __tablename__="game_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    nonce: Mapped[str] = mapped_column(String(64), unique=True)
    server_seed: Mapped[str] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)


class GameResult(Base):
    __tablename__="game_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    score: Mapped[int] = mapped_column(Integer)
    reward_vld: Mapped[int] = mapped_column(BigInteger)
    reward_xp: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class EventProgress(Base):
    __tablename__="event_progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    reward_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__=(UniqueConstraint("user_id","event_id",name="uq_event_progress_user_event"),)

class Event(Base):
    __tablename__="events"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    banner: Mapped[str] = mapped_column(String(255))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    global_goal: Mapped[int|None] = mapped_column(Integer)
    global_progress: Mapped[int] = mapped_column(Integer, default=0)
    action_type: Mapped[str] = mapped_column(String(40), default="game")
    reward_vld: Mapped[int] = mapped_column(BigInteger, default=1000)
    reward_xp: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class SeasonReward(Base):
    __tablename__="season_rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    level: Mapped[int] = mapped_column(Integer)
    free_vld: Mapped[int] = mapped_column(BigInteger, default=0)
    free_xp: Mapped[int] = mapped_column(Integer, default=0)
    free_scrap: Mapped[int] = mapped_column(BigInteger, default=0)
    premium_product_id: Mapped[int|None] = mapped_column(ForeignKey("stars_products.id"))
    __table_args__=(UniqueConstraint("season_id","level",name="uq_season_reward_level"),)

class SeasonProgress(Base):
    __tablename__="season_progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    claimed_levels: Mapped[list] = mapped_column(JSON, default=list)
    premium_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__=(UniqueConstraint("user_id","season_id",name="uq_season_progress_user_season"),)

class Season(Base):
    __tablename__="seasons"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    levels: Mapped[int] = mapped_column(Integer, default=50)


class Vault(Base):
    __tablename__="vaults"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    slots: Mapped[int] = mapped_column(Integer, default=50)

class VaultUpgrade(Base):
    __tablename__="vault_upgrades"
    id: Mapped[int] = mapped_column(primary_key=True)
    vault_id: Mapped[int] = mapped_column(ForeignKey("vaults.id"))
    level: Mapped[int] = mapped_column(Integer)
    cost_vld: Mapped[int] = mapped_column(BigInteger)
    slots: Mapped[int] = mapped_column(Integer)
    __table_args__=(UniqueConstraint("vault_id","level",name="uq_vault_upgrade_level"),)

class Referral(Base):
    __tablename__="referrals"
    id: Mapped[int] = mapped_column(primary_key=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    invitee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class StarsProduct(Base):
    __tablename__="stars_products"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    stars_price: Mapped[int] = mapped_column(Integer)
    image: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    limited: Mapped[bool] = mapped_column(Boolean, default=False)

class UserCosmetic(Base):
    __tablename__="user_cosmetics"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("stars_products.id"))
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__=(UniqueConstraint("user_id","product_id",name="uq_user_cosmetic"),)

class Premium(Base):
    __tablename__="premium"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class StarsPurchase(Base):
    __tablename__="stars_purchases"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("stars_products.id"))
    payload: Mapped[str] = mapped_column(String(255), unique=True)
    telegram_charge_id: Mapped[str|None] = mapped_column(String(255), unique=True)
    invoice_url: Mapped[str|None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Guild(Base):
    __tablename__="guilds"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    tag: Mapped[str] = mapped_column(String(12), unique=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    max_members: Mapped[int] = mapped_column(Integer, default=20)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class GuildMember(Base):
    __tablename__="guild_members"
    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="member")


class GuildEvent(Base):
    __tablename__="guild_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    contribution: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__=(UniqueConstraint("guild_id","event_id",name="uq_guild_event"),)

class MarketListing(Base):
    __tablename__="market_listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"), unique=True)
    price: Mapped[int] = mapped_column(BigInteger)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class MarketTransaction(Base):
    __tablename__="market_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("market_listings.id"), unique=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    price: Mapped[int] = mapped_column(BigInteger)
    seller_amount: Mapped[int] = mapped_column(BigInteger)
    fee: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Trade(Base):
    __tablename__="trades"
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    sender_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    receiver_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Notification(Base):
    __tablename__="notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class EconomyConfig(Base):
    __tablename__="economy_config"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[int] = mapped_column(BigInteger)


class CraftRecipe(Base):
    __tablename__="craft_recipes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    output_item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    vld_cost: Mapped[int] = mapped_column(BigInteger, default=0)
    scrap_cost: Mapped[int] = mapped_column(BigInteger, default=0)
    core_cost: Mapped[int] = mapped_column(BigInteger, default=0)
    min_level: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class CraftHistory(Base):
    __tablename__="craft_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("craft_recipes.id"))
    output_inventory_id: Mapped[int|None] = mapped_column(ForeignKey("inventory.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class FusionHistory(Base):
    __tablename__="fusion_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    input_inventory_ids: Mapped[list] = mapped_column(JSON)
    output_inventory_id: Mapped[int|None] = mapped_column(ForeignKey("inventory.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class GuildQuest(Base):
    __tablename__="guild_quests"
    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    target: Mapped[int] = mapped_column(Integer)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    reward_xp: Mapped[int] = mapped_column(Integer, default=0)
    reward_vld: Mapped[int] = mapped_column(BigInteger, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))

class GuildQuestClaim(Base):
    __tablename__="guild_quest_claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    guild_quest_id: Mapped[int] = mapped_column(ForeignKey("guild_quests.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__=(UniqueConstraint("guild_quest_id","user_id",name="uq_guild_quest_claim"),)

class PromoCode(Base):
    __tablename__="promo_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    reward_vld: Mapped[int] = mapped_column(BigInteger, default=0)
    reward_xp: Mapped[int] = mapped_column(Integer, default=0)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class PromoRedemption(Base):
    __tablename__="promo_redemptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    promo_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__=(UniqueConstraint("promo_id","user_id",name="uq_promo_user"),)



class TradeItem(Base):
    __tablename__="trade_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"))
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"))
    owner_side: Mapped[str] = mapped_column(String(20))
    __table_args__=(UniqueConstraint("trade_id","inventory_id",name="uq_trade_item"),)


class ReferralReward(Base):
    __tablename__="referral_rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    invitee_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    milestone: Mapped[str] = mapped_column(String(40))
    reward_vld: Mapped[int] = mapped_column(BigInteger, default=0)
    reward_xp: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__=(UniqueConstraint("inviter_id","invitee_id","milestone",name="uq_referral_reward_milestone"),)
