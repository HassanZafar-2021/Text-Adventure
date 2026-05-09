#!/usr/bin/env python3
"""
=============================================================================
  THE COOK'S ASSISTANT: A LUMBRIDGE ADVENTURE
  Inspired by the Cook's Assistant quest from RuneScape
=============================================================================
"""

import sys
import random
import time
import textwrap
import threading

# ─── Terminal helpers ─────────────────────────────────────────────────────────

WIDTH = 72

def wrap(text):
    return textwrap.fill(text, width=WIDTH)

def slow_print(text, delay=0.018):
    for ch in text:
        print(ch, end='', flush=True)
        time.sleep(delay)
    print()

def boxprint(text, char='─', padding=1):
    lines = textwrap.wrap(text, width=WIDTH - 4)
    inner = WIDTH - 2
    print('┌' + char * inner + '┐')
    for line in lines:
        pad = ' ' * padding
        print('│' + pad + line.ljust(inner - padding * 2) + pad + '│')
    print('└' + char * inner + '┘')

def divider(char='─'):
    print(char * WIDTH)

def header(title):
    print()
    divider('═')
    print(f"  {title}")
    divider('═')
    print()

def pause(msg="[Press ENTER to continue...]"):
    input(f"\n  {msg}")

def choose(options):
    """
    Display a numbered menu and return the chosen key.
    `options` is a list of (key, label) tuples.
    """
    print()
    for i, (_, label) in enumerate(options, 1):
        print(f"  [{i}] {label}")
    print()
    while True:
        raw = input("  > ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        # also allow typing the key directly
        for key, _ in options:
            if raw.lower() == key.lower():
                return key
        print(f"  Please enter a number between 1 and {len(options)}.")

# ─── Game state ───────────────────────────────────────────────────────────────

class GameState:
    def __init__(self):
        self.inventory = []
        self.current_room = "kitchen"
        self.flags = {
            # quest progress
            "quest_started": False,
            "quest_complete": False,
            # item collected flags
            "has_egg":   False,
            "has_milk":  False,
            "has_flour": False,
            # optional achievements
            "helped_miller":   False,
            "stole_egg":       False,
            "befriended_fred": False,
            "freed_prisoner":  False,
            "spoke_to_duke":   False,
            "found_secret_recipe": False,
            "defeated_guard_captain": False,
            # exploration
            "visited_dungeon": False,
            "visited_forest":  False,
            "market_explored": False,
        }
        self.player_name = "Adventurer"
        self.reputation = 0   # -5 .. +5, affects dialogue
        self.health = 10
        self.max_health = 10
        self.combat_wins = 0
        # Timer
        self.time_limit = 600        # 10 minutes in seconds
        self.start_time = None       # set when quest begins
        self.timer_active = False

    def add_item(self, item):
        if item not in self.inventory:
            self.inventory.append(item)
            print(f"\n  ✦ {item.title()} added to inventory.")

    def remove_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)

    def has_item(self, item):
        return item in self.inventory

    def set_flag(self, flag, value=True):
        self.flags[flag] = value

    def flag(self, flag):
        return self.flags.get(flag, False)

    def ingredients_collected(self):
        return self.flag("has_egg") and self.flag("has_milk") and self.flag("has_flour")

    def show_inventory(self):
        print()
        divider()
        if self.inventory:
            print(f"  Inventory: {', '.join(self.inventory)}")
        else:
            print("  Inventory: (empty)")
        print(f"  Health: {'♥ ' * self.health}{'♡ ' * (self.max_health - self.health)}")
        rep_label = "Virtuous" if self.reputation >= 3 else "Shady" if self.reputation <= -3 else "Neutral"
        print(f"  Reputation: {rep_label} ({self.reputation:+d})")
        divider()

    def take_damage(self, dmg):
        self.health = max(0, self.health - dmg)

    def heal(self, amt):
        self.health = min(self.max_health, self.health + amt)

    def is_dead(self):
        return self.health <= 0

    # ── Timer helpers ──────────────────────────────────────────────────────
    def start_timer(self):
        self.start_time = time.time()
        self.timer_active = True

    def elapsed(self):
        if self.start_time is None:
            return 0
        return int(time.time() - self.start_time)

    def remaining(self):
        return max(0, self.time_limit - self.elapsed())

    def is_out_of_time(self):
        return self.timer_active and self.remaining() == 0

    def timer_bar(self):
        """Return a compact timer string for the prompt line."""
        if not self.timer_active:
            return ""
        secs = self.remaining()
        mins = secs // 60
        s    = secs % 60
        # colour cue via ASCII: show urgency brackets
        if secs <= 60:
            tag = f"[!!!  {mins}:{s:02d}  !!!]"
        elif secs <= 180:
            tag = f"[!!  {mins}:{s:02d}  !!]"
        else:
            tag = f"[{mins}:{s:02d}]"
        return tag


def labeled_exits(room_key):
    """
    Return a human-readable exit string like:
      north (Castle Great Hall)  |  south (Courtyard)  |  down (Dungeon)
    """
    room = ROOMS[room_key]
    parts = []
    for direction, dest_key in room["exits"].items():
        dest_name = ROOMS[dest_key]["name"] if dest_key in ROOMS else dest_key
        parts.append(f"{direction} ({dest_name})")
    return "  |  ".join(parts)


G = GameState()

# ─── Room descriptions ────────────────────────────────────────────────────────

ROOMS = {
    "kitchen": {
        "name": "Lumbridge Castle Kitchen",
        "desc": (
            "Steam rolls through the castle kitchen. Copper pots hang from iron hooks, "
            "and the hearth roars with orange flame. The smell of old spices and burnt "
            "bread hangs in the air. The head cook, a stout man named Giliedan, paces "
            "frantically near the chopping block."
        ),
        "exits": {"south": "castle-hall"},
        "items": ["knife"],
    },
    "castle-hall": {
        "name": "Lumbridge Castle Great Hall",
        "desc": (
            "Tapestries depicting ancient battles line the stone walls. Torches flicker "
            "in iron sconces. The great hall stretches high overhead, its vaulted ceiling "
            "lost in shadow. Servants hurry past with laden trays. A staircase descends "
            "into darkness to the north-east."
        ),
        "exits": {"north": "kitchen", "south": "outside", "down": "dungeon"},
        "items": [],
    },
    "dungeon": {
        "name": "Lumbridge Castle Dungeon",
        "desc": (
            "The air turns cold and damp. Torchlight barely reaches the slick stone walls. "
            "Chains rattle in a distant cell. Something growls from the deeper darkness. "
            "The stairs back up to the hall are behind you."
        ),
        "exits": {"up": "castle-hall"},
        "items": ["rusty key"],
    },
    "prison-cell": {
        "name": "Forgotten Cell",
        "desc": (
            "A gaunt, pale figure slumps against the wall — a man in a tattered blue robe. "
            "He lifts his head slowly when he hears you. 'Please...' he rasps. "
            "'I've been locked here for months. The guard captain has the cell key.'"
        ),
        "exits": {"back": "dungeon"},
        "items": [],
    },
    "outside": {
        "name": "Castle Courtyard",
        "desc": (
            "Sunlight. A cobblestone courtyard opens before you, ringed by the castle "
            "walls. A gate leads south into town. Two guards in bronze armour stand watch, "
            "eyeing you lazily. A wooden notice board is pinned with parchment scraps."
        ),
        "exits": {"north": "castle-hall", "south": "town-square", "east": "duke-quarters"},
        "items": [],
    },
    "duke-quarters": {
        "name": "Duke Horacio's Antechamber",
        "desc": (
            "Red velvet curtains, gilded furniture, and the faint smell of pine resin. "
            "A butler stands at a polished desk, eyeing you with practiced disapproval. "
            "Through an inner door you can hear the Duke humming to himself."
        ),
        "exits": {"west": "outside"},
        "items": [],
    },
    "town-square": {
        "name": "Lumbridge Town Square",
        "desc": (
            "The heart of Lumbridge is alive with noise. Merchants cry their wares, "
            "children chase a dog through the mud, and an old man plays a lute "
            "badly near the fountain. Roads branch off in every direction. "
            "A market stall catches your eye."
        ),
        "exits": {"north": "outside", "east": "chicken-farm", "west": "cow-farm",
                  "south": "south-road", "northeast": "market-stall"},
        "items": [],
    },
    "market-stall": {
        "name": "Merchant Elara's Stall",
        "desc": (
            "A colourful canvas awning shelters an impressive spread of goods. "
            "Merchant Elara, a sharp-eyed woman with ink-stained fingers, "
            "sizes you up immediately. 'Looking to trade, are we?'"
        ),
        "exits": {"southwest": "town-square"},
        "items": [],
    },
    "south-road": {
        "name": "South Road (Lumbridge Swamp Path)",
        "desc": (
            "The road narrows between ancient oak trees. Moss clings to every surface. "
            "Ahead the path dips toward the dark treeline of Lumbridge Swamp. "
            "A hooded figure sits on a fallen log, sharpening a dagger."
        ),
        "exits": {"north": "town-square", "south": "dark-forest"},
        "items": [],
    },
    "dark-forest": {
        "name": "Lumbridge Dark Forest",
        "desc": (
            "The canopy closes overhead, swallowing most of the light. Twisted roots "
            "cross the path. Strange mushrooms glow faintly blue. Something watches you "
            "from the trees — you can feel it. Deep in the undergrowth you spot the "
            "entrance to a cave."
        ),
        "exits": {"north": "south-road", "east": "hidden-cave"},
        "items": ["blue mushroom"],
    },
    "hidden-cave": {
        "name": "Hidden Cave",
        "desc": (
            "The cave smells of old ash and something sweet. Crude paintings cover the "
            "walls — animals, stars, a crown. At the far end sits a small stone altar "
            "with a rolled parchment on it."
        ),
        "exits": {"west": "dark-forest"},
        "items": ["ancient recipe"],
    },
    "chicken-farm": {
        "name": "Farmer Fred's Chicken Farm",
        "desc": (
            "A dozen chickens roam freely, pecking at the dirt. The farmhouse door "
            "is open, and you can hear Farmer Fred singing off-key inside. "
            "A henhouse sits in the corner, stuffed with straw."
        ),
        "exits": {"west": "town-square"},
        "items": [],
    },
    "cow-farm": {
        "name": "Beefy Bill's Cow Farm",
        "desc": (
            "Wide-eyed cows chew cud in the afternoon sun. A battered wooden sign "
            "reads 'BEEFY BILL'S DAIRY — FRESHEST MILK IN LUMBRIDGE.' "
            "Bill himself leans on a fence post, chewing on a stalk of grass."
        ),
        "exits": {"east": "town-square"},
        "items": ["empty bucket"],
    },
    "mill": {
        "name": "Lumbridge Windmill",
        "desc": (
            "The great sails of the windmill creak and groan, but they're not turning. "
            "Miller Myre stands at the door, arms crossed, staring up at the frozen mechanism "
            "with a look of profound frustration. Sacks of grain line the wall inside."
        ),
        "exits": {"south": "town-square"},
        "items": [],
    },
}

# Connect mill to town-square
ROOMS["town-square"]["exits"]["north"] = "outside"  # already set above
ROOMS["town-square"]["exits"]["northwest"] = "mill"

# ─── Narrative scenes ─────────────────────────────────────────────────────────

def scene_intro():
    print()
    slow_print("  Loading adventure...", 0.04)
    time.sleep(0.5)
    header("THE COOK'S ASSISTANT: A LUMBRIDGE ADVENTURE")
    slow_print(wrap(
        "The kingdom of Gielinor stretches wide and wild, but today your story begins "
        "in the modest town of Lumbridge — where a desperate cook, a missing recipe, "
        "and a Duke's birthday cake are about to change everything."
    ))
    print()
    slow_print("  What is your name, adventurer?")
    name = input("  > ").strip()
    if name:
        G.player_name = name
    print()
    slow_print(f"  Welcome, {G.player_name}. Your legend begins now.")
    pause()

def scene_kitchen_intro():
    header("LUMBRIDGE CASTLE KITCHEN")
    slow_print(wrap(
        f"The moment you step inside, the cook — a stout, red-faced man — grabs your "
        f"arm with floury hands."
    ))
    print()
    slow_print(wrap(
        '"THANK THE GODS! A traveller! Please, you must help me. The Duke\'s birthday '
        'feast is tonight and I need to bake his famous Lumbridge Fruitcake — but I\'ve '
        'run out of three key ingredients. Without them the whole celebration is ruined!"'
    ))
    print()
    slow_print(wrap(
        "He thrusts a crumpled recipe card at you. You can read the key ingredients:\n"
        "  • One fresh egg\n"
        "  • A bucket of creamy milk\n"
        "  • A pot of fine-milled flour"
    ))
    print()
    slow_print(wrap(
        '"I need all three. Please — will you fetch them for me?"'
    ))
    print()
    opt = choose([
        ("yes", "Of course — I'll help you, cook."),
        ("ask",  "What's in it for me?"),
        ("no",   "I'm far too busy for this."),
    ])
    if opt == "yes":
        slow_print(wrap(
            '"Bless you! Farmer Fred has chickens east of the square, Beefy Bill has cows '
            'to the west, and Miller Myre runs the windmill to the north. Hurry — please!"'
        ))
        G.reputation += 1
        G.set_flag("quest_started")
        G.start_timer()
        slow_print(wrap(
            f"\n  ⏰  You have {G.time_limit // 60} minutes to collect all ingredients "
            "and return to the kitchen. The clock is running!"
        ))
    elif opt == "ask":
        slow_print(wrap(
            '"Reward? I... yes, of course. Help me and the Duke will surely compensate you. '
            'You have my word as Giliedan, Royal Cook of Lumbridge!" He looks desperate enough '
            'that you believe him.'
        ))
        G.set_flag("quest_started")
        G.start_timer()
        slow_print(wrap(
            f"\n  ⏰  You have {G.time_limit // 60} minutes to collect all ingredients "
            "and return to the kitchen. The clock is running!"
        ))
    else:
        slow_print(wrap(
            '"Oh... I see." The cook deflates visibly. You feel a pang of guilt as you turn away. '
            'But something tells you this isn\'t the end of the story.'
        ))
        G.reputation -= 1
        slow_print(wrap(
            '(You can always return to the kitchen and speak to the cook again.)'
        ))
    pause()

# ─── Location events ──────────────────────────────────────────────────────────

def event_chicken_farm():
    if G.flag("has_egg"):
        slow_print(wrap("The hens cluck contentedly. You've already got your egg."))
        return

    header("FARMER FRED'S CHICKEN FARM")
    slow_print(wrap(
        "Farmer Fred ambles out of the farmhouse, hands in his pockets. He's a big man "
        "with a red beard and suspicious eyes."
    ))
    print()
    slow_print('"Aye? What d\'you want with my chickens?"')
    print()
    opt = choose([
        ("ask",    "Ask politely for an egg."),
        ("trade",  "Offer something in trade."),
        ("search", "Slip around back and search the henhouse yourself."),
        ("steal",  "Distract him and steal an egg."),
    ])

    if opt == "ask":
        if G.reputation >= 1:
            slow_print(wrap(
                '"A quest from the castle cook, is it? Ha! I love a good story. Here — take two, '
                'my hens have been busy."'
            ))
            slow_print(wrap("He hands you a pair of brown eggs with a grin."))
        else:
            slow_print(wrap(
                '"Hmm. You look honest enough. Go on then — one egg, and mind you don\'t scare '
                'the hens."'
            ))
        G.add_item("egg")
        G.set_flag("has_egg")
        G.reputation += 1
        G.set_flag("befriended_fred")

    elif opt == "trade":
        if G.has_item("blue mushroom"):
            slow_print(wrap(
                '"A forest mushroom! My wife loves those. She does something magical with them '
                'in soup. Deal! Take your egg, friend."'
            ))
            G.remove_item("blue mushroom")
            G.add_item("egg")
            G.set_flag("has_egg")
            G.reputation += 2
            G.set_flag("befriended_fred")
        else:
            slow_print(wrap(
                "\"What've you got, then?\" He peers at your pack. \"Nothing worth trading for. "
                "Come back when you've got something interesting.\""
            ))

    elif opt == "search":
        slow_print(wrap(
            "You sidle around to the henhouse. Fred watches you the whole time, arms folded."
        ))
        r = random.random()
        if r < 0.6:
            slow_print(wrap(
                '"Found one, did ye? Good. I suppose that\'s fair enough for a traveller in need." '
                "Fred shrugs and goes back inside."
            ))
            G.add_item("egg")
            G.set_flag("has_egg")
        else:
            slow_print(wrap(
                "\"HEY! Don't go poking around in there \u2014 you're disturbing them! Get out!\" "
                "Fred chases you off. You'll need a better approach."
            ))
            G.reputation -= 1

    elif opt == "steal":
        slow_print(wrap(
            "You point dramatically at the sky. 'Look! A giant eagle!' "
            "Fred stares. You slip a hand into the henhouse... and grab an egg. "
        ))
        r = random.random()
        if r < 0.4:
            slow_print(wrap(
                '"Nice try." Fred didn\'t move an inch. He\'s seen that trick before. '
                '"Give it back or I\'m calling the guards." You hand it over, red-faced.'
            ))
            G.reputation -= 2
        else:
            slow_print(wrap(
                "Success — barely. Fred turns back around just as you pocket it. "
                "Your hands are shaking. You feel guilty, but you have the egg."
            ))
            G.add_item("egg")
            G.set_flag("has_egg")
            G.set_flag("stole_egg")
            G.reputation -= 1
    pause()

def event_cow_farm():
    if G.flag("has_milk"):
        slow_print(wrap("The cows moo. You've already got your milk."))
        return

    header("BEEFY BILL'S COW FARM")
    slow_print(wrap(
        "Beefy Bill is a surprisingly small man for someone whose entire identity is dairy. "
        "He nods at you with professional calm."
    ))
    print()
    slow_print("\"Afternoon. Here for milk, I'd wager. Everyone is these days.\"")
    print()
    opt = choose([
        ("ask",   "Ask for a bucket of milk."),
        ("help",  "Offer to mend the broken fence in exchange."),
        ("milk",  "Ask if you can milk a cow yourself."),
    ])

    if opt == "ask":
        if G.flag("befriended_fred"):
            slow_print(wrap(
                '"Fred sent word you were coming. Any friend of Fred\'s is welcome here." '
                "He fills a bucket without another word."
            ))
            G.reputation += 1
        else:
            slow_print(wrap(
                '"That\'ll be two copper coins normally... but you look like you\'re on a '
                'mission. Fine. Take a bucket. Don\'t tell anyone I gave it free — I have '
                'a reputation to maintain."'
            ))
        G.add_item("bucket of milk")
        G.set_flag("has_milk")

    elif opt == "help":
        slow_print(wrap(
            "Bill raises an eyebrow. 'You know how to fence?' You nod confidently "
            "(you don't, but how hard can it be?)."
        ))
        slow_print(wrap(
            "Twenty minutes later, the fence is standing — crooked, but standing. "
            "Bill surveys your work. 'Good enough. Take the milk.'"
        ))
        G.add_item("bucket of milk")
        G.set_flag("has_milk")
        G.reputation += 1
        G.heal(1)  # felt good doing honest work

    elif opt == "milk":
        slow_print(wrap(
            "Bill shrugs. 'Bessie's calm today. Go ahead.' "
            "You approach the cow carefully. She eyes you with bovine suspicion. "
        ))
        r = random.random()
        if r < 0.7:
            slow_print(wrap(
                "After a clumsy few minutes, you fill the bucket. "
                "Bill looks quietly impressed. 'Not bad. You've done that before.'"
            ))
            G.add_item("bucket of milk")
            G.set_flag("has_milk")
        else:
            slow_print(wrap(
                "Bessie shifts and kicks the bucket across the yard. Bill winces. "
                "'Maybe... let me do it.' He refills the bucket himself and hands it over."
            ))
            G.add_item("bucket of milk")
            G.set_flag("has_milk")
    pause()

def event_mill():
    if G.flag("has_flour"):
        slow_print(wrap("The mill grinds steadily. You've already got your flour."))
        return

    header("LUMBRIDGE WINDMILL")
    slow_print(wrap(
        "Miller Myre looks like a man who hasn't slept in two days. He's staring at the "
        "mill's drive shaft, which is clearly jammed with something."
    ))
    print()
    slow_print(wrap(
        "\"The mechanism's seized up -- a stone got lodged in the gears yesterday. "
        "I can't mill anything. And you need flour, don't you? Everyone needs flour.\""
    ))
    print()
    opt = choose([
        ("fix",  "Offer to climb up and clear the jam."),
        ("ask",  "Ask if there's any pre-milled flour left in the sacks."),
        ("pay",  "Offer something valuable in exchange."),
    ])

    if opt == "fix":
        slow_print(wrap(
            "You climb the creaking stairs to the top of the windmill. "
            "Through a narrow hatch you can see the massive gear assembly. "
            "A fist-sized stone is wedged between two cogs."
        ))
        print()
        slow_print(wrap("You'll need to pry it loose. This will take some effort."))
        print()
        # mini puzzle
        attempts = 0
        while attempts < 3:
            attempts += 1
            act = choose([
                ("pry",   "Pry the stone with the knife (if you have one)."),
                ("push",  "Try to push the stone free with your hands."),
                ("kick",  "Give the gear a good solid kick."),
            ])
            if act == "pry" and G.has_item("knife"):
                slow_print(wrap(
                    "You lever the knife under the stone and push. With a grinding shriek, "
                    "the stone pops free and the windmill lurches into motion. The sails "
                    "begin to turn. Myre shouts with joy from below."
                ))
                G.add_item("pot of flour")
                G.set_flag("has_flour")
                G.set_flag("helped_miller")
                G.reputation += 2
                break
            elif act == "push":
                slow_print(wrap("Your fingers slip. The stone doesn't budge. Try something else."))
            elif act == "kick":
                r = random.random()
                if r < 0.4:
                    slow_print(wrap(
                        "The stone dislodges with a CLANG. The windmill groans and starts turning. "
                        "'It worked!' Myre bellows. 'You mad genius!'"
                    ))
                    G.add_item("pot of flour")
                    G.set_flag("has_flour")
                    G.set_flag("helped_miller")
                    G.reputation += 1
                    break
                else:
                    slow_print(wrap("You stub your toe. Badly. The stone doesn't move."))
                    G.take_damage(1)
        else:
            slow_print(wrap(
                "After several failed attempts, Myre calls up: 'Never mind! I found a sack "
                "of pre-milled flour in the back. It's a bit old but it'll do.'"
            ))
            G.add_item("pot of flour")
            G.set_flag("has_flour")

    elif opt == "ask":
        slow_print(wrap(
            "Myre strokes his chin. 'There might be one pre-milled sack... but it's old. "
            "Good enough for the castle, I suppose. Hang on.'"
        ))
        slow_print(wrap(
            "He digs behind a stack of grain and produces a slightly dusty pot. "
            "'Here. Won't be as fine as fresh-milled, but it'll bake.'"
        ))
        G.add_item("pot of flour")
        G.set_flag("has_flour")

    elif opt == "pay":
        if G.has_item("ancient recipe"):
            slow_print(wrap(
                "You show Myre the ancient recipe from the cave. His eyes go wide. "
                "'Is this... the old Lumbridge bread recipe? My grandfather used to talk about this!' "
                "He grabs the parchment and presses a pot of the finest flour into your hands. "
                "'Take it all!'"
            ))
            G.remove_item("ancient recipe")
            G.set_flag("found_secret_recipe")  # track for ending
            G.add_item("pot of flour")
            G.set_flag("has_flour")
            G.set_flag("helped_miller")
            G.reputation += 2
        else:
            slow_print(wrap(
                "'Got anything worth trading?' You show him your pack. He shakes his head. "
                "'Nothing useful there. Try fixing the mill — that's the real payment.'"
            ))
    pause()

def event_dungeon():
    G.set_flag("visited_dungeon")
    header("LUMBRIDGE CASTLE DUNGEON")
    slow_print(wrap(
        "The dungeon is darker than you expected. Your eyes adjust slowly. "
        "Two doors branch off the main corridor — one leads to a locked cell, "
        "one to a guard's post where you can hear snoring."
    ))
    if not G.flag("freed_prisoner"):
        slow_print(wrap(
            "Through the bars of the cell you can see a haggard figure in a blue robe."
        ))
    print()
    opt = choose([
        ("cell",   "Approach the locked cell."),
        ("guard",  "Sneak toward the guard post."),
        ("fight",  "Draw your weapon and look for monsters to fight."),
        ("up",     "Head back upstairs to the castle hall."),
    ])

    if opt == "cell":
        event_prison_cell()
    elif opt == "guard":
        event_guard_post()
    elif opt == "fight":
        event_dungeon_combat()
    elif opt == "up":
        G.current_room = "castle-hall"
        slow_print("You climb the stairs back to the castle hall.")

def event_prison_cell():
    header("FORGOTTEN CELL")
    slow_print(wrap(
        "The figure looks up. He's older than he first appeared, with deep-set eyes "
        "and a trim beard gone ragged from captivity."
    ))
    print()
    slow_print(wrap(
        "\"You're not a guard...\" he whispers. \"Please -- can you get me out? The guard "
        "captain keeps the key. His post is just down the corridor. I am Wizard Bedabin -- "
        "I was imprisoned for... political reasons. Free me and I'll reward you well.\""
    ))
    print()
    if G.flag("freed_prisoner"):
        slow_print(wrap("The cell is already empty. Bedabin is long gone."))
        pause()
        return

    opt = choose([
        ("get_key", "Go find the guard captain's key."),
        ("decline", "This isn't your problem. Leave."),
        ("pick",    "Try to pick the lock yourself."),
    ])

    if opt == "get_key":
        slow_print(wrap(
            "You nod to the wizard. 'I'll see what I can do.' He slumps back against the wall, "
            "eyes bright with renewed hope."
        ))
        event_guard_post(goal="key")
    elif opt == "decline":
        slow_print(wrap(
            "You walk away. The wizard calls softly after you: 'I understand. Please — "
            "just... think about it.'"
        ))
        G.reputation -= 1
    elif opt == "pick":
        if G.has_item("knife"):
            slow_print(wrap(
                "You work the knife into the lock. After a tense few minutes — CLICK. "
                "The door swings open."
            ))
            slow_print(wrap(
                "Bedabin staggers out and grips your arm. 'Thank you. Truly. Take this — "
                "it saved my life once, perhaps it will serve you.' He presses a vial of "
                "glowing liquid into your hand before limping toward the stairs."
            ))
            G.add_item("healing potion")
            G.set_flag("freed_prisoner")
            G.reputation += 2
        else:
            slow_print(wrap(
                "Without any tool, you can't get the lock open. You'll need a key — "
                "or something to pick it with."
            ))
    pause()

def event_guard_post(goal=None):
    header("DUNGEON GUARD POST")
    slow_print(wrap(
        "A guard captain sits slumped in a chair, snoring loudly. A ring of keys "
        "hangs from his belt. On the table: a half-eaten meat pie, a candle, "
        "and a logbook."
    ))
    print()
    opt = choose([
        ("steal",  "Quietly lift the keys from his belt."),
        ("wake",   "Wake him up and try to convince him."),
        ("fight",  "Challenge the captain to a fight."),
        ("leave",  "Slip back out quietly."),
    ])

    if opt == "steal":
        r = random.random()
        if r < 0.55:
            slow_print(wrap(
                "Your fingers are steady. The keys come free without a sound. "
                "The captain snores on."
            ))
            _free_wizard()
        else:
            slow_print(wrap(
                "The captain stirs. 'EH? WHO'S THERE?' He grabs his sword. You back away quickly "
                "before he fully wakes, but he's now on alert — and angry."
            ))
            G.take_damage(1)
            G.reputation -= 1
    elif opt == "wake":
        slow_print(wrap(
            "The captain blinks awake, hand already on his sword. "
            "'What in— who are you? State your business!'"
        ))
        print()
        opt2 = choose([
            ("quest",  "Explain you're on a quest for the castle cook."),
            ("bribe",  "Offer something valuable."),
            ("bluff",  "Claim you have orders from the Duke himself."),
        ])
        if opt2 == "quest":
            slow_print(wrap(
                "'The cook's errand boy, eh?' He looks skeptical. "
                "'What's it worth to me to let a prisoner go?' He doesn't budge."
            ))
        elif opt2 == "bribe":
            if G.has_item("healing potion") or G.has_item("blue mushroom"):
                item = "healing potion" if G.has_item("healing potion") else "blue mushroom"
                slow_print(wrap(
                    f"You offer the {item}. He examines it. 'Fine. Take the key and "
                    "don't tell anyone I was sleeping.' He unclips the key and "
                    "tosses it to you."
                ))
                G.remove_item(item)
                _free_wizard()
            else:
                slow_print(wrap("'Nothing worth my job. Get out of my sight.'"))
        elif opt2 == "bluff":
            if G.reputation >= 2:
                slow_print(wrap(
                    "You square your shoulders and speak with authority. "
                    "The captain's eyes widen. 'The Duke... yes, of course. I'll release him "
                    "at once, my lord. Sorry for the trouble.' He fumbles for the key."
                ))
                _free_wizard()
                G.set_flag("defeated_guard_captain")
            else:
                slow_print(wrap(
                    "He narrows his eyes. 'Duke's orders would come with a royal seal. "
                    "You're no messenger.' He stands and draws his sword."
                ))
                event_dungeon_combat(forced=True)
    elif opt == "fight":
        event_dungeon_combat(forced=True)
    elif opt == "leave":
        slow_print(wrap("You back quietly into the corridor."))
    pause()

def _free_wizard():
    if G.flag("freed_prisoner"):
        return
    slow_print(wrap(
        "You hurry to the cell and unlock it. Bedabin steadies himself on the wall "
        "and looks at you with genuine gratitude."
    ))
    slow_print(wrap(
        '"I won\'t forget this. When the time comes, I\'ll make sure you\'re rewarded properly. '
        'For now — take this." He hands you a small vial of glowing liquid.'
    ))
    G.add_item("healing potion")
    G.set_flag("freed_prisoner")
    G.reputation += 3

def event_dungeon_combat(forced=False):
    header("COMBAT!")
    if forced:
        slow_print(wrap(
            "The guard captain draws his sword and charges. You have no choice but to fight."
        ))
    else:
        enemies = ["dungeon rat", "skeletal warrior", "cave goblin", "giant spider"]
        enemy = random.choice(enemies)
        slow_print(wrap(f"A {enemy} lunges from the shadows. Battle begins!"))

    enemy_hp = random.randint(2, 4)
    rounds = 0
    while enemy_hp > 0 and G.health > 0:
        rounds += 1
        print(f"\n  Your HP: {G.health}/{G.max_health}  |  Enemy HP: {enemy_hp}")
        print()
        act = choose([
            ("attack", "Attack!"),
            ("dodge",  "Dodge and look for an opening."),
            ("potion", "Drink healing potion (if you have one)."),
            ("run",    "Run away!"),
        ])

        if act == "attack":
            dmg = random.choices([0, 1, 2, 3], weights=[0.15, 0.35, 0.35, 0.15])[0]
            if dmg == 0:
                slow_print("  Your swing goes wide. The enemy steps aside.")
            else:
                slow_print(f"  You hit for {dmg} damage!")
                enemy_hp -= dmg

            # enemy hits back
            if enemy_hp > 0:
                edm = random.choices([0, 1, 2], weights=[0.3, 0.5, 0.2])[0]
                if edm == 0:
                    slow_print("  The enemy swings but misses.")
                else:
                    slow_print(f"  The enemy hits you for {edm} damage!")
                    G.take_damage(edm)

        elif act == "dodge":
            slow_print("  You roll aside. The enemy's strike misses. You look for an opening.")
            dmg = random.choices([0, 1, 2], weights=[0.2, 0.5, 0.3])[0]
            if dmg > 0:
                slow_print(f"  You find a gap and deal {dmg} damage!")
                enemy_hp -= dmg
            else:
                slow_print("  But you can't find an opening this round.")

        elif act == "potion":
            if G.has_item("healing potion"):
                G.remove_item("healing potion")
                G.heal(4)
                slow_print(f"  You drink the potion. HP restored to {G.health}.")
            else:
                slow_print("  You have no healing potion.")

        elif act == "run":
            slow_print(wrap("You break away and sprint for the stairs. The enemy snarls behind you."))
            G.current_room = "castle-hall"
            pause()
            return

    if G.is_dead():
        slow_print(wrap(
            "\nThe world goes dark. You wake up in the castle hall, stripped of your pack. "
            "Everything is gone..."
        ))
        G.inventory.clear()
        G.health = G.max_health // 2
        G.set_flag("has_egg", False)
        G.set_flag("has_milk", False)
        G.set_flag("has_flour", False)
        G.current_room = "castle-hall"
    else:
        G.combat_wins += 1
        slow_print(wrap(f"\nVictory! You stand over the fallen enemy, breathing hard."))
        if random.random() < 0.4:
            loot = random.choice(["gold coin", "old boot", "mystery vial", "torn map"])
            G.add_item(loot)
            slow_print(wrap(f"You find: {loot}."))
        G.reputation += 1
    pause()

def event_market_stall():
    header("MERCHANT ELARA'S STALL")
    slow_print(wrap(
        "Elara's stall is packed: dried herbs, bottled things, odd-looking tools, "
        "and two crates labeled 'MISC.' She watches you with amused patience."
    ))
    print()
    slow_print('"Trade? Information? Either costs something."')
    print()
    opt = choose([
        ("info",  "Ask her what she knows about the Duke's birthday."),
        ("buy",   "Ask about her wares."),
        ("leave", "Leave the stall."),
    ])

    if opt == "info":
        slow_print(wrap(
            '"The Duke? Oh, he\'s been impossible lately. Apparently the old Royal Chef '
            'retired and they hired that Giliedan fellow on short notice. '
            'Between you and me — the Duke absolutely expects his fruitcake. '
            'If it doesn\'t appear, heads will roll. Figuratively. Probably."'
        ))
        slow_print(wrap(
            '"There\'s also a rumour that a wizard was locked up in the dungeon for '
            'knowing too much about the Duke\'s... finances. Not my business."'
        ))
        G.set_flag("market_explored")

    elif opt == "buy":
        slow_print(wrap(
            '"I\'ve got blue mushroom antidote, blank parchment, and a compass — '
            'all one good trade each. What\'ve you got?"'
        ))
        if G.has_item("gold coin"):
            slow_print(wrap('"Ooh, a gold coin. Now we\'re talking."'))
            opt2 = choose([
                ("antidote", "Buy the antidote."),
                ("compass",  "Buy the compass."),
                ("pass",     "Never mind."),
            ])
            if opt2 != "pass":
                item = "antidote" if opt2 == "antidote" else "compass"
                G.remove_item("gold coin")
                G.add_item(item)
                slow_print(f'  "Pleasure doing business," Elara says, wrapping the {item}.')
        else:
            slow_print(wrap('"You don\'t have anything worth trading right now."'))

    elif opt == "leave":
        slow_print(wrap('"Come back when your pockets are heavier!"'))
    pause()

def event_duke():
    header("DUKE HORACIO'S ANTECHAMBER")
    slow_print(wrap(
        "The butler raises an eyebrow at your appearance but allows you through — "
        "barely. The Duke is standing at a tall window, hands clasped behind his back."
    ))
    print()
    if not G.flag("spoke_to_duke"):
        slow_print(wrap(
            '"Ah, a visitor. Are you here about the cake? Giliedan said he\'d send '
            'someone reliable." He turns. "I trust you\'re reliable?"'
        ))
        opt = choose([
            ("yes",  '"Absolutely, Your Grace."'),
            ("maybe", '"I\'m doing my best."'),
        ])
        if opt == "yes":
            slow_print(wrap(
                '"Good. Good. I\'ve had that cake every birthday since I was twelve. '
                'It\'s more than tradition — it\'s the only constant in an uncertain world." '
                "He looks briefly vulnerable. Then straightens. 'Don't let me down.'"
            ))
            G.reputation += 1
        else:
            slow_print(wrap(
                '"Your best will have to do." He turns back to the window. '
                "'Lumbridge deserves better than 'trying'.'"
            ))
        G.set_flag("spoke_to_duke")
    else:
        slow_print(wrap(
            '"Still collecting ingredients? Time is running out, adventurer. '
            "The feast is this evening.'"
        ))
    pause()

def event_south_road():
    header("SOUTH ROAD")
    slow_print(wrap(
        "The hooded figure on the log looks up as you approach. "
        "His face is young but his eyes are old. He's sharpening a curved dagger "
        "with practiced ease."
    ))
    print()
    slow_print('"Heading into the forest? Most folk don\'t come back the same."')
    print()
    opt = choose([
        ("talk",    "Ask what he knows about the forest."),
        ("ignore",  "Walk past without speaking."),
        ("boast",   "Tell him you fear nothing."),
    ])
    if opt == "talk":
        slow_print(wrap(
            '"There\'s a cave due east through the trees. Old, old place. '
            'The kind of old that predates the town. Something\'s kept in there — '
            'writing, I think. Worth a look if you\'re curious." '
            "He goes back to sharpening his blade. Conversation over."
        ))
        G.set_flag("visited_forest")
    elif opt == "ignore":
        slow_print(wrap("He watches you go without another word."))
    elif opt == "boast":
        slow_print(wrap(
            '"Sure you don\'t." He smiles thinly and says nothing else.'
        ))
    pause()

def event_dark_forest():
    G.set_flag("visited_forest")
    header("LUMBRIDGE DARK FOREST")
    slow_print(wrap(
        "The forest is alive with sounds that don't quite make sense at noon. "
        "Twigs snap somewhere to your left. The blue mushrooms pulse gently "
        "in the dim light — beautiful and slightly unsettling."
    ))
    print()
    if "blue mushroom" in ROOMS["dark-forest"]["items"]:
        slow_print(wrap("Several blue mushrooms grow near the path."))
        opt = choose([
            ("take",  "Pick a blue mushroom."),
            ("cave",  "Head east toward the cave entrance."),
            ("leave", "This place unsettles you. Leave."),
        ])
        if opt == "take":
            G.add_item("blue mushroom")
            ROOMS["dark-forest"]["items"].remove("blue mushroom")
            slow_print(wrap("You carefully pick a mushroom. It glows faintly in your palm."))
        elif opt == "cave":
            G.current_room = "hidden-cave"
            return
        elif opt == "leave":
            G.current_room = "south-road"
            return
    else:
        opt = choose([
            ("cave",  "Head east toward the cave entrance."),
            ("leave", "Leave the forest."),
        ])
        if opt == "cave":
            G.current_room = "hidden-cave"
            return
        else:
            G.current_room = "south-road"
            return
    pause()

def event_hidden_cave():
    header("HIDDEN CAVE")
    slow_print(wrap(
        "The cave smells of ancient fires. The painted walls show scenes of "
        "people gathered around a great table — celebration after celebration, "
        "century after century. At the stone altar lies a single rolled parchment."
    ))
    print()
    if "ancient recipe" in ROOMS["hidden-cave"]["items"]:
        opt = choose([
            ("take",  "Take the parchment."),
            ("read",  "Read it without taking it."),
            ("leave", "Leave it undisturbed."),
        ])
        if opt == "take":
            G.add_item("ancient recipe")
            ROOMS["hidden-cave"]["items"].remove("ancient recipe")
            slow_print(wrap(
                "You unroll the parchment carefully. It's a recipe — "
                "'The Original Lumbridge Celebration Loaf' — written in a hand "
                "centuries old. Someone will want this."
            ))
        elif opt == "read":
            slow_print(wrap(
                "The recipe is remarkable — ingredients you've never heard of, "
                "a method that must have taken generations to perfect. "
                "It's the kind of thing that should be shared, not left in a cave."
            ))
        elif opt == "leave":
            slow_print(wrap("You leave it as you found it. Some things belong where they are."))
            G.reputation += 1
    else:
        slow_print(wrap("The altar is empty. You've already taken what was here."))
    pause()

# ─── Ending ───────────────────────────────────────────────────────────────────

def compute_ending():
    """Determine which ending the player gets."""
    rep = G.reputation
    freed = G.flag("freed_prisoner")
    stole = G.flag("stole_egg")
    helped = G.flag("helped_miller")
    secret = G.flag("found_secret_recipe")
    spoke_duke = G.flag("spoke_to_duke")

    if rep >= 5 and freed and helped and spoke_duke:
        return "legendary"
    elif secret and freed:
        return "wizard_scholar"
    elif rep >= 3 and not stole:
        return "hero"
    elif stole and rep < 0:
        return "rogue"
    elif rep < -2:
        return "infamy"
    else:
        return "standard"

def scene_ending():
    header("THE COOK'S KITCHEN — FINALE")
    slow_print(wrap(
        f"You return to the kitchen and lay the ingredients on the chopping block. "
        f"Egg, milk, flour — all of it. Giliedan stares at the collection for a long "
        f"moment, then looks at you."
    ))
    print()

    ending = compute_ending()

    if ending == "legendary":
        slow_print(wrap(
            '"I... I don\'t know what to say. You fixed the mill, freed a prisoner, '
            'spoke to the Duke himself, and brought everything back in time." '
            "He begins mixing immediately, hands steady now. "
            '"The Duke will hear of this. The whole kingdom will hear of this."'
        ))
        print()
        slow_print(wrap(
            "The feast that evening is spectacular. The cake is perfect. "
            "Duke Horacio calls you forward and, in front of the entire court, "
            "names you an Official Friend of Lumbridge — a title that hasn't been "
            "granted in forty years."
        ))
        print()
        boxprint("✦ ENDING: LEGEND OF LUMBRIDGE ✦  The rarest outcome. Well earned.", char='═')

    elif ending == "wizard_scholar":
        slow_print(wrap(
            "The cake is baked — but what happens next surprises everyone. "
            "Wizard Bedabin appears at the feast, fully restored. "
            "He presents the ancient recipe to the court as a gift from you, "
            "and the Duke — moved nearly to tears — declares it will be kept "
            "in the royal archive."
        ))
        print()
        boxprint("✦ ENDING: THE SCHOLAR'S GIFT ✦  History remembered. Magic rewarded.", char='═')

    elif ending == "hero":
        slow_print(wrap(
            "The cake comes out perfectly — golden, fragrant, magnificent. "
            "The Duke takes one bite and closes his eyes. "
            "'That\'s it,' he says quietly. 'That\'s exactly it.' "
            "Giliedan shakes your hand for a very long time."
        ))
        print()
        boxprint("✦ ENDING: THE COOK'S HERO ✦  Honest, kind, and competent. Lumbridge remembers.", char='═')

    elif ending == "rogue":
        slow_print(wrap(
            "The cake is baked. It works. But Farmer Fred heard about his egg — "
            "word travels fast in a small town. He's waiting for you outside the castle. "
            "He doesn't look angry, exactly. Just disappointed."
        ))
        print()
        slow_print(wrap(
            '"I would\'ve given it to you," he says quietly. "You only had to ask."'
        ))
        print()
        boxprint("✦ ENDING: THE NECESSARY THIEF ✦  The job is done. But at a cost.", char='═')

    elif ending == "infamy":
        slow_print(wrap(
            "The cake is baked, somehow. But the stories that follow you out of "
            "Lumbridge are not flattering ones. You got the job done — no one can "
            "take that away — but 'the way you went about it' will be muttered "
            "in this town for years."
        ))
        print()
        boxprint("✦ ENDING: NECESSARY EVIL ✦  Results matter. So does everything else.", char='═')

    else:  # standard
        slow_print(wrap(
            "The cake is baked. The Duke is pleased. Giliedan weeps with relief "
            "and presses a warm roll into your hands as payment. "
            "It's not much — but you feel good about it."
        ))
        print()
        boxprint("✦ ENDING: COOK'S ASSISTANT ✦  Quest complete. The Duke is fed.", char='═')

    print()
    slow_print(f"  Reputation: {G.reputation:+d}  |  Combat wins: {G.combat_wins}  |  Prisoner freed: {G.flag('freed_prisoner')}")
    slow_print(f"  Secret found: {G.flag('found_secret_recipe')}  |  Duke spoken to: {G.flag('spoke_to_duke')}")
    print()
    slow_print("  Thanks for playing, " + G.player_name + ".")
    divider()
    sys.exit()

# ─── Room rendering & main loop ───────────────────────────────────────────────

def render_room(room_key):
    room = ROOMS[room_key]
    header(room["name"])
    slow_print(wrap(room["desc"]), 0.012)
    print()

    # items on the ground
    ground = ROOMS[room_key].get("items", [])
    if ground:
        slow_print(f"  You see: {', '.join(ground)}.")

    # labeled exits
    slow_print(f"  Exits: {labeled_exits(room_key)}")
    print()

def handle_command(raw, room_key):
    cmd = raw.strip().lower()
    room = ROOMS[room_key]

    # meta
    if cmd in ("quit", "exit", "q"):
        print("\n  Farewell, " + G.player_name + ".")
        sys.exit()
    if cmd in ("i", "inv", "inventory"):
        G.show_inventory()
        return room_key
    if cmd in ("help", "?"):
        print()
        print("  MOVEMENT:   n / s / e / w / u / d  (or: north, south, go north, etc.)")
        print("  ITEMS:      take <item>  |  use <item>  |  drink <item>")
        print("  INFO:       look  (re-show room)  |  i  (inventory)  |  help")
        print("  QUIT:       q")
        print()
        print("  Tip: exits are always shown in the prompt line. Just type the direction.")
        return room_key
    if cmd == "look":
        render_room(room_key)
        return room_key

    # movement
    direction_aliases = {
        "n": "north", "s": "south", "e": "east", "w": "west",
        "u": "up", "d": "down", "ne": "northeast", "nw": "northwest",
        "se": "southeast", "sw": "southwest",
    }
    all_direction_words = set(direction_aliases.keys()) | set(direction_aliases.values())

    def resolve_direction(word):
        if word in room["exits"]:
            return word
        if word in direction_aliases and direction_aliases[word] in room["exits"]:
            return direction_aliases[word]
        return None

    nav_cmd = cmd[3:].strip() if cmd.startswith("go ") else cmd
    move = resolve_direction(nav_cmd)

    if move:
        return room["exits"][move]

    # recognisable direction word but no exit that way
    if nav_cmd in all_direction_words:
        exits = list(room["exits"].keys())
        slow_print(f"  You can't go {nav_cmd} from here.  Available exits: {', '.join(exits)}")
        return room_key

    # take items
    if cmd.startswith("take ") or cmd.startswith("pick up "):
        item_name = cmd.replace("take ", "").replace("pick up ", "").strip()
        ground = room.get("items", [])
        match = next((i for i in ground if i.lower() == item_name), None)
        if match:
            G.add_item(match)
            ground.remove(match)
            if match == "rusty key" and not G.flag("freed_prisoner"):
                slow_print(wrap(
                    "It's a rusty old key. Could unlock something down here."
                ))
        else:
            slow_print(f"  There is no '{item_name}' here to take.")
        return room_key

    # use/drink
    if cmd.startswith("use ") or cmd.startswith("drink "):
        item_name = cmd.replace("use ", "").replace("drink ", "").strip()
        if item_name == "healing potion" and G.has_item("healing potion"):
            G.remove_item("healing potion")
            G.heal(4)
            slow_print(f"  You drink the potion. HP restored to {G.health}.")
        elif item_name == "rusty key" and room_key == "dungeon" and not G.flag("freed_prisoner"):
            slow_print(wrap(
                "You try the key in the cell door — it fits! You swing the door open. "
                "Bedabin shuffles out, blinking."
            ))
            slow_print(wrap(
                '"You found the key... Thank you. Here — this is all I have left." '
                "He hands you a small vial."
            ))
            G.add_item("healing potion")
            G.set_flag("freed_prisoner")
            G.reputation += 2
        else:
            slow_print(f"  You can't use that here.")
        return room_key

    # talk / interact — handled by location events
    if cmd in ("talk", "interact", "look around", "search", "explore"):
        slow_print(wrap("  (Use the numbered menus when they appear, or type a direction to move.)"))
        return room_key

    slow_print(f"  I don't know how to '{raw}'.")
    slow_print("  Type 'help' for a list of commands.")
    return room_key


def location_event(room_key):
    """Fire the special event for a room, if any."""
    events = {
        "kitchen":      lambda: scene_kitchen_intro() if not G.flag("quest_started") else cook_status(),
        "chicken-farm": event_chicken_farm,
        "cow-farm":     event_cow_farm,
        "mill":         event_mill,
        "dungeon":      event_dungeon,
        "market-stall": event_market_stall,
        "duke-quarters": event_duke,
        "south-road":   event_south_road,
        "dark-forest":  event_dark_forest,
        "hidden-cave":  event_hidden_cave,
        "prison-cell":  event_prison_cell,
    }
    if room_key in events:
        events[room_key]()

def cook_status():
    slow_print(wrap("Giliedan looks up from his prep. 'How are the ingredients coming along?'"))
    missing = []
    if not G.flag("has_egg"):   missing.append("egg")
    if not G.flag("has_milk"):  missing.append("bucket of milk")
    if not G.flag("has_flour"): missing.append("pot of flour")
    if missing:
        slow_print(wrap(f'"Still need: {", ".join(missing)}. Please hurry!"'))
    else:
        scene_ending()

def main():
    scene_intro()
    G.current_room = "kitchen"

    # first visit always fires kitchen intro
    first_visit = {room: True for room in ROOMS}

    while True:
        room_key = G.current_room

        # render the room description on first visit or after returning
        if first_visit.get(room_key, True):
            render_room(room_key)
            first_visit[room_key] = False
            location_event(room_key)
        else:
            # brief reminder: room name + labeled exits
            room_data = ROOMS[room_key]
            ground = room_data.get("items", [])
            timer_str = f"  {G.timer_bar()}" if G.timer_active else ""
            print(f"\n  [{room_data['name']}]{timer_str}")
            print(f"  Exits: {labeled_exits(room_key)}", end="")
            if ground:
                print(f"  |  You see: {', '.join(ground)}", end="")
            print()

        # check win condition
        if room_key == "kitchen" and G.flag("quest_started") and G.ingredients_collected():
            scene_ending()

        # check timer expiry
        if G.is_out_of_time():
            print()
            divider('═')
            slow_print("  ⏰  TIME'S UP!")
            slow_print(wrap(
                "The feast bell tolls across Lumbridge. You sprint back to the kitchen, "
                "breathless -- but it's too late. The Duke's birthday feast has begun "
                "without the cake. Giliedan stares at you, devastated."
            ))
            slow_print(
                "I thought you'd make it, he whispers. The Duke will not be pleased."
            )
            divider('═')
            slow_print(f"\n  Final time: {G.elapsed() // 60}m {G.elapsed() % 60}s  |  Ingredients collected: "
                       f"{'egg ' if G.flag('has_egg') else ''}{'milk ' if G.flag('has_milk') else ''}{'flour' if G.flag('has_flour') else '(none)'}")
            print()
            slow_print("  GAME OVER — The Duke goes cakeless.")
            print()
            sys.exit()

        # check death
        if G.is_dead():
            slow_print(wrap(
                "\nYou collapse. The world spins and goes dark... "
                "You wake up outside the castle, stripped of your gear."
            ))
            G.inventory.clear()
            G.health = G.max_health // 2
            G.set_flag("has_egg", False)
            G.set_flag("has_milk", False)
            G.set_flag("has_flour", False)
            G.current_room = "outside"
            first_visit["outside"] = True
            continue

        # build prompt — show timer inline so player always sees it
        if G.timer_active:
            prompt = f"\n  {G.timer_bar()}  > "
        else:
            prompt = "\n  > "

        cmd = input(prompt).strip()
        if not cmd:
            continue

        new_room = handle_command(cmd, room_key)

        if new_room != room_key:
            G.current_room = new_room
            render_room(new_room)
            location_event(new_room)

if __name__ == "__main__":
    main()