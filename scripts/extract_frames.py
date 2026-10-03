#!/usr/bin/env python3
"""Extract video frames at specified timestamps using opencv-python.

The camera thumbnail can be painted out with --mask, and frames that are nearly
identical to an image already in the output directory (for example one saved by
detect_screen_changes.py) are skipped unless --keep-duplicates is given.
"""

import argparse
import glob
import json
import os
import sys

from video_utils import (FILL_MODES, apply_mask, changed_fraction, cv2, grab_filename,
                         open_video, parse_mask, read_at, small_gray)


def extract(video_path: str, output_dir: str, timestamps: list[float], offset: float = 2.0,
            mask=None, fill: str = "auto", keep_duplicates: bool = False, same: float = 0.01):
    os.makedirs(output_dir, exist_ok=True)
    cap, _, _, _, _ = open_video(video_path)

    existing = []
    if not keep_duplicates:
        for path in sorted(glob.glob(os.path.join(output_dir, "*.png"))):
            img = cv2.imread(path)
            if img is not None:
                existing.append(small_gray(img))

    extracted = skipped = 0
    for ts in timestamps:
        target = ts + offset
        filename = grab_filename(output_dir, target)
        if os.path.exists(filename) and not keep_duplicates:
            skipped += 1
            continue
        frame = read_at(cap, target)
        if frame is None:
            continue
        frame = apply_mask(frame, mask, fill)
        if not keep_duplicates:
            small = small_gray(frame)
            if any(changed_fraction(small, e) < same for e in existing):
                skipped += 1
                continue
            existing.append(small)
        cv2.imwrite(filename, frame)
        extracted += 1

    cap.release()
    note = f" ({skipped} skipped as duplicates of existing frames)" if skipped else ""
    print(f"Extracted {extracted} frames to {output_dir}/{note}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract video frames at timestamps")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("output_dir", help="Directory to save PNGs (e.g., screenshots/)")
    parser.add_argument("timestamps", help="JSON array of timestamps in seconds, e.g. '[2700, 2850, 3000]'")
    parser.add_argument("--offset", type=float, default=2.0, help="Seconds to add to each timestamp (default: 2.0)")
    parser.add_argument("--mask", help="Camera thumbnail to paint out, as x,y,w,h pixels (from detect_camera_overlay.py)")
    parser.add_argument("--fill", choices=FILL_MODES, default="auto",
                        help="How to paint out the thumbnail (default: auto = match surrounding color)")
    parser.add_argument("--keep-duplicates", action="store_true",
                        help="Save every frame even if it matches one already in the output directory")
    args = parser.parse_args()
    try:
        mask = parse_mask(args.mask)
    except ValueError as e:
        sys.exit(f"Error: {e}")
    extract(args.video_path, args.output_dir, json.loads(args.timestamps), args.offset,
            mask, args.fill, args.keep_duplicates)
