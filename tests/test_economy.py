from app.economy import RARITIES,roll
def test_odds(): assert abs(sum(RARITIES.values())-100)<1e-9
def test_roll(): assert roll() in RARITIES
