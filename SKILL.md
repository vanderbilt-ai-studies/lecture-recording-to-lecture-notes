---
name: lecture-recording-to-lecture-notes
description: Convert a lecture recording (Zoom .vtt transcript and .mp4 video) into polished Markdown lecture notes illustrated with screen grabs taken straight from the video, with the speaker's camera thumbnail removed, plus speaker quotes and Q&A. Use for any lecture, class, or talk recording.
---

# Lecture Recording to Lecture Notes

Transform a lecture recording into polished, tutorial-style Markdown notes. The transcript supplies the words; the video recording of the shared screen supplies every image. Screen grabs are taken automatically wherever the screen changes or the speaker points at something, with the speaker's camera thumbnail painted out.

The video is the only visual source. Do not look for, ask for, or wait for any other presentation files.

## Workflow

Run these phases in order without pausing for confirmation, unless the transcript or video is missing.

---

### Phase 0: Find the recording

**Scan the working directory** for:

| Type | Extensions | Role |
|------|-----------|------|
| Transcript | `.vtt` | Required: WebVTT from Zoom |
| Video | `.mp4` | Required for images: the source of every screen grab |
| Existing screen grabs | images in `screenshots/` | Optional: kept and interleaved with new ones |

If the user supplies readings or notes of their own, use them as extra context, but don't search the directory for anything beyond the files above.

**Choosing the video when Zoom produced several.** Zoom cloud recordings can include several `.mp4` files for the same meeting. Prefer, in order:
1. **Shared screen only** (no camera): no thumbnail to remove.
2. **Shared screen with speaker view** or **with gallery view**: the usual file; the thumbnail is removed in Phase 1.
3. **Active speaker** or **gallery view** only: shows no screen content; use only if nothing else exists.

A single file named like `GMT20260922-193423_Recording_1920x1080.mp4` is the normal case.

**Check the one dependency:** `python3 -c "import cv2"`. The scripts install `opencv-python` automatically if it's missing.

**Report the inventory briefly and continue immediately:**
```
## Recording
- Transcript: [filename.vtt]
- Video: [filename.mp4] ([duration], [width]x[height])
- Existing screen grabs: [count] in screenshots/ (or "none")
```

If there is no `.vtt`, stop and ask for one. If there is no `.mp4`, ask for the video recording; if the user can't provide it, write text-only notes and say so at the top.

---

### Phase 1: Remove the camera thumbnail

Zoom overlays the speaker's camera, or a name tile when the camera is off, in a corner of shared-screen recordings, usually the top-right. Paint it out of every screen grab.

```bash
python3 <skill-path>/scripts/detect_camera_overlay.py "recording.mp4" --check-image overlay_check.png
```

It prints JSON such as:
```json
{"found": true, "corner": "top-right", "box": [1592, 0, 328, 188], "mask_arg": "1592,0,328,188", "score": 0.99, ...}
```

**Always look at `overlay_check.png`.** It shows a frame with the detected box outlined in red over a 10% grid labelled in pixels.
- The red box covers the whole thumbnail, including the name label: use `mask_arg` as `--mask` in Phase 2.
- `found` is false, or the box is wrong, but a thumbnail is visible: read its edges off the grid labels and build the mask yourself as `x,y,w,h` in pixels. Pad by ~8 px so the border is covered.
- There's no thumbnail (screen-only recording): use no mask.

`--fill auto` (the default) paints the box with the surrounding background color so it disappears into the page. `--fill gray` paints a neutral gray box instead.

Delete `overlay_check.png` once the mask is settled; it isn't part of the output.

---

### Phase 2: Transcript analysis & screen grabs

#### 2a. Parse the VTT transcript

Read the `.vtt` file and parse it into structured entries:
```
{ index, start_time, end_time, speaker, text }
```

VTT format rules:
- Lines with `-->` contain timestamps: `HH:MM:SS.mmm --> HH:MM:SS.mmm`
- Speaker names often appear as `Speaker Name: text` on the text line
- Blank lines separate entries
- Skip the `WEBVTT` header and any `NOTE` blocks

Merge consecutive entries from the same speaker into coherent paragraphs for analysis.

#### 2b. Capture every distinct screen

Scan the whole video once and save a frame each time the screen settles on something new:

```bash
python3 <skill-path>/scripts/detect_screen_changes.py "recording.mp4" --mask 1592,0,328,188 --extract screenshots/ -o screens.json
```

This takes well under a minute per hour of video. Frames are saved as `screenshots/auto_HHMMSS.png`, and `screens.json` lists each capture's time. Tuning, if needed:
- Too many near-identical captures (e.g. lots of typing): raise `--min-change` (default `0.03`) or `--min-gap` (default `5` s).
- Missed changes: lower `--min-change`.
- Captures taken mid-animation or mid-scroll: raise `--settle` (default `2` s).

#### 2c. Grab the moments the speaker points at

Screen-change detection misses moments where the speaker talks about something already on screen. Find those in the transcript:

**Trigger phrases.** Flag entries containing phrases like:
- "let me show you", "as you can see", "if you look at", "on the screen"
- "I'm clicking", "let me click", "I'll type", "in the terminal", "in the browser"
- "let me share my screen", "let me demonstrate", "here's an example"
- "let me pull up", "switching to", "opening up", "running this"
- "the output shows", "you'll see", "notice that", "look at this", "next slide"

**Silent gaps.** Flag gaps where `start_time(entry N+1) - end_time(entry N) > 3 seconds`. Silence often means typing, navigating, or waiting for output.

Deduplicate the flagged timestamps (merge any within 5 seconds, keeping the later one) and extract them with the same mask:

```bash
python3 <skill-path>/scripts/extract_frames.py "recording.mp4" screenshots/ '[2700, 2850, 3000]' --mask 1592,0,328,188
```

Each frame is taken 2 seconds after the timestamp (`--offset`) so the screen can settle. Frames nearly identical to one already in `screenshots/` are skipped automatically.

#### 2d. Review the screen grabs

Look at the grabs with vision and keep only the ones worth showing:
- **Drop near-duplicates:** keep the most complete version (e.g. the fully built-up screen, the finished command output).
- **Drop transitional frames:** half-loaded pages, mid-scroll blur, open menus that aren't the point.
- **Drop frames with no screen content:** a full-frame camera view, a blank desktop, the Zoom waiting screen.
- **Drop anything private:** email inboxes, chat or notification pop-ups, passwords or QR codes for sign-in, and class rosters, seating charts, or student photos and names. If a frame is useful but has a private area, crop it rather than include it as-is.
- **Check the thumbnail is gone:** if any frame still shows the camera box, fix the mask and re-extract.

Delete the rejected files so `screenshots/` holds only what the notes use, and delete `screens.json` once you've used it.

If `screenshots/` held images before this run, keep them and interleave them chronologically with the new grabs.

#### 2e. Align screen grabs to the transcript

Each grab's filename is its video time. Match it to the transcript passage being spoken at that time, and note what the screen shows (a title, a diagram, a terminal, a web page). Use this mapping to place images and to name sections in Phase 3.

---

### Phase 3: Note generation

Write all outputs (the Markdown file and `screenshots/`) into the session's directory, where the `.vtt` and `.mp4` are. Name the Markdown file `[session-name]-lecture-notes.md`, deriving the session name from the directory name or the VTT filename (e.g., `03-how-llms-actually-work.vtt` becomes `03-how-llms-actually-work-lecture-notes.md`).

The Markdown file should have this structure:

```markdown
---
title: "[Lecture Title]"
date: "[Date of recording]"
presenter: "[Speaker Name(s)]"
duration: "[Total duration from transcript timestamps]"
source_transcript: "[filename.vtt]"
source_video: "[filename.mp4]"
---

# [Lecture Title]

## Key Concepts and Learning Objectives

**Key Terms and Concepts:**
- Term 1 — definition or explanation
- Term 2 — definition or explanation
- ...

**Learning Objectives:**
1. Understand [concept]...
2. Be able to [skill]...
3. ...

---

## [Section Title]

![What the screen shows](screenshots/auto_000512.png)

Tutorial-style narrative prose that explains the content covered in this
section. This is NOT a raw transcript — it is rewritten as clear, readable
instructional text that follows the lecture's logical flow.

> "Direct quote from the speaker that captures a key insight or memorable
> phrasing" — Speaker Name

More prose explaining the next concept...

### Demo: [What Was Demonstrated]

![Screenshot](screenshots/auto_004523.png)

Step-by-step walkthrough of what's happening on screen. Describe what the
viewer would see: the tool being used, the commands typed, the output
produced, and what it means.

---

## [Next Section Title]

... (repeat pattern) ...

---

## Q&A

**Q (Audience Member Name):** The question asked?

**A (Speaker Name):** The answer given, paraphrased for clarity.

---

## Summary

- Bullet-point summary of the main takeaways from the lecture
- Each point should be actionable or conceptual

## References

- Links, papers, tools, or resources mentioned during the lecture
```

#### Style Rules

1. **Preamble first.** Start with key concepts, terms, and learning objectives before the body. Derive these from the transcript, what's on screen, and any readings the user supplied.

2. **Tutorial-style prose.** Rewrite transcript content as clear instructional narrative. Do not dump raw transcript text. Preserve the speaker's logical flow but improve clarity, fix filler words, and add structure.

3. **Speaker quotes as blockquotes.** When the speaker says something particularly insightful, memorable, or important, include it as a blockquote with attribution: `> "quote" — Name`.

4. **Section boundaries.** Create new sections at natural topic transitions. Use screen changes, explicit "moving on" phrases, and topic shifts as section boundary signals.

5. **Q&A sections.** When audience members ask questions (detected by speaker changes and question phrasing), format them in the Q&A style. Group Q&A at the end or inline with the relevant section; use judgment based on how the lecture flowed.

6. **Image placement.** Put the screen grab that introduces a topic at the start of its section, and demo grabs inline where the demo happens in the narrative. One image per moment. Give each image alt text that says what the screen shows.

7. **Relative paths.** All image paths must be relative to the output Markdown file (e.g., `screenshots/auto_004523.png`).

8. **Metadata frontmatter.** Include YAML frontmatter with title, date, presenter, duration, source transcript, and source video filenames.

9. **No hallucinated content.** Only include information that appears in the transcript, on screen in the video, or in readings the user supplied. Do not invent examples, add external references not mentioned, or fabricate speaker quotes.

---

## Important Notes

- **Large transcripts**: For transcripts longer than ~50,000 tokens, process in chunks by time range (e.g., 15-minute segments) and stitch together at the end.
- **Multiple speakers**: Track speaker names throughout and attribute quotes correctly. If the VTT doesn't include speaker names, ask the user to identify speakers.
- **Speaker name verification**: VTT transcripts from Zoom often misidentify speakers. Cross-reference names against what the video shows: the title screen at the start of the talk and the name label on the camera thumbnail (visible in `overlay_check.png`). When there is a conflict, prefer the on-screen name over the VTT or the user's prompt.
- **Output location**: Write all outputs (Markdown and `screenshots/`) into the session's directory alongside the recording. Name the file `[session-name]-lecture-notes.md`. Leave no working files behind (`overlay_check.png`, `screens.json`).
- **Iterative refinement**: After generating the first draft, offer to refine specific sections, add or swap screen grabs, or adjust the level of detail.
