#!/usr/bin/env python3
"""Extract video frames at specified timestamps using opencv-python."""

import argparse
import json
import os
import sys

try:
    import cv2
except ImportError:
    print("opencv-python not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "-q"])
    import cv2


def extract(video_path: str, output_dir: str, timestamps: list[float], offset: float = 2.0):
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    extracted = 0

    for ts in timestamps:
        target = ts + offset
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(target * fps))
        ret, frame = cap.read()
        if ret:
            h = int(target // 3600)
            m = int((target % 3600) // 60)
            s = int(target % 60)
            filename = os.path.join(output_dir, f"auto_{h:02d}{m:02d}{s:02d}.png")
            cv2.imwrite(filename, frame)
            extracted += 1

    cap.release()
    print(f"Extracted {extracted} frames to {output_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract video frames at timestamps")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("output_dir", help="Directory to save PNGs (e.g., screenshots/)")
    parser.add_argument("timestamps", help="JSON array of timestamps in seconds, e.g. '[2700, 2850, 3000]'")
    parser.add_argument("--offset", type=float, default=2.0, help="Seconds to add to each timestamp (default: 2.0)")
    args = parser.parse_args()
    timestamps = json.loads(args.timestamps)
    extract(args.video_path, args.output_dir, timestamps, args.offset)
