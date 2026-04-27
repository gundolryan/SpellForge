import cv2
import numpy as np
import math
import time


GAMES = [
    {
        "id": "target",
        "title": "TARGET HUNT",
        "desc": "Shoot targets before\nthey reach the center",
        "color": (0, 140, 255),
        "icon": "◎",
    },
    {
        "id": "coming1",
        "title": "COMING SOON",
        "desc": "More modes\nin development",
        "color": (80, 80, 80),
        "icon": "?",
    },
    {
        "id": "coming2",
        "title": "COMING SOON",
        "desc": "More modes\nin development",
        "color": (80, 80, 80),
        "icon": "?",
    },
]

HOLD_FRAMES = 40   # ~1.3s to select


class GameLobby:
    def __init__(self, frame_shape):
        h, w = frame_shape[:2]
        self.frame_shape = frame_shape
        self.cards = self._layout_cards(w, h)
        self.hover_frames = [0] * len(GAMES)
        self.selected = None       # set to game id when confirmed

    def _layout_cards(self, w, h):
        n = len(GAMES)
        card_w, card_h = 260, 300
        gap = 40
        total_w = n * card_w + (n - 1) * gap
        start_x = (w - total_w) // 2
        cy = h // 2 - 20
        cards = []
        for i in range(n):
            x = start_x + i * (card_w + gap)
            cards.append((x, cy - card_h // 2, card_w, card_h))
        return cards

    def update(self, index_tip_px, is_pointing):
        """Call each frame. Returns game id string when player selects, else None."""
        for i, (gx, gy, gw, gh) in enumerate(self.cards):
            if GAMES[i]["id"].startswith("coming"):
                self.hover_frames[i] = 0
                continue

            tx, ty = index_tip_px
            inside = gx <= tx <= gx + gw and gy <= ty <= gy + gh
            if is_pointing and inside:
                self.hover_frames[i] = min(self.hover_frames[i] + 1, HOLD_FRAMES)
            else:
                self.hover_frames[i] = max(self.hover_frames[i] - 2, 0)

            if self.hover_frames[i] >= HOLD_FRAMES:
                self.selected = GAMES[i]["id"]
                return GAMES[i]["id"]

        return None

    def draw(self, frame, index_tip_px, is_pointing):
        h, w = frame.shape[:2]
        t = time.time()

        # Dark overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (10, 10, 20), -1)
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

        # Title
        title = "SELECT GAME MODE"
        tw = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)[0][0]
        cv2.putText(frame, title, (w // 2 - tw // 2, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (220, 220, 220), 2)

        subtitle = "Point at a card and hold to select"
        sw = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0][0]
        cv2.putText(frame, subtitle, (w // 2 - sw // 2, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (130, 130, 130), 1)

        for i, (gx, gy, gw, gh) in enumerate(self.cards):
            game = GAMES[i]
            color = game["color"]
            prog = self.hover_frames[i] / HOLD_FRAMES
            coming = game["id"].startswith("coming")

            # Card background
            card_overlay = frame.copy()
            cv2.rectangle(card_overlay, (gx, gy), (gx + gw, gy + gh),
                          (30, 30, 40) if coming else (20, 30, 50), -1)
            alpha = 0.55 if not coming else 0.4
            if prog > 0:
                alpha = min(0.85, 0.55 + prog * 0.3)
            cv2.addWeighted(card_overlay, alpha, frame, 1 - alpha, 0, frame)

            # Card border
            border_color = (50, 50, 60) if coming else color
            thick = 1 if coming else (2 + int(prog * 2))
            cv2.rectangle(frame, (gx, gy), (gx + gw, gy + gh), border_color, thick)

            # Progress arc around card
            if prog > 0 and not coming:
                cx_arc = gx + gw // 2
                cy_arc = gy + gh // 2
                r_arc = min(gw, gh) // 2 + 10
                angle = int(360 * prog)
                cv2.ellipse(frame, (cx_arc, cy_arc), (r_arc, r_arc),
                            -90, 0, angle, color, 3)

            # Icon area circle
            icon_cy = gy + 90
            icon_cx = gx + gw // 2
            icon_r = 44
            if not coming:
                pulse = int(5 * math.sin(t * 4 + i))
                cv2.circle(frame, (icon_cx, icon_cy), icon_r + pulse, color, 2)
                cv2.circle(frame, (icon_cx, icon_cy), icon_r - 10 + pulse,
                           tuple(c // 3 for c in color), -1)
            else:
                cv2.circle(frame, (icon_cx, icon_cy), icon_r, (60, 60, 60), 1)

            # Title
            title_col = (180, 180, 180) if coming else (230, 230, 255)
            title_w = cv2.getTextSize(game["title"], cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)[0][0]
            cv2.putText(frame, game["title"],
                        (gx + gw // 2 - title_w // 2, gy + 165),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, title_col, 2)

            # Description (two lines)
            for li, line in enumerate(game["desc"].split("\n")):
                lw = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[0][0]
                cv2.putText(frame, line,
                            (gx + gw // 2 - lw // 2, gy + 200 + li * 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                            (100, 100, 100) if coming else (160, 180, 200), 1)

            # Hover progress bar at bottom of card
            if prog > 0 and not coming:
                bar_y = gy + gh - 14
                cv2.rectangle(frame, (gx + 10, bar_y), (gx + gw - 10, bar_y + 6),
                              (40, 40, 50), -1)
                bar_fill = int((gw - 20) * prog)
                cv2.rectangle(frame, (gx + 10, bar_y),
                              (gx + 10 + bar_fill, bar_y + 6), color, -1)

        # Draw cursor dot at index tip
        if is_pointing:
            tx, ty = index_tip_px
            cv2.circle(frame, (tx, ty), 10, (0, 200, 255), -1)
            cv2.circle(frame, (tx, ty), 14, (0, 200, 255), 2)
            pulse_r = int(18 + 5 * math.sin(t * 12))
            cv2.circle(frame, (tx, ty), pulse_r, (0, 200, 255), 1)

        # G to exit hint
        cv2.putText(frame, "G: back", (12, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)
