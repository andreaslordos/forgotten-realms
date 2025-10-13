# AI MUD Design Document

This document outlines the game systems, mechanics, and design goals for **AI MUD**, a text-based MMORPG that uses AI to generate new areas. Below is a complete specification to guide development and ensure an AI or collaborator fully understands the project’s objectives.

---

## 1. Core Concept

AI MUD is a **text-based** multiplayer online role-playing game (MMORPG). Its key features include:
1. **Intentional AI Generation**: Instead of randomly expanding the map, the game introduces special “Doors of Gold” that spawn entire themed dungeons or zones behind them.
2. **Time Loop Narrative**: The world is stuck in a weekly cycle, resetting fully once every week, while partial resets can be triggered mid-week by archmages or inactivity.
3. **Persistent Player Progress**: Players retain their **levels and points** across resets. However, items, puzzle states, and AI-generated zones are wiped on the weekly reset (with some nuances for mid-week resets).
4. **Puzzles and Combat**: Puzzle-solving for treasure and points, plus a simple continuous combat system that allows attacking or fleeing.

---

## 2. World Overview

### 2.1 The Village

- **Village Center**: The main area where players spawn or re-spawn.
- **Swamp Area**: A special location connected to the village.
  - **Treasure “Swamping”**: Players can drop treasure in the swamp to earn points. The dropped treasure goes into the “underswamp,” an area only accessible to Archmages via teleport.
- **Time Loop Lore**: Each weekly reset explains the “reverted” state of the village as being part of a recurrent time loop or alternate dimension scenario. Clues or flavor text can hint at prior weeks’ events.

### 2.2 Doors of Gold (AI-Generated Zones)

- **Location**: Placed intentionally at certain “edge” or special rooms in the village (or in existing dungeons).
- **Activation**: Entering a Door of Gold triggers AI generation of:
  1. A **themed** dungeon or area (e.g., haunted castle, abandoned ruins, etc.).
  2. Several **rooms** connected logically.
  3. **NPCs and puzzles** consistent with the theme.
  4. A potential **goal** or treasure to discover.
- **Persistence**: Once generated, this new area remains accessible to all players until the weekly reset.

---

## 3. Resets and Persistence

### 3.1 Weekly Reset

- **Schedule**: Happens once a week on a fixed schedule (e.g., Sunday at midnight).
- **Effect**:
  - **All AI-generated zones** are deleted, returning the game to the original “village state.”
  - **All puzzle states** and **items** are restored to default.
  - **Player progress** (levels and points) **is retained** (everything else is wiped).

### 3.2 Mid-Week Reset (Archmage or Inactivity)

- **Archmage Trigger**:
  - At the highest level (e.g., “Archmage”), players can type `reset` to forcibly reset the world.
  - All players are kicked out; upon rejoining, the **world reverts to its start-of-week** condition.
- **Inactivity Trigger**:
  - If the game remains inactive for **2 hours**, it resets automatically.
- **Effect**:
  - **AI-generated areas remain** (i.e., the newly created dungeons are not deleted this week).
  - **Puzzle states, items on the ground, and player positions** revert to how they were at the start-of-week.
  - Player **levels/points** are retained.

---

## 4. Player Progression & Inventory

### 4.1 Levels & Points

- **Points**: Earned primarily by:
  - **Swamping treasure** in the swamp area.
  - Solving puzzles or defeating mobs.
- **Levels**: Gated by specific point thresholds. Higher levels may unlock:
  - Increased stats (stamina, strength, dexterity).
  - New commands (e.g., Archmage’s `reset`, `teleport to underswamp`).
- **Persistence**: Levels and points are saved across all resets, weekly or mid-week.

### 4.2 Inventory & Carrying Capacity

- **Item Limits**: Players have a maximum item count (`carrying_capacity_num`) and a weight limit (`strength`).
- **Item Types**:
  1. **Treasure**: Can be swamped for points.
  2. **Puzzle items**: Tools or keys for puzzle solutions (e.g., axe, special key, rune stone).
  3. **Weapons**: Used for combat.
- **Dropping Items**:
  - If a player **flees** combat, they drop all their items automatically.
  - Voluntarily dropping items in the swamp yields points if it’s treasure.

---

## 5. Puzzles & Interactivity

### 5.1 Puzzle Design

- **Distributed Puzzle Pieces**: One area might contain the tool (e.g., an enchanted axe), which is needed in a different area (e.g., chop down a giant yew tree) to unlock or reveal something.
- **Actions**:
  - `knock on door` could teleport the player inside.
  - `chop yew tree with axe` might open an underground passage.
  - AI may generate other interactive commands (e.g., `push statue`, `light torch`, etc.).
- **Reward**: Generally yields high-value treasure or grants points directly.

### 5.2 Puzzle States

- **Mid-Week Reset**: Resets puzzles to their **un-solved** state. Items return to their original spawn locations.
- **Weekly Reset**: Removes the entire AI-generated puzzle content. Only the base puzzles in the default village remain.

---

## 6. Combat System

### 6.1 Basic Combat

- **Commands**:
  - `attack <target>` or `kill <target>` (optionally specifying a weapon, e.g., `with axe`).
  - `ret <target> [with <weapon>]` (short for “retaliate”).
- **Continuous & RNG**:
  - Once combat starts, damage is computed using a combination of player/mob stats, weapon bonuses, and some random variation.
  - Combat continues automatically (turn-by-turn or time-based) until one side flees or is defeated.
- **Flee**:
  - Command: `flee` (or `run`).
  - Cost: Player **drops all items** and **loses some points**, but remains alive.

### 6.2 NPC & Mob Interaction

- **AI-Generated Mobs**:
  - Themed creatures roam the generated zones (skeletons, trolls, spirits, etc.).
  - Some are aggressive on sight, others only attack if provoked.
- **Stats & Difficulty**:
  - The AI can scale mob strength based on the zone theme or the average player level (optional).

---

## 7. Example Gameplay Flow

1. **Start of a New Week**
   - The world is reset to the default village layout. No generated zones exist yet.
   - Players log in with their persistent level and points.

2. **Players Explore**
   - They discover a **Door of Gold** on the outskirts of the village.
   - Entering it triggers an **AI** module that creates a **themed dungeon** (e.g., “Crystal Catacombs”).

3. **Puzzles & Combat**
   - Players encounter puzzles (e.g., a locked gate requiring a special lever or axe to open).
   - Mobs might attack, granting points or loot upon defeat.

4. **Treasure & Swamping**
   - Successfully solving puzzles yields treasure items.
   - Dropping treasure in the swamp converts them to points. Points can lead to level-ups.

5. **Resets**
   - **Archmage reset** or **2-hour inactivity** → The dungeon persists, but puzzle states revert to fresh.
   - **Weekly reset** → Entire generated content is wiped, returning to the village-only state, with players keeping their level/points.

---

## 8. Implementation Considerations

1. **AI Generation Module**
   - A dedicated system (`ai_generator.py`, for instance) that, given a theme prompt, creates rooms, NPCs, items, and puzzle hooks.
   - Maintains a simple lore or context state so subsequent generations remain cohesive.

2. **Puzzle & State Management**
   - Store puzzle definitions and their “solved/unsolved” states.
   - Each puzzle can define triggers, required items, and effects (e.g., reveals a hidden room, drops a special item).

3. **Combat Implementation**
   - A combat manager or routine that handles multi-turn combat loops.
   - Integrate with player stats (stamina, strength, etc.) and a random factor for attack rolls.

4. **Data Persistence**
   - **JSON or DB**: Continue using JSON for quick iteration. Later, a database might be beneficial.
   - Distinct files for:
     - `rooms.json` (including AI-generated areas),
     - `players.json` (levels, points, inventory),
     - `auth.json` (login credentials).

5. **Reset Logic**
   - Distinguish between mid-week resets (archmage/inactivity) and weekly resets.
   - Possibly store a “baseline snapshot” of the game state for mid-week resets vs. the “original village” for weekly resets.

---

## 9. Next Steps

1. **Extend Commands**
   - Add `flee`, `kill <target> with <weapon>`, puzzle actions (`knock`, `chop`, etc.), and `reset` for archmages.
2. **Implement AI Generator**
   - Design how the system picks or receives a “theme” for each newly discovered Door of Gold.
   - Ensure generated content references existing lore (time loop, village, etc.).
3. **Puzzle System**
   - Decide how puzzle states and triggers are stored (could be a dictionary in each room, or a global puzzle manager).
4. **Refine Combat & Stats**
   - Tie in level-based stat progression. Possibly add gear-based bonuses.
5. **Test Resets**
   - Confirm weekly and mid-week reset routines. Ensure items, puzzle states, and AI expansions behave as intended.

---

## 10. Summary

**AI MUD** is a week-based, text-only MMORPG with:

- **Doors of Gold** that spawn entire, AI-generated zones full of puzzles and enemies.
- **A swamp mechanic** to convert treasure into points.
- **Multiple reset types** ensuring players keep leveling progress but must re-explore or re-solve puzzles regularly.
- **A consistent lore** built around a village trapped in a repeating time loop, with hints of continuity each reset.

By following this spec, we’ll maintain both a **dynamic, ever-changing** world and a **cohesive narrative** that underscores the cyclic nature of the setting. This design document should give any future collaborator (or AI system) enough clarity to implement and expand the MUD with confidence.
