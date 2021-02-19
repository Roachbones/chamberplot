
# todo: investigate float imprecision?
# todo: calibrate Pirani pressure

"""
SCAN_PATH = "/home/rose/Documents/capstone/rga/MassSpecData-06507-20210210-171042.csv"
EVENTS = {
    181: "turned on gun filament",
    289: "opened Ar leak valve, turned off ion pump",
    349: "closed Ar leak valve",
    370: "turned up gun",
    569: "turned off gun, turned on ion pump"
}
"""

import datetime, time
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import xml.etree.ElementTree as ET

MASS_GUESSES = { # Used in legend labels.
    2: "$H_2$",
    18: "$H_2O$",
    40: "Ar"
}

def parse_scans(scan_path):
    """
    Reads the file at scan_path and outputs a list of scans,
    where each scan is a tuple of (xml_data, rows).
    xml_data is an xml tree of the scan's metadata.
    rows is a list of tuples of (time, mass, pressure) representing the data points.
    """
    with open(scan_path) as file:
        raw_data = file.read()[:-1]

    scans = []

    for scan_data in ["<?" + i for i in raw_data.split("<?")][1:]: # need better variable names. what is data?

        xml_length = scan_data.rindex(">") + 1
        xml_data, csv_data = scan_data[:xml_length], scan_data[xml_length + 1:].strip()

        xml_root = ET.fromstring(xml_data)

        raw_rows = csv_data.split("\n")
        if len(raw_rows) < 40:
            print("Skipping tiny scan of length {}.".format(len(raw_rows)))
            continue
        
        rows = []
        t_0 = None
        for raw_row in raw_rows:
            # t means time, m means mass, p means pressure
            raw_t, raw_m, raw_p = [i.strip() for i in raw_row[:-1].split(", ")]
            
            t = time.mktime(datetime.datetime.strptime(raw_t, "%Y/%m/%d %H:%M:%S.%f").timetuple())
            if t_0 is None:
                t_0 = t
            t = t - t_0 # normalize time

            # We'll need to change this if we ever monitor non-integer masses for some reason.
            m = int(float(raw_m))
            
            p = float(raw_p)
            
            rows.append((t, m, p))
        
        scans.append((xml_root, rows))
    
    return scans

def plot_file(scan_path, scan_index=None, events={}, pressure_floor=2e-10):
    

    if scan_index is None and len(scans) > 1:
        print("Found {} scans in file.".format(len(scans)))
        for i in range(len(scans)):
            print("\nPlotting scan {}.".format(i))
            plot(scan_path, i) # lazy
        return
    

def plot(scan_path, scan_index=None, events={}, pressure_floor=2e-10):
    """
    Plots the scan_indexth scan in scan_path, labelling specified events.
    
    scan_path: path to an RGA output file.
    scan_index: ordinal of the scan in the file. None plots every scan.
    events: a dictionary of events to label on the plot.
        Each key is a timestamp, in seconds, and its value is a string description
        of the event that happened at that time. For example:
        {
            181: "turned on gun filament",
            289: "turned off ion pump"
        }
    pressure_floor: y-axis minimum bound.
        Overridden if the absolute minimum of the data exceeds it.

    Currently only plots trends. todo: implement mass sweep
    """

    scans = parse_scans(scan_path)

    xml_root, rows = scans[scan_index]

    fig, ax = plt.subplots()
    ax.set_yscale("log")
    ax.set_ylabel("relative pressure (Pa)") # assuming that the rga is set to Pa
    ax.set_title("RGA: " + xml_root.find("ConfigurationParameters").get("DateTime"))

    mode = xml_root.find("OperatingParameters").get("Mode")
    
    if mode == "Trend":
        mass_series = {}
        for t, m, p in rows:
            if m not in mass_series:
                mass_series[m] = [t], [p]
            else:
                mass_series[m][0].append(t)
                mass_series[m][1].append(p)

        ax.set_xlabel("time (s)")

        pressure_lines = []

        for m, (times, pressures) in sorted(mass_series.items()):
            if m == 5: # Pirani pressure??
                continue
            if m == 999: # I sure hope we never have to detect mass 999!
                label = "Total pressure" 
            elif m in MASS_GUESSES:
                label = "{} ({}?)".format(m, MASS_GUESSES[m])
            else:
                label = str(m)
            pressure_lines.append(*ax.plot(times, pressures, label=label))

        event_lines = []

        for t, label in events.items():
            event_lines.append(ax.axvline(t, linestyle="--", label=label, color=next(ax._get_lines.prop_cycler)['color']))

        fig.legend(handles = pressure_lines + event_lines) # arrange the legend
    else:
        masses = []
        pressures = []
        for t, m, p in rows:
            masses.append(m)
            pressures.append(p)

        ax.bar(masses, pressures)

    # trim noise floor
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom=max(bottom, PRESSURE_FLOOR), top=top)


    plt.show()


EVENTS = { # time (in seconds): description. For example:  181: "turned on gun filament"
}

PRESSURE_FLOOR = 2e-10 # minimum of y axis. if minimum pressure is above this, use that instead.

SCAN_PATH = "rga_data/MassSpecData-06507-20210210-171042.csv"
SCAN_INDEX = None # each file can contain multiple scans due to a bug in the software.

plot(SCAN_PATH, SCAN_INDEX, EVENTS, PRESSURE_FLOOR)
