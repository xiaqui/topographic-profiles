# topodisp.py - 複数CSVファイルを重ね表示（1:1スケール＋移動平均）
import pygame
import csv
import glob


# 複数CSVから標高データ読み込み
def load_multiple_csv():
    files = glob.glob("cross_section_*km_elevation.csv")
    if not files:
        print("No CSV files found matching pattern: cross_section_*km_elevation.csv")
        return []

    datasets = []
    for file in sorted(files):
        data = []
        length_km = 0  # Will be updated from CSV data
        distance = file.split("_")[2].replace(
            "km", ""
        )  # Extract distance from filename

        with open(file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                data.append(float(row[4]))  # Elevation column
                length_km = max(length_km, float(row[1]))  # Update distance

        datasets.append(
            {
                "data": data,
                "length_km": length_km,
                "distance": distance,
                "filename": file,
            }
        )
        print(f"Loaded {file}: {len(data)} points, {distance}km distance")

    return datasets


# 移動平均適用
def smooth(data, window=3):
    smoothed = []
    half = window // 2
    for i in range(len(data)):
        left = max(0, i - half)
        right = min(len(data), i + half + 1)
        smoothed.append(sum(data[left:right]) / (right - left))
    return smoothed


# 複数データセットを表示
datasets = load_multiple_csv()
if not datasets:
    exit()

# Display mode selection
fill_mode = True  # True: filled polygons, False: line drawing only
print(f"Display mode: {'Filled' if fill_mode else 'Line'} drawing")
print("Press 'F' to toggle between filled and line mode, 'ESC' to quit")

# Apply smoothing to all datasets
for dataset in datasets:
    dataset["data"] = smooth(dataset["data"])

# Calculate display parameters
max_elev = max(max(d["data"]) for d in datasets)
length_km = datasets[0]["length_km"]  # Assume all same length
margin = 40
WIDTH = 1280
inner_width = WIDTH - 2 * margin
scale = inner_width / length_km
plot_height = int((max_elev / 1000) * scale)
HEIGHT = plot_height + 2 * margin

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))

# Color palette for different lines
colors = [
    (255, 0, 0),  # Red
    (0, 255, 0),  # Green
    (0, 0, 255),  # Blue
    (255, 255, 0),  # Yellow
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Cyan
    (255, 128, 0),  # Orange
    (128, 0, 255),  # Purple
    (0, 128, 255),  # Light Blue
    (255, 128, 128),  # Pink
]


def update_display():
    """Display drawing function"""
    # Clear screen
    screen.fill((240, 240, 255))

    # Draw grid and axes
    grid_color = (200, 200, 200)
    axis_color = (100, 100, 100)
    text_color = (50, 50, 50)

    # Draw vertical grid lines (distance)
    for km in range(0, int(length_km) + 1, 5):  # Every 5km
        x = margin + km * scale
        if 0 <= x <= WIDTH - margin:
            pygame.draw.line(screen, grid_color, (x, margin), (x, HEIGHT - margin), 1)
            # Distance labels
            if km % 10 == 0:  # Label every 10km
                label = "0km" if km == 0 else str(km)
                text = font.render(label, True, text_color)
                screen.blit(text, (x - 15, HEIGHT - margin + 5))

    # Draw horizontal grid lines (elevation in km)
    for elev_m in range(0, int(max_elev) + 1, 500):  # Every 500m
        y = HEIGHT - margin - (elev_m / 1000) * scale
        if margin <= y <= HEIGHT - margin:
            pygame.draw.line(screen, grid_color, (margin, y), (WIDTH - margin, y), 1)
            # Elevation labels in km
            if elev_m % 1000 == 0:  # Label every 1000m = 1km
                elev_km = elev_m // 1000
                label = "0km" if elev_km == 0 else str(elev_km)
                text = font.render(label, True, text_color)
                screen.blit(text, (5, y - 8))

    # Draw axes
    pygame.draw.line(
        screen, axis_color, (margin, margin), (margin, HEIGHT - margin), 2
    )  # Y-axis
    pygame.draw.line(
        screen,
        axis_color,
        (margin, HEIGHT - margin),
        (WIDTH - margin, HEIGHT - margin),
        2,
    )  # X-axis

    # Draw all datasets (sorted by distance, farthest first for proper depth)
    sorted_datasets_for_drawing = sorted(
        datasets, key=lambda d: float(d["distance"]), reverse=True
    )

    for dataset in sorted_datasets_for_drawing:
        data = dataset["data"]
        # Find original color index to maintain consistent coloring
        original_index = datasets.index(dataset)
        color = colors[original_index % len(colors)]

        # Calculate coordinates for the profile line
        points = []
        for j, elev in enumerate(data):
            dist_km = length_km * j / (len(data) - 1)
            x = margin + dist_km * scale
            y = HEIGHT - margin - (elev / 1000) * scale
            points.append((x, y))

        # Create filled polygon by adding bottom edge points
        if len(points) > 1:
            if fill_mode:
                # Add bottom-left and bottom-right points to close the polygon
                filled_points = points[:]
                filled_points.append((points[-1][0], HEIGHT - margin))  # Bottom-right
                filled_points.append((points[0][0], HEIGHT - margin))  # Bottom-left

                # Fill the area with semi-transparent color
                fill_color = (*color, 128)  # Add alpha for transparency
                # Create a surface for transparency
                temp_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.polygon(temp_surface, fill_color, filled_points)
                screen.blit(temp_surface, (0, 0))

            # Draw the outline (always drawn in both modes)
            pygame.draw.aalines(screen, color, False, points, 2)

    # Draw legend (sorted by distance, farthest first, right-aligned)
    # Sort datasets by distance (descending order for farthest first)
    sorted_datasets = sorted(datasets, key=lambda d: float(d["distance"]), reverse=True)

    for i, dataset in enumerate(sorted_datasets):
        # Find original color index
        original_index = datasets.index(dataset)
        color = colors[original_index % len(colors)]

        y_pos = 10 + i * 20
        # Draw colored line first (behind text)
        distance_str = dataset["distance"]  # Keep original string including minus sign
        text = font.render(f"{distance_str}km", True, (0, 0, 0))
        # Right-align text so 'km' aligns in a column
        text_x = WIDTH - text.get_width() - 5
        pygame.draw.line(
            screen,
            color,
            (text_x, y_pos + 8),
            (text_x + text.get_width(), y_pos + 8),
            3,
        )
        # Draw text on top
        screen.blit(text, (text_x, y_pos))

    # Draw checkbox UI in top-left corner
    draw_checkbox()

    pygame.display.flip()


def draw_checkbox():
    """Draw fill mode checkbox in top-left corner"""
    checkbox_x = 10
    checkbox_y = 10
    checkbox_size = 16

    # Draw checkbox square
    checkbox_rect = pygame.Rect(checkbox_x, checkbox_y, checkbox_size, checkbox_size)
    pygame.draw.rect(screen, (255, 255, 255), checkbox_rect)  # White background
    pygame.draw.rect(screen, (0, 0, 0), checkbox_rect, 2)  # Black border

    # Draw checkmark if fill_mode is True
    if fill_mode:
        # Draw checkmark (✓)
        check_points = [
            (checkbox_x + 3, checkbox_y + 8),
            (checkbox_x + 7, checkbox_y + 12),
            (checkbox_x + 13, checkbox_y + 4),
        ]
        pygame.draw.lines(screen, (0, 0, 0), False, check_points, 3)

    # Draw label text
    label_text = font.render("Fill", True, (0, 0, 0))
    screen.blit(label_text, (checkbox_x + checkbox_size + 5, checkbox_y))

    return checkbox_rect  # Return rect for click detection


def is_point_in_checkbox(pos):
    """Check if mouse position is within checkbox area"""
    checkbox_x = 10
    checkbox_y = 10
    checkbox_size = 16
    label_width = 30  # Approximate width of "Fill" text

    # Expand clickable area to include label
    click_rect = pygame.Rect(
        checkbox_x, checkbox_y, checkbox_size + label_width, checkbox_size
    )
    return click_rect.collidepoint(pos)


# Update window caption
def update_caption():
    caption = f"Multiple Cross-sections ({len(datasets)} files) - {'Filled' if fill_mode else 'Line'} Mode"
    pygame.display.set_caption(caption)


update_caption()

# Initialize font for labels
font = pygame.font.SysFont(None, 16)

# Initial display
update_display()

# Event loop with real-time toggle
clock = pygame.time.Clock()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                # Toggle fill mode with F key
                fill_mode = not fill_mode
                print(f"Switched to: {'Filled' if fill_mode else 'Line'} mode")
                update_caption()
                update_display()
            elif event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                mouse_pos = pygame.mouse.get_pos()
                if is_point_in_checkbox(mouse_pos):
                    # Toggle fill mode with mouse click
                    fill_mode = not fill_mode
                    print(
                        f"Clicked: Switched to {'Filled' if fill_mode else 'Line'} mode"
                    )
                    update_caption()
                    update_display()

    clock.tick(30)

pygame.quit()
exit()
