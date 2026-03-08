import pygame
import math
import random
import sys
import json
import os
import socket

pygame.init()

# Get the actual screen size of the mobile device
screen_info = pygame.display.Info()
WIDTH = screen_info.current_w
HEIGHT = screen_info.current_h

# Set fullscreen mode for Android
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("Crown Battle: Mobile Sniper")

clock = pygame.time.Clock()

# --- SCALING HELPERS & FONTS ---
SCALE = min(WIDTH, HEIGHT)
FONT_TITLE = pygame.font.SysFont(None, int(SCALE * 0.12))
FONT_LARGE = pygame.font.SysFont(None, int(SCALE * 0.08))
FONT_MED = pygame.font.SysFont(None, int(SCALE * 0.06))
FONT_SMALL = pygame.font.SysFont(None, int(SCALE * 0.04))
FONT_TINY = pygame.font.SysFont(None, int(SCALE * 0.03))

# --- COLORS ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 80, 80)
BLUE = (80, 140, 255)
GREEN = (60, 200, 60)
YELLOW = (255, 220, 0)
BROWN = (140, 90, 40)
DARK_ORANGE = (204, 85, 0)
DARK_BLUE = (0, 0, 139)
PURPLE = (128, 0, 128)
DEADLIEST = (30, 5, 5)

gravity = 0.7
PLAYER_SPEED = 5

game_state = "menu"
play_mode = "bot" # Can be "bot", "alone", "lan_host", "lan_client"
dragged_item = None
respawn_timer = 0 

particles = []
bricks = []

# ---------------- SAVE/LOAD SYSTEM ----------------
def get_save_path():
    if 'ANDROID_PRIVATE' in os.environ:
        return os.path.join(os.environ['ANDROID_PRIVATE'], "crown_save.json")
    return "crown_save.json"

SAVE_FILE = get_save_path()

# Default UI positions as percentages of screen (x, y)
DEFAULT_UI = {
    "move_joy": [0.15, 0.8],
    "aim_joy": [0.85, 0.8],
    "jump_btn": [0.85, 0.6],
    "dash_btn": [0.85, 0.45],
    "brick_h": [0.15, 0.55],
    "brick_v": [0.25, 0.55]
}

def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                color = tuple(data.get("color", BLUE))
                ui = data.get("ui_layout", DEFAULT_UI)
                return data.get("crowns", 0), color, ui
        except:
            return 0, BLUE, DEFAULT_UI
    return 0, BLUE, DEFAULT_UI

def save_data(c, col, ui_elements):
    ui_layout = {
        "move_joy": [ui_elements['move_joy'].base.x / WIDTH, ui_elements['move_joy'].base.y / HEIGHT],
        "aim_joy": [ui_elements['aim_joy'].base.x / WIDTH, ui_elements['aim_joy'].base.y / HEIGHT],
        "jump_btn": [ui_elements['jump_btn'].centerx / WIDTH, ui_elements['jump_btn'].centery / HEIGHT],
        "dash_btn": [ui_elements['dash_btn'].centerx / WIDTH, ui_elements['dash_btn'].centery / HEIGHT],
        "brick_h": [ui_elements['brick_h'].centerx / WIDTH, ui_elements['brick_h'].centery / HEIGHT],
        "brick_v": [ui_elements['brick_v'].centerx / WIDTH, ui_elements['brick_v'].centery / HEIGHT]
    }
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump({"crowns": c, "color": col, "ui_layout": ui_layout}, f)
    except Exception as e:
        print(f"Save failed: {e}")

crowns, player_color, ui_layout = load_data()

# ---------------- CONTROLS ----------------
class Joystick:
    def __init__(self, x, y, radius):
        self.base = pygame.Vector2(x, y)
        self.pos = pygame.Vector2(x, y)
        self.radius = radius
        self.active = False
        self.value = pygame.Vector2(0, 0)
        self.angle = 0
        self.just_released = False

    def handle_event(self, event):
        self.just_released = False
        ex, ey = None, None
        is_down, is_up, is_motion = False, False, False

        if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
            is_down = True
            if event.type == pygame.FINGERDOWN:
                ex, ey = event.x * WIDTH, event.y * HEIGHT
            else:
                ex, ey = event.pos
                
        elif event.type == pygame.MOUSEMOTION or event.type == pygame.FINGERMOTION:
            is_motion = True
            if event.type == pygame.FINGERMOTION:
                ex, ey = event.x * WIDTH, event.y * HEIGHT
            else:
                ex, ey = event.pos

        elif event.type == pygame.MOUSEBUTTONUP or event.type == pygame.FINGERUP:
            is_up = True

        if is_down and ex is not None:
            if pygame.Vector2(ex, ey).distance_to(self.base) < self.radius:
                self.active = True
                
        elif is_motion and self.active and ex is not None:
            vec = pygame.Vector2(ex, ey) - self.base
            if vec.length() > 0:
                self.angle = math.atan2(vec.y, vec.x)
            if vec.length() > self.radius:
                vec.scale_to_length(self.radius)
            self.pos = self.base + vec
            self.value = vec / self.radius
            
        elif is_up and self.active:
            self.active = False
            self.just_released = True
            self.pos = self.base
            self.value = pygame.Vector2(0, 0)

    def draw(self, screen):
        pygame.draw.circle(screen, (90, 90, 90), self.base, self.radius, 3)
        pygame.draw.circle(screen, (200, 200, 200), self.pos, int(self.radius * 0.3))

JOY_RAD = int(SCALE * 0.12)
BTN_SIZE = int(SCALE * 0.12)

move_joystick = Joystick(WIDTH * ui_layout["move_joy"][0], HEIGHT * ui_layout["move_joy"][1], JOY_RAD)
aim_joystick = Joystick(WIDTH * ui_layout["aim_joy"][0], HEIGHT * ui_layout["aim_joy"][1], JOY_RAD)
exit_button = pygame.Rect(20, 20, int(SCALE*0.18), int(SCALE*0.08))
jump_button = pygame.Rect(0, 0, BTN_SIZE, BTN_SIZE)
jump_button.center = (WIDTH * ui_layout["jump_btn"][0], HEIGHT * ui_layout["jump_btn"][1])

dash_button = pygame.Rect(0, 0, BTN_SIZE, BTN_SIZE)
dash_button.center = (WIDTH * ui_layout["dash_btn"][0], HEIGHT * ui_layout["dash_btn"][1])

brick_h_btn = pygame.Rect(0, 0, BTN_SIZE, BTN_SIZE)
brick_h_btn.center = (WIDTH * ui_layout["brick_h"][0], HEIGHT * ui_layout["brick_h"][1])

brick_v_btn = pygame.Rect(0, 0, BTN_SIZE, BTN_SIZE)
brick_v_btn.center = (WIDTH * ui_layout["brick_v"][0], HEIGHT * ui_layout["brick_v"][1])

def get_current_ui():
    return {
        "move_joy": move_joystick, "aim_joy": aim_joystick,
        "jump_btn": jump_button, "dash_btn": dash_button,
        "brick_h": brick_h_btn, "brick_v": brick_v_btn
    }

def draw_centered_text(surface, text, rect, font, color=BLACK):
    txt_surf = font.render(text, True, color)
    surface.blit(txt_surf, (rect.centerx - txt_surf.get_width()//2, rect.centery - txt_surf.get_height()//2))

def draw_3d_button(surface, rect, color, text, font, text_color=WHITE):
    """Draws a nice 3D looking button for the mobile menu"""
    shadow_rect = pygame.Rect(rect.x, rect.y + 6, rect.width, rect.height)
    darker_color = (max(0, color[0]-50), max(0, color[1]-50), max(0, color[2]-50))
    pygame.draw.rect(surface, darker_color, shadow_rect, border_radius=12)
    pygame.draw.rect(surface, color, rect, border_radius=12)
    draw_centered_text(surface, text, rect, font, text_color)

# ---------------- PARTICLES ----------------
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dx = random.uniform(-3, 3)
        self.dy = random.uniform(-3, 3)
        self.life = random.randint(15, 25)
        self.size = random.randint(2, 4)

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.life -= 1

    def draw(self):
        pygame.draw.circle(screen, (255, 80, 80), (int(self.x), int(self.y)), self.size)

# ---------------- PLAYER ----------------
class Player:
    def __init__(self, x, y):
        self.dash_cd = 0
        self.dash_frames = 0
        self.dash_speed = 0
        self.sniper_cd = 0
        self.rect = pygame.Rect(x, y, int(SCALE*0.04), int(SCALE*0.06))
        self.vel_y = 0
        self.on_ground = False
        self.health = 100
        self.bullets = []
        self.hit_timer = 0
        self.facing = 1

    def dash(self, direction):
        if self.dash_cd == 0:
            self.dash_frames = 10 
            self.dash_speed = direction * 15 
            self.dash_cd = 300 

    def move(self):
        if self.dash_frames > 0:
            dx = self.dash_speed
            self.dash_frames -= 1
        else:
            dx = move_joystick.value.x * PLAYER_SPEED
        
        if dx > 0: self.facing = 1
        elif dx < 0: self.facing = -1

        self.vel_y += gravity
        dy = self.vel_y

        self.rect.x += dx
        self.rect.y += dy

        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > WIDTH: self.rect.right = WIDTH

        if self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y = 0
            self.on_ground = True

        for brick in bricks:
            if self.rect.colliderect(brick.rect) and self.vel_y > 0:
                self.rect.bottom = brick.rect.top
                self.vel_y = 0
                self.on_ground = True

        if self.dash_cd > 0: self.dash_cd -= 1
        if self.sniper_cd > 0: self.sniper_cd -= 1

    def shoot_sniper(self, angle):
        if self.sniper_cd == 0:
            speed = 28
            bullet = {
                "x": self.rect.centerx,
                "y": self.rect.centery,
                "dx": math.cos(angle) * speed,
                "dy": math.sin(angle) * speed
            }
            self.bullets.append(bullet)
            self.sniper_cd = 45

    def update_bullets(self):
        new = []
        for b in self.bullets:
            b["x"] += b["dx"]
            b["y"] += b["dy"]
            hit = False
            for brick in bricks:
                if brick.rect.collidepoint(b["x"], b["y"]): hit = True
            if not hit and 0 < b["x"] < WIDTH and 0 < b["y"] < HEIGHT:
                new.append(b)
        self.bullets = new

    def draw(self):
        color = RED if self.hit_timer > 0 else player_color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        
        outline = RED if player_color == DEADLIEST else BLACK
        pygame.draw.rect(screen, outline, self.rect, 2, border_radius=8)
        
        hbar_w = self.rect.width
        pygame.draw.rect(screen, BLACK, (self.rect.x, self.rect.y - 10, hbar_w, 6), border_radius=3)
        pygame.draw.rect(screen, GREEN, (self.rect.x, self.rect.y - 10, hbar_w * (max(0, self.health) / 100), 6), border_radius=3)

        if aim_joystick.active:
            end_x = self.rect.centerx + math.cos(aim_joystick.angle) * 800
            end_y = self.rect.centery + math.sin(aim_joystick.angle) * 800
            pygame.draw.line(screen, (255, 0, 0, 100), self.rect.center, (end_x, end_y), 2)

        for b in self.bullets:
            tracer_end = (int(b["x"] - b["dx"]*0.5), int(b["y"] - b["dy"]*0.5))
            pygame.draw.line(screen, WHITE, (int(b["x"]), int(b["y"])), tracer_end, 3)
            pygame.draw.circle(screen, YELLOW, (int(b["x"]), int(b["y"])), 4)

        if self.hit_timer > 0: self.hit_timer -= 1

# ---------------- ENEMY / MULTIPLAYER OPPONENT ----------------
class AIEnemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, int(SCALE*0.04), int(SCALE*0.06))
        self.vel_y = 0
        self.on_ground = False
        self.health = 100
        self.bullets = []
        self.shoot_timer = 0
        self.hit_timer = 0

    def update(self, player):
        dx = -2.5 if player.rect.x < self.rect.x else 2.5
        if random.randint(0, 100) < 2 and self.on_ground:
            self.vel_y = -11
            self.on_ground = False
            
        self.vel_y += gravity
        dy = self.vel_y
        
        self.rect.x += dx
        self.rect.y += dy

        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > WIDTH: self.rect.right = WIDTH

        if self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y = 0
            self.on_ground = True

        for brick in bricks:
            if self.rect.colliderect(brick.rect) and self.vel_y > 0:
                self.rect.bottom = brick.rect.top
                self.vel_y = 0
                self.on_ground = True

        self.shoot_timer += 1
        if self.shoot_timer > 60:
            bdx = player.rect.centerx - self.rect.centerx
            bdy = player.rect.centery - self.rect.centery
            angle = math.atan2(bdy, bdx)
            bullet = {
                "x": self.rect.centerx,
                "y": self.rect.centery,
                "dx": math.cos(angle) * 11,
                "dy": math.sin(angle) * 11
            }
            self.bullets.append(bullet)
            self.shoot_timer = 0

    def update_bullets(self):
        new = []
        for b in self.bullets:
            b["x"] += b["dx"]
            b["y"] += b["dy"]
            hit = False
            for brick in bricks:
                if brick.rect.collidepoint(b["x"], b["y"]): hit = True
            if not hit and 0 < b["x"] < WIDTH and 0 < b["y"] < HEIGHT:
                new.append(b)
        self.bullets = new

    def draw(self):
        color = (255, 120, 120) if self.hit_timer > 0 else RED
        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        hbar_w = self.rect.width
        pygame.draw.rect(screen, BLACK, (self.rect.x, self.rect.y - 8, hbar_w, 5))
        pygame.draw.rect(screen, GREEN, (self.rect.x, self.rect.y - 8, hbar_w * (max(0, self.health) / 100), 5))

        for b in self.bullets:
            pygame.draw.circle(screen, (255, 200, 50), (int(b["x"]), int(b["y"])), 5)
            pygame.draw.circle(screen, (255, 255, 255), (int(b["x"]), int(b["y"])), 2)

        if self.hit_timer > 0: self.hit_timer -= 1

# ---------------- BRICKS ----------------
class Brick:
    def __init__(self, x, y, mode):
        bw = int(SCALE * 0.1)
        bh = int(SCALE * 0.025)
        if mode == "H": self.rect = pygame.Rect(x, y, bw, bh)
        else: self.rect = pygame.Rect(x, y, bh, bw)
        self.timer = 360

    def update(self): self.timer -= 1
    def draw(self): pygame.draw.rect(screen, BROWN, self.rect, border_radius=4)

def spawn_crown():
    x = random.randint(int(WIDTH*0.1), int(WIDTH*0.9))
    y = random.randint(int(HEIGHT*0.1), int(HEIGHT*0.7))
    return pygame.Rect(x, y, int(SCALE*0.06), int(SCALE*0.05))

player = Player(WIDTH * 0.2, HEIGHT - 100)
enemy = AIEnemy(WIDTH * 0.8, HEIGHT - 100)
crown = spawn_crown()

# ---------------- LOOP ----------------
while True:
    clock.tick(60)
    
    # -------- MENU --------
    if game_state == "menu":
        screen.fill((20, 20, 30))
        title = FONT_TITLE.render("CROWN BATTLE", True, WHITE)
        crown_txt = FONT_MED.render(f"CROWNS: {crowns}", True, YELLOW)
        
        btn_w = int(WIDTH * 0.45)
        btn_h = int(HEIGHT * 0.08)
        start_y = HEIGHT * 0.35
        spacing = btn_h * 1.4
        
        # UI Button Layout
        col1_x = WIDTH//2 - btn_w - 10
        col2_x = WIDTH//2 + 10

        bot_btn = pygame.Rect(col1_x, start_y, btn_w, btn_h)
        alone_btn = pygame.Rect(col2_x, start_y, btn_w, btn_h)
        lan_btn = pygame.Rect(WIDTH//2 - btn_w//2, start_y + spacing, btn_w, btn_h)
        store_btn = pygame.Rect(col1_x, start_y + spacing*2, btn_w, btn_h)
        cust_btn = pygame.Rect(col2_x, start_y + spacing*2, btn_w, btn_h)
        quit_btn = pygame.Rect(WIDTH//2 - btn_w//2, start_y + spacing*3.2, btn_w, btn_h)

        # Draw Buttons with 3D Effect
        draw_3d_button(screen, bot_btn, (220, 60, 60), "VS BOT", FONT_MED)
        draw_3d_button(screen, alone_btn, (60, 200, 60), "ALONE", FONT_MED)
        draw_3d_button(screen, lan_btn, (80, 140, 255), "1v1 LAN", FONT_MED)
        draw_3d_button(screen, store_btn, (200, 180, 40), "STORE", FONT_MED)
        draw_3d_button(screen, cust_btn, (140, 90, 200), "EDIT UI", FONT_MED)
        draw_3d_button(screen, quit_btn, (100, 100, 100), "QUIT", FONT_MED)

        screen.blit(title, (WIDTH // 2 - title.get_width()//2, HEIGHT * 0.08))
        screen.blit(crown_txt, (WIDTH // 2 - crown_txt.get_width()//2, HEIGHT * 0.20))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
                mx, my = event.pos if event.type == pygame.MOUSEBUTTONDOWN else (event.x * WIDTH, event.y * HEIGHT)
                if bot_btn.collidepoint(mx, my): 
                    play_mode = "bot"
                    game_state = "game"
                if alone_btn.collidepoint(mx, my): 
                    play_mode = "alone"
                    game_state = "game"
                
                if lan_btn.collidepoint(mx, my): 
                    game_state = "lan_menu"
                if store_btn.collidepoint(mx, my): game_state = "store"
                if cust_btn.collidepoint(mx, my): game_state = "customize"
                if quit_btn.collidepoint(mx, my): pygame.quit(); sys.exit()
                
        pygame.display.update()
        continue

    # -------- LAN MENU --------
    if game_state == "lan_menu":
        screen.fill((20, 20, 30))
        title = FONT_LARGE.render("LAN MULTIPLAYER", True, WHITE)
        info = FONT_SMALL.render("Connect to same WiFi / Hotspot", True, YELLOW)
        
        btn_w = int(WIDTH * 0.4)
        btn_h = int(HEIGHT * 0.1)
        
        host_btn = pygame.Rect(WIDTH//2 - btn_w//2, HEIGHT * 0.4, btn_w, btn_h)
        join_btn = pygame.Rect(WIDTH//2 - btn_w//2, HEIGHT * 0.55, btn_w, btn_h)
        back_btn = pygame.Rect(WIDTH * 0.05, HEIGHT * 0.05, int(WIDTH * 0.15), int(HEIGHT * 0.08))

        draw_3d_button(screen, host_btn, (60, 200, 60), "HOST GAME", FONT_MED)
        draw_3d_button(screen, join_btn, (80, 140, 255), "JOIN GAME", FONT_MED)
        draw_3d_button(screen, back_btn, (100, 100, 100), "BACK", FONT_SMALL)

        screen.blit(title, (WIDTH // 2 - title.get_width()//2, HEIGHT * 0.15))
        screen.blit(info, (WIDTH // 2 - info.get_width()//2, HEIGHT * 0.25))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
                mx, my = event.pos if event.type == pygame.MOUSEBUTTONDOWN else (event.x * WIDTH, event.y * HEIGHT)
                if back_btn.collidepoint(mx, my): 
                    game_state = "menu"
                if host_btn.collidepoint(mx, my):
                    # Placeholder: Start Host Server
                    play_mode = "lan_host"
                    game_state = "game"
                if join_btn.collidepoint(mx, my):
                    # Placeholder: Scan for Host
                    play_mode = "lan_client"
                    game_state = "game"

        pygame.display.update()
        continue

    # -------- STORE --------
    if game_state == "store":
        screen.fill((20, 20, 30))
        title = FONT_LARGE.render("CROWN STORE", True, YELLOW)
        crown_txt = FONT_MED.render(f"YOUR CROWNS: {crowns}", True, WHITE)
        
        screen.blit(title, (WIDTH // 2 - title.get_width()//2, HEIGHT * 0.1))
        screen.blit(crown_txt, (WIDTH // 2 - crown_txt.get_width()//2, HEIGHT * 0.2))

        btn_w = int(WIDTH * 0.35)
        btn_h = int(HEIGHT * 0.12)
        
        b_default = pygame.Rect(WIDTH * 0.1, HEIGHT * 0.35, btn_w, btn_h)
        b_orange = pygame.Rect(WIDTH * 0.55, HEIGHT * 0.35, btn_w, btn_h)
        b_blue = pygame.Rect(WIDTH * 0.1, HEIGHT * 0.55, btn_w, btn_h)
        b_purple = pygame.Rect(WIDTH * 0.55, HEIGHT * 0.55, btn_w, btn_h)
        b_deadly = pygame.Rect(WIDTH // 2 - btn_w//2, HEIGHT * 0.75, btn_w, btn_h)
        b_back = pygame.Rect(WIDTH * 0.05, HEIGHT * 0.05, int(WIDTH * 0.15), int(HEIGHT * 0.08))

        draw_3d_button(screen, b_default, BLUE, "Default Blue", FONT_SMALL)
        draw_3d_button(screen, b_orange, DARK_ORANGE, "Orange (1 C)", FONT_SMALL)
        draw_3d_button(screen, b_blue, DARK_BLUE, "Dark Blue (20 C)", FONT_SMALL)
        draw_3d_button(screen, b_purple, PURPLE, "Toxic (50 C)", FONT_SMALL)
        draw_3d_button(screen, b_deadly, DEADLIEST, "DEADLY (100 C)", FONT_SMALL, RED)
        draw_3d_button(screen, b_back, (100, 100, 100), "BACK", FONT_SMALL)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
                mx, my = event.pos if event.type == pygame.MOUSEBUTTONDOWN else (event.x * WIDTH, event.y * HEIGHT)
                if b_back.collidepoint(mx, my): game_state = "menu"
                
                ui_state = get_current_ui()
                if b_default.collidepoint(mx, my): 
                    player_color = BLUE; save_data(crowns, player_color, ui_state)
                if b_orange.collidepoint(mx, my) and crowns >= 1: 
                    player_color = DARK_ORANGE; save_data(crowns, player_color, ui_state)
                if b_blue.collidepoint(mx, my) and crowns >= 20: 
                    player_color = DARK_BLUE; save_data(crowns, player_color, ui_state)
                if b_purple.collidepoint(mx, my) and crowns >= 50: 
                    player_color = PURPLE; save_data(crowns, player_color, ui_state)
                if b_deadly.collidepoint(mx, my) and crowns >= 100: 
                    player_color = DEADLIEST; save_data(crowns, player_color, ui_state)

        pygame.display.update()
        continue

    # -------- CUSTOMIZE UI --------
    if game_state == "customize":
        screen.fill((40, 40, 50))
        title = FONT_MED.render("DRAG ITEMS TO CUSTOMIZE LAYOUT", True, WHITE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT * 0.05))
        
        b_save = pygame.Rect(WIDTH//2 - int(WIDTH*0.1), HEIGHT * 0.85, int(WIDTH*0.2), int(HEIGHT*0.1))
        draw_3d_button(screen, b_save, GREEN, "SAVE", FONT_MED, BLACK)

        move_joystick.draw(screen)
        aim_joystick.draw(screen)
        pygame.draw.rect(screen, (160, 160, 160), jump_button, border_radius=10)
        pygame.draw.rect(screen, (160, 160, 160), dash_button, border_radius=10)
        pygame.draw.rect(screen, BROWN, brick_h_btn, border_radius=10)
        pygame.draw.rect(screen, BROWN, brick_v_btn, border_radius=10)
        
        draw_centered_text(screen, "JUMP", jump_button, FONT_TINY, BLACK)
        draw_centered_text(screen, "DASH", dash_button, FONT_TINY, BLACK)
        draw_centered_text(screen, "H-BRK", brick_h_btn, FONT_TINY, WHITE)
        draw_centered_text(screen, "V-BRK", brick_v_btn, FONT_TINY, WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
                mx, my = event.pos if event.type == pygame.MOUSEBUTTONDOWN else (event.x * WIDTH, event.y * HEIGHT)
                if b_save.collidepoint(mx, my): 
                    save_data(crowns, player_color, get_current_ui())
                    game_state = "menu"
                elif jump_button.collidepoint(mx, my): dragged_item = jump_button
                elif dash_button.collidepoint(mx, my): dragged_item = dash_button
                elif brick_h_btn.collidepoint(mx, my): dragged_item = brick_h_btn
                elif brick_v_btn.collidepoint(mx, my): dragged_item = brick_v_btn
                elif math.hypot(mx - move_joystick.base.x, my - move_joystick.base.y) < move_joystick.radius:
                    dragged_item = move_joystick
                elif math.hypot(mx - aim_joystick.base.x, my - aim_joystick.base.y) < aim_joystick.radius:
                    dragged_item = aim_joystick

            elif event.type == pygame.MOUSEMOTION or event.type == pygame.FINGERMOTION:
                mx, my = event.pos if event.type == pygame.MOUSEMOTION else (event.x * WIDTH, event.y * HEIGHT)
                if dragged_item:
                    if isinstance(dragged_item, pygame.Rect):
                        dragged_item.center = (mx, my)
                    else: # Joystick
                        dragged_item.base = pygame.Vector2(mx, my)
                        dragged_item.pos = pygame.Vector2(mx, my)

            elif event.type == pygame.MOUSEBUTTONUP or event.type == pygame.FINGERUP:
                dragged_item = None

        pygame.display.update()
        continue
 
    # -------- WIN SCREEN --------
    if game_state == "win":
        screen.fill((20, 20, 30))
        text = FONT_LARGE.render("YOU GOT THE CROWN!", True, WHITE)
        
        btn_w = int(WIDTH * 0.25)
        btn_h = int(HEIGHT * 0.1)
        btn_restart = pygame.Rect(WIDTH//2 - btn_w - 20, HEIGHT * 0.5, btn_w, btn_h)
        btn_menu = pygame.Rect(WIDTH//2 + 20, HEIGHT * 0.5, btn_w, btn_h)

        draw_3d_button(screen, btn_restart, GREEN, "RESTART", FONT_MED, BLACK)
        draw_3d_button(screen, btn_menu, (100, 100, 100), "MENU", FONT_MED, WHITE)

        screen.blit(text, (WIDTH // 2 - text.get_width()//2, HEIGHT * 0.3))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
                mx, my = event.pos if event.type == pygame.MOUSEBUTTONDOWN else (event.x * WIDTH, event.y * HEIGHT)
                
                if btn_restart.collidepoint(mx, my) or btn_menu.collidepoint(mx, my):
                    player.rect.x, player.rect.y = WIDTH * 0.2, HEIGHT - 100
                    player.health = 100
                    enemy.rect.x, enemy.rect.y = WIDTH * 0.8, HEIGHT - 100
                    enemy.health = 100
                    bricks.clear(); particles.clear()
                    crown = spawn_crown()
                    
                    if btn_restart.collidepoint(mx, my): game_state = "game"
                    else: game_state = "menu"

        pygame.display.update()
        continue

    # -------- DEATH SCREEN --------
    if game_state == "dead":
        screen.fill((40, 10, 10))
        text = FONT_LARGE.render("YOU DIED", True, RED)
        
        seconds_left = math.ceil(respawn_timer / 60)
        timer_text = FONT_MED.render(f"RESPAWNING IN {seconds_left}...", True, WHITE)
        
        screen.blit(text, (WIDTH // 2 - text.get_width()//2, HEIGHT * 0.3))
        screen.blit(timer_text, (WIDTH // 2 - timer_text.get_width()//2, HEIGHT * 0.5))

        respawn_timer -= 1
        
        if respawn_timer <= 0:
            player.health = 100
            player.rect.x, player.rect.y = WIDTH * 0.2, HEIGHT - 100
            enemy.rect.x, enemy.rect.y = WIDTH * 0.8, HEIGHT - 100
            enemy.health = 100
            bricks.clear(); particles.clear()
            game_state = "game"

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

        pygame.display.update()
        continue


    # -------- GAME EVENTS --------
    for event in pygame.event.get():
        move_joystick.handle_event(event)
        aim_joystick.handle_event(event)

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
            if event.type == pygame.FINGERDOWN:
                tx, ty = event.x * WIDTH, event.y * HEIGHT
            else:
                tx, ty = event.pos
            
            if jump_button.collidepoint(tx, ty):
                if player.on_ground:
                    player.vel_y = -12
                    player.on_ground = False 
                    
            elif dash_button.collidepoint(tx, ty):
                player.dash(player.facing)
                
            elif brick_h_btn.collidepoint(tx, ty):
                bw = int(SCALE * 0.1)
                bx = player.rect.centerx + (player.facing * bw) - (bw//2)
                by = player.rect.bottom - int(SCALE * 0.025)
                bricks.append(Brick(bx, by, "H"))

            elif brick_v_btn.collidepoint(tx, ty):
                bw = int(SCALE * 0.1)
                bx = player.rect.centerx + (player.facing * (bw-10)) - 9
                by = player.rect.centery - (bw//2)
                bricks.append(Brick(bx, by, "V"))

    if aim_joystick.just_released:
        player.shoot_sniper(aim_joystick.angle)

    # UPDATE
    player.move()
    player.update_bullets()

    # ONLY UPDATE ENEMY IF NOT IN ALONE MODE
    if play_mode != "alone":
        if play_mode == "bot":
            enemy.update(player)
        elif play_mode in ["lan_host", "lan_client"]:
            pass # Network Sync Logic Goes Here in the Future
            
        enemy.update_bullets()

        for b in player.bullets:
            if enemy.rect.collidepoint(b["x"], b["y"]):
                enemy.health -= 50  
                enemy.hit_timer = 10
                for i in range(25): 
                    particles.append(Particle(b["x"], b["y"]))
                b["x"] = -100 

        for b in enemy.bullets:
            if player.rect.collidepoint(b["x"], b["y"]):
                player.health -= 50
                player.hit_timer = 10
                for i in range(25):
                    particles.append(Particle(b["x"], b["y"]))
                b["x"] = -100
                
        if enemy.health <= 0:
            enemy.rect.x = random.randint(int(WIDTH*0.2), int(WIDTH*0.8))
            enemy.rect.y = HEIGHT - 100
            enemy.health = 100

    for p in particles: p.update()
    particles = [p for p in particles if p.life > 0]

    for brick in bricks: brick.update()
    bricks = [b for b in bricks if b.timer > 0]

    # Trigger Death Countdown
    if player.health <= 0 and game_state == "game":
        game_state = "dead"
        respawn_timer = 120 
        move_joystick.active = False
        aim_joystick.active = False

    if player.rect.colliderect(crown):
        crowns += 1
        save_data(crowns, player_color, get_current_ui())
        game_state = "win"

    # DRAW
    screen.fill((30, 30, 40))

    # --- DRAW THE PREMIUM CROWN ---
    crown_draw_y = crown.y + math.sin(pygame.time.get_ticks() * 0.005) * 8
    glow_size = int(SCALE * 0.03) + math.sin(pygame.time.get_ticks() * 0.01) * 5
    glow_rect = crown.inflate(glow_size, glow_size)
    pygame.draw.ellipse(screen, (80, 70, 0), glow_rect) 
    pygame.draw.ellipse(screen, (130, 110, 0), crown.inflate(5, 5)) 

    cw_h = crown.width // 2
    pts = [
        (crown.left, crown_draw_y + 15),          
        (crown.left - 5, crown_draw_y - 5),       
        (crown.left + cw_h//2, crown_draw_y + 8),      
        (crown.left + cw_h, crown_draw_y - 12),     
        (crown.centerx, crown_draw_y + 5),        
        (crown.right - cw_h, crown_draw_y - 12),    
        (crown.right - cw_h//2, crown_draw_y + 8),     
        (crown.right + 5, crown_draw_y - 5),      
        (crown.right, crown_draw_y + 15),         
    ]
    pygame.draw.polygon(screen, (255, 215, 0), pts)
    pygame.draw.rect(screen, (218, 165, 32), (crown.x, crown_draw_y + 15, crown.width, 15), border_radius=3) 
    pygame.draw.line(screen, WHITE, (crown.left + 5, crown_draw_y + 15), (crown.left, crown_draw_y), 2)
    pygame.draw.lines(screen, BLACK, True, pts, 2)
    pygame.draw.rect(screen, BLACK, (crown.x, crown_draw_y + 15, crown.width, 15), 2, border_radius=3)
    pygame.draw.circle(screen, RED, (crown.centerx, int(crown_draw_y + 22)), 6)
    pygame.draw.circle(screen, (255, 100, 100), (crown.centerx - 2, int(crown_draw_y + 20)), 2)
    pygame.draw.circle(screen, BLUE, (crown.left + 10, int(crown_draw_y + 22)), 3)
    pygame.draw.circle(screen, BLUE, (crown.right - 10, int(crown_draw_y + 22)), 3)

    player.draw()
    
    # ONLY DRAW ENEMY IF NOT IN ALONE MODE
    if play_mode != "alone":
        enemy.draw()

    for brick in bricks: brick.draw()
    for p in particles: p.draw()

    # JOYSTICKS & MOBILE BUTTONS
    move_joystick.draw(screen)
    aim_joystick.draw(screen)

    dash_color = (80, 80, 80) if player.dash_cd > 0 else (160, 160, 160)
    
    pygame.draw.rect(screen, (160, 160, 160), jump_button, border_radius=10)
    pygame.draw.rect(screen, dash_color, dash_button, border_radius=10)
    pygame.draw.rect(screen, BROWN, brick_h_btn, border_radius=10)
    pygame.draw.rect(screen, BROWN, brick_v_btn, border_radius=10)

    draw_centered_text(screen, "JUMP", jump_button, FONT_TINY, BLACK)
    draw_centered_text(screen, "DASH", dash_button, FONT_TINY, WHITE if player.dash_cd > 0 else BLACK)
    draw_centered_text(screen, "H-BRK", brick_h_btn, FONT_TINY, WHITE)
    draw_centered_text(screen, "V-BRK", brick_v_btn, FONT_TINY, WHITE)

    pygame.display.update()