"""Production schema fixes: event global progress and CaseItem weight type."""
from alembic import op

revision = "0003_production_schema_fixes"
down_revision = "0002_full_systems"
branch_labels = None
depends_on = None


def upgrade():
    # IF NOT EXISTS keeps upgrades safe for databases created from the corrected 0001.
    op.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS global_progress INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE events ALTER COLUMN global_progress DROP DEFAULT")
    # Older 0001 revisions declared case_items.weight as TEXT; current metadata uses Float.
    op.execute("ALTER TABLE case_items ALTER COLUMN weight TYPE DOUBLE PRECISION USING weight::double precision")


def downgrade():
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS global_progress")
