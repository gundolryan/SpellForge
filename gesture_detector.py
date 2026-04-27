import numpy as np
from collections import deque
import time
import math


class GestureDetector:
    OPEN_PALM_HOLD = 8    # ~0.27s — shield
    FIST_HOLD      = 12   # ~0.40s — charge
    POINT_HOLD     = 15   # ~0.50s — fireball

    def __init__(self):
        self._cd = {"push": 0}
        self.last_gesture_name = None

        # ── Shield (open palm) ────────────────────────────────────────────────
        self.open_palm_counter   = 0
        self.is_palm_open        = False
        self._prev_palm_open     = False
        self.shield_activated_time = 0.0
        self.palm_center         = (0, 0)
        self.current_palm_size   = 0.0

        # ── Charge (fist) ─────────────────────────────────────────────────────
        self.fist_counter  = 0
        self.is_fist       = False
        self.charged       = False
        self.charge_expires = 0.0

        # ── Fireball (index pointing) ─────────────────────────────────────────
        self.point_counter   = 0
        self.is_pointing     = False
        self.index_tip_px    = (0, 0)
        self.point_direction = (1.0, 0.0)

    @property
    def is_charged(self):
        return self.charged and time.time() < self.charge_expires

    @property
    def COOLDOWN_FRAMES(self):
        return 12

    def update(self, landmarks, frame_shape):
        for k in self._cd:
            if self._cd[k] > 0:
                self._cd[k] -= 1

        # Order matters: palm → point → fist (each excludes the previous)
        self._update_palm_state(landmarks, frame_shape)
        self._update_point_state(landmarks, frame_shape)
        self._update_fist_state(landmarks, frame_shape)

        # Cancel charge only on shield (palm open) — pointing should consume it, not cancel
        if self.is_palm_open and self.charged:
            self.charged = False

        gesture = None
        if self._cd["push"] == 0 and self.point_counter >= self.POINT_HOLD:
            gesture = self._fire_point()

        if gesture:
            self._cd["push"] = self.COOLDOWN_FRAMES
            self.point_counter = 0
            self.last_gesture_name = gesture[0]

        return gesture

    # ── Fire event ────────────────────────────────────────────────────────────
    def _fire_point(self):
        vx, vy  = self.point_direction
        charged = self.is_charged
        if charged:
            self.charged = False
        return ("push", self.index_tip_px, float(vx), float(vy), charged)

    # ── Shield: palm open with hold delay ─────────────────────────────────────
    def _update_palm_state(self, landmarks, frame_shape):
        h, w = frame_shape[:2]
        palm_ids = [0, 5, 9, 13, 17]
        palm_pts = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in palm_ids])
        palm_center = palm_pts.mean(axis=0)

        tips = np.array([[landmarks[i].x * w, landmarks[i].y * h]
                          for i in [4, 8, 12, 16, 20]])
        avg_dist  = np.linalg.norm(tips - palm_center, axis=1).mean()
        wrist     = np.array([landmarks[0].x * w, landmarks[0].y * h])
        mid_mcp   = np.array([landmarks[9].x * w, landmarks[9].y * h])
        palm_size = np.linalg.norm(wrist - mid_mcp)

        raw_open = palm_size > 0 and avg_dist / palm_size > 1.0
        self.open_palm_counter = (
            min(self.open_palm_counter + 1, self.OPEN_PALM_HOLD) if raw_open else 0
        )

        prev = self.is_palm_open
        self.is_palm_open      = raw_open and self.open_palm_counter >= self.OPEN_PALM_HOLD
        self.palm_center        = (int(palm_center[0]), int(palm_center[1]))
        self.current_palm_size  = float(palm_size)

        if self.is_palm_open and not prev:
            self.shield_activated_time = time.time()

    # ── Fireball: index pointing with hold delay ───────────────────────────────
    def _update_point_state(self, landmarks, frame_shape):
        h, w = frame_shape[:2]

        def pt(idx):
            return np.array([landmarks[idx].x * w, landmarks[idx].y * h])

        wrist     = pt(0)
        mid_mcp   = pt(9)
        palm_size = np.linalg.norm(wrist - mid_mcp)

        if palm_size == 0 or self.is_palm_open:
            self.is_pointing   = False
            self.point_counter = 0
            return

        # Measure each finger by tip-to-MCP distance (robust across camera angles)
        def ext(tip_idx, mcp_idx):
            return np.linalg.norm(pt(tip_idx) - pt(mcp_idx)) / palm_size

        idx_ext = ext(8,  5)   # index
        mid_ext = ext(12, 9)   # middle
        rng_ext = ext(16, 13)  # ring
        pky_ext = ext(20, 17)  # pinky

        is_pointing_now = (
            idx_ext > 0.9 and          # index clearly extended
            idx_ext > mid_ext * 1.15 and  # index more extended than middle
            mid_ext < 0.90 and
            rng_ext < 0.95 and
            pky_ext < 0.95
        )

        if is_pointing_now:
            self.point_counter = min(self.point_counter + 1, self.POINT_HOLD)
            ix = landmarks[8].x * w - landmarks[5].x * w
            iy = landmarks[8].y * h - landmarks[5].y * h
            length = math.sqrt(ix * ix + iy * iy)
            if length > 0:
                self.point_direction = (ix / length, iy / length)
            self.index_tip_px = (int(landmarks[8].x * w), int(landmarks[8].y * h))
        else:
            self.point_counter = 0

        self.is_pointing = is_pointing_now

    # ── Charge: fist with hold delay ──────────────────────────────────────────
    def _update_fist_state(self, landmarks, frame_shape):
        h, w = frame_shape[:2]
        palm_ids = [0, 5, 9, 13, 17]
        palm_pts = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in palm_ids])
        palm_center = palm_pts.mean(axis=0)

        all_tips  = np.array([[landmarks[i].x * w, landmarks[i].y * h]
                               for i in [4, 8, 12, 16, 20]])
        all_dists = np.linalg.norm(all_tips - palm_center, axis=1)
        wrist     = np.array([landmarks[0].x * w, landmarks[0].y * h])
        mid_mcp   = np.array([landmarks[9].x * w, landmarks[9].y * h])
        palm_size = np.linalg.norm(wrist - mid_mcp)

        # All fingers curled AND no single finger sticking out (excludes pointing)
        is_fist_now = (
            palm_size > 0 and
            not self.is_palm_open and
            not self.is_pointing and
            all_dists.mean() / palm_size < 0.78 and
            all_dists.max()  / palm_size < 1.15
        )

        if is_fist_now:
            self.fist_counter = min(self.fist_counter + 1, self.FIST_HOLD)
        else:
            self.fist_counter = 0

        # Set charged on the moment hold completes
        if self.fist_counter >= self.FIST_HOLD and not self.is_charged:
            self.charged = True
            self.charge_expires = time.time() + 3600.0

        self.is_fist = is_fist_now
