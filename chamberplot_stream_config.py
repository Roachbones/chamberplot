# configures the stream plotter as it's running.
# sloppy and error-prone, sorry.

import time
import json
from pprint import pprint

def to_number(s):
    m = float(s)
    if float(m) == int(m):
        m = int(m)
    return m

while True: 
    command, param = input("enter command: ").split(" ", maxsplit=1)
    with open("chamberplot_stream_config.json") as file:
        config = json.load(file)
    if command == "add":
        for i in param.split(" "):
            config["interesting_masses"].append(to_number(i))
    elif command == "remove":
        for i in param.split(" "):
            config["interesting_masses"].remove(to_number(i))
    elif command == "masses":
        config["interesting_masses"] = [to_number(i) for i in param.split(" ")]
    elif command == "onion":
        config["onion_opacity"] = float(param)
    elif command == "floor":
        config["pressure_floor"] = float(param)
    else:
        print("invalid command. sorry this program is hard to use.")
        print("commands: add, remove, masses, onion, floor")
        continue

    config["nonce"] += 1
    config["interesting_masses"].sort()
    with open("chamberplot_stream_config.json", "w") as file:
        json.dump(config, file, indent=4)
