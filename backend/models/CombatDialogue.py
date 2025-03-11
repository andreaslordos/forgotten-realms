# backend/models/CombatDialogue.py

import random

class CombatDialogue:
    """
    Provides colorful, varied dialogue for combat interactions.
    Includes messages for hits, misses, and special cases like
    taking heavy damage or landing killing blows.
    """
    
    # Player successfully hits opponent
    PLAYER_HIT_MESSAGES = [
        "Your retributive cross sends {target} sprawling!",
        "You beat {target} with a punishing cross!",
        "You catch {target} with a hefty forehand!",
        "You strike out at {target} with a tremendous punch!",
        "You beat {target} with a punishing blow!",
        "Your counter forehand sends {target} sideways!",
        "Your retaliatory whack sends {target} to the floor!",
        "You thrash {target} with a savage clout!",
        "You hit out at {target} with a violent whack!",
        "You catch {target} with a severe thump!",
        "Your precise strike lands squarely on {target}!",
        "You deliver a mighty blow that staggers {target}!",
        "With lightning speed, you connect a solid hit to {target}!",
        "Your attack lands with bone-jarring force on {target}!"
    ]
    
    # Player weapon hit messages
    PLAYER_WEAPON_HIT_MESSAGES = [
        "Your {weapon} slices into {target} with deadly precision!",
        "You drive your {weapon} forward, catching {target} off guard!",
        "Your {weapon} connects with {target} in a devastating arc!",
        "With a flourish, you strike {target} using your {weapon}!",
        "Your {weapon} finds its mark, sending {target} reeling!",
        "You thrust your {weapon} forward, landing a solid blow on {target}!",
        "Your skillful attack with your {weapon} catches {target} by surprise!",
        "You swing your {weapon} in a wide arc, connecting squarely with {target}!",
        "Your {weapon} strikes true, drawing a pained reaction from {target}!"
    ]
    
    # Player misses opponent
    PLAYER_MISS_MESSAGES = [
        "Your wild swing misses {target} completely!",
        "{target} narrowly evades your attack!",
        "You lunge forward but {target} steps aside!",
        "Your attack fails to connect as {target} dodges!",
        "You strike out but only catch air as {target} moves!",
        "Your blow goes wide, missing {target} entirely!",
        "{target} deftly avoids your clumsy attack!",
        "You stumble slightly, your attack going astray!",
        "With surprising agility, {target} avoids your strike!"
    ]
    
    # Opponent successfully hits player
    OPPONENT_HIT_MESSAGES = [
        "The momentum of a thrust by {target} sends you sideways.",
        "You are stunned by the vigour of a whack by {target}!",
        "The weight of a thrust from {target} sends you staggering.",
        "The energy of a forehand from {target} sends you spinning.",
        "You narrowly take a weak whack from {target}.",
        "A sudden strike from {target} catches you off guard!",
        "{target}'s attack lands with surprising force!",
        "You reel from a powerful blow delivered by {target}!",
        "A quick strike from {target} finds its way through your defense!",
        "{target} connects with a jarring hit that rattles your bones!"
    ]
    
    # Opponent weapon hit messages
    OPPONENT_WEAPON_HIT_MESSAGES = [
        "{target}'s {weapon} strikes you with unexpected force!",
        "You feel the sting as {target}'s {weapon} finds its mark!",
        "{target} swings their {weapon}, landing a solid blow!",
        "The weight of {target}'s {weapon} connects, sending you backwards!",
        "{target}'s {weapon} catches you with a glancing blow!",
        "You barely raise your guard as {target}'s {weapon} strikes!",
        "{target} maneuvers their {weapon} in a fluid arc that connects painfully!",
        "A quick thrust of {target}'s {weapon} catches you unprepared!"
    ]
    
    # Opponent misses player
    OPPONENT_MISS_MESSAGES = [
        "You simply elude a feeble blow by {target}.",
        "You comfortably duck a terrible thump from {target}.",
        "You easily duck a pathetic thrust by {target}.",
        "You effortlessly avoid a dreadful clout from {target}.",
        "You deftly sidestep {target}'s clumsy attack!",
        "{target}'s wild swing meets nothing but air!",
        "You twist away from {target}'s poorly aimed strike!",
        "With practiced ease, you avoid {target}'s attack!",
        "You shift your weight, causing {target}'s blow to miss entirely!",
        "{target}'s attack falls short as you step back just in time!"
    ]
    
    # Player takes heavy damage but continues
    HEAVY_DAMAGE_RECOVERY = [
        "With renewed vigour you pull through, and hurtle into the carnage.",
        "Gritting your teeth you compose, and throw yourself into the battle.",
        "With tremendous willpower you carry on, and head back into the carnage.",
        "With a vast effort you concentrate, and hurtle into the affray.",
        "Despite the pain, you steel yourself and press forward!",
        "Summoning your resolve, you shake off the blow and continue the fight!",
        "Your determination burns bright as you ready yourself for another exchange!",
        "The hit staggers you, but your fighting spirit remains unbroken!"
    ]
    
    # Player lands killing blow
    KILLING_BLOW_MESSAGES = [
        "Your last punch killed {target}!",
        "Your final strike brings {target} crashing down!",
        "With a decisive blow, you vanquish {target}!",
        "{target} collapses from your powerful attack!",
        "Your well-placed strike finishes {target} off!",
        "A deadly precision in your attack proves too much for {target}!",
        "Your overwhelming assault finally overcomes {target}!",
        "With one last mighty blow, you defeat {target}!",
        "Your attack strikes true, and {target} falls before you!"
    ]
    
    # Player weapon killing blow
    WEAPON_KILLING_BLOW_MESSAGES = [
        "Your {weapon} delivers the final, fatal blow to {target}!",
        "With deadly precision, your {weapon} ends the fight with {target}!",
        "Your {weapon} flashes one last time, and {target} falls!",
        "A masterful strike with your {weapon} finishes {target} off!",
        "Your {weapon} proves superior as {target} drops before you!",
        "The fight concludes as your {weapon} delivers a decisive blow to {target}!"
    ]
    
    # Victory messages
    VICTORY_MESSAGES = [
        "You are victorious - this time...",
    ]
    
    @staticmethod
    def get_player_hit_message(target_name, weapon=None):
        """Get a random message for when the player hits their target."""
        if weapon:
            messages = CombatDialogue.PLAYER_WEAPON_HIT_MESSAGES
            return random.choice(messages).format(target=target_name, weapon=weapon.name)
        else:
            return random.choice(CombatDialogue.PLAYER_HIT_MESSAGES).format(target=target_name)
    
    @staticmethod
    def get_player_miss_message(target_name):
        """Get a random message for when the player misses their target."""
        return random.choice(CombatDialogue.PLAYER_MISS_MESSAGES).format(target=target_name)
    
    @staticmethod
    def get_opponent_hit_message(target_name, weapon=None):
        """Get a random message for when the opponent hits the player."""
        if weapon:
            messages = CombatDialogue.OPPONENT_WEAPON_HIT_MESSAGES
            return random.choice(messages).format(target=target_name, weapon=weapon.name)
        else:
            return random.choice(CombatDialogue.OPPONENT_HIT_MESSAGES).format(target=target_name)
    
    @staticmethod
    def get_opponent_miss_message(target_name):
        """Get a random message for when the opponent misses the player."""
        return random.choice(CombatDialogue.OPPONENT_MISS_MESSAGES).format(target=target_name)
    
    @staticmethod
    def get_heavy_damage_recovery():
        """Get a random message for when player takes heavy damage but continues."""
        return random.choice(CombatDialogue.HEAVY_DAMAGE_RECOVERY)
    
    @staticmethod
    def get_killing_blow_message(target_name, weapon=None):
        """Get a random message for when player lands a killing blow."""
        if weapon:
            messages = CombatDialogue.WEAPON_KILLING_BLOW_MESSAGES
            msg = random.choice(messages).format(target=target_name, weapon=weapon.name)
        else:
            msg = random.choice(CombatDialogue.KILLING_BLOW_MESSAGES).format(target=target_name)
        
        return msg + "\n" + random.choice(CombatDialogue.VICTORY_MESSAGES)