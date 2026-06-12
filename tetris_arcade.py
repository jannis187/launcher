"""
╔═══════════════════════════════════════════════════╗
║        TETRIS  ARCADE  •  2  PLAYERS              ║
║  P1: WASD  (A/D=move, W=rotate, S=soft, SS=hard)  ║
║  P2: ARROWS (←/→=move, ↑=rotate, ↓=soft, ↓↓=hard)║
╚═══════════════════════════════════════════════════╝
"""

import pygame
import random
import math
import sys
import json
import os

# ─── Layout ───────────────────────────────────────────────────────────────────
CELL        = 28
COLS        = 10
ROWS        = 20
BOARD_W     = COLS * CELL         # 280
BOARD_H     = ROWS * CELL         # 560

SCREEN_W    = 1280
SCREEN_H    = 900

# Board positions
P1_BX = 60
P2_BX = SCREEN_W - 60 - BOARD_W   # 620
BOARD_Y = (SCREEN_H - BOARD_H) // 2  # 100

# Side panel width
PANEL_W = 120

FPS = 60
SCORE_FILE = os.path.join(os.path.dirname(__file__), "tetris_hiscore.json")

# ─── Palette ──────────────────────────────────────────────────────────────────
DARK_BG     = (6,   6,  16)
PANEL_BG    = (10,  10, 24)
GRID_LINE   = (20,  20, 42)
BLACK       = (0,   0,  0)
WHITE       = (255,255,255)
GREY        = (110,110,130)
DARK_GREY   = (35,  35, 52)

NEON_CYAN   = (0,  230,255)
NEON_GREEN  = (0,  255, 80)
NEON_PINK   = (255, 40,160)
NEON_YELLOW = (255,220,  0)
NEON_ORANGE = (255,120,  0)
NEON_RED    = (255, 40, 40)
NEON_BLUE   = (40, 100,255)
NEON_PURPLE = (180, 40,255)

# ─── Tetromino definitions ─────────────────────────────────────────────────────
# Each piece: list of 4 rotations, each rotation: list of (row,col) offsets from pivot
TETROMINOES = {
    'I': {
        'color': NEON_CYAN,
        'rotations': [
            [(0,0),(0,1),(0,2),(0,3)],
            [(0,0),(1,0),(2,0),(3,0)],
            [(0,0),(0,1),(0,2),(0,3)],
            [(0,0),(1,0),(2,0),(3,0)],
        ],
        'spawn': (0, 3),
    },
    'O': {
        'color': NEON_YELLOW,
        'rotations': [
            [(0,0),(0,1),(1,0),(1,1)],
            [(0,0),(0,1),(1,0),(1,1)],
            [(0,0),(0,1),(1,0),(1,1)],
            [(0,0),(0,1),(1,0),(1,1)],
        ],
        'spawn': (0, 4),
    },
    'T': {
        'color': NEON_PURPLE,
        'rotations': [
            [(0,1),(1,0),(1,1),(1,2)],
            [(0,0),(1,0),(1,1),(2,0)],
            [(0,0),(0,1),(0,2),(1,1)],
            [(0,1),(1,0),(1,1),(2,1)],
        ],
        'spawn': (0, 3),
    },
    'S': {
        'color': NEON_GREEN,
        'rotations': [
            [(0,1),(0,2),(1,0),(1,1)],
            [(0,0),(1,0),(1,1),(2,1)],
            [(0,1),(0,2),(1,0),(1,1)],
            [(0,0),(1,0),(1,1),(2,1)],
        ],
        'spawn': (0, 3),
    },
    'Z': {
        'color': NEON_RED,
        'rotations': [
            [(0,0),(0,1),(1,1),(1,2)],
            [(0,1),(1,0),(1,1),(2,0)],
            [(0,0),(0,1),(1,1),(1,2)],
            [(0,1),(1,0),(1,1),(2,0)],
        ],
        'spawn': (0, 3),
    },
    'J': {
        'color': NEON_BLUE,
        'rotations': [
            [(0,0),(1,0),(1,1),(1,2)],
            [(0,0),(0,1),(1,0),(2,0)],
            [(0,0),(0,1),(0,2),(1,2)],
            [(0,1),(1,1),(2,0),(2,1)],
        ],
        'spawn': (0, 3),
    },
    'L': {
        'color': NEON_ORANGE,
        'rotations': [
            [(0,2),(1,0),(1,1),(1,2)],
            [(0,0),(1,0),(2,0),(2,1)],
            [(0,0),(0,1),(0,2),(1,0)],
            [(0,0),(0,1),(1,1),(2,1)],
        ],
        'spawn': (0, 3),
    },
}
PIECE_NAMES = list(TETROMINOES.keys())

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_hiscore():
    try:
        with open(SCORE_FILE) as f:
            return json.load(f).get("hiscore", 0)
    except Exception:
        return 0

def save_hiscore(score):
    try:
        with open(SCORE_FILE, "w") as f:
            json.dump({"hiscore": score}, f)
    except Exception:
        pass

def scanline_surface(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 2):
        pygame.draw.line(s, (0, 0, 0, 35), (0, y), (w, y))
    return s

def draw_neon_text(surf, text, font, color, cx, cy, glow=True, alpha=255):
    if alpha < 255:
        tmp = pygame.Surface(font.size(text), pygame.SRCALPHA)
        if glow:
            gc = tuple(min(255, c//2) for c in color)
            for dx,dy in [(-2,0),(2,0),(0,-2),(0,2)]:
                gs = font.render(text, True, gc)
                tmp.blit(gs, gs.get_rect(center=(tmp.get_width()//2+dx, tmp.get_height()//2+dy)))
        ts = font.render(text, True, color)
        tmp.blit(ts, ts.get_rect(center=(tmp.get_width()//2, tmp.get_height()//2)))
        tmp.set_alpha(alpha)
        surf.blit(tmp, tmp.get_rect(center=(cx,cy)))
        return
    if glow:
        gc = tuple(min(255,c//2) for c in color)
        for dx,dy in [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,1),(-1,1),(1,-1)]:
            gs = font.render(text, True, gc)
            surf.blit(gs, gs.get_rect(center=(cx+dx, cy+dy)))
    ts = font.render(text, True, color)
    surf.blit(ts, ts.get_rect(center=(cx,cy)))

def draw_neon_rect(surf, color, rect, width=2, glow=True, radius=4):
    if glow:
        gs = pygame.Surface((rect[2]+16, rect[3]+16), pygame.SRCALPHA)
        gc = (*tuple(c//4 for c in color), 55)
        pygame.draw.rect(gs, gc, (0,0,rect[2]+16,rect[3]+16), border_radius=radius+4)
        surf.blit(gs, (rect[0]-8, rect[1]-8))
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)

def draw_cell(surf, color, bx, by, row, col, alpha=255, ghost=False):
    x = bx + col * CELL
    y = by + row * CELL
    if ghost:
        s = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, 45), (1,1,CELL-2,CELL-2), border_radius=3)
        pygame.draw.rect(s, (*color, 90), (1,1,CELL-2,CELL-2), 1, border_radius=3)
        surf.blit(s, (x, y))
        return
    inner = pygame.Rect(x+1, y+1, CELL-2, CELL-2)
    if alpha < 255:
        s = pygame.Surface((CELL,CELL), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (1,1,CELL-2,CELL-2), border_radius=3)
        # highlight
        hc = tuple(min(255,c+80) for c in color)
        pygame.draw.rect(s, (*hc, alpha//2), (2,2,CELL-4,4), border_radius=2)
        surf.blit(s, (x,y))
        return
    pygame.draw.rect(surf, color, inner, border_radius=3)
    # Top-left highlight
    hc = tuple(min(255,c+90) for c in color)
    pygame.draw.rect(surf, hc, (x+2, y+2, CELL-4, 4), border_radius=2)
    # Dark shadow bottom-right
    sc = tuple(max(0,c-70) for c in color)
    pygame.draw.rect(surf, sc, (x+2, y+CELL-5, CELL-4, 3), border_radius=2)

# ─── Particle System ──────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.0, 5.0)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle)*speed
        self.vy = math.sin(angle)*speed - 1.5
        self.life = random.randint(20,45)
        self.max_life = self.life
        self.color = color
        self.size = random.uniform(2,5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.18
        self.vx *= 0.97
        self.life -= 1

    def draw(self, surf):
        a = int(255*self.life/self.max_life)
        r = max(1, int(self.size*self.life/self.max_life))
        s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a), (r,r), r)
        surf.blit(s, (int(self.x)-r, int(self.y)-r))

class ParticleSystem:
    def __init__(self):
        self.ps = []
    def emit(self, x, y, color, count=12):
        for _ in range(count):
            self.ps.append(Particle(x,y,color))
    def update(self):
        self.ps = [p for p in self.ps if p.life>0]
        for p in self.ps: p.update()
    def draw(self, surf):
        for p in self.ps: p.draw(surf)

# ─── Piece ────────────────────────────────────────────────────────────────────

class Piece:
    def __init__(self, name=None):
        self.name = name or random.choice(PIECE_NAMES)
        self.data = TETROMINOES[self.name]
        self.color = self.data['color']
        self.rot = 0
        r, c = self.data['spawn']
        self.row = r
        self.col = c

    def cells(self, row=None, col=None, rot=None):
        r = self.row if row is None else row
        c = self.col if col is None else col
        rt = self.rot if rot is None else rot
        return [(r+dr, c+dc) for dr,dc in self.data['rotations'][rt]]

# ─── Board Logic ──────────────────────────────────────────────────────────────

class Board:
    def __init__(self, bx, by, player_id, fonts):
        self.bx = bx
        self.by = by
        self.pid = player_id   # 1 or 2
        self.fonts = fonts
        self.grid = [[None]*COLS for _ in range(ROWS)]  # None or color tuple
        self.particles = ParticleSystem()

        self.bag = []
        self.current = self._next_piece()
        self.next_piece = self._next_piece()
        self.hold_piece = None
        self.hold_used = False

        self.score = 0
        self.lines = 0
        self.level = 1
        self.combo = -1
        self.alive = True
        self.game_over = False

        self.fall_timer = 0
        self.fall_interval = self._fall_interval()

        # DAS (Delayed Auto Shift)
        self.das_dir = 0
        self.das_timer = 0
        self.das_delay = 10
        self.das_repeat = 3

        # Lock delay
        self.lock_timer = 0
        self.lock_delay = 6
        self.lock_reset_count = 0

        # Animation
        self.clear_flash = []   # rows being cleared
        self.clear_timer = 0
        self.shake_x = self.shake_y = 0
        self.shake_timer = 0

        # Lines to send (attack)
        self.garbage_queue = []
        self.pending_garbage = 0

    def _refill_bag(self):
        bag = PIECE_NAMES[:]
        random.shuffle(bag)
        self.bag.extend(bag)

    def _next_piece(self):
        if len(self.bag) < 4:
            self._refill_bag()
        return Piece(self.bag.pop(0))

    def _fall_interval(self):
        # frames per cell drop — decreases with level
        return max(2, 50 - (self.level - 1) * 4)

    def _valid(self, piece, row=None, col=None, rot=None):
        for r,c in piece.cells(row,col,rot):
            if r < 0: return False
            if r >= ROWS or c < 0 or c >= COLS: return False
            if self.grid[r][c] is not None: return False
        return True

    def _ghost_row(self):
        r = self.current.row
        while self._valid(self.current, row=r+1):
            r += 1
        return r

    def _lock(self):
        for r,c in self.current.cells():
            if 0 <= r < ROWS and 0 <= c < COLS:
                self.grid[r][c] = self.current.color

        # Check line clears
        full = [r for r in range(ROWS) if all(self.grid[r][c] is not None for c in range(COLS))]
        if full:
            self.clear_flash = full
            self.clear_timer = 18
        else:
            self._settle_and_spawn()

    def _settle_and_spawn(self):
        full = [r for r in range(ROWS) if all(self.grid[r][c] is not None for c in range(COLS))]
        cleared = len(full)

        if cleared > 0:
            self.combo += 1
            pts = [0,100,300,500,800][cleared] * self.level
            combo_bonus = 50 * self.combo * self.level if self.combo > 0 else 0
            self.score += pts + combo_bonus
            self.lines += cleared

            # Particle explosion per cleared row
            for row in full:
                for col in range(COLS):
                    color = self.grid[row][col] or NEON_WHITE
                    px = self.bx + col*CELL + CELL//2
                    py = self.by + row*CELL + CELL//2
                    self.particles.emit(px, py, color, count=4)

            # Remove full rows
            for row in full:
                del self.grid[row]
                self.grid.insert(0, [None]*COLS)

            # Level up every 10 lines
            new_level = self.lines // 10 + 1
            if new_level > self.level:
                self.level = new_level
                self.fall_interval = self._fall_interval()

            # Shake
            self._shake(5 if cleared >= 4 else 3, 10)

            # Attack lines
            attack = [0,0,1,2,4][cleared]
            if self.combo > 1:
                attack += 1
            self.pending_garbage = attack

        else:
            self.combo = -1

        # Add incoming garbage
        if self.garbage_queue:
            g = self.garbage_queue.pop(0)
            self._add_garbage(g)

        # Spawn next
        self.current = self.next_piece
        self.next_piece = self._next_piece()
        self.hold_used = False
        self.lock_timer = 0
        self.lock_reset_count = 0

        if not self._valid(self.current):
            self.alive = False
            self.game_over = True

    def _add_garbage(self, lines):
        hole = random.randint(0, COLS-1)
        for _ in range(lines):
            self.grid.pop(0)
            row = [DARK_GREY]*COLS
            row[hole] = None
            self.grid.append(row)

    def _shake(self, intensity=4, duration=8):
        self.shake_timer = duration
        self.shake_intensity = intensity

    def move(self, dc):
        # Don't allow movement if piece is on the ground
        if not self._valid(self.current, row=self.current.row+1):
            return
        if self._valid(self.current, col=self.current.col+dc):
            self.current.col += dc
            self.lock_timer = 0
            if self.lock_reset_count < 15:
                self.lock_reset_count += 1

    def rotate(self, direction=1):
        new_rot = (self.current.rot + direction) % 4
        # Wall kick attempts
        kicks = [0,-1,1,-2,2]
        for kick in kicks:
            if self._valid(self.current, col=self.current.col+kick, rot=new_rot):
                self.current.col += kick
                self.current.rot = new_rot
                self.lock_timer = 0
                if self.lock_reset_count < 15:
                    self.lock_reset_count += 1
                return

    def soft_drop(self):
        if self._valid(self.current, row=self.current.row+1):
            self.current.row += 1
            self.score += 1
            self.lock_timer = 0
        else:
            self.lock_timer = self.lock_delay  # instant lock on soft drop block

    def hard_drop(self):
        ghost = self._ghost_row()
        dropped = ghost - self.current.row
        self.current.row = ghost
        self.score += dropped * 2
        # Particles at landing spot
        for dc in range(4):
            cells = self.current.cells()
            if cells:
                # bottom-most cell
                pass
        self._lock()

    def hold(self):
        if self.hold_used:
            return
        self.hold_used = True
        if self.hold_piece is None:
            self.hold_piece = Piece(self.current.name)
            self.current = self.next_piece
            self.next_piece = self._next_piece()
        else:
            held_name = self.hold_piece.name
            self.hold_piece = Piece(self.current.name)
            self.current = Piece(held_name)

    def update(self, keys_held, key_events):
        if not self.alive:
            return

        # Clear animation
        if self.clear_timer > 0:
            self.clear_timer -= 1
            if self.clear_timer == 0:
                self._settle_and_spawn()
            return

        self.particles.update()

        # Screen shake
        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_x = random.randint(-self.shake_intensity, self.shake_intensity)
            self.shake_y = random.randint(-self.shake_intensity, self.shake_intensity)
        else:
            self.shake_x = self.shake_y = 0

        # Key events (single press)
        for k, action in key_events:
            if action == 'rotate':
                self.rotate(1)
            elif action == 'rotate_ccw':
                self.rotate(-1)
            elif action == 'hard_drop':
                self.hard_drop()
                return
            elif action == 'hold':
                self.hold()
            elif action == 'left':
                self.das_dir = -1
                self.das_timer = self.das_delay
                self.move(-1)
            elif action == 'right':
                self.das_dir = 1
                self.das_timer = self.das_delay
                self.move(1)

        # DAS (held movement)
        left_held  = keys_held.get('left', False)
        right_held = keys_held.get('right', False)
        if left_held and not right_held:
            if self.das_dir != -1:
                self.das_dir = -1
                self.das_timer = self.das_delay
            self.das_timer -= 1
            if self.das_timer <= 0:
                self.move(-1)
                self.das_timer = self.das_repeat
        elif right_held and not left_held:
            if self.das_dir != 1:
                self.das_dir = 1
                self.das_timer = self.das_delay
            self.das_timer -= 1
            if self.das_timer <= 0:
                self.move(1)
                self.das_timer = self.das_repeat
        else:
            self.das_dir = 0

        soft = keys_held.get('soft', False)

        # Gravity
        if soft:
            self.fall_timer += 4
        else:
            self.fall_timer += 1

        if self.fall_timer >= self.fall_interval:
            self.fall_timer = 0
            if self._valid(self.current, row=self.current.row+1):
                self.current.row += 1
                self.lock_timer = 0
            else:
                # Piece touching ground - lock immediately
                self._lock()

    def draw(self, surf):
        ox = self.bx + self.shake_x
        oy = self.by + self.shake_y

        # Board bg
        pygame.draw.rect(surf, PANEL_BG, (ox, oy, BOARD_W, BOARD_H))

        # Grid lines
        for c in range(COLS+1):
            x = ox + c*CELL
            pygame.draw.line(surf, GRID_LINE, (x,oy), (x,oy+BOARD_H))
        for r in range(ROWS+1):
            y = oy + r*CELL
            pygame.draw.line(surf, GRID_LINE, (ox,y), (ox+BOARD_W,y))

        # Placed cells
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] is not None:
                    color = self.grid[r][c]
                    # Flash clear rows
                    if r in self.clear_flash and self.clear_timer > 0:
                        t = self.clear_timer / 18
                        flash_col = tuple(min(255,int(color[i]*(1-t)+255*t)) for i in range(3))
                        draw_cell(surf, flash_col, ox, oy, r, c)
                    else:
                        draw_cell(surf, color, ox, oy, r, c)

        if self.alive and self.clear_timer == 0:
            # Ghost piece
            ghost_row = self._ghost_row()
            if ghost_row != self.current.row:
                for r,c in self.current.cells(row=ghost_row):
                    if 0 <= r < ROWS and 0 <= c < COLS:
                        draw_cell(surf, self.current.color, ox, oy, r, c, ghost=True)

            # Active piece
            for r,c in self.current.cells():
                if 0 <= r < ROWS and 0 <= c < COLS:
                    draw_cell(surf, self.current.color, ox, oy, r, c)

        # Particles
        self.particles.draw(surf)

        # Board border
        border_col = (NEON_CYAN if self.pid==1 else NEON_PINK) if self.alive else NEON_RED
        t = (math.sin(pygame.time.get_ticks()*0.002)+1)/2
        bc = tuple(int(border_col[i]*0.6 + border_col[i]*0.4*t) for i in range(3))
        draw_neon_rect(surf, bc, (ox-2, oy-2, BOARD_W+4, BOARD_H+4), width=2, radius=2)

        # Game over overlay
        if self.game_over:
            ov = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
            ov.fill((0,0,0,160))
            surf.blit(ov, (ox, oy))
            draw_neon_text(surf, "K.O.", self.fonts['title'], NEON_RED, ox+BOARD_W//2, oy+BOARD_H//2-20)

    def draw_side_panel(self, surf, side='right'):
        """Draw next/hold/score panel beside the board."""
        if side == 'right':
            px = self.bx + BOARD_W + 10
        else:
            px = self.bx - PANEL_W - 10
        py = self.by

        label_col = NEON_CYAN if self.pid==1 else NEON_PINK
        p_label = "P1" if self.pid==1 else "P2"

        # Player label
        draw_neon_text(surf, p_label, self.fonts['medium'], label_col, px+PANEL_W//2, py-30)

        # Score
        draw_neon_text(surf, "SCORE", self.fonts['tiny'], GREY, px+PANEL_W//2, py+16, glow=False)
        draw_neon_text(surf, str(self.score), self.fonts['small'], WHITE, px+PANEL_W//2, py+36)

        # Lines
        draw_neon_text(surf, f"LV {self.level}", self.fonts['small'], label_col, px+PANEL_W//2, py+62)
        draw_neon_text(surf, f"LN {self.lines}", self.fonts['tiny'], GREY, px+PANEL_W//2, py+82, glow=False)

        # Combo
        if self.combo > 0:
            t = (math.sin(pygame.time.get_ticks()*0.006)+1)/2
            cc = (255, int(180+75*t), 0)
            draw_neon_text(surf, f"x{self.combo+1}", self.fonts['medium'], cc, px+PANEL_W//2, py+108)

        # Next piece box
        draw_neon_text(surf, "NEXT", self.fonts['tiny'], GREY, px+PANEL_W//2, py+140, glow=False)
        nb = pygame.Rect(px+8, py+152, PANEL_W-16, 80)
        pygame.draw.rect(surf, PANEL_BG, nb)
        draw_neon_rect(surf, label_col, nb, width=1, glow=False, radius=3)
        self._draw_mini_piece(surf, self.next_piece, px+PANEL_W//2, py+192)

        # Hold piece box
        draw_neon_text(surf, "HOLD", self.fonts['tiny'], GREY, px+PANEL_W//2, py+252, glow=False)
        hb = pygame.Rect(px+8, py+264, PANEL_W-16, 80)
        pygame.draw.rect(surf, PANEL_BG, hb)
        hcol = DARK_GREY if self.hold_used else label_col
        draw_neon_rect(surf, hcol, hb, width=1, glow=False, radius=3)
        if self.hold_piece:
            self._draw_mini_piece(surf, self.hold_piece, px+PANEL_W//2, py+304,
                                  dim=self.hold_used)

        # Garbage indicator
        if self.pending_garbage > 0:
            draw_neon_text(surf, f"▲{self.pending_garbage}", self.fonts['small'], NEON_RED,
                           px+PANEL_W//2, py+370)

    def _draw_mini_piece(self, surf, piece, cx, cy, dim=False):
        cells = piece.data['rotations'][0]
        rows = [r for r,c in cells]
        cols_ = [c for r,c in cells]
        min_r, max_r = min(rows), max(rows)
        min_c, max_c = min(cols_), max(cols_)
        w = (max_c - min_c + 1)
        h = (max_r - min_r + 1)
        mc = 10   # mini cell size
        ox = cx - (w*mc)//2
        oy = cy - (h*mc)//2
        color = tuple(c//2 for c in piece.color) if dim else piece.color
        for r,c in cells:
            x = ox + (c - min_c)*mc
            y = oy + (r - min_r)*mc
            pygame.draw.rect(surf, color, (x+1,y+1,mc-2,mc-2), border_radius=2)
            hc = tuple(min(255,v+60) for v in color)
            pygame.draw.rect(surf, hc, (x+2,y+2,mc-4,3), border_radius=1)


# ─── Input Handler ────────────────────────────────────────────────────────────

class InputHandler:
    """Translates raw pygame events into game actions for each player."""
    def __init__(self):
        # P1: WASD  — A/D move, W rotate, S soft drop, Q hold, double-tap S = hard drop handled via timer
        # P2: Arrows — left/right move, up rotate, down soft, shift hold
        self.p1_keys_held = {k: False for k in ['left','right','soft']}
        self.p2_keys_held = {k: False for k in ['left','right','soft']}
        self.p1_events = []
        self.p2_events = []

        # Hard drop tracking: double-tap S/down within 200ms
        self.p1_s_last = 0
        self.p2_down_last = 0
        self.double_tap_ms = 220

    def process_event(self, event):
        now = pygame.time.get_ticks()
        if event.type == pygame.KEYDOWN:
            k = event.key
            # P1
            if k == pygame.K_a:
                self.p1_events.append((k,'left'))
                self.p1_keys_held['left'] = True
            elif k == pygame.K_d:
                self.p1_events.append((k,'right'))
                self.p1_keys_held['right'] = True
            elif k == pygame.K_w:
                self.p1_events.append((k,'rotate'))
            elif k == pygame.K_s:
                if now - self.p1_s_last < self.double_tap_ms:
                    self.p1_events.append((k,'hard_drop'))
                    self.p1_s_last = 0
                else:
                    self.p1_s_last = now
                self.p1_keys_held['soft'] = True
            elif k == pygame.K_q:
                self.p1_events.append((k,'hold'))
            # P2
            elif k == pygame.K_LEFT:
                self.p2_events.append((k,'left'))
                self.p2_keys_held['left'] = True
            elif k == pygame.K_RIGHT:
                self.p2_events.append((k,'right'))
                self.p2_keys_held['right'] = True
            elif k == pygame.K_UP:
                self.p2_events.append((k,'rotate'))
            elif k == pygame.K_DOWN:
                if now - self.p2_down_last < self.double_tap_ms:
                    self.p2_events.append((k,'hard_drop'))
                    self.p2_down_last = 0
                else:
                    self.p2_down_last = now
                self.p2_keys_held['soft'] = True
            elif k == pygame.K_RSHIFT or k == pygame.K_RCTRL:
                self.p2_events.append((k,'hold'))

        elif event.type == pygame.KEYUP:
            k = event.key
            if k == pygame.K_a:   self.p1_keys_held['left']  = False
            elif k == pygame.K_d: self.p1_keys_held['right'] = False
            elif k == pygame.K_s: self.p1_keys_held['soft']  = False
            elif k == pygame.K_LEFT:  self.p2_keys_held['left']  = False
            elif k == pygame.K_RIGHT: self.p2_keys_held['right'] = False
            elif k == pygame.K_DOWN:  self.p2_keys_held['soft']  = False

    def flush(self):
        e1 = self.p1_events[:]
        e2 = self.p2_events[:]
        self.p1_events.clear()
        self.p2_events.clear()
        return e1, e2


# ─── Game Screen ──────────────────────────────────────────────────────────────

class GameScreen:
    def __init__(self, fonts, hiscore_ref):
        self.fonts = fonts
        self.hiscore_ref = hiscore_ref
        self.input = InputHandler()
        self.board1 = Board(P1_BX, BOARD_Y, 1, fonts)
        self.board2 = Board(P2_BX, BOARD_Y, 2, fonts)
        self.done = False
        self.winner = None
        self.done_timer = 0
        self.particles = ParticleSystem()
        self.ticks = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.done:
            return
        self.input.process_event(event)

    def update(self):
        self.ticks += 1
        e1, e2 = self.input.flush()

        if not self.done:
            self.board1.update(self.input.p1_keys_held, e1)
            self.board2.update(self.input.p2_keys_held, e2)

            # Cross-attack: send garbage
            if self.board1.pending_garbage > 0 and self.board2.alive:
                self.board2.garbage_queue.append(self.board1.pending_garbage)
                self.board1.pending_garbage = 0
            if self.board2.pending_garbage > 0 and self.board1.alive:
                self.board1.garbage_queue.append(self.board2.pending_garbage)
                self.board2.pending_garbage = 0

            if self.board1.game_over or self.board2.game_over:
                self.done = True
                if self.board1.game_over and not self.board2.game_over:
                    self.winner = 2
                elif self.board2.game_over and not self.board1.game_over:
                    self.winner = 1
                else:
                    # Whoever has more score
                    self.winner = 1 if self.board1.score >= self.board2.score else 2

                best = max(self.board1.score, self.board2.score)
                if best > self.hiscore_ref[0]:
                    self.hiscore_ref[0] = best

        else:
            self.done_timer += 1

        self.particles.update()

    def is_done(self):
        return self.done and self.done_timer > 100

    def draw(self, surf):
        self.board1.draw(surf)
        self.board2.draw(surf)
        self.board1.draw_side_panel(surf, side='left')
        self.board2.draw_side_panel(surf, side='right')
        self.particles.draw(surf)

        # Center divider
        cx = SCREEN_W // 2
        for i in range(0, SCREEN_H, 20):
            col_t = (math.sin(pygame.time.get_ticks()*0.002 + i*0.05)+1)/2
            col = (0, int(50+30*col_t), int(80+40*col_t))
            pygame.draw.line(surf, col, (cx, i), (cx, i+10))

        # Center HUD
        t = pygame.time.get_ticks()*0.003
        draw_neon_text(surf, "VS", self.fonts['title'], NEON_YELLOW, cx, SCREEN_H//2)

        # Level sync indicator
        l1 = self.board1.level
        l2 = self.board2.level
        draw_neon_text(surf, f"LV{l1}", self.fonts['tiny'], NEON_CYAN, cx-28, SCREEN_H//2+36, glow=False)
        draw_neon_text(surf, f"LV{l2}", self.fonts['tiny'], NEON_PINK, cx+28, SCREEN_H//2+36, glow=False)

        # Score diff bar
        s1, s2 = self.board1.score, self.board2.score
        total = max(s1+s2, 1)
        bar_w = 80
        bar_h = 8
        p1_w = int(bar_w * s1 / total)
        pygame.draw.rect(surf, DARK_GREY, (cx-bar_w//2, SCREEN_H//2+54, bar_w, bar_h), border_radius=3)
        if p1_w > 0:
            pygame.draw.rect(surf, NEON_CYAN, (cx-bar_w//2, SCREEN_H//2+54, p1_w, bar_h), border_radius=3)

        if self.done:
            self._draw_result(surf)

    def _draw_result(self, surf):
        prog = min(1.0, self.done_timer/60)
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0,0,0,int(160*prog)))
        surf.blit(ov, (0,0))

        if self.done_timer > 30:
            col = NEON_CYAN if self.winner==1 else NEON_PINK
            draw_neon_text(surf, f"PLAYER {self.winner} WINS!", self.fonts['title'], col,
                           SCREEN_W//2, SCREEN_H//2 - 50)
            s1,s2 = self.board1.score, self.board2.score
            draw_neon_text(surf, f"P1: {s1}    P2: {s2}", self.fonts['medium'], GREY,
                           SCREEN_W//2, SCREEN_H//2 + 10)
            if max(s1,s2) >= self.hiscore_ref[0] and max(s1,s2) > 0:
                t=(math.sin(pygame.time.get_ticks()*0.005)+1)/2
                draw_neon_text(surf, "NEW HIGH SCORE!", self.fonts['small'],
                               (255,int(180+75*t),0), SCREEN_W//2, SCREEN_H//2+50)
            draw_neon_text(surf, "ANY KEY  •  BACK TO MENU", self.fonts['small'], DARK_GREY,
                           SCREEN_W//2, SCREEN_H//2+90)


# ─── Menu ─────────────────────────────────────────────────────────────────────

class MenuScreen:
    def __init__(self, fonts, hiscore_ref):
        self.fonts = fonts
        self.hiscore_ref = hiscore_ref
        self.cursor = 0
        self.items = ["2 PLAYER BATTLE", "HIGH SCORE", "CONTROLS", "QUIT"]
        self.start_game = False
        self.sub = None   # None | "score" | "controls"
        self.stars = [(random.randint(0,SCREEN_W), random.randint(0,SCREEN_H),
                       random.uniform(0.3,1.5)) for _ in range(100)]
        self.ticks = 0
        self.falling_pieces = []
        self._spawn_deco()

    def _spawn_deco(self):
        for _ in range(8):
            name = random.choice(PIECE_NAMES)
            color = TETROMINOES[name]['color']
            self.falling_pieces.append({
                'name': name, 'color': color,
                'x': random.randint(0, SCREEN_W),
                'y': random.randint(-200, SCREEN_H),
                'vy': random.uniform(0.4, 1.2),
                'rot': random.randint(0,3),
                'alpha': random.randint(20,55),
            })

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        k = event.key
        if self.sub:
            if k in (pygame.K_a, pygame.K_LEFT, pygame.K_ESCAPE):
                self.sub = None
            return
        if k in (pygame.K_w, pygame.K_UP):
            self.cursor = (self.cursor-1) % len(self.items)
        elif k in (pygame.K_s, pygame.K_DOWN):
            self.cursor = (self.cursor+1) % len(self.items)
        elif k in (pygame.K_d, pygame.K_RETURN, pygame.K_RIGHT):
            sel = self.items[self.cursor]
            if sel == "2 PLAYER BATTLE":
                self.start_game = True
            elif sel == "HIGH SCORE":
                self.sub = "score"
            elif sel == "CONTROLS":
                self.sub = "controls"
            elif sel == "QUIT":
                pygame.quit(); sys.exit()

    def update(self):
        self.ticks += 1
        for i,(x,y,spd) in enumerate(self.stars):
            self.stars[i] = (x, (y+spd*0.3) % SCREEN_H, spd)
        for p in self.falling_pieces:
            p['y'] += p['vy']
            if p['y'] > SCREEN_H + 100:
                p['y'] = random.randint(-150, -20)
                p['x'] = random.randint(0, SCREEN_W)

    def draw(self, surf):
        # Stars
        for x,y,spd in self.stars:
            br = int(50+60*spd)
            pygame.draw.circle(surf, (br,br,br+20), (int(x),int(y)), 1 if spd<0.8 else 2)

        # Falling deco pieces
        for p in self.falling_pieces:
            cells = TETROMINOES[p['name']]['rotations'][p['rot']]
            mc = 14
            for r,c in cells:
                x = int(p['x']) + c*mc
                y = int(p['y']) + r*mc
                s = pygame.Surface((mc,mc), pygame.SRCALPHA)
                pygame.draw.rect(s, (*p['color'], p['alpha']), (1,1,mc-2,mc-2), border_radius=2)
                surf.blit(s, (x,y))

        if self.sub == "score":
            self._draw_score(surf)
        elif self.sub == "controls":
            self._draw_controls(surf)
        else:
            self._draw_main(surf)

    def _frame(self, surf):
        t = pygame.time.get_ticks()*0.001
        for i in range(3):
            a = int(50+25*math.sin(t+i*0.5))
            s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            m = 8+i*6
            pygame.draw.rect(s, (*NEON_CYAN, a), (m,m,SCREEN_W-m*2,SCREEN_H-m*2), 1, border_radius=6)
            surf.blit(s, (0,0))

    def _draw_main(self, surf):
        self._frame(surf)
        t = pygame.time.get_ticks()*0.002
        ty = 120 + int(5*math.sin(t))

        draw_neon_text(surf, "TETRIS", self.fonts['logo'], NEON_CYAN, SCREEN_W//2, ty)
        draw_neon_text(surf, "ARCADE  BATTLE", self.fonts['title'], NEON_PINK,
                       SCREEN_W//2, ty+82)

        lw=300; lx=SCREEN_W//2-lw//2; ly=ty+115
        pygame.draw.line(surf, NEON_CYAN, (lx,ly),(lx+lw,ly),1)
        pygame.draw.circle(surf,NEON_CYAN,(lx,ly),3)
        pygame.draw.circle(surf,NEON_CYAN,(lx+lw,ly),3)

        hi_text = f"BEST  {self.hiscore_ref[0]:08d}"
        draw_neon_text(surf, hi_text, self.fonts['small'], NEON_YELLOW, SCREEN_W//2, ty+140)

        iy = 330; gap = 64
        for i, item in enumerate(self.items):
            y = iy + i*gap
            sel = (i == self.cursor)
            if sel:
                bw,bh = 340,48
                bx=SCREEN_W//2-bw//2; by=y-bh//2
                p=(math.sin(pygame.time.get_ticks()*0.004)+1)/2
                col=(0,int(150+105*p),int(200+55*p))
                draw_neon_rect(surf,col,(bx,by,bw,bh),width=2,glow=True,radius=6)
                draw_neon_text(surf,"▶",self.fonts['medium'],NEON_CYAN,SCREEN_W//2-185,y)
                c=WHITE
            else:
                c=GREY
            draw_neon_text(surf, item, self.fonts['medium'], c, SCREEN_W//2, y, glow=sel)

        draw_neon_text(surf,"W/S  NAVIGATE    D  SELECT",self.fonts['tiny'],DARK_GREY,SCREEN_W//2,SCREEN_H-25)

    def _draw_score(self, surf):
        self._frame(surf)
        draw_neon_text(surf,"HIGH SCORE",self.fonts['title'],NEON_YELLOW,SCREEN_W//2,130)
        t=pygame.time.get_ticks()*0.003
        col=(255,int(180+75*math.sin(t)),0)
        draw_neon_text(surf,f"{self.hiscore_ref[0]:08d}",self.fonts['logo'],col,SCREEN_W//2,SCREEN_H//2-20)
        draw_neon_text(surf,"COMBINED BEST",self.fonts['small'],GREY,SCREEN_W//2,SCREEN_H//2+60)
        draw_neon_text(surf,"A  BACK",self.fonts['small'],DARK_GREY,SCREEN_W//2,SCREEN_H-35)

    def _draw_controls(self, surf):
        self._frame(surf)
        draw_neon_text(surf,"CONTROLS",self.fonts['title'],NEON_CYAN,SCREEN_W//2,80)

        cols_data = [
            ("PLAYER 1", NEON_CYAN, [
                ("Move",    "A / D"),
                ("Rotate",  "W"),
                ("Soft Drop","S"),
                ("Hard Drop","S  S  (double tap)"),
                ("Hold",    "Q"),
            ]),
            ("PLAYER 2", NEON_PINK, [
                ("Move",    "← / →"),
                ("Rotate",  "↑"),
                ("Soft Drop","↓"),
                ("Hard Drop","↓  ↓  (double tap)"),
                ("Hold",    "R-SHIFT"),
            ]),
        ]

        for pi,(label,lcol,actions) in enumerate(cols_data):
            cx_ = SCREEN_W//4 + pi*(SCREEN_W//2)
            draw_neon_text(surf,label,self.fonts['medium'],lcol,cx_,145)
            pygame.draw.line(surf,lcol,(cx_-100,165),(cx_+100,165),1)
            for ai,(act,key) in enumerate(actions):
                y=198+ai*64
                draw_neon_text(surf,act,self.fonts['tiny'],GREY,cx_,y,glow=False)
                draw_neon_text(surf,key,self.fonts['small'],lcol,cx_,y+24)

        draw_neon_text(surf,"GARBAGE: clearing lines sends junk rows to opponent",
                       self.fonts['tiny'],GREY,SCREEN_W//2,SCREEN_H-65,glow=False)
        draw_neon_text(surf,"A  BACK",self.fonts['small'],DARK_GREY,SCREEN_W//2,SCREEN_H-35)


# ─── App ──────────────────────────────────────────────────────────────────────

class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("TETRIS ARCADE — 2 PLAYER")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.fonts = self._load_fonts()
        self.scanlines = scanline_surface(SCREEN_W, SCREEN_H)
        self.hiscore = [load_hiscore()]
        self.mode = "menu"
        self.menu = MenuScreen(self.fonts, self.hiscore)
        self.game = None

    def _load_fonts(self):
        candidates = ["Courier New","Courier","DejaVu Sans Mono","monospace"]
        def gf(size):
            for n in candidates:
                try: return pygame.font.SysFont(n, size, bold=True)
                except: pass
            return pygame.font.Font(None, size)
        return {
            'logo':   gf(88),
            'title':  gf(48),
            'hud':    gf(34),
            'medium': gf(28),
            'small':  gf(21),
            'tiny':   gf(16),
        }

    def run(self):
        while True:
            self.clock.tick(FPS)
            self._events()
            self._update()
            self._draw()

    def _events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_hiscore(self.hiscore[0])
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.mode == "game":
                    self._back_to_menu(); return

            if self.mode == "menu":
                self.menu.handle_event(event)
                if self.menu.start_game:
                    self.menu.start_game = False
                    self._start_game()
            elif self.mode == "game":
                if self.game and self.game.is_done():
                    if event.type == pygame.KEYDOWN:
                        self._back_to_menu()
                else:
                    self.game.handle_event(event)

    def _start_game(self):
        self.game = GameScreen(self.fonts, self.hiscore)
        self.mode = "game"

    def _back_to_menu(self):
        save_hiscore(self.hiscore[0])
        self.menu = MenuScreen(self.fonts, self.hiscore)
        self.mode = "menu"
        self.game = None

    def _update(self):
        if self.mode == "menu":
            self.menu.update()
        elif self.mode == "game" and self.game:
            self.game.update()

    def _draw(self):
        self.screen.fill(DARK_BG)
        if self.mode == "menu":
            self.menu.draw(self.screen)
        elif self.mode == "game" and self.game:
            self.game.draw(self.screen)

        # CRT
        self.screen.blit(self.scanlines, (0,0))
        self._vignette()
        pygame.display.flip()

    def _vignette(self):
        v = pygame.Surface((SCREEN_W,SCREEN_H), pygame.SRCALPHA)
        for i in range(50):
            a = int(120*(1-i/50)**2)
            c=(0,0,0,a)
            pygame.draw.line(v,c,(0,i),(SCREEN_W,i))
            pygame.draw.line(v,c,(0,SCREEN_H-1-i),(SCREEN_W,SCREEN_H-1-i))
        for i in range(40):
            a=int(100*(1-i/40)**2)
            c=(0,0,0,a)
            pygame.draw.line(v,c,(i,0),(i,SCREEN_H))
            pygame.draw.line(v,c,(SCREEN_W-1-i,0),(SCREEN_W-1-i,SCREEN_H))
        self.screen.blit(v,(0,0))


if __name__ == "__main__":
    App().run()
