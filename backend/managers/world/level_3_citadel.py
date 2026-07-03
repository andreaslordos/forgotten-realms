# backend/managers/world/level_3_citadel.py
"""
Level 3: Bleakspire Citadel

The mist-wreathed fortress of Lord Morvane, the Pale Sovereign, and the
final zone of the Mournvale. Players fight through the citadel to the
throne hall, destroy Morvane, and loot the sovereign's vault.

Rooms: 14 total
Mobs: Gargoyle, wraith, vampire spawn (2), Lord Morvane (boss)
Transitions:
  - From Level 2 (castle_gates): Sir Aldric's Watchfire mark unseals the
    citadel gates, opening the way east to the outer gate.

Design Principles Applied:
  - Room descriptions explicitly name items in the room
  - Items have synonyms for flexible player input
  - Multiple verbs per stateful item (snuff/extinguish, lift/raise/open)
  - Examine interactions provide hints for puzzles
  - Multi-step puzzle chains with clues (candles then prayer, crank then
    winch, Watchfire mark then mirror)
"""

from typing import Any, Dict
from models.Room import Room
from models.Item import Item
from models.StatefulItem import StatefulItem
from models.Weapon import Weapon
from .level_base import LevelGenerator
from .shared_conditions import bears_watchfire_mark


class Level3Citadel(LevelGenerator):
    """Generator for Level 3: Bleakspire Citadel."""

    level_number = 3
    level_name = "Bleakspire Citadel"

    def generate_rooms(self) -> Dict[str, Room]:
        """Generate all rooms for Bleakspire Citadel."""

        # =====================================================================
        # APPROACH - Outer gate and causeway
        # =====================================================================

        outer_gate = Room(
            "outer_gate",
            "Outer Gate of Bleakspire",
            "The great gates of Bleakspire stand unsealed at your back to the "
            "west, their dead runes still weeping frost down the iron. Ahead, "
            "a narrow causeway strides east over a black chasm toward the "
            "citadel proper. A rune-scarred arch looms overhead, and the cold "
            "here has teeth.",
            is_outdoor=True,
        )

        causeway = Room(
            "causeway",
            "The Causeway",
            "A narrow ribbon of stone spans a chasm whose bottom the eye "
            "refuses to find, wind screaming up out of the dark below. A "
            "gargoyle perches on the parapet midway across, still in the way "
            "that stone should be - and is not. The outer gate lies west and "
            "the citadel bailey waits to the east.",
            is_outdoor=True,
        )

        # =====================================================================
        # LOWER CITADEL - Bailey and its wings
        # =====================================================================

        bailey = Room(
            "bailey",
            "Citadel Bailey",
            "Dead grass and older bones carpet this courtyard beneath walls "
            "that lean inward like conspirators. Kennels crouch against the "
            "north wall, the doors of the great hall gape to the east, and a "
            "lightless chapel broods to the south. Behind you, to the west, "
            "the causeway is the only way out.",
            is_outdoor=True,
        )

        kennels = Room(
            "kennels",
            "The Kennels",
            "Iron cages line the walls, each holding the dried husk of a "
            "hound that starved at its post. An iron crank lies among the "
            "dead hound cages, dropped and forgotten by whoever last worked "
            "the citadel's machines. The bailey lies south.",
        )

        chapel_dark = Room(
            "chapel_dark",
            "Defiled Chapel",
            "Whatever grace this chapel held was strangled long ago. A "
            "defiled altar crouches beneath a shattered rose window, ringed "
            "by black candles whose flames burn cold and cast no light. "
            "Scratches in the flagstones behind the altar suggest the floor "
            "itself once moved. The bailey lies north.",
        )

        # =====================================================================
        # CRYPTS - Beneath the chapel (revealed by the altar prayer)
        # =====================================================================

        crypt_stair = Room(
            "crypt_stair",
            "Crypt Stair",
            "A cramped stair corkscrews down through sweating stone, each "
            "step worn hollow by centuries of vanished processions. The "
            "chapel lies back up the steps, and a low corridor runs north "
            "into the undercrypt. The dark down here is total, and it "
            "listens.",
            is_dark=True,
        )

        undercrypt = Room(
            "undercrypt",
            "Undercrypt of the Gray Watch",
            "Stone tombs stand rank on rank in the blackness, each carved "
            "with the burning-tower crest of the Gray Watch. Upon the "
            "centermost bier lies the order's burial regalia, folded with a "
            "reverence the citadel above has long forgotten. Something cold "
            "and hateful drifts between the tombs. The stair lies south.",
            is_dark=True,
        )

        # =====================================================================
        # KEEP - Great hall, solar and the throne stair
        # =====================================================================

        great_hall = Room(
            "great_hall",
            "Great Hall",
            "Long tables lie overturned beneath torn banners, the wreck of a "
            "feast no one survived. Every hearth is cold, and the silence "
            "has the quality of held breath. The bailey lies west, a private "
            "solar opens to the north, and the throne stair waits beyond the "
            "east archway.",
        )

        solar = Room(
            "solar",
            "The Solar",
            "This was Morvane's records room: shelves of ledgers, a "
            "copyist's desk, and dust thick enough to bury sound. A leather "
            "journal lies open on the desk, and an iron winch is bolted to "
            "the wall, its chain vanishing into a channel cut through the "
            "stone. The great hall lies south.",
        )

        throne_stair = Room(
            "throne_stair",
            "Throne Stair",
            "A broad stair of black marble climbs toward the throne hall "
            "above, but a lowered iron portcullis seals it off at the first "
            "landing. The teeth of the grate are sunk deep into sockets in "
            "the stone, and its lifting chain rattles away westward through "
            "a channel in the wall. The great hall lies west.",
        )

        # =====================================================================
        # UPPER CITADEL - Throne hall and the sovereign's chambers
        # =====================================================================

        throne_hall = Room(
            "throne_hall",
            "Throne Hall of the Pale Sovereign",
            "The throne hall crowns the citadel in cold splendor, all pale "
            "marble and windows of grey glass. A basalt throne stands upon "
            "the dais, and the air around it aches like a wound that never "
            "closed. An archway opens north into the sovereign's sanctum, a "
            "colonnade leads south onto a high balcony, and the portcullis "
            "stair falls away below.",
        )

        sanctum = Room(
            "sanctum",
            "The Sanctum",
            "Morvane's private sanctum smells of candle smoke and centuries. "
            "A standing mirror in a frame of black silver dominates the east "
            "wall, reflecting the room a half-heartbeat out of step, and a "
            "grimoire rests on a reading stand beside it. The throne hall "
            "lies south.",
        )

        balcony = Room(
            "balcony",
            "High Balcony",
            "The balcony juts from the citadel's crown into a freezing wind, "
            "and the whole of the Mournvale unrolls below: the huddled "
            "village, the black woods, the thread of the river and its "
            "bridge, all of it stitched shut beneath the mist. A gem of "
            "polished jet lies forgotten on the parapet. The throne hall "
            "lies back to the north.",
            is_outdoor=True,
        )

        vault = Room(
            "vault",
            "The Sovereign's Vault",
            "No window has ever let light into this chamber, and the dark "
            "has grown fat on what it guards. The crown of the Pale "
            "Sovereign, a silver scepter, and a casket of gems crowd a stone "
            "shelf, while the Dawnblade burns with pale silver fire upon an "
            "iron rack - the one thing in Bleakspire that dares to shine. "
            "The mirror-door stands west, back to the sanctum.",
            is_dark=True,
        )

        # =====================================================================
        # Store all rooms
        # =====================================================================

        self._rooms = {
            # Approach
            "outer_gate": outer_gate,
            "causeway": causeway,
            # Lower citadel
            "bailey": bailey,
            "kennels": kennels,
            "chapel_dark": chapel_dark,
            # Crypts
            "crypt_stair": crypt_stair,
            "undercrypt": undercrypt,
            # Keep
            "great_hall": great_hall,
            "solar": solar,
            "throne_stair": throne_stair,
            # Upper citadel
            "throne_hall": throne_hall,
            "sanctum": sanctum,
            "balcony": balcony,
            "vault": vault,
        }

        return self._rooms

    def connect_internal_exits(self) -> None:
        """Connect exits between rooms within the citadel."""

        # =====================================================================
        # APPROACH CONNECTIONS
        # =====================================================================

        self._rooms["outer_gate"].exits = {
            # Back to Level 2. The reverse exit (castle_gates east) is added
            # by the Watchfire gates puzzle in level_2_woods - do NOT add it.
            "west": "castle_gates",
            "east": "causeway",
        }

        self._rooms["causeway"].exits = {
            "west": "outer_gate",
            "east": "bailey",
        }

        # =====================================================================
        # LOWER CITADEL CONNECTIONS
        # =====================================================================

        self._rooms["bailey"].exits = {
            "west": "causeway",
            "north": "kennels",
            "east": "great_hall",
            "south": "chapel_dark",
        }

        self._rooms["kennels"].exits = {
            "south": "bailey",
        }

        self._rooms["chapel_dark"].exits = {
            "north": "bailey",
            # "down": "crypt_stair" - hidden, revealed by the altar prayer
        }

        # =====================================================================
        # CRYPT CONNECTIONS
        # =====================================================================

        self._rooms["crypt_stair"].exits = {
            "up": "chapel_dark",
            "north": "undercrypt",
        }

        self._rooms["undercrypt"].exits = {
            "south": "crypt_stair",
        }

        # =====================================================================
        # KEEP CONNECTIONS
        # =====================================================================

        self._rooms["great_hall"].exits = {
            "west": "bailey",
            "north": "solar",
            "east": "throne_stair",
        }

        self._rooms["solar"].exits = {
            "south": "great_hall",
        }

        self._rooms["throne_stair"].exits = {
            "west": "great_hall",
            # "up": "throne_hall" - blocked by portcullis, raised by the
            # winch in the solar
        }

        # =====================================================================
        # UPPER CITADEL CONNECTIONS
        # =====================================================================

        self._rooms["throne_hall"].exits = {
            "down": "throne_stair",
            "north": "sanctum",
            "south": "balcony",
        }

        self._rooms["sanctum"].exits = {
            "south": "throne_hall",
            # "east": "vault" - hidden behind the standing mirror
        }

        self._rooms["balcony"].exits = {
            "north": "throne_hall",
        }

        self._rooms["vault"].exits = {
            "west": "sanctum",
        }

    def add_items(self) -> None:
        """Add items to rooms in the citadel."""

        # =====================================================================
        # OUTER GATE - Rune-scarred arch (flavor)
        # =====================================================================

        gate_arch = StatefulItem(
            name="arch",
            id="gate_arch",
            description="A rune-scarred arch looms over the unsealed gateway.",
            state="default",
            takeable=False,
            synonyms=["rune-scarred arch", "archway", "runes", "keystone"],
        )
        gate_arch.set_room_id("outer_gate")
        gate_arch.add_state_description(
            "default",
            "A rune-scarred arch looms overhead, its sealing runes burnt out.",
        )
        gate_arch.add_interaction(
            verb="examine",
            message=(
                "The arch is scarred where the sealing runes burned "
                "themselves out against the Watchfire. Above the keystone is "
                "carved a burning tower - the crest of the Gray Watch - "
                "defaced by claw marks that failed to erase it. Whoever "
                "built these gates feared what you carry in your palm."
            ),
        )
        self._rooms["outer_gate"].add_item(gate_arch)

        # =====================================================================
        # CAUSEWAY - The chasm (flavor)
        # =====================================================================

        chasm = StatefulItem(
            name="chasm",
            id="causeway_chasm",
            description="A black chasm yawns beneath the narrow causeway.",
            state="default",
            takeable=False,
            synonyms=["drop", "abyss", "gorge", "parapet"],
        )
        chasm.set_room_id("causeway")
        chasm.add_state_description(
            "default",
            "The chasm gapes on either side of the causeway, breathing cold.",
        )
        chasm.add_interaction(
            verb="examine",
            message=(
                "You lean out and look down. The mist below is not still - "
                "it turns slowly, like something rolling over in its sleep. "
                "The causeway's parapet is scored with claw marks the size "
                "of your hand, and they are not old."
            ),
        )
        self._rooms["causeway"].add_item(chasm)

        # =====================================================================
        # KENNELS - Dead hound cages and the iron crank
        # =====================================================================

        hound_cages = StatefulItem(
            name="cages",
            id="hound_cages",
            description="Rows of iron cages hold the citadel's dead hounds.",
            state="default",
            takeable=False,
            synonyms=["cage", "kennel cages", "hounds", "hound", "bars"],
        )
        hound_cages.set_room_id("kennels")
        hound_cages.add_state_description(
            "default",
            "Iron cages line the walls, their occupants long dead at their posts.",
        )
        hound_cages.add_interaction(
            verb="examine",
            message=(
                "The hounds died at their posts, muzzles pressed against the "
                "bars, still facing the door they were set to watch. Wedged "
                "between two cages, where it was dropped, lies an iron crank "
                "- its square shaft made for the socket of some heavy "
                "mechanism."
            ),
        )
        self._rooms["kennels"].add_item(hound_cages)

        iron_crank = Item(
            name="crank",
            id="iron_crank",
            description=(
                "An iron crank lies here, its square shaft sized for the "
                "socket of some heavy mechanism."
            ),
            weight=2,
            value=0,
            takeable=True,
            synonyms=["iron crank", "handle"],
        )
        self._rooms["kennels"].add_item(iron_crank)

        # =====================================================================
        # DEFILED CHAPEL - Puzzle 1: snuff the candles, then pray
        # =====================================================================

        black_candles = StatefulItem(
            name="candles",
            id="black_candles",
            description="Black candles ring the altar, burning with cold flames.",
            state="lit",
            takeable=False,
            synonyms=["black candles", "candle", "black candle", "flames"],
        )
        black_candles.set_room_id("chapel_dark")
        black_candles.add_state_description(
            "lit",
            "Black candles ring the altar, their cold flames casting no light.",
        )
        black_candles.add_state_description(
            "snuffed",
            "The black candles stand dead, their wicks smoking faintly.",
        )
        black_candles.add_interaction(
            verb="snuff",
            from_state="lit",
            target_state="snuffed",
            message=(
                "You pinch out the black candles one by one. Each flame dies "
                "with a sound like a small indrawn breath, and the darkness "
                "around the altar recoils, thinning like smoke in a draft. "
                "For the first time in centuries, the chapel is merely dark."
            ),
        )
        black_candles.add_interaction(
            verb="extinguish",
            from_state="lit",
            target_state="snuffed",
            message=(
                "You smother the cold flames one by one. The darkness around "
                "the altar recoils as each one dies, and something old in "
                "the chapel seems to exhale. The candles stand dead."
            ),
        )
        black_candles.add_interaction(
            verb="snuff",
            from_state="snuffed",
            message="The black candles are already out, their wicks still smoking.",
        )
        black_candles.add_interaction(
            verb="extinguish",
            from_state="snuffed",
            message="The black candles are already dead. Nothing here still burns.",
        )
        black_candles.add_interaction(
            verb="light",
            from_state="snuffed",
            message=(
                "The wicks refuse every flame you offer them. Whatever "
                "burned there was not fire, and it is not coming back."
            ),
        )
        black_candles.add_interaction(
            verb="examine",
            from_state="lit",
            message=(
                "Nine candles of black tallow ring the altar, burning with "
                "flames that shed cold instead of light. The wax never "
                "drips. Scratched into the altar step beneath them is a "
                "single line: 'PUT OUT THE BLACK FLAME, THEN KNEEL AND PRAY.'"
            ),
        )
        black_candles.add_interaction(
            verb="examine",
            from_state="snuffed",
            message=(
                "The black candles stand dead, wicks smoking faintly. The "
                "chapel feels larger without their cold, as if something "
                "that was leaning over you has straightened up."
            ),
        )
        self._rooms["chapel_dark"].add_item(black_candles)

        def candles_snuffed(player: Any, game_state: Any) -> bool:
            """Check if the black candles in the chapel have been snuffed."""
            room = game_state.get_room("chapel_dark")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "black_candles":
                    return bool(getattr(item, "state", None) == "snuffed")
            return False

        defiled_altar = StatefulItem(
            name="altar",
            id="defiled_altar",
            description="A defiled altar crouches beneath the shattered window.",
            state="defiled",
            takeable=False,
            synonyms=["defiled altar", "stone altar", "altar stone"],
        )
        defiled_altar.set_room_id("chapel_dark")
        defiled_altar.add_state_description(
            "defiled",
            "The defiled altar squats beneath the window, caked in dark residue.",
        )
        defiled_altar.add_state_description(
            "restored",
            "The restored altar stands clean, and steps descend behind it.",
        )
        defiled_altar.add_interaction(
            verb="pray",
            from_state="defiled",
            target_state="restored",
            message=(
                "You kneel at the altar and speak what words come. They "
                "arrive in an order you did not choose - the litany of the "
                "Gray Watch, spoken through you by many quiet voices at "
                "once. The defilement cracks and sloughs away like burnt "
                "skin, and with a grinding of ancient stone the floor "
                "behind the altar slides open, revealing steps that descend "
                "into the crypts below."
            ),
            conditional_fn=candles_snuffed,
            add_exit=("down", "crypt_stair"),
            points_awarded=100,
        )
        defiled_altar.add_interaction(
            verb="pray",
            from_state="defiled",
            message=(
                "You kneel and begin to pray, but the black flames lean "
                "toward you and drink the words out of the air before they "
                "are finished. No prayer will hold in this chapel while the "
                "candles burn."
            ),
        )
        defiled_altar.add_interaction(
            verb="pray",
            from_state="restored",
            message=(
                "You kneel once more. The quiet that answers is a kept "
                "promise - the Watch has nothing further to ask of you here."
            ),
        )
        defiled_altar.add_interaction(
            verb="examine",
            from_state="defiled",
            message=(
                "The altar was the Gray Watch's own - their burning tower is "
                "carved into its face, though claws have gouged deep marks "
                "across it. Dark residue cakes the altar stone, and the "
                "black candles ringing it burn with cold flames. Around its "
                "base an inscription survives: 'WHEN THE FALSE FLAME DIES, "
                "THE WATCH STILL ANSWERS PRAYER.' The flagstones behind the "
                "altar are scored in a wide arc, as if they once slid aside."
            ),
        )
        defiled_altar.add_interaction(
            verb="examine",
            from_state="restored",
            message=(
                "The altar stone is clean, its tower crest bright as if "
                "freshly cut. Behind it, stone steps descend into the "
                "crypts beneath the chapel."
            ),
        )
        self._rooms["chapel_dark"].add_item(defiled_altar)

        # =====================================================================
        # UNDERCRYPT - Tombs of the Gray Watch and their regalia
        # =====================================================================

        watch_tombs = StatefulItem(
            name="tombs",
            id="watch_tombs",
            description="Stone tombs of the Gray Watch fill the undercrypt.",
            state="default",
            takeable=False,
            synonyms=["tomb", "biers", "bier", "graves", "sarcophagi"],
        )
        watch_tombs.set_room_id("undercrypt")
        watch_tombs.add_state_description(
            "default",
            "The tombs of the Gray Watch stand rank on rank in the dark.",
        )
        watch_tombs.add_interaction(
            verb="examine",
            message=(
                "Knight after knight of the Gray Watch lies here in carved "
                "stone, swords clasped, faces worn smooth by the dark. At "
                "the far end, below the lowest tier of tombs, a corner of "
                "gold gleams - a door of gold sunk into the floor, with no "
                "lock, no seam, and no handle. Whatever opens it, no key "
                "forged by man will do it."
            ),
        )
        self._rooms["undercrypt"].add_item(watch_tombs)

        regalia = Item(
            name="regalia",
            id="gray_watch_regalia",
            description=(
                "The burial regalia of the Gray Watch lies here, a gray "
                "tabard and silvered pauldrons folded and untouched by rot."
            ),
            weight=2,
            value=120,
            takeable=True,
            synonyms=["gray watch regalia", "tabard", "pauldrons"],
        )
        self._rooms["undercrypt"].add_item(regalia)

        # =====================================================================
        # GREAT HALL - Torn banners (flavor)
        # =====================================================================

        hall_banners = StatefulItem(
            name="banners",
            id="hall_banners",
            description="Torn banners hang from the rafters of the great hall.",
            state="default",
            takeable=False,
            synonyms=["banner", "torn banners", "standards"],
        )
        hall_banners.set_room_id("great_hall")
        hall_banners.add_state_description(
            "default",
            "Torn banners stir overhead in a draft that touches nothing else.",
        )
        hall_banners.add_interaction(
            verb="examine",
            message=(
                "The banners once carried the burning tower of the Gray "
                "Watch. Every one has been overpainted with a pale, eyeless "
                "tower on a field of grey - Morvane's seal. Beneath the "
                "paint the older crest bleeds through, refusing to fade."
            ),
        )
        self._rooms["great_hall"].add_item(hall_banners)

        # =====================================================================
        # SOLAR - Puzzle 2: the winch (requires the iron crank), plus the
        # journal of Lord Morvane
        # =====================================================================

        winch = StatefulItem(
            name="winch",
            id="solar_winch",
            description="An iron winch is bolted to the wall, its drum jammed.",
            state="jammed",
            takeable=False,
            synonyms=["iron winch", "windlass", "mechanism", "drum"],
        )
        winch.set_room_id("solar")
        winch.add_state_description(
            "jammed",
            "An iron winch is bolted to the wall, rusted fast, its socket empty.",
        )
        winch.add_state_description(
            "turned",
            "The iron winch stands locked at the end of its travel, chain taut.",
        )
        winch.add_interaction(
            verb="turn",
            required_instrument="iron_crank",
            from_state="jammed",
            target_state="turned",
            message=(
                "You seat the iron crank in the winch's square socket and "
                "heave. The mechanism screams, sheds a century of rust, and "
                "the chains shriek away through the walls - somewhere east, "
                "iron clatters upward as a portcullis rises link by "
                "grinding link, then locks open with a boom that shakes "
                "dust from the shelves."
            ),
            reciprocal_exit=("throne_stair", "up", "throne_hall"),
            points_awarded=100,
        )
        winch.add_interaction(
            verb="turn",
            from_state="turned",
            message=(
                "The winch is already wound to its stop, the chain taut as "
                "a hanged man's rope. Somewhere east, the portcullis hangs "
                "open."
            ),
        )
        winch.add_interaction(
            verb="examine",
            from_state="jammed",
            message=(
                "The winch drum is wound with heavy chain that runs into a "
                "channel cut through the stone, off through the walls "
                "toward the throne stair east of the great hall. Its "
                "turning socket is square, sized for an iron crank, and "
                "empty. Rust has jammed the drum, but the mechanism looks "
                "sound - given the right handle."
            ),
        )
        winch.add_interaction(
            verb="examine",
            from_state="turned",
            message=(
                "The winch stands locked at the end of its travel, its "
                "chain taut in the wall channel. Whatever it lifted is "
                "staying lifted."
            ),
        )
        # The portcullis at the throne stair reflects the winch's state.
        winch.link_item("stair_portcullis")
        self._rooms["solar"].add_item(winch)

        journal = StatefulItem(
            name="journal",
            id="morvane_journal",
            description=(
                "A leather journal lies open on the desk, written in a "
                "precise, bloodless hand."
            ),
            state="default",
            weight=1,
            value=10,
            takeable=True,
            synonyms=["leather journal", "diary", "records"],
        )
        journal.add_interaction(
            verb="read",
            message=(
                "The script is Morvane's own, precise and utterly without "
                "warmth:\n"
                "'The Gray Watch are dust, yet their habits outlive them. "
                "They prayed below their chapel, and something below still "
                "listens for it. I have let the candles burn there to keep "
                "it deaf.'\n"
                "'The portcullis chain runs to the solar. I keep the crank "
                "elsewhere; let the stair stay shut.'\n"
                "'Beneath the tombs there is a door of gold that no key "
                "forged by man will open. I have stopped trying. I have "
                "not stopped listening.'"
            ),
        )
        journal.add_interaction(
            verb="examine",
            message=(
                "The journal is bound in pale leather you decide not to "
                "look at too closely. Its entries are dated across three "
                "centuries in the same unchanging hand."
            ),
        )
        self._rooms["solar"].add_item(journal)

        # =====================================================================
        # THRONE STAIR - The lowered portcullis (raised by the solar winch)
        # =====================================================================

        portcullis = StatefulItem(
            name="portcullis",
            id="stair_portcullis",
            description="A lowered iron portcullis seals the stair upward.",
            state="lowered",
            takeable=False,
            synonyms=["iron portcullis", "gate", "grate", "bars"],
        )
        portcullis.set_room_id("throne_stair")
        portcullis.add_state_description(
            "lowered",
            "A lowered iron portcullis seals the stair, teeth sunk into stone.",
        )
        portcullis.add_state_description(
            "turned",
            "The portcullis hangs high in its housing; the stair above is open.",
        )
        portcullis.add_interaction(
            verb="examine",
            from_state="lowered",
            message=(
                "The portcullis is citadel iron, each bar thick as your "
                "wrist, its teeth sunk deep into sockets in the stone. No "
                "lever or windlass stands on this side - the lifting chain "
                "rattles away west through a channel in the wall, toward "
                "the great hall and the rooms beyond it."
            ),
        )
        portcullis.add_interaction(
            verb="examine",
            from_state="turned",
            message=(
                "The portcullis hangs high in its housing, dripping rust, "
                "its teeth clear of the floor. The stair to the throne "
                "hall stands open."
            ),
        )
        portcullis.add_interaction(
            verb="lift",
            from_state="lowered",
            message=(
                "You work your fingers under the lowest bar and heave until "
                "your vision swims. It does not shift a hair's breadth - "
                "the counterweight chain runs west through the wall, and "
                "the gate will only move from wherever that chain ends."
            ),
        )
        portcullis.add_interaction(
            verb="raise",
            from_state="lowered",
            message=(
                "No strength of arm will raise citadel iron. The lifting "
                "chain runs west through the wall - find its winch."
            ),
        )
        portcullis.add_interaction(
            verb="open",
            from_state="lowered",
            message=(
                "The portcullis is not a door to be opened; it is a weight "
                "to be lifted, and its chain runs west into the wall."
            ),
        )
        portcullis.add_interaction(
            verb="lift",
            from_state="turned",
            message="The portcullis is already raised and locked in its housing.",
        )
        self._rooms["throne_stair"].add_item(portcullis)

        # =====================================================================
        # THRONE HALL - The basalt throne (flavor)
        # =====================================================================

        pale_throne = StatefulItem(
            name="throne",
            id="pale_throne",
            description="A basalt throne stands upon the dais.",
            state="default",
            takeable=False,
            synonyms=["basalt throne", "dais", "seat"],
        )
        pale_throne.set_room_id("throne_hall")
        pale_throne.add_state_description(
            "default",
            "The basalt throne waits on its dais, patient as a grave.",
        )
        pale_throne.add_interaction(
            verb="examine",
            message=(
                "The throne is a single block of basalt, polished by "
                "centuries of stillness rather than use. Sitting in it "
                "would be like climbing into a grave that fits."
            ),
        )
        pale_throne.add_interaction(
            verb="touch",
            message=(
                "The stone is colder than the air, colder than winter - "
                "cold the way a dead man's hand is cold. You take your "
                "fingers away."
            ),
        )
        self._rooms["throne_hall"].add_item(pale_throne)

        # =====================================================================
        # SANCTUM - Puzzle 3: the standing mirror (requires the Watchfire
        # mark), plus Morvane's grimoire
        # =====================================================================

        standing_mirror = StatefulItem(
            name="mirror",
            id="standing_mirror",
            description="A standing mirror in a black silver frame fills the east wall.",
            state="dark",
            takeable=False,
            synonyms=["standing mirror", "glass", "looking glass"],
        )
        standing_mirror.set_room_id("sanctum")
        standing_mirror.add_state_description(
            "dark",
            "The standing mirror is dark, its reflection a half-beat out of step.",
        )
        standing_mirror.add_state_description(
            "blazing",
            "The standing mirror blazes with silver light, swung aside like a door.",
        )
        # NOTE: the conditional interaction MUST come first - interactions
        # are checked in order and fall through when conditional_fn is False.
        standing_mirror.add_interaction(
            verb="touch",
            from_state="dark",
            target_state="blazing",
            message=(
                "You press your palm to the glass. In the mirror, your "
                "reflection's palm burns with silver fire - the Watchfire "
                "mark, blazing like a brand of cold light. The darkness in "
                "the glass shrieks and boils away, and the standing mirror "
                "swings aside on hidden hinges, revealing a vault to the "
                "east."
            ),
            conditional_fn=bears_watchfire_mark,
            add_exit=("east", "vault"),
            points_awarded=150,
        )
        standing_mirror.add_interaction(
            verb="touch",
            from_state="dark",
            message=(
                "You press your palm to the cold glass. Your reflection "
                "stares back, unmarked, and the darkness within the mirror "
                "does not stir. Something in the glass is waiting for a "
                "mark of silver fire that you do not bear."
            ),
        )
        standing_mirror.add_interaction(
            verb="touch",
            from_state="blazing",
            message=(
                "The glass is warm now, humming faintly with silver light. "
                "The way east into the vault stands open."
            ),
        )
        standing_mirror.add_interaction(
            verb="examine",
            from_state="dark",
            message=(
                "The mirror's frame is black silver, worked with a ring of "
                "small towers. The glass reflects the sanctum faithfully - "
                "except that in the reflection the room is darker, and the "
                "frame's towers burn. Etched at the mirror's foot: 'ONLY "
                "THE WATCHFIRE SHOWS TRUE.' It seems to be waiting for a "
                "touch - from the right palm."
            ),
        )
        standing_mirror.add_interaction(
            verb="examine",
            from_state="blazing",
            message=(
                "The mirror stands swung aside on hidden hinges, its glass "
                "full of steady silver fire. Beyond it, the vault opens to "
                "the east."
            ),
        )
        self._rooms["sanctum"].add_item(standing_mirror)

        grimoire = StatefulItem(
            name="grimoire",
            id="pale_grimoire",
            description=(
                "A grimoire bound in grey vellum rests on the reading "
                "stand, heavier than it looks."
            ),
            state="default",
            weight=2,
            value=150,
            takeable=True,
            synonyms=["tome", "spellbook", "book"],
        )
        grimoire.add_interaction(
            verb="read",
            message=(
                "The grimoire's pages are mist pressed flat and inked in "
                "silence. The rites it records are those that sealed the "
                "Mournvale: circles of fog, names unspoken, a valley "
                "folded shut like a letter. In the margins, one note "
                "recurs in a hand that shakes: 'The mark of silver fire "
                "undoes all of this.'"
            ),
        )
        grimoire.add_interaction(
            verb="examine",
            message=(
                "The grimoire is bound in grey vellum and clasped in black "
                "silver. It is cold, and slightly damp, like everything "
                "the mist has owned."
            ),
        )
        self._rooms["sanctum"].add_item(grimoire)

        # =====================================================================
        # BALCONY - The view and the forgotten jet gem
        # =====================================================================

        parapet = StatefulItem(
            name="parapet",
            id="balcony_parapet",
            description="A stone parapet rings the balcony's edge.",
            state="default",
            takeable=False,
            synonyms=["railing", "ledge", "view", "overlook"],
        )
        parapet.set_room_id("balcony")
        parapet.add_state_description(
            "default",
            "The parapet overlooks the whole of the mist-bound Mournvale.",
        )
        parapet.add_interaction(
            verb="examine",
            message=(
                "From here the whole Mournvale lies pinned beneath the "
                "mist: the village with its guttering lights, the black "
                "woods, the thread of the river and its bridge. At this "
                "height the mist's true shape is plain - a closed ring "
                "around the valley, without a single gap. On the parapet "
                "stones, a gem of polished jet lies where someone set it "
                "down and never came back."
            ),
        )
        self._rooms["balcony"].add_item(parapet)

        jet_gem = Item(
            name="gem",
            id="jet_gem",
            description=(
                "A gem of polished jet lies here, drinking what little "
                "light there is."
            ),
            weight=0,
            value=100,
            takeable=True,
            synonyms=["jet", "jet gem", "black gem"],
        )
        self._rooms["balcony"].add_item(jet_gem)

        # =====================================================================
        # VAULT - The sovereign's hoard
        # =====================================================================

        crown = Item(
            name="crown",
            id="pale_crown",
            description=(
                "The crown of the Pale Sovereign rests here, pale gold set "
                "with colorless stones that hold no sparkle."
            ),
            weight=1,
            value=400,
            takeable=True,
            synonyms=["crown of the pale sovereign", "pale crown"],
        )
        self._rooms["vault"].add_item(crown)

        scepter = Item(
            name="scepter",
            id="silver_scepter",
            description=(
                "A silver scepter lies here, its head worked into a closed "
                "ring of mist-veiled towers."
            ),
            weight=1,
            value=300,
            takeable=True,
            synonyms=["silver scepter", "sceptre", "rod"],
        )
        self._rooms["vault"].add_item(scepter)

        casket = Item(
            name="casket",
            id="casket_of_gems",
            description=(
                "A small iron casket sits here, brimming with gems that "
                "glitter like frost."
            ),
            weight=3,
            value=200,
            takeable=True,
            synonyms=["casket of gems", "gems", "small casket"],
        )
        self._rooms["vault"].add_item(casket)

        dawnblade = Weapon(
            name="dawnblade",
            id="dawnblade",
            description=(
                "The Dawnblade lies here across an iron rack, its long "
                "blade glowing with pale silver fire - the last light the "
                "Gray Watch ever forged."
            ),
            weight=3,
            value=250,
            takeable=True,
            damage=12,
            min_level="Magister",
            min_strength=14,
            min_dexterity=10,
        )
        dawnblade.synonyms = ["dawn blade", "silver sword", "sword", "blade"]
        dawnblade.emits_light = True
        self._rooms["vault"].add_item(dawnblade)

        # =====================================================================
        # GOLDEN DOOR - a legend, not a feature (see services/golden_doors)
        # =====================================================================
        from services.golden_doors import create_golden_door

        create_golden_door(
            "undercrypt",
            self._rooms["undercrypt"],
            theme_hint=(
                "a cold dimension on the far side of every mirror, where the "
                "Gray Watch's dead keep a second, stranger vigil"
            ),
            riddle_text=("'I AM ALWAYS COMING BUT I NEVER ARRIVE. NAME ME.'"),
            riddle_answer="tomorrow",
        )

    def spawn_mobs(self, mob_manager: Any) -> None:
        """Spawn mobs for Level 3."""

        # Gargoyle guarding the causeway
        self.spawn_mob_in_room(mob_manager, "gargoyle", "causeway")

        # Wraith haunting the tombs of the Gray Watch
        self.spawn_mob_in_room(mob_manager, "wraith", "undercrypt")

        # Vampire spawn prowling the lower citadel
        self.spawn_mob_in_room(mob_manager, "spawn", "great_hall")
        self.spawn_mob_in_room(mob_manager, "spawn", "bailey")

        # LORD MORVANE, THE PALE SOVEREIGN - final boss
        self.spawn_mob_in_room(mob_manager, "morvane", "throne_hall")
