# "generates" data like the rga does, for testing the live plotter.

import os
import time
import random
#from chamberplot import parse_scan
 
real_scan_paths = [i for i in os.listdir("rga_data") if i.startswith("MassSpecData")]
real_scan_paths.sort()

for real_scan_path in real_scan_paths:
    with open("rga_data/" + real_scan_path) as file:
        real_lines = file.read()

    with open("spoofed_rga_data/" + real_scan_path, "w") as file:
        for real_line in real_lines:
            file.write(real_line)
            file.flush()
            time.sleep(0.001 * random.random())
        
        
