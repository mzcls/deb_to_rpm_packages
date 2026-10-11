#!/usr/bin/env python3
"""
Fix the WeMeet (腾讯会议) Linux client's xdg-desktop-portal ScreenCast D-Bus race.

Root cause
----------
libscreen_share_module.so issues the standard ScreenCast calls

    CreateSession -> SelectSources -> Start -> OpenPipeWireRemote

but calls ``Start`` immediately after emitting ``SelectSources``, without
waiting for the ``SelectSources`` Response signal.  This is a race that some
portal backends tolerate (xdg-desktop-portal-gnome sets the parameters
synchronously and shows the picker during ``Start``) and others do not
(xdg-desktop-portal-wlr/-hyprland block in ``SelectSources`` while the user
picks a source, so the too-early ``Start`` fails).  The visible symptom on
Wayland is that sharing never starts / shows no video.

Fix
---
This applies only "Hunk 0" of the community patch
    https://github.com/Matheritasiv/wemeet-screenshare-patch
which moves the ``dbusStart()`` call out of ``dbusSelectSources()`` and into
the ``onSelectSourcesResponse()`` callback, repairing the async chain.

The colour-format hunks (upstream "Hunk 1a"/"Hunk 1b" plus a preloaded hook)
are intentionally *not* applied: GNOME's portal backend natively supports the
``BGRx`` format WeMeet asks for and does not offer ``RGBx``, so forcing the
colour conversion breaks capture on GNOME (white/black screen).  See upstream
issue #2.  If you are on a backend that genuinely lacks ``BGRx`` support, those
hunks must be applied separately together with the hook.

Usage
-----
    wemeet-dbus-race-fix.py <wemeet_root> [--strict]

<wemeet_root> is the installation root, e.g. /opt/wemeet (or the RPM buildroot
counterpart).  Offsets are validated byte-for-byte before writing anything; on
an unknown build the script skips with a warning (or fails with --strict).
"""

import argparse
import mmap
import os
import sys

REL_PATH = "bin/modules/screen_share/libscreen_share_module.so"

# Hunk 0 from the upstream patch (offset -> (original, patched)); equal lengths.
HUNK0 = {
    0x43D2FA: (bytes.fromhex("00"), bytes.fromhex("5d")),
    0x43D331: (bytes.fromhex("88f7"), bytes.fromhex("60fb")),
    0x43D336: (bytes.fromhex("83c718488b8588f7ffff48"), bytes.fromhex("89fe4883c618e910000000")),
    0x43D357: (bytes.fromhex("0000"), bytes.fromhex("e208")),
    0x43DC38: (bytes.fromhex("e8c305d9"), bytes.fromhex("e9ecf6ff")),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply WeMeet ScreenCast D-Bus race fix (Hunk 0).")
    ap.add_argument("wemeet_root", help="WeMeet installation root, e.g. /opt/wemeet")
    ap.add_argument("--strict", action="store_true",
                    help="fail (non-zero) instead of skipping when the build is unknown")
    args = ap.parse_args()

    path = os.path.join(args.wemeet_root.rstrip("/"), REL_PATH)
    if not os.path.isfile(path):
        print(f"[wemeet-patch] file not found: {path}")
        return 1 if args.strict else 0

    size = os.path.getsize(path)
    with open(path, "r+b") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_WRITE)

        # Already patched? (idempotent)
        if all(mm[o:o + len(p)] == p for o, (_orig, p) in HUNK0.items()):
            print("[wemeet-patch] already patched, nothing to do")
            mm.close()
            return 0

        # Validate every site before writing any of them.
        mismatches = []
        for offset, (original, _patched) in sorted(HUNK0.items()):
            if offset + len(original) > size:
                mismatches.append((offset, b"<out of bounds>", original))
                continue
            actual = mm[offset:offset + len(original)]
            if actual != original:
                mismatches.append((offset, actual, original))

        if mismatches:
            for offset, actual, expected in mismatches:
                print(f"[wemeet-patch] MISMATCH 0x{offset:08x}: expected {expected.hex()} got {actual.hex()}")
            mm.close()
            print("[wemeet-patch] WARNING: unrecognised WeMeet build, screen-share fix NOT applied")
            return 1 if args.strict else 0

        for offset, (_original, patched) in sorted(HUNK0.items()):
            mm.seek(offset)
            mm.write(patched)
        mm.flush()
        mm.close()

    print("[wemeet-patch] applied Hunk 0 (ScreenCast D-Bus race fix)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
