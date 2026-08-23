#!/usr/bin/env python3
"""
MIDI Playback Engine for 40hoursaday Practice Partner.
Copyright (c) 2026 Mathias Menzel-Nielsen
Licensed under the GNU General Public License v3.0 (GPL-3.0)

Handles accurate MIDI playback, real-time speed adjustment,
seeking, looping, metronome count-in, and ALSA/MIDI output.
"""

import math
import os
import threading
import time
from typing import List, Optional, Tuple, Dict, Any
import mido

class MidiPlayer:
    def __init__(self, default_port_substring: str = "Midi Through"):
        self.lock = threading.Lock()
        self._wake_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._should_stop = False

        # Configuration & Port
        self.target_port_name: Optional[str] = None
        self.default_port_substring = default_port_substring
        self._init_port()

        # Playback State
        self.state: str = "idle"  # "idle", "playing", "paused"
        self.current_filepath: Optional[str] = None
        self.current_filename: Optional[str] = None
        
        # Audio / MIDI Properties
        self.duration: float = 0.0
        self.bpm: float = 120.0
        self.time_signature: Tuple[int, int] = (4, 4)
        self.events: List[Tuple[float, mido.Message]] = []

        # Playback Controls
        self.speed: float = 1.0  # 0.10 to 2.00 (10% to 200%)
        self.position: float = 0.0  # Current position in original song seconds
        self.loop: bool = False
        self.transpose: int = 0  # Semitone shift (-12 to +12)
        self.count_in_bars: int = 0  # 0 = off, 1 = 1 bar, 2 = 2 bars

        # Real-time synchronization
        self._clock_base_time: float = 0.0
        self._song_base_pos: float = 0.0

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
        available = self.get_available_ports()
        if port_name in available:
            self.target_port_name = port_name
            return True
        # Try substring match
        for p in available:
            if port_name.lower() in p.lower():
                self.target_port_name = p
                return True
        return False

    def load_file(self, filepath: str) -> bool:
        """Loads and parses a MIDI file."""
        if not os.path.isfile(filepath):
            return False

        try:
            mid = mido.MidiFile(filepath)
            events = []
            current_time = 0.0
            
            initial_tempo = 500000  # Default 120 bpm (500000 us/beat)
            numerator = 4
            denominator = 4

            # Scan tracks for meta tempo/time sig
            for track in mid.tracks:
                for msg in track:
                    if msg.type == 'set_tempo':
                        initial_tempo = msg.tempo
                    elif msg.type == 'time_signature':
                        numerator = msg.numerator
                        denominator = msg.denominator

            # Flatten playback events with absolute seconds
            for msg in mid:
                current_time += msg.time
                if not msg.is_meta:
                    events.append((current_time, msg.copy()))

            with self.lock:
                self.current_filepath = filepath
                self.current_filename = os.path.basename(filepath)
                self.duration = current_time
                self.bpm = round(mido.tempo2bpm(initial_tempo), 1)
                self.time_signature = (numerator, denominator)
                self.events = events
                self.position = 0.0
                self.state = "idle"

            return True
        except Exception as e:
            print(f"[MidiPlayer] Error loading file {filepath}: {e}")
            return False

    def play(self, filepath: Optional[str] = None, speed: Optional[float] = None, 
             port: Optional[str] = None, loop: Optional[bool] = None, 
             count_in: Optional[int] = None, transpose: Optional[int] = None) -> bool:
        """Starts playback with optional parameters."""
        self.stop()

        if port:
            self.set_port(port)

        if filepath and filepath != self.current_filepath:
            if not self.load_file(filepath):
                return False

        if not self.events:
            return False

        with self.lock:
            if speed is not None:
                self.speed = max(0.10, min(3.0, float(speed)))
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

    def _update_position_unlocked(self):
        """Internal helper to calculate real-time position."""
        if self.state == "playing":
            elapsed_real = time.time() - self._clock_base_time
            self.position = min(self.duration, self._song_base_pos + elapsed_real * self.speed)

    def get_status(self) -> Dict[str, Any]:
        """Returns the current player status for the UI/API."""
        with self.lock:
            self._update_position_unlocked()
            return {
                "state": self.state,
                "filename": self.current_filename,
                "filepath": self.current_filepath,
                "position": round(self.position, 2),
                "duration": round(self.duration, 2),
                "speed": round(self.speed, 2),
                "speed_percent": int(round(self.speed * 100)),
                "loop": self.loop,
                "transpose": self.transpose,
                "count_in_bars": self.count_in_bars,
                "port": self.target_port_name,
                "available_ports": self.get_available_ports(),
                "bpm": self.bpm,
                "time_signature": f"{self.time_signature[0]}/{self.time_signature[1]}"
            }

    def _play_count_in(self, port) -> bool:
        """Plays metronome clicks before song starts."""
        if self.count_in_bars <= 0:
            return True

        beats_per_bar = self.time_signature[0]
        total_beats = self.count_in_bars * beats_per_bar
        base_beat_duration = 60.0 / max(20.0, self.bpm)
        
        for beat in range(total_beats):
            if self._should_stop:
                return False

            with self.lock:
                current_speed = self.speed

            beat_duration = base_beat_duration / current_speed
            is_accent = (beat % beats_per_bar == 0)
            note = 76 if is_accent else 77  # GM Woodblock
            vel = 110 if is_accent else 85

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

        return True

    def _playback_loop(self):
        """Core playback loop thread."""
        target_port = self.target_port_name
        if not target_port:
            self._init_port()
            target_port = self.target_port_name
            if not target_port:
                print("[MidiPlayer] No MIDI port available for playback.")
                with self.lock:
                    self.state = "idle"
                return

        try:
            with mido.open_output(target_port) as port:
                while True:
                    with self.lock:
                        if self._should_stop:
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

                        with self.lock:
                            msg_to_send = orig_msg.copy()
                            if self.transpose != 0 and msg_to_send.type in ('note_on', 'note_off', 'polytouch'):
                                if getattr(msg_to_send, 'channel', 0) != 9:
                                    new_note = max(0, min(127, msg_to_send.note + self.transpose))
                                    msg_to_send.note = new_note
                            self.position = event_t

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
                            for ch in range(16):
                                port.send(mido.Message('control_change', channel=ch, control=123, value=0))
                            time.sleep(0.3)
                            continue
                        else:
                            self.state = "idle"
                            self.position = 0.0
                            break

        except Exception as e:
            print(f"[MidiPlayer] Output error on {target_port}: {e}")
        finally:
            self.panic()
            with self.lock:
                self.state = "idle"
