# profile-generator.py
# Topographic utilities for generating and visualizing elevation cross-sections
# Supports arbitrary movement from a base point and cross-section generation perpendicular to movement direction

import pygame
import sys
import csv
import requests
import time
import math

# Location presets (like C #define)
LOCATION_FUJI = (35.3606, 138.7274)
LOCATION_SOUTH_ALPS = (35.6762, 138.2371)
LOCATION_HIMALAYAS = (27.9881, 86.9250)  # Mt. Everest
LOCATION_ALPS = (45.8326, 6.8652)  # Mont Blanc

# Sample elevation data (dummy: use DEM data in practice)
elevation_data = []


def load_elevation_csv(filename):
    """
    Load elevation data from CSV file
    Expected format: one elevation per line (e.g., 100\n120\n130\n...)
    or comma-separated values (e.g., 100,120,130,...)
    """
    data = []
    with open(filename, encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            for val in row:
                try:
                    data.append(float(val))
                except ValueError:
                    pass
    return data


# Pygame elevation profile display test function
def show_elevation_profile(data, length_km=100.0):
    # Correct negative elevations to 0 (sea level)
    # Interpolate missing values (None) linearly
    def interpolate_missing(data):
        new_data = data[:]
        n = len(data)
        for i, v in enumerate(new_data):
            if v is None:
                # Find valid values before and after
                left = i - 1
                while left >= 0 and new_data[left] is None:
                    left -= 1
                right = i + 1
                while right < n and new_data[right] is None:
                    right += 1
                if left >= 0 and right < n:
                    # Linear interpolation
                    new_data[i] = new_data[left] + (
                        new_data[right] - new_data[left]
                    ) * (i - left) / (right - left)
                elif left >= 0:
                    new_data[i] = new_data[left]
                elif right < n:
                    new_data[i] = new_data[right]
                else:
                    new_data[i] = 0
        return new_data

    data = interpolate_missing(data)
    data = [max(0, elev) for elev in data]

    # Apply moving average smoothing (specify window width as parameter)
    def smooth_elevation(data, window=5):
        if window <= 1:
            return data[:]
        smoothed = []
        half = window // 2
        for i in range(len(data)):
            left = max(0, i - half)
            right = min(len(data), i + half + 1)
            smoothed.append(sum(data[left:right]) / (right - left))
        return smoothed

    # Apply smoothing with window size 3
    data = smooth_elevation(data, window=3)
    # Display with 1:1 ratio: horizontal axis = distance, vertical axis = elevation
    max_distance = length_km * 1000  # m
    max_elev = max(data)
    margin = 40
    min_elev = 0  # Sea level baseline
    elev_range = max_elev - min_elev + 1

    # Fixed 1280px width, calculate height for 1:1 ratio
    FIXED_WIDTH = 1280
    inner_width = FIXED_WIDTH - 2 * margin
    max_distance_km = max_distance / 1000
    elev_range_km = elev_range / 1000
    scale = inner_width / max_distance_km
    plot_height = int(elev_range_km * scale)
    HEIGHT = plot_height + 2 * margin
    WIDTH = FIXED_WIDTH
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Elevation Profile (1:1 scale)")
    font = pygame.font.SysFont(None, 18)
    screen.fill((240, 240, 255))
    # Axes
    pygame.draw.line(
        screen,
        (0, 0, 0),
        (margin, HEIGHT - margin),
        (WIDTH - margin, HEIGHT - margin),
        2,
    )
    pygame.draw.line(screen, (0, 0, 0), (margin, margin), (margin, HEIGHT - margin), 2)
    # Vertical axis ticks
    n_vticks = 5
    for i in range(n_vticks + 1):
        elev_km = elev_range_km * i / n_vticks
        y = HEIGHT - margin - elev_km * scale
        label_val = min_elev / 1000 + elev_km
        pygame.draw.line(screen, (0, 0, 0), (margin - 6, y), (margin, y), 2)
        label = font.render(f"{label_val:.1f}", True, (0, 0, 0))
        screen.blit(label, (margin - 40, y - 8))

    # Horizontal axis ticks
    n_ticks = 10
    for i in range(n_ticks + 1):
        dist_km = max_distance_km * i / n_ticks
        x = margin + dist_km * scale
        pygame.draw.line(
            screen, (0, 0, 0), (x, HEIGHT - margin), (x, HEIGHT - margin + 6), 2
        )
        label = font.render(f"{dist_km:.1f}", True, (0, 0, 0))
        screen.blit(label, (x - 16, HEIGHT - margin + 8))
    # Elevation profile
    points = []
    for i, elev in enumerate(data):
        dist_km = max_distance_km * i / (len(data) - 1)
        x = margin + dist_km * scale
        y = HEIGHT - margin - ((elev - min_elev) / 1000) * scale
        points.append((x, y))
    if len(points) > 1:
        pygame.draw.aalines(screen, (60, 120, 60), False, points)
    pygame.display.flip()

    # Event loop
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        clock.tick(30)
    pygame.quit()
    sys.exit()


def fetch_elevation_open_elevation(points, sleep_sec=1.0):
    """
    Fetch elevation data from Open-Elevation API for a list of coordinates
    Args:
        points: List of (lat, lon) tuples
        sleep_sec: Sleep duration between API calls to avoid rate limiting
    Returns:
        List of elevation values in meters
    """
    url = "https://api.open-elevation.com/api/v1/lookup"
    locations = [{"latitude": lat, "longitude": lon} for lat, lon in points]
    # API rate limiting: process 100 points at a time
    elevations = []
    for i in range(0, len(locations), 100):
        chunk = locations[i : i + 100]
        resp = requests.post(url, json={"locations": chunk})
        if resp.status_code == 200:
            data = resp.json()
            elevations.extend([r["elevation"] for r in data["results"]])
        else:
            print("API error", resp.status_code, resp.text)
            elevations.extend([None] * len(chunk))
        time.sleep(sleep_sec)  # API rate limiting
    return elevations


def generate_line_points(lat1, lon1, lat2, lon2, n):
    """
    Generate n equally spaced points along a line from point A to point B
    Args:
        lat1, lon1: Starting point coordinates
        lat2, lon2: Ending point coordinates
        n: Number of points to generate
    Returns:
        List of (lat, lon) tuples
    """
    return [
        (lat1 + (lat2 - lat1) * i / (n - 1), lon1 + (lon2 - lon1) * i / (n - 1))
        for i in range(n)
    ]


def generate_cross_section_points(
    center_lat, center_lon, move_bearing_deg, length_km, n
):
    """
    Generate coordinates for a cross-section perpendicular to the movement direction
    Args:
        center_lat, center_lon: Center point of the cross-section
        move_bearing_deg: Direction of movement (degrees from north)
        length_km: Length of the cross-section (km)
        n: Number of points to generate along the cross-section
    Returns:
        List of (lat, lon) tuples representing the cross-section
    """
    R = 6371.0  # Earth radius in km
    half = length_km / 2

    def dest_point(lat, lon, bearing_deg, dist_km):
        lat1 = math.radians(lat)
        lon1 = math.radians(lon)
        bearing = math.radians(bearing_deg)
        d_div_r = dist_km / R
        lat2 = math.asin(
            math.sin(lat1) * math.cos(d_div_r)
            + math.cos(lat1) * math.sin(d_div_r) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(d_div_r) * math.cos(lat1),
            math.cos(d_div_r) - math.sin(lat1) * math.sin(lat2),
        )
        return math.degrees(lat2), math.degrees(lon2)

    # Calculate left and right endpoints as seen from the movement direction
    left_lat, left_lon = dest_point(center_lat, center_lon, move_bearing_deg - 90, half)
    right_lat, right_lon = dest_point(
        center_lat, center_lon, move_bearing_deg + 90, half
    )

    return generate_line_points(left_lat, left_lon, right_lat, right_lon, n)


def dest_point(lat, lon, bearing_deg, dist_km):
    """
    Calculate destination point given distance and bearing from starting point
    """
    R = 6371.0  # Earth radius in km
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    bearing = math.radians(bearing_deg)
    d_div_r = dist_km / R
    lat2 = math.asin(
        math.sin(lat1) * math.cos(d_div_r)
        + math.cos(lat1) * math.sin(d_div_r) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(d_div_r) * math.cos(lat1),
        math.cos(d_div_r) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def example_usage():
    """
    Example usage scenarios for elevation cross-section generation
    """
    # Example 1: Mt. Fuji cross-section facing north
    print("Example 1: Mt. Fuji cross-section facing north")
    base_lat, base_lon = 35.3606, 138.7274  # Mt. Fuji
    cross_section_demo(
        base_lat,
        base_lon,
        move_bearing=0,
        move_distance=0,
        length_km=20,
        description="Mt. Fuji base - North facing",
    )

    # Example 2: 10km north of Mt. Fuji, cross-section facing east
    print("\nExample 2: 10km north of Mt. Fuji, cross-section facing east")
    cross_section_demo(
        base_lat,
        base_lon,
        move_bearing=0,
        move_distance=10,
        length_km=15,
        description="10km North of Mt. Fuji - East facing",
    )

    # Example 3: 5km northeast of Mt. Fuji, cross-section facing southeast
    print("\nExample 3: 5km northeast of Mt. Fuji, cross-section facing southeast")
    cross_section_demo(
        base_lat,
        base_lon,
        move_bearing=45,
        move_distance=5,
        length_km=12,
        description="5km NE of Mt. Fuji - SE facing",
    )


def cross_section_demo(
    base_lat, base_lon, move_bearing, move_distance, length_km, description
):
    """
    Demonstrate cross-section generation with given parameters
    """
    print(f"  Location: {description}")
    print(f"  Base coordinates: ({base_lat:.4f}, {base_lon:.4f})")
    print(f"  Movement: {move_distance}km at {move_bearing}° bearing")
    print(f"  Cross-section: {length_km}km perpendicular to movement direction")

    # Calculate center point
    center_lat, center_lon = dest_point(base_lat, base_lon, move_bearing, move_distance)
    print(f"  Center coordinates: ({center_lat:.4f}, {center_lon:.4f})")

    # Generate cross-section points (sample for demonstration)
    n_points = 21  # Fewer points for demo
    points = generate_cross_section_points(
        center_lat, center_lon, move_bearing, length_km, n_points
    )

    print(f"  Generated {len(points)} points along cross-section")
    print(f"  Left endpoint: ({points[0][0]:.4f}, {points[0][1]:.4f})")
    print(f"  Right endpoint: ({points[-1][0]:.4f}, {points[-1][1]:.4f})")


def save_elevation_csv(data, filename, length_km=None, points=None):
    """
    Save elevation data to CSV file
    Args:
        data: List of elevation values
        filename: Output filename
        length_km: Total distance in km (optional, for distance calculation)
        points: List of (lat, lon) coordinates (optional)
    """
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header
        if points and length_km:
            writer.writerow(
                ["Index", "Distance_km", "Latitude", "Longitude", "Elevation_m"]
            )
        elif length_km:
            writer.writerow(["Index", "Distance_km", "Elevation_m"])
        elif points:
            writer.writerow(["Index", "Latitude", "Longitude", "Elevation_m"])
        else:
            writer.writerow(["Index", "Elevation_m"])

        # Write data
        for i, elev in enumerate(data):
            row = [str(i)]

            if length_km:
                dist_km = length_km * i / (len(data) - 1) if len(data) > 1 else 0
                row.append(f"{dist_km:.3f}")

            if points and i < len(points):
                lat, lon = points[i]
                row.extend([f"{lat:.6f}", f"{lon:.6f}"])

            row.append(f"{elev:.1f}" if elev is not None else "N/A")
            writer.writerow(row)

    print(f"Elevation data saved to: {filename}")


def save_cross_section_summary(
    base_lat,
    base_lon,
    move_bearing_deg,
    move_distance_km,
    length_km,
    center_lat,
    center_lon,
    points,
    filename,
):
    """
    Save cross-section parameters and coordinates to CSV file
    Args:
        base_lat, base_lon: Base coordinates
        move_bearing_deg: Movement direction
        move_distance_km: Movement distance
        length_km: Cross-section length
        center_lat, center_lon: Center coordinates
        points: List of cross-section coordinates
        filename: Output filename
    """
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write metadata
        writer.writerow(["# Cross-Section Parameters"])
        writer.writerow(["Base_Latitude", base_lat])
        writer.writerow(["Base_Longitude", base_lon])
        writer.writerow(["Movement_Bearing_deg", move_bearing_deg])
        writer.writerow(["Movement_Distance_km", move_distance_km])
        writer.writerow(["Cross_Section_Length_km", length_km])
        writer.writerow(["Center_Latitude", center_lat])
        writer.writerow(["Center_Longitude", center_lon])
        writer.writerow([])  # Empty row

        # Write coordinates
        writer.writerow(["# Cross-Section Coordinates"])
        writer.writerow(["Index", "Distance_from_left_km", "Latitude", "Longitude"])

        for i, (lat, lon) in enumerate(points):
            dist_from_left = length_km * i / (len(points) - 1) if len(points) > 1 else 0
            writer.writerow(
                [str(i), f"{dist_from_left:.3f}", f"{lat:.6f}", f"{lon:.6f}"]
            )

    print(f"Cross-section summary saved to: {filename}")


def save_elevation_profile_image(data, length_km, filename):
    """
    Save elevation profile as image file (PNG)
    Args:
        data: List of elevation values
        length_km: Total distance in km
        filename: Output filename (should end with .png)
    """
    # This is a simplified version - would need additional libraries like matplotlib for better output
    # For now, we'll save the data that could be used to recreate the visualization
    import json

    profile_data = {
        "length_km": length_km,
        "elevations": data,
        "points_count": len(data),
        "max_elevation": max(data) if data else 0,
        "min_elevation": min(data) if data else 0,
    }

    # Save as JSON for now (could be extended to actual image with matplotlib)
    json_filename = filename.replace(".png", ".json")
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2)

    print(f"Elevation profile data saved to: {json_filename}")
    print("Note: For actual PNG output, consider using matplotlib")


def save_display_coordinates_csv(data, length_km, filename):
    """
    Save pygame display coordinates to CSV file
    Args:
        data: List of elevation values
        length_km: Total distance in km
        filename: Output filename
    """
    # Recalculate display coordinates (same logic as in show_elevation_profile)
    max_distance = length_km * 1000  # m
    max_elev = max(data) if data else 100
    margin = 40
    min_elev = 0  # Sea level baseline
    elev_range = max_elev - min_elev + 1

    # Fixed 1280px width, calculate height for 1:1 ratio
    FIXED_WIDTH = 1280
    inner_width = FIXED_WIDTH - 2 * margin
    max_distance_km = max_distance / 1000
    elev_range_km = elev_range / 1000
    scale = inner_width / max_distance_km
    plot_height = int(elev_range_km * scale)
    HEIGHT = plot_height + 2 * margin

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write display parameters
        writer.writerow(["# Display Parameters"])
        writer.writerow(["Screen_Width", FIXED_WIDTH])
        writer.writerow(["Screen_Height", HEIGHT])
        writer.writerow(["Margin", margin])
        writer.writerow(["Scale_pixels_per_km", f"{scale:.3f}"])
        writer.writerow(["Max_Elevation_m", max_elev])
        writer.writerow(["Min_Elevation_m", min_elev])
        writer.writerow([])  # Empty row

        # Write coordinate headers
        writer.writerow(["# Display Coordinates"])
        writer.writerow(["Index", "Distance_km", "Elevation_m", "Screen_X", "Screen_Y"])

        # Calculate and write display coordinates
        for i, elev in enumerate(data):
            dist_km = max_distance_km * i / (len(data) - 1) if len(data) > 1 else 0
            screen_x = margin + dist_km * scale
            screen_y = HEIGHT - margin - ((elev - min_elev) / 1000) * scale

            writer.writerow(
                [
                    str(i),
                    f"{dist_km:.3f}",
                    f"{elev:.1f}" if elev is not None else "N/A",
                    f"{screen_x:.1f}",
                    f"{screen_y:.1f}",
                ]
            )

    print(f"Display coordinates saved to: {filename}")


if __name__ == "__main__":
    print("topograph.py: Elevation cross-section generation test")

    # Uncomment the line below to see usage examples
    # example_usage()

    try:
        # Clean up existing cross-section files before generating new ones
        import glob
        import os

        patterns = [
            "cross_section_*km_elevation.csv",
            "cross_section_*km_coordinates.csv",
            "cross_section_*km_profile.json",
            "cross_section_*km_display_coords.csv",
        ]
        for pattern in patterns:
            existing_files = glob.glob(pattern)
            for file in existing_files:
                os.remove(file)
                print(f"Removed existing file: {file}")

        # Base point and parameters - MODIFY THESE VALUES AS NEEDED
        # base_lat, base_lon = 35.3606, 138.7274  # Mt. Fuji coordinates
        # base_lat, base_lon = 35.6762, 138.2371  # South Alps (Kitadake area)
        base_lat, base_lon = LOCATION_FUJI
        move_bearing_deg = (
            -90  # Movement direction (degrees from north): 0=N, 90=E, 180=S, 270=W
        )
        length_km = 20  # Cross-section length (km) perpendicular to movement direction
        n_points = int(length_km * 1000 / 200) + 1  # ~200m spacing between points

        # Multiple distances to generate (negative values move in opposite direction)
        distances = [-20, -10, 0]  # km
        save_to_files = True

        for move_distance_km in distances:
            print(f"\n=== Processing distance: {move_distance_km}km ===")

            # Calculate center point after movement
            center_lat, center_lon = dest_point(
                base_lat, base_lon, move_bearing_deg, move_distance_km
            )

            # Generate cross-section coordinate list
            points = generate_cross_section_points(
                center_lat, center_lon, move_bearing_deg, length_km, n_points
            )

            # File prefix with distance
            output_prefix = f"cross_section_{move_distance_km}km"

            # Save cross-section summary if enabled
            if save_to_files:
                save_cross_section_summary(
                    base_lat,
                    base_lon,
                    move_bearing_deg,
                    move_distance_km,
                    length_km,
                    center_lat,
                    center_lon,
                    points,
                    f"{output_prefix}_coordinates.csv",
                )

            # Fetch elevation data
            print(f"Fetching elevation data for {len(points)} points...")
            elevation_data = fetch_elevation_open_elevation(points)
            if not elevation_data or any(e is None for e in elevation_data):
                raise Exception("Failed to fetch elevation data")

            # Save elevation data if enabled
            if save_to_files:
                save_elevation_csv(
                    elevation_data,
                    f"{output_prefix}_elevation.csv",
                    length_km=length_km,
                    points=points,
                )
                save_elevation_profile_image(
                    elevation_data, length_km, f"{output_prefix}_profile.png"
                )
                save_display_coordinates_csv(
                    elevation_data, length_km, f"{output_prefix}_display_coords.csv"
                )

        print("\n=== All distances processed! ===")
        print("Files generated for distances:", distances)
    except requests.exceptions.RequestException as e:
        print(f"Network error while fetching elevation data: {e}")
        print("Using dummy data for display")
        dummy_data = [
            100,
            120,
            130,
            140,
            160,
            180,
            170,
            150,
            140,
            130,
            120,
            110,
            100,
            90,
            80,
            85,
            90,
            100,
            120,
            140,
        ]

        # Save dummy data if file output is enabled
        output_prefix = "cross_section_dummy"
        save_elevation_csv(dummy_data, f"{output_prefix}_elevation.csv", length_km=20)
        save_elevation_profile_image(dummy_data, 20, f"{output_prefix}_profile.png")
        save_display_coordinates_csv(
            dummy_data, 20, f"{output_prefix}_display_coords.csv"
        )

        show_elevation_profile(dummy_data, length_km=20)
    except Exception as e:
        print(f"Error occurred: {e}")
        print("Using dummy data for display")
        dummy_data = [
            100,
            120,
            130,
            140,
            160,
            180,
            170,
            150,
            140,
            130,
            120,
            110,
            100,
            90,
            80,
            85,
            90,
            100,
            120,
            140,
        ]

        # Save dummy data if file output is enabled
        output_prefix = "cross_section_dummy"
        save_elevation_csv(dummy_data, f"{output_prefix}_elevation.csv", length_km=20)
        save_elevation_profile_image(dummy_data, 20, f"{output_prefix}_profile.png")
        save_display_coordinates_csv(
            dummy_data, 20, f"{output_prefix}_display_coords.csv"
        )

        show_elevation_profile(dummy_data, length_km=20)
