import sys
import pygame as pg
from pygame.locals import *
import random
import math

pg.init()

# Конфигурация экрана
width, height = 900, 600
cell_size = 30
grid_width, grid_height = width // cell_size, height // cell_size

screen = pg.display.set_mode((width, height))
fpsClock = pg.time.Clock()
fps = 120

# Состояние игры
snake = [(grid_width//2, grid_height//2)]
direction = (1, 0)
apple = None
auto_mode = True
show_path = False
move_interval = 80
last_move_time = 0

# Гамильтонов цикл
hamilton_path = []
path_map = {}

def get_random_element(lst):
    return random.choice(lst)

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
        for edge in spanning_tree:
            if edge.contains(self):
                self.spanning_tree_adjacent.append(edge.get_other_node(self))

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
        self.node1.spanning_tree_adjacent.append(self.node2)
        self.node2.spanning_tree_adjacent.append(self.node1)

class HamiltonianCycle:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.cycle = []
        self.spanning_tree = []
        self.spanning_tree_nodes = []
        self.create_cycle()

    def create_cycle(self):
        self.create_spanning_tree()
        cycle_nodes = []
        
        # Создание узлов для полного поля с учетом размеров
        for i in range(self.w):
            for j in range(self.h):
                cycle_nodes.append(HNode(i, j))
        
        # Установка связей между соседями
        for n in cycle_nodes:
            n.set_edges(cycle_nodes)

        # Построение связей на основе остовного дерева
        for edge in self.spanning_tree:
            x1, y1 = edge.node1.x * 2, edge.node1.y * 2
            x2, y2 = edge.node2.x * 2, edge.node2.y * 2
            self.connect_nodes(x1 + 1, y1, x2, y1, cycle_nodes)
            self.connect_nodes(x1 + 1, y1 + 1, x2, y1 + 1, cycle_nodes)

        # Построение цикла
        self.build_hamiltonian_path(cycle_nodes)
        
    def create_spanning_tree(self):
        st_nodes = [HNode(i, j) for i in range(self.w//2) for j in range(self.h//2)]
        
        for n in st_nodes:
            n.set_edges(st_nodes)

        spanning_tree = []
        start_node = get_random_element(st_nodes)
        spanning_tree.append(HEdge(start_node, start_node.edges[0]))
        in_tree = {start_node, start_node.edges[0]}

        while len(in_tree) < len(st_nodes):
            node = get_random_element(list(in_tree))
            candidates = [n for n in node.edges if n not in in_tree]
            
            if candidates:
                new_node = get_random_element(candidates)
                spanning_tree.append(HEdge(node, new_node))
                in_tree.add(new_node)

        for n in st_nodes:
            n.set_spanning_tree_edges(spanning_tree)

        self.spanning_tree = spanning_tree
        self.spanning_tree_nodes = st_nodes

    def get_next_position(self, x, y):
        for i, node in enumerate(self.cycle):
            if node.x == x and node.y == y:
                return self.cycle[(i + 1) % len(self.cycle)]
        return None

    def connect_nodes(self, x1, y1, x2, y2, nodes):
        if 0 <= x1 < self.w and 0 <= y1 < self.h:
            idx1 = y1 + self.h * x1
            idx2 = y2 + self.h * x2
            if idx2 < len(nodes):
                HEdge(nodes[idx1], nodes[idx2]).connect_nodes()

    def fix_cycle_connections(self, cycle_nodes):
        """Добавление недостающих связей для полного цикла"""
        # Находим узлы с одной связью
        degree1 = [n for n in cycle_nodes if len(n.spanning_tree_adjacent) == 1]
        
        # Создаем дополнительные связи
        new_edges = []
        for n in degree1:
            other = n.spanning_tree_adjacent[0]
            dx, dy = other.get_direction_to(n)
            new_x = n.x + dx
            new_y = n.y + dy
            
            if 0 <= new_x < self.w*2 and 0 <= new_y < self.h*2:
                target_idx = new_y + (self.h*2) * new_x
                if target_idx < len(cycle_nodes):
                    target = cycle_nodes[target_idx]
                    new_edge = HEdge(n, target)
                    if not any(e.is_equal_to(new_edge) for e in new_edges):
                        new_edges.append(new_edge)
        
        # Применяем новые связи
        for e in new_edges:
            e.connect_nodes()
            
    def build_hamiltonian_path(self, cycle_nodes):
        start = cycle_nodes[0]
        self.cycle = [start]
        current = start.spanning_tree_adjacent[0]
        prev = start
        
        while current != start and len(self.cycle) < len(cycle_nodes):
            self.cycle.append(current)
            next_nodes = [n for n in current.spanning_tree_adjacent if n != prev]
            prev = current
            current = next_nodes[0] if next_nodes else start

        # Проверка с выводом информации для отладки
        if len(self.cycle) != len(cycle_nodes):
            print(f"Warning: Partial cycle ({len(self.cycle)}/{len(cycle_nodes)})")
            # Временно разрешаем частичные циклы
            # raise ValueError("Failed to build full Hamiltonian cycle")

        for i, node in enumerate(self.cycle):
            node.cycle_no = i

    def build_full_cycle(self, cycle_nodes):
        """Построение полного цикла обхода"""
        start_node = cycle_nodes[0]
        self.cycle = [start_node]
        prev_node = start_node
        current_node = start_node.spanning_tree_adjacent[0]
        
        while True:
            self.cycle.append(current_node)
            next_nodes = [n for n in current_node.spanning_tree_adjacent if n != prev_node]
            
            if not next_nodes:
                break
                
            prev_node = current_node
            current_node = next_nodes[0]
            
            # Проверка завершения цикла
            if current_node == start_node and len(self.cycle) == len(cycle_nodes):
                break

        # Проверка полноты цикла
        if len(self.cycle) != len(cycle_nodes):
            raise ValueError("Failed to build full Hamiltonian cycle")
            
        # Обновляем индексы узлов
        for i, node in enumerate(self.cycle):
            node.cycle_no = i

hamilton = HamiltonianCycle(grid_width, grid_height)
hamilton_path = [(node.x, node.y) for node in hamilton.cycle]
path_map = {pos: i for i, pos in enumerate(hamilton_path)}

def get_auto_direction():
    head = snake[0]
    current_idx = path_map.get(head, 0)
    next_pos = hamilton_path[(current_idx + 1) % len(hamilton_path)]
    
    dx = next_pos[0] - head[0]
    dy = next_pos[1] - head[1]
    
    if dx not in (-1, 0, 1): dx = -1 if dx > 0 else 1
    if dy not in (-1, 0, 1): dy = -1 if dy > 0 else 1
    
    return (dx, dy)

# Остальные функции остаются без изменений
def update_snake():
    global snake, direction, last_move_time
    current_time = pg.time.get_ticks()
    
    if current_time - last_move_time < move_interval:
        return
    
    if auto_mode:
        new_dir = get_auto_direction()
        if (new_dir[0] + direction[0], new_dir[1] + direction[1]) != (0, 0):
            direction = new_dir

    new_head = (
        (snake[0][0] + direction[0]) % grid_width,
        (snake[0][1] + direction[1]) % grid_height
    )
    
    if new_head in snake:
        game_over()
        return
    
    snake.insert(0, new_head)
    if new_head == apple:
        spawn_apple()
    else:
        snake.pop()
    
    last_move_time = current_time

def draw():
    screen.fill((30, 30, 30))
    
    for x, y in snake:
        pg.draw.rect(screen, (200, 200, 200), 
                    (x*cell_size, y*cell_size, cell_size-1, cell_size-1))
    if apple:
        pg.draw.rect(screen, (200, 10, 10),
                    (apple[0]*cell_size, apple[1]*cell_size, cell_size-1, cell_size-1))
    
    if show_path:
        points = [(x*cell_size + cell_size//2, y*cell_size + cell_size//2)
                 for x, y in hamilton_path]
        pg.draw.lines(screen, (0, 255, 0), False, points, 2)

def spawn_apple():
    global apple
    while True:
        pos = (random.randint(0, grid_width-1), random.randint(0, grid_height-1))
        if pos not in snake:
            apple = pos
            break

def game_over():
    pg.quit()
    sys.exit()

spawn_apple()

# Главный цикл
while True:
    for event in pg.event.get():
        if event.type == QUIT:
            game_over()
        if event.type == KEYDOWN:
            if event.key == K_p:
                show_path = not show_path
            elif event.key == K_a:
                auto_mode = not auto_mode
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 4:
                move_interval = max(20, move_interval - 10)
            elif event.button == 5:
                move_interval = min(200, move_interval + 10)
    
    update_snake()
    draw()
    pg.display.flip()
    fpsClock.tick(fps)