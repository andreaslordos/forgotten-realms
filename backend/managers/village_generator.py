# backend/managers/village_generator.py
# Valley of Barovia - A Curse of Strahd inspired gothic horror world

from typing import Dict, Optional, Any
from models.Room import Room
from models.Item import Item
from models.StatefulItem import StatefulItem
from models.ContainerItem import ContainerItem
from models.Weapon import Weapon
from models.SpecializedRooms import SwampRoom


# ============================================================================
# PUZZLE CONDITION FUNCTIONS
# These are used by StatefulItem.add_interaction(conditional_fn=...)
# ============================================================================


def has_sunsword(player: Any, game_state: Any) -> bool:
    """Check if player has the sunsword in their inventory."""
    return any(
        hasattr(item, "id") and item.id == "sunsword" for item in player.inventory
    )


def has_any_weapon(player: Any, game_state: Any) -> bool:
    """Check if player has any weapon in their inventory."""
    from models.Weapon import Weapon

    return any(isinstance(item, Weapon) for item in player.inventory)


def stones_aligned(player: Any, game_state: Any) -> bool:
    """Check if all three standing stones are correctly aligned."""
    room = game_state.get_room("clearing")
    if not room:
        return False

    east_state = None
    west_state = None
    north_state = None

    for item in room.items:
        if hasattr(item, "id"):
            if item.id == "eaststone":
                east_state = getattr(item, "state", None)
            elif item.id == "weststone":
                west_state = getattr(item, "state", None)
            elif item.id == "northstone":
                north_state = getattr(item, "state", None)

    return east_state == "sunrise" and west_state == "sunset" and north_state == "noon"


def beacon_has_skull(player: Any, game_state: Any) -> bool:
    """Check if the dragon skull has been placed on the beacon."""
    room = game_state.get_room("hall")
    if not room:
        return False
    for item in room.items:
        if hasattr(item, "id") and item.id == "dragon_beacon":
            return getattr(item, "state", None) == "skull_placed"
    return False


def player_has_light(player: Any, game_state: Any) -> bool:
    """Check if player has a light source in their inventory."""
    for item in player.inventory:
        if getattr(item, "emits_light", False):
            return True
    return False


def knight_honored(player: Any, game_state: Any) -> bool:
    """Check if player has shown respect to the knights (knelt before inscription)."""
    room = game_state.get_room("quarters")
    if not room:
        return False
    for item in room.items:
        if hasattr(item, "id") and item.id == "knight_inscription":
            return getattr(item, "state", None) == "honored"
    return False


def treasury_unlocked(player: Any, game_state: Any) -> bool:
    """Check if the treasury pedestal dials are correctly set."""
    room = game_state.get_room("treasury")
    if not room:
        return False

    dial_states: Dict[str, Optional[str]] = {}
    for item in room.items:
        if hasattr(item, "id") and item.id in ("dial1", "dial2", "dial3"):
            dial_states[item.id] = getattr(item, "state", None)

    # Correct sequence: sun, star, moon (hinted in tome)
    return (
        dial_states.get("dial1") == "sun"
        and dial_states.get("dial2") == "star"
        and dial_states.get("dial3") == "moon"
    )


# ============================================================================
# MAZE PUZZLE CONDITION FUNCTIONS
# ============================================================================


def player_visited_vallaki_church(player: Any, game_state: Any) -> bool:
    """Check if player has visited St. Andral's Church in Vallaki."""
    return "vallakichurch" in getattr(player, "visited", set())


def mirrors_aligned(player: Any, game_state: Any) -> bool:
    """Check if the mirrors in the Hall of Mirrors are correctly touched in sequence."""
    room = game_state.get_room("maze_mirror")
    if not room:
        return False
    # Check the mirror sequence stored on the room
    sequence = getattr(room, "mirror_sequence", [])
    return sequence == ["east", "south", "west", "north"]


def altar_restored(player: Any, game_state: Any) -> bool:
    """Check if the Argynvostholt altar has been restored."""
    room = game_state.get_room("argchapel")
    if not room:
        return False
    for item in room.items:
        if hasattr(item, "id") and item.id == "arg_altar":
            return getattr(item, "state", None) == "restored"
    return False


def altar_restored_and_skull_placed(player: Any, game_state: Any) -> bool:
    """Check if altar is restored AND skull is placed on beacon."""
    return altar_restored(player, game_state) and beacon_has_skull(player, game_state)


def generate_valley_of_barovia(mob_manager: Optional[Any] = None) -> Dict[str, Room]:
    """
    Generates the Valley of Barovia, a gothic horror world.
    Returns a dictionary mapping room_id to Room objects.

    Args:
        mob_manager (MobManager, optional): Mob manager for spawning mobs
    """
    rooms: Dict[str, Room] = {}

    # Create all rooms
    generate_rooms(rooms)

    # Connect rooms with exits
    connect_exits(rooms)

    # Precompute paths to the swamp for outdoor rooms
    compute_swamp_paths(rooms)

    # Add stateful items to rooms
    add_stateful_items(rooms)

    # Add regular items to rooms
    add_regular_items(rooms)

    # Add container items
    add_container_items(rooms)

    # Add weapons
    add_weapons(rooms)

    # Spawn mobs if mob_manager provided
    if mob_manager:
        spawn_initial_mobs(mob_manager, rooms)

    return rooms


def spawn_initial_mobs(mob_manager: Any, rooms: Dict[str, Room]) -> None:
    """
    Spawn initial mobs in the Valley of Barovia.

    Args:
        mob_manager (MobManager): The mob manager
        rooms (dict): Dictionary of room objects
    """

    def spawn_mob_in_room(mob_type: str, room_id: str) -> None:
        if room_id in rooms:
            mob_manager.spawn_mob(mob_type, room_id)
            mob = mob_manager.mobs.get(list(mob_manager.mobs.keys())[-1])
            if mob:
                rooms[room_id].add_item(mob)

    # Village of Barovia - peaceful NPCs and undead
    spawn_mob_in_room("peasant", "square")
    spawn_mob_in_room("barkeep", "tavern")
    spawn_mob_in_room("priest", "church")
    spawn_mob_in_room("zombie", "graveyard")
    spawn_mob_in_room("ghoul", "crypt")

    # Svalich Woods - wolves and Vistani
    spawn_mob_in_room("wolf", "woods")
    spawn_mob_in_room("vistani", "pool")
    spawn_mob_in_room("seer", "wagon")
    spawn_mob_in_room("bats", "hollow")
    spawn_mob_in_room("specter", "barrow")  # Difficulty progression mob

    # Old Bonegrinder - hags
    spawn_mob_in_room("hag", "mill")
    spawn_mob_in_room("daughter", "bedroom")
    spawn_mob_in_room("raven", "path")

    # Argynvostholt - ghosts and revenants
    spawn_mob_in_room("revenant", "hall")
    spawn_mob_in_room("phantom", "approach")
    spawn_mob_in_room("specter", "chapel")

    # Vallaki - guards, allies, and vampire spawn
    spawn_mob_in_room("guard", "towngate")
    spawn_mob_in_room("baron", "mansion")
    spawn_mob_in_room("wereraven", "attic")
    spawn_mob_in_room("hunter", "inn")
    spawn_mob_in_room("prisoner", "mansiondungeon")

    # Castle Ravenloft - the deadliest encounters
    spawn_mob_in_room("gargoyle", "courtyard")
    spawn_mob_in_room("wraith", "castledungeon")
    spawn_mob_in_room("consort", "dining")
    spawn_mob_in_room("strahd", "tomb")
    spawn_mob_in_room("skeleton", "castlecrypt")
    spawn_mob_in_room("spawn", "castlechapel")
    spawn_mob_in_room("spawn", "coffin")

    # Configure NPC interactions
    configure_npc_interactions(mob_manager, rooms)


def configure_npc_interactions(mob_manager: Any, rooms: Dict[str, Room]) -> None:
    """Configure accepts_item interactions for NPCs."""

    def find_mob_by_name(name: str) -> Any:
        """Find a mob by its name."""
        for mob_id, mob in mob_manager.mobs.items():
            if mob.name.lower() == name.lower():
                return mob
        return None

    # === SEER (wagon) - Give wine for better fortune reading ===
    seer = find_mob_by_name("seer")
    if seer:
        seer.accepts_item = {
            "wine": {
                "message": (
                    "The seer's milky eyes light up as she takes the wine.\n\n"
                    "'Ah, a gift freely given! The mists part for generosity...'\n\n"
                    "She drinks deeply, then fixes you with an unseeing gaze:\n\n"
                    "'I see your path clearly now. The Dark Lord fears three things:\n"
                    "The light of the sun made manifest, the bones of the saint,\n"
                    "and the dragon's beacon rekindled. Seek these, and you may prevail.'"
                ),
                "one_time": True,
                "triggered": False,
            }
        }

    # === PRIEST (church) - Give bones to unlock blessing ===
    priest = find_mob_by_name("priest")
    if priest:

        async def priest_blessing(
            player: Any,
            game_state: Any,
            player_manager: Any,
            online_sessions: Any,
            sio: Any,
            utils: Any,
        ) -> None:
            """Grant player a blessing and cure afflictions."""
            # Find player's session
            player_sid = None
            for sid, session in online_sessions.items():
                if session.get("player") == player:
                    player_sid = sid
                    break
            if player_sid:
                session = online_sessions.get(player_sid, {})
                # Clear afflictions
                session["afflictions"] = {}

        priest.accepts_item = {
            "bones": {
                "message": (
                    "Father Donavich gasps as you hand him the holy bones.\n\n"
                    "'The bones of St. Andral! You've found them! The church is "
                    "protected once more!'\n\n"
                    "He clasps your hands, tears in his eyes.\n\n"
                    "'Bless you, brave soul. May the Morning Lord's light guide you. "
                    "I grant you his blessing - you are cleansed of all afflictions.'"
                ),
                "one_time": True,
                "triggered": False,
                "effect_fn": priest_blessing,
            }
        }

    # === BARKEEP (tavern) - Give coin for hints ===
    barkeep = find_mob_by_name("barkeep")
    if barkeep:
        barkeep.accepts_item = {
            "coin": {
                "message": (
                    "The barkeep palms the coin and leans in conspiratorially.\n\n"
                    "'You want to know about the Devil? I've heard things...'\n\n"
                    "'They say his heart isn't in his chest - it's in a crystal, "
                    "hidden in his castle. Destroy that, and he can be hurt.'\n\n"
                    "'And there's a sword, a blade of pure sunlight, locked away "
                    "in his treasury. The dials must be set right: sun, star, moon.'"
                ),
                "one_time": True,
                "triggered": False,
            }
        }

    # === RAVEN (millpath) - Give food to reveal wereraven ===
    raven = find_mob_by_name("raven")
    if raven:
        raven.accepts_item = {
            "bone": {
                "message": (
                    "The raven hops down and pecks at the bone. Then, before your "
                    "eyes, it transforms!\n\n"
                    "A dark-haired man now stands before you, sharp-featured and keen-eyed.\n\n"
                    "'You have a kind heart,' he says. 'We Keepers of the Feather "
                    "watch over Barovia. The hags at the mill - they steal children. "
                    "Free them if you can, but beware: the hag's true name is her "
                    "weakness. Say it in her kitchen, and she weakens.'\n\n"
                    "He transforms back into a raven and flies away."
                ),
                "one_time": True,
                "triggered": False,
            },
            "meat": {
                "message": (
                    "The raven hops down and pecks at the meat. Then, before your "
                    "eyes, it transforms!\n\n"
                    "A dark-haired man now stands before you, sharp-featured and keen-eyed.\n\n"
                    "'You have a kind heart,' he says. 'We Keepers of the Feather "
                    "watch over Barovia. The hags at the mill - they steal children. "
                    "Free them if you can, but beware: the hag's true name is her "
                    "weakness. Say it in her kitchen, and she weakens.'\n\n"
                    "He transforms back into a raven and flies away."
                ),
                "one_time": True,
                "triggered": False,
            },
        }

    # === HUNTER (inn) - Give fang to get silver weapon ===
    hunter = find_mob_by_name("hunter")
    if hunter:

        async def give_silver_dagger(
            player: Any,
            game_state: Any,
            player_manager: Any,
            online_sessions: Any,
            sio: Any,
            utils: Any,
        ) -> None:
            """Give player a silver dagger."""
            from models.Weapon import Weapon

            silver_dagger = Weapon(
                name="silver dagger",
                id="silver_dagger",
                description="A dagger of pure silver, deadly to creatures of the night.",
                weight=1,
                value=50,
                takeable=True,
                damage=8,
                min_level="Neophyte",
                min_strength=0,
                min_dexterity=5,
            )
            player.add_item(silver_dagger)
            player_manager.save_players()

        hunter.accepts_item = {
            "fang": {
                "message": (
                    "The hunter examines the fang, then nods with respect.\n\n"
                    "'A vampire fang. You've faced the spawn and survived. "
                    "That takes courage - or foolishness.'\n\n"
                    "He reaches into his pack and pulls out a gleaming blade.\n\n"
                    "'Take this silver dagger. Against the undead, silver cuts "
                    "deeper than steel. You'll need it if you're going to the castle.'"
                ),
                "one_time": True,
                "triggered": False,
                "effect_fn": give_silver_dagger,
            }
        }

    # === WOLF (woods) - Give meat/bone to calm ===
    wolf = find_mob_by_name("wolf")
    if wolf:

        async def calm_wolf(
            player: Any,
            game_state: Any,
            player_manager: Any,
            online_sessions: Any,
            sio: Any,
            utils: Any,
        ) -> None:
            """Make the wolf non-aggressive."""
            wolf_mob = find_mob_by_name("wolf")
            if wolf_mob:
                wolf_mob.aggressive = False
                wolf_mob.target_player = None

        wolf.accepts_item = {
            "meat": {
                "message": (
                    "You toss the meat to the wolf. It sniffs cautiously, then "
                    "devours it hungrily.\n\n"
                    "The wolf's posture relaxes. Its snarl fades to a curious "
                    "expression. It seems you've earned a measure of trust - "
                    "for now, at least."
                ),
                "one_time": True,
                "triggered": False,
                "effect_fn": calm_wolf,
            },
            "bone": {
                "message": (
                    "You offer the bone to the wolf. It snatches it from your "
                    "hand and begins gnawing contentedly.\n\n"
                    "The wolf's aggressive stance softens. It regards you with "
                    "something almost like gratitude. Perhaps not all creatures "
                    "in Barovia are beyond redemption."
                ),
                "one_time": True,
                "triggered": False,
                "effect_fn": calm_wolf,
            },
        }

    # === PRISONER (mansiondungeon) - Untie for information ===
    prisoner = find_mob_by_name("prisoner")
    if prisoner:
        # Add untie/free interaction to the prisoner
        prisoner.add_interaction(
            verb="untie",
            target_state="freed",
            message=(
                "You work at the heavy chains binding the prisoner. After much effort, "
                "they come loose.\n\n"
                "The prisoner slumps to the ground, gasping.\n\n"
                "'Thank you... thank you...' he whispers. 'The Baron - he's mad. He tortures "
                "anyone who doesn't smile at his festivals. There's a secret vault behind "
                "the dungeon wall - third stone from the door. His darkest crimes are recorded "
                "there. Expose him, and Vallaki might be free.'\n\n"
                "The prisoner limps away into the shadows."
            ),
            from_state="alive",
        )
        prisoner.add_interaction(
            verb="free",
            target_state="freed",
            message=(
                "You work at the heavy chains binding the prisoner. After much effort, "
                "they come loose.\n\n"
                "The prisoner slumps to the ground, gasping.\n\n"
                "'Thank you... thank you...' he whispers. 'The Baron - he's mad. He tortures "
                "anyone who doesn't smile at his festivals. There's a secret vault behind "
                "the dungeon wall - third stone from the door. His darkest crimes are recorded "
                "there. Expose him, and Vallaki might be free.'\n\n"
                "The prisoner limps away into the shadows."
            ),
            from_state="alive",
        )
        prisoner.add_interaction(
            verb="release",
            target_state="freed",
            message=(
                "You work at the heavy chains binding the prisoner. After much effort, "
                "they come loose.\n\n"
                "The prisoner slumps to the ground, gasping.\n\n"
                "'Thank you... thank you...' he whispers. 'The Baron - he's mad. He tortures "
                "anyone who doesn't smile at his festivals. There's a secret vault behind "
                "the dungeon wall - third stone from the door. His darkest crimes are recorded "
                "there. Expose him, and Vallaki might be free.'\n\n"
                "The prisoner limps away into the shadows."
            ),
            from_state="alive",
        )
        prisoner.add_state_description(
            "freed", "The chains lie empty. The prisoner has escaped into the night."
        )

    # === GARGOYLE (courtyard) - Give coin to pass safely ===
    gargoyle = find_mob_by_name("gargoyle")
    if gargoyle:

        async def calm_gargoyle(
            player: Any,
            game_state: Any,
            player_manager: Any,
            online_sessions: Any,
            sio: Any,
            utils: Any,
        ) -> None:
            """Make the gargoyle non-aggressive."""
            gargoyle_mob = find_mob_by_name("gargoyle")
            if gargoyle_mob:
                gargoyle_mob.aggressive = False
                gargoyle_mob.target_player = None

        gargoyle.accepts_item = {
            "coin": {
                "message": (
                    "The gargoyle's stone eyes fix on the coin. A gravelly voice "
                    "rumbles from within:\n\n"
                    "'Tribute... accepted.'\n\n"
                    "It plucks the coin from your palm and freezes back into "
                    "apparent stone. But this time, its gaze doesn't follow you. "
                    "You may pass unharmed."
                ),
                "one_time": True,
                "triggered": False,
                "effect_fn": calm_gargoyle,
            }
        }


def generate_rooms(rooms: Dict[str, Room]) -> None:
    """Generate all the rooms for the Valley of Barovia."""

    # ===== VILLAGE OF BAROVIA =====

    square: Room = Room(
        "square",
        "Village Square",
        "A bleak village square choked with perpetual mist. A gallows stands in the center, "
        "its rope swaying despite the still air. Boarded windows stare down from decaying buildings "
        "like hollow eyes. The smell of fear hangs heavier than the fog. A crumbling church offers "
        "faint hope to the north. The tavern's dim light flickers to the east. A dirt road leads "
        "south toward the woods, and the burgomaster's manor looms to the west.",
        is_outdoor=True,
    )

    tavern: Room = Room(
        "tavern",
        "Blood of the Vine Tavern",
        "The tavern's interior is dim and smoky. A few haggard villagers nurse drinks in silence, "
        "their eyes darting nervously toward the door. The barkeep polishes the same glass endlessly. "
        "Scratched tables and a cold hearth complete the miserable atmosphere. A worn rug lies "
        "near the back wall. The village square is visible through grimy windows to the west.",
    )

    cellar: Room = Room(
        "cellar",
        "Tavern Cellar",
        "Dusty wine barrels line the walls of this cold cellar. Cobwebs hang thick in the corners. "
        "The smell of damp earth and old wine fills the air. Rats scurry between the casks.",
        is_dark=True,
    )

    church: Room = Room(
        "church",
        "Village Church",
        "This small stone church has seen better days. Cracked pews face a simple altar, and "
        "what remains of stained glass depicts scenes of lost hope. Father Donavich's prayers echo "
        "weakly off the walls. Despite the decay, something about this place feels... safer. The "
        "village square lies to the south, and the graveyard to the west. An iron grate in the "
        "floor leads down to the undercroft.",
    )

    undercroft: Room = Room(
        "undercroft",
        "Church Undercroft",
        "A cramped stone chamber beneath the church. The air is thick with the smell of incense "
        "and something else - something wrong. Scratching sounds echo from the shadows. "
        "Holy symbols have been scratched into the walls, some drawn in what looks like dried blood.",
        is_dark=True,
    )

    shop: Room = Room(
        "shop",
        "Bildrath's Mercantile",
        "A cramped general store crammed with overpriced goods. Bildrath eyes you with undisguised "
        "greed. The shelves hold basic supplies, all marked at extortionate prices. 'If you want it, "
        "you'll pay for it,' he mutters. The square lies to the northeast.",
    )

    manor: Room = Room(
        "manor",
        "Burgomaster's Manor",
        "Once grand, this manor now shows signs of siege. Claw marks score the wooden door, and "
        "the windows are boarded shut. The smell of death lingers in the air. Dust covers everything, "
        "and portraits of the Kolyan family watch from the walls with painted eyes. A study lies "
        "to the north. The square is to the east.",
    )

    study: Room = Room(
        "study",
        "Manor Study",
        "Books line the walls, many dealing with the history of Barovia and its dread lord. "
        "A desk sits by a shuttered window, covered in papers and a half-finished letter. "
        "Something important might be found among these documents.",
    )

    graveyard: Room = Room(
        "graveyard",
        "Village Graveyard",
        "Crooked headstones jut from the muddy earth at odd angles. Many graves show signs of "
        "disturbance - dirt mounded fresh, stones overturned. The mist clings especially thick here, "
        "and you swear you can see shapes moving within it. An iron gate leads to a family crypt. "
        "The church stands to the east.",
        is_outdoor=True,
    )

    crypt: Room = Room(
        "crypt",
        "Family Crypt",
        "Stone sarcophagi line the walls of this underground chamber. The air is stale and cold. "
        "Names and dates are carved into the stone - Kolyanovich, Dilisnya, Wachter. Something "
        "skitters in the shadows. The dead do not rest easy in Barovia.",
        is_dark=True,
    )

    # ===== SVALICH WOODS =====

    road: Room = Room(
        "road",
        "Old Svalich Road",
        "A muddy road winds through oppressive forest. The trees press close on either side, "
        "their bare branches reaching like grasping fingers. Mist pools in every hollow. "
        "The village lies to the north, while the road continues south toward a crossroads. "
        "Wolf howls echo in the distance.",
        is_outdoor=True,
    )

    crossroads: Room = Room(
        "crossroads",
        "Gallows Crossroads",
        "Several roads meet at a weathered signpost. A gallows stands here, a rotting corpse "
        "swinging gently in the breeze. The signs point in various directions: 'Barovia' to the north, "
        "'Vallaki' to the west, 'Castle Ravenloft' to the east, and 'Tser Pool' to the south. "
        "A trail leads southeast into the dark woods. Crows watch from nearby branches.",
        is_outdoor=True,
    )

    woods: Room = Room(
        "woods",
        "Svalich Woods",
        "Dense forest surrounds you. The trees here are ancient and twisted, their bark "
        "blackened as if by fire. Mist curls between the trunks, and the silence is oppressive. "
        "Occasionally, you catch glimpses of movement - wolves perhaps, or something worse. "
        "A clearing is visible to the west. The crossroads lies to the northwest, and a dark "
        "hollow opens to the south.",
        is_outdoor=True,
    )

    clearing: Room = Room(
        "clearing",
        "Forest Clearing",
        "A small clearing in the endless forest. Three ancient standing stones form a circle "
        "at the center, each carved with faded symbols. Wolf tracks crisscross the muddy ground. "
        "A path leads toward a windmill on a distant hill to the west. The dark woods continue east.",
        is_outdoor=True,
    )

    barrow: Room = Room(
        "barrow",
        "Ancient Barrow",
        "Stone steps descend into an ancient burial mound. The air is thick with the dust of ages. "
        "Offerings to forgotten gods lie scattered about - tarnished coins, crumbled bones, a rusted blade. "
        "The darkness here feels sacred, undisturbed for centuries. Steps lead back up to the clearing.",
        is_dark=True,
    )

    pool: Room = Room(
        "pool",
        "Tser Pool",
        "A dark pool reflects the grey sky. Colorful Vistani wagons are camped on the shore, "
        "their painted sides a stark contrast to the dreary landscape. Cooking fires burn, and "
        "the sound of music drifts from somewhere. A worn path leads to a fortune teller's wagon. "
        "The crossroads lies to the north.",
        is_outdoor=True,
    )

    wagon: Room = Room(
        "wagon",
        "Fortune Teller's Wagon",
        "Inside the cramped wagon, incense smoke hangs thick in the air. Silken scarves cover "
        "every surface, and strange charms dangle from the ceiling. An ancient woman sits before "
        "a worn deck of cards, her milky eyes seeing far more than they should. "
        "'Sit,' she says. 'The cards have been expecting you.'",
    )

    hollow: Room = Room(
        "hollow",
        "Dark Hollow",
        "This depression in the forest floor is unnaturally dark. The trees overhead block "
        "what little light exists, and the mist here has a cloying quality. Something rustles "
        "in the undergrowth. The forest path continues to the north.",
        is_dark=True,
        is_outdoor=True,
    )

    bridge: Room = Room(
        "bridge",
        "Stone Bridge",
        "An ancient stone bridge spans a rushing river. The water below is black and swift. "
        "Gargoyle statues crouch at each end, their faces worn smooth by centuries of rain. "
        "The road to Vallaki continues to the west, while the crossroads lies to the east. "
        "An overgrown path leads south toward a ruined manor.",
        is_outdoor=True,
    )

    castlegates: Room = Room(
        "castlegates",
        "Castle Gates",
        "Massive iron gates stand open, their hinges groaning in the wind. Beyond them, a "
        "crumbling bridge leads to the castle itself, its spires stabbing at the grey sky. "
        "The gates seem to invite you in. Or perhaps... they're ensuring you can't leave. "
        "The crossroads lies to the west. The castle courtyard beckons to the east.",
        is_outdoor=True,
    )

    mists: Room = Room(
        "mists",
        "Choking Mists",
        "The mists here are so thick you can barely see your hand before your face. They "
        "seem almost solid, pressing against you, turning you back. No matter which direction "
        "you try, you always end up back where you started. There is no escape from Barovia.",
        is_outdoor=True,
    )

    # ===== OLD BONEGRINDER =====

    millpath: Room = Room(
        "millpath",
        "Path to Windmill",
        "A winding path leads up a barren hill toward a decrepit windmill. The sails turn "
        "slowly despite the lack of wind, creaking with each rotation. The smell of baking "
        "drifts down - something sweet, but wrong. A raven watches from a dead tree. "
        "The clearing lies to the east. The mill entrance beckons.",
        is_outdoor=True,
    )

    mill: Room = Room(
        "mill",
        "Old Bonegrinder",
        "The ground floor of the windmill is cluttered with old millstones and mysterious "
        "sacks. The smell of baking is stronger here, mixed with something rotten. Flour "
        "covers everything in a fine layer. Stairs lead up to a kitchen, a trapdoor "
        "leads down to a basement, and the exit is behind you.",
    )

    kitchen: Room = Room(
        "kitchen",
        "Hag's Kitchen",
        "The smell hits you first - sweetness masking something rotten. Pastries cool on a "
        "wooden table beside a massive oven. The oven is large enough to fit a child. "
        "A closer look at the ingredients reveals they are... wrong. Very wrong. "
        "Stairs lead down to the mill floor and up to a bedroom. You shouldn't be here.",
    )

    bedroom: Room = Room(
        "bedroom",
        "Hag's Bedroom",
        "A filthy bedroom with a straw mattress and piles of stolen clothes. Strange dolls "
        "made of sticks and bone hang from the ceiling. A cracked mirror shows reflections "
        "that don't quite match reality. Stairs lead down to the kitchen, and a rickety "
        "ladder leads up to the attic.",
    )

    millattic: Room = Room(
        "millattic",
        "Windmill Attic",
        "Dusty and cramped, the attic contains several wooden crates. Muffled sounds come "
        "from one of them - crying, perhaps. The floorboards creak ominously. A ladder leads "
        "back down to the bedroom below.",
    )

    millbasement: Room = Room(
        "millbasement",
        "Root Cellar",
        "Cold earth walls press close in this cramped cellar. Bones are scattered across the "
        "floor - chicken bones, you hope. Jars of preserved... things line rough shelves. "
        "The smell of decay is overwhelming.",
        is_dark=True,
    )

    # ===== ARGYNVOSTHOLT =====

    approach: Room = Room(
        "approach",
        "Overgrown Path",
        "A path choked with dead weeds leads to a ruined manor. The building was once grand - "
        "a dragon statue still stands proud atop the main tower, despite centuries of decay. "
        "Ghostly lights flicker in the windows. The main hall is visible through broken doors "
        "to the east. The stone bridge lies to the north.",
        is_outdoor=True,
    )

    hall: Room = Room(
        "hall",
        "Ruined Great Hall",
        "The once-magnificent hall is now open to the elements. A massive dragon skull hangs "
        "above a cold fireplace - not a true dragon, but the sigil of the Order of the Silver "
        "Dragon. Tattered banners bearing the same symbol hang from the walls. Passages lead "
        "to a chapel to the north, quarters to the south, and the overgrown approach to the west. "
        "Stone steps descend to a tomb below.",
    )

    argchapel: Room = Room(
        "argchapel",
        "Destroyed Chapel",
        "This chapel has been desecrated. The altar is overturned, holy symbols smashed, and "
        "dark stains mark the floor. Yet something lingers here - a cold presence filled with "
        "ancient rage. The great hall lies to the south.",
    )

    quarters: Room = Room(
        "quarters",
        "Knights' Quarters",
        "Rows of beds line the walls, their occupants long dead. Armor stands on wooden racks, "
        "tarnished but intact. Personal effects - letters, tokens, small portraits - speak to "
        "the knights who once lived here. The great hall lies to the north, and a tower stair "
        "leads up.",
    )

    argtower: Room = Room(
        "argtower",
        "Watchtower",
        "From this crumbling tower, you can see for miles - the Svalich Woods, the village "
        "of Barovia, and in the distance, Castle Ravenloft looming over all. A spectral knight "
        "might once have stood watch here.",
    )

    vault: Room = Room(
        "vault",
        "Hidden Vault",
        "Behind a secret panel lies a small vault. The Order kept their most precious items "
        "here - weapons blessed against the undead, relics of their dragon patron. Most have "
        "been looted, but something might remain.",
        is_dark=True,
    )

    argtomb: Room = Room(
        "argtomb",
        "Argynvost's Tomb",
        "This grand chamber was built to honor the silver dragon Argynvost, who fell defending "
        "Barovia. His bones were stolen long ago by Strahd, but the memorial remains. Cold "
        "light filters through stained glass depicting the dragon in life.",
    )

    # ===== VALLAKI =====

    towngate: Room = Room(
        "towngate",
        "Vallaki Gates",
        "Heavy wooden gates mark the entrance to Vallaki. Guards eye you suspiciously, "
        "checking for signs of vampirism. Posters proclaim the 'Festival of the Blazing Sun' - "
        "apparently, mandatory happiness is enforced here. The main street leads west into town. "
        "The bridge and road to Barovia lie to the east.",
        is_outdoor=True,
    )

    street: Room = Room(
        "street",
        "Main Street",
        "The main street of Vallaki is lined with shops and homes. Colorful decorations hang "
        "everywhere, but the townspeople's smiles look forced. Guards patrol constantly. "
        "A sign points to the Blue Water Inn to the south. St. Andral's Church stands to the "
        "north. The burgomaster's mansion looms to the west, and the town gates lie to the east.",
        is_outdoor=True,
    )

    inn: Room = Room(
        "inn",
        "Blue Water Inn",
        "This inn is the most welcoming place you've found in Barovia. A fire crackles in the "
        "hearth, and the smell of cooking food fills the air. The innkeepers, the Martikov family, "
        "seem genuinely kind. A grizzled hunter nurses a drink in the corner. "
        "The main street lies to the north. A door leads east to the stockyard. Stairs lead up "
        "to an attic.",
    )

    attic: Room = Room(
        "attic",
        "Inn Attic",
        "The dusty attic seems empty at first, but you notice signs of habitation - bedrolls, "
        "scattered feathers, a crude nest. Someone - or something - has been living here. "
        "The space feels oddly safe.",
    )

    stockyard: Room = Room(
        "stockyard",
        "Stockyard",
        "A grim stockyard where wolf heads are displayed on spikes - the Baron's trophies. "
        "An executioner's block stands in the center, stained dark with old blood. The smell "
        "of death lingers. This is where the Baron's 'justice' is carried out.",
        is_outdoor=True,
    )

    mansion: Room = Room(
        "mansion",
        "Burgomaster's Mansion",
        "Baron Vallakovich's mansion is garishly decorated with sun symbols and banners "
        "proclaiming 'ALL WILL BE WELL.' Guards stand rigid at every door. The Baron himself "
        "paces the main hall, muttering about the upcoming festival. The main street lies to "
        "the east. A door leads down to the mansion dungeon.",
    )

    mansiondungeon: Room = Room(
        "mansiondungeon",
        "Mansion Dungeon",
        "The Baron's private dungeon is a place of horror. Torture implements line the walls. "
        "Prisoners - those who failed to be happy enough - moan in their cells. The guards "
        "pretend not to hear.",
        is_dark=True,
    )

    vallakichurch: Room = Room(
        "vallakichurch",
        "St. Andral's Church",
        "This church stands as a beacon of hope in Vallaki. Father Lucian tends to his flock "
        "with genuine care. The church is protected by the bones of St. Andral - or it was, "
        "until they were stolen. Without them, even this sanctuary is not safe. The main "
        "street lies to the south.",
    )

    camp: Room = Room(
        "camp",
        "Vistani Camp",
        "A Vistani camp sits outside Vallaki's walls. These wanderers come and go as they "
        "please - the only people in Barovia who can leave. They trade in secrets and dreams, "
        "and are not above deception. The lake shore is visible to the north. The town gates "
        "lie to the east.",
        is_outdoor=True,
    )

    lake: SwampRoom = SwampRoom(
        "lake",
        "Lake Zarovich",
        "The dark waters of Lake Zarovich lap against a rocky shore. The lake is cold and "
        "deep - some say bottomless. Fishermen tell tales of things seen in the depths, "
        "shapes that shouldn't exist. A rowboat is tied to a small dock. The Vistani camp "
        "lies to the south. Drop treasure here to offer it to the depths.",
        treasure_destination="lake",  # Items stay in the lake (could be retrieved)
        awards_points=True,
    )

    # ===== CASTLE RAVENLOFT =====

    courtyard: Room = Room(
        "courtyard",
        "Castle Courtyard",
        "Massive stone walls loom overhead, blocking what little light penetrates Barovia's "
        "eternal gloom. Gargoyles perch on every ledge, their eyes seeming to follow your "
        "movements. The grand entrance beckons to the east, its doors hanging open in mocking "
        "invitation. The howl of wolves echoes from somewhere far below. The gates lie to "
        "the west.",
        is_outdoor=True,
    )

    entrance: Room = Room(
        "entrance",
        "Grand Entrance Hall",
        "Dust covers everything in this cavernous hall. Twin staircases sweep upward to a "
        "balcony. Suits of armor stand silent sentinel along the walls, and you can't shake "
        "the feeling they're watching you. A chandelier hangs overhead, its candles burning "
        "with an eerie blue flame. The courtyard lies to the west, the dining hall to the "
        "north, and stairs lead up into the castle.",
    )

    dining: Room = Room(
        "dining",
        "Dining Hall",
        "A long table is set for a feast that has waited centuries for guests. The food looks "
        "fresh - impossibly so. Candles burn without melting. A figure sits at the head of the "
        "table, but vanishes when you look directly at it. Strahd's mockery of hospitality. "
        "The entrance hall lies to the south, and the spiral staircase to the east.",
    )

    stairs: Room = Room(
        "stairs",
        "Spiral Staircase",
        "A massive spiral staircase connects the castle's many levels. The steps are worn "
        "smooth by centuries of use. Cold drafts sweep up and down, carrying whispers and "
        "the occasional scream. Passages lead off in multiple directions.",
    )

    castlestudy: Room = Room(
        "castlestudy",
        "Strahd's Study",
        "This private study is filled with books and maps. Many detail the history of Barovia, "
        "others the nature of vampirism. A portrait of a beautiful woman hangs above the "
        "fireplace - Tatyana, the object of Strahd's eternal obsession. A tome bound in "
        "black leather sits on the desk. The spiral staircase lies to the south.",
    )

    castlecrypt: Room = Room(
        "castlecrypt",
        "Castle Crypt",
        "Rows of stone coffins fill this underground chamber. Many bear the names of Strahd's "
        "victims and servants. The air is cold and still, and the darkness seems to press "
        "against your light source. Stairs lead up to the castle. Passages lead east to the "
        "master's tomb and west to the dungeon.",
        is_dark=True,
    )

    tomb: Room = Room(
        "tomb",
        "Strahd's Tomb",
        "The heart of Castle Ravenloft. An ornate coffin sits on a raised dais, surrounded by "
        "treasure accumulated over centuries. This is where the Dark Lord rests. The walls are "
        "covered in murals depicting Strahd's life and crimes. A crystal heart pulses with "
        "red light in an alcove - the Heart of Sorrow, source of his power. The crypt lies "
        "to the west.",
        is_dark=True,
    )

    treasury: Room = Room(
        "treasury",
        "Castle Treasury",
        "Gold and jewels are piled carelessly in this chamber - wealth means nothing to an "
        "immortal. Among the treasure lie items of true value: enchanted weapons, magical "
        "artifacts, and perhaps the legendary Sunsword, bane of vampires. The spiral "
        "staircase lies to the north.",
    )

    castledungeon: Room = Room(
        "castledungeon",
        "Castle Dungeon",
        "The dungeons of Castle Ravenloft have held countless prisoners over the centuries. "
        "Most didn't survive long. Chains hang from the walls, some still bearing bones. "
        "The screams of the damned echo through these halls. The crypt lies to the east.",
        is_dark=True,
    )

    tower: Room = Room(
        "tower",
        "High Tower",
        "From the highest point of Castle Ravenloft, all of Barovia is visible - a land "
        "trapped in eternal twilight, surrounded by impenetrable mists. Strahd has stood "
        "here countless times, surveying his prison. The view is beautiful and terrible. "
        "Stairs lead back down into the castle.",
    )

    castlechapel: Room = Room(
        "castlechapel",
        "Desecrated Chapel",
        "Once a place of worship, this chapel has been corrupted by Strahd's presence. "
        "Holy symbols have been inverted, the altar stained with old blood. Yet something "
        "remains - the Icon of Ravenloft, hidden behind the altar, still holds power. "
        "The spiral staircase lies to the west, and a dark passage leads north.",
    )

    coffin: Room = Room(
        "coffin",
        "Coffin Room",
        "Rows of empty coffins line this hidden chamber - resting places for Strahd's vampire "
        "spawn. Most are empty now, their occupants hunting in the night. But some are "
        "occupied, waiting for sunset. The chapel lies to the south.",
        is_dark=True,
    )

    # ===== CRYPTKEEPER'S MAZE =====
    # A puzzle dungeon beneath the village graveyard

    maze_entry: Room = Room(
        "maze_entry",
        "Maze Entrance",
        "Stone steps descend into an ancient labyrinth. The air is cold and stale, "
        "untouched for centuries. Faded murals on the walls depict robed figures "
        "performing strange rituals. An iron gate blocks the passage north. "
        "Steps lead back up to the crypt.",
        is_dark=True,
    )

    maze_pool: Room = Room(
        "maze_pool",
        "Flooded Chamber",
        "A vast chamber stretches before you, its floor covered in dark, still water. "
        "The ceiling is lost in shadow. Stone pillars rise from the depths, and you "
        "can barely make out stepping stones crossing to the far side. Without light, "
        "this place would be a death trap. A drowned corpse floats face-down nearby.",
        is_dark=True,
    )

    maze_crossing: Room = Room(
        "maze_crossing",
        "Three-Way Crossing",
        "The maze opens into a junction where three passages meet. The walls here are "
        "carved with warnings in an ancient script. To the west, you hear a faint "
        "humming. To the east, the smell of old parchment. The flooded chamber lies "
        "to the south.",
    )

    maze_mirror: Room = Room(
        "maze_mirror",
        "Hall of Mirrors",
        "Four large mirrors line the walls of this octagonal chamber - one at each "
        "cardinal direction. Each mirror shows a different reflection: the eastern "
        "shows a blazing sun, the southern shows dancing shadows, the western shows "
        "a pale moon, and the northern shows twinkling stars. A riddle is carved "
        "into a pedestal at the center.",
    )
    # Initialize mirror sequence tracking
    maze_mirror.mirror_sequence = []  # type: ignore[attr-defined]

    maze_library: Room = Room(
        "maze_library",
        "Dusty Archive",
        "Ancient tomes line the walls of this forgotten library. Dust motes dance in "
        "the air. A ghostly whisper echoes through the chamber as you enter: "
        "'Answer my riddle, seeker, or face the wrath of those who failed before you.' "
        "A tome on a central pedestal glows with faint light. The crossing lies west.",
    )

    maze_chapel: Room = Room(
        "maze_chapel",
        "Sealed Chapel",
        "A small underground chapel, its altar still intact. Holy symbols of a "
        "forgotten faith adorn the walls. The air feels heavy with expectation. "
        "A passage north is blocked by a shimmering barrier of light. Something "
        "must be spoken to break the seal. The archive lies south.",
    )

    maze_sanctum: Room = Room(
        "maze_sanctum",
        "Cryptkeeper's Sanctum",
        "You have reached the heart of the maze! This circular chamber was once "
        "the resting place of the Cryptkeeper, guardian of Barovia's oldest secrets. "
        "His bones rest peacefully in an ornate sarcophagus. Treasure and relics "
        "are piled around the room - rewards for those clever enough to reach here.",
        is_dark=True,
    )

    # Add all rooms to the dictionary
    rooms["square"] = square
    rooms["tavern"] = tavern
    rooms["cellar"] = cellar
    rooms["church"] = church
    rooms["undercroft"] = undercroft
    rooms["shop"] = shop
    rooms["manor"] = manor
    rooms["study"] = study
    rooms["graveyard"] = graveyard
    rooms["crypt"] = crypt
    rooms["road"] = road
    rooms["crossroads"] = crossroads
    rooms["woods"] = woods
    rooms["clearing"] = clearing
    rooms["barrow"] = barrow
    rooms["pool"] = pool
    rooms["wagon"] = wagon
    rooms["hollow"] = hollow
    rooms["bridge"] = bridge
    rooms["castlegates"] = castlegates
    rooms["mists"] = mists
    rooms["millpath"] = millpath
    rooms["mill"] = mill
    rooms["kitchen"] = kitchen
    rooms["bedroom"] = bedroom
    rooms["millattic"] = millattic
    rooms["millbasement"] = millbasement
    rooms["approach"] = approach
    rooms["hall"] = hall
    rooms["argchapel"] = argchapel
    rooms["quarters"] = quarters
    rooms["argtower"] = argtower
    rooms["vault"] = vault
    rooms["argtomb"] = argtomb
    rooms["towngate"] = towngate
    rooms["street"] = street
    rooms["inn"] = inn
    rooms["attic"] = attic
    rooms["stockyard"] = stockyard
    rooms["mansion"] = mansion
    rooms["mansiondungeon"] = mansiondungeon
    rooms["vallakichurch"] = vallakichurch
    rooms["camp"] = camp
    rooms["lake"] = lake
    rooms["courtyard"] = courtyard
    rooms["entrance"] = entrance
    rooms["dining"] = dining
    rooms["stairs"] = stairs
    rooms["castlestudy"] = castlestudy
    rooms["castlecrypt"] = castlecrypt
    rooms["tomb"] = tomb
    rooms["treasury"] = treasury
    rooms["castledungeon"] = castledungeon
    rooms["tower"] = tower
    rooms["castlechapel"] = castlechapel
    rooms["coffin"] = coffin
    rooms["maze_entry"] = maze_entry
    rooms["maze_pool"] = maze_pool
    rooms["maze_crossing"] = maze_crossing
    rooms["maze_mirror"] = maze_mirror
    rooms["maze_library"] = maze_library
    rooms["maze_chapel"] = maze_chapel
    rooms["maze_sanctum"] = maze_sanctum

    # Baron's secret vault - hidden behind loose stone in dungeon
    baron_vault: Room = Room(
        "baron_vault",
        "Baron's Secret Vault",
        "A cramped space behind the dungeon wall. The air is thick with the smell of "
        "old blood and secrets. Documents are scattered about - records of the Baron's "
        "'disappeared' citizens, those who refused to smile at his festivals. "
        "Among the horrors, you see a strongbox and some treasures.",
        is_dark=True,
    )
    rooms["baron_vault"] = baron_vault


def connect_exits(rooms: Dict[str, Room]) -> None:
    """Connect all rooms with appropriate exits."""

    # ===== VILLAGE OF BAROVIA =====
    rooms["square"].exits = {
        "north": "church",
        "east": "tavern",
        "south": "road",
        "west": "manor",
        "southwest": "shop",
    }

    rooms["tavern"].exits = {
        "west": "square",
        # "down": "cellar" - will be revealed by hidden trapdoor
    }

    rooms["cellar"].exits = {
        "up": "tavern",
    }

    rooms["church"].exits = {
        "south": "square",
        "west": "graveyard",
        # "down": "undercroft" - revealed when grate is opened
    }

    rooms["undercroft"].exits = {
        "up": "church",
    }

    rooms["shop"].exits = {
        "northeast": "square",
    }

    rooms["manor"].exits = {
        "east": "square",
        "north": "study",
    }

    rooms["study"].exits = {
        "south": "manor",
    }

    rooms["graveyard"].exits = {
        "east": "church",
        "in": "crypt",
    }

    rooms["crypt"].exits = {
        "out": "graveyard",
        "down": "maze_entry",
    }

    # ===== SVALICH WOODS =====
    rooms["road"].exits = {
        "north": "square",
        "south": "crossroads",
    }

    rooms["crossroads"].exits = {
        "north": "road",
        "south": "pool",
        "east": "castlegates",
        "west": "bridge",
        "southeast": "woods",
    }

    rooms["woods"].exits = {
        "northwest": "crossroads",
        "west": "clearing",
        "south": "hollow",
    }

    rooms["clearing"].exits = {
        "east": "woods",
        "west": "millpath",
        # "down": "barrow" - hidden, revealed when standing stones are aligned
    }

    rooms["barrow"].exits = {
        "up": "clearing",
    }

    rooms["pool"].exits = {
        "north": "crossroads",
        "in": "wagon",
    }

    rooms["wagon"].exits = {
        "out": "pool",
    }

    rooms["hollow"].exits = {
        "north": "woods",
    }

    rooms["bridge"].exits = {
        "east": "crossroads",
        "west": "towngate",
        "south": "approach",
    }

    rooms["castlegates"].exits = {
        "west": "crossroads",
        "east": "courtyard",
    }

    rooms["mists"].exits = {
        "south": "crossroads",
        "north": "crossroads",
        "east": "crossroads",
        "west": "crossroads",
    }

    # ===== OLD BONEGRINDER =====
    rooms["millpath"].exits = {
        "east": "clearing",
        "in": "mill",
    }

    rooms["mill"].exits = {
        "out": "millpath",
        "up": "kitchen",
        "down": "millbasement",
    }

    rooms["kitchen"].exits = {
        "down": "mill",
        "up": "bedroom",
    }

    rooms["bedroom"].exits = {
        "down": "kitchen",
        "up": "millattic",
    }

    rooms["millattic"].exits = {
        "down": "bedroom",
    }

    rooms["millbasement"].exits = {
        "up": "mill",
    }

    # ===== ARGYNVOSTHOLT =====
    rooms["approach"].exits = {
        "east": "hall",
        "north": "bridge",
    }

    rooms["hall"].exits = {
        "west": "approach",
        "north": "argchapel",
        "south": "quarters",
        "down": "argtomb",
    }

    rooms["argchapel"].exits = {
        "south": "hall",
    }

    rooms["quarters"].exits = {
        "north": "hall",
        "up": "argtower",
        # "in": "vault" - hidden, revealed by searching
    }

    rooms["argtower"].exits = {
        "down": "quarters",
    }

    rooms["vault"].exits = {
        "out": "quarters",
    }

    rooms["argtomb"].exits = {
        "up": "hall",
    }

    # ===== VALLAKI =====
    rooms["towngate"].exits = {
        "east": "bridge",
        "west": "street",
        "southwest": "camp",
    }

    rooms["street"].exits = {
        "east": "towngate",
        "south": "inn",
        "north": "vallakichurch",
        "west": "mansion",
    }

    rooms["inn"].exits = {
        "north": "street",
        "up": "attic",
        "east": "stockyard",
    }

    rooms["attic"].exits = {
        "down": "inn",
    }

    rooms["stockyard"].exits = {
        "west": "inn",
    }

    rooms["mansion"].exits = {
        "east": "street",
        "down": "mansiondungeon",
    }

    rooms["mansiondungeon"].exits = {
        "up": "mansion",
    }

    rooms["vallakichurch"].exits = {
        "south": "street",
    }

    rooms["camp"].exits = {
        "north": "lake",
        "northeast": "towngate",
    }

    rooms["lake"].exits = {
        "south": "camp",
    }

    # ===== CASTLE RAVENLOFT =====
    rooms["courtyard"].exits = {
        "west": "castlegates",
        "east": "entrance",
    }

    rooms["entrance"].exits = {
        "west": "courtyard",
        "north": "dining",
        "up": "stairs",
    }

    rooms["dining"].exits = {
        "south": "entrance",
        "east": "stairs",
    }

    rooms["stairs"].exits = {
        "down": "castlecrypt",
        "up": "tower",
        "north": "castlestudy",
        "south": "treasury",
        "west": "dining",
        "east": "castlechapel",
        "out": "entrance",
    }

    rooms["castlestudy"].exits = {
        "south": "stairs",
    }

    rooms["castlecrypt"].exits = {
        "up": "stairs",
        "east": "tomb",
        "west": "castledungeon",
    }

    rooms["tomb"].exits = {
        "west": "castlecrypt",
        # "in": "coffin" - hidden area
    }

    rooms["treasury"].exits = {
        "north": "stairs",
    }

    rooms["castledungeon"].exits = {
        "east": "castlecrypt",
    }

    rooms["tower"].exits = {
        "down": "stairs",
    }

    rooms["castlechapel"].exits = {
        "west": "stairs",
        "north": "coffin",
    }

    rooms["coffin"].exits = {
        "south": "castlechapel",
    }

    # ===== CRYPTKEEPER'S MAZE =====
    rooms["maze_entry"].exits = {
        "up": "crypt",
        # "north": "maze_pool" - unlocked by maze_gate
    }

    rooms["maze_pool"].exits = {
        "south": "maze_entry",
        "north": "maze_crossing",
    }

    rooms["maze_crossing"].exits = {
        "south": "maze_pool",
        "west": "maze_mirror",
        "east": "maze_library",
    }

    rooms["maze_mirror"].exits = {
        "east": "maze_crossing",
    }

    rooms["maze_library"].exits = {
        "west": "maze_crossing",
        # "north": "maze_chapel" - unlocked by riddle
    }

    rooms["maze_chapel"].exits = {
        "south": "maze_library",
        # "north": "maze_sanctum" - unlocked by saint's name
    }

    rooms["maze_sanctum"].exits = {
        "south": "maze_chapel",
    }

    # Baron's vault - only accessible after solving puzzle
    rooms["baron_vault"].exits = {
        "out": "mansiondungeon",
    }


def compute_swamp_paths(rooms: Dict[str, Room]) -> None:
    """Precompute shortest path direction to the lake for all outdoor rooms.

    Uses BFS starting from the lake and working outward. For each outdoor
    room, stores the direction to move to get one step closer to the lake.
    """
    import logging
    from collections import deque
    from typing import List, Tuple

    logger = logging.getLogger(__name__)
    logger.info("Computing swamp paths from lake...")

    target = "lake"

    # Guard clause: if lake doesn't exist, nothing to compute
    if target not in rooms:
        logger.warning("Lake room not found, skipping swamp path computation.")
        return

    # Build reverse adjacency: for each room, which rooms lead TO it and via what direction
    reverse_adj: Dict[str, List[Tuple[str, str]]] = {rid: [] for rid in rooms}
    for room_id, room in rooms.items():
        for direction, dest_id in room.exits.items():
            if dest_id in reverse_adj:
                reverse_adj[dest_id].append((room_id, direction))

    # BFS from target outward
    visited: set[str] = {target}
    queue: deque[str] = deque([target])
    outdoor_count = 0

    while queue:
        current = queue.popleft()
        # For each room that has an exit leading to current
        for source_id, direction in reverse_adj[current]:
            if source_id not in visited:
                visited.add(source_id)
                source_room = rooms[source_id]
                # Only set swamp_direction for outdoor rooms
                if getattr(source_room, "is_outdoor", False):
                    source_room.swamp_direction = direction
                    outdoor_count += 1
                    logger.debug(f"  {source_id}: swamp_direction = {direction}")
                queue.append(source_id)

    logger.info(f"Swamp paths computed for {outdoor_count} outdoor rooms.")


def add_container_items(rooms: Dict[str, Room]) -> None:
    """Add container items to rooms."""

    # Coffin in crypt
    coffin_container: ContainerItem = ContainerItem(
        "coffin",
        "coffin_crypt",
        "A stone coffin with a heavy lid.",
        weight=200,
        value=0,
        capacity_limit=5,
        capacity_weight=30,
        takeable=False,
    )
    coffin_container.add_interaction(
        verb="open",
        target_state="open",
        message="You push the heavy lid aside, revealing the coffin's contents.",
        from_state="closed",
    )
    coffin_container.add_interaction(
        verb="close",
        target_state="closed",
        message="You slide the coffin lid back into place.",
        from_state="open",
    )
    rooms["crypt"].add_item(coffin_container)

    # Cage in mill attic - children trapped by hag
    # Breaking it requires the executioner's axe from stockyard
    # Freeing children has CONSEQUENCES - alerts the hag!
    cage: StatefulItem = StatefulItem(
        "cage",
        "hag_cage",
        "An iron cage holds several small, whimpering figures.",
        weight=200,
        value=0,
        takeable=False,
        state="locked",
        synonyms=["iron cage", "bars", "prison", "cell", "children cage"],
    )
    cage.add_state_description(
        "locked",
        "An iron cage holds several children. Their hollow eyes plead for rescue. The lock looks sturdy.",
    )
    cage.add_state_description(
        "broken",
        "The cage lies open, its bars bent and broken. The children have fled into the night.",
    )
    cage.add_interaction(
        verb="examine",
        message="Terrified children huddle inside the iron cage. They're too frightened to speak, "
        "but their eyes beg for salvation. The cage is locked tight - "
        "you'd need something powerful to break through.",
    )
    cage.add_interaction(
        verb="break",
        message="You strain against the bars, but the iron is too strong. "
        "You'd need something heavier - an axe perhaps.",
    )
    cage.add_interaction(
        verb="open",
        message="The cage is locked with a heavy padlock. You can't open it normally.",
    )
    cage.add_interaction(
        verb="use",
        required_instrument="axe",
        target_state="broken",
        message="You swing the executioner's axe with all your might! CLANG! CLANG! "
        "The iron bars buckle and break! The children scramble out, crying with relief. "
        "'Run!' you urge them, and they flee down the stairs into the night.\n\n"
        "From below, you hear a TERRIBLE SHRIEK. The hag has noticed.\n"
        "'MY PRETTIES! WHO DARES?!' Her voice echoes through the mill. "
        "You hear heavy footsteps on the stairs. She's coming for you.",
        from_state="locked",
    )
    cage.add_interaction(
        verb="chop",
        required_instrument="axe",
        target_state="broken",
        message="You chop at the cage bars with savage determination! "
        "The iron gives way and the children pour out, sobbing with gratitude. "
        "As they flee, a blood-curdling scream rises from below. "
        "'NOOOOO! MY CHILDREN!' The hag is coming!",
        from_state="locked",
    )
    rooms["millattic"].add_item(cage)


def add_stateful_items(rooms: Dict[str, Room]) -> None:
    """Add all stateful interactive objects to rooms."""

    # Tavern rug hiding trapdoor
    rug: StatefulItem = StatefulItem(
        "rug",
        "tavern_rug",
        "A worn rug lies near the back wall.",
        weight=20,
        value=0,
        takeable=False,
        state="flat",
        synonyms=["carpet", "mat", "tapestry", "worn rug"],
    )
    rug.add_state_description("flat", "A worn rug lies near the back wall.")
    rug.add_state_description(
        "moved", "A worn rug has been pushed aside, revealing a trapdoor."
    )
    rug.set_room_id("tavern")
    rug.add_interaction(
        verb="move",
        target_state="moved",
        message="You push the rug aside, revealing a trapdoor leading down.",
        from_state="flat",
        add_exit=("down", "cellar"),
    )
    rug.add_interaction(
        verb="pull",
        target_state="moved",
        message="You pull the rug aside, revealing a trapdoor underneath.",
        from_state="flat",
        add_exit=("down", "cellar"),
    )
    rooms["tavern"].add_item(rug)

    # Church grate to undercroft
    grate: StatefulItem = StatefulItem(
        "grate",
        "church_grate",
        "An iron grate is set into the floor near the altar.",
        weight=100,
        value=0,
        takeable=False,
        state="closed",
        synonyms=["grille", "grid", "iron grate", "trapdoor", "floor grate"],
    )
    grate.add_state_description(
        "closed", "An iron grate is set into the floor near the altar."
    )
    grate.add_state_description(
        "open", "The iron grate stands open, revealing steps leading down."
    )
    grate.set_room_id("church")
    grate.add_interaction(
        verb="open",
        target_state="open",
        message="With effort, you pull the heavy grate open. Stone steps descend into darkness.",
        from_state="closed",
        add_exit=("down", "undercroft"),
    )
    grate.add_interaction(
        verb="close",
        target_state="closed",
        message="You lower the iron grate back into place.",
        from_state="open",
        remove_exit="down",
    )
    rooms["church"].add_item(grate)

    # === DRAGON'S BEACON PUZZLE ===
    # === ARGYNVOSTHOLT ALTAR (argchapel) ===
    # Must restore the altar before the beacon can be lit
    # Creates a 3-step chain: altar -> skull -> light

    arg_altar: StatefulItem = StatefulItem(
        "ruined altar",
        "arg_altar",
        "A ruined altar lies at the front of the chapel.",
        synonyms=["altar", "dragon altar", "knights altar"],
        weight=500,
        value=0,
        takeable=False,
        state="ruined",
    )
    arg_altar.add_state_description(
        "ruined",
        "The altar lies in ruins - toppled stones and shattered icons. "
        "It could perhaps be restored by someone who respects the Order.",
    )
    arg_altar.add_state_description(
        "restored",
        "The altar has been restored to its former glory. "
        "A silver dragon banner hangs proudly behind it.",
    )
    arg_altar.set_room_id("argchapel")
    arg_altar.add_interaction(
        verb="restore",
        target_state="restored",
        message="You carefully right the fallen stones and reassemble the altar. "
        "As you work, you feel the approval of the dragon knights watching over you. "
        "When finished, the altar glows faintly with silver light. "
        "The chapel feels sanctified once more - perhaps now the beacon can be lit.",
    )
    arg_altar.add_interaction(
        verb="repair",
        target_state="restored",
        message="You repair the damaged altar piece by piece. "
        "With each stone you place, you feel the spirits of the Order grow stronger. "
        "When complete, a faint silver aura surrounds the restored altar.",
    )
    arg_altar.add_interaction(
        verb="examine",
        message="The altar was once magnificent - carved with images of a silver dragon "
        "protecting knights in battle. Now it lies in ruins, desecrated by Strahd's forces. "
        "It could be restored with care and respect.",
    )
    rooms["argchapel"].add_item(arg_altar)

    # Return Argynvost's skull to the beacon and light it to honor the knights
    # The skull is found in argtomb (Strahd's castle crypt)
    # Completing this makes the revenant friendly

    beacon: StatefulItem = StatefulItem(
        "beacon",
        "dragon_beacon",
        "An unlit brazier stands beneath the dragon skull mount.",
        weight=500,
        value=0,
        takeable=False,
        state="unlit",
        synonyms=["brazier", "torch holder", "fire", "dragon beacon"],
    )
    beacon.add_state_description(
        "unlit",
        "An unlit brazier stands beneath the empty dragon skull mount on the wall.",
    )
    beacon.add_state_description(
        "skull_placed",
        "Argynvost's skull rests on the brazier, waiting to be honored with flame.",
    )
    beacon.add_state_description(
        "lit",
        "Silver flames dance in the brazier beneath Argynvost's skull! "
        "The entire hall is bathed in warm, protective light.",
    )
    beacon.set_room_id("hall")
    beacon.add_interaction(
        verb="place",
        required_instrument="skull",
        target_state="skull_placed",
        message="You reverently place Argynvost's skull upon the brazier. "
        "The dragon's empty eye sockets seem to gaze upon you with approval. "
        "Now it needs only fire to complete the memorial.",
        from_state="unlit",
    )
    beacon.add_interaction(
        verb="light",
        target_state="lit",
        message="You touch flame to the brazier. SILVER FIRE erupts, engulfing the skull! "
        "But it does not burn - instead, a spectral dragon rises from the flames, "
        "letting out a triumphant roar! The hall fills with warm silver light. "
        "You hear armor clanking behind you - the revenant knight bows deeply. "
        "'You have honored our lord,' he intones. 'The Order is in your debt.'",
        from_state="skull_placed",
        conditional_fn=altar_restored_and_skull_placed,
    )
    beacon.add_interaction(
        verb="light",
        message="You touch flame to the brazier, but the fire sputters and dies. "
        "Something feels incomplete... The chapel altar must first be restored "
        "before the beacon can accept the dragon's flame.",
        from_state="skull_placed",
        conditional_fn=lambda p, gs: not altar_restored(p, gs)
        and player_has_light(p, gs),
    )
    beacon.add_interaction(
        verb="light",
        message="You need a source of fire - a torch or lantern - to light the beacon.",
        from_state="skull_placed",
    )
    beacon.add_interaction(
        verb="examine",
        message="A grand brazier designed to hold Argynvost's skull. "
        "The mount above is empty - the skull was stolen by Strahd long ago. "
        "Returning and lighting it would honor the fallen dragon and his knights.",
    )
    rooms["hall"].add_item(beacon)

    # === KNIGHT'S TRIAL PUZZLE ===
    # Must kneel before the inscription, then push the wall
    # This teaches players that the Order values humility and respect

    inscription: StatefulItem = StatefulItem(
        "inscription",
        "knight_inscription",
        "An inscription is carved into a stone plaque on the wall.",
        weight=10000,
        value=0,
        takeable=False,
        state="waiting",
    )
    inscription.add_state_description(
        "waiting",
        "An inscription is carved into a stone plaque: 'Only the worthy may enter. Prove your valor.'",
    )
    inscription.add_state_description(
        "honored", "The inscription glows faintly. You have proven your worth."
    )
    inscription.set_room_id("quarters")
    inscription.add_interaction(
        verb="read",
        message="The inscription reads: 'Only the worthy may enter. Prove your valor. "
        "The knights of this order valued humility above all else.'",
    )
    inscription.add_interaction(
        verb="kneel",
        target_state="honored",
        message="You kneel before the inscription in respect to the fallen knights. "
        "The stone glows faintly and a warmth spreads through you. "
        "You have proven yourself worthy.",
        from_state="waiting",
    )
    inscription.add_interaction(
        verb="bow",
        target_state="honored",
        message="You bow deeply before the inscription, honoring the knights who fell here. "
        "The stone glows and you feel accepted.",
        from_state="waiting",
    )
    rooms["quarters"].add_item(inscription)

    # Hidden wall in quarters leading to vault
    wall: StatefulItem = StatefulItem(
        "wall",
        "quarters_wall",
        "The stone wall here looks slightly different from the rest.",
        weight=10000,
        value=0,
        takeable=False,
        state="solid",
        synonyms=["panel", "secret wall", "hidden wall", "stone wall"],
    )
    wall.add_state_description(
        "solid", "The stone wall here looks slightly different from the rest."
    )
    wall.add_state_description(
        "open", "A section of wall has swung open, revealing a hidden vault."
    )
    wall.set_room_id("quarters")
    wall.add_interaction(
        verb="push",
        target_state="open",
        message="You push against the wall. It recognizes your worth and swings inward, "
        "revealing a hidden vault filled with the Order's treasures!",
        from_state="solid",
        add_exit=("in", "vault"),
        conditional_fn=knight_honored,
    )
    wall.add_interaction(
        verb="push",
        message="You push against the wall, but it resists. You feel... judged. Unworthy. "
        "The inscription on the stone plaque might hold the key.",
        from_state="solid",
    )
    wall.add_interaction(
        verb="examine",
        message="Looking closely, you notice the mortar here is different - fresher, perhaps. "
        "An inscription on a nearby plaque catches your eye.",
    )
    rooms["quarters"].add_item(wall)

    # Skull in Argynvost's tomb (quest item)
    skull: StatefulItem = StatefulItem(
        "skull",
        "dragon_skull",
        "The dragon skull that once hung in the great hall lies here, stolen by Strahd long ago.",
        weight=25,
        value=100,
        takeable=True,
        state="here",
    )
    skull.add_state_description(
        "here", "The dragon skull that once hung in the great hall lies here."
    )
    skull.add_interaction(
        verb="examine",
        message="The skull of Argynvost, the silver dragon who died defending Barovia. "
        "His spirit cannot rest until this is returned to the manor.",
    )
    rooms["argtomb"].add_item(skull)

    # Heart of Sorrow in Strahd's tomb - requires sunsword to destroy
    crystal_heart: StatefulItem = StatefulItem(
        "heart",
        "heart_of_sorrow",
        "A massive crystal heart pulses with blood-red light, protected by an invisible barrier.",
        weight=50,
        value=0,
        takeable=False,
        state="intact",
    )
    crystal_heart.add_state_description(
        "intact",
        "A massive crystal heart pulses with blood-red light, protected by an invisible barrier.",
    )
    crystal_heart.add_state_description(
        "destroyed", "Shattered crystal fragments are all that remain of the heart."
    )
    crystal_heart.set_room_id("tomb")
    # Can only destroy with sunsword - the sun's light pierces the barrier
    crystal_heart.add_interaction(
        verb="use",
        required_instrument="sunsword",
        target_state="destroyed",
        message="You thrust the Sunsword into the Heart of Sorrow! The blade's radiant light "
        "pierces the magical barrier. The crystal shatters with a sound like a thousand screams. "
        "Somewhere in the castle, you hear Strahd roar in agony. His power is broken!",
        from_state="intact",
    )
    # Regular attacks fail
    crystal_heart.add_interaction(
        verb="destroy",
        message="Your weapon bounces off an invisible barrier. The heart pulses mockingly. "
        "Perhaps the Tome of Strahd holds the secret to destroying it...",
        from_state="intact",
    )
    crystal_heart.add_interaction(
        verb="break",
        message="You strike the heart, but a magical barrier repels your blow. "
        "There must be another way...",
        from_state="intact",
    )
    crystal_heart.add_interaction(
        verb="examine",
        message="The Heart of Sorrow - Strahd's connection to the castle itself. A shimmering "
        "barrier protects it from harm. The Tome of Strahd whispers: 'The Heart fears only "
        "the light of the sun.' Perhaps a weapon of pure sunlight could pierce the barrier.",
    )
    rooms["tomb"].add_item(crystal_heart)

    # === TREASURY PUZZLE ===
    # Three dials that must be set to sun, star, moon (in that order)
    # Then the pedestal can be opened to reveal the sunsword

    dial1: StatefulItem = StatefulItem(
        "first dial",
        "dial1",
        "The first dial shows a moon symbol.",
        weight=100,
        value=0,
        takeable=False,
        state="moon",
    )
    dial1.add_state_description("sun", "The first dial shows a sun symbol.")
    dial1.add_state_description("star", "The first dial shows a star symbol.")
    dial1.add_state_description("moon", "The first dial shows a moon symbol.")
    dial1.set_room_id("treasury")
    dial1.add_interaction(
        verb="turn",
        target_state="star",
        message="You turn the first dial. It clicks to show a star.",
        from_state="moon",
    )
    dial1.add_interaction(
        verb="turn",
        target_state="sun",
        message="You turn the first dial. It clicks to show a sun.",
        from_state="star",
    )
    dial1.add_interaction(
        verb="turn",
        target_state="moon",
        message="You turn the first dial. It clicks to show a moon.",
        from_state="sun",
    )
    rooms["treasury"].add_item(dial1)

    dial2: StatefulItem = StatefulItem(
        "second dial",
        "dial2",
        "The second dial shows a sun symbol.",
        weight=100,
        value=0,
        takeable=False,
        state="sun",
    )
    dial2.add_state_description("sun", "The second dial shows a sun symbol.")
    dial2.add_state_description("star", "The second dial shows a star symbol.")
    dial2.add_state_description("moon", "The second dial shows a moon symbol.")
    dial2.set_room_id("treasury")
    dial2.add_interaction(
        verb="turn",
        target_state="star",
        message="You turn the second dial. It clicks to show a star.",
        from_state="sun",
    )
    dial2.add_interaction(
        verb="turn",
        target_state="moon",
        message="You turn the second dial. It clicks to show a moon.",
        from_state="star",
    )
    dial2.add_interaction(
        verb="turn",
        target_state="sun",
        message="You turn the second dial. It clicks to show a sun.",
        from_state="moon",
    )
    rooms["treasury"].add_item(dial2)

    dial3: StatefulItem = StatefulItem(
        "third dial",
        "dial3",
        "The third dial shows a star symbol.",
        weight=100,
        value=0,
        takeable=False,
        state="star",
    )
    dial3.add_state_description("sun", "The third dial shows a sun symbol.")
    dial3.add_state_description("star", "The third dial shows a star symbol.")
    dial3.add_state_description("moon", "The third dial shows a moon symbol.")
    dial3.set_room_id("treasury")
    dial3.add_interaction(
        verb="turn",
        target_state="moon",
        message="You turn the third dial. It clicks to show a moon.",
        from_state="star",
    )
    dial3.add_interaction(
        verb="turn",
        target_state="sun",
        message="You turn the third dial. It clicks to show a sun.",
        from_state="moon",
    )
    dial3.add_interaction(
        verb="turn",
        target_state="star",
        message="You turn the third dial. It clicks to show a star.",
        from_state="sun",
    )
    rooms["treasury"].add_item(dial3)

    # The pedestal holding the sunsword
    pedestal: StatefulItem = StatefulItem(
        "pedestal",
        "treasury_pedestal",
        "An ornate stone pedestal with three runic dials. Something glimmers behind a glass case.",
        weight=500,
        value=0,
        takeable=False,
        state="locked",
    )
    pedestal.add_state_description(
        "locked",
        "An ornate stone pedestal with three runic dials. A glass case protects "
        "a gleaming blade within. The dials show: moon, sun, star.",
    )
    pedestal.add_state_description(
        "unlocked", "The glass case has slid open, revealing the legendary Sunsword!"
    )
    pedestal.set_room_id("treasury")
    pedestal.add_interaction(
        verb="open",
        target_state="unlocked",
        message="As you touch the case, the dials flash! Sun... Star... Moon... "
        "The sequence is CORRECT! The glass case slides open with a hiss, "
        "revealing the legendary Sunsword!",
        from_state="locked",
        conditional_fn=treasury_unlocked,
    )
    pedestal.add_interaction(
        verb="open",
        message="You touch the glass case. The dials flash angrily and a piercing alarm "
        "echoes through the castle! You hear stone grinding in the courtyard... "
        "The sequence was WRONG. Perhaps the Tome of Strahd holds the answer.",
        from_state="locked",
        # This triggers when conditional_fn fails - alarm consequence
    )
    pedestal.add_interaction(
        verb="examine",
        message="Three dials are set into the pedestal's base, each showing a celestial symbol. "
        "A glass case protects a blade that radiates brilliant light. "
        "There must be a correct sequence to open it safely.",
    )
    rooms["treasury"].add_item(pedestal)

    # === CASTLE TREASURE ITEMS ===
    # Treasury contains gold and jewels (matches room description)
    gold_pile: Item = Item(
        "gold",
        "treasury_gold",
        "A pile of gold coins, accumulated over centuries of Strahd's rule.",
        weight=10,
        value=150,
        takeable=True,
        synonyms=["gold pile", "coins", "gold coins", "pile"],
    )
    rooms["treasury"].add_item(gold_pile)

    jeweled_chalice: Item = Item(
        "chalice",
        "treasury_chalice",
        "A jewel-encrusted golden chalice, stained dark with old blood.",
        weight=3,
        value=100,
        takeable=True,
        synonyms=["cup", "goblet", "jeweled chalice", "golden chalice"],
    )
    rooms["treasury"].add_item(jeweled_chalice)

    # Tomb contains ancient treasures
    ancient_crown: Item = Item(
        "crown",
        "tomb_crown",
        "An ancient crown of tarnished silver, once worn by a forgotten king of Barovia.",
        weight=2,
        value=200,
        takeable=True,
        synonyms=["ancient crown", "silver crown", "king's crown"],
    )
    rooms["tomb"].add_item(ancient_crown)

    strahds_ring: Item = Item(
        "ring",
        "strahds_ring",
        "A heavy signet ring bearing the von Zarovich crest. It radiates dark power.",
        weight=1,
        value=150,
        takeable=True,
        synonyms=["signet ring", "strahd's ring", "von zarovich ring"],
    )
    rooms["tomb"].add_item(strahds_ring)

    # === STANDING STONES PUZZLE ===
    # Three stones in the clearing that must be aligned correctly to reveal the barrow
    # Solution: eaststone=sunrise, weststone=sunset, northstone=noon
    # Hint found on corpse note at crossroads

    eaststone: StatefulItem = StatefulItem(
        "eaststone",
        "eaststone",
        "The eastern stone is dark and dormant.",
        weight=10000,
        value=0,
        takeable=False,
        state="dark",
        synonyms=["east stone", "eastern stone", "eastern", "east"],
    )
    eaststone.add_state_description("dark", "The eastern stone is dark and dormant.")
    eaststone.add_state_description(
        "sunrise", "The eastern stone glows with the warm light of dawn."
    )
    eaststone.add_state_description(
        "noon", "The eastern stone blazes with harsh midday light."
    )
    eaststone.add_state_description(
        "sunset", "The eastern stone flickers with dying orange light."
    )
    eaststone.set_room_id("clearing")
    eaststone.add_interaction(
        verb="touch",
        target_state="sunrise",
        message="You touch the eastern stone. It warms and begins to glow with dawn's light.",
        from_state="dark",
    )
    eaststone.add_interaction(
        verb="touch",
        target_state="noon",
        message="You touch the eastern stone. The light intensifies to a blazing noon.",
        from_state="sunrise",
    )
    eaststone.add_interaction(
        verb="touch",
        target_state="sunset",
        message="You touch the eastern stone. The light dims to a warm sunset glow.",
        from_state="noon",
    )
    eaststone.add_interaction(
        verb="touch",
        target_state="dark",
        message="You touch the eastern stone. The light fades completely.",
        from_state="sunset",
    )
    rooms["clearing"].add_item(eaststone)

    weststone: StatefulItem = StatefulItem(
        "weststone",
        "weststone",
        "The western stone is dark and dormant.",
        weight=10000,
        value=0,
        takeable=False,
        state="dark",
        synonyms=["west stone", "western stone", "western", "west"],
    )
    weststone.add_state_description("dark", "The western stone is dark and dormant.")
    weststone.add_state_description(
        "sunrise", "The western stone glows with the warm light of dawn."
    )
    weststone.add_state_description(
        "noon", "The western stone blazes with harsh midday light."
    )
    weststone.add_state_description(
        "sunset", "The western stone flickers with dying orange light."
    )
    weststone.set_room_id("clearing")
    weststone.add_interaction(
        verb="touch",
        target_state="sunrise",
        message="You touch the western stone. It warms and begins to glow with dawn's light.",
        from_state="dark",
    )
    weststone.add_interaction(
        verb="touch",
        target_state="noon",
        message="You touch the western stone. The light intensifies to a blazing noon.",
        from_state="sunrise",
    )
    weststone.add_interaction(
        verb="touch",
        target_state="sunset",
        message="You touch the western stone. The light dims to a warm sunset glow.",
        from_state="noon",
    )
    weststone.add_interaction(
        verb="touch",
        target_state="dark",
        message="You touch the western stone. The light fades completely.",
        from_state="sunset",
    )
    rooms["clearing"].add_item(weststone)

    northstone: StatefulItem = StatefulItem(
        "northstone",
        "northstone",
        "The northern stone is dark and dormant.",
        weight=10000,
        value=0,
        takeable=False,
        state="dark",
        synonyms=["north stone", "northern stone", "northern", "north"],
    )
    northstone.add_state_description("dark", "The northern stone is dark and dormant.")
    northstone.add_state_description(
        "sunrise", "The northern stone glows with the warm light of dawn."
    )
    northstone.add_state_description(
        "noon", "The northern stone blazes with harsh midday light."
    )
    northstone.add_state_description(
        "sunset", "The northern stone flickers with dying orange light."
    )
    northstone.set_room_id("clearing")
    northstone.add_interaction(
        verb="touch",
        target_state="sunrise",
        message="You touch the northern stone. It warms and begins to glow with dawn's light.",
        from_state="dark",
    )
    northstone.add_interaction(
        verb="touch",
        target_state="noon",
        message="You touch the northern stone. The light intensifies to a blazing noon.",
        from_state="sunrise",
    )
    northstone.add_interaction(
        verb="touch",
        target_state="sunset",
        message="You touch the northern stone. The light dims to a warm sunset glow.",
        from_state="noon",
    )
    northstone.add_interaction(
        verb="touch",
        target_state="dark",
        message="You touch the northern stone. The light fades completely.",
        from_state="sunset",
    )
    rooms["clearing"].add_item(northstone)

    # The stones "puzzle checker" - a hidden mechanism that reveals the barrow
    # We use a special stateful item that checks alignment and reveals the exit
    stones: StatefulItem = StatefulItem(
        "stones",
        "standing_stones",
        "Three ancient standing stones form a circle at the center of the clearing.",
        weight=10000,
        value=0,
        takeable=False,
        state="dormant",
        synonyms=["circle", "standing stones", "stone circle", "standing"],
    )
    stones.add_state_description(
        "dormant",
        "Three ancient standing stones form a circle. They seem to be waiting for something.",
    )
    stones.add_state_description(
        "awakened",
        "The three stones hum with power. A passage has opened in the earth between them!",
    )
    stones.set_room_id("clearing")
    stones.add_interaction(
        verb="examine",
        message="Three standing stones arranged in a circle. Each stone bears faded carvings - "
        "the eastern stone shows a rising sun, the western stone a setting sun, "
        "and the northern stone a sun at its peak. Perhaps they can be activated?",
    )
    stones.add_interaction(
        verb="touch",
        target_state="awakened",
        message="As you touch the central point between the stones, they resonate in harmony! "
        "The ground trembles and splits open, revealing ancient stone steps "
        "leading down into the earth. The barrow is revealed!",
        from_state="dormant",
        conditional_fn=stones_aligned,
        add_exit=("down", "barrow"),
    )
    stones.add_interaction(
        verb="touch",
        message="As you touch the misaligned stones, ancient magic surges through them!\n"
        "Lightning arcs between the stones, striking you with devastating force!\n"
        "The last thing you see is the stones' carvings glowing with malevolent light...",
        from_state="dormant",
        kills_player=True,
        damage_message="As you touch the misaligned stones, ancient magic surges through them!\n"
        "Lightning arcs between the stones, striking you with devastating force!\n"
        "The last thing you see is the stones' carvings glowing with malevolent light...",
    )
    rooms["clearing"].add_item(stones)

    # === OVEN HORROR (kitchen) ===
    # Opening the oven reveals the true horror of the hag's pastries
    oven: StatefulItem = StatefulItem(
        "oven",
        "hag_oven",
        "A massive iron oven dominates the kitchen, radiating unnatural heat.",
        weight=1000,
        value=0,
        takeable=False,
        state="closed",
        synonyms=["furnace", "stove", "iron oven", "cooker"],
    )
    oven.add_state_description(
        "closed",
        "A massive iron oven radiates heat. Scratching sounds come from within.",
    )
    oven.add_state_description(
        "open", "The oven door hangs open, revealing its horrifying contents."
    )
    oven.set_room_id("kitchen")
    oven.add_interaction(
        verb="examine",
        message="The oven is enormous - large enough to fit a person. "
        "Scratching sounds come from inside. Do you really want to look?",
    )
    oven.add_interaction(
        verb="open",
        target_state="open",
        message="You pull open the oven door and recoil in horror! "
        "Inside, among the ashes and coals, you see... bones. Small bones. "
        "The scratching was a rat gnawing on what remains of the hag's 'ingredients.' "
        "The sweet pastries... you understand now what they're made from. "
        "You feel sick to your stomach.",
        from_state="closed",
    )
    oven.add_interaction(
        verb="close",
        target_state="closed",
        message="You slam the oven door shut, but the image is burned into your mind.",
        from_state="open",
    )
    rooms["kitchen"].add_item(oven)

    # === HAG'S TRUE NAME PUZZLE ===
    # Saying "Morgantha" in the kitchen weakens the hag
    # Hints are scattered: wagon (Mor...), bedroom dolls (...gantha), basement note

    async def weaken_hag(
        player: Any,
        game_state: Any,
        player_manager: Any,
        online_sessions: Any,
        sio: Any,
        utils: Any,
    ) -> None:
        """Weaken the hag by speaking her true name."""
        # Mark the hag as weakened - this would affect combat
        # For now we just set a flag that could be checked
        mob_manager = getattr(utils, "mob_manager", None)
        if mob_manager:
            for mob_id, mob in mob_manager.mobs.items():
                if getattr(mob, "mob_type", None) == "hag":
                    mob.damage = max(1, mob.damage // 2)  # Halve damage
                    setattr(mob, "weakened", True)

    rooms["kitchen"].add_speech_trigger(
        keyword="morgantha",
        message="As you speak the hag's true name, a TERRIBLE SHRIEK echoes through the mill!\n\n"
        "'HOW DO YOU KNOW THAT NAME?!' The hag's voice trembles with fear and rage. "
        "'No one should know my TRUE NAME! That was sealed away centuries ago!'\n\n"
        "You feel a shift in the air - the hag's power has been diminished. "
        "If you face her in combat, she will be significantly weakened!",
        effect_fn=weaken_hag,
        one_time=True,
    )

    # ===== CRYPTKEEPER'S MAZE PUZZLES =====

    # === MAZE GATE (maze_entry) ===
    # Requires the crypt_key from the gallows corpse puzzle
    maze_gate: StatefulItem = StatefulItem(
        "gate",
        "maze_gate",
        "A heavy iron gate blocks the passage north.",
        weight=500,
        value=0,
        takeable=False,
        state="locked",
    )
    maze_gate.add_state_description(
        "locked", "A heavy iron gate blocks the passage north. It is locked tight."
    )
    maze_gate.add_state_description(
        "open", "The iron gate stands open, revealing a dark passage beyond."
    )
    maze_gate.set_room_id("maze_entry")
    maze_gate.add_interaction(
        verb="unlock",
        required_instrument="key",
        target_state="open",
        message="You insert the rusted key into the lock. It turns with a grinding screech! "
        "The ancient gate swings open, releasing a gust of stale air from the depths below.",
        from_state="locked",
        add_exit=("north", "maze_pool"),
    )
    maze_gate.add_interaction(
        verb="open",
        message="The gate is locked. You need a key to open it.",
        from_state="locked",
    )
    maze_gate.add_interaction(
        verb="examine",
        message="An ancient iron gate, rusted but solid. A heavy lock secures it. "
        "The key from the gallows might fit...",
    )
    rooms["maze_entry"].add_item(maze_gate)

    # === STEPPING STONES (maze_pool) ===
    # Environmental puzzle - need light to cross safely
    stepping_stones: StatefulItem = StatefulItem(
        "stones",
        "stepping_stones",
        "Stepping stones cross the flooded chamber.",
        weight=10000,
        value=0,
        takeable=False,
        state="visible",
        synonyms=["stone", "stepping", "path"],
    )
    stepping_stones.add_state_description(
        "visible", "Stepping stones cross the flooded chamber. They look slippery."
    )
    stepping_stones.set_room_id("maze_pool")
    stepping_stones.add_interaction(
        verb="cross",
        message="With your light source, you carefully pick your way across the stepping stones. "
        "The water is black and deep - you don't want to know what lurks below. "
        "But you make it safely to the other side.",
        conditional_fn=player_has_light,
    )
    stepping_stones.add_interaction(
        verb="cross",
        message="You step forward into the darkness... and immediately plunge into the icy water! "
        "Something cold wraps around your ankle and PULLS YOU DOWN! You thrash desperately "
        "but the water fills your lungs. The last thing you see is pale shapes in the depths...",
        kills_player=True,
        damage_message="You step forward into the darkness and plunge into the water. "
        "Something drags you down into the depths...",
    )
    stepping_stones.add_interaction(
        verb="examine",
        message="Stone pillars rise from the dark water. Without light, you can barely see them. "
        "Crossing in darkness would be suicidal.",
    )
    rooms["maze_pool"].add_item(stepping_stones)

    # Drowned corpse as a hint
    drowned_corpse: Item = Item(
        "corpse",
        "drowned_corpse",
        "A waterlogged corpse floats face-down in the water, a torch clutched in its dead hand.",
        weight=100,
        value=0,
        takeable=False,
    )
    rooms["maze_pool"].add_item(drowned_corpse)

    # === MIRROR PUZZLE (maze_mirror) ===
    # Touch mirrors in correct sequence: east, south, west, north
    # Based on riddle: sun rises east, shadows flee at noon (south),
    # moon in darkness (west), stars point north

    mirror_riddle: StatefulItem = StatefulItem(
        "pedestal",
        "mirror_pedestal",
        "A stone pedestal stands at the center of the chamber.",
        weight=200,
        value=0,
        takeable=False,
        state="unread",
        synonyms=["riddle", "inscription"],
    )
    mirror_riddle.add_state_description(
        "unread", "A stone pedestal stands at the center with a riddle carved into it."
    )
    mirror_riddle.add_state_description(
        "read", "A stone pedestal with a riddle you have read."
    )
    mirror_riddle.set_room_id("maze_mirror")
    mirror_riddle.add_interaction(
        verb="read",
        target_state="read",
        message="The riddle reads:\n\n"
        "'First the sun rises in the east,\n"
        "Then at noon the shadows flee,\n"
        "Moon in darkness claims the west,\n"
        "Stars point north eternally.'\n\n"
        "Four mirrors surround you. Perhaps they must be touched in a certain order?",
    )
    mirror_riddle.add_interaction(
        verb="examine",
        message="A riddle is carved into the pedestal. 'Read' it to see the words.",
    )
    rooms["maze_mirror"].add_item(mirror_riddle)

    # Helper function to create mirror touch effect
    def create_mirror_touch_effect(direction: str, description: str) -> StatefulItem:
        mirror = StatefulItem(
            f"{direction} mirror",
            f"mirror_{direction}",
            f"The {direction}ern mirror shows {description}.",
            weight=100,
            value=0,
            takeable=False,
            state="dormant",
            synonyms=[direction, f"{direction}ern"],
        )
        mirror.add_state_description(
            "dormant", f"The {direction}ern mirror shows {description}."
        )
        mirror.add_state_description(
            "touched", f"The {direction}ern mirror glows faintly."
        )
        mirror.set_room_id("maze_mirror")
        return mirror

    mirror_east = create_mirror_touch_effect("east", "a blazing sun")
    mirror_south = create_mirror_touch_effect("south", "dancing shadows")
    mirror_west = create_mirror_touch_effect("west", "a pale moon")
    mirror_north = create_mirror_touch_effect("north", "twinkling stars")

    rooms["maze_mirror"].add_item(mirror_east)
    rooms["maze_mirror"].add_item(mirror_south)
    rooms["maze_mirror"].add_item(mirror_west)
    rooms["maze_mirror"].add_item(mirror_north)

    # === ARCHIVE RIDDLE (maze_library) ===
    # The riddle tome and speech trigger for "death"

    archive_tome: StatefulItem = StatefulItem(
        "tome",
        "archive_tome",
        "A glowing tome rests on the central pedestal.",
        weight=5,
        value=0,
        takeable=False,
        state="unread",
        synonyms=["book", "pedestal"],
    )
    archive_tome.add_state_description(
        "unread", "A glowing tome rests on the central pedestal."
    )
    archive_tome.add_state_description("read", "The tome's riddle echoes in your mind.")
    archive_tome.set_room_id("maze_library")
    archive_tome.add_interaction(
        verb="read",
        target_state="read",
        message="The tome's pages glow with ethereal light. A riddle appears:\n\n"
        "'I am sought by kings and beggars alike,\n"
        "Yet none who find me wish to stay.\n"
        "I am feared by the living, welcomed by the suffering,\n"
        "And Strahd himself cannot keep me at bay.\n"
        "What am I?'\n\n"
        "The ghostly voice whispers: 'Speak the answer, if you dare...'",
    )
    archive_tome.add_interaction(
        verb="examine",
        message="The tome pulses with magic. Reading it might reveal a riddle.",
    )
    rooms["maze_library"].add_item(archive_tome)

    # Speech trigger for the riddle answer
    async def open_chapel_door(
        player: Any,
        game_state: Any,
        player_manager: Any,
        online_sessions: Any,
        sio: Any,
        utils: Any,
    ) -> None:
        """Open the passage to the chapel when riddle is answered."""
        room = game_state.get_room("maze_library")
        if room and "north" not in room.exits:
            room.exits["north"] = "maze_chapel"

    rooms["maze_library"].add_speech_trigger(
        keyword="death",
        message="As you speak the word, the ghostly voice sighs with profound relief.\n\n"
        "'Yes... DEATH is the answer we all seek to avoid, yet cannot escape. "
        "Even Strahd, for all his power, fears the true death that waits beyond his immortality.'\n\n"
        "A hidden door slides open to the north, revealing a passage to a small chapel.",
        effect_fn=open_chapel_door,
        one_time=True,
    )

    # === CHAPEL SEAL (maze_chapel) ===
    # Must speak "andral" to break the seal - only works if visited Vallaki church

    chapel_altar: StatefulItem = StatefulItem(
        "sealed altar",
        "maze_altar",
        "A small altar stands before a shimmering barrier of light.",
        synonyms=["altar", "maze altar", "barrier altar"],
        weight=300,
        value=0,
        takeable=False,
        state="sealed",
    )
    chapel_altar.add_state_description(
        "sealed",
        "A shimmering barrier of light blocks the passage north. "
        "An inscription reads: 'Speak the name of the saint who protects the faithful.'",
    )
    chapel_altar.add_state_description(
        "unsealed", "The barrier has dissolved. The passage north is open."
    )
    chapel_altar.set_room_id("maze_chapel")
    chapel_altar.add_interaction(
        verb="examine",
        message="The altar is carved with protective symbols. An inscription reads:\n"
        "'Only one who has prayed at the saint's church may speak his name with true faith. "
        "Speak the name of the saint who protects the faithful of Vallaki.'\n\n"
        "Perhaps visiting St. Andral's Church would help you learn the name?",
    )
    rooms["maze_chapel"].add_item(chapel_altar)

    # Speech trigger for the saint's name
    async def unseal_sanctum(
        player: Any,
        game_state: Any,
        player_manager: Any,
        online_sessions: Any,
        sio: Any,
        utils: Any,
    ) -> None:
        """Unseal the passage to the sanctum."""
        room = game_state.get_room("maze_chapel")
        if room and "north" not in room.exits:
            room.exits["north"] = "maze_sanctum"
        # Update altar state
        for item in room.items:
            if hasattr(item, "id") and item.id == "maze_altar":
                item.state = "unsealed"
                break

    rooms["maze_chapel"].add_speech_trigger(
        keyword="andral",
        message="As you speak the saint's name, the altar glows with brilliant white light!\n\n"
        "The shimmering barrier wavers, then dissolves completely. You feel a wave of "
        "warmth wash over you - the blessing of St. Andral recognizes your faith.\n\n"
        "The passage to the sanctum is now open!",
        effect_fn=unseal_sanctum,
        conditional_fn=player_visited_vallaki_church,
        one_time=True,
    )

    # Fallback if player hasn't visited the church
    rooms["maze_chapel"].add_speech_trigger(
        keyword="andral",
        message="You speak the name, but it feels hollow on your tongue. The barrier "
        "pulses mockingly. Perhaps you must first visit the saint's church and "
        "pray there before you can speak his name with true faith.",
        conditional_fn=lambda p, gs: not player_visited_vallaki_church(p, gs),
        one_time=False,
    )


def add_regular_items(rooms: Dict[str, Room]) -> None:
    """Add regular (non-stateful) items to rooms."""

    # === LIGHT SOURCES ===
    torch: Item = Item(
        "torch",
        "torch",
        "A sputtering torch casts flickering shadows.",
        weight=1,
        value=2,
    )
    torch.emits_light = True
    rooms["tavern"].add_item(torch)

    lantern: Item = Item(
        "lantern",
        "lantern",
        "A battered lantern with a steady flame.",
        weight=2,
        value=15,
    )
    lantern.emits_light = True
    rooms["pool"].add_item(lantern)

    # === READABLE ITEMS ===
    letter: StatefulItem = StatefulItem(
        "letter",
        "kolyan_letter",
        "A half-finished letter lies on the desk.",
        weight=1,
        value=5,
        state="unread",
    )
    letter.add_state_description("unread", "A half-finished letter lies on the desk.")
    letter.add_state_description("read", "A letter you have read.")
    letter.add_interaction(
        verb="read",
        target_state="read",
        message="The letter reads:\n\n"
        "'Hail thee of might and valor. I, Burgomaster Kolyan Indirovich, write to entreat thy aid. "
        "My adopted daughter, Ireena, is being pursued by a creature of terrible evil. He has "
        "already visited her twice, drinking her blood each time. She grows weaker. I beg thee, "
        "come to our village and help us escape this accursed land...\n\n"
        "The letter trails off, unfinished. Kolyan never sent it. He never got the chance.",
    )
    rooms["study"].add_item(letter)

    tome: StatefulItem = StatefulItem(
        "tome",
        "tome_of_strahd",
        "A tome bound in black leather sits on the desk.",
        weight=3,
        value=100,
        state="unread",
    )
    tome.add_state_description(
        "unread", "A tome bound in black leather sits on the desk."
    )
    tome.add_state_description("read", "The Tome of Strahd, now read.")
    tome.add_interaction(
        verb="read",
        target_state="read",
        message="You open the Tome of Strahd and read:\n\n"
        "'I am the Ancient. I am the Land. My beginnings are lost in the darkness of the past. "
        "I was the warrior, I was good and just. I thundered across the land like the wrath of "
        "a just god, but the war years and the killing years wore down my soul...\n\n"
        "I found her, my Tatyana. So beautiful, so pure. But she loved another - my brother, "
        "Sergei. On their wedding day, I made my pact. I killed my brother. I drank her blood. "
        "And she threw herself from the walls of this very castle rather than become mine...'\n\n"
        "In the margins, Strahd has scrawled notes:\n\n"
        "'The Heart of Sorrow protects me. It fears only the light of the sun.'\n\n"
        "'My treasury is sealed by the celestial lock. Sun first, then star, then moon. "
        "Only a fool would try to take from me without knowing the sequence.'",
    )
    rooms["castlestudy"].add_item(tome)

    # === SEER'S PRICE (wagon) ===
    # The seer requires payment (coin or wine) before reading the cards
    seer_bowl: StatefulItem = StatefulItem(
        "bowl",
        "seer_bowl",
        "A brass offering bowl sits before the seer.",
        weight=5,
        value=0,
        takeable=False,
        state="empty",
    )
    seer_bowl.add_state_description(
        "empty",
        "A brass offering bowl sits empty before the seer. She eyes you expectantly.",
    )
    seer_bowl.add_state_description(
        "filled", "The offering bowl holds your gift. The seer nods with satisfaction."
    )
    seer_bowl.add_interaction(
        verb="place",
        required_instrument="coin",
        target_state="filled",
        message="You place the coin in the bowl. The seer's eyes light up. "
        "'A fair price for knowledge. Now I will read for you.'",
        from_state="empty",
    )
    seer_bowl.add_interaction(
        verb="place",
        required_instrument="wine",
        target_state="filled",
        message="You place the wine in the bowl. The seer smiles approvingly. "
        "'A fine gift! The spirits favor generosity. I will read your fortune.'",
        from_state="empty",
    )
    seer_bowl.add_interaction(
        verb="examine",
        message="The brass bowl is for offerings. The seer expects payment "
        "before she will read the cards. A coin or wine would likely satisfy her.",
    )
    rooms["wagon"].add_item(seer_bowl)

    def seer_paid(player: Any, game_state: Any) -> bool:
        room = game_state.get_room("wagon")
        if not room:
            return False
        for item in room.items:
            if hasattr(item, "id") and item.id == "seer_bowl":
                return getattr(item, "state", None) == "filled"
        return False

    cards: StatefulItem = StatefulItem(
        "cards",
        "tarokka_deck",
        "A worn deck of Tarokka cards sits on a silk cloth.",
        weight=1,
        value=20,
        takeable=False,
        state="waiting",
    )
    cards.add_state_description(
        "waiting", "A worn deck of Tarokka cards sits on a silk cloth."
    )
    cards.add_state_description(
        "read", "The Tarokka cards have been read. The seer stares into nothing."
    )
    cards.add_interaction(
        verb="read",
        target_state="read",
        message="The seer shuffles the worn deck and draws three cards:\n\n"
        "'The Artifact - Seek the sun's blade in the castle's golden hoard.\n"
        "The Broken One - An ally awaits in the inn of blue water.\n"
        "The Mists - The lord of this land rests in darkness beneath his throne.'\n\n"
        "The seer pauses, then adds in a low whisper:\n"
        "'And beware the hag of the windmill... her name begins with Mor... "
        "To speak her full name is to weaken her. But I cannot remember more.'\n\n"
        "She nods cryptically. 'The cards have spoken. Heed their wisdom, traveler.'",
        from_state="waiting",
        conditional_fn=seer_paid,
    )
    cards.add_interaction(
        verb="read",
        message="The seer pulls the deck away from you. 'First, you must offer a gift. "
        "Knowledge does not come free in Barovia.' She gestures to the brass bowl.",
        from_state="waiting",
    )
    rooms["wagon"].add_item(cards)

    invitation: StatefulItem = StatefulItem(
        "invitation",
        "invitation",
        "An elegant invitation card lies on a table.",
        weight=1,
        value=0,
        state="unread",
    )
    invitation.add_state_description(
        "unread", "An elegant invitation card lies on a table."
    )
    invitation.add_interaction(
        verb="read",
        message="The invitation reads:\n\n"
        "'My Dear Guest,\n\n"
        "I bid you welcome to my home. Your presence honors me, and I look forward to making "
        "your acquaintance. Please, enjoy my hospitality. Dinner will be served at midnight.\n\n"
        "Your Humble Host,\n"
        "Count Strahd von Zarovich'\n\n"
        "The handwriting is elegant but somehow threatening.",
    )
    rooms["entrance"].add_item(invitation)

    # === CROSSROADS CORPSE WITH HINT NOTE ===
    # This corpse has a note that hints at the standing stones puzzle solution
    corpse: StatefulItem = StatefulItem(
        "corpse",
        "crossroads_corpse",
        "A weathered corpse swings from the crossroads gibbet.",
        weight=100,
        value=0,
        takeable=False,
        state="unsearched",
    )
    corpse.add_state_description(
        "unsearched",
        "A weathered corpse swings from the crossroads gibbet. It might have something useful.",
    )
    corpse.add_state_description(
        "searched",
        "A weathered corpse swings from the gibbet. Its pockets have been searched.",
    )
    corpse.add_interaction(
        verb="search",
        target_state="searched",
        message="You search the corpse's pockets and find a crumpled note.",
        from_state="unsearched",
    )
    corpse.add_interaction(
        verb="examine",
        message="The corpse has been here for some time. Crows have been at it. "
        "There might be something in its pockets.",
    )
    rooms["crossroads"].add_item(corpse)

    note: StatefulItem = StatefulItem(
        "note",
        "corpse_note",
        "A crumpled note found on the corpse.",
        weight=1,
        value=0,
        state="unread",
    )
    note.add_interaction(
        verb="read",
        target_state="read",
        message="The note is stained but legible:\n\n"
        "'Three stones mark the path to the ancient barrow.\n"
        "East greets the dawn.\n"
        "West bids farewell.\n"
        "North watches all from its peak.'\n\n"
        "Below, in a shaky hand: 'I almost had it. So close...'",
    )

    # Hidden until corpse is searched
    def corpse_searched(game_state: Any) -> bool:
        room = game_state.get_room("crossroads")
        if not room:
            return False
        for item in room.items:
            if hasattr(item, "id") and item.id == "crossroads_corpse":
                return getattr(item, "state", None) == "searched"
        return False

    rooms["crossroads"].add_hidden_item(note, corpse_searched)

    # === GALLOWS PUZZLE ===
    # Cut the rope to drop the corpse, revealing a key in its fist
    # Players can interact with "rope", "corpse", "body", etc. via synonyms

    gallows_corpse: StatefulItem = StatefulItem(
        "corpse",
        "gallows_corpse",
        "A body hangs from the gallows, clutching something in its rotting fist.",
        weight=150,
        value=0,
        takeable=False,
        state="hanging",
        synonyms=["body", "rope", "remains", "cadaver", "gallows"],
    )
    gallows_corpse.add_state_description(
        "hanging",
        "A body hangs from the gallows, clutching something in its rotting fist.",
    )
    gallows_corpse.add_state_description(
        "fallen", "The corpse lies crumpled on the ground. Its fist has opened."
    )
    gallows_corpse.set_room_id("square")
    gallows_corpse.add_interaction(
        verb="examine",
        message="The corpse has been hanging here for some time. Crows have been at it. "
        "In its rotting fist, it clutches something - a key perhaps? "
        "You'd need to cut the rope to get it down.",
        from_state="hanging",
    )
    gallows_corpse.add_interaction(
        verb="examine",
        message="The corpse lies in a heap. Whatever it was holding has fallen free.",
        from_state="fallen",
    )
    gallows_corpse.add_interaction(
        verb="cut",
        target_state="fallen",
        message="You slash at the rope with your blade! The corpse drops with a sickening thud. "
        "Its fist opens upon impact, and a rusted iron key clatters across the cobblestones.",
        from_state="hanging",
        conditional_fn=has_any_weapon,
    )
    gallows_corpse.add_interaction(
        verb="cut",
        message="You have nothing sharp enough to cut the rope. You need a blade.",
        from_state="hanging",
    )
    rooms["square"].add_item(gallows_corpse)

    # The crypt key - hidden until corpse falls
    crypt_key: Item = Item(
        "key",
        "crypt_key",
        "A rusted iron key, cold to the touch.",
        weight=1,
        value=5,
    )

    def gallows_puzzle_solved(game_state: Any) -> bool:
        room = game_state.get_room("square")
        if not room:
            return False
        for item in room.items:
            # Check if corpse has fallen
            if hasattr(item, "id"):
                if (
                    item.id == "gallows_corpse"
                    and getattr(item, "state", None) == "fallen"
                ):
                    return True
        return False

    rooms["square"].add_hidden_item(crypt_key, gallows_puzzle_solved)

    # === BARROW TREASURE ===
    # Reward for solving the standing stones puzzle
    amulet: Item = Item(
        "amulet",
        "barrow_amulet",
        "An ancient silver barrow amulet that glows faintly with protective magic.",
        weight=1,
        value=75,
    )
    rooms["barrow"].add_item(amulet)

    gold_pile: Item = Item(
        "gold",
        "barrow_gold",
        "A pile of ancient gold coins, offerings to forgotten gods.",
        weight=5,
        value=50,
    )
    rooms["barrow"].add_item(gold_pile)

    # === CRYPTKEEPER'S SANCTUM REWARDS ===
    cryptkeeper_amulet: Item = Item(
        "amulet",
        "cryptkeeper_amulet",
        "The cryptkeeper's bone amulet, inscribed with protective runes. It pulses with ancient power.",
        weight=1,
        value=100,
    )
    rooms["maze_sanctum"].add_item(cryptkeeper_amulet)

    ancient_gold: Item = Item(
        "gold",
        "ancient_gold",
        "A pile of ancient gold coins, far older than anything in Barovia.",
        weight=8,
        value=100,
    )
    rooms["maze_sanctum"].add_item(ancient_gold)

    cryptkeeper_tome: StatefulItem = StatefulItem(
        "tome",
        "cryptkeeper_tome",
        "A leather-bound tome resting on the sarcophagus.",
        weight=3,
        value=50,
        state="unread",
    )
    cryptkeeper_tome.add_state_description(
        "unread", "A leather-bound tome resting on the sarcophagus."
    )
    cryptkeeper_tome.add_state_description(
        "read", "The Cryptkeeper's tome, filled with ancient secrets."
    )
    cryptkeeper_tome.add_interaction(
        verb="read",
        target_state="read",
        message="You open the tome and read the Cryptkeeper's final words:\n\n"
        "'I am the last of my order, sworn to guard Barovia's oldest secrets. "
        "When the Dark Lord rose, we knew our time was ending. I sealed this maze "
        "so that only the worthy could reach our treasures.\n\n"
        "If you read this, you have proven yourself clever and brave. "
        "Take what you find here and use it against the darkness.\n\n"
        "Remember: the hag fears her true name. The Baron hides shame in shadows. "
        "And Strahd... Strahd can be destroyed, but only by one who understands "
        "that even immortals fear the final death.'\n\n"
        "The tome contains hints about other puzzles in the land!",
    )
    rooms["maze_sanctum"].add_item(cryptkeeper_tome)

    # === QUEST ITEMS ===
    symbol: Item = Item(
        "symbol",
        "holy_symbol",
        "A silver holy symbol hangs on a chain.",
        weight=1,
        value=25,
    )
    rooms["church"].add_item(symbol)

    bones: Item = Item(
        "bones",
        "saint_bones",
        "Ancient bones wrapped in rotting cloth - the relics of St. Andral.",
        weight=3,
        value=0,
    )
    # bones are hidden - need to be discovered via interaction
    rooms["stockyard"].add_item(bones)  # Coffin maker hid them here

    stone: Item = Item(
        "stone",
        "heartstone",
        "A smooth grey heartstone that pulses with inner warmth.",
        weight=1,
        value=50,
    )
    rooms["bedroom"].add_item(stone)

    # === HAG NAME HINTS ===
    # Hint 1: Dolls in bedroom whisper part of the name
    hag_dolls: StatefulItem = StatefulItem(
        "dolls",
        "hag_dolls",
        "Strange dolls made of sticks and bone hang from the ceiling.",
        weight=5,
        value=0,
        takeable=False,
        state="hanging",
        synonyms=["doll", "stick", "bone"],
    )
    hag_dolls.add_state_description(
        "hanging", "Strange dolls made of sticks and bone hang from the ceiling."
    )
    hag_dolls.add_interaction(
        verb="examine",
        message="The dolls are disturbing - crude figures made of twigs wrapped in hair. "
        "As you look at them, you swear you hear a faint whisper: '...gantha... gantha...' "
        "The sound seems to come from the dolls themselves.",
    )
    hag_dolls.add_interaction(
        verb="touch",
        message="As your fingers brush the dolls, a voice whispers directly into your ear: "
        "'...gantha... she who bakes the children... gantha...' "
        "You snatch your hand back in horror.",
    )
    rooms["bedroom"].add_item(hag_dolls)

    # Hint 2: Note in mill basement about true names
    hag_note: StatefulItem = StatefulItem(
        "note",
        "hag_basement_note",
        "A crumpled note lies among the bones.",
        weight=1,
        value=0,
        state="unread",
    )
    hag_note.add_state_description("unread", "A crumpled note lies among the bones.")
    hag_note.add_state_description("read", "A note you have read.")
    hag_note.add_interaction(
        verb="read",
        target_state="read",
        message="The note is stained but legible:\n\n"
        "'To any who find this - the creature upstairs is no mere witch. "
        "She is a night hag, bound to this place by dark pacts. "
        "Only her TRUE NAME can weaken her power. I searched but could not find it. "
        "Perhaps the Vistani know? They trade in secrets...\n\n"
        "If you discover her name, speak it aloud in her presence. "
        "It may be the only way to survive.'\n\n"
        "The writer's final words are smeared with blood.",
    )
    rooms["millbasement"].add_item(hag_note)

    # === BARON'S SECRET PUZZLE ===
    # Baron's journal in mansion hints at secret, loose stone in dungeon reveals vault
    baron_journal: StatefulItem = StatefulItem(
        "journal",
        "baron_journal",
        "A leather-bound journal lies on the Baron's desk.",
        weight=2,
        value=15,
        state="unread",
        synonyms=["book", "diary"],
    )
    baron_journal.add_state_description(
        "unread", "A leather-bound journal lies on the Baron's desk."
    )
    baron_journal.add_state_description(
        "read", "The Baron's journal, now read. It revealed a dark secret."
    )
    baron_journal.add_interaction(
        verb="read",
        target_state="read",
        message="The journal contains the Baron's private thoughts:\n\n"
        "'The festival must succeed. All will be well. ALL WILL BE WELL.\n\n"
        "I have hidden the evidence of my... methods... in the dungeon below. "
        "Behind the third stone from the door, in the north wall. "
        "No one must ever find what I have done in the name of happiness.\n\n"
        "If they knew the true cost of our festivals... the sacrifices I've made... "
        "they would never smile again.'\n\n"
        "The Baron's handwriting becomes increasingly erratic on the later pages.",
    )
    baron_journal.add_interaction(
        verb="examine",
        message="A leather journal embossed with the Vallakovich family crest. "
        "The Baron guards it jealously. It might contain secrets...",
    )
    rooms["mansion"].add_item(baron_journal)

    # Loose stone in mansion dungeon - requires light and having read journal
    def journal_was_read(player: Any, game_state: Any) -> bool:
        """Check if player has read the baron's journal."""
        for item in player.inventory:
            if hasattr(item, "id") and item.id == "baron_journal":
                return getattr(item, "state", None) == "read"
        # Also check if it's in any room (might have been dropped)
        for room_id, room in game_state.rooms.items():
            for item in room.items:
                if hasattr(item, "id") and item.id == "baron_journal":
                    return getattr(item, "state", None) == "read"
        return False

    def can_find_stone(player: Any, game_state: Any) -> bool:
        """Must have light AND have read the journal."""
        return player_has_light(player, game_state) and journal_was_read(
            player, game_state
        )

    loose_stone: StatefulItem = StatefulItem(
        "stone",
        "loose_stone",
        "The dungeon walls are made of rough stone blocks.",
        weight=100,
        value=0,
        takeable=False,
        state="set",
        synonyms=["wall", "brick", "block", "third stone", "loose"],
    )
    loose_stone.add_state_description(
        "set", "The dungeon walls are made of rough stone blocks."
    )
    loose_stone.add_state_description(
        "removed", "One stone has been pulled from the wall, revealing a hidden space."
    )
    loose_stone.set_room_id("mansiondungeon")
    loose_stone.add_interaction(
        verb="examine",
        message="With your light, you can see the dungeon walls clearly. "
        "Now that you know where to look, you notice the third stone from the door "
        "is slightly different - it's loose, and there are scratch marks around it.",
        conditional_fn=can_find_stone,
    )
    loose_stone.add_interaction(
        verb="examine",
        message="The walls are rough stone. In this darkness, you can barely see anything. "
        "You'd need light to examine them properly.",
        conditional_fn=lambda p, gs: not player_has_light(p, gs),
    )
    loose_stone.add_interaction(
        verb="examine",
        message="The walls are made of rough stone blocks. They all look the same to you. "
        "Perhaps if you knew what to look for...",
    )
    loose_stone.add_interaction(
        verb="move",
        target_state="removed",
        message="Knowing exactly where to look, you pry at the third stone from the door. "
        "It shifts with a grinding sound, then slides out! Behind it is a small vault "
        "containing the Baron's darkest secrets - and his hidden treasures.",
        from_state="set",
        conditional_fn=can_find_stone,
        add_exit=("in", "baron_vault"),
    )
    loose_stone.add_interaction(
        verb="move",
        message="You run your hands over the wall but can't find anything unusual. "
        "Maybe you need to know exactly where to look?",
        from_state="set",
    )
    loose_stone.add_interaction(
        verb="push",
        target_state="removed",
        message="You push on the loose stone. It slides inward with a click, "
        "revealing a hidden compartment!",
        from_state="set",
        conditional_fn=can_find_stone,
        add_exit=("in", "baron_vault"),
    )
    loose_stone.add_interaction(
        verb="pull",
        target_state="removed",
        message="You grip the edges of the loose stone and pull. "
        "It slides out, revealing a dark space behind!",
        from_state="set",
        conditional_fn=can_find_stone,
        add_exit=("in", "baron_vault"),
    )
    rooms["mansiondungeon"].add_item(loose_stone)

    # Baron's vault contents
    baron_gold: Item = Item(
        "gold",
        "baron_gold",
        "A pile of gold coins confiscated from 'unhappy' citizens.",
        weight=10,
        value=75,
    )
    rooms["baron_vault"].add_item(baron_gold)

    baron_documents: Item = Item(
        "documents",
        "baron_documents",
        "Disturbing records of the Baron's 'corrections' - those who refused to be happy.",
        weight=2,
        value=25,
        synonyms=["records", "papers"],
    )
    rooms["baron_vault"].add_item(baron_documents)

    # === CONSUMABLES ===
    wine: Item = Item(
        "wine",
        "wine_bottle",
        "A dusty bottle of wine from the Wizard of Wines.",
        weight=2,
        value=10,
    )
    rooms["cellar"].add_item(wine)

    pastry: StatefulItem = StatefulItem(
        "pastry",
        "dream_pastry",
        "A sweet-smelling dream pastry that looks delicious.",
        weight=1,
        value=5,
        state="uneaten",
    )
    pastry.add_state_description(
        "uneaten", "A sweet-smelling dream pastry that looks delicious."
    )
    pastry.add_interaction(
        verb="eat",
        message="You eat the pastry. It's delicious, but as you chew, you realize too late "
        "what it might be made from. A dreamy euphoria washes over you, followed by "
        "horrifying visions. When you wake, you feel somehow... less.",
    )
    rooms["kitchen"].add_item(pastry)

    # === TREASURE ===
    coin1: Item = Item(
        "coin",
        "coin_manor",
        "A tarnished silver coin bearing Strahd's visage.",
        weight=1,
        value=10,
    )
    rooms["manor"].add_item(coin1)

    # Removed coin from treasury to consolidate items (puzzle items take priority)

    # === MISC ===
    cloak: Item = Item(
        "cloak",
        "tattered_cloak",
        "A tattered black cloak that might provide some concealment.",
        weight=2,
        value=5,
    )
    cloak.grants_invisibility = True
    rooms["hollow"].add_item(cloak)

    rope: Item = Item(
        "rope",
        "rope",
        "A coil of sturdy rope.",
        weight=3,
        value=5,
    )
    rooms["mill"].add_item(rope)

    shield: Item = Item(
        "shield",
        "knight_shield",
        "A battered shield bearing the symbol of the Order of the Silver Dragon.",
        weight=8,
        value=30,
    )
    rooms["vault"].add_item(shield)  # Moved to vault to limit quarters to 2 items

    banner: Item = Item(
        "banner",
        "order_banner",
        "A tattered banner displaying a silver dragon.",
        weight=2,
        value=15,
    )
    rooms["hall"].add_item(banner)

    icon: Item = Item(
        "icon",
        "icon_ravenloft",
        "The Icon of Ravenloft, hidden behind the desecrated altar.",
        weight=5,
        value=100,
    )
    rooms["castlechapel"].add_item(icon)


def add_weapons(rooms: Dict[str, Room]) -> None:
    """Add weapons to rooms."""

    # Sword in Argynvostholt vault - silver, effective against undead
    sword: Weapon = Weapon(
        name="sword",
        id="silver_sword",
        description="A silver longsword engraved with prayers against the undead.",
        weight=5,
        value=150,
        damage=12,
    )
    rooms["vault"].add_item(sword)

    # Axe in Vallaki stockyard - executioner's weapon
    axe: Weapon = Weapon(
        name="axe",
        id="executioner_axe",
        description="A heavy executioner's axe, stained with old blood.",
        weight=7,
        value=80,
        damage=14,
    )
    rooms["stockyard"].add_item(axe)

    # === CONTENT POLISH ITEMS ===

    # Execution block in stockyard (flavor/lore)
    execution_block: StatefulItem = StatefulItem(
        "block",
        "execution_block",
        "A heavy wooden block stained dark with old blood sits in the center of the stockyard.",
        weight=500,
        value=0,
        takeable=False,
        state="present",
        synonyms=["execution block", "chopping block", "wooden block"],
    )
    execution_block.add_interaction(
        verb="examine",
        message=(
            "The execution block is deeply scarred from countless blows. "
            "Dried blood has soaked into the grain of the wood over the years. "
            "A plaque reads: 'For the unhappy. For the ungrateful. For those "
            "who will not SMILE.'\n\n"
            "An executioner's axe leans against the wall nearby."
        ),
    )
    rooms["stockyard"].add_item(execution_block)

    # Notice board in inn with quest hints
    notice_board: StatefulItem = StatefulItem(
        "board",
        "notice_board",
        "A wooden notice board hangs on the wall, covered with weathered papers.",
        weight=50,
        value=0,
        takeable=False,
        state="present",
        synonyms=["notice board", "bulletin board", "papers", "notices"],
    )
    notice_board.add_interaction(
        verb="read",
        message=(
            "Several notices are pinned to the board:\n\n"
            "LOST: Bones of St. Andral. Last seen in church undercroft. "
            "Reward offered for safe return to Father Lucian.\n\n"
            "WARNING: Children missing near Old Bonegrinder. Avoid the mill!\n\n"
            "WANTED: Information on the Argynvostholt ruins. "
            "Speak to the Vistani seer if you dare.\n\n"
            "NOTICE: The Baron's Festival of the Blazing Sun is MANDATORY. "
            "All citizens WILL be happy. SMILES ARE REQUIRED."
        ),
    )
    notice_board.add_interaction(
        verb="examine",
        message=(
            "Several notices are pinned to the board:\n\n"
            "LOST: Bones of St. Andral. Last seen in church undercroft. "
            "Reward offered for safe return to Father Lucian.\n\n"
            "WARNING: Children missing near Old Bonegrinder. Avoid the mill!\n\n"
            "WANTED: Information on the Argynvostholt ruins. "
            "Speak to the Vistani seer if you dare.\n\n"
            "NOTICE: The Baron's Festival of the Blazing Sun is MANDATORY. "
            "All citizens WILL be happy. SMILES ARE REQUIRED."
        ),
    )
    rooms["inn"].add_item(notice_board)

    # Hint note about cage in bedroom (hag's bedroom)
    doll_note: StatefulItem = StatefulItem(
        "note",
        "doll_note",
        "A crumpled note lies among the broken dolls.",
        weight=1,
        value=0,
        takeable=True,
        state="unread",
        synonyms=["crumpled note", "doll note", "paper"],
    )
    doll_note.add_interaction(
        verb="read",
        message=(
            "The note is written in a childish scrawl:\n\n"
            "'Mommy locks us in the cage upstairs. She says we're special. "
            "The bars are too strong - we tried to bend them. "
            "Only the executioner's blade could break them, "
            "but the axe is far away in the town.'\n\n"
            "The rest of the note is too smeared with tears to read."
        ),
    )
    rooms["bedroom"].add_item(doll_note)

    # Sunsword in castle treasury - hidden until pedestal is unlocked
    sunsword: Weapon = Weapon(
        name="sunsword",
        id="sunsword",
        description="The legendary Sunsword! Its blade blazes with brilliant sunlight.",
        weight=4,
        value=500,
        damage=20,
    )
    sunsword.emits_light = True  # It's a sword made of sunlight!

    # Hidden until pedestal is opened - condition checks pedestal state
    def pedestal_is_open(game_state: Any) -> bool:
        room = game_state.get_room("treasury")
        if not room:
            return False
        for item in room.items:
            if hasattr(item, "id") and item.id == "treasury_pedestal":
                return getattr(item, "state", None) == "unlocked"
        return False

    rooms["treasury"].add_hidden_item(sunsword, pedestal_is_open)

    # Dagger in cellar
    dagger: Weapon = Weapon(
        name="dagger",
        id="cellar_dagger",
        description="A rusty dagger left behind by some previous occupant.",
        weight=1,
        value=5,
        damage=4,
    )
    rooms["cellar"].add_item(dagger)

    # Staff at Tser Pool - moved from wagon to consolidate items
    staff: Weapon = Weapon(
        name="staff",
        id="seer_staff",
        description="An ornate staff topped with a crystal orb.",
        weight=4,
        value=75,
        damage=8,
    )
    rooms["pool"].add_item(staff)

    # Blessed dagger in Cryptkeeper's Sanctum - reward for maze completion
    blessed_dagger: Weapon = Weapon(
        name="dagger",
        id="blessed_dagger",
        description="A silver dagger blessed by ancient priests. It gleams with holy light.",
        weight=1,
        value=120,
        damage=10,
    )
    blessed_dagger.emits_light = True  # Holy weapon radiates light
    rooms["maze_sanctum"].add_item(blessed_dagger)
