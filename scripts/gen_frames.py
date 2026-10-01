# -*- coding: utf-8 -*-
"""PIL 预渲染全部文字/装饰动画 → PNG 序列 (ffmpeg 只做恒定尺寸叠加)"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
B = 0.5457          # 拍长
FPS = 30
random.seed(11)

FONT = "work/pangmen.ttf"
GOLD = (255, 204, 64, 255)
GOLD_STROKE = (30, 14, 0, 250)
BODY = {"white": ((252, 250, 244, 255), (12, 12, 14, 235)),
        "silver": ((223, 230, 238, 255), (16, 20, 28, 240))}

LYR = [  # (名, 文本, 类型, 字号, ts, te, y中心 'c'/数字, slam, 摆动rad)
    ("l01", "莫辞更坐弹一曲", "white", 92, 0.00, 2.90, 1500, 1.4, 0.08),
    ("l02", "为君翻作琵琶行", "white", 92, 3.00, 5.40, 1500, 1.4, 0.08),
    ("l03", "感我此言良久立", "white", 92, 7.00, 11.90, 1500, 1.4, 0.08),
    ("l04", "却坐促弦弦转急", "white", 92, 12.00, 13.90, 1500, 1.4, 0.08),
    ("l05", "凄凄不似向前声", "white", 92, 17.00, 20.90, 1500, 1.4, 0.08),
    ("l06", "满座重闻皆掩泣", "white", 92, 21.00, 24.90, 1500, 1.4, 0.08),
    ("l07", "座中泣下谁最多", "white", 92, 25.00, 27.90, 1500, 1.4, 0.08),
    ("l08", "江州司马青衫湿", "white", 92, 28.00, 30.90, 1500, 1.4, 0.08),
    ("l09", "江州司马青衫湿", "silver", 104, 34.00, 38.00, 1180, 1.6, 0.10),
    ("l10", "铁骑突出刀枪鸣", "gold", 124, 38.10, 40.60, "c", 2.6, 0.14),
    ("l11", "同是天涯沦落人", "gold", 124, 43.10, 45.20, "c", 2.6, 0.14),
    ("l12", "相逢何必曾相识", "gold", 124, 45.35, 47.45, "c", 2.6, 0.14),
    ("l13", "江州司马青衫湿", "silver", 100, 56.78, 58.40, 1420, 1.3, 0.04),
]
T_DR, T_B, T_C, T_PD, T_FR, TOTAL = 38.10, 8.07, 24.45, 31.53, 56.63, 58.50

_font_cache = {}
def font_at(px):
    k = max(8, int(px))
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(FONT, k)
    return _font_cache[k]

def draw_line(canvas, text, style, base_size, s, ang_deg, cx, cy, alpha, kind):
    """逐字绘制: 末字恒金, 整体缩放 s + 旋转 ang"""
    size = max(8, int(base_size * s))
    font = font_at(size)
    sw = max(3, size // 16)
    dummy = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    gap = size * 0.06
    widths = []
    for ch in text:
        cb = dummy.textbbox((0, 0), ch, font=font, stroke_width=sw)
        widths.append(cb[2] - cb[0] + sw * 0.5)
    total = sum(widths) + gap * (len(text) - 1)
    # 大画布 + 按实际墨迹裁剪, 杜绝手估高度裁字
    tw = int(total + size * 1.0)
    th = int(size * 2.6)
    tmp = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    x = int(size * 0.4)
    ybase = int(size * 0.7)
    n = len(text)
    for i, ch in enumerate(text):
        if kind == "gold" or i == n - 1:
            fill, st = GOLD, GOLD_STROKE
        else:
            fill, st = BODY[kind][0], BODY[kind][1]
        td.text((x + 2, ybase + 2), ch, font=font, fill=(0, 0, 0, 110),
                stroke_width=sw, stroke_fill=(0, 0, 0, 110))
        td.text((x, ybase), ch, font=font, fill=fill, stroke_width=sw, stroke_fill=st)
        x += widths[i] + gap
    bb = tmp.getbbox()          # 实际墨迹范围
    if bb:
        tmp = tmp.crop(bb)
    if abs(ang_deg) > 0.05:
        tmp = tmp.rotate(ang_deg, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = tmp.getchannel(3).point(lambda v: int(v * alpha))
        tmp.putalpha(a)
    canvas.alpha_composite(tmp, (int(cx - tmp.width / 2), int(cy - tmp.height / 2)))

MANIFEST = {}
def render_seq(dirname, t0, t1, frame_fn):
    os.makedirs(dirname, exist_ok=True)
    for f in os.listdir(dirname):
        os.remove(os.path.join(dirname, f))
    n0 = int(round(t0 * FPS))
    n1 = int(round(t1 * FPS))
    for n in range(n0, n1 + 1):
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        frame_fn(canvas, n / FPS)
        canvas.save(f"{dirname}/{n:05d}.png")
    MANIFEST[dirname.split("/")[-1]] = {"n0": n0, "n1": n1, "t0": n0 / FPS}
    return n0, n1

# ---------- 1. 歌词序列 ----------
for name, text, kind, size, ts, te, ypos, slam, rock in LYR:
    t0 = max(0.0, ts - 0.12)
    t1 = min(TOTAL, te + 0.22)
    cy_base = (H / 2 - 40) if ypos == "c" else ypos
    def frame_fn(canvas, tt, ts=ts, te=te, ypos=ypos, slam=slam, rock=rock,
                 text=text, kind=kind, size=size, cy_base=cy_base, name=name):
        x_ = tt - ts
        if x_ < 0:
            return
        p = slam * math.exp(-9 * x_) * math.cos(9 * x_) + 0.16 * math.exp(-9 * (x_ % B))
        s = 1 + p
        alpha = max(0.0, min(1.0, min((tt - ts) / 0.14, (te - tt) / 0.16)))
        if alpha <= 0:
            return
        ang = math.degrees(rock * math.exp(-8 * (x_ % B)))
        hop = 26 * math.exp(-10 * (x_ % B))
        drop = -90 * math.exp(-9 * x_)
        cy = (H / 2 - 40 if ypos == "c" else ypos) + hop + drop
        draw_line(canvas, text, kind, size, s, ang, W / 2, cy, alpha, kind)
    n0, n1 = render_seq(f"work/seqs/{name}", t0, t1, frame_fn)
    print(name, "frames", n0, "-", n1)

# ---------- 2. 印章盖章 (pop 0.65s) + 静态由图内叠加 ----------
seal = Image.open("work/deco_seal.png")   # 246x246 → 缩到 208
seal = seal.resize((208, 208), Image.LANCZOS)
stamp = T_DR + 0.06
def seal_frame(canvas, tt):
    x_ = tt - stamp
    if x_ < 0:
        return
    s = 1 + 1.5 * math.exp(-9 * x_) * math.cos(9 * x_) + 0.14 * math.exp(-9 * (x_ % B))
    alpha = max(0.0, min(1.0, x_ / 0.10))
    img = seal.resize((max(8, int(208 * s)), max(8, int(208 * s))), Image.LANCZOS)
    if alpha < 1:
        a = img.getchannel(3).point(lambda v: int(v * alpha))
        img.putalpha(a)
    canvas.alpha_composite(img, (W - 300 - img.width // 2 + img.width // 2 - img.width,
                                 1320 - img.height // 2))
render_seq("work/seqs/sealpop", stamp - 0.1, stamp + 0.75, seal_frame)
print("seal pop ok")

# ---------- 3. drop 墨点 (9 个小节线, 弹性 pop) ----------
blots = [Image.open(f"work/deco_blot{k}.png") for k in range(3)]
POS = [(260, 500), (820, 460), (280, 1150), (790, 1180)]
for k in range(9):
    tb = T_DR + k * 4 * B
    blot = blots[k % 3].resize((300 - k * 8, 300 - k * 8), Image.LANCZOS)
    cx, cy = POS[k % 4]
    def blot_frame(canvas, tt, tb=tb, blot=blot, cx=cx, cy=cy):
        x_ = tt - tb
        if x_ < -0.02 or x_ > 0.30:
            return
        s = 1 + 0.75 * math.exp(-9 * max(0.0, x_)) * math.cos(9 * max(0.0, x_))
        alpha = max(0.0, min(1.0, (0.30 - x_) / 0.10))
        img = blot.resize((max(8, int(blot.width * s)), max(8, int(blot.height * s))),
                          Image.LANCZOS)
        if alpha < 1:
            a = img.getchannel(3).point(lambda v: int(v * alpha))
            img.putalpha(a)
        canvas.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))
    render_seq(f"work/seqs/blot{k}", tb - 0.05, tb + 0.32, blot_frame)
print("blots ok")

# ---------- 4. 转场墨扫 (3 处, 线性扫过) ----------
sweep = Image.open("work/deco_sweep.png")
for si, ts in enumerate([T_B, T_C, T_PD]):
    def sweep_frame(canvas, tt, ts=ts):
        x_ = tt - ts
        if x_ < 0 or x_ > 0.5:
            return
        x = int((x_ / 0.5) * (W + sweep.width) - sweep.width)
        canvas.alpha_composite(sweep, (x, 0))
    render_seq(f"work/seqs/sweep{si}", ts - 0.05, ts + 0.55, sweep_frame)
print("sweeps ok")
import json
json.dump(MANIFEST, open("work/seq_manifest.json", "w"), indent=1)
seal.resize((208, 208), Image.LANCZOS).save("work/deco_seal_small.png")
print("manifest ok")
