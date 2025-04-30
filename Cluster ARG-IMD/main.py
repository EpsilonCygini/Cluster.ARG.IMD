import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point

# Load data with error handling
try:
    districts = gpd.read_file('up_districts.geojson')
    data = pd.read_csv('data.csv')
except FileNotFoundError as e:
    print(f"Error: {e}")
    exit(1)

# Validate CSV columns
required_cols = ['Lat1', 'Long1', 'Lat2', 'Long2']
if not all(col in data.columns for col in required_cols):
    print(f"Error: CSV must contain columns: {required_cols}")
    exit(1)

# Ensure coordinate system
districts = districts.to_crs(epsg=4326)

# Decide district name column
district_name_col = next((col for col in ['district', 'DISTRICT'] if col in districts.columns), None)
if not district_name_col:
    print("Error: No 'district' or 'DISTRICT' column found in GeoJSON.")
    exit(1)

# Standardize district names
districts[district_name_col] = districts[district_name_col].str.title()

# Calculate map center
bounds = districts.total_bounds
map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

# Create map
m = folium.Map(location=map_center, zoom_start=6)

# Feature groups
districts_fg = folium.FeatureGroup(name='Districts + Markers', show=True, control=False)
imd_fg = folium.FeatureGroup(name='IMD Sensors', show=False, control=False)
rahat_fg = folium.FeatureGroup(name='Rahat Sensors', show=False, control=False)

# Add district polygons
folium.GeoJson(
    districts,
    style_function=lambda x: {'fillColor': 'transparent', 'color': 'blue', 'weight': 2},
    tooltip=folium.GeoJsonTooltip(fields=[district_name_col], aliases=['District:'])
).add_to(districts_fg)

# Helper to get district
def get_district_name(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return "Invalid Coordinates"
    point = Point(lon, lat)
    for _, row in districts.iterrows():
        if row['geometry'].contains(point):
            return row[district_name_col].title()
    return "District out of UP"

# Add IMD markers
for _, row in data.iterrows():
    if pd.notna(row['Lat1']) and pd.notna(row['Long1']):
        district = get_district_name(row['Lat1'], row['Long1'])
        if district not in ["District out of UP", "Invalid Coordinates"]:
            marker = folium.CircleMarker(
                location=[row['Lat1'], row['Long1']],
                radius=5,
                popup=f"District: {district}<br>Type: IMD",
                color='green',
                fill=True,
                fill_color='green',
                fill_opacity=0.7
            )
            marker.add_to(imd_fg)
            marker.add_to(districts_fg)

# Add Rahat markers
for _, row in data.iterrows():
    if pd.notna(row['Lat2']) and pd.notna(row['Long2']):
        district = get_district_name(row['Lat2'], row['Long2'])
        if district not in ["District out of UP", "Invalid Coordinates"]:
            marker = folium.CircleMarker(
                location=[row['Lat2'], row['Long2']],
                radius=5,
                popup=f"District: {district}<br>Type: Rahat",
                color='orange',
                fill=True,
                fill_color='orange',
                fill_opacity=0.7
            )
            marker.add_to(rahat_fg)
            marker.add_to(districts_fg)

# Add feature groups to map
districts_fg.add_to(m)
imd_fg.add_to(m)
rahat_fg.add_to(m)

# Inject custom JavaScript & CSS for independent toggle buttons
toggle_script = """
<script>
function toggleLayer(layerName) {
    var layer = layer_dict[layerName];
    if (map.hasLayer(layer)) {
        map.removeLayer(layer);
    } else {
        map.addLayer(layer);
    }
}

var layer_dict = {};
</script>
"""

custom_css = """
<style>
.control-panel {
    position: absolute;
    top: 10px;
    left: 10px;
    z-index: 9999;
    background-color: white;
    padding: 10px;
    border-radius: 5px;
}
.control-panel button {
    display: block;
    margin-bottom: 5px;
    width: 160px;
}
</style>
"""

control_html = """
<div class="control-panel">
    <button onclick="toggleLayer('Districts + Markers')">Toggle Districts + Markers</button>
    <button onclick="toggleLayer('IMD Sensors')">Toggle IMD Sensors</button>
    <button onclick="toggleLayer('Rahat Sensors')">Toggle Rahat Sensors</button>
</div>
"""

# Add HTML/CSS/JS to the map
m.get_root().html.add_child(folium.Element(custom_css + control_html + toggle_script))

# Link Python objects to JS layer names
m.get_root().script.add_child(folium.Element(f"""
<script>
layer_dict['Districts + Markers'] = {districts_fg.get_name()};
layer_dict['IMD Sensors'] = {imd_fg.get_name()};
layer_dict['Rahat Sensors'] = {rahat_fg.get_name()};
</script>
"""))

# Save the final map
m.save("custom_control_map.html")
print("✅ Custom toggle map saved as 'custom_control_map.html'")
