# backend/managers/world/level_1_village.py
"""
Level 1: Village of Barovia

A safe starting area under eternal twilight. The village is quiet,
oppressed by the mists that trap all souls in this cursed valley.
NPCs here offer hints and quests. The mist barrier blocks exit south
until solved.

Rooms: ~35-40 total
Mobs: Non-aggressive NPCs (peasant, barkeep, priest)
Transition to L2: Mist barrier requires BOTH mist_token AND priest's blessing + speaking "Lathander"
"""

from typing import Any, Dict, Optional
from models.Room import Room
from models.Item import Item
from models.StatefulItem import StatefulItem
from models.ContainerItem import ContainerItem
from models.Weapon import Weapon
from models.SpecializedRooms import SwampRoom
from .level_base import LevelGenerator
from .shared_conditions import player_is_novice_or_below


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
            "Perpetual mist chokes this bleak village square. A gallows stands in "
            "the center, its rope swaying despite the still air. A cracked fountain "
            "stands dry nearby. The church lies north, the tavern east, the mercantile "
            "southwest, the manor west, and a dirt road leads south.",
            is_outdoor=True,
        )

        tavern = Room(
            "tavern",
            "Blood of the Vine Tavern",
            "The tavern's interior is dim and smoky. Scratched tables surround a "
            "cold hearth, and the village square is visible through grimy windows "
            "to the west.",
        )

        cellar = Room(
            "cellar",
            "Tavern Cellar",
            "Dusty wine barrels line the walls of this cold cellar. Strange symbols "
            "are scratched into the stone. The trapdoor leads back up to the tavern.",
            is_dark=True,
        )

        church = Room(
            "church",
            "Village Church",
            "This small stone church has seen better days. Cracked pews face a simple "
            "altar beneath what remains of stained glass. Despite the decay, something "
            "here feels safer. The square lies south, graveyard west.",
        )

        undercroft = Room(
            "undercroft",
            "Church Undercroft",
            "Holy symbols are scratched into the walls of this cramped stone chamber, "
            "some in what looks like dried blood. Scratching sounds echo from somewhere "
            "in the shadows. Stone steps lead back up to the church.",
            is_dark=True,
        )

        shop = Room(
            "shop",
            "Bildrath's Mercantile",
            "Dusty shelves hold overpriced goods in this cramped general store. A sign "
            "reads 'NO CREDIT'. The square lies northeast.",
        )

        manor = Room(
            "manor",
            "Burgomaster's Manor",
            "Once grand, this manor now shows signs of siege. Claw marks score the "
            "wooden door and dust covers everything. A blocked staircase leads nowhere. "
            "A study lies north, the square east.",
        )

        study = Room(
            "study",
            "Manor Study",
            "Books line the walls, many dealing with the history of Barovia. A desk "
            "sits by a shuttered window, an old globe beside it. A portrait of a young "
            "woman named Ireena watches from the wall. The manor's main hall lies south.",
        )

        graveyard = Room(
            "graveyard",
            "Village Graveyard",
            "Crooked headstones jut from the muddy earth. A weathered angel statue "
            "watches over them, one wing broken. Fresh flowers mark a grave labeled "
            "'Kolyan Indirovich'. An iron gate leads to a family crypt. The church "
            "stands east, a ruined shrine to the south. A fetid bog lies to the west.",
            is_outdoor=True,
        )

        crypt = Room(
            "crypt",
            "Family Crypt",
            "Stone sarcophagi line the walls with names carved into the stone - "
            "Kolyanovich, Dilisnya, Wachter. Wilted flowers lie scattered on the floor. "
            "Claw marks score the inside of the crypt door. The graveyard lies through "
            "the iron gate.",
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
            "This crumbling stone gatehouse marks the village's southern boundary. Beyond "
            "the rusted iron gates, an impenetrable mist blocks the road. Strange symbols "
            "score the gateposts. The road leads north.",
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
            "weathervane spins slowly atop the chimney. The ladder leads down to "
            "the alley.",
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
            "Bundles of dried herbs hang from the ceiling, filling the air with a "
            "pungent aroma. A workbench dominates one wall and a small cauldron hangs "
            "over a cold fire pit. The village square lies north.",
        )

        well = Room(
            "well",
            "Village Well",
            "An old stone well stands in a small courtyard. The water below reflects "
            "nothing — not even the grey sky. Paths lead to the church east and the "
            "manor south.",
            is_outdoor=True,
        )

        garden = Room(
            "garden",
            "Overgrown Garden",
            "What was once a garden is now choked with weeds. A scarecrow watches "
            "with button eyes, stuffing leaking from its chest. The manor lies south, "
            "a tool shed west.",
            is_outdoor=True,
        )

        shed = Room(
            "shed",
            "Tool Shed",
            "Rusted implements and spiderwebs fill this rickety shed. Coils of rope "
            "hang from hooks on the wall. The garden is visible through the doorway.",
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
            "left mid-work. Soot covers everything. The village square lies north.",
        )

        fountain = Room(
            "fountain",
            "Broken Fountain",
            "A cracked fountain stands dry, its central statue defaced beyond "
            "recognition. Dead leaves gather in the basin and the inscription has "
            "been scratched out. The church lies northeast.",
            is_outdoor=True,
        )

        burnt = Room(
            "burnt",
            "Burned Ruin",
            "This building burned long ago. Only charred timbers and stone foundation "
            "remain. A child's toy lies miraculously unburned among the debris. The "
            "smell of old smoke clings to everything. The road lies east, a ruined "
            "shrine to the southwest.",
            is_outdoor=True,
        )

        chapel_ruins = Room(
            "chapel_ruins",
            "Ruined Shrine",
            "A small roadside shrine, long abandoned. The idol has been smashed, "
            "leaving only fragments. Someone left fresh offerings despite the "
            "destruction - a crust of bread, a wilted flower. The graveyard lies "
            "north, a burned ruin to the northeast.",
            is_outdoor=True,
        )

        cellar_tunnel = Room(
            "cellar_tunnel",
            "Secret Tunnel",
            "Tool marks score the walls of this cramped earthen tunnel, dug in secret "
            "over many years. Roots dangle from the ceiling. The tunnel leads back to "
            "the cellar.",
            is_dark=True,
        )

        watchtower = Room(
            "watchtower",
            "Crumbling Watchtower",
            "This small watchtower once guarded the village's southern approach. The "
            "roof has collapsed and the stairs are treacherous. Stairs lead down to "
            "the gatehouse.",
        )

        # =====================================================================
        # SWAMP - Treasure drop point
        # =====================================================================

        lake = SwampRoom(
            "lake",
            "Murky Bog",
            "A fetid bog lies at the edge of the village, shrouded in thick mist. "
            "Dark water bubbles sluggishly between gnarled roots and rotting logs. "
            "The smell of decay hangs heavy in the air. Local legend says treasures "
            "dropped here are claimed by the spirits below - and rewarded. The village "
            "lies to the east.",
            treasure_destination="underlake",
            awards_points=True,
        )

        # Inaccessible room where treasure goes (no exits, players can't reach it)
        underlake = Room(
            "underlake",
            "Beneath the Bog",
            "The murky depths beneath the bog. Treasures claimed by the spirits rest "
            "here, never to be seen again by mortal eyes.",
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
            # Swamp
            "lake": lake,
            "underlake": underlake,
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
            "west": "lake",
        }

        self._rooms["crypt"].exits = {
            "out": "graveyard",
        }

        self._rooms["lake"].exits = {
            "out": "square",
            "east": "graveyard",
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
            "southwest": "chapel_ruins",
        }

        self._rooms["chapel_ruins"].exits = {
            "north": "graveyard",
            "northeast": "burnt",
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

        # rug back into place
        rug.add_interaction(
            verb="move",
            from_state="moved",
            target_state="flat",
            message="You move the rug back into place, hiding the trapdoor beneath.",
            remove_exit="down",
        )
        rug.add_interaction(
            verb="pull",
            from_state="moved",
            target_state="flat",
            message="You pull the rug back into place, hiding the trapdoor beneath.",
            remove_exit="down",
        )
        rug.add_interaction(
            verb="lower",
            from_state="moved",
            target_state="flat",
            message="You lower the edge of the rug, hiding the trapdoor beneath.",
            remove_exit="down",
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
            verb="move",
            from_state="moved",
            target_state="hanging",
            message="You swing the painting back into place, hiding the wall safe.",
        )
        painting.add_interaction(
            verb="examine",
            message="A faded oil painting depicting nobles on a hunt. It hangs slightly crooked, "
            "as if it's been moved recently. The frame seems loose.",
        )
        self._rooms["tavern"].add_item(painting)

        # Wall safe (container that can hold items)
        safe = ContainerItem(
            name="safe",
            id="tavern_safe",
            description="A small iron safe set into the wall",
            state="locked",
            takeable=False,
            capacity_limit=5,
            capacity_weight=20,
        )
        safe.synonyms = ["wall safe", "iron safe", "strongbox"]
        safe.set_room_id("tavern")

        # Clear default open/close interactions (they're for closed/open states)
        safe.interactions = {}

        # Add custom interactions for locked/open states
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
            message="The safe clicks open!",
            required_instrument="opener",
        )
        safe.add_interaction(
            verb="open",
            from_state="locked",
            message="The safe is locked tight.",
        )
        safe.add_interaction(
            verb="close",
            from_state="open",
            target_state="locked",
            message="You close the safe and it locks automatically.",
        )
        safe.add_interaction(
            verb="examine",
            message="A sturdy iron safe. The lock mechanism looks simple enough - something "
            "thin and pointed might do the trick.",
        )

        # Add contents directly to the safe container
        safe_pouch = ContainerItem(
            name="pouch",
            id="safe_pouch",
            description="A small leather pouch lies here",
            weight=1,
            value=0,
            takeable=True,
        )

        cellar_key = Item(
            name="key",
            id="cellar_key",
            description="A tarnished brass key lies here, its teeth worn smooth by age.",
            weight=0,
            value=5,
            takeable=True,
            synonyms=["old key", "brass key", "tarnished key", "cellar key"],
        )

        # Put items inside the safe
        safe.items.append(cellar_key)
        safe.items.append(safe_pouch)
        safe.update_weight()
        safe.update_description()

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

        cellar_chest = ContainerItem(
            name="chest",
            id="cellar_chest",
            description="A dusty wooden chest bound with iron bands",
            state="locked",
            takeable=False,
            capacity_limit=10,
            capacity_weight=50,
        )
        cellar_chest.synonyms = ["wooden chest", "locked chest", "dusty chest"]
        cellar_chest.set_room_id("cellar")

        # Clear default open/close interactions
        cellar_chest.interactions = {}

        # Three states: locked, closed (unlocked), open
        cellar_chest.add_state_description(
            "locked", "A dusty wooden chest sits in the corner, locked tight."
        )
        cellar_chest.add_state_description(
            "closed", "A dusty wooden chest sits in the corner, closed but unlocked."
        )
        cellar_chest.add_state_description("open", "The wooden chest stands open.")

        # Opening interactions
        cellar_chest.add_interaction(
            verb="open",
            from_state="locked",
            target_state="open",
            message="The old key turns in the lock with a satisfying click. The chest creaks open!",
            required_instrument="cellar_key",
        )
        cellar_chest.add_interaction(
            verb="open",
            from_state="locked",
            message="The chest is locked. You need a key.",
        )
        cellar_chest.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You lift the lid and the chest creaks open.",
        )

        # Unlocking interactions
        cellar_chest.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="closed",
            message="The key fits perfectly! You hear the lock click open.",
            required_instrument="cellar_key",
        )
        cellar_chest.add_interaction(
            verb="unlock",
            from_state="locked",
            message="You need a key to unlock this chest.",
        )
        cellar_chest.add_interaction(
            verb="unlock",
            from_state="closed",
            message="The chest is already unlocked.",
        )
        cellar_chest.add_interaction(
            verb="unlock",
            from_state="open",
            message="The chest is already open.",
        )

        # Closing interactions
        cellar_chest.add_interaction(
            verb="close",
            from_state="open",
            target_state="closed",
            message="You close the chest lid. It remains unlocked.",
        )
        cellar_chest.add_interaction(
            verb="close",
            from_state="open",
            target_state="locked",
            message="You close the chest and lock it with the key.",
            required_instrument="cellar_key",
        )
        cellar_chest.add_interaction(
            verb="close",
            from_state="closed",
            message="The chest is already closed.",
        )
        cellar_chest.add_interaction(
            verb="close",
            from_state="locked",
            message="The chest is already closed and locked.",
        )

        # Locking interactions
        cellar_chest.add_interaction(
            verb="lock",
            from_state="closed",
            target_state="locked",
            message="You turn the key and the chest locks with a click.",
            required_instrument="cellar_key",
        )
        cellar_chest.add_interaction(
            verb="lock",
            from_state="closed",
            message="You need a key to lock this chest.",
        )
        cellar_chest.add_interaction(
            verb="lock",
            from_state="open",
            message="You need to close the chest before you can lock it.",
        )
        cellar_chest.add_interaction(
            verb="lock",
            from_state="locked",
            message="The chest is already locked.",
        )

        # Other interactions
        cellar_chest.add_interaction(
            verb="break",
            message="The iron bands are too sturdy. You'd need a key to open this properly.",
        )
        cellar_chest.add_interaction(
            verb="examine",
            message="A sturdy wooden chest bound with iron bands. It has a keyhole on the front.",
        )

        # Add contents directly to the chest
        mist_token = Item(
            name="token",
            id="mist_token",
            description="A silver token inscribed with swirling runes that pulse "
            "with faint otherworldly light.",
            weight=0,
            value=100,
            takeable=True,
        )

        old_documents = StatefulItem(
            name="documents",
            id="old_documents",
            description="Yellow documents are deposited here, worn by time.",
            weight=0,
            value=10,
            takeable=True,
            synonyms=["papers"],
        )

        # Put items inside the chest
        cellar_chest.items.append(mist_token)
        cellar_chest.items.append(old_documents)
        cellar_chest.update_weight()
        cellar_chest.update_description()

        self._rooms["cellar"].add_item(cellar_chest)

        old_documents.add_interaction(
            verb="read",
            message="The yellowed pages describe the curse upon Barovia. One passage reads:\n"
            "'The mists that imprison us are of Strahd's making, yet even his darkness "
            "cannot stand against the Morning Lord's light. To escape, one must possess "
            "BOTH the silver token of passage AND the blessing of the faithful.'\n"
            "A marginal note in different handwriting adds: 'Hold the token before the mist "
            "and speak His true name. Not the Morning Lord - his REAL name.'",
        )

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
            verb="move",
            from_state="moved",
            target_state="blocking",
            message="You push the heavy crate back into place, blocking the tunnel entrance.",
            add_exit=("north", "cellar_tunnel"),
        )
        crate.add_interaction(
            verb="push",
            from_state="moved",
            target_state="blocking",
            message="With effort, you shove the crate back into place, blocking the tunnel entrance.",
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
            # no_removal callbacks are set in configure_npc_interactions()
            # where we have access to mob_manager to check if priest is alive
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
            description="A tallow candle lies here, ready to provide dim but steady light.",
            weight=0,
            value=2,
            takeable=True,
            emits_light=True,
        )
        self._rooms["church"].add_item(candle)

        # =====================================================================
        # UNDERCROFT - Holy bones, prayer book
        # =====================================================================

        phylactery = StatefulItem(
            name="phylactery",
            id="undercroft_phylactery",
            description="An old wooden phylactery is here.",
            state="closed",
            takeable=False,
            synonyms=["box"],
        )
        phylactery.set_room_id("undercroft")
        phylactery.add_state_description(
            "closed", "An old phylactery stands against the wall, its glass cracked."
        )
        phylactery.add_state_description(
            "open",
            "The phylactery stands open.",
        )

        phylactery.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You carefully open the cracked phylactery. Inside, wrapped in faded velvet, "
            "are the sacred bones of St. Andral! They radiate gentle warmth.",
        )
        phylactery.add_interaction(
            verb="examine",
            message="A wooden phylactery for holding sacred relics. Through the cracked glass, "
            "you can see something wrapped in velvet within.",
        )
        self._rooms["undercroft"].add_item(phylactery)

        # Bones - hidden until phylactery opened
        def phylactery_opened(game_state: Any) -> bool:
            room = game_state.get_room("undercroft")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "undercroft_phylactery":
                    return getattr(item, "state", None) == "open"
            return False

        holy_bones = Item(
            name="bones",
            id="holy_bones",
            description="The sacred bones of St. Andral lie here, wrapped in faded velvet and "
            "radiating a faint warmth.",
            weight=2,
            value=200,
            takeable=True,
            synonyms=["holy bones", "sacred bones", "st andral bones", "relics"],
        )
        self._rooms["undercroft"].add_hidden_item(holy_bones, phylactery_opened)

        prayerbook = StatefulItem(
            name="prayerbook",
            id="prayer_book",
            description="A torn prayer book lies here, its pages yellowed and worn.",
            state="default",
            weight=1,
            value=5,
            takeable=True,
            synonyms=["prayer book", "book", "torn book"],
        )
        prayerbook.add_interaction(
            verb="read",
            message="One passage is circled in faded ink: 'The Morning Lord's blessing "
            "grants safe passage through the mists of evil.'",
        )
        self._rooms["undercroft"].add_item(prayerbook)

        # =====================================================================
        # MANOR STUDY - Opener, globe, portrait clue
        # =====================================================================

        opener = Item(
            name="opener",
            id="opener",
            description="An ornate silver letter opener lies here, its point wickedly sharp.",
            weight=0,
            value=15,
            takeable=True,
        )
        self._rooms["study"].add_item(opener)

        unfinished_letter = StatefulItem(
            name="letter",
            id="unfinished_letter",
            description="A half-finished letter lies here, the ink faded with age.",
            state="default",
            weight=0,
            value=10,
            takeable=True,
            synonyms=["half-finished letter", "note", "message"],
        )

        unfinished_letter.add_interaction(
            verb="read",
            from_state="default",
            target_state="default",
            message="The letter reads: 'My dearest Ireena, if you are reading this, I am already dead. The Devil has come for us at last. Flee if you can, but know this - the tavern cellar holds a secret that may save you. The token hidden there can pierce.....' The rest of the letter is illegible.",
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
            description="A tarnished silver hand mirror lies here, its surface clouded with age.",
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

        # =====================================================================
        # GATEHOUSE - Mist barrier (level transition puzzle)
        # Requires BOTH priest's blessing AND mist token + speaking "Lathander"
        # =====================================================================

        # Helper function to check if player has the blessing
        def has_blessing(player: Any, game_state: Any) -> bool:
            """Check if player has received the Morning Lord's blessing."""
            # Find player's session
            try:
                from globals import online_sessions

                for sid, session in online_sessions.items():
                    if session.get("player") == player:
                        blessings = session.get("blessings", set())
                        return "morning_lord" in blessings
            except ImportError:
                pass
            return False

        def has_no_blessing(player: Any, game_state: Any) -> bool:
            """Check if player does NOT have the blessing."""
            return not has_blessing(player, game_state)

        def has_token(player: Any, game_state: Any) -> bool:
            """Check if player is holding the mist token."""
            for item in player.inventory:
                if getattr(item, "id", None) == "mist_token":
                    return True
            return False

        def has_blessing_and_token(player: Any, game_state: Any) -> bool:
            """Check if player has BOTH blessing and token."""
            return has_blessing(player, game_state) and has_token(player, game_state)

        def has_token_but_no_blessing(player: Any, game_state: Any) -> bool:
            """Check if player has token but NOT blessing."""
            return has_token(player, game_state) and not has_blessing(
                player, game_state
            )

        def has_blessing_but_no_token(player: Any, game_state: Any) -> bool:
            """Check if player has blessing but NOT token."""
            return has_blessing(player, game_state) and not has_token(
                player, game_state
            )

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
            "then recoil as if sensing something. There must be a way through...",
        )
        mist_barrier.add_state_description(
            "parted",
            "The mist has parted, revealing the road south into the Svalich Woods.",
        )

        # === Using token directly (doesn't work - need to speak the word) ===
        mist_barrier.add_interaction(
            verb="use",
            from_state="blocking",
            message="The token flickers as you hold it toward the mist, but nothing happens. "
            "Perhaps speaking a word of power while holding it would help... something "
            "related to the god of light?",
            required_instrument="mist_token",
        )

        # === Entering without preparation ===
        mist_barrier.add_interaction(
            verb="enter",
            from_state="blocking",
            message="You step into the mist. Cold fingers grasp at you, turning you around. "
            "No matter which way you push, you end up back at the gatehouse. "
            "This darkness requires both divine blessing and an artifact of passage.",
        )

        mist_barrier.add_interaction(
            verb="examine",
            message="The mist is unnaturally thick and dark - Strahd's curse made manifest. "
            "It almost seems alive, watching you hungrily.\n"
            "Faded runes on the gateposts read: 'By the Morning Lord's name, the darkness "
            "parts. Token and blessing together light the way.'\n"
            "You'll need the priest's blessing AND a token of passage to escape Barovia.",
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
            required_instrument="shop_torch",
        )
        self._rooms["gatehouse"].add_item(torch_bracket)

        # === SPEECH TRIGGERS FOR MIST BARRIER ===
        # Speaking "Lathander" with both blessing and token parts the mists

        def mists_already_parted(player: Any, game_state: Any) -> bool:
            """Check if the mists have already been parted."""
            gatehouse_room = game_state.get_room("gatehouse")
            if gatehouse_room:
                for item in gatehouse_room.items:
                    if hasattr(item, "id") and item.id == "mist_barrier":
                        return getattr(item, "state", None) == "parted"
            return False

        async def part_the_mists(
            player: Any,
            game_state: Any,
            player_manager: Any,
            online_sessions: Any,
            sio: Any,
            utils: Any,
        ) -> None:
            """Part the mists and open the way south."""
            # Open the exit
            gatehouse_room = game_state.get_room("gatehouse")
            if gatehouse_room and "south" not in gatehouse_room.exits:
                gatehouse_room.exits["south"] = "road_south"

            # Update mist barrier state
            for item in gatehouse_room.items:
                if hasattr(item, "id") and item.id == "mist_barrier":
                    item.state = "parted"
                    if hasattr(item, "state_descriptions"):
                        item.description = item.state_descriptions.get(
                            "parted", item.description
                        )
                    break

            # Award points (add_points handles notification automatically)
            player.add_points(200, sio, online_sessions)
            player_manager.save_players()

        # Already parted: Check this first
        self._rooms["gatehouse"].add_speech_trigger(
            keyword="lathander",
            message="The Morning Lord's name echoes through the parted mists.\n"
            "The way south already lies open before you.",
            conditional_fn=mists_already_parted,
            one_time=False,
        )

        # Success: Has both blessing and token
        self._rooms["gatehouse"].add_speech_trigger(
            keyword="lathander",
            message="You raise the mist token high and cry out: 'LATHANDER!'\n"
            "The token blazes with golden light! The Morning Lord's blessing flows "
            "through you, channeling divine power into the artifact!\n"
            "The mists SHRIEK as they're torn asunder, parting before you like a "
            "curtain of shadow fleeing the dawn!\n"
            "The way south to the Svalich Woods lies open!",
            effect_fn=part_the_mists,
            conditional_fn=has_blessing_and_token,
            one_time=True,
        )

        # Partial: Has token but no blessing
        self._rooms["gatehouse"].add_speech_trigger(
            keyword="lathander",
            message="You hold up the token and speak the sacred name: 'Lathander!'\n"
            "The token flickers weakly, but the mists remain unmoved.\n"
            "You feel the word should have power, but something is missing... "
            "Perhaps you need the Morning Lord's blessing to truly invoke his name?",
            conditional_fn=has_token_but_no_blessing,
            one_time=False,
        )

        # Partial: Has blessing but no token
        self._rooms["gatehouse"].add_speech_trigger(
            keyword="lathander",
            message="As you speak the Morning Lord's true name, warmth fills your heart - "
            "the priest's blessing responds! But the divine power has no focus...\n"
            "You need the mist token to channel the light against this darkness.",
            conditional_fn=has_blessing_but_no_token,
            one_time=False,
        )

        # Failure: Has neither
        self._rooms["gatehouse"].add_speech_trigger(
            keyword="lathander",
            message="You speak the name 'Lathander' but your words are hollow, "
            "swallowed by the hungry mist.\n"
            "Without the priest's blessing and the token of passage, "
            "the sacred name holds no power here.",
            one_time=False,
        )

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
            message="Most notices are illegible, but one stands out:\n"
            "'WANTED: News of the Holy Bones of St. Andral. The church offers blessing "
            "to any who return them to Father Donavich.'\n"
            "Another reads: 'BEWARE THE MISTS - None who enter return.'",
        )
        notice_board.add_interaction(
            verb="examine",
            message="A wooden board covered in yellowed papers. Most are rotted or illegible, "
            "but a few notices remain readable.",
        )
        self._rooms["square"].add_item(notice_board)

        # =====================================================================
        # CRYPT - Coffin with skeleton guardian
        # =====================================================================

        # Track whether skeleton has been spawned
        coffin_opened_once = {"spawned": False}

        def spawn_skeleton_guardian(player: Any, game_state: Any) -> Optional[str]:
            """Spawn a skeleton when the coffin is opened for the first time."""
            if coffin_opened_once["spawned"]:
                return None

            coffin_opened_once["spawned"] = True

            # Get mob_manager from utils module (runtime attached)
            import utils as utils_module

            mob_manager = getattr(utils_module, "mob_manager", None)
            if not mob_manager:
                return None

            # Spawn skeleton in the crypt
            mob_manager.spawn_mob("skeleton", "crypt", game_state)

            return (
                "As the lid grinds open, the skeletal remains suddenly lurch upright! "
                "Empty eye sockets blaze with unholy light as it rises from its resting "
                "place, ancient bones rattling with malevolent purpose!"
            )

        crypt_coffin = StatefulItem(
            name="coffin",
            id="crypt_coffin",
            description="A stone coffin with a heavy lid.",
            state="closed",
            takeable=False,
            synonyms=["stone coffin", "sarcophagus"],
        )
        crypt_coffin.set_room_id("crypt")
        crypt_coffin.add_state_description(
            "closed",
            "A stone coffin dominates the chamber, its heavy lid firmly in place.",
        )
        crypt_coffin.add_state_description(
            "open",
            "The stone coffin stands open, its lid pushed aside.",
        )
        crypt_coffin.add_interaction(
            verb="open",
            target_state="open",
            message="You push the heavy stone lid aside with a grinding sound.",
            from_state="closed",
            effect_fn=spawn_skeleton_guardian,
        )
        crypt_coffin.add_interaction(
            verb="close",
            target_state="closed",
            message="You slide the heavy lid back into place.",
            from_state="open",
        )
        crypt_coffin.add_interaction(
            verb="examine",
            from_state="closed",
            message="The coffin is carved from a single block of stone. Strange symbols "
            "are etched around its edges. The lid looks heavy but movable.",
        )
        crypt_coffin.add_interaction(
            verb="examine",
            from_state="open",
            message="The coffin is empty now, save for dust and ancient cobwebs.",
        )
        self._rooms["crypt"].add_item(crypt_coffin)

        # =====================================================================
        # GRAVEYARD - Angel statue, flowers
        # =====================================================================

        angel_statue = StatefulItem(
            name="statue",
            id="graveyard_statue",
            description="A weathered angel statue with one wing broken is watching over the graves.",
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
            "feel a warmth in your chest, a sense of peace. The angel's blessing fills you "
            "with renewed strength.",
            conditional_fn=player_is_novice_or_below,
            points_awarded=5,
        )
        angel_statue.add_interaction(
            verb="pray",
            message="You kneel before the angel and offer a silent prayer. For a moment, you "
            "feel a warmth in your chest, a sense of peace. The angel watches over you, "
            "but you sense its blessing is meant for those still finding their way.",
        )
        self._rooms["graveyard"].add_item(angel_statue)

        # =====================================================================
        # SHOP - Display case, supplies
        # =====================================================================

        # Condition functions for display case
        def bildrath_is_alive(player: Any, game_state: Any) -> bool:
            """Check if Bildrath is alive in the shop."""
            mob_manager = getattr(game_state, "_mob_manager", None)
            if not mob_manager:
                # Try to get it from the utils module (runtime attached)
                import utils as utils_module

                mob_manager = getattr(utils_module, "mob_manager", None)
            if mob_manager:
                for mob in mob_manager.get_mobs_in_room("shop"):
                    if mob.name.lower() == "bildrath":
                        return True
            return False

        def bildrath_is_dead(player: Any, game_state: Any) -> bool:
            """Check if Bildrath is dead (not in shop)."""
            return not bildrath_is_alive(player, game_state)

        display_case = ContainerItem(
            name="case",
            id="shop_case",
            description="A locked display case containing valuable items",
            state="locked",
            takeable=False,
            capacity_limit=10,
            capacity_weight=30,
        )
        display_case.synonyms = ["display case", "glass case", "locked case"]
        display_case.set_room_id("shop")

        # Clear default open/close interactions
        display_case.interactions = {}

        # Three states: locked, closed (unlocked), open
        display_case.add_state_description(
            "locked", "A locked display case contains valuable items."
        )
        display_case.add_state_description(
            "closed", "The display case is closed but unlocked."
        )
        display_case.add_state_description("open", "The display case stands open.")

        # === OPENING INTERACTIONS ===
        # If Bildrath is alive, he blocks opening
        display_case.add_interaction(
            verb="open",
            from_state="locked",
            message="Bildrath snarls at you. 'Touch that case and I'll have your hands! "
            "That's not for browsing - gold first, then you can look!'",
            conditional_fn=bildrath_is_alive,
        )
        # If Bildrath is dead, you can open it with a key
        display_case.add_interaction(
            verb="open",
            from_state="locked",
            target_state="open",
            message="With Bildrath out of the way, you use the key to unlock the display case. "
            "The glass door swings open!",
            required_instrument="cellar_key",
            conditional_fn=bildrath_is_dead,
        )
        # If Bildrath is dead but no key
        display_case.add_interaction(
            verb="open",
            from_state="locked",
            message="The display case is locked. You'll need a key to open it.",
            conditional_fn=bildrath_is_dead,
        )
        # Open from closed (unlocked) state
        display_case.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the display case.",
        )

        # === UNLOCKING INTERACTIONS ===
        display_case.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="closed",
            message="With Bildrath out of the way, you use the key to unlock the display case.",
            required_instrument="cellar_key",
            conditional_fn=bildrath_is_dead,
        )
        display_case.add_interaction(
            verb="unlock",
            from_state="locked",
            message="Bildrath snarls at you. 'Touch that case and I'll have your hands! "
            "That's not for browsing - gold first, then you can look!'",
            conditional_fn=bildrath_is_alive,
        )
        display_case.add_interaction(
            verb="unlock",
            from_state="locked",
            message="The display case is locked. You'll need a key.",
            conditional_fn=bildrath_is_dead,
        )
        display_case.add_interaction(
            verb="unlock",
            from_state="closed",
            message="The display case is already unlocked.",
        )
        display_case.add_interaction(
            verb="unlock",
            from_state="open",
            message="The display case is already open.",
        )

        # === CLOSING INTERACTIONS ===
        display_case.add_interaction(
            verb="close",
            from_state="open",
            target_state="closed",
            message="You close the display case. It remains unlocked.",
        )
        display_case.add_interaction(
            verb="close",
            from_state="open",
            target_state="locked",
            message="You close the display case and lock it with the key.",
            required_instrument="cellar_key",
        )
        display_case.add_interaction(
            verb="close",
            from_state="closed",
            message="The display case is already closed.",
        )
        display_case.add_interaction(
            verb="close",
            from_state="locked",
            message="The display case is already closed and locked.",
        )

        # === LOCKING INTERACTIONS ===
        display_case.add_interaction(
            verb="lock",
            from_state="closed",
            target_state="locked",
            message="You turn the key and the display case locks with a click.",
            required_instrument="cellar_key",
        )
        display_case.add_interaction(
            verb="lock",
            from_state="closed",
            message="You need a key to lock the display case.",
        )
        display_case.add_interaction(
            verb="lock",
            from_state="open",
            message="You need to close the display case before you can lock it.",
        )
        display_case.add_interaction(
            verb="lock",
            from_state="locked",
            message="The display case is already locked.",
        )

        # === OTHER INTERACTIONS ===
        display_case.add_interaction(
            verb="examine",
            message="Through the glass, you can see a silver shiv, an elixir, "
            "and what looks like a lantern that never goes out. All absurdly expensive, "
            "no doubt.",
        )
        display_case.add_interaction(
            verb="break",
            message="The glass is surprisingly thick. Bildrath must have paid extra "
            "for reinforced glass.",
        )

        # Add contents directly to the display case
        shiv = Weapon(
            name="shiv",
            id="silver_shiv",
            description="A finely crafted silver shiv, its blade intricately engraved.",
            weight=1,
            value=75,
            takeable=True,
            damage=6,
            min_level="Neophyte",
            min_strength=0,
            min_dexterity=8,
        )

        elixir = Item(
            name="elixir",
            id="healing_elixir",
            description="A small vial of red liquid, promising restored health.",
            weight=1,
            value=50,
            takeable=True,
        )

        lantern = Item(
            name="lantern",
            id="everburning_lantern",
            description="A magical lantern, its flame burning eternally.",
            weight=1,
            value=100,
            takeable=True,
            emits_light=True,
        )

        # Put items inside the display case
        display_case.items.append(shiv)
        display_case.items.append(elixir)
        display_case.items.append(lantern)
        display_case.update_weight()
        display_case.update_description()

        self._rooms["shop"].add_item(display_case)

        # Basic supplies
        torch = Item(
            name="torch",
            id="shop_torch",
            description="A wooden torch lies here, wrapped in oil-soaked rags.",
            weight=1,
            value=10,  # Overpriced
            takeable=True,
            emits_light=True,
        )
        self._rooms["shop"].add_item(torch)

        rope = Item(
            name="rope",
            id="shop_rope",
            description="A coil of sturdy hemp rope lies here.",
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
            description="A heavy woodcutter's axe lies here, its blade still sharp despite its age.",
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
            description="A crude brass telescope lies here, dented and scratched.",
            state="default",
            takeable=True,
            weight=2,
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
        well_bucket.add_state_description(
            "raised_treasure",
            "The bucket hangs above the well, dripping water.",
        )
        well_bucket.add_state_description(
            "down_second", "The bucket has been lowered into the well again."
        )

        # First lowering
        well_bucket.add_interaction(
            verb="lower",
            from_state="up",
            target_state="down",
            message="You lower the bucket into the dark water. It disappears into the inky depths.",
        )
        # First raising - reveals treasure
        well_bucket.add_interaction(
            verb="raise",
            from_state="down",
            target_state="raised_treasure",
            message="You pull the bucket back up. The water is icy cold. Among the water, "
            "you notice something glinting - a few coins from wishes long forgotten!",
        )
        # Second lowering (after treasure revealed)
        well_bucket.add_interaction(
            verb="lower",
            from_state="raised_treasure",
            target_state="down_second",
            message="You lower the bucket into the well again, hoping for more treasure...",
        )
        # Second raising - SPIDER DEATH TRAP!
        well_bucket.add_interaction(
            verb="raise",
            from_state="down_second",
            target_state="raised_treasure",  # Won't actually reach this state
            message="As you pull the bucket up, a massive black spider clings to the rope! "
            "Before you can react, it lunges and sinks its fangs into your arm. "
            "Icy venom floods through your veins. The world goes dark...",
            kills_player=True,
        )
        self._rooms["well"].add_item(well_bucket)

        # Coins become visible after raising the bucket with treasure
        def bucket_has_treasure(game_state: Any) -> bool:
            room = game_state.get_room("well")
            if not room:
                return False
            for item in room.items:
                if getattr(item, "id", None) == "well_bucket":
                    return getattr(item, "state", None) == "raised_treasure"
            return False

        well_coins = Item(
            name="coins",
            id="well_coins",
            description="A handful of tarnished copper and silver coins lie here, old wishes "
            "long forgotten.",
            weight=1,
            value=15,
            takeable=True,
            synonyms=["coin", "copper coins", "silver coins", "wish coins"],
        )
        self._rooms["well"].add_hidden_item(well_coins, bucket_has_treasure)

        # =====================================================================
        # COTTAGE2 (Herbalist) - Remedies and hints
        # =====================================================================

        journal = StatefulItem(
            name="journal",
            id="herb_journal",
            description="A leather journal lies here, filled with herbal recipes and notes.",
            state="default",
            weight=1,
            value=15,
            takeable=True,
            synonyms=["leather journal", "recipe book", "herbalist journal"],
        )
        journal.add_interaction(
            verb="read",
            message="Most entries detail herbal remedies, but one passage catches your eye: "
            "'The hag at the windmill fears her true name spoken in her kitchen. "
            "They call her Morgantha, though she has not used that name in centuries.'",
        )
        self._rooms["cottage2"].add_item(journal)

        mortar = Item(
            name="mortar",
            id="herb_mortar",
            description="A stone mortar and pestle sits here, stained with various herbs.",
            weight=3,
            value=5,
            takeable=True,
            synonyms=["mortar and pestle", "pestle", "grinding bowl"],
        )
        self._rooms["cottage2"].add_item(mortar)

        # =====================================================================
        # WATCHTOWER - Spyglass, guard log
        # =====================================================================

        guard_log = StatefulItem(
            name="logbook",
            id="guard_log",
            description="A guard's logbook lies here, its last entry dated years ago.",
            state="default",
            weight=1,
            value=5,
            takeable=True,
            synonyms=["log", "guard book", "journal"],
        )
        guard_log.add_interaction(
            verb="read",
            message="The last entry reads: 'The mists grow thicker. No one has passed "
            "through in months. I fear we are truly trapped. There are rumors of a "
            "token that can part the mists, hidden somewhere in the village. I must "
            "find it before—' The entry ends abruptly.",
        )
        self._rooms["watchtower"].add_item(guard_log)

    def spawn_mobs(self, mob_manager: Any) -> None:
        """Spawn mobs for Level 1."""

        # Village NPCs - all non-aggressive
        self.spawn_mob_in_room(mob_manager, "peasant", "square")
        self.spawn_mob_in_room(mob_manager, "barkeep", "tavern")
        self.spawn_mob_in_room(mob_manager, "priest", "church")
        self.spawn_mob_in_room(mob_manager, "bildrath", "shop")

    def configure_npc_interactions(self, mob_manager: Any) -> None:
        """Configure NPC interactions for Level 1."""

        def find_mob_by_name(name: str) -> Any:
            for mob_id, mob in mob_manager.mobs.items():
                if mob.name.lower() == name.lower():
                    return mob
            return None

        # Peasant - give coins for hints
        peasant = find_mob_by_name("peasant")
        if peasant:

            async def peasant_gives_hint(
                player: Any,
                game_state: Any,
                player_manager: Any,
                online_sessions: Any,
                sio: Any,
                utils: Any,
            ) -> None:
                """Give coins for hints."""
                player.add_points(10)
                # Remove the peasant from the room
                mob_manager.remove_mob(peasant.id, game_state)

            peasant.accepts_item = {
                "coin": {
                    "message": "The peasant palms the coin and leans in conspiratorially. 'Looking to leave, are you? Can't say I blame you.' The peasant then disappears in a puff of smoke.",
                    "one_time": True,
                    "triggered": False,
                    "effect_fn": peasant_gives_hint,
                },
            }

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
                    # Blessing granted - but player still needs token and keyword!

            priest.accepts_item = {
                "bones": {
                    "message": (
                        "Father Donavich gasps as you hand him the holy bones.\n"
                        "'The bones of St. Andral! You've found them! The church is "
                        "protected once more!'\n"
                        "He clasps your hands, tears streaming down his face.\n"
                        "'Bless you, brave soul. I grant you the Morning Lord's blessing!'\n"
                        "Warmth flows through you as divine light briefly surrounds you.\n"
                        "'To escape these mists, you'll need more than my blessing alone. "
                        "Seek the token of passage, and when you stand before the mist, "
                        "hold it high and speak His true name - Lathander. "
                        "Together, blessing and token will part the darkness.'"
                    ),
                    "one_time": True,
                    "triggered": False,
                    "effect_fn": priest_blessing,
                }
            }

        # Donation box - dynamic no_removal based on priest being alive
        # and grants blessing when bones are placed in it
        church = self._rooms.get("church")
        donation_box = None
        if church:
            for item in church.items:
                if getattr(item, "id", None) == "donation_box":
                    donation_box = item
                    break

        if donation_box:
            # Track if blessing already granted via donation box
            donation_blessing_granted = {"value": False}

            def check_priest_alive(game_state: Any) -> tuple[bool, str | None]:
                """Check if priest is alive - if so, block removal."""
                # Find priest in church
                for mob in mob_manager.get_mobs_in_room("church"):
                    if mob.name.lower() == "priest":
                        # Priest is alive (dead mobs excluded from get_mobs_in_room)
                        return (
                            True,
                            "The priest glares at you sternly. "
                            "'Those offerings belong to the Morning Lord, "
                            "not to your pockets!'",
                        )
                # Priest is dead or not present
                return (False, None)

            def on_bones_donated(
                game_state: Any, container: Any, item: Any
            ) -> str | None:
                """Grant blessing when bones are placed in donation box."""
                if item.id != "holy_bones" and "bone" not in item.name.lower():
                    return None

                # Only grant once
                if donation_blessing_granted["value"]:
                    return None
                donation_blessing_granted["value"] = True

                # Grant the blessing to the player (need to find their session)
                try:
                    from globals import online_sessions

                    for sid, session in online_sessions.items():
                        # Find all players in church and grant blessing
                        player = session.get("player")
                        if player and player.current_room == "church":
                            if "blessings" not in session:
                                session["blessings"] = set()
                            session["blessings"].add("morning_lord")
                except ImportError:
                    pass

                # Check if priest is alive for appropriate message
                priest_alive = False
                for mob in mob_manager.get_mobs_in_room("church"):
                    if mob.name.lower() == "priest":
                        priest_alive = True
                        break

                if priest_alive:
                    return (
                        "\nFather Donavich sees the bones and gasps.\n"
                        "'The bones of St. Andral! The church is protected once more!'\n"
                        "He makes the sign of the Morning Lord over you.\n"
                        "'I grant you his blessing! But to escape the mists, you'll need "
                        "the token of passage as well. Hold it before the mist and speak "
                        "the Morning Lord's true name - Lathander!'"
                    )
                else:
                    return (
                        "\nAs the holy bones settle into the donation box, "
                        "a warm light briefly fills the church.\n"
                        "Though the priest is gone, St. Andral's blessing flows through you.\n"
                        "Ancient words echo in your mind: 'Token and blessing together... "
                        "speak the name of light before the darkness...'"
                    )

            donation_box.no_removal_condition = check_priest_alive
            donation_box.on_item_added = on_bones_donated

        # Barkeep - give coin for hints
        barkeep = find_mob_by_name("barkeep")
        if barkeep:
            barkeep.accepts_item = {
                "coin": {
                    "message": (
                        "The barkeep palms the coin and leans in conspiratorially.\n"
                        "'Looking to leave, are you? Can't say I blame you.'\n"
                        "'The mists won't let you go easy. You'll need TWO things: "
                        "a silver token hidden in MY cellar - locked up tight, old burgomaster "
                        "had the key, check his study in the manor - AND the priest's blessing.'\n"
                        "'Father Donavich's been distracted lately, muttering about stolen bones. "
                        "Help him with that, he might bless you.'\n"
                        "'Once you have both, go to the gatehouse. Hold up the token and... "
                        'speak the god\'s name, I think? Not "Morning Lord" - his REAL name. '
                        "Something with an L...'"
                    ),
                    "one_time": True,
                    "triggered": False,
                }
            }
