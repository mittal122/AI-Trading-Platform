"""Market structure (§5.3).

Walks swings chronologically, labelling each as HH/HL/LH/LL against the previous
swing of the same kind, and emitting BOS/CHoCH structure events:

  * A new high above the last swing high -> BOS_up if the trend is already "up",
    otherwise CHoCH_up (and the trend flips to "up"). Mirrored for lows/down.
  * The series trend is the direction of the last structure event ("neutral" if
    none exist).

The level stored on a structure event is the *broken* prior swing extreme — the
price at which structure gave way (what you'd draw the BOS/CHoCH line at).
"""

from dataclasses import dataclass, field

from backend.app.schemas.smc import (
    StructureEvent,
    StructureType,
    Swing,
    SwingLabel,
    TrendState,
)


@dataclass
class StructureResult:
    swings: list[Swing] = field(default_factory=list)   # now carrying labels
    events: list[StructureEvent] = field(default_factory=list)
    trend: TrendState = TrendState.NEUTRAL


def analyze_structure(swings: list[Swing]) -> StructureResult:
    prev_high: float | None = None
    prev_low: float | None = None
    trend = TrendState.NEUTRAL
    events: list[StructureEvent] = []

    for s in swings:
        if s.is_high:
            if prev_high is not None and s.price > prev_high:
                s.label = SwingLabel.HH
                if trend == TrendState.UP:
                    etype = StructureType.BOS_UP
                else:
                    etype = StructureType.CHOCH_UP
                    trend = TrendState.UP
                events.append(StructureEvent(
                    index=s.index, time=s.time, price=prev_high, type=etype,
                ))
            elif prev_high is not None:
                s.label = SwingLabel.LH
            prev_high = s.price
        else:
            if prev_low is not None and s.price < prev_low:
                s.label = SwingLabel.LL
                if trend == TrendState.DOWN:
                    etype = StructureType.BOS_DOWN
                else:
                    etype = StructureType.CHOCH_DOWN
                    trend = TrendState.DOWN
                events.append(StructureEvent(
                    index=s.index, time=s.time, price=prev_low, type=etype,
                ))
            elif prev_low is not None:
                s.label = SwingLabel.HL
            prev_low = s.price

    return StructureResult(swings=swings, events=events, trend=trend)
