# python-expt
プロトタイプのための技術実験室です ~ experiment for experience!

## Topographic Cross-Section Generator

Generates and visualizes elevation cross-sections for any location with the ability to:
- Move from a base point by any distance and bearing
- Generate cross-sections perpendicular to the movement direction
- Display elevation profiles with 1:1 scale using Pygame
- Fetch real elevation data from Open-Elevation API

### Features
- **Arbitrary Movement**: Move from any base coordinates by specifying distance and bearing
- **Perpendicular Cross-Sections**: Generate cross-sections that are always perpendicular to movement direction
- **Correct Orientation**: Left/right endpoints correspond to left/right as seen from movement direction
- **Real Elevation Data**: Uses Open-Elevation API with fallback to dummy data
- **Visual Display**: Interactive 1:1 scale elevation profile with proper axes and labels
- **File Output**: Save elevation data, coordinates, and profile data to CSV/JSON files

### Usage
1. Set base coordinates (`base_lat`, `base_lon`)
2. Set movement parameters (`move_bearing_deg`, `move_distance_km`)
3. Set cross-section parameters (`length_km`, point spacing)
4. Configure file output options (`save_to_files`, `output_prefix`)
5. Run the script to generate and display the elevation profile
- example: python profile-generator.py; if ($?) { python profile-viewer.py }

### File Output Options
When `save_to_files = True`, the following files are generated:
- `{prefix}_coordinates.csv`: Cross-section parameters and coordinate points
- `{prefix}_elevation.csv`: Elevation data with distances and coordinates
- `{prefix}_profile.json`: Profile visualization data for external tools
- `{prefix}_display_coords.csv`: Pygame screen coordinates for visualization

Example output files: `cross_section_coordinates.csv`, `cross_section_elevation.csv`, `cross_section_display_coords.csv`

### Example Scenarios
- Mt. Fuji base location with north-facing cross-section
- 10km north of Mt. Fuji with east-facing cross-section
- 5km northeast of Mt. Fuji with southeast-facing cross-section

### Dependencies
- `pygame`: For visualization
- `requests`: For API calls
- `math`: For geographic calculations
