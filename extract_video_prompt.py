#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最小可跑方案：视频 -> 抽帧 -> 开源图像描述模型逐帧 caption -> 结构化输出 JSON

依赖：
- ffmpeg 可执行文件
- pip install -r requirements.txt

示例：
python extract_video_prompt.py \
  --video demo.mp4 \
  --outdir ./out \
  --fps 1
"""

import argparse
import json
import math
import os
import subprocess
from pathlib import Path
from typing import List, Dict

from PIL import Image
from tqdm import tqdm

import torch
from transformers import BlipProcessor, BlipForConditionalGeneration


def run_cmd(cmd: List[str]):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"命令失败: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def get_video_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    out = run_cmd(cmd).strip()
    return float(out)


def extract_frames(video_path: str, frames_dir: Path, fps: float):
    ensure_dir(frames_dir)
    out_pattern = str(frames_dir / "frame_%06d.jpg")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",
        out_pattern
    ]
    run_cmd(cmd)


def list_frames(frames_dir: Path) -> List[Path]:
    return sorted(frames_dir.glob("frame_*.jpg"))


def sec_of_index(i: int, fps: float) -> float:
    # frame_000001 对应 i=0 -> t=0
    return i / fps


def load_model(model_name: str, device: str):
    processor = BlipProcessor.from_pretrained(model_name)
    model = BlipForConditionalGeneration.from_pretrained(model_name)
    model.to(device)
    model.eval()
    return processor, model


def caption_image(processor, model, img_path: Path, device: str, max_new_tokens: int = 40) -> str:
    image = Image.open(img_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens)
    text = processor.decode(out[0], skip_special_tokens=True)
    return " ".join(text.strip().split())


def compress_timeline(captions: List[Dict], min_seg_len_sec: float = 1.5):
    """简单分段：相邻 caption 完全一致归并；太短段会尝试并入前段"""
    if not captions:
        return []

    segments = []
    cur = {
        "start": captions[0]["time"],
        "end": captions[0]["time"],
        "caption": captions[0]["caption"],
    }

    for item in captions[1:]:
        if item["caption"] == cur["caption"]:
            cur["end"] = item["time"]
        else:
            segments.append(cur)
            cur = {"start": item["time"], "end": item["time"], "caption": item["caption"]}
    segments.append(cur)

    # 修正结束时间（每帧代表一个采样点，给个最小跨度）
    for i in range(len(segments)):
        if i < len(segments) - 1:
            segments[i]["end"] = max(segments[i]["end"], segments[i+1]["start"])
        else:
            segments[i]["end"] = max(segments[i]["end"], segments[i]["start"] + 0.5)

    merged = []
    for seg in segments:
        seg_len = seg["end"] - seg["start"]
        if merged and seg_len < min_seg_len_sec:
            # 短段合并到前一段，保留更多信息
            merged[-1]["end"] = seg["end"]
            if seg["caption"] not in merged[-1]["caption"]:
                merged[-1]["caption"] = merged[-1]["caption"] + "; then " + seg["caption"]
        else:
            merged.append(seg)

    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="输入视频路径")
    parser.add_argument("--outdir", default="./out", help="输出目录")
    parser.add_argument("--fps", type=float, default=1.0, help="抽帧频率（每秒几帧）")
    parser.add_argument("--model", default="Salesforce/blip-image-captioning-base", help="caption 模型")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"视频不存在: {video_path}")

    outdir = Path(args.outdir)
    frames_dir = outdir / "frames"
    ensure_dir(outdir)

    print("[1/4] 抽帧中...")
    extract_frames(str(video_path), frames_dir, args.fps)
    frames = list_frames(frames_dir)
    if not frames:
        raise RuntimeError("没有抽取到帧，请检查 ffmpeg 或视频文件")

    print(f"[2/4] 加载模型: {args.model} ({args.device})")
    processor, model = load_model(args.model, args.device)

    print("[3/4] 逐帧描述中...")
    frame_caps = []
    for idx, f in enumerate(tqdm(frames)):
        t = sec_of_index(idx, args.fps)
        cap = caption_image(processor, model, f, args.device)
        frame_caps.append({
            "index": idx,
            "time": round(t, 3),
            "frame": str(f),
            "caption": cap
        })

    print("[4/4] 生成结构化输出...")
    duration = get_video_duration(str(video_path))
    segments = compress_timeline(frame_caps)

    result = {
        "video": str(video_path),
        "duration": duration,
        "fps_sample": args.fps,
        "model": args.model,
        "frame_captions": frame_caps,
        "timeline_segments": segments,
    }

    json_path = outdir / "analysis.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"完成: {json_path}")


if __name__ == "__main__":
    main()
