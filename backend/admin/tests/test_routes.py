import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from admin.routes import (
    AdminRouteController,
    _serialize_mob_definition,
    create_admin_token,
    is_admin_session,
)


class FakeRequest:
    def __init__(self, headers=None, payload=None, match_info=None):
        self.headers = headers or {}
        self._payload = payload
        self.match_info = match_info or {}

    async def json(self):
        if self._payload is None:
            raise json.JSONDecodeError("missing", "", 0)
        return self._payload


class FakeWorldBuilder:
    def __init__(self):
        self.world_data = {"version": 1, "rooms": []}
        self.validation = {"ok": True, "errors": [], "warnings": []}
        self.saved = None
        self.applied = None
        self.reset_called = False
        self.published = None
        self.active_draft_id = "main"
        self.drafts = [
            {
                "id": "main",
                "name": "Main Draft",
                "source": "test",
                "created_at": "2026-06-01T20:00:00Z",
                "updated_at": "2026-06-01T20:00:00Z",
                "room_count": 0,
                "description": "",
            }
        ]
        self.draft_worlds = {"main": self.world_data}

    def load_or_export(self):
        return self.world_data

    def save(self, world_data):
        self.saved = world_data
        return {"path": "storage/world_builder/draft_world.json"}

    def validate(self, world_data, spawn_room=None):
        return self.validation

    def apply(self, world_data):
        self.applied = world_data
        return self.validation

    def reset_from_baseline(self, world_factory):
        self.reset_called = True
        self.world_data = {"version": 1, "rooms": [{"id": "square"}]}
        return self.world_data

    def reset_draft_from_baseline(self, draft_id, world_factory):
        if draft_id not in self.draft_worlds:
            raise KeyError(draft_id)
        self.reset_called = True
        self.draft_worlds[draft_id] = {
            "version": 1,
            "rooms": [{"id": "draft-baseline"}],
            "mobs": [],
        }
        return {
            "world": self.draft_worlds[draft_id],
            "saved": {
                "path": f"storage/world_builder/drafts/{draft_id}.json",
                "draft": next(
                    draft for draft in self.drafts if draft["id"] == draft_id
                ),
                "manifest": self.list_drafts(),
            },
        }

    def publish(self, world_data, checks=None, message=None):
        self.published = {"world_data": world_data, "checks": checks or []}
        return {"committed": True, "pushed": True, "commit": "abc123"}

    def list_drafts(self):
        return {"active_draft_id": self.active_draft_id, "drafts": self.drafts}

    def create_draft(
        self, *, name, source="active", source_draft_id=None, description=""
    ):
        draft_id = name.lower().replace(" ", "-")
        draft = {
            "id": draft_id,
            "name": name,
            "source": source,
            "created_at": "2026-06-01T20:10:00Z",
            "updated_at": "2026-06-01T20:10:00Z",
            "room_count": 0,
            "description": description,
        }
        self.drafts.append(draft)
        self.draft_worlds[draft_id] = dict(self.world_data)
        return {
            "draft": draft,
            "world": self.draft_worlds[draft_id],
            "manifest": self.list_drafts(),
        }

    def load_draft(self, draft_id):
        if draft_id not in self.draft_worlds:
            raise KeyError(draft_id)
        draft = next(draft for draft in self.drafts if draft["id"] == draft_id)
        return {"world": self.draft_worlds[draft_id], "draft": draft}

    def save_draft(self, draft_id, world_data):
        if draft_id not in self.draft_worlds:
            raise KeyError(draft_id)
        self.saved = world_data
        self.draft_worlds[draft_id] = world_data
        return {"path": f"storage/world_builder/drafts/{draft_id}.json"}

    def rename_draft(self, draft_id, *, name=None, description=None):
        if draft_id not in self.draft_worlds:
            raise KeyError(draft_id)
        draft = next(draft for draft in self.drafts if draft["id"] == draft_id)
        if name is not None:
            draft["name"] = name
        if description is not None:
            draft["description"] = description
        return {"draft": draft, "manifest": self.list_drafts()}

    def delete_draft(self, draft_id):
        if draft_id not in self.draft_worlds:
            raise KeyError(draft_id)
        del self.draft_worlds[draft_id]
        self.drafts = [draft for draft in self.drafts if draft["id"] != draft_id]
        if self.active_draft_id == draft_id and self.drafts:
            self.active_draft_id = self.drafts[0]["id"]
        return self.list_drafts()

    def activate_draft(self, draft_id):
        if draft_id not in self.draft_worlds:
            raise KeyError(draft_id)
        self.active_draft_id = draft_id
        return self.list_drafts()

    def apply_draft(self, draft_id, world_data):
        self.save_draft(draft_id, world_data)
        self.applied = world_data
        return self.validation

    def publish_draft(self, draft_id, world_data, checks=None, message=None):
        self.save_draft(draft_id, world_data)
        self.published = {"world_data": world_data, "checks": checks or []}
        return {"ok": True, "step": "push"}


class AdminRouteControllerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.player = SimpleNamespace(name="Stupidgem")
        self.sessions = {"sid1": {"player": self.player, "admin_token": "token-123"}}
        self.builder = FakeWorldBuilder()
        self.controller = AdminRouteController(
            game_state=SimpleNamespace(rooms={}),
            mob_manager=SimpleNamespace(mobs={}),
            online_sessions=self.sessions,
            world_builder=self.builder,
            world_factory=Mock(return_value={}),
        )

    def request(self, payload=None):
        return FakeRequest(
            headers={"Authorization": "Bearer token-123"},
            payload=payload,
        )

    def decode(self, response):
        return json.loads(response.text)

    def test_is_admin_session_requires_hardcoded_admin_name(self):
        self.assertTrue(is_admin_session({"player": SimpleNamespace(name="stupidgem")}))
        self.assertFalse(is_admin_session({"player": SimpleNamespace(name="other")}))
        self.assertFalse(is_admin_session({}))

    def test_create_admin_token_returns_distinct_values(self):
        self.assertNotEqual(create_admin_token(), create_admin_token())

    async def test_get_world_rejects_missing_admin_token(self):
        response = await self.controller.get_world(FakeRequest())

        self.assertEqual(response.status, 401)
        self.assertEqual(self.decode(response)["error"], "unauthorized")

    async def test_get_world_returns_world_for_admin_token(self):
        response = await self.controller.get_world(self.request())

        self.assertEqual(response.status, 200)
        self.assertEqual(self.decode(response)["world"], self.builder.world_data)

    async def test_session_reports_admin_for_valid_token(self):
        response = await self.controller.session(self.request())

        self.assertEqual(response.status, 200)
        self.assertEqual(self.decode(response), {"admin": True, "player": "Stupidgem"})

    async def test_session_reports_non_admin_without_valid_token(self):
        response = await self.controller.session(FakeRequest())

        self.assertEqual(response.status, 200)
        self.assertEqual(self.decode(response), {"admin": False})

    async def test_save_world_rejects_invalid_json(self):
        response = await self.controller.save_world(
            FakeRequest(headers={"Authorization": "Bearer token-123"})
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(self.decode(response)["error"], "invalid_json")

    async def test_save_world_rejects_missing_world_object(self):
        response = await self.controller.save_world(self.request({"rooms": []}))

        self.assertEqual(response.status, 400)
        self.assertEqual(self.decode(response)["error"], "invalid_world")

    async def test_save_world_validates_and_saves_payload(self):
        payload = {"world": {"version": 1, "rooms": [{"id": "square"}]}}

        response = await self.controller.save_world(self.request(payload))

        self.assertEqual(response.status, 200)
        body = self.decode(response)
        self.assertEqual(body["validation"]["ok"], True)
        self.assertEqual(self.builder.saved, payload["world"])

    async def test_save_world_rejects_validation_errors(self):
        self.builder.validation = {
            "ok": False,
            "errors": [{"code": "broken_exit", "message": "bad"}],
            "warnings": [],
        }

        response = await self.controller.save_world(
            self.request({"world": {"version": 1, "rooms": []}})
        )

        self.assertEqual(response.status, 400)
        self.assertIsNone(self.builder.saved)
        self.assertEqual(self.decode(response)["error"], "validation_failed")

    async def test_validate_world_returns_validation_result(self):
        response = await self.controller.validate_world(
            self.request({"world": {"version": 1, "rooms": []}})
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(self.decode(response)["validation"], self.builder.validation)

    async def test_apply_world_validates_saves_and_applies(self):
        world = {"version": 1, "rooms": [{"id": "square"}]}

        response = await self.controller.apply_world(self.request({"world": world}))

        self.assertEqual(response.status, 200)
        self.assertEqual(self.builder.saved, world)
        self.assertEqual(self.builder.applied, world)
        self.assertEqual(self.decode(response)["applied"]["rooms"], 1)

    async def test_reset_world_uses_baseline_factory(self):
        response = await self.controller.reset_world(self.request())

        self.assertEqual(response.status, 200)
        self.assertTrue(self.builder.reset_called)
        self.assertEqual(self.decode(response)["world"]["rooms"][0]["id"], "square")

    async def test_publish_world_validates_saves_and_publishes(self):
        world = {"version": 1, "rooms": [{"id": "square"}]}

        response = await self.controller.publish_world(self.request({"world": world}))

        self.assertEqual(response.status, 200)
        self.assertEqual(self.builder.saved, world)
        self.assertEqual(self.builder.published["world_data"], world)
        self.assertTrue(self.decode(response)["publish"]["pushed"])

    async def test_publish_world_returns_error_when_publish_fails(self):
        world = {"version": 1, "rooms": [{"id": "square"}]}
        self.builder.publish = Mock(
            return_value={
                "ok": False,
                "step": "check",
                "error": "tests failed",
                "output": "",
            }
        )

        response = await self.controller.publish_world(self.request({"world": world}))

        self.assertEqual(response.status, 500)
        body = self.decode(response)
        self.assertEqual(body["error"], "publish_failed")
        self.assertEqual(body["message"], "tests failed")
        self.assertFalse(body["publish"]["ok"])

    async def test_draft_routes_create_load_save_and_activate(self):
        response = await self.controller.list_world_drafts(self.request())
        self.assertEqual(response.status, 200)
        self.assertEqual(self.decode(response)["active_draft_id"], "main")

        create = await self.controller.create_world_draft(
            self.request({"name": "Experiment", "source": "active"})
        )
        self.assertEqual(create.status, 200)
        draft_id = self.decode(create)["draft"]["id"]

        load = await self.controller.get_world_draft(self.request(), draft_id)
        self.assertEqual(load.status, 200)
        self.assertEqual(self.decode(load)["draft"]["id"], draft_id)

        world = {"version": 1, "rooms": [{"id": "experiment"}], "mobs": []}
        save = await self.controller.save_world_draft(
            self.request({"world": world}), draft_id
        )
        self.assertEqual(save.status, 200)
        self.assertEqual(self.builder.saved, world)

        rename = await self.controller.update_world_draft(
            self.request({"name": "Renamed", "description": "Desc"}), draft_id
        )
        self.assertEqual(rename.status, 200)
        self.assertEqual(self.decode(rename)["draft"]["name"], "Renamed")

        activate = await self.controller.activate_world_draft(self.request(), draft_id)
        self.assertEqual(activate.status, 200)
        self.assertEqual(self.decode(activate)["active_draft_id"], draft_id)

    async def test_draft_reset_targets_selected_draft(self):
        draft_id = self.builder.create_draft(name="Experiment")["draft"]["id"]

        response = await self.controller.reset_world_draft(self.request(), draft_id)

        self.assertEqual(response.status, 200)
        body = self.decode(response)
        self.assertTrue(self.builder.reset_called)
        self.assertEqual(body["world"]["rooms"][0]["id"], "draft-baseline")
        self.assertEqual(body["draft"]["id"], draft_id)
        self.assertEqual(
            self.builder.draft_worlds[draft_id]["rooms"][0]["id"], "draft-baseline"
        )

    async def test_mob_definitions_rejects_missing_admin_token(self):
        response = await self.controller.list_mob_definitions(FakeRequest())

        self.assertEqual(response.status, 401)
        self.assertEqual(self.decode(response)["error"], "unauthorized")

    async def test_mob_definitions_returns_serialized_definitions(self):
        response = await self.controller.list_mob_definitions(self.request())

        self.assertEqual(response.status, 200)
        definitions = self.decode(response)["mob_definitions"]
        self.assertGreater(len(definitions), 0)
        expected_keys = {
            "id",
            "name",
            "description",
            "strength",
            "dexterity",
            "max_stamina",
            "damage",
            "aggressive",
            "aggro_delay_min",
            "aggro_delay_max",
            "movement_interval",
            "patrol_rooms",
            "point_value",
            "pronouns",
            "instant_death",
            "loot_table",
        }
        for definition in definitions:
            self.assertEqual(expected_keys, set(definition))

        by_id = {definition["id"]: definition for definition in definitions}
        peasant = by_id["peasant"]
        self.assertEqual(peasant["name"], "peasant")
        self.assertFalse(peasant["aggressive"])
        self.assertEqual(peasant["patrol_rooms"], ["square", "road", "shop"])
        self.assertEqual(peasant["movement_interval"], 150)
        self.assertEqual(peasant["loot_table"][0]["chance"], 0.3)
        self.assertEqual(peasant["loot_table"][0]["item"]["id"], "coin")

    async def test_mob_definitions_includes_level_names(self):
        response = await self.controller.list_mob_definitions(self.request())

        level_names = self.decode(response)["levels"]
        self.assertIn("Neophyte", level_names)
        self.assertGreater(len(level_names), 3)
        self.assertTrue(all(isinstance(name, str) and name for name in level_names))

    async def test_mob_definitions_serializes_weapon_loot_items(self):
        response = await self.controller.list_mob_definitions(self.request())

        guard = next(
            definition
            for definition in self.decode(response)["mob_definitions"]
            if definition["id"] == "guard"
        )
        dagger = guard["loot_table"][0]["item"]
        self.assertEqual(dagger["id"], "dagger")
        self.assertEqual(dagger["item_type"], "weapon")
        self.assertEqual(dagger["damage"], 4)

    def test_serialize_mob_definition_applies_mobile_defaults(self):
        serialized = _serialize_mob_definition(
            "ghost", {"name": "ghost", "description": "Boo."}
        )

        self.assertEqual(serialized["id"], "ghost")
        self.assertEqual(serialized["strength"], 20)
        self.assertEqual(serialized["dexterity"], 20)
        self.assertEqual(serialized["max_stamina"], 100)
        self.assertEqual(serialized["damage"], 5)
        self.assertFalse(serialized["aggressive"])
        self.assertEqual(serialized["aggro_delay_min"], 0)
        self.assertEqual(serialized["aggro_delay_max"], 0)
        self.assertEqual(serialized["movement_interval"], 10)
        self.assertEqual(serialized["patrol_rooms"], [])
        self.assertEqual(serialized["point_value"], 0)
        self.assertEqual(serialized["pronouns"], "it")
        self.assertFalse(serialized["instant_death"])
        self.assertEqual(serialized["loot_table"], [])

    def test_serialize_mob_definition_skips_malformed_loot_entries(self):
        serialized = _serialize_mob_definition(
            "ghost",
            {
                "name": "ghost",
                "description": "Boo.",
                "loot_table": [
                    "bad-entry",
                    {"chance": 0.5},
                    {"item": object(), "chance": 0.5},
                ],
            },
        )

        self.assertEqual(serialized["loot_table"], [])

    def test_serialize_mob_definition_defaults_come_from_mobile_constructor(self):
        """Stat defaults must be sourced from Mobile.__init__, not a copy."""
        import inspect

        from models.Mobile import Mobile

        defaults = {
            name: parameter.default
            for name, parameter in inspect.signature(Mobile.__init__).parameters.items()
            if parameter.default is not inspect.Parameter.empty
        }

        serialized = _serialize_mob_definition(
            "ghost", {"name": "ghost", "description": "Boo."}
        )

        for field in (
            "strength",
            "dexterity",
            "max_stamina",
            "damage",
            "aggressive",
            "aggro_delay_min",
            "aggro_delay_max",
            "movement_interval",
            "point_value",
            "pronouns",
            "instant_death",
        ):
            self.assertEqual(serialized[field], defaults[field], field)

    def test_serialize_mob_definition_passes_through_definition_overrides(self):
        serialized = _serialize_mob_definition(
            "ogre",
            {
                "name": "Ogre",
                "description": "Big and mean.",
                "strength": 55,
                "dexterity": 11,
                "max_stamina": 250,
                "damage": 17,
                "aggressive": True,
                "aggro_delay_min": 2,
                "aggro_delay_max": 6,
                "movement_interval": 40,
                "patrol_rooms": ["cave", "bridge"],
                "point_value": 120,
                "pronouns": "he",
                "instant_death": True,
            },
        )

        self.assertEqual(serialized["id"], "ogre")
        self.assertEqual(serialized["name"], "Ogre")
        self.assertEqual(serialized["description"], "Big and mean.")
        self.assertEqual(serialized["strength"], 55)
        self.assertEqual(serialized["dexterity"], 11)
        self.assertEqual(serialized["max_stamina"], 250)
        self.assertEqual(serialized["damage"], 17)
        self.assertTrue(serialized["aggressive"])
        self.assertEqual(serialized["aggro_delay_min"], 2)
        self.assertEqual(serialized["aggro_delay_max"], 6)
        self.assertEqual(serialized["movement_interval"], 40)
        self.assertEqual(serialized["patrol_rooms"], ["cave", "bridge"])
        self.assertEqual(serialized["point_value"], 120)
        self.assertEqual(serialized["pronouns"], "he")
        self.assertTrue(serialized["instant_death"])

    async def test_draft_routes_apply_publish_delete_and_missing_draft(self):
        draft_id = self.builder.create_draft(name="Experiment")["draft"]["id"]
        world = {"version": 1, "rooms": [{"id": "experiment"}], "mobs": []}

        apply = await self.controller.apply_world_draft(
            self.request({"world": world}), draft_id
        )
        self.assertEqual(apply.status, 200)
        self.assertEqual(self.builder.applied, world)

        publish = await self.controller.publish_world_draft(
            self.request({"world": world}), draft_id
        )
        self.assertEqual(publish.status, 200)
        self.assertTrue(self.decode(publish)["publish"]["ok"])

        delete = await self.controller.delete_world_draft(self.request(), draft_id)
        self.assertEqual(delete.status, 200)

        missing = await self.controller.get_world_draft(self.request(), draft_id)
        self.assertEqual(missing.status, 404)
        self.assertEqual(self.decode(missing)["error"], "draft_not_found")


class AdminRouteAuthorizationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.player = SimpleNamespace(name="Stupidgem")
        self.sessions = {"sid1": {"player": self.player, "admin_token": "token-123"}}
        self.controller = AdminRouteController(
            game_state=SimpleNamespace(rooms={}),
            mob_manager=SimpleNamespace(mobs={}),
            online_sessions=self.sessions,
            world_builder=FakeWorldBuilder(),
            world_factory=Mock(return_value={}),
        )

    def decode(self, response):
        return json.loads(response.text)

    def all_handlers(self):
        return [
            self.controller.get_world,
            self.controller.save_world,
            self.controller.validate_world,
            self.controller.apply_world,
            self.controller.reset_world,
            self.controller.publish_world,
            self.controller.list_world_drafts,
            self.controller.create_world_draft,
            self.controller.get_world_draft,
            self.controller.save_world_draft,
            self.controller.update_world_draft,
            self.controller.delete_world_draft,
            self.controller.activate_world_draft,
            self.controller.reset_world_draft,
            self.controller.apply_world_draft,
            self.controller.publish_world_draft,
            self.controller.list_mob_definitions,
        ]

    async def test_every_admin_handler_rejects_missing_token(self):
        for handler in self.all_handlers():
            response = await handler(FakeRequest())

            self.assertEqual(response.status, 401, handler.__name__)
            self.assertEqual(self.decode(response)["error"], "unauthorized")

    async def test_every_admin_handler_rejects_unknown_token(self):
        for handler in self.all_handlers():
            request = FakeRequest(headers={"Authorization": "Bearer wrong-token"})

            response = await handler(request)

            self.assertEqual(response.status, 401, handler.__name__)

    async def test_world_body_handlers_reject_missing_world_object(self):
        handlers = [
            self.controller.validate_world,
            self.controller.apply_world,
            self.controller.publish_world,
            self.controller.save_world_draft,
            self.controller.apply_world_draft,
            self.controller.publish_world_draft,
        ]
        for handler in handlers:
            request = FakeRequest(
                headers={"Authorization": "Bearer token-123"},
                payload={"not_world": True},
            )

            response = await handler(request)

            self.assertEqual(response.status, 400, handler.__name__)
            self.assertEqual(self.decode(response)["error"], "invalid_world")

    async def test_json_body_handlers_reject_invalid_json(self):
        request = FakeRequest(headers={"Authorization": "Bearer token-123"})

        response = await self.controller.create_world_draft(request)

        self.assertEqual(response.status, 400)
        self.assertEqual(self.decode(response)["error"], "invalid_json")

    async def test_json_body_handlers_reject_non_object_payload(self):
        request = FakeRequest(
            headers={"Authorization": "Bearer token-123"},
            payload=["not", "an", "object"],
        )

        response = await self.controller.update_world_draft(request, "main")

        self.assertEqual(response.status, 400)
        self.assertEqual(self.decode(response)["error"], "invalid_json")

    async def test_options_returns_no_content_with_cors_headers(self):
        response = await self.controller.options(FakeRequest())

        self.assertEqual(response.status, 204)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "*")


class RegisterAdminRoutesTest(unittest.TestCase):
    def test_register_admin_routes_registers_world_and_mob_definition_routes(self):
        from aiohttp import web

        from admin.routes import register_admin_routes

        app = web.Application()
        controller = register_admin_routes(
            app,
            game_state=SimpleNamespace(rooms={}),
            mob_manager=SimpleNamespace(mobs={}),
            online_sessions={},
            world_factory=Mock(return_value={}),
            world_builder=FakeWorldBuilder(),
        )

        registered = {
            (route.method, route.resource.canonical) for route in app.router.routes()
        }
        self.assertIn(("GET", "/admin/api/world"), registered)
        self.assertIn(("GET", "/admin/api/world/mob-definitions"), registered)
        self.assertIn(("OPTIONS", "/admin/api/world/mob-definitions"), registered)
        self.assertIn(("POST", "/admin/api/world/validate"), registered)
        self.assertIsInstance(controller, AdminRouteController)

    def test_register_admin_routes_defaults_world_builder_spawn_to_global(self):
        from aiohttp import web
        from globals import SPAWN_ROOM

        from admin.routes import register_admin_routes

        app = web.Application()
        controller = register_admin_routes(
            app,
            game_state=SimpleNamespace(rooms={}),
            mob_manager=SimpleNamespace(mobs={}),
            online_sessions={},
            world_factory=Mock(return_value={}),
        )

        self.assertEqual(controller.world_builder.spawn_room_id, SPAWN_ROOM)


if __name__ == "__main__":
    unittest.main()
