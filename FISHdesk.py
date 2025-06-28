import pygame
import numpy as np
import random
import sys
import os

try:
    import win32api
    import win32con
    import win32gui
    IS_WINDOWS = True
except ImportError:
    IS_WINDOWS = False

# --- 全局配置参数 ---
NUM_POINTS = 13000
TARGET_FPS = 800
DOT_SIZE = 1
PET_COLOR = (250, 240, 240)
TRANSPARENT_COLOR = (1, 1, 1)
PET_SPEED = 0.3
WANDER_STRENGTH = 0.0005

WRAP_AROUND = True      # 是否启用边界穿越
ALWAYS_ON_TOP = True    # 是否窗口置顶
WRAP_MARGIN = 10        # 穿越边界的冗余距离（部分进入/离开效果）
FADE_MARGIN = 60        # alpha 动画触发距离（距离边缘开始淡出/入）


class DesktopPet:
    def __init__(self):
        pygame.init()
        self.screen_info = pygame.display.Info()
        self.screen_width = self.screen_info.current_w
        self.screen_height = self.screen_info.current_h
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.NOFRAME)

        if IS_WINDOWS:
            hwnd = pygame.display.get_wm_info()["window"]
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                   win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
            win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANSPARENT_COLOR), 0, win32con.LWA_COLORKEY)
            if ALWAYS_ON_TOP:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        else:
            self.screen.set_colorkey(TRANSPARENT_COLOR)

        self.clock = pygame.time.Clock()
        self.pet_x = self.screen_width / 2
        self.pet_y = self.screen_height / 2
        self.pet_angle = random.uniform(0, 2 * np.pi)
        self.pet_orientation_angle = self.pet_angle
        self.t = 0
        self.t_step = np.pi / 240
        i = np.arange(NUM_POINTS, 0, -1)
        self.x = i.astype(float)
        self.y = i / 235.0

        self.pet_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.last_wrap = False  # 是否刚刚穿越屏幕

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or \
               (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return False
        return True

    def update_state(self):
        # 如果刚刚穿越，改变方向
        if self.last_wrap:
            self.pet_angle = random.uniform(0, 2 * np.pi)

        # 平滑转向
        angle_diff = self.pet_angle - self.pet_orientation_angle
        angle_diff = (angle_diff + np.pi) % (2 * np.pi) - np.pi
        self.pet_orientation_angle += angle_diff * 0.05  # 惯性调整角度

        # 位移
        self.pet_x += PET_SPEED * np.cos(self.pet_orientation_angle)
        self.pet_y += PET_SPEED * np.sin(self.pet_orientation_angle)

        self.check_bounds()
        self.t += self.t_step

    def draw(self):
        self.screen.fill(TRANSPARENT_COLOR)
        self.pet_surface.fill((0, 0, 0, 0))

        k = (4 + np.sin(self.y * 2 - self.t) * 3) * np.cos(self.x / 29)
        e = self.y / 8 - 13
        d = np.sqrt(k ** 2 + e ** 2)
        q = 3 * np.sin(k * 2) + 0.3 / (k + np.finfo(float).eps) + \
            np.sin(self.y / 25) * k * (9 + 4 * np.sin(e * 9 - d * 3 + self.t * 2))
        c = d - self.t
        local_u = q + 30 * np.cos(c) + 200
        local_v = q * np.sin(c) + 39 * d - 220
        centered_u = local_u - 200
        centered_v = -local_v + 220
        angle_correction = -np.pi / 2
        cos_o = np.cos(self.pet_orientation_angle + angle_correction)
        sin_o = np.sin(self.pet_orientation_angle + angle_correction)
        rotated_u = centered_u * cos_o - centered_v * sin_o
        rotated_v = centered_u * sin_o + centered_v * cos_o
        screen_u = rotated_u + self.pet_x
        screen_v = rotated_v + self.pet_y

        alpha = self.calculate_alpha(self.pet_x, self.pet_y)
        pet_color_with_alpha = (*PET_COLOR, alpha)

        for i in range(NUM_POINTS):
            pygame.draw.circle(self.pet_surface, pet_color_with_alpha, (screen_u[i], screen_v[i]), DOT_SIZE)

        self.screen.blit(self.pet_surface, (0, 0))
        pygame.display.flip()

    def calculate_alpha(self, x, y):
        dist_left = x
        dist_right = self.screen_width - x
        dist_top = y
        dist_bottom = self.screen_height - y
        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)

        if min_dist > FADE_MARGIN:
            return 255
        else:
            alpha = int((min_dist / FADE_MARGIN) * 255)
            return max(0, min(255, alpha))

    def check_bounds(self):
        self.last_wrap = False  # 默认未穿越

        if WRAP_AROUND:
            if self.pet_x < -WRAP_MARGIN:
                self.pet_x = self.screen_width + WRAP_MARGIN
                self.last_wrap = True
            elif self.pet_x > self.screen_width + WRAP_MARGIN:
                self.pet_x = -WRAP_MARGIN
                self.last_wrap = True

            if self.pet_y < -WRAP_MARGIN:
                self.pet_y = self.screen_height + WRAP_MARGIN
                self.last_wrap = True
            elif self.pet_y > self.screen_height + WRAP_MARGIN:
                self.pet_y = -WRAP_MARGIN
                self.last_wrap = True

    def run(self):
        print("Pygame 桌面宠物已启动！")
        print("按 'ESC' 键来退出。")
        running = True
        while running:
            running = self.handle_events()
            self.update_state()
            self.draw()
            self.clock.tick(TARGET_FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    pet = DesktopPet()
    pet.run()