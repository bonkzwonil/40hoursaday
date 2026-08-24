#!/usr/bin/env python3
"""
Repair the bar structure of a rendered performance MIDI using its MusicXML score.

Expressive renderers such as VirtuosoNet read a score, render a performance, and
then write a MIDI file that throws the score away: every output carries the same
hardcoded 4/4 header, a single 120 BPM tempo event and no tempo map at all, even
when the score is in 6/8. The performed note times are fine - they simply live in
the tick axis as raw elapsed time - but nothing downstream can find a barline,
because the file no longer says where the bars are.

This puts the structure back without touching how the music sounds:

  * the score's time signatures are written at their real positions
  * the notes are placed at their score positions in the tick axis
  * a tempo map is built so that every one of those ticks plays back at the
    moment the performer actually played it

So playback is sample-identical to the input, while bar 34 beat 3 is now a
question the file can answer. The result is an ordinary MIDI file - the practice
app, a DAW, or anything else reads the bars correctly with no special support.

Usage:
    ./score_repair.py <score.mxl|.musicxml|.xml> <performance.mid> [-o out.mid]
    ./score_repair.py score.mxl perf.mid --report     # analyse only, write nothing
    ./score_repair.py score.mxl perf.mid --no-pad     # start at the first played bar
"""

import argparse
import bisect
import difflib
import glob
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

import mido

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from player import MidiPlayer  # noqa: E402

STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
MAX_TEMPO_US = 0xFFFFFF          # the tempo meta event is three bytes
MIN_TEMPO_US = 1


# ---------------------------------------------------------------------------
# MusicXML
# ---------------------------------------------------------------------------

def read_score(path):
    """Score note onsets, barlines and meters, all in divisions from the start."""
    if path.lower().endswith('.mxl'):
        with zipfile.ZipFile(path) as z:
            inner = [n for n in z.namelist()
                     if n.lower().endswith(('.xml', '.musicxml'))
                     and not n.startswith('META-INF')]
            root = ET.fromstring(z.read(inner[0]))
    else:
        root = ET.parse(path).getroot()

    parts = root.findall('.//part')
    if not parts:
        raise SystemExit(f"no <part> found in {path}")

    divisions = 1
    notes = []
    barlines = []
    meters = []
    end = 0

    for part in parts:
        pos = 0
        prev_onset = 0
        for m_index, measure in enumerate(part.findall('measure')):
            if len(barlines) <= m_index:
                barlines.append(pos)
            measure_start = pos
            for el in measure:
                if el.tag == 'attributes':
                    d = el.find('divisions')
                    if d is not None:
                        divisions = int(d.text)
                    t = el.find('time')
                    if t is not None and t.find('beats') is not None:
                        meters.append((measure_start,
                                       int(t.find('beats').text),
                                       int(t.find('beat-type').text)))
                elif el.tag == 'note':
                    dur_el = el.find('duration')
                    dur = int(dur_el.text) if dur_el is not None else 0
                    is_chord = el.find('chord') is not None
                    is_grace = el.find('grace') is not None
                    pitch = el.find('pitch')
                    # A chord member sounds with the note before it, not after.
                    onset = prev_onset if is_chord else pos
                    if pitch is not None and not any(
                            t.get('type') == 'stop' for t in el.findall('tie')):
                        semis = (int(pitch.find('octave').text) + 1) * 12 \
                            + STEP[pitch.find('step').text]
                        alter = pitch.find('alter')
                        if alter is not None:
                            semis += int(float(alter.text))
                        notes.append((onset, semis))
                    if not is_chord and not is_grace:
                        prev_onset = pos
                        pos += dur
                elif el.tag == 'backup':
                    pos -= int(el.find('duration').text)
                elif el.tag == 'forward':
                    pos += int(el.find('duration').text)
            pos = max(pos, measure_start)
        end = max(end, pos)

    barlines.append(end)
    notes.sort()
    meters = sorted(set(meters)) or [(0, 4, 4)]
    return {'notes': notes, 'barlines': barlines, 'divisions': divisions,
            'meters': meters, 'end': end}


# ---------------------------------------------------------------------------
# Performance MIDI
# ---------------------------------------------------------------------------

def read_performance(path):
    """Every event with an absolute time in seconds, plus the note onsets."""
    mid = mido.MidiFile(path)
    tpb = mid.ticks_per_beat or 480
    clock, _ = MidiPlayer._make_tick_clock(
        MidiPlayer._extract_timeline(mid)['tempos'], tpb)

    events = []      # (seconds, order, message) for every non-meta message
    onsets = []      # (seconds, pitch)
    order = 0
    for track in mid.tracks:
        at = 0
        for msg in track:
            at += msg.time
            if msg.is_meta:
                continue
            secs = clock(at)
            events.append((secs, order, msg.copy()))
            order += 1
            if msg.type == 'note_on' and msg.velocity > 0:
                onsets.append((secs, msg.note))
    events.sort(key=lambda e: (e[0], e[1]))
    onsets.sort()
    return mid, events, chord_order(onsets)


def chord_order(onsets, window=0.05):
    """Sort simultaneities by pitch instead of by the millisecond they sounded.

    A rendered chord is not truly simultaneous - a performance spreads its notes
    over a few dozen milliseconds, and a rolled chord over much more. Sorting the
    performance purely by time therefore lists a chord in *performed* order while
    the score lists it in pitch order, and the two sequences disagree inside every
    chord. On a dense piano part that wrecks the alignment: matching fell to 32%
    on a five-voice score with 859 chords, against 97% on a near-monophonic one.
    Grouping and re-sorting by pitch makes the two agree.
    """
    out = []
    i = 0
    while i < len(onsets):
        j = i
        while j + 1 < len(onsets) and onsets[j + 1][0] - onsets[i][0] <= window:
            j += 1
        out.extend(sorted(onsets[i:j + 1], key=lambda x: (x[1], x[0])))
        i = j + 1
    return out


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def align(score_notes, perf_onsets):
    """Monotonic (score divisions, performance seconds) anchors from the notes.

    Matching is on the pitch sequence alone. That is enough here because the
    performance is a rendering of this very score, so the two sequences differ
    only by ornaments, repeats and the odd dropped voice.
    """
    matcher = difflib.SequenceMatcher(a=[p for _, p in score_notes],
                                      b=[p for _, p in perf_onsets],
                                      autojunk=False)
    pairs = []
    matched = 0
    for block in matcher.get_matching_blocks():
        matched += block.size
        for k in range(block.size):
            pairs.append((score_notes[block.a + k][0], perf_onsets[block.b + k][0]))
    pairs.sort()

    mono = []
    for x, y in pairs:
        if not mono or (x > mono[-1][0] and y > mono[-1][1]):
            mono.append((x, y))
    return mono, matched


class Warp:
    """Piecewise-linear map between score divisions and performed seconds."""

    def __init__(self, anchors):
        self.xs = [a for a, _ in anchors]
        self.ys = [b for _, b in anchors]

    def _interp(self, src, dst, v):
        i = bisect.bisect_left(src, v)
        if len(src) < 2:
            return dst[0]
        if i <= 0:
            slope = (dst[1] - dst[0]) / max(1e-9, src[1] - src[0])
            return dst[0] + (v - src[0]) * slope
        if i >= len(src):
            slope = (dst[-1] - dst[-2]) / max(1e-9, src[-1] - src[-2])
            return dst[-1] + (v - src[-1]) * slope
        f = (v - src[i - 1]) / max(1e-9, src[i] - src[i - 1])
        return dst[i - 1] + f * (dst[i] - dst[i - 1])

    def to_seconds(self, pos):
        return self._interp(self.xs, self.ys, pos)

    def to_score(self, secs):
        return self._interp(self.ys, self.xs, secs)


# ---------------------------------------------------------------------------
# Rebuild
# ---------------------------------------------------------------------------

def build_repaired(score, perf_mid, events, anchors, tpb=480, pad_rests=True):
    """Writes a MIDI whose bars are the score's and whose timing is the performance's."""
    divisions = score['divisions']
    warp = Warp(anchors)

    def pos_to_tick(pos):
        return int(round(pos * tpb / divisions))

    # Which measures the alignment actually covers. These renderings drop leading
    # rests, so a part that enters in bar 19 has nothing before it to align.
    first_pos = anchors[0][0]
    bars = score['barlines']
    first_bar_idx = max(0, bisect.bisect_right(bars, first_pos) - 1)
    shift_pos = 0 if pad_rests else bars[first_bar_idx]

    def out_tick(pos):
        return max(0, pos_to_tick(pos - shift_pos))

    # --- tempo map: one segment per anchor, so every anchored note lands on the
    # --- exact instant it was performed and the barlines interpolate between.
    tempo_points = []
    for i in range(len(anchors) - 1):
        (p0, s0), (p1, s1) = anchors[i], anchors[i + 1]
        t0, t1 = out_tick(p0), out_tick(p1)
        d_ticks, d_secs = t1 - t0, s1 - s0
        if d_ticks <= 0 or d_secs <= 0:
            continue
        us_per_quarter = int(round(d_secs * 1_000_000.0 * tpb / d_ticks))
        us_per_quarter = max(MIN_TEMPO_US, min(MAX_TEMPO_US, us_per_quarter))
        if not tempo_points or tempo_points[-1][1] != us_per_quarter:
            tempo_points.append((t0, us_per_quarter))
    if not tempo_points or tempo_points[0][0] != 0:
        head = tempo_points[0][1] if tempo_points else 500000
        tempo_points.insert(0, (0, head))

    # The first anchor may sit inside its bar; hold the opening tempo back to 0
    # so the run-up to the first played note is not an accidental fermata.
    meta = [(t, mido.MetaMessage('set_tempo', tempo=v)) for t, v in tempo_points]
    for pos, num, den in score['meters']:
        if pos >= shift_pos or pos == 0:
            meta.append((out_tick(max(pos, shift_pos)),
                         mido.MetaMessage('time_signature', numerator=num,
                                          denominator=den)))
    meta.sort(key=lambda x: (x[0], x[1].type != 'time_signature'))

    # --- notes: performed time -> score position -> tick
    placed = []
    for secs, order, msg in events:
        pos = warp.to_score(secs)
        placed.append((out_tick(pos), order, msg))
    placed.sort(key=lambda x: (x[0], x[1]))

    out = mido.MidiFile(type=1, ticks_per_beat=tpb)
    meta_track = mido.MidiTrack()
    prev = 0
    for tick, m in meta:
        meta_track.append(m.copy(time=max(0, tick - prev)))
        prev = tick
    meta_track.append(mido.MetaMessage('end_of_track', time=0))
    out.tracks.append(meta_track)

    note_track = mido.MidiTrack()
    prev = 0
    for tick, _order, m in placed:
        note_track.append(m.copy(time=max(0, tick - prev)))
        prev = tick
    note_track.append(mido.MetaMessage('end_of_track', time=0))
    out.tracks.append(note_track)
    return out, first_bar_idx + 1, shift_pos


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(out_mid, original_onsets, score, first_bar):
    """Does the repaired file still sound the same, and can it now find its bars?"""
    _mid, _events, new_onsets = read_performance_obj(out_mid)

    # Timing fidelity is measured relative to the first note, not in absolute
    # time: padding the leading rests deliberately moves the whole performance
    # later, so what has to be preserved is every interval within it.
    # Compare on time alone, not on the chord-ordered sequence, so that a chord
    # re-sorted for matching is not mistaken for a timing change.
    a = sorted(t for t, _ in original_onsets)
    b = sorted(t for t, _ in new_onsets)
    n = min(len(a), len(b))
    worst = 0.0
    if n:
        for i in range(n):
            worst = max(worst, abs((a[i] - a[0]) - (b[i] - b[0])))

    beat_map, _ = MidiPlayer._build_beat_map(out_mid)
    downs = [b['time'] for b in beat_map if b['downbeat']]
    onset_times = sorted({round(t, 4) for t, _ in new_onsets})

    def hit(grid, tol=0.030):
        k = 0
        for g in grid:
            i = bisect.bisect_left(onset_times, g)
            for j in (i - 1, i):
                if 0 <= j < len(onset_times) and abs(onset_times[j] - g) <= tol:
                    k += 1
                    break
        return 100.0 * k / max(1, len(grid))

    return {'onset_error': worst, 'bars': len(downs), 'downbeat_pct': hit(downs),
            'meter': beat_map[0]['time_sig'] if beat_map else '?',
            'bpm': MidiPlayer._nominal_bpm(beat_map)}


def read_performance_obj(mid):
    tpb = mid.ticks_per_beat or 480
    clock, _ = MidiPlayer._make_tick_clock(
        MidiPlayer._extract_timeline(mid)['tempos'], tpb)
    events, onsets, order = [], [], 0
    for track in mid.tracks:
        at = 0
        for msg in track:
            at += msg.time
            if msg.is_meta:
                continue
            secs = clock(at)
            events.append((secs, order, msg))
            order += 1
            if msg.type == 'note_on' and msg.velocity > 0:
                onsets.append((secs, msg.note))
    events.sort(key=lambda e: (e[0], e[1]))
    onsets.sort()
    return mid, events, chord_order(onsets)


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

def find_scores(score_dir):
    out = {}
    for ext in ('*.mxl', '*.musicxml', '*.xml'):
        for path in sorted(glob.glob(os.path.join(score_dir, ext))):
            out.setdefault(os.path.splitext(os.path.basename(path))[0], path)
    return out


def find_performances(midi_dirs):
    """Group rendered performances by the score they came from.

    The renderer names its output Partituren_<score>_by_isgn_<style>.mid, so the
    score a file belongs to is recoverable from the name alone.
    """
    found = {}
    for d in midi_dirs:
        for path in sorted(glob.glob(os.path.join(d, '*.mid'))):
            name = os.path.basename(path)
            if not name.startswith('Partituren_') or '_by_isgn_' not in name:
                continue
            if name.endswith('.repaired.mid'):
                continue
            stem = name[len('Partituren_'):].split('_by_isgn_')[0]
            found.setdefault(stem, []).append(path)
    return found


def run_batch(args):
    scores = find_scores(args.score)
    if not scores:
        raise SystemExit(f"no MusicXML scores in {args.score}")
    perfs = find_performances(args.midi_dir or [])

    os.makedirs(args.out_dir, exist_ok=True)
    jobs = [(stem, scores[stem], p) for stem in sorted(scores)
            for p in perfs.get(stem, [])]
    if not jobs:
        raise SystemExit(
            f"no rendered performances found in {', '.join(args.midi_dir)}.\n"
            f"Point --midi-dir at the directory holding the "
            f"Partituren_<score>_by_isgn_<style>.mid files.")
    unmatched = [s for s in sorted(scores) if not perfs.get(s)]

    print("=" * 96)
    print(f"  {len(scores)} score(s) in {args.score}")
    print(f"  {sum(len(v) for v in perfs.values())} rendered performance(s) found, "
          f"{len(jobs)} of them matched to a score")
    print(f"  writing to {args.out_dir}")
    print("=" * 96)
    print(f"  {'meter':>6} {'bars':>5} {'align':>6} {'downbeats':>17} {'drift':>9}  file")
    print("  " + "-" * 92)

    ok = fail = 0
    for stem, score_path, perf_path in jobs:
        name = os.path.basename(perf_path)
        try:
            score = read_score(score_path)
            perf_mid, events, onsets = read_performance(perf_path)
            anchors, matched = align(score['notes'], onsets)
            if len(anchors) < 2:
                raise ValueError("scores share almost no notes with this rendering")

            before, _ = MidiPlayer._build_beat_map(perf_mid)
            onset_times = sorted({round(t, 4) for t, _ in onsets})
            b_pct = _hit([b['time'] for b in before if b['downbeat']], onset_times)

            out, first_bar, _ = build_repaired(score, perf_mid, events, anchors,
                                               tpb=args.tpb, pad_rests=not args.no_pad)
            v = verify(out, onsets, score, first_bar)

            # A repaired file is only worth having if it still plays back as it
            # did and its bars actually land on the music. Writing one that fails
            # either test would hand over a file that is quietly wrong, which is
            # worse than leaving the original alone.
            problems = []
            if v['onset_error'] > args.max_drift:
                problems.append(f"drifts {v['onset_error']*1000:.0f}ms")
            if v['downbeat_pct'] < args.min_downbeats:
                problems.append(f"only {v['downbeat_pct']:.0f}% of downbeats land on a note")
            if v['downbeat_pct'] < b_pct:
                problems.append("no better than the original")

            line = (f"  {v['meter']:>6} {v['bars']:>5} "
                    f"{100.0*matched/max(1,len(score['notes'])):>5.0f}% "
                    f"{b_pct:>6.1f}% -> {v['downbeat_pct']:>5.1f}% "
                    f"{v['onset_error']*1000:>7.1f}ms")
            if problems:
                print(f"{line}  SKIPPED  {name[:38]}")
                print(f"           {'; '.join(problems)}")
                fail += 1
                continue
            dest = os.path.join(args.out_dir, os.path.splitext(name)[0] + '.mid')
            if not args.report:
                out.save(dest)
            print(f"{line}           {name[:38]}")
            ok += 1
        except Exception as exc:
            print(f"  {'FAIL':>6} {str(exc)[:60]:<58}  {name[:44]}")
            fail += 1

    print("  " + "-" * 92)
    print(f"  {ok} repaired, {fail} skipped as not trustworthy"
          + ("  (--report: nothing written)" if args.report else ""))
    if unmatched:
        print(f"\n  {len(unmatched)} score(s) have no rendered performance to repair:")
        for u in unmatched:
            print(f"    {u[:70]}")
        print("  Nothing to fix for these - a score alone already knows its bars.")
        print("  Export them with MuseScore if you want a plain MIDI:")
        print(f'    mscore3 -o out.mid "{os.path.join(args.score, unmatched[0])}.mxl"')
    return 0 if fail == 0 else 1


def _hit(grid, onset_times, tol=0.030):
    k = 0
    for g in grid:
        i = bisect.bisect_left(onset_times, g)
        for j in (i - 1, i):
            if 0 <= j < len(onset_times) and abs(onset_times[j] - g) <= tol:
                k += 1
                break
    return 100.0 * k / max(1, len(grid))


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('score', help='MusicXML score, or a directory of them with --batch')
    ap.add_argument('performance', nargs='?', help='rendered performance MIDI')
    ap.add_argument('--batch', action='store_true',
                    help='treat `score` as a directory and repair every rendering '
                         'found in --midi-dir that belongs to a score in it')
    ap.add_argument('--midi-dir', action='append', default=None,
                    help='directory of rendered performances (repeatable, --batch only; '
                         'defaults to the score directory)')
    ap.add_argument('--out-dir', default=None, help='where to write repaired files (--batch)')
    ap.add_argument('--max-drift', type=float, default=0.015,
                    help='reject a repair that shifts playback by more than this (seconds)')
    ap.add_argument('--min-downbeats', type=float, default=60.0,
                    help='reject a repair whose downbeats land on a note less often than this %%')
    ap.add_argument('-o', '--out', default=None,
                    help='output file (default: <performance>.repaired.mid)')
    ap.add_argument('--report', action='store_true',
                    help='analyse and print only, write nothing')
    ap.add_argument('--no-pad', action='store_true',
                    help='start the file at the first played bar instead of at '
                         'score bar 1 (bar numbers then restart from 1)')
    ap.add_argument('--tpb', type=int, default=480, help='output resolution')
    args = ap.parse_args()

    if args.batch:
        if not args.midi_dir:
            # Scores and their renderings often sit together; otherwise say where.
            args.midi_dir = [args.score]
        if not args.out_dir:
            args.out_dir = os.path.join(args.score, 'repaired_midi')
        return run_batch(args)

    if not args.performance:
        ap.error("a performance MIDI is required (or use --batch)")

    score = read_score(args.score)
    perf_mid, events, onsets = read_performance(args.performance)
    anchors, matched = align(score['notes'], onsets)
    if len(anchors) < 2:
        raise SystemExit("could not align: the score and the performance share "
                         "almost no notes - is this the right score?")

    before, _ = MidiPlayer._build_beat_map(perf_mid)
    b_downs = [b['time'] for b in before if b['downbeat']]
    onset_times = sorted({round(t, 4) for t, _ in onsets})

    def hit(grid, tol=0.030):
        k = 0
        for g in grid:
            i = bisect.bisect_left(onset_times, g)
            for j in (i - 1, i):
                if 0 <= j < len(onset_times) and abs(onset_times[j] - g) <= tol:
                    k += 1
                    break
        return 100.0 * k / max(1, len(grid))

    print("=" * 76)
    print(f"  score       {os.path.basename(args.score)}")
    print(f"              {len(score['barlines'])-1} measures, "
          f"{'/'.join(map(str, score['meters'][0][1:]))}"
          + (f" (+{len(score['meters'])-1} meter change(s))" if len(score['meters']) > 1 else "")
          + f", {len(score['notes'])} notes")
    print(f"  performance {os.path.basename(args.performance)}")
    print(f"              {perf_mid.length:.1f}s, {len(onsets)} notes, "
          f"header says {before[0]['time_sig'] if before else '?'}")
    print(f"  aligned     {matched} notes -> {len(anchors)} anchors "
          f"({100.0*matched/max(1,len(score['notes'])):.1f}% of the score)")
    print("=" * 76)

    out, first_bar, _shift = build_repaired(score, perf_mid, events, anchors,
                                            tpb=args.tpb, pad_rests=not args.no_pad)
    v = verify(out, onsets, score, first_bar)

    print(f"  bars in the file      {v['bars']}   meter {v['meter']}   "
          f"{v['bpm']} BPM")
    print(f"  music begins at bar   {first_bar}"
          + ("  (leading rests padded so bar numbers match the score)"
             if not args.no_pad else "  -> renumbered to 1 (--no-pad)"))
    print(f"  downbeats on a note   {hit(b_downs):.1f}%  ->  {v['downbeat_pct']:.1f}%")
    print(f"  playback shifted by   {v['onset_error']*1000:.3f} ms worst case")

    if v['onset_error'] > 0.005:
        print("  WARNING: the repaired file does not play back identically.")

    if args.report:
        print("\n  --report: nothing written.")
        return 0

    dest = args.out or os.path.splitext(args.performance)[0] + '.repaired.mid'
    out.save(dest)
    print(f"\n  wrote {dest}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
