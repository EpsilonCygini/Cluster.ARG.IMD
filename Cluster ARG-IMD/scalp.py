import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point
import json

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

districts[district_name_col] = districts[district_name_col].str.title()

# Calculate map center
bounds = districts.total_bounds
map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

# Create base map
m = folium.Map(location=map_center, zoom_start=6)

# Add district boundaries
folium.GeoJson(
    districts,
    name="UP District Boundaries",
    style_function=lambda x: {'fillColor': 'transparent', 'color': 'blue', 'weight': 2, 'fillOpacity': 0.1},
    tooltip=folium.GeoJsonTooltip(fields=[district_name_col], aliases=['District:'])
).add_to(m)

# Helper to find district name
def get_district_name(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return "Invalid Coordinates"
    point = Point(lon, lat)
    for _, row in districts.iterrows():
        if row['geometry'].contains(point):
            return row[district_name_col].title()
    return "District out of UP"

district_groups = {}
active_districts = set()
layer_name_map = {}

# Add IMD markers
for _, row in data.iterrows():
    if pd.notna(row['Lat1']) and pd.notna(row['Long1']):
        district = get_district_name(row['Lat1'], row['Long1'])
        if district not in ["District out of UP", "Invalid Coordinates"]:
            if district not in district_groups:
                imd_name = f"IMD - {district}"
                rahat_name = f"Rahat - {district}"
                district_groups[district] = {
                    'IMD': folium.FeatureGroup(name=imd_name, show=True),
                    'Rahat': folium.FeatureGroup(name=rahat_name, show=True),
                    'IMD_name': imd_name,
                    'Rahat_name': rahat_name
                }
            folium.CircleMarker(
                location=[row['Lat1'], row['Long1']],
                radius=5,
                popup=f"District: {district}<br>Type: IMD",
                color='green',
                fill=True,
                fill_color='green',
                fill_opacity=0.7
            ).add_to(district_groups[district]['IMD'])
            active_districts.add(district)

# Add Rahat markers
for _, row in data.iterrows():
    if pd.notna(row['Lat2']) and pd.notna(row['Long2']):
        district = get_district_name(row['Lat2'], row['Long2'])
        if district not in ["District out of UP", "Invalid Coordinates"]:
            if district not in district_groups:
                imd_name = f"IMD - {district}"
                rahat_name = f"Rahat - {district}"
                district_groups[district] = {
                    'IMD': folium.FeatureGroup(name=imd_name, show=True),
                    'Rahat': folium.FeatureGroup(name=rahat_name, show=True),
                    'IMD_name': imd_name,
                    'Rahat_name': rahat_name
                }
            folium.CircleMarker(
                location=[row['Lat2'], row['Long2']],
                radius=5,
                popup=f"District: {district}<br>Type: Rahat",
                color='orange',
                fill=True,
                fill_color='orange',
                fill_opacity=0.7
            ).add_to(district_groups[district]['Rahat'])
            active_districts.add(district)

# Add to map & build JS layer name map
for district, groups in district_groups.items():
    groups['IMD'].add_to(m)
    groups['Rahat'].add_to(m)
    layer_name_map[district] = [groups['IMD_name'], groups['Rahat_name']]

# Add layer control
folium.LayerControl(collapsed=False).add_to(m)

# Add legend
legend_html = '''
<div id="map-legend" style="
    position: fixed; 
    bottom: 70px; 
    left: 70px; 
    width: 300px; 
    background-color: white; 
    border:2px solid grey; 
    z-index:9999; 
    font-size:14px; 
    padding: 10px; 
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <b>Legend</b>
        <span style="cursor: pointer; font-weight: bold;" onclick="document.getElementById('map-legend').style.display='none';">×</span>
    </div>
    <div style="margin-top: 10px;">
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 15px; height: 15px; background-color: green; margin-right: 8px; border: 1px solid #333;"></div>
            IMD Sensors
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 15px; height: 15px; background-color: orange; margin-right: 8px; border: 1px solid #333;"></div>
            Rahat Sensors
        </div>
    </div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Dropdown for filtering
district_list = sorted(active_districts)
district_list.insert(0, 'All Districts')
dropdown_html = f'''
<div style="
    position: fixed;
    top: 10px;
    left: 70px;
    z-index:9999;
    background-color: white;
    padding: 10px;
    border: 2px solid grey;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
">
    <label for="districtFilter"><b>Filter by District:</b></label>
    <select id="districtFilter" onchange="filterMarkers()">
        {''.join([f'<option value="{d}">{d}</option>' for d in district_list])}
    </select>
</div>
<script>
function filterMarkers() {{
    var selected = document.getElementById('districtFilter').value;
    var layerNameMap = {json.dumps(layer_name_map)};
    for (var district in layerNameMap) {{
        let names = layerNameMap[district];
        map.eachLayer(function(layer) {{
            if (names.includes(layer.options?.name)) {{
                if (selected === "All Districts" || selected === district) {{
                    map.addLayer(layer);
                }} else {{
                    map.removeLayer(layer);
                }}
            }}
        }});
    }}
}}
</script>
'''
m.get_root().html.add_child(folium.Element(dropdown_html))

# Save
m.save("ttsx.html")
print("✅ Map saved as 'ttsx.html'")
