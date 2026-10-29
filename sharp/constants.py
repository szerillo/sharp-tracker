"""Named constants for the sharp tracker. Every entry carries a provenance line (SHARP_TRACKER_BUILD_SPEC_2026-10-14 §12).

An entry without `source` is a bug. `status` is one of:
  rule      a build rule from the spec; revisit trigger noted
  prior     a reference value borrowed from outside (Matt Downs thread, upside.tools 10/13/2026); NOT a result of ours
  fitted    produced by our own test code on our own log; sample and date recorded
"""
import datetime as dt

SPEC = "SHARP_TRACKER_BUILD_SPEC_2026-10-14.md"
THREAD = "Matt Downs thread, upside.tools, 10/13/2026 (pooled NFL/NBA/MLB, hand-set weights, Pinnacle unranked)"

# ---------------------------------------------------------------- rules (spec) ----
EXCHANGE_SPREAD_MAX = dict(value=0.04, status="rule", source=f"{SPEC} §5; revisit at 10k events",
                           note="exchange mid enters the ruler only when ask-bid <= this; wider is logged, flagged wide, excluded")
EXCHANGE_MIN_DEPTH_USD = dict(value=500, status="rule", source="Sean 10/15 (Chuba Hubbard CAR@PHI, Novig -2400 bid with $2.4k vs $61 on the other side): an exchange quote enters the "
                                                              "ruler only with at least this many resting dollars within 3c of best ON EACH SIDE; otherwise flagged thin")
EXCHANGE_OUTLIER_PTS = dict(value=0.05, status="rule", source="Sean 10/15: a passing exchange quote more than this far (probability points) from the median of the books on the same "
                                                              "line is flagged outlier and excluded unless 2+ other venues sit within 3 pts of it; one big make order is not a price")
EXCHANGE_OUTLIER_CONFIRM = dict(value=2, status="rule", source="companion to exchange_outlier_pts: venues within 3 pts needed to keep an outlying exchange quote")
DISAGREEMENT_THRESHOLD_ML = dict(value=0.02, status="rule", source=f"{SPEC} §6 Test B/C (thread definition); revisit after first run")
DISAGREEMENT_THRESHOLD_LINE = dict(value=0.5, status="rule", source=f"{SPEC} §6 Test B")
MIN_EVENTS_GAME_LINES = dict(value=1500, status="rule", source=f"{SPEC} §6 publication gate")
MIN_PROP_ROWS = dict(value=20000, status="rule", source=f"{SPEC} §6 publication gate (settled prop rows)")
MIN_PAIRS_PROPS = dict(value=3000, status="rule", source=f"{SPEC} §6 Test C publication gate, per venue per sport")
MIN_EVENTS_DEVIG_FIT = dict(value=2000, status="rule", source=f"{SPEC} §5; refit at 10,000")
WEIGHT_CAP = dict(value=0.60, status="rule", source=f"{SPEC} §7")
NEW_VENUE_DAYS = dict(value=30, status="rule", source=f"{SPEC} §7: venues under 30 days sit at the median weight until 1,500 events")
SPEED_HORIZONS_MIN = dict(value=[24 * 60, 6 * 60, 60], status="rule", source=f"{SPEC} §6 Test B")
HORIZON_TOLERANCE_MIN = dict(value=120, status="rule", source="Fable 10/14: the T-24h/6h/1h snapshot is the latest tick at most this old; the game-lines job has been landing "
                                                            "irregularly (4-8 book snapshots per game instead of ~40), so 45 min would blank most snapshots; tighten to 45 once cadence is verified")
SPEED_REACTION_CONTROL_MIN = dict(value=30, status="rule", source=f"{SPEC} §6 Test B control (ii)")
CLOSE_WINDOW_MIN = dict(value=20, status="rule", source="Fable 10/14: 'close' = last tick per venue inside this many minutes before first pitch; "
                                                      "the 20-minute job cadence means most venues have exactly one tick in the window")
STALE_BOOK_MIN = dict(value=45, status="rule", source="Fable 10/14: a book tick older than this at the fair timestamp is not a price; excluded from the fair")
STALE_EXCHANGE_MIN = dict(value=45, status="rule", source="Fable 10/14: same for exchange quotes (20-minute cadence + one missed run)")
STEAM_MOVE_PTS = dict(value=0.03, status="rule", source=f"{SPEC} §6 steam-chasing test: 3+ point hourly move")
OPENER_MOVE_PTS = dict(value=0.03, status="rule", source=f"{SPEC} §6 opener test: side moved toward by 3+ points")
UNBETTABLE_VENUES = dict(value=["BetMGM"], status="rule", source="Sean: BetMGM is not bettable for him; logged, never shown as best price")
KALSHI_TAKER_FEE = dict(value=0.07, status="rule", source="Kalshi fee schedule: taker fee = 0.07 x contracts x p x (1-p), rounded up to the cent; applied to the ask when ranking bettable prices; Novig charges no pregame fee")

# ---------------------------------------------------------------- devig ----------
# Method per sport/market class. Until the calibration harness has MIN_EVENTS_DEVIG_FIT settled events the method is a
# prior from the July MLB vig-stripping battery, not a fit.
DEVIG_METHOD = {
    ("mlb", "game"): dict(value="power", status="prior", fit_date=None, sample=0, calibration_error=None, alternative="shin",
                          source="MLB vig-stripping battery, July 2026: power and Shin indistinguishable on two-way markets, both better than proportional beyond 70%"),
    ("mlb", "prop"): dict(value="power", status="prior", fit_date=None, sample=0, calibration_error=None, alternative="shin",
                          source="same battery; props are two-way"),
}
for _sp in ("nfl", "nba", "cfb", "nhl", "soccer"):
    for _mc in ("game", "prop"):
        DEVIG_METHOD[(_sp, _mc)] = dict(DEVIG_METHOD[("mlb", _mc)], source="MLB battery result carried over (Fable 10/29); two-way markets")

# ---------------------------------------------------------------- weights --------
# PRIOR weights, NOT fitted. Thread values, renormalised per venue name as we log it. They are the ridge target until
# fit_weights() has MIN_EVENTS_GAME_LINES settled events; every number the dashboard derives from these is tagged 'unfitted'.
WEIGHTS = {
    ("mlb", "game"): dict(
        value={"Novig": 7.5, "FD": 1.1, "Kalshi": 1.1, "DK": 1.0, "Pinnacle": 1.0, "Polymarket": 1.0, "Caesars": 0.3, "BetMGM": 0.1, "Fanatics": 0.1,
               "BetRivers": 0.0, "theScore": 0.0, "Circa": 1.0},
        status="prior", fit_date=None, sample=0, heldout_brier=None,
        source=f"{THREAD}; BetRivers/theScore not weighted in the thread (below coin flip) -> 0. Reference for the fit, not a weight: Downs' 10/16 update "
               "(6,087 games, 24h/6h/1h pooled) gap closure Novig 52, Polymarket 44, ProphetX 33, Kalshi 33, FD 25, Fanatics 12, Caesars 1, BetMGM -1, DK -2, "
               "BetRivers -4, bet365 -6, Hard Rock -9; Novig fell from 68 to 52 as the sample grew"),
    ("mlb", "prop"): dict(
        value={"Novig": 7.0, "Kalshi": 7.0, "DK": 1.4, "Pinnacle": 1.4, "FD": 1.0, "Caesars": 0.5, "BetMGM": 0.1, "Fanatics": 0.5,
               "BetRivers": 0.0, "theScore": 0.0},
        status="prior", fit_date=None, sample=0, heldout_brier=None, source=f"{THREAD}; BetRivers 0.3 in the thread for props, Hard Rock 0.1; neither logged by us yet"),
}
# Registry sports start from the MLB priors (same venues, same mechanism: exchange-anchored, books by closure); each is replaced by its own
# ridge fit once the sport's gate opens (Fable 10/29, placeholder prior — not a fitted weight).
for _sp in ("nfl", "nba", "cfb", "nhl", "soccer"):
    for _mc in ("game", "prop"):
        WEIGHTS[(_sp, _mc)] = dict(WEIGHTS[("mlb", _mc)], status="prior", source="MLB prior carried over as placeholder (Fable 10/29); refit per sport when gated")

# ---------------------------------------------------------------- feeds ----------
# Measured weekly: seconds between the venue's own site and the feed we log it from (spec §2). None = not measured yet.
FEED_LAG_S = {
    "Pinnacle": dict(value=None, status="rule", source="guest.api.arcadia.pinnacle.com direct; lag vs site unmeasured"),
    "Kalshi": dict(value=0, status="rule", source="Kalshi's own REST API; the venue is the feed"),
    "Polymarket": dict(value=0, status="rule", source="Polymarket Gamma + CLOB public APIs; the venue is the feed"),
    "Novig": dict(value=0, status="rule", source="Novig public API; the venue is the feed"),
    "DK": dict(value=None, status="rule", source="Action Network scoreboard (book id 1548); lag vs DK site unmeasured"),
    "FD": dict(value=None, status="rule", source="Action Network (book id 69 game lines / 1006 props); unmeasured"),
    "Caesars": dict(value=None, status="rule", source="Action Network (1005); unmeasured"),
    "BetRivers": dict(value=None, status="rule", source="Action Network (972); unmeasured"),
    "Fanatics": dict(value=None, status="rule", source="Action Network (2789); unmeasured"),
    "theScore": dict(value=None, status="rule", source="Action Network (4621); unmeasured"),
    "BetMGM": dict(value=None, status="rule", source="Action Network (939), props only; unmeasured; not bettable"),
}

VENUE_CLASS = {"Kalshi": "exchange", "Novig": "exchange", "Polymarket": "exchange", "Pinnacle": "sharp_book", "Circa": "sharp_book",
               "DK": "book", "FD": "book", "Caesars": "book", "BetRivers": "book", "Fanatics": "book", "theScore": "book", "BetMGM": "book",
               "AN_Consensus": "reference", "AN_Open": "reference"}
RULER_ELIGIBLE = {v for v, c in VENUE_CLASS.items() if c in ("exchange", "sharp_book", "book")}


def dump():
    """Flat listing for the constants panel on the dashboard."""
    out = []
    for name, c in [("exchange_spread_max", EXCHANGE_SPREAD_MAX), ("exchange_min_depth_usd", EXCHANGE_MIN_DEPTH_USD),
                    ("exchange_outlier_pts", EXCHANGE_OUTLIER_PTS), ("exchange_outlier_confirm", EXCHANGE_OUTLIER_CONFIRM), ("disagreement_threshold_ml", DISAGREEMENT_THRESHOLD_ML),
                    ("disagreement_threshold_line", DISAGREEMENT_THRESHOLD_LINE), ("min_events_game_lines", MIN_EVENTS_GAME_LINES),
                    ("min_prop_rows", MIN_PROP_ROWS), ("min_pairs_props", MIN_PAIRS_PROPS), ("min_events_devig_fit", MIN_EVENTS_DEVIG_FIT),
                    ("weight_cap", WEIGHT_CAP), ("new_venue_days", NEW_VENUE_DAYS), ("close_window_min", CLOSE_WINDOW_MIN), ("horizon_tolerance_min", HORIZON_TOLERANCE_MIN),
                    ("stale_book_min", STALE_BOOK_MIN), ("stale_exchange_min", STALE_EXCHANGE_MIN), ("steam_move_pts", STEAM_MOVE_PTS),
                    ("opener_move_pts", OPENER_MOVE_PTS), ("unbettable_venues", UNBETTABLE_VENUES), ("kalshi_taker_fee", KALSHI_TAKER_FEE)]:
        out.append(dict(name=name, **c))
    for (s, m), c in DEVIG_METHOD.items(): out.append(dict(name=f"devig_method[{s}][{m}]", **c))
    for (s, m), c in WEIGHTS.items(): out.append(dict(name=f"weights[{s}][{m}]", **c))
    for v, c in FEED_LAG_S.items(): out.append(dict(name=f"feed_lag[{v}]", **c))
    return out
