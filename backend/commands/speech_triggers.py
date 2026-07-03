# backend/commands/speech_triggers.py
"""
Room speech-trigger processing and declarative exit changes.

One code path for firing keyword triggers (used by the executor's fallback
for bare keywords AND by 'say', so 'say dawnfather' works the same as typing
'dawnfather') and one for applying add_exit/remove_exit/reciprocal_exit
configs (shared with item interactions).
"""

from typing import Any, Dict, Optional, cast


def apply_exit_config(
    config: Dict[str, Any], current_room: Any, game_state: Any
) -> None:
    """Apply declarative exit changes from an interaction or trigger config."""
    if "add_exit" in config:
        direction, target_room_id = config["add_exit"]
        current_room.exits[direction] = target_room_id
    if "remove_exit" in config:
        current_room.exits.pop(config["remove_exit"], None)
    if "reciprocal_exit" in config:
        source_id, direction, target_room_id = config["reciprocal_exit"]
        source_room = game_state.get_room(source_id)
        if source_room:
            source_room.exits[direction] = target_room_id


async def process_speech_triggers(
    raw_input: str,
    player: Any,
    current_room: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> Optional[str]:
    """
    Fire the first matching speech trigger in the room, if any.

    Returns the trigger's message, or None if nothing matched.
    """
    triggers_map = getattr(current_room, "speech_triggers", None)
    if not isinstance(triggers_map, dict) or not triggers_map:
        return None

    lowered = raw_input.lower().strip()
    for keyword, triggers in triggers_map.items():
        if keyword not in lowered:
            continue
        trigger_list = triggers if isinstance(triggers, list) else [triggers]
        for config in trigger_list:
            if not isinstance(config, dict):
                continue
            if config.get("one_time") and config.get("triggered"):
                continue
            conditional_fn = config.get("conditional_fn")
            if conditional_fn and not conditional_fn(player, game_state):
                continue
            if config.get("one_time"):
                config["triggered"] = True
            apply_exit_config(config, current_room, game_state)
            effect_fn = config.get("effect_fn")
            if effect_fn:
                await effect_fn(
                    player,
                    game_state,
                    player_manager,
                    online_sessions,
                    sio,
                    utils,
                )
            return cast(str, config.get("message", ""))
    return None
