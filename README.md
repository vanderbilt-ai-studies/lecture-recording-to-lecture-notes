# Lecture Recording → Lecture Notes

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that turns a recorded lecture — a Zoom `.vtt` transcript plus, optionally, the `.mp4` video, the slide deck, and supplementary readings — into polished, tutorial-style Markdown lecture notes with embedded slides, auto-extracted demo screenshots, attributed speaker quotes, and a Q&A section.

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
├── 03-how-llms-actually-work.vtt     # Zoom transcript (required)
├── recording.mp4                     # optional
├── slides.pdf                        # optional (.pdf or .pptx)
└── reading.md                        # optional supplementary material
```

the skill writes, into the same folder:

```
03-how-llms-actually-work/
├── 03-how-llms-actually-work-lecture-notes.md   # the notes
├── slides/
│   ├── slide-001.png
│   └── ...
└── screenshots/
    ├── auto_004523.png                           # frames pulled from demo moments
    └── ...
```

The notes contain:

- **YAML frontmatter** — title, date, presenter, duration, source transcript
- **Key concepts and learning objectives** up front
- **Sectioned, tutorial-style prose** rewritten from the transcript (not a raw dump), following the lecture's logical flow
- **Slide images** placed at the start of the section they belong to
- **Demo walkthroughs** with screenshots captured from the video at the moments the speaker was showing something
- **Blockquoted speaker quotes** with attribution
- **Q&A** with questions and paraphrased answers
- **Summary** of takeaways and a **References** list of resources mentioned in the lecture

---

## How it works

The skill guides Claude through four phases.

| Phase | What happens |
|---|---|
| **0. Discovery** | Scans the working directory, classifies transcript / video / slides / supplementary files / existing screenshots, checks for Python dependencies, and shows you an inventory. **It waits for your confirmation before continuing.** |
| **1. Slide conversion** | Renders PDF slides to `slides/slide-NNN.png` with PyMuPDF. PPTX decks are converted to PDF through LibreOffice when available; otherwise their text is extracted for alignment and the video supplies the visuals. |
| **2. Transcript analysis & screenshots** | Parses the VTT into timed, speaker-attributed entries, then finds "visual moments" three ways: trigger phrases ("let me show you", "in the terminal", "as you can see"…), silent gaps longer than 3 seconds, and slide-transition language. Frames are pulled from the video 2 seconds after each moment, deduplicated, and compared against the aligned slide so each moment gets **one** image — the slide if it's just the slide, the screenshot if it's a live demo. |
| **3. Note generation** | Writes the Markdown document following the structure and style rules below, using only content from the transcript, slides, and supplied materials. |

After the first draft, Claude offers to refine sections, add screenshots, or change the level of detail.

---

## Repository layout

```
lecture-recording-to-lecture-notes/
├── SKILL.md                  # The skill: workflow, output template, style rules
├── README.md                 # This file
└── scripts/
    ├── pdf_to_slides.py      # PDF → slide-NNN.png (PyMuPDF)
    ├── extract_frames.py     # video + timestamps → auto_HHMMSS.png (OpenCV)
    └── pptx_to_text.py       # PPTX → per-slide text JSON (python-pptx)
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

- **Python 3.9+**
- Python packages (each helper script installs its own dependency with `pip` on first run if it's missing):

| Package | Needed for | Import check |
|---|---|---|
| `pymupdf` | PDF slides → PNG | `python3 -c "import fitz"` |
| `opencv-python` | Screenshots from video | `python3 -c "import cv2"` |
| `python-pptx` | Text from PPTX slides | `python3 -c "import pptx"` |

To install them all up front:

```bash
pip install pymupdf opencv-python python-pptx
```

**Optional system tools** (used only as fallbacks or for better PPTX rendering):

- **LibreOffice** (`libreoffice` / `soffice`) — renders PPTX decks as real slide images
- **ffmpeg** — fallback frame extraction if OpenCV is unavailable
- **poppler** (`pdftoppm`) or **ImageMagick** (`convert`) — fallback PDF rendering if PyMuPDF is unavailable

Only the `.vtt` transcript is strictly required; the video, slides, and extra materials each add to the result.

---

## Usage

1. Put the lecture's files in one folder (one folder per session works best).
2. Open Claude Code in that folder, or attach the files in Claude.
3. Ask for notes in plain language, for example:

   > Make lecture notes from this recording.

   > Turn week 3's Zoom transcript and slides into study notes.

   > Write up this talk as tutorial-style notes with screenshots from the demos.

4. Review the file inventory Claude presents and confirm (or correct) it.
5. Claude converts slides, extracts screenshots, and writes `<session-name>-lecture-notes.md`.
6. Ask for revisions: more detail on a section, more or fewer screenshots, a different Q&A placement, and so on.

---

## Input files

| Type | Extensions | Required? | Role |
|---|---|---|---|
| Transcript | `.vtt` | **Yes** | WebVTT from Zoom (speaker-labelled lines like `Name: text` work best) |
| Video | `.mp4` | No | Source for auto-extracted demo screenshots |
| Slides | `.pdf`, `.pptx` | No | Rendered and embedded; also used to verify presenter names |
| Supplementary | `.md`, `.txt`, `.docx`, papers | No | Extra context; explicit learning objectives here are used as-is |
| Manual screenshots | images in `screenshots/` | No | Kept and interleaved chronologically with auto-extracted ones |

**Getting a VTT from Zoom:** in the Zoom web portal, open **Recordings**, choose the cloud recording, and download the **Audio transcript** file (`.vtt`). Cloud recording with audio transcription must be enabled for the meeting.

---

## Output

- **Notes file:** `<session-name>-lecture-notes.md`, where the session name comes from the folder or VTT filename (e.g. `03-how-llms-actually-work.vtt` → `03-how-llms-actually-work-lecture-notes.md`).
- **`slides/`:** `slide-001.png`, `slide-002.png`, … (200 DPI by default).
- **`screenshots/`:** `auto_HHMMSS.png`, named by the video timestamp of the frame (e.g. `auto_004523.png` = 00:45:23).
- All image links in the Markdown are relative, so the folder can be moved, committed to Git, or rendered on GitHub as-is.

Skeleton of the generated document:

```markdown
---
title: "How LLMs Actually Work"
date: "2026-09-15"
presenter: "Jane Doe"
duration: "1:14:32"
source_transcript: "03-how-llms-actually-work.vtt"
---

# How LLMs Actually Work

## Key Concepts and Learning Objectives
**Key Terms and Concepts:** ...
**Learning Objectives:** ...

---

## Tokenization
![Slide: Tokenization](slides/slide-004.png)
Tutorial-style explanation...

> "A quote that captures the key idea." — Jane Doe

### Demo: Counting tokens in the playground
![Screenshot](screenshots/auto_004523.png)
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

### `scripts/pdf_to_slides.py`

```bash
python3 scripts/pdf_to_slides.py slides.pdf slides/ [--dpi 200]
```

Renders every page of a PDF to `slides/slide-NNN.png`.

### `scripts/extract_frames.py`

```bash
python3 scripts/extract_frames.py recording.mp4 screenshots/ '[2700, 2850, 3000]' [--offset 2.0]
```

Takes a JSON array of timestamps in seconds and saves one frame per timestamp, `--offset` seconds later (default 2 s, which lets the screen settle), as `screenshots/auto_HHMMSS.png`.

### `scripts/pptx_to_text.py`

```bash
python3 scripts/pptx_to_text.py presentation.pptx -o slides_text.json
```

Writes a JSON list of `{ "slide_number": N, "texts": [...] }`, used to align slides with the transcript when the deck can't be rendered to images. Without `-o`, it prints to stdout.

---

## Style rules the notes follow

1. **Preamble first** — key terms and learning objectives before the body.
2. **Tutorial-style prose** — rewritten for clarity, filler removed, speaker's logical flow preserved.
3. **Speaker quotes as blockquotes** with attribution.
4. **Sections at natural topic transitions** — slide changes, "moving on" phrases, topic shifts.
5. **Q&A** grouped at the end or inline, depending on how the lecture flowed.
6. **One image per moment** — slides at section starts, screenshots inline at demos, never both for the same moment.
7. **Relative image paths.**
8. **YAML frontmatter** with title, date, presenter, duration, and source transcript.
9. **No invented content** — no examples, references, or quotes that aren't in the transcript, slides, or supplied materials.

---

## Tips and limitations

- **Long lectures:** transcripts over ~50,000 tokens are processed in time-range chunks (e.g. 15 minutes) and stitched together.
- **Speaker names:** Zoom often mislabels speakers. The skill checks names against the title slide and prefers the slide when they conflict. If the VTT has no speaker labels, Claude will ask who is speaking.
- **PPTX without LibreOffice:** only slide *text* can be extracted, so visuals come from video screenshots instead. Exporting the deck to PDF first gives the best results.
- **Screenshot quality** depends on the recording's resolution and on what was shared. Gallery-view recordings won't capture screen shares well; use the "shared screen" recording layout when possible.
- **Accuracy:** the notes are only as accurate as the transcript. Review technical terms, names, and quotes before distributing the notes.
- **Privacy:** recordings and transcripts can include student names and voices. Follow your institution's policies (e.g. FERPA) before sharing notes that name participants from Q&A.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install` fails inside a script | Install manually into the Python you're using: `python3 -m pip install pymupdf opencv-python python-pptx`. On system Pythons with PEP 668 protection, use a virtual environment. |
| `Error: Could not open video` | Check the path, and that the file is a complete download (Zoom sometimes delivers a partial file while processing). Try the ffmpeg fallback. |
| Screenshots are black or show the wrong thing | Adjust `--offset`, or ask Claude to re-extract specific timestamps. |
| Slides render blank or with missing fonts from PPTX | Export to PDF from PowerPoint/Keynote and use the PDF instead. |
| Wrong presenter name in the notes | Tell Claude the correct name; it will update attributions throughout. |

---

## Contributing

Issues and pull requests are welcome. If you change the workflow, update both `SKILL.md` (what Claude follows) and this README (what people read). Test changes on a real recording before submitting a PR.

---

Maintained by [Vanderbilt AI Studies](https://github.com/vanderbilt-ai-studies).
