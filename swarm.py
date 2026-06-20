import pygame
import random
import numpy as np
import csv
import datetime
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--record-duration", type=int, default=0, help="Record the simulation for N seconds to simulation_battle.mp4")
args, unknown = parser.parse_known_args()
recording = args.record_duration > 0
video_pipe = None

# =========================
# CONFIG
# =========================
WIDTH = 120
HEIGHT = 120
CELL = 5
FPS = 60

EMPTY = 0
RED = 1
BLUE = 2
FLAG = 3  # Center flag

# =========================
# FIELDS
# =========================
attraction_field = np.zeros((HEIGHT, WIDTH))
threat_field = np.zeros((HEIGHT, WIDTH))
frontier_field = np.zeros((HEIGHT, WIDTH))
# Trail fields for graph formation
trail_field = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
blue_trail_field = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
red_trail_field = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
# Edge influence fields for fast lookup (updated once per graph update)
red_edge_influence_field = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
blue_edge_influence_field = np.zeros((HEIGHT, WIDTH), dtype=np.float32)

# =========================
# ANALYTICS HISTORY
# =========================
history_red = []
history_blue = []
history_entropy = []

MAX_HISTORY = 200

# Flag holder: None, RED, or BLUE
flag_holder = None
# Flag respawn timer (frames until flag respawns after capture)
flag_respawn_timer = 0
FLAG_RESPAWN_DELAY = 500  # frames

# Screenshot and data logging
SCREENSHOT_INTERVAL = 1800  # frames (30 seconds at 60 FPS)
frame_count = 0
# Ensure directories exist

# =========================
# SIMULATION METRICS LAYER (Phase 1)
# =========================
simulation_metrics = {
    "red_dominance": [],
    "blue_dominance": [],
    "graph_diversity_red": [],
    "graph_diversity_blue": [],
    "exploration_ratio": [],
    "congestion_index": [],
}
# For tracking active edges/nodes, visited areas, etc.
active_edges_count = []
active_nodes_count = []
map_visited_ratio = []
average_trail_concentration = []
congested_hubs_count = []

# =========================
# GRAPH AMNESIA CONSTANTS (Phase 2)
# =========================
GRAPH_MEMORY_DECAY = 0.98
GRAPH_AMNESIA_INTERVAL = 200  # frames

# =========================
# STRUCTURAL FORGETTING CONSTANTS (Phase 3)
# =========================
MIN_TRAFFIC_THRESHOLD = 0.1  # minimum traffic to keep an edge

# =========================
# EXPLORATION REBOUNDS CONSTANTS (Phase 4)
# =========================
ENTROPY_LOW_THRESHOLD = 0.2
GLOBAL_RANDOMNESS_MULTIPLIER = 2.0
TRAIL_WEIGHT_DECAY_FACTOR = 0.5
EXPLORATION_REBOUND_DURATION = 100  # frames
exploration_rebound_timer = 0
global_randomness_multiplier_current = 1.0
trail_weight_multiplier_current = 1.0

# =========================
# HUB CONGESTION PENALTY CONSTANTS (Phase 5)
# =========================
HUB_LIMIT = 5  # max connections before penalty
CONGESTION_PENALTY_FACTOR = 0.1

# =========================
# SWARM vs ZMQ DIFFERENT ROLES CONSTANTS (Phase 6)
# =========================
SWARM_TRAIL_DEPOSIT = 0.1
ZMQ_TRAIL_DEPOSIT = SWARM_TRAIL_DEPOSIT * 0.3  # 30% of Swarm's deposit

# =========================
# DIVERSITY PRESSURE METRIC CONSTANTS (Phase 7)
# =========================
DIVERSITY_LOW_THRESHOLD = 0.3
ENTROPY_BOOST_FACTOR = 1.5
os.makedirs("data", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)

# =========================
# BRAINS
# =========================

class ChaosBrain:
    def direction(self, agent, grid):
        return random.choice([(1,0),(-1,0),(0,1),(0,-1)])


class SwarmBrain:
    def direction(self, agent, grid):
        x, y = agent.x, agent.y
        options = [(1,0),(-1,0),(0,1),(0,-1)]

        best, best_score = None, -999

        # Choose the appropriate trail field and graph based on team
        if agent.team == RED:
            trail_field = red_trail_field
            nodes = red_nodes
            edges = red_edges
        else:
            trail_field = blue_trail_field
            nodes = blue_nodes
            edges = blue_edges

        for dx, dy in options:
            nx, ny = x + dx, y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                # occupancy: prefer empty cells
                occupancy = 1 if grid[ny][nx] == EMPTY else -1
                # frontier: we want to go to high frontier (original frontier_field marks borders)
                frontier = frontier_field[ny][nx]
                # local trail: team-specific trail strength
                local_trail = trail_field[ny][nx]
                # nearby edge strength: sum of weights of edges near this point
                nearby_edge_strength = 0.0
                edge_radius = 5.0  # radius to consider for edge influence
                for edge in edges:
                    # distance from point to edge midpoint
                    mid_x = (edge.node_a.x + edge.node_b.x) / 2.0
                    mid_y = (edge.node_a.y + edge.node_b.y) / 2.0
                    dist = ((nx - mid_x)**2 + (ny - mid_y)**2)**0.5
                    if dist < edge_radius:
                        # Apply congestion penalty: reduce edge weight based on node congestion
                        congestion_penalty_a = get_congestion_penalty(edge.node_a, edges)
                        congestion_penalty_b = get_congestion_penalty(edge.node_b, edges)
                        avg_congestion_penalty = (congestion_penalty_a + congestion_penalty_b) / 2.0
                        effective_weight = edge.weight * (1.0 - avg_congestion_penalty)
                        nearby_edge_strength += effective_weight
                # random entropy
                entropy = random.random() * 0.1 * global_randomness_multiplier_current

                # Combine with weights (tunable parameters)
                score = (
                    occupancy * 1.0 +
                    frontier * 0.5 +
                    local_trail * 0.3 * trail_weight_multiplier_current +
                    nearby_edge_strength * 0.2 +
                    entropy
                )

                if score > best_score:
                    best_score = score
                    best = (dx, dy)

        return best if best else random.choice(options)
def is_node_congested(node, edges):
    """Check if a node is congested (has too many connections)."""
    return node.degree > HUB_LIMIT

def get_congestion_penalty(node, edges):
    """Get congestion penalty factor for a node (0.0 to 1.0)."""
    if node.degree > HUB_LIMIT:
        excess = node.degree - HUB_LIMIT
        return min(excess * CONGESTION_PENALTY_FACTOR, 1.0)
    return 0.0

class ZMQBrainLike:
    def direction(self, agent, grid):
        x, y = agent.x, agent.y
        options = [(1,0),(-1,0),(0,1),(0,-1)]

        best, best_score = None, -999

        # Determine friendly and enemy teams
        if agent.team == RED:
            friendly_team = RED
            enemy_team = BLUE
            friendly_nodes = red_nodes
            friendly_edges = red_edges
            enemy_nodes = blue_nodes
            enemy_edges = blue_edges
            friendly_trail = red_trail_field
            enemy_trail = blue_trail_field
        else:
            friendly_team = BLUE
            enemy_team = RED
            friendly_nodes = blue_nodes
            friendly_edges = blue_edges
            enemy_nodes = red_nodes
            enemy_edges = red_edges
            friendly_trail = blue_trail_field
            enemy_trail = red_trail_field

        # Precompute strongest enemy hub (node with max traffic)
        strongest_enemy_hub = None
        max_enemy_traffic = -1
        for node in enemy_nodes:
            if node.traffic > max_enemy_traffic:
                max_enemy_traffic = node.traffic
                strongest_enemy_hub = node
        # Precompute flag position
        global flag_x, flag_y

        for dx, dy in options:
            nx, ny = x + dx, y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                # Graph-based scoring
                score = 0.0
                
                # 1. Attraction to strongest enemy hub (we want to go near it to attack)
                if strongest_enemy_hub is not None:
                    dist_to_hub = ((nx - strongest_enemy_hub.x)**2 + (ny - strongest_enemy_hub.y)**2)**0.5
                    # Closer is better -> negative distance
                    score += -dist_to_hub * 0.1  # weight
                
                # 2. Following friendly edges (similar to SwarmBrain's nearby_edge_strength)
                nearby_friendly_edge_strength = 0.0
                edge_radius = 5.0
                for edge in friendly_edges:
                    mid_x = (edge.node_a.x + edge.node_b.x) / 2.0
                    mid_y = (edge.node_a.y + edge.node_b.y) / 2.0
                    dist = ((nx - mid_x)**2 + (ny - mid_y)**2)**0.5
                    if dist < edge_radius:
                        # Apply congestion penalty: reduce edge weight based on node congestion
                        congestion_penalty_a = get_congestion_penalty(edge.node_a, friendly_edges)
                        congestion_penalty_b = get_congestion_penalty(edge.node_b, friendly_edges)
                        avg_congestion_penalty = (congestion_penalty_a + congestion_penalty_b) / 2.0
                        effective_weight = edge.weight * (1.0 - avg_congestion_penalty)
                        nearby_friendly_edge_strength += effective_weight
                score += nearby_friendly_edge_strength * 0.2
                
                # 3. Attraction to flag (we want to capture/defend flag)
                dist_to_flag = ((nx - flag_x)**2 + (ny - flag_y)**2)**0.5
                score += -dist_to_flag * 0.1  # closer to flag is better
                 
                # 4. Local friendly trail (reinforce our own trails)
                local_friendly_trail = friendly_trail[ny][nx]
                score += local_friendly_trail * 0.2 * trail_weight_multiplier_current
                  
                # 5. Random entropy
                score += random.random() * 0.1 * global_randomness_multiplier_current

                if score > best_score:
                    best_score = score
                    best = (dx, dy)

        return best if best else random.choice(options)


class SunflowerBrain:
    def direction(self, agent, grid):
        x, y = agent.x, agent.y
        options = [(1,0),(-1,0),(0,1),(0,-1)]
        
        if agent.team == RED:
            friendly_nodes = red_nodes
            friendly_trail = red_trail_field
        else:
            friendly_nodes = blue_nodes
            friendly_trail = blue_trail_field
            
        global flag_x, flag_y, flag_holder
        sun_x, sun_y = flag_x, flag_y
        if flag_holder == agent.team and friendly_nodes:
            strongest_node = max(friendly_nodes, key=lambda n: n.traffic, default=None)
            if strongest_node:
                sun_x, sun_y = strongest_node.x, strongest_node.y
        
        best, best_score = None, -999
        for dx, dy in options:
            nx, ny = x + dx, y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                score = 0.0
                
                # Attraction to the "sun" (heliotropism)
                dist_to_sun = ((nx - sun_x)**2 + (ny - sun_y)**2)**0.5
                score += -dist_to_sun * 0.2
                
                # Local trail follow
                score += friendly_trail[ny][nx] * 0.3 * trail_weight_multiplier_current
                
                # Occupancy preference
                score += 0.5 if grid[ny][nx] == EMPTY else -0.5
                
                # Entropy / noise
                score += random.random() * 0.1 * global_randomness_multiplier_current
                
                if score > best_score:
                    best_score = score
                    best = (dx, dy)
                    
        return best if best else random.choice(options)


class TacticalChaosBrain:
    def direction(self, agent, grid):
        x, y = agent.x, agent.y
        options = [(1,0),(-1,0),(0,1),(0,-1)]
        
        # Determine enemy nodes
        enemy_nodes = blue_nodes if agent.team == RED else red_nodes
        
        # Find nearest enemy node within radius 20
        nearest_node = None
        min_dist = 20.0
        for n in enemy_nodes:
            dist = ((x - n.x)**2 + (y - n.y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                nearest_node = n
                
        # If an enemy node is nearby, move towards it to disrupt it (sabotage)
        if nearest_node:
            best, best_score = None, -999
            for dx, dy in options:
                nx, ny = x + dx, y + dy
                if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                    dist_to_node = ((nx - nearest_node.x)**2 + (ny - nearest_node.y)**2)**0.5
                    score = -dist_to_node + random.random() * 2.0
                    if score > best_score:
                        best_score = score
                        best = (dx, dy)
            return best if best else random.choice(options)
            
        # Otherwise, move completely randomly (pure scattering chaos)
        return random.choice(options)


BRAIN_CLASSES = [ChaosBrain, SwarmBrain, ZMQBrainLike, SunflowerBrain, TacticalChaosBrain]

# =========================
# AGENT
# =========================

class Agent:
    def __init__(self, id, team):
        self.id = id
        self.team = team
        self.x = random.randint(0, WIDTH - 1)
        self.y = random.randint(0, HEIGHT - 1)
        self.history = []  # store recent positions for trail reinforcement

    def step(self, grid, brain):
        dx, dy = brain.direction(self, grid)
        # Impairment: if our team does not hold the flag, add noise
        global flag_holder
        if flag_holder is not None and flag_holder != self.team:
            dx += random.choice([-1, 0, 1])
            dy += random.choice([-1, 0, 1])
        self.x = max(0, min(WIDTH - 1, self.x + dx))
        self.y = max(0, min(HEIGHT - 1, self.y + dy))
        grid[self.y][self.x] = self.team
        
        # Deposit trail for graph formation
        global trail_field, red_trail_field, blue_trail_field
        # Determine trail deposit amount based on brain type
        # SwarmBrain builds trails strongly, ZMQBrainLike builds trails weakly (strategist vs builder)
        if brain.__class__.__name__ == "SwarmBrain":
            trail_deposit = SWARM_TRAIL_DEPOSIT
        else:  # ZMQBrainLike or other brains
            trail_deposit = ZMQ_TRAIL_DEPOSIT
            
        trail_field[self.y][self.x] += trail_deposit
        if self.team == RED:
            red_trail_field[self.y][self.x] += trail_deposit
        if self.team == BLUE:
            blue_trail_field[self.y][self.x] += trail_deposit
        
        # Update position history
        self.history.append((self.x, self.y))
        if len(self.history) > 20:  # keep last 20 positions
            self.history.pop(0)


# =========================
# FIELD SYSTEM
# =========================

def update_fields(grid):
    attraction_field.fill(0)
    threat_field.fill(0)
    frontier_field.fill(0)

    for y in range(1, HEIGHT - 1):
        for x in range(1, WIDTH - 1):

            v = grid[y][x]

            if v == EMPTY:
                attraction_field[y][x] = 1

            if v in (RED, BLUE):
                threat_field[y][x] = 1

            neighbors = [
                grid[y+1][x], grid[y-1][x],
                grid[y][x+1], grid[y][x-1]
            ]

            if EMPTY in neighbors and (RED in neighbors or BLUE in neighbors):
                frontier_field[y][x] = 1


def decay_fields():
    global attraction_field, threat_field, frontier_field
    attraction_field *= 0.97
    threat_field *= 0.97
    frontier_field *= 0.97

def decay_trail_fields():
    global trail_field, red_trail_field, blue_trail_field
    trail_field *= 0.995
    red_trail_field *= 0.995
    blue_trail_field *= 0.995


# =========================
# GRAPH STRUCTURES
# =========================
# Constants for graph formation
NODE_THRESHOLD = 10.0  # trail strength to consider a node
NODE_RADIUS = 3        # radius to check for local maxima
EDGE_RADIUS = 15       # radius to search for neighboring nodes to connect
EDGE_TRAIL_THRESHOLD = 5.0  # minimum trail strength along a path to consider an edge
EDGE_UPDATE_INTERVAL = 5    # update edges every N frames
CAPTURE_BONUS = 5.0   # bonus to trail when flag is captured
GRAPH_ANALYTICS_INTERVAL = 100  # frames between graph analytics updates
# Graph warfare constants
ENEMY_PRESSURE_THRESHOLD = 20.0  # enemy trail strength threshold to trigger damage
DAMAGE_AMOUNT = 0.5              # amount to reduce enemy trail on edge per frame

# Global graph storage
red_nodes = []
blue_nodes = []
red_edges = []
blue_edges = []
frame_counter = 0  # for periodic updates

# Graph analytics history
red_graph_metrics_history = []
blue_graph_metrics_history = []
# Latest metrics for dominance model
red_latest_metrics = {}
blue_latest_metrics = {}
# Dominance history
history_dominance_red = []
history_dominance_blue = []
MAX_DOMINANCE_HISTORY = 200

class GraphNode:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team  # RED, BLUE, or None for neutral
        self.traffic = 0.0
        self.team_pressure = 0.0  # sum of trail strength from this team
        self.degree = 0  # number of connections (edges)

class GraphEdge:
    def __init__(self, node_a, node_b):
        self.node_a = node_a
        self.node_b = node_b
        self.weight = 1.0  # will be set as distance / traffic
        self.traffic = 0.0
        self.ownership = None  # RED, BLUE, or None

# Global graph storage
red_nodes = []
blue_nodes = []
red_edges = []
blue_edges = []
frame_counter = 0  # for periodic updates


def update_graph_nodes():
    global red_nodes, blue_nodes, frame_counter
    # We'll rebuild nodes from scratch each update for simplicity
    red_nodes.clear()
    blue_nodes.clear()
    
    # For red team
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if red_trail_field[y][x] > NODE_THRESHOLD:
                # Check if it's a local maximum within NODE_RADIUS
                is_max = True
                for dy in range(-NODE_RADIUS, NODE_RADIUS+1):
                    for dx in range(-NODE_RADIUS, NODE_RADIUS+1):
                        ny = y + dy
                        nx = x + dx
                        if 0 <= ny < HEIGHT and 0 <= nx < WIDTH:
                            if red_trail_field[ny][nx] > red_trail_field[y][x]:
                                is_max = False
                                break
                    if not is_max:
                        break
                if is_max:
                    red_nodes.append(GraphNode(x, y, RED))
    
    # For blue team
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if blue_trail_field[y][x] > NODE_THRESHOLD:
                is_max = True
                for dy in range(-NODE_RADIUS, NODE_RADIUS+1):
                    for dx in range(-NODE_RADIUS, NODE_RADIUS+1):
                        ny = y + dy
                        nx = x + dx
                        if 0 <= ny < HEIGHT and 0 <= nx < WIDTH:
                            if blue_trail_field[ny][nx] > blue_trail_field[y][x]:
                                is_max = False
                                break
                    if not is_max:
                        break
                if is_max:
                    blue_nodes.append(GraphNode(x, y, BLUE))

def update_graph_edges():
    global red_edges, blue_edges, frame_counter
    red_edges.clear()
    blue_edges.clear()
    
    # Function to check if there's a continuous trail between two points
    def has_continuous_trail(trail_field, x1, y1, x2, y2, threshold):
        # Simple linear interpolation and check points along the line
        steps = max(abs(x2-x1), abs(y2-y1))
        if steps == 0:
            return trail_field[y1][x1] > threshold
        for i in range(steps+1):
            t = i / max(steps, 1)
            x = int(x1 + t * (x2 - x1))
            y = int(y1 + t * (y2 - y1))
            if trail_field[y][x] < threshold:
                return False
        return True
    
    # For red edges
    for i, node_a in enumerate(red_nodes):
        for node_b in red_nodes[i+1:]:
            dist = ((node_a.x - node_b.x)**2 + (node_a.y - node_b.y)**2)**0.5
            if dist < EDGE_RADIUS:
                 if has_continuous_trail(red_trail_field, node_a.x, node_a.y, node_b.x, node_b.y, EDGE_TRAIL_THRESHOLD):
                     edge = GraphEdge(node_a, node_b)
                     # weight = distance / traffic, but traffic we will update later
                     edge.weight = dist  # temporary, we'll adjust later
                     red_edges.append(edge)
                     node_a.degree += 1
                     node_b.degree += 1
    
    # For blue edges
    for i, node_a in enumerate(blue_nodes):
        for node_b in blue_nodes[i+1:]:
            dist = ((node_a.x - node_b.x)**2 + (node_a.y - node_b.y)**2)**0.5
            if dist < EDGE_RADIUS:
                 if has_continuous_trail(blue_trail_field, node_a.x, node_a.y, node_b.x, node_b.y, EDGE_TRAIL_THRESHOLD):
                     edge = GraphEdge(node_a, node_b)
                     edge.weight = dist
                     blue_edges.append(edge)
                     node_a.degree += 1
                     node_b.degree += 1

def update_graph():
    global frame_counter
    frame_counter += 1
    if frame_counter % EDGE_UPDATE_INTERVAL == 0:
        update_graph_nodes()
        update_graph_edges()
        # After creating edges, we can update traffic and weights
        update_edge_traffic_and_weights()
        # Update edge influence fields for fast lookup in brains
        update_edge_influence(red_edges, red_edge_influence_field)
        update_edge_influence(blue_edges, blue_edge_influence_field)
    # Graph analytics every GRAPH_ANALYTICS_INTERVAL frames
    if frame_counter % GRAPH_ANALYTICS_INTERVAL == 0:
        red_metrics = compute_graph_metrics(red_nodes, red_edges)
        blue_metrics = compute_graph_metrics(blue_nodes, blue_edges)
        red_graph_metrics_history.append(red_metrics)
        blue_graph_metrics_history.append(blue_metrics)
        # Keep only last 200 entries to match MAX_HISTORY
        if len(red_graph_metrics_history) > 200:
            red_graph_metrics_history.pop(0)
        if len(blue_graph_metrics_history) > 200:
            blue_graph_metrics_history.pop(0)
        # Update latest metrics for dominance model
        global red_latest_metrics, blue_latest_metrics
        red_latest_metrics = red_metrics
        blue_latest_metrics = blue_metrics
    # Apply graph amnesia periodically to prevent overfitting
    if frame_counter % GRAPH_AMNESIA_INTERVAL == 0:
        apply_graph_amnesia()
    # Apply structural forgetting (mark unused edges) every 100 frames
    if frame_counter % 100 == 0:
        mark_edges_for_removal()
    # Actually remove marked edges every 150 frames (to allow some buffer)
    if frame_counter % 150 == 0:
        remove_marked_edges()

def update_edge_traffic_and_weights():
    # Update traffic based on how much trail is on the edge
    # For simplicity, we'll set traffic as the average trail strength along the edge
    # And then weight = distance / (traffic + 1) to avoid division by zero
    def update_edges(edges, trail_field):
        for edge in edges:
            # Sample points along the edge
            steps = max(abs(edge.node_b.x - edge.node_a.x), abs(edge.node_b.y - edge.node_a.y))
            if steps == 0:
                avg_trail = trail_field[edge.node_a.y][edge.node_a.x]
            else:
                total = 0.0
                for i in range(steps+1):
                    t = i / max(steps, 1)
                    x = int(edge.node_a.x + t * (edge.node_b.x - edge.node_a.x))
                    y = int(edge.node_a.y + t * (edge.node_b.y - edge.node_a.y))
                    total += trail_field[y][x]
                avg_trail = total / (steps+1)
            edge.traffic = avg_trail
            # weight = distance / (traffic + 1)  # higher traffic -> lower weight
            dist = ((edge.node_a.x - edge.node_b.x)**2 + (edge.node_a.y - edge.node_b.y)**2)**0.5
            edge.weight = dist / (edge.traffic + 1.0)
    
    update_edges(red_edges, red_trail_field)
    update_edges(blue_edges, blue_trail_field)


def update_edge_influence(edges, influence_field):
    """Update influence field with edge weights at edge midpoints."""
    influence_field.fill(0)
    for e in edges:
        mx = int((e.node_a.x + e.node_b.x) / 2)
        my = int((e.node_a.y + e.node_b.y) / 2)
        if 0 <= mx < WIDTH and 0 <= my < HEIGHT:
            influence_field[my][mx] += e.weight


def compute_graph_metrics(nodes, edges):
    num_nodes = len(nodes)
    num_edges = len(edges)
    avg_degree = np.mean([n.degree for n in nodes]) if num_nodes > 0 else 0.0
    if num_nodes > 1:
        coords = np.array([[n.x, n.y] for n in nodes])
        diversity = float(np.mean(np.std(coords, axis=0)))
    else:
        diversity = 0.0
    return {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "avg_degree": avg_degree,
        "diversity": diversity,
    }

def compute_dominance(team, count, flag_holder, latest_metrics):
    score = count * 1.0
    if flag_holder == team:
        score += 15.0
    if latest_metrics:
        num_nodes = latest_metrics.get("num_nodes", 0)
        num_edges = latest_metrics.get("num_edges", 0)
        diversity = latest_metrics.get("diversity", 0.0)
        score += num_nodes * 0.5 + num_edges * 0.3 + diversity * 2.0
    return float(score)

def apply_graph_warfare():
    global red_trail_field, blue_trail_field
    damage_radius = 3
    for a in agents:
        if a.team == RED:
            y_min, y_max = max(0, a.y - damage_radius), min(HEIGHT, a.y + damage_radius + 1)
            x_min, x_max = max(0, a.x - damage_radius), min(WIDTH, a.x + damage_radius + 1)
            mask = blue_trail_field[y_min:y_max, x_min:x_max] > ENEMY_PRESSURE_THRESHOLD
            blue_trail_field[y_min:y_max, x_min:x_max][mask] -= DAMAGE_AMOUNT
        elif a.team == BLUE:
            y_min, y_max = max(0, a.y - damage_radius), min(HEIGHT, a.y + damage_radius + 1)
            x_min, x_max = max(0, a.x - damage_radius), min(WIDTH, a.x + damage_radius + 1)
            mask = red_trail_field[y_min:y_max, x_min:x_max] > ENEMY_PRESSURE_THRESHOLD
            red_trail_field[y_min:y_max, x_min:x_max][mask] -= DAMAGE_AMOUNT

def update_simulation_metrics():
    global red_nodes, blue_nodes, red_edges, blue_edges, trail_field, grid, flag_holder
    active_edges_count.append(len(red_edges) + len(blue_edges))
    active_nodes_count.append(len(red_nodes) + len(blue_nodes))
    visited_cells = np.sum(grid != EMPTY)
    map_visited_ratio.append(visited_cells / (WIDTH * HEIGHT))
    average_trail_concentration.append(float(np.mean(trail_field)))
    
    red_congested = sum(1 for n in red_nodes if n.degree > HUB_LIMIT)
    blue_congested = sum(1 for n in blue_nodes if n.degree > HUB_LIMIT)
    congested_hubs_count.append(red_congested + blue_congested)
    
    r, b, _ = stats(grid)
    dom_red = compute_dominance(RED, r, flag_holder, red_latest_metrics)
    dom_blue = compute_dominance(BLUE, b, flag_holder, blue_latest_metrics)
    simulation_metrics["red_dominance"].append(dom_red)
    simulation_metrics["blue_dominance"].append(dom_blue)
    
    red_div = red_latest_metrics.get("diversity", 0.0) if red_latest_metrics else 0.0
    blue_div = blue_latest_metrics.get("diversity", 0.0) if blue_latest_metrics else 0.0
    simulation_metrics["graph_diversity_red"].append(red_div)
    simulation_metrics["graph_diversity_blue"].append(blue_div)
    
    empty_count = np.sum(grid == EMPTY)
    simulation_metrics["exploration_ratio"].append(empty_count / (WIDTH * HEIGHT))
    
    total_nodes = len(red_nodes) + len(blue_nodes)
    congested_total = red_congested + blue_congested
    congestion_idx = congested_total / total_nodes if total_nodes > 0 else 0.0
    simulation_metrics["congestion_index"].append(congestion_idx)

def update_exploration_rebound():
    global exploration_rebound_timer, global_randomness_multiplier_current, trail_weight_multiplier_current
    current_entropy = entropy_measure()
    if exploration_rebound_timer > 0:
        exploration_rebound_timer -= 1
        if exploration_rebound_timer == 0:
            global_randomness_multiplier_current = 1.0
            trail_weight_multiplier_current = 1.0
    else:
        if current_entropy < ENTROPY_LOW_THRESHOLD:
            exploration_rebound_timer = EXPLORATION_REBOUND_DURATION
            global_randomness_multiplier_current = GLOBAL_RANDOMNESS_MULTIPLIER
            trail_weight_multiplier_current = TRAIL_WEIGHT_DECAY_FACTOR

def apply_graph_amnesia():
    global red_trail_field, blue_trail_field
    red_trail_field *= GRAPH_MEMORY_DECAY
    blue_trail_field *= GRAPH_MEMORY_DECAY

def mark_edges_for_removal():
    global red_edges, blue_edges
    for e in red_edges:
        if e.traffic < MIN_TRAFFIC_THRESHOLD:
            e.marked_for_removal = True
    for e in blue_edges:
        if e.traffic < MIN_TRAFFIC_THRESHOLD:
            e.marked_for_removal = True

def remove_marked_edges():
    global red_edges, blue_edges
    red_edges = [e for e in red_edges if not getattr(e, "marked_for_removal", False)]
    blue_edges = [e for e in blue_edges if not getattr(e, "marked_for_removal", False)]


def get_battle_recommendation():
    global red_brain_idx, blue_brain_idx, flag_holder, red_latest_metrics, blue_latest_metrics
    r_name = BRAIN_CLASSES[red_brain_idx].__name__
    b_name = BRAIN_CLASSES[blue_brain_idx].__name__
    
    r_nodes = red_latest_metrics.get("num_nodes", 0) if red_latest_metrics else 0
    b_nodes = blue_latest_metrics.get("num_nodes", 0) if blue_latest_metrics else 0
    
    rec_red = ""
    rec_blue = ""
    
    # Recommendations for RED
    if r_name == "ChaosBrain":
        rec_red = "Deploy Swarm/SunflowerBrain to coordinate."
    elif flag_holder == BLUE:
        rec_red = "Deploy SunflowerBrain to contest center flag."
    elif b_nodes > 3 and r_name != "ZMQBrainLike" and r_name != "TacticalChaosBrain":
        rec_red = "Deploy ZMQ or TacticalChaos to disrupt enemy hubs."
    else:
        rec_red = "Deploy SwarmBrain to expand territory."
        
    # Recommendations for BLUE
    if b_name == "ChaosBrain":
        rec_blue = "Deploy Swarm/SunflowerBrain to coordinate."
    elif flag_holder == RED:
        rec_blue = "Deploy SunflowerBrain to contest center flag."
    elif r_nodes > 3 and b_name != "ZMQBrainLike" and b_name != "TacticalChaosBrain":
        rec_blue = "Deploy ZMQ or TacticalChaos to disrupt enemy hubs."
    else:
        rec_blue = "Deploy SwarmBrain to expand territory."
        
    return rec_red, rec_blue


def reset_round():
    global grid, agents, trail_field, red_trail_field, blue_trail_field, flag_x, flag_y, flag_holder, flag_respawn_timer
    global history_red, history_blue, history_entropy, history_dominance_red, history_dominance_blue
    
    grid.fill(EMPTY)
    agents = spawn()
    trail_field.fill(0)
    red_trail_field.fill(0)
    blue_trail_field.fill(0)
    
    # Spawn flag back in the center for start of round
    flag_x = WIDTH // 2
    flag_y = HEIGHT // 2
    grid[flag_y][flag_x] = FLAG
    flag_holder = None
    flag_respawn_timer = 0
    
    # Reset graphs
    history_red.clear()
    history_blue.clear()
    history_entropy.clear()
    history_dominance_red.clear()
    history_dominance_blue.clear()


def draw_progress_bar(screen, x, y, w, h, val, max_val, color_rgb):
    # Draw background bar (dark grey)
    pygame.draw.rect(screen, (30, 30, 30), (x, y, w, h))
    # Draw filled portion
    pct = max(0.0, min(1.0, float(val) / float(max_val)))
    if pct > 0:
        pygame.draw.rect(screen, color_rgb, (x, y, int(w * pct), h))
    # Draw border
    pygame.draw.rect(screen, (80, 80, 80), (x, y, w, h), 1)


def draw_double_graph(screen, series_red, series_blue, x0, y0, w, h, max_val=200.0, draw_threshold=None):
    # Draw background box
    pygame.draw.rect(screen, (15, 15, 15), (x0, y0, w, h))
    pygame.draw.rect(screen, (50, 50, 50), (x0, y0, w, h), 1)
    
    # Draw horizontal grid line at 50%
    pygame.draw.line(screen, (40, 40, 40), (x0, y0 + h // 2), (x0 + w, y0 + h // 2), 1)
    
    # Draw threshold line if specified
    if draw_threshold is not None and draw_threshold <= max_val:
        thresh_y = y0 + h - int((draw_threshold / max_val) * h)
        # Draw thin solid yellow line
        pygame.draw.line(screen, (220, 220, 50), (x0, thresh_y), (x0 + w, thresh_y), 1)
        # Draw threshold label
        try:
            thresh_font = pygame.font.SysFont("consolas", 10)
        except Exception:
            thresh_font = pygame.font.Font(None, 10)
        surf = thresh_font.render(f"WIN: {int(draw_threshold)}", True, (220, 220, 50))
        screen.blit(surf, (x0 + 5, thresh_y - 12))

    # Helper to draw a single series
    def draw_series(series, color_rgb):
        if len(series) < 2:
            return
        # Plot up to last 200 history items
        pts = series[-MAX_HISTORY:]
        n = len(pts)
        for i in range(1, n):
            # Map index to X coordinate
            x1 = x0 + (i-1) * w // MAX_HISTORY
            x2 = x0 + i * w // MAX_HISTORY
            
            v1 = max(0.0, min(max_val, pts[i-1]))
            v2 = max(0.0, min(max_val, pts[i]))
            
            y1 = y0 + h - int((v1 / max_val) * h)
            y2 = y0 + h - int((v2 / max_val) * h)
            
            pygame.draw.line(screen, color_rgb, (x1, y1), (x2, y2), 2)

    draw_series(series_blue, (60, 120, 220))
    draw_series(series_red, (220, 60, 60))


def draw_comparison_card(screen, font):
    # Draw background box
    rect_x = WIDTH * CELL + 15
    rect_y = 465
    rect_w = 270
    rect_h = 120
    
    # Semi-transparent dark background
    box_surf = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
    box_surf.fill((15, 15, 15, 230))
    screen.blit(box_surf, (rect_x, rect_y))
    
    # Border
    pygame.draw.rect(screen, (70, 70, 70), (rect_x, rect_y, rect_w, rect_h), 1)
    
    # Lines of comparison
    try:
        title_font = pygame.font.SysFont("consolas", 12, bold=True)
    except Exception:
        title_font = pygame.font.Font(None, 12)
        
    title = title_font.render("TINY AMPS vs LEGACY SYSTEM", True, (240, 240, 240))
    screen.blit(title, (rect_x + 10, rect_y + 8))
    
    legacy_text = font.render("Legacy Ingest : 3,600 msg/s", True, (220, 80, 80))
    legacy_cpu  = font.render("  Subscriber CPU: 100.0% (Base)", True, (220, 80, 80))
    
    amps_text   = font.render("Tiny AMPS     : 60 msg/s", True, (80, 220, 80))
    amps_cpu    = font.render("  Subscriber CPU: 1.7% (-98.3%)", True, (80, 220, 80))
    
    screen.blit(legacy_text, (rect_x + 10, rect_y + 26))
    screen.blit(legacy_cpu, (rect_x + 10, rect_y + 42))
    screen.blit(amps_text, (rect_x + 10, rect_y + 65))
    screen.blit(amps_cpu, (rect_x + 10, rect_y + 81))


# =========================
# STATS + METRICS
# =========================

def stats(grid):
    r = np.sum(grid == RED)
    b = np.sum(grid == BLUE)
    e = np.sum(grid == EMPTY)
    return r, b, e


def entropy_measure():
    return float(
        np.mean(attraction_field)
        + np.mean(threat_field)
        + np.mean(frontier_field)
    )


def regression_trend(series):
    if len(series) < 10:
        return 0.0
    x = np.arange(len(series))
    y = np.array(series)
    slope = np.polyfit(x, y, 1)[0]
    return slope


def interpret(r_slope, b_slope, entropy):
    if entropy > 0.6:
        return "High chaos: swarm loses structure advantage"
    if r_slope > b_slope:
        return "Red gaining dominance via structural advantage"
    if b_slope > r_slope:
        return "Blue expanding more efficiently"
    return "Balanced system: no stable attractor yet"


def save_history():
    """Save the current history to a CSV file."""
    # Ensure data directory exists
    import os
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(data_dir, f"swarmsim_data_{timestamp}.csv")
    
    # Write CSV
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['frame', 'red_count', 'blue_count', 'entropy'])
        # We have three history lists; they should be the same length
        length = min(len(history_red), len(history_blue), len(history_entropy))
        for i in range(length):
            writer.writerow([i, history_red[i], history_blue[i], history_entropy[i]])
    
    print(f"History saved to {filename}")


# =========================
# DRAWING
# =========================

def color(v):
    if v == EMPTY:
        return (25, 25, 25)
    if v == RED:
        return (220, 60, 60)
    if v == BLUE:
        return (60, 120, 220)
    if v == FLAG:
        return (255, 255, 0)  # Yellow
    return (0, 0, 0)  # fallback


def draw_grid(screen, grid):
    for y in range(HEIGHT):
        for x in range(WIDTH):
            pygame.draw.rect(
                screen,
                color(grid[y][x]),
                (x * CELL, y * CELL, CELL, CELL)
            )


def draw_graph(screen, series, color_rgb, x0, y0, w, h):
    if len(series) < 2:
        return

    maxv = max(series) + 1e-6
    minv = min(series)

    for i in range(1, len(series)):
        x1 = x0 + (i-1) * w // MAX_HISTORY
        x2 = x0 + i * w // MAX_HISTORY

        y1 = y0 + h - int((series[i-1]-minv)/(maxv-minv+1e-6)*h)
        y2 = y0 + h - int((series[i]-minv)/(maxv-minv+1e-6)*h)

        pygame.draw.line(screen, color_rgb, (x1,y1), (x2,y2), 2)


# =========================
# INIT
# =========================

pygame.init()
try:
    screen = pygame.display.set_mode((WIDTH * CELL + 300, HEIGHT * CELL))
except pygame.error:
    import os
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.display.init()
    screen = pygame.display.set_mode((WIDTH * CELL + 300, HEIGHT * CELL))
    print("[SwarmSim] No graphical display available. Running in headless (dummy) mode.")

clock = pygame.time.Clock()
try:
    font = pygame.font.SysFont("consolas", 16)
except Exception:
    font = pygame.font.Font(None, 16)

grid = np.zeros((HEIGHT, WIDTH), dtype=np.int8)
# Place flag at center
grid[HEIGHT // 2, WIDTH // 2] = FLAG

if recording:
    import subprocess
    width_px = WIDTH * CELL + 300
    height_px = HEIGHT * CELL
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{width_px}x{height_px}', '-pix_fmt', 'rgb24', '-r', str(FPS),
        '-i', '-', '-an', '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'ultrafast', 'simulation_battle.mp4'
    ]
    video_pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    print(f"[SwarmSim] Recording enabled. Target duration: {args.record_duration}s ({args.record_duration * FPS} frames) to simulation_battle.mp4...")

red_count = 30
blue_count = 30


def spawn():
    agents = []
    for i in range(red_count):
        agents.append(Agent(i, RED))
    for i in range(blue_count):
        agents.append(Agent(i + 1000, BLUE))
    return agents


agents = spawn()

red_brain_idx = 0
blue_brain_idx = 0

# =========================
# AUTO COMMANDER LAYER
# =========================
AUTO_COMMANDER = True
RED_LATENCY = 0       # Tiny AMPS: Instant (0 frames delay)
BLUE_LATENCY = 150    # Legacy System: Delayed (150 frames delay due to subscriber tax/queue lag)

red_wins = 0
blue_wins = 0
win_banner_timer = 0
winner_team = None
flag_x = WIDTH // 2
flag_y = HEIGHT // 2

red_target_reason = ""
blue_target_reason = ""

red_target_brain_idx = 0
red_reaction_timer = 0

blue_target_brain_idx = 0
blue_reaction_timer = 0

def get_auto_brain_recommendation(team):
    global flag_holder, red_latest_metrics, blue_latest_metrics
    enemy_team = BLUE if team == RED else RED
    enemy_latest_metrics = blue_latest_metrics if team == RED else red_latest_metrics
    
    # 1. If enemy holds the flag -> SunflowerBrain (idx 3) to capture flag
    if flag_holder == enemy_team:
        return 3, "Enemy_holds_flag"
        
    # 2. If enemy has a strong node network -> deploy TacticalChaosBrain (idx 4) or ZMQBrainLike (idx 2)
    enemy_node_count = enemy_latest_metrics.get("num_nodes", 0) if enemy_latest_metrics else 0
    if enemy_node_count > 3:
        return (4 if team == RED else 2), "Enemy_has_dense_hubs"
        
    # 3. Otherwise, SwarmBrain (idx 1)
    return 1, "Build_territory_networks"

def update_auto_commander():
    global red_brain_idx, blue_brain_idx, red_target_brain_idx, red_reaction_timer, blue_target_brain_idx, blue_reaction_timer, red_target_reason, blue_target_reason
    if not AUTO_COMMANDER:
        return
        
    red_opt, red_res = get_auto_brain_recommendation(RED)
    blue_opt, blue_res = get_auto_brain_recommendation(BLUE)
    
    # RED (Tiny AMPS)
    if red_opt != red_target_brain_idx:
        red_target_brain_idx = red_opt
        red_target_reason = red_res
        red_reaction_timer = RED_LATENCY
        
    if red_reaction_timer > 0:
        red_reaction_timer -= 1
    elif red_brain_idx != red_target_brain_idx:
        red_brain_idx = red_target_brain_idx
        if amps_client:
            decision_msg = f"team=RED brain={BRAIN_CLASSES[red_brain_idx].__name__} delay=0f reason={red_target_reason}"
            amps_client.publish("swarm.event.decision", decision_msg.encode("utf-8"))
        
    # BLUE (Legacy)
    if blue_opt != blue_target_brain_idx:
        blue_target_brain_idx = blue_opt
        blue_target_reason = blue_res
        blue_reaction_timer = BLUE_LATENCY
        
    if blue_reaction_timer > 0:
        blue_reaction_timer -= 1
    elif blue_brain_idx != blue_target_brain_idx:
        blue_brain_idx = blue_target_brain_idx
        if amps_client:
            decision_msg = f"team=BLUE brain={BRAIN_CLASSES[blue_brain_idx].__name__} delay=150f reason={blue_target_reason}"
            amps_client.publish("swarm.event.decision", decision_msg.encode("utf-8"))


# =========================
# LOOP
# =========================

# Connect to Tiny AMPS broker
amps_client = None
try:
    import sys
    sys.path.insert(0, "/home/ds/Documents/Dev/tiny-amps-net/py")
    from amps import TinyAMPSTCPClient
    amps_client = TinyAMPSTCPClient(host="127.0.0.1", port=5585)
    print("[Tiny AMPS] Connected to local broker!")
except Exception as e:
    print(f"[Tiny AMPS] Failed to connect: {e}")

running = True

while running:
    screen.fill((0, 0, 0))
    update_auto_commander()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z:
                red_brain_idx = (red_brain_idx + 1) % len(BRAIN_CLASSES)

            if event.key == pygame.K_m:
                blue_brain_idx = (blue_brain_idx + 1) % len(BRAIN_CLASSES)

            if event.key == pygame.K_s:
                save_history()

    red_brain = BRAIN_CLASSES[red_brain_idx]()
    blue_brain = BRAIN_CLASSES[blue_brain_idx]()

    for a in agents:
        if a.team == RED:
            a.step(grid, red_brain)
        else:
            a.step(grid, blue_brain)

    # Publish high-frequency agent telemetry to Tiny AMPS
    if amps_client:
        closest_agent_id = -1
        min_dist = 9999.0
        for ag in agents:
            dist = ((ag.x - 60)**2 + (ag.y - 60)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_agent_id = ag.id

        for a in agents:
            is_closest = 1 if a.id == closest_agent_id else 0
            is_holder = 1 if flag_holder == a.team else 0
            payload = f"id={a.id} team={a.team} x={a.x} y={a.y} closest={is_closest} flag={is_holder}".encode("utf-8")
            amps_client.publish(f"swarm.telemetry.agent.{a.id}", payload)
            
            if is_closest and is_closest != getattr(a, "_prev_closest", 0):
                team_name = "RED" if a.team == RED else "BLUE"
                amps_client.publish(
                    "swarm.event.lead",
                    f"event=new_lead agent_id={a.id} team={team_name} x={a.x} y={a.y}".encode("utf-8")
                )
            setattr(a, "_prev_closest", is_closest)

    # --- Flag capture logic ---
    # Check if any agent is on the flag position
    if flag_holder is None:
        for a in agents:
            if a.x == flag_x and a.y == flag_y:
                # Agent captured the flag
                flag_holder = a.team
                grid[flag_y][flag_x] = EMPTY  # Remove flag
                if amps_client:
                    team_name = "RED" if a.team == RED else "BLUE"
                    amps_client.publish(
                        "swarm.event.flag",
                        f"event=capture agent_id={a.id} team={team_name} x={a.x} y={a.y}".encode("utf-8")
                    )
                flag_respawn_timer = FLAG_RESPAWN_DELAY
                # Reinforce trail for recent movement history
                for (hx, hy) in a.history:
                    trail_field[hy][hx] += CAPTURE_BONUS
                    if a.team == RED:
                        red_trail_field[hy][hx] += CAPTURE_BONUS
                    else:
                        blue_trail_field[hy][hx] += CAPTURE_BONUS
                break  # Only one capture per frame

    # Flag respawn timer
    if flag_respawn_timer > 0:
        flag_respawn_timer -= 1
        if flag_respawn_timer == 0:
            # Respawn flag at random position!
            flag_x = random.randint(15, WIDTH - 15)
            flag_y = random.randint(15, HEIGHT - 15)
            grid[flag_y][flag_x] = FLAG
            flag_holder = None
            if amps_client:
                amps_client.publish("swarm.event.flag", f"event=respawn x={flag_x} y={flag_y}".encode("utf-8"))

    update_fields(grid)
    decay_fields()
    decay_trail_fields()
    update_graph()
    apply_graph_warfare()
    update_simulation_metrics()
    update_exploration_rebound()

    r, b, e = stats(grid)

    # =========================
    # HISTORY UPDATE
    # =========================
    history_red.append(r)
    history_blue.append(b)
    history_entropy.append(entropy_measure())
    # Compute dominance for each team
    dominance_red = compute_dominance(RED, r, flag_holder, red_latest_metrics)
    dominance_blue = compute_dominance(BLUE, b, flag_holder, blue_latest_metrics)
    history_dominance_red.append(dominance_red)
    history_dominance_blue.append(dominance_blue)
    
    # Check for Victory Condition
    VICTORY_LIMIT = 180.0
    if dominance_red >= VICTORY_LIMIT and win_banner_timer == 0:
        winner_team = RED
        red_wins += 1
        win_banner_timer = 180  # 3 seconds at 60 FPS
        if amps_client:
            amps_client.publish(
                "swarm.event.victory",
                f"winner=RED red_wins={red_wins} blue_wins={blue_wins}".encode("utf-8")
            )
        reset_round()
    elif dominance_blue >= VICTORY_LIMIT and win_banner_timer == 0:
        winner_team = BLUE
        blue_wins += 1
        win_banner_timer = 180
        if amps_client:
            amps_client.publish(
                "swarm.event.victory",
                f"winner=BLUE red_wins={red_wins} blue_wins={blue_wins}".encode("utf-8")
            )
        reset_round()
    # Trim histories
    history_red[:] = history_red[-MAX_HISTORY:]
    history_blue[:] = history_blue[-MAX_HISTORY:]
    history_entropy[:] = history_entropy[-MAX_HISTORY:]
    history_dominance_red[:] = history_dominance_red[-MAX_DOMINANCE_HISTORY:]
    history_dominance_blue[:] = history_dominance_blue[-MAX_DOMINANCE_HISTORY:]

    # =========================
    # REGRESSION ANALYSIS
    # =========================
    red_dominance_slope = regression_trend(history_dominance_red)
    blue_dominance_slope = regression_trend(history_dominance_blue)

    explanation = interpret(red_dominance_slope, blue_dominance_slope, np.mean(history_entropy)+1e-6)

    # =========================
    # DRAW WORLD
    # =========================
    draw_grid(screen, grid)

    # graphs panel
    # HUD text
    rec_red, rec_blue = get_battle_recommendation()
    
    # Publish recommendation and latency metrics to Tiny AMPS
    if amps_client and frame_count % 100 == 0:
        payload_text = (
            f"RED: {rec_red} | BLUE: {rec_blue} | "
            f"RED_LAG: {red_reaction_timer}f | BLUE_LAG: {blue_reaction_timer}f"
        )
        amps_client.publish("swarm.event.recommendation", payload_text.encode("utf-8"))
        
    if red_dominance_slope > blue_dominance_slope + 0.001:
        outcome = "RED wins (Tiny AMPS zero lag)"
    elif blue_dominance_slope > red_dominance_slope + 0.001:
        outcome = "BLUE wins (Legacy queue lag)"
    else:
        outcome = "Stable deadlock"

    lines = [
        f"RED (Tiny AMPS) : {BRAIN_CLASSES[red_brain_idx].__name__}",
        f"BLUE (Legacy)   : {BRAIN_CLASSES[blue_brain_idx].__name__}",
        f"SCORE           : RED {red_wins} - {blue_wins} BLUE",
        f"FLAG HOLDER     : {flag_holder if flag_holder is not None else 'None'}",
        f"DECISION LATENCY:",
        f" RED (Tiny AMPS): {RED_LATENCY}f (Instant)",
        f" BLUE (Legacy)  : {BLUE_LATENCY}f (2.5s lag)",
        f"REACTION TIMERS:",
        f" RED: {red_reaction_timer}f | BLUE: {blue_reaction_timer}f",
        f"OUTCOME: {outcome}"
    ]

    panel_x = WIDTH * CELL + 20
    y = 10
    for l in lines:
        surf = font.render(l, True, (240,240,240))
        screen.blit(surf, (panel_x, y))
        y += 16

    # Draw Dominance Progress Bars
    red_dom_label = font.render(f"RED Dominance: {dominance_red:.1f} / 180.0", True, (220, 60, 60))
    screen.blit(red_dom_label, (panel_x, 180))
    draw_progress_bar(screen, panel_x, 196, 260, 8, dominance_red, 180.0, (220, 60, 60))

    blue_dom_label = font.render(f"BLUE Dominance: {dominance_blue:.1f} / 180.0", True, (60, 120, 220))
    screen.blit(blue_dom_label, (panel_x, 208))
    draw_progress_bar(screen, panel_x, 224, 260, 8, dominance_blue, 180.0, (60, 120, 220))

    # Draw Territory Graph (Cell Count)
    territory_label = font.render("TERRITORY (Cell Count)", True, (200, 200, 200))
    screen.blit(territory_label, (panel_x, 240))
    draw_double_graph(screen, history_red, history_blue, panel_x, 256, 260, 80, max_val=200.0)

    # Draw Dominance Graph
    dominance_label = font.render("DOMINANCE (Victory threshold 180)", True, (200, 200, 200))
    screen.blit(dominance_label, (panel_x, 345))
    draw_double_graph(screen, history_dominance_red, history_dominance_blue, panel_x, 361, 260, 80, max_val=200.0, draw_threshold=180.0)

    # Screenshot and data logging
    frame_count += 1
    if frame_count % SCREENSHOT_INTERVAL == 0:
        # Save screenshot
        screenshot_path = os.path.join("screenshots", f"swarmsim_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        pygame.image.save(screen, screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
        # Save history data
        save_history()
        print(f"History data saved at frame {frame_count}")

    # Draw victory banner
    if win_banner_timer > 0:
        win_banner_timer -= 1
        if winner_team is not None:
            banner_text = "RED (TINY AMPS) WINS ROUND!" if winner_team == RED else "BLUE (LEGACY LAG) WINS ROUND!"
            banner_color = (220, 60, 60) if winner_team == RED else (60, 120, 220)
            try:
                large_font = pygame.font.SysFont("consolas", 18, bold=True)
            except Exception:
                large_font = pygame.font.Font(None, 18)
            surf = large_font.render(banner_text, True, banner_color)
            text_w, text_h = surf.get_size()
            box_w, box_h = text_w + 30, text_h + 16
            box_x, box_y = (WIDTH * CELL) // 2 - box_w // 2, (HEIGHT * CELL) // 2 - box_h // 2
            pygame.draw.rect(screen, (15, 15, 15), (box_x, box_y, box_w, box_h))
            pygame.draw.rect(screen, banner_color, (box_x, box_y, box_w, box_h), 2)
            screen.blit(surf, (box_x + 15, box_y + 8))

    draw_comparison_card(screen, font)
    pygame.display.flip()

    if recording and video_pipe:
        raw_data = pygame.image.tostring(screen, 'RGB')
        video_pipe.stdin.write(raw_data)
        if frame_count >= args.record_duration * FPS:
            print("[SwarmSim] Recording complete! Closing video stream...")
            video_pipe.stdin.close()
            video_pipe.wait()
            running = False

    if not recording:
        clock.tick(FPS)

pygame.quit()