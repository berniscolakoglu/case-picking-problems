import matplotlib.pyplot as plt
import networkx as nx
import json

def build_graph_and_draw_warehouse(config_file):
    """
    Draws a 2D representation of a parallel-aisle warehouse with locations on both sides of each aisle
    and a graph representation of the aisles.

    Parameters:
        config_file (str): Path to the JSON file specifying warehouse parameters and storage.
    """
    # Load configuration and storage
    with open(config_file, 'r') as f:
        config = json.load(f)

    num_aisles = config['num_aisles']
    locations_per_aisle = config['locations_per_aisle']
    aisle_draw_size = config['aisle_draw_size']
    location_draw_size = config['location_draw_size']
    storage_data = config['storage']

    # Create a plot
    fig, ax = plt.subplots(figsize=(15, locations_per_aisle * location_draw_size / 2))

    # Create a graph
    G = nx.Graph()

    # Parse storage data
    storage_map = {}
    for item in storage_data:
        color = item['color']
        for loc in item['storage']:
            key = (loc['aisle'], loc['loc'], loc['side'])
            storage_map[key] = {'color': color, 'quantity': loc['quantity']}

    # Draw warehouse layout and add nodes/edges to the graph
    for aisle in range(num_aisles):
        aisle_x_left = aisle * (aisle_draw_size + 2 * location_draw_size)
        aisle_x_right = aisle_x_left + location_draw_size + aisle_draw_size

        node_x = aisle_x_left + location_draw_size + aisle_draw_size / 2

        # Add node for the start of aisle
        G.add_node((aisle, 0), pos=(node_x, location_draw_size / 2))

        for loc in range(locations_per_aisle):
            loc_y = (loc + 1) * location_draw_size

            # Left side locations
            left_key = (aisle, loc, 'left')
            left_color = storage_map.get(left_key, {}).get('color', 'none')
            left_quantity = storage_map.get(left_key, {}).get('quantity', None)
            left_item = storage_map.get(left_key, {}).get('item', None)
            left_rect = plt.Rectangle((aisle_x_left, loc_y), location_draw_size, location_draw_size, edgecolor='black', facecolor=left_color)
            ax.add_patch(left_rect)
            if left_quantity:
                ax.text(aisle_x_left + location_draw_size / 2, loc_y + location_draw_size / 2, str(left_quantity), ha='center', va='center', fontsize=8)

            # Right side locations
            right_key = (aisle, loc, 'right')
            right_color = storage_map.get(right_key, {}).get('color', 'none')
            right_quantity = storage_map.get(right_key, {}).get('quantity', None)
            right_item = storage_map.get(right_key, {}).get('item', None)
            right_rect = plt.Rectangle((aisle_x_right, loc_y), location_draw_size, location_draw_size, edgecolor='black', facecolor=right_color)
            ax.add_patch(right_rect)
            if right_quantity:
                ax.text(aisle_x_right + location_draw_size / 2, loc_y + location_draw_size / 2, str(right_quantity), ha='center', va='center', fontsize=8)

            # Add graph nodes for aisle points
            n = (aisle, loc+1)
            G.add_node(n, pos=(node_x, loc_y + location_draw_size / 2), storage={
                'left': {'item': left_item, 'quantity': left_quantity},
                'right': {'item': right_item, 'quantity': right_quantity}
            })

            # Add vertical edges if not the first location
            G.add_edge((aisle, loc), n)

        # Add node for the end of aisle
        G.add_node((aisle, locations_per_aisle + 1), pos=(node_x, (locations_per_aisle + 1) * location_draw_size + location_draw_size / 2), storage=None)
        G.add_edge((aisle, locations_per_aisle), (aisle, locations_per_aisle + 1))

        # Add horizontal edges between adjacent aisles
        if aisle > 0:
            G.add_edge((aisle - 1, 0), (aisle, 0))
            G.add_edge((aisle - 1, locations_per_aisle + 1), (aisle, locations_per_aisle + 1))

    # Draw the boundary around the entire warehouse
    warehouse_width = num_aisles * (aisle_draw_size + 2 * location_draw_size)
    warehouse_height = (2 + locations_per_aisle) * location_draw_size 
    boundary = plt.Rectangle((0, 0), warehouse_width, warehouse_height, edgecolor='black', facecolor='none', linewidth=2)
    ax.add_patch(boundary)

    # Set plot limits
    ax.set_xlim(-location_draw_size, warehouse_width + location_draw_size)
    ax.set_ylim(-location_draw_size, warehouse_height + location_draw_size)

    # Draw the graph
    pos = nx.get_node_attributes(G, 'pos')
    nx.draw(G, pos, node_size=50, node_color='black', ax=ax)

    # Add grid and labels
    ax.set_aspect('equal')
    ax.axis('off')

    return G,(fig, ax)


if __name__ == '__main__':
    G, _ = build_graph_and_draw_warehouse("config.json")
    plt.show()
