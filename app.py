#!/usr/bin/env python3
"""
40hoursaday - Practice Partner Web Application
Copyright (c) 2026 Mathias Menzel-Nielsen
Licensed under the GNU General Public License v3.0 (GPL-3.0)

A modern, mobile-first MIDI practice assistant for musicians (violin, piano, etc.)
Allows selecting accompaniment pieces, dynamic speed scaling (10%-200%),
ALSA/MIDI device selection, seeking, looping, and count-in metronome.
"""

import argparse
import os
import sys
from player import MidiPlayer
from library import MidiLibrary
from server import ThreadedHTTPServer, PracticePartnerHandler

def main():
    parser = argparse.ArgumentParser(description="40hoursaday - MIDI Practice Partner Server")
    parser.add_argument("-H", "--host", default="0.0.0.0", help="HTTP host to bind to (default: 0.0.0.0)")
    parser.add_argument("-p", "--port", type=int, default=8090, help="HTTP port to listen on (default: 8080)")
    parser.add_argument("-d", "--midi-dir", action="append", help="MIDI directory to scan (can be specified multiple times)")
    parser.add_argument("-m", "--midi-port", default="Midi Through", help="Default MIDI output port substring (default: 'Midi Through')")
    parser.add_argument("--allow-program-change", action="store_true", default=False, help="Allow MIDI Program Change and Bank Select events (default: ignored to protect synth presets)")
    parser.add_argument("--lazy", "--lazy-loading", action="store_true", default=False, help="Enable fast lazy loading (skips parsing duration/BPM until played)")
    args = parser.parse_args()

    # Search directories for MIDI files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    primary_midi_dir = os.path.join(script_dir, "midi_files")
    os.makedirs(primary_midi_dir, exist_ok=True)

    default_dirs = [
        primary_midi_dir,
        os.path.expanduser("~/midi"),
        os.path.expanduser("~/Music"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Pianoteq 8 STAGE"),
        os.path.expanduser("~/Pianoteq"),
    ]
    
    midi_dirs = args.midi_dir if args.midi_dir else default_dirs
    # Only keep directories that exist
    valid_dirs = [primary_midi_dir] + [d for d in midi_dirs if d != primary_midi_dir and os.path.exists(d)]

    print("=" * 60)
    print("🎻  40HOURSADAY - Practice Partner")
    print("=" * 60)
    
    # Initialize Engine & Library
    player = MidiPlayer(
        default_port_substring=args.midi_port,
        ignore_program_change=not args.allow_program_change
    )
    library = MidiLibrary(search_dirs=valid_dirs, lazy_loading=args.lazy)

    print(f"📁 MIDI Directories : {', '.join(library.search_dirs)}")
    files = library.scan_files()
    print(f"🎵 Found MIDI Files  : {len(files)}")
    for f in files[:5]:
        print(f"   • {f['display_name']} ({f['duration_str']})")
    if len(files) > 5:
        print(f"   ... and {len(files) - 5} more")

    print(f"🎹 Active MIDI Port  : {player.target_port_name or 'None found'}")
    print(f"🌐 Web Server URL    : http://{args.host}:{args.port}")
    print(f"📱 Access URL        : http://localhost:{args.port}")
    print("=" * 60)

    PracticePartnerHandler.player = player
    PracticePartnerHandler.library = library

    httpd = ThreadedHTTPServer((args.host, args.port), PracticePartnerHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        player.stop()
        httpd.server_close()
        print("Done. Happy practicing!")

if __name__ == '__main__':
    main()
