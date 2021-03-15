# chamberplot
Residual gas analyzer data plotter for Extorr's Vacuum Plus software.

Extorr claims that their quadrupole residual gas analyzer is only compatible with their proprietary Vacuum Plus software. They also declined my request to share the source code of Vacuum Plus. Vacuum Plus works okay most of the time, but it leaves visualization features to be desired. So, I made this set of Python scripts for my physics capstone project to make it easier to visualize data from the RGA.

Chamberplot can plot previously generated RGA data and can also plot RGA data as it is generated. In the latter case, it displays both a trend view and a mass sweep view, and allows the user to decide on the fly which masses to plot on the trend view. This could be useful for things like controlled thermal desorption or whatever else you do in ultra-high vacuum.

Downsides: It's kinda messy since I made this under time contraints of my capstone schedule. Also it uses matplotlib, which is great for making high-quality plots for research papers, but is pretty slow so it's not great for realtime visualization.

## Usage
- Download this repository.
- Install Python 3.
- Install matplotlib (probably with the command `pip install matplotlib`)
- Edit `chamberplot_stream.py` so it looks for RGA data in the correct directory.
- Run `chamberplot_stream.py`.
- Optionally, also run `chamberplot_stream_config.py` to configure the program is it's running. You can also just edit `chamberplot_stream_config.json` directly if you never make mistakes.

You can use the spoofer script to simulate the RGA so you can develop this program while away from the lab. Be sure to clear the spoofed data directory between tests.
