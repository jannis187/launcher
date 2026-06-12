"""
╔══════════════════════════════════════════╗
║         SNAKE ARCADE  •  v1.0            ║
║   Retro arcade cabinet feel in pygame    ║
╚══════════════════════════════════════════╝
Controls: WASD to move / navigate menus
"""

import pygame
import random
import math
import sys
import json
import os

# ─── Constants ────────────────────────────────────────────────────────────────

SCREEN_W, SCREEN_H = 1280, 900
GRID_COLS, GRID_ROWS = 30, 30
CELL = 16
BOARD_W = GRID_COLS * CELL       # 480
BOARD_H = GRID_ROWS * CELL       # 480
BOARD_X = (SCREEN_W - BOARD_W) // 2   # 160
BOARD_Y = 160

FPS = 60

# Retro arcade palette
BLACK       = (0,   0,   0)
DARK_BG     = (8,   8,   18)
PANEL_BG    = (12,  12,  28)
GRID_LINE   = (18,  18,  38)
NEON_GREEN  = (0,   255, 80)
NEON_LIME   = (120, 255, 0)
NEON_CYAN   = (0,   230, 255)
NEON_PINK   = (255, 40,  160)
NEON_YELLOW = (255, 220, 0)
NEON_ORANGE = (255, 120, 0)
NEON_RED    = (255, 40,  40)
DIM_GREEN   = (0,   80,  30)
DIM_CYAN    = (0,   60,  80)
WHITE       = (255, 255, 255)
GREY        = (120, 120, 140)
DARK_GREY   = (40,  40,  55)

SCORE_FILE = os.path.join(os.path.dirname(__file__), "snake_hiscore.json")

# Difficulty presets: (label, ticks_per_move, wall_kill)
DIFFICULTIES = [
    ("EASY",   12, False),
    ("MEDIUM",  8, True),
    ("HARD",    5, True),
    ("INSANE",  3, True),
]

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

def draw_neon_rect(surf, color, rect, width=2, glow=True, radius=4):
    """Draw a rectangle with optional neon glow effect."""
    if glow:
        glow_surf = pygame.Surface((rect[2] + 20, rect[3] + 20), pygame.SRCALPHA)
        dim = tuple(max(0, c // 4) for c in color)
        pygame.draw.rect(glow_surf, (*dim, 60), (0, 0, rect[2]+20, rect[3]+20), border_radius=radius+4)
        surf.blit(glow_surf, (rect[0]-10, rect[1]-10))
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)

def draw_neon_text(surf, text, font, color, cx, cy, glow=True):
    """Render text with neon glow."""
    if glow:
        glow_color = tuple(min(255, c // 2) for c in color)
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,-1),(-1,1),(1,1)]:
            s = font.render(text, True, glow_color)
            surf.blit(s, s.get_rect(center=(cx+dx, cy+dy)))
    s = font.render(text, True, color)
    surf.blit(s, s.get_rect(center=(cx, cy)))

def scanline_surface(w, h):
    """Create a scanline overlay."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 2):
        pygame.draw.line(s, (0, 0, 0, 40), (0, y), (w, y))
    return s

# ─── Particle System ──────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.5, 5.0)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(18, 35)
        self.max_life = self.life
        self.color = color
        self.size = random.uniform(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.life -= 1

    def draw(self, surf):
        alpha = int(255 * self.life / self.max_life)
        r = max(1, int(self.size * self.life / self.max_life))
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (int(self.x)-r, int(self.y)-r))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=12):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def update(self):
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)

# ─── Snake Game Logic ─────────────────────────────────────────────────────────

class Snake:
    def __init__(self):
        cx, cy = GRID_COLS // 2, GRID_ROWS // 2
        self.body = [(cx, cy), (cx-1, cy), (cx-2, cy)]
        self.direction = (1, 0)
        self.next_dir = (1, 0)
        self.grew = False

    def set_direction(self, dx, dy):
        # Prevent 180-degree turn
        if (dx, dy) != (-self.direction[0], -self.direction[1]):
            self.next_dir = (dx, dy)

    def move(self):
        self.direction = self.next_dir
        hx, hy = self.body[0]
        new_head = (hx + self.direction[0], hy + self.direction[1])
        self.body.insert(0, new_head)
        if not self.grew:
            self.body.pop()
        self.grew = False

    def grow(self):
        self.grew = True

    @property
    def head(self):
        return self.body[0]

    def self_collision(self):
        return self.head in self.body[1:]


class Food:
    def __init__(self, snake_body):
        self.pos = self._random_pos(snake_body)
        self.pulse = 0.0
        self.special = False
        self.special_timer = 0

    def _random_pos(self, avoid):
        avoid_set = set(avoid)
        candidates = [
            (x, y)
            for x in range(GRID_COLS)
            for y in range(GRID_ROWS)
            if (x, y) not in avoid_set
        ]
        return random.choice(candidates) if candidates else (0, 0)

    def respawn(self, snake_body, score):
        self.pos = self._random_pos(snake_body)
        self.pulse = 0.0
        # Chance of special golden food every 5 points
        self.special = (score > 0 and score % 5 == 0 and random.random() < 0.4)
        self.special_timer = 120 if self.special else 0

    def update(self):
        self.pulse += 0.12
        if self.special:
            self.special_timer -= 1
            if self.special_timer <= 0:
                self.special = False

    def draw(self, surf):
        gx, gy = self.pos
        px = BOARD_X + gx * CELL
        py = BOARD_Y + gy * CELL
        t = (math.sin(self.pulse) + 1) / 2  # 0..1

        if self.special:
            color = (255, int(180 + 75*t), 0)
            glow_col = (255, 140, 0)
            size = int(CELL * 0.65 + CELL * 0.1 * t)
        else:
            color = (int(180 + 75*t), 255, int(80*t))
            glow_col = NEON_GREEN
            size = int(CELL * 0.55 + CELL * 0.08 * t)

        # Glow
        glow = pygame.Surface((CELL*2, CELL*2), pygame.SRCALPHA)
        r = int(CELL * 0.6 + CELL * 0.15 * t)
        pygame.draw.circle(glow, (*glow_col, 50), (CELL, CELL), r)
        surf.blit(glow, (px - CELL//2, py - CELL//2))
        # Body
        cx_ = px + CELL // 2
        cy_ = py + CELL // 2
        pygame.draw.circle(surf, color, (cx_, cy_), size)
        # Shine
        pygame.draw.circle(surf, WHITE, (cx_ - size//3, cy_ - size//3), max(1, size//4))


# ─── Game Screen ──────────────────────────────────────────────────────────────

class GameScreen:
    def __init__(self, fonts, difficulty_idx, hiscore_ref):
        self.fonts = fonts
        self.diff_idx = difficulty_idx
        self.hiscore_ref = hiscore_ref

        label, ticks, wall_kill = DIFFICULTIES[difficulty_idx]
        self.ticks_per_move = ticks
        self.wall_kill = wall_kill

        self.snake = Snake()
        self.food = Food(self.snake.body)
        self.particles = ParticleSystem()
        self.score = 0
        self.tick = 0
        self.alive = True
        self.death_timer = 0
        self.flash_timer = 0
        self.combo = 0
        self.combo_timer = 0

        # Screen shake
        self.shake_x = 0
        self.shake_y = 0
        self.shake_timer = 0

    def _shake(self, intensity=5, duration=8):
        self.shake_timer = duration
        self.shake_intensity = intensity

    def handle_event(self, event):
        if not self.alive:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self.snake.set_direction(0, -1)
            elif event.key == pygame.K_s:
                self.snake.set_direction(0, 1)
            elif event.key == pygame.K_a:
                self.snake.set_direction(-1, 0)
            elif event.key == pygame.K_d:
                self.snake.set_direction(1, 0)

    def update(self):
        if not self.alive:
            self.death_timer += 1
            self.particles.update()
            return

        self.tick += 1
        self.particles.update()

        # Combo decay
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0

        # Screen shake
        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_x = random.randint(-self.shake_intensity, self.shake_intensity)
            self.shake_y = random.randint(-self.shake_intensity, self.shake_intensity)
        else:
            self.shake_x = self.shake_y = 0

        # Flash
        if self.flash_timer > 0:
            self.flash_timer -= 1

        # Move snake
        if self.tick % self.ticks_per_move == 0:
            self.snake.move()
            hx, hy = self.snake.head

            # Wall collision
            if self.wall_kill:
                if not (0 <= hx < GRID_COLS and 0 <= hy < GRID_ROWS):
                    self._die()
                    return
            else:
                # Wrap around
                self.snake.body[0] = (hx % GRID_COLS, hy % GRID_ROWS)

            # Self collision
            if self.snake.self_collision():
                self._die()
                return

            # Food eaten
            if self.snake.head == self.food.pos:
                self.snake.grow()
                pts = 3 if self.food.special else 1
                self.combo += 1
                self.combo_timer = 40
                pts = pts * min(self.combo, 4)
                self.score += pts

                # Particles
                fx = BOARD_X + self.food.pos[0] * CELL + CELL // 2
                fy = BOARD_Y + self.food.pos[1] * CELL + CELL // 2
                col = NEON_YELLOW if self.food.special else NEON_GREEN
                self.particles.emit(fx, fy, col, count=16 if self.food.special else 10)
                self.flash_timer = 4

                self.food.respawn(self.snake.body, self.score)

                if self.score > self.hiscore_ref[0]:
                    self.hiscore_ref[0] = self.score

        self.food.update()

    def _die(self):
        self.alive = False
        hx, hy = self.snake.head
        px = BOARD_X + hx * CELL + CELL // 2
        py = BOARD_Y + hy * CELL + CELL // 2
        self.particles.emit(px, py, NEON_RED, count=30)
        for seg in self.snake.body[:5]:
            sx = BOARD_X + seg[0] * CELL + CELL // 2
            sy = BOARD_Y + seg[1] * CELL + CELL // 2
            self.particles.emit(sx, sy, NEON_ORANGE, count=8)
        self._shake(8, 14)

    def is_done(self):
        return not self.alive and self.death_timer > 90

    def draw(self, surf):
        off = (self.shake_x, self.shake_y)

        # Board background
        board_rect = pygame.Rect(BOARD_X + off[0], BOARD_Y + off[1], BOARD_W, BOARD_H)
        pygame.draw.rect(surf, PANEL_BG, board_rect)

        # Grid lines
        for col in range(GRID_COLS + 1):
            x = BOARD_X + col * CELL + off[0]
            pygame.draw.line(surf, GRID_LINE, (x, BOARD_Y + off[1]), (x, BOARD_Y + BOARD_H + off[1]))
        for row in range(GRID_ROWS + 1):
            y = BOARD_Y + row * CELL + off[1]
            pygame.draw.line(surf, GRID_LINE, (BOARD_X + off[0], y), (BOARD_X + BOARD_W + off[0], y))

        # Board border
        glow_alpha = 120 + int(50 * math.sin(pygame.time.get_ticks() * 0.002))
        border_col = NEON_CYAN if self.alive else NEON_RED
        draw_neon_rect(surf, border_col, (BOARD_X-2+off[0], BOARD_Y-2+off[1], BOARD_W+4, BOARD_H+4), width=2, radius=2)

        # Food
        self.food.draw(surf)

        # Snake
        self._draw_snake(surf, off)

        # Particles
        self.particles.draw(surf)

        # Flash overlay
        if self.flash_timer > 0:
            fl = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
            fl.fill((100, 255, 100, int(60 * self.flash_timer / 4)))
            surf.blit(fl, (BOARD_X + off[0], BOARD_Y + off[1]))

        # HUD
        self._draw_hud(surf)

        # Death overlay
        if not self.alive:
            self._draw_death_overlay(surf)

    def _draw_snake(self, surf, off):
        length = len(self.snake.body)
        for i, (gx, gy) in enumerate(self.snake.body):
            px = BOARD_X + gx * CELL + off[0]
            py = BOARD_Y + gy * CELL + off[1]
            t = i / max(length - 1, 1)

            if i == 0:
                # Head — brighter
                head_color = NEON_GREEN
                r = CELL // 2 - 1
                pygame.draw.rect(surf, head_color, (px+1, py+1, CELL-2, CELL-2), border_radius=4)
                # Eyes
                dx, dy = self.snake.direction
                eye_offset = 3
                if dx == 1:
                    e1 = (px + CELL - 4, py + 3)
                    e2 = (px + CELL - 4, py + CELL - 5)
                elif dx == -1:
                    e1 = (px + 3, py + 3)
                    e2 = (px + 3, py + CELL - 5)
                elif dy == -1:
                    e1 = (px + 3, py + 3)
                    e2 = (px + CELL - 5, py + 3)
                else:
                    e1 = (px + 3, py + CELL - 4)
                    e2 = (px + CELL - 5, py + CELL - 4)
                pygame.draw.circle(surf, BLACK, e1, 2)
                pygame.draw.circle(surf, BLACK, e2, 2)
            else:
                # Body gradient: green → lime → dark green
                g = int(180 + 75 * (1 - t))
                body_color = (0, g, int(40 * (1-t)))
                margin = 2 if i > 1 else 1
                pygame.draw.rect(surf, body_color,
                                 (px + margin, py + margin, CELL - margin*2, CELL - margin*2),
                                 border_radius=3)

    def _draw_hud(self, surf):
        # Score panel top
        score_text = f"SCORE  {self.score:06d}"
        hi_text    = f"BEST   {self.hiscore_ref[0]:06d}"
        diff_label = DIFFICULTIES[self.diff_idx][0]

        draw_neon_text(surf, score_text, self.fonts['hud'], NEON_GREEN, SCREEN_W//2, 50)
        draw_neon_text(surf, hi_text,    self.fonts['hud'], NEON_CYAN,  SCREEN_W//2, 85)

        # Difficulty badge
        diff_col = [NEON_GREEN, NEON_YELLOW, NEON_ORANGE, NEON_PINK][self.diff_idx]
        draw_neon_text(surf, diff_label, self.fonts['small'], diff_col, SCREEN_W//2, 118)

        # Combo display
        if self.combo >= 2:
            alpha = min(255, self.combo_timer * 6)
            draw_neon_text(surf, f"x{self.combo} COMBO!", self.fonts['medium'], NEON_YELLOW,
                           SCREEN_W//2, BOARD_Y + BOARD_H + 30)

        # Length bottom
        length_text = f"LENGTH  {len(self.snake.body):03d}"
        draw_neon_text(surf, length_text, self.fonts['small'], GREY, SCREEN_W//2, BOARD_Y + BOARD_H + 55)

    def _draw_death_overlay(self, surf):
        progress = min(1.0, self.death_timer / 60)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(140 * progress)))
        surf.blit(overlay, (0, 0))

        if self.death_timer > 30:
            draw_neon_text(surf, "GAME OVER", self.fonts['title'], NEON_RED, SCREEN_W//2, SCREEN_H//2 - 30)
            draw_neon_text(surf, f"SCORE: {self.score}", self.fonts['medium'], NEON_YELLOW, SCREEN_W//2, SCREEN_H//2 + 20)
            if self.score >= self.hiscore_ref[0] and self.score > 0:
                t = (math.sin(pygame.time.get_ticks() * 0.005) + 1) / 2
                col = (255, int(200 + 55*t), 0)
                draw_neon_text(surf, "NEW HIGH SCORE!", self.fonts['small'], col, SCREEN_W//2, SCREEN_H//2 + 55)
            draw_neon_text(surf, "PRESS  W / S  TO CONTINUE", self.fonts['small'], GREY, SCREEN_W//2, SCREEN_H//2 + 90)


# ─── Menu Screen ──────────────────────────────────────────────────────────────

class MenuScreen:
    MAIN   = "main"
    DIFF   = "difficulty"
    SCORES = "scores"
    HELP   = "help"
    ABOUT  = "about"

    def __init__(self, fonts, hiscore_ref):
        self.fonts = fonts
        self.hiscore_ref = hiscore_ref
        self.state = self.MAIN
        self.cursor = 0
        self.diff_cursor = 0
        self.selected_diff = 1  # default MEDIUM
        self.blink = 0
        self.star_field = [(random.randint(0, SCREEN_W), random.randint(0, SCREEN_H),
                            random.uniform(0.3, 1.5)) for _ in range(120)]
        self.start_game = False
        self.scroll_offset = 0

        self.main_items = ["PLAY", "DIFFICULTY", "HIGH SCORES", "HOW TO PLAY", "ABOUT", "QUIT"]

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        if self.state == self.MAIN:
            if k == pygame.K_w:
                self.cursor = (self.cursor - 1) % len(self.main_items)
            elif k == pygame.K_s:
                self.cursor = (self.cursor + 1) % len(self.main_items)
            elif k in (pygame.K_d, pygame.K_RETURN, pygame.K_SPACE):
                self._select_main()

        elif self.state == self.DIFF:
            if k == pygame.K_w:
                self.diff_cursor = (self.diff_cursor - 1) % len(DIFFICULTIES)
            elif k == pygame.K_s:
                self.diff_cursor = (self.diff_cursor + 1) % len(DIFFICULTIES)
            elif k in (pygame.K_d, pygame.K_RETURN):
                self.selected_diff = self.diff_cursor
                self.state = self.MAIN
            elif k == pygame.K_a:
                self.state = self.MAIN

        elif self.state in (self.SCORES, self.HELP, self.ABOUT):
            if k in (pygame.K_a, pygame.K_ESCAPE):
                self.state = self.MAIN

    def _select_main(self):
        sel = self.main_items[self.cursor]
        if sel == "PLAY":
            self.start_game = True
        elif sel == "DIFFICULTY":
            self.diff_cursor = self.selected_diff
            self.state = self.DIFF
        elif sel == "HIGH SCORES":
            self.state = self.SCORES
        elif sel == "HOW TO PLAY":
            self.state = self.HELP
        elif sel == "ABOUT":
            self.state = self.ABOUT
        elif sel == "QUIT":
            pygame.quit()
            sys.exit()

    def update(self):
        self.blink = (self.blink + 1) % 60
        # Scroll starfield
        for i, (x, y, spd) in enumerate(self.star_field):
            ny = (y + spd * 0.4) % SCREEN_H
            self.star_field[i] = (x, ny, spd)

    def draw(self, surf):
        self._draw_starfield(surf)
        if self.state == self.MAIN:
            self._draw_main(surf)
        elif self.state == self.DIFF:
            self._draw_difficulty(surf)
        elif self.state == self.SCORES:
            self._draw_scores(surf)
        elif self.state == self.HELP:
            self._draw_help(surf)
        elif self.state == self.ABOUT:
            self._draw_about(surf)

    def _draw_starfield(self, surf):
        for x, y, spd in self.star_field:
            br = int(60 + 80 * spd)
            r = 1 if spd < 0.8 else 2
            pygame.draw.circle(surf, (br, br, br+20), (int(x), int(y)), r)

    def _draw_cabinet_frame(self, surf):
        """Draw decorative arcade cabinet border."""
        t = pygame.time.get_ticks() * 0.001
        for i in range(4):
            alpha = int(60 + 30 * math.sin(t + i * 0.5))
            col = (*NEON_CYAN, alpha)
            s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            margin = 6 + i * 5
            pygame.draw.rect(s, col, (margin, margin, SCREEN_W - margin*2, SCREEN_H - margin*2), 1, border_radius=8)
            surf.blit(s, (0, 0))

    def _draw_main(self, surf):
        self._draw_cabinet_frame(surf)

        # Title
        t = pygame.time.get_ticks() * 0.002
        title_y = 130 + int(6 * math.sin(t))
        draw_neon_text(surf, "SNAKE", self.fonts['logo'], NEON_GREEN, SCREEN_W//2, title_y)

        # Subtitle with pulse
        sub_alpha = int(180 + 75 * math.sin(t * 1.5))
        draw_neon_text(surf, "ARCADE", self.fonts['title'], (0, sub_alpha, int(sub_alpha * 0.6)),
                       SCREEN_W//2, title_y + 80)

        # Decorative line
        lw = 260
        lx = SCREEN_W//2 - lw//2
        ly = title_y + 115
        pygame.draw.line(surf, NEON_CYAN, (lx, ly), (lx + lw, ly), 1)
        pygame.draw.circle(surf, NEON_CYAN, (lx, ly), 3)
        pygame.draw.circle(surf, NEON_CYAN, (lx + lw, ly), 3)

        # Menu items
        item_start_y = 340
        item_gap = 58
        for i, item in enumerate(self.main_items):
            y = item_start_y + i * item_gap
            selected = (i == self.cursor)

            if selected:
                # Selection box
                box_w, box_h = 320, 44
                bx = SCREEN_W//2 - box_w//2
                by = y - box_h//2
                pulse = (math.sin(pygame.time.get_ticks() * 0.004) + 1) / 2
                col = (0, int(180 + 75 * pulse), int(60 + 40 * pulse))
                draw_neon_rect(surf, col, (bx, by, box_w, box_h), width=2, glow=True, radius=6)
                # Arrow
                draw_neon_text(surf, "▶", self.fonts['medium'], NEON_GREEN, SCREEN_W//2 - 175, y)
                color = WHITE
            else:
                color = GREY

            draw_neon_text(surf, item, self.fonts['medium'], color, SCREEN_W//2, y, glow=selected)

        # Diff badge bottom
        diff_label, _, _ = DIFFICULTIES[self.selected_diff]
        diff_col = [NEON_GREEN, NEON_YELLOW, NEON_ORANGE, NEON_PINK][self.selected_diff]
        draw_neon_text(surf, f"[ {diff_label} ]", self.fonts['small'], diff_col, SCREEN_W//2, SCREEN_H - 60)

        # Control hint
        draw_neon_text(surf, "W/S  NAVIGATE    D  SELECT", self.fonts['tiny'], DARK_GREY, SCREEN_W//2, SCREEN_H - 28)

    def _draw_difficulty(self, surf):
        self._draw_cabinet_frame(surf)
        draw_neon_text(surf, "DIFFICULTY", self.fonts['title'], NEON_CYAN, SCREEN_W//2, 130)

        desc = [
            "Walls wrap  •  Relaxed pace",
            "Walls kill  •  Standard pace",
            "Walls kill  •  Fast pace",
            "Walls kill  •  Extreme speed",
        ]
        colors = [NEON_GREEN, NEON_YELLOW, NEON_ORANGE, NEON_PINK]

        for i, (label, _, wk) in enumerate(DIFFICULTIES):
            y = 270 + i * 90
            selected = (i == self.diff_cursor)
            col = colors[i]

            if selected:
                bx = SCREEN_W//2 - 200
                draw_neon_rect(surf, col, (bx, y-30, 400, 60), width=2, glow=True, radius=6)
                draw_neon_text(surf, "▶", self.fonts['medium'], col, SCREEN_W//2 - 220, y-2)

            alpha_col = col if selected else tuple(c//3 for c in col)
            draw_neon_text(surf, label, self.fonts['medium'], alpha_col, SCREEN_W//2, y - 5, glow=selected)
            draw_neon_text(surf, desc[i], self.fonts['tiny'], GREY if not selected else (180,180,200),
                           SCREEN_W//2, y + 22, glow=False)

        draw_neon_text(surf, "D  CONFIRM    A  BACK", self.fonts['small'], DARK_GREY, SCREEN_W//2, SCREEN_H - 35)

    def _draw_scores(self, surf):
        self._draw_cabinet_frame(surf)
        draw_neon_text(surf, "HIGH SCORES", self.fonts['title'], NEON_YELLOW, SCREEN_W//2, 130)

        t = pygame.time.get_ticks() * 0.003
        pulse_col = (255, int(180 + 75 * math.sin(t)), 0)
        draw_neon_text(surf, f"{self.hiscore_ref[0]:08d}", self.fonts['logo'], pulse_col, SCREEN_W//2, SCREEN_H//2 - 20)
        draw_neon_text(surf, "ALL TIME BEST", self.fonts['small'], GREY, SCREEN_W//2, SCREEN_H//2 + 60)

        draw_neon_text(surf, "A  BACK", self.fonts['small'], DARK_GREY, SCREEN_W//2, SCREEN_H - 35)

    def _draw_help(self, surf):
        self._draw_cabinet_frame(surf)
        draw_neon_text(surf, "HOW TO PLAY", self.fonts['title'], NEON_CYAN, SCREEN_W//2, 110)

        lines = [
            ("MOVE",    "W A S D",         NEON_GREEN),
            ("EAT",     "Green dots = +1", NEON_GREEN),
            ("BONUS",   "Gold dots = +3",  NEON_YELLOW),
            ("COMBO",   "Eat fast = bonus multiplier", NEON_ORANGE),
            ("WRAP",    "Easy: walls wrap around", GREY),
            ("DEATH",   "Med/Hard: walls kill you!", NEON_RED),
            ("GOAL",    "Eat, grow, survive!", WHITE),
        ]
        for i, (key, val, col) in enumerate(lines):
            y = 230 + i * 72
            draw_neon_text(surf, key, self.fonts['small'], GREY, SCREEN_W//2 - 130, y, glow=False)
            draw_neon_text(surf, val, self.fonts['small'], col, SCREEN_W//2 + 60, y)
            pygame.draw.line(surf, DARK_GREY, (SCREEN_W//2 - 200, y+20), (SCREEN_W//2 + 200, y+20))

        draw_neon_text(surf, "A  BACK", self.fonts['small'], DARK_GREY, SCREEN_W//2, SCREEN_H - 35)

    def _draw_about(self, surf):
        self._draw_cabinet_frame(surf)
        draw_neon_text(surf, "ABOUT", self.fonts['title'], NEON_PINK, SCREEN_W//2, 130)

        info = [
            ("SNAKE ARCADE", NEON_GREEN, self.fonts['medium']),
            ("Version 1.0", GREY, self.fonts['small']),
            ("", WHITE, self.fonts['small']),
            ("Built with pygame 2", NEON_CYAN, self.fonts['small']),
            ("Retro arcade vibes", NEON_YELLOW, self.fonts['small']),
            ("", WHITE, self.fonts['small']),
            ("INSERT COIN TO PLAY", NEON_PINK, self.fonts['medium']),
        ]
        y = 250
        for text, col, font in info:
            if text:
                draw_neon_text(surf, text, font, col, SCREEN_W//2, y)
            y += 58

        draw_neon_text(surf, "A  BACK", self.fonts['small'], DARK_GREY, SCREEN_W//2, SCREEN_H - 35)


# ─── Main App ─────────────────────────────────────────────────────────────────

class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("SNAKE ARCADE")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        # Fonts — use monospaced/pixel style
        self.fonts = self._load_fonts()
        self.scanlines = scanline_surface(SCREEN_W, SCREEN_H)
        self.hiscore = [load_hiscore()]

        self.menu = MenuScreen(self.fonts, self.hiscore)
        self.game = None
        self.mode = "menu"   # "menu" | "game"
        self.game_over_choice = None  # for post-game menu navigation

    def _load_fonts(self):
        # Try to use a monospaced font for the retro feel
        candidates = ["Courier New", "Courier", "DejaVu Sans Mono", "monospace"]
        def get_font(size):
            for name in candidates:
                try:
                    f = pygame.font.SysFont(name, size, bold=True)
                    return f
                except Exception:
                    pass
            return pygame.font.Font(None, size)

        return {
            'logo':   get_font(96),
            'title':  get_font(52),
            'hud':    get_font(36),
            'medium': get_font(30),
            'small':  get_font(22),
            'tiny':   get_font(17),
        }

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_hiscore(self.hiscore[0])
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.mode == "game":
                    self._return_to_menu()
                    return

            if self.mode == "menu":
                self.menu.handle_event(event)
                if self.menu.start_game:
                    self.menu.start_game = False
                    self._start_game()
            elif self.mode == "game":
                if self.game and self.game.is_done():
                    # Post-game: W/S to navigate back to menu
                    if event.type == pygame.KEYDOWN and event.key in (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
                        self._return_to_menu()
                else:
                    self.game.handle_event(event)

    def _start_game(self):
        self.game = GameScreen(self.fonts, self.menu.selected_diff, self.hiscore)
        self.mode = "game"

    def _return_to_menu(self):
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

        # CRT scanlines overlay
        self.screen.blit(self.scanlines, (0, 0))

        # Vignette
        self._draw_vignette()

        pygame.display.flip()

    def _draw_vignette(self):
        """Dark vignette at screen edges for CRT effect."""
        v = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(60):
            alpha = int(140 * (1 - i/60) ** 2)
            col = (0, 0, 0, alpha)
            # top
            pygame.draw.line(v, col, (0, i), (SCREEN_W, i))
            # bottom
            pygame.draw.line(v, col, (0, SCREEN_H-1-i), (SCREEN_W, SCREEN_H-1-i))
        for i in range(50):
            alpha = int(120 * (1 - i/50) ** 2)
            col = (0, 0, 0, alpha)
            pygame.draw.line(v, col, (i, 0), (i, SCREEN_H))
            pygame.draw.line(v, col, (SCREEN_W-1-i, 0), (SCREEN_W-1-i, SCREEN_H))
        self.screen.blit(v, (0, 0))


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    App().run()
