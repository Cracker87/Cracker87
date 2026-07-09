#!/bin/sh
# Homebird meeting capture (macOS): record system audio + mic, transcribe
# locally with whisper.cpp, ingest the transcript. Fully offline.
#
# One-time setup:
#   brew install ffmpeg blackhole-2ch
#   git clone https://github.com/ggerganov/whisper.cpp && cd whisper.cpp
#   make -j && ./models/download-ggml-model.sh medium
#   # In Audio MIDI Setup: create a Multi-Output (speakers + BlackHole)
#   # and select it as system output during meetings.
#
# Usage: ./meeting_capture.sh "Meeting title"   (Ctrl-C to stop)

set -eu
TITLE="${1:-Meeting}"
WHISPER_DIR="${WHISPER_DIR:-$HOME/whisper.cpp}"
TMPWAV="$(mktemp -t homebird_meeting).wav"

echo "Recording… Ctrl-C to stop." >&2
# :BlackHole device index may differ; list devices with:
#   ffmpeg -f avfoundation -list_devices true -i ""
ffmpeg -loglevel error -f avfoundation -i ":BlackHole 2ch" \
    -ac 1 -ar 16000 "$TMPWAV" || true

echo "Transcribing locally with whisper.cpp…" >&2
"$WHISPER_DIR/main" -m "$WHISPER_DIR/models/ggml-medium.bin" \
    -f "$TMPWAV" -otxt -of "$TMPWAV" >/dev/null

python3 - "$TITLE" "$TMPWAV.txt" <<'PY'
import json, sys, time
title, path = sys.argv[1], sys.argv[2]
text = open(path).read().strip()
line = json.dumps({"ts": time.time(), "source": "meeting",
                   "app": "Meeting", "window": title,
                   "text": f"Transcript: {text}"})
import subprocess
subprocess.run([sys.executable, "-m", "homebird", "ingest", "-"],
               input=line, text=True, check=True)
PY

rm -f "$TMPWAV" "$TMPWAV.txt"
echo "Meeting '$TITLE' transcribed and ingested." >&2
