import networkx as nx
import json
import matplotlib.pyplot as plt
import pandas as pd
from draw import build_graph_and_draw_warehouse
import gurobipy as gp
from gurobipy import GRB
from itertools import product

config_file = 'config.json'

G, _ = build_graph_and_draw_warehouse(config_file)

with open(config_file, 'r') as f:
    config = json.load(f)


num_aisles = config['num_aisles']
num_locations_per_aisle = config['locations_per_aisle']

# create set S
S = {"all": [s['item'] for s in config['storage']], }
# print(S)

# creating set K
K = [i for i in range(len(config['pick_lists']))]
# print(K)

# create set N
N = {"all": [(i, j, l) for i in range(num_aisles) for j in range(1, num_locations_per_aisle + 1) for l in
             ['left', 'right']], }
# print(N)

# create set N_s and parameters q_i
q = {}
for s in config['storage']:
    N[s["item"]] = []
    for ns in s["storage"]:
        N[s["item"]].append((ns["aisle"], ns["loc"] + 1, ns["side"]))
        q[(ns["aisle"], ns["loc"] + 1, ns["side"])] = ns["quantity"]
# print(q)
# print(N)

# create sets S_k, N_k, sf_k, sc_sk and parameters r_sk
r = {}
sf = {}
sc = {}
for k in K:
    S[f"list_{k}"] = [s["item"] for s in config["pick_lists"][k]]
    sf[f"list_{k}"] = S[f"list_{k}"][-1]
    for s in config["pick_lists"][k]:
        r[(s["item"], f"list_{k}")] = s["quantity"]
        index = config["pick_lists"][k].index(s)
        if config["pick_lists"][k].index(s) != config["pick_lists"][k].index(config["pick_lists"][k][-1]):
            sc[s["item"], f"list_{k}"] = config["pick_lists"][k][index + 1]["item"]
    N[f"list_{k}"] = []
    N[(f"list_{k}", 0)] = []
    for item in S[f"list_{k}"]:
        N[f"list_{k}"] += N[item]
    N[(f"list_{k}", 0)] = N[f"list_{k}"] + [(config["depot"]["aisle"], config["depot"]["loc"])]

# print(S)
# print(r)
# print(sf)
# print(sc)
# print(N)

# create parameter c_ij and shortest paths of (i, j)
nodes = [node for node in N["all"] + [(config["depot"]["aisle"], config["depot"]["loc"])]]
c = pd.DataFrame(index=nodes, columns=nodes)
path = pd.DataFrame(index=nodes, columns=nodes)
for i in nodes:
    for j in nodes:
        if i[0] == j[0] and i[1] == j[1]:
            c.at[i, j] = 0
        else:
            c.at[i, j] = nx.shortest_path_length(G, source=(i[0], i[1]), target=(j[0], j[1]), weight="cost",
                                                 method='dijkstra')
            path.at[i, j] = nx.shortest_path(G, source=(i[0], i[1]), target=(j[0], j[1]), weight="cost",
                                             method='dijkstra')
# print(c)
# print(path)

# create the model
model = gp.Model('Case Picking Problem')

# add decision variables together with domain constraints
x_indices = []
y_indices = []
v_indices = []

for k in K:
    x_indices += [(i[0], i[1], f"list_{k}") for i in list(product(N[(f"list_{k}", 0)], N[(f"list_{k}", 0)]))]
    for s in S[f"list_{k}"]:
        y_indices += [(i, f"list_{k}") for i in N[s]]
    v_indices += [(i, f"list_{k}") for i in N[f"list_{k}"]]

x = model.addVars(x_indices, vtype=GRB.BINARY, name="x")
y = model.addVars(y_indices, vtype=GRB.INTEGER, name="y")
v = model.addVars(v_indices, vtype=GRB.INTEGER, name="v")
Cmax = model.addVar(vtype=GRB.INTEGER, name="Cmax")

# add constraints
# constraint (2)
model.addConstrs(
    (gp.quicksum(c.at[i, j] * x[(i, j, f"list_{k}")] for i in N[(f"list_{k}", 0)] for j in N[(f"list_{k}", 0)]) <= Cmax
     for k in K), name="(2)")

# constraint (3)
model.addConstrs((gp.quicksum(y[i, f"list_{k}"] for i in N[s]) == r[s, f"list_{k}"] for k in K for s in S[f"list_{k}"]),
                 name="(3)")

# constraint (4)
model.addConstrs((gp.quicksum(y[i1, k] for (i1, k) in y_indices if i1 == i) <= q[i] for s in S["all"] for i in N[s]),
                 name="(4)")

# constraint (5)
model.addConstrs(
    (y[i, f"list_{k}"] <= min(q[i], r[s, f"list_{k}"]) * (1 - x[i, i, f"list_{k}"]) for k in K for s in S[f"list_{k}"]
     for i in N[s]), name="(5)")

# constraint (6)
model.addConstrs((x[(config["depot"]["aisle"], config["depot"]["loc"]), (
    config["depot"]["aisle"], config["depot"]["loc"]), f"list_{k}"] == 0 for k in K), name="(6)")

# constraint (7)
model.addConstrs(
    (gp.quicksum(x[i, j, f"list_{k}"] for j in N[(f"list_{k}", 0)]) == 1 for k in K for i in N[(f"list_{k}", 0)]),
    name="(7)")

# constraint (8)
model.addConstrs(
    (gp.quicksum(x[j, i, f"list_{k}"] for j in N[(f"list_{k}", 0)]) == 1 for k in K for i in N[(f"list_{k}", 0)]),
    name="(8)")

# constraint (9)
model.addConstrs(
    (v[i, f"list_{k}"] + 1 <= v[j, f"list_{k}"] + len(N[f"list_{k}"]) * (1 - x[i, j, f"list_{k}"]) for k in K for i in
     N[f"list_{k}"] for j in N[f"list_{k}"] if i != j), name="(9)")

# constraint (10)
for k in K:
    for s in [item for item in S[f"list_{k}"] if item != sf[f"list_{k}"]]:
        for i in N[s]:
            for j in N[sc[s, f"list_{k}"]]:
                model.addConstr(
                    (v[i, f"list_{k}"] + 1 <= v[j, f"list_{k}"]), name="(10)"
                )

# set objective function
model.setObjective(Cmax, GRB.MINIMIZE)

# save model for future inspection
model.write('CasePicking.lp')

# run the optimization engine
model.optimize()

# get model results
print("---------------------------------------------------------------------------------------------------------")
for v in model.getVars():
    if v.x > 1e-6:
        print(v.varName, v.x)


def create_ordered_cycle_from_edges(edges, depot):
    # create ordered route from pick locations selected
    ordered_route = []
    start_node = depot
    while len(edges):
        for i, edge in enumerate(edges):
            if edge[0] == start_node:
                ordered_route.append(edge[0])
                start_node = edge[-1]
                edges.pop(i)
    ordered_route.append(edge[-1])
    return ordered_route


route = {f"list_{k}": [] for k in K}
pick = {f"list_{k}": [] for k in K}
extended_route = {f"list_{k}": [] for k in K}
for (i, j, k) in x:
    if i != j and x[i, j, k].x > 1e-6:
        if i == (config["depot"]["aisle"], config["depot"]["loc"]):
            route[k] = [(i, j)] + route[k]
        else:
            route[k].append((i, j))

print("---------------------------------------------------------------------------------------------------------")
# get stops (depot and visited pick locations) of each route,
# get routes for each picklist,
# get the item and the quantity to be collected at each stop
for k in K:
    print(f"Picklist {k}:")
    route[f"list_{k}"] = create_ordered_cycle_from_edges(route[f"list_{k}"],
                                                         (config["depot"]["aisle"], config["depot"]["loc"]))
    print(f"Stops on the route: {route[f"list_{k}"]}")
    for i in range(len(route[f"list_{k}"]) - 1):
        start_node = route[f"list_{k}"][i]
        end_node = route[f"list_{k}"][i + 1]
        path_btw = path.at[start_node, end_node]
        extended_route[f"list_{k}"].append(path_btw) #get the path used between two successively visited pick locations
        if i == 0 or i == len(route[f"list_{k}"]) - 1:
            pick[f"list_{k}"].append("depot")
        else:
            for item in config["storage"]:
                for storage_location in item["storage"]:
                    if (storage_location["aisle"] == start_node[0] and storage_location["loc"] == start_node[1] - 1 and storage_location["side"] == start_node[2]):
                        pick[f"list_{k}"].append((item["item"], y[start_node, f"list_{k}"].x)) # get the item and the quantity from pick locations
    pick[f"list_{k}"].append("depot")
    print(f"Picks on stops: {pick[f"list_{k}"]}")
    print(f"Nodes on picker route: {extended_route[f"list_{k}"]}")
    print("---------------------------------------------------------------------------------------------------------")
plt.show()