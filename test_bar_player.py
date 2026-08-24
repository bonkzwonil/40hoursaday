#!/usr/bin/env python3
"""
Simple Real-time MIDI Bar Counter Test Script.
Plays a MIDI file and prints "n BAR" at the exact moment each measure begins.

Usage:
    python3 test_bar_player.py <path_to_midi> [port_name] [speed]
"""

import sys
import time
import os
import mido

def play_midi_with_bar_counter(filepath: str, port_name: str = "Midi Through", speed: float = 1.0, 
                               custom_num: int = None, custom_den: int = None, multiplier: float = 1.0):
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    mid = mido.MidiFile(filepath)
    tpb = mid.ticks_per_beat or 480

    # 1. Collect all tempo and time signature events with absolute ticks
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

    # Snap setup events near tick 0 (within first 48 ticks) to tick 0
    threshold = max(24, tpb // 4)
    if tempo_events:
        if 0 < tempo_events[0][0] <= threshold:
            tempo_events[0] = (0, tempo_events[0][1])
        elif tempo_events[0][0] > threshold:
            tempo_events.insert(0, (0, 500000))
    else:
        tempo_events.insert(0, (0, 500000))

    if time_sig_events:
        if 0 < time_sig_events[0][0] <= threshold:
            time_sig_events[0] = (0, time_sig_events[0][1], time_sig_events[0][2])
        elif time_sig_events[0][0] > threshold:
            time_sig_events.insert(0, (0, 4, 4))
    else:
        time_sig_events.insert(0, (0, 4, 4))

    # Deduplicate keeping last at same tick
    def dedup(events):
        d = {}
        for ev in events:
            d[ev[0]] = ev[1:]
        return sorted([(k, *v) for k, v in d.items()], key=lambda x: x[0])

    tempo_events = dedup(tempo_events)
    time_sig_events = dedup(time_sig_events)

    # 2. Build tempo segments for tick -> seconds conversion
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

    # 3. Build Measure & Bar Boundaries:
    # A bar starts at tick T_bar and ends after Num * (TPB * 4/Den) ticks
    bars = []
    current_bar_num = 1

    for i in range(len(time_sig_events)):
        start_tick, num, den = time_sig_events[i]
        if custom_num and custom_den:
            num, den = custom_num, custom_den
        next_tick = time_sig_events[i+1][0] if i+1 < len(time_sig_events) else max_tick + tpb * 10
        ticks_per_bar = max(1, int(round(num * tpb * (4.0 / den) * multiplier)))

        t = start_tick
        while t < next_tick:
            t_sec = tick_to_time(t)
            next_t_sec = tick_to_time(t + ticks_per_bar)
            tempo_us = get_tempo_at_tick(t)
            bpm = round(mido.tempo2bpm(tempo_us) / max(0.1, multiplier), 1)
            bars.append({
                'bar': current_bar_num,
                'time': t_sec,
                'duration': next_t_sec - t_sec,
                'bpm': bpm,
                'meter': f"{num}/{den}",
                'tick': t
            })
            current_bar_num += 1
            t += ticks_per_bar

    print("=" * 70)
    print(f"🎵 Playing: {os.path.basename(filepath)}")
    print(f"   Length: {mid.length:.2f}s | Meter: {bars[0]['meter'] if bars else '4/4'} | Initial BPM: {bars[0]['bpm'] if bars else round(mido.tempo2bpm(tempo_events[0][1]), 1)}")
    if multiplier != 1.0:
        print(f"   Multiplier: {multiplier:.1f}x")
    print(f"   Total Bars: {len(bars)} | Speed: {speed*100:.0f}%")
    print("=" * 70)

    # Open MIDI port (auto-detect FluidSynth / Pianoteq / specified port)
    available = mido.get_output_names()
    target_port = None
    if port_name and port_name != "Midi Through":
        for p in available:
            if port_name.lower() in p.lower():
                target_port = p
                break
    if not target_port:
        for p in available:
            if "fluid" in p.lower() or "pianoteq" in p.lower():
                target_port = p
                break
    if not target_port:
        for p in available:
            if "through" in p.lower():
                target_port = p
                break
    if not target_port and available:
        target_port = available[0]

    out_port = mido.open_output(target_port) if target_port else None
    print(f"Connected to MIDI Port: {target_port or 'None (dry run)'}\n")

    # Flatten note events with absolute seconds
    events = []
    t_acc = 0.0
    for msg in mid:
        t_acc += msg.time
        if not msg.is_meta:
            events.append((t_acc, msg.copy()))

    # Real-time Playback Loop with Bar Triggering
    start_wall = time.time()
    next_bar_idx = 0
    event_idx = 0

    try:
        while event_idx < len(events) or next_bar_idx < len(bars):
            now_song_time = (time.time() - start_wall) * speed

            # 1. Trigger Bar Change
            while next_bar_idx < len(bars) and bars[next_bar_idx]['time'] <= now_song_time:
                b = bars[next_bar_idx]
                print(f"👉 {b['bar']:3d} BAR  |  time: {b['time']:6.2f}s  |  duration: {b['duration']:5.2f}s  |  tempo: {b['bpm']:5.1f} BPM  |  meter: {b['meter']}")
                next_bar_idx += 1

            # 2. Send ready MIDI events
            while event_idx < len(events) and events[event_idx][0] <= now_song_time:
                ev_time, msg = events[event_idx]
                if out_port:
                    out_port.send(msg)
                event_idx += 1

            # Sleep tiny interval to avoid busy loop
            time.sleep(0.002)

        print("\n✅ Playback complete!")
    except KeyboardInterrupt:
        print("\n⏹️ Stopped by user.")
    finally:
        if out_port:
            for ch in range(16):
                out_port.send(mido.Message('control_change', channel=ch, control=123, value=0))
                out_port.send(mido.Message('control_change', channel=ch, control=120, value=0))
            out_port.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test MIDI Player with Real-Time Bar Counter")
    parser.add_argument("file", help="Path to MIDI file")
    parser.add_argument("extra_args", nargs="*", help="Optional positional arguments [port] [speed]")
    parser.add_argument("-p", "--port", default=None, help="MIDI output port (default: auto-detects FluidSynth / Midi Through)")
    parser.add_argument("-s", "--speed", type=float, default=None, help="Playback speed multiplier (e.g. 1.0, 0.8)")
    parser.add_argument("-m", "--meter", default=None, help="Override time signature (e.g. '3/4', '4/4', '6/8', '2/4')")
    parser.add_argument("--mult", type=float, default=1.0, help="Beat division multiplier (e.g. 2.0 for 2x quarter duration, 0.5 for cut time)")
    args = parser.parse_args()

    port = args.port
    speed = args.speed if args.speed is not None else 1.0

    if args.extra_args:
        if len(args.extra_args) >= 1 and not port:
            port = args.extra_args[0]
        if len(args.extra_args) >= 2 and args.speed is None:
            try:
                speed = float(args.extra_args[1])
            except ValueError:
                pass

    if not port:
        port = "Midi Through"

    custom_num = None
    custom_den = None
    if args.meter:
        parts = args.meter.strip().split('/')
        if len(parts) == 2:
            custom_num = int(parts[0])
            custom_den = int(parts[1])

    play_midi_with_bar_counter(
        args.file,
        port_name=port,
        speed=speed,
        custom_num=custom_num,
        custom_den=custom_den,
        multiplier=args.mult
    )

if __name__ == "__main__":
    main()
