# 模板说明

这五个脚本来自已跑通的项目（琵琶行DJ名龙版 × MW系列 58.5s 竖屏混剪），是参数化模板：
- beat_analysis.py  节拍/能量/drop 检测（librosa）→ beats.json
- build_clips.py    按 EDL 渲染中间镜头（含镜头边界吸附 place()）
- make_transitions.py  xfade 段落转场拼接（注意后镜头加长补偿）
- gen_frames.py     PIL 动画序列：书法歌词砸入/末字金/印章盖章/墨点/墨扫
- pipe_render.py    三段式最终渲染（mkv→PIL合成→x264），含 blend 色度 bug 规避

使用：换新项目时改其中的 时间轴/歌词/EDL 常量，架构与坑位规避保持不动。
