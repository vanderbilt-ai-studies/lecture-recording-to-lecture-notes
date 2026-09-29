# Lecture Recording → Lecture Notes

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that turns a recorded lecture (a Zoom `.vtt` transcript and the `.mp4` video) into polished, tutorial-style Markdown lecture notes illustrated with screen grabs taken straight from the recording, with attributed speaker quotes and a Q&A section.

All you need is the recording. The skill finds every distinct screen the speaker showed, grabs the moments the speaker points at, and paints the speaker's camera thumbnail out of each image.

It is built for instructors, TAs, and students who want readable notes from a class, workshop, or talk without hand-transcribing it or watching the recording again.

---

## Contents

- [What it produces](#what-it-produces)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Installation](#installation)
- [Requirements](#requirements)
- [Usage](#usage)
- [Input files](#input-files)
- [Output](#output)
- [Helper scripts](#helper-scripts)
- [Style rules the notes follow](#style-rules-the-notes-follow)
- [Tips and limitations](#tips-and-limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## What it produces

Given a session folder like this:

```
03-how-llms-actually-work/
├── 03-how-llms-actually-work.vtt     # Zoom transcript
└── GMT20260915-175554_Recording_1920x1080.mp4   # Zoom video
```

the skill writes, into the same folder:

```
03-how-llms-actually-work/
├── 03-how-llms-actually-work-lecture-notes.md   # the notes
└── screenshots/
    ├── auto_000512.png                           # screen grabs, named by video time
    ├── auto_004523.png
    └── ...
```

The notes contain:

- **YAML frontmatter:** title, date, presenter, duration, source transcript and video
- **Key concepts and learning objectives** up front
- **Sectioned, tutorial-style prose** rewritten from the transcript (not a raw dump), following the lecture's logical flow
- **Screen grabs** placed where each topic starts and inline at demos, with the camera thumbnail removed
- **Demo walkthroughs** describing what happened on screen
- **Blockquoted speaker quotes** with attribution
- **Q&A** with questions and paraphrased answers
- **Summary** of takeaways and a **References** list of resources mentioned in the lecture

---

## How it works

The skill guides Claude through four phases and runs straight through without stopping for confirmation.

| Phase | What happens |
|---|---|
| **0. Find the recording** | Locates the `.vtt` transcript and the `.mp4` video. When Zoom produced several videos, it prefers the shared-screen-only file (no camera), then shared screen with speaker view. |
| **1. Remove the camera thumbnail** | Detects the camera box Zoom overlays on the shared screen, usually in the top-right, even when the camera is off and only the name tile shows. Claude confirms the detection on an annotated check frame, then that box is painted out of every grab with the surrounding background color. |
| **2. Screen grabs** | One pass over the video saves a frame each time the screen settles on something new (slide advances, new windows, command output). Then it grabs extra frames where the transcript shows the speaker pointing at something ("as you can see", "in the terminal", silent pauses). Near-duplicates are skipped automatically. Claude reviews the rest, dropping transitional frames and anything private (inboxes, notifications, sign-in codes, student rosters or photos). |
| **3. Note generation** | Writes the Markdown document following the structure and style rules below, using only what's in the transcript and on screen. |

After the first draft, Claude offers to refine sections, add or swap screen grabs, or change the level of detail.

### How the camera thumbnail is found

Screen content changes throughout a lecture, but the thumbnail's border stays in exactly the same place. The detector samples 60 frames across the video and looks for a rectangle anchored in a frame corner:

- Both of its inner edges must show up in nearly every sampled frame.
- Boundary stretches that are black against black carry no evidence either way (for example, a dark camera image next to a letterbox bar), so they are ignored instead of counted as missing edge.
- The content inside or around the box must change over the lecture, which rules out static page layout.
- If a static object inside the camera view (a projector screen, a door frame) forms a smaller rectangle nested in the same corner, the largest rectangle wins.

On a dozen real Zoom recordings it found the thumbnail every time, including camera-off name tiles and an empty-room camera, with no false positives on screen recordings that have no thumbnail. It takes about 3 seconds per recording.

---

## Repository layout

```
lecture-recording-to-lecture-notes/
├── SKILL.md                       # The skill: workflow, output template, style rules
├── README.md                      # This file
└── scripts/
    ├── detect_camera_overlay.py   # find the camera thumbnail → --mask value + check image
    ├── detect_screen_changes.py   # one pass over the video → a frame per distinct screen
    ├── extract_frames.py          # frames at given timestamps (masked, de-duplicated)
    └── video_utils.py             # shared helpers: masking, frame comparison
```

`SKILL.md` is the file Claude reads. Its frontmatter `name` and `description` determine when the skill is triggered.

---

## Installation

### Claude Code

Clone into your personal skills directory (available in every project):

```bash
git clone https://github.com/vanderbilt-ai-studies/lecture-recording-to-lecture-notes.git ~/.claude/skills/lecture-recording-to-lecture-notes
```

Or into a single project's skills directory (shared with anyone who uses that repo):

```bash
git clone https://github.com/vanderbilt-ai-studies/lecture-recording-to-lecture-notes.git .claude/skills/lecture-recording-to-lecture-notes
```

Claude Code picks up skills automatically; start a new session after installing.

### Claude.ai / Claude desktop app

1. Download this repository as a ZIP (**Code → Download ZIP**), or zip the folder yourself so that `SKILL.md` is at the top level of the skill folder.
2. In Claude, go to **Settings → Capabilities → Skills** and upload the ZIP.
3. Make sure code execution is enabled so the helper scripts can run.

### Updating

```bash
git -C ~/.claude/skills/lecture-recording-to-lecture-notes pull
```

---

## Requirements

- **Python 3.10+**
- **`opencv-python`** (brings `numpy` with it). The scripts install it with `pip` on first run if it's missing, or install it up front:

```bash
pip install opencv-python
```

Nothing else is needed: no system tools, no presentation software.

---

## Usage

1. Put the lecture's `.vtt` and `.mp4` in one folder (one folder per session works best).
2. Open Claude Code in that folder, or attach the files in Claude.
3. Ask for notes in plain language, for example:

   > Make lecture notes from this recording.

   > Turn week 3's Zoom recording into study notes.

   > Write up this talk as tutorial-style notes with screenshots from the demos.

4. Claude reports what it found and carries on: it removes the camera thumbnail, captures the screens, and writes `<session-name>-lecture-notes.md`.
5. Ask for revisions: more detail on a section, a different screenshot, a different Q&A placement, and so on.

---

## Input files

| Type | Extensions | Required? | Role |
|---|---|---|---|
| Transcript | `.vtt` | **Yes** | WebVTT from Zoom (speaker-labelled lines like `Name: text` work best) |
| Video | `.mp4` | **Yes, for images** | Source of every screen grab. Without it, the notes are text only. |
| Existing screen grabs | images in `screenshots/` | No | Kept and interleaved chronologically with new ones |
| Your own readings or notes | any | No | Used as extra context when you hand them to Claude |

**Getting the files from Zoom:** in the Zoom web portal, open **Recordings**, choose the cloud recording, and download the video and the **Audio transcript** (`.vtt`). Cloud recording with audio transcription must be enabled for the meeting. If your account records **Shared screen** as a separate file, download that one: it has no camera thumbnail at all.

---

## Output

- **Notes file:** `<session-name>-lecture-notes.md`, where the session name comes from the folder or VTT filename (e.g. `03-how-llms-actually-work.vtt` → `03-how-llms-actually-work-lecture-notes.md`).
- **`screenshots/`:** `auto_HHMMSS.png`, named by the video time of the frame (e.g. `auto_004523.png` = 00:45:23), full resolution, camera thumbnail removed.
- All image links in the Markdown are relative, so the folder can be moved, committed to Git, or rendered on GitHub as-is.
- No working files are left behind.

Skeleton of the generated document:

```markdown
---
title: "How LLMs Actually Work"
date: "2026-09-15"
presenter: "Jane Doe"
duration: "1:14:32"
source_transcript: "03-how-llms-actually-work.vtt"
source_video: "GMT20260915-175554_Recording_1920x1080.mp4"
---

# How LLMs Actually Work

## Key Concepts and Learning Objectives
**Key Terms and Concepts:** ...
**Learning Objectives:** ...

---

## Tokenization
![Diagram of text split into tokens](screenshots/auto_000512.png)
Tutorial-style explanation...

> "A quote that captures the key idea." — Jane Doe

### Demo: Counting tokens in the playground
![Token counter showing 42 tokens](screenshots/auto_004523.png)
Step-by-step walkthrough...

---

## Q&A
**Q (Audience Member):** ...
**A (Jane Doe):** ...

## Summary
- ...

## References
- ...
```

---

## Helper scripts

The scripts can also be run on their own.

### `scripts/detect_camera_overlay.py`

```bash
python3 scripts/detect_camera_overlay.py recording.mp4 [--check-image overlay_check.png]
```

Prints JSON with `found`, `corner`, `box` (`[x, y, w, h]` in pixels), `mask_arg` (the same box as `x,y,w,h`, ready for `--mask`), and `score`. It also writes a check image: a frame with the box outlined in red over a labelled 10% grid, so you can confirm the result or read off a corrected box.

### `scripts/detect_screen_changes.py`

```bash
python3 scripts/detect_screen_changes.py recording.mp4 --mask 1592,0,328,188 --extract screenshots/ [-o screens.json]
```

Scans the video once, one frame per second, and records a capture each time the screen holds still for 2 seconds on content that differs from the previous capture. With `--extract`, it saves each capture as `auto_HHMMSS.png`. It processes a 2-hour recording in about 30 seconds.

| Option | Default | Effect |
|---|---|---|
| `--mask x,y,w,h` | none | Box to paint out (from `detect_camera_overlay.py`) |
| `--fill auto\|gray\|black\|none` | `auto` | `auto` matches the surrounding background color |
| `--min-change` | `0.03` | Fraction of pixels that must differ from the last capture |
| `--settle` | `2.0` | Seconds the screen must hold still before it's captured |
| `--min-gap` | `5.0` | Minimum seconds between captures |
| `--step` | `1.0` | Seconds between sampled frames |

### `scripts/extract_frames.py`

```bash
python3 scripts/extract_frames.py recording.mp4 screenshots/ '[2700, 2850, 3000]' --mask 1592,0,328,188 [--offset 2.0]
```

Takes a JSON array of timestamps in seconds and saves one frame per timestamp, `--offset` seconds later (default 2 s, which lets the screen settle). It accepts the same `--mask` and `--fill` options. It skips frames nearly identical to an image already in the output folder; pass `--keep-duplicates` to save them anyway.

---

## Style rules the notes follow

1. **Preamble first:** key terms and learning objectives before the body.
2. **Tutorial-style prose:** rewritten for clarity, filler removed, speaker's logical flow preserved.
3. **Speaker quotes as blockquotes** with attribution.
4. **Sections at natural topic transitions:** screen changes, "moving on" phrases, topic shifts.
5. **Q&A** grouped at the end or inline, depending on how the lecture flowed.
6. **One image per moment**, with alt text describing what the screen shows.
7. **Relative image paths.**
8. **YAML frontmatter** with title, date, presenter, duration, source transcript, and source video.
9. **No invented content:** no examples, references, or quotes that aren't in the transcript, on screen, or in materials you supplied.

---

## Tips and limitations

- **Use a shared-screen recording.** Screen grabs need the screen share in the video. A speaker-view or gallery-view recording has no screen content to capture.
- **Long lectures:** transcripts over ~50,000 tokens are processed in time-range chunks (e.g. 15 minutes) and stitched together.
- **Speaker names:** Zoom often mislabels speakers. The skill checks names against the title screen and the name label on the camera thumbnail. If the VTT has no speaker labels, Claude will ask who is speaking.
- **Typing-heavy demos** produce many small screen changes. The default thresholds keep one capture per settled screen; raise `--min-change` if you still get too many.
- **Accuracy:** the notes are only as accurate as the transcript. Review technical terms, names, and quotes before distributing the notes.
- **Privacy:** recordings can show student names, photos, seating charts, email, and notifications. The skill is told to drop or crop those frames, but review the screenshots before sharing, and follow your institution's policies (e.g. FERPA) before sharing notes that name participants from Q&A.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install` fails inside a script | Install manually into the Python you're using: `python3 -m pip install opencv-python`. On system Pythons with PEP 668 protection, use a virtual environment. |
| `Error: Could not open video` | Check the path, and that the file is a complete download (Zoom sometimes delivers a partial file while processing). |
| The camera thumbnail still shows in grabs | Open the check image, read the thumbnail's edges off the grid, and pass `--mask x,y,w,h` yourself (pad ~8 px). |
| A gray or colored block looks out of place | Try `--fill auto` (matches the background) or `--fill gray`. |
| Too many near-identical screenshots | Raise `--min-change` or `--min-gap` in `detect_screen_changes.py`. |
| A screen the speaker showed was missed | Lower `--min-change`, or ask Claude to grab that moment by time. |
| Screenshots caught mid-scroll or mid-animation | Raise `--settle`, or adjust `--offset` in `extract_frames.py`. |
| Wrong presenter name in the notes | Tell Claude the correct name; it will update attributions throughout. |

---

## Contributing

Issues and pull requests are welcome. If you change the workflow, update both `SKILL.md` (what Claude follows) and this README (what people read). Test changes on a real recording before submitting a PR.

---

Maintained by [Vanderbilt AI Studies](https://github.com/vanderbilt-ai-studies).
