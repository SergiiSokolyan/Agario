import pygame
from random import randint
from math import hypot
import socket
import threading

pygame.init()
window = pygame.display.set_mode((1000, 1000))
clock = pygame.time.Clock()

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client_socket.connect(('6.tcp.eu.ngrok.io', 13165))
except socket.error as e:
    print(f"Не вдалося підключитися до сервера: {e}")
    pygame.quit()
    exit()

try:
    start_data_str = client_socket.recv(1024).decode()
    parts = start_data_str.split(',')

    player_id = int(parts[0])
    initial_x = float(parts[1])
    initial_y = float(parts[2])
    initial_size = float(parts[3])

    if initial_size <= 0:
        initial_size = 10.0
        print("Початковий розмір гравця був <= 0, встановлено мінімальний розмір 10.")

    my_player = [initial_x, initial_y, initial_size]

except (ValueError, IndexError, socket.error) as e:
    print(f"Помилка парсингу початкових даних гравця або отримання: {e}")
    print("Встановлюємо значення гравця за замовчуванням: [0.0, 0.0, 10.0]")
    player_id = 0
    my_player = [0.0, 0.0, 10.0]

scale = 1.0
other_players = []

class Food:
    def __init__(self, x, y, r, c):
        self.x = x
        self.y = y
        self.radius = r
        self.color = c

eats = [Food(randint(-2000, 2000), randint(-2000, 2000), 10,
             (randint(100, 255), randint(100, 255), randint(100, 255)))
        for _ in range(200)]

def receive_data():
    global other_players
    while True:
        try:
            data_bytes = client_socket.recv(4096)
            if not data_bytes:
                print("З'єднання з сервером розірвано (receive_data).")
                break
            data_str = data_bytes.decode()

            parsed_players = []
            player_entries = data_str.strip('|').split('|')

            for entry in player_entries:
                if not entry:
                    continue

                parts = entry.split(',')
                if len(parts) == 5:
                    pid = int(parts[0])
                    if pid != player_id:  # Не малювати самого себе
                        parsed_players.append([float(parts[1]), float(parts[2]), float(parts[3])])

            other_players = parsed_players

        except (socket.error, ValueError, IndexError) as e:
            print(f"Помилка прийому даних або парсингу в потоці receive_data: {e}")
            break

receive_thread = threading.Thread(target=receive_data)
receive_thread.daemon = True
receive_thread.start()

running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]: my_player[1] -= 7
    if keys[pygame.K_s]: my_player[1] += 7
    if keys[pygame.K_a]: my_player[0] -= 7
    if keys[pygame.K_d]: my_player[0] += 7

    try:
        send_data = f"{player_id},{my_player[0]},{my_player[1]},{my_player[2]},Player".encode()
        client_socket.send(send_data)
    except socket.error as e:
        print(f"Помилка відправки своїх даних на сервер: {e}")
        running = False

    window.fill((0, 0, 0))

    if my_player[2] <= 0:
        my_player[2] = 1.0
        print("Розмір гравця став <= 0, встановлено мінімальний розмір 1.0.")

    scale = max(0.3, min(50 / my_player[2], 1.5))

    for eat in eats[:]:
        sx = int((eat.x - my_player[0]) * scale + 500)
        sy = int((eat.y - my_player[1]) * scale + 500)
        sr = int(eat.radius * scale)

        dist = hypot(my_player[0] - eat.x, my_player[1] - eat.y)

        if dist < my_player[2]:
            eats.remove(eat)
            my_player[2] += 1
        else:
            if -sr < sx < 1000 + sr and -sr < sy < 1000 + sr:
                pygame.draw.circle(window, eat.color, (sx, sy), sr)

    for player in other_players:
        px = int((player[0] - my_player[0]) * scale + 500)
        py = int((player[1] - my_player[1]) * scale + 500)
        pr = int(player[2] * scale)

        if -pr < px < 1000 + pr and -pr < py < 1000 + pr:
            pygame.draw.circle(window, (255, 0, 0), (px, py), pr)

    pygame.draw.circle(window, (0, 255, 0), (500, 500), int(my_player[2]))

    pygame.display.update()
    clock.tick(60)

pygame.quit()
client_socket.close()
