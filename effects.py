import cv2
import numpy as np
import time
import math


# ── Base ──────────────────────────────────────────────────────────────────────

class Effect:
    def __init__(self, duration):
        self.start_time = time.time()
        self.duration = duration

    @property
    def progress(self):
        return min(1.0, (time.time() - self.start_time) / self.duration)

    @property
    def alive(self):
        return self.progress < 1.0

    def _alpha(self, p, fade_in=0.1, fade_out=0.2):
        if p < fade_in:
            return p / fade_in
        if p > 1.0 - fade_out:
            return (1.0 - p) / fade_out
        return 1.0

    def draw(self, frame):
        raise NotImplementedError


# ── Fireball (directional push) ───────────────────────────────────────────────

class FireballEffect(Effect):
    def __init__(self, pos, vx, vy, charged=False):
        mult = 2.2 if charged else 1.0
        super().__init__(duration=2.0 if charged else 1.6)
        self.pos = np.array(pos, dtype=float)
        self.vx = vx
        self.vy = vy
        self.speed = 18 * (1.4 if charged else 1.0)
        self.charged = charged
        self.core_r = int(22 * mult)
        self.glow_r = int(40 * mult)
        self.trail_max = 30 if charged else 22
        self.trail = []

    def draw(self, frame):
        p = self.progress
        t = time.time()
        alpha = self._alpha(p, 0.05, 0.3)

        self.pos[0] += self.speed * self.vx
        self.pos[1] += self.speed * self.vy
        self.trail.append(tuple(self.pos.astype(int)))
        if len(self.trail) > self.trail_max:
            self.trail.pop(0)

        for i, tp in enumerate(self.trail):
            ratio = i / max(len(self.trail), 1)
            r = max(1, int(self.core_r * 0.5 * ratio))
            col = (0, int(200 * ratio) if self.charged else int(80 * ratio), int(255 * ratio))
            cv2.circle(frame, tp, r, col, -1)

        cx, cy = int(self.pos[0]), int(self.pos[1])

        overlay = frame.copy()
        cv2.circle(overlay, (cx, cy), self.glow_r,
                   (0, 100, 255) if not self.charged else (0, 200, 255), -1)
        cv2.addWeighted(overlay, 0.3 * alpha, frame, 1 - 0.3 * alpha, 0, frame)

        cv2.circle(frame, (cx, cy), self.core_r,
                   (0, 140, 255) if not self.charged else (0, 220, 255), -1)
        cv2.circle(frame, (cx, cy), self.core_r // 2,
                   (30, 210, 255) if not self.charged else (100, 255, 255), -1)
        cv2.circle(frame, (cx, cy), max(4, self.core_r // 5), (200, 240, 255), -1)

        n_sparks = 10 if self.charged else 6
        for i in range(n_sparks):
            angle = t * 6 + i * (2 * math.pi / n_sparks)
            sx = cx + int((self.glow_r - 5) * math.cos(angle))
            sy = cy + int((self.glow_r - 5) * math.sin(angle))
            cv2.circle(frame, (sx, sy), 3, (0, 200, 255), -1)

        if p < 0.25:
            label = "★ MEGA FIREBALL!" if self.charged else "FIREBALL!"
            cv2.putText(frame, label, (cx - 70, cy - self.glow_r - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                        (0, 220, 255) if self.charged else (0, 160, 255), 2)


# ── Manager ───────────────────────────────────────────────────────────────────

class EffectManager:
    def __init__(self):
        self.effects = []

    def add(self, gesture_result):
        name, *args = gesture_result
        if name == "push":
            pos, vx, vy, charged = args
            self.effects.append(FireballEffect(pos, vx, vy, charged))

    def draw(self, frame):
        self.effects = [e for e in self.effects if e.alive]
        for e in self.effects:
            e.draw(frame)
