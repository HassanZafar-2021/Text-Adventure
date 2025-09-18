import sys
# Text Adventure Game
rooms = {
    "kitchen": {
        "desc": "You are in the Lumbridge Castle kitchen. The cook looks worried and needs your help.",
        "south": "castle-hall"
    },
    "castle-hall": {
        "desc": "You are in the grand hall of Lumbridge Castle. Stairs lead up, and the kitchen is to the north. The castle exit is south. A staircase leads down to the dungeon.",
        "north": "kitchen",
        "south": "outside",
        "down": "dungeon",
    },
    "dungeon": {
        "desc": "You are in the dark, damp Lumbridge dungeon. Monsters lurk in the shadows. The stairs lead up.",
        "up": "castle-hall",
        "staircase": "castle-hall"
    },
    "outside": {
        "desc": "You are outside Lumbridge Castle. The castle entrance is to the north, and the town square is to the south.",
        "north": "castle-hall",
        "south": "town-square"
    },
    "town-square": {
        "desc": "You are in the Lumbridge town square. Shops and villagers are all around. The mill is to the north, the castle is to the south, the chicken farm is east, and the cow farm is west.",
        "north": "mill",
        "south": "outside",
        "east": "chicken-farm",
        "west": "cow-farm"
    },
    "chicken-farm": {
        "desc": "You are at the chicken farm. Chickens cluck and peck at the ground. The town square is west.",
        "west": "town-square"
    },
    "cow-farm": {
        "desc": "You are at the cow farm. Cows graze peacefully. The town square is east.",
        "east": "town-square"
    },
    "mill": {
        "desc": "You are at the windmill north of Lumbridge. The miller is here, and sacks of flour are everywhere. The town square is south.",
        "south": "town-square"
    }
}

current_room = "kitchen"
inventory = []
items = {
    "kitchen": ["knife"],
    "chicken-farm": ["egg"],
    "cow-farm": ["milk"],
    "mill": ["flour"],
    "town-square": ["musicbox"],
    "dungeon": []
}
import random
def dungeon_event():
    print("You hear growls and see monsters in the darkness.")
    fight_rounds = 0
    while True:
        print("Options: (a) Attack a monster, (b) Leave dungeon")
        choice = input("> ").strip().lower()
        if choice == "a":
            fight_rounds += 1
            outcome = random.choices([
                "win",
                "nothing",
                "lose"
            ], weights=[0.5, 0.3, 0.2])[0]
            if outcome == "win":
                print("You defeat a monster and feel triumphant!")
            elif outcome == "nothing":
                print("You swing and miss. The monster dodges!")
            elif outcome == "lose":
                print("A monster hits you! You feel weak.")
            if fight_rounds >= 5:
                print("You have fought for too long. The monsters overwhelm you!")
                print("You have died and lost all your inventory.")
                inventory.clear()
                print("You wake up at the castle hall, dazed and empty-handed.")
                return "castle-hall"
        elif choice == "b":
            print("You quickly leave the dungeon and return upstairs.")
            return "castle-hall"
        else:
            print("Choose a or b.")

# Quest state
quest_started = False
quest_completed = False
ingredients_needed = {"egg": False, "milk": False, "flour": False}
helped_miller = False
stole_egg = False

def print_inventory():
    if inventory:
        print("Inventory:", ", ".join(inventory))
    else:
        print("Inventory: (empty)")

def check_quest_completion():
    return all(ingredients_needed.values())

def kitchen_intro():
    print("\nThe cook wrings his hands nervously.")
    print('"Oh dear, oh dear! I need to bake a cake for the Duke, but I\'m missing the ingredients! Will you help me? (yes/no)"')
    while True:
        choice = input("> ").strip().lower()
        if choice == "yes":
            print('"Thank you! I need an egg, a bucket of milk, and a pot of flour. Please hurry!"')
            return True
        elif choice == "no":
            print('The cook sighs. "I suppose I\'ll have to find someone else..."')
            print("Game over.")
            sys.exit()
        else:
            print("Please answer 'yes' or 'no'.")

def chicken_farm_event():
    global stole_egg
    print("You see Farmer Fred watching his chickens.")
    print("Options: (a) Ask for an egg, (b) Search the coop, (c) Try to steal an egg")
    while True:
        choice = input("> ").strip().lower()
        if choice == "a":
            print('Farmer Fred smiles. "Of course! Take one, and good luck with the cake."')
            return "egg", False
        elif choice == "b":
            print("You search the coop and find a fresh egg.")
            return "egg", False
        elif choice == "c":
            print("You try to sneak an egg, but Fred catches you! He looks angry, but lets you go with a warning.")
            stole_egg = True
            return "egg", True
        else:
            print("Choose a, b, or c.")

def cow_farm_event():
    print("A dairy cow grazes nearby. There's a bucket here.")
    print("Options: (a) Milk the cow, (b) Look for the farmer, (c) Leave")
    while True:
        choice = input("> ").strip().lower()
        if choice == "a":
            print("You milk the cow and fill the bucket with fresh milk.")
            return "milk"
        elif choice == "b":
            print('The farmer nods. "Go ahead and take some milk!"')
            return "milk"
        elif choice == "c":
            print("You leave the cow farm.")
            return None
        else:
            print("Choose a, b, or c.")

def mill_event():
    global helped_miller
    print("The miller looks frustrated. The mill is jammed.")
    print("Options: (a) Offer to help fix the mill, (b) Ask for flour, (c) Try to sneak some flour")
    while True:
        choice = input("> ").strip().lower()
        if choice == "a":
            print("You help the miller fix the jam. Grateful, he gives you a pot of the finest flour.")
            helped_miller = True
            return "flour"
        elif choice == "b":
            print('The miller says, "If you help me fix the mill, I\'ll give you some flour!"')
        elif choice == "c":
            print("You try to sneak some flour, but the miller catches you. He scolds you, but lets you take a little.")
            return "flour"
        else:
            print("Choose a, b, or c.")

def ending():
    print("\nYou return to the kitchen with the ingredients.")
    if stole_egg:
        print('The cook frowns. "Did you steal this egg? I hope you didn\'t upset Farmer Fred..."')
    if helped_miller:
        print('The cook beams. "The miller says you were a great help! Thank you!"')
    if check_quest_completion():
        print('The cook quickly bakes the cake. The Duke is delighted! You have completed the Cook\'s Assistant quest!')
        print("Congratulations! Ending: Heroic Helper.")
    else:
        print('The cook sighs. "You\'re still missing something..."')
        print("Ending: Incomplete Quest.")
    print("Thanks for playing!")
    sys.exit()

# Main game loop
if not quest_started:
    print("\nWelcome to the Cook's Assistant Adventure!")
    quest_started = kitchen_intro()

while True:
    desc = rooms[current_room]["desc"]
    border = '-' * (len(desc) + 4)
    print(f"\n{border}\n| {desc} |\n{border}")
    # Show available directions
    directions = []
    for d in ["north", "south", "east", "west", "up", "down"]:
        if d in rooms[current_room]:
            directions.append(d)
    if directions:
        print("Available directions:", ", ".join(directions))
    print()  # Add a blank line between story and inventory
    print_inventory()
    if quest_started and not quest_completed and check_quest_completion() and current_room == "kitchen":
        quest_completed = True
        ending()

    command = input("> ").strip().lower()

    if command in ["exit", "quit"]:
        print("Thanks for playing!")
        sys.exit()

    elif current_room == "dungeon":
        # Enter dungeon event loop
        new_room = dungeon_event()
        current_room = new_room

    elif command in ["north", "south", "east", "west", "up", "down", "staircase"]:
        if command in rooms[current_room]:
            current_room = rooms[current_room][command]
        else:
            print("That is not a valid direction.")

    elif command.startswith("take "):
        item = command.split(" ", 1)[1]
        if item in items.get(current_room, []):
            inventory.append(item)
            items[current_room].remove(item)
            print(f"You took the {item}.")
            if item in ingredients_needed:
                ingredients_needed[item] = True
        else:
            print(f"There is no {item} here.")

    elif quest_started and current_room == "chicken-farm" and not ingredients_needed["egg"]:
        item, stole = chicken_farm_event()
        if item:
            inventory.append(item)
            if item in items.get(current_room, []):
                items[current_room].remove(item)
            ingredients_needed[item] = True

    elif quest_started and current_room == "cow-farm" and not ingredients_needed["milk"]:
        item = cow_farm_event()
        if item:
            inventory.append(item)
            if item in items.get(current_room, []):
                items[current_room].remove(item)
            ingredients_needed[item] = True

    elif quest_started and current_room == "mill" and not ingredients_needed["flour"]:
        item = mill_event()
        if item:
            inventory.append(item)
            if item in items.get(current_room, []):
                items[current_room].remove(item)
            ingredients_needed[item] = True

    else:
        print("You can't do that.")