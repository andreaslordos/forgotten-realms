from models.ContainerItem import ContainerItem
from models.Player import Player


def get_player_inventory(player: Player) -> str:
    return_str = " ".join([item.name for item in player.inventory])

    for item in player.inventory:
        if isinstance(item, ContainerItem):
            return_str += f"\n{item.get_contained()}"
    return return_str
