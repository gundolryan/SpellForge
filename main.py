import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np
import math
import time
import os
import urllib.request

from gesture_detector import GestureDetector
from effects import EffectManager

MODEL_PATH = "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

GESTURE_LABELS = {
    "push": ("FIREBALL", (0, 160, 255)),
}


def download_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand landmark model (~10MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Done.")


def draw_hand(frame, landmarks, h, w):
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for c1, c2 in HAND_CONNECTIONS:
        cv2.line(frame, pts[c1], pts[c2], (0, 200, 100), 2)
    for i, pt in enumerate(pts):
        color = (0, 0, 220) if i in [4, 8, 12, 16, 20] else (180, 50, 50)
        cv2.circle(frame, pt, 5, color, -1)


# ── Shield visuals ────────────────────────────────────────────────────────────

def draw_shield_loading(frame, center, palm_size, progress):
    cx, cy = center
    r = max(int(palm_size * 1.6), 80)
    cv2.circle(frame, (cx, cy), r, (80, 50, 10), 1)
    angle = int(360 * progress)
    cv2.ellipse(frame, (cx, cy), (r, r), -90, 0, angle, (200, 120, 20), 3)
    tip = math.radians(-90 + angle)
    cv2.circle(frame, (cx + int(r * math.cos(tip)), cy + int(r * math.sin(tip))),
               6, (255, 180, 50), -1)


def draw_live_shield(frame, center, palm_size, t, activated_time):
    cx, cy = center
    r = int(palm_size * 1.6 + 8 * math.sin(t * 7))
    r = max(r, 80)

    flash = max(0.0, 1.0 - (t - activated_time) / 0.4)
    if flash > 0:
        overlay = frame.copy()
        cv2.circle(overlay, (cx, cy), r + int(30 * flash), (200, 180, 80), -1)
        cv2.addWeighted(overlay, 0.45 * flash, frame, 1 - 0.45 * flash, 0, frame)

    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), r, (180, 60, 0), -1)
    cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
    col = (255, 160, 30)
    cv2.circle(frame, (cx, cy), r, col, 3)
    cv2.circle(frame, (cx, cy), int(r * 0.82), col, 1)
    for i in range(6):
        a0 = 2 * math.pi / 6 * i + t * 0.4
        a1 = a0 + math.pi / 6 * 0.7
        pts = [(cx + int(r * 0.92 * math.cos(a)), cy + int(r * 0.92 * math.sin(a)))
               for a in np.linspace(a0, a1, 12)]
        for j in range(len(pts) - 1):
            cv2.line(frame, pts[j], pts[j + 1], col, 2)
    cv2.putText(frame, "SHIELD", (cx - 38, cy - r - 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)


# ── Charge visuals ────────────────────────────────────────────────────────────

def draw_fist_loading(frame, center, palm_size, progress):
    cx, cy = center
    r = max(int(palm_size * 1.3), 60)
    cv2.circle(frame, (cx, cy), r, (30, 80, 80), 1)
    angle = int(360 * progress)
    cv2.ellipse(frame, (cx, cy), (r, r), -90, 0, angle, (60, 220, 220), 3)
    tip = math.radians(-90 + angle)
    cv2.circle(frame, (cx + int(r * math.cos(tip)), cy + int(r * math.sin(tip))),
               5, (100, 255, 255), -1)


def draw_charge_aura(frame, wrist_px, t, is_fist):
    cx, cy = wrist_px
    r = int(65 + 10 * math.sin(t * 10))
    fill_alpha = 0.20 if is_fist else 0.10
    overlay = frame.copy()
    cv2.circle(overlay, (cx, cy), r, (0, 255, 255), -1)
    cv2.addWeighted(overlay, fill_alpha, frame, 1 - fill_alpha, 0, frame)
    for i in range(3):
        rr = r + i * 14 + int(4 * math.sin(t * 8 + i * 1.2))
        cv2.circle(frame, (cx, cy), rr, (80, 255, 255), 1)
    cv2.putText(frame, "CHARGED", (cx - 42, cy - r - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 255, 255), 1)


# ── Fireball (pointing) visuals ───────────────────────────────────────────────

def draw_point_loading(frame, index_tip_px, direction, progress):
    tx, ty = index_tip_px
    vx, vy = direction
    # Aiming beam grows as it charges
    beam_len = int(160 * progress)
    ex = tx + int(beam_len * vx)
    ey = ty + int(beam_len * vy)
    brightness = int(255 * progress)
    cv2.line(frame, (tx, ty), (ex, ey), (0, brightness // 2, brightness), 2)
    # Tip glow at beam end
    if beam_len > 10:
        cv2.circle(frame, (ex, ey), int(6 * progress), (0, brightness, 255), -1)
    # Charging arc at fingertip
    arc_r = 18
    angle = int(360 * progress)
    cv2.ellipse(frame, (tx, ty), (arc_r, arc_r), -90, 0, angle,
                (0, int(160 * progress), 255), 2)


# ── UI ────────────────────────────────────────────────────────────────────────

def draw_hand_label(frame, label, color, wrist_px, side):
    prefix = "L" if side == "Left" else "R"
    cv2.putText(frame, f"{prefix}: {label}",
                (wrist_px[0] - 60, wrist_px[1] - 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)


def draw_ui(frame):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 48), (20, 20, 20), -1)
    cv2.putText(frame, "MAGIC GESTURE SYSTEM", (12, 33),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)
    lines = [
        ("Palm open     ->  Shield",          (255, 160,  30)),
        ("Point finger  ->  Fireball",         (  0, 160, 255)),
        ("Fist -> Point ->  Mega Fireball",    ( 80, 255, 255)),
        ("Q to quit",                          (100, 100, 100)),
    ]
    for i, (text, col) in enumerate(lines):
        cv2.putText(frame, text, (12, h - 88 + i * 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    download_model()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detectors: dict[str, GestureDetector] = {}
    effects = EffectManager()
    hand_labels: dict[str, dict] = {}

    options = mp_vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=mp_vision.RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.65,
        min_hand_presence_confidence=0.65,
        min_tracking_confidence=0.65,
    )

    with mp_vision.HandLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            t = time.time()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            active = set()
            if result.hand_landmarks:
                for i, hand_lms in enumerate(result.hand_landmarks):
                    raw  = result.handedness[i][0].category_name
                    side = "Right" if raw == "Left" else "Left"
                    active.add(side)

                    if side not in detectors:
                        detectors[side] = GestureDetector()

                    det = detectors[side]
                    draw_hand(frame, hand_lms, h, w)
                    wrist_px = (int(hand_lms[0].x * w), int(hand_lms[0].y * h))

                    gesture = det.update(hand_lms, frame.shape)

                    # ── Live visuals ──────────────────────────────────────────
                    # Shield
                    if det.is_palm_open:
                        draw_live_shield(frame, det.palm_center,
                                         det.current_palm_size, t,
                                         det.shield_activated_time)
                    elif 0 < det.open_palm_counter < det.OPEN_PALM_HOLD:
                        draw_shield_loading(frame, det.palm_center,
                                            det.current_palm_size,
                                            det.open_palm_counter / det.OPEN_PALM_HOLD)

                    # Charge
                    if det.is_charged:
                        draw_charge_aura(frame, wrist_px, t, det.is_fist)
                    elif 0 < det.fist_counter < det.FIST_HOLD:
                        draw_fist_loading(frame, det.palm_center,
                                          det.current_palm_size,
                                          det.fist_counter / det.FIST_HOLD)

                    # Fireball pointing
                    if det.is_pointing and det.point_counter > 0:
                        draw_point_loading(frame, det.index_tip_px,
                                           det.point_direction,
                                           det.point_counter / det.POINT_HOLD)

                    # ── Gesture event ─────────────────────────────────────────
                    if gesture:
                        effects.add(gesture)
                        name    = gesture[0]
                        charged = gesture[-1] if name == "push" else False
                        base_label, color = GESTURE_LABELS[name]
                        label = ("★ " + base_label) if charged else base_label
                        hand_labels[side] = {
                            "label": label, "color": color,
                            "end": t + 1.0, "pos": wrist_px,
                        }

                    if side in hand_labels and hand_labels[side]["end"] > t:
                        info = hand_labels[side]
                        draw_hand_label(frame, info["label"], info["color"],
                                        wrist_px, side)

            for side in list(detectors):
                if side not in active:
                    del detectors[side]

            effects.draw(frame)
            draw_ui(frame)

            cv2.imshow("Magic Gesture System", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
