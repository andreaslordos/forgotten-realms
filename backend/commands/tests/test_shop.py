"""
Comprehensive tests for the shop module.

Tests cover:
- find_shopkeeper room lookup
- handle_list wares listing
- handle_buy purchases, refunds, and fresh-copy stock
- handle_sell payouts and refusals
- handle_drink consumable effects (heal, cure_all)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.shop import (
    find_shopkeeper,
    handle_buy,
    handle_drink,
    handle_list,
    handle_sell,
)
from models.Consumable import EFFECT_CURE_ALL, EFFECT_HEAL, Consumable
from models.Item import Item
from models.Player import Player
from services.affliction_service import apply_affliction, get_active_afflictions


class ShopTestBase(unittest.IsolatedAsyncioTestCase):
    """Shared fixtures: a real player and a mock shopkeeper in one room."""

    def setUp(self):
        """Set up a real player, a stocked shopkeeper, and shop mocks."""
        self.player = Player("Shopper")
        self.player.current_room = "market_square"
        self.player.gold = 50

        self.sword = Item(
            "iron sword", "shop_sword_1", "A plain iron sword.", weight=5, value=20
        )
        self.potion = Consumable(
            "healing draught",
            "shop_potion_1",
            "A warm red draught.",
            effect=EFFECT_HEAL,
            magnitude=10,
            value=12,
        )

        self.shopkeeper = Mock()
        self.shopkeeper.name = "merchant"
        self.shopkeeper.shop_stock = [
            {"item": self.sword, "price": 30},
            {"item": self.potion, "price": 15},
        ]
        self.shopkeeper.buys_items = True

        self.mob_manager = Mock()
        self.mob_manager.get_mobs_in_room = Mock(return_value=[self.shopkeeper])

        self.utils = Mock()
        self.utils.mob_manager = self.mob_manager

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()

    def call_args(self, cmd):
        """Build the standard handler argument tuple for a command dict."""
        return (
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )


class FindShopkeeperTest(ShopTestBase):
    """Test find_shopkeeper room lookup."""

    async def test_find_shopkeeper_returns_mob_with_stock(self):
        """Test a mob with non-empty shop_stock in the room is found."""
        # Arrange & Act
        result = find_shopkeeper(self.player, self.utils)

        # Assert
        self.assertIs(result, self.shopkeeper)
        self.mob_manager.get_mobs_in_room.assert_called_once_with("market_square")

    async def test_find_shopkeeper_ignores_mobs_without_stock(self):
        """Test mobs with empty shop_stock are not shopkeepers."""
        # Arrange
        rat = Mock()
        rat.shop_stock = []
        self.mob_manager.get_mobs_in_room.return_value = [rat]

        # Act
        result = find_shopkeeper(self.player, self.utils)

        # Assert
        self.assertIsNone(result)

    async def test_find_shopkeeper_returns_none_for_empty_room(self):
        """Test an empty room yields no shopkeeper."""
        # Arrange
        self.mob_manager.get_mobs_in_room.return_value = []

        # Act
        result = find_shopkeeper(self.player, self.utils)

        # Assert
        self.assertIsNone(result)

    async def test_find_shopkeeper_returns_none_without_mob_manager(self):
        """Test missing utils.mob_manager is handled gracefully."""
        # Arrange
        bare_utils = Mock(spec=[])

        # Act
        result = find_shopkeeper(self.player, bare_utils)

        # Assert
        self.assertIsNone(result)


class HandleListTest(ShopTestBase):
    """Test handle_list wares listing."""

    async def test_handle_list_without_shopkeeper(self):
        """Test list reports when no one is selling."""
        # Arrange
        self.mob_manager.get_mobs_in_room.return_value = []

        # Act
        result = await handle_list(*self.call_args({"verb": "list"}))

        # Assert
        self.assertEqual(result, "There is no one here selling anything.")

    async def test_handle_list_shows_wares_with_prices(self):
        """Test list shows each stocked item with its price."""
        # Arrange & Act
        result = await handle_list(*self.call_args({"verb": "list"}))

        # Assert
        self.assertIn("Merchant offers:", result)
        self.assertIn("iron sword", result)
        self.assertIn("30 gold", result)
        self.assertIn("healing draught", result)
        self.assertIn("15 gold", result)

    async def test_handle_list_shows_player_gold(self):
        """Test list ends with the player's gold balance."""
        # Arrange & Act
        result = await handle_list(*self.call_args({"verb": "list"}))

        # Assert
        self.assertIn("You have 50 gold.", result)

    async def test_handle_list_shows_buys_goods_line_when_buys_items(self):
        """Test list advertises buying when the shopkeeper buys goods."""
        # Arrange & Act
        result = await handle_list(*self.call_args({"verb": "list"}))

        # Assert
        self.assertIn("also buys goods", result)

    async def test_handle_list_omits_buys_goods_line_when_not_buying(self):
        """Test list omits the buying line for a sell-only shopkeeper."""
        # Arrange
        self.shopkeeper.buys_items = False

        # Act
        result = await handle_list(*self.call_args({"verb": "list"}))

        # Assert
        self.assertNotIn("also buys goods", result)

    async def test_handle_list_skips_entries_without_item(self):
        """Test malformed stock entries with no item are skipped."""
        # Arrange
        self.shopkeeper.shop_stock = [{"price": 99}, {"item": self.sword, "price": 30}]

        # Act
        result = await handle_list(*self.call_args({"verb": "list"}))

        # Assert
        self.assertNotIn("99", result)
        self.assertIn("iron sword", result)


class HandleBuyTest(ShopTestBase):
    """Test handle_buy purchases."""

    async def test_handle_buy_without_subject(self):
        """Test buy with no subject asks what to buy."""
        # Arrange & Act
        result = await handle_buy(*self.call_args({"verb": "buy"}))

        # Assert
        self.assertEqual(result, "Buy what?")

    async def test_handle_buy_without_shopkeeper(self):
        """Test buy fails when no shopkeeper is present."""
        # Arrange
        self.mob_manager.get_mobs_in_room.return_value = []

        # Act
        result = await handle_buy(*self.call_args({"verb": "buy", "subject": "sword"}))

        # Assert
        self.assertEqual(result, "There is no one here selling anything.")

    async def test_handle_buy_unknown_item(self):
        """Test buying an item the shopkeeper doesn't stock."""
        # Arrange & Act
        result = await handle_buy(*self.call_args({"verb": "buy", "subject": "banana"}))

        # Assert
        self.assertEqual(result, "Merchant doesn't sell 'banana'.")

    async def test_handle_buy_insufficient_gold(self):
        """Test buying with too little gold refuses and keeps gold intact."""
        # Arrange
        self.player.gold = 10

        # Act
        result = await handle_buy(*self.call_args({"verb": "buy", "subject": "sword"}))

        # Assert
        self.assertIn("costs 30 gold", result)
        self.assertIn("you only have 10", result)
        self.assertEqual(self.player.gold, 10)
        self.assertEqual(self.player.inventory, [])

    async def test_handle_buy_success_deducts_gold_and_adds_item(self):
        """Test a successful buy deducts the price and adds the item."""
        # Arrange & Act
        result = await handle_buy(*self.call_args({"verb": "buy", "subject": "sword"}))

        # Assert
        self.assertIn("You buy the iron sword for 30 gold.", result)
        self.assertIn("(20 gold left)", result)
        self.assertEqual(self.player.gold, 20)
        self.assertEqual(len(self.player.inventory), 1)
        self.assertEqual(self.player.inventory[0].name, "iron sword")
        self.player_manager.save_players.assert_called_once()

    async def test_handle_buy_hands_over_fresh_copy_not_stock_instance(self):
        """Test the bought item is a copy, never the shared stock instance."""
        # Arrange & Act
        await handle_buy(*self.call_args({"verb": "buy", "subject": "sword"}))

        # Assert
        bought = self.player.inventory[0]
        self.assertIsNot(bought, self.sword)
        self.assertEqual(bought.id, self.sword.id)

    async def test_handle_buy_consumable_preserves_type(self):
        """Test buying a consumable hands over a Consumable copy."""
        # Arrange & Act
        await handle_buy(*self.call_args({"verb": "buy", "subject": "draught"}))

        # Assert
        bought = self.player.inventory[0]
        self.assertIsInstance(bought, Consumable)
        self.assertIsNot(bought, self.potion)
        self.assertEqual(bought.magnitude, 10)

    async def test_handle_buy_refunds_gold_on_capacity_failure(self):
        """Test a failed pickup (full inventory) refunds the gold."""
        # Arrange
        self.player.carrying_capacity_num = 0

        # Act
        result = await handle_buy(*self.call_args({"verb": "buy", "subject": "sword"}))

        # Assert
        self.assertEqual(result, "You are carrying too many items.")
        self.assertEqual(self.player.gold, 50)
        self.assertEqual(self.player.inventory, [])
        self.player_manager.save_players.assert_not_called()


class HandleSellTest(ShopTestBase):
    """Test handle_sell payouts and refusals."""

    def setUp(self):
        """Add a sellable trinket to the player's inventory."""
        super().setUp()
        self.trinket = Item(
            "silver ring", "ring_1", "A silver ring.", weight=1, value=10
        )
        self.player.inventory.append(self.trinket)

    async def test_handle_sell_without_subject(self):
        """Test sell with no subject asks what to sell."""
        # Arrange & Act
        result = await handle_sell(*self.call_args({"verb": "sell"}))

        # Assert
        self.assertEqual(result, "Sell what?")

    async def test_handle_sell_without_shopkeeper(self):
        """Test sell fails when no shopkeeper is present."""
        # Arrange
        self.mob_manager.get_mobs_in_room.return_value = []

        # Act
        result = await handle_sell(*self.call_args({"verb": "sell", "subject": "ring"}))

        # Assert
        self.assertEqual(result, "There is no one here buying anything.")

    async def test_handle_sell_refuses_when_shopkeeper_not_buying(self):
        """Test sell fails when the shopkeeper doesn't buy goods."""
        # Arrange
        self.shopkeeper.buys_items = False

        # Act
        result = await handle_sell(*self.call_args({"verb": "sell", "subject": "ring"}))

        # Assert
        self.assertEqual(result, "Merchant isn't interested in buying.")
        self.assertIn(self.trinket, self.player.inventory)

    async def test_handle_sell_pays_half_value_and_removes_item(self):
        """Test selling pays value // 2 gold and removes the item."""
        # Arrange & Act
        result = await handle_sell(*self.call_args({"verb": "sell", "subject": "ring"}))

        # Assert
        self.assertIn("You sell the silver ring for 5 gold.", result)
        self.assertIn("(55 gold total)", result)
        self.assertEqual(self.player.gold, 55)
        self.assertNotIn(self.trinket, self.player.inventory)
        self.player_manager.save_players.assert_called_once()

    async def test_handle_sell_refuses_worthless_item(self):
        """Test selling a zero-value item is refused and item kept."""
        # Arrange
        junk = Item("old boot", "boot_1", "A soggy old boot.", value=0)
        self.player.inventory.append(junk)

        # Act
        result = await handle_sell(*self.call_args({"verb": "sell", "subject": "boot"}))

        # Assert
        self.assertIn("worthless", result)
        self.assertIn(junk, self.player.inventory)
        self.assertEqual(self.player.gold, 50)

    async def test_handle_sell_item_not_carried(self):
        """Test selling something not in inventory."""
        # Arrange & Act
        result = await handle_sell(
            *self.call_args({"verb": "sell", "subject": "crown"})
        )

        # Assert
        self.assertEqual(result, "You aren't carrying a 'crown'.")
        self.assertEqual(self.player.gold, 50)


class HandleDrinkTest(ShopTestBase):
    """Test handle_drink consumable effects."""

    async def test_handle_drink_without_subject(self):
        """Test drink with no subject asks what to drink."""
        # Arrange & Act
        result = await handle_drink(*self.call_args({"verb": "drink"}))

        # Assert
        self.assertEqual(result, "Drink what?")

    async def test_handle_drink_not_carrying_consumable(self):
        """Test drinking something you don't carry."""
        # Arrange & Act
        result = await handle_drink(
            *self.call_args({"verb": "drink", "subject": "potion"})
        )

        # Assert
        self.assertEqual(result, "You aren't carrying a drinkable 'potion'.")

    async def test_handle_drink_ignores_non_consumable_items(self):
        """Test a plain item with a matching name is not drinkable."""
        # Arrange
        fake = Item("potion bottle", "bottle_1", "An empty potion bottle.")
        self.player.inventory.append(fake)

        # Act
        result = await handle_drink(
            *self.call_args({"verb": "drink", "subject": "potion"})
        )

        # Assert
        self.assertEqual(result, "You aren't carrying a drinkable 'potion'.")
        self.assertIn(fake, self.player.inventory)

    async def test_handle_drink_heal_restores_stamina_and_consumes_item(self):
        """Test a heal potion restores magnitude stamina and is consumed."""
        # Arrange - level 0 max_stamina is 45; leave 15 missing
        self.player.stamina = 30
        potion = Consumable(
            "healing draught",
            "potion_1",
            "A warm red draught.",
            effect=EFFECT_HEAL,
            magnitude=10,
        )
        self.player.inventory.append(potion)

        # Act
        result = await handle_drink(
            *self.call_args({"verb": "drink", "subject": "draught"})
        )

        # Assert
        self.assertEqual(self.player.stamina, 40)
        self.assertIn("+10 stamina", result)
        self.assertNotIn(potion, self.player.inventory)
        self.player_manager.save_players.assert_called_once()

    async def test_handle_drink_heal_caps_at_max_stamina(self):
        """Test healing never overshoots max_stamina."""
        # Arrange - only 5 stamina missing but magnitude is 10
        self.player.stamina = self.player.max_stamina - 5
        potion = Consumable(
            "healing draught",
            "potion_1",
            "A warm red draught.",
            effect=EFFECT_HEAL,
            magnitude=10,
        )
        self.player.inventory.append(potion)

        # Act
        result = await handle_drink(
            *self.call_args({"verb": "drink", "subject": "draught"})
        )

        # Assert
        self.assertEqual(self.player.stamina, self.player.max_stamina)
        self.assertIn("+5 stamina", result)

    async def test_handle_drink_cure_all_removes_afflictions(self):
        """Test a cure-all tonic clears session afflictions and is consumed."""
        # Arrange
        session = {"player": self.player}
        apply_affliction(session, "blind", 300, "witch")
        apply_affliction(session, "deaf", 300, "witch")
        self.online_sessions["sid1"] = session
        tonic = Consumable(
            "bitter tonic",
            "tonic_1",
            "A bitter cleansing tonic.",
            effect=EFFECT_CURE_ALL,
        )
        self.player.inventory.append(tonic)

        # Act
        result = await handle_drink(
            *self.call_args({"verb": "drink", "subject": "tonic"})
        )

        # Assert
        self.assertEqual(get_active_afflictions(session), set())
        self.assertIn("The foulness lifts from you.", result)
        self.assertNotIn(tonic, self.player.inventory)
        self.player_manager.save_players.assert_called_once()

    async def test_handle_drink_cure_all_with_nothing_to_cure(self):
        """Test a cure-all tonic with no afflictions still gets drunk."""
        # Arrange
        self.online_sessions["sid1"] = {"player": self.player}
        tonic = Consumable(
            "bitter tonic",
            "tonic_1",
            "A bitter cleansing tonic.",
            effect=EFFECT_CURE_ALL,
        )
        self.player.inventory.append(tonic)

        # Act
        result = await handle_drink(
            *self.call_args({"verb": "drink", "subject": "tonic"})
        )

        # Assert
        self.assertIn("nothing ailed you", result)
        self.assertNotIn(tonic, self.player.inventory)

    async def test_handle_drink_unknown_effect_does_nothing(self):
        """Test an unrecognized effect drinks with no effect."""
        # Arrange
        weird = Consumable(
            "strange brew",
            "brew_1",
            "A strange fizzing brew.",
            effect="teleport",
        )
        self.player.inventory.append(weird)

        # Act
        result = await handle_drink(
            *self.call_args({"verb": "drink", "subject": "brew"})
        )

        # Assert
        self.assertEqual(result, "You drink the strange brew. Nothing happens.")
        self.assertNotIn(weird, self.player.inventory)


if __name__ == "__main__":
    unittest.main()
