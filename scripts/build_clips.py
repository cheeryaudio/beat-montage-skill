# -*- coding: utf-8 -*-
"""琵琶行DJ名龙版 x 现代战争 燃混剪 — EDL 构建 + 逐镜头渲染"""
import json, os, subprocess, sys

FF = r"C:\Users\ASUS\AppData\Roaming\Python\Python314\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
SRC = "raw/mw141.mp4"
MUSIC = "music/pipa_dj.mp3"
M0, M1 = 184.0, 242.5          # 用歌的 184s→242.5s
os.makedirs("work/clips", exist_ok=True)

beats = json.load(open("work/beats.json"))["beat_times"]

def snap(t):
    return min(beats, key=lambda b: abs(b - t))

# ---------- 剪辑单 ----------
# 每条: (音乐起点, 音乐终点, 源镜头中心时间, 风格)
# 风格: fill=居中竖切 | fillL/fillR=偏左/右 | punch=冲击缩放+抖动 | flash=白闪
#       rgb=色差故障 | push=缓推近 | stillbg=满幅模糊底 | slow=慢放
def beat_idx_near(t):
    return min(range(len(beats)), key=lambda i: abs(beats[i] - t))

def seq(start_t, n, step):
    """从 start_t 附近节拍起, 沿节拍列表按 step 步进取 n+1 个边界"""
    i0 = beat_idx_near(start_t)
    return [beats[min(i0 + k * step, len(beats) - 1)] for k in range(n + 1)]

EDL = []
def seg(ma, mb, center, style="fill"):
    EDL.append([ma, mb, center, style])

# A 铺垫 (v0-8): 两镜, 慢节奏
a_b = seq(188.0, 1, 8)          # 184 → ~188 → ~192, 每镜8拍
seg(M0, a_b[0], 206.0, "stillbg")   # 夕阳战场
seg(a_b[0], a_b[1], 15.2, "fill")   # 烟尘战场
# B 蓄势 (v8-24): 每2拍一切
b_pool_B = [51.2, 64.5, 99.0, 72.5, 132.8, 131.0, 25.0, 125.3, 126.6,
            145.5, 68.5, 170.0, 176.8, 252.8, 127.9]
b_b = seq(192.0, len(b_pool_B), 2)
for i, c in enumerate(b_pool_B):
    seg(b_b[i], b_b[i + 1], c, "punch" if i % 3 == 2 else ["fill", "fillL", "fillR"][i % 3])
# C 加速 (v~24-31): 每拍一切
c_end = b_b[-1]
b_pool_C = [137.5, 134.3, 112.5, 105.5, 77.5, 96.5, 91.0, 150.5,
            61.9, 96.5, 105.5, 175.2, 186.6]
c_b = seq(c_end, len(b_pool_C), 1)
for i, c in enumerate(b_pool_C):
    seg(c_b[i], c_b[i + 1], c, "flash" if i == len(b_pool_C) - 1 else ("punch" if i % 2 else "fill"))
# Pre-drop 蓄力: 慢镜 + 静默, 末端锚定在 drop 节拍上
pd3 = snap(222.0); pd2 = snap(220.0); pd1 = snap(219.0); pd0 = c_b[-1]
seg(pd0, pd1, 219.8, "push")      # 灰烬战场 缓推
seg(pd1, pd2, 236.9, "fill")      # 血色 一瞬
seg(pd2, pd3, 299.3, "slowm")      # 普莱斯特写 减速+推近强调 (静默+riser)
# DROP: 每拍一切
drop = [
    (299.3, "flash"), (236.9, "rgb"),  (256.7, "slowm"), (125.1, "punch"),
    (244.8, "flash"), (225.1, "flash"), (288.5, "punch"), (105.5, "flash"),
    (126.5, "rgb"),   (61.9, "punch"),  (293.9, "punch"), (233.0, "rgb"),
    (24.9, "punch"),  (192.8, "punch"), (252.8, "punch"), (121.0, "flash"),
    (229.0, "flash"), (68.5, "punch"),  (248.8, "punch"), (175.0, "rgb"),
    (145.5, "punch"), (186.6, "flash"), (183.5, "punch"), (377.6, "punch"),
    (169.8, "flash"), (384.8, "punch"), (130.9, "rgb"),   (283.2, "punch"),
    (15.5, "punch"),  (134.5, "punch"), (25.0, "punch"),  (240.9, "punch"),
    (393.6, "flash"), (299.3, "slowm"),
]
d_b = seq(pd3, len(drop), 1)
for i, (c, st) in enumerate(drop):
    seg(d_b[i], d_b[i + 1], c, st)
# 收尾定格
seg(d_b[-1], M1, 315.5, "stillbg")

# ---------- 校验 ----------
durs = [b - a for a, b, _, _ in EDL]
total = sum(durs)
print(f"clips={len(EDL)}  total={total:.2f}s (target {M1-M0:.2f}s)")
bad = [e for e in EDL if e[1] - e[0] <= 0.05]
if bad: sys.exit(f"BAD EDL: {bad}")

# 源镜头是否越出可用范围/跨检测切点
shots = json.load(open("work/shots.json"))
for i, (ma, mb, c, st) in enumerate(EDL):
    need = (mb - ma) / (0.6 if st == "slow" else 1.0)
    a, b = c - need / 2 - 0.05, c + need / 2 + 0.05
    for sa, sb in shots:
        if a < sa < b or a < sb < b:
            print(f"  WARN clip{i:02d} m{ma:.1f} src~{c} may cross cut {sa:.2f}-{sb:.2f}")

# ---------- 源窗口吸附: 把取用窗口整段放进宿主镜头内 ----------
def place(center, need):
    """返回调整后的源窗口起点; 无足够长的宿主镜头则返回 None"""
    hosts = [(sa, sb) for sa, sb in shots if sa - 0.02 <= center <= sb + 0.02]
    if not hosts:
        return center - need / 2
    sa, sb = max(hosts, key=lambda h: h[1] - h[0])   # 取最长宿主
    if sb - sa < need + 0.12:
        return None
    a = min(max(center - need / 2, sa + 0.06), sb - need - 0.06)
    return a

# ---------- 渲染每个中间镜头 ----------
W, H = 1080, 1920
for i, (ma, mb, c, st) in enumerate(EDL):
    out = f"work/clips/c{i:03d}.mp4"
    if os.path.exists(out):
        continue
    vd = mb - ma
    # xfade 转场对的后一个镜头延长渲染, 保证拼接后总时长不变
    extra = 0.22 if i == 30 else (0.18 if i in (2, 17, 67) else 0.0)
    vd_r = vd + extra
    if st in ("slowm",):
        need = vd_r / 0.6; pts = "1.6667*PTS"
    elif st == "pushs":
        need = vd_r / 0.85; pts = "1.1765*PTS"
    else:
        need = vd_r; pts = None
    vin = place(c, need)
    if vin is None:
        sys.exit(f"clip{i:02d} src~{c} 宿主镜头过短, 需换素材")
    vf = []
    if pts:
        vf.append("setpts=" + pts)
    if st == "stillbg" and i == len(EDL) - 1:
        # 结尾定格: 用精确截取的合影静帧, 模糊底 + 缓慢推近
        fc = ("split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
              "crop=1080:1920,boxblur=24:2,eq=brightness=-0.12[bgd];"
              "[fg]scale=1080:-2[fgs];[bgd][fgs]overlay=(W-w)/2:(H-h)/2,"
              "scale=2160:3840,zoompan=z='1+0.05*on/(30*%.2f)':d=1:"
              "x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=%dx%d:fps=30,"
              "fade=t=in:st=0:d=0.15:color=white" % (vd_r, W, H))
        cmd = [FF, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30",
               "-t", f"{vd_r:.3f}", "-i", "work/freeze.png",
               "-filter_complex", fc, "-r", "30", "-pix_fmt", "yuv420p",
               "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-an", out]
        subprocess.run(cmd, check=True)
        print(f"clip{i:03d} FREEZE {vd:.2f}s (still 315.6)")
        continue
    if st == "stillbg":
        vf.append(
            "split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=24:2,eq=brightness=-0.12[bgd];"
            "[fg]scale=1080:-2[fgs];[bgd][fgs]overlay=(W-w)/2:(H-h)/2")
        cmd_vf = ["-filter_complex", vf[0]]
    else:
        if st == "slowm":
            # 减速强调: 光流插帧慢放 0.6x + 持续推近放大
            zf = 0.22 if i == 32 else 0.15
            vf.append(
                f"crop=608:1080,"
                f"minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
                f"scale=2160:3840,"
                f"zoompan=z='1+{zf:.2f}*on/(30*{vd_r:.2f})':d=1:"
                f"x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s={W}x{H}:fps=30")
            if i == 66:
                vf.append("fade=t=in:st=0:d=0.12:color=white")
            if i == 32:
                vf.append("eq=brightness=-0.05:saturation=0.9")
        elif st in ("push", "pushs"):
            vf.append(f"crop=608:1080,scale=1620:2880,"
                      f"zoompan=z='1+0.16*on/(30*{vd:.2f})':d=1:"
                      f"x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s={W}x{H}:fps=30")
        elif st in ("fill", "fillL", "fillR", "slow"):
            off = {"fill": 0, "fillL": -90, "fillR": 90}[st]
            x = f"(iw-608)/2{off:+d}"
            vf.append(f"crop=608:1080:x='{x}':y=0,scale={W}:{H}")
        elif st in ("punch", "flash", "rgb"):
            # 段落边界镜头(2=B起,17=C起,33=drop起): 更强抖动 + 白闪入 + 色差
            bnd = i in (2, 17, 33)
            a1 = 26 if bnd else 14
            sgn = "1" if i % 2 else "-1"
            vf.append(
                f"crop=536:952:x='(iw-536)/2+({a1}*sin(45*t)*exp(-6*t))*{sgn}'"
                f":y='(ih-952)/2+({a1 * 0.6:.0f}*sin(37*t)*exp(-6*t))',"
                f"scale=1608:2856,"
                f"zoompan=z='{1.30 if i == 33 else 1.18:.2f}-{0.30 if i == 33 else 0.18:.2f}*min(1,on/(30*{0.15 if i == 33 else 0.16:.2f}))':d=1:"
                f"x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1608x2856:fps=30,"
                f"crop=1560:2772:x='(iw-1560)/2+(22*sin(51*t)*exp(-7*t))*{sgn}'"
                f":y='(ih-2772)/2+(14*sin(43*t)*exp(-7*t))',"
                f"scale={W}:{H}")
        if st == "flash" or i in (2, 17):
            vf.append("fade=t=in:st=0:d=0.12:color=white")
        if st == "rgb" or i == 33:
            vf.append("rgbashift=rh=8:bh=-8")
        if st == "pushs":
            vf.append("eq=brightness=-0.06:saturation=0.9")
        cmd_vf = ["-vf", ",".join(vf)]
    cmd = [FF, "-y", "-loglevel", "error", "-ss", f"{vin:.3f}", "-i", SRC]
    if pts:
        cmd += ["-t", f"{need:.3f}"]
    cmd += cmd_vf
    cmd += ["-t", f"{vd_r:.3f}", "-r", "30", "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-an", out]
    subprocess.run(cmd, check=True)
    print(f"clip{i:03d} m{ma:6.2f}-{mb:6.2f} src{vin:7.2f}+{need:.2f} {st:8s} -> {vd:.2f}s")

with open("work/concat.txt", "w") as f:
    for i in range(len(EDL)):
        f.write(f"file 'clips/c{i:03d}.mp4'\n")
json.dump(EDL, open("work/edl.json", "w"), indent=1)
print("ALL CLIPS DONE")
