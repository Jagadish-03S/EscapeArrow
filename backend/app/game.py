"""Pure puzzle rules. Each arrow occupies one cell and exits along its ray."""
import random, math
DIRECTIONS=((1,0),(-1,0),(0,1),(0,-1))
def tier(level): return 'easy' if level<=10 else 'moderate' if level<=30 else 'hard'
def settings(level):
    # Growth is bounded by touch-friendly grid limits; randomized puzzles continue indefinitely.
    size=min(10,5+(level-1)//10)
    count=min(size*size-2,8+level*2)
    return size,count

def blocked(arrow, arrows, size):
    x,y=arrow['x'],arrow['y']; dx,dy=arrow['dx'],arrow['dy']
    cells={(a['x'],a['y']) for a in arrows if a['id']!=arrow['id']}
    x+=dx;y+=dy
    while 0<=x<size and 0<=y<size:
        if (x,y) in cells:return True
        x+=dx;y+=dy
    return False

def generate(level, seed=None):
    rng=random.Random(seed); size,count=settings(level); arrows=[]
    # Reverse construction: each newly added arrow can exit before all older arrows.
    cells=[(x,y) for x in range(size) for y in range(size)]; rng.shuffle(cells)
    while len(arrows)<count:
        candidates=[]
        occupied={(a['x'],a['y']) for a in arrows}
        for x,y in cells:
            if (x,y) in occupied:continue
            for dx,dy in DIRECTIONS:
                a={'id':len(arrows),'x':x,'y':y,'dx':dx,'dy':dy}
                if not blocked(a,arrows,size):candidates.append(a)
        if not candidates:break
        arrows.append(rng.choice(candidates))
    rng.shuffle(arrows)
    return {'size':size,'arrows':arrows}

def rating(seconds, collisions, level):
    par=min(180,45+max(0,level-10)*2)
    return round(max(0.5,min(5,5-collisions*0.65-max(0,seconds-par)/60)),1)
def payout(level, seconds):return {'coins':{'easy':5,'moderate':7,'hard':11}[tier(level)],'diamonds':3 if seconds<=45 else 0}
