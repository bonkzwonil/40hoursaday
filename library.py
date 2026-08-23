#!/usr/bin/env python3
"""
MIDI Library manager for 40hoursaday Practice Partner.
Copyright (c) 2026 Mathias Menzel-Nielsen
Licensed under the GNU General Public License v3.0 (GPL-3.0)

Handles directory scanning, metadata extraction (duration, bpm),
caching, and file uploads.
"""

import os
import time
from typing import List, Dict, Any, Optional
import mido

IGNORED_DIRS = {
    '.git', '.cache', '.local', '.config', '.vscode', '.emacs.d',
    'node_modules', '__pycache__', 'venv', '.venv', 'build', 'snap'
}

class MidiLibrary:
    def __init__(self, search_dirs: List[str]):
        self.search_dirs = [os.path.abspath(os.path.expanduser(d)) for d in search_dirs]
        self._meta_cache: Dict[str, Dict[str, Any]] = {}

    def get_upload_dir(self) -> str:
        """Returns the primary upload directory, ensuring it exists."""
        primary = self.search_dirs[0]
        os.makedirs(primary, exist_ok=True)
        return primary

    def get_file_metadata(self, filepath: str) -> Dict[str, Any]:
        """Extracts and caches metadata (duration, bpm, size, mtime) for a MIDI file."""
        try:
            stat = os.stat(filepath)
            mtime = stat.st_mtime
            size = stat.st_size
            
            # Check cache
            cached = self._meta_cache.get(filepath)
            if cached and cached.get("mtime") == mtime:
                return cached

            # Parse with mido
            mid = mido.MidiFile(filepath)
            duration = round(mid.length, 1)
            
            initial_tempo = 500000
            for track in mid.tracks:
                for msg in track:
                    if msg.type == 'set_tempo':
                        initial_tempo = msg.tempo
                        break
            bpm = round(mido.tempo2bpm(initial_tempo), 1)

            mins, secs = divmod(int(duration), 60)
            duration_str = f"{mins:02d}:{secs:02d}"

            filename = os.path.basename(filepath)
            display_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")

            meta = {
                "filepath": filepath,
                "filename": filename,
                "display_name": display_name,
                "size_bytes": size,
                "mtime": mtime,
                "mtime_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
                "duration": duration,
                "duration_str": duration_str,
                "bpm": bpm
            }
            self._meta_cache[filepath] = meta
            return meta
        except Exception as e:
            filename = os.path.basename(filepath)
            return {
                "filepath": filepath,
                "filename": filename,
                "display_name": os.path.splitext(filename)[0],
                "size_bytes": 0,
                "mtime": 0,
                "mtime_str": "",
                "duration": 0.0,
                "duration_str": "--:--",
                "bpm": 120.0,
                "error": str(e)
            }

    def scan_files(self) -> List[Dict[str, Any]]:
        """Scans all search directories for MIDI files quickly."""
        results = []
        seen_paths = set()

        for d in self.search_dirs:
            if not os.path.exists(d):
                continue
            
            for root, dirs, files in os.walk(d, topdown=True):
                # Prune hidden and unwanted directories in-place
                dirs[:] = [
                    sub for sub in dirs 
                    if not sub.startswith('.') and sub.lower() not in IGNORED_DIRS
                ]
                
                rel_depth = len(os.path.relpath(root, d).split(os.sep))
                if rel_depth > 3:
                    dirs.clear()
                    continue

                for f in files:
                    if f.lower().endswith(('.mid', '.midi')):
                        full_path = os.path.abspath(os.path.join(root, f))
                        if full_path not in seen_paths:
                            seen_paths.add(full_path)
                            results.append(self.get_file_metadata(full_path))

        # Sort alphabetically by display name
        results.sort(key=lambda x: x.get("display_name", "").lower())
        return results

    def save_uploaded_file(self, filename: str, content: bytes) -> Optional[Dict[str, Any]]:
        """Saves uploaded binary MIDI content into upload directory."""
        clean_name = os.path.basename(filename)
        if not clean_name.lower().endswith(('.mid', '.midi')):
            clean_name += '.mid'

        target_dir = self.get_upload_dir()
        target_path = os.path.join(target_dir, clean_name)

        base, ext = os.path.splitext(clean_name)
        counter = 1
        while os.path.exists(target_path):
            target_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
            counter += 1

        try:
            with open(target_path, "wb") as f:
                f.write(content)
            return self.get_file_metadata(target_path)
        except Exception as e:
            print(f"[MidiLibrary] Error saving upload: {e}")
            return None

    def delete_file(self, filepath: str) -> bool:
        """Deletes a MIDI file if it is located inside one of the library dirs."""
        norm_path = os.path.abspath(filepath)
        is_safe = any(norm_path.startswith(d) for d in self.search_dirs)
        if not is_safe or not os.path.isfile(norm_path):
            return False

        try:
            os.remove(norm_path)
            self._meta_cache.pop(norm_path, None)
            return True
        except Exception as e:
            print(f"[MidiLibrary] Error deleting {norm_path}: {e}")
            return False
