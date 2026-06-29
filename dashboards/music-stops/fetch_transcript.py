#!/usr/bin/env python3
"""Best-effort: fetch the source video's transcript into transcript.txt.

Used in CI to ground the AI narrative in the actual video. Fails silently — the
prompt carries a curated framing fallback, and YouTube frequently blocks
datacenter IPs, so this is a bonus when it works, never a dependency.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_ID = os.environ.get("MUSIC_VIDEO_ID", "OmyrLc44dik")
LANGS = ["en", "en-US", "en-GB"]


def fetch_text():
    from youtube_transcript_api import YouTubeTranscriptApi
    # v1.x instance API
    try:
        fetched = YouTubeTranscriptApi().fetch(VIDEO_ID, languages=LANGS)
        return " ".join(getattr(s, "text", "") for s in fetched)
    except (AttributeError, TypeError):
        pass
    # v0.x static API
    chunks = YouTubeTranscriptApi.get_transcript(VIDEO_ID, languages=LANGS)
    return " ".join(c.get("text", "") for c in chunks)


def main():
    try:
        text = " ".join(fetch_text().split()).strip()
        if not text:
            raise RuntimeError("empty transcript")
        with open(os.path.join(HERE, "transcript.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        print(f"transcript: {len(text)} chars for {VIDEO_ID}")
    except Exception as e:  # noqa: BLE001 — best-effort, never fail the build
        print(f"[skip] transcript fetch for {VIDEO_ID}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
