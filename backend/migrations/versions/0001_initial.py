from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision="0001_initial"; down_revision=None; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('achievements',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('code', sa.String(80), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(40), nullable=False),
        sa.Column('reward_vld', sa.BigInteger(), nullable=False),
        sa.Column('reward_xp', sa.Integer(), nullable=False),
        sa.Column('requirement', sa.JSON(), nullable=False),
        sa.Column('title_reward', sa.String(80), nullable=True),
    )
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('admin_user_id', sa.BigInteger(), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target', sa.String(100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('cases',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(80), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('price', sa.BigInteger(), nullable=False),
        sa.Column('image', sa.String(255), nullable=False),
        sa.Column('weights', sa.JSON(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
    )
    op.create_table('collections',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(80), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=False),
    )
    op.create_table('economy_config',
        sa.Column('key', sa.String(80), nullable=False, primary_key=True),
        sa.Column('value', sa.BigInteger(), nullable=False),
    )
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('banner', sa.String(255), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('global_goal', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(40), nullable=False),
        sa.Column('reward_vld', sa.BigInteger(), nullable=False),
        sa.Column('reward_xp', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
    )
    op.create_table('games',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('code', sa.String(40), nullable=False, unique=True),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('energy_cost', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
    )
    op.create_table('items',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('rarity', sa.String(20), nullable=False),
        sa.Column('collection', sa.String(80), nullable=False),
        sa.Column('base_value', sa.BigInteger(), nullable=False),
        sa.Column('max_level', sa.Integer(), nullable=False),
        sa.Column('image', sa.String(255), nullable=False),
        sa.Column('animation', sa.String(64), nullable=False),
        sa.Column('effect', sa.String(128), nullable=False),
        sa.Column('craftable', sa.Boolean(), nullable=False),
        sa.Column('upgradeable', sa.Boolean(), nullable=False),
        sa.Column('tradable', sa.Boolean(), nullable=False),
        sa.Column('recycle_value', sa.BigInteger(), nullable=False),
    )
    op.create_table('promo_codes',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('code', sa.String(80), nullable=False, unique=True),
        sa.Column('reward_vld', sa.BigInteger(), nullable=False),
        sa.Column('reward_xp', sa.Integer(), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=False),
        sa.Column('uses', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
    )
    op.create_table('quests',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('title', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(40), nullable=False),
        sa.Column('quest_type', sa.String(40), nullable=False),
        sa.Column('target', sa.Integer(), nullable=False),
        sa.Column('reward_vld', sa.BigInteger(), nullable=False),
        sa.Column('reward_xp', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hidden', sa.Boolean(), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('quests.id'), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False),
    )
    op.create_table('seasons',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('levels', sa.Integer(), nullable=False),
    )
    op.create_table('stars_products',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('code', sa.String(80), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('stars_price', sa.Integer(), nullable=False),
        sa.Column('image', sa.String(255), nullable=False),
        sa.Column('category', sa.String(40), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('limited', sa.Boolean(), nullable=False),
    )
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False, unique=True),
        sa.Column('username', sa.String(64), nullable=True),
        sa.Column('nickname', sa.String(32), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('xp', sa.Integer(), nullable=False),
        sa.Column('energy', sa.Integer(), nullable=False),
        sa.Column('energy_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('referral_code', sa.String(32), nullable=False, unique=True),
        sa.Column('streak', sa.Integer(), nullable=False),
        sa.Column('last_daily', sa.DateTime(timezone=True), nullable=True),
        sa.Column('banned', sa.Boolean(), nullable=False),
        sa.Column('session_version', sa.Integer(), nullable=False),
        sa.Column('selected_title', sa.String(80), nullable=False),
        sa.Column('selected_frame', sa.String(80), nullable=True),
        sa.Column('selected_background', sa.String(80), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('case_items',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('weight', sa.Text(), nullable=False),
        sa.UniqueConstraint('case_id', 'item_id', name='uq_case_item'),
    )
    op.create_table('case_pity',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('openings', sa.Integer(), nullable=False),
        sa.Column('since_epic', sa.Integer(), nullable=False),
        sa.Column('since_legendary', sa.Integer(), nullable=False),
        sa.UniqueConstraint('user_id', 'case_id', name='uq_case_pity_user_case'),
    )
    op.create_table('collection_items',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('collection_id', sa.Integer(), sa.ForeignKey('collections.id'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.UniqueConstraint('collection_id', 'item_id', name='uq_collection_item'),
    )
    op.create_table('craft_recipes',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('output_item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('requirements', sa.JSON(), nullable=False),
        sa.Column('vld_cost', sa.BigInteger(), nullable=False),
        sa.Column('scrap_cost', sa.BigInteger(), nullable=False),
        sa.Column('core_cost', sa.BigInteger(), nullable=False),
        sa.Column('min_level', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
    )
    op.create_table('event_progress',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('reward_claimed', sa.Boolean(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'event_id', name='uq_event_progress_user_event'),
    )
    op.create_table('game_sessions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('game_id', sa.Integer(), sa.ForeignKey('games.id'), nullable=False),
        sa.Column('nonce', sa.String(64), nullable=False, unique=True),
        sa.Column('server_seed', sa.String(128), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claimed', sa.Boolean(), nullable=False),
    )
    op.create_table('guilds',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(80), nullable=False, unique=True),
        sa.Column('tag', sa.String(12), nullable=False, unique=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('xp', sa.Integer(), nullable=False),
        sa.Column('max_members', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('inventory',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('favorite', sa.Boolean(), nullable=False),
        sa.Column('equipped', sa.Boolean(), nullable=False),
    )
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(120), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('operations',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('key', sa.String(128), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'key', name='uq_operation_user_key'),
    )
    op.create_table('premium',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('promo_redemptions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('promo_id', sa.Integer(), sa.ForeignKey('promo_codes.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('promo_id', 'user_id', name='uq_promo_user'),
    )
    op.create_table('quest_progress',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('quest_id', sa.Integer(), sa.ForeignKey('quests.id'), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('claimed', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('user_id', 'quest_id', name='uq_quest_progress_user_quest'),
    )
    op.create_table('referral_rewards',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('inviter_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('invitee_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('milestone', sa.String(40), nullable=False),
        sa.Column('reward_vld', sa.BigInteger(), nullable=False),
        sa.Column('reward_xp', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('inviter_id', 'invitee_id', 'milestone', name='uq_referral_reward_milestone'),
    )
    op.create_table('referrals',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('inviter_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('invitee_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('season_progress',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('season_id', sa.Integer(), sa.ForeignKey('seasons.id'), nullable=False),
        sa.Column('xp', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('claimed_levels', sa.JSON(), nullable=False),
        sa.Column('premium_pass', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('user_id', 'season_id', name='uq_season_progress_user_season'),
    )
    op.create_table('season_rewards',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('season_id', sa.Integer(), sa.ForeignKey('seasons.id'), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('free_vld', sa.BigInteger(), nullable=False),
        sa.Column('free_xp', sa.Integer(), nullable=False),
        sa.Column('free_scrap', sa.BigInteger(), nullable=False),
        sa.Column('premium_product_id', sa.Integer(), sa.ForeignKey('stars_products.id'), nullable=True),
        sa.UniqueConstraint('season_id', 'level', name='uq_season_reward_level'),
    )
    op.create_table('stars_purchases',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('stars_products.id'), nullable=False),
        sa.Column('payload', sa.String(255), nullable=False, unique=True),
        sa.Column('telegram_charge_id', sa.String(255), nullable=True, unique=True),
        sa.Column('invoice_url', sa.String(1024), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('trades',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('sender_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('receiver_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('sender_confirmed', sa.Boolean(), nullable=False),
        sa.Column('receiver_confirmed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(40), nullable=False),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('balance_after', sa.BigInteger(), nullable=False),
        sa.Column('reference', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('user_achievements',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('achievement_id', sa.Integer(), sa.ForeignKey('achievements.id'), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),
    )
    op.create_table('user_balances',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, primary_key=True),
        sa.Column('vld', sa.BigInteger(), nullable=False),
        sa.Column('scrap', sa.BigInteger(), nullable=False),
        sa.Column('core', sa.BigInteger(), nullable=False),
        sa.Column('season_xp', sa.Integer(), nullable=False),
    )
    op.create_table('user_cosmetics',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('stars_products.id'), nullable=False),
        sa.Column('purchased_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('equipped', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_user_cosmetic'),
    )
    op.create_table('vaults',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('slots', sa.Integer(), nullable=False),
    )
    op.create_table('craft_history',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('recipe_id', sa.Integer(), sa.ForeignKey('craft_recipes.id'), nullable=False),
        sa.Column('output_inventory_id', sa.Integer(), sa.ForeignKey('inventory.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('fusion_history',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('input_inventory_ids', sa.JSON(), nullable=False),
        sa.Column('output_inventory_id', sa.Integer(), sa.ForeignKey('inventory.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('game_results',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('game_sessions.id'), nullable=False, unique=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('reward_vld', sa.BigInteger(), nullable=False),
        sa.Column('reward_xp', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('guild_events',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('guild_id', sa.Integer(), sa.ForeignKey('guilds.id'), nullable=False),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=False),
        sa.Column('contribution', sa.Integer(), nullable=False),
        sa.UniqueConstraint('guild_id', 'event_id', name='uq_guild_event'),
    )
    op.create_table('guild_members',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('guild_id', sa.Integer(), sa.ForeignKey('guilds.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('role', sa.String(20), nullable=False),
    )
    op.create_table('guild_quests',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('guild_id', sa.Integer(), sa.ForeignKey('guilds.id'), nullable=False),
        sa.Column('title', sa.String(120), nullable=False),
        sa.Column('target', sa.Integer(), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('reward_xp', sa.Integer(), nullable=False),
        sa.Column('reward_vld', sa.BigInteger(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table('market_listings',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('seller_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('inventory_id', sa.Integer(), sa.ForeignKey('inventory.id'), nullable=False, unique=True),
        sa.Column('price', sa.BigInteger(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
    )
    op.create_table('trade_items',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('trade_id', sa.Integer(), sa.ForeignKey('trades.id'), nullable=False),
        sa.Column('inventory_id', sa.Integer(), sa.ForeignKey('inventory.id'), nullable=False),
        sa.Column('owner_side', sa.String(20), nullable=False),
        sa.UniqueConstraint('trade_id', 'inventory_id', name='uq_trade_item'),
    )
    op.create_table('vault_upgrades',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('vault_id', sa.Integer(), sa.ForeignKey('vaults.id'), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('cost_vld', sa.BigInteger(), nullable=False),
        sa.Column('slots', sa.Integer(), nullable=False),
        sa.UniqueConstraint('vault_id', 'level', name='uq_vault_upgrade_level'),
    )
    op.create_table('guild_quest_claims',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('guild_quest_id', sa.Integer(), sa.ForeignKey('guild_quests.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('guild_quest_id', 'user_id', name='uq_guild_quest_claim'),
    )
    op.create_table('market_transactions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('market_listings.id'), nullable=False, unique=True),
        sa.Column('buyer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('seller_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('price', sa.BigInteger(), nullable=False),
        sa.Column('seller_amount', sa.BigInteger(), nullable=False),
        sa.Column('fee', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

def downgrade():
    op.drop_table('market_transactions')
    op.drop_table('guild_quest_claims')
    op.drop_table('vault_upgrades')
    op.drop_table('trade_items')
    op.drop_table('market_listings')
    op.drop_table('guild_quests')
    op.drop_table('guild_members')
    op.drop_table('guild_events')
    op.drop_table('game_results')
    op.drop_table('fusion_history')
    op.drop_table('craft_history')
    op.drop_table('vaults')
    op.drop_table('user_cosmetics')
    op.drop_table('user_balances')
    op.drop_table('user_achievements')
    op.drop_table('transactions')
    op.drop_table('trades')
    op.drop_table('stars_purchases')
    op.drop_table('season_rewards')
    op.drop_table('season_progress')
    op.drop_table('referrals')
    op.drop_table('referral_rewards')
    op.drop_table('quest_progress')
    op.drop_table('promo_redemptions')
    op.drop_table('premium')
    op.drop_table('operations')
    op.drop_table('notifications')
    op.drop_table('inventory')
    op.drop_table('guilds')
    op.drop_table('game_sessions')
    op.drop_table('event_progress')
    op.drop_table('craft_recipes')
    op.drop_table('collection_items')
    op.drop_table('case_pity')
    op.drop_table('case_items')
    op.drop_table('users')
    op.drop_table('stars_products')
    op.drop_table('seasons')
    op.drop_table('quests')
    op.drop_table('promo_codes')
    op.drop_table('items')
    op.drop_table('games')
    op.drop_table('events')
    op.drop_table('economy_config')
    op.drop_table('collections')
    op.drop_table('cases')
    op.drop_table('audit_logs')
    op.drop_table('achievements')
