# backend/managers/world/level_2_woods.py
"""
Level 2: Svalich Woods & Tser Pool

Dark forest wilderness with Vistani camps and natural dangers.
Wolves patrol the woods, and the Vistani offer cryptic guidance.

Rooms: ~35-40 total
Mobs: Wolves (2-3), bats, Vistani (non-aggressive), seer
Transitions:
  - To Level 3 (Bonegrinder): Standing stones puzzle reveals path
  - To Level 4 (Argynvostholt): Return knight's medallion to ghostly knight at bridge
  - Castle gates are LOCKED until beacon is lit (Level 4 completion)

Design Principles Applied:
  - Room descriptions explicitly name items in the room
  - Items have synonyms for flexible player input
  - Multiple verbs per stateful item (move/pull/lift, examine, search)
  - Examine interactions provide hints for puzzles
  - Hidden items revealed by condition functions
  - Multi-step puzzle chains with clues
"""

from typing import Dict, Any
from models.Room import Room
from models.Item import Item
from models.StatefulItem import StatefulItem
from models.Weapon import Weapon
from .level_base import LevelGenerator
from .shared_items import (
    create_torch,
    create_coin,
)


class Level2Woods(LevelGenerator):
    """Generator for Level 2: Svalich Woods & Tser Pool."""

    level_number = 2
    level_name = "Svalich Woods"

    def generate_rooms(self) -> Dict[str, Room]:
        """Generate all rooms for the Svalich Woods."""

        # =====================================================================
        # MAIN ROADS - Core pathways through the forest
        # =====================================================================

        # Entry point from Level 1 (gatehouse barrier leads here)
        road_south = Room(
            "road_south",
            "Old Svalich Road",
            "The road emerges from the mists. Ancient oaks loom on either side and a "
            "weathered milestone stands at the roadside. A rusted signpost points "
            "south toward a crossroads. To the east, a narrow trail disappears into "
            "the undergrowth.",
            is_outdoor=True,
        )

        crossroads = Room(
            "crossroads",
            "Gallows Crossroads",
            "Four roads meet beneath a grim gallows where a corpse sways in the "
            "windless air. A carved signpost stands at the center. A tarnished brass "
            "bell hangs from it, green with age. Someone scratched words into the post.",
            is_outdoor=True,
        )

        # =====================================================================
        # DEEP WOODS - Core wilderness area
        # =====================================================================

        woods_path = Room(
            "woods_path",
            "Forest Path",
            "A winding path cuts through dense forest. Wolf tracks press deep into "
            "the mud. An old hollow log lies across the path. The path continues "
            "east into deeper woods and a game trail branches north.",
            is_outdoor=True,
        )

        clearing = Room(
            "clearing",
            "Standing Stone Clearing",
            "Three massive standing stones form a triangle in this clearing, each "
            "twice a man's height with spiraling carvings. A flat altar stone lies "
            "at the center. The eastern stone shows a rising sun, the western a "
            "setting sun, the northern a sun at its zenith. Paths lead east and south.",
            is_outdoor=True,
        )

        dark_grove = Room(
            "dark_grove",
            "Dark Grove",
            "The trees grow so close you must squeeze between them. The air is thick "
            "with rot. A carpet of dead leaves covers the ground. A glint of metal "
            "catches your eye near a gnarled root. The clearing lies north.",
            is_dark=True,
            is_outdoor=True,
        )

        wolf_territory = Room(
            "wolf_territory",
            "Wolf Territory",
            "This forest reeks of wolf. Gnawed bones litter the ground. A rocky "
            "outcrop rises to the east with a dark den entrance between the stones. "
            "A pile of bones lies scattered near it. The game trail leads south.",
            is_outdoor=True,
        )

        wolf_den = Room(
            "wolf_den",
            "Wolf Den",
            "The stench of wolf is overwhelming. Bones scatter everywhere - animal "
            "and human. A large nest of matted fur occupies the back. An old leather "
            "satchel lies half-buried in one corner.",
            is_dark=True,
        )

        stream_crossing = Room(
            "stream_crossing",
            "Forest Stream",
            "A clear stream cuts through the forest, surprisingly pure in this "
            "land of mists. Mossy stepping stones provide crossing. The water "
            "is cold and swift, tumbling over smooth rocks. A weathered wooden "
            "sign is nailed to a tree, its message faded.\n\n"
            "A fallen branch has dammed part of the stream, creating a small "
            "pool where fish dart in the shadows. The hollow lies west, and "
            "a mushroom-covered glade opens to the east.",
            is_outdoor=True,
        )

        hollow = Room(
            "hollow",
            "Misty Hollow",
            "A deep depression in the forest floor where mist collects like "
            "water. The fog here is so thick you can barely see the ground. "
            "Whispers seem to echo from within the mist - voices speaking words "
            "you can almost understand. A crude stone marker stands at the edge.\n\n"
            "An old rope dangles from a tree branch overhead, swaying gently "
            "despite the still air. The stream lies to the east, the main "
            "woods are to the north.",
            is_outdoor=True,
        )

        mushroom_glade = Room(
            "mushroom_glade",
            "Mushroom Glade",
            "A perfect ring of pale mushrooms encircles this small glade. The "
            "air here feels charged, like before a lightning strike. Local legend "
            "warns against stepping inside fairy rings. Strange lights flicker "
            "at the edge of vision.\n\n"
            "At the center of the ring sits a small wooden box, weathered by "
            "years of rain and sun. The stream lies to the west.",
            is_outdoor=True,
        )

        # =====================================================================
        # TSER POOL - Vistani camp area
        # =====================================================================

        tser_pool = Room(
            "tser_pool",
            "Tser Pool",
            "A dark pool reflects the grey sky like a tarnished mirror. Colorful "
            "Vistani wagons are camped on the muddy shore, their painted sides "
            "a jarring splash of color in this dreary land. Cooking fires burn, "
            "and the smell of spiced meat drifts on the breeze.\n\n"
            "A fortune teller's wagon stands apart from the others, its door "
            "marked with strange symbols. A merchant's stall has been set up "
            "near the water's edge. An old wooden dock extends into the pool.",
            is_outdoor=True,
        )

        wagon = Room(
            "wagon",
            "Fortune Teller's Wagon",
            "Incense smoke hangs thick in the cramped wagon, making your eyes "
            "water. Silken scarves of deep purple and crimson cover every surface. "
            "Strange charms dangle from the ceiling - bones, feathers, glass eyes. "
            "A crystal ball sits on a velvet cloth before you.\n\n"
            "An ancient woman watches from her chair, her milky eyes seeing far "
            "more than they should. A worn deck of tarot cards lies on the table "
            "beside a silver bell.",
        )

        merchant_stall = Room(
            "merchant_stall",
            "Vistani Merchant's Stall",
            "A canvas awning shelters tables laden with curious goods - jewelry "
            "from distant lands, bundles of dried herbs, stoppered bottles of "
            "unknown liquids, and weapons of unusual make. A Vistani man with "
            "gold rings in his ears watches you with knowing eyes.\n\n"
            "A locked strongbox sits beneath the main table. A wooden rack "
            "displays several blades and a fine crossbow.",
        )

        old_dock = Room(
            "old_dock",
            "Rotting Dock",
            "Weathered planks creak beneath your feet as you walk out over the "
            "dark water. The pool is deeper than it looks - you cannot see the "
            "bottom. Something large moves in the depths. A rowboat is tied to "
            "a post, half-full of rainwater.\n\n"
            "The shore lies back to the west. An inscription is carved into one "
            "of the dock posts, barely visible beneath years of grime.",
        )

        # =====================================================================
        # BRIDGE & WESTERN APPROACHES
        # =====================================================================

        river_approach = Room(
            "river_approach",
            "River Approach",
            "The road narrows as it approaches a rushing river. The water is "
            "black and swift, roaring over rocks. Spray fills the air. An ancient "
            "stone bridge spans the torrent ahead, gargoyles crouching at either "
            "end. Something moves on the bridge.\n\n"
            "A worn stone bench sits by the roadside, placed here long ago for "
            "weary travelers. Someone has left fresh flowers on it.",
            is_outdoor=True,
        )

        bridge = Room(
            "bridge",
            "Stone Bridge",
            "This ancient bridge of weathered stone spans the rushing river below. "
            "Gargoyle statues crouch at each corner, their faces worn smooth by "
            "centuries of rain. The water's roar is deafening.\n\n"
            "A spectral knight bars the western path, his translucent form "
            "flickering like candlelight. He wears tarnished armor bearing a "
            "dragon crest, and his hollow eyes burn with eternal purpose. His "
            "skeletal hand rests on a ghostly sword.",
            is_outdoor=True,
        )

        # =====================================================================
        # CASTLE APPROACHES (gated until beacon lit)
        # =====================================================================

        castle_road = Room(
            "castle_road",
            "Road to the Castle",
            "The road climbs steeply through the forest toward a dark silhouette "
            "looming against the grey sky - Castle Ravenloft. Lightning flickers "
            "around its spires. The air grows colder with each step.\n\n"
            "A wayside shrine stands at the roadside, its guardian statue "
            "weathered beyond recognition. Offerings - coins, flowers, teeth - "
            "are piled at its base. The castle gates are visible ahead.",
            is_outdoor=True,
        )

        castle_gates = Room(
            "castle_gates",
            "Castle Gates",
            "Massive iron gates tower before you, twice the height of a man. "
            "Frost covers every surface despite no visible cold, and glowing "
            "runes pulse with dark energy across the metal. The castle beyond "
            "looms impossibly large, its spires stabbing at the churning sky.\n\n"
            "A heavy iron chain secures the gates, its links as thick as your "
            "wrist. A brass plate beside the gate bears an inscription. Dragon "
            "statues flank the entrance, their eyes following your movements.",
            is_outdoor=True,
        )

        # =====================================================================
        # HIDDEN AREAS (revealed by puzzles)
        # =====================================================================

        barrow = Room(
            "barrow",
            "Ancient Barrow",
            "Stone steps descend into an ancient burial mound. The air is thick "
            "with the dust of ages and the smell of old death. Niches in the "
            "walls once held offerings, now long since crumbled or stolen.\n\n"
            "A stone sarcophagus dominates the chamber, its lid carved with the "
            "image of a sleeping warrior. Tarnished coins are scattered on the "
            "floor. A rusted sword leans against the far wall.",
            is_dark=True,
        )

        # =====================================================================
        # FLAVOR ROOMS - Atmospheric expansion
        # =====================================================================

        overgrown_trail = Room(
            "overgrown_trail",
            "Overgrown Trail",
            "Brambles and thorns have nearly consumed this old trail. Scratches "
            "on tree trunks mark the passage of deer - and perhaps wolves hunting "
            "them. A weathered boot lies in the undergrowth, its owner long gone.\n\n"
            "The trail continues south toward the main road.",
            is_outdoor=True,
        )

        fallen_tree = Room(
            "fallen_tree",
            "Fallen Oak",
            "A massive oak has fallen across the path, torn from the earth by "
            "some ancient storm. Its root ball forms a wall taller than a man. "
            "The hollow beneath the roots creates a natural shelter, and someone "
            "has used it recently - ashes of a cook fire remain.\n\n"
            "An old pack lies in the shelter, forgotten or abandoned. The trail "
            "continues north toward the forest path.",
            is_outdoor=True,
        )

        raven_roost = Room(
            "raven_roost",
            "Raven's Roost",
            "An ancient dead tree stands alone in a small clearing, every branch "
            "covered in ravens. Dozens of the black birds watch you with gleaming "
            "intelligent eyes. They seem to be waiting for something - or someone.\n\n"
            "One raven, larger than the others, wears a silver band around its "
            "leg. Strange droppings - some glittering - cover the ground beneath "
            "the tree. A path leads west to the shrine.",
            is_outdoor=True,
        )

        old_shrine = Room(
            "old_shrine",
            "Forgotten Shrine",
            "A small stone shrine stands half-hidden by overgrowth, dedicated to "
            "a deity long forgotten in this cursed land. Despite its age, fresh "
            "offerings appear at its base - wildflowers, small coins, bits of "
            "bread. Someone still believes.\n\n"
            "The shrine's guardian statue has lost its head, but its hands are "
            "cupped as if waiting to receive something. A silver bowl sits "
            "between the stone palms. The ravens roost lies east.",
            is_outdoor=True,
        )

        ravine_edge = Room(
            "ravine_edge",
            "Ravine Edge",
            "A deep ravine cuts through the forest, its bottom lost in shadow "
            "and mist. You can hear water rushing far below. A fallen log "
            "provides precarious crossing - it looks stable enough, but the "
            "drop is deadly.\n\n"
            "Someone has carved handholds into the log for better grip. Rope "
            "fibers caught on splinters suggest a safer method once existed.",
            is_outdoor=True,
        )

        hunters_cache = Room(
            "hunters_cache",
            "Hunter's Cache",
            "A wooden platform is built into the branches of an ancient oak, "
            "accessible by a rope ladder. This hunter's blind has been abandoned "
            "for some time - leaves cover everything, and spider webs fill the "
            "corners.\n\n"
            "A locked wooden chest sits in one corner, its iron bands rusted. "
            "Carved into the platform's railing are tally marks - dozens of them.",
        )

        # =====================================================================
        # Store all rooms
        # =====================================================================

        self._rooms = {
            # Main roads
            "road_south": road_south,
            "crossroads": crossroads,
            # Deep woods
            "woods_path": woods_path,
            "clearing": clearing,
            "dark_grove": dark_grove,
            "wolf_territory": wolf_territory,
            "wolf_den": wolf_den,
            "stream_crossing": stream_crossing,
            "hollow": hollow,
            "mushroom_glade": mushroom_glade,
            # Tser Pool area
            "tser_pool": tser_pool,
            "wagon": wagon,
            "merchant_stall": merchant_stall,
            "old_dock": old_dock,
            # Bridge & approaches
            "river_approach": river_approach,
            "bridge": bridge,
            "castle_road": castle_road,
            "castle_gates": castle_gates,
            # Hidden areas
            "barrow": barrow,
            # Flavor rooms
            "overgrown_trail": overgrown_trail,
            "fallen_tree": fallen_tree,
            "raven_roost": raven_roost,
            "old_shrine": old_shrine,
            "ravine_edge": ravine_edge,
            "hunters_cache": hunters_cache,
        }

        return self._rooms

    def connect_internal_exits(self) -> None:
        """Connect exits between rooms within the Woods."""

        # =====================================================================
        # MAIN ROAD CONNECTIONS
        # =====================================================================

        # Entry point from Level 1 (gatehouse barrier south exit leads here)
        self._rooms["road_south"].exits = {
            "north": "gatehouse",  # Connection back to Level 1 (through mist barrier)
            "south": "crossroads",
            "east": "overgrown_trail",
        }

        # Crossroads - Central hub of Level 2
        self._rooms["crossroads"].exits = {
            "north": "road_south",
            "south": "tser_pool",
            "east": "castle_road",
            "west": "river_approach",
            "southeast": "woods_path",
        }

        # =====================================================================
        # DEEP WOODS CONNECTIONS
        # =====================================================================

        self._rooms["woods_path"].exits = {
            "northwest": "crossroads",
            "east": "clearing",
            "north": "wolf_territory",
            "south": "fallen_tree",
        }

        self._rooms["clearing"].exits = {
            "west": "woods_path",
            "south": "dark_grove",
            # "down": "barrow" - hidden, revealed by standing stones puzzle
        }

        self._rooms["dark_grove"].exits = {
            "north": "clearing",
            "east": "hollow",
        }

        self._rooms["wolf_territory"].exits = {
            "south": "woods_path",
            "in": "wolf_den",
        }

        self._rooms["wolf_den"].exits = {
            "out": "wolf_territory",
        }

        self._rooms["stream_crossing"].exits = {
            "west": "hollow",
            "east": "mushroom_glade",
            "north": "ravine_edge",
        }

        self._rooms["hollow"].exits = {
            "north": "woods_path",
            "east": "stream_crossing",
            "west": "dark_grove",
        }

        self._rooms["mushroom_glade"].exits = {
            "west": "stream_crossing",
        }

        # =====================================================================
        # TSER POOL CONNECTIONS
        # =====================================================================

        self._rooms["tser_pool"].exits = {
            "north": "crossroads",
            "in": "wagon",
            "east": "merchant_stall",
            "south": "old_dock",
        }

        self._rooms["wagon"].exits = {
            "out": "tser_pool",
        }

        self._rooms["merchant_stall"].exits = {
            "west": "tser_pool",
        }

        self._rooms["old_dock"].exits = {
            "north": "tser_pool",
        }

        # =====================================================================
        # BRIDGE & APPROACHES
        # =====================================================================

        self._rooms["river_approach"].exits = {
            "east": "crossroads",
            "west": "bridge",
        }

        self._rooms["bridge"].exits = {
            "east": "river_approach",
            # "west": "towngate" - Level 4 transition via ghostly knight
        }

        self._rooms["castle_road"].exits = {
            "west": "crossroads",
            "east": "castle_gates",
        }

        self._rooms["castle_gates"].exits = {
            "west": "castle_road",
            # "east": "courtyard" - Level 5, locked until beacon lit
        }

        # =====================================================================
        # HIDDEN AREAS
        # =====================================================================

        self._rooms["barrow"].exits = {
            "up": "clearing",
        }

        # =====================================================================
        # FLAVOR ROOM CONNECTIONS
        # =====================================================================

        self._rooms["overgrown_trail"].exits = {
            "west": "road_south",
            "south": "raven_roost",
        }

        self._rooms["fallen_tree"].exits = {
            "north": "woods_path",
            "east": "hunters_cache",
        }

        self._rooms["raven_roost"].exits = {
            "north": "overgrown_trail",
            "west": "old_shrine",
        }

        self._rooms["old_shrine"].exits = {
            "east": "raven_roost",
        }

        self._rooms["ravine_edge"].exits = {
            "south": "stream_crossing",
        }

        self._rooms["hunters_cache"].exits = {
            "west": "fallen_tree",
            "down": "fallen_tree",
        }

    def add_items(self) -> None:
        """Add items to rooms in the Woods."""

        # =====================================================================
        # ROAD SOUTH - Entry from Level 1
        # =====================================================================

        milestone = StatefulItem(
            name="milestone",
            id="road_milestone",
            description="A weathered stone milestone, its inscription worn by time.",
            state="unread",
            takeable=False,
            synonyms=["stone", "marker", "signpost", "post"],
        )
        milestone.set_room_id("road_south")
        milestone.add_state_description(
            "unread",
            "A weathered milestone stands at the roadside.",
        )
        milestone.add_state_description(
            "read",
            "The milestone's inscription has been traced with your finger.",
        )
        milestone.add_interaction(
            verb="read",
            from_state="unread",
            target_state="read",
            message=(
                "You trace the worn letters with your finger:\n\n"
                "    'Barovia - 1 league North\n"
                "     Crossroads - 100 paces South\n"
                "     Beware the Mists'\n\n"
                "Below the official inscription, someone has scratched:\n"
                "'The stones remember. Sunrise, noon, sunset.'"
            ),
        )
        milestone.add_interaction(
            verb="examine",
            message=(
                "The milestone is ancient, made of granite. The inscription is "
                "barely legible, worn by countless years of rain and wind. "
                "Someone has scratched something below the official text."
            ),
        )
        self._rooms["road_south"].add_item(milestone)

        # =====================================================================
        # CROSSROADS - Signpost and bell
        # =====================================================================

        signpost = StatefulItem(
            name="signpost",
            id="crossroads_signpost",
            description="A carved wooden signpost with four pointing arms.",
            state="default",
            takeable=False,
            synonyms=["sign", "post", "wooden post"],
        )
        signpost.set_room_id("crossroads")
        signpost.add_state_description(
            "default",
            "A weathered signpost points to distant destinations.",
        )
        signpost.add_interaction(
            verb="read",
            message=(
                "The signpost arms read:\n"
                "  North: 'BAROVIA - Village of the Damned'\n"
                "  South: 'TSER POOL - The Vistani Know'\n"
                "  East:  'RAVENLOFT - Abandon Hope'\n"
                "  West:  'VALLAKI - Through the Ghost'\n\n"
                "Scratched into the post below: 'Ring for luck - if you dare.'"
            ),
        )
        signpost.add_interaction(
            verb="examine",
            message=(
                "The signpost is old but well-maintained. Four arms point "
                "in the cardinal directions. A tarnished brass bell hangs "
                "beneath the main post. Scratch marks below suggest many "
                "travelers have left their mark."
            ),
        )
        self._rooms["crossroads"].add_item(signpost)

        brass_bell = StatefulItem(
            name="brass bell",
            id="crossroads_bell",
            description="A tarnished brass bell hanging from the signpost.",
            state="silent",
            takeable=False,
            synonyms=["bell", "tarnished bell"],
        )
        brass_bell.set_room_id("crossroads")
        brass_bell.add_state_description(
            "silent",
            "A tarnished brass bell hangs from the signpost, waiting to be rung.",
        )
        brass_bell.add_state_description(
            "rung",
            "The brass bell sways gently, its echo fading.",
        )
        brass_bell.add_interaction(
            verb="ring",
            from_state="silent",
            target_state="rung",
            message=(
                "You ring the bell. Its clear tone echoes across the crossroads, "
                "far louder than such a small bell should be. The crows on the "
                "gallows take flight. For a moment, you feel watched.\n\n"
                "The corpse on the gallows seems to twitch. Probably the wind."
            ),
        )
        brass_bell.add_interaction(
            verb="ring",
            from_state="rung",
            target_state="silent",
            message="You ring the bell again. The crows have returned, watching.",
        )
        brass_bell.add_interaction(
            verb="examine",
            message=(
                "The brass bell is green with age but still functional. A small "
                "inscription on its rim reads: 'Ring for the dead, that they may "
                "rest.' Cheerful."
            ),
        )
        brass_bell.add_interaction(
            verb="take",
            message="The bell is firmly attached to the signpost. It won't budge.",
        )
        self._rooms["crossroads"].add_item(brass_bell)

        # Rotting corpse (flavor)
        corpse = StatefulItem(
            name="corpse",
            id="gallows_corpse",
            description="A rotting corpse swings from the gallows.",
            state="default",
            takeable=False,
            synonyms=["body", "hanged man", "dead man", "rotting body"],
        )
        corpse.set_room_id("crossroads")
        corpse.add_state_description(
            "default",
            "A rotting corpse sways gently on the gallows.",
        )
        corpse.add_state_description(
            "searched",
            "The corpse has been searched. Its pockets are empty.",
        )
        corpse.add_interaction(
            verb="examine",
            message=(
                "The corpse wears the tattered remains of a merchant's outfit. "
                "A sign around its neck reads: 'TRAITOR TO THE LORD.' The "
                "ravens have been at the eyes. Something bulges in the coat pocket."
            ),
        )
        corpse.add_interaction(
            verb="search",
            from_state="default",
            target_state="searched",
            message=(
                "You reach into the corpse's pocket, trying not to gag. Your "
                "fingers close around a folded piece of paper - a note! The rest "
                "of the pockets contain only lint and despair."
            ),
        )
        self._rooms["crossroads"].add_item(corpse)

        # Hidden note in corpse
        corpse_note = Item(
            name="note",
            id="corpse_note",
            description=(
                "A crumpled, stained note. The handwriting is hurried:\n\n"
                "'If you read this, I am dead. The ghost on the bridge seeks "
                "his medallion - stolen by wolves. Their den lies east of the "
                "game trail. Return it and he may let you pass.\n\n"
                "Do not trust the hags. Do not enter the mill. May the "
                "Morninglord have mercy on your soul.'"
            ),
            weight=0,
            value=0,
            takeable=True,
            synonyms=["crumpled note", "paper", "letter"],
        )

        def corpse_searched(game_state: Any) -> bool:
            room = game_state.get_room("crossroads")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "gallows_corpse":
                    return getattr(item, "state", None) == "searched"
            return False

        self._rooms["crossroads"].add_hidden_item(corpse_note, corpse_searched)

        # =====================================================================
        # CLEARING - Standing Stones Puzzle
        # =====================================================================

        # Eastern Stone
        eastern_stone = StatefulItem(
            name="eastern stone",
            id="eastern_stone",
            description="A massive standing stone carved with a sun rising over mountains.",
            state="default",
            takeable=False,
            synonyms=["east stone", "sunrise stone", "stone"],
        )
        eastern_stone.set_room_id("clearing")
        eastern_stone.add_state_description(
            "default",
            "The eastern stone shows a faded sun carving, its light obscured.",
        )
        eastern_stone.add_state_description(
            "sunrise",
            "The eastern stone glows faintly - its sun carving depicts a sunrise!",
        )
        eastern_stone.add_state_description(
            "noon",
            "The eastern stone's sun is at its zenith.",
        )
        eastern_stone.add_state_description(
            "sunset",
            "The eastern stone's sun is setting.",
        )
        eastern_stone.add_interaction(
            verb="turn",
            from_state="default",
            target_state="sunrise",
            message=(
                "You grip the rough stone and turn it. The carvings shift - "
                "the sun now rises over the mountains. The stone hums faintly."
            ),
        )
        eastern_stone.add_interaction(
            verb="turn",
            from_state="sunrise",
            target_state="noon",
            message="You turn the stone. The sun climbs to noon.",
        )
        eastern_stone.add_interaction(
            verb="turn",
            from_state="noon",
            target_state="sunset",
            message="You turn the stone. The sun descends toward sunset.",
        )
        eastern_stone.add_interaction(
            verb="turn",
            from_state="sunset",
            target_state="default",
            message="You turn the stone back to its faded, neutral position.",
        )
        eastern_stone.add_interaction(
            verb="push",
            from_state="default",
            target_state="sunrise",
            message="You push against the stone. It rotates - sunrise!",
        )
        eastern_stone.add_interaction(
            verb="examine",
            message=(
                "The eastern stone is covered in spiraling carvings. The main "
                "image shows a sun over mountains. The stone can be rotated to "
                "show different sun positions. An inscription at the base reads: "
                "'THE EAST WELCOMES THE DAWN.'"
            ),
        )
        self._rooms["clearing"].add_item(eastern_stone)

        # Western Stone
        western_stone = StatefulItem(
            name="western stone",
            id="western_stone",
            description="A massive standing stone carved with a sun setting into the sea.",
            state="default",
            takeable=False,
            synonyms=["west stone", "sunset stone"],
        )
        western_stone.set_room_id("clearing")
        western_stone.add_state_description(
            "default",
            "The western stone shows a faded sun carving over water.",
        )
        western_stone.add_state_description(
            "sunrise",
            "The western stone's sun is rising.",
        )
        western_stone.add_state_description(
            "noon",
            "The western stone's sun is at noon.",
        )
        western_stone.add_state_description(
            "sunset",
            "The western stone glows warmly - its sun sets into the sea!",
        )
        western_stone.add_interaction(
            verb="turn",
            from_state="default",
            target_state="sunrise",
            message="You turn the western stone. The sun begins to rise.",
        )
        western_stone.add_interaction(
            verb="turn",
            from_state="sunrise",
            target_state="noon",
            message="You turn the stone. The sun reaches noon.",
        )
        western_stone.add_interaction(
            verb="turn",
            from_state="noon",
            target_state="sunset",
            message=(
                "You turn the western stone. The sun sinks into the carved sea, "
                "and the stone glows with warm light. Sunset!"
            ),
        )
        western_stone.add_interaction(
            verb="turn",
            from_state="sunset",
            target_state="default",
            message="You turn the stone back to its neutral position.",
        )
        western_stone.add_interaction(
            verb="push",
            from_state="noon",
            target_state="sunset",
            message="You push the stone. It rotates to show sunset!",
        )
        western_stone.add_interaction(
            verb="examine",
            message=(
                "The western stone depicts a sun over rolling waves. Like the "
                "others, it can be rotated. The inscription reads: "
                "'THE WEST BIDS FAREWELL TO LIGHT.'"
            ),
        )
        self._rooms["clearing"].add_item(western_stone)

        # Northern Stone
        northern_stone = StatefulItem(
            name="northern stone",
            id="northern_stone",
            description="A massive standing stone carved with a blazing sun overhead.",
            state="default",
            takeable=False,
            synonyms=["north stone", "noon stone"],
        )
        northern_stone.set_room_id("clearing")
        northern_stone.add_state_description(
            "default",
            "The northern stone shows a faded sun directly overhead.",
        )
        northern_stone.add_state_description(
            "sunrise",
            "The northern stone's sun is rising from the horizon.",
        )
        northern_stone.add_state_description(
            "noon",
            "The northern stone blazes with light - high noon!",
        )
        northern_stone.add_state_description(
            "sunset",
            "The northern stone's sun is setting.",
        )
        northern_stone.add_interaction(
            verb="turn",
            from_state="default",
            target_state="sunrise",
            message="You turn the northern stone. Dawn breaks in the carving.",
        )
        northern_stone.add_interaction(
            verb="turn",
            from_state="sunrise",
            target_state="noon",
            message=(
                "You turn the northern stone. The sun climbs to its zenith, "
                "blazing directly overhead. The stone radiates warmth!"
            ),
        )
        northern_stone.add_interaction(
            verb="turn",
            from_state="noon",
            target_state="sunset",
            message="You turn the stone. The sun begins its descent.",
        )
        northern_stone.add_interaction(
            verb="turn",
            from_state="sunset",
            target_state="default",
            message="You turn the stone back to neutral.",
        )
        northern_stone.add_interaction(
            verb="push",
            from_state="sunrise",
            target_state="noon",
            message="You push the stone. High noon blazes forth!",
        )
        northern_stone.add_interaction(
            verb="examine",
            message=(
                "The northern stone shows a sun directly overhead, surrounded "
                "by radiating lines. The inscription reads: "
                "'THE NORTH STANDS AT ZENITH.'"
            ),
        )
        self._rooms["clearing"].add_item(northern_stone)

        # Altar Stone
        def stones_aligned(game_state: Any) -> bool:
            """Check if all three stones are in correct positions."""
            room = game_state.get_room("clearing")
            if not room:
                return False
            east_correct = False
            west_correct = False
            north_correct = False
            for item in room.items:
                item_id = getattr(item, "id", None)
                state = getattr(item, "state", None)
                if item_id == "eastern_stone" and state == "sunrise":
                    east_correct = True
                elif item_id == "western_stone" and state == "sunset":
                    west_correct = True
                elif item_id == "northern_stone" and state == "noon":
                    north_correct = True
            return east_correct and west_correct and north_correct

        altar = StatefulItem(
            name="altar stone",
            id="clearing_altar",
            description="A flat altar stone lies at the center of the three standing stones.",
            state="dormant",
            takeable=False,
            synonyms=["altar", "flat stone", "center stone"],
        )
        altar.set_room_id("clearing")
        altar.add_state_description(
            "dormant",
            "A flat altar stone lies silent at the center of the formation.",
        )
        altar.add_state_description(
            "active",
            "The altar pulses with ancient power! A passage has opened downward!",
        )
        altar.add_interaction(
            verb="touch",
            from_state="dormant",
            target_state="active",
            message=(
                "As you touch the altar, the three standing stones begin to hum. "
                "Lines of light connect them - sunrise, noon, sunset! The earth "
                "trembles, and the altar stone slides aside, revealing stone steps "
                "descending into darkness.\n\n"
                "An ancient barrow lies below. The path to forgotten knowledge "
                "is open!"
            ),
            conditional_fn=stones_aligned,
            add_exit=("down", "barrow"),
        )
        altar.add_interaction(
            verb="touch",
            from_state="dormant",
            message=(
                "You place your hands on the altar stone. It feels warm, almost "
                "alive. But nothing happens. The three surrounding stones seem "
                "to be waiting for something... their sun carvings hint at the "
                "natural order of day."
            ),
        )
        altar.add_interaction(
            verb="examine",
            message=(
                "The altar is a flat granite slab, worn smooth by countless "
                "years. Faint traces of old offerings stain its surface - blood, "
                "wine, tears. An inscription circles its edge:\n\n"
                "'When dawn rises in the east, noon blazes in the north, and "
                "sunset falls in the west, touch the heart and descend to wisdom.'"
            ),
        )
        altar.add_interaction(
            verb="push",
            from_state="dormant",
            message="The altar doesn't budge. Perhaps there's another way to activate it.",
        )
        altar.add_interaction(
            verb="activate",
            from_state="dormant",
            target_state="active",
            message=(
                "The altar responds to your intent! Light streams between the "
                "standing stones as they recognize the correct alignment. The "
                "altar slides aside with a grinding of ancient stone."
            ),
            conditional_fn=stones_aligned,
            add_exit=("down", "barrow"),
        )
        self._rooms["clearing"].add_item(altar)

        # =====================================================================
        # WOLF DEN - Medallion puzzle
        # =====================================================================

        bone_pile = StatefulItem(
            name="pile of bones",
            id="wolf_bones",
            description="A grisly pile of gnawed bones - animal and human alike.",
            state="unsearched",
            takeable=False,
            synonyms=["bones", "bone pile", "gnawed bones"],
        )
        bone_pile.set_room_id("wolf_den")
        bone_pile.add_state_description(
            "unsearched",
            "A pile of gnawed bones lies scattered near your feet.",
        )
        bone_pile.add_state_description(
            "searched",
            "The bone pile has been searched. Something metallic glints within.",
        )
        bone_pile.add_interaction(
            verb="search",
            from_state="unsearched",
            target_state="searched",
            message=(
                "You dig through the grisly pile, trying not to think about "
                "whose bones these might be. Your fingers close around something "
                "cold and metallic - a silver medallion bearing a dragon crest!"
            ),
        )
        bone_pile.add_interaction(
            verb="examine",
            from_state="unsearched",
            message=(
                "The bones are a mix of animal and human, all gnawed clean by "
                "powerful jaws. Some still wear scraps of clothing. You notice "
                "something glinting deeper in the pile - metal of some kind."
            ),
        )
        bone_pile.add_interaction(
            verb="examine",
            from_state="searched",
            message=(
                "The scattered bones reveal their secrets. Among them, you can "
                "now clearly see a silver medallion with a dragon design."
            ),
        )
        bone_pile.add_interaction(
            verb="dig",
            from_state="unsearched",
            target_state="searched",
            message=(
                "You dig through the bones, pushing aside skulls and ribcages. "
                "There! A silver medallion lies beneath, its dragon crest still "
                "bright despite years among the dead."
            ),
        )
        self._rooms["wolf_den"].add_item(bone_pile)

        # Knight's medallion - hidden until bones searched
        medallion = Item(
            name="medallion",
            id="knight_medallion",
            description=(
                "A silver medallion bearing the crest of a knight's order - a "
                "dragon coiled around a sword. Despite its time among wolf bones, "
                "it gleams as if newly polished. It feels cold to the touch."
            ),
            weight=0,
            value=50,
            takeable=True,
            synonyms=[
                "silver medallion",
                "dragon medallion",
                "knight's medallion",
                "crest",
            ],
        )

        def bones_searched(game_state: Any) -> bool:
            room = game_state.get_room("wolf_den")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "wolf_bones":
                    return getattr(item, "state", None) == "searched"
            return False

        self._rooms["wolf_den"].add_hidden_item(medallion, bones_searched)

        # Old satchel with clue
        satchel = StatefulItem(
            name="leather satchel",
            id="wolf_satchel",
            description="An old leather satchel, half-buried in debris.",
            state="closed",
            takeable=False,
            synonyms=["satchel", "bag", "old satchel"],
        )
        satchel.set_room_id("wolf_den")
        satchel.add_state_description(
            "closed",
            "An old leather satchel lies half-buried in one corner.",
        )
        satchel.add_state_description(
            "open",
            "The leather satchel lies open, its contents revealed.",
        )
        satchel.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message=(
                "You pull the satchel from the debris and open it. Inside you "
                "find a few copper coins, a dagger, and a water-stained letter:\n\n"
                "'Brother,\n"
                "If the wolves take me, know that I died trying to recover Sir "
                "Godfrey's medallion. The ghost on the bridge cannot rest until "
                "it is returned. Search among the bones if you must.\n"
                "May the Morninglord guide you.\n"
                "-Edmund'"
            ),
        )
        satchel.add_interaction(
            verb="search",
            from_state="closed",
            target_state="open",
            message="You open and search the satchel, finding coins, a dagger, and a letter.",
        )
        satchel.add_interaction(
            verb="examine",
            message="The leather is cracked and old, but the satchel might still hold something.",
        )
        self._rooms["wolf_den"].add_item(satchel)

        # Dagger from satchel (hidden until opened)
        rusty_dagger = Weapon(
            name="dagger",
            id="wolf_dagger",
            description="A rusty but functional dagger, found in the wolf den.",
            weight=1,
            value=8,
            takeable=True,
            damage=4,
            min_level="Neophyte",
            min_strength=0,
            min_dexterity=0,
        )
        rusty_dagger.synonyms = ["rusty dagger", "knife"]

        def satchel_opened(game_state: Any) -> bool:
            room = game_state.get_room("wolf_den")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "wolf_satchel":
                    return getattr(item, "state", None) == "open"
            return False

        self._rooms["wolf_den"].add_hidden_item(rusty_dagger, satchel_opened)

        # =====================================================================
        # BRIDGE - Ghostly Knight
        # =====================================================================

        ghostly_knight = StatefulItem(
            name="spectral knight",
            id="ghost_knight",
            description=(
                "A ghostly knight in tarnished armor blocks the western path. "
                "His form flickers like candlelight, and his hollow eyes burn "
                "with eternal purpose."
            ),
            state="blocking",
            takeable=False,
            synonyms=["knight", "ghost", "ghostly knight", "spirit", "specter"],
        )
        ghostly_knight.set_room_id("bridge")
        ghostly_knight.add_state_description(
            "blocking",
            "A spectral knight stands guard, blocking all passage west.",
        )
        ghostly_knight.add_state_description(
            "appeased",
            "The ghostly knight bows respectfully, his vigil ended at last.",
        )
        ghostly_knight.add_interaction(
            verb="give",
            required_instrument="knight_medallion",
            from_state="blocking",
            target_state="appeased",
            message=(
                "You hold out the silver medallion. The knight's hollow eyes widen "
                "with recognition, his flickering form steadying.\n\n"
                "'My... my honor,' he whispers, his voice like wind through dead "
                "leaves. 'Returned at last, after all these years.'\n\n"
                "He takes the medallion with translucent fingers, pressing it to "
                "his chest where his heart once beat. A single spectral tear runs "
                "down his cheek.\n\n"
                "'You have my eternal gratitude, mortal. The road to Vallaki is "
                "open to you. May you find what you seek in these cursed lands.'\n\n"
                "He steps aside, bowing deeply, and the way west is clear."
            ),
            add_exit=("west", "towngate"),  # Opens path to Level 4 Vallaki
            consume_instrument=True,
        )
        ghostly_knight.add_interaction(
            verb="give",
            required_instrument="medallion",
            from_state="blocking",
            target_state="appeased",
            message=(
                "You hold out the medallion. The knight's hollow eyes widen - "
                "'My honor! Returned at last!' He takes it reverently and steps "
                "aside, bowing. The way west to Vallaki is open."
            ),
            add_exit=("west", "towngate"),
            consume_instrument=True,
        )
        ghostly_knight.add_interaction(
            verb="talk",
            from_state="blocking",
            message=(
                "The knight's hollow voice echoes across the bridge:\n\n"
                "'I cannot let you pass, mortal. My honor was lost in these very "
                "woods - my medallion, stolen by the wolf pack that haunts the "
                "eastern trails. Until it is returned, I am bound to this bridge.'\n\n"
                "He gestures toward the forest with his ghostly blade.\n\n"
                "'The wolves lair somewhere east of here, along the game trail. "
                "Find my medallion among their... trophies... and I shall trouble "
                "you no more.'"
            ),
        )
        ghostly_knight.add_interaction(
            verb="attack",
            from_state="blocking",
            message=(
                "Your weapon passes through the knight as if through smoke. "
                "He regards you with infinite sadness in his burning eyes.\n\n"
                "'I am beyond your harm, mortal. I have stood this vigil for "
                "three hundred years. Find my medallion if you wish to pass.'"
            ),
        )
        ghostly_knight.add_interaction(
            verb="examine",
            from_state="blocking",
            message=(
                "The knight wears tarnished plate armor bearing a dragon crest - "
                "the same design as on a medallion, you realize. His form "
                "flickers constantly, more solid at times, nearly invisible at "
                "others. The sword in his hand looks terrifyingly real.\n\n"
                "An inscription on his breastplate reads: 'Sir Godfrey, Order "
                "of the Silver Dragon.'"
            ),
        )
        self._rooms["bridge"].add_item(ghostly_knight)

        # =====================================================================
        # CASTLE GATES - Dark magic barrier
        # =====================================================================

        def beacon_lit(game_state: Any) -> bool:
            """Check if the dragon beacon has been lit (Level 4 completion)."""
            # This will be a global flag set when players complete Level 4
            return getattr(game_state, "beacon_lit", False)

        iron_gates = StatefulItem(
            name="iron gates",
            id="castle_gates_item",
            description="Massive iron gates covered in frost and glowing runes.",
            state="sealed",
            takeable=False,
            synonyms=["gates", "castle gates", "massive gates"],
        )
        iron_gates.set_room_id("castle_gates")
        iron_gates.add_state_description(
            "sealed",
            "The massive iron gates are sealed by dark magic. Runes pulse with malevolent light.",
        )
        iron_gates.add_state_description(
            "open",
            "The iron gates stand open, the runes dark and lifeless.",
        )
        iron_gates.add_interaction(
            verb="open",
            from_state="sealed",
            message=(
                "You push against the gates with all your strength. They don't "
                "budge - not even slightly. The runes flare angrily at your touch, "
                "and cold burns your palms.\n\n"
                "Some greater power seals these gates. The inscription speaks of "
                "a beacon... perhaps lighting it would weaken this dark magic."
            ),
        )
        iron_gates.add_interaction(
            verb="open",
            from_state="sealed",
            target_state="open",
            message=(
                "As you touch the gates, light erupts on the horizon - the dragon "
                "beacon! Its radiance washes across the land, and the runes on the "
                "gates flicker and die. The iron groans, frost shattering, as the "
                "gates slowly swing open.\n\n"
                "Castle Ravenloft awaits."
            ),
            conditional_fn=beacon_lit,
            add_exit=("east", "courtyard"),  # Level 5
        )
        iron_gates.add_interaction(
            verb="push",
            from_state="sealed",
            message="The gates are sealed by magic. No mortal strength can budge them.",
        )
        iron_gates.add_interaction(
            verb="examine",
            message=(
                "The gates are twice the height of a man, their iron surface "
                "covered in frost despite no visible cold. Glowing runes pulse "
                "across the metal in patterns that hurt to look at.\n\n"
                "A brass plate beside the gates reads:\n"
                "'THESE GATES ANSWER ONLY TO THE LIGHT OF THE SILVER DRAGON. "
                "REKINDLE THE BEACON, AND THE WAY SHALL OPEN.'"
            ),
        )
        self._rooms["castle_gates"].add_item(iron_gates)

        brass_plate = StatefulItem(
            name="brass plate",
            id="gates_plate",
            description="A brass plate mounted beside the castle gates.",
            state="default",
            takeable=False,
            synonyms=["plate", "inscription", "sign"],
        )
        brass_plate.set_room_id("castle_gates")
        brass_plate.add_state_description(
            "default",
            "A brass plate bears an inscription beside the gates.",
        )
        brass_plate.add_interaction(
            verb="read",
            message=(
                "The plate reads:\n\n"
                "'THESE GATES ANSWER ONLY TO THE LIGHT OF THE SILVER DRAGON.\n"
                "REKINDLE THE BEACON IN THE MANOR OF ARGYNVOSTHOLT,\n"
                "AND THE WAY TO RAVENLOFT SHALL OPEN.\n\n"
                "- Lord Argynvost, Commander of the Silver Order'"
            ),
        )
        brass_plate.add_interaction(
            verb="examine",
            message="The brass plate is old but well-preserved. Its inscription is clear.",
        )
        self._rooms["castle_gates"].add_item(brass_plate)

        # =====================================================================
        # TSER POOL AREA - Vistani items
        # =====================================================================

        # Fortune teller's wagon
        crystal_ball = StatefulItem(
            name="crystal ball",
            id="crystal_ball",
            description="A large crystal ball sits on velvet cloth, swirling with mist.",
            state="clouded",
            takeable=False,
            synonyms=["ball", "orb", "scrying orb"],
        )
        crystal_ball.set_room_id("wagon")
        crystal_ball.add_state_description(
            "clouded",
            "A crystal ball swirls with inner mist, waiting to reveal secrets.",
        )
        crystal_ball.add_interaction(
            verb="examine",
            message=(
                "The crystal ball is perfectly smooth, about the size of a man's "
                "head. Mist swirls within its depths, occasionally forming shapes - "
                "a castle, a wolf, a woman's face. The seer watches you watch it."
            ),
        )
        crystal_ball.add_interaction(
            verb="touch",
            message=(
                "The moment your fingers touch the crystal, the mist parts. You "
                "see yourself standing before massive gates, light blazing behind "
                "you. Then darkness, and a pale face with crimson eyes.\n\n"
                "The seer chuckles. 'You'll need the beacon before those gates "
                "open. And before the beacon... the ghost must rest.'"
            ),
        )
        crystal_ball.add_interaction(
            verb="take",
            message="The seer's milky eyes fix on you. 'That is not for taking, traveler.'",
        )
        self._rooms["wagon"].add_item(crystal_ball)

        tarot_deck = Item(
            name="tarot",
            id="tarot_deck",
            description=(
                "A worn deck of tarot cards. The images are strange - familiar "
                "archetypes twisted into Barovian forms. The Tower shows Castle "
                "Ravenloft burning. The Lovers depicts a man and woman separated "
                "by mist. Death rides a pale horse through eternal twilight."
            ),
            weight=0,
            value=15,
            takeable=True,
            synonyms=["tarot deck", "cards", "deck", "fortune cards"],
        )
        self._rooms["wagon"].add_item(tarot_deck)

        silver_bell = Item(
            name="bell",
            id="wagon_bell",
            description=(
                "A small silver bell with a clear, pure tone. The seer says it "
                "wards off evil spirits. Whether that's true remains to be seen."
            ),
            weight=0,
            value=10,
            takeable=True,
            synonyms=["silver bell", "small bell"],
        )
        self._rooms["wagon"].add_item(silver_bell)

        # Merchant stall
        weapon_rack = StatefulItem(
            name="weapon rack",
            id="merchant_rack",
            description="A wooden rack displaying several weapons for sale.",
            state="default",
            takeable=False,
            synonyms=["rack", "weapons", "display"],
        )
        weapon_rack.set_room_id("merchant_stall")
        weapon_rack.add_state_description(
            "default",
            "A wooden rack displays weapons - a short sword and crossbow are notable.",
        )
        weapon_rack.add_interaction(
            verb="examine",
            message=(
                "The rack holds:\n"
                "  - A short sword (20 gold) - well-balanced, good steel\n"
                "  - A crossbow (35 gold) - Vistani make, reliable\n"
                "  - Several daggers (5 gold each)\n\n"
                "The Vistani trader watches you appraisingly."
            ),
        )
        self._rooms["merchant_stall"].add_item(weapon_rack)

        strongbox = StatefulItem(
            name="strongbox",
            id="merchant_strongbox",
            description="A locked iron strongbox under the merchant's table.",
            state="locked",
            takeable=False,
            synonyms=["box", "locked box", "iron box"],
        )
        strongbox.set_room_id("merchant_stall")
        strongbox.add_state_description(
            "locked",
            "A locked strongbox sits beneath the table.",
        )
        strongbox.add_interaction(
            verb="open",
            from_state="locked",
            message="The strongbox is securely locked. The merchant's eyes narrow at your attempt.",
        )
        strongbox.add_interaction(
            verb="examine",
            message=(
                "A heavy iron strongbox with a formidable lock. The merchant's "
                "most valuable goods are surely kept inside. Attempting to steal "
                "from the Vistani would be... unwise."
            ),
        )
        self._rooms["merchant_stall"].add_item(strongbox)

        # Old dock
        dock_post = StatefulItem(
            name="dock post",
            id="dock_post",
            description="A weathered post at the end of the dock.",
            state="default",
            takeable=False,
            synonyms=["post", "wooden post"],
        )
        dock_post.set_room_id("old_dock")
        dock_post.add_state_description(
            "default",
            "A weathered post with rope coiled around it, securing a rowboat.",
        )
        dock_post.add_interaction(
            verb="examine",
            message=(
                "The post is carved with Vistani symbols - protection against "
                "water spirits, you think. An inscription is carved below:\n\n"
                "'The lake holds secrets. Ask the seer about the ghost ship.'"
            ),
        )
        dock_post.add_interaction(
            verb="read",
            message="The inscription reads: 'The lake holds secrets. Ask the seer about the ghost ship.'",
        )
        self._rooms["old_dock"].add_item(dock_post)

        rowboat = StatefulItem(
            name="rowboat",
            id="dock_rowboat",
            description="A small rowboat tied to the dock, half full of rainwater.",
            state="tied",
            takeable=False,
            synonyms=["boat", "small boat"],
        )
        rowboat.set_room_id("old_dock")
        rowboat.add_state_description(
            "tied",
            "A waterlogged rowboat is tied to the dock post.",
        )
        rowboat.add_interaction(
            verb="examine",
            message=(
                "The rowboat has seen better days but looks seaworthy. A pair of "
                "oars lies inside, and something glints beneath the rainwater - "
                "a copper coin, perhaps."
            ),
        )
        rowboat.add_interaction(
            verb="enter",
            message=(
                "You step into the rowboat. It rocks alarmingly but holds. The "
                "water of Tser Pool is dark and still. Where would you go? The "
                "Vistani say the pool has no far shore..."
            ),
        )
        rowboat.add_interaction(
            verb="bail",
            message="You scoop water out of the rowboat. A copper coin gleams at the bottom.",
        )
        self._rooms["old_dock"].add_item(rowboat)

        # Hidden coin in rowboat
        copper_coin = Item(
            name="coin",
            id="dock_coin",
            description="An ancient copper coin with strange markings - not Barovian.",
            weight=0,
            value=5,
            takeable=True,
            synonyms=["copper coin", "old coin"],
        )
        self._rooms["old_dock"].add_item(copper_coin)

        # =====================================================================
        # BARROW - Ancient treasures
        # =====================================================================

        sarcophagus = StatefulItem(
            name="sarcophagus",
            id="barrow_sarcophagus",
            description="A stone sarcophagus carved with the image of a sleeping warrior.",
            state="closed",
            takeable=False,
            synonyms=["tomb", "coffin", "stone coffin"],
        )
        sarcophagus.set_room_id("barrow")
        sarcophagus.add_state_description(
            "closed",
            "A stone sarcophagus dominates the chamber, its lid firmly in place.",
        )
        sarcophagus.add_state_description(
            "open",
            "The sarcophagus stands open, revealing ancient remains.",
        )
        sarcophagus.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message=(
                "With great effort, you slide the heavy stone lid aside. Inside "
                "lies the skeletal remains of an ancient warrior, still clad in "
                "rusted chainmail. A silver amulet rests on the ribcage, and a "
                "fine longsword lies at the warrior's side."
            ),
        )
        sarcophagus.add_interaction(
            verb="examine",
            from_state="closed",
            message=(
                "The sarcophagus is carved from a single block of granite. The "
                "warrior on its surface wears archaic armor and clutches a sword. "
                "An inscription in old Common reads: 'HERE LIES VALDRIS, WHO "
                "STOOD AGAINST THE DARKNESS.'"
            ),
        )
        sarcophagus.add_interaction(
            verb="push",
            from_state="closed",
            target_state="open",
            message="You push the heavy lid. It grinds aside, revealing the warrior's remains.",
        )
        self._rooms["barrow"].add_item(sarcophagus)

        # Hidden items in sarcophagus
        silver_amulet = Item(
            name="amulet",
            id="barrow_amulet",
            description=(
                "A silver amulet on a tarnished chain. The symbol is a sun "
                "rising over mountains - the same as the eastern standing stone. "
                "It radiates faint warmth."
            ),
            weight=0,
            value=40,
            takeable=True,
            synonyms=["silver amulet", "necklace", "pendant"],
        )

        fine_sword = Weapon(
            name="longsword",
            id="barrow_sword",
            description=(
                "An ancient but well-preserved longsword. The blade bears faint "
                "runic inscriptions that seem to glow in darkness. This weapon "
                "was made to fight evil."
            ),
            weight=3,
            value=100,
            takeable=True,
            damage=10,
            min_level="Apprentice",
            min_strength=12,
            min_dexterity=8,
        )
        fine_sword.synonyms = ["fine longsword", "sword", "ancient sword"]

        def sarcophagus_opened(game_state: Any) -> bool:
            room = game_state.get_room("barrow")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "barrow_sarcophagus":
                    return getattr(item, "state", None) == "open"
            return False

        self._rooms["barrow"].add_hidden_item(silver_amulet, sarcophagus_opened)
        self._rooms["barrow"].add_hidden_item(fine_sword, sarcophagus_opened)

        # Scattered coins
        self._rooms["barrow"].add_item(create_coin("barrow_coin1"))
        self._rooms["barrow"].add_item(create_coin("barrow_coin2"))

        # Torch for dark room
        self._rooms["barrow"].add_item(create_torch())

        # =====================================================================
        # DARK GROVE - Hidden cache
        # =====================================================================

        buried_cache = StatefulItem(
            name="glinting metal",
            id="grove_cache",
            description="Something metallic glints among the dead leaves.",
            state="buried",
            takeable=False,
            synonyms=["metal", "glint", "buried metal"],
        )
        buried_cache.set_room_id("dark_grove")
        buried_cache.add_state_description(
            "buried",
            "A glint of metal catches your eye among the dead leaves.",
        )
        buried_cache.add_state_description(
            "uncovered",
            "A small iron lockbox lies where you uncovered it.",
        )
        buried_cache.add_interaction(
            verb="dig",
            from_state="buried",
            target_state="uncovered",
            message=(
                "You brush aside the leaves and dig into the soft earth. Your "
                "fingers find a small iron lockbox, buried here by some previous "
                "traveler. The lock is rusted and weak."
            ),
        )
        buried_cache.add_interaction(
            verb="uncover",
            from_state="buried",
            target_state="uncovered",
            message="You uncover a small iron lockbox beneath the leaves.",
        )
        buried_cache.add_interaction(
            verb="examine",
            from_state="buried",
            message=(
                "Something metallic is half-buried in the leaves near a gnarled "
                "root. It would take only a bit of digging to uncover it."
            ),
        )
        self._rooms["dark_grove"].add_item(buried_cache)

        lockbox = StatefulItem(
            name="iron lockbox",
            id="grove_lockbox",
            description="A small iron lockbox with a rusted lock.",
            state="locked",
            takeable=False,
            synonyms=["lockbox", "box", "chest"],
        )
        lockbox.set_room_id("dark_grove")
        lockbox.add_state_description(
            "locked",
            "A small iron lockbox lies in the earth, its lock rusted.",
        )
        lockbox.add_state_description(
            "open",
            "The lockbox lies open, its contents revealed.",
        )
        lockbox.add_interaction(
            verb="open",
            from_state="locked",
            target_state="open",
            message=(
                "The rusted lock crumbles under pressure. Inside the lockbox you "
                "find a handful of gold coins and a rolled-up piece of parchment - "
                "a map of some kind!"
            ),
        )
        lockbox.add_interaction(
            verb="break",
            from_state="locked",
            target_state="open",
            message="You break the rusted lock. The box contains coins and a map.",
        )
        lockbox.add_interaction(
            verb="examine",
            from_state="locked",
            message="The lockbox's lock is so rusted it might break with enough force.",
        )

        def cache_uncovered(game_state: Any) -> bool:
            room = game_state.get_room("dark_grove")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "grove_cache":
                    return getattr(item, "state", None) == "uncovered"
            return False

        self._rooms["dark_grove"].add_hidden_item(lockbox, cache_uncovered)

        # Map and coins (hidden until lockbox opened)
        treasure_map = Item(
            name="map",
            id="grove_map",
            description=(
                "A faded map showing the Svalich Woods. An X marks a spot south "
                "of the standing stones with the note: 'Cache buried. Mill path "
                "revealed when stones align.' Another X marks the wolf den with: "
                "'Ghost's honor.' Useful information!"
            ),
            weight=0,
            value=5,
            takeable=True,
            synonyms=["faded map", "parchment", "treasure map"],
        )

        gold_coins = Item(
            name="coins",
            id="grove_gold",
            description="A handful of tarnished gold coins - someone's savings.",
            weight=0,
            value=50,
            takeable=True,
            synonyms=["gold coins", "gold", "money"],
        )

        def lockbox_opened(game_state: Any) -> bool:
            room = game_state.get_room("dark_grove")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "grove_lockbox":
                    return getattr(item, "state", None) == "open"
            return False

        self._rooms["dark_grove"].add_hidden_item(treasure_map, lockbox_opened)
        self._rooms["dark_grove"].add_hidden_item(gold_coins, lockbox_opened)

        # =====================================================================
        # HOLLOW - Rope puzzle
        # =====================================================================

        hanging_rope = StatefulItem(
            name="old rope",
            id="hollow_rope",
            description="An old rope hangs from a tree branch over the misty hollow.",
            state="hanging",
            takeable=False,
            synonyms=["rope", "hanging rope"],
        )
        hanging_rope.set_room_id("hollow")
        hanging_rope.add_state_description(
            "hanging",
            "An old rope dangles from a branch overhead, swaying despite no wind.",
        )
        hanging_rope.add_interaction(
            verb="pull",
            message=(
                "You pull the rope. It holds firm but nothing seems to happen. "
                "The mist in the hollow seems to swirl more intensely for a moment."
            ),
        )
        hanging_rope.add_interaction(
            verb="climb",
            message=(
                "You climb the rope. It leads up to a branch overlooking the "
                "hollow. From here you can see that the mist forms patterns - "
                "almost like words. They seem to say... 'SUNRISE NOON SUNSET.'"
            ),
        )
        hanging_rope.add_interaction(
            verb="examine",
            message=(
                "The rope is old but sturdy. It's tied around a thick branch "
                "overhead. Someone clearly used this regularly - the rope shows "
                "wear in a pattern suggesting climbing."
            ),
        )
        self._rooms["hollow"].add_item(hanging_rope)

        stone_marker = StatefulItem(
            name="stone marker",
            id="hollow_marker",
            description="A crude stone marker stands at the edge of the hollow.",
            state="default",
            takeable=False,
            synonyms=["marker", "stone", "crude stone"],
        )
        stone_marker.set_room_id("hollow")
        stone_marker.add_state_description(
            "default",
            "A crude stone marker stands at the hollow's edge, carved with symbols.",
        )
        stone_marker.add_interaction(
            verb="read",
            message=(
                "The marker bears crude carvings:\n"
                "  A circle (the sun?)\n"
                "  Three arrows pointing east, north, west\n"
                "  The words: 'DAWN - ZENITH - DUSK'\n\n"
                "Below, someone has scratched: 'Touch the heart when they align.'"
            ),
        )
        stone_marker.add_interaction(
            verb="examine",
            message=(
                "The stone marker is old, possibly older than the village itself. "
                "Its carvings depict the sun's path across the sky. The inscription "
                "seems to be a clue about the standing stones."
            ),
        )
        self._rooms["hollow"].add_item(stone_marker)

        # =====================================================================
        # MUSHROOM GLADE - Fairy ring
        # =====================================================================

        fairy_ring = StatefulItem(
            name="mushroom ring",
            id="fairy_ring",
            description="A perfect circle of pale mushrooms in the glade.",
            state="intact",
            takeable=False,
            synonyms=["ring", "mushrooms", "fairy ring", "mushroom circle"],
        )
        fairy_ring.set_room_id("mushroom_glade")
        fairy_ring.add_state_description(
            "intact",
            "A perfect ring of pale mushrooms encircles the glade.",
        )
        fairy_ring.add_interaction(
            verb="enter",
            message=(
                "You step into the ring of mushrooms. The air grows thick, the "
                "world seems to spin, and for a moment you see... another place. "
                "Green fields, sunlight, laughter. Then it fades, and you stand "
                "in the grey Barovian forest once more. A tear runs down your cheek."
            ),
        )
        fairy_ring.add_interaction(
            verb="examine",
            message=(
                "The mushrooms are unnaturally perfect - each one identical, "
                "arranged with mathematical precision. Local legend warns against "
                "entering such rings. They say you might not return."
            ),
        )
        fairy_ring.add_interaction(
            verb="pick",
            message=(
                "As your fingers near a mushroom, a jolt of energy throws you "
                "back. The fair folk don't take kindly to thieves, it seems."
            ),
        )
        self._rooms["mushroom_glade"].add_item(fairy_ring)

        wooden_box = StatefulItem(
            name="wooden box",
            id="glade_box",
            description="A weathered wooden box sits at the center of the fairy ring.",
            state="closed",
            takeable=False,
            synonyms=["box", "small box"],
        )
        wooden_box.set_room_id("mushroom_glade")
        wooden_box.add_state_description(
            "closed",
            "A weathered wooden box sits at the ring's center.",
        )
        wooden_box.add_state_description(
            "open",
            "The wooden box lies open, its contents taken.",
        )
        wooden_box.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message=(
                "You carefully reach into the ring and open the box. Inside lies "
                "a single perfect acorn, warm to the touch despite the cold air. "
                "A fairy gift? Or a fairy trap?"
            ),
        )
        wooden_box.add_interaction(
            verb="examine",
            from_state="closed",
            message=(
                "The box is small, made of pale wood, and completely unadorned. "
                "It sits exactly at the center of the fairy ring, as if placed "
                "there deliberately. Opening it might be risky..."
            ),
        )
        self._rooms["mushroom_glade"].add_item(wooden_box)

        # Hidden acorn
        magic_acorn = Item(
            name="acorn",
            id="glade_acorn",
            description=(
                "A perfect acorn that gleams like gold. It's warm to the touch "
                "and hums faintly. The Vistani might know what it's for."
            ),
            weight=0,
            value=25,
            takeable=True,
            synonyms=["golden acorn", "magic acorn"],
        )

        def box_opened(game_state: Any) -> bool:
            room = game_state.get_room("mushroom_glade")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "glade_box":
                    return getattr(item, "state", None) == "open"
            return False

        self._rooms["mushroom_glade"].add_hidden_item(magic_acorn, box_opened)

        # =====================================================================
        # FLAVOR ROOMS - Additional items
        # =====================================================================

        # Fallen tree - old pack
        old_pack = StatefulItem(
            name="old pack",
            id="fallen_pack",
            description="An old traveler's pack lies in the shelter beneath the roots.",
            state="closed",
            takeable=False,
            synonyms=["pack", "backpack", "bag"],
        )
        old_pack.set_room_id("fallen_tree")
        old_pack.add_state_description(
            "closed",
            "An old pack lies in the root shelter, its contents unknown.",
        )
        old_pack.add_state_description(
            "open",
            "The old pack has been searched.",
        )
        old_pack.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message=(
                "You open the rotting pack. Inside you find dried rations (spoiled), "
                "a tinderbox (working!), and a crumpled note:\n\n"
                "'If you find this, know that I made it as far as the standing "
                "stones. The answer is in the sun - dawn east, noon north, dusk west. "
                "Touch the altar when aligned. The barrow holds treasure.'"
            ),
        )
        old_pack.add_interaction(
            verb="search",
            from_state="closed",
            target_state="open",
            message="You search the pack. A tinderbox and an informative note!",
        )
        self._rooms["fallen_tree"].add_item(old_pack)

        # Tinderbox hidden item
        tinderbox = Item(
            name="tinderbox",
            id="fallen_tinderbox",
            description="A brass tinderbox with flint and steel inside. Still functional.",
            weight=0,
            value=8,
            takeable=True,
            synonyms=["flint", "striker"],
        )

        def pack_opened(game_state: Any) -> bool:
            room = game_state.get_room("fallen_tree")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "fallen_pack":
                    return getattr(item, "state", None) == "open"
            return False

        self._rooms["fallen_tree"].add_hidden_item(tinderbox, pack_opened)

        # Raven roost
        banded_raven = StatefulItem(
            name="banded raven",
            id="banded_raven",
            description="A large raven wearing a silver band on its leg.",
            state="watching",
            takeable=False,
            synonyms=["raven", "large raven", "bird"],
        )
        banded_raven.set_room_id("raven_roost")
        banded_raven.add_state_description(
            "watching",
            "A large raven with a silver leg band watches you with unusual intelligence.",
        )
        banded_raven.add_interaction(
            verb="examine",
            message=(
                "This raven is larger than the others, and clearly their leader. "
                "It wears a silver band inscribed with tiny symbols. Its eyes "
                "gleam with intelligence far beyond a normal bird's."
            ),
        )
        banded_raven.add_interaction(
            verb="talk",
            message=(
                "You speak to the raven. It cocks its head, listening intently. "
                "Then, impossibly, it speaks:\n\n"
                "'The stones remember. The ghost waits. The gates fear the light. "
                "Bring wine to the seer for more.'\n\n"
                "The other ravens caw in what might be laughter."
            ),
        )
        self._rooms["raven_roost"].add_item(banded_raven)

        # Glittering droppings (coins hidden in guano)
        raven_droppings = StatefulItem(
            name="glittering droppings",
            id="raven_droppings",
            description="The droppings beneath the tree glitter with something metallic.",
            state="unsearched",
            takeable=False,
            synonyms=["droppings", "guano", "mess"],
        )
        raven_droppings.set_room_id("raven_roost")
        raven_droppings.add_state_description(
            "unsearched",
            "Droppings cover the ground beneath the tree. Something glitters within.",
        )
        raven_droppings.add_state_description(
            "searched",
            "The droppings have been searched. The ravens look amused.",
        )
        raven_droppings.add_interaction(
            verb="search",
            from_state="unsearched",
            target_state="searched",
            message=(
                "You reluctantly dig through the mess. The ravens watch, clearly "
                "entertained. Your persistence is rewarded - several coins and "
                "a small silver ring emerge from the filth!"
            ),
        )
        raven_droppings.add_interaction(
            verb="examine",
            message=(
                "Glittering objects are visible in the droppings - the ravens "
                "have collected shiny things and... well, done their business "
                "over them. Searching would be unpleasant but potentially rewarding."
            ),
        )
        self._rooms["raven_roost"].add_item(raven_droppings)

        # Hidden treasures in droppings
        silver_ring = Item(
            name="ring",
            id="raven_ring",
            description="A small silver ring, cleaned of its recent surroundings.",
            weight=0,
            value=15,
            takeable=True,
            synonyms=["silver ring", "small ring"],
        )

        def droppings_searched(game_state: Any) -> bool:
            room = game_state.get_room("raven_roost")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "raven_droppings":
                    return getattr(item, "state", None) == "searched"
            return False

        self._rooms["raven_roost"].add_hidden_item(silver_ring, droppings_searched)
        self._rooms["raven_roost"].add_hidden_item(
            create_coin("raven_coin"), droppings_searched
        )

        # Old shrine
        silver_bowl = StatefulItem(
            name="silver bowl",
            id="shrine_bowl",
            description="A tarnished silver bowl sits in the statue's cupped hands.",
            state="empty",
            takeable=False,
            synonyms=["bowl", "offering bowl"],
        )
        silver_bowl.set_room_id("old_shrine")
        silver_bowl.add_state_description(
            "empty",
            "An empty silver bowl rests in the statue's hands, waiting for offerings.",
        )
        silver_bowl.add_state_description(
            "filled",
            "The silver bowl holds your offering.",
        )
        silver_bowl.add_interaction(
            verb="examine",
            message=(
                "The bowl is tarnished but valuable. An inscription around the "
                "rim reads: 'GIVE AND YE SHALL RECEIVE.' Placing an offering "
                "might bring luck - or the gods' attention."
            ),
        )
        silver_bowl.add_interaction(
            verb="take",
            message=(
                "As your hand nears the bowl, you feel a chill of warning. "
                "Perhaps stealing from a shrine would bring bad luck..."
            ),
        )
        self._rooms["old_shrine"].add_item(silver_bowl)

        # Hunter's cache
        locked_chest = StatefulItem(
            name="locked chest",
            id="hunter_chest",
            description="A locked wooden chest sits in the corner of the hunter's blind.",
            state="locked",
            takeable=False,
            synonyms=["chest", "wooden chest"],
        )
        locked_chest.set_room_id("hunters_cache")
        locked_chest.add_state_description(
            "locked",
            "A locked chest sits in the corner, its iron bands rusted.",
        )
        locked_chest.add_state_description(
            "open",
            "The chest lies open, its hunter's supplies revealed.",
        )
        locked_chest.add_interaction(
            verb="open",
            from_state="locked",
            target_state="open",
            message=(
                "The rusted lock gives way with effort. Inside you find a hunter's "
                "supplies: a good crossbow, some bolts, dried meat, and a leather "
                "journal detailing wolf movements through these woods."
            ),
        )
        locked_chest.add_interaction(
            verb="break",
            from_state="locked",
            target_state="open",
            message="You break the rusted lock open. Hunter's supplies inside!",
        )
        locked_chest.add_interaction(
            verb="examine",
            from_state="locked",
            message="The chest's lock is heavily rusted. It might break with force.",
        )
        self._rooms["hunters_cache"].add_item(locked_chest)

        # Crossbow (hidden until chest opened)
        hunters_crossbow = Weapon(
            name="crossbow",
            id="hunter_crossbow",
            description=(
                "A well-maintained crossbow left by a long-gone hunter. It's "
                "already loaded and ready to fire."
            ),
            weight=4,
            value=35,
            takeable=True,
            damage=8,
            min_level="Apprentice",
            min_strength=8,
            min_dexterity=10,
        )
        hunters_crossbow.synonyms = ["hunters crossbow", "bow"]

        def chest_opened(game_state: Any) -> bool:
            room = game_state.get_room("hunters_cache")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "hunter_chest":
                    return getattr(item, "state", None) == "open"
            return False

        self._rooms["hunters_cache"].add_hidden_item(hunters_crossbow, chest_opened)

        # Stream crossing - wooden sign
        wooden_sign = StatefulItem(
            name="wooden sign",
            id="stream_sign",
            description="A weathered wooden sign is nailed to a tree by the stream.",
            state="default",
            takeable=False,
            synonyms=["sign", "old sign"],
        )
        wooden_sign.set_room_id("stream_crossing")
        wooden_sign.add_state_description(
            "default",
            "A faded wooden sign is nailed to a tree near the stream.",
        )
        wooden_sign.add_interaction(
            verb="read",
            message=(
                "The faded text reads:\n\n"
                "'DANGER - WOLVES TO THE NORTH\n"
                " FAIRY RING TO THE EAST - DO NOT ENTER\n"
                " HOLLOW TO THE WEST - BEWARE THE MISTS'"
            ),
        )
        wooden_sign.add_interaction(
            verb="examine",
            message="The sign is old and weathered but still readable.",
        )
        self._rooms["stream_crossing"].add_item(wooden_sign)

    def spawn_mobs(self, mob_manager: Any) -> None:
        """Spawn mobs for Level 2."""

        # Wolves - aggressive patrols
        self.spawn_mob_in_room(mob_manager, "wolf", "wolf_territory")
        self.spawn_mob_in_room(mob_manager, "wolf", "woods_path")

        # Bats in the hollow
        self.spawn_mob_in_room(mob_manager, "bats", "hollow")

        # Specter guarding the barrow
        self.spawn_mob_in_room(mob_manager, "specter", "barrow")

        # Non-aggressive Vistani
        self.spawn_mob_in_room(mob_manager, "vistani", "tser_pool")
        self.spawn_mob_in_room(mob_manager, "seer", "wagon")
        self.spawn_mob_in_room(mob_manager, "vistani_trader", "merchant_stall")

    def configure_npc_interactions(self, mob_manager: Any) -> None:
        """Configure NPC interactions for Level 2."""

        def find_mob_in_room(name: str, room_id: str) -> Any:
            for mob_id, mob in mob_manager.mobs.items():
                if mob.name.lower() == name.lower() and mob.room_id == room_id:
                    return mob
            return None

        # Seer - give wine for detailed fortune
        seer = find_mob_in_room("seer", "wagon")
        if seer:
            seer.accepts_item = {
                "wine": {
                    "message": (
                        "The seer's milky eyes light up as she takes the wine.\n\n"
                        "'Ah, a gift freely given! The mists part for generosity...'\n\n"
                        "She drinks deeply, then fixes you with an unseeing gaze:\n\n"
                        "'I see your path clearly now:\n\n"
                        "1. THE STONES - In the clearing, three stones hold the sun. "
                        "Turn the east to sunrise, the north to noon, the west to sunset. "
                        "Then touch the altar - ancient wisdom awaits below.\n\n"
                        "2. THE GHOST - A knight guards the western bridge. His medallion "
                        "was stolen by wolves - search their den for bones that gleam. "
                        "Return his honor and he shall let you pass.\n\n"
                        "3. THE GATES - They answer only to the beacon's light. You must "
                        "journey to Argynvostholt and rekindle the dragon fire.\n\n"
                        "'May the Morninglord guide your steps, traveler.'"
                    ),
                    "one_time": True,
                    "triggered": False,
                }
            }

        # Vistani trader - accepts gold for information
        trader = find_mob_in_room("vistani_trader", "merchant_stall")
        if trader:
            trader.accepts_item = {
                "coin": {
                    "message": (
                        "The Vistani trader nods appreciatively.\n\n"
                        "'Information is more valuable than gold in Barovia, friend. "
                        "But gold opens lips...'\n\n"
                        "'The ghost on the bridge was once Sir Godfrey of the Silver "
                        "Dragon order. His medallion - his very honor - was stolen by "
                        "the wolf pack. They lair east of here, along the game trails.\n\n"
                        "'As for the castle gates... see those runes? Dark magic, bound "
                        "to the will of the land's master. Only the light of the dragon "
                        "beacon can break the seal. The beacon is in Argynvostholt, the "
                        "ruined manor beyond the bridge.\n\n"
                        "'The seer knows more, if you bring her wine.'"
                    ),
                    "one_time": True,
                    "triggered": False,
                },
                "gold coins": {
                    "message": (
                        "The trader's eyes widen at the gold.\n\n"
                        "'Generous! Very generous! For this, I share everything:\n\n"
                        "'The standing stones in the clearing hide an ancient barrow. "
                        "Align the suns - dawn in the east, noon in the north, dusk in "
                        "the west - then touch the altar. The way will open.\n\n"
                        "'In the barrow lies treasure and a weapon blessed against evil. "
                        "You'll need such things where you're going.\n\n"
                        "'The ghost knight wants his medallion. The wolf den has it. "
                        "The castle gates need the beacon lit. It's all connected, friend. "
                        "Everything in Barovia is connected.'"
                    ),
                    "one_time": True,
                    "triggered": False,
                },
            }
