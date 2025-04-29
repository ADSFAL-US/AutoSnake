import sys
import pygame as pg
from pygame.locals import *
import random
import math
import time
import ctypes
import os
import threading
from hamiltonial import HamiltonianCycle, HNode, HEdge
from pystray import MenuItem as item
import pystray
from PIL import Image, ImageDraw

# Если NOFRAME не определен в pygame, определим его сами
try:
    NOFRAME
except NameError:
    NOFRAME = 0x00000020  # Типичное значение для SDL_NOFRAME

# Windows API для мониторинга активности и управления окнами
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Константы
SW_HIDE = 0
SW_SHOW = 5
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9
SPI_GETSCREENSAVEACTIVE = 16
SPI_SETSCREENSAVEACTIVE = 17
WS_EX_TOOLWINDOW = 0x00000080
GWL_EXSTYLE = -20
GWL_STYLE = -16
WS_POPUP = 0x80000000

# Константы для скринсейвера
INACTIVITY_START_GENERATING = 5 #90  # 1.5 минуты в секундах
INACTIVITY_START_SCREENSAVER = 10 #120  # 2 минуты в секундах

# Глобальные переменные
last_activity_time = time.time()
screensaver_active = False
generating_cycle = False
hamilton = None
running = True
pygame_thread = None
icon = None
last_move_time = 0
hamilton_path = []
path_map = {}
snake = []
direction = (1, 0)
add_count = 0
apple = None
head_cycle_position = 0

def load_settings():
    """Загрузка настроек из файла settings.txt"""
    default_settings = {
        "width": 24,  # четное число ячеек по горизонтали
        "height": 16,  # четное число ячеек по вертикали
        "delay": 80   # задержка между тиками змейки
    }
    
    settings = default_settings.copy()
    
    try:
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        if key in settings:
                            settings[key] = int(value)
    except Exception as e:
        print(f"Ошибка при чтении настроек: {e}")
    
    # Проверка валидности настроек
    if settings["width"] % 2 != 0:
        settings["width"] = (settings["width"] // 2) * 2
    if settings["height"] % 2 != 0:
        settings["height"] = (settings["height"] // 2) * 2
    if settings["delay"] <= 0:
        settings["delay"] = 80
    
    return settings

def create_tray_icon():
    """Создаёт иконку в системном трее"""
    # Создаем простую иконку
    image = Image.new('RGB', (64, 64), color = (0, 128, 0))
    d = ImageDraw.Draw(image)
    # Рисуем змейку
    for i in range(3):
        d.rectangle((10 + i*15, 30, 20 + i*15, 40), fill=(0, 255, 0))
    # Рисуем яблоко
    d.rectangle((45, 20, 55, 30), fill=(255, 0, 0))
    
    def on_quit():
        global running
        running = False
        icon.stop()
        
    # Создаем меню
    menu = (item('Выход', on_quit),)
    
    # Создаем иконку
    global icon
    icon = pystray.Icon("snake_screensaver", image, "Snake Screensaver", menu)
    icon.run()

def remove_from_taskbar(hwnd):
    """Удаляет окно из таскбара"""
    # Получение текущего стиля окна
    style = user32.GetWindowLongA(hwnd, GWL_EXSTYLE)
    # Добавление флага WS_EX_TOOLWINDOW
    user32.SetWindowLongA(hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW)

def check_activity():
    """Проверяет активность пользователя"""
    global last_activity_time, screensaver_active, generating_cycle, hamilton
    
    # Получаем информацию о позиции мыши и нажатиях клавиш
    current_time = time.time()
    
    # Проверка, есть ли активность
    mouse_info = pg.mouse.get_rel()
    keys_pressed = any(pg.key.get_pressed())
    mouse_pressed = any(pg.mouse.get_pressed())
    
    activity_detected = mouse_info != (0, 0) or keys_pressed or mouse_pressed
    
    if activity_detected:
        # Сбрасываем таймер при обнаружении активности
        if screensaver_active:
            # Если активен скринсейвер, скрываем окно и очищаем цикл
            hide_window()
            screensaver_active = False
            
        if generating_cycle:
            # Если идет генерация, останавливаем
            generating_cycle = False
            
        last_activity_time = current_time
        return True
        
    # Проверяем, нужно ли начать генерацию цикла
    inactivity_time = current_time - last_activity_time
    
    if not generating_cycle and not screensaver_active and inactivity_time >= INACTIVITY_START_GENERATING:
        generating_cycle = True
        
    # Проверяем, нужно ли активировать скринсейвер
    if generating_cycle and not screensaver_active and inactivity_time >= INACTIVITY_START_SCREENSAVER:
        if hamilton and hamilton.cycle:
            init_game()  # Инициализируем игру перед показом окна
            screensaver_active = True
            show_window()
            
    return False

def hide_window():
    """Скрывает окно программы"""
    hwnd = pg.display.get_wm_info()["window"]
    
    # Полностью скрываем окно
    user32.ShowWindow(hwnd, SW_HIDE)
    
    # Дополнительно перемещаем его за пределы экрана
    user32.SetWindowPos(hwnd, 0, -32000, -32000, 0, 0, 0x0001)
    
    # Установим минимальный стиль окна, чтобы убрать заголовок и границы
    style = user32.GetWindowLongA(hwnd, GWL_STYLE)
    user32.SetWindowLongA(hwnd, GWL_STYLE, WS_POPUP)

def show_window():
    """Показывает и разворачивает окно программы"""
    hwnd = pg.display.get_wm_info()["window"]
    
    # Восстанавливаем стиль окна, чтобы убрать декорации
    user32.SetWindowLongA(hwnd, GWL_STYLE, WS_POPUP)
    
    # Сначала возвращаем окно на экран
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001)
    
    # Затем показываем и разворачиваем
    user32.ShowWindow(hwnd, SW_MAXIMIZE)
    user32.SetForegroundWindow(hwnd)

def init_game():
    """Инициализирует игру и гамильтонов цикл"""
    global hamilton, hamilton_path, path_map, snake, direction, add_count, apple
    
    # Получаем настройки
    settings = load_settings()
    grid_width, grid_height = settings["width"], settings["height"]
    
    # Инициализация гамильтонова цикла
    if hamilton is None:
        hamilton = HamiltonianCycle(grid_width//2, grid_height//2)
    
    # Инициализируем путь и карту только если цикл доступен
    if hamilton and hamilton.cycle:
        hamilton_path = [(node.x, node.y) for node in hamilton.cycle]
        path_map = {pos: i for i, pos in enumerate(hamilton_path)}
    
    # Инициализируем змейку
    snake = [(grid_width//2, grid_height//2)]
    snake.append((grid_width//2 - 1, grid_height//2))
    snake.append((grid_width//2 - 2, grid_height//2))
    direction = (1, 0)
    add_count = 0
    
    # Создаем яблоко
    available = []
    for x in range(grid_width):
        for y in range(grid_height):
            pos = (x, y)
            if pos not in snake:
                available.append(pos)
    
    if available:
        apple = random.choice(available)

def main():
    global hamilton, generating_cycle, screensaver_active, last_activity_time, running
    global hamilton_path, path_map, snake, direction, add_count, apple, head_cycle_position, last_move_time
    
    # Инициализация Pygame
    pg.init()
    
    # Загрузка настроек
    settings = load_settings()
    
    # Настройка размеров
    width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    # Рассчитываем размер ячейки так, чтобы они поместились в экран с отступом
    max_cell_width = (width - 20) // settings["width"]
    max_cell_height = (height - 20) // settings["height"]
    cell_size = min(max_cell_width, max_cell_height)
    
    # Рассчитываем размеры игрового поля
    grid_width, grid_height = settings["width"], settings["height"]
    game_width = cell_size * grid_width
    game_height = cell_size * grid_height
    
    # Рассчитываем отступы для центрирования игры на экране
    margin_x = (width - game_width) // 2
    margin_y = (height - game_height) // 2
    
    move_interval = settings["delay"]
    
    # Создаем окно с атрибутами для предотвращения показа заголовка
    os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    
    # Используем FULLSCREEN для создания окна без заголовка
    screen = pg.display.set_mode((width, height), FULLSCREEN | NOFRAME)
    
    # Скрываем курсор мыши в полноэкранном режиме
    pg.mouse.set_visible(False)
    
    pg.display.set_caption("Snake Screensaver")
    
    # Удаляем окно из таскбара
    hwnd = pg.display.get_wm_info()["window"]
    remove_from_taskbar(hwnd)
    
    # Скрываем окно при запуске
    hide_window()
    
    # Инициализация переменных
    snake.clear()
    snake.append((grid_width//2, grid_height//2))
    snake.append((grid_width//2 - 1, grid_height//2))
    snake.append((grid_width//2 - 2, grid_height//2))
    direction = (1, 0)
    apple = None
    auto_mode = True
    show_path = False
    last_move_time = 0
    add_count = 0
    acceleration_mode = True
    fpsClock = pg.time.Clock()
    fps = 60
    
    # Инициализация переменных AI
    head_cycle_position = 0
    tail_cycle_position = 0
    
    # Определение функций для игры
    def get_cycle_position(pos):
        return path_map.get(pos, -1)

    def get_distance_between_points(from_pos, to_pos):
        distance = to_pos - from_pos
        while distance < 0:
            distance += len(hamilton_path)
        return distance

    def is_adjacent(pos1, pos2):
        dx = abs(pos1[0] - pos2[0])
        dy = abs(pos1[1] - pos2[1])
        return (dx == 1 and dy == 0) or (dx == 0 and dy == 1)

    def will_overtake_tail(new_pos_cycle):
        min_distance_between_head_and_tail = 50
        actual_tail = get_cycle_position(snake[-1])
        
        if actual_tail == -1:
            return True
        
        if get_distance_between_points(head_cycle_position, actual_tail) <= min_distance_between_head_and_tail + add_count:
            return True
        
        tail = actual_tail - min_distance_between_head_and_tail - add_count
        if tail < 0:
            tail += len(hamilton_path)
        
        if get_distance_between_points(head_cycle_position, new_pos_cycle) >= get_distance_between_points(head_cycle_position, tail):
            return True
        
        return False

    def get_next_position(head, tail, apple_pos):
        global head_cycle_position
        
        head_cycle_position = get_cycle_position(head)
        
        if head_cycle_position == -1:
            print("ОШИБКА: Голова змейки не находится на пути цикла Гамильтона!")
            # Попробуем восстановить позицию головы
            for i, pos in enumerate(hamilton_path):
                if pos == head:
                    head_cycle_position = i
                    break
            # Если не удалось, используем безопасный путь
            if head_cycle_position == -1:
                return follow_safe_path()
        
        apple_cycle_pos = get_cycle_position(apple_pos)
        
        possible_next_positions = []
        for i in range(len(hamilton_path)):
            if is_adjacent(head, hamilton_path[i]):
                possible_next_positions.append(i)
        
        if acceleration_mode and possible_next_positions:
            min_dist = float('inf')
            min_index = 0
            
            for i, pos_idx in enumerate(possible_next_positions):
                distance = apple_cycle_pos - pos_idx
                while distance < 0:
                    distance += len(hamilton_path)
                
                if will_overtake_tail(pos_idx):
                    continue
                
                if distance < min_dist:
                    min_dist = distance
                    min_index = i
            
            if min_dist != float('inf'):
                return hamilton_path[possible_next_positions[min_index]]
        
        next_cycle_pos = (head_cycle_position + 1) % len(hamilton_path)
        return hamilton_path[next_cycle_pos]

    def follow_safe_path():
        head = snake[0]
        current_idx = get_cycle_position(head)
        
        if current_idx == -1:
            min_dist = float('inf')
            closest_idx = 0
            
            for i, pos in enumerate(hamilton_path):
                dist = abs(pos[0] - head[0]) + abs(pos[1] - head[1])
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            
            current_idx = closest_idx
        
        next_pos = hamilton_path[(current_idx + 1) % len(hamilton_path)]
        return next_pos

    def get_auto_direction():
        head = snake[0]
        tail = snake[-1]
        next_pos = get_next_position(head, tail, apple)
        
        dx = next_pos[0] - head[0]
        dy = next_pos[1] - head[1]
        
        if dx != 0:
            dx = 1 if dx > 0 else -1
        if dy != 0:
            dy = 1 if dy > 0 else -1
        
        return (dx, dy)

    def update_snake():
        global snake, direction, add_count, head_cycle_position, last_move_time, apple
        current_time = pg.time.get_ticks()
        
        if current_time - last_move_time < move_interval:
            return
        
        if auto_mode and hamilton and hamilton_path:
            new_dir = get_auto_direction()
            if (new_dir[0] + direction[0], new_dir[1] + direction[1]) != (0, 0):
                direction = new_dir

        new_head = (
            snake[0][0] + direction[0],
            snake[0][1] + direction[1]
        )
        
        if (new_head[0] < 0 or new_head[0] >= grid_width or 
            new_head[1] < 0 or new_head[1] >= grid_height):
            reset_game()
            return
        
        if new_head in snake:
            reset_game()
            return
        
        snake.insert(0, new_head)
        
        if new_head == apple:
            add_count += 4
            spawn_apple()
        else:
            if add_count <= 0:
                snake.pop()
            else:
                add_count -= 1
        
        last_move_time = current_time

    def draw():
        if not screensaver_active:
            # Если скринсейвер не активен, очищаем экран
            screen.fill((0, 0, 0))
            return
            
        screen.fill((30, 30, 30))
        
        # Draw snake
        for i, (x, y) in enumerate(snake):
            color_value = max(100, 200 - i * 3)
            pg.draw.rect(screen, (0, color_value, 0), 
                        (margin_x + x*cell_size, margin_y + y*cell_size, cell_size-1, cell_size-1))
        
        # Draw apple
        if apple:
            pg.draw.rect(screen, (200, 10, 10),
                        (margin_x + apple[0]*cell_size, margin_y + apple[1]*cell_size, cell_size-1, cell_size-1))
        
        # Draw path if enabled
        if show_path and hamilton and hamilton_path:
            # Draw Hamiltonian cycle
            points = [(margin_x + x*cell_size + cell_size//2, margin_y + y*cell_size + cell_size//2)
                    for x, y in hamilton_path]
            pg.draw.lines(screen, (0, 255, 0, 128), True, points, 2)
            
            # Отображаем позиции всех сегментов змейки на цикле
            for i, segment in enumerate(snake):
                seg_cycle_pos = get_cycle_position(segment)
                if seg_cycle_pos != -1:
                    seg_pos = hamilton_path[seg_cycle_pos]
                    r = min(255, int(255 * (1 - i / len(snake))))
                    b = min(255, int(255 * (i / len(snake))))
                    pg.draw.circle(screen, (r, 100, b), 
                                (margin_x + seg_pos[0]*cell_size + cell_size//2, 
                                 margin_y + seg_pos[1]*cell_size + cell_size//2), 3)
                
            # Отображение информации отладки
            real_tail_position = get_cycle_position(snake[-1])
            font = pg.font.SysFont(None, 24)
            text = font.render(f"Head: {head_cycle_position}, Tail: {real_tail_position}, Len: {len(snake)}", True, (255, 255, 255))
            screen.blit(text, (margin_x + 10, margin_y + 10))

    def spawn_apple():
        global apple
        available = []
        for x in range(grid_width):
            for y in range(grid_height):
                pos = (x, y)
                if pos not in snake:
                    available.append(pos)
        
        if available:
            apple = random.choice(available)

    def reset_game():
        global snake, direction, add_count
        snake = [(grid_width//2, grid_height//2)]
        snake.append((grid_width//2 - 1, grid_height//2))
        snake.append((grid_width//2 - 2, grid_height//2))
        direction = (1, 0)
        add_count = 0
        spawn_apple()

    # Инициализируем игру
    spawn_apple()
    
    # Главный цикл
    while running:
        for event in pg.event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                if screensaver_active:
                    if event.key == K_p:
                        show_path = not show_path
                    elif event.key == K_a:
                        auto_mode = not auto_mode
                    elif event.key == K_s:
                        acceleration_mode = not acceleration_mode
                    elif not auto_mode:  # Manual control when auto mode is off
                        if event.key == K_UP and direction != (0, 1):
                            direction = (0, -1)
                        elif event.key == K_DOWN and direction != (0, -1):
                            direction = (0, 1)
                        elif event.key == K_LEFT and direction != (1, 0):
                            direction = (-1, 0)
                        elif event.key == K_RIGHT and direction != (-1, 0):
                            direction = (1, 0)
            if event.type == MOUSEBUTTONDOWN:
                if screensaver_active:
                    if event.button == 4:
                        move_interval = max(1, move_interval - 10)
                    elif event.button == 5:
                        move_interval = min(200, move_interval + 10)
        
        # Проверка активности пользователя
        check_activity()
        
        # Если нужно сгенерировать цикл, делаем это
        if generating_cycle and hamilton is None:
            hamilton = HamiltonianCycle(grid_width//2, grid_height//2)
            # Подготавливаем игру сразу после генерации цикла
            if hamilton and hamilton.cycle:
                hamilton_path = [(node.x, node.y) for node in hamilton.cycle]
                path_map = {pos: i for i, pos in enumerate(hamilton_path)}
            
        # Если скринсейвер активен, обновляем игру
        if screensaver_active:
            update_snake()
            
        # Отрисовка
        draw()
        pg.display.flip()
        fpsClock.tick(fps)
    
    pg.quit()
    sys.exit()

if __name__ == "__main__":
    # Запускаем иконку в трее в отдельном потоке
    tray_thread = threading.Thread(target=create_tray_icon, daemon=True)
    tray_thread.start()
    
    # Запускаем основную программу
    main()