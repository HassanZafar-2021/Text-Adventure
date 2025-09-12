# Text Adventure Game
rooms = {
    "kitchen": {
        "desc": "You are in the Lumbridge Castle kitchen. The cook looks worried and needs your help.",
        "south": "castle-hall"
    },
    "castle-hall": {
        "desc": "You are in the grand hall of Lumbridge Castle. Stairs lead up, and the kitchen is to the north. The castle exit is south.",
        "north": "kitchen",
        "south": "outside"
    },
    "outside": {
        "desc": "You are outside Lumbridge Castle. The town stretches to the south, and the castle entrance is to the north.",
        "north": "castle-hall",
        "south": "town-square"
    },
    "town-square": {
        "desc": "You are in the Lumbridge town square. Shops and villagers are all around. The castle is to the north, and the chicken farm is east.",
        "north": "outside",
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
    "kitchen": ["flour"],
    "chicken-farm": ["egg"],
    "cow-farm": ["milk"]
}
while True:
    print("\n" + rooms[current_room]["desc"])
    command = input("> ").strip().lower()
    
    if command in ["exit", "quit"]:
        print("Thanks for playing!")
        break
    
    elif command in rooms[current_room]:
        current_room = rooms[current_room][command]
    
    elif command.startswith("take "):
        item = command.split(" ", 1)[1]
        if item in items.get(current_room, []):
            inventory.append(item)
            items[current_room].remove(item)
            print(f"You took the {item}.")
        else:
            print(f"There is no {item} here.")
    else:
        print("You can't do that.")