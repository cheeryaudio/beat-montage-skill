# -*- coding: utf-8 -*-
"""最终管线:
passA: grade+border+title → ffv1 mkv (已验证干净的输出路径, 无 fade)
passB: mkv →(ffmpeg管道 rgb24)→ PIL合成动画序列+数值淡入淡出 →(管道 rgb24)→ x264 + 混音音频
"""
import json, subprocess, os, math
import numpy as np
from PIL import Image

FF = r"C:\Users\ASUS\AppData\Roaming\Python\Python314\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
W, H, FPS = 1080, 1920, 30
TOTAL = 58.5
NF = int(TOTAL * FPS)
B = 0.5457

edl = json.load(open("work/edl.json"))
def vt(m): return m - M0 if (M0 := 184.0) else 0
t_B = vt(edl[2][0]); t_C = vt(edl[17][0]); t_PD = vt(edl[30][0])
t_DR = vt(edl[33][0]); t_FR = vt(edl[67][0])

# ---------- pass A ----------
GRADE = (
    "[0:v]format=gbrp,split=2[g1][g2];"
    "[g2]gblur=sigma=18[gbl];"
    "[g1][gbl]blend=all_mode=screen:all_opacity=0.32,format=rgb24,scale=1080:1920[b0];"
    "[b0]format=rgb24[b0r];"
    "[1:v]format=rgb24[pr];"
    "[b0r][pr]blend=all_mode=overlay:all_opacity=0.30[b1];"
    "[b1]eq=saturation=0.35:brightness=0.02,"
    "curves=master='0/0.02 0.22/0.14 0.5/0.5 0.78/0.86 1/0.985',"
    "unsharp=11:11:1.1:5:5:0,"
    "colorbalance=rs=0.06:bs=-0.04,"
    "vignette=angle=PI/4.8,noise=alls=3:allf=t+u,format=rgb24[vg0];"
    "[2:v]format=rgb24[brd];"
    "[vg0][brd]blend=all_mode=multiply:all_opacity=1,scale=1080:1920[b2];"
    "[b2]format=yuv420p[vg];"
    "[vg][3:v]overlay=x='W-w-44':y='96':eof_action=pass[vout]"
)
subprocess.run([FF, "-y", "-loglevel", "error",
                "-filter_complex_threads", "1", "-filter_threads", "1",
                "-f", "concat", "-safe", "0", "-i", "work/concat_final.txt",
                "-loop", "1", "-framerate", "30", "-t", f"{TOTAL}", "-i", "work/paper.png",
                "-loop", "1", "-framerate", "30", "-t", f"{TOTAL}", "-i", "work/deco_border.png",
                "-loop", "1", "-framerate", "30", "-t", f"{TOTAL}", "-i", "work/deco_title.png",
                "-filter_complex", GRADE, "-map", "[vout]",
                "-c:v", "ffv1", "-t", f"{TOTAL}", "work/passA.mkv"], check=True)
print("passA ok", flush=True)

# ---------- 序列调度 ----------
MAN = json.load(open("work/seq_manifest.json"))
SEQ_DIRS = {}
for k in range(13):
    SEQ_DIRS[f"lyr{k}"] = f"work/seqs/l{k + 1:02d}"
for si in range(3):
    SEQ_DIRS[f"sweep{si}"] = f"work/seqs/sweep{si}"
SEQ_DIRS["sealpop"] = "work/seqs/sealpop"
for k in range(9):
    SEQ_DIRS[f"blot{k}"] = f"work/seqs/blot{k}"

from collections import defaultdict
buckets = defaultdict(list)
def add_range(key, n0, n1):
    for n in range(n0, n1 + 1):
        if 0 <= n < NF:
            buckets[n].append(key)
for k in range(13):
    m = MAN[f"l{k + 1:02d}"]
    add_range(f"lyr{k}", m["n0"], m["n1"])
for si in range(3):
    m = MAN[f"sweep{si}"]
    add_range(f"sweep{si}", m["n0"], m["n1"])
m = MAN["sealpop"]
add_range("sealpop", m["n0"], m["n1"])
seal_static = Image.open("work/deco_seal_small.png")
stamp_f = int((t_DR + 0.06 + 0.80) * FPS)
for n in range(stamp_f, NF):
    buckets[n].append("@seal")
for k in range(9):
    m = MAN[f"blot{k}"]
    add_range(f"blot{k}", m["n0"], m["n1"])
print("schedule ok", sum(len(v) for v in buckets.values()), "composites", flush=True)

_cache = {}
def seq_frame(key, n):
    p = f"{SEQ_DIRS[key]}/{n:05d}.png"
    if not os.path.exists(p):
        return None
    if p in _cache:
        return _cache[p]
    if len(_cache) > 24:
        _cache.clear()
    im = Image.open(p).convert("RGBA")
    _cache[p] = im
    return im

# ---------- pass B: 管道 ----------
dec = subprocess.Popen([FF, "-loglevel", "error", "-i", "work/passA.mkv",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen([FF, "-y", "-loglevel", "error",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                        "-i", "work/mix.m4a",
                        "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", "out/pipa_xing_x_mw_v5.mp4"],
                       stdin=subprocess.PIPE)
FRB = W * H * 3
nfail = 0
for n in range(NF):
    buf = bytearray()
    while len(buf) < FRB:
        chunk = dec.stdout.read(FRB - len(buf))
        if not chunk:
            break
        buf += chunk
    if len(buf) < FRB:
        print("decoder EOF at", n); break
    arr = np.frombuffer(bytes(buf), dtype=np.uint8).reshape(H, W, 3)
    fade = min(1.0, n / 18.0, (NF - 1 - n) / 18.0)
    if fade < 1.0:
        arr = (arr.astype(np.float32) * fade).clip(0, 255).astype(np.uint8)
    frame = Image.frombuffer("RGB", (W, H), arr.tobytes()).convert("RGBA")
    for key in buckets.get(n, []):
        if key == "@seal":
            frame.alpha_composite(seal_static, (572, 1216))
        else:
            fimg = seq_frame(key, n)
            if fimg is not None:
                frame.alpha_composite(fimg)
    out = np.asarray(frame.convert("RGB"), dtype=np.uint8)
    enc.stdin.write(out.tobytes())
    if n % 300 == 0:
        print(f"  frame {n}/{NF}", flush=True)
enc.stdin.close()
enc.wait()
dec.wait()
print("passB ok, rc(enc)=", enc.returncode, "rc(dec)=", dec.returncode, flush=True)
# 自动清理无损中间产物 (passA.mkv 约1.3GB)
if enc.returncode == 0 and dec.returncode == 0:
    try:
        os.remove("work/passA.mkv")
        print("cleanup: passA.mkv removed")
    except FileNotFoundError:
        pass
