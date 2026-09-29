#!/usr/bin/env python3
"""Find the moments a screen recording settles on something new, such as a slide
advance, a new window, or the result of a command, and optionally save a frame
for each one.

The video is scanned once, one frame per --step seconds, with the camera
thumbnail masked out so the speaker moving doesn't count as a change. A moment
is kept when the screen has held still for --settle seconds and differs from
the last kept frame by more than --min-change of its pixels.

Prints a JSON list of {"t", "time", "change", "file"} objects.
"""

import argparse
import json
import os
import sys

from video_utils import (FILL_MODES, apply_mask, changed_fraction, cv2, grab_filename,
                         hhmmss, open_video, parse_mask, small_gray)


def detect(video_path, mask=None, fill="auto", step=1.0, settle=2.0, min_change=0.03,
           still=0.002, min_gap=5.0, output_dir=None):
    cap, fps, duration, _, _ = open_video(video_path)
    stride = max(1, round(step * fps))
    settle_samples = max(1, round(settle / step))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    kept, prev, last_kept, last_kept_t, still_count = [], None, None, -min_gap, 0
    index = 0
    while True:
        if not cap.grab():
            break
        index += 1
        if (index - 1) % stride:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            break
        t = (index - 1) / fps
        frame = apply_mask(frame, mask, fill)
        cur = small_gray(frame)

        still_count = still_count + 1 if prev is not None and changed_fraction(cur, prev) < still else 0
        prev = cur
        if still_count < settle_samples or t - last_kept_t < min_gap:
            continue
        change = 1.0 if last_kept is None else changed_fraction(cur, last_kept)
        if change < min_change:
            continue

        entry = {"t": round(t, 1), "time": hhmmss(t), "change": round(change, 3)}
        if output_dir:
            entry["file"] = grab_filename(output_dir, t)
            cv2.imwrite(entry["file"], frame)
        kept.append(entry)
        last_kept, last_kept_t = cur, t
        if len(kept) % 25 == 0:
            print(f"  {len(kept)} screens so far (at {hhmmss(t)} of {hhmmss(duration)})", file=sys.stderr)

    cap.release()
    return kept


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect screen changes in a lecture recording")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--mask", help="Camera thumbnail to paint out, as x,y,w,h pixels (from detect_camera_overlay.py)")
    parser.add_argument("--fill", choices=FILL_MODES, default="auto",
                        help="How to paint out the thumbnail (default: auto = match surrounding color)")
    parser.add_argument("--extract", metavar="DIR", help="Also save a frame for each detected screen into DIR")
    parser.add_argument("--step", type=float, default=1.0, help="Seconds between sampled frames (default: 1.0)")
    parser.add_argument("--settle", type=float, default=2.0,
                        help="Seconds the screen must hold still before it is captured (default: 2.0)")
    parser.add_argument("--min-change", type=float, default=0.03,
                        help="Fraction of pixels that must differ from the last capture (default: 0.03)")
    parser.add_argument("--min-gap", type=float, default=5.0, help="Minimum seconds between captures (default: 5.0)")
    parser.add_argument("--output", "-o", help="Write the JSON list here instead of stdout")
    args = parser.parse_args()

    screens = detect(args.video_path, parse_mask(args.mask), args.fill, args.step, args.settle,
                     args.min_change, min_gap=args.min_gap, output_dir=args.extract)
    text = json.dumps(screens, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
    else:
        print(text)
    where = f" into {args.extract}/" if args.extract else ""
    print(f"Detected {len(screens)} distinct screens{where}", file=sys.stderr)
