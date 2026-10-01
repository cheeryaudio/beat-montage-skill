import json
import librosa
import numpy as np

y, sr = librosa.load("music/pipa_dj.mp3", sr=22050, mono=True)
dur = len(y) / sr

# 节拍与起搏
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", trim=False)
beat_times = [round(float(t), 3) for t in beats]

# 能量曲线 (每 0.5s 一格), 找高能段落
hop = 512
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
frame_t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
# 每 5s 求均值能量
bin_sec = 5
bins = []
for start in np.arange(0, dur, bin_sec):
    m = (frame_t >= start) & (frame_t < start + bin_sec)
    if m.any():
        bins.append((round(float(start), 1), round(float(rms[m].mean()), 5)))

# 音量突变点 (drop 通常伴随能量阶跃): 比较 1s 能量 vs 前 3s
win = int(sr * 1.0)
pre = int(sr * 3.0)
jumps = []
for i in range(pre, len(y) - win, int(sr * 0.5)):
    e_now = float(np.sqrt(np.mean(y[i : i + win] ** 2)))
    e_pre = float(np.sqrt(np.mean(y[i - pre : i] ** 2)))
    if e_now > 0 and e_now / max(e_pre, 1e-6) > 1.35:
        jumps.append((round(i / sr, 1), round(e_now / max(e_pre, 1e-6), 2)))

# 合并相邻跳变
merged = []
for t, r in jumps:
    if merged and t - merged[-1][0] < 3:
        if r > merged[-1][1]:
            merged[-1] = [t, r]
    else:
        merged.append([t, r])

out = {
    "duration": round(dur, 2),
    "tempo": round(float(np.atleast_1d(tempo)[0]), 1),
    "n_beats": len(beat_times),
    "energy_bins_5s": bins,
    "energy_jumps": merged,
}
with open("work/beats.json", "w") as f:
    json.dump({**out, "beat_times": beat_times}, f, ensure_ascii=False, indent=1)

print("duration:", out["duration"], " tempo:", out["tempo"], " beats:", len(beat_times))
print("energy jumps (drop candidates):", merged)
print("energy profile per 5s:")
for t, e in bins:
    bar = "#" * int(e * 600)
    print(f"  {t:6.1f}s {e:.4f} {bar}")
