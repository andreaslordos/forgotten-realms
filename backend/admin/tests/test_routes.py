import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from admin.routes import AdminRouteController, create_admin_token, is_admin_session


class FakeRequest:
    def __init__(self, headers=None, payload=None):
        self.headers = headers or {}
        self._payload = payload

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

    def publish(self, world_data, checks=None, message=None):
        self.published = {"world_data": world_data, "checks": checks or []}
        return {"committed": True, "pushed": True, "commit": "abc123"}


class AdminRouteControllerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.player = SimpleNamespace(name="Stupidgem")
        self.sessions = {
            "sid1": {"player": self.player, "admin_token": "token-123"}
        }
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


if __name__ == "__main__":
    unittest.main()
