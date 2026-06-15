"""
local_choreography.py — Local choreography generator for Mini Pupper Dance

Replaces HF Space's basic commands with richer, genre-appropriate moves
generated locally. Uses the song URL as a deterministic seed so the same
song always gets the same dance.

Import chain:
    hf_dance_to_audio.py  →  local_choreography.enrich_choreography()
                                  ↓
                          robot_control.py._build_movement()
"""

import hashlib
import random


# ═══════════════════════════════════════════════════════════════════
#  Genre Move Pools
#  Each genre has 15-20 moves with probability weights.
#  Higher weight = more likely to be picked by the seeded RNG.
# ═══════════════════════════════════════════════════════════════════

GENRE_POOLS = {
    # ═══════════════════════════════════════════════════════════════
    #  Redistributed weights (2026-06-12)
    #  Goal: every move gets ≥4-5% chance. Top moves still define
    #  the genre vibe but no longer dominate (>16% max).
    #  Tail moves raised to ~4-6% so they actually appear in dances.
    # ═══════════════════════════════════════════════════════════════
    "rock": {
        # Vibe: aggressive headbanging, swagger, rear energy
        # Signature: headbang (still #1), sig:rock (windmill head)
        "moves": [
            "headbang", "sig:rock", "butt_shrug", "swagger", "dip",
            "bounce", "body_row", "backleg_lift", "twerk",
            "wiggle",
        ],
        "weights": [
            0.16, 0.04, 0.12, 0.13, 0.09,
            0.08, 0.12, 0.07, 0.11,
            0.08,
        ],
    },
    "classical": {
        # Vibe: graceful bowing, elegant swagger, ballet-like leg lifts
        # Signature: greet (bow), swagger (graceful sway)
        "moves": [
            "greet", "swagger", "backleg_lift", "dip", "nod",
            "look_up", "look_down", "body_row", "bounce",
            "butt_shrug",
        ],
        "weights": [
            0.16, 0.14, 0.12, 0.10, 0.09,
            0.08, 0.10, 0.07, 0.07, 0.07,            
        ],
    },
    "pop": {
        # Vibe: energetic, varied, body waves, twerks, sassy
        # Signature: sig:pop (body wave), twerk, wiggle
        "moves": [
            "disco1", "bounce", "swagger", "look_right", "look_left",
            "look_up", "look_down", "body_row", "backleg_lift", "twerk",
            "wiggle", "butt_shrug",
        ],
        "weights": [
            0.14, 0.11, 0.10, 0.09,
            0.09, 0.08, 0.08, 0.07, 0.06,
            0.06, 0.05, 0.07, 
        ],
    },
    "disco": {
        # Vibe: groovy shoulder shrugs, bouncy, funky body rolls
        # Signature: shoulder_shrug (the John Travolta move)
        "moves": [
            "shoulder_shrug", "bounce", "swagger", "backleg_lift",
            "body_row", "twerk", "wiggle", "dip",
            "look_up", "butt_shrug", "look_down", "nod",
        ],
        "weights": [
            0.14, 0.11, 0.10, 0.09,
            0.09, 0.08, 0.08, 0.07, 0.06,
            0.06, 0.06, 0.05,
        ],
    },
    "hiphop": {
        # Vibe: bouncy head moves, assertive twerks, swagger
        # Signature: disco2 (assertive head pattern), twerk, wiggle
        "moves": [
            "disco2", "twerk", "wiggle", "butt_shrug", "swagger",
            "bounce", "dip", "backleg_lift", "nod",
            "look_up", "look_down", "body_row",
        ],
        "weights": [
            0.13, 0.10, 0.10, 0.09, 0.09,
            0.08, 0.08, 0.07, 0.06, 0.07,
            0.05, 0.08,
        ],
    },
    "electronic": {
        # Vibe: fast rhythmic head patterns, body rolls, repetitive
        # Signature: disco3 (rapid quadrant scan), body_row, backleg_lift
        "moves": [
            "disco3", "body_row", "backleg_lift", "look_down",
            "look_up", "bounce", "twerk", "wiggle",
            "dip", "butt_shrug", "swagger", "nod",
        ],
        "weights": [
            0.13, 0.10, 0.10, 0.09,
            0.08, 0.08, 0.09, 0.08, 0.07,
            0.06, 0.05, 0.07,
        ],
    },
    "jazz": {
        # Vibe: smooth squats, cool nods, relaxed leans
        # Signature: squat (jazz crouch), nod (cool jazz nod)
        "moves": [
            "squat", "nod", "backleg_lift", "butt_shrug",
            "swagger", "dip", "body_row", "bounce", "look_up",
            "look_down", "twerk", "wiggle",
        ],
        "weights": [
            0.14, 0.10, 0.10, 0.09, 0.08,
            0.08, 0.08, 0.07, 0.08,
            0.06, 0.07, 0.05,
        ],
    },
    "latin": {
        # Vibe: hip wiggles, rear action, passionate kicks
        # Signature: front_kick (rearing kick), wiggle, butt_shrug
        "moves": [
            "front_kick", "wiggle", "butt_shrug", "twerk",
            "backleg_lift", "body_row", "look_down", "bounce",
            "dip", "swagger", "look_up", "nod",
        ],
        "weights": [
            0.13, 0.11, 0.10, 0.09,
            0.08, 0.08, 0.10, 0.10,
            0.06, 0.06, 0.05, 0.05,
        ],
    },
    "reggae": {
        # Vibe: laid-back elevation, chill nods, gentle rocks
        # Signature: raise-body (elevated chill), nod, bounce
        "moves": [
            "raise-body", "nod", "bounce", "body_row", "dip",
            "swagger", "backleg_lift", "wiggle", "butt_shrug",
            "look_up", "look_down", "twerk",
        ],
        "weights": [
            0.14, 0.10, 0.10, 0.09, 0.10,
            0.08, 0.07, 0.07, 0.09,
            0.06, 0.05, 0.05,
        ],
    },
    "country": {
        # Vibe: bouncy squats, cheerful dips, look up to the sky
        # Signature: lower_body (squat), dip, bounce
        "moves": [
            "lower_body", "dip", "bounce", "look_up", "body_row",
            "backleg_lift", "swagger", "look_down", "nod",
            "twerk", "wiggle", "butt_shrug",
        ],
        "weights": [
            0.14, 0.10, 0.10, 0.09, 0.10,
            0.08, 0.07, 0.10, 0.06, 0.06,
            0.05, 0.05,
        ],
    },
    "folk": {
        # Vibe: organic scanning, gentle bounces, earthy nods
        # Signature: seek (looking around at nature), bounce, nod
        "moves": [
            "seek", "bounce", "nod", "look_up", "look_down",
            "body_row", "swagger", "dip", "backleg_lift",
            "twerk", "wiggle", "butt_shrug",
        ],
        "weights": [
            0.14, 0.10, 0.10, 0.09, 0.10,
            0.08, 0.07, 0.10, 0.06, 0.06,
            0.05, 0.05, 
        ],
    },
}

# ── Compound Move Registry ─────────────────────────────────────
# Moves that expand into multiple atomic sub-moves across consecutive slots.
# Each entry: (atomic_command, direct_angle)
# Angles are in degrees / height units, passed directly to _build_movement,
# bypassing _map_angle (which maps the Space's 0-100 abstract values).
# Only include moves whose sub-moves are all atomic robot_control.py commands.
COMPOUND_EXPANSIONS = {
    "dip": [
        ("lower-body", 0),      # sink body down
        ("look-down", -15),     # lower gaze
        ("body-row", -15),      # tilt body left
        ("stop", 0),            # hold pose
        ("look-up", 0),         # return gaze
        ("body-row", 0),        # level body
        ("raise-body", 2),      # return height
        ("stop", 0),            # settle
    ],
    "spin": [
        ("rotate_cw", 180),     # spin 180 CW
        ("stop", 0),            # pause at apex
        ("rotate_ccw", 90),     # half spin back
        ("stop", 0),            # settle
    ],
}

# Genre aliases for HF Space / user input normalization
GENRE_ALIASES = {
    "hip-hop": "hiphop",
    "hiphop": "hiphop",
    "reggaeton": "latin",
    "salsa": "latin",
    "tango": "latin",
    "blues": "jazz",
    "r&b": "jazz",
    "soul": "jazz",
    "metal": "rock",
    "punk": "rock",
    "alternative": "rock",
    "edm": "electronic",
    "techno": "electronic",
    "house": "electronic",
    "trance": "electronic",
    "dubstep": "electronic",
    "k-pop": "pop",
    "j-pop": "pop",
    "showtunes": "pop",
    "bluegrass": "country",
    "indie": "folk",
    "acoustic": "folk",
}

# Moves that use the angle parameter
# Each entry defines the type of angle and a sensible default
ANGLE_MOVES = {
    "rotate_cw":     {"type": "rotation", "default": 30},
    "rotate_ccw":    {"type": "rotation", "default": 30},
    "body-row":      {"type": "roll",     "default": 10},
    "swagger":       {"type": "roll",     "default": 10},
    "look-up":       {"type": "pitch",    "default": 20},
    "look-down":     {"type": "pitch",    "default": 20},
    "look-right":    {"type": "yaw",      "default": 30},
    "look-left":     {"type": "yaw",      "default": 30},
    "spin":          {"type": "rotation", "default": 180},
    "lean":          {"type": "roll",     "default": 15},
    "raise-body":    {"type": "height",   "default": 10},
    "lower-body":    {"type": "height",   "default": 10},
    "squat":         {"type": "height",   "default": 15},
    "right":         {"type": "strafe",   "default": 10},
    "left":          {"type": "strafe",   "default": 10},
}


def _resolve_genre(raw_genre: str) -> str:
    """Resolve genre aliases to canonical genre names."""
    genre = raw_genre.strip().lower()
    if genre in GENRE_POOLS:
        return genre
    return GENRE_ALIASES.get(genre, "pop")


def _map_angle(move_name: str, space_angle: float) -> float:
    """Map the Space's abstract angle to what this move expects, or return None."""
    if move_name not in ANGLE_MOVES:
        return None
    info = ANGLE_MOVES[move_name]
    angle = space_angle if (space_angle and space_angle != 0) else info["default"]

    # Scale per move type
    if info["type"] == "rotation":
        return max(10, min(360, angle * 3))
    elif info["type"] == "roll":
        return max(5, min(30, angle))
    elif info["type"] == "pitch":
        return max(5, min(30, angle))
    elif info["type"] == "yaw":
        return max(5, min(45, angle))
    elif info["type"] == "height":
        return max(5, min(30, angle * 2))
    elif info["type"] == "strafe":
        return max(5, min(30, angle))
    return angle


def _expand_compounds(choreo: list, seed: str) -> list:
    """
    Expand compound moves into atomic sub-moves across consecutive slots.

    For each compound move found, replaces it with its N sub-moves
    (spaced at time_acc intervals). All subsequent entries are shifted
    right by (N - 1) * time_acc. Entries past the original song-end
    ceiling are truncated.

    Args:
        choreo: List of (cmd, time_acc, angle, start_time) from RNG pass.
        seed: Song seed string (for logging only).

    Returns:
        Expanded list with compound moves decomposed.
    """
    if not choreo:
        return choreo

    # Song-end ceiling: use the last entry's end time
    last_end = choreo[-1][3] + choreo[-1][1]

    expanded = []
    shift = 0.0  # cumulative time shift for entries after a compound

    for cmd, time_acc, angle, start_time in choreo:
        # Guard against degenerate time_acc
        slot_dur = max(time_acc, 0.1)

        adjusted_start = start_time + shift

        if cmd in COMPOUND_EXPANSIONS:
            sub_moves = COMPOUND_EXPANSIONS[cmd]
            n = len(sub_moves)
            # Emit sub-moves spaced at slot_dur intervals
            for j, (sub_cmd, fixed_angle) in enumerate(sub_moves):
                sub_start = adjusted_start + j * slot_dur
                expanded.append((sub_cmd, slot_dur, fixed_angle, sub_start))
            # Shift all subsequent entries right by (n - 1) slots
            shift += (n - 1) * slot_dur
        else:
            expanded.append((cmd, slot_dur, angle, adjusted_start))

    # Truncate entries that now start past the song-end ceiling
    expanded = [e for e in expanded if e[3] < last_end]

    return expanded


def enrich_choreography(
    hf_timed: list,
    genre: str,
    song_seed: str,
) -> list:
    """Replace HF Space commands with seed-based genre-appropriate moves.

    Pass 1: Genre-aware replacement (1:1 slot mapping).
    Pass 2: Expand compound moves into atomic sub-moves, shift remainder.
    Pass 3: Truncate entries past song-end ceiling.

    Args:
        hf_timed: List of (cmd, time_acc, angle, start_time) from HF Space.
        genre: Detected genre string.
        song_seed: Deterministic seed string (song URL or title).

    Returns:
        List of (cmd, time_acc, angle, start_time) with replaced commands.
    """
    if not hf_timed:
        return hf_timed

    # Resolve genre
    canonical_genre = _resolve_genre(genre)
    pool = GENRE_POOLS.get(canonical_genre, GENRE_POOLS["pop"])

    # Create deterministic seed from song identifier
    seed_int = int(hashlib.sha256(song_seed.encode()).hexdigest(), 16)
    rng = random.Random(seed_int)

    # ── Pass 1: genre-aware replacement (1:1) ──
    raw_choreo = []
    for entry in hf_timed:
        if len(entry) < 4:
            raw_choreo.append(entry)
            continue

        cmd, time_acc, angle, start_time = entry[:4]

        # Pick a move from the genre pool
        move = rng.choices(pool["moves"], weights=pool["weights"], k=1)[0]

        # Map the angle for this move
        move_angle = _map_angle(move, angle)

        # Negate angle for CCW rotation / left strafe
        if move in ("rotate_ccw", "left") and move_angle is not None:
            move_angle = -move_angle

        raw_choreo.append((move, time_acc, move_angle, start_time))

    # ── Pass 2: expand compounds, shift remainder ──
    expanded = _expand_compounds(raw_choreo, song_seed)

    # Log via injected logger if available
    _log_fn = getattr(enrich_choreography, "_log", None)
    if _log_fn:
        _log_fn(
            f"Local choreography: {len(expanded)} moves "
            f"(expanded from {len(raw_choreo)}), "
            f"genre={canonical_genre}, seed={seed_int & 0xFFFF:04x}"
        )

    return expanded


# Allow external code to inject a log function
enrich_choreography._log = None


def set_logger(log_func):
    """Set a logging function for this module."""
    enrich_choreography._log = log_func
