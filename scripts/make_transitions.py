# -*- coding: utf-8 -*-
"""段落转场: xfade 拼接 4 组关键镜头对, 生成 concat_final.txt"""
import subprocess, os, re

FF = r"C:\Users\ASUS\AppData\Roaming\Python\Python314\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"

# (前镜头, 后镜头, 转场, 时长)
JOINS = [
    ("c001", "c002", "smoothleft", 0.18),  # 铺垫→蓄势: 甩入
    ("c016", "c017", "circleopen", 0.18),  # 蓄势→加速: 圆环爆开
    ("c029", "c030", "fade",       0.22),  # 加速→蓄力: 呼吸淡变
    ("c066", "c067", "circleopen", 0.18),  # drop→定格: 圆环收进合影
]

def dur(p):
    o = subprocess.run([FF, "-hide_banner", "-i", p], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", o)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

keep = set(range(68))
used = set()
for a, b, tr, td in JOINS:
    used.add(int(a[1:])); used.add(int(b[1:]))
for a, b, tr, td in JOINS:
    pa, pb = f"work/clips/{a}.mp4", f"work/clips/{b}.mp4"
    da, db = dur(pa), dur(pb)
    out = f"work/clips/j{a[1:]}{b[1:]}.mp4"
    fc = (f"[0:v]setpts=PTS-STARTPTS,fps=30[a];"
          f"[1:v]setpts=PTS-STARTPTS,fps=30[b];"
          f"[a][b]xfade=transition={tr}:duration={td}:offset={da - td:.3f},format=yuv420p[v]")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", pa, "-i", pb,
                    "-filter_complex", fc, "-map", "[v]", "-r", "30",
                    "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-an", out],
                   check=True)
    jd = dur(out)
    print(f"{a}+{b} {tr}: {da:.2f}+{db:.2f} -> {jd:.2f} (expect {da - td + db:.2f})")

lines = []
i = 0
while i < 68:
    hit = next((j for j, (a, b, _, _) in enumerate(JOINS) if int(a[1:]) == i), None)
    if hit is not None:
        a, b, _, _ = JOINS[hit]
        lines.append(f"file 'clips/j{a[1:]}{b[1:]}.mp4'")
        i += 2
    else:
        lines.append(f"file 'clips/c{i:03d}.mp4'")
        i += 1
open("work/concat_final.txt", "w").write("\n".join(lines))
print("concat_final.txt ok,", len(lines), "entries")
