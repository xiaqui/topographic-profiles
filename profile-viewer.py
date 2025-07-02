# profile-viewer.py - 複数CSVファイルを重ね表示（1:1スケール＋移動平均）
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
pygame.display.set_caption(f"Multiple Cross-sections ({len(datasets)} files)")

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

# Clear screen
screen.fill((240, 240, 255))

# Initialize font for labels
font = pygame.font.SysFont(None, 16)

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
    screen, axis_color, (margin, HEIGHT - margin), (WIDTH - margin, HEIGHT - margin), 2
)  # X-axis

# Draw all datasets
for i, dataset in enumerate(datasets):
    data = dataset["data"]
    color = colors[i % len(colors)]

    # Calculate coordinates
    points = []
    for j, elev in enumerate(data):
        dist_km = length_km * j / (len(data) - 1)
        x = margin + dist_km * scale
        y = HEIGHT - margin - (elev / 1000) * scale
        points.append((x, y))

    # Draw line
    if len(points) > 1:
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
    distance_num = dataset["distance"].lstrip("-")  # Remove leading hyphen
    text = font.render(f"{distance_num}km", True, (0, 0, 0))
    # Right-align text so 'km' aligns in a column
    text_x = WIDTH - text.get_width() - 5
    pygame.draw.line(
        screen, color, (text_x, y_pos + 8), (text_x + text.get_width(), y_pos + 8), 3
    )
    # Draw text on top
    screen.blit(text, (text_x, y_pos))

pygame.display.flip()

# Event loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
