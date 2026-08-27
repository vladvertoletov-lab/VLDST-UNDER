import sys
sys.path.insert(0, "backend")
from app.services.level import xp_for_level, level_from_total_xp

def test_level_curve():
    assert xp_for_level(2) > xp_for_level(1)
    assert level_from_total_xp(0) == 1
    assert level_from_total_xp(xp_for_level(2)) == 2
