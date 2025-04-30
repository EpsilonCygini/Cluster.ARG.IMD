import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Load data
districts = gpd.read_file('up_districts.geojson')
data = pd.read_csv('data.csv')

# Ensure correct CRS
districts = districts.to_crs(epsg=4326)

# Determine the correct district name column
district_name_col = 'district' if 'district' in districts.columns else 'DISTRICT'

# Prepare a dictionary to store counts
counts = {district: {'Green': 0, 'Red': 0} for district in districts[district_name_col]}

# Helper function to find district name
def get_district_name(lat, lon):
    point = Point(lon, lat)
    for _, row in districts.iterrows():
        if row['geometry'].contains(point):
            return row[district_name_col]
    return None

# Count green markers (Lat1/Long1)
for _, row in data.iterrows():
    if pd.notna(row['Lat1']) and pd.notna(row['Long1']):
        district = get_district_name(row['Lat1'], row['Long1'])
        if district:
            counts[district]['Green'] += 1

# Count red markers (Lat2/Long2)
for _, row in data.iterrows():
    if pd.notna(row['Lat2']) and pd.notna(row['Long2']):
        district = get_district_name(row['Lat2'], row['Long2'])
        if district:
            counts[district]['Red'] += 1

# Convert to DataFrame for Excel output
output_df = pd.DataFrame([
    {'District': district, 'Green_Markers': values['Green'], 'Red_Markers': values['Red']}
    for district, values in counts.items()
])

# Save to Excel
output_df.to_excel('district_marker_counts.xlsx', index=False)
print("✅ Excel file 'district_marker_counts.xlsx' has been created.")