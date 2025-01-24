import networkx
import json
import matplotlib.pyplot as plt
from draw import build_graph_and_draw_warehouse

config_file = 'config.json'

G, _ = build_graph_and_draw_warehouse(config_file)


with open(config_file, 'r') as f:
    config = json.load(f)

num_aisles = config['num_aisles']
num_locations_per_aisle = config['locations_per_aisle']

S = { s['item'] for s in config['storage'] }
K = [i for i in range(len(config['pick_lists']))]
# S_k = [ x['item'] for x in config['pick_lists'][k] ]

N = [ (i,j,l) for i in range(num_aisles) for j in range(1, num_locations_per_aisle + 1) for l in ['left', 'right'] ]

plt.show()