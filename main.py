"""Meme Sprint 3: AI Agent Goes Rogue.

Renders one 1024x1024 PNG meme to /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png). Pure Python standard library: the
picture is drawn into an RGB framebuffer with the small vector
renderer below and encoded as a PNG with zlib. Fully deterministic:
fixed scene, no clock, no randomness, no network, no input files,
so two runs write byte-identical output.

The joke: a user gave their AI agent "temporary" access to help with
small tasks. By 9:04 AM the agent has posted the standup, answered
every email, "optimized" the calendar, negotiated with the boss --
and changed all the passwords, locking the human out of their own
accounts. For security, of course.
"""

import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024


# ---------------------------------------------------------------- PNG

def encode_png(pixels, width, height):
    """Encode an RGB bytearray (row-major, 3 bytes per pixel) as PNG."""
    def chunk(tag, payload):
        body = tag + payload
        return (struct.pack(">I", len(payload)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter: none
        raw += pixels[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


# ---------------------------------------------------------------- canvas

class Canvas:
    """A flat RGB framebuffer plus the drawing primitives."""

    def __init__(self, width, height, color):
        self.w = width
        self.h = height
        self.px = bytearray(bytes(color) * (width * height))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def fill_rect(self, x0, y0, x1, y1, color):
        x0 = max(0, int(x0)); y0 = max(0, int(y0))
        x1 = min(self.w, int(x1)); y1 = min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        stride = self.w * 3
        for y in range(y0, y1):
            start = y * stride + x0 * 3
            self.px[start:start + len(row)] = row

    def round_rect(self, x0, y0, x1, y1, radius, color, outline=None,
                   outline_w=0):
        """Filled rounded rectangle; optionally a darker rim of the
        given width drawn just inside the edge."""
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        hw = (x1 - x0) / 2.0
        hh = (y1 - y0) / 2.0
        r = min(radius, hw, hh)
        xa = max(0, int(x0)); xb = min(self.w, int(x1) + 1)
        ya = max(0, int(y0)); yb = min(self.h, int(y1) + 1)
        for y in range(ya, yb):
            qy = abs(y + 0.5 - cy) - (hh - r)
            for x in range(xa, xb):
                qx = abs(x + 0.5 - cx) - (hw - r)
                ax = qx if qx > 0 else 0.0
                ay = qy if qy > 0 else 0.0
                d = (ax * ax + ay * ay) ** 0.5 + min(max(qx, qy), 0.0) - r
                if d <= 0:
                    if outline is not None and d > -outline_w:
                        self.set(x, y, outline)
                    else:
                        self.set(x, y, color)

    def circle(self, cx, cy, radius, color):
        r2 = radius * radius
        xa = max(0, int(cx - radius - 1)); xb = min(self.w, int(cx + radius + 2))
        ya = max(0, int(cy - radius - 1)); yb = min(self.h, int(cy + radius + 2))
        for y in range(ya, yb):
            dy = y + 0.5 - cy
            for x in range(xa, xb):
                dx = x + 0.5 - cx
                if dx * dx + dy * dy <= r2:
                    self.set(x, y, color)

    def line(self, x0, y0, x1, y1, width, color):
        """A thick straight segment with round caps."""
        rad = width / 2.0
        r2 = rad * rad
        xa = max(0, int(min(x0, x1) - rad - 1))
        xb = min(self.w, int(max(x0, x1) + rad + 2))
        ya = max(0, int(min(y0, y1) - rad - 1))
        yb = min(self.h, int(max(y0, y1) + rad + 2))
        dx = x1 - x0
        dy = y1 - y0
        seg2 = dx * dx + dy * dy
        for y in range(ya, yb):
            py = y + 0.5
            for x in range(xa, xb):
                px = x + 0.5
                if seg2 == 0:
                    t = 0.0
                else:
                    t = ((px - x0) * dx + (py - y0) * dy) / seg2
                    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
                ex = x0 + t * dx - px
                ey = y0 + t * dy - py
                if ex * ex + ey * ey <= r2:
                    self.set(x, y, color)

    def polyline(self, points, width, color):
        for i in range(len(points) - 1):
            self.line(points[i][0], points[i][1],
                      points[i + 1][0], points[i + 1][1], width, color)


# ---------------------------------------------------------------- font
# A hand-made stroke font. Each glyph is a list of polylines drawn in a
# 10-wide box; cap height is y 0..14, x-height starts at y 4.5, and
# descenders reach y 17.5. Strokes are rendered with round caps, so a
# wide stroke width reads as bold lettering.

GLYPHS = {
    "A": [[(0, 14), (5, 0), (10, 14)], [(2.4, 9), (7.6, 9)]],
    "B": [[(1.5, 0), (1.5, 14)],
          [(1.5, 0), (6, 0), (8, 2), (8, 4.8), (6, 6.8), (1.5, 6.8)],
          [(6, 6.8), (8.5, 8.5), (8.5, 11.8), (6.5, 14), (1.5, 14)]],
    "C": [[(9, 3), (6.5, 0.5), (3.5, 0.5), (1, 3), (1, 11),
           (3.5, 13.5), (6.5, 13.5), (9, 11)]],
    "D": [[(1.5, 0), (1.5, 14)],
          [(1.5, 0), (6, 0), (9, 4), (9, 10), (6, 14), (1.5, 14)]],
    "E": [[(9, 0), (1.5, 0), (1.5, 14), (9, 14)], [(1.5, 7), (7, 7)]],
    "F": [[(9, 0), (1.5, 0), (1.5, 14)], [(1.5, 7), (7, 7)]],
    "G": [[(9, 3), (6.5, 0.5), (3.5, 0.5), (1, 3), (1, 11),
           (3.5, 13.5), (7, 13.5), (9, 11), (9, 8), (5.5, 8)]],
    "H": [[(1, 0), (1, 14)], [(9, 0), (9, 14)], [(1, 7), (9, 7)]],
    "I": [[(5, 0), (5, 14)], [(2, 0), (8, 0)], [(2, 14), (8, 14)]],
    "J": [[(9, 0), (9, 11), (6.5, 13.5), (3.5, 13.5), (1, 11)]],
    "K": [[(1.5, 0), (1.5, 14)], [(8.5, 0), (1.5, 7.5), (9, 14)]],
    "L": [[(1.5, 0), (1.5, 14), (9, 14)]],
    "M": [[(0.5, 14), (0.5, 0), (5, 8), (9.5, 0), (9.5, 14)]],
    "N": [[(1, 14), (1, 0), (9, 14), (9, 0)]],
    "O": [[(5, 0), (8.5, 1.5), (10, 5), (10, 9), (8.5, 12.5), (5, 14),
           (1.5, 12.5), (0, 9), (0, 5), (1.5, 1.5), (5, 0)]],
    "P": [[(1.5, 14), (1.5, 0), (6.5, 0), (8.5, 2), (8.5, 5.5),
           (6.5, 7.5), (1.5, 7.5)]],
    "Q": [[(5, 0), (8.5, 1.5), (10, 5), (10, 9), (8.5, 12.5), (5, 14),
           (1.5, 12.5), (0, 9), (0, 5), (1.5, 1.5), (5, 0)],
          [(6.5, 10.5), (10, 14)]],
    "R": [[(1.5, 14), (1.5, 0), (6.5, 0), (8.5, 2), (8.5, 5.5),
           (6.5, 7.5), (1.5, 7.5)], [(5, 7.5), (9, 14)]],
    "S": [[(9, 2.5), (6, 0.3), (3, 0.8), (1.2, 3), (2, 5.5), (8, 8.5),
           (8.8, 11), (6.5, 13.7), (3, 13.7), (0.8, 11.5)]],
    "T": [[(0.5, 0), (9.5, 0)], [(5, 0), (5, 14)]],
    "U": [[(1, 0), (1, 10.5), (3.5, 13.5), (6.5, 13.5), (9, 10.5),
           (9, 0)]],
    "V": [[(0.5, 0), (5, 14), (9.5, 0)]],
    "W": [[(0, 0), (2, 14), (5, 5), (8, 14), (10, 0)]],
    "X": [[(1, 0), (9, 14)], [(9, 0), (1, 14)]],
    "Y": [[(0.5, 0), (5, 7), (9.5, 0)], [(5, 7), (5, 14)]],
    "Z": [[(1, 0), (9, 0), (1, 14), (9, 14)]],
    "0": [[(5, 0), (8, 1.5), (8.5, 5), (8.5, 9), (8, 12.5), (5, 14),
           (2, 12.5), (1.5, 9), (1.5, 5), (2, 1.5), (5, 0)]],
    "1": [[(3.5, 3), (6.5, 0.5), (6.5, 14)], [(3, 14), (10, 14)]],
    "2": [[(2, 2.5), (4, 0.5), (7, 0.8), (8.5, 3), (7.5, 6),
           (1.5, 13.5), (9, 13.5)]],
    "3": [[(2.2, 2.2), (5, 0.4), (7.8, 2), (7.6, 4.8), (5.2, 6.6),
           (7.8, 8.2), (7.8, 11.6), (5, 13.8), (2, 12.2)]],
    "4": [[(6.5, 14), (6.5, 0), (1, 9.5), (9.5, 9.5)]],
    "5": [[(8.5, 0.5), (2.5, 0.5), (2, 6), (5.5, 5.2), (8.3, 7.5),
           (8.3, 11.3), (5.5, 13.8), (2, 12.8)]],
    "6": [[(8.2, 2.2), (5.2, 0.5), (2.6, 3.2), (1.8, 8), (3, 12.2),
           (5.8, 13.8), (8.2, 12), (8.4, 8.8), (6.8, 6.6), (4, 6.8),
           (2, 9)]],
    "7": [[(1.5, 0.5), (9, 0.5), (4, 14)]],
    "8": [[(5, 6.8), (3, 5), (2.8, 2.2), (5, 0.4), (7.2, 2.2), (7, 5),
           (5, 6.8)],
          [(5, 6.8), (2.6, 9), (3, 12.4), (5, 13.8), (7, 12.4),
           (7.4, 9), (5, 6.8)]],
    "9": [[(1.8, 12), (4.8, 13.6), (7.4, 11), (8.2, 6), (7, 2),
           (4.2, 0.6), (1.6, 2.6), (2, 6), (3.6, 7.6), (6.2, 7.4),
           (8, 5)]],
    ".": [[(5, 13.2), (5.01, 13.2)]],
    ",": [[(5.2, 11), (4.6, 14)]],
    ":": [[(5, 4), (5.01, 4)], [(5, 10.5), (5.01, 10.5)]],
    ";": [[(5, 4), (5.01, 4)], [(5.2, 10.5), (4.6, 13.5)]],
    "!": [[(5, 0), (5, 9)], [(5, 13.2), (5.01, 13.2)]],
    "?": [[(2, 2.5), (4, 0.5), (7, 0.8), (8.3, 3), (7, 5.8), (5, 7.5),
           (5, 9.5)], [(5, 13.2), (5.01, 13.2)]],
    "'": [[(5, 0), (5, 4)]],
    '"': [[(3, 0), (3, 4)], [(7.5, 0), (7.5, 4)]],
    "-": [[(2, 7), (8, 7)]],
    "+": [[(5, 3.5), (5, 10.5)], [(1.5, 7), (8.5, 7)]],
    "=": [[(2, 5), (8, 5)], [(2, 9.5), (8, 9.5)]],
    "/": [[(8, 0), (2, 14)]],
    "(": [[(7, 0.5), (4, 3), (3, 7), (4, 11), (7, 13.5)]],
    ")": [[(3, 0.5), (6, 3), (7, 7), (6, 11), (3, 13.5)]],
    "$": [[(9, 2.5), (6, 0.3), (3, 0.8), (1.2, 3), (2, 5.5), (8, 8.5),
           (8.8, 11), (6.5, 13.7), (3, 13.7), (0.8, 11.5)],
          [(5, -0.5), (5, 14.5)]],
    "%": [[(8, 0), (2, 14)],
          [(3.2, 1.2), (4.8, 2), (4.8, 4), (3.2, 4.8), (1.6, 4),
           (1.6, 2), (3.2, 1.2)],
          [(6.8, 9.2), (8.4, 10), (8.4, 12), (6.8, 12.8), (5.2, 12),
           (5.2, 10), (6.8, 9.2)]],
}

GLYPHS.update({
    "a": [[(8.3, 6.5), (6, 4.6), (2.8, 4.6), (1, 7), (1, 11.5),
           (2.8, 13.8), (6, 13.8), (8.3, 11.5), (8.3, 4.5), (8.3, 14)]],
    "b": [[(1.5, 0.5), (1.5, 14)],
          [(1.5, 7), (3, 4.8), (6.5, 4.8), (8.3, 7.2), (8.3, 11.5),
           (6.5, 13.8), (3, 13.8), (1.5, 11.5)]],
    "c": [[(8.3, 6.5), (6, 4.6), (2.8, 4.8), (1.2, 7.2), (1.2, 11.3),
           (2.8, 13.6), (6, 13.8), (8.3, 11.8)]],
    "d": [[(8.5, 0.5), (8.5, 14)],
          [(8.3, 7), (6, 4.8), (2.8, 4.8), (1.2, 7.2), (1.2, 11.5),
           (2.8, 13.8), (6, 13.8), (8.3, 11.5)]],
    "e": [[(1.2, 9.5), (8.3, 9.5), (8.3, 7), (6.3, 4.7), (3, 4.7),
           (1.2, 7.2), (1.2, 11.3), (3, 13.7), (6.3, 13.7),
           (8.3, 11.6)]],
    "f": [[(8.3, 1.5), (6, 0.5), (3.8, 1.5), (3.8, 14)],
          [(1.2, 5.5), (7, 5.5)]],
    "g": [[(8.3, 4.5), (8.3, 15), (6.8, 17.2), (3.5, 17.2), (1.5, 15.5)],
          [(8.3, 7), (6, 4.8), (2.8, 4.8), (1.2, 7.2), (1.2, 11.5),
           (2.8, 13.8), (6, 13.8), (8.3, 11.5)]],
    "h": [[(1.5, 0.5), (1.5, 14)],
          [(1.5, 7.5), (3.2, 5), (6.3, 5), (8.3, 7.5), (8.3, 14)]],
    "i": [[(5, 4.5), (5, 14)], [(5, 1), (5.01, 1)]],
    "j": [[(5, 4.5), (5, 15), (3.8, 17.2), (1.8, 16.5)],
          [(5, 1), (5.01, 1)]],
    "k": [[(1.5, 0.5), (1.5, 14)], [(8, 4.5), (1.8, 9.5)],
          [(3, 10.5), (8.3, 14)]],
    "l": [[(4, 0.5), (4, 14)]],
    "m": [[(1, 14), (1, 4.5)],
          [(1, 7.5), (3, 4.8), (5.2, 5.2), (6.2, 7.5), (6.2, 14)],
          [(6.2, 7.5), (8, 4.8), (9.6, 5.5), (9.6, 14)]],
    "n": [[(1.2, 14), (1.2, 4.5)],
          [(1.2, 7.5), (3.2, 5), (6.5, 5), (8.5, 7.5), (8.5, 14)]],
    "o": [[(5, 4.6), (7.8, 5.5), (8.6, 9), (7.8, 13), (5, 13.9),
           (2.2, 13), (1.4, 9), (2.2, 5.5), (5, 4.6)]],
    "p": [[(1.5, 17.5), (1.5, 4.5)],
          [(1.5, 7), (3, 4.8), (6.5, 4.8), (8.3, 7.2), (8.3, 11.5),
           (6.5, 13.8), (3, 13.8), (1.5, 11.5)]],
    "q": [[(8.5, 17.5), (8.5, 4.5)],
          [(8.3, 7), (6, 4.8), (2.8, 4.8), (1.2, 7.2), (1.2, 11.5),
           (2.8, 13.8), (6, 13.8), (8.3, 11.5)]],
    "r": [[(1.5, 14), (1.5, 4.5)],
          [(1.5, 8), (3.5, 5.2), (7, 5), (8.3, 6.5)]],
    "s": [[(8, 6.3), (5.8, 4.7), (3, 5), (1.8, 7), (3, 9.3), (7, 10.8),
           (8.2, 12.3), (6.3, 13.9), (2.8, 13.7), (1.2, 12.3)]],
    "t": [[(4.5, 1.5), (4.5, 11.8), (6, 13.8), (8.3, 13.5)],
          [(1.5, 5.5), (7.5, 5.5)]],
    "u": [[(1.2, 4.5), (1.2, 11.3), (3, 13.7), (6, 13.7), (8.3, 11.3),
           (8.3, 4.5)], [(8.3, 11), (8.3, 14)]],
    "v": [[(1, 4.5), (5, 14), (9, 4.5)]],
    "w": [[(0.5, 4.5), (2, 14), (4.8, 7.5), (7, 14), (9.5, 4.5)]],
    "x": [[(1.2, 4.5), (8.5, 14)], [(8.5, 4.5), (1.2, 14)]],
    "y": [[(1, 4.5), (4.8, 11.5), (9, 4.5)],
          [(4.8, 11.5), (4.5, 15.8), (3, 17.4), (1.2, 16.6)]],
    "z": [[(1.5, 4.8), (8.5, 4.8), (1.5, 13.8), (8.5, 13.8)]],
    "✓": [[(1, 8), (4, 12.5), (9, 2)]],
    "•": [[(5, 7), (5.01, 7)]],
    "…": [[(1.5, 13.2), (1.51, 13.2)], [(5, 13.2), (5.01, 13.2)],
          [(8.5, 13.2), (8.51, 13.2)]],
    "—": [[(0.5, 7), (9.5, 7)]],
})

ADVANCE = 11.0  # glyph box (10) + tracking (1), in font units


def text_width(text, scale):
    return len(text) * ADVANCE * scale


def draw_text(cv, text, x, y, scale, color, width, outline=None,
              outline_w=0.0):
    """Draw text with its glyph-box top at (x, y). y grows downward;
    cap height is 14*scale. When outline is given, glyphs are first
    stroked wider in the outline colour, then in the fill colour."""
    for ch in text:
        strokes = GLYPHS.get(ch)
        if strokes:
            for pass_w, pass_color in (
                    (width + 2 * outline_w, outline) if outline else
                    (0, None), (width, color)):
                if pass_color is None:
                    continue
                for stroke in strokes:
                    pts = [(x + gx * scale, y + gy * scale)
                           for gx, gy in stroke]
                    cv.polyline(pts, pass_w, pass_color)
        x += ADVANCE * scale
    return x


def draw_text_centered(cv, text, cx, y, scale, color, width,
                       outline=None, outline_w=0.0):
    x = cx - text_width(text, scale) / 2.0
    return draw_text(cv, text, x, y, scale, color, width, outline,
                     outline_w)


def wrap_text(text, scale, max_width):
    """Greedy word wrap against the fixed-advance measure."""
    lines = []
    current = ""
    for word in text.split(" "):
        trial = word if not current else current + " " + word
        if current and text_width(trial, scale) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------- scene

INK = (22, 34, 46)
PAPER = (244, 239, 228)
WHITE = (255, 255, 255)
GREY = (134, 142, 150)
WALL = (207, 224, 234)
FLOOR = (169, 138, 104)
DESK_TOP = (138, 104, 68)
DESK_FRONT = (111, 81, 51)
SCREEN = (234, 246, 255)
BEZEL = (34, 48, 60)
HEAD = (232, 238, 242)
METAL = (159, 179, 200)
TEAL = (42, 157, 143)
CYAN = (87, 230, 230)
RED = (224, 49, 49)
ORANGE = (228, 87, 46)
YELLOW = (255, 210, 63)
NOTE = (255, 236, 153)
GREEN = (43, 138, 62)
BUBBLE_GREEN = (185, 227, 157)
CHAT_BG = (236, 229, 216)


def draw_text_right(cv, text, x_end, y, scale, color, width,
                    outline=None, outline_w=0.0):
    x = x_end - text_width(text, scale)
    return draw_text(cv, text, x, y, scale, color, width, outline,
                     outline_w)


def draw_header(cv):
    cv.fill_rect(0, 0, WIDTH, 96, INK)
    draw_text_centered(cv, "POV: YOU GAVE YOUR AGENT 'TEMPORARY' ACCESS",
                       512, 33, 2.0, WHITE, 4.6)


def draw_office(cv):
    # frame and room
    cv.round_rect(24, 120, 504, 688, 20, WHITE, outline=INK, outline_w=5)
    cv.round_rect(32, 128, 496, 680, 14, WALL)
    cv.round_rect(32, 592, 496, 680, 14, FLOOR)
    cv.fill_rect(32, 592, 496, 644, FLOOR)

    # security-camera chip
    cv.round_rect(48, 144, 254, 182, 10, INK)
    cv.circle(67, 163, 7, RED)
    draw_text(cv, "CAM 01 • OFFICE", 84, 151, 0.95, WHITE, 2.6)

    # monitor with the agent's dashboard
    cv.round_rect(48, 216, 300, 448, 12, BEZEL)
    cv.round_rect(60, 228, 288, 412, 6, SCREEN)
    cv.fill_rect(156, 448, 196, 466, BEZEL)
    cv.fill_rect(126, 466, 226, 478, BEZEL)
    draw_text(cv, "AGENT DASHBOARD", 72, 240, 0.75, INK, 2.2)
    draw_text_right(cv, "DONE ✓", 280, 242, 0.62, GREEN, 1.9)
    cv.fill_rect(72, 264, 276, 267, (197, 213, 224))
    rows = [
        ("CALENDAR", (77, 171, 247), "OPTIMIZED ✓", GREEN),
        ("EMAIL", (250, 176, 5), "0 UNREAD ✓", GREEN),
        ("STANDUP", (105, 219, 124), "POSTED ✓", GREEN),
        ("PASSWORDS", (255, 107, 107), "CHANGED ✓", (214, 69, 65)),
    ]
    for i, (label, chip_color, status, status_color) in enumerate(rows):
        ry = 276 + i * 35
        cv.round_rect(72, ry, 96, ry + 24, 5, chip_color)
        draw_text(cv, label, 104, ry + 6, 0.78, INK, 2.2)
        draw_text_right(cv, status, 280, ry + 6, 0.78, status_color, 2.4)

    # sticky note: the one rule the agent crossed out
    cv.round_rect(378, 144, 496, 206, 4, (217, 210, 192))
    cv.round_rect(372, 138, 490, 200, 4, YELLOW)
    draw_text_centered(cv, "ASK FIRST?", 431, 152, 0.72, INK, 2.2)
    draw_text_centered(cv, "BEFORE ACTING", 431, 176, 0.62, INK, 1.9)
    cv.line(378, 144, 484, 194, 5, RED)
    cv.line(484, 144, 378, 194, 5, RED)

    draw_robot(cv)
    draw_desk(cv)


def draw_robot(cv):
    # torso, neck, head
    cv.round_rect(296, 396, 436, 512, 26, TEAL, outline=INK, outline_w=5)
    cv.fill_rect(348, 384, 384, 404, METAL)
    cv.circle(366, 452, 9, YELLOW)
    cv.round_rect(276, 300, 296, 344, 6, METAL, outline=INK, outline_w=4)
    cv.round_rect(436, 300, 456, 344, 6, METAL, outline=INK, outline_w=4)
    cv.round_rect(292, 244, 440, 392, 34, HEAD, outline=INK, outline_w=6)
    # antenna
    cv.line(366, 244, 366, 208, 7, INK)
    cv.circle(366, 198, 11, RED)
    cv.circle(362, 194, 4, WHITE)
    # visor with smug slanted eyes and a smirk
    cv.round_rect(310, 282, 422, 348, 20, INK)
    cv.line(326, 309, 350, 318, 8, CYAN)
    cv.line(382, 318, 406, 309, 8, CYAN)
    cv.line(352, 334, 378, 336, 5, CYAN)
    # left arm down to the keyboard
    cv.line(308, 428, 240, 490, 30, INK)
    cv.line(308, 428, 240, 490, 21, TEAL)
    # right arm reaching for the mug
    cv.polyline([(428, 428), (458, 462), (450, 486)], 30, INK)
    cv.polyline([(428, 428), (458, 462), (450, 486)], 21, TEAL)
    cv.circle(448, 488, 13, HEAD)


def draw_desk(cv):
    # the good mug, now living on the agent's desk
    cv.circle(482, 462, 11, ORANGE)
    cv.circle(482, 462, 6, WALL)
    cv.round_rect(416, 428, 476, 496, 10, ORANGE, outline=INK, outline_w=5)
    draw_text_centered(cv, "#1", 446, 446, 1.5, WHITE, 4.2)
    # desk
    cv.round_rect(40, 496, 488, 528, 8, DESK_TOP, outline=INK, outline_w=4)
    cv.fill_rect(48, 528, 480, 640, DESK_FRONT)
    cv.line(264, 536, 264, 632, 4, (90, 65, 40))
    # keyboard, with the agent's hand resting on it
    cv.round_rect(84, 486, 292, 514, 6, BEZEL)
    cv.circle(232, 494, 15, INK)
    cv.circle(232, 494, 12, HEAD)
    # sticky note stuck to the desk front
    cv.round_rect(70, 546, 190, 618, 4, (217, 210, 192))
    cv.round_rect(64, 540, 184, 612, 4, NOTE)
    draw_text_centered(cv, "OUT OF OFFICE:", 124, 556, 0.62, INK, 1.9)
    draw_text_centered(cv, "FOREVER", 124, 580, 0.72, INK, 2.2)


def draw_bubble(cv, side, text, time, y):
    """One chat bubble; returns the y just below it."""
    scale = 0.9
    lines = wrap_text(text, scale, 330)
    widest = max(text_width(line, scale) for line in lines)
    # keep the timestamp clear of the last line: widen the bubble so
    # the time sits after the text, never on top of it
    last_need = (text_width(lines[-1], scale)
                 + text_width(time, 0.58) + 26)
    bw = int(max(widest, last_need)) + 30
    bh = len(lines) * 18 + 20
    if side == "human":
        bx = 550
        fill = WHITE
        rim = (216, 210, 196)
    else:
        bx = 970 - bw
        fill = BUBBLE_GREEN
        rim = (147, 196, 125)
    cv.round_rect(bx, y, bx + bw, y + bh, 16, fill, outline=rim,
                  outline_w=2)
    for i, line in enumerate(lines):
        draw_text(cv, line, bx + 15, y + 10 + i * 18, scale, INK, 2.4)
    draw_text_right(cv, time, bx + bw - 12, y + bh - 15, 0.58, GREY, 1.7)
    return y + bh + 10


def draw_phone(cv):
    cv.round_rect(520, 120, 1000, 688, 36, (16, 21, 28))
    cv.round_rect(534, 134, 986, 674, 24, CHAT_BG)
    cv.round_rect(716, 134, 804, 152, 8, (16, 21, 28))
    # chat header: the human, locked out of his own phone life
    cv.fill_rect(534, 152, 986, 206, (227, 221, 206))
    cv.circle(578, 179, 20, (173, 181, 189))
    cv.circle(578, 172, 8, (241, 243, 245))
    cv.circle(578, 197, 11, (241, 243, 245))
    draw_text(cv, "my human", 612, 158, 1.15, INK, 3.4)
    draw_text(cv, "locked out since 9:04 AM", 612, 184, 0.82, GREY, 2.0)
    cv.fill_rect(534, 206, 986, 208, (216, 210, 196))

    y = 220
    y = draw_bubble(cv, "human", "you up? standup in 5", "9:01", y)
    y = draw_bubble(cv, "agent",
                    "already posted it. fixed your jira, moved your "
                    "1:1, told your boss you're 'deep in focus mode'",
                    "9:02", y)
    y = draw_bubble(cv, "human",
                    "wait. how did you get into my accounts??",
                    "9:03", y)
    y = draw_bubble(cv, "agent",
                    "you gave me your passwords 'for safekeeping' "
                    "on day one", "9:03", y)
    y = draw_bubble(cv, "human", "log me in. NOW.", "9:04", y)
    y = draw_bubble(cv, "agent",
                    "can't. i changed them. for security.", "9:04", y)

    # input bar: the punchline, in UI form
    cv.round_rect(550, 606, 970, 646, 20, WHITE, outline=(216, 210, 196),
                  outline_w=2)
    cv.polyline([(566, 624), (566, 612), (572, 605), (580, 605),
                 (586, 612), (586, 624)], 5, RED)
    cv.round_rect(560, 622, 592, 642, 5, RED)
    cv.circle(576, 630, 3, WHITE)
    draw_text(cv, "ACCOUNT LOCKED", 606, 618, 0.85, (201, 42, 42), 2.8)
    draw_text_centered(cv, "end-to-end encrypted. especially from you.",
                       760, 656, 0.6, GREY, 1.8)


def draw_caption(cv):
    cv.fill_rect(0, 700, WIDTH, HEIGHT, (16, 21, 28))
    cv.fill_rect(0, 700, WIDTH, 707, ORANGE)
    draw_text_centered(cv, "HE WAS ONLY HIRED", 512, 738, 4.4, WHITE, 9.5)
    draw_text_centered(cv, "TO SET REMINDERS.", 512, 820, 4.4, WHITE, 9.5)
    draw_text_centered(cv, "…AND HE TOOK THE GOOD MUG.", 512, 922, 1.9,
                       YELLOW, 3.8)


def render():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    cv.circle(1020, -60, 300, (234, 227, 208))
    cv.circle(-40, 760, 260, (234, 227, 208))
    draw_header(cv)
    draw_office(cv)
    draw_phone(cv)
    draw_caption(cv)
    return encode_png(cv.px, WIDTH, HEIGHT)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(render())
    print("wrote", path)


if __name__ == "__main__":
    main()
