// AXReader — Homebird's macOS screen-text capture daemon.
//
// Reads the frontmost window's Accessibility tree (text only, never
// screenshots), skips secure/password fields, dedupes identical frames,
// and emits JSON lines on stdout:
//   {"ts": 1720500000.1, "app": "Slack", "window": "#eng", "text": "..."}
//
// Build (on the Mac):   swiftc -O AXReader.swift -o axreader
// Run:                  ./axreader --interval 0.5 | python3 -m homebird ingest -
// Requires: System Settings → Privacy & Security → Accessibility → allow.

import AppKit
import ApplicationServices
import Foundation

let args = CommandLine.arguments
var interval = 0.5 // seconds between scans (2 Hz default; raise carefully)
if let i = args.firstIndex(of: "--interval"), i + 1 < args.count,
   let v = Double(args[i + 1]) { interval = max(0.05, v) }

guard AXIsProcessTrusted() else {
    FileHandle.standardError.write(
        "AXReader: not trusted. Grant Accessibility permission in System Settings.\n"
            .data(using: .utf8)!)
    exit(1)
}

let skipRoles: Set<String> = [
    kAXSecureTextFieldRole as String, // never read password fields
    "AXMenuBar", "AXScrollBar",
]

func collectText(_ element: AXUIElement, depth: Int, into out: inout [String]) {
    if depth > 24 || out.count > 400 { return }
    var roleRef: CFTypeRef?
    AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleRef)
    let role = roleRef as? String ?? ""
    if skipRoles.contains(role) { return }

    for attr in [kAXValueAttribute, kAXTitleAttribute, kAXDescriptionAttribute] {
        var ref: CFTypeRef?
        AXUIElementCopyAttributeValue(element, attr as CFString, &ref)
        if let s = ref as? String, s.count > 1, s.count < 20_000 {
            out.append(s)
        }
    }
    var childrenRef: CFTypeRef?
    AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString,
                                  &childrenRef)
    if let children = childrenRef as? [AXUIElement] {
        for child in children.prefix(64) {
            collectText(child, depth: depth + 1, into: &out)
        }
    }
}

var lastHash = 0

func scanFrontmost() {
    guard let app = NSWorkspace.shared.frontmostApplication else { return }
    let appName = app.localizedName ?? "unknown"
    let axApp = AXUIElementCreateApplication(app.processIdentifier)

    var windowRef: CFTypeRef?
    AXUIElementCopyAttributeValue(axApp, kAXFocusedWindowAttribute as CFString,
                                  &windowRef)
    guard let windowRefUnwrapped = windowRef else { return }
    let window = windowRefUnwrapped as! AXUIElement

    var titleRef: CFTypeRef?
    AXUIElementCopyAttributeValue(window, kAXTitleAttribute as CFString, &titleRef)
    let title = titleRef as? String ?? ""

    var texts: [String] = []
    collectText(window, depth: 0, into: &texts)
    let joined = texts.joined(separator: "\n")
    guard joined.count > 2 else { return }

    let frameHash = "\(appName)|\(title)|\(joined)".hashValue
    if frameHash == lastHash { return } // unchanged frame — emit nothing
    lastHash = frameHash

    let record: [String: Any] = [
        "ts": Date().timeIntervalSince1970,
        "app": appName,
        "window": title,
        "text": joined,
        "source": "screen",
    ]
    if let data = try? JSONSerialization.data(withJSONObject: record),
       let line = String(data: data, encoding: .utf8) {
        print(line)
        fflush(stdout)
    }
}

signal(SIGPIPE, SIG_IGN)
while true {
    scanFrontmost()
    Thread.sleep(forTimeInterval: interval)
}
