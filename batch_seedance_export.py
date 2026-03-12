#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量处理：
- 遍历目录内视频
- 逐个调用 extract_video_prompt.py 生成 analysis.json
- 一键导出三套 Seedance 提示词（电影感/短剧感/广告感）

示例：
python batch_seedance_export.py \
  --input-dir ./videos \
  --output-dir ./batch_out \
  --fps 1 \
  --ratio 16:9 \
  --duration 15
"""

import argparse
import subprocess
from pathlib import Path
from typing import List


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def run_cmd(cmd: List[str]):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"命令失败: {' '.join(cmd)}\n{p.stdout}")
    return p.stdout


def collect_videos(input_dir: Path) -> List[Path]:
    videos = [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    return sorted(videos)


def make_topic_from_filename(video_path: Path) -> str:
    name = video_path.stem.replace("_", " ").replace("-", " ").strip()
    return name if name else "视频二次创作"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, help="视频目录（支持递归）")
    parser.add_argument("--output-dir", default="./batch_out", help="批量输出目录")
    parser.add_argument("--fps", type=float, default=1.0, help="抽帧频率")
    parser.add_argument("--ratio", default="16:9", help="输出比例")
    parser.add_argument("--duration", type=int, default=15, help="目标时长")
    parser.add_argument("--model", default="Salesforce/blip-image-captioning-base", help="caption 模型")
    parser.add_argument("--device", default="", help="cuda 或 cpu，留空自动")
    parser.add_argument("--topic-prefix", default="", help="统一主题前缀，如：国风武侠：")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    videos = collect_videos(input_dir)
    if not videos:
        raise RuntimeError(f"未找到视频文件: {input_dir}")

    base_dir = Path(__file__).resolve().parent
    extract_script = base_dir / "extract_video_prompt.py"
    build_script = base_dir / "build_seedance_prompt.py"

    success = 0
    failed = []

    for i, video in enumerate(videos, start=1):
        print(f"\n[{i}/{len(videos)}] 处理中: {video}")
        try:
            item_out = output_dir / video.stem
            item_out.mkdir(parents=True, exist_ok=True)

            analysis_out = item_out / "analysis"
            analysis_json = analysis_out / "analysis.json"

            # 1) 视频分析
            cmd_extract = [
                "python", str(extract_script),
                "--video", str(video),
                "--outdir", str(analysis_out),
                "--fps", str(args.fps),
                "--model", args.model,
            ]
            if args.device:
                cmd_extract += ["--device", args.device]
            run_cmd(cmd_extract)

            # 2) 导出三套风格 Seedance 提示词
            topic = f"{args.topic_prefix}{make_topic_from_filename(video)}".strip()
            prompt_out = item_out / "seedance_prompts.txt"
            cmd_build = [
                "python", str(build_script),
                "--analysis", str(analysis_json),
                "--topic", topic,
                "--duration", str(args.duration),
                "--ratio", args.ratio,
                "--all-styles",
                "--out", str(prompt_out),
            ]
            run_cmd(cmd_build)

            print(f"✅ 完成: {prompt_out}")
            success += 1
        except Exception as e:
            print(f"❌ 失败: {video} -> {e}")
            failed.append((video, str(e)))

    print("\n================ 批量任务完成 ================")
    print(f"成功: {success}")
    print(f"失败: {len(failed)}")
    if failed:
        print("失败列表:")
        for v, err in failed:
            print(f"- {v}: {err}")


if __name__ == "__main__":
    main()
