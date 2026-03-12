#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
把 analysis.json 自动转为 Seedance 2.0 可用中文提示词模板。
支持：
1) 单风格导出
2) 一键导出多风格（电影感/短剧感/广告感）

示例：
python build_seedance_prompt.py \
  --analysis ./out/analysis.json \
  --topic "张三丰大战灭绝师太" \
  --duration 15 \
  --ratio 16:9 \
  --all-styles \
  --out ./out/seedance_prompt.txt
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple


STYLE_PRESETS: Dict[str, str] = {
    "movie": "电影感，高对比光影，镜头语言丰富，叙事张力强",
    "drama": "短剧感，情绪冲突明显，人物关系清晰，节奏紧凑",
    "ad": "广告感，产品级构图，画面干净利落，质感高级，节奏明快",
}

STYLE_CN_NAME = {
    "movie": "电影感",
    "drama": "短剧感",
    "ad": "广告感",
}


def mmss(sec: float) -> str:
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m:02d}:{s:02d}"


def segment_line(seg: dict) -> str:
    s = mmss(seg["start"])
    e = mmss(seg["end"])
    return f"{s}-{e}：{seg['caption']}"


def build_prompt(topic: str, duration: int, ratio: str, style: str, segments: list) -> str:
    timeline = "\n".join([segment_line(s) for s in segments[:12]])

    prompt = f"""{duration}秒，{ratio}，24fps，{style}。
主题：{topic}。

请基于以下分镜参考生成连续视频，保持主体一致、动作连贯、镜头自然过渡：
{timeline}

画面要求：
- 强化镜头语言：推镜、跟拍、环绕、特写与全景交替
- 强化光影与氛围：风、尘、烟、体积光、动态阴影
- 动作节奏清晰：起势、冲突、爆发、收势
- 避免画面抖动和角色崩坏

音效要求：
- 根据动作自动生成环境音与打击音
- 音乐随节奏推进，高潮段增强低频与冲击感

禁止项：
- 不要字幕、文字、LOGO、水印
- 不要现代穿帮元素（现代建筑、电子设备、现代服饰）
"""
    return prompt


def build_shot_breakdown(segments: list, duration: int) -> str:
    if not segments:
        return ""

    src_end = max(s["end"] for s in segments)
    scale = duration / src_end if src_end > 0 else 1.0

    lines = []
    for s in segments[:8]:
        start = max(0, int(round(s["start"] * scale)))
        end = min(duration, max(start + 1, int(round(s["end"] * scale))))
        lines.append(f"{start}-{end}秒：{s['caption']}")
    return "\n".join(lines)


def build_style_block(style_label: str, style_text: str, topic: str, duration: int, ratio: str, segments: List[dict]) -> str:
    main_prompt = build_prompt(
        topic=topic,
        duration=duration,
        ratio=ratio,
        style=style_text,
        segments=segments,
    )
    shot_breakdown = build_shot_breakdown(segments, duration)

    return f"""## {style_label}

### 版本A：直接可用主提示词
{main_prompt}

### 版本B：时间戳分镜版（便于微调）
{duration}秒，{ratio}，24fps，{style_text}。
主题：{topic}

分镜：
{shot_breakdown}

音效：根据每段动作自动生成环境音、打击音与氛围音乐。
禁止：字幕、LOGO、水印、现代元素。
"""


def resolve_styles(args) -> List[Tuple[str, str]]:
    if args.all_styles:
        return [(STYLE_CN_NAME[k], STYLE_PRESETS[k]) for k in ["movie", "drama", "ad"]]

    # 自定义 style 优先
    if args.style:
        return [("自定义风格", args.style)]

    # 默认电影感
    return [(STYLE_CN_NAME["movie"], STYLE_PRESETS["movie"])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", required=True, help="extract_video_prompt.py 输出的 analysis.json")
    parser.add_argument("--topic", required=True, help="二创主题")
    parser.add_argument("--duration", type=int, default=15, help="目标视频时长")
    parser.add_argument("--ratio", default="16:9", help="画面比例，如 16:9 / 9:16")
    parser.add_argument("--style", default="", help="单风格描述（留空则默认电影感）")
    parser.add_argument("--all-styles", action="store_true", help="一键导出电影感/短剧感/广告感三套")
    parser.add_argument("--out", default="seedance_prompt.txt", help="输出文本文件")
    args = parser.parse_args()

    p = Path(args.analysis)
    if not p.exists():
        raise FileNotFoundError(f"analysis 文件不存在: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))
    segments = data.get("timeline_segments", [])

    style_blocks = []
    for style_label, style_text in resolve_styles(args):
        style_blocks.append(
            build_style_block(
                style_label=style_label,
                style_text=style_text,
                topic=args.topic,
                duration=args.duration,
                ratio=args.ratio,
                segments=segments,
            )
        )

    final_text = "# Seedance 2.0 二创提示词（自动生成）\n\n" + "\n\n---\n\n".join(style_blocks)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_text, encoding="utf-8")
    print(f"已生成: {out_path.resolve()}")


if __name__ == "__main__":
    main()
