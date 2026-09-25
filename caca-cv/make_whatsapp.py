#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 420, 820
BG = (229, 221, 213)
HEADER_BG = (18, 140, 126)
SENT = (220, 248, 198)
RECV = (255, 255, 255)
TEXT_DARK = (17, 27, 33)
TEXT_GRAY = (102, 116, 128)
TIME_COLOR = (102, 116, 128)
BUBBLE_SHADOW = (200, 195, 190)

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

def load_font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                pass
    return ImageFont.load_default()

try:
    font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
    font_reg  = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    font_sm   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    font_hdr  = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    font_time_hdr = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
except:
    font_bold = font_reg = font_sm = font_hdr = font_time_hdr = ImageFont.load_default()

# ── header ────────────────────────────────────────────────────
draw.rectangle([(0,0),(W,62)], fill=HEADER_BG)

# avatar circle
draw.ellipse([(12,14),(48,50)], fill=(255,255,255,80))
draw.ellipse([(14,16),(46,48)], fill=(150,200,190))
draw.text((24, 24), "🌍", font=font_hdr, fill=(255,255,255))

draw.text((58, 14), "Pariz trip 🗼", font=font_bold, fill=(255,255,255))
draw.text((58, 34), "Ana, Maja, Luka, Tomislav, ti", font=font_sm, fill=(200,235,230))

# ── date chip ─────────────────────────────────────────────────
chip_txt = "danas"
chip_w = 70
chip_x = (W - chip_w) // 2
draw.rounded_rectangle([(chip_x, 72),(chip_x+chip_w, 90)], radius=8, fill=(210,202,194))
draw.text((chip_x+14, 76), chip_txt, font=font_sm, fill=TEXT_GRAY)

# ── messages ──────────────────────────────────────────────────
messages = [
    # (sender, text_lines, time, is_sent)
    ("Ana",     ["Dečki idemo u Pariz!! 🎉", "tko što želi posjetiti?"], "10:04", False),
    ("Maja",    ["ja MORAM na Eiffelov toranj", "i Notre-Dame 🙏"], "10:06", False),
    ("Luka",    ["Louvre je must za mene", "i Versailles ako stignem 👀"], "10:07", False),
    ("ti",      ["Champs-Élysées i Arc de Triomphe 🫡", "i neki dobar restoran brate"], "10:09", True),
    ("Tomislav",["Sacré-Cœur i Montmartre!!", "usput i koji muzej modernog"], "10:11", False),
    ("Ana",     ["okej znači ima nas 5\ni svako hoće nešto drugo 😅\ntko to planira??"], "10:14", False),
    ("Maja",    ["nema šanse ručno 💀"], "10:15", False),
    ("ti",      ["hm neka AI to složi 🤖"], "10:16", True),
]

COLORS = {
    "Ana":      (149, 117, 205),
    "Maja":     (230, 120, 70),
    "Luka":     (72, 169, 166),
    "Tomislav": (100, 160, 90),
}

y = 100
PAD = 10
MAX_W = 260

for sender, lines, time_str, is_sent in messages:
    # measure bubble
    line_widths = []
    for ln in lines:
        bb = draw.textbbox((0,0), ln, font=font_reg)
        line_widths.append(bb[2]-bb[0])
    name_w = 0
    if not is_sent:
        nb = draw.textbbox((0,0), sender, font=font_bold)
        name_w = nb[2]-nb[0]

    content_w = min(max(max(line_widths), name_w) + PAD*2, MAX_W)
    n_lines = sum(1 + (draw.textbbox((0,0), ln, font=font_reg)[2] // MAX_W) for ln in lines)
    bubble_h = (8 if not is_sent else 4) + len(lines)*18 + PAD*2 - 4

    if is_sent:
        bx = W - content_w - 12
    else:
        bx = 12

    # tail
    if is_sent:
        tail = [(W-12, y+4),(W-6, y),(W-6, y+10)]
        draw.polygon(tail, fill=SENT)
        draw.rounded_rectangle([(bx, y),(bx+content_w, y+bubble_h)], radius=8, fill=SENT)
    else:
        tail = [(12, y+4),(6, y),(6, y+10)]
        draw.polygon(tail, fill=RECV)
        draw.rounded_rectangle([(bx, y),(bx+content_w, y+bubble_h)], radius=8, fill=RECV)

    # sender name
    ty = y + PAD - 2
    if not is_sent:
        col = COLORS.get(sender, TEXT_GRAY)
        draw.text((bx+PAD, ty), sender, font=font_bold, fill=col)
        ty += 18

    # message lines
    for ln in lines:
        draw.text((bx+PAD, ty), ln, font=font_reg, fill=TEXT_DARK)
        ty += 18

    # timestamp
    tb = draw.textbbox((0,0), time_str, font=font_sm)
    tw = tb[2]-tb[0]
    if is_sent:
        draw.text((bx+content_w-tw-PAD, y+bubble_h-14), time_str, font=font_sm, fill=TIME_COLOR)
    else:
        draw.text((bx+content_w-tw-PAD, y+bubble_h-14), time_str, font=font_sm, fill=TIME_COLOR)

    y += bubble_h + 8

# ── input bar ─────────────────────────────────────────────────
draw.rectangle([(0, H-52),(W, H)], fill=(242,242,242))
draw.rounded_rectangle([(8, H-44),(W-55, H-10)], radius=20, fill=(255,255,255))
draw.text((20, H-34), "Poruka", font=font_reg, fill=TEXT_GRAY)
draw.ellipse([(W-47, H-44),(W-9, H-10)], fill=HEADER_BG)
draw.text((W-36, H-34), "➤", font=font_reg, fill=(255,255,255))

out = "/Users/lorenajakic/Desktop/whatsapp_chat.png"
img.save(out, quality=95)
print(f"✓ {out}")
