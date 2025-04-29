# hamiltonian.py
import math
import random

class HNode:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.edges = []
        self.spanning_tree_adjacent = []
        self.cycle_no = -1

    def set_edges(self, all_nodes):
        self.edges = [
            n for n in all_nodes 
            if math.dist((self.x, self.y), (n.x, n.y)) == 1
        ]

    def set_spanning_tree_edges(self, spanning_tree):
        self.spanning_tree_adjacent = []
        for edge in spanning_tree:
            if edge.contains(self):
                other = edge.get_other_node(self)
                if other not in self.spanning_tree_adjacent:
                    self.spanning_tree_adjacent.append(other)
    
    def get_direction_to(self, other):
        return (other.x - self.x, other.y - self.y)

class HEdge:
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2

    def is_equal_to(self, other):
        return (self.node1 == other.node1 and self.node2 == other.node2) or \
               (self.node1 == other.node2 and self.node2 == other.node1)

    def contains(self, node):
        return node == self.node1 or node == self.node2

    def get_other_node(self, node):
        return self.node2 if node == self.node1 else self.node1

    def connect_nodes(self):
        if self.node2 not in self.node1.spanning_tree_adjacent:
            self.node1.spanning_tree_adjacent.append(self.node2)
        if self.node1 not in self.node2.spanning_tree_adjacent:
            self.node2.spanning_tree_adjacent.append(self.node1)

class HamiltonianCycle:
    def __init__(self, base_w, base_h):
        self.base_w = base_w
        self.base_h = base_h
        self.full_w = base_w * 2
        self.full_h = base_h * 2
        self.cycle = []
        self.spanning_tree = []
        self.create_cycle()

    def create_cycle(self):
        # Create spanning tree for the base grid
        self.create_spanning_tree()
        
        # Create nodes for the full-size grid
        cycle_nodes = []
        for i in range(self.full_w):
            for j in range(self.full_h):
                cycle_nodes.append(HNode(i, j))
        
        # Set edges between neighboring nodes
        for n in cycle_nodes:
            n.set_edges(cycle_nodes)
        
        # Connect nodes based on the spanning tree connections
        for st_node in self.spanning_tree_nodes:
            for other in st_node.spanning_tree_adjacent:
                direction = st_node.get_direction_to(other)
                x = st_node.x * 2
                y = st_node.y * 2
                
                # Create the corresponding connections in the full grid
                if direction[0] == 1:  # Node is to the right
                    self.connect_pair(x + 1, y, x + 2, y, cycle_nodes)
                    self.connect_pair(x + 1, y + 1, x + 2, y + 1, cycle_nodes)
                elif direction[1] == 1:  # Node is below
                    self.connect_pair(x, y + 1, x, y + 2, cycle_nodes)
                    self.connect_pair(x + 1, y + 1, x + 1, y + 2, cycle_nodes)
        
        # Find nodes with only one connection and connect them
        self.fix_degree_one_nodes(cycle_nodes)
        
        # Build the cycle
        self.build_cycle(cycle_nodes)
        
        # Assign cycle numbers
        for i, node in enumerate(self.cycle):
            node.cycle_no = i

    def connect_pair(self, x1, y1, x2, y2, nodes):
        """Connect two nodes in the full grid by their coordinates"""
        if (0 <= x1 < self.full_w and 0 <= y1 < self.full_h and 
            0 <= x2 < self.full_w and 0 <= y2 < self.full_h):
            idx1 = y1 + self.full_h * x1
            idx2 = y2 + self.full_h * x2
            if idx1 < len(nodes) and idx2 < len(nodes):
                a = nodes[idx1]
                b = nodes[idx2]
                if b not in a.spanning_tree_adjacent:
                    a.spanning_tree_adjacent.append(b)
                if a not in b.spanning_tree_adjacent:
                    b.spanning_tree_adjacent.append(a)

    def fix_degree_one_nodes(self, cycle_nodes):
        """Connect nodes that have only one connection"""
        # First round of fixing - based on direction
        degree1_nodes = [n for n in cycle_nodes if len(n.spanning_tree_adjacent) == 1]
        new_edges = []
        
        for node in degree1_nodes:
            if not node.spanning_tree_adjacent:
                continue
                
            # Get direction from the connected node to this node
            other = node.spanning_tree_adjacent[0]
            dx, dy = node.x - other.x, node.y - other.y
            
            # Extend in the same direction to find another node
            target_x, target_y = node.x + dx, node.y + dy
            
            if (0 <= target_x < self.full_w and 0 <= target_y < self.full_h):
                # Calculate the index in the flat list
                target_idx = target_y + self.full_h * target_x
                if target_idx < len(cycle_nodes):
                    target = cycle_nodes[target_idx]
                    edge = HEdge(node, target)
                    # Check if the edge is already added
                    unique_edge = True
                    for e in new_edges:
                        if e.is_equal_to(edge):
                            unique_edge = False
                            break
                    if unique_edge:
                        new_edges.append(edge)
        
        # Connect all new edges
        for edge in new_edges:
            edge.connect_nodes()
        
        # Second round of fixing - connect remaining degree1 nodes
        degree1_nodes = [n for n in cycle_nodes if len(n.spanning_tree_adjacent) == 1]
        new_edges = []
        
        for node in degree1_nodes:
            # Find another degree1 node that's adjacent to this one and in the same cell
            for other in degree1_nodes:
                if node != other and math.dist((node.x, node.y), (other.x, other.y)) == 1:
                    # Check if they're in the same 2x2 cell
                    if (node.x // 2 == other.x // 2 and node.y // 2 == other.y // 2):
                        edge = HEdge(node, other)
                        # Check for uniqueness
                        unique_edge = True
                        for e in new_edges:
                            if e.is_equal_to(edge):
                                unique_edge = False
                                break
                        if unique_edge:
                            new_edges.append(edge)
                        break
        
        # Connect all new edges from second round
        for edge in new_edges:
            edge.connect_nodes()

    def build_cycle(self, cycle_nodes):
        """Build a cycle starting from a random node"""
        # Find a node with at least one connection
        start = next((n for n in cycle_nodes if n.spanning_tree_adjacent), None)
        if not start:
            raise ValueError("No valid start node found")
        
        self.cycle = [start]
        
        if not start.spanning_tree_adjacent:
            raise ValueError("Starting node has no connections")
            
        current = start.spanning_tree_adjacent[0]
        previous = start
        
        # Keep traversing until we return to the start
        while current != start:
            # Add the current node to the cycle
            self.cycle.append(current)
            
            # Find the next node to visit
            next_node = None
            for node in current.spanning_tree_adjacent:
                if node != previous:
                    next_node = node
                    break
            
            if not next_node:
                # If we can't find a next node that's not the previous one,
                # that means we've reached a dead end (this shouldn't happen)
                break
            
            previous = current
            current = next_node
        
        # Verify the cycle is complete
        if len(self.cycle) != len(cycle_nodes):
            missing = len(cycle_nodes) - len(self.cycle)
            raise ValueError(f"Cycle incomplete! Missing {missing} nodes")

    def create_spanning_tree(self):
        """Create a random spanning tree for the base grid"""
        # Create nodes for the base grid
        st_nodes = []
        for i in range(self.base_w):
            for j in range(self.base_h):
                st_nodes.append(HNode(i, j))
        
        # Set edges between neighboring nodes
        for n in st_nodes:
            n.set_edges(st_nodes)
        
        # Create a random spanning tree
        spanning_tree = []
        
        # Start with a random node
        random_node = random.choice(st_nodes)
        if not random_node.edges:
            random_node = next(n for n in st_nodes if n.edges)
            
        # Connect it to a random neighbor
        random_edge = random.choice(random_node.edges)
        spanning_tree.append(HEdge(random_node, random_edge))
        
        # Track nodes that are part of the tree
        nodes_in_tree = [random_node, random_edge]
        
        # Add edges until all nodes are in the tree
        while len(nodes_in_tree) < len(st_nodes):
            # Select a random node from the tree
            current_node = random.choice(nodes_in_tree)
            
            # Find neighbors that aren't in the tree yet
            available_edges = [n for n in current_node.edges if n not in nodes_in_tree]
            
            if available_edges:
                # Connect to a random neighbor
                next_node = random.choice(available_edges)
                nodes_in_tree.append(next_node)
                spanning_tree.append(HEdge(current_node, next_node))
        
        # Set spanning tree edges for all nodes
        for n in st_nodes:
            n.set_spanning_tree_edges(spanning_tree)
        
        self.spanning_tree = spanning_tree
        self.spanning_tree_nodes = st_nodes

    def get_next_position(self, x, y):
        """Get the next position in the cycle after (x,y)"""
        for i, node in enumerate(self.cycle):
            if node.x == x and node.y == y:
                return self.cycle[(i + 1) % len(self.cycle)]
        return None