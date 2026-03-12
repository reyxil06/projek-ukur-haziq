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
    tiles=None,
    control_scale=True
)


# =============================
# BASEMAP
# =============================

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    attr="Google",
    name="Google Hybrid (Satelit)",
    overlay=False,
    control=True
).add_to(m)

folium.TileLayer(
    tiles="OpenStreetMap",
    name="openstreetmap",
    overlay=False,
    control=True
).add_to(m)

folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="© OpenStreetMap contributors",
    name="Peta Jalan (OSM)",
    overlay=False,
    control=True
).add_to(m)


# =============================
# SURVEY LAYER
# =============================

survey_layer = folium.FeatureGroup(name="Data Survey", show=True)


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
    )*111139


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
    ).add_to(survey_layer)

    folium.Marker(
        point,
        icon=folium.DivIcon(
            html=f'<div style="color:white;font-weight:bold">{row["STN"]}</div>'
        )
    ).add_to(survey_layer)


# =============================
# CLOSE POLYGON
# =============================

coords_closed = coords + [coords[0]]


# =============================
# POLYGON
# =============================

folium.Polygon(
    coords_closed,
    color=poly_color,
    fill=True,
    fill_opacity=0.4
).add_to(survey_layer)


# =============================
# BEARING + DISTANCE
# =============================

perimeter = 0

for i in range(len(coords)):

    p1 = coords[i]
    p2 = coords[(i+1)%len(coords)]

    mid = [
        (p1[0]+p2[0])/2,
        (p1[1]+p2[1])/2
    ]

    brg = bearing(p1[0],p1[1],p2[0],p2[1])
    dist = distance(p1,p2)

    perimeter += dist

    label=f"{brg:.2f}°<br>{dist:.2f} m"

    folium.Marker(
        mid,
        icon=folium.DivIcon(
            html=f'<div style="color:yellow;font-size:{bearing_size}px">{label}</div>'
        )
    ).add_to(survey_layer)


survey_layer.add_to(m)


# =============================
# AREA CALCULATION
# =============================

poly = Polygon([(p[1],p[0]) for p in coords_closed])

area_m2 = poly.area * 12364000000
area_hect = area_m2 / 10000

col1,col2 = st.columns(2)

col1.metric("Area (m²)",round(area_m2,2))
col2.metric("Area (Hektar)",round(area_hect,4))


# =============================
# EXPORT QGIS DATA
# =============================

st.sidebar.subheader("Eksport Data QGIS")

features=[]

# POINT

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


# LINE

for i in range(len(coords)):

    p1 = coords[i]
    p2 = coords[(i+1)%len(coords)]

    brg = bearing(p1[0],p1[1],p2[0],p2[1])
    dist = distance(p1,p2)

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


# POLYGON

features.append({

"type":"Feature",

"geometry":{
"type":"Polygon",
"coordinates":[[[p[1],p[0]] for p in coords_closed]]
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


# =============================
# DISPLAY MAP
# =============================

folium.LayerControl(collapsed=False).add_to(m)

st_folium(m,width=900,height=650)
