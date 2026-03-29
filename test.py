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
# STYLE
# =============================
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 0rem;
    padding-left: 0rem;
    padding-right: 0rem;
}
iframe {
    height: 100vh !important;
}
section[data-testid="stSidebar"] {
    background-color: #1e1e1e;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =============================
# LOGIN
# =============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("🔐 Sistem Survey Lot PUO")

    user_id = st.text_input("Masukkan ID")
    password = st.text_input("Masukkan Kata Laluan", type="password")

    if st.button("Log Masuk"):
        if user_id in ["wan","muhammad","haziq"] and password == "wanziq67":
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
# SIDEBAR
# =============================
st.sidebar.header("Kawalan Paparan")

# 🔥 KAWALAN LAPISAN
st.sidebar.subheader("Kawalan Lapisan")
show_satellite = st.sidebar.checkbox("Google Satellite", True)
show_label = st.sidebar.checkbox("Label Stesen", True)
show_bearing = st.sidebar.checkbox("Bearing & Jarak", True)

st.sidebar.markdown("---")

marker_size = st.sidebar.slider("Saiz Marker",5,25,12)
bearing_size = st.sidebar.slider("Saiz Label",8,20,12)
zoom_level = st.sidebar.slider("Zoom",10,22,19)
poly_color = st.sidebar.color_picker("Warna","#ffff00")

epsg = st.sidebar.text_input("Kod EPSG","4390")

if st.sidebar.button("Log Keluar"):
    st.session_state.logged_in=False
    st.rerun()

# =============================
# FILE
# =============================
uploaded = st.file_uploader("📂 Upload CSV (STN, E, N)",type="csv")

if uploaded is None:
    st.stop()

df = pd.read_csv(uploaded)
df.columns = df.columns.str.strip().str.upper()

# =============================
# CONVERT
# =============================
transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
lon, lat = transformer.transform(df["E"].values, df["N"].values)

df["lon"] = lon
df["lat"] = lat

# =============================
# MAP
# =============================
center_lat = df["lat"].mean()
center_lon = df["lon"].mean()

m = folium.Map(
    location=[center_lat,center_lon],
    zoom_start=zoom_level,
    tiles=None,
    control_scale=True
)

# BASEMAP CONTROL
if show_satellite:
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Hybrid",
        max_zoom=25
    ).add_to(m)
else:
    folium.TileLayer("OpenStreetMap").add_to(m)

# =============================
# FUNCTION
# =============================
def bearing(lat1,lon1,lat2,lon2):
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    diff = math.radians(lon2-lon1)

    x = math.sin(diff)*math.cos(lat2)
    y = math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(diff)

    return (math.degrees(math.atan2(x,y))+360)%360

def to_dms(angle):
    d = int(angle)
    m = int((angle - d) * 60)
    s = int((angle - d - m/60) * 3600)
    return f"{d}°{m:02d}'{s:02d}\""

def distance(p1,p2):
    return math.sqrt(
        (p1[0]-p2[0])**2 +
        (p1[1]-p2[1])**2
    )*111139

# =============================
# SURVEY
# =============================
survey_layer = folium.FeatureGroup(name="Survey")

coords=[]

for i,row in df.iterrows():

    point=[row["lat"],row["lon"]]
    coords.append(point)

    # POINT
    folium.Marker(
        location=point,
        icon=folium.Icon(color="red", icon="map-marker", prefix="fa")
    ).add_to(survey_layer)

    # LABEL
    if show_label:
        folium.Marker(
            point,
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    color:white;
                    font-weight:bold;
                    font-size:13px;
                    text-shadow:1px 1px 2px black;
                ">
                {row["STN"]}
                </div>
                """
            )
        ).add_to(survey_layer)

coords_closed = coords + [coords[0]]

# POLYGON
folium.Polygon(
    coords_closed,
    color=poly_color,
    weight=4,
    fill=True,
    fill_opacity=0.2
).add_to(survey_layer)

# =============================
# BEARING
# =============================
perimeter = 0

for i in range(len(coords)):

    p1 = coords[i]
    p2 = coords[(i+1)%len(coords)]

    mid = [(p1[0]+p2[0])/2,(p1[1]+p2[1])/2]

    brg = bearing(p1[0],p1[1],p2[0],p2[1])
    dist = distance(p1,p2)

    perimeter += dist

    dms = to_dms(brg)
    label = f"{dms}<br>{dist:.2f}m"

    if show_bearing:
        folium.Marker(
            mid,
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    color:#5a2d0c;
                    font-size:{bearing_size}px;
                    font-weight:bold;
                    text-align:center;
                ">
                {label}
                </div>
                """
            )
        ).add_to(survey_layer)

survey_layer.add_to(m)

# =============================
# AREA
# =============================
poly = Polygon([(p[1],p[0]) for p in coords_closed])
area_m2 = poly.area * 12364000000
area_hect = area_m2 / 10000

# =============================
# SIDEBAR REPORT
# =============================
st.sidebar.subheader("📋 Laporan Lot")

st.sidebar.text(f"""
NO LOT : LOT_SAMPLE
STESEN : {len(coords)}
PEMILIK : Wan Muhammad Haziq
LUAS : {area_m2:.2f} m²
EKAR : {area_hect*2.47105:.4f} ac
PERIMETER : {perimeter:.2f} m
""")

# =============================
# DISPLAY
# =============================
folium.LayerControl().add_to(m)

st_folium(m, width="100%", height=900)
