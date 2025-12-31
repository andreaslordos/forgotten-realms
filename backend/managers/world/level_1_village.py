# backend/managers/world/level_1_village.py
"""
Level 1: Village of Barovia

A safe starting area under eternal twilight. The village is quiet,
oppressed by the mists that trap all souls in this cursed valley.
NPCs here offer hints and quests. The mist barrier blocks exit south
until solved.

Rooms: ~35-40 total
Mobs: Non-aggressive NPCs (peasant, barkeep, priest)
Transition to L2: Mist barrier requires mist_token from cellar OR priest's blessing
"""

from typing import Dict, Any
from models.Room import Room
from models.Item import Item
from models.StatefulItem import StatefulItem
from models.ContainerItem import ContainerItem
from models.Weapon import Weapon
from .level_base import LevelGenerator


class Level1Village(LevelGenerator):
    """Generator for Level 1: Village of Barovia."""

    level_number = 1
    level_name = "Village of Barovia"

    def generate_rooms(self) -> Dict[str, Room]:
        """Generate all rooms for the Village of Barovia."""

        # =====================================================================
        # VILLAGE CORE - Main locations
        # =====================================================================

        square = Room(
            "square",
            "Village Square",
            "A bleak village square choked with perpetual mist. A gallows stands "
            "in the center, its rope swaying despite the still air. A weathered notice "
            "board stands near the gallows and a rusty bucket lies overturned by a "
            "cracked fountain. The church lies north, the tavern east, the mercantile "
            "southwest, the manor west, and a dirt road leads south.",
            is_outdoor=True,
        )

        tavern = Room(
            "tavern",
            "Blood of the Vine Tavern",
            "The tavern's interior is dim and smoky. A worn rug lies near the back "
            "wall, its edges curled with age. A faded painting hangs crooked on the "
            "wall above scratched tables and a cold hearth. The village square is "
            "visible through grimy windows to the west.",
        )

        cellar = Room(
            "cellar",
            "Tavern Cellar",
            "Dusty wine barrels line the walls of this cold cellar. A locked chest "
            "sits in the dusty corner with strange symbols scratched into the nearby "
            "wall. An old crate has been pushed against the far wall, as if to hide "
            "something.",
            is_dark=True,
        )

        church = Room(
            "church",
            "Village Church",
            "This small stone church has seen better days. Cracked pews face a simple "
            "altar beneath what remains of stained glass. An iron grate is set into "
            "the floor and a donation box sits by the entrance. Despite the decay, "
            "something here feels safer. The square lies south, graveyard west.",
        )

        undercroft = Room(
            "undercroft",
            "Church Undercroft",
            "A cramped stone chamber beneath the church. Holy symbols scratched into "
            "the walls, some in what looks like dried blood. A torn prayer book lies "
            "on the floor near an old reliquary with cracked glass. Scratching sounds "
            "echo from somewhere in the shadows.",
            is_dark=True,
        )

        shop = Room(
            "shop",
            "Bildrath's Mercantile",
            "A cramped general store crammed with overpriced goods. Dusty shelves hold "
            "basic supplies - rope, torches, rations. A locked display case contains "
            "more valuable items. A sign reads 'NO CREDIT'. The square lies northeast.",
        )

        manor = Room(
            "manor",
            "Burgomaster's Manor",
            "Once grand, this manor now shows signs of siege. Claw marks score the "
            "wooden door and dust covers everything. A coat rack stands by the door "
            "and a silver mirror lies on a side table. The blocked staircase leads "
            "nowhere. A study lies north, the square east.",
        )

        study = Room(
            "study",
            "Manor Study",
            "Books line the walls, many dealing with the history of Barovia. A desk "
            "sits by a shuttered window, covered in papers and a half-finished letter. "
            "An ornate silver opener gleams beside an old globe. A portrait of a young "
            "woman named Ireena watches from the wall. The manor's main hall lies south.",
        )

        graveyard = Room(
            "graveyard",
            "Village Graveyard",
            "Crooked headstones jut from the muddy earth. A weathered angel statue "
            "watches over them, one wing broken. Fresh flowers mark a grave labeled "
            "'Kolyan Indirovich'. An iron gate leads to a family crypt. The church "
            "stands east.",
            is_outdoor=True,
        )

        crypt = Room(
            "crypt",
            "Family Crypt",
            "Stone sarcophagi line the walls. Names are carved into the stone - "
            "Kolyanovich, Dilisnya, Wachter. A stone coffin dominates the center "
            "amid wilted flowers. Claw marks score the inside of the crypt door. "
            "The graveyard lies through the iron gate.",
            is_dark=True,
        )

        # =====================================================================
        # VILLAGE OUTSKIRTS - Extended areas
        # =====================================================================

        road = Room(
            "road",
            "Old Svalich Road",
            "A muddy road winds through the village outskirts. A broken signpost "
            "points in various directions, its paint faded. Wagon wheel ruts scar "
            "the mud. The village square lies north, a gatehouse south, an alley east.",
            is_outdoor=True,
        )

        gatehouse = Room(
            "gatehouse",
            "Village Gatehouse",
            "A crumbling stone gatehouse marks the village's southern boundary. Beyond "
            "the rusted iron gates, an impenetrable mist blocks the road. A stone bench "
            "and ancient torch bracket stand by the gate. Strange symbols score the "
            "gateposts. The road leads north.",
            is_outdoor=True,
        )

        alley = Room(
            "alley",
            "Shadowed Alley",
            "A narrow alley between decaying buildings. Someone scratched 'THEY WATCH "
            "AT NIGHT' into the wall. A rickety ladder leans against the wall leading "
            "to a rooftop. The road lies west, a boarded door north.",
        )

        rooftop = Room(
            "rooftop",
            "Crooked Rooftop",
            "From this sagging rooftop you can see most of the village. A broken "
            "weathervane spins slowly. Someone left a crude telescope here aimed at "
            "the distant castle. The ladder leads down to the alley.",
        )

        cottage1 = Room(
            "cottage1",
            "Abandoned Cottage",
            "This cottage was left in a hurry. A meal sits rotting on the table and "
            "a child's doll lies abandoned by the cold hearth. A rocking chair moves "
            "slightly as if recently vacated. The door leads south.",
        )

        cottage2 = Room(
            "cottage2",
            "Herbalist's Cottage",
            "Bundles of dried herbs hang from the ceiling. A mortar and pestle sits "
            "on a workbench beside a leather journal of remedies. A small cauldron "
            "hangs over a cold fire pit. The village square lies north.",
        )

        well = Room(
            "well",
            "Village Well",
            "An old stone well stands in a small courtyard. The water below reflects "
            "nothing - not even the grey sky. Coins glint at the bottom, wishes never "
            "granted. Paths lead to the church east and the manor south.",
            is_outdoor=True,
        )

        garden = Room(
            "garden",
            "Overgrown Garden",
            "What was once a garden is now choked with weeds. A rusty fork is stuck "
            "in the earth and a scarecrow watches with button eyes, stuffing leaking "
            "from its chest. The manor lies south, a tool shed west.",
            is_outdoor=True,
        )

        shed = Room(
            "shed",
            "Tool Shed",
            "A rickety shed filled with rusted implements and spiderwebs. An axe "
            "leans against the wall, its blade still sharp. Coils of rope hang from "
            "hooks. The garden is visible through the doorway.",
        )

        stable = Room(
            "stable",
            "Abandoned Stable",
            "The stable is empty but the smell of horses lingers. Straw covers the "
            "floor, old and musty. A saddle sits on a rack and horseshoes hang from "
            "nails. The manor courtyard is visible east.",
        )

        # =====================================================================
        # FLAVOR ROOMS - Atmospheric expansion
        # =====================================================================

        smithy = Room(
            "smithy",
            "Cold Smithy",
            "The forge has been cold for months. Tools lie scattered as if the smith "
            "left mid-work and a half-finished horseshoe sits on the anvil. Soot covers "
            "everything. The village square lies north.",
        )

        fountain = Room(
            "fountain",
            "Broken Fountain",
            "A cracked fountain stands dry, its central statue defaced beyond "
            "recognition. Dead leaves gather in the basin beside a green copper "
            "coin. The inscription has been scratched out. The church lies northeast.",
            is_outdoor=True,
        )

        burnt = Room(
            "burnt",
            "Burned Ruin",
            "This building burned long ago. Only charred timbers and stone foundation "
            "remain. A child's toy lies miraculously unburned among the debris. The "
            "smell of old smoke clings to everything. The road lies south.",
            is_outdoor=True,
        )

        chapel_ruins = Room(
            "chapel_ruins",
            "Ruined Shrine",
            "A small roadside shrine, long abandoned. The idol has been smashed, "
            "leaving only fragments. Someone left fresh offerings despite the "
            "destruction - a crust of bread, a wilted flower. The road lies east.",
            is_outdoor=True,
        )

        cellar_tunnel = Room(
            "cellar_tunnel",
            "Secret Tunnel",
            "A cramped earthen tunnel dug in secret over many years. Tool marks score "
            "the walls and roots dangle from the ceiling. A lantern stub lies discarded "
            "in the dirt. The tunnel leads back to the cellar.",
            is_dark=True,
        )

        watchtower = Room(
            "watchtower",
            "Crumbling Watchtower",
            "This small watchtower once guarded the village's southern approach. The "
            "roof has collapsed and stairs are treacherous. A guard's logbook lies "
            "open, pages blank for years. A brass spyglass rests on the windowsill. "
            "Stairs lead down to the gatehouse.",
        )

        # =====================================================================
        # Store all rooms
        # =====================================================================

        self._rooms = {
            # Village core
            "square": square,
            "tavern": tavern,
            "cellar": cellar,
            "church": church,
            "undercroft": undercroft,
            "shop": shop,
            "manor": manor,
            "study": study,
            "graveyard": graveyard,
            "crypt": crypt,
            # Village outskirts
            "road": road,
            "gatehouse": gatehouse,
            "alley": alley,
            "rooftop": rooftop,
            "cottage1": cottage1,
            "cottage2": cottage2,
            "well": well,
            "garden": garden,
            "shed": shed,
            "stable": stable,
            # Flavor rooms
            "smithy": smithy,
            "fountain": fountain,
            "burnt": burnt,
            "chapel_ruins": chapel_ruins,
            "cellar_tunnel": cellar_tunnel,
            "watchtower": watchtower,
        }

        return self._rooms

    def connect_internal_exits(self) -> None:
        """Connect exits between rooms within the Village."""

        # =====================================================================
        # VILLAGE CORE CONNECTIONS
        # =====================================================================

        self._rooms["square"].exits = {
            "north": "church",
            "east": "tavern",
            "south": "road",
            "west": "manor",
            "southwest": "shop",
            "southeast": "smithy",
            "northwest": "well",
        }

        self._rooms["tavern"].exits = {
            "west": "square",
            # "down": "cellar" - revealed by moving rug
        }

        self._rooms["cellar"].exits = {
            "up": "tavern",
            # "north": "cellar_tunnel" - revealed by moving crate
        }

        self._rooms["cellar_tunnel"].exits = {
            "south": "cellar",
        }

        self._rooms["church"].exits = {
            "south": "square",
            "west": "graveyard",
            "southwest": "fountain",
            # "down": "undercroft" - revealed by opening grate
        }

        self._rooms["undercroft"].exits = {
            "up": "church",
        }

        self._rooms["shop"].exits = {
            "northeast": "square",
        }

        self._rooms["manor"].exits = {
            "east": "square",
            "north": "study",
            "west": "stable",
            "northwest": "garden",
        }

        self._rooms["study"].exits = {
            "south": "manor",
        }

        self._rooms["graveyard"].exits = {
            "east": "church",
            "in": "crypt",
            "south": "chapel_ruins",
        }

        self._rooms["crypt"].exits = {
            "out": "graveyard",
        }

        # =====================================================================
        # VILLAGE OUTSKIRTS CONNECTIONS
        # =====================================================================

        self._rooms["road"].exits = {
            "north": "square",
            "south": "gatehouse",
            "east": "alley",
            "west": "burnt",
            "northwest": "cottage1",
        }

        self._rooms["gatehouse"].exits = {
            "north": "road",
            "up": "watchtower",
            # "south": "road_south" - mist barrier blocks until solved
        }

        self._rooms["watchtower"].exits = {
            "down": "gatehouse",
        }

        self._rooms["alley"].exits = {
            "west": "road",
            "up": "rooftop",
            "north": "cottage2",
        }

        self._rooms["rooftop"].exits = {
            "down": "alley",
        }

        self._rooms["cottage1"].exits = {
            "southeast": "road",
        }

        self._rooms["cottage2"].exits = {
            "south": "alley",
            "north": "square",
        }

        self._rooms["well"].exits = {
            "east": "church",
            "south": "manor",
            "southeast": "square",
        }

        self._rooms["garden"].exits = {
            "south": "manor",
            "west": "shed",
        }

        self._rooms["shed"].exits = {
            "east": "garden",
        }

        self._rooms["stable"].exits = {
            "east": "manor",
        }

        # =====================================================================
        # FLAVOR ROOM CONNECTIONS
        # =====================================================================

        self._rooms["smithy"].exits = {
            "north": "square",
        }

        self._rooms["fountain"].exits = {
            "northeast": "church",
        }

        self._rooms["burnt"].exits = {
            "east": "road",
        }

        self._rooms["chapel_ruins"].exits = {
            "north": "graveyard",
        }

    def add_items(self) -> None:
        """Add items to rooms in the Village."""

        # =====================================================================
        # TAVERN - Rug hiding trapdoor (main puzzle)
        # =====================================================================

        rug = StatefulItem(
            name="rug",
            id="tavern_rug",
            description="A worn rug with faded patterns, curled at the edges from years of foot traffic.",
            state="flat",
            takeable=False,
            synonyms=["carpet", "mat", "worn rug", "floor rug"],
        )
        rug.set_room_id("tavern")
        rug.add_state_description(
            "flat", "A worn rug lies near the back wall, its edges curled with age."
        )
        rug.add_state_description(
            "moved",
            "A worn rug has been pushed aside, revealing a trapdoor leading down.",
        )

        rug.add_interaction(
            verb="move",
            from_state="flat",
            target_state="moved",
            message="You push the rug aside, revealing a trapdoor leading down into darkness!",
            add_exit=("down", "cellar"),
        )
        rug.add_interaction(
            verb="pull",
            from_state="flat",
            target_state="moved",
            message="You pull the rug aside, revealing a dusty trapdoor hidden beneath!",
            add_exit=("down", "cellar"),
        )
        rug.add_interaction(
            verb="lift",
            from_state="flat",
            target_state="moved",
            message="You lift the edge of the rug, revealing a trapdoor hidden beneath!",
            add_exit=("down", "cellar"),
        )
        rug.add_interaction(
            verb="examine",
            message="A worn rug with faded patterns. The edges are curled, and there seems to be "
            "something uneven underneath. It looks like it could be moved.",
        )
        self._rooms["tavern"].add_item(rug)

        # Painting with hidden safe
        painting = StatefulItem(
            name="painting",
            id="tavern_painting",
            description="A faded oil painting of a hunting scene, hanging crooked on the wall.",
            state="hanging",
            takeable=False,
            synonyms=["faded painting", "oil painting", "picture", "art"],
        )
        painting.set_room_id("tavern")
        painting.add_state_description(
            "hanging", "A faded painting hangs crooked on the wall."
        )
        painting.add_state_description(
            "moved", "The painting has been moved aside, revealing a small wall safe."
        )

        painting.add_interaction(
            verb="move",
            from_state="hanging",
            target_state="moved",
            message="You swing the painting aside, revealing a small wall safe hidden behind it!",
        )
        painting.add_interaction(
            verb="examine",
            message="A faded oil painting depicting nobles on a hunt. It hangs slightly crooked, "
            "as if it's been moved recently. The frame seems loose.",
        )
        self._rooms["tavern"].add_item(painting)

        # Wall safe
        safe = StatefulItem(
            name="safe",
            id="tavern_safe",
            description="A small iron safe set into the wall.",
            state="locked",
            takeable=False,
            synonyms=["wall safe", "iron safe", "strongbox"],
        )
        safe.set_room_id("tavern")
        safe.add_state_description(
            "locked", "A small iron safe is set into the wall. It's locked tight."
        )
        safe.add_state_description(
            "open", "The wall safe stands open, its contents accessible."
        )

        safe.add_interaction(
            verb="open",
            from_state="locked",
            target_state="open",
            message="The safe clicks open, revealing a small pouch of coins and an old key!",
            required_instrument="opener",
        )
        safe.add_interaction(
            verb="open",
            from_state="locked",
            message="The safe is locked tight.",
        )
        safe.add_interaction(
            verb="examine",
            message="A sturdy iron safe. The lock mechanism looks simple enough - something "
            "thin and pointed might do the trick.",
        )

        # Safe contents as hidden items
        def safe_opened(game_state: Any) -> bool:
            room = game_state.get_room("tavern")
            if not room:
                return False
            # Check hidden_items directly to avoid recursion
            if "tavern_safe" in room.hidden_items:
                item, _ = room.hidden_items["tavern_safe"]
                return getattr(item, "state", None) == "open"
            # Also check regular items
            for item in room.items:
                if getattr(item, "id", None) == "tavern_safe":
                    return getattr(item, "state", None) == "open"
            return False

        safe_coins = Item(
            name="coin pouch",
            id="safe_coins",
            description="A small leather pouch containing a handful of gold coins.",
            weight=1,
            value=50,
            takeable=True,
        )
        self._rooms["tavern"].add_hidden_item(safe_coins, safe_opened)

        cellar_key = Item(
            name="old key",
            id="cellar_key",
            description="A tarnished brass key with teeth worn smooth by age.",
            weight=0,
            value=5,
            takeable=True,
            synonyms=["brass key", "tarnished key"],
        )
        self._rooms["tavern"].add_hidden_item(cellar_key, safe_opened)

        # Only add safe as hidden until painting moved
        def painting_moved(game_state: Any) -> bool:
            room = game_state.get_room("tavern")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "tavern_painting":
                    return getattr(item, "state", None) == "moved"
            return False

        self._rooms["tavern"].add_hidden_item(safe, painting_moved)

        # =====================================================================
        # CELLAR - Chest with mist token, crate hiding tunnel
        # =====================================================================

        cellar_chest = StatefulItem(
            name="chest",
            id="cellar_chest",
            description="A dusty wooden chest bound with iron bands.",
            state="locked",
            takeable=False,
            synonyms=["wooden chest", "locked chest", "dusty chest"],
        )
        cellar_chest.set_room_id("cellar")
        cellar_chest.add_state_description(
            "locked", "A dusty wooden chest sits in the corner, locked tight."
        )
        cellar_chest.add_state_description("open", "The wooden chest stands open.")

        cellar_chest.add_interaction(
            verb="open",
            from_state="locked",
            target_state="open",
            message="The old key turns in the lock with a satisfying click. Inside, you find "
            "a strange silver token and some old documents!",
            required_instrument="cellar_key",
        )
        cellar_chest.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="open",
            message="The key fits perfectly! The chest creaks open, revealing its hidden contents!",
            required_instrument="cellar_key",
        )
        cellar_chest.add_interaction(
            verb="open",
            from_state="locked",
            message="The chest is locked. You need a key.",
        )
        cellar_chest.add_interaction(
            verb="break",
            message="The iron bands are too sturdy. You'd need a key to open this properly.",
        )
        self._rooms["cellar"].add_item(cellar_chest)

        # Mist token - hidden until chest is opened
        def chest_opened(game_state: Any) -> bool:
            room = game_state.get_room("cellar")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "cellar_chest":
                    return getattr(item, "state", None) == "open"
            return False

        mist_token = Item(
            name="mist token",
            id="mist_token",
            description="A silver token inscribed with swirling runes. It pulses with faint "
            "otherworldly light. The mists seem to recoil from it.",
            weight=0,
            value=100,
            takeable=True,
            synonyms=["silver token", "token", "rune token"],
        )
        self._rooms["cellar"].add_hidden_item(mist_token, chest_opened)

        old_documents = Item(
            name="documents",
            id="old_documents",
            description="Yellowed documents describing the mist barrier. One passage reads: "
            "'The token grants passage, but the Morning Lord's blessing may also part the mists.'",
            weight=0,
            value=10,
            takeable=True,
            synonyms=["old documents", "papers", "yellowed papers"],
        )
        self._rooms["cellar"].add_hidden_item(old_documents, chest_opened)

        # Crate hiding tunnel
        crate = StatefulItem(
            name="crate",
            id="cellar_crate",
            description="An old wooden crate pushed against the far wall.",
            state="blocking",
            takeable=False,
            synonyms=["wooden crate", "old crate", "box"],
        )
        crate.set_room_id("cellar")
        crate.add_state_description(
            "blocking", "An old crate has been pushed against the far wall."
        )
        crate.add_state_description(
            "moved", "The crate has been moved, revealing a narrow tunnel entrance."
        )

        crate.add_interaction(
            verb="move",
            from_state="blocking",
            target_state="moved",
            message="You push the heavy crate aside, revealing a narrow tunnel dug into the earth!",
            add_exit=("north", "cellar_tunnel"),
        )
        crate.add_interaction(
            verb="push",
            from_state="blocking",
            target_state="moved",
            message="With effort, you shove the crate away from the wall. A secret tunnel lies behind it!",
            add_exit=("north", "cellar_tunnel"),
        )
        crate.add_interaction(
            verb="examine",
            message="A heavy wooden crate. Scrape marks on the floor suggest it's been moved before. "
            "Strange... there seems to be a draft coming from behind it.",
        )
        self._rooms["cellar"].add_item(crate)

        # Wall symbols
        wall_symbols = StatefulItem(
            name="symbols",
            id="cellar_symbols",
            description="Strange symbols scratched into the cellar wall.",
            state="default",
            takeable=False,
            synonyms=["scratches", "markings", "wall symbols", "strange symbols"],
        )
        wall_symbols.set_room_id("cellar")
        wall_symbols.add_interaction(
            verb="examine",
            message="The symbols appear to be protective wards - the same style as the ones at the "
            "gatehouse. Someone was very afraid of something getting in... or out.",
        )
        wall_symbols.add_interaction(
            verb="read",
            message="The symbols aren't letters, but you recognize them as protective sigils. "
            "Whoever carved these feared the dark.",
        )
        self._rooms["cellar"].add_item(wall_symbols)

        # =====================================================================
        # CHURCH - Grate to undercroft, donation box
        # =====================================================================

        grate = StatefulItem(
            name="grate",
            id="church_grate",
            description="An iron grate set into the floor near the altar.",
            state="closed",
            takeable=False,
            synonyms=["iron grate", "floor grate", "trapdoor", "grille"],
        )
        grate.set_room_id("church")
        grate.add_state_description(
            "closed", "An iron grate is set into the floor near the altar."
        )
        grate.add_state_description(
            "open",
            "The iron grate stands open, revealing steps leading down into darkness.",
        )

        grate.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="With effort, you pull the heavy grate open. Stone steps descend into darkness. "
            "A foul smell wafts up from below.",
            add_exit=("down", "undercroft"),
        )
        grate.add_interaction(
            verb="close",
            from_state="open",
            target_state="closed",
            message="You lower the iron grate back into place, sealing the undercroft.",
            remove_exit="down",
        )
        grate.add_interaction(
            verb="examine",
            message="A heavy iron grate set into the stone floor. Through the bars, you can see "
            "stone steps descending into darkness. The bars show scratch marks on the inside.",
        )
        self._rooms["church"].add_item(grate)

        donation_box = ContainerItem(
            name="donation box",
            id="donation_box",
            description="A simple wooden box for offerings to the Morning Lord.",
            weight=5,
            value=0,
            capacity_limit=10,
            capacity_weight=20,
            takeable=False,
        )
        donation_box.synonyms = ["box", "offering box", "wooden box"]
        donation_box.add_interaction(
            verb="open",
            target_state="open",
            message="You lift the lid of the donation box.",
            from_state="closed",
        )
        donation_box.add_interaction(
            verb="close",
            target_state="closed",
            message="You close the donation box.",
            from_state="open",
        )
        self._rooms["church"].add_item(donation_box)

        # Candles
        candle = Item(
            name="candle",
            id="church_candle",
            description="A tallow candle that provides dim but steady light.",
            weight=0,
            value=2,
            takeable=True,
            emits_light=True,
        )
        self._rooms["church"].add_item(candle)

        # =====================================================================
        # UNDERCROFT - Holy bones, prayer book
        # =====================================================================

        reliquary = StatefulItem(
            name="reliquary",
            id="undercroft_reliquary",
            description="An old wooden reliquary with cracked glass.",
            state="closed",
            takeable=False,
            synonyms=["box", "wooden reliquary", "glass case"],
        )
        reliquary.set_room_id("undercroft")
        reliquary.add_state_description(
            "closed", "An old reliquary stands against the wall, its glass cracked."
        )
        reliquary.add_state_description(
            "open",
            "The reliquary stands open, revealing sacred bones wrapped in velvet.",
        )

        reliquary.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You carefully open the cracked reliquary. Inside, wrapped in faded velvet, "
            "are the sacred bones of St. Andral! They radiate gentle warmth.",
        )
        reliquary.add_interaction(
            verb="examine",
            message="A wooden reliquary for holding sacred relics. Through the cracked glass, "
            "you can see something wrapped in velvet within.",
        )
        self._rooms["undercroft"].add_item(reliquary)

        # Bones - hidden until reliquary opened
        def reliquary_opened(game_state: Any) -> bool:
            room = game_state.get_room("undercroft")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "undercroft_reliquary":
                    return getattr(item, "state", None) == "open"
            return False

        holy_bones = Item(
            name="bones",
            id="holy_bones",
            description="The sacred bones of St. Andral, wrapped in faded velvet. They radiate "
            "warmth and seem to glow faintly in the darkness.",
            weight=2,
            value=200,
            takeable=True,
            synonyms=["holy bones", "sacred bones", "st andral bones", "relics"],
        )
        self._rooms["undercroft"].add_hidden_item(holy_bones, reliquary_opened)

        prayer_book = Item(
            name="prayer book",
            id="prayer_book",
            description="A torn prayer book. One passage is circled: 'The Morning Lord's blessing "
            "grants safe passage through the mists of evil.'",
            weight=1,
            value=5,
            takeable=True,
            synonyms=["book", "torn book"],
        )
        self._rooms["undercroft"].add_item(prayer_book)

        # =====================================================================
        # MANOR STUDY - Opener, globe, portrait clue
        # =====================================================================

        opener = Item(
            name="opener",
            id="opener",
            description="An ornate silver opener with a wickedly sharp point.",
            weight=0,
            value=15,
            takeable=True,
            synonyms=["silver opener", "knife"],
        )
        self._rooms["study"].add_item(opener)

        unfinished_letter = Item(
            name="letter",
            id="unfinished_letter",
            description="A half-finished letter: 'My dearest Ireena, if you are reading this, "
            "I am already dead. The Devil has come for us at last. Flee if you can, but know "
            "this - the tavern cellar holds a secret that may save you. The token hidden there "
            "can pierce even his cursed mists. Your loving father, Kolyan.'",
            weight=0,
            value=10,
            takeable=True,
            synonyms=["half-finished letter", "note", "message"],
        )
        self._rooms["study"].add_item(unfinished_letter)

        globe = StatefulItem(
            name="globe",
            id="study_globe",
            description="An ornate globe showing lands that may no longer exist.",
            state="default",
            takeable=False,
        )
        globe.set_room_id("study")
        globe.add_interaction(
            verb="spin",
            message="You spin the globe. It creaks on its axis. All the lands are unfamiliar - "
            "except for a small valley labeled 'Barovia', circled in red ink.",
        )
        globe.add_interaction(
            verb="examine",
            message="An antique globe on a brass stand. The continents are unfamiliar, but a "
            "small valley is circled in red ink and labeled 'Barovia - the Land of Eternal Night'.",
        )
        self._rooms["study"].add_item(globe)

        # =====================================================================
        # MANOR - Mirror, coat rack
        # =====================================================================

        mirror = StatefulItem(
            name="mirror",
            id="manor_mirror",
            description="A tarnished silver hand mirror lying on the side table.",
            state="face_down",
            takeable=True,
            weight=1,
            synonyms=["hand mirror", "silver mirror", "looking glass"],
        )
        mirror.set_room_id("manor")
        mirror.add_interaction(
            verb="look",
            message="You gaze into the tarnished mirror. For a moment, you see not your reflection, "
            "but a pale face with burning red eyes staring back at you. Then it's gone, "
            "leaving only your startled expression.",
        )
        mirror.add_interaction(
            verb="examine",
            message="A tarnished silver mirror. Your reflection seems... off somehow. As if "
            "something else is watching from behind the glass.",
        )
        self._rooms["manor"].add_item(mirror)

        old_coat = Item(
            name="coat",
            id="old_coat",
            description="A dusty old coat hanging from the rack. It might provide some warmth.",
            weight=2,
            value=5,
            takeable=True,
            synonyms=["old coat", "dusty coat", "jacket"],
        )
        self._rooms["manor"].add_item(old_coat)

        # =====================================================================
        # GATEHOUSE - Mist barrier (level transition puzzle)
        # =====================================================================

        mist_barrier = StatefulItem(
            name="mist",
            id="mist_barrier",
            description="An impenetrable wall of mist blocks the road south.",
            state="blocking",
            takeable=False,
            synonyms=["mist barrier", "mists", "fog", "wall of mist"],
        )
        mist_barrier.set_room_id("gatehouse")
        mist_barrier.add_state_description(
            "blocking",
            "An impenetrable wall of mist blocks the road south. Tendrils reach toward you, "
            "then recoil. There must be a way through...",
        )
        mist_barrier.add_state_description(
            "parted",
            "The mist has parted, revealing the road south into the Svalich Woods.",
        )

        # Mist token allows passage
        mist_barrier.add_interaction(
            verb="enter",
            from_state="blocking",
            target_state="parted",
            message="You hold up the mist token. It flares with silver light! The mists shriek "
            "and part before you, revealing the road south. The way is now open!",
            required_instrument="mist_token",
            add_exit=("south", "road_south"),  # Connects to Level 2
        )
        mist_barrier.add_interaction(
            verb="use",
            from_state="blocking",
            target_state="parted",
            message="The token blazes with light as you approach the mist! The dark tendrils "
            "recoil and part, revealing the road beyond!",
            required_instrument="mist_token",
            add_exit=("south", "road_south"),
        )
        mist_barrier.add_interaction(
            verb="enter",
            from_state="blocking",
            message="You step into the mist. Cold fingers grasp at you, turning you around. "
            "No matter which way you push, you end up back at the gatehouse. "
            "You need something to pierce this barrier.",
        )
        mist_barrier.add_interaction(
            verb="examine",
            message="The mist is unnaturally thick and dark. It almost seems alive, watching you. "
            "The wards carved into the gateposts might once have kept it at bay, but they've "
            "faded with time. You'll need something special to pass through.",
        )
        self._rooms["gatehouse"].add_item(mist_barrier)

        # Torch bracket
        torch_bracket = StatefulItem(
            name="bracket",
            id="gatehouse_bracket",
            description="An ancient torch bracket mounted beside the gate.",
            state="empty",
            takeable=False,
            synonyms=["torch bracket", "sconce", "holder"],
        )
        torch_bracket.set_room_id("gatehouse")
        torch_bracket.add_state_description(
            "empty", "An ancient torch bracket is mounted beside the gate, empty."
        )
        torch_bracket.add_state_description(
            "lit", "A torch burns in the bracket, casting flickering shadows."
        )

        torch_bracket.add_interaction(
            verb="place",
            from_state="empty",
            target_state="lit",
            message="You place a torch in the bracket. The flames seem to push back the mist slightly.",
            required_instrument="torch",
        )
        self._rooms["gatehouse"].add_item(torch_bracket)

        # =====================================================================
        # SQUARE - Notice board, bucket, fountain
        # =====================================================================

        notice_board = StatefulItem(
            name="notice board",
            id="square_notice",
            description="A weathered notice board covered in faded postings.",
            state="default",
            takeable=False,
            synonyms=["board", "notices", "postings"],
        )
        notice_board.set_room_id("square")
        notice_board.add_interaction(
            verb="read",
            message="Most notices are illegible, but one stands out:\n\n"
            "'WANTED: News of the Holy Bones of St. Andral. The church offers blessing "
            "to any who return them to Father Donavich.'\n\n"
            "Another reads: 'BEWARE THE MISTS - None who enter return.'",
        )
        notice_board.add_interaction(
            verb="examine",
            message="A wooden board covered in yellowed papers. Most are rotted or illegible, "
            "but a few notices remain readable.",
        )
        self._rooms["square"].add_item(notice_board)

        rusty_bucket = Item(
            name="bucket",
            id="rusty_bucket",
            description="A rusty iron bucket with a hole in the bottom.",
            weight=2,
            value=1,
            takeable=True,
            synonyms=["rusty bucket", "iron bucket"],
        )
        self._rooms["square"].add_item(rusty_bucket)

        # =====================================================================
        # CRYPT - Coffin container, scratch marks
        # =====================================================================

        crypt_coffin = ContainerItem(
            name="coffin",
            id="crypt_coffin",
            description="A stone coffin with a heavy lid.",
            weight=500,
            value=0,
            capacity_limit=5,
            capacity_weight=50,
            takeable=False,
        )
        crypt_coffin.synonyms = ["stone coffin", "sarcophagus"]
        crypt_coffin.add_interaction(
            verb="open",
            target_state="open",
            message="You push the heavy stone lid aside with a grinding sound. Inside lies "
            "the desiccated remains of a noble, clutching a silver pendant.",
            from_state="closed",
        )
        crypt_coffin.add_interaction(
            verb="close",
            target_state="closed",
            message="You slide the heavy lid back into place.",
            from_state="open",
        )
        self._rooms["crypt"].add_item(crypt_coffin)

        # =====================================================================
        # GRAVEYARD - Angel statue, flowers
        # =====================================================================

        angel_statue = StatefulItem(
            name="statue",
            id="graveyard_statue",
            description="A weathered angel statue, one wing broken, watching over the graves.",
            state="default",
            takeable=False,
            synonyms=["angel statue", "angel", "stone angel", "weathered statue"],
        )
        angel_statue.set_room_id("graveyard")
        angel_statue.add_interaction(
            verb="examine",
            message="The stone angel has seen better days. One wing is broken off, and the face "
            "is worn smooth by years of rain. Yet somehow it still seems to offer comfort, "
            "as if watching over the souls buried here.",
        )
        angel_statue.add_interaction(
            verb="pray",
            message="You kneel before the angel and offer a silent prayer. For a moment, you "
            "feel a warmth in your chest, a sense of peace. Then it fades, but you feel "
            "slightly stronger for it.",
        )
        self._rooms["graveyard"].add_item(angel_statue)

        # =====================================================================
        # SHOP - Display case, supplies
        # =====================================================================

        display_case = StatefulItem(
            name="case",
            id="shop_case",
            description="A locked display case containing valuable items.",
            state="locked",
            takeable=False,
            synonyms=["display case", "glass case", "locked case"],
        )
        display_case.set_room_id("shop")
        display_case.add_state_description(
            "locked", "A locked display case contains more valuable items."
        )
        display_case.add_state_description("open", "The display case stands open.")

        display_case.add_interaction(
            verb="open",
            from_state="locked",
            message="Bildrath snarls at you. 'Touch that case and I'll have your hands! "
            "That's not for browsing - gold first, then you can look!'",
        )
        display_case.add_interaction(
            verb="examine",
            message="Through the glass, you can see a silver dagger, some healing potions, "
            "and what looks like a genuine torch that never goes out. All absurdly expensive, "
            "no doubt.",
        )
        self._rooms["shop"].add_item(display_case)

        # Basic supplies
        torch = Item(
            name="torch",
            id="shop_torch",
            description="A wooden torch wrapped in oil-soaked rags.",
            weight=1,
            value=10,  # Overpriced
            takeable=True,
            emits_light=True,
        )
        self._rooms["shop"].add_item(torch)

        rope = Item(
            name="rope",
            id="shop_rope",
            description="A coil of sturdy hemp rope, useful for climbing or binding.",
            weight=3,
            value=15,
            takeable=True,
        )
        self._rooms["shop"].add_item(rope)

        # =====================================================================
        # SHED - Axe (important tool for hag's cage later)
        # =====================================================================

        axe = Weapon(
            name="axe",
            id="woodcutter_axe",
            description="A heavy woodcutter's axe. The blade is still sharp despite its age.",
            weight=5,
            value=20,
            takeable=True,
            damage=8,
            min_level="Neophyte",
            min_strength=8,
            min_dexterity=0,
        )
        axe.synonyms = ["woodcutter axe", "woodcutters axe", "hatchet"]
        self._rooms["shed"].add_item(axe)

        # =====================================================================
        # ROOFTOP - Telescope, broken weathervane
        # =====================================================================

        telescope = StatefulItem(
            name="telescope",
            id="rooftop_telescope",
            description="A crude brass telescope aimed at the distant castle.",
            state="default",
            takeable=True,
            weight=2,
            synonyms=["spyglass", "brass telescope"],
        )
        telescope.set_room_id("rooftop")
        telescope.add_interaction(
            verb="look",
            message="You peer through the telescope at Castle Ravenloft. Lightning flashes "
            "reveal dark spires and crumbling battlements. For a moment, you think you "
            "see a figure watching from a high window. Then the lightning fades.",
        )
        telescope.add_interaction(
            verb="examine",
            message="A simple brass telescope, scratched and dented. Someone spent many hours "
            "here, watching the castle. Perhaps they were looking for a weakness. "
            "Or perhaps they were simply waiting for death.",
        )
        self._rooms["rooftop"].add_item(telescope)

        # =====================================================================
        # WELL - Bucket mechanism, coins
        # =====================================================================

        well_bucket = StatefulItem(
            name="well bucket",
            id="well_bucket",
            description="A bucket hanging from a frayed rope over the well.",
            state="up",
            takeable=False,
            synonyms=["bucket", "rope", "pulley"],
        )
        well_bucket.set_room_id("well")
        well_bucket.add_state_description(
            "up", "A bucket hangs from a frayed rope over the well."
        )
        well_bucket.add_state_description(
            "down", "The bucket has been lowered into the well."
        )

        well_bucket.add_interaction(
            verb="lower",
            from_state="up",
            target_state="down",
            message="You lower the bucket into the dark water. When you pull it up, the water "
            "is icy cold. Among the water, you notice something glinting - a few coins "
            "from wishes long forgotten.",
        )
        well_bucket.add_interaction(
            verb="raise",
            from_state="down",
            target_state="up",
            message="You pull the bucket back up.",
        )
        self._rooms["well"].add_item(well_bucket)

        # =====================================================================
        # COTTAGE2 (Herbalist) - Remedies and hints
        # =====================================================================

        journal = Item(
            name="journal",
            id="herb_journal",
            description="A leather journal containing herbal recipes. One entry reads: "
            "'The hag at the windmill fears her true name spoken in her kitchen. "
            "They call her Morgantha, though she has not used that name in centuries.'",
            weight=1,
            value=15,
            takeable=True,
            synonyms=["leather journal", "recipe book", "herbalist journal"],
        )
        self._rooms["cottage2"].add_item(journal)

        mortar = Item(
            name="mortar",
            id="herb_mortar",
            description="A stone mortar and pestle, stained with various herbs.",
            weight=3,
            value=5,
            takeable=True,
            synonyms=["mortar and pestle", "pestle", "grinding bowl"],
        )
        self._rooms["cottage2"].add_item(mortar)

        # =====================================================================
        # WATCHTOWER - Spyglass, guard log
        # =====================================================================

        spyglass = Item(
            name="spyglass",
            id="tower_spyglass",
            description="A brass spyglass in good condition. Through it, the mist barrier "
            "seems to shimmer with strange symbols.",
            weight=1,
            value=30,
            takeable=True,
            synonyms=["brass spyglass", "telescope"],
        )
        self._rooms["watchtower"].add_item(spyglass)

        guard_log = Item(
            name="logbook",
            id="guard_log",
            description="A guard's logbook. The last entry, dated years ago, reads: "
            "'The mists grow thicker. No one has passed through in months. I fear "
            "we are truly trapped. There are rumors of a token that can part the "
            "mists, hidden somewhere in the village. I must find it before-' "
            "The entry ends abruptly.",
            weight=1,
            value=5,
            takeable=True,
            synonyms=["log", "guard book", "journal"],
        )
        self._rooms["watchtower"].add_item(guard_log)

    def spawn_mobs(self, mob_manager: Any) -> None:
        """Spawn mobs for Level 1."""

        # Village NPCs - all non-aggressive
        self.spawn_mob_in_room(mob_manager, "peasant", "square")
        self.spawn_mob_in_room(mob_manager, "barkeep", "tavern")
        self.spawn_mob_in_room(mob_manager, "priest", "church")

    def configure_npc_interactions(self, mob_manager: Any) -> None:
        """Configure NPC interactions for Level 1."""

        def find_mob_by_name(name: str) -> Any:
            for mob_id, mob in mob_manager.mobs.items():
                if mob.name.lower() == name.lower():
                    return mob
            return None

        # Priest - give bones for blessing (alternative to mist token)
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
                """Grant blessing that allows passage through mists."""
                # Mark player as blessed
                player_sid = None
                for sid, session in online_sessions.items():
                    if session.get("player") == player:
                        player_sid = sid
                        break
                if player_sid:
                    session = online_sessions.get(player_sid, {})
                    if "blessings" not in session:
                        session["blessings"] = set()
                    session["blessings"].add("morning_lord")

                    # Open the mist barrier
                    gatehouse = game_state.get_room("gatehouse")
                    if gatehouse:
                        gatehouse.exits["south"] = "road_south"

            priest.accepts_item = {
                "bones": {
                    "message": (
                        "Father Donavich gasps as you hand him the holy bones.\n\n"
                        "'The bones of St. Andral! You've found them! The church is "
                        "protected once more!'\n\n"
                        "He clasps your hands, tears streaming down his face.\n\n"
                        "'Bless you, brave soul. May the Morning Lord's light guide you. "
                        "I grant you his blessing - the mists shall not bar your way. "
                        "Go south from the gatehouse, and the darkness will part before you.'"
                    ),
                    "one_time": True,
                    "triggered": False,
                    "effect_fn": priest_blessing,
                }
            }

        # Barkeep - give coin for hints
        barkeep = find_mob_by_name("barkeep")
        if barkeep:
            barkeep.accepts_item = {
                "coin": {
                    "message": (
                        "The barkeep palms the coin and leans in conspiratorially.\n\n"
                        "'Looking to leave, are you? Can't say I blame you.'\n\n"
                        "'There's a token, they say. Hidden in a chest in MY cellar, of all "
                        "places. How it got there, I don't know. But the cellar's locked up "
                        "tight. The old burgomaster had a key - check his manor study.'\n\n"
                        "'Or if you're the religious type, Father Donavich might help. "
                        "He's been asking about some stolen bones...'"
                    ),
                    "one_time": True,
                    "triggered": False,
                }
            }
