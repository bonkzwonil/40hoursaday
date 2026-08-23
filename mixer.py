#!/usr/bin/env python3
"""
PulseAudio Mixer Interface using pactl JSON format.
Copyright (c) 2026 Mathias Menzel-Nielsen
Licensed under the GNU General Public License v3.0 (GPL-3.0)

Thin, robust wrapper to query and control PulseAudio sinks and application streams.
"""

import json
import subprocess
from typing import Dict, List, Any, Optional

def _parse_volume_dict(vol_dict: Optional[dict]) -> int:
    """Extract an average integer volume percentage (0-100+) from pactl volume dict."""
    if not vol_dict:
        return 100
    percents = []
    for ch, data in vol_dict.items():
        if isinstance(data, dict) and "value_percent" in data:
            val_str = data["value_percent"].rstrip("%")
            try:
                percents.append(int(val_str))
            except ValueError:
                pass
    return int(sum(percents) / len(percents)) if percents else 100

def _format_stream_label(app_name: str, media_name: str) -> str:
    """Produce a friendly user-facing label for known application streams."""
    low_app = (app_name or "").lower()
    low_med = (media_name or "").lower()
    
    if "shairport" in low_app or "shairport" in low_med:
        return "AirPlay (Shairport Sync)"
    if "pianoteq" in low_app or "pianoteq" in low_med:
        return "Pianoteq"
    if "spotify" in low_app or "librespot" in low_app:
        return "Spotify"
    if "mpd" in low_app or "mopidy" in low_app:
        return "Music Player Daemon"
    if "browser" in low_app or "chrome" in low_app or "firefox" in low_app:
        return "Web Browser"
    
    return app_name or media_name or "Audio Stream"

class PulseMixer:
    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Fetch current PulseAudio sinks and active application playback streams."""
        sinks_out: List[Dict[str, Any]] = []
        streams_out: List[Dict[str, Any]] = []
        
        # 1. Fetch Sinks (Hardware Outputs)
        try:
            raw_sinks = subprocess.check_output(
                ["pactl", "--format=json", "list", "sinks"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2.0
            )
            parsed_sinks = json.loads(raw_sinks)
            if isinstance(parsed_sinks, list):
                for s in parsed_sinks:
                    desc = s.get("description") or s.get("name") or f"Sink #{s.get('index')}"
                    sinks_out.append({
                        "id": s.get("index"),
                        "name": s.get("name", ""),
                        "description": desc,
                        "volume": _parse_volume_dict(s.get("volume")),
                        "mute": bool(s.get("mute")),
                        "state": s.get("state", "UNKNOWN")
                    })
        except Exception:
            pass

        # 2. Fetch Sink-Inputs (Application Streams)
        try:
            raw_inputs = subprocess.check_output(
                ["pactl", "--format=json", "list", "sink-inputs"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2.0
            )
            parsed_inputs = json.loads(raw_inputs)
            if isinstance(parsed_inputs, list):
                for i in parsed_inputs:
                    props = i.get("properties", {})
                    raw_app = props.get("application.name", "")
                    raw_media = props.get("media.name", "")
                    friendly_label = _format_stream_label(raw_app, raw_media)
                    
                    streams_out.append({
                        "id": i.get("index"),
                        "name": friendly_label,
                        "raw_app": raw_app,
                        "raw_media": raw_media,
                        "volume": _parse_volume_dict(i.get("volume")),
                        "mute": bool(i.get("mute")),
                        "corked": bool(i.get("corked")),
                        "sink_id": i.get("sink")
                    })
        except Exception:
            pass

        return {
            "sinks": sinks_out,
            "streams": streams_out,
            "count_sinks": len(sinks_out),
            "count_streams": len(streams_out)
        }

    @staticmethod
    def set_sink_volume(sink_id: int, volume_percent: int) -> bool:
        """Set volume percentage (0-150%) for a sink."""
        volume_percent = max(0, min(150, int(volume_percent)))
        try:
            subprocess.run(
                ["pactl", "set-sink-volume", str(sink_id), f"{volume_percent}%"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0
            )
            return True
        except Exception:
            return False

    @staticmethod
    def set_sink_mute(sink_id: int, mute: bool) -> bool:
        """Set mute state for a sink."""
        mute_val = "1" if mute else "0"
        try:
            subprocess.run(
                ["pactl", "set-sink-mute", str(sink_id), mute_val],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0
            )
            return True
        except Exception:
            return False

    @staticmethod
    def set_stream_volume(stream_id: int, volume_percent: int) -> bool:
        """Set volume percentage (0-150%) for a playback stream (sink-input)."""
        volume_percent = max(0, min(150, int(volume_percent)))
        try:
            subprocess.run(
                ["pactl", "set-sink-input-volume", str(stream_id), f"{volume_percent}%"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0
            )
            return True
        except Exception:
            return False

    @staticmethod
    def set_stream_mute(stream_id: int, mute: bool) -> bool:
        """Set mute state for a playback stream (sink-input)."""
        mute_val = "1" if mute else "0"
        try:
            subprocess.run(
                ["pactl", "set-sink-input-mute", str(stream_id), mute_val],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0
            )
            return True
        except Exception:
            return False
