#!/usr/bin/python3
import math, random, sys
import render
from grid import Grid
import ani, scorecard
import persist

class EndOfGame(Exception): pass

class Cell:
    def __init__(self, power):
        self.power = power

    def render(self, t, coord):
        color = ([t.default, t.white, t.cyan, t.blue, t.magenta, t.red]
            [self.power - 1] if self.power < 7 else t.yellow)
        def c(a): t.write(a, c=color)
        with t.location(y=coord.y, x=coord.x):
            c(" ____ ")
        with t.location(y=coord.y + 1, x=coord.x):
            c("/    \\")
        with t.location(y=coord.y + 2, x=coord.x):
            c("\u258c{0}\u2590".format(center(4, 2 ** self.power)))
        with t.location(y=coord.y + 3, x=coord.x):
            c("\\____/")

    def __repr__(self):
        return "Cell({0})".format(self.power)

    def __eq__(self, other):
        return other and self.power == other.power

def center(n, string):
    s = str(string)
    l = len(s)

    p = max(0, n - l)
    pl = math.floor(p / 2)
    pr = math.ceil(p / 2)
    return "".join((" " * pl, s, " " * pr))

def addrand(grid, anims):
    triples = [triple for triple in grid.triples if not triple.v]
    if len(triples) > 1:
        triples = random.sample(triples, 1)

    for triple in triples:
        c = Cell(random.sample([1, 1, 1, 1, 1, 1, 1, 1, 1, 2], 1)[0])
        anims.insert(0, ani.TileSpawn(c, ani.Coord(2+triple.x*7, 2+triple.y*4)))
        grid[triple[0], triple[1]] = c

class WrapperRev:
    def __init__(self, l):
        self.l = l

    def __getitem__(self, i):
        return self.l[len(self.l) - i - 1]

    def __setitem__(self, i, n):
        self.l[len(self.l) - i - 1] = n

    def __iter__(self):
        i = 0
        while i < len(self):
            yield self[i]
            i += 1

    def __len__(self):
        return len(self.l)

def pushrow(r, cbase, cstep, anims, score):
    new = []
    previously_combined = False
    for i, c in enumerate(r):
        if c is not None:
            if new and (not previously_combined) and c == new[-1]:
                anims.append(ani.TileMove(
                    c, cbase + i * cstep,
                    cbase + (len(new)-1) * cstep))
                new[-1] = Cell(c.power + 1)
                score.diff += 2 ** (c.power + 1)
                previously_combined = True
            else:
                anims.append(ani.TileMove(
                    c, cbase + i * cstep,
                    cbase + len(new) * cstep))
                new.append(c)
                previously_combined = False

    if all(x == z for x, z in zip(r, new)):
        return False
    else:
        for i in range(len(r)):
            r[i] = new[i] if i < len(new) else None
        return True

class Score:
    def __init__(self, score=0, hiscore=0):
        self.score = score
        self.hiscore = hiscore
        self.diff = 0

def get_practical_state(grid):
    for triple in grid.triples:
        if triple.v == Cell(11):
            return 1
    for triple in grid.triples:
        if triple.v == None:
            return 0
    
    for row in grid.rows:
        for i in range(3):
            if row[i] == row[i+1]:
                return 0
    for col in grid.cols:
        for i in range(3):
            if col[i] == col[i+1]:
                return 0
    return -1

def main(t, per):
    animationrate = .009
    for arg in sys.argv:
        if arg in ['-h', '--help']:
            t.done()
            import blessings
            t = blessings.Terminal()
            print("""{b}2048{n}
Implementation in python by Samuel Phillips <samuel.phillips29@gmail.com>
Based on 2048 by Gabriele Cirulli. <gabrielecirulli.com>
To play:
    Use hjkl to push the tiles:
              ^
        < {b}h j k l{n} >
            v

    The objective is to combine tiles to form a 2048 tile.
    Press {b}q{n} to quit.
    {b}!{n} will start a Python debugger.
    Use -A{u}xxx{n} or --animrate{u}xxx{n} to speed up or slow down the
    animations. The default rate is {animrate}.

    The game's high score is soted in ~/.2048tty by default. You can change
    this location be setting the 2048TTY_FILE environment varible.
    """.format(
        b=t.bold, n=t.normal, u=t.underline, animrate=animationrate))
            sys.exit(0)
        elif arg.startswith('-A'):
            animationrate = float(arg[2:])
        elif arg.startswith('--animrate'):
            animationrate = float(arg[len('--animrate'):])


    grid = Grid(x=4, y=4)
    debug = False
    inspect = ani.Coord(0, 0)

    addrand(grid, [])
    addrand(grid, [])
    tx = '_'
    tilesiz = ani.Coord(7, 4)
    stepx = tilesiz * ani.ci
    stepy = tilesiz * ani.cj
    tl = ani.Coord(2, 2)
    anims = None
    score = Score(hiscore=per["hiscore"]) # Class needed because no pointers
    won_already = False
    while not tx.startswith("q"):
        t.clear()
        winlose = get_practical_state(grid)
        t.write(str(winlose), at=ani.Coord(0,0))
        if winlose == 1 and not won_already:
            won_already = True
            for i in range(t.c.LINES//2 -5, t.c.LINES//2 + 5):
                t.write("#" * t.c.COLS, at=ani.cj * i, c=t.yellow)
            msg = "...YOU WON!..."
            t.write(msg, at=ani.Coord((t.c.COLS - len(msg))//2, t.c.LINES//2-1))
            t.write("press c to continue", at=ani.cj * (t.c.LINES//2 + 3))
            msg = "press q to quit"
            t.write(msg, at=ani.Coord(t.c.COLS - len(msg), t.c.LINES//2 + 3))
            while True:
                k = t.getch()
                if k.startswith('c'):
                    tx == '_'
                    break
                elif k.startswith('q'):
                    per["hiscore"] = max(per["hiscore"], score.hiscore)
                    raise EndOfGame()
            continue

        elif winlose == -1:
            for i in range(t.c.LINES//2 -5, t.c.LINES//2 + 5):
                t.write("#" * t.c.COLS, at=ani.cj * i, c=t.red)
            msg = "...YOU LOST..."
            t.write(msg, at=ani.Coord((t.c.COLS - len(msg))//2, t.c.LINES//2-1))
            msg = "press any key to quit"
            t.write(msg, at=ani.Coord(t.c.COLS - len(msg), t.c.LINES//2 + 3))
            t.getch()
            break

# main grid
        for trip in grid.triples:
            if trip.v:
                trip.v.render(t, tl + tilesiz * ani.Coord(trip.x, trip.y))
# score card
        score.diff = 0
        scorecard.draw(t, tl + tilesiz * ani.ci * 4 + ani.Coord(10, 5),
                score.score, score.hiscore)
# debug
        if debug:
            for i, row in enumerate(grid.rows):
                t.write(repr(row), at=ani.Coord(30, 2+i))
            for i, anim in enumerate(anims):
                t.write(repr(anim), at=ani.Coord(30, 3+len(grid.rows)+i))
            ic = tl + tilesiz * inspect
            t.write('#', at=ic, c=t.red)
            t.write(repr(ic), at=ani.Coord(30, 3+len(grid.rows)+len(anims)))

# refresh screen
        t.go()
# clear anims
        anims = []
# get & process input
        tx = t.getch()
    # movement
        if tx.startswith('h'):
            ok = []
            for i, row in enumerate(grid.rows):
                ok.append(pushrow(row, tl + stepy * i, stepx, anims, score))
            if any(ok): addrand(grid, anims)
        elif tx.startswith('l'):
            ok = []
            for i, row in enumerate(grid.rows):
                ok.append(pushrow(
                            WrapperRev(row),
                            tl + stepy*i + stepx*len(grid.rows) - stepx,
                            -stepx, anims, score))
            if any(ok): addrand(grid, anims)
        elif tx.startswith('k'):
            ok = []
            for i, col in enumerate(grid.cols):
                ok.append(pushrow(col, tl + stepx * i, stepy, anims, score))
            if any(ok): addrand(grid, anims)
        elif tx.startswith('j'):
            ok = []
            for i, col in enumerate(grid.cols):
                ok.append(pushrow(
                            WrapperRev(col),
                            tl + stepx*i + stepy*len(grid.cols) - stepy,
                            -stepy, anims, score))
            if any(ok): addrand(grid, anims)
    # debug mode
        elif tx.startswith('d'):
            debug = not debug
    # start pdb if things are really bad
        elif tx.startswith('!'):
            import pdb
            with t.location():
                t.c.curs_set(1)
                t.c.nocbreak()
                t.s.keypad(False)
                pdb.set_trace()
                t.s.keypad(True)
                t.c.cbreak()
                t.c.curs_set(0)
        elif debug:
    # move location indicator
            if tx.startswith('H'):
                inspect -= ani.ci
            elif tx.startswith('L'):
                inspect += ani.ci
            elif tx.startswith('K'):
                inspect -= ani.cj
            elif tx.startswith('J'):
                inspect += ani.cj
            elif tx.isdigit():
                grid[inspect.x, inspect.y] = Cell(int(tx))
        score.score += score.diff
        score.hiscore = max(score.score, score.hiscore)
        anims.append(scorecard.ScoreCardAnim(
                score.diff,
                tl + tilesiz * ani.ci * 4 + ani.Coord(10, 5),
                score.score, score.hiscore))
# don't want any suprise motions
        t.input_flush()

        ani.play(t, animationrate, anims)
    per["hiscore"] = max(per["hiscore"], score.hiscore)

if __name__ == '__main__':
    per = persist.Persister()
    t = render.Terminal()
    try:
        main(t, per)
    except EndOfGame:
        pass
    finally:
        t.done()
        per.finish()
