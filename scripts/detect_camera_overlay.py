#!/usr/bin/env python3
"""Find the speaker's camera thumbnail that Zoom overlays on a shared-screen
recording, so it can be painted out of screen grabs.

The thumbnail is a fixed rectangle flush against one corner of the frame (the
top-right in Zoom's "shared screen with active speaker" layout). Screen content
changes over a lecture, but the thumbnail's border stays in the same place, so
the detector looks for a corner-anchored rectangle whose inner edges are present
in most sampled frames.

Prints JSON with the box and a ready-to-use --mask argument, and writes a check
image (the box outlined in red over a labelled 10% grid) so the result can be
confirmed by eye.
"""

import argparse
import json
import os

from video_utils import cv2, np, open_video, read_at

WORK_WIDTH = 480
CORNERS = ("top-right", "top-left", "bottom-right", "bottom-left")


def to_canonical(a, corner):
    """Flip a map so the given corner becomes the top-left origin."""
    if "right" in corner:
        a = a[:, ::-1]
    if "bottom" in corner:
        a = a[::-1, :]
    return a


def edge_persistence(frames, informative=0.2):
    """Per pixel: how reliably a vertical / horizontal edge sits there.

    Returns (pv, iv, ph, ih). pv/ph is the fraction of frames with an edge,
    counted only over frames where the neighbourhood has any detail at all, and
    iv/ih marks pixels that had detail often enough to judge. A boundary that
    runs through black-on-black (a dark camera image next to a letterbox bar)
    carries no evidence either way, so it is ignored rather than counted as a
    missing edge.
    """
    ev = np.zeros(frames[0].shape, dtype=np.float32)
    eh = np.zeros_like(ev)
    active = np.zeros_like(ev)
    kernel_v = np.ones((1, 3), np.uint8)
    kernel_h = np.ones((3, 1), np.uint8)
    kernel_a = np.ones((3, 3), np.uint8)
    for g in frames:
        gx = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)) > 40
        gy = np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)) > 40
        # Dilate across the edge so a one-pixel wobble from scaling still counts.
        ev += cv2.dilate(gx.astype(np.uint8), kernel_v)
        eh += cv2.dilate(gy.astype(np.uint8), kernel_h)
        active += cv2.dilate((gx | gy).astype(np.uint8), kernel_a)
    n = len(frames)
    seen = active / n >= informative
    safe = np.maximum(active, 1)
    pv = np.where(seen, ev / safe, 0).astype(np.float32)
    ph = np.where(seen, eh / safe, 0).astype(np.float32)
    return pv, seen.astype(np.float32), ph, seen.astype(np.float32)


def best_rectangle(pv, iv, ph, ih, std, min_frac, max_frac, min_coverage=0.3, min_std=5.0, tie=0.03):
    """Search corner-anchored rectangles; score = weaker of the two inner edges.

    Each edge scores the mean persistence over the pixels along it that carry
    evidence, and must carry evidence along at least min_coverage of its length.
    A real overlay sits on changing content: the camera image inside it or the
    shared screen around it varies over the lecture. Boxes where neither varies
    (min_std, in gray levels) are just static page layout and are rejected.
    Static things inside the camera view (a projector screen, a door frame) can
    form a smaller rectangle nested in the same corner that scores as well as
    the thumbnail itself, so among near-equal scores the largest box wins.
    """
    H, W = pv.shape
    wmin, wmax = max(4, int(W * min_frac)), int(W * max_frac)
    hmin, hmax = max(4, int(H * min_frac)), int(H * max_frac)
    hs = np.arange(hmin, hmax)[:, None]
    ws = np.arange(wmin, wmax)[None, :]

    def along_columns(a):  # sum of rows [0, h) in column w
        return np.vstack([np.zeros((1, W)), np.cumsum(a, axis=0)])[hmin:hmax, wmin:wmax]

    def along_rows(a):  # sum of columns [0, w) in row h
        return np.hstack([np.zeros((H, 1)), np.cumsum(a, axis=1)])[hmin:hmax, wmin:wmax]

    band = max(3, int(W * 0.03))
    best = None
    for corner in CORNERS:
        v, vi = to_canonical(pv, corner), to_canonical(iv, corner)
        h, hi = to_canonical(ph, corner), to_canonical(ih, corner)
        # Right edge at column w over rows [0, h); bottom edge at row h over cols [0, w).
        r_seen, b_seen = along_columns(vi), along_rows(hi)
        right = along_columns(v) / np.maximum(r_seen, 1)
        bottom = along_rows(h) / np.maximum(b_seen, 1)
        covered = (r_seen / hs >= min_coverage) & (b_seen / ws >= min_coverage)
        # Mean temporal variation inside the box and in a band just outside it.
        integral = cv2.integral(np.ascontiguousarray(to_canonical(std, corner)).astype(np.float64))
        inner = integral[hs, ws]
        hb, wb = np.minimum(hs + band, H), np.minimum(ws + band, W)
        outer = (integral[hb, wb] - inner) / np.maximum(hb * wb - hs * ws, 1)
        varying = np.maximum(inner / (hs * ws), outer) >= min_std
        score = np.where(covered & varying, np.minimum(right, bottom), 0)
        top = float(score.max())
        area = np.where(score >= top - tie, hs * ws, 0)
        i, j = np.unravel_index(np.argmax(area), area.shape)
        cand = (top, corner, int(ws[0, j]), int(hs[i, 0]))
        if best is None or top > best[0]:
            best = cand
    return best


def to_box(corner, w, h, W, H, scale, full_w, full_h, pad=1):
    """Canonical (w, h) at work scale -> x, y, w, h in full-resolution pixels."""
    bw = min(full_w, int(round((w + pad) * scale)))
    bh = min(full_h, int(round((h + pad) * scale)))
    x = full_w - bw if "right" in corner else 0
    y = full_h - bh if "bottom" in corner else 0
    return [x, y, bw, bh]


def write_check_image(frame, box, path):
    img = frame.copy()
    H, W = img.shape[:2]
    for k in range(1, 10):
        x, y = W * k // 10, H * k // 10
        cv2.line(img, (x, 0), (x, H), (255, 200, 0), 1)
        cv2.line(img, (0, y), (W, y), (255, 200, 0), 1)
        cv2.putText(img, str(x), (x + 3, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 120, 0), 1)
        cv2.putText(img, str(y), (3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 120, 0), 1)
    if box:
        x, y, w, h = box
        cv2.rectangle(img, (x, y), (x + w - 1, y + h - 1), (0, 0, 255), 3)
    cv2.imwrite(path, img)


def clearest_frame(frames, corner, w, h):
    """Index of the sampled frame where the box's inner edges are most visible
    (so the check image shows the thumbnail, not a full-screen camera shot)."""
    def strength(g):
        c = to_canonical(g.astype(np.float32), corner)
        return np.abs(c[:h, w] - c[:h, w - 1]).mean() + np.abs(c[h, :w] - c[h - 1, :w]).mean()
    return int(np.argmax([strength(g) for g in frames]))


def detect(video_path, samples=60, min_frac=0.06, max_frac=0.4, threshold=0.85, check_path=None):
    cap, fps, duration, full_w, full_h = open_video(video_path)
    frames, times = [], []
    for k in range(samples):
        t = duration * (0.05 + 0.9 * k / max(1, samples - 1))
        frame = read_at(cap, t)
        if frame is None:
            continue
        small = cv2.resize(frame, (WORK_WIDTH, round(full_h * WORK_WIDTH / full_w)), interpolation=cv2.INTER_AREA)
        frames.append(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        times.append(t)
    if not frames:
        raise SystemExit(f"Error: could not read frames from {video_path}")

    std = np.std(np.array(frames, dtype=np.float32), axis=0)
    score, corner, w, h = best_rectangle(*edge_persistence(frames), std, min_frac, max_frac)
    H, W = frames[0].shape
    found = score >= threshold
    box = to_box(corner, w, h, W, H, full_w / W, full_w, full_h) if found else None
    check_time = times[clearest_frame(frames, corner, w, h)] if found else times[len(times) // 2]
    check_frame = read_at(cap, check_time) if check_path else None
    cap.release()

    result = {
        "found": bool(found),
        "corner": corner if found else None,
        "box": box,
        "mask_arg": ",".join(map(str, box)) if box else "none",
        "score": round(score, 3),
        "frame_size": [full_w, full_h],
        "frames_sampled": len(frames),
    }
    if check_frame is not None:
        write_check_image(check_frame, box, check_path)
        result["check_image"] = check_path
        result["check_time"] = round(check_time, 1)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect the camera thumbnail in a shared-screen recording")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--check-image", default="overlay_check.png",
                        help="Where to write the annotated check frame (default: overlay_check.png; 'none' to skip)")
    parser.add_argument("--samples", type=int, default=60, help="Frames to sample across the video (default: 60)")
    parser.add_argument("--threshold", type=float, default=0.85,
                        help="Minimum edge-persistence score to report a thumbnail (default: 0.85)")
    args = parser.parse_args()
    check = None if args.check_image.lower() == "none" else args.check_image
    if check:
        os.makedirs(os.path.dirname(os.path.abspath(check)), exist_ok=True)
    print(json.dumps(detect(args.video_path, args.samples, threshold=args.threshold, check_path=check), indent=2))
