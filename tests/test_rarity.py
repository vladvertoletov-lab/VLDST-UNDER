import sys
sys.path.insert(0, "backend")
from app.services.cases import RANKS

def test_rarity_order():
    assert RANKS == ["COMMON","RARE","EPIC","LEGENDARY","MYTHIC","SECRET"]

def test_default_weights_sum_to_one():
    weights={"COMMON":.55,"RARE":.28,"EPIC":.12,"LEGENDARY":.04,"MYTHIC":.009,"SECRET":.001}
    assert abs(sum(weights.values())-1) < 1e-9
