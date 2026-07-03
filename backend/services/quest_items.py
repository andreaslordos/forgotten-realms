# backend/services/quest_items.py
"""
Self-healing quest items.

Progression-critical items (the mist token, the knight's medallion) can leave
the world for good: swamped into the treasure sink for points, consumed by a
wrong interaction, or lost when a session dies without a clean disconnect.
Any of those would brick story progression for every player until the weekly
reset. Level generators register such items here, and the tick service
periodically restores any that are missing and still needed.

Items sitting in a swamp treasure-sink room (e.g. 'underlake') count as
GONE — the sink is unreachable by design, so a swamped quest item must be
restored to its source like any other loss.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuestItemAnchor:
    """Where a quest item belongs and when it stops mattering."""

    template: Any  # Item used as the blueprint for replacements
    room_id: str
    container_id: Optional[str]
    done_check: Callable[[Any], bool]  # (game_state) -> True when no longer needed


_anchors: List[QuestItemAnchor] = []


def register_quest_item(
    template: Any,
    room_id: str,
    container_id: Optional[str] = None,
    done_check: Optional[Callable[[Any], bool]] = None,
) -> None:
    """Register a progression-critical item for self-healing restoration."""
    _anchors.append(
        QuestItemAnchor(
            template=template,
            room_id=room_id,
            container_id=container_id,
            done_check=done_check or (lambda game_state: False),
        )
    )


def clear_quest_item_registry() -> None:
    """Forget all registrations (used by tests and world resets)."""
    _anchors.clear()


def _iter_items_deep(items: Any) -> Iterator[Any]:
    """Yield every item in a list, recursing into container contents."""
    if not isinstance(items, list):
        return
    for item in items:
        yield item
        yield from _iter_items_deep(getattr(item, "items", None))


def _treasure_sink_room_ids(game_state: Any) -> Set[str]:
    """Room ids that swamp rooms teleport treasure into (unreachable sinks)."""
    sinks: Set[str] = set()
    for room in game_state.rooms.values():
        destination = getattr(room, "treasure_destination", None)
        if destination:
            sinks.add(destination)
    return sinks


def _present_item_ids(
    game_state: Any, online_sessions: Dict[str, Dict[str, Any]]
) -> Set[str]:
    """One pass over the world collecting every reachable item id."""
    present: Set[str] = set()
    sinks = _treasure_sink_room_ids(game_state)
    for room_id, room in game_state.rooms.items():
        if room_id in sinks:
            continue  # Swamped items are gone for gameplay purposes.
        for hidden_id in getattr(room, "hidden_items", {}):
            present.add(str(hidden_id))
        for item in _iter_items_deep(room.items):
            item_id = getattr(item, "id", None)
            if item_id:
                present.add(str(item_id))
    for session in online_sessions.values():
        player = session.get("player")
        if player is None:
            continue
        for item in _iter_items_deep(player.inventory):
            item_id = getattr(item, "id", None)
            if item_id:
                present.add(str(item_id))
    return present


def _make_copy(template: Any) -> Any:
    return type(template).from_dict(template.to_dict())


def ensure_quest_items(
    game_state: Any, online_sessions: Dict[str, Dict[str, Any]]
) -> List[str]:
    """
    Restore any registered quest item that has vanished from the world and is
    still needed. Returns the ids of restored items.
    """
    if not _anchors:
        return []
    restored: List[str] = []
    present = _present_item_ids(game_state, online_sessions)
    for anchor in _anchors:
        try:
            if anchor.done_check(game_state):
                continue
            item_id = str(getattr(anchor.template, "id", ""))
            if not item_id or item_id in present:
                continue
            room = game_state.get_room(anchor.room_id)
            if room is None:
                continue
            fresh = _make_copy(anchor.template)
            placed = False
            if anchor.container_id:
                for item in room.items:
                    if getattr(item, "id", None) == anchor.container_id and isinstance(
                        getattr(item, "items", None), list
                    ):
                        item.items.append(fresh)
                        placed = True
                        break
            if not placed:
                room.add_item(fresh)
            restored.append(item_id)
            logger.info(
                "Restored missing quest item '%s' to %s", item_id, anchor.room_id
            )
        except Exception:  # pragma: no cover - never break the tick loop
            logger.exception("Quest item restoration failed")
    return restored
