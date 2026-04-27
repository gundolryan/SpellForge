import cv2
import numpy as np
import math
import time
import random


class EnemyBullet:
    SPEED = 5.0

    def __init__(self, pos, target_pos):
        self.pos = np.array(pos, dtype=float)
        direction = np.array(target_pos, dtype=float) - self.pos
        norm = np.linalg.norm(direction)
        self.vel = direction / norm * self.SPEED if norm > 0 else np.array([0, 1], dtype=float)
        self.alive = True
        self.blocked_time = None

    def update(self, center):
        if not self.alive:
            return False
        self.pos += self.vel
        return np.linalg.norm(self.pos - np.array(center, dtype=float)) < 30

    def check_shield(self, shield_center, shield_radius):
        if shield_center is None:
            return False
        return np.linalg.norm(self.pos - np.array(shield_center, dtype=float)) < shield_radius

    def draw(self, frame, t):
        cx, cy = int(self.pos[0]), int(self.pos[1])

        if self.blocked_time is not None:
            elapsed = time.time() - self.blocked_time
            if elapsed < 0.3:
                alpha = 1.0 - elapsed / 0.3
                r = int(14 * (1 + elapsed * 5))
                ov = frame.copy()
                cv2.circle(ov, (cx, cy), r, (200, 120, 20), -1)
                cv2.addWeighted(ov, alpha * 0.6, frame, 1 - alpha * 0.6, 0, frame)
            return

        # Pulsing red energy bolt
        pulse = 0.7 + 0.3 * math.sin(t * 20)
        r = int(10 * pulse)
        ov = frame.copy()
        cv2.circle(ov, (cx, cy), r + 6, (0, 30, 180), -1)
        cv2.addWeighted(ov, 0.35, frame, 0.65, 0, frame)
        cv2.circle(frame, (cx, cy), r, (0, 60, 220), -1)
        cv2.circle(frame, (cx, cy), max(1, r // 2), (80, 130, 255), -1)

        # Short trail
        trail_x = int(cx - self.vel[0] * 3)
        trail_y = int(cy - self.vel[1] * 3)
        cv2.line(frame, (trail_x, trail_y), (cx, cy), (0, 40, 150), 2)


class Target:
    SHOOT_INTERVAL_BASE = 180  # frames between shots at wave 1

    def __init__(self, frame_shape, wave=1):
        h, w = frame_shape[:2]
        self.center = np.array([w // 2, h // 2], dtype=float)

        edge = random.randint(0, 3)
        m = 70
        if edge == 0:
            x, y = random.randint(m, w - m), m
        elif edge == 1:
            x, y = random.randint(m, w - m), h - m
        elif edge == 2:
            x, y = m, random.randint(m, h - m)
        else:
            x, y = w - m, random.randint(m, h - m)

        self.pos    = np.array([x, y], dtype=float)
        self.radius = random.randint(35, 55)
        self.speed  = random.uniform(0.5, 0.8 + wave * 0.15)
        self.alive  = True
        self.hit_time = None

        direction  = self.center - self.pos
        self.vel   = direction / np.linalg.norm(direction) * self.speed

        # Shooting
        interval = max(60, self.SHOOT_INTERVAL_BASE - wave * 15)
        self.shoot_timer = random.randint(interval // 2, interval)
        self.shoot_interval = interval
        self.wave = wave

    def update(self):
        """Returns True if target reached center."""
        if not self.alive:
            return False
        self.pos += self.vel
        return np.linalg.norm(self.pos - self.center) < 35

    def try_shoot(self):
        """Returns a new EnemyBullet aimed at center, or None."""
        if not self.alive:
            return None
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_interval
            return EnemyBullet(self.pos.copy(), self.center)
        return None

    def check_hit(self, fireball_pos):
        return np.linalg.norm(self.pos - np.array(fireball_pos)) < self.radius + 18

    def draw(self, frame, t):
        cx, cy = int(self.pos[0]), int(self.pos[1])

        if self.hit_time is not None:
            elapsed = time.time() - self.hit_time
            if elapsed < 0.45:
                alpha = 1.0 - elapsed / 0.45
                r = int(self.radius * (1 + elapsed * 4))
                overlay = frame.copy()
                cv2.circle(overlay, (cx, cy), r, (0, 80, 255), -1)
                cv2.addWeighted(overlay, alpha * 0.55, frame, 1 - alpha * 0.55, 0, frame)
                cv2.circle(frame, (cx, cy), int(r * 0.5), (50, 180, 255), -1)
            return

        pulse = int(4 * math.sin(t * 5))
        r = self.radius + pulse
        cv2.circle(frame, (cx, cy), r,            (0, 0, 200), 2)
        cv2.circle(frame, (cx, cy), int(r * 0.7), (0, 80, 255), 2)
        cv2.circle(frame, (cx, cy), int(r * 0.4), (0, 180, 255), -1)
        cv2.circle(frame, (cx, cy), int(r * 0.15),(255, 255, 255), -1)

        cv2.line(frame, (cx - r, cy), (cx + r, cy), (0, 0, 150), 1)
        cv2.line(frame, (cx, cy - r), (cx, cy + r), (0, 0, 150), 1)

        dist_ratio = 1.0 - min(1.0, np.linalg.norm(self.pos - self.center) /
                                     np.linalg.norm(np.array([frame.shape[1]//2,
                                                               frame.shape[0]//2])))
        bar_w = int(r * 2 * dist_ratio)
        bar_x = cx - r
        bar_y = cy + r + 8
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + r * 2, bar_y + 6), (50, 50, 50), -1)
        color = (0, 255 - int(200 * dist_ratio), int(200 * dist_ratio))
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 6), color, -1)


class TargetGame:
    KILLS_PER_WAVE = 8

    def __init__(self, frame_shape):
        self.frame_shape    = frame_shape
        self.score          = 0
        self.lives          = 3
        self.wave           = 1
        self.kills          = 0
        self.targets        = []
        self.bullets        = []
        self.spawn_timer    = 0
        self.spawn_interval = 90
        self.max_targets    = 4
        self.game_over      = False
        self._wave_banner_time = time.time()
        self._explosions    = []   # [(cx, cy, start_time)] for AoE visuals

    def update(self, active_effects, shield_center=None, shield_radius=0):
        if self.game_over:
            return

        h, w = self.frame_shape[:2]
        center = (w // 2, h // 2)

        # Spawn targets
        self.spawn_timer += 1
        alive_count = sum(1 for t in self.targets if t.alive)
        if self.spawn_timer >= self.spawn_interval and alive_count < self.max_targets:
            self.targets.append(Target(self.frame_shape, self.wave))
            self.spawn_timer = 0

        # Move targets, collect new bullets
        for target in self.targets:
            if target.alive:
                reached = target.update()
                if reached:
                    target.alive = False
                    self.lives -= 1
                    if self.lives <= 0:
                        self.game_over = True
                bullet = target.try_shoot()
                if bullet:
                    self.bullets.append(bullet)

        # Fireball vs target collision
        AOE_RADIUS = 150
        from effects import FireballEffect
        for effect in active_effects:
            if not isinstance(effect, FireballEffect) or effect.spent:
                continue
            for target in self.targets:
                if not target.alive:
                    continue
                if not target.check_hit(effect.pos):
                    continue

                if effect.charged:
                    # Mega fireball: AoE — kill all targets within radius
                    hit_cx, hit_cy = int(effect.pos[0]), int(effect.pos[1])
                    self._explosions.append((hit_cx, hit_cy, time.time()))
                    for t2 in self.targets:
                        if not t2.alive:
                            continue
                        if np.linalg.norm(t2.pos - effect.pos) <= AOE_RADIUS:
                            t2.alive    = False
                            t2.hit_time = time.time()
                            self.score += 20 * self.wave
                            self.kills += 1
                else:
                    # Regular fireball: single target, then spent
                    target.alive    = False
                    target.hit_time = time.time()
                    self.score += 10 * self.wave
                    self.kills += 1
                    effect.spent = True
                break

        # Move enemy bullets, check shield & center hit
        shield_active = shield_center is not None and shield_radius > 0
        for bullet in self.bullets:
            if not bullet.alive:
                continue
            if bullet.blocked_time is not None:
                continue

            # Shield blocks bullet
            if shield_active and bullet.check_shield(shield_center, shield_radius):
                bullet.blocked_time = time.time()
                self.score += 5 * self.wave
                continue

            # Bullet reaches center → lose life
            reached = bullet.update(center)
            if reached:
                bullet.alive = False
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over = True

        # Cleanup
        self.targets = [
            t for t in self.targets
            if t.alive or (t.hit_time and time.time() - t.hit_time < 0.5)
        ]
        self.bullets = [
            b for b in self.bullets
            if b.alive and (b.blocked_time is None or time.time() - b.blocked_time < 0.35)
        ]

        # Wave progression
        if self.kills >= self.KILLS_PER_WAVE * self.wave:
            self.wave           += 1
            self.spawn_interval  = max(35, 90 - self.wave * 8)
            self.max_targets     = min(10, 4 + self.wave)
            self._wave_banner_time = time.time()

    def draw(self, frame):
        t = time.time()
        h, w = self.frame_shape[:2]

        # AoE explosion visuals
        self._explosions = [(cx, cy, st) for cx, cy, st in self._explosions
                            if t - st < 0.5]
        for cx, cy, st in self._explosions:
            elapsed = t - st
            alpha = 1.0 - elapsed / 0.5
            r = int(30 + elapsed * 280)
            ov = frame.copy()
            cv2.circle(ov, (cx, cy), r, (80, 255, 255), -1)
            cv2.addWeighted(ov, alpha * 0.18, frame, 1 - alpha * 0.18, 0, frame)
            cv2.circle(frame, (cx, cy), r, (80, 255, 255), 2)
            cv2.circle(frame, (cx, cy), max(1, r // 3), (200, 255, 255), -1)

        for bullet in self.bullets:
            bullet.draw(frame, t)

        for target in self.targets:
            target.draw(frame, t)

        self._draw_hud(frame, t)

        if t - self._wave_banner_time < 2.0:
            alpha = min(1.0, (2.0 - (t - self._wave_banner_time)) / 0.5)
            text  = f"WAVE  {self.wave}"
            tw    = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.8, 3)[0][0]
            overlay = frame.copy()
            cv2.putText(overlay, text, (w // 2 - tw // 2, h // 2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.8, (200, 200, 200), 3)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        if self.game_over:
            self._draw_game_over(frame)

    def _draw_hud(self, frame, t):
        h, w = self.frame_shape[:2]

        cv2.putText(frame, f"{self.score:05d}", (w - 160, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(frame, "SCORE", (w - 160, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 160, 160), 1)

        for i in range(3):
            color = (0, 50, 220) if i < self.lives else (60, 60, 60)
            cx = 20 + i * 32
            cv2.circle(frame, (cx, 70), 12, color, -1)

        cv2.putText(frame, f"WAVE  {self.wave}", (w // 2 - 55, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        cv2.putText(frame, "G: exit game", (12, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 100, 100), 1)

    def _draw_game_over(self, frame):
        h, w = self.frame_shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        cv2.putText(frame, "GAME OVER",
                    (w // 2 - 175, h // 2 - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 0, 220), 4)
        cv2.putText(frame, f"SCORE  {self.score}",
                    (w // 2 - 110, h // 2 + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
        cv2.putText(frame, f"WAVE  {self.wave}",
                    (w // 2 - 75, h // 2 + 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 1)
        cv2.putText(frame, "R  to restart     G  to exit",
                    (w // 2 - 175, h // 2 + 135),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (140, 140, 140), 1)
