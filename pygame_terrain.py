import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import pandas as pd
from PIL import Image
import numpy as np

# Screen settings
WIDTH, HEIGHT = 1600, 900
POINT_SIZE = 4

# Viewport settings (in data units)
VIEW_WIDTH, VIEW_HEIGHT = WIDTH / 9, HEIGHT / 9

# Camera settings
camera_x, camera_y, camera_z = 2300, -1850, 150
camera_speed = 5.0

# Key state tracking
keys = {K_LEFT: False, K_RIGHT: False, K_UP: False, K_DOWN: False}

def init():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glPointSize(POINT_SIZE)
    glClearColor(0.05, 0.06, 0.08, 1.0)

def setup_projection():
    glViewport(0, 0, WIDTH, HEIGHT)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(50, WIDTH / HEIGHT, 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)

def image_to_df(image_path):
    image = Image.open(image_path).convert('RGB')
    width, height = image.size
    data = [(x, y, *image.getpixel((x, y))) for y in range(height) for x in range(width)]
    return pd.DataFrame(data, columns=['x', 'y', 'r', 'g', 'b'])

def load_point_cloud(heightmap_df, brightness_df):
    points = heightmap_df[['x', 'y', 'r']].values
    points[:, 1] = -points[:, 1]  # Invert Y-axis
    colors = brightness_df[['r', 'g', 'b']].values / 255.0
    return points, colors

def filter_and_normalize_points(points, colors, camera_x, camera_y, view_width, view_height):
    half_width = view_width / 2
    half_height = view_height / 2

    x_min = camera_x - half_width
    x_max = camera_x + half_width
    y_min = camera_y - half_height
    y_max = camera_y + half_height

    mask = (
        (points[:, 0] >= x_min) & (points[:, 0] < x_max) &
        (points[:, 1] >= y_min) & (points[:, 1] < y_max)
    )
    visible_points = points[mask]
    visible_colors = colors[mask]

    if visible_points.size > 0:
        min_z = visible_points[:, 2].min()
        max_z = visible_points[:, 2].max()
        visible_points[:, 2] = (visible_points[:, 2] - min_z) / (max_z - min_z + 1e-5) * 15.0

    return visible_points, visible_colors

def draw_points(points, colors):
    glBegin(GL_POINTS)
    for i, point in enumerate(points):
        color = colors[i]
        color = (color[0],color[1],color[2],0.5+point[2]/30)
        glColor4f(*color)
        glVertex3f(*point)
    glEnd()

def handle_key_events():
    global camera_x, camera_y
    if keys[K_LEFT]:
        camera_x -= camera_speed
    if keys[K_RIGHT]:
        camera_x += camera_speed
    if keys[K_UP]:
        camera_y += camera_speed
    if keys[K_DOWN]:
        camera_y -= camera_speed

def handle_mouse_scroll(mouse_x, mouse_y):
    """Scroll the camera based on the mouse's position relative to the screen center."""
    global camera_x, camera_y

    # Calculate the offset from the center of the screen
    offset_x = (mouse_x - WIDTH / 2) / WIDTH
    offset_y = (mouse_y - HEIGHT / 2) / HEIGHT

    # Adjust camera position based on the offset (larger offset = faster movement)
    camera_x += offset_x * camera_speed * 5
    camera_y -= offset_y * camera_speed * 5

def draw_directional_triangle(position, direction, scale=1.0,mouse_down=False):
    """Draws a triangle pointing in the specified direction."""
    base_size = 5 * scale  # Base width of the triangle
    height = 10 * scale     # Height of the triangle

    # Calculate the normalized direction vector
    direction_length = np.sqrt(direction[0] ** 2 + direction[1] ** 2)
    if direction_length > 0:
        direction = (direction[0] / direction_length, direction[1] / direction_length, 0)

    # Calculate triangle vertices
    tip = (
        position[0] + direction[0] * height,
        position[1] + direction[1] * height,
        position[2]
    )
    left_base = (
        position[0] - direction[1] * base_size,
        position[1] + direction[0] * base_size,
        position[2]
    )
    right_base = (
        position[0] + direction[1] * base_size,
        position[1] - direction[0] * base_size,
        position[2]
    )

    # Draw the triangle
    glBegin(GL_TRIANGLES)
    glColor4f(0.8, 0.9, 0.9,0.4+0.4*int(mouse_down))  
    glVertex3f(*tip)
    glVertex3f(*left_base)
    glVertex3f(*right_base)
    glEnd()

def main(heightmap_df, brightness_df):
    points, colors = load_point_cloud(heightmap_df, brightness_df)

    global camera_x, camera_y, camera_z
    rotation_x, rotation_y = 0, 0
    mouse_down = False
    mouse_x, mouse_y = WIDTH // 2, HEIGHT // 2  # Initialize mouse position at the center

    init()
    setup_projection()
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                if event.key in keys:
                    keys[event.key] = True
            elif event.type == KEYUP:
                if event.key in keys:
                    keys[event.key] = False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_down = True
                    mouse_x, mouse_y = pygame.mouse.get_pos()  # Get the initial mouse position
                elif event.button == 4:  # Scroll up
                    camera_z -= 5
                elif event.button == 5:  # Scroll down
                    camera_z += 5
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_down = False

        mouse_x, mouse_y = pygame.mouse.get_pos()

        if mouse_down:
            # Continuously update camera position based on the current mouse position
            
            handle_mouse_scroll(mouse_x, mouse_y)
            
        handle_key_events()

        visible_points, visible_colors = filter_and_normalize_points(
            points, colors, camera_x, camera_y, VIEW_WIDTH, VIEW_HEIGHT
        )

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        glTranslatef(-camera_x, -camera_y, -camera_z)
        glRotatef(rotation_x, 1, 0, 0)
        glRotatef(rotation_y, 0, 1, 0)

        draw_points(visible_points, visible_colors)


        direction = ((mouse_x - WIDTH / 2), -(mouse_y - HEIGHT / 2), 0)  # Direction from center
        mag = np.sqrt(direction[0] ** 2 + direction[1] ** 2)
        draw_directional_triangle(
            position=(camera_x+direction[0]/20, camera_y+direction[1]/20, camera_z-50),  # Triangle starts at the camera's position
            direction=direction,
            scale= (mag**0.75)*0.005 + 0.1,
            mouse_down=mouse_down  # Adjust the scale if needed
        )


        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

# Example usage
heightmap_df = image_to_df('./src/images/nyTerrain.png')
brightness_df = image_to_df('./src/images/ndvi_nyState.png')

main(heightmap_df, brightness_df)
