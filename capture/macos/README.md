# Homebird macOS capture

## Screen text (AXReader)

```sh
swiftc -O AXReader.swift -o axreader
./axreader --interval 0.5 | python3 -m homebird ingest -
```

Grant **System Settings → Privacy & Security → Accessibility** to the
terminal (or the compiled binary) the first time. AXReader:

- reads only the **frontmost window's** accessibility tree — text, never pixels;
- **skips `AXSecureTextField`** (passwords are never captured, even pre-redaction);
- emits a frame **only when the content changed** (hash-deduped), so idle
  screens cost nothing;
- the Python side redacts secrets, dedupes again, and applies your
  deny-list before anything touches disk.

## Run at login (launchd)

Save as `~/Library/LaunchAgents/ai.homebird.capture.plist`, then
`launchctl load` it:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>ai.homebird.capture</string>
  <key>ProgramArguments</key><array>
    <string>/bin/sh</string><string>-c</string>
    <string>~/homebird/axreader --interval 0.5 | /usr/bin/python3 -m homebird ingest -</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
```

## Routines on a schedule

Run `python3 -m homebird routine run-due` every 5 minutes (launchd
`StartInterval` 300, or cron). Firing is idempotent per period, so
frequent polling is safe.

## Meetings

See `scripts/meeting_capture.sh` — records system audio and transcribes
locally with whisper.cpp, then ingests the transcript.
