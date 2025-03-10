# backend/managers/village_generator.py

from models.Room import Room
from models.Item import Item
from models.StatefulItem import StatefulItem
from models.ContainerItem import ContainerItem

def generate_village_of_chronos():
    """
    Generates the Village of Chronos, the default starting area.
    Returns a dictionary mapping room_id to Room objects.
    """
    rooms = {}
    
    # Create all rooms
    generate_rooms(rooms)
    
    # Connect rooms with exits
    connect_exits(rooms)
    
    # Add stateful items to rooms
    add_stateful_items(rooms)
    
    # Add regular items to rooms
    add_regular_items(rooms)

    # Add container items
    add_container_items(rooms)
    
    return rooms

def generate_rooms(rooms):
    """Generate all the rooms for the village."""
    
    # Village Center
    spawn = Room(
        "spawn",
        "Village Center",
        "The heart of Chronos Village pulses with subtle energy. Cobblestone paths radiate in all directions. "
        "A weathered sundial stands in the center, its shadow perpetually fixed despite the passing of day and night. "
        "The air feels charged, as if time itself hesitates here. Villagers move about with practiced routine, "
        "unaware they've lived this same moment countless times before. Paths lead to various village structures."
    )
    
    # Elder's Cottage - exterior and interior
    elders_cottage = Room(
        "elders_cottage",
        "Outside Elder's Cottage",
        "A quaint cottage of weathered stone stands before you. Herbs hang in bunches beside the entrance, and "
        "wind chimes crafted from bones and crystal tinkle softly. Smoke curls from the chimney, carrying the scent "
        "of strange incense. Through a window, you glimpse the stooped figure of the village Elder moving about inside. "
        "The village center lies to the east, while a small garden path circles behind the cottage to the north."
    )
    
    cottage_interior = Room(
        "cottage_interior",
        "Inside Elder's Cottage",
        "The interior is larger than it appeared from outside. The air smells of herbs and old parchment. "
        "The Elder Chronister, a woman whose age seems impossible to determine, sits by a hearth that "
        "flickers with blue-white flames. Time-worn books and curious instruments line the shelves, and a large "
        "mechanical model of celestial bodies hangs from the ceiling, rotating without any obvious mechanism. "
        "A narrow staircase in the corner leads upward."
    )
    
    cottage_upstairs = Room(
        "cottage_upstairs",
        "Cottage Upper Floor",
        "This upper floor serves as the Elder's observatory and private study. A large circular window "
        "faces the night sky, regardless of the time of day outside. Star charts and temporal diagrams cover the walls, "
        "many marked with notes in a script that seems to change as you look at it. A desk cluttered with scrolls "
        "sits beneath the window, and a comfortable-looking bed occupies one corner."
    )
    
    cottage_cellar = Room(
        "cottage_cellar",
        "Hidden Cellar",
        "A cool, dry cellar extends beneath the cottage. Unlike the wooden construction above, "
        "these walls are ancient stone that predates the village itself. Shelves line the walls, holding bottles of "
        "strangely luminescent liquids and jars containing preserved specimens from beyond this reality. "
        "At the far end, a tunnel leads off to the north, its purpose and destination unclear."
    )
    
    cottage_garden = Room(
        "cottage_garden",
        "Herb Garden",
        "Behind the Elder's cottage lies a circular garden of impeccably maintained herbs and flowers, many of which "
        "don't seem native to this world. The plants grow in concentric rings around a small reflecting pool, their "
        "colors and scents shifting subtly. Some appear to bloom and wither in moments, while others remain "
        "frozen in perfect bloom. A stone bench provides a place for contemplation."
    )
    
    # Marketplace area
    marketplace = Room(
        "marketplace",
        "Village Marketplace",
        "Wooden stalls arranged in a semicircle host merchants who call out their wares in practiced cadence. "
        "Oddly, many of the same items appear day after day despite being sold. The smell of fresh bread and "
        "exotic spices fills the air. To the west lies the village center, while north stands the imposing "
        "Mystic's Tower. A narrow alley leads east toward the edge of the village, where mist rises from the "
        "Whispering Swamp."
    )
    
    curiosity_shop = Room(
        "curiosity_shop",
        "Curiosity Shop",
        "This space expands impossibly once you enter, revealing a cluttered shop filled with artifacts from "
        "across multiple realities. The proprietor, an ageless figure with kaleidoscope eyes, nods in greeting. "
        "Shelves bend with the weight of strange items. Time feels peculiar here - sometimes speeding up, "
        "sometimes slowing to a crawl. The exit back to the marketplace seems both close and impossibly distant."
    )
    
    # Mystic's Tower complex
    mystics_tower = Room(
        "mystics_tower",
        "Mystic's Tower Base",
        "A spiral tower of pale stone reaches skyward, occasionally shimmering as if not fully anchored in reality. "
        "The tower's shadow behaves strangely, sometimes pointing opposite the sun or splitting into multiple silhouettes. "
        "From inside, you hear the synchronized ticking of countless clocks. The marketplace bustles to the south, "
        "while a winding path leads west into the forest."
    )
    
    tower_interior = Room(
        "tower_interior",
        "Tower Main Chamber",
        "Inside, pendulum clocks line the walls, each showing a different time, their ticking strangely synchronized. "
        "Crystals hang from the ceiling, refracting light in impossible patterns. A circular staircase wraps around "
        "a central column inscribed with mathematical formulae and arcane symbols. Across the chamber lies a workshop "
        "filled with half-finished temporal instruments."
    )
    
    tower_workshop = Room(
        "tower_workshop",
        "Clockwork Workshop",
        "This circular room branches off from the main chamber, filled with workbenches covered in gears, "
        "springs, and crystalline components. Half-assembled devices tick and whir, measuring unknown forces. "
        "Blueprints on the walls depict machines that could never function in normal physics. Through a round window, "
        "you see the village from an angle that shouldn't be possible from this position."
    )
    
    tower_upper = Room(
        "tower_upper",
        "Upper Observatory",
        "This chamber near the tower's peak has walls transparent from the inside, offering panoramic views of the village "
        "and lands beyond - though sometimes showing what might be rather than what is. A massive telescope points "
        "toward the stars, even in daylight. Star charts hover in mid-air, rearranging themselves as you watch."
    )
    
    tower_top = Room(
        "tower_top",
        "Tower Summit",
        "The highest room offers breathtaking views in all directions. The floor is a glass mosaic depicting "
        "the convergence of multiple timelines into the single point that is Chronos Village. At the center stands a "
        "pedestal holding a slowly rotating crystal. The air is charged with possibility, and occasionally your vision "
        "splits, showing multiple versions of the same view."
    )
    
    tower_basement = Room(
        "tower_basement",
        "Tower Underchamber",
        "This spherical chamber beneath the tower has walls covered in softly glowing runes that pulse in rhythm "
        "with the ticking clocks above. The floor is a perfect mirror, reflecting not the ceiling but a star-filled void. "
        "In the center, a complex mechanical device maps the flow of time throughout the village. A narrow tunnel leads north."
    )
    
    # Library area
    ancient_library = Room(
        "ancient_library",
        "Ancient Library Entrance",
        "A building of pale stone stands before you, its architecture unlike the rest of the village. Wide steps lead up "
        "to massive bronze doors. Golden light spills out from inside along with the distinctive scent of old books. "
        "The well courtyard lies to the north, while a small reading garden is visible to the east."
    )
    
    library_main = Room(
        "library_main",
        "Grand Archive",
        "Towering bookshelves filled with leather-bound tomes reach up to vaulted ceilings. Some books appear partially "
        "transparent, while others shift position when not directly observed. In the center sits a massive circular "
        "table with an inlaid map of what might be Chronos, showing more paths and structures than currently exist. "
        "Archways lead to specialized reading rooms, while a spiral staircase connects to other levels."
    )
    
    library_reading = Room(
        "library_reading",
        "Reading Room",
        "A peaceful circular chamber branches off from the Grand Archive, furnished with comfortable chairs and reading "
        "desks. Soft, sourceless light provides perfect illumination. Occasionally, transparent scholars appear, engaged "
        "in silent discussion before fading away. Windows look out onto the reading garden, though the angle seems "
        "impossible given the room's location."
    )
    
    reading_garden = Room(
        "reading_garden",
        "Library Gardens",
        "A tranquil garden surrounds the eastern side of the library, designed for outdoor reading and contemplation. "
        "Stone benches sit among flowering plants that bloom regardless of season. A small fountain at the center "
        "produces a soothing backdrop, its water occasionally flowing upward before resuming its normal course. "
        "Several forgotten tomes rest on the benches."
    )
    
    library_mezzanine = Room(
        "library_mezzanine",
        "Library Mezzanine",
        "A balcony level overlooks the Grand Archive below. This level houses rarer volumes in glass cases that occasionally "
        "become transparent, allowing glimpses of the knowledge within. A series of reading desks are positioned near "
        "the railing, each equipped with magnifying glasses and translation codices."
    )
    
    library_astronomy = Room(
        "library_astronomy",
        "Astronomy Section",
        "The highest level of the library is dedicated to astronomical knowledge. The ceiling is an enchanted "
        "glass dome showing the night sky regardless of the time of day. Star charts and telescopes are arranged "
        "around the circular room. In the center, a complex orrery depicts not just this world's solar system "
        "but several others as well, all in constant motion."
    )
    
    library_basement = Room(
        "library_basement",
        "Forbidden Archives",
        "The most dangerous knowledge is kept in this shadowy basement. The air is noticeably cooler here, and the silence deeper. "
        "Books are chained to shelves, some visibly straining against their bindings. Warning signs in multiple languages "
        "caution against reading certain tomes aloud. At the far end, a narrow tunnel leads northward, partially hidden "
        "behind a bookshelf."
    )
    
    # Well and underground areas
    old_well = Room(
        "old_well",
        "The Old Well Courtyard",
        "A stone well stands in a small courtyard surrounded by cobblestone paths. The ground around it is always damp "
        "despite no evidence of spills. Villagers hurry past, avoiding eye contact with the well from which whispers "
        "occasionally emerge - voices that speak of events yet to happen. Paths lead to the village center north, "
        "the library south, and the forgotten shrine east."
    )
    
    well_bottom = Room(
        "well_bottom",
        "Bottom of the Well",
        "This surprisingly dry chamber lies at the bottom of the ancient well shaft. Glowing moss provides dim illumination, "
        "revealing carefully laid stonework far older than the village above. The walls bear inscriptions predicting events "
        "in the village's future and recording its past. Water seeps from small cracks, flowing upward against gravity. "
        "A narrow tunnel leads eastward into darkness."
    )
    
    underground_junction = Room(
        "underground_junction",
        "Underground Passage Junction",
        "Several rough-hewn tunnels converge in this spacious underground chamber. Glowing crystals embedded in the walls "
        "provide soft illumination, revealing ancient support pillars carved with scenes from the village's founding. "
        "The floor is worn smooth by centuries of passage. A small underground stream bubbles from a crack in the floor, "
        "flows across the chamber, and disappears into another crevice."
    )
    
    # Shrine area
    forgotten_shrine = Room(
        "forgotten_shrine",
        "Forgotten Shrine Entrance",
        "Half-buried in the earth lies an ancient shrine predating the village itself. Stone steps descend into "
        "a semicircular courtyard surrounded by weathered columns. Vines with luminescent flowers crawl across the "
        "stonework, and the air hums with residual magic. From deep within comes a soft, rhythmic pulse, like the "
        "heartbeat of time itself."
    )
    
    shrine_interior = Room(
        "shrine_interior",
        "Shrine Inner Sanctum",
        "The heart of the ancient shrine is a circular chamber dominated by a central altar with seven different-colored "
        "indentations forming a circle. The air hums with powerful magic, and time seems to slow in this sacred space. "
        "At the back stands a weathered statue of a hooded figure with outstretched hands. A narrow staircase spirals "
        "downward along the wall."
    )
    
    shrine_underground = Room(
        "shrine_underground",
        "Ritual Chamber",
        "A perfectly circular chamber extends beneath the shrine. The walls are mirror-smooth obsidian reflecting "
        "distorted images of yourself, sometimes showing alternate versions. In the center is a circular pool of "
        "silvery liquid that occasionally ripples without cause. Seven pedestals surround the pool, each aligned with "
        "one of the indentations on the altar above."
    )
    
    # Forest and northern areas
    northern_path = Room(
        "northern_path",
        "Northern Path",
        "A winding dirt path stretches northward from the village, flanked by ancient oak trees whose branches "
        "intertwine overhead. Occasionally, the leaves shift color from green to autumn gold and back again in seconds. "
        "Small lights - perhaps fireflies or something more magical - flicker among the branches. The village center "
        "lies south, the mystic's tower east, and the dense forest continues north."
    )
    
    forest_edge = Room(
        "forest_edge",
        "Edge of the Whispering Forest",
        "The forest creates a natural boundary for the village to the north. Trees with silvery bark stand "
        "like sentinels, their leaves rustling with whispers that sound almost like words. One massive yew tree "
        "dominates the area, its trunk bearing carvings that change meaning depending on when viewed. The path "
        "back to the village lies south, while barely visible trails lead deeper into the forest."
    )
    
    forest_clearing = Room(
        "forest_clearing",
        "Whispering Clearing",
        "The forest opens into a perfectly circular clearing where no trees grow. The ground is covered in soft moss "
        "that glows faintly at night, and standing stones form a small circle at the center. Each stone bears symbols "
        "similar to those in the forgotten shrine. The clearing is eerily quiet compared to the surrounding forest, "
        "as if sound itself is muffled here."
    )
    
    forest_hideaway = Room(
        "forest_hideaway",
        "Hidden Grove",
        "This secluded grove is hidden from casual discovery by dense foliage. A small structure resembling a combination "
        "of tree house and shrine nestles among ancient branches - apparently the dwelling of a forest hermit, though "
        "they're nowhere to be seen. Curious tools and gathered herbs hang from branches, and a small fire pit shows "
        "recent use. Carved wooden figurines depict various village residents in remarkable detail."
    )
    
    yew_tree_hollow = Room(
        "yew_tree_hollow",
        "Within the Ancient Yew",
        "This impossible space within the massive yew tree is larger inside than the tree could possibly contain. "
        "The walls are living wood, pulsing gently like a heartbeat. Soft light filters through the wood grain, "
        "and the air smells of sap and ancient magic. Carved into the living wood are images showing the history "
        "of the village and events yet to come."
    )
    
    # Swamp areas
    whispering_swamp = Room(
        "whispering_swamp",
        "Whispering Swamp Edge",
        "A perpetual mist hangs over this murky swamp at the village's eastern edge. The ground gradually transforms "
        "from solid earth to soggy terrain as you leave the marketplace behind. The air feels thinner here, as if "
        "the boundary between dimensions wears thin. Twisted trees rise from the murky water, their branches "
        "reaching like gnarled fingers toward the sky."
    )
    
    swamp_depths = Room(
        "swamp_depths",
        "Swamp Depths",
        "Deep within the swamp, reality feels particularly fragile. A small island of relatively dry land is surrounded "
        "by pools of iridescent water. The mist is thicker here, sometimes parting to reveal glimpses of other worlds. "
        "A worn stone obelisk rises from the center of the island, covered in warnings about dimensional instability."
    )
    
    forest_swamp_trail = Room(
        "forest_swamp_trail",
        "Overgrown Trail",
        "This narrow trail winds along the boundary between the Whispering Forest and the swamp. Vegetation from both "
        "regions intermingles here, creating strange hybrid plants. Signs of animal passage are visible in the soft ground, "
        "though the tracks sometimes vanish mid-step, as if the creatures phase in and out of existence."
    )
    
    # Golden Door
    golden_door = Room(
        "golden_door",
        "The First Golden Door",
        "A small island in the deepest part of the swamp holds a free-standing archway of obsidian stone. The archway "
        "is accessible by a partially submerged path of ancient stepping stones. Warnings in ancient script are carved "
        "into the stone, cautioning about unstable fragments of other worlds - pocket dimensions that follow different rules."
    )
    
    # Underswamp - special area only accessible to archmages
    underswamp = Room(
        "underswamp",
        "The Underswamp",
        "This vast cavern hidden beneath the Whispering Swamp can only be accessed by those with the highest "
        "dimensional awareness. The chamber glitters with accumulated treasures from countless cycles. "
        "Crystalline formations grow from the ceiling, each containing what appears to be a frozen moment "
        "from a different potential timeline. There is no physical entrance or exit - only Archmages can teleport here."
    )
    
    # Add all rooms to the dictionary
    rooms["spawn"] = spawn
    rooms["elders_cottage"] = elders_cottage
    rooms["cottage_interior"] = cottage_interior
    rooms["cottage_upstairs"] = cottage_upstairs
    rooms["cottage_cellar"] = cottage_cellar
    rooms["cottage_garden"] = cottage_garden
    rooms["marketplace"] = marketplace
    rooms["curiosity_shop"] = curiosity_shop
    rooms["mystics_tower"] = mystics_tower
    rooms["tower_interior"] = tower_interior
    rooms["tower_workshop"] = tower_workshop
    rooms["tower_upper"] = tower_upper
    rooms["tower_top"] = tower_top
    rooms["tower_basement"] = tower_basement
    rooms["ancient_library"] = ancient_library
    rooms["library_main"] = library_main
    rooms["library_reading"] = library_reading
    rooms["reading_garden"] = reading_garden
    rooms["library_mezzanine"] = library_mezzanine
    rooms["library_astronomy"] = library_astronomy
    rooms["library_basement"] = library_basement
    rooms["old_well"] = old_well
    rooms["well_bottom"] = well_bottom
    rooms["underground_junction"] = underground_junction
    rooms["forgotten_shrine"] = forgotten_shrine
    rooms["shrine_interior"] = shrine_interior
    rooms["shrine_underground"] = shrine_underground
    rooms["northern_path"] = northern_path
    rooms["forest_edge"] = forest_edge
    rooms["forest_clearing"] = forest_clearing
    rooms["forest_hideaway"] = forest_hideaway
    rooms["yew_tree_hollow"] = yew_tree_hollow
    rooms["whispering_swamp"] = whispering_swamp
    rooms["swamp_depths"] = swamp_depths
    rooms["forest_swamp_trail"] = forest_swamp_trail
    rooms["golden_door"] = golden_door
    rooms["underswamp"] = underswamp

def connect_exits(rooms):
    """Connect all rooms with appropriate exits."""
    
    # Village Center connections
    rooms["spawn"].exits = {
        "north": "northern_path", 
        "east": "marketplace", 
        "south": "old_well", 
        "west": "elders_cottage"
    }
    
    # Elder's Cottage area
    rooms["elders_cottage"].exits = {
        "east": "spawn",
        "north": "cottage_garden"
        # "in" exit will be handled by the cottage door object
    }
    
    rooms["cottage_interior"].exits = {
        "out": "elders_cottage",
        "up": "cottage_upstairs"
        # "down" exit will be added when trapdoor is discovered
    }
    
    rooms["cottage_upstairs"].exits = {
        "down": "cottage_interior"
    }
    
    rooms["cottage_cellar"].exits = {
        "up": "cottage_interior",
        "north": "underground_junction"
    }
    
    rooms["cottage_garden"].exits = {
        "south": "elders_cottage",
        "east": "spawn"
    }
    
    # Marketplace area
    rooms["marketplace"].exits = {
        "west": "spawn", 
        "north": "mystics_tower", 
        "east": "whispering_swamp"
        # "shop" exit will be handled by the curiosity stall object
    }
    
    rooms["curiosity_shop"].exits = {
        "out": "marketplace"
    }
    
    # Mystic's Tower complex
    rooms["mystics_tower"].exits = {
        "south": "marketplace", 
        "west": "northern_path"
        # "in" exit will be handled by the tower door object
    }
    
    rooms["tower_interior"].exits = {
        "out": "mystics_tower",
        "up": "tower_upper",
        "down": "tower_basement",
        "west": "tower_workshop"
    }
    
    rooms["tower_workshop"].exits = {
        "east": "tower_interior"
    }
    
    rooms["tower_upper"].exits = {
        "up": "tower_top",
        "down": "tower_interior"
    }
    
    rooms["tower_top"].exits = {
        "down": "tower_upper"
    }
    
    rooms["tower_basement"].exits = {
        "up": "tower_interior",
        "north": "underground_junction"
    }
    
    # Library area
    rooms["ancient_library"].exits = {
        "north": "old_well",
        "east": "reading_garden"
        # "in" exit will be handled by the library doors object
    }
    
    rooms["library_main"].exits = {
        "out": "ancient_library",
        "east": "library_reading",
        "up": "library_mezzanine",
        "down": "library_basement"
    }
    
    rooms["library_reading"].exits = {
        "west": "library_main",
        "out": "reading_garden"
    }
    
    rooms["reading_garden"].exits = {
        "west": "ancient_library",
        "in": "library_reading",
        "north": "spawn"
    }
    
    rooms["library_mezzanine"].exits = {
        "down": "library_main",
        "up": "library_astronomy"
    }
    
    rooms["library_astronomy"].exits = {
        "down": "library_mezzanine"
    }
    
    rooms["library_basement"].exits = {
        "up": "library_main",
        "north": "underground_junction"
    }
    
    # Well area
    rooms["old_well"].exits = {
        "north": "spawn", 
        "south": "ancient_library", 
        "east": "forgotten_shrine"
        # "down" exit will be handled by the well object
    }
    
    rooms["well_bottom"].exits = {
        "east": "underground_junction"
        # up exit will be handled by well object
    }
    
    rooms["underground_junction"].exits = {
        "west": "well_bottom",
        "north": "cottage_cellar",
        "east": "shrine_underground",
        "southeast": "library_basement"
    }
    
    # Shrine area
    rooms["forgotten_shrine"].exits = {
        "west": "old_well",
        "east": "shrine_interior"
    }
    
    rooms["shrine_interior"].exits = {
        "west": "forgotten_shrine",
        "down": "shrine_underground"
    }
    
    rooms["shrine_underground"].exits = {
        "up": "shrine_interior",
        "west": "underground_junction"
    }
    
    # Forest and northern areas
    rooms["northern_path"].exits = {
        "south": "spawn", 
        "east": "mystics_tower", 
        "north": "forest_edge"
    }
    
    rooms["forest_edge"].exits = {
        "south": "northern_path",
        "north": "forest_clearing"
        # "in" exit to yew_tree_hollow will be handled by the yew tree object
    }
    
    rooms["forest_clearing"].exits = {
        "south": "forest_edge",
        "west": "forest_hideaway",
        "east": "forest_swamp_trail"
    }
    
    rooms["forest_hideaway"].exits = {
        "east": "forest_clearing"
    }
    
    rooms["yew_tree_hollow"].exits = {
        "out": "forest_edge"
    }
    
    # Swamp areas
    rooms["whispering_swamp"].exits = {
        "west": "marketplace",
        "east": "swamp_depths",
        "northeast": "forest_swamp_trail"
    }
    
    rooms["swamp_depths"].exits = {
        "west": "whispering_swamp",
        "east": "golden_door"
    }
    
    rooms["forest_swamp_trail"].exits = {
        "southwest": "whispering_swamp",
        "northeast": "forest_clearing"
    }
    
    rooms["golden_door"].exits = {
        "west": "swamp_depths"
        # "north" exit will be dynamically added by AI generation 
    }
    
    # The underswamp has no normal exits - only accessible via archmage teleport
    rooms["underswamp"].exits = {}

# Update to village_generator.py to make containers work with the interaction system

def add_container_items(rooms):
    bag = ContainerItem("bag", 
                        "bag", 
                        "A musty carpet bag lies here",
                        weight = 0.1, 
                        value = 0,
                        capacity_limit=8,
                        capacity_weight=40
                        )
    
    # Add container interactions for opening and closing
    if hasattr(bag, 'add_interaction'):
        # Add open interaction for closed state
        bag.add_interaction(
            verb="open",
            target_state="open",
            message="You open the bag.",
            from_state="closed"
        )
        
        # Add close interaction for open state
        bag.add_interaction(
            verb="close",
            target_state="closed",
            message="You close the bag.",
            from_state="open"
        )
    
    rooms["elders_cottage"].add_item(bag)
def add_stateful_items(rooms):
    """
    Add all stateful interactive objects to rooms.
    
    Args:
        rooms (dict): Dictionary mapping room_id to Room objects
    """
    from models.StatefulItem import StatefulItem
    
    # First add all the linked doors
    add_linked_doors(rooms)
    
    # Cottage trapdoor and rug
    # ------------------------
    # Create the rug that covers the trapdoor
    cottage_rug = StatefulItem(
        "rug",
        "cottage_rug",
        "A worn circular rug lies in the center of the room.",
        weight=20,
        value=0,
        takeable=False,
        state="covering"
    )
    cottage_rug.add_state_description("covering", "A worn circular rug lies in the center of the room.")
    cottage_rug.add_state_description("moved", "A worn circular rug has been moved aside.")
    cottage_rug.set_room_id("cottage_interior")
    
    # Register rug interactions
    cottage_rug.add_interaction(
        verb="move",
        target_state="moved",
        message="You move the rug aside, revealing a wooden trapdoor underneath.",
        from_state="covering"
    )
    cottage_rug.add_interaction(
        verb="pull",
        target_state="moved",
        message="You pull back the rug, revealing a wooden trapdoor underneath.",
        from_state="covering"
    )
    cottage_rug.add_interaction(
        verb="move",
        target_state="covering",
        message="You move the rug back to its original position, covering the trapdoor.",
        from_state="moved"
    )
    cottage_rug.add_interaction(
        verb="replace",
        target_state="covering",
        message="You replace the rug, covering the trapdoor.",
        from_state="moved"
    )
    
    # Create the trapdoor as a separate item
    cottage_trapdoor = StatefulItem(
        "trapdoor",
        "cottage_trapdoor",
        "A wooden trapdoor is set into the floor.",
        weight=50,
        value=0,
        takeable=False,
        state="closed"
    )
    cottage_trapdoor.add_state_description("closed", "A wooden trapdoor is set into the floor.")
    cottage_trapdoor.add_state_description("open", "An open trapdoor reveals stone steps leading down.")
    cottage_trapdoor.set_room_id("cottage_interior")
    
    # Register trapdoor interactions
    cottage_trapdoor.add_interaction(
        verb="open",
        target_state="open",
        message="You open the wooden trapdoor, revealing stone steps leading down into darkness.",
        add_exit=("down", "cottage_cellar"),
        from_state="closed"
    )
    cottage_trapdoor.add_interaction(
        verb="close",
        target_state="closed",
        message="You close the trapdoor.",
        remove_exit="down",
        from_state="open"
    )
    
    # Add the rug as a visible item
    rooms["cottage_interior"].add_item(cottage_rug)
    
    # Add the trapdoor as a hidden item
    rooms["cottage_interior"].add_hidden_item(
        cottage_trapdoor,
        lambda game_state: any(
            item.id == "cottage_rug" and item.state == "moved" 
            for item in game_state.get_room("cottage_interior").items
        )
    )
    
    # Yew tree in the forest
    # ---------------------
    yew_tree = StatefulItem(
        "tree",
        "yew_tree",
        "A massive yew tree with carved symbols in its bark.",
        weight=100000,
        value=0,
        takeable=False,
        state="intact"
    )
    yew_tree.add_state_description("intact", "A massive yew tree with carved symbols in its bark.")
    yew_tree.add_state_description("cut", "A yew tree with a section carved out, revealing a passage inside.")
    yew_tree.set_room_id("forest_edge")
    
    # Register yew tree interactions
    yew_tree.add_interaction(
        verb="chop",
        required_instrument="axe",
        target_state="cut",
        message="You swing the axe at the ancient yew tree. The trunk folds inward, revealing a hidden passage.",
        add_exit=("in", "yew_tree_hollow"),
        from_state="intact"
    )
    yew_tree.add_interaction(
        verb="cut",
        required_instrument="axe",
        target_state="cut",
        message="You cut into the yew tree with the axe, revealing a hidden passage.",
        add_exit=("in", "yew_tree_hollow"),
        from_state="intact"
    )
    yew_tree.add_interaction(
        verb="examine",
        message="The tree's bark is covered in strange symbols that seem to shift slightly as you look at them."
    )
    
    rooms["forest_edge"].add_item(yew_tree)
    
    # Old well in the courtyard
    # ------------------------
    old_well = StatefulItem(
        "well",
        "well",
        "A stone well with a locked wooden lid sits here.",
        weight=1000,
        value=0,
        takeable=False,
        state="locked"
    )
    old_well.add_state_description("locked", "A stone well with a locked wooden lid sits here.")
    old_well.add_state_description("unlocked", "A stone well with its wooden lid sits here.")
    old_well.add_state_description("open", "A stone well with its wooden lid removed stands open.")
    old_well.add_state_description("with_rope", "A stone well with a rope descending into darkness.")
    old_well.set_room_id("old_well")

    # Register well interactions
    old_well.add_interaction(
        verb="unlock",
        required_instrument="key",
        target_state="unlocked",
        message="You unlock the well's lid with the bronze key.",
        from_state="locked"
    )
    old_well.add_interaction(
        verb="open",
        required_instrument="key",
        target_state="open",
        message="You open the well's lid, revealing a dark pit below.",
        from_state="locked",
    )
    old_well.add_interaction(
        verb="open",
        target_state="open",
        message="You open the well's lid, revealing a dark pit below.",
        from_state="unlocked"
    )
    old_well.add_interaction(
        verb="close",
        target_state="unlocked",
        message="You put back the well's lid.",
        from_state="open",
    )
    old_well.add_interaction(
        verb="lock",
        required_instrument="key",
        target_state="locked",
        message="You lock the well's lid with the key.",
        from_state="unlocked",
    )
    # Updated version with consume_instrument and reciprocal_exit
    old_well.add_interaction(
        verb="tie",
        required_instrument="rope",
        target_state="with_rope",
        message="You tie the rope to the well's edge, providing a way down.",
        add_exit=("down", "well_bottom"),
        from_state="open",
        consume_instrument=True,  # The rope is consumed when used
        reciprocal_exit=("well_bottom", "up", "old_well")  # Creates the return path
    )
    old_well.add_interaction(
        verb="close",
        target_state="unlocked",
        message="You put back the well's lid, making the rope inaccessible.",
        from_state="with_rope",
        remove_exit="down"  # Remove the downward exit when well is closed
    )
    
    rooms["old_well"].add_item(old_well)
    
    # Shrine altar with rune stones
    # ----------------------------
    shrine_altar = StatefulItem(
        "altar",
        "altar",
        "A circular stone altar with seven empty colored indentations.",
        weight=2000,
        value=0,
        takeable=False,
        state="empty"
    )
    shrine_altar.add_state_description("empty", "A circular stone altar with seven empty colored indentations.")
    shrine_altar.add_state_description("partial", "A circular altar with some glowing rune stones in place.")
    shrine_altar.add_state_description("complete", "A circular altar with seven glowing rune stones in place.")
    shrine_altar.set_room_id("shrine_interior")
    
    # Register altar interactions
    shrine_altar.add_interaction(
        verb="place",
        required_instrument="stone",
        message="You place the rune stone in a matching indentation. It begins to glow softly.",
        from_state="empty"
    )
    shrine_altar.add_interaction(
        verb="place",
        required_instrument="stone",
        message="You place another rune stone in its matching indentation. The altar pulses with energy.",
        from_state="partial"
    )
    shrine_altar.add_interaction(
        verb="touch",
        message="The altar feels cool to the touch, vibrating slightly with latent energy."
    )
    shrine_altar.add_interaction(
        verb="examine",
        message="The circular altar has seven indentations arranged in a pattern: red, orange, yellow, green, blue, indigo, and violet."
    )
    
    rooms["shrine_interior"].add_item(shrine_altar)
    
    # Golden door in archway
    # ---------------------
    golden_door_obj = StatefulItem(
        "door",
        "golden_door",
        "A door of pure golden light shimmers within the archway.",
        weight=1000,
        value=0,
        takeable=False,
        state="closed"
    )
    golden_door_obj.add_state_description("closed", "A door of pure golden light shimmers within the archway.")
    golden_door_obj.add_state_description("open", "An open doorway of golden light leads to another reality.")
    golden_door_obj.set_room_id("golden_door")
    
    # Register golden door interactions
    golden_door_obj.add_interaction(
        verb="open",
        target_state="open",
        message="As you reach for the door, it dissolves into golden mist before reforming as an open portal.",
        add_exit=("north", "ai_generated_zone"),  # This would connect to an AI-generated area
        from_state="closed"
    )
    golden_door_obj.add_interaction(
        verb="close",
        target_state="closed",
        message="The doorway of light gradually shrinks until it's once again a closed door.",
        remove_exit="north",
        from_state="open"
    )
    golden_door_obj.add_interaction(
        verb="touch",
        message="Your hand passes through the golden light, feeling warm tingles across your skin."
    )
    golden_door_obj.add_interaction(
        verb="examine",
        message="The golden door isn't made of physical material. It's pure light, pulsing with the rhythm of another world."
    )
    
    rooms["golden_door"].add_item(golden_door_obj)
    
    # Swamp pool
    # ---------
    swamp_pool = StatefulItem(
        "pool",
        "pool",
        "A pool of shimmering water ripples without cause.",
        weight=5000,
        value=0,
        takeable=False,
        state="active"
    )
    swamp_pool.add_state_description("active", "A pool of shimmering water ripples without cause.")
    swamp_pool.add_state_description("swirling", "The pool's water swirls violently, forming a miniature whirlpool.")
    swamp_pool.add_state_description("calm", "The pool's water has become mysteriously still and mirror-like.")
    swamp_pool.set_room_id("swamp_depths")
    
    # Register swamp pool interactions
    swamp_pool.add_interaction(
        verb="touch",
        target_state="swirling",
        message="As you touch the water, it begins to swirl violently, forming a whirlpool that soon calms itself.",
        from_state="active"
    )
    swamp_pool.add_interaction(
        verb="drop",
        target_state="swirling",
        message="As the object hits the water, the pool begins to swirl, absorbing the item into its depths.",
        from_state="active"
    )
    swamp_pool.add_interaction(
        verb="drink",
        message="You taste a single drop of the water. It tastes normal but leaves your tongue tingling with strange energy."
    )
    swamp_pool.add_interaction(
        verb="examine",
        message="The pool's water shimmers with an inner light, occasionally revealing glimpses of other landscapes far below its surface."
    )
    
    rooms["swamp_depths"].add_item(swamp_pool)

# Update add_regular_items in village_generator.py to include readable content

def add_regular_items(rooms):
    """Add regular (non-stateful) items to rooms."""
    
    # Elder's cottage items
    ancient_tome = Item(
        "tome",
        "tome",
        "An ancient leather-bound tome lies here.",
        weight=0.5,
        value=5
    )
    
    # Make the tome readable using the StatefulItem features
    readable_tome = StatefulItem(
        "tome", 
        "ancient_tome",
        "An ancient leather-bound tome lies here.",
        weight=0.5,
        value=5,
        takeable=True,
        state="unread"
    )
    readable_tome.add_state_description("unread", "An ancient leather-bound tome lies here.")
    readable_tome.add_state_description("read", "An ancient leather-bound tome lies here.")
    
    # Add read interaction for unread state
    readable_tome.add_interaction(
        verb="read",
        target_state="read",
        message="You carefully open the ancient tome and read:\n\n"
               "\"The village of Chronos exists at a nexus of temporal convergence. Seven cycles "
               "bind us to the eternal return, and those who master the cycles may glimpse beyond "
               "the golden doors. The Well of Whispers touches all realities, and those who "
               "listen may hear secrets from worlds yet to be. Beware the thirteenth hour, when "
               "time folds upon itself and the veil between worlds grows thin.\"\n\n"
               "The rest of the pages contain complex mathematical formulae and star charts "
               "you cannot decipher.",
        from_state="unread"
    )
    
    # Add read interaction for already read state (no state change)
    readable_tome.add_interaction(
        verb="read",
        message="You open the tome again. The text remains the same:\n\n"
               "\"The village of Chronos exists at a nexus of temporal convergence. Seven cycles "
               "bind us to the eternal return, and those who master the cycles may glimpse beyond "
               "the golden doors...\"\n\n"
               "The mathematical formulae still make no sense to you.",
        from_state="read"
    )
    
    rooms["cottage_interior"].add_item(readable_tome)
    
    # Library manuscript
    glowing_manuscript = StatefulItem(
        "manuscript",
        "manuscript",
        "A manuscript written in glowing ink has been left here.",
        weight=0.5,
        value=20,
        state="unread"
    )
    glowing_manuscript.add_state_description("unread", "A manuscript written in glowing ink has been left here.")
    glowing_manuscript.add_state_description("read", "A manuscript written in glowing ink has been left here.")
    
    # Add read interaction
    glowing_manuscript.add_interaction(
        verb="read",
        target_state="read",
        message="You open the manuscript and find that the glowing text shifts as you read:\n\n"
               "\"The Golden Doors appear where reality wears thin. Each leads to a fragment "
               "of potential – a pocket dimension with its own rules and treasures. The fragments "
               "persist until the Great Reset, when the timestream purifies itself. Seven stones "
               "in the shrine altar may stabilize a fragment between resets, but such power "
               "comes at great cost.\"\n\n"
               "The remaining pages contain instructions for ritual preparation that you "
               "cannot fully comprehend."
    )
    
    rooms["library_main"].add_item(glowing_manuscript)
    
    # Dimensional compass
    dimensional_compass = Item(
        "compass",
        "compass",
        "A peculiar brass compass rests on the ground.",
        weight=0.05,
        value=15
    )
    rooms["cottage_upstairs"].add_item(dimensional_compass)
    
    # Bronze key
    bronze_key = Item(
        "key",
        "key",
        "A tarnished bronze key lies here.",
        weight=0.02,
        value=5
    )
    rooms["marketplace"].add_item(bronze_key)
    
    # Remembrance charm
    remembrance_charm = Item(
        "amulet",
        "amulet",
        "A faintly glowing blue amulet has been left here.",
        weight=0.1,
        value=20
    )
    rooms["curiosity_shop"].add_item(remembrance_charm)
    
    # Crystal lens
    crystal_lens = Item(
        "lens",
        "lens",
        "A perfectly cut crystal lens gleams nearby.",
        weight=0.05,
        value=25
    )
    rooms["tower_workshop"].add_item(crystal_lens)
    
    # Add more readable items for other books and manuscripts
    # Blue rune stone with readable carvings
    blue_rune_stone = StatefulItem(
        "stone",
        "bluestone",
        "A smooth blue stone etched with a glowing rune catches your eye.",
        weight=1,
        value=15,
        state="unread"
    )
    blue_rune_stone.add_state_description("unread", "A smooth blue stone etched with a glowing rune catches your eye.")
    blue_rune_stone.add_state_description("read", "A smooth blue stone etched with a glowing rune catches your eye.")
    
    blue_rune_stone.add_interaction(
        verb="read",
        target_state="read",
        message="You study the rune on the stone. It seems to represent 'water' or 'flow', "
               "and holding it gives you a sense of calm fluidity, as if time itself could "
               "be navigated like a river."
    )
    blue_rune_stone.add_interaction(
        verb="examine",
        message="The stone is perfectly smooth and cool to the touch. The blue rune carved "
               "into it pulses gently with inner light."
    )
    
    rooms["library_astronomy"].add_item(blue_rune_stone)
    
    # Remaining items as before
    frayed_rope = Item(
        "rope",
        "rope",
        "A weathered rope lies coiled on the ground.",
        weight=3,
        value=5
    )
    rooms["old_well"].add_item(frayed_rope)
    
    wooden_bucket = Item(
        "bucket",
        "bucket",
        "A sturdy wooden bucket sits here.",
        weight=2,
        value=5
    )
    rooms["old_well"].add_item(wooden_bucket)
        
    silver_flute = Item(
        "flute",
        "flute",
        "A delicate silver flute has been discarded here.",
        weight=1,
        value=25
    )
    rooms["northern_path"].add_item(silver_flute)
    
    enchanted_axe = Item(
        "axe",
        "axe",
        "An unusual-looking axe rests against a tree.",
        weight=3,
        value=40
    )
    rooms["forest_hideaway"].add_item(enchanted_axe)


def add_linked_doors(rooms):
    """
    Create all linked doors between rooms in the village.
    
    Args:
        rooms (dict): Dictionary mapping room_id to Room objects
    """
    from utils import create_linked_doors
    
    # Cottage doors (exterior to interior)
    create_linked_doors(
        room1_id="elders_cottage",
        room2_id="cottage_interior",
        door1_id="cottage_exterior_door",
        door2_id="cottage_interior_door",
        door_name="sturdy wooden door",
        dir1to2="in",
        dir2to1="out",
        initial_state="closed",
        rooms=rooms
    )
    
    # Tower doors (exterior to interior)
    create_linked_doors(
        room1_id="mystics_tower",
        room2_id="tower_interior",
        door1_id="tower_exterior_door", 
        door2_id="tower_interior_door",
        door_name="massive wooden door",
        dir1to2="in",
        dir2to1="out",
        initial_state="open",
        rooms=rooms
    )
    
    # Library doors (exterior to interior)
    create_linked_doors(
        room1_id="ancient_library",
        room2_id="library_main",
        door1_id="library_exterior_door",
        door2_id="library_interior_door",
        door_name="bronze library door",
        dir1to2="in",
        dir2to1="out",
        initial_state="open",
        rooms=rooms
    )
    
    # Workshop door (tower interior to workshop)
    create_linked_doors(
        room1_id="tower_interior",
        room2_id="tower_workshop",
        door1_id="workshop_exterior_door",
        door2_id="workshop_interior_door",
        door_name="ornate workshop door",
        dir1to2="west",
        dir2to1="east",
        initial_state="open",
        rooms=rooms
    )
    
    # Reading room door (library main to reading room)
    create_linked_doors(
        room1_id="library_main",
        room2_id="library_reading",
        door1_id="reading_room_exterior_door",
        door2_id="reading_room_interior_door",
        door_name="polished oak door",
        dir1to2="east",
        dir2to1="west",
        initial_state="open",
        rooms=rooms
    )
    
    # Shrine doors (exterior to interior)
    create_linked_doors(
        room1_id="forgotten_shrine",
        room2_id="shrine_interior",
        door1_id="shrine_exterior_door",
        door2_id="shrine_interior_door",
        door_name="ancient stone door",
        dir1to2="east",
        dir2to1="west",
        initial_state="open",
        rooms=rooms
    )
    
    # Curiosity shop entry (marketplace to shop)
    create_linked_doors(
        room1_id="marketplace",
        room2_id="curiosity_shop",
        door1_id="shop_exterior_curtain",
        door2_id="shop_interior_curtain",
        door_name="violet curtain",
        dir1to2="in",
        dir2to1="out",
        initial_state="open",
        rooms=rooms
    )