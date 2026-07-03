# backend/commands/shop.py
"""
Shop commands: list, buy, sell — and drink for consumables.

Shopkeepers are mobs with a non-empty shop_stock. Selling pays half an
item's value in gold; buying hands over a fresh copy of the stocked item.
Gold (from mob drops and coins) and points (from swamping treasure) are
separate currencies: selling never competes with swamping.
"""

import logging
from typing import Any, Dict, Optional

from commands.registry import command_registry
from commands.natural_language_parser import vocabulary_manager
from models.Consumable import EFFECT_CURE_ALL, EFFECT_HEAL, Consumable
from services.affliction_service import cure_all_afflictions, find_player_sid

logger = logging.getLogger(__name__)

SELL_DIVISOR = 2  # Shopkeepers pay value // 2 in gold


def find_shopkeeper(player: Any, utils: Any) -> Optional[Any]:
    """Find a living shopkeeper (mob with stock) in the player's room."""
    mob_manager = getattr(utils, "mob_manager", None)
    if not mob_manager:
        return None
    for mob in mob_manager.get_mobs_in_room(player.current_room):
        if getattr(mob, "shop_stock", None):
            return mob
    return None


async def handle_list(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """List a shopkeeper's wares."""
    shopkeeper = find_shopkeeper(player, utils)
    if not shopkeeper:
        return "There is no one here selling anything."

    lines = [f"{shopkeeper.name.capitalize()} offers:"]
    for entry in shopkeeper.shop_stock:
        item = entry.get("item")
        price = entry.get("price", 0)
        if item is None:
            continue
        lines.append(f"  {item.name:<16} {price} gold")
    if getattr(shopkeeper, "buys_items", False):
        lines.append(f"{shopkeeper.name.capitalize()} also buys goods (half value).")
    lines.append(f"You have {player.gold} gold.")
    return "\n".join(lines)


async def handle_buy(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """Buy an item from a shopkeeper."""
    subject = cmd.get("subject")
    if not subject:
        return "Buy what?"

    shopkeeper = find_shopkeeper(player, utils)
    if not shopkeeper:
        return "There is no one here selling anything."

    for entry in shopkeeper.shop_stock:
        item = entry.get("item")
        if item is None or not item.matches_name(subject):
            continue
        price = int(entry.get("price", 0))
        if player.gold < price:
            return (
                f"{item.name.capitalize()} costs {price} gold - "
                f"you only have {player.gold}."
            )
        # Hand over a fresh copy so stock is never a shared instance.
        fresh = type(item).from_dict(item.to_dict())
        player.gold -= price
        success, message = player.add_item(fresh)
        if not success:
            player.gold += price  # refund
            return str(message)
        player_manager.save_players()
        return (
            f"You buy the {fresh.name} for {price} gold. "
            f"({player.gold} gold left)"
        )
    return f"{shopkeeper.name.capitalize()} doesn't sell '{subject}'."


async def handle_sell(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """Sell an item from your inventory to a shopkeeper."""
    subject = cmd.get("subject")
    if not subject:
        return "Sell what?"

    shopkeeper = find_shopkeeper(player, utils)
    if not shopkeeper:
        return "There is no one here buying anything."
    if not getattr(shopkeeper, "buys_items", False):
        return f"{shopkeeper.name.capitalize()} isn't interested in buying."

    for item in list(player.inventory):
        if not item.matches_name(subject):
            continue
        price = int(getattr(item, "value", 0)) // SELL_DIVISOR
        if price <= 0:
            return (
                f"{shopkeeper.name.capitalize()} sneers. "
                f"'That {item.name} is worthless to me.'"
            )
        player.remove_item(item)
        player.gold += price
        player_manager.save_players()
        return (
            f"You sell the {item.name} for {price} gold. "
            f"({player.gold} gold total)"
        )
    return f"You aren't carrying a '{subject}'."


async def handle_drink(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """Drink a consumable from your inventory."""
    subject = cmd.get("subject")
    if not subject:
        return "Drink what?"

    for item in list(player.inventory):
        if not isinstance(item, Consumable) or not item.matches_name(subject):
            continue
        player.remove_item(item)
        if item.effect == EFFECT_HEAL:
            healed = min(player.max_stamina - player.stamina, item.magnitude)
            player.stamina += healed
            player_manager.save_players()
            return (
                f"You drink the {item.name}. Warmth spreads through you "
                f"(+{healed} stamina)."
            )
        if item.effect == EFFECT_CURE_ALL:
            sid = find_player_sid(player, online_sessions)
            cured = 0
            if sid is not None:
                cured = cure_all_afflictions(online_sessions.get(sid, {}))
            player_manager.save_players()
            if cured:
                return f"You drink the {item.name}. The foulness lifts from you."
            return f"You drink the {item.name}, though nothing ailed you."
        return f"You drink the {item.name}. Nothing happens."

    return f"You aren't carrying a drinkable '{subject}'."


command_registry.register("list", handle_list, "List a shopkeeper's wares.")
command_registry.register("buy", handle_buy, "Buy an item from a shopkeeper.")
command_registry.register("sell", handle_sell, "Sell an item to a shopkeeper.")
command_registry.register("drink", handle_drink, "Drink a potion or draught.")
command_registry.register_aliases(["quaff"], "drink")

for _verb in ("list", "buy", "sell", "drink"):
    vocabulary_manager.add_verb(_verb)
