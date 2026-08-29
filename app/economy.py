import secrets
RARITIES={"COMMON":55.0,"RARE":28.0,"EPIC":12.0,"LEGENDARY":4.0,"MYTHIC":0.9,"SECRET":0.1}
CASES=[
("VLDST ORIGIN",500),("VLDST NEON",1500),("VLDST PULSE",3000),("VLDST AURA",5000),
("VLDST SHADOW",8000),("VLDST VOID",12000),("VLDST RIFT",18000),("VLDST PHANTOM",25000),
("VLDST QUANTUM",35000),("VLDST OMEGA",50000),("VLDST BLACK",75000),("VLDST GOLD",100000),
("VLDST CYBER",125000),("VLDST INFERNO",175000),("VLDST FROZEN",250000),("VLDST GALAXY",350000),
("VLDST ULTRA",500000),("VLDST RADIANT",750000),("VLDST UNDERGROUND",1000000),("VLDST SINGULARITY",1500000)]
def roll(bonus=False):
    odds=RARITIES.copy()
    if bonus:
        odds["MYTHIC"]*=1.5; odds["SECRET"]*=1.5
        k=100/sum(odds.values()); odds={x:y*k for x,y in odds.items()}
    n=secrets.randbelow(100000)/1000; a=0
    for r,w in odds.items():
        a+=w
        if n<a:return r
    return "COMMON"
