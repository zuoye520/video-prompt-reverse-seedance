# 视频逆向提词（本地最小版）

目标：把视频自动拆解为文字描述，并生成可用于 Seedance 2.0 的二创提示词。

## 1) 环境准备

```bash
cd /root/.openclaw/workspace/video_prompt_reverse
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

安装 ffmpeg（若未安装）：

```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y ffmpeg
```

检查：

```bash
ffmpeg -version
python -c "import torch; print('torch ok')"
```

---

## 2) 从视频提取描述

```bash
python extract_video_prompt.py \
  --video /path/to/your/video.mp4 \
  --outdir ./out \
  --fps 1
```

输出：
- `./out/frames/`：抽帧图片
- `./out/analysis.json`：逐帧描述 + 时间线分段

> `--fps 1` 通常够用；运镜复杂视频可试 `--fps 2`。

---

## 3) 自动转 Seedance 2.0 提示词

```bash
python build_seedance_prompt.py \
  --analysis ./out/analysis.json \
  --topic "你的二创主题" \
  --duration 15 \
  --ratio 16:9 \
  --style "电影级写实风，强运镜" \
  --out ./out/seedance_prompt.txt
```

输出：
- `./out/seedance_prompt.txt`
  - 版本A：直接可贴到 Seedance 的主提示词
  - 版本B：时间戳分镜版（方便精修）

---

## 4) 实战建议

1. 先跑一次 `fps=1`，看结果是否抓住主体和动作。
2. 若节奏不准，升到 `fps=2` 再重跑。
3. 对 `seedance_prompt.txt` 做人工微调：
   - 加“风格词”（如：赛博朋克、水墨、纪录片）
   - 加“禁止项”（字幕、LOGO、水印、现代穿帮）
   - 把关键段落改成更明确动作描述

---

## 5) 局限说明（很重要）

- 这是“逆向重建提示词”，不是还原原作者真实提示词。
- 逐帧 caption 对复杂镜头、隐喻剧情、特效语义不一定稳定。
- 建议把它作为“草稿生成器 + 人工精修”的流水线。
