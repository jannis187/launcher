"""
Arcade Game Selection Screen
Retro-Style Carousel Menu
Controls: LEFT / RIGHT (navigate) | ENTER (select) | ESC (quit)
"""

import json
import os
import subprocess
import pygame
import sys
import math

# ── CONFIG ─────────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1280, 800
FPS = 60
CAROUSEL_ANIM_SPEED = 5.0
BASE_DIR = os.path.dirname(__file__)
DATA_JSON = os.path.join(BASE_DIR, "data.json")
BANNER_CACHE = {}

# Palette
BG_COLOR      = (8,   6,  18)
NEON_CYAN     = (0,  255, 240)
NEON_MAGENTA  = (255,  0, 180)
NEON_YELLOW   = (255, 230,   0)
NEON_GREEN    = ( 57, 255,  20)
NEON_ORANGE   = (255, 110,   0)
NEON_PINK     = (255,  60, 120)
WHITE         = (255, 255, 255)
BLACK         = (  0,   0,   0)
DARK_PANEL    = ( 15,  12,  30, 220)   # semi-transparent overlay
MUTED_TEXT    = (180, 170, 210)


# ── CARD LAYOUT ────────────────────────────────────────────────────────────────
# (width, height, x_offset_per_slot, alpha, scale) indexed by abs(slot)
SLOT_STYLE = {
    0: {"w": 300, "h": 360, "alpha": 255, "scale": 1.00},
    1: {"w": 230, "h": 290, "alpha": 170, "scale": 0.85},
    2: {"w": 170, "h": 220, "alpha": 100, "scale": 0.68},
}
SLOT_X_STEP = [0, 310, 245]   # x distance from centre for each abs(slot)


# ── HELPERS ────────────────────────────────────────────────────────────────────
def lerp(a, b, t):
    return a + (b - a) * t


def draw_rounded_rect(surf, color, rect, radius=14, alpha=255):
    """Draw a filled rounded rectangle with optional alpha."""
    tmp = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(tmp, (*color[:3], alpha), (0, 0, rect[2], rect[3]), border_radius=radius)
    surf.blit(tmp, (rect[0], rect[1]))


def draw_text_shadow(surf, text, font, color, x, y, shadow_offset=2, shadow_alpha=160, alpha=255):
    """Render text with a dark drop-shadow for legibility on any background."""
    shadow_surf = font.render(text, True, (0, 0, 0))
    shadow_surf.set_alpha(min(shadow_alpha, alpha))
    surf.blit(shadow_surf, (x + shadow_offset, y + shadow_offset))
    txt_surf = font.render(text, True, color)
    txt_surf.set_alpha(alpha)
    surf.blit(txt_surf, (x, y))
    return txt_surf.get_width()


def parse_color(value, default=(255, 255, 255)):
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("#") and len(value) in (4, 7):
            if len(value) == 4:
                value = "#" + "".join(c * 2 for c in value[1:])
            return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))
        try:
            parts = [int(p) for p in value.split(",")]
            if len(parts) == 3:
                return tuple(parts)
        except Exception:
            return default
    elif isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(int(v) for v in value)
    return default


def load_banner(path):
    if not path:
        return None
    key = os.path.abspath(os.path.join(BASE_DIR, path))
    if key in BANNER_CACHE:
        return BANNER_CACHE[key]
    try:
        surf = pygame.image.load(key).convert()
        BANNER_CACHE[key] = surf
        return surf
    except Exception:
        return None


def load_game_data(data_path):
    if os.path.isfile(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                games = json.load(f)
                if isinstance(games, dict) and "games" in games:
                    games = games["games"]
                if isinstance(games, list):
                    data_dir = os.path.dirname(os.path.abspath(data_path))
                    for game in games:
                        game["accent"] = parse_color(game.get("accent", NEON_CYAN), NEON_CYAN)
                        game["bg"] = parse_color(game.get("bg", (25, 15, 35)), (25, 15, 35))
                        game["programmer"] = game.get("programmer", []) or []
                        game["banner_surf"] = load_banner(game.get("banner"))
                        # After: game["banner_surf"] = load_banner(game.get("banner"))
                        # Add:
                        if game["banner_surf"]:
                            game["banner_surf"] = pygame.transform.scale(
                                game["banner_surf"], (SCREEN_W, SCREEN_H)
                            )
                        game_folder = game.get("start_folder") or game.get("game_folder") or ""
                        game_file = game.get("game_path", "")
                        if game_folder and game_file:
                            abs_path = os.path.abspath(os.path.join(data_dir, game_folder, game_file))
                        elif game_file:
                            abs_path = os.path.abspath(os.path.join(data_dir, game_file))
                        else:
                            abs_path = None
                        game["game_folder"] = game_folder
                        game["game_file"] = game_file
                        game["game_path_abs"] = abs_path
                        game["game_cwd"] = os.path.abspath(os.path.join(data_dir, game_folder)) if game_folder else (os.path.dirname(abs_path) if abs_path else None)
                        game["art_surf"] = load_banner(game.get("art"))   # reuses the same loader
                        if game["art_surf"]:
                            s = SLOT_STYLE[0]
                            game["art_surf"] = pygame.transform.scale(game["art_surf"], (s["w"], s["h"]))
                    return games
        except Exception:
            pass
    print(f"ERROR: Unable to load or parse JSON data from {data_path}")
    return []


def wrap_text(text, font, max_width):
    """Word-wrap text into lines that fit max_width."""
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word])
        if font.size(test)[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def scanline_overlay(surf, line_height=4, alpha=30):
    """Draw subtle CRT scanlines over the whole surface."""
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for y in range(0, surf.get_height(), line_height):
        pygame.draw.line(overlay, (0, 0, 0, alpha), (0, y), (surf.get_width(), y))
    surf.blit(overlay, (0, 0))


def render_card(game, style, selected=False, tick=0):
    """Build a card Surface for a single game entry."""
    w, h = style["w"], style["h"]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # ── Background ────────────────────────────────────────────────────────────
    draw_rounded_rect(surf, game["bg"], (0, 0, w, h), radius=14, alpha=255)

    art = game.get("art_surf")
    if art:
        # Scale art to fill the card (stretch from 300×600 source → card size)
        art_scaled = pygame.transform.scale(art, (w, h))

        # Clip to rounded rect by using a mask surface
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=14)
        art_scaled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(art_scaled, (0, 0))

        # Dark gradient strip at the bottom for the title
        gradient_h = max(38, int(h * 0.22))
        gradient = pygame.Surface((w, gradient_h), pygame.SRCALPHA)
        for row in range(gradient_h):
            alpha = int(200 * (row / gradient_h))
            pygame.draw.line(gradient, (0, 0, 0, alpha), (0, row), (w, row))
        surf.blit(gradient, (0, h - gradient_h))

        # Title over the gradient
        title_size = max(13, int(w * 0.075))
        try:
            font_title = pygame.font.SysFont("couriernew,consolas,monospace", title_size, bold=True)
        except Exception:
            font_title = pygame.font.SysFont(None, title_size)

        pad = 10
        ty = h - font_title.get_height() - pad

    else:
        # ── Fallback: text-only card (original layout) ────────────────────────
        fade = 0.5 * math.sin(tick * 0.03)
        info_alpha = int(200 - 100 * fade)

        title_size = max(14, int(w * 0.078))
        genre_size = max(11, int(w * 0.048))
        label_size = max(10, int(w * 0.042))

        try:
            font_title = pygame.font.SysFont("couriernew,consolas,monospace", title_size, bold=True)
            font_genre = pygame.font.SysFont("arial,helvetica,sans-serif",    genre_size)
            font_label = pygame.font.SysFont("arial,helvetica,sans-serif",    label_size)
        except Exception:
            font_title = pygame.font.SysFont(None, title_size)
            font_genre = pygame.font.SysFont(None, genre_size)
            font_label = pygame.font.SysFont(None, label_size)

        pad = 14
        lines = game["title"].split()
        mid = len(lines) // 2 or 1
        title_lines = [" ".join(lines[:mid]), " ".join(lines[mid:])] if len(lines) > 1 else lines
        ty = pad
        for line in title_lines:
            draw_text_shadow(surf, line, font_title, game["accent"], pad, ty)
            ty += font_title.get_height() + 2

        ty += 6
        pygame.draw.line(surf, (*game["accent"], info_alpha), (pad, ty), (w - pad, ty), 1)
        ty += 8
        draw_text_shadow(surf, game["genre"], font_genre, MUTED_TEXT, pad, ty, shadow_offset=1, alpha=info_alpha)
        ty += font_genre.get_height() + 10

        for person in game.get("programmer", []):
            draw_text_shadow(surf, person, font_label, WHITE, pad + 2, ty, shadow_offset=1, shadow_alpha=100, alpha=info_alpha)
            ty += font_label.get_height() + 4

        if selected:
            stars = "#" * game.get("rating", 0) + "+" * (5 - game.get("rating", 0))
            draw_text_shadow(surf, stars, font_genre, NEON_YELLOW, pad, ty, shadow_offset=1, alpha=info_alpha)
            ty += font_genre.get_height() + 10

        cx2 = pad
        for tag in [game.get("players", ""), game.get("year", "")]:
            if not tag:
                continue
            tw = font_label.size(tag)[0] + 16
            draw_rounded_rect(surf, (255, 255, 255), (cx2, ty, tw, label_size + 10), radius=5, alpha=max(20, info_alpha // 2))
            draw_text_shadow(surf, tag, font_label, WHITE, cx2 + 8, ty + 4, shadow_offset=1, alpha=info_alpha)
            cx2 += tw + 8

    # ── Border (always drawn on top) ──────────────────────────────────────────
    fade = 0.5 * math.sin(tick * 0.03)
    border_alpha = int(200 - 100 * fade) if selected else 80
    border_w = 2 if selected else 1
    pygame.draw.rect(
        surf,
        (*game["accent"], border_alpha),
        (0, 0, w, h),
        width=border_w,
        border_radius=14,
    )

    return surf

def blur_region(screen, rect, scale=0.1):
    x, y, w, h = rect

    # Grab background
    region = screen.subsurface(rect).copy()

    # Downscale then upscale
    small = pygame.transform.smoothscale(
        region,
        (max(1, int(w * scale)), max(1, int(h * scale)))
    )
    blurred = pygame.transform.smoothscale(small, (w, h))

    screen.blit(blurred, (x, y))

# ── INFO PANEL ─────────────────────────────────────────────────────────────────
def draw_info_panel(screen, game, rect, font_title, font_body):
    x, y, w, h = rect
    blur_region(screen, (x,y,w,h), scale=0.08)
    draw_rounded_rect(screen, (*game["accent"], 100), (x, y, w, h), radius=12, alpha=70)
    pygame.draw.rect(screen, (*game["accent"], 100), (x, y, w, h), width=1, border_radius=12)

    pad = 18
    cy = y + pad

    # Title
    draw_text_shadow(screen, game["title"], font_title, game["accent"], x + pad, cy)
    cy += font_title.get_height() + 10

    # Description (word-wrapped)
    lines = wrap_text(game.get("desc", ""), font_body, w - pad * 2)
    for line in lines:
        draw_text_shadow(screen, line, font_body, WHITE, x + pad, cy, shadow_offset=1, shadow_alpha=120)
        cy += font_body.get_height() + 3

    # Programmer credit
    programmers = game.get("programmer", [])
    if programmers:
        cy += 6
        credits = "Entwickelt von: " + ", ".join(programmers)
        draw_text_shadow(screen, credits, font_body, (255,255,255), x + pad, cy, shadow_offset=1, shadow_alpha=120)


def launch_game(game):
    path = game.get("game_path_abs")
    if not path:
        print(f"No game_path defined for {game.get('title', 'unknown')}")
        return
    if not os.path.exists(path):
        print(f"Game path does not exist: {path}")
        return

    cwd = game.get("game_cwd") or os.path.dirname(path)

    try:
        # Close launcher window
        pygame.display.quit()

        if path.lower().endswith(".py"):
            proc = subprocess.Popen(
                [sys.executable, path],
                cwd=cwd,
                close_fds=True,
            )
        elif os.name == "nt":
            proc = subprocess.Popen(
                ["cmd", "/c", "start", "/wait", "", path],
                cwd=cwd,
                shell=False,
            )
        else:
            proc = subprocess.Popen(
                [path],
                cwd=cwd,
                close_fds=True,
            )

        proc.wait()  # Block until the game exits

    except Exception as exc:
        print(f"Failed to launch {path}: {exc}")

    finally:
        # Recreate the display
        pygame.display.init()
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Game Launcher")

        return screen


# ── HEADER ─────────────────────────────────────────────────────────────────────
def draw_header(screen, font_big, font_small, tick):
    title = "WÄHLE EIN SPIEL"
    ts = font_big.render(title, True, WHITE)
    tx = (SCREEN_W - ts.get_width()) // 2
    # Glow effect: draw title twice, slightly blurred by offset
    for dx, dy, a in [(-1, -1, 60), (1, 1, 60), (0, 0, 255)]:
        t = font_big.render(title, True, NEON_CYAN if (dx, dy) == (0, 0) else WHITE)
        t.set_alpha(a)
        screen.blit(t, (tx + dx, 22 + dy))

    # Blinking sub-text
    if (tick // 30) % 2 == 0:
        sub = "◄  DRÜCKE START  ►"
        ss = font_small.render(sub, True, MUTED_TEXT)
        screen.blit(ss, ((SCREEN_W - ss.get_width()) // 2, 58))


# ── CONTROLS HINT ──────────────────────────────────────────────────────────────
def draw_controls(screen, font_small):
    hints = [
        ("◄ ►", "Navigieren"),
        ("*", "Auswählen"),
    ]
    gap = 220
    total = gap * len(hints)
    sx = (SCREEN_W - total) // 2 + gap // 2
    y = SCREEN_H - 50
    for key, label in hints:
        # Key pill
        kw = font_small.size(key)[0] + 20
        draw_rounded_rect(screen, (255, 255, 255), (sx - kw // 2, y - 4, kw, 28), radius=6, alpha=30)
        pygame.draw.rect(screen, (*WHITE, 80), (sx - kw // 2, y - 4, kw, 28), width=1, border_radius=6)
        ks = font_small.render(key, True, WHITE)
        screen.blit(ks, (sx - ks.get_width() // 2, y + 1))
        # Label
        ls = font_small.render(label, True, MUTED_TEXT)
        screen.blit(ls, (sx - ls.get_width() // 2, y + 28))
        sx += gap


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Arcade Game Selection")
    clock = pygame.time.Clock()

    # ── Fonts ──────────────────────────────────────────────────────────────────
    try:
        font_header = pygame.font.SysFont("couriernew,consolas,monospace", 28, bold=True)
        font_sub    = pygame.font.SysFont("arial,helvetica,sans-serif",    15)
        font_info_t = pygame.font.SysFont("couriernew,consolas,monospace", 20, bold=True)
        font_info_b = pygame.font.SysFont("arial,helvetica,sans-serif",    16)
        font_ctrl   = pygame.font.SysFont("couriernew,consolas,monospace", 14, bold=True)
    except Exception:
        font_header = pygame.font.SysFont(None, 28)
        font_sub    = pygame.font.SysFont(None, 15)
        font_info_t = pygame.font.SysFont(None, 20)
        font_info_b = pygame.font.SysFont(None, 16)
        font_ctrl   = pygame.font.SysFont(None, 14)

    games = load_game_data(DATA_JSON)
    if not games:
        print("No game data available. Please fix data.json and restart.")
        pygame.quit()
        sys.exit(1)

    n = len(games)
    current = 0
    anim_offset = 0.0   # fractional slot offset (animates toward 0)
    tick = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        tick += 1

        # ── Events ─────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    current = (current - 1) % n
                    anim_offset += 1.0
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    current = (current + 1) % n
                    anim_offset -= 1.0
                elif event.key == pygame.K_RETURN:
                    selected_game = games[current]
                    print(f"[SELECTED] {selected_game['title']}")
                    # Flash effect
                    flash = pygame.Surface((SCREEN_W, SCREEN_H))
                    flash.fill(selected_game["accent"])
                    flash.set_alpha(80)
                    screen.blit(flash, (0, 0))
                    pygame.display.flip()
                    pygame.time.wait(120)
                    screen = launch_game(selected_game)
                elif event.key == pygame.K_CAPSLOCK:
                    running = False

        # Animate offset toward 0
        anim_offset = lerp(anim_offset, 0.0, min(1.0, CAROUSEL_ANIM_SPEED * dt))
        if abs(anim_offset) < 0.002:
            anim_offset = 0.0

        # ── Draw ───────────────────────────────────────────────────────────────
        screen.fill(BG_COLOR)

        # Background banner from selected game
        active_banner = games[current].get("banner_surf")
        if active_banner:
            active_banner.set_alpha(90)
            screen.blit(active_banner, (0, 0))
            draw_rounded_rect(screen, (0, 0, 0), (0, 0, SCREEN_W, SCREEN_H), radius=0, alpha=70)

        # Subtle background grid lines
        #for gy in range(0, SCREEN_H, 40):
        #    pygame.draw.line(screen, (255, 255, 255, 8), (0, gy), (SCREEN_W, gy))
        #for gx in range(0, SCREEN_W, 80):
        #    pygame.draw.line(screen, (255, 255, 255, 6), (gx, 0), (gx, SCREEN_H))

        draw_header(screen, font_header, font_sub, tick)

        # ── Carousel ───────────────────────────────────────────────────────────
        cx = SCREEN_W // 2
        cy = 120 + 185   # vertical centre of carousel area

        # Draw cards furthest first (back to front)
        render_order = sorted(
            range(n),
            key=lambda i: -abs((((i - current) % n + n) % n
                                + (n // 2 + 1)) % n - (n // 2 + 1) - anim_offset),
        )

        for idx in render_order:
            raw_slot = ((idx - current) % n + n) % n
            if raw_slot > n // 2:
                raw_slot -= n
            slot = raw_slot - anim_offset
            abs_slot = abs(slot)

            if abs_slot > 2.4:
                continue

            # Interpolate style between slot levels
            def interp_style(s):
                lo = int(s)
                hi = lo + 1
                frac = s - lo
                if lo >= 2:
                    return SLOT_STYLE.get(2, SLOT_STYLE[2])
                s0 = SLOT_STYLE.get(lo, SLOT_STYLE[2])
                s1 = SLOT_STYLE.get(hi, SLOT_STYLE[2])
                return {
                    "w": int(lerp(s0["w"], s1["w"], frac)),
                    "h": int(lerp(s0["h"], s1["h"], frac)),
                    "alpha": int(lerp(s0["alpha"], s1["alpha"], frac)),
                    "scale": lerp(s0["scale"], s1["scale"], frac),
                }

            style = interp_style(abs_slot)
            selected = (idx == current and abs(anim_offset) < 0.3)
            card_surf = render_card(games[idx], style, selected, tick)

            # x position
            sign = 1 if slot > 0 else (-1 if slot < 0 else 0)
            x_off = 0
            for lvl in range(1, int(abs_slot) + 1):
                step_idx = min(lvl, len(SLOT_X_STEP) - 1)
                x_off += SLOT_X_STEP[step_idx]
            frac_part = abs_slot % 1
            if int(abs_slot) < len(SLOT_X_STEP) - 1:
                next_step = SLOT_X_STEP[min(int(abs_slot) + 1, len(SLOT_X_STEP) - 1)]
                x_off += frac_part * next_step

            card_x = cx + sign * x_off - style["w"] // 2
            card_y = cy - style["h"] // 2

            card_surf.set_alpha(style["alpha"])
            screen.blit(card_surf, (card_x, card_y))

            # Accent indicator bar below centre card
            if selected:
                bar_w = 60
                bar_x = cx - bar_w // 2
                bar_y = card_y + style["h"] + 10
                pygame.draw.rect(
                    screen,
                    games[current]["accent"],
                    (bar_x, bar_y, bar_w, 4),
                    border_radius=2,
                )

        # ── Info panel ─────────────────────────────────────────────────────────
        panel_h = 120
        panel_y = SCREEN_H - panel_h - 70
        draw_info_panel(
            screen,
            games[current],
            (40, panel_y, SCREEN_W - 80, panel_h),
            font_info_t,
            font_info_b,
        )

        # ── Controls ───────────────────────────────────────────────────────────
        draw_controls(screen, font_ctrl)

        # CRT scanlines
        scanline_overlay(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
