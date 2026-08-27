def xp_for_level(level: int) -> int:
    return int(500 * (level ** 1.55))

def level_from_total_xp(xp: int) -> int:
    level=1
    while level < 100 and xp_for_level(level+1) <= xp:
        level += 1
    return level
