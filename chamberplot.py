
# todo: investigate float imprecision?

import csv
import datetime, time
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
import xml.etree.ElementTree as ET
from copy import deepcopy
import os

# Set default font
rcParams["font.sans-serif"] = ["Ubuntu"]

MASS_GUESSES = { # Used in legend labels.
    2: "$H_2$",
    12: "$C$",
    16: "$O$, $CH_4$",
    17: "$HO$",
    18: "$H_2O$",
    19: "$F$",
    28: "$N_2$",
    40: "$Ar$",
    44: "$CO_2$",
    178: "$C_8H_18S_2$"
}

# Try to give every mass we're gonna plot a unique and consistent color, loosely related to its magnitude.
# This way, different graphs in the paper use consistent colors for masses.
expected_masses = (2, 12, 16, 17, 28, 40, 178)
mass_cmap = matplotlib.cm.get_cmap("plasma")
MASS_PALETTE = {mass: mass_cmap(i / len(expected_masses)) for i, mass in enumerate(expected_masses)}
MASS_PALETTE[5] = "black" # total pressure
MASS_PALETTE[999] = "grey" # total pressure

# Actually, let's generate palettes on the fly instead. I don't care about consistency across graphs.
def generate_mass_palette(masses):
    """
    Generates a color palette for an iterable of masses.
    Returns a dictionary of the form {mass: color}.
    """
    mass_cmap = matplotlib.cm.get_cmap("plasma")
    palette = {mass: mass_cmap(i / len(masses)) for i, mass in enumerate(masses)}
    palette[999] = "grey" # total pressure
    palette[5] = "black" # Pirani pressure
    return palette


x_label_cmap = matplotlib.cm.get_cmap("viridis") # color gradient used for event lines

scans_cache = {} # Caches parsed scans in case you want to retry a plot without reading files again.

def parse_scans(scan_path, normalize_time=False):
    """
    Reads the file at scan_path and outputs a list of scans,
    where each scan is a tuple of (xml_data, rows).
    xml_data is an xml tree of the scan's metadata.
    rows is a list of tuples of (time, mass, pressure) representing the data points.
    skip_xml should be true if you don't need to parse the xml.

    This should probably be restructured so it makes a dictionary of the
    important xml information instead of returning the whole xml root.
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

        #xml_info = {
        #    "DateTime": xml_root.find("ConfigurationParameters").get("DateTime"),

        raw_rows = csv_part.split("\n")
        
        rows = []
        t_0 = None
        for raw_row in raw_rows:
            # t means time, m means mass, p means pressure
            raw_t, raw_m, raw_p = [i.strip() for i in raw_row[:-1].split(", ")]
            
            t = datetime.datetime.strptime(raw_t, "%Y/%m/%d %H:%M:%S.%f")
            if normalize_time:
                t = t.timestamp()
            if t_0 is None:
                t_0 = t
            if normalize_time:
                t = t - t_0

            m = float(raw_m)            
            p = float(raw_p)
            
            rows.append([t, m, p])
        
        scans.append((xml_root, rows))

    # Make a fresh copy for the cache.
    # This way it won't get messed up when other functions modify rows.
    scans_cache[scan_path] = deepcopy(scans)
    
    return scans    

def plot_parsed_scan(scan, x_labels={}, pressure_floor=0, title=None, plot_kwargs={}):
    """
    Plots a scan that has already been parsed with parse_scan. Used internally.
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
        t_unit="s"
        """
        if t_final > 36000:
            t_unit, t_conversion_factor = "hours", 1/60/60
        elif t_final > 3600:
            t_unit, t_conversion_factor = "minutes", 1/60
        else:
            t_unit, t_conversion_factor = "s", 1

        for row in rows:
            row[0] *= t_conversion_factor"""
            
        #ax.set_xlabel("time ({})".format(t_unit))

        ax.set_xlabel("date and time")
        
        mass_series = {}
        for t, m, p in rows:
            if m not in mass_series:
                mass_series[m] = [t], [p]
            else:
                mass_series[m][0].append(t)
                mass_series[m][1].append(p)

        mass_palette = generate_mass_palette(mass_series.keys())
        
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
                    label = "{} ({})".format(m, MASS_GUESSES[m])
                else:
                    label = str(m)
                
            pressure_lines.append(*ax.plot(times, pressures, label=label, color=mass_palette[m], **plot_kwargs))

        event_lines = []

        for i, (t, label) in enumerate(x_labels.items()):
            event_lines.append(ax.axvline(
                t,
                linestyle="--",
                label=label,
                color=x_label_cmap(i / len(x_labels)),
                zorder=0.5
            ))
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

        ax.plot(masses, pressures, **plot_kwargs)

    # trim noise floor
    bottom, top = ax.get_ylim()
    #print(bottom, top, pressure_floor)
    ax.set_ylim(bottom=max(bottom, pressure_floor), top=top)

    #plt.savefig("tmp.png", dpi=256)
    #plt.show()
    return fig

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

def plot(scan_path, scan_index=0, x_labels={}, pressure_floor=2e-10, title=None, normalize_time=False):
    """
    Plots the scan_indexth scan in scan_path, labelling specified events.
    
    scan_path: path to an RGA output file.
    scan_index: ordinal of the scan in the file. Use plot_all_scans_in_file to plot every scan.
    x_labels: specifies vertical bars to plot and label.
        For a trend scan:
            Dictionary. Each key is a timestamp, in whatever units the plot uses for the x-axis.
            (This makes it easier to check when events happen by using your cursor in the matplotlib window.)
            Each value is a string description of the event that happened at that time. For example:
            {
                181: "turned on gun filament",
                289: "turned off ion pump"
            }
        For a mass sweep scan:
            Iterable of masses to label, using MASS_GUESSES. For example: [2, 40]
    pressure_floor: y-axis minimum bound.
        Overridden if the absolute minimum of the data exceeds it.
    """
    return plot_parsed_scan(
        parse_scans(scan_path, normalize_time=True)[scan_index],
        x_labels=x_labels,
        pressure_floor=pressure_floor,
        title=title
    )

def plot_combined_trend(scan_paths, masses, x_labels={}, pressure_floor=2e-10, title="Combined trend", plot_kwargs={}):
    """
    Combines a bunch of scans and plots their data as a single trend.
    Use this to turn series of sweeps (and/or trends) into a trend.
    scan_paths should be an iterable of paths to the scans. Uses every scan in each path.
    masses should be a tuple of masses to monitor, because you would have way too many
    lines if you tried to turn a sweep into a trend without narrowing down the masses.
    """
    combined_rows = []
    for scan_path in scan_paths:
        scans = parse_scans(scan_path, False)
        if len(scans) != 1:
            #print("Warning: {} contains {} scans.".format(scan_path, len(scans)))
            pass
        for xml_root, rows in scans:
            combined_rows.extend(rows)

    combined_rows.sort() # sort by time

    selected_rows = [list(row) for row in combined_rows if row[1] in masses]

    t_0 = selected_rows[0][0]

    # We should change how xml is parsed and used so this is less hacky.
    xml_root.find("OperatingParameters").set("Mode", "Trend")
    
    return plot_parsed_scan(
        (xml_root, selected_rows),
        x_labels=x_labels,
        pressure_floor=pressure_floor,
        title=title,
        plot_kwargs=plot_kwargs
    )



if 0:
    with open("sweep_series_paths.txt") as file:
        sweep_series_paths = file.read().split("\n")
    
    first_row_times = []
    modified_times = []
    config_parameter_times = []
    for scan_path in sweep_series_paths[:100]:
        xml_root, rows = parse_scans(scan_path)[0]
        first_row_times.append(rows[0][0])
        modified_times.append(os.path.getmtime(scan_path))
        config_parameter_times.append(
            datetime.datetime.strptime(
                xml_root.find("ConfigurationParameters").get("DateTime"),
                "%m/%d/%Y %H:%M:%S %p" # example: 2/22/2021 5:20:10 PM
            )
        )
    plt.plot(modified_times, first_row_times)


if 1:
    max_mass = 200
    masses = [i for i in range(1, max_mass) if i != 5]
    mass_cmap = matplotlib.cm.get_cmap("turbo")
    mass_palette = {mass: mass_cmap(i / len(masses)) for i, mass in enumerate(masses)}
    for m in masses:
        scan_paths = ["rga-3-10/" + i for i in os.listdir("rga-3-10") if i.startswith("MassSpecData")]
        scan_paths.sort()
        fig = plot_combined_trend(
            scan_paths[4:-1],
            (m,),
            title="Thermal Desorption Ramp",
            pressure_floor=1e-9,
            x_labels={
                datetime.datetime.strptime("3/10/2021 15:39", "%m/%d/%Y %H:%M"): "began thermal desorption at 2V",
                datetime.datetime.strptime("3/10/2021 20:14", "%m/%d/%Y %H:%M"): "maxed out heater voltage, from 112V to 133V"
            },
            plot_kwargs = {
                "linestyle": "",
                "marker": "."
            }
        )
        ax = fig.axes[0]
        ax.lines[0].set_color(mass_palette[m])
        _ = ax.set_ylim(bottom=1e-9, top=1e-5)
        _ = ax.set_xlim(
            left=datetime.datetime.strptime("3/10/2021 15:30", "%m/%d/%Y %H:%M"),
            right=datetime.datetime.strptime("3/10/2021 20:45", "%m/%d/%Y %H:%M")
        )
        [c for c in fig.get_children() if isinstance(c, matplotlib.legend.Legend)][0].remove()
        _ = ax.text((m / max_mass) * 1.3 - 0.15, -0.15, str(m), color=mass_palette[m], fontsize="small", transform=ax.transAxes)
        #fig.axes[0].text(0, 0, "HELLO, WORLD", color="purple", fontsize="large")
        fig.set_size_inches(9, 7)
        fig.subplots_adjust(top=0.83, right=0.83)
        print(m, end=" ")
        fig.savefig("layers/layer_" + str(m).zfill(3) + ".png", dpi=256, transparent=True)


if 0:
    scan_paths = ["rga-3-10/" + i for i in os.listdir("rga-3-10") if i.startswith("MassSpecData")]
    scan_paths.sort()
    fig = plot_combined_trend(
        scan_paths[4:-1],
        (32, 33, 34, 178),
        title="Thermal Desorption Ramp",
        pressure_floor=1e-9,
        x_labels={
            datetime.datetime.strptime("3/10/2021 15:39", "%m/%d/%Y %H:%M"): "began thermal desorption at 2V",
            datetime.datetime.strptime("3/10/2021 20:14", "%m/%d/%Y %H:%M"): "maxed out heater voltage, from 112V to 133V"
        },
        plot_kwargs = {
            "linestyle": "",
            "marker": "."
        }
    )
    fig.set_size_inches(9, 7)
    fig.subplots_adjust(top=0.83, right=0.83)
    fig.savefig("figures/desorption_ramp.png", dpi=256)
    fig.savefig("figures/desorption_ramp.svg", dpi=256)


if 0:
    with open("sweep_series_paths.txt") as file:
        sweep_series_paths = file.read().split("\n")
    with open("sweep_series_events.txt") as file:
        event_log = file.read().split("\n")
        events = {}
    for entry in event_log:
        if not entry.startswith(" "):
            day_entry = entry
        else:
            entry = entry[1:]
            time_string, event_message = entry.split(" ", maxsplit=1)
            event_time = datetime.datetime.strptime(day_entry + " " + time_string, "%m/%d/%Y %H:%M%p")
            events[event_time] = event_message
    plot_combined_trend(
        sweep_series_paths,
        (2, 18, 40)
        #x_labels=events
    )
    

if 0:
    plot_combined_trend(
        sweep_series_paths[:100],
        (2, 18, 40),
        x_labels={
            5.272: "brief power outage in Rickey"
        }
    )

if 0:
    plot(
        "/home/rose/Documents/capstone/chamberplot/rga_data/MassSpecData-06507-20210219-140402.csv",
        pressure_floor = 2e-9
    )

if 0:
    fig = plot(
        "rga_data/MassSpecData-06507-20210210-171042.csv",
        6,
        {
            181: "turned on ion gun filament",
            289: "opened Ar leak valve, turned off ion pump",
            349: "closed Ar leak valve",
            370: "turned up ion gun",
            569: "turned off ion gun, turned on ion pump"
        },
        normalize_time=True,
        title="One Round of Sputtering"
    )
    fig.set_size_inches(9, 7)
    fig.savefig("figures/sputtering_run.png", dpi=256)
    fig.savefig("figures/sputtering_run.svg", dpi=256)
