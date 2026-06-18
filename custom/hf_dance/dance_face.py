"""
dance_face.py — Mini Pupper LCD Face Display for Dance Choreography

Cycles through REST → TROT → HOP → FINISHHOP faces on the robot's
LCD display, synced to the song's BPM and genre.

Usage:
    from dance_face import generate_face_cues, DanceFace

    cues = generate_face_cues(bpm=120, duration=180.0, genre="pop")
    df = DanceFace()
    df.start(cues, stop_flag_path="/tmp/minipupper_dance_active")
    # ... dance loop runs ...
    df.stop()
"""

import os
import time
import threading
from enum import Enum
from MangDang.mini_pupper.display import Display


class BehaviorState(Enum):
    DEACTIVATED = -1
    REST = 0
    TROT = 1
    HOP = 2
    FINISHHOP = 3
    SHUTDOWN = 96
    IP = 97
    TEST = 98
    LOWBATTERY = 99


# The face cycle: calm -> moving -> leap -> landing -> repeat
FACE_CYCLE = [
    BehaviorState.REST,       # calm
    BehaviorState.TROT,       # walking
    BehaviorState.HOP,        # leaping!
    BehaviorState.FINISHHOP,  # landing
]

# Genre -> beats per face change (higher = slower / more relaxed)
GENRE_PACING = {
    "classical":   8,   # slow, graceful
    "jazz":        6,   # smooth
    "chill":       8,   # relaxed
    "reggae":      6,   # laid-back
    "folk":        6,   # unhurried
    "pop":         4,   # energetic 4-beat
    "hiphop":      4,   # bouncy
    "country":     4,   # cheerful
    "disco":       4,   # groovy
    "latin":       3,   # faster 3-beat
    "rock":        2,   # aggressive 2-beat
    "electronic":  2,   # rapid-fire
}
DEFAULT_PACING = 4


def generate_face_cues(bpm: float, duration: float, genre: str = "pop") -> list:
    """
    Generate face-change cues synced to BPM and genre pacing.

    Returns list of (cmd, time_acc, angle, start_time) tuples compatible
    with the dance timetable format.

    Fields:
        cmd        = "display"  (sentinel for the dance loop)
        time_acc   = 0.0        (instant -- no acceleration)
        angle      = float      (BehaviorState.value)
        start_time = float      (seconds from audio start)
    """
    if bpm <= 0:
        bpm = 120

    beat_s = 60.0 / bpm
    pacing = GENRE_PACING.get(genre.lower(), DEFAULT_PACING)
    cycle_len = len(FACE_CYCLE)

    cues = []
    beat_num = 0

    while True:
        t = beat_num * beat_s
        if t > duration:
            break

        if beat_num % pacing == 0:
            idx = (beat_num // pacing) % cycle_len
            state_val = float(FACE_CYCLE[idx].value)
            cues.append(("display", 0.0, state_val, t))

        beat_num += 1

    return cues


def _resolve_state(val: float) -> BehaviorState:
    """Convert a stored float back to a BehaviorState enum member."""
    try:
        return BehaviorState(int(val))
    except (ValueError, TypeError):
        return BehaviorState.REST


class DanceFace:
    """
    Manages the Mini Pupper LCD display during a dance session.

    Runs face changes in a lightweight daemon thread that sleeps until
    each cue's timestamp, then calls Display.show_state().

    The thread checks stop_flag_path on every sleep cycle so it dies
    cleanly when cmd_stop() is invoked.
    """

    def __init__(self):
        self.disp = Display()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # -----------------------------------------------------------------
    def start(
        self,
        cues: list,
        audio_delay: float = 0.0,
        stop_flag_path: str = "/tmp/minipupper_dance_active",
    ) -> None:
        """
        Start the face-display thread.

        Args:
            cues: (cmd, time_acc, angle, start_time) tuples from
                  generate_face_cues(), OR simpler (state_val, time) pairs.
            audio_delay: Seconds to offset all cue times by.
            stop_flag_path: Thread stops if this file disappears.
        """
        if not cues:
            return

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(cues, audio_delay, stop_flag_path),
            daemon=True,
        )
        self._thread.start()

    # -----------------------------------------------------------------
    def stop(self) -> None:
        """Signal the face thread to stop and wait up to 2s."""
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    # -----------------------------------------------------------------
    def show_now(self, state_val: int) -> None:
        """Immediately show a face (useful for post-dance)."""
        try:
            self.disp.show_state(_resolve_state(state_val))
        except Exception:
            pass

    # -----------------------------------------------------------------
    #  Internal
    # -----------------------------------------------------------------
    def _run(self, cues: list, audio_delay: float, stop_flag_path: str) -> None:
        t0 = time.time()

        # Normalise to (state_value, start_time) pairs
        pairs = []
        for c in cues:
            if len(c) == 2:
                pairs.append((c[0], c[1]))
            elif len(c) >= 4:
                pairs.append((int(c[2]), c[3]))
            else:
                continue

        if not pairs:
            return

        for state_val, cue_time in pairs:
            if self._stop.is_set() or not os.path.exists(stop_flag_path):
                break

            elapsed = time.time() - t0
            remaining = audio_delay + cue_time - elapsed

            if remaining > 0:
                while remaining > 0 and not self._stop.is_set() and os.path.exists(stop_flag_path):
                    chunk = min(remaining, 0.5)
                    time.sleep(chunk)
                    remaining -= chunk

            if self._stop.is_set() or not os.path.exists(stop_flag_path):
                break

            try:
                self.disp.show_state(_resolve_state(state_val))
            except Exception:
                pass


def face_cues_from_choreography(timed_moves: list, genre: str = "pop") -> list:
    """
    Generate face-change cues from the actual choreography timestamps.

    Instead of synthesizing timestamps from BPM, this uses the start_time
    of every Nth entry in the timed choreography. This naturally tracks
    variable tempo because it follows whatever timing the HF Space baked in.

    Args:
        timed_moves: List of (cmd, duration, angle, start_time) tuples.
        genre: Genre string for pacing selection.

    Returns:
        List of (cmd, time_acc, angle, start_time) tuples in the same
        format as generate_face_cues().
    """
    if not timed_moves or not isinstance(timed_moves, list):
        return []

    pacing = GENRE_PACING.get(genre.lower(), DEFAULT_PACING)
    cycle_len = len(FACE_CYCLE)

    cues = []
    for i, entry in enumerate(timed_moves):
        if len(entry) < 4:
            continue
        if i % pacing == 0:
            face_idx = (i // pacing) % cycle_len
            state_val = float(FACE_CYCLE[face_idx].value)
            # Use the choreography entry's actual start_time
            cues.append(("display", 0.0, state_val, entry[3]))

    return cues
