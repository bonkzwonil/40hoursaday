#!/usr/bin/env python3
"""
Bar & beat verification tool for the 40hoursaday practice partner.

This drives the very same timeline code the player uses (MidiPlayer._build_beat_map),
so whatever this prints is what the app will count. A second, look-alike
implementation living in the test would only prove that the test agrees with itself.

Two modes:

  play    plays the file and prints every bar as it starts, so you can hear whether
          the count lands with the music.

  check   no MIDI port needed. Scores the timeline against the file itself:
            * timing      - do the beat times match mido's own playback clock?
            * downbeats   - do the barlines land on notes the piece actually plays?
            * phantoms    - does the grid invent bars after the music stops?
            * numbering   - are bar numbers contiguous, and beats 1..n per bar?

Usage:
    ./test_bar_player.py check  <file.mid> [more.mid ...]
    ./test_bar_player.py check  --dir ~/midi
    ./test_bar_player.py play   <file.mid> [-p PORT] [-s SPEED] [-m 3/4] [--mult 1.0]
                                [--offset BEATS] [--bar-offset N]
"""

import argparse
import bisect
import glob
import os
import sys
import time

import mido

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from player import MidiPlayer  # noqa: E402


# ----------------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------------

def build_map(path, num=None, den=None, mult=1.0, offset=0.0, bar_offset=0):
    mid = mido.MidiFile(path)
    beat_map, beat_times = MidiPlayer._build_beat_map(
        mid, custom_num=num, custom_den=den, multiplier=mult,
        grid_offset_beats=offset, bar_number_offset=bar_offset)
    return mid, beat_map, beat_times


def playback_clock(mid):
    """Tick -> seconds exactly as mido plays the file. This is the reference."""
    tpb = mid.ticks_per_beat or 480
    tempo, secs, tick = 500000, 0.0, 0
    marks = [(0, 0.0, 500000)]
    for msg in mido.merge_tracks(mid.tracks):
        tick += msg.time
        secs += mido.tick2second(msg.time, tpb, tempo)
        if msg.type == 'set_tempo':
            tempo = msg.tempo
            marks.append((tick, secs, tempo))
    ticks = [m[0] for m in marks]

    def at(t):
        i = max(0, bisect.bisect_right(ticks, t) - 1)
        start, base, tp = marks[i]
        return base + mido.tick2second(t - start, tpb, tp)

    return at


def note_onsets(mid):
    """Every note attack in seconds, on mido's own clock."""
    out, t = [], 0.0
    for msg in mid:
        t += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            out.append(round(t, 4))
    return sorted(set(out))


def last_sounding_second(mid):
    """When the last note stops sounding (ignores trailing markers / controllers)."""
    t, last = 0.0, 0.0
    for msg in mid:
        t += msg.time
        if msg.type in ('note_on', 'note_off'):
            last = t
    return last


# ----------------------------------------------------------------------------
# grid confidence
# ----------------------------------------------------------------------------

def hit_rate(grid, onsets, tol):
    """Share of grid points that have a note attack within tol seconds."""
    if not onsets or not grid:
        return 0.0
    n = 0
    for g in grid:
        i = bisect.bisect_left(onsets, g)
        for j in (i - 1, i):
            if 0 <= j < len(onsets) and abs(onsets[j] - g) <= tol:
                n += 1
                break
    return 100.0 * n / len(grid)


def grid_tolerance(beat_map):
    """Scale the tolerance to the beat: 30 ms is loose at 200 BPM and tight at 40."""
    beat = beat_map[len(beat_map) // 2]['duration'] if beat_map else 0.5
    return max(0.020, min(0.060, 0.08 * beat))


ALT_METERS = [(2, 4), (3, 4), (4, 4), (5, 4), (6, 8), (3, 8), (12, 8)]


def suggest_grid(path, mid, beat_map, onsets, tol, meters=None, steps=4):
    """Sweeps meters and barline offsets, looking for a grid that fits better.

    A low downbeat score on its own means nothing - a syncopated tune can leave
    most of its downbeats empty on purpose. It only matters when some *other*
    grid explains the notes clearly better, which is what points at a wrong meter
    in the header or barlines that do not start at tick 0.
    """
    own_meter = (beat_map[0]['time_sig_num'], beat_map[0]['time_sig_den'])
    own = hit_rate([b['time'] for b in beat_map if b['downbeat']], onsets, tol)
    results = []
    for num, den in (meters or ([own_meter] + [m for m in ALT_METERS if m != own_meter])):
        for step in range(num * steps):
            off = step / float(steps)
            try:
                bm, _ = MidiPlayer._build_beat_map(mid, custom_num=num, custom_den=den,
                                                   grid_offset_beats=off)
            except Exception:
                continue
            if not bm:
                continue
            score = hit_rate([b['time'] for b in bm if b['downbeat']], onsets, tol)
            results.append((score, num, den, off))
    results.sort(reverse=True)
    return own, own_meter, results


# ----------------------------------------------------------------------------
# check
# ----------------------------------------------------------------------------

def check_file(path, tolerance=None, verbose=False, deep=False):
    try:
        mid, beat_map, _ = build_map(path)
    except Exception as exc:
        print(f"  ERROR  {os.path.basename(path)}: {exc}")
        return None
    if not beat_map:
        print(f"  EMPTY  {os.path.basename(path)}: no beats")
        return None

    clock = playback_clock(mid)
    onsets = note_onsets(mid)
    music_end = last_sounding_second(mid)

    # 1. timing: the beat map must agree with the playback clock tick for tick
    timing_err = max(abs(b['time'] - clock(b['tick'])) for b in beat_map)

    # 2. downbeats: barlines should coincide with notes the piece actually plays
    tol = tolerance if tolerance is not None else grid_tolerance(beat_map)
    down_pct = hit_rate([b['time'] for b in beat_map if b['downbeat']], onsets, tol)
    beat_pct = hit_rate([b['time'] for b in beat_map], onsets, tol)

    # 3. phantoms: bars starting after the last note has stopped sounding
    phantoms = sum(1 for b in beat_map if b['downbeat'] and b['time'] > music_end + 0.05)

    # 4. numbering: contiguous bars, beats running 1..n inside each bar
    problems = []
    bars = [b['bar'] for b in beat_map if b['downbeat']]
    for a, b in zip(bars, bars[1:]):
        if b != a + 1:
            problems.append(f"bar {a} -> {b}")
    for prev, cur in zip(beat_map, beat_map[1:]):
        if cur['bar'] == prev['bar'] and cur['beat'] != prev['beat'] + 1:
            problems.append(f"beat {prev['bar']}:{prev['beat']} -> {cur['bar']}:{cur['beat']}")
        elif cur['bar'] != prev['bar'] and cur['beat'] != 1:
            problems.append(f"bar change into beat {cur['bar']}:{cur['beat']}")
    for b in beat_map:
        if not 1 <= b['beat'] <= b['beats_per_bar']:
            problems.append(f"beat {b['beat']} outside 1..{b['beats_per_bar']}")
            break
    # times must never go backwards
    for prev, cur in zip(beat_map, beat_map[1:]):
        if cur['time'] < prev['time']:
            problems.append(f"time goes backwards at bar {cur['bar']}")
            break

    # 5. is some other grid a clearly better fit? A low downbeat score by itself
    #    proves nothing - syncopated music leaves downbeats empty on purpose. It
    #    only matters if shifting or re-metering the grid explains the notes much
    #    better, which is the signature of a wrong header or offset barlines.
    better = None
    if deep and onsets:
        _own, _own_meter, ranked = suggest_grid(path, mid, beat_map, onsets, tol)
        if ranked and ranked[0][0] > down_pct * 1.25 + 8.0:
            better = ranked[0]

    ok = timing_err <= 0.001 and phantoms == 0 and not problems
    first, last = beat_map[0], beat_map[-1]
    pickup = " pickup" if first['bar'] == 0 else ""
    flag = "PASS" if ok else "FAIL"

    print(f"  [{flag}] {os.path.basename(path)[:52]}")
    print(f"         meter {first['time_sig']}{pickup}  bars {first['bar']}..{last['bar']}  "
          f"beats {len(beat_map)}  tempo {MidiPlayer._nominal_bpm(beat_map)} BPM")
    print(f"         timing max err {timing_err*1000:.3f} ms   downbeats on a note "
          f"{down_pct:.1f}%   all beats {beat_pct:.1f}%   phantom bars {phantoms}")
    if problems:
        print(f"         numbering: {len(problems)} problem(s): {problems[:3]}")
    if better:
        score, num, den, off = better
        print(f"         grid hint: {num}/{den} offset {off:g} beats scores {score:.1f}% "
              f"(this file's own grid: {down_pct:.1f}%)")
    if verbose:
        metres = []
        for b in beat_map:
            if not metres or metres[-1][1] != b['time_sig']:
                metres.append((b['bar'], b['time_sig']))
        print(f"         meter changes: {metres[:12]}")

    return {'ok': ok, 'timing': timing_err, 'down': down_pct, 'better': better,
            'phantoms': phantoms, 'problems': len(problems)}


def run_check(paths, verbose=False, deep=False):
    print("=" * 78)
    print("Bar & beat timeline check")
    print("=" * 78)
    results = [r for r in (check_file(p, verbose=verbose, deep=deep) for p in paths) if r]
    if not results:
        print("\nNothing to check.")
        return 1
    passed = sum(1 for r in results if r['ok'])
    worst = max(r['timing'] for r in results)
    hinted = [r for r in results if r.get('better')]
    print("-" * 78)
    print(f"{passed}/{len(results)} files pass.  Worst timing error: {worst*1000:.3f} ms")
    if deep and hinted:
        print(f"{len(hinted)} file(s) would fit a different grid noticeably better - see "
              f"the grid hints above, or run 'suggest <file>' for the full ranking.")
    elif not deep:
        print("Run with --deep to also test whether a different meter or barline "
              "offset would fit the notes better.")
    return 0 if passed == len(results) else 1


# ----------------------------------------------------------------------------
# suggest
# ----------------------------------------------------------------------------

def run_suggest(args):
    mid, beat_map, _ = build_map(args.file)
    if not beat_map:
        print("No beats found in this file.")
        return 1
    onsets = note_onsets(mid)
    tol = grid_tolerance(beat_map)
    own, own_meter, ranked = suggest_grid(args.file, mid, beat_map, onsets, tol)

    print("=" * 78)
    print(f"  {os.path.basename(args.file)}")
    print(f"  header says {own_meter[0]}/{own_meter[1]}, and that grid puts a note on "
          f"{own:.1f}% of its downbeats")
    print(f"  (tolerance {tol*1000:.0f} ms, {len(onsets)} distinct note attacks)")
    print("=" * 78)
    print(f"  {'score':>7}  {'meter':>7}  {'offset':>8}  suggestion")
    for score, num, den, off in ranked[:10]:
        cmd = f"-m {num}/{den}" + (f" --offset {off:g}" if off else "")
        print(f"  {score:6.1f}%  {num:>3}/{den:<3}  {off:8.2f}  play {cmd}")

    best = ranked[0][0] if ranked else 0.0
    print("-" * 78)
    if best < 40.0:
        print("  No grid fits this file well. It is almost certainly an unquantised")
        print("  recording whose rubato was never written into the tempo map, so the")
        print("  barlines cannot be recovered from the file - pick the meter you know")
        print("  is right and expect the count to drift against the performance.")
    elif best > own * 1.25 + 8.0:
        print("  The header's meter looks wrong. Try the top suggestion above; the same")
        print("  values go into the app's meter control.")
    else:
        print("  The file's own grid is the best available - a lower score here just")
        print("  means the music is syncopated, not that the bar count is wrong.")
    return 0


# ----------------------------------------------------------------------------
# play
# ----------------------------------------------------------------------------

def pick_port(preferred):
    available = mido.get_output_names()
    if preferred:
        for p in available:
            if preferred.lower() in p.lower():
                return p
    for want in ("fluid", "pianoteq", "timidity", "through"):
        for p in available:
            if want in p.lower():
                return p
    return available[0] if available else None


def run_play(args):
    num = den = None
    if args.meter:
        num, den = (int(x) for x in args.meter.split('/'))

    mid, beat_map, _ = build_map(args.file, num, den, args.mult,
                                 args.offset, args.bar_offset)
    if not beat_map:
        print("No beats found in this file.")
        return 1

    bars = [b for b in beat_map if b['downbeat']]
    port_name = pick_port(args.port)
    print("=" * 78)
    print(f"  {os.path.basename(args.file)}")
    print(f"  meter {beat_map[0]['time_sig']}   tempo {MidiPlayer._nominal_bpm(beat_map)} BPM"
          f"   bars {bars[0]['bar']}..{bars[-1]['bar']}   speed {args.speed*100:.0f}%")
    if args.mult != 1.0 or args.offset or args.bar_offset:
        print(f"  sub-division x{args.mult}   grid offset {args.offset} beats"
              f"   bar numbering {args.bar_offset:+d}")
    print(f"  MIDI out: {port_name or 'none (silent dry run)'}")
    print("=" * 78)

    events, t = [], 0.0
    for msg in mid:
        t += msg.time
        if not msg.is_meta:
            events.append((t, msg.copy()))

    out = mido.open_output(port_name) if port_name else None
    start = time.time()
    bar_i = ev_i = 0
    try:
        while ev_i < len(events) or bar_i < len(bars):
            now = (time.time() - start) * args.speed

            while bar_i < len(bars) and bars[bar_i]['time'] <= now:
                b = bars[bar_i]
                label = "Auftakt" if b['bar'] == 0 else f"bar {b['bar']:>4}"
                print(f"  {label}  {b['time']:7.2f}s   {b['bpm']:5.1f} BPM   {b['time_sig']}")
                bar_i += 1

            while ev_i < len(events) and events[ev_i][0] <= now:
                if out:
                    out.send(events[ev_i][1])
                ev_i += 1

            time.sleep(0.001)
        print("\n  Done.")
    except KeyboardInterrupt:
        print("\n  Stopped.")
    finally:
        if out:
            for ch in range(16):
                out.send(mido.Message('control_change', channel=ch, control=123, value=0))
                out.send(mido.Message('control_change', channel=ch, control=120, value=0))
            out.close()
    return 0


# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode")

    c = sub.add_parser("check", help="verify the bar/beat timeline (no MIDI port needed)")
    c.add_argument("files", nargs="*", help="MIDI files")
    c.add_argument("--dir", help="check every .mid in this directory")
    c.add_argument("-v", "--verbose", action="store_true", help="list meter changes")
    c.add_argument("--deep", action="store_true",
                   help="also test alternative meters and barline offsets (slower)")

    g = sub.add_parser("suggest", help="rank meters and barline offsets against the notes")
    g.add_argument("file")

    p = sub.add_parser("play", help="play the file and print each bar as it starts")
    p.add_argument("file")
    p.add_argument("-p", "--port", default=None, help="MIDI output port substring")
    p.add_argument("-s", "--speed", type=float, default=1.0, help="playback speed")
    p.add_argument("-m", "--meter", default=None, help="override the meter, e.g. 3/4")
    p.add_argument("--mult", type=float, default=1.0, help="beat sub-division multiplier")
    p.add_argument("--offset", type=float, default=0.0,
                   help="shift the barlines by this many beats")
    p.add_argument("--bar-offset", type=int, default=0,
                   help="renumber bar 1 to match a printed score")

    args = ap.parse_args()
    if args.mode == "play":
        return run_play(args)
    if args.mode == "suggest":
        return run_suggest(args)
    if args.mode == "check":
        paths = list(args.files)
        if args.dir:
            for ext in ("*.mid", "*.MID", "*.midi"):
                paths += sorted(glob.glob(os.path.join(os.path.expanduser(args.dir), ext)))
        if not paths:
            ap.error("check needs at least one file or --dir")
        return run_check(paths, verbose=args.verbose, deep=args.deep)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
