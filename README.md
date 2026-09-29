<div align="center">
  <img src="assets/story_studio_logo.png" alt="Story Studio Logo" width="360" />

  # Story Studio
  ### Genre-aware AI fiction writer with quality gating, audio and video output
</div>

---

## Overview

Story Studio is an interactive Python CLI (plus a small Streamlit viewer) for writing multi-chapter fiction with Claude. You start with a raw concept. The tool detects the genre and routes the story to a specialised genre model (crime, fantasy, horror, literary, romance). It then walks you through premise, titles, world-building, characters, story beats and a chapter plan, and writes each chapter scene by scene. A persistent **story bible** (JSON in `stories/`) keeps continuity across chapters. Drafts can be scored by a quality gate, an emotion scorer and a scene-interest scorer. Finished chapters can be turned into narrated audio (ElevenLabs) and simple text-on-background videos (FFmpeg).

## Key features

- **Genre auto-detection** routes each story to one of 5 genre modules, each with its own characters, psychology, config and writer.
- **Guided pipeline**: premise → titles → world → characters → beats → chapter plan → scene drafts → chapter → refinement.
- **Story bible** persistence, so stories can be resumed later (`load`, `list`).
- **Quality gate** (Claude) scores chapters and can drive a write → score → rewrite loop.
- **Emotion scoring** via DeepSeek (OpenAI-compatible API) and an **interest scorer** that produces scene-level reports.
- **Arc calculator** and **dialogue parser** (used to split dialogue by speaker for audio).
- **Multilingual** writing in 15 languages: English, Hindi, Spanish, French, Portuguese, German, Italian, Japanese, Chinese, Arabic, Bengali, Tamil and more.
- **Audio**: per-character ElevenLabs voices (`eleven_multilingual_v2`), post-processed with pydub.
- **Video**: FFmpeg renders per-segment clips with character-aware voice effects, an intro title card and an outro fade.
- **Benchmark script** with smoke and full phases, and sample benchmark outputs in `output/`.
- **Streamlit UI** to browse stories, read chapters and trigger writing.

## Tech stack

Python 3.11+, Anthropic SDK (Claude), OpenAI SDK (for DeepSeek), ElevenLabs, pydub, FFmpeg, Rich, python-dotenv, Streamlit.

## Repository layout

```
main.py                 # CLI entry point
web_app.py              # Streamlit UI (see web/README.md)
core/
  story_writer.py       # Claude writing pipeline, supported languages
  story_bible.py        # story state / persistence (stories/*.json)
  quality_gate.py       # chapter scoring + gated writing
  emotion_scorer.py     # DeepSeek emotion analysis
  interest_scorer.py    # scene interest report
  arc_calculator.py, dialogue_parser.py
  voice_engine.py       # ElevenLabs audio
  video_engine.py       # FFmpeg video
  env.py                # API-key helpers
genres/                 # base_genre.py + crime/ fantasy/ horror/ literary/ romance/
scripts/run_story_benchmark.py
stories/                # sample/benchmark story bibles
output/                 # sample exports and benchmark reports
documentation/          # generated project notes
```

## Prerequisites

- Python 3.11+
- FFmpeg on your `PATH` (only for video)
- An Anthropic API key. DeepSeek and ElevenLabs keys are optional and only needed for emotion scoring and audio/video.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create a .env file with the keys listed below
```

## Usage

```bash
python main.py new                      # start a new story (interactive)
python main.py list                     # list all stories
python main.py load <story_id>          # continue an existing story
python main.py write <story_id> <ch>    # write a specific chapter
python main.py quality <story_id> <ch>  # score chapter quality
python main.py interest <story_id> <ch> # scene interest report
python main.py audio <story_id> <ch>    # generate chapter audio
python main.py video <story_id> <ch>    # generate chapter video
python main.py export <story_id>        # export full story as text

streamlit run web_app.py                # web UI at http://localhost:8501

python scripts/run_story_benchmark.py --phase smoke   # or --phase full / --report-only
```

## Configuration

`.env` (loaded with python-dotenv):

```env
ANTHROPIC_API_KEY=      # required (writing + quality gate)
DEEPSEEK_API_KEY=       # optional (emotion scorer)
ELEVENLABS_API_KEY=     # optional (audio/video)
```

The model names (Claude Opus/Sonnet, `deepseek-chat`) are constants in `core/story_writer.py`, `core/quality_gate.py` and `core/emotion_scorer.py`. The code references `.env.example`, but that file is not included in the repo.

## Status

**Paused.**

## License

MIT. See [LICENSE](LICENSE).
