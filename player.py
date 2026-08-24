#!/usr/bin/env python3
"""
MIDI Playback Engine for 40hoursaday Practice Partner.
Copyright (c) 2026 Mathias Menzel-Nielsen
Licensed under the GNU General Public License v3.0 (GPL-3.0)

Handles accurate MIDI playback, real-time speed adjustment,
seeking, looping, metronome count-in, and ALSA/MIDI output.
"""

import bisect
import json
import math
import os
import threading
import time
from typing import List, Optional, Tuple, Dict, Any
import mido

class MidiPlayer:
    def __init__(self, default_port_substring: str = "Midi Through", 
                 allow_program_change_patterns: Optional[List[str]] = None,
                 block_program_change_patterns: Optional[List[str]] = None):
        self.lock = threading.Lock()
        self._wake_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._should_stop = False

        # Configuration & Port
        self.target_port_name: Optional[str] = None
        self.default_port_substring = default_port_substring
        self.allow_patterns: List[str] = [p.lower().strip() for p in (allow_program_change_patterns or []) if p.strip()]
        self.block_patterns: List[str] = [p.lower().strip() for p in (block_program_change_patterns or []) if p.strip()]
        
        self.config_file = os.path.expanduser("~/.config/40hoursaday/port_settings.json")
        self.port_program_changes: Dict[str, bool] = {}
        # Playback State
        self.state: str = "idle"  # "idle", "playing", "paused"
        self.current_filepath: Optional[str] = None
        self.current_filename: Optional[str] = None
        
        # Audio / MIDI Properties
        self.duration: float = 0.0
        self.bpm: float = 120.0
        self.time_signature: Tuple[int, int] = (4, 4)
        self.events: List[Tuple[float, mido.Message]] = []
        self.beat_map: List[Dict[str, Any]] = []
        self.beat_times: List[float] = []
        self.meter_multiplier: float = 1.0
        self.custom_time_sig: Optional[Tuple[int, int]] = None
        self._mid_file_obj: Optional[mido.MidiFile] = None

        # Playback Controls
        self.speed: float = 1.0  # 0.10 to 2.00 (10% to 200%)
        self.volume: float = 1.0  # 0.0 to 1.0 (0% to 100% velocity scale)
        self.position: float = 0.0  # Current position in original song seconds
        self.loop: bool = False
        self.transpose: int = 0  # Semitone shift (-12 to +12)
        self.count_in_bars: int = 0  # 0 = off, 1 = 1 bar, 2 = 2 bars
        self.count_in_active: bool = False
        self.count_in_current_beat: int = 0
        self.count_in_total_beats: int = 0
        self.muted_channels: set = set()  # Set of 0-indexed muted channels (0..15)
        self.channel_volumes: Dict[int, float] = {ch: 1.0 for ch in range(16)}  # 0-indexed channel volumes (0.0 to 1.0)

        # Real-time synchronization
        self._clock_base_time: float = 0.0
        self._song_base_pos: float = 0.0

        self._load_port_settings()
        self._init_port()

    def _load_port_settings(self) -> None:
        """Loads per-device Program Change settings from disk."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.port_program_changes = data.get("program_changes", {})
            except Exception as e:
                print(f"[MidiPlayer] Warning: Could not load port settings: {e}")

    def _save_port_settings(self) -> None:
        """Saves per-device Program Change settings to disk."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"program_changes": self.port_program_changes}, f, indent=2)
        except Exception as e:
            print(f"[MidiPlayer] Warning: Could not save port settings: {e}")

    def is_program_change_allowed_for_port(self, port_name: Optional[str]) -> bool:
        """Checks whether Program Change / Bank Select events should be sent to this port."""
        if not port_name:
            return False

        # 1. Exact match in saved user settings
        if port_name in self.port_program_changes:
            return bool(self.port_program_changes[port_name])

        # 2. Substring match in saved user settings
        p_lower = port_name.lower().strip()
        for saved_port, allowed in self.port_program_changes.items():
            s_lower = saved_port.lower().strip()
            if s_lower in p_lower or p_lower in s_lower:
                return bool(allowed)

        # 3. CLI explicitly blocked
        if "all" in self.block_patterns:
            return False
        for pat in self.block_patterns:
            if pat in p_lower:
                return False

        # 4. CLI explicitly allowed
        if "all" in self.allow_patterns:
            return True
        for pat in self.allow_patterns:
            if pat in p_lower:
                return True

        # 5. Smart defaults based on device type
        # General MIDI synths (FluidSynth, Timidity, GM, default VirMIDI 0-0/16:0) allow Program Changes
        if any(x in p_lower for x in ("fluid", "musescore", "timidity", "gm", "virmidi 0-0", "16:0", "through", "synth")):
            return True

        # Piano plugins / hardware stage pianos protect presets
        if any(x in p_lower for x in ("pianoteq", "piano", "virmidi 0-1", "17:0", "stage")):
            return False

        # Default fallback: allow if not blocked
        return False

    def set_port_program_change(self, port_name: str, allow: bool) -> bool:
        """Configures and persists Program Change permission for a specific MIDI port."""
        if not port_name or not port_name.strip():
            return False
        with self.lock:
            self.port_program_changes[port_name.strip()] = bool(allow)
            self._save_port_settings()
        return True

    def _init_port(self):
        """Finds best matching output port."""
        available = self.get_available_ports()
        if not available:
            self.target_port_name = None
            return

        # Try to find default substring
        for port in available:
            if self.default_port_substring.lower() in port.lower():
                self.target_port_name = port
                return

        # Fallback to first available
        self.target_port_name = available[0]

    def get_available_ports(self) -> List[str]:
        """Returns all unique ALSA / MIDI output ports found by mido."""
        try:
            raw_ports = list(mido.get_output_names())
            unique_ports = []
            for p in raw_ports:
                if p and p not in unique_ports:
                    unique_ports.append(p)
            return unique_ports
        except Exception as e:
            print(f"[MidiPlayer] Error getting output names: {e}")
            return []

    def set_port(self, port_name: str) -> bool:
        """Sets target MIDI output port."""
        if not port_name or not port_name.strip():
            return False
        available = self.get_available_ports()
        matched_port = None
        if port_name in available:
            matched_port = port_name
        else:
            # Try bidirectional substring match
            p_lower = port_name.lower()
            for p in available:
                if p_lower in p.lower() or p.lower() in p_lower:
                    matched_port = p
                    break

        if matched_port:
            with self.lock:
                self.target_port_name = matched_port
                self._wake_event.set()
            return True
        return False

    @staticmethod
    def _build_beat_map(mid: mido.MidiFile, custom_num: Optional[int] = None, custom_den: Optional[int] = None, multiplier: float = 1.0) -> Tuple[List[Dict[str, Any]], List[float]]:
        """Extracts exact musical bars, beats, and tempo changes across the entire piece."""
        base_tpb = mid.ticks_per_beat or 480
        tpb = base_tpb
        
        tempo_events = []      # (abs_tick, tempo_us)
        time_sig_events = []   # (abs_tick, num, den)
        
        max_tick = 0
        for track in mid.tracks:
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                if msg.type == 'set_tempo':
                    tempo_events.append((abs_tick, msg.tempo))
                elif msg.type == 'time_signature':
                    time_sig_events.append((abs_tick, msg.numerator, msg.denominator))
            if abs_tick > max_tick:
                max_tick = abs_tick
                
        tempo_events.sort(key=lambda x: x[0])
        time_sig_events.sort(key=lambda x: x[0])
        
        # Deduplicate events at the same tick (keep last)
        def _dedup(events):
            d = {}
            for ev in events:
                d[ev[0]] = ev[1:]
            return sorted([(k, *v) for k, v in d.items()], key=lambda x: x[0])
            
        tempo_events = _dedup(tempo_events)
        time_sig_events = _dedup(time_sig_events)
        
        if not tempo_events or tempo_events[0][0] > 0:
            tempo_events.insert(0, (0, 500000))
        if not time_sig_events or time_sig_events[0][0] > 0:
            time_sig_events.insert(0, (0, custom_num or 4, custom_den or 4))
        elif custom_num and custom_den:
            time_sig_events = [(0, custom_num, custom_den)]
            
        # Build tempo segments for tick -> seconds piecewise conversion
        tempo_segments = []
        curr_time = 0.0
        for i in range(len(tempo_events)):
            start_tick, tempo = tempo_events[i]
            next_tick = tempo_events[i+1][0] if i+1 < len(tempo_events) else max_tick + tpb * 100
            tempo_segments.append((start_tick, next_tick, curr_time, tempo))
            delta_ticks = next_tick - start_tick
            curr_time += (delta_ticks * tempo) / (tpb * 1_000_000.0)
            
        def tick_to_time(tick):
            for start_tick, next_tick, start_time, tempo in tempo_segments:
                if start_tick <= tick < next_tick:
                    dtick = tick - start_tick
                    return start_time + (dtick * tempo) / (tpb * 1_000_000.0)
            last = tempo_segments[-1]
            dtick = tick - last[0]
            return last[2] + (dtick * last[3]) / (tpb * 1_000_000.0)

        def get_tempo_at_tick(tick):
            for start_tick, next_tick, start_time, tempo in tempo_segments:
                if start_tick <= tick < next_tick:
                    return tempo
            return tempo_segments[-1][3]

        beat_map = []
        current_bar = 1
        for i in range(len(time_sig_events)):
            start_tick, num, den = time_sig_events[i]
            if custom_num and custom_den:
                num, den = custom_num, custom_den
            next_tick = time_sig_events[i+1][0] if i+1 < len(time_sig_events) else max_tick + tpb * 10
            
            ticks_per_beat_unit = max(1, int(round(tpb * (4.0 / den) * multiplier)))
            ticks_per_bar = num * ticks_per_beat_unit
            
            t = start_tick
            while t < next_tick:
                delta_from_section = t - start_tick
                bar_offset = delta_from_section // ticks_per_bar
                bar_tick_rem = delta_from_section % ticks_per_bar
                beat_in_bar = (bar_tick_rem // ticks_per_beat_unit) + 1
                
                bar_num = current_bar + bar_offset
                time_sec = tick_to_time(t)
                tempo_us = get_tempo_at_tick(t)
                bpm = round(mido.tempo2bpm(tempo_us) / max(0.1, multiplier), 1)
                time_sig_str = f'{num}/{den}'
                
                next_beat_time = tick_to_time(t + ticks_per_beat_unit)
                beat_dur = max(0.001, next_beat_time - time_sec)
                
                beat_map.append({
                    'time': round(time_sec, 4),
                    'bar': bar_num,
                    'beat': beat_in_bar,
                    'beats_per_bar': num,
                    'bpm': bpm,
                    'time_sig': time_sig_str,
                    'time_sig_num': num,
                    'time_sig_den': den,
                    'duration': round(beat_dur, 4)
                })
                
                t += ticks_per_beat_unit
                
            section_ticks = next_tick - start_tick
            bars_in_section = (section_ticks + ticks_per_bar - 1) // ticks_per_bar
            current_bar += bars_in_section
            
        beat_times = [b['time'] for b in beat_map]
        return beat_map, beat_times

    def load_file(self, filepath: str) -> bool:
        """Loads and parses a MIDI file."""
        if not os.path.isfile(filepath):
            return False

        try:
            mid = mido.MidiFile(filepath)
            self._mid_file_obj = mid
            beat_map, beat_times = self._build_beat_map(
                mid,
                custom_num=self.time_signature[0] if self.custom_time_sig else None,
                custom_den=self.time_signature[1] if self.custom_time_sig else None,
                multiplier=self.meter_multiplier
            )
            events = []
            current_time = 0.0

            # Flatten playback events with absolute seconds
            for msg in mid:
                current_time += msg.time
                if not msg.is_meta:
                    events.append((current_time, msg.copy()))

            initial_bpm = beat_map[0]['bpm'] if beat_map else 120.0
            initial_sig = (beat_map[0]['time_sig_num'], beat_map[0]['time_sig_den']) if beat_map else (4, 4)

            with self.lock:
                self.current_filepath = filepath
                self.current_filename = os.path.basename(filepath)
                self.duration = current_time
                self.bpm = initial_bpm
                if not self.custom_time_sig:
                    self.time_signature = initial_sig
                self.events = events
                self.beat_map = beat_map
                self.beat_times = beat_times
                self.position = 0.0
                self.state = "idle"

            return True
        except Exception as e:
            print(f"[MidiPlayer] Error loading file {filepath}: {e}")
            return False

    def set_meter(self, numerator: Optional[int] = None, denominator: Optional[int] = None, multiplier: Optional[float] = None) -> bool:
        """Sets custom meter or sub-division multiplier and rebuilds beat map immediately."""
        with self.lock:
            if numerator is not None and denominator is not None:
                self.time_signature = (int(numerator), int(denominator))
                self.custom_time_sig = self.time_signature
            if multiplier is not None:
                self.meter_multiplier = max(0.25, min(4.0, float(multiplier)))
            
            if self._mid_file_obj:
                self.beat_map, self.beat_times = self._build_beat_map(
                    self._mid_file_obj,
                    custom_num=self.time_signature[0] if self.custom_time_sig else None,
                    custom_den=self.time_signature[1] if self.custom_time_sig else None,
                    multiplier=self.meter_multiplier
                )
            return True

    def play(self, filepath: Optional[str] = None, speed: Optional[float] = None, 
             port: Optional[str] = None, loop: Optional[bool] = None, 
             count_in: Optional[int] = None, transpose: Optional[int] = None,
             volume: Optional[float] = None) -> bool:
        """Starts playback with optional parameters."""
        self.stop()

        if port and isinstance(port, str) and port.strip():
            self.set_port(port.strip())

        if filepath and filepath != self.current_filepath:
            if not self.load_file(filepath):
                return False

        if not self.events:
            return False

        with self.lock:
            if speed is not None:
                self.speed = max(0.10, min(3.0, float(speed)))
            if volume is not None:
                v = float(volume)
                if v > 1.0:
                    v = v / 100.0
                self.volume = max(0.0, min(1.0, v))
            if loop is not None:
                self.loop = bool(loop)
            if count_in is not None:
                self.count_in_bars = max(0, min(4, int(count_in)))
            if transpose is not None:
                self.transpose = max(-24, min(24, int(transpose)))

            self.position = 0.0
            self.state = "playing"
            self._should_stop = False
            self._wake_event.clear()

        self._worker_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._worker_thread.start()
        return True

    def pause(self):
        """Pauses current playback."""
        with self.lock:
            if self.state == "playing":
                self.state = "paused"
                self._update_position_unlocked()
                self._wake_event.set()
        self.panic()

    def resume(self):
        """Resumes playback from current position."""
        with self.lock:
            if self.state == "paused":
                self.state = "playing"
                self._clock_base_time = time.time()
                self._song_base_pos = self.position
                self._wake_event.set()

    def stop(self):
        """Stops playback and resets position to 0."""
        with self.lock:
            self._should_stop = True
            self.state = "idle"
            self.position = 0.0
            self.count_in_active = False
            self.count_in_current_beat = 0
            self._wake_event.set()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None

        self.panic()

    def set_speed(self, speed: float):
        """Live updates playback speed."""
        speed = max(0.10, min(3.0, float(speed)))
        with self.lock:
            if self.state == "playing":
                self._update_position_unlocked()
                self._clock_base_time = time.time()
                self._song_base_pos = self.position
            self.speed = speed
            self._wake_event.set()

    def set_volume(self, volume: float):
        """Live updates playback volume (note velocity scaling)."""
        v = float(volume)
        if v > 1.0:
            v = v / 100.0
        with self.lock:
            self.volume = max(0.0, min(1.0, v))

    def seek(self, position_seconds: float):
        """Seeks to a specific position in seconds."""
        with self.lock:
            self.position = max(0.0, min(self.duration, float(position_seconds)))
            if self.state == "playing":
                self._clock_base_time = time.time()
                self._song_base_pos = self.position
                self._wake_event.set()
        self.panic()

    def set_loop(self, loop: bool):
        """Toggles looping."""
        with self.lock:
            self.loop = bool(loop)

    def set_transpose(self, transpose: int):
        """Sets semitone transpose."""
        with self.lock:
            self.transpose = max(-24, min(24, int(transpose)))

    def set_count_in(self, bars: int):
        """Sets count-in bars."""
        with self.lock:
            self.count_in_bars = max(0, min(4, int(bars)))

    def set_channel_volume(self, channel: int, volume: float) -> bool:
        """Sets volume scaling (0.0 to 1.0) for a MIDI channel (1-16 or 0-15)."""
        try:
            ch_num = int(channel)
            vol = float(volume)
        except (TypeError, ValueError):
            return False

        if 1 <= ch_num <= 16:
            ch_idx = ch_num - 1
        elif ch_num == 0:
            ch_idx = 0
        else:
            return False

        if vol > 1.0:
            vol = vol / 100.0
        vol = max(0.0, min(1.0, vol))

        with self.lock:
            self.channel_volumes[ch_idx] = vol
        return True

    def reset_channel_volumes(self) -> bool:
        """Resets all channel volumes to 1.0 (100%)."""
        with self.lock:
            for ch in range(16):
                self.channel_volumes[ch] = 1.0
        return True

    def set_channel_mute(self, channel: int, mute: bool) -> bool:
        """Sets mute state for a MIDI channel (accepts 1-based 1..16 or 0-based 0..15)."""
        try:
            ch_num = int(channel)
        except (TypeError, ValueError):
            return False

        if 1 <= ch_num <= 16:
            ch_idx = ch_num - 1
        elif ch_num == 0:
            ch_idx = 0
        else:
            return False

        with self.lock:
            if mute:
                self.muted_channels.add(ch_idx)
            else:
                self.muted_channels.discard(ch_idx)

        # If muting during active playback, send note-off/panic to that specific channel
        if mute and self.target_port_name:
            try:
                with mido.open_output(self.target_port_name) as port:
                    port.send(mido.Message('control_change', channel=ch_idx, control=123, value=0))
                    port.send(mido.Message('control_change', channel=ch_idx, control=120, value=0))
                    port.send(mido.Message('control_change', channel=ch_idx, control=64, value=0))
            except Exception:
                pass

        return True

    def unmute_all_channels(self) -> bool:
        """Unmutes all MIDI channels."""
        with self.lock:
            self.muted_channels.clear()
        return True

    def panic(self):
        """Sends all notes off, all sound off, and sustain off on all channels."""
        if not self.target_port_name:
            return
        try:
            with mido.open_output(self.target_port_name) as port:
                for ch in range(16):
                    port.send(mido.Message('control_change', channel=ch, control=123, value=0))
                    port.send(mido.Message('control_change', channel=ch, control=120, value=0))
                    port.send(mido.Message('control_change', channel=ch, control=64, value=0))
        except Exception as e:
            print(f"[MidiPlayer] Panic error: {e}")

    def get_bar_beat(self, pos: Optional[float] = None) -> Tuple[int, int, float, int, float, str, int, int]:
        """Calculates (bar, beat, beat_fraction, beats_per_bar, bpm, time_signature, time_sig_num, time_sig_den) for a given song position."""
        if pos is None:
            pos = self.position

        if not self.beat_map or not self.beat_times:
            beats_per_bar = max(1, self.time_signature[0])
            effective_bpm = max(10.0, self.bpm)
            sec_per_beat = 60.0 / effective_bpm
            total_beats = pos / sec_per_beat if sec_per_beat > 0 else 0.0
            bar = int(math.floor(total_beats / beats_per_bar)) + 1
            beat = int(math.floor(total_beats % beats_per_bar)) + 1
            beat_fraction = total_beats % 1.0
            return (bar, beat, round(beat_fraction, 3), beats_per_bar, self.bpm, f"{self.time_signature[0]}/{self.time_signature[1]}", self.time_signature[0], self.time_signature[1])

        idx = bisect.bisect_right(self.beat_times, pos) - 1
        if idx < 0:
            b = self.beat_map[0]
            return (b['bar'], b['beat'], 0.0, b['beats_per_bar'], b['bpm'], b['time_sig'], b['time_sig_num'], b['time_sig_den'])

        if idx >= len(self.beat_map):
            b = self.beat_map[-1]
            return (b['bar'], b['beat'], 1.0, b['beats_per_bar'], b['bpm'], b['time_sig'], b['time_sig_num'], b['time_sig_den'])

        b = self.beat_map[idx]
        elapsed = pos - b['time']
        beat_fraction = min(1.0, max(0.0, elapsed / max(0.001, b['duration'])))
        return (b['bar'], b['beat'], round(beat_fraction, 3), b['beats_per_bar'], b['bpm'], b['time_sig'], b['time_sig_num'], b['time_sig_den'])

    def _update_position_unlocked(self):
        """Internal helper to calculate real-time position."""
        if self.state == "playing":
            elapsed_real = time.time() - self._clock_base_time
            self.position = min(self.duration, self._song_base_pos + elapsed_real * self.speed)

    def get_status(self, include_beat_map: bool = True) -> Dict[str, Any]:
        """Returns the current player status for the UI/API."""
        with self.lock:
            self._update_position_unlocked()
            available = self.get_available_ports()
            bar, beat, beat_fraction, beats_per_bar, live_bpm, live_time_sig, time_sig_num, time_sig_den = self.get_bar_beat(self.position)
            res = {
                "state": self.state,
                "filename": self.current_filename,
                "filepath": self.current_filepath,
                "position": round(self.position, 3),
                "duration": round(self.duration, 2),
                "speed": round(self.speed, 2),
                "speed_percent": int(round(self.speed * 100)),
                "volume": round(self.volume, 2),
                "volume_percent": int(round(self.volume * 100)),
                "loop": self.loop,
                "transpose": self.transpose,
                "count_in_bars": self.count_in_bars,
                "count_in_active": self.count_in_active,
                "count_in_current_beat": self.count_in_current_beat,
                "count_in_total_beats": self.count_in_total_beats,
                "bar": bar,
                "beat": beat,
                "beat_fraction": beat_fraction,
                "beats_per_bar": beats_per_bar,
                "time_sig_num": time_sig_num,
                "time_sig_den": time_sig_den,
                "muted_channels": [ch + 1 for ch in sorted(self.muted_channels)],
                "channel_volumes": {ch + 1: int(round(self.channel_volumes.get(ch, 1.0) * 100)) for ch in range(10)},
                "port": self.target_port_name,
                "available_ports": available,
                "allow_program_change": self.is_program_change_allowed_for_port(self.target_port_name),
                "port_program_changes": {p: self.is_program_change_allowed_for_port(p) for p in available},
                "bpm": live_bpm,
                "time_signature": live_time_sig,
                "meter_multiplier": self.meter_multiplier,
                "custom_meter": self.custom_time_sig is not None
            }
            if include_beat_map:
                res["beat_map"] = self.beat_map
            return res

    def _play_count_in(self, port) -> bool:
        """Plays metronome clicks before song starts."""
        if self.count_in_bars <= 0:
            return True

        beats_per_bar = self.time_signature[0]
        total_beats = self.count_in_bars * beats_per_bar
        base_beat_duration = 60.0 / max(20.0, self.bpm)

        with self.lock:
            self.count_in_active = True
            self.count_in_total_beats = total_beats
            self.count_in_current_beat = 0
        
        try:
            for beat in range(total_beats):
                if self._should_stop:
                    return False

                with self.lock:
                    self.count_in_current_beat = beat + 1
                    current_speed = self.speed
                    current_volume = self.volume

                beat_duration = base_beat_duration / current_speed
                is_accent = (beat % beats_per_bar == 0)
                note = 76 if is_accent else 77  # GM Woodblock
                base_vel = 110 if is_accent else 85
                vel = 0 if current_volume <= 0 else max(1, min(127, int(round(base_vel * current_volume))))

                try:
                    port.send(mido.Message('note_on', channel=9, note=note, velocity=vel))
                    sleep_note = min(0.05, beat_duration * 0.3)
                    time.sleep(sleep_note)
                    port.send(mido.Message('note_off', channel=9, note=note, velocity=0))
                    remaining = max(0.0, beat_duration - sleep_note)
                    if remaining > 0:
                        time.sleep(remaining)
                except Exception as e:
                    print(f"[MidiPlayer] Count-in error: {e}")
                    time.sleep(beat_duration)
        finally:
            with self.lock:
                self.count_in_active = False
                self.count_in_current_beat = 0
                self.count_in_total_beats = 0

        return True

    def _playback_loop(self):
        """Core playback loop thread with dynamic port switching."""
        active_port_obj = None
        active_port_name = None

        def _get_current_target_port():
            with self.lock:
                if not self.target_port_name:
                    self._init_port()
                return self.target_port_name

        def _ensure_active_port():
            nonlocal active_port_obj, active_port_name
            desired = _get_current_target_port()
            if not desired:
                return None
            if active_port_obj is not None and active_port_name == desired:
                return active_port_obj

            # Switch port: send all notes off to old port and close it
            if active_port_obj is not None:
                try:
                    for ch in range(16):
                        active_port_obj.send(mido.Message('control_change', channel=ch, control=123, value=0))
                        active_port_obj.send(mido.Message('control_change', channel=ch, control=120, value=0))
                        active_port_obj.send(mido.Message('control_change', channel=ch, control=64, value=0))
                    active_port_obj.close()
                except Exception as e:
                    print(f"[MidiPlayer] Error closing old port {active_port_name}: {e}")
                active_port_obj = None
                active_port_name = None

            try:
                active_port_obj = mido.open_output(desired)
                active_port_name = desired
                return active_port_obj
            except Exception as e:
                print(f"[MidiPlayer] Failed to open MIDI port '{desired}': {e}")
                return None

        try:
            port = _ensure_active_port()
            if not port:
                print("[MidiPlayer] No MIDI port available for playback.")
                with self.lock:
                    self.state = "idle"
                return

            while True:
                with self.lock:
                    if self._should_stop:
                        break

                port = _ensure_active_port()
                if not port:
                    break

                # Metronome Count-in if starting at position 0
                if self.position <= 0.05 and self.count_in_bars > 0:
                    ok = self._play_count_in(port)
                    if not ok or self._should_stop:
                        break

                with self.lock:
                    self._clock_base_time = time.time()
                    self._song_base_pos = self.position
                    event_idx = 0
                    while event_idx < len(self.events) and self.events[event_idx][0] < self.position:
                        event_idx += 1

                while event_idx < len(self.events):
                    with self.lock:
                        if self._should_stop:
                            break

                        while self.state == "paused":
                            self._wake_event.clear()
                            self.lock.release()
                            self._wake_event.wait(timeout=0.2)
                            self.lock.acquire()
                            if self._should_stop:
                                break
                            if self.state == "playing":
                                self._clock_base_time = time.time()
                                self._song_base_pos = self.position
                                event_idx = 0
                                while event_idx < len(self.events) and self.events[event_idx][0] < self.position:
                                    event_idx += 1

                        if self._should_stop:
                            break

                        event_t, orig_msg = self.events[event_idx]
                        current_speed = self.speed
                        start_wall = self._clock_base_time
                        start_pos = self._song_base_pos

                    # Calculate wall clock target for next message
                    target_wall_time = start_wall + (event_t - start_pos) / current_speed
                    delay = target_wall_time - time.time()

                    if delay > 0.001:
                        woken = self._wake_event.wait(timeout=delay)
                        if woken:
                            self._wake_event.clear()
                            with self.lock:
                                if self._should_stop:
                                    break
                                event_idx = 0
                                while event_idx < len(self.events) and self.events[event_idx][0] < self.position:
                                    event_idx += 1
                            continue

                    port = _ensure_active_port()
                    if not port:
                        break

                    with self.lock:
                        msg_ch = getattr(orig_msg, 'channel', None)
                        is_muted = (msg_ch is not None and msg_ch in self.muted_channels)
                        if not is_muted:
                            msg_to_send = orig_msg.copy()
                            if self.transpose != 0 and msg_to_send.type in ('note_on', 'note_off', 'polytouch'):
                                if getattr(msg_to_send, 'channel', 0) != 9:
                                    new_note = max(0, min(127, msg_to_send.note + self.transpose))
                                    msg_to_send.note = new_note
                            if msg_to_send.type == 'note_on' and getattr(msg_to_send, 'velocity', 0) > 0:
                                ch_vol = self.channel_volumes.get(msg_ch, 1.0) if msg_ch is not None else 1.0
                                eff_vol = self.volume * ch_vol
                                if eff_vol <= 0.0:
                                    msg_to_send.velocity = 0
                                else:
                                    msg_to_send.velocity = max(1, min(127, int(round(msg_to_send.velocity * eff_vol))))
                        else:
                            msg_to_send = None

                    if msg_to_send is None:
                        event_idx += 1
                        continue

                    # Per-device Program Change & Bank Select filter
                    if msg_to_send.type == 'program_change' or (msg_to_send.type == 'control_change' and getattr(msg_to_send, 'control', -1) in (0, 32)):
                        if not self.is_program_change_allowed_for_port(active_port_name):
                            event_idx += 1
                            continue

                    try:
                        port.send(msg_to_send)
                    except Exception as e:
                        print(f"[MidiPlayer] Error sending message: {e}")

                    event_idx += 1

                with self.lock:
                    if self._should_stop:
                        break

                    if self.loop and not self._should_stop:
                        self.position = 0.0
                        self._clock_base_time = time.time()
                        self._song_base_pos = 0.0
                        if port:
                            for ch in range(16):
                                port.send(mido.Message('control_change', channel=ch, control=123, value=0))
                        time.sleep(0.3)
                        continue
                    else:
                        self.state = "idle"
                        self.position = 0.0
                        break

        except Exception as e:
            print(f"[MidiPlayer] Playback loop exception: {e}")
        finally:
            if active_port_obj is not None:
                try:
                    for ch in range(16):
                        active_port_obj.send(mido.Message('control_change', channel=ch, control=123, value=0))
                        active_port_obj.send(mido.Message('control_change', channel=ch, control=120, value=0))
                        active_port_obj.send(mido.Message('control_change', channel=ch, control=64, value=0))
                    active_port_obj.close()
                except Exception:
                    pass
            self.panic()
            with self.lock:
                self.state = "idle"
