"""Compatibility revision.

The project baseline was squashed into 0001_initial before first production release.
Deployments that already recorded 0002 are still compatible; fresh installations
receive the complete schema from 0001 and this revision intentionally performs no-op.
"""
revision="0002_full_systems"
down_revision="0001_initial"
branch_labels=None
depends_on=None

def upgrade():
    return None

def downgrade():
    return None
