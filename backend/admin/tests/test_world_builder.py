import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from admin.world_builder import (
    WorldBuilder,
    apply_world_data,
    export_live_world,
    load_world_data,
    run_git_publish,
    save_script_files,
    save_world_data,
    validate_world_data,
)
from managers.game_state import GameState
from managers.mob_definitions import get_mob_definitions
from managers.mob_manager import MobManager
from managers.world import generate_world
from models.ContainerItem import ContainerItem
from models.Item import Item
from models.Mobile import Mobile
from models.Room import Room
from models.StatefulItem import StatefulItem
from models.Weapon import Weapon


def always_true(*_args):
    return True


class WorldBuilderExportTests(unittest.TestCase):
    def test_export_live_world_returns_json_safe_rooms_items_and_mobs(self):
        game_state = GameState()
        spawn = Room(
            "spawn",
            "Spawn",
            "The starting room.",
            exits={"north": "hall"},
            is_outdoor=True,
        )
        hall = Room("hall", "Hall", "A long hallway.", exits={"south": "spawn"})

        key = Item("Iron Key", "key", "A small key.", synonyms=["iron key"])
        sword = Weapon(
            "Sword",
            "sword",
            "A sharp sword.",
            damage=12,
            min_strength=3,
        )
        lever = StatefulItem(
            "Lever",
            "lever",
            "A lever is mounted on the wall.",
            takeable=False,
            state="down",
        )
        lever.add_state_description("up", "The lever is up.")
        lever.add_interaction(
            "pull",
            target_state="up",
            message="The lever clicks.",
            conditional_fn=always_true,
        )
        bag = ContainerItem(
            "Bag",
            "bag",
            "A canvas bag",
            state="closed",
            capacity_limit=2,
            capacity_weight=5,
        )
        bag.add_item(Item("Coin", "coin", "A tarnished coin.", weight=1))

        spawn.add_item(key)
        spawn.add_item(sword)
        spawn.add_item(lever)
        spawn.add_item(bag)
        spawn.add_hidden_item(Item("Gem", "gem", "A hidden gem."), always_true)

        game_state.add_room(spawn)
        game_state.add_room(hall)

        mob_manager = MobManager()
        wolf = Mobile(
            "Wolf",
            "wolf_1",
            "A hungry wolf.",
            aggressive=True,
            patrol_rooms=["spawn", "hall"],
            current_room="spawn",
        )
        mob_manager.mobs[wolf.id] = wolf
        spawn.add_item(wolf)

        data = export_live_world(
            game_state,
            mob_manager,
            spawn_room_id="spawn",
            metadata={"source": "unit-test"},
        )

        json.dumps(data)
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["spawn_room_id"], "spawn")
        self.assertEqual(data["metadata"]["source"], "unit-test")
        self.assertEqual([room["id"] for room in data["rooms"]], ["spawn", "hall"])

        exported_spawn = data["rooms"][0]
        item_types = {item["id"]: item["type"] for item in exported_spawn["items"]}
        self.assertEqual(item_types["key"], "item")
        self.assertEqual(item_types["sword"], "weapon")
        self.assertEqual(item_types["lever"], "stateful_item")
        self.assertEqual(item_types["bag"], "container_item")
        self.assertNotIn("wolf_1", item_types)

        exported_lever = next(
            item for item in exported_spawn["items"] if item["id"] == "lever"
        )
        marker = exported_lever["interactions"]["pull"][0]["conditional_fn"]
        self.assertTrue(marker["unserializable"])
        self.assertEqual(marker["kind"], "callable")
        self.assertEqual(marker["name"], "always_true")

        self.assertEqual(exported_spawn["hidden_items"][0]["id"], "gem")
        self.assertTrue(exported_spawn["hidden_items"][0]["condition"]["unserializable"])

        self.assertEqual(len(data["mobs"]), 1)
        self.assertEqual(data["mobs"][0]["id"], "wolf_1")
        self.assertEqual(data["mobs"][0]["type"], "mobile")

    def test_export_live_world_includes_editor_layout_defaults(self):
        game_state = GameState()
        game_state.add_room(Room("spawn", "Spawn", "The starting room."))
        game_state.add_room(Room("hall", "Hall", "A long hallway."))

        data = export_live_world(game_state, spawn_room_id="spawn")

        self.assertEqual(
            data["regions"],
            [{"id": "world", "name": "World", "color": "#8b5a3c"}],
        )
        self.assertEqual(
            data["layers"],
            [{"id": "surface", "name": "Surface", "z": 0, "visible": True}],
        )
        self.assertEqual(data["layout"]["default_layer_id"], "surface")
        self.assertEqual(data["rooms"][0]["x"], 120)
        self.assertEqual(data["rooms"][0]["y"], 110)
        self.assertEqual(
            data["rooms"][0]["layout"],
            {"x": 120, "y": 110, "layer_id": "surface", "pinned": True},
        )
        self.assertEqual(data["rooms"][1]["x"], 270)
        self.assertEqual(data["rooms"][1]["layout"]["x"], 270)


class WorldBuilderGeneratedWorldTests(unittest.TestCase):
    def test_generated_world_exports_without_validation_errors(self):
        game_state = GameState()
        mob_manager = MobManager()
        mob_manager.load_mob_definitions(get_mob_definitions())

        for room in generate_world(mob_manager=mob_manager).values():
            game_state.add_room(room)

        world_data = export_live_world(
            game_state,
            mob_manager,
            spawn_room_id="square",
        )
        validation = validate_world_data(world_data, spawn_room_id="square")

        self.assertEqual([], [issue.to_dict() for issue in validation.errors])


class WorldBuilderValidationTests(unittest.TestCase):
    def test_validate_world_data_reports_errors_and_unreachable_warnings(self):
        data = {
            "version": 1,
            "spawn_room_id": "spawn",
            "rooms": [
                {
                    "id": "spawn",
                    "name": "Spawn",
                    "description": "Start.",
                    "exits": {"north": "missing"},
                    "items": [
                        {
                            "id": "bad_item",
                            "name": "Bad Item",
                            "description": "Invalid room ref.",
                            "room_id": "missing",
                        }
                    ],
                },
                {"id": "spawn", "name": "Duplicate", "description": "Dup."},
                {"id": "", "name": "", "description": "Missing id and name."},
                {"id": "island", "name": "Island", "description": "Cut off."},
            ],
            "mobs": [
                {
                    "id": "bad_mob",
                    "name": "Bad Mob",
                    "description": "Nowhere.",
                    "current_room": "missing",
                    "patrol_rooms": ["spawn", "missing"],
                }
            ],
        }

        result = validate_world_data(data)

        self.assertFalse(result.ok)
        error_codes = {issue.code for issue in result.errors}
        warning_codes = {issue.code for issue in result.warnings}
        self.assertIn("duplicate_room_id", error_codes)
        self.assertIn("missing_room_id", error_codes)
        self.assertIn("missing_room_name", error_codes)
        self.assertIn("broken_exit", error_codes)
        self.assertIn("invalid_item_room_ref", error_codes)
        self.assertIn("invalid_mob_room_ref", error_codes)
        self.assertIn("invalid_mob_patrol_ref", error_codes)
        self.assertIn("unreachable_room", warning_codes)
        self.assertIn("errors", result.to_dict())
        self.assertIn("warnings", result.to_dict())

    def test_validate_world_data_accepts_room_maps_and_missing_spawn_without_warning(self):
        data = {
            "version": 1,
            "rooms": {
                "spawn": {
                    "name": "Spawn",
                    "description": "Start.",
                    "exits": {"east": "hall"},
                },
                "hall": {
                    "name": "Hall",
                    "description": "A hall.",
                    "exits": {"west": "spawn"},
                },
            },
            "mobs": [],
        }

        result = validate_world_data(data)

        self.assertTrue(result.ok)
        self.assertEqual(result.warnings, [])

    def test_validate_world_data_reports_invalid_script_paths_and_room_refs(self):
        data = {
            "version": 1,
            "rooms": [{"id": "spawn", "name": "Spawn", "description": "Start."}],
            "scripts": [
                {
                    "id": "bad_path",
                    "path": "../outside.py",
                    "content": "def run():\n    pass\n",
                    "room_id": "spawn",
                },
                {
                    "id": "bad_room",
                    "path": "backend/world_scripts/bad_room.py",
                    "content": "def run():\n    pass\n",
                    "room_id": "missing",
                },
                {
                    "id": "bad_repo_file",
                    "path": "backend/socket_server.py",
                    "content": "def run():\n    pass\n",
                    "room_id": "spawn",
                },
            ],
        }

        result = validate_world_data(data)

        self.assertFalse(result.ok)
        self.assertIn("invalid_script_path", {issue.code for issue in result.errors})
        self.assertIn("invalid_script_room_ref", {issue.code for issue in result.errors})

    def test_validate_world_data_accepts_authoring_metadata(self):
        data = {
            "version": 1,
            "spawn_room_id": "spawn",
            "regions": [
                {
                    "id": "village",
                    "name": "Village",
                    "color": "#4f8fba",
                    "parent_region_id": None,
                }
            ],
            "layers": [
                {
                    "id": "surface",
                    "name": "Surface",
                    "z": 0,
                    "visible": True,
                    "region_id": "village",
                }
            ],
            "tags": [
                {
                    "id": "safe",
                    "label": "Safe",
                    "color": "#4f8fba",
                    "scope": ["room"],
                }
            ],
            "layout": {
                "grid_size": 24,
                "snap_to_grid": True,
                "default_layer_id": "surface",
            },
            "rooms": [
                {
                    "id": "spawn",
                    "name": "Spawn",
                    "description": "Start.",
                    "region_id": "village",
                    "tags": ["safe"],
                    "x": 120,
                    "y": 160,
                    "z": 0,
                    "layout": {
                        "x": 120.0,
                        "y": 160.0,
                        "layer_id": "surface",
                        "pinned": True,
                    },
                }
            ],
            "mobs": [],
        }

        result = validate_world_data(data)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual([], result.warnings)

    def test_validate_world_data_reports_invalid_authoring_metadata_refs(self):
        data = {
            "version": 1,
            "regions": [
                {"id": "village", "name": "Village", "color": "blue"},
                {"id": "village", "name": "Duplicate Village"},
                {
                    "id": "loop_a",
                    "name": "Loop A",
                    "parent_region_id": "loop_b",
                },
                {
                    "id": "loop_b",
                    "name": "Loop B",
                    "parent_region_id": "loop_a",
                },
                {
                    "id": "orphan",
                    "name": "Orphan",
                    "parent_region_id": "missing_region",
                },
            ],
            "layers": [
                {
                    "id": "surface",
                    "name": "Surface",
                    "region_id": "missing_region",
                    "color": "not-a-hex-color",
                },
                {"id": "surface", "name": "Duplicate Surface"},
            ],
            "tags": [
                {"id": "safe", "label": "Safe", "color": "bad-color"},
                {"id": "safe", "label": "Duplicate Safe"},
            ],
            "layout": {"default_layer_id": "missing_layer"},
            "rooms": [
                {
                    "id": "spawn",
                    "name": "Spawn",
                    "description": "Start.",
                    "region_id": "missing_region",
                    "tags": ["safe", "missing_tag"],
                    "layout": {
                        "x": float("inf"),
                        "y": "east",
                        "layer_id": "missing_layer",
                    },
                }
            ],
            "mobs": [],
        }

        result = validate_world_data(data)

        self.assertFalse(result.ok)
        error_codes = {issue.code for issue in result.errors}
        self.assertIn("duplicate_region_id", error_codes)
        self.assertIn("duplicate_layer_id", error_codes)
        self.assertIn("duplicate_tag_id", error_codes)
        self.assertIn("invalid_region_color", error_codes)
        self.assertIn("invalid_layer_color", error_codes)
        self.assertIn("invalid_tag_color", error_codes)
        self.assertIn("invalid_region_parent_ref", error_codes)
        self.assertIn("region_parent_cycle", error_codes)
        self.assertIn("invalid_layer_region_ref", error_codes)
        self.assertIn("invalid_layout_default_layer_ref", error_codes)
        self.assertIn("invalid_room_region_ref", error_codes)
        self.assertIn("invalid_room_tag_ref", error_codes)
        self.assertIn("invalid_room_layer_ref", error_codes)
        self.assertIn("invalid_room_layout_coordinate", error_codes)

    def test_validate_world_data_warns_when_legacy_coordinates_conflict_with_layout(self):
        data = {
            "version": 1,
            "regions": [{"id": "village", "name": "Village"}],
            "layers": [
                {"id": "surface", "name": "Surface", "z": 1, "region_id": "village"}
            ],
            "layout": {"default_layer_id": "surface"},
            "rooms": [
                {
                    "id": "spawn",
                    "name": "Spawn",
                    "description": "Start.",
                    "x": 10,
                    "y": 20,
                    "z": 0,
                    "layout": {"x": 11, "y": 25, "layer_id": "surface"},
                }
            ],
            "mobs": [],
        }

        result = validate_world_data(data)

        self.assertTrue(result.ok, result.to_dict())
        conflicts = [
            issue
            for issue in result.warnings
            if issue.code == "legacy_layout_conflict"
        ]
        self.assertEqual(3, len(conflicts), result.to_dict())


class WorldBuilderPersistenceTests(unittest.TestCase):
    def test_save_and_load_world_data_round_trips_json(self):
        data = {
            "version": 1,
            "spawn_room_id": "spawn",
            "rooms": [{"id": "spawn", "name": "Spawn", "description": "Start."}],
            "mobs": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "world.json"

            save_world_data(data, path)
            loaded = load_world_data(path)

        self.assertEqual(loaded, data)

    def test_save_script_files_writes_relative_script_content_under_repo(self):
        data = {
            "version": 1,
            "rooms": [{"id": "spawn", "name": "Spawn", "description": "Start."}],
            "scripts": [
                {
                    "id": "welcome",
                    "path": "backend/world_scripts/welcome.py",
                    "content": "def run():\n    return 'hello'\n",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            written = save_script_files(data, tmpdir)
            script_path = Path(tmpdir) / "backend/world_scripts/welcome.py"

            self.assertEqual(written, [script_path.resolve()])
            self.assertEqual(script_path.read_text(), "def run():\n    return 'hello'\n")

    def test_save_script_files_skips_paths_outside_world_scripts(self):
        data = {
            "version": 1,
            "rooms": [{"id": "spawn", "name": "Spawn", "description": "Start."}],
            "scripts": [
                {
                    "id": "unsafe",
                    "path": "backend/socket_server.py",
                    "content": "print('owned')\n",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            written = save_script_files(data, tmpdir)

            self.assertEqual(written, [])
            self.assertFalse((Path(tmpdir) / "backend/socket_server.py").exists())


class WorldBuilderApplyTests(unittest.TestCase):
    def test_apply_world_data_replaces_rooms_and_mobs_with_model_instances(self):
        data = {
            "version": 1,
            "spawn_room_id": "spawn",
            "rooms": [
                {
                    "id": "spawn",
                    "name": "Spawn",
                    "description": "Start.",
                    "exits": {"north": "hall"},
                    "is_dark": True,
                    "items": [
                        {
                            "type": "item",
                            "id": "key",
                            "name": "Key",
                            "description": "A key.",
                            "weight": 1,
                            "value": 2,
                            "takeable": True,
                        },
                        {
                            "type": "weapon",
                            "id": "sword",
                            "name": "Sword",
                            "description": "Sharp.",
                            "damage": 9,
                        },
                        {
                            "type": "stateful_item",
                            "id": "door",
                            "name": "Door",
                            "description": "Closed.",
                            "takeable": False,
                            "state": "closed",
                            "state_descriptions": {
                                "closed": "Closed.",
                                "open": "Open.",
                            },
                            "interactions": {
                                "open": [
                                    {
                                        "target_state": "open",
                                        "message": "Opened.",
                                        "conditional_fn": {
                                            "unserializable": True,
                                            "kind": "callable",
                                            "name": "legacy_check",
                                        },
                                        "effect_fn": {
                                            "unserializable": True,
                                            "kind": "callable",
                                            "name": "legacy_effect",
                                        },
                                    }
                                ]
                            },
                            "linked_items": ["other_door"],
                        },
                        {
                            "type": "container_item",
                            "id": "bag",
                            "name": "Bag",
                            "description": "Bag.",
                            "state": "open",
                            "capacity_limit": 3,
                            "capacity_weight": 10,
                            "items": [
                                {
                                    "type": "item",
                                    "id": "coin",
                                    "name": "Coin",
                                    "description": "A coin.",
                                }
                            ],
                        },
                    ],
                },
                {
                    "id": "hall",
                    "name": "Hall",
                    "description": "Hall.",
                    "exits": {"south": "spawn"},
                },
            ],
            "mobs": [
                {
                    "type": "mobile",
                    "id": "wolf_1",
                    "name": "Wolf",
                    "description": "A wolf.",
                    "strength": 7,
                    "dexterity": 8,
                    "max_stamina": 30,
                    "stamina": 20,
                    "damage": 4,
                    "aggressive": True,
                    "patrol_rooms": ["spawn", "hall"],
                    "current_room": "spawn",
                }
            ],
        }
        game_state = GameState()
        game_state.add_room(Room("old", "Old", "Old."))
        mob_manager = MobManager()
        mob_manager.mobs["old_mob"] = Mobile("Old Mob", "old_mob", "Old.")

        result = apply_world_data(data, game_state, mob_manager)

        self.assertTrue(result.ok)
        self.assertEqual(set(game_state.rooms), {"spawn", "hall"})
        spawn = game_state.rooms["spawn"]
        self.assertTrue(spawn.is_dark)
        self.assertIsInstance(spawn.items[0], Item)
        self.assertIsInstance(spawn.items[1], Weapon)
        self.assertIsInstance(spawn.items[2], StatefulItem)
        self.assertIsInstance(spawn.items[3], ContainerItem)
        self.assertEqual(spawn.items[1].damage, 9)
        self.assertEqual(spawn.items[2].linked_items, ["other_door"])
        self.assertNotIn("conditional_fn", spawn.items[2].interactions["open"][0])
        self.assertNotIn("effect_fn", spawn.items[2].interactions["open"][0])
        self.assertEqual(spawn.items[3].items[0].id, "coin")
        self.assertEqual(set(mob_manager.mobs), {"wolf_1"})
        self.assertIsInstance(mob_manager.mobs["wolf_1"], Mobile)
        self.assertIn(mob_manager.mobs["wolf_1"], spawn.items)

    def test_apply_world_data_does_not_mutate_runtime_when_validation_fails(self):
        game_state = GameState()
        game_state.add_room(Room("old", "Old", "Old."))

        result = apply_world_data(
            {
                "version": 1,
                "spawn_room_id": "spawn",
                "rooms": [
                    {
                        "id": "spawn",
                        "name": "Spawn",
                        "description": "Start.",
                        "exits": {"north": "missing"},
                    }
                ],
                "mobs": [],
            },
            game_state,
        )

        self.assertFalse(result.ok)
        self.assertEqual(set(game_state.rooms), {"old"})

    def test_apply_world_data_preserves_existing_hidden_item_conditions(self):
        game_state = GameState()
        spawn = Room("spawn", "Spawn", "Start.")

        def existing_condition(_game_state):
            return True

        spawn.add_hidden_item(Item("Gem", "gem", "A hidden gem."), existing_condition)
        game_state.add_room(spawn)
        data = export_live_world(game_state, spawn_room_id="spawn")

        result = apply_world_data(data, game_state)

        self.assertTrue(result.ok)
        applied_spawn = game_state.rooms["spawn"]
        self.assertIn("gem", applied_spawn.hidden_items)
        self.assertIs(applied_spawn.hidden_items["gem"][1], existing_condition)
        self.assertEqual(
            [item.id for item in applied_spawn.get_items(game_state)],
            ["gem"],
        )


class WorldBuilderPublishTests(unittest.TestCase):
    @patch("admin.world_builder.subprocess.run")
    def test_run_git_publish_saves_valid_world_runs_checks_commits_and_pushes(
        self, run_mock
    ):
        run_mock.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        data = {
            "version": 1,
            "spawn_room_id": "spawn",
            "rooms": [{"id": "spawn", "name": "Spawn", "description": "Start."}],
            "mobs": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "world.json"
            result = run_git_publish(
                data,
                path,
                repo_path=tmpdir,
                message="Publish test world",
                checks=[["python3", "-m", "unittest", "backend.admin.tests.test_world_builder"]],
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.step, "push")
        self.assertEqual(
            run_mock.call_args_list,
            [
                call(
                    ["python3", "-m", "unittest", "backend.admin.tests.test_world_builder"],
                    cwd=tmpdir,
                    text=True,
                    capture_output=True,
                    check=False,
                ),
                call(
                    ["git", "add", str(path)],
                    cwd=tmpdir,
                    text=True,
                    capture_output=True,
                    check=False,
                ),
                call(
                    ["git", "commit", "-m", "Publish test world"],
                    cwd=tmpdir,
                    text=True,
                    capture_output=True,
                    check=False,
                ),
                call(
                    ["git", "push"],
                    cwd=tmpdir,
                    text=True,
                    capture_output=True,
                    check=False,
                ),
            ],
        )

    @patch("admin.world_builder.subprocess.run")
    def test_run_git_publish_adds_script_files_with_world_data(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        data = {
            "version": 1,
            "spawn_room_id": "spawn",
            "rooms": [{"id": "spawn", "name": "Spawn", "description": "Start."}],
            "scripts": [
                {
                    "id": "welcome",
                    "path": "backend/world_scripts/welcome.py",
                    "content": "def run():\n    return 'hello'\n",
                }
            ],
            "mobs": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "world.json"
            result = run_git_publish(data, path, repo_path=tmpdir)
            script_path = (Path(tmpdir) / "backend/world_scripts/welcome.py").resolve()

        self.assertTrue(result.ok)
        self.assertIn(
            call(
                ["git", "add", str(path), str(script_path)],
                cwd=tmpdir,
                text=True,
                capture_output=True,
                check=False,
            ),
            run_mock.call_args_list,
        )

    @patch("admin.world_builder.subprocess.run")
    def test_run_git_publish_fails_closed_when_a_check_fails(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="failed"
        )
        data = {
            "version": 1,
            "spawn_room_id": "spawn",
            "rooms": [{"id": "spawn", "name": "Spawn", "description": "Start."}],
            "mobs": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_git_publish(
                data,
                Path(tmpdir) / "world.json",
                repo_path=tmpdir,
                checks=[["false"]],
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.step, "check")
        self.assertIn("failed", result.error)
        self.assertEqual(run_mock.call_count, 1)

    @patch("admin.world_builder.subprocess.run")
    def test_run_git_publish_parses_env_assignments_in_publish_checks(
        self, run_mock
    ):
        run_mock.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        data = {
            "version": 1,
            "spawn_room_id": "spawn",
            "rooms": [{"id": "spawn", "name": "Spawn", "description": "Start."}],
            "mobs": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_git_publish(
                data,
                Path(tmpdir) / "world.json",
                repo_path=tmpdir,
                checks=[
                    [
                        "PYTHONPATH=backend",
                        "python3",
                        "-m",
                        "unittest",
                        "backend.admin.tests.test_world_builder",
                    ]
                ],
            )

        self.assertTrue(result.ok)
        first_call = run_mock.call_args_list[0]
        self.assertEqual(
            [
                "python3",
                "-m",
                "unittest",
                "backend.admin.tests.test_world_builder",
            ],
            first_call.args[0],
        )
        self.assertEqual("backend", first_call.kwargs["env"]["PYTHONPATH"])


class WorldBuilderFacadeTests(unittest.TestCase):
    def test_world_builder_facade_loads_saved_data_or_exports_current_world(self):
        game_state = GameState()
        game_state.add_room(Room("spawn", "Spawn", "Start."))
        mob_manager = MobManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "world.json"
            builder = WorldBuilder(
                game_state=game_state,
                mob_manager=mob_manager,
                data_path=path,
                repo_path=tmpdir,
                spawn_room_id="spawn",
            )
            exported = builder.load_or_export()
            self.assertEqual(exported["rooms"][0]["id"], "spawn")

            saved = {
                "version": 1,
                "spawn_room_id": "spawn",
                "rooms": [
                    {
                        "id": "saved",
                        "name": "Saved",
                        "description": "Saved.",
                    }
                ],
                "mobs": [],
            }
            builder.save(saved)
            script_data = {
                **saved,
                "scripts": [
                    {
                        "id": "script",
                        "path": "backend/world_scripts/script.py",
                        "content": "VALUE = 1\n",
                    }
                ],
            }
            builder.save(script_data)
            loaded = builder.load_or_export()

        self.assertEqual(loaded["rooms"][0]["id"], "saved")

    def test_draft_store_migrates_legacy_draft_and_saves_independent_drafts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "world_builder"
            legacy_path = root / "draft_world.json"
            save_world_data(
                {"version": 1, "rooms": [{"id": "legacy"}], "mobs": []},
                legacy_path,
            )
            builder = WorldBuilder(
                game_state=GameState(),
                mob_manager=MobManager(),
                data_path=legacy_path,
                repo_path=tmpdir,
                spawn_room_id="legacy",
            )

            manifest = builder.list_drafts()
            self.assertEqual(manifest["active_draft_id"], "current-draft")
            self.assertEqual(manifest["drafts"][0]["name"], "Current Draft")
            self.assertEqual(builder.load_draft("current-draft")["rooms"][0]["id"], "legacy")

            created = builder.create_draft(name="Experiment", source="active")
            draft_id = created["draft"]["id"]
            builder.save_draft(
                draft_id,
                {"version": 1, "rooms": [{"id": "experiment"}], "mobs": []},
            )

            self.assertEqual(builder.load_draft("current-draft")["rooms"][0]["id"], "legacy")
            self.assertEqual(builder.load_draft(draft_id)["rooms"][0]["id"], "experiment")
            self.assertEqual(builder.list_drafts()["active_draft_id"], "current-draft")

    def test_draft_store_creates_from_live_and_rejects_unsafe_ids(self):
        game_state = GameState()
        game_state.add_room(Room("live-room", "Live Room", "Live."))

        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_path = Path(tmpdir) / "world_builder" / "draft_world.json"
            builder = WorldBuilder(
                game_state=game_state,
                mob_manager=MobManager(),
                data_path=legacy_path,
                repo_path=tmpdir,
                spawn_room_id="live-room",
            )

            created = builder.create_draft(name="Live Copy", source="live")

            self.assertEqual(created["draft"]["id"], "live-copy")
            self.assertEqual(created["world"]["rooms"][0]["id"], "live-room")
            with self.assertRaises(KeyError):
                builder.load_draft("../bad")

    def test_draft_store_rename_activate_and_delete_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_path = Path(tmpdir) / "world_builder" / "draft_world.json"
            builder = WorldBuilder(
                game_state=GameState(),
                mob_manager=MobManager(),
                data_path=legacy_path,
                repo_path=tmpdir,
                spawn_room_id="square",
            )
            first = builder.create_draft(name="First", source="live")["draft"]["id"]
            second = builder.create_draft(name="Second", source_draft_id=first)["draft"]["id"]

            renamed = builder.rename_draft(first, name="Renamed", description="New desc")
            self.assertEqual(renamed["draft"]["name"], "Renamed")
            self.assertEqual(renamed["draft"]["description"], "New desc")

            activated = builder.activate_draft(second)
            self.assertEqual(activated["active_draft_id"], second)
            deleted = builder.delete_draft(second)

            self.assertNotEqual(deleted["active_draft_id"], second)
            self.assertTrue(any(draft["id"] == first for draft in deleted["drafts"]))

    def test_reset_selected_draft_from_baseline_does_not_mutate_runtime(self):
        game_state = GameState()
        game_state.add_room(Room("live", "Live", "Runtime room."))

        def baseline_factory():
            return {"baseline": Room("baseline", "Baseline", "Generated room.")}

        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_path = Path(tmpdir) / "world_builder" / "draft_world.json"
            builder = WorldBuilder(
                game_state=game_state,
                mob_manager=None,
                data_path=legacy_path,
                repo_path=tmpdir,
                spawn_room_id="baseline",
            )
            draft_id = builder.create_draft(name="Experiment", source="live")["draft"]["id"]

            result = builder.reset_draft_from_baseline(draft_id, baseline_factory)

            self.assertEqual(result["world"]["rooms"][0]["id"], "baseline")
            self.assertEqual(builder.load_draft(draft_id)["rooms"][0]["id"], "baseline")
            self.assertEqual(list(game_state.rooms.keys()), ["live"])

    @patch("admin.world_builder.run_git_publish")
    def test_apply_and_publish_selected_draft_save_that_draft(self, publish_mock):
        publish_mock.return_value = {"ok": True, "step": "push"}
        game_state = GameState()

        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_path = Path(tmpdir) / "world_builder" / "draft_world.json"
            builder = WorldBuilder(
                game_state=game_state,
                mob_manager=MobManager(),
                data_path=legacy_path,
                repo_path=tmpdir,
                spawn_room_id="square",
            )
            draft_id = builder.create_draft(name="Experiment", source="live")["draft"]["id"]
            world = {"version": 1, "rooms": [{"id": "experiment", "name": "Experiment"}], "mobs": []}

            apply_result = builder.apply_draft(draft_id, world)
            publish_result = builder.publish_draft(draft_id, world, checks=[["python3", "-V"]])

            self.assertTrue(apply_result.ok)
            self.assertEqual(game_state.rooms["experiment"].name, "Experiment")
            self.assertEqual(builder.load_draft(draft_id)["rooms"][0]["id"], "experiment")
            self.assertEqual(publish_result["ok"], True)
            publish_mock.assert_called_once()
            self.assertEqual(publish_mock.call_args.args[0]["rooms"][0]["id"], "experiment")


if __name__ == "__main__":
    unittest.main()
