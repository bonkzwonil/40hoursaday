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
from fractions import Fraction
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
        self.grid_offset_beats: float = 0.0   # shifts the barline grid
        self.bar_number_offset: int = 0       # renumbers bar 1 to match a score
        self.pickup_bar_zero: bool = True     # Auftakt is bar 0, first full bar is 1
        self.nominal_bpm: float = 120.0       # stable tempo of the piece
        self.expressive_tempo: bool = False   # tempo map records rubato, not marks
        self.main_time_signature: Tuple[int, int] = (4, 4)  # ignores a pickup bar
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

    # ------------------------------------------------------------------
    # Musical timeline (tempo map / meter map / bar & beat grid)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_timeline(mid: mido.MidiFile) -> Dict[str, Any]:
        """Reads tempo changes, meter changes and the musical extent from every track.

        Ticks are absolute and never snapped: the tempo map has to reproduce mido's
        own playback timing exactly, otherwise the metronome drifts against the audio.
        """
        tempo_map: Dict[int, int] = {}          # tick -> microseconds per quarter
        meter_map: Dict[int, Tuple[int, int]] = {}  # tick -> (numerator, denominator)
        first_onset: Optional[int] = None
        last_onset: int = 0
        last_sound: int = 0
        max_tick: int = 0

        for track in mid.tracks:
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                if msg.type == 'set_tempo':
                    # Later tracks win at the same tick, matching merge_tracks order.
                    tempo_map[abs_tick] = msg.tempo
                elif msg.type == 'time_signature':
                    meter_map[abs_tick] = (max(1, msg.numerator), max(1, msg.denominator))
                elif msg.type == 'note_on' and msg.velocity > 0:
                    if first_onset is None or abs_tick < first_onset:
                        first_onset = abs_tick
                    if abs_tick > last_onset:
                        last_onset = abs_tick
                    if abs_tick > last_sound:
                        last_sound = abs_tick
                elif msg.type == 'note_off' or msg.type == 'note_on':
                    # Note ends still count as sounding: a final chord may ring on
                    # long after its onset, and the bar count has to keep running.
                    if abs_tick > last_sound:
                        last_sound = abs_tick
            if abs_tick > max_tick:
                max_tick = abs_tick

        # MIDI default before any set_tempo is 120 BPM (500000 us per quarter).
        if 0 not in tempo_map:
            tempo_map[0] = 500000
        tempos = sorted(tempo_map.items())

        # A meter event a hair after 0 is a writer quirk; it still opens measure 1.
        meters = sorted(meter_map.items())
        if meters and 0 < meters[0][0] <= max(1, (mid.ticks_per_beat or 480) // 8):
            meters = [(0, meters[0][1])] + meters[1:]
        if not meters or meters[0][0] != 0:
            meters = [(0, (4, 4))] + [m for m in meters if m[0] > 0]
        # Collapse consecutive duplicates - a repeated identical meter must not
        # open a spurious measure and bump every following bar number.
        collapsed: List[Tuple[int, Tuple[int, int]]] = []
        for tick, sig in meters:
            if collapsed and collapsed[-1][1] == sig:
                continue
            collapsed.append((tick, sig))

        return {
            'tempos': tempos,
            'meters': collapsed,
            'first_onset': first_onset,
            'last_onset': last_onset,
            'last_sound': last_sound,
            'max_tick': max_tick,
        }

    @staticmethod
    def _make_tick_clock(tempos: List[Tuple[int, int]], tpb: int):
        """Returns (tick_to_time, tempo_at_tick) for a piecewise-constant tempo map."""
        starts: List[int] = []
        offsets: List[float] = []
        values: List[int] = []
        elapsed = 0.0
        for i, (tick, tempo) in enumerate(tempos):
            if i > 0:
                elapsed += (tick - tempos[i - 1][0]) * tempos[i - 1][1] / (tpb * 1_000_000.0)
            starts.append(tick)
            offsets.append(elapsed)
            values.append(tempo)

        def tick_to_time(tick: float) -> float:
            i = bisect.bisect_right(starts, tick) - 1
            if i < 0:
                i = 0
            return offsets[i] + (tick - starts[i]) * values[i] / (tpb * 1_000_000.0)

        def tempo_at_tick(tick: float) -> int:
            i = bisect.bisect_right(starts, tick) - 1
            return values[max(0, i)]

        return tick_to_time, tempo_at_tick

    @staticmethod
    def _strong_beats(num: int, den: int) -> set:
        """Beats that carry a natural accent, 1-based.

        Compound meters group their eighths in threes, so 6/8 is felt in 2 and
        9/8 in 3 - accenting all six eighths of a 6/8 bar is simply wrong.
        """
        if den >= 8 and num in (6, 9, 12) and num % 3 == 0:
            return {i for i in range(1, num + 1) if (i - 1) % 3 == 0}
        if num == 4:
            return {1, 3}
        return {1}

    @staticmethod
    def _on_musical_grid(tick: int, tpb: int) -> bool:
        """Whether a tick sits on a note value a writer would actually have typed.

        Used to tell an engraved score from a recorded performance. Anything on a
        sixteenth - or on a triplet eighth - was placed deliberately; a value a few
        ticks off a barline is a human attack, and means nothing structurally.
        """
        for divisor in (4, 3, 6, 8):
            unit = tpb / divisor
            if unit >= 1 and abs(tick / unit - round(tick / unit)) * unit <= 1.0:
                return True
        return False

    @staticmethod
    def _detect_pickup(meters: List[Tuple[int, Tuple[int, int]]], tpb: int,
                       first_onset: Optional[int], mult_num: int, mult_den: int) -> bool:
        """True when the piece opens with an Auftakt (pickup measure).

        This matters because a pickup counted as bar 1 puts every later bar number
        one off the printed score, which is exactly the number a player is reading
        off the page. Two notations occur in the wild:

          a) engraver style - the anacrusis is its own short measure, e.g. a 1/4 bar
             in front of the real 3/4 (MuseScore, Sibelius, Finale all write this).
             This is unambiguous and is trusted outright.

          b) sequencer style - measure 1 is present at full length but padded with
             rests, so the first note enters late inside an otherwise normal bar.
             Here "pickup" and "the piece simply opens on a rest" look identical in
             the file, so this is only accepted on strong evidence: the entry has to
             sit on a real note value, and the anacrusis has to be short enough to be
             one. A recorded performance, whose notes land wherever the player put
             them, is left alone rather than guessed at - an unstable guess would
             flip the whole bar count on a note landing a few ticks either way.
        """
        def bar_ticks(num: int, den: int) -> int:
            return max(1, round(num * tpb * 4 * mult_num / (den * mult_den)))

        # a) short opening measure followed by a longer meter
        if len(meters) >= 2:
            (t0, (n0, d0)), (t1, (n1, d1)) = meters[0], meters[1]
            first_span = t1 - t0
            if first_span == bar_ticks(n0, d0) and first_span < bar_ticks(n1, d1):
                return True

        # b) padded first measure - only when the entry is clearly notated
        if first_onset is None:
            return False
        t0, (n0, d0) = meters[0]
        bar = bar_ticks(n0, d0)
        beat = max(1, bar // max(1, n0))
        offset = first_onset - t0
        if not beat <= offset < bar:
            return False
        anacrusis = bar - offset
        return anacrusis <= bar / 2 and MidiPlayer._on_musical_grid(offset, tpb)

    @staticmethod
    def _build_beat_map(mid: mido.MidiFile, custom_num: Optional[int] = None,
                        custom_den: Optional[int] = None, multiplier: float = 1.0,
                        grid_offset_beats: float = 0.0,
                        bar_number_offset: int = 0,
                        pickup_bar_zero: bool = True) -> Tuple[List[Dict[str, Any]], List[float]]:
        """Builds the exact bar/beat grid of the piece.

        Beat positions are derived in ticks with rational arithmetic and only then
        converted to seconds through the tempo map, so a piece with hundreds of
        tempo changes stays sample-accurate instead of accumulating rounding drift.

        grid_offset_beats shifts the whole grid (for files whose barlines do not
        start at tick 0) and bar_number_offset renumbers bar 1 (for files whose
        bar numbering does not match the printed score).

        pickup_bar_zero picks the numbering convention for an Auftakt. Engravers
        leave the anacrusis unnumbered so that bar 1 is the first full measure,
        which is what MuseScore, Sibelius and Finale all print; counting it as
        bar 1 instead is the other common convention. Both are defensible, so it
        is a setting rather than a decision made here.
        """
        tpb = mid.ticks_per_beat or 480
        info = MidiPlayer._extract_timeline(mid)
        tempos = info['tempos']
        meters = info['meters']

        tick_to_time, tempo_at_tick = MidiPlayer._make_tick_clock(tempos, tpb)

        mult = Fraction(max(0.05, float(multiplier))).limit_denominator(64)
        if custom_num and custom_den:
            meters = [(0, (int(custom_num), int(custom_den)))]

        # Where the music actually stops. Bars past this point are phantoms: many
        # files carry a long tail of markers or controller data after the last note.
        music_end = info['last_sound'] or info['last_onset'] or info['max_tick']

        shift = 0
        if grid_offset_beats:
            base_den = meters[0][1][1]
            shift = int(round(float(grid_offset_beats) * tpb * 4 * mult.numerator
                              / (base_den * mult.denominator)))

        beat_map: List[Dict[str, Any]] = []
        pickup = MidiPlayer._detect_pickup(meters, tpb, info['first_onset'],
                                           mult.numerator, mult.denominator)
        bar_number = (0 if (pickup and pickup_bar_zero) else 1) + int(bar_number_offset)

        for i, (section_start, (num, den)) in enumerate(meters):
            section_end = meters[i + 1][0] if i + 1 < len(meters) else None
            if section_end is None:
                # Last section runs to the end of the bar that still holds music.
                section_end = music_end + 1
            if section_end <= section_start:
                continue

            # Exact tick length of one beat and one bar in this section. The floor
            # matters: a corrupt file can declare an absurd denominator, and a beat
            # shorter than a tick would make the walk below crawl through hundreds
            # of millions of iterations before reaching the end of the piece.
            beat_ticks = max(Fraction(1), Fraction(tpb * 4, den) * mult)
            bar_ticks = beat_ticks * num
            strong = MidiPlayer._strong_beats(num, den)
            quarters_per_bar = float(bar_ticks) / tpb
            origin = section_start + shift

            k = 0
            bars_done = 0
            while True:
                pos = origin + beat_ticks * k
                tick = int(round(pos))
                if tick >= section_end:
                    break
                if tick < 0:
                    # A negative grid offset can push the first beats before the
                    # start of the file; there is no music there to count.
                    k += 1
                    continue

                beat_in_bar = (k % num) + 1
                bar_no = bar_number + (k // num)

                start_s = tick_to_time(tick)
                end_s = tick_to_time(int(round(origin + beat_ticks * (k + 1))))
                bar_start_tick = int(round(origin + bar_ticks * (k // num)))
                bar_end_tick = int(round(origin + bar_ticks * (k // num + 1)))
                bar_secs = max(1e-6, tick_to_time(bar_end_tick) - tick_to_time(bar_start_tick))

                # Three tempi, because they are genuinely different numbers.
                #
                # bpm       the piece's tempo in quarter notes, averaged over this
                #           bar. Quarter notes because that is what the MIDI tempo
                #           meta means and what every DAW shows: a 6/8 bar lasting
                #           three seconds is 60, not 120. Averaged over the bar
                #           because performance files carry a set_tempo on every
                #           single beat, and the raw values swing so wildly that a
                #           live readout is unreadable.
                # bpm_beat  the instantaneous value, exact but jumpy.
                # click_bpm the rate the metronome actually ticks at, which follows
                #           the beat unit and the sub-division setting.
                inst_bpm = mido.tempo2bpm(tempo_at_tick(tick))
                bar_bpm = 60.0 * quarters_per_bar / bar_secs
                click_bpm = 60.0 * num / bar_secs

                beat_map.append({
                    'time': round(start_s, 5),
                    'bar': bar_no,
                    'beat': beat_in_bar,
                    'beats_per_bar': num,
                    'bpm': round(bar_bpm, 1),
                    'bpm_beat': round(inst_bpm, 1),
                    'click_bpm': round(click_bpm, 1),
                    'time_sig': f'{num}/{den}',
                    'time_sig_num': num,
                    'time_sig_den': den,
                    'accent': beat_in_bar in strong,
                    'downbeat': beat_in_bar == 1,
                    'tick': tick,
                    'duration': round(max(0.001, end_s - start_s), 5),
                })

                k += 1
                bars_done = (k + num - 1) // num

            bar_number += max(0, bars_done)

        beat_times = [b['time'] for b in beat_map]
        return beat_map, beat_times

    @staticmethod
    def _nominal_bpm(beat_map: List[Dict[str, Any]]) -> float:
        """One stable tempo for the whole piece: the median bar tempo.

        Reading the first tempo event instead is wrong for recorded performances,
        where the opening beat is often nowhere near the tempo the piece settles
        into, and it is wrong again for pieces that open with a slow introduction.
        The median ignores both, along with any closing ritardando.
        """
        if not beat_map:
            return 120.0
        values = sorted(b['bpm'] for b in beat_map)
        i = len(values) // 2
        med = values[i] if len(values) % 2 else (values[i - 1] + values[i]) / 2.0
        return round(med, 1)

    @staticmethod
    def _main_time_signature(beat_map: List[Dict[str, Any]]) -> Tuple[int, int]:
        """The meter the piece actually lives in, measured by how many bars use it.

        The first meter event is a bad answer: engraver exports often open with a
        one-beat pickup measure, and counting a musician in with a single click
        because bar 0 happens to be 1/4 would be nonsense.
        """
        if not beat_map:
            return (4, 4)
        tally: Dict[Tuple[int, int], int] = {}
        for b in beat_map:
            if b['beat'] == 1:
                key = (b['time_sig_num'], b['time_sig_den'])
                tally[key] = tally.get(key, 0) + 1
        if not tally:
            return (beat_map[0]['time_sig_num'], beat_map[0]['time_sig_den'])
        return max(tally.items(), key=lambda kv: kv[1])[0]

    @staticmethod
    def _tempo_is_expressive(mid: mido.MidiFile, beat_map: List[Dict[str, Any]]) -> bool:
        """True when the tempo map describes a performance rather than the score.

        A file carrying a set_tempo on virtually every beat is not marking tempo
        changes, it is recording how a human pushed and pulled the pulse. Those
        instantaneous values swing by a factor of ten inside a single phrase, so
        showing them as "the tempo" is noise; the piece's settled tempo is the
        useful number. A file with a handful of tempo events means them literally
        - an accelerando, a ritardando, a new section - and those should be shown
        as they happen.
        """
        if not beat_map:
            return False
        tempos = MidiPlayer._extract_timeline(mid)['tempos']
        return len(tempos) >= max(8, 0.4 * len(beat_map))

    def load_file(self, filepath: str) -> bool:
        """Loads and parses a MIDI file."""
        if not os.path.isfile(filepath):
            return False

        try:
            mid = mido.MidiFile(filepath)
            self._mid_file_obj = mid
            self.custom_time_sig = None
            self.meter_multiplier = 1.0
            self.grid_offset_beats = 0.0
            self.bar_number_offset = 0

            beat_map, beat_times = self._build_beat_map(
                mid,
                custom_num=None,
                custom_den=None,
                multiplier=1.0,
                pickup_bar_zero=self.pickup_bar_zero
            )
            events = []
            current_time = 0.0

            # Flatten playback events with absolute seconds
            for msg in mid:
                current_time += msg.time
                if not msg.is_meta:
                    events.append((current_time, msg.copy()))

            nominal = self._nominal_bpm(beat_map)
            main_sig = self._main_time_signature(beat_map)
            expressive = self._tempo_is_expressive(mid, beat_map)

            with self.lock:
                self.current_filepath = filepath
                self.current_filename = os.path.basename(filepath)
                self.duration = current_time
                self.bpm = nominal
                self.nominal_bpm = nominal
                self.expressive_tempo = expressive
                self.main_time_signature = main_sig
                self.time_signature = main_sig
                self.events = events
                self.beat_map = beat_map
                self.beat_times = beat_times
                self.position = 0.0
                self.state = "idle"

            return True
        except Exception as e:
            print(f"[MidiPlayer] Error loading file {filepath}: {e}")
            return False

    def set_meter(self, numerator: Optional[int] = None, denominator: Optional[int] = None,
                  multiplier: Optional[float] = None, offset_beats: Optional[float] = None,
                  bar_offset: Optional[int] = None, pickup_bar_zero: Optional[bool] = None,
                  reset: bool = False) -> bool:
        """Overrides the meter, the beat sub-division, or the position of the barlines.

        offset_beats slides the whole grid, which is the only way to get a usable
        bar count out of a recorded performance whose barlines do not begin at
        tick 0. bar_offset renumbers bar 1 so the display matches a printed score.
        """
        with self.lock:
            if reset:
                # Resets the per-file grid, not the numbering convention: that is
                # a standing preference and survives loading another piece.
                self.custom_time_sig = None
                self.meter_multiplier = 1.0
                self.grid_offset_beats = 0.0
                self.bar_number_offset = 0
                self.time_signature = self.main_time_signature
            if numerator is not None and denominator is not None:
                self.time_signature = (max(1, int(numerator)), max(1, int(denominator)))
                self.custom_time_sig = self.time_signature
            if multiplier is not None:
                self.meter_multiplier = max(0.25, min(4.0, float(multiplier)))
            if offset_beats is not None:
                self.grid_offset_beats = float(offset_beats)
            if bar_offset is not None:
                self.bar_number_offset = int(bar_offset)
            if pickup_bar_zero is not None:
                self.pickup_bar_zero = bool(pickup_bar_zero)

            if self._mid_file_obj:
                self.beat_map, self.beat_times = self._build_beat_map(
                    self._mid_file_obj,
                    custom_num=self.time_signature[0] if self.custom_time_sig else None,
                    custom_den=self.time_signature[1] if self.custom_time_sig else None,
                    multiplier=self.meter_multiplier,
                    grid_offset_beats=self.grid_offset_beats,
                    bar_number_offset=self.bar_number_offset,
                    pickup_bar_zero=self.pickup_bar_zero
                )
                self.nominal_bpm = self._nominal_bpm(self.beat_map)
                self.expressive_tempo = self._tempo_is_expressive(self._mid_file_obj,
                                                                  self.beat_map)
                if not self.custom_time_sig:
                    self.main_time_signature = self._main_time_signature(self.beat_map)
                    self.time_signature = self.main_time_signature
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

    def get_bar_beat(self, pos: Optional[float] = None) -> Dict[str, Any]:
        """Musical position at a given time in original song seconds.

        Returns bar, beat, how far into the beat we are, the meter in force and the
        tempo of the current bar. beat_fraction drives the visual pulse, so it is
        measured against this beat's own duration - under a ritardando each beat is
        longer than the last and a fixed BPM would run ahead of the music.
        """
        if pos is None:
            pos = self.position

        if not self.beat_map or not self.beat_times:
            num, den = self.time_signature
            beats_per_bar = max(1, num)
            sec_per_beat = 60.0 / max(10.0, self.bpm)
            total_beats = pos / sec_per_beat
            beat = int(math.floor(total_beats % beats_per_bar)) + 1
            return {
                'bar': int(math.floor(total_beats / beats_per_bar)) + 1,
                'beat': beat,
                'beat_fraction': round(total_beats % 1.0, 3),
                'beats_per_bar': beats_per_bar,
                'bpm': self.bpm,
                'time_sig': f'{num}/{den}',
                'time_sig_num': num,
                'time_sig_den': den,
                'accent': beat == 1,
                'downbeat': beat == 1,
            }

        idx = bisect.bisect_right(self.beat_times, pos) - 1
        # Before the first beat we sit on beat one; past the last we hold the final
        # beat rather than inventing bars that the piece never had.
        if idx < 0:
            b, fraction = self.beat_map[0], 0.0
        elif idx >= len(self.beat_map) - 1:
            b = self.beat_map[-1]
            fraction = min(1.0, max(0.0, (pos - b['time']) / max(0.001, b['duration'])))
        else:
            b = self.beat_map[idx]
            fraction = min(1.0, max(0.0, (pos - b['time']) / max(0.001, b['duration'])))

        return {
            'bar': b['bar'],
            'beat': b['beat'],
            'beat_fraction': round(fraction, 3),
            'beats_per_bar': b['beats_per_bar'],
            'bpm': b['bpm'],
            'time_sig': b['time_sig'],
            'time_sig_num': b['time_sig_num'],
            'time_sig_den': b['time_sig_den'],
            'accent': b['accent'],
            'downbeat': b['downbeat'],
        }

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
            mus = self.get_bar_beat(self.position)
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
                "bar": mus['bar'],
                "beat": mus['beat'],
                "beat_fraction": mus['beat_fraction'],
                "beats_per_bar": mus['beats_per_bar'],
                "time_sig_num": mus['time_sig_num'],
                "time_sig_den": mus['time_sig_den'],
                "accent": mus['accent'],
                "downbeat": mus['downbeat'],
                "muted_channels": [ch + 1 for ch in sorted(self.muted_channels)],
                "channel_volumes": {ch + 1: int(round(self.channel_volumes.get(ch, 1.0) * 100)) for ch in range(10)},
                "port": self.target_port_name,
                "available_ports": available,
                "allow_program_change": self.is_program_change_allowed_for_port(self.target_port_name),
                "port_program_changes": {p: self.is_program_change_allowed_for_port(p) for p in available},
                "bpm": mus['bpm'],
                "nominal_bpm": self.nominal_bpm,
                "expressive_tempo": self.expressive_tempo,
                "time_signature": mus['time_sig'],
                "meter_multiplier": self.meter_multiplier,
                "custom_meter": self.custom_time_sig is not None,
                "grid_offset_beats": round(self.grid_offset_beats, 3),
                "bar_number_offset": self.bar_number_offset,
                "pickup_bar_zero": self.pickup_bar_zero,
                "has_pickup": bool(self.beat_map and self.beat_map[0]['bar'] <= 0),
                "total_bars": (self.beat_map[-1]['bar'] if self.beat_map else 0)
            }
            if include_beat_map:
                res["beat_map"] = self.beat_map
            return res

    def _first_full_bar_unlocked(self) -> Optional[Dict[str, Any]]:
        """First beat of the first complete measure, skipping any pickup bar."""
        for b in self.beat_map:
            if b['bar'] >= 1 and b['beat'] == 1:
                return b
        return self.beat_map[0] if self.beat_map else None

    def count_in_meter_unlocked(self) -> Tuple[int, int]:
        """Meter to count in - the first full measure, never a pickup."""
        b = self._first_full_bar_unlocked()
        if b:
            return (max(1, b['beats_per_bar']), max(1, b['time_sig_den']))
        return self.main_time_signature

    def count_in_beat_duration_unlocked(self) -> float:
        """One count-in click in seconds, taken from the bar the music starts in.

        This follows the click rate, not the quarter-note tempo: counting a 6/8 bar
        in means six eighths, not six quarters.
        """
        b = self._first_full_bar_unlocked()
        if b and b.get('click_bpm'):
            return 60.0 / max(20.0, float(b['click_bpm']))
        return 60.0 / max(20.0, self.bpm)

    def _play_count_in(self, port) -> bool:
        """Clicks the player in before the piece starts.

        The count-in has to use the meter and tempo the music actually starts in,
        not whatever happens to sit at tick 0: a file that opens with a one-beat
        pickup measure would otherwise give a single click, and a performance file
        whose first beat is an out-of-tempo rubato would count in at the wrong speed.
        """
        if self.count_in_bars <= 0:
            return True

        with self.lock:
            beats_per_bar, _den = self.count_in_meter_unlocked()
            beat_duration_src = self.count_in_beat_duration_unlocked()
            accents = self._strong_beats(beats_per_bar, _den)

        total_beats = self.count_in_bars * beats_per_bar
        base_beat_duration = beat_duration_src

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
                is_accent = ((beat % beats_per_bar) + 1) in accents
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
