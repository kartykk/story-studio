"""Story-Studio Streamlit UI — browse stories, read chapters, trigger write."""
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import streamlit as st

STORIES_DIR = Path(__file__).resolve().parent / "stories"
ROOT = Path(__file__).resolve().parent


def list_story_files() -> list[Path]:
    return sorted(STORIES_DIR.glob("*.json"))


def load_story_meta(story_id: str) -> dict:
    from core.story_bible import StoryBible

    bible = StoryBible.load(story_id)
    return {
        "id": story_id,
        "title": bible.title or story_id,
        "genre": bible.genre or "unknown",
        "chapters": len(bible.chapters or []),
        "bible": bible,
    }


def run_cli_write(story_id: str, chapter: int) -> tuple[int, str]:
    cmd = [sys.executable, "main.py", "write", story_id, str(chapter)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return proc.returncode, proc.stdout + proc.stderr


def outline_payload(bible) -> dict:
    beats = [asdict(b) for b in bible.beats] if bible.beats else []
    plan = [cp.to_dict() for cp in bible.chapter_plan] if bible.chapter_plan else []
    if beats or plan:
        return {"beats": beats, "chapter_plan": plan}
    return {"note": "No outline in bible"}


def main():
    st.set_page_config(page_title="Story Studio", layout="wide")
    st.title("Story Studio")

    files = list_story_files()
    if not files:
        st.warning("No stories in stories/. Run `python main.py new` first.")
        return

    names = [f.stem for f in files]
    selected = st.sidebar.selectbox("Story", names)
    meta = load_story_meta(selected)
    bible = meta["bible"]

    st.subheader(meta["title"])
    st.caption(f"Genre: {meta['genre']} · Chapters written: {meta['chapters']}")

    tab_read, tab_outline, tab_write = st.tabs(["Read", "Outline", "Write"])

    with tab_read:
        written_nums = sorted(c["number"] for c in bible.chapters) if bible.chapters else []
        if not written_nums:
            st.info("No chapters written yet. Use the Write tab or `python main.py write`.")
        else:
            ch = st.number_input(
                "Chapter",
                min_value=1,
                max_value=max(written_nums),
                value=written_nums[0],
                step=1,
            )
            if ch not in written_nums:
                st.warning(f"Chapter {ch} has not been written yet.")
            else:
                chapter = bible.get_chapter(int(ch))
                if chapter:
                    st.markdown(f"### {chapter.get('title', f'Chapter {ch}')}")
                    st.markdown(chapter.get("content", ""))

    with tab_outline:
        st.json(outline_payload(bible))

    with tab_write:
        next_default = (max((c["number"] for c in bible.chapters), default=0) + 1) if bible.chapters else 1
        next_ch = st.number_input("Write chapter #", min_value=1, value=next_default, step=1)
        if st.button("Generate chapter (CLI)"):
            with st.spinner("Running main.py write…"):
                code, log = run_cli_write(selected, int(next_ch))
            st.code(log or "(no output)")
            if code == 0:
                st.success("Done")
                st.rerun()
            else:
                st.error(f"Exit code {code}")


if __name__ == "__main__":
    main()
