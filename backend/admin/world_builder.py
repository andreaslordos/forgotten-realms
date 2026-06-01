import copy
import json
import math
import os
import subprocess
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from managers.game_state import GameState
from managers.mob_manager import MobManager
from models.ContainerItem import ContainerItem
from models.Item import Item
from models.Mobile import Mobile
from models.Room import Room
from models.StatefulItem import StatefulItem
from models.Weapon import Weapon

JsonDict = Dict[str, Any]
PathLike = Union[str, Path]

WORLD_DATA_VERSION = 1
HEX_DIGITS = set("0123456789abcdefABCDEF")
WORLD_SCRIPT_ROOT = Path("backend/world_scripts")


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    path: str = ""

    def to_dict(self) -> JsonDict:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class ValidationResult:
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> JsonDict:
        return {
            "ok": self.ok,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


@dataclass
class PublishResult:
    ok: bool
    step: str
    output: str = ""
    error: str = ""
    validation: Optional[JsonDict] = None

    def to_dict(self) -> JsonDict:
        data: JsonDict = {
            "ok": self.ok,
            "step": self.step,
            "output": self.output,
            "error": self.error,
        }
        if self.validation is not None:
            data["validation"] = self.validation
        return data


def export_live_world(
    game_state: GameState,
    mob_manager: Optional[MobManager] = None,
    *,
    spawn_room_id: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> JsonDict:
    rooms = [
        _serialize_room(room)
        for room in game_state.rooms.values()
        if isinstance(room, Room)
    ]
    mobs = [
        _serialize_mob(mob)
        for mob in (mob_manager.get_all_mobs() if mob_manager else [])
        if isinstance(mob, Mobile)
    ]
    return {
        "version": WORLD_DATA_VERSION,
        "spawn_room_id": spawn_room_id,
        "metadata": _json_safe(dict(metadata or {})),
        "rooms": rooms,
        "mobs": mobs,
    }


def validate_world_data(
    world_data: Mapping[str, Any], *, spawn_room_id: Optional[str] = None
) -> ValidationResult:
    result = ValidationResult()
    room_entries = _room_entries(world_data)
    room_ids = [_room_id(room) for _, _, room in room_entries]
    non_empty_room_ids = [room_id for room_id in room_ids if room_id]
    room_id_set = set(non_empty_room_ids)
    metadata = _validate_authoring_metadata(result, world_data)

    for room_id, count in Counter(non_empty_room_ids).items():
        if count > 1:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "duplicate_room_id",
                    f"Room id '{room_id}' appears {count} times.",
                    "rooms",
                )
            )

    for _, path, room in room_entries:
        room_id = _room_id(room)
        if not room_id:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "missing_room_id",
                    "Room is missing an id.",
                    path,
                )
            )
        if not room.get("name"):
            result.errors.append(
                ValidationIssue(
                    "error",
                    "missing_room_name",
                    f"Room '{room_id or '<missing>'}' is missing a name.",
                    f"{path}.name",
                )
            )

        exits = room.get("exits", {}) or {}
        if isinstance(exits, Mapping):
            for direction, target_room_id in exits.items():
                if target_room_id not in room_id_set:
                    result.errors.append(
                        ValidationIssue(
                            "error",
                            "broken_exit",
                            f"Room '{room_id}' exit '{direction}' points to missing room '{target_room_id}'.",
                            f"{path}.exits.{direction}",
                        )
                    )

        _validate_items_for_room_refs(result, room.get("items", []), room_id_set, path)
        _validate_hidden_items_for_room_refs(
            result, room.get("hidden_items", []), room_id_set, path
        )
        _validate_room_authoring_metadata(result, room, path, metadata)

    for index, mob in enumerate(_list_value(world_data.get("mobs", []))):
        if not isinstance(mob, Mapping):
            continue
        mob_id = str(mob.get("id") or "")
        mob_path = f"mobs[{index}]"
        if not mob_id:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "missing_mob_id",
                    "Mob is missing an id.",
                    mob_path,
                )
            )
        if not mob.get("name"):
            result.errors.append(
                ValidationIssue(
                    "error",
                    "missing_mob_name",
                    f"Mob '{mob_id or '<missing>'}' is missing a name.",
                    f"{mob_path}.name",
                )
            )
        current_room = mob.get("current_room")
        if current_room and current_room not in room_id_set:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_mob_room_ref",
                    f"Mob '{mob_id}' references missing current_room '{current_room}'.",
                    f"{mob_path}.current_room",
                )
            )
        for patrol_index, patrol_room_id in enumerate(
            _list_value(mob.get("patrol_rooms", []))
        ):
            if patrol_room_id not in room_id_set:
                result.errors.append(
                    ValidationIssue(
                        "error",
                        "invalid_mob_patrol_ref",
                        f"Mob '{mob_id}' patrol room '{patrol_room_id}' does not exist.",
                        f"{mob_path}.patrol_rooms[{patrol_index}]",
                    )
                )

    for index, script in enumerate(_script_entries(world_data)):
        script_id = str(script.get("id") or "")
        script_path = str(script.get("path") or "")
        script_ref_path = f"scripts[{index}]"
        if not script_id:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "missing_script_id",
                    "Script is missing an id.",
                    script_ref_path,
                )
            )
        if not script_path or _resolve_world_script_path(Path("."), script_path) is None:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_script_path",
                    f"Script '{script_id or '<missing>'}' must use a safe repo-relative path.",
                    f"{script_ref_path}.path",
                )
            )
        room_ref = script.get("room_id")
        if room_ref and room_ref not in room_id_set:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_script_room_ref",
                    f"Script '{script_id or '<missing>'}' references missing room_id '{room_ref}'.",
                    f"{script_ref_path}.room_id",
                )
            )

    effective_spawn_room_id = spawn_room_id or world_data.get("spawn_room_id")
    if effective_spawn_room_id:
        if effective_spawn_room_id not in room_id_set:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "spawn_room_missing",
                    f"Spawn room '{effective_spawn_room_id}' does not exist.",
                    "spawn_room_id",
                )
            )
        else:
            reachable = _reachable_rooms(room_entries, str(effective_spawn_room_id))
            for room_id in sorted(room_id_set - reachable):
                result.warnings.append(
                    ValidationIssue(
                        "warning",
                        "unreachable_room",
                        f"Room '{room_id}' is unreachable from spawn '{effective_spawn_room_id}'.",
                        f"rooms.{room_id}",
                    )
                )

    return result


def save_world_data(world_data: Mapping[str, Any], path: PathLike) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(_json_safe(dict(world_data)), handle, indent=2, sort_keys=True)
        handle.write("\n")


def save_script_files(
    world_data: Mapping[str, Any], repo_path: PathLike
) -> List[Path]:
    """Write GUI-authored script entries with content to repo-relative files."""
    repo_root = Path(repo_path).resolve()
    written: List[Path] = []
    for script in _script_entries(world_data):
        script_path = script.get("path")
        content = script.get("content")
        if not script_path or content is None:
            continue
        resolved_path = _resolve_world_script_path(repo_root, str(script_path))
        if resolved_path is None:
            continue
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(str(content), encoding="utf-8")
        written.append(resolved_path)
    return written


def load_world_data(path: PathLike) -> JsonDict:
    with Path(path).open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("World data root must be a JSON object.")
    return loaded


def apply_world_data(
    world_data: Mapping[str, Any],
    game_state: GameState,
    mob_manager: Optional[MobManager] = None,
) -> ValidationResult:
    validation = validate_world_data(world_data)
    if not validation.ok:
        return validation

    existing_hidden_conditions = _hidden_item_conditions_by_room(game_state.rooms)
    new_rooms: Dict[str, Room] = {}
    for _, _, room_data in _room_entries(world_data):
        room_id = _room_id(room_data)
        if not room_id:
            continue
        room = Room(
            room_id=room_id,
            name=str(room_data.get("name") or ""),
            description=str(room_data.get("description") or ""),
            exits=dict(room_data.get("exits", {}) or {}),
            is_dark=bool(room_data.get("is_dark", False)),
            is_outdoor=bool(room_data.get("is_outdoor", False)),
        )
        room.swamp_direction = room_data.get("swamp_direction")
        room.speech_triggers = _strip_unserializable_markers(
            room_data.get("speech_triggers", {}) or {}
        )

        for item_data in _list_value(room_data.get("items", [])):
            if isinstance(item_data, Mapping):
                item = _item_from_data(item_data)
                _set_room_id_if_supported(item, room_id)
                room.add_item(item)

        for hidden_id, hidden_item_data in _hidden_item_entries(
            room_data.get("hidden_items", [])
        ):
            item = _item_from_data(hidden_item_data)
            _set_room_id_if_supported(item, room_id)
            item_id = hidden_id or item.id
            condition = existing_hidden_conditions.get(room_id, {}).get(
                item_id, _hidden_item_condition
            )
            room.hidden_items[item_id] = (item, condition)

        new_rooms[room_id] = room

    new_mobs: Dict[str, Mobile] = {}
    for mob_data in _list_value(world_data.get("mobs", [])):
        if not isinstance(mob_data, Mapping):
            continue
        mob = _mob_from_data(mob_data)
        new_mobs[mob.id] = mob
        if mob.current_room and mob.current_room in new_rooms:
            new_rooms[mob.current_room].add_item(mob)

    game_state.rooms = new_rooms
    if mob_manager is not None:
        mob_manager.mobs = new_mobs
    return validation


def run_git_publish(
    world_data: Mapping[str, Any],
    data_path: PathLike,
    *,
    repo_path: PathLike = ".",
    message: Optional[str] = None,
    checks: Optional[Sequence[Sequence[str]]] = None,
) -> PublishResult:
    validation = validate_world_data(world_data)
    if not validation.ok:
        return PublishResult(
            ok=False,
            step="validate",
            error="World data validation failed.",
            validation=validation.to_dict(),
        )

    save_world_data(world_data, data_path)
    script_paths = save_script_files(world_data, repo_path)

    repo_cwd = str(repo_path)
    for check_command in checks or []:
        completed = _run_command(check_command, repo_cwd)
        if completed.returncode != 0:
            return _failed_publish_result("check", completed)

    add_paths = [str(data_path)] + [str(script_path) for script_path in script_paths]
    commands: List[Tuple[str, Sequence[str]]] = [
        ("add", ["git", "add", *add_paths]),
        ("commit", ["git", "commit", "-m", message or "Publish world data"]),
        ("push", ["git", "push"]),
    ]
    output_parts: List[str] = []
    for step, command in commands:
        completed = _run_command(command, repo_cwd)
        output_parts.append(_combined_output(completed))
        if completed.returncode != 0:
            return _failed_publish_result(step, completed)

    return PublishResult(ok=True, step="push", output="\n".join(output_parts))


class WorldBuilder:
    def __init__(
        self,
        *,
        game_state: GameState,
        mob_manager: Optional[MobManager] = None,
        data_path: PathLike,
        repo_path: PathLike = ".",
        spawn_room_id: Optional[str] = None,
    ) -> None:
        self.game_state = game_state
        self.mob_manager = mob_manager
        self.data_path = Path(data_path)
        self.repo_path = Path(repo_path)
        self.spawn_room_id = spawn_room_id

    def export_current(self, metadata: Optional[Mapping[str, Any]] = None) -> JsonDict:
        return export_live_world(
            self.game_state,
            self.mob_manager,
            spawn_room_id=self.spawn_room_id,
            metadata=metadata,
        )

    def load(self) -> JsonDict:
        return load_world_data(self.data_path)

    def load_or_export(self) -> JsonDict:
        if self.data_path.exists():
            return self.load()
        return self.export_current()

    def validate(self, world_data: Mapping[str, Any]) -> ValidationResult:
        return validate_world_data(world_data, spawn_room_id=self.spawn_room_id)

    def save(self, world_data: Mapping[str, Any]) -> JsonDict:
        save_world_data(world_data, self.data_path)
        script_paths = save_script_files(world_data, self.repo_path)
        return {
            "path": str(self.data_path),
            "scripts": [str(path) for path in script_paths],
        }

    def apply(self, world_data: Mapping[str, Any]) -> ValidationResult:
        return apply_world_data(world_data, self.game_state, self.mob_manager)

    def reset_from_baseline(
        self, world_factory: Callable[..., Dict[str, Room]]
    ) -> JsonDict:
        if self.mob_manager is not None:
            self.mob_manager.mobs = {}
            generated_rooms = world_factory(mob_manager=self.mob_manager)
        else:
            generated_rooms = world_factory()

        self.game_state.rooms = {}
        for room in generated_rooms.values():
            self.game_state.add_room(room)

        world_data = self.export_current(metadata={"source": "baseline_reset"})
        self.save(world_data)
        return world_data

    def publish(
        self,
        world_data: Mapping[str, Any],
        *,
        message: Optional[str] = None,
        checks: Optional[Sequence[Sequence[str]]] = None,
    ) -> PublishResult:
        return run_git_publish(
            world_data,
            self.data_path,
            repo_path=self.repo_path,
            message=message,
            checks=checks,
        )


def _serialize_room(room: Room) -> JsonDict:
    return {
        "id": room.room_id,
        "name": room.name,
        "description": room.description,
        "exits": _json_safe(dict(room.exits)),
        "is_dark": room.is_dark,
        "is_outdoor": room.is_outdoor,
        "swamp_direction": room.swamp_direction,
        "items": [
            _serialize_item(item)
            for item in room.items
            if not isinstance(item, Mobile)
        ],
        "hidden_items": [
            {
                "id": item_id,
                "item": _serialize_item(item),
                "condition": _json_safe(condition),
            }
            for item_id, (item, condition) in room.hidden_items.items()
        ],
        "speech_triggers": _json_safe(room.speech_triggers),
    }


def _serialize_item(item: Any) -> JsonDict:
    if isinstance(item, Mobile):
        return _serialize_mob(item)

    if isinstance(item, ContainerItem):
        data = item.to_dict()
        data["type"] = "container_item"
        data["items"] = [_serialize_item(contained) for contained in item.items]
        return _json_safe(data)

    if isinstance(item, Weapon):
        data = item.to_dict()
        data["type"] = "weapon"
        return _json_safe(data)

    if isinstance(item, StatefulItem):
        data = item.to_dict()
        data["type"] = "stateful_item"
        data["state"] = item.state
        data["state_descriptions"] = dict(item.state_descriptions)
        data["interactions"] = item.interactions
        data["room_id"] = item.room_id
        data["linked_items"] = list(item.linked_items)
        return _json_safe(data)

    if isinstance(item, Item):
        data = item.to_dict()
        data["type"] = "item"
        return _json_safe(data)

    return _json_safe({"type": "unknown", "repr": repr(item)})


def _serialize_mob(mob: Mobile) -> JsonDict:
    data = mob.to_dict()
    data["type"] = "mobile"
    data["loot_table"] = [
        {"item": _serialize_item(entry.get("item")), "chance": entry.get("chance", 0)}
        for entry in mob.loot_table
        if isinstance(entry, Mapping) and entry.get("item") is not None
    ]
    return _json_safe(data)


def _item_from_data(data: Mapping[str, Any]) -> Item:
    sanitized = _strip_unserializable_markers(dict(data))
    item_type = sanitized.get("type") or sanitized.get("item_type")

    if item_type == "weapon":
        return Weapon.from_dict(sanitized)

    if item_type == "container_item":
        container = ContainerItem(
            name=str(sanitized["name"]),
            id=str(sanitized["id"]),
            description=str(sanitized.get("description", "")),
            weight=int(sanitized.get("base_weight", sanitized.get("weight", 1))),
            value=int(sanitized.get("value", 0)),
            takeable=bool(sanitized.get("takeable", True)),
            state=sanitized.get("state", "open"),
            capacity_limit=int(sanitized.get("capacity_limit", 10)),
            capacity_weight=int(sanitized.get("capacity_weight", 100)),
            no_removal=bool(sanitized.get("no_removal", False)),
            no_removal_message=sanitized.get("no_removal_message"),
        )
        container.items = [
            _item_from_data(item_data)
            for item_data in _list_value(sanitized.get("items", []))
            if isinstance(item_data, Mapping)
        ]
        container.state_descriptions = dict(sanitized.get("state_descriptions", {}))
        if sanitized.get("interactions") is not None:
            container.interactions = dict(sanitized.get("interactions", {}))
        container.linked_items = list(sanitized.get("linked_items", []))
        container.room_id = sanitized.get("room_id")
        container.base_description = str(
            sanitized.get("base_description", sanitized.get("description", ""))
        )
        container.base_weight = int(
            sanitized.get("base_weight", sanitized.get("weight", 1))
        )
        container.update_weight()
        container.update_description()
        return container

    if item_type == "stateful_item" or "state" in sanitized or "interactions" in sanitized:
        item = StatefulItem.from_dict(sanitized)
        item.interactions = dict(sanitized.get("interactions", {}))
        item.linked_items = list(sanitized.get("linked_items", []))
        item.room_id = sanitized.get("room_id")
        return item

    return Item.from_dict(sanitized)


def _mob_from_data(data: Mapping[str, Any]) -> Mobile:
    sanitized = _strip_unserializable_markers(dict(data))
    mob = Mobile.from_dict(sanitized)
    if "interactions" in sanitized:
        mob.interactions = dict(sanitized.get("interactions", {}))
    if "linked_items" in sanitized:
        mob.linked_items = list(sanitized.get("linked_items", []))
    return mob


def _room_entries(world_data: Mapping[str, Any]) -> List[Tuple[str, str, JsonDict]]:
    rooms = world_data.get("rooms", [])
    entries: List[Tuple[str, str, JsonDict]] = []
    if isinstance(rooms, Mapping):
        for key, value in rooms.items():
            if not isinstance(value, Mapping):
                continue
            room = dict(value)
            room.setdefault("id", key)
            entries.append((str(key), f"rooms.{key}", room))
        return entries

    for index, value in enumerate(_list_value(rooms)):
        if isinstance(value, Mapping):
            entries.append((str(index), f"rooms[{index}]", dict(value)))
    return entries


def _room_id(room: Mapping[str, Any]) -> str:
    return str(room.get("id") or room.get("room_id") or "")


def _validate_authoring_metadata(
    result: ValidationResult, world_data: Mapping[str, Any]
) -> JsonDict:
    regions = _metadata_entries(result, world_data, "regions")
    layers = _metadata_entries(result, world_data, "layers")
    tags = _metadata_entries(result, world_data, "tags")

    region_ids = _metadata_ids(result, regions, "region", "regions")
    layer_ids = _metadata_ids(result, layers, "layer", "layers")
    tag_ids = _metadata_ids(result, tags, "tag", "tags")
    region_id_set = set(region_ids)
    layer_id_set = set(layer_ids)

    _validate_duplicate_metadata_ids(result, "region", region_ids, "regions")
    _validate_duplicate_metadata_ids(result, "layer", layer_ids, "layers")
    _validate_duplicate_metadata_ids(result, "tag", tag_ids, "tags")

    parent_by_region: Dict[str, str] = {}
    for index, region in regions:
        region_id = _metadata_id(region)
        region_path = f"regions[{index}]"
        if "color" in region and not _is_valid_hex_color(region.get("color")):
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_region_color",
                    f"Region '{region_id or '<missing>'}' has invalid hex color.",
                    f"{region_path}.color",
                )
            )
        parent_region_id = region.get("parent_region_id")
        if parent_region_id:
            parent_ref = str(parent_region_id)
            parent_by_region[region_id] = parent_ref
            if parent_ref not in region_id_set:
                result.errors.append(
                    ValidationIssue(
                        "error",
                        "invalid_region_parent_ref",
                        f"Region '{region_id}' references missing parent_region_id '{parent_ref}'.",
                        f"{region_path}.parent_region_id",
                    )
                )

    _validate_region_parent_cycles(result, parent_by_region)

    layer_z_by_id: Dict[str, float] = {}
    for index, layer in layers:
        layer_id = _metadata_id(layer)
        layer_path = f"layers[{index}]"
        if "color" in layer and not _is_valid_hex_color(layer.get("color")):
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_layer_color",
                    f"Layer '{layer_id or '<missing>'}' has invalid hex color.",
                    f"{layer_path}.color",
                )
            )
        region_ref = layer.get("region_id")
        if region_ref and str(region_ref) not in region_id_set:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_layer_region_ref",
                    f"Layer '{layer_id}' references missing region_id '{region_ref}'.",
                    f"{layer_path}.region_id",
                )
            )
        if "z" in layer:
            layer_z = _finite_number_value(layer.get("z"))
            if layer_z is None:
                result.errors.append(
                    ValidationIssue(
                        "error",
                        "invalid_layer_z",
                        f"Layer '{layer_id or '<missing>'}' z must be a finite number.",
                        f"{layer_path}.z",
                    )
                )
            elif layer_id:
                layer_z_by_id[layer_id] = layer_z

    for index, tag in tags:
        tag_id = _metadata_id(tag)
        if "color" in tag and not _is_valid_hex_color(tag.get("color")):
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_tag_color",
                    f"Tag '{tag_id or '<missing>'}' has invalid hex color.",
                    f"tags[{index}].color",
                )
            )

    layout = world_data.get("layout")
    if layout is not None:
        if not isinstance(layout, Mapping):
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_layout_metadata",
                    "World layout metadata must be an object.",
                    "layout",
                )
            )
        else:
            default_layer_id = layout.get("default_layer_id")
            if default_layer_id and str(default_layer_id) not in layer_id_set:
                result.errors.append(
                    ValidationIssue(
                        "error",
                        "invalid_layout_default_layer_ref",
                        f"Layout default_layer_id '{default_layer_id}' does not exist.",
                        "layout.default_layer_id",
                    )
                )

    return {
        "region_ids": region_id_set,
        "layer_ids": layer_id_set,
        "tag_ids": set(tag_ids),
        "layer_z_by_id": layer_z_by_id,
    }


def _validate_room_authoring_metadata(
    result: ValidationResult,
    room: Mapping[str, Any],
    path: str,
    metadata: Mapping[str, Any],
) -> None:
    room_id = _room_id(room)
    region_ids = _string_set(metadata.get("region_ids", set()))
    layer_ids = _string_set(metadata.get("layer_ids", set()))
    tag_ids = _string_set(metadata.get("tag_ids", set()))
    layer_z_by_id = metadata.get("layer_z_by_id", {})

    region_ref = room.get("region_id")
    if region_ref and str(region_ref) not in region_ids:
        result.errors.append(
            ValidationIssue(
                "error",
                "invalid_room_region_ref",
                f"Room '{room_id}' references missing region_id '{region_ref}'.",
                f"{path}.region_id",
            )
        )

    tags = room.get("tags", [])
    if tags is None:
        tags = []
    if not isinstance(tags, list):
        result.errors.append(
            ValidationIssue(
                "error",
                "invalid_room_tags",
                f"Room '{room_id}' tags must be a list.",
                f"{path}.tags",
            )
        )
    else:
        for index, tag_ref in enumerate(tags):
            if str(tag_ref) not in tag_ids:
                result.errors.append(
                    ValidationIssue(
                        "error",
                        "invalid_room_tag_ref",
                        f"Room '{room_id}' references missing tag '{tag_ref}'.",
                        f"{path}.tags[{index}]",
                    )
                )

    layout = room.get("layout")
    if layout is None:
        return
    if not isinstance(layout, Mapping):
        result.errors.append(
            ValidationIssue(
                "error",
                "invalid_room_layout",
                f"Room '{room_id}' layout must be an object.",
                f"{path}.layout",
            )
        )
        return

    for coordinate in ("x", "y"):
        if coordinate in layout and _finite_number_value(layout.get(coordinate)) is None:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_room_layout_coordinate",
                    f"Room '{room_id}' layout.{coordinate} must be a finite number.",
                    f"{path}.layout.{coordinate}",
                )
            )

    layer_ref = layout.get("layer_id")
    if layer_ref and str(layer_ref) not in layer_ids:
        result.errors.append(
            ValidationIssue(
                "error",
                "invalid_room_layer_ref",
                f"Room '{room_id}' references missing layout.layer_id '{layer_ref}'.",
                f"{path}.layout.layer_id",
            )
        )

    _warn_for_legacy_layout_conflicts(
        result,
        room,
        layout,
        path,
        room_id,
        layer_z_by_id if isinstance(layer_z_by_id, Mapping) else {},
    )


def _metadata_entries(
    result: ValidationResult, world_data: Mapping[str, Any], key: str
) -> List[Tuple[int, Mapping[str, Any]]]:
    value = world_data.get(key, [])
    if value in (None, []):
        return []
    if not isinstance(value, list):
        result.errors.append(
            ValidationIssue(
                "error",
                f"invalid_{key}_metadata",
                f"World {key} metadata must be a list.",
                key,
            )
        )
        return []

    entries: List[Tuple[int, Mapping[str, Any]]] = []
    singular = key[:-1]
    for index, entry in enumerate(value):
        if not isinstance(entry, Mapping):
            result.errors.append(
                ValidationIssue(
                    "error",
                    f"invalid_{singular}_metadata",
                    f"World {singular} metadata entry must be an object.",
                    f"{key}[{index}]",
                )
            )
            continue
        entries.append((index, entry))
    return entries


def _metadata_ids(
    result: ValidationResult,
    entries: Sequence[Tuple[int, Mapping[str, Any]]],
    kind: str,
    path: str,
) -> List[str]:
    ids: List[str] = []
    for index, entry in entries:
        entry_id = _metadata_id(entry)
        if not entry_id:
            result.errors.append(
                ValidationIssue(
                    "error",
                    f"missing_{kind}_id",
                    f"{kind.title()} is missing an id.",
                    f"{path}[{index}].id",
                )
            )
            continue
        ids.append(entry_id)
    return ids


def _metadata_id(entry: Mapping[str, Any]) -> str:
    return str(entry.get("id") or "")


def _validate_duplicate_metadata_ids(
    result: ValidationResult, kind: str, ids: Sequence[str], path: str
) -> None:
    for entry_id, count in Counter(ids).items():
        if count > 1:
            result.errors.append(
                ValidationIssue(
                    "error",
                    f"duplicate_{kind}_id",
                    f"{kind.title()} id '{entry_id}' appears {count} times.",
                    path,
                )
            )


def _validate_region_parent_cycles(
    result: ValidationResult, parent_by_region: Mapping[str, str]
) -> None:
    reported_cycles: Set[frozenset[str]] = set()
    for start_region_id in parent_by_region:
        seen_at: Dict[str, int] = {}
        path: List[str] = []
        region_id: Optional[str] = start_region_id
        while region_id and region_id in parent_by_region:
            if region_id in seen_at:
                cycle = path[seen_at[region_id] :] + [region_id]
                cycle_key = frozenset(cycle)
                if cycle_key not in reported_cycles:
                    reported_cycles.add(cycle_key)
                    result.errors.append(
                        ValidationIssue(
                            "error",
                            "region_parent_cycle",
                            f"Region parent cycle detected: {' -> '.join(cycle)}.",
                            f"regions.{region_id}.parent_region_id",
                        )
                    )
                break
            seen_at[region_id] = len(path)
            path.append(region_id)
            region_id = parent_by_region.get(region_id)


def _warn_for_legacy_layout_conflicts(
    result: ValidationResult,
    room: Mapping[str, Any],
    layout: Mapping[str, Any],
    path: str,
    room_id: str,
    layer_z_by_id: Mapping[str, Any],
) -> None:
    for coordinate in ("x", "y"):
        legacy_value = _finite_number_value(room.get(coordinate))
        layout_value = _finite_number_value(layout.get(coordinate))
        if legacy_value is None or layout_value is None:
            continue
        if legacy_value != layout_value:
            result.warnings.append(
                ValidationIssue(
                    "warning",
                    "legacy_layout_conflict",
                    f"Room '{room_id}' legacy {coordinate} differs from layout.{coordinate}.",
                    f"{path}.layout.{coordinate}",
                )
            )

    legacy_z = _finite_number_value(room.get("z"))
    layer_id = layout.get("layer_id")
    layer_z = (
        _finite_number_value(layer_z_by_id.get(str(layer_id)))
        if layer_id is not None
        else None
    )
    if legacy_z is None or layer_z is None or legacy_z == layer_z:
        return
    result.warnings.append(
        ValidationIssue(
            "warning",
            "legacy_layout_conflict",
            f"Room '{room_id}' legacy z differs from layout.layer_id z.",
            f"{path}.layout.layer_id",
        )
    )


def _is_valid_hex_color(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("#"):
        return False
    digits = value[1:]
    return len(digits) in (3, 6) and all(char in HEX_DIGITS for char in digits)


def _finite_number_value(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return numeric


def _string_set(value: Any) -> Set[str]:
    if isinstance(value, set):
        return {str(entry) for entry in value}
    if isinstance(value, list):
        return {str(entry) for entry in value}
    if isinstance(value, tuple):
        return {str(entry) for entry in value}
    return set()


def _validate_items_for_room_refs(
    result: ValidationResult,
    items: Any,
    room_id_set: Iterable[str],
    path: str,
) -> None:
    valid_room_ids = set(room_id_set)
    for index, item in enumerate(_list_value(items)):
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("id") or "")
        item_path = f"{path}.items[{index}]"
        if not item_id:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "missing_item_id",
                    "Item is missing an id.",
                    item_path,
                )
            )
        if not item.get("name"):
            result.errors.append(
                ValidationIssue(
                    "error",
                    "missing_item_name",
                    f"Item '{item_id or '<missing>'}' is missing a name.",
                    f"{item_path}.name",
                )
            )
        room_ref = item.get("room_id")
        if room_ref and room_ref not in valid_room_ids:
            result.errors.append(
                ValidationIssue(
                    "error",
                    "invalid_item_room_ref",
                    f"Item '{item_id}' references missing room_id '{room_ref}'.",
                    f"{item_path}.room_id",
                )
            )
        if item.get("type") == "container_item":
            _validate_items_for_room_refs(
                result,
                item.get("items", []),
                valid_room_ids,
                item_path,
            )


def _validate_hidden_items_for_room_refs(
    result: ValidationResult,
    hidden_items: Any,
    room_id_set: Iterable[str],
    path: str,
) -> None:
    for index, (_, item_data) in enumerate(_hidden_item_entries(hidden_items)):
        _validate_items_for_room_refs(
            result,
            [item_data],
            room_id_set,
            f"{path}.hidden_items[{index}]",
        )


def _reachable_rooms(
    room_entries: Sequence[Tuple[str, str, Mapping[str, Any]]], spawn_room_id: str
) -> set[str]:
    rooms_by_id = {_room_id(room): room for _, _, room in room_entries if _room_id(room)}
    reachable: set[str] = set()
    queue: deque[str] = deque([spawn_room_id])
    while queue:
        room_id = queue.popleft()
        if room_id in reachable:
            continue
        reachable.add(room_id)
        room = rooms_by_id.get(room_id, {})
        exits = room.get("exits", {}) or {}
        if not isinstance(exits, Mapping):
            continue
        for target_room_id in exits.values():
            if target_room_id in rooms_by_id and target_room_id not in reachable:
                queue.append(str(target_room_id))
    return reachable


def _hidden_item_entries(hidden_items: Any) -> List[Tuple[str, Mapping[str, Any]]]:
    if isinstance(hidden_items, Mapping):
        entries = []
        for hidden_id, value in hidden_items.items():
            if isinstance(value, Mapping):
                item_data = value.get("item", value)
                if isinstance(item_data, Mapping):
                    entries.append((str(hidden_id), item_data))
        return entries

    entries = []
    for value in _list_value(hidden_items):
        if not isinstance(value, Mapping):
            continue
        item_data = value.get("item", value)
        if isinstance(item_data, Mapping):
            entries.append((str(value.get("id") or item_data.get("id") or ""), item_data))
    return entries


def _script_entries(world_data: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return [
        script
        for script in _list_value(world_data.get("scripts", []))
        if isinstance(script, Mapping)
    ]


def _resolve_repo_relative_path(repo_root: Path, script_path: str) -> Optional[Path]:
    path = Path(script_path)
    if path.is_absolute() or ".." in path.parts:
        return None
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return resolved


def _resolve_world_script_path(repo_root: Path, script_path: str) -> Optional[Path]:
    resolved = _resolve_repo_relative_path(repo_root, script_path)
    if resolved is None:
        return None
    allowed_root = (repo_root / WORLD_SCRIPT_ROOT).resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        return None
    return resolved


def _json_safe(value: Any) -> Any:
    if callable(value):
        return {
            "unserializable": True,
            "kind": "callable",
            "name": getattr(value, "__name__", value.__class__.__name__),
            "module": getattr(value, "__module__", None),
        }
    if isinstance(value, Mapping):
        return {str(key): _json_safe(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(inner) for inner in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return {
            "unserializable": True,
            "kind": value.__class__.__name__,
            "repr": repr(value),
        }


def _strip_unserializable_markers(value: Any) -> Any:
    if _is_unserializable_marker(value):
        return None
    if isinstance(value, Mapping):
        cleaned: JsonDict = {}
        for key, inner in value.items():
            if _is_unserializable_marker(inner):
                continue
            cleaned_value = _strip_unserializable_markers(inner)
            if cleaned_value is not None:
                cleaned[str(key)] = cleaned_value
        return cleaned
    if isinstance(value, list):
        cleaned_list = []
        for inner in value:
            if _is_unserializable_marker(inner):
                continue
            cleaned_value = _strip_unserializable_markers(inner)
            if cleaned_value is not None:
                cleaned_list.append(cleaned_value)
        return cleaned_list
    return value


def _is_unserializable_marker(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("unserializable") is True
        and "kind" in value
    )


def _set_room_id_if_supported(item: Item, room_id: str) -> None:
    if isinstance(item, StatefulItem) and not item.room_id:
        item.room_id = room_id


def _hidden_item_conditions_by_room(
    rooms: Mapping[str, Room],
) -> Dict[str, Dict[str, Callable[[Any], bool]]]:
    conditions: Dict[str, Dict[str, Callable[[Any], bool]]] = {}
    for room_id, room in rooms.items():
        if not isinstance(room, Room):
            continue
        room_conditions: Dict[str, Callable[[Any], bool]] = {}
        for hidden_id, (_, condition) in room.hidden_items.items():
            if callable(condition):
                room_conditions[str(hidden_id)] = condition
        conditions[str(room_id)] = room_conditions
    return conditions


def _hidden_item_condition(_game_state: Any) -> bool:
    return False


def _list_value(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _run_command(command: Sequence[str], cwd: str) -> subprocess.CompletedProcess[str]:
    argv, env_updates = _split_command_env_assignments(command)
    run_kwargs: JsonDict = {
        "cwd": cwd,
        "text": True,
        "capture_output": True,
        "check": False,
    }
    if env_updates:
        env = os.environ.copy()
        env.update(env_updates)
        run_kwargs["env"] = env
    return subprocess.run(argv, **run_kwargs)


def _split_command_env_assignments(
    command: Sequence[str],
) -> Tuple[List[str], Dict[str, str]]:
    argv = list(command)
    env_updates: Dict[str, str] = {}
    while argv and _is_env_assignment(argv[0]):
        key, value = argv.pop(0).split("=", 1)
        env_updates[key] = value
    return argv, env_updates


def _is_env_assignment(token: str) -> bool:
    if "=" not in token:
        return False
    key, _ = token.split("=", 1)
    if not key or key[0].isdigit():
        return False
    return all(char == "_" or char.isalnum() for char in key)


def _combined_output(completed: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part for part in [completed.stdout, completed.stderr] if part)


def _failed_publish_result(
    step: str, completed: subprocess.CompletedProcess[str]
) -> PublishResult:
    return PublishResult(
        ok=False,
        step=step,
        output=completed.stdout or "",
        error=_combined_output(completed),
    )


__all__ = [
    "PublishResult",
    "ValidationIssue",
    "ValidationResult",
    "WORLD_DATA_VERSION",
    "WorldBuilder",
    "apply_world_data",
    "export_live_world",
    "load_world_data",
    "run_git_publish",
    "save_script_files",
    "save_world_data",
    "validate_world_data",
]
