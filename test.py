import streamlit as st
import pandas as pd
import folium
import math
import json
from shapely.geometry import Polygon
from streamlit_folium import st_folium
from pyproj import Transformer

st.set_page_config(layout="wide")

# =============================
# LOGIN SYSTEM
# =============================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("🔐 Sistem Survey Lot PUO")

    user_id = st.text_input("Masukkan ID")
    password = st.text_input("Masukkan Kata Laluan", type="password")

    if st.button("Log Masuk"):

        senarai_id = ["wan","muhammad","haziq"]

        if user_id in senarai_id and password == "wanziq67":
            st.session_state.logged_in = True
            st.rerun()

        else:
            st.error("ID atau kata laluan salah")

    st.stop()


# =============================
# HEADER
# =============================

st.title("SISTEM SURVEY LOT")
st.caption("Politeknik Ungku Omar | Jabatan Kejuruteraan Awam")

# =============================
# SIDEBAR CONTROL
# =============================

st.sidebar.header("Kawalan Paparan")

marker_size = st.sidebar.slider("Saiz Marker Stesen",5,25,12)
bearing_size = st.sidebar.slider("Saiz Bearing/Jarak",8,20,12)
zoom_level = st.sidebar.slider("Tahap Zoom",10,22,19)
poly_color = st.sidebar.color_picker("Warna Poligon","#ffff00")

epsg = st.sidebar.text_input("Kod EPSG","4390")

if st.sidebar.button("Log Keluar"):
    st.session_state.logged_in=False
    st.rerun()


# =============================
# FILE UPLOAD
# =============================

uploaded = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)",type="csv")

if uploaded is None:
    st.stop()

df = pd.read_csv(uploaded)

df.columns = df.columns.str.strip().str.upper()

# =============================
# EPSG CONVERSION
# =============================

transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)

lon, lat = transformer.transform(df["E"].values, df["N"].values)

df["lon"] = lon
df["lat"] = lat


# =============================
# MAP CENTER
# =============================

center_lat = df["lat"].mean()
center_lon = df["lon"].mean()

m = folium.Map(
    location=[center_lat,center_lon],
    zoom_start=zoom_level,
    control_scale=True
)

# =============================
# BASEMAP
# =============================

folium.TileLayer(
    "OpenStreetMap",
    name="openstreetmap"
).add_to(m)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    name="Google Hybrid (Satelit)",
    attr="Google"
).add_to(m)

folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    name="Peta Jalan (OSM)",
    attr="OpenStreetMap"
).add_to(m)


# =============================
# BEARING FUNCTION
# =============================

def bearing(lat1,lon1,lat2,lon2):

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    diff = math.radians(lon2-lon1)

    x = math.sin(diff)*math.cos(lat2)
    y = math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(diff)

    initial = math.degrees(math.atan2(x,y))

    return (initial+360)%360


# =============================
# DISTANCE FUNCTION
# =============================

def distance(p1,p2):

    return math.sqrt(
        (p1[0]-p2[0])**2 +
        (p1[1]-p2[1])**2
    )*111000


# =============================
# POINT + STN
# =============================

coords=[]

for i,row in df.iterrows():

    point=[row["lat"],row["lon"]]

    coords.append(point)

    folium.CircleMarker(
        location=point,
        radius=marker_size/2,
        color="red",
        fill=True
    ).add_to(m)

    folium.Marker(
        point,
        icon=folium.DivIcon(
            html=f'<div style="color:white;font-weight:bold">{row["STN"]}</div>'
        )
    ).add_to(m)


# =============================
# POLYGON
# =============================

folium.Polygon(
    coords,
    color=poly_color,
    fill=True,
    fill_opacity=0.4
).add_to(m)


# =============================
# BEARING + DISTANCE
# =============================

for i in range(len(coords)):

    p1 = coords[i]
    p2 = coords[(i+1)%len(coords)]

    mid = [
        (p1[0]+p2[0])/2,
        (p1[1]+p2[1])/2
    ]

    brg = bearing(p1[0],p1[1],p2[0],p2[1])
    dist = distance(p1,p2)

    label=f"{brg:.2f}°<br>{dist:.2f} m"

    folium.Marker(
        mid,
        icon=folium.DivIcon(
            html=f'<div style="color:yellow;font-size:{bearing_size}px">{label}</div>'
        )
    ).add_to(m)


# =============================
# AREA CALCULATION
# =============================

poly = Polygon([(p[1],p[0]) for p in coords])

area_m2 = poly.area * 12300000000
area_hect = area_m2/10000

st.metric("Area (Hektar)",round(area_hect,4))


# =============================
# EXPORT GEOJSON
# =============================

st.sidebar.subheader("Eksport Data")

geojson = {
"type":"FeatureCollection",
"features":[
{
"type":"Feature",
"geometry":{
"type":"Polygon",
"coordinates":[[[p[1],p[0]] for p in coords]]
}
}
]
}

geojson_str=json.dumps(geojson)

st.sidebar.download_button(
"🚀 Export ke QGIS (.geojson)",
geojson_str,
file_name="survey_lot.geojson"
)


# =============================
# DISPLAY MAP
# =============================

folium.LayerControl().add_to(m)

st_folium(m,width=900,height=650)
# =============================
# EXPORT QGIS DATA
# =============================

st.sidebar.subheader("Eksport Data QGIS")

features = []

# POINT FEATURES (STN)
for i,row in df.iterrows():

    features.append({
        "type":"Feature",
        "geometry":{
            "type":"Point",
            "coordinates":[row["lon"],row["lat"]]
        },
        "properties":{
            "STN":row["STN"]
        }
    })


# LINE DATA (Bearing + Distance)
perimeter = 0

for i in range(len(coords)):

    p1 = coords[i]
    p2 = coords[(i+1)%len(coords)]

    brg = bearing(p1[0],p1[1],p2[0],p2[1])
    dist = distance(p1,p2)

    perimeter += dist

    features.append({
        "type":"Feature",
        "geometry":{
            "type":"LineString",
            "coordinates":[
                [p1[1],p1[0]],
                [p2[1],p2[0]]
            ]
        },
        "properties":{
            "line":f"{i+1}-{(i+2) if i+1<len(coords) else 1}",
            "bearing":round(brg,2),
            "distance_m":round(dist,3)
        }
    })


# POLYGON FEATURE
features.append({

"type":"Feature",

"geometry":{
"type":"Polygon",
"coordinates":[[[p[1],p[0]] for p in coords]]
},

"properties":{
"Area_m2":round(area_m2,3),
"Area_hectare":round(area_hect,4),
"Perimeter_m":round(perimeter,3)
}

})


geojson = {
"type":"FeatureCollection",
"features":features
}

geojson_str=json.dumps(geojson)

st.sidebar.download_button(
"🚀 Export QGIS Lengkap (.geojson)",
geojson_str,
file_name="survey_lot_full.geojson"
)
