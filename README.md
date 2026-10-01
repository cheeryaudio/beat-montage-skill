# beat-montage-skill

**卡点燃剪混剪 Agent Skill** —— 把"几段游戏/影视片段 + 一首 DJ 歌"变成一支节拍卡点的竖屏燃剪短片。

为 [ZCode / Claude Code 类 Agent Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) 设计：
SKILL.md 即编辑手册，scripts/ 是从真实项目中跑通的参数化模板
（ demo：琵琶行 DJ 名龙版 × 使命召唤：现代战争，27.5s 竖屏成片）。

## 它做什么

```
素材片段 + DJ 歌曲
   │
   ├─ 1. librosa 节拍/能量/drop 检测          → beats.json
   ├─ 2. 场景切点检测 + 缩略图墙 + 亮度图谱    → 镜头清单(逐个"看"过)
   ├─ 3. EDL 剪辑单: 铺垫→蓄势→静默→drop→定格  → 按 112BPM 实测节拍对齐
   ├─ 4. 逐镜头渲染: 缩放冲击/白闪/色差/慢放    (无 blend 链)
   ├─ 5. PIL 逐帧动画: 书法字幕砸入/末字金/印章/墨点/墨扫
   └─ 6. 三段式渲染: 安全滤镜图 → PIL 合成 → x264 + 混音
        → 1080×1920 竖屏成片
```

## 为什么要用它（而不是直接手写 ffmpeg 滤镜图）

我们在 Windows + imageio-ffmpeg/BtbN 构建上实测踩过一整套**深坑**，
每一条都复现过、定位过、给出了解法（详见 SKILL.md「已知深坑」与 `docs/pitfalls.md`）：

| 坑 | 症状 | 解法 |
|---|---|---|
| blend 输出直连 overlay | 画面整体变绿（色度平面损坏） | 每个 blend 后插 `scale` 屏障 |
| zoompan/动态尺寸 overlay 链 | 同样变绿且**非确定**（时好时坏） | 动画全部改 PIL 预渲染序列 |
| image2 帧序列作 overlay 输入 | 同上 | 动画走 pass B 的 PIL 合成 |
| graph → rawvideo 输出 | mkv/png 干净、rawvideo 变绿 | 中间产物用 ffv1/文件交接 |
| ffv1 中间文件(master 构建) | 解码在 ~700 帧处卡死 | 调色直进管道, 不落中间文件 |
| 管道 `dec.wait()` | 永久挂起 | 读完全部帧后 `dec.kill()` |
| `-i list.txt` 忘加 `-f concat` | 列表被当 ansi 视频喂进图 | 对比实验带齐 `-f concat` |

> 其中 blend→overlay 色度损坏在 **上游最新 master 构建（2026-09-30）上同样复现**，
> 是上游真 bug——scale 屏障方案长期有效，升级 ffmpeg 后请回归测试。

## 编辑理念（SKILL.md 里有完整十条）

高潮 ≠ 能量最大处；前 3 秒钩子法则；速度梯度拒绝等长快切；
S 级镜头省着用；卡点卡在"动作起始帧"；静默要真的静；
实录与电影镜头交替；drop 调色加码；文字少而狠。

## 使用

1. 把 `SKILL.md` 与 `scripts/` 放入 Agent 的技能目录
   （ZCode: `~/.zcode/skills/beat-montage/`；Claude Code: `~/.claude/skills/beat-montage/`）
2. 准备：素材片段（游戏/影视击杀集锦）+ DJ 歌曲（mp3）+ 一款书法/重型字体
3. 对 Agent 说："用 xx 歌的高潮和这些素材剪一支卡点燃剪"——按 SKILL.md 工作流执行
4. 依赖：`pip install librosa pillow numpy`，ffmpeg 任意较新构建
   （本机深坑规避已内置，其他平台请自行回归测试）

## 免责与素材

- 仓库只包含**管线代码与文档**，不包含任何歌曲、游戏画面、字体文件（各有各自版权）
- 请使用你拥有 rights 的素材，成片仅供个人创作使用

## License

MIT
