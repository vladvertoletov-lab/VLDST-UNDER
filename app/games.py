import secrets
GAMES={
"REACTION":(5,100,10),"MEMORY":(6,120,9),"DECRYPT":(7,150,8),"SIGNAL":(5,100,10),
"PULSE":(8,180,7),"ORBIT":(6,140,9),"CIPHER":(8,200,7),"MATRIX":(10,250,6),
"VAULT":(12,300,6),"RUSH":(4,80,12)}
def play(name):
    e,m,k=GAMES[name]; score=secrets.randbelow(m+1); return score,score*k,max(1,score//10),e
