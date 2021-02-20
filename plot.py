
# todo: investigate float imprecision?
# todo: calibrate Pirani pressure

debug=[]

import datetime, time
import matplotlib
import matplotlib.pyplot as plt
#import numpy as np
import xml.etree.ElementTree as ET
import csv
from copy import deepcopy

MASS_GUESSES = { # Used in legend labels.
    2: "$H_2$",
    18: "$H_2O$",
    40: "Ar"
}

# Try to give every mass we're gonna plot a unique and consistent color, loosely related to its magnitude.
# This way, different graphs in the paper use consistent colors for masses.
expected_masses = (2, 12, 16, 17, 28, 40, 44)
mass_cmap = matplotlib.cm.get_cmap("plasma")
MASS_PALETTE = {mass: mass_cmap(i / len(expected_masses)) for i, mass in enumerate(expected_masses)}
MASS_PALETTE[999] = "grey" # total pressure

x_label_cmap = matplotlib.cm.get_cmap("viridis")

scans_cache = {} # Caches parsed scans in case you want to retry a plot without reading files again.

def parse_scans(scan_path, normalize_time=True):
    """
    Reads the file at scan_path and outputs a list of scans,
    where each scan is a tuple of (xml_data, rows).
    xml_data is an xml tree of the scan's metadata.
    rows is a list of tuples of (time, mass, pressure) representing the data points.
    skip_xml should be true if you don't need to parse the xml.
    """
    if scan_path in scans_cache:
        return scans_cache[scan_path]
    
    with open(scan_path) as file: #scans_path? path?
        raw_scans = file.read()[:-1]

    scans = []

    for raw_scan in ["<?" + i for i in raw_scans.split("<?")][1:]:

        xml_length = raw_scan.rindex(">") + 1
        xml_part, csv_part = raw_scan[:xml_length], raw_scan[xml_length + 1:].strip()
        xml_root = ET.fromstring(xml_part)

        raw_rows = csv_part.split("\n")
        
        rows = []
        t_0 = None
        for raw_row in raw_rows:
            # t means time, m means mass, p means pressure
            raw_t, raw_m, raw_p = [i.strip() for i in raw_row[:-1].split(", ")]
            
            t = time.mktime(datetime.datetime.strptime(raw_t, "%Y/%m/%d %H:%M:%S.%f").timetuple())
            if t_0 is None:
                t_0 = t
            if normalize_time:
                t = t - t_0 # normalize time

            m = float(raw_m)            
            p = float(raw_p)
            
            rows.append([t, m, p])
        
        scans.append((xml_root, rows))

    # Make a fresh copy for the cache.
    # This way it won't get messed up when other functions modify rows.
    scans_cache[scan_path] = deepcopy(scans)
    
    return scans    

def plot_parsed_scan(scan, x_labels={}, pressure_floor=0, title=None):
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
    """

    xml_root, rows = scan

    fig, ax = plt.subplots()
    ax.set_yscale("log")
    ax.set_ylabel("relative pressure (Pa)") # assuming that the rga is set to Pa
    # set title. default to scan timestamp
    ax.set_title(title or ("RGA: " + xml_root.find("ConfigurationParameters").get("DateTime")))

    mode = xml_root.find("OperatingParameters").get("Mode")
    
    if mode == "Trend":
        t_final = rows[-1][0]
        if t_final > 36000:
            t_unit, t_conversion_factor = "hours", 1/60/60
        elif t_final > 3600:
            t_unit, t_conversion_factor = "minutes", 1/60
        else:
            t_unit, t_conversion_factor = "s", 1

        for row in rows:
            row[0] *= t_conversion_factor
            
        ax.set_xlabel("time ({})".format(t_unit))
        
        mass_series = {}
        for t, m, p in rows:
            if m not in mass_series:
                mass_series[m] = [t], [p]
            else:
                mass_series[m][0].append(t)
                mass_series[m][1].append(p)

        pressure_lines = []
        for i, (m, (times, pressures)) in enumerate(sorted(mass_series.items())):
            if m == int(m):
                m = int(m)
            
            if m == 5: # Pirani pressure??
                continue
            
            if m == 999: # I sure hope we never have to detect mass 999!
                label = "Total pressure"
            else:
                if m in MASS_GUESSES:
                    label = "{} ({}?)".format(m, MASS_GUESSES[m])
                else:
                    label = str(m)
                
            pressure_lines.append(*ax.plot(times, pressures, label=label, color=MASS_PALETTE.get(m)))

        event_lines = []

        for i, (t, label) in enumerate(x_labels.items()):
            event_lines.append(ax.axvline(t, linestyle="--", label=label, color=x_label_cmap(i / len(x_labels))))
            # todo: x_labels should have a better name

        fig.legend(handles = pressure_lines + event_lines) # arrange the legend
    else:
        ax.set_xlabel("mass (amu)")
        #ax.xaxis.grid(True, which='minor')
        ax.xaxis.set_major_locator(plt.MultipleLocator(10))
        ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
        
        masses = []
        pressures = []
        for t, m, p in rows:
            masses.append(m)
            pressures.append(p)

        ax.plot(masses, pressures)

    # trim noise floor
    bottom, top = ax.get_ylim()
    print(bottom, top, pressure_floor)
    ax.set_ylim(bottom=max(bottom, pressure_floor), top=top)

    plt.savefig("tmp.png", dpi=256)
    plt.show()

def plot_all_scans_in_file(scan_path):
    """
    Plots every scan in the file at scan_path.
    Used to check contents of a scan file.
    Use plot for more controlled plotting.
    """
    scans = parse_scans(scan_path)
    
    print("Found {} scans in file.".format(len(scans)))
    for i, scan in enumerate(scans):
        if len(scan[1]) < 40:
            print("Skipping tiny scan of length {}.".format(len(scan[1])))
            continue
        print("\nPlotting scan {}.".format(i))
        plot_parsed_scan(scan)
    return

def plot(scan_path, scan_index=0, x_labels={}, pressure_floor=2e-10, title=None):
    """
    Plots the scan_indexth scan in scan_path, labelling specified events.
    
    scan_path: path to an RGA output file.
    scan_index: ordinal of the scan in the file. Use plot_all_scans_in_file to plot every scan.
    x_labels: specifies vertical bars to plot and label.
        For a trend scan:
            Dictionary. Each key is a timestamp, in seconds. Each value is a string description
            of the event that happened at that time. For example:
            {
                181: "turned on gun filament",
                289: "turned off ion pump"
            }
        For a mass sweep scan:
            Iterable of masses to label, using MASS_GUESSES. For example: [2, 40]
    pressure_floor: y-axis minimum bound.
        Overridden if the absolute minimum of the data exceeds it.
    """
    plot_parsed_scan(
        parse_scans(scan_path)[scan_index],
        x_labels=x_labels,
        pressure_floor=pressure_floor,
        title=title
    )

def plot_sweeps_trend(scan_paths, masses, x_labels={}, pressure_floor=2e-10, title="Combined trend"): # improve name
    combined_rows = []
    for scan_path in scan_paths:
        scans = parse_scans(scan_path, False)
        if len(scans) != 1:
            print("Warning: {} contains {} scans.".format(scan_path, len(scans)))
        for xml_root, rows in scans:
            #if xml_root.find("OperatingParameters").get("Mode") != "Mass sweep":
            #    print("Warning: {} contains a trend scan. Skipping.")
            #    continue
            combined_rows.extend(rows)
    combined_rows.sort() # sort by time

    selected_rows = [list(row) for row in combined_rows if row[1] in masses]

    t_0 = selected_rows[0][0]
    for row in selected_rows:
        row[0] -= t_0 # normalize time

    xml_root.find("OperatingParameters").set("Mode", "Trend") # kinda hacky

    debug.append(selected_rows)
    
    plot_parsed_scan(
        (xml_root, selected_rows),
        x_labels=x_labels,
        pressure_floor=pressure_floor,
        title=title
    )

def frankenstein(scan_paths, output_scan_path):
    """
    Combines all the scans in scan_paths into a single file. Not very useful.
    Really just concatenates the files.
    """
    concatenated_raw_data = ""
    for scan_path in scan_paths:
        with open(scan_path) as file:
            concatenated_raw_data += file.read()
    with open(output_scan_path, "w") as file:
        file.write(concatenated_raw_data)

EVENTS = { # time (in seconds): description. For example:  181: "turned on gun filament"
}

SCAN_PATH = "rga_data/MassSpecData-06507-20210210-171042.csv"
SCAN_INDEX = None # each file can contain multiple scans due to a bug in the software.

#plot(SCAN_PATH, SCAN_INDEX, EVENTS)

#plot_all_scans_in_file(SCAN_PATH)

with open("sweep_series_paths.txt") as file:
    sweep_series_paths = file.read().split("\n")

if 1:
    plot_sweeps_trend(
        sweep_series_paths,
        (2, 18, 40)
    )

if 0:
    plot(
        "/home/rose/Documents/capstone/chamberplot/rga_data/MassSpecData-06507-20210219-140402.csv",
        pressure_floor = 2e-9
    )

if 0:
    plot(
        "rga_data/MassSpecData-06507-20210210-171042.csv",
        6,
        {
            181: "turned on gun filament",
            289: "opened Ar leak valve, turned off ion pump",
            349: "closed Ar leak valve",
            370: "turned up gun",
            569: "turned off gun, turned on ion pump"
        }
    )
