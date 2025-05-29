import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import base64
import os

st.set_page_config(page_title="Graffiti Reporter", layout="wide")
st.markdown("<h1 style='margin-bottom: 0.5rem;'>🚨 Graffiti Reporter - Silver Spring, MD</h1>", unsafe_allow_html=True)

# DataFrame column setup
required_columns = [
    "reporter", "location", "location_desc", "notes", "status", 
    "lat", "lng", "remover", "before_image", "after_image"
]

# Load from session state or create new data
if "data" not in st.session_state:
    st.session_state["data"] = pd.DataFrame(columns=required_columns)

data = st.session_state["data"]

if "selected_index" not in st.session_state:
    st.session_state["selected_index"] = None

# Sidebar summary
with st.sidebar:
    st.markdown("### 📊 Report Summary")
    st.write(f"**Total Reports:** {len(data)}")
    if not data.empty:
        st.bar_chart(data["status"].value_counts())
    else:
        st.info("No reports yet.")

# Map display
st.markdown("### 🗺️ Map of All Graffiti Reports")
m = folium.Map(location=[38.9907, -77.0261], zoom_start=15, control_scale=True, attributionControl=False)

for i, row in data.iterrows():
    color = "green" if row["status"] == "Removed" else "red"
    folium.Marker(
        location=[row["lat"], row["lng"]],
        tooltip=f"{row['location_desc']} ({row['status']}) by {row['reporter']}",
        popup=folium.Popup(f"<b>Report #{i}</b><br>{row['notes']}<br><i>{row['location_desc']}</i>", max_width=300),
        icon=folium.Icon(color=color)
    ).add_to(m)

map_data = st_folium(m, height=500, width=700)

# Detect pin click
if map_data and map_data.get("last_clicked"):
    clicked_lat = round(map_data["last_clicked"]["lat"], 5)
    clicked_lng = round(map_data["last_clicked"]["lng"], 5)
    match = data[(data["lat"].round(5) == clicked_lat) & (data["lng"].round(5) == clicked_lng)]
    if not match.empty:
        st.session_state["selected_index"] = match.index[0]
        st.success(f"📌 Selected report #{match.index[0]} from the map.")

# New graffiti report
st.markdown("---")
st.markdown("### ➕ Report New Graffiti")

reporter = st.text_input("🧑 Your Name (Required)")
location_desc = st.text_input("📍 Location Description")
notes = st.text_area("📝 Describe the graffiti")
before_photo = st.file_uploader("📷 Upload 'Before' Photo (Optional)", type=["jpg", "jpeg", "png"])

# Get map click for lat/lng
click = map_data.get("last_clicked") if map_data else None
if click:
    lat = click["lat"]
    lng = click["lng"]
    location = f"{lat:.5f}, {lng:.5f}"
    st.info(f"Selected location: {location}")
else:
    lat = lng = location = None
    st.warning("Click a location on the map to report graffiti.")

# Handle submission
if st.button("🚀 Submit Report"):
    if not reporter.strip():
        st.error("Reporter name is required.")
    elif not click:
        st.error("You must select a location on the map.")
    else:
        before_image_b64 = ""
        if before_photo:
            before_image_b64 = base64.b64encode(before_photo.read()).decode("utf-8")

        new_row = pd.DataFrame([{
            "reporter": reporter.strip(),
            "location": location,
            "location_desc": location_desc.strip(),
            "notes": notes.strip(),
            "status": "Reported",
            "lat": lat,
            "lng": lng,
            "remover": "",
            "before_image": before_image_b64,
            "after_image": ""
        }])
        data = pd.concat([data, new_row], ignore_index=True)
        st.session_state["data"] = data
        st.success("✅ Report submitted!")

# Update Section
st.markdown("---")
st.markdown("### 🛠️ Update or Remove a Report")

active_reports = data[data["status"] == "Reported"]

def make_label(row, idx):
    return f"Report #{idx} | \"{row['location_desc']}\" | Location: {row['location']}"

dropdown_options = [make_label(row, i) for i, row in active_reports.iterrows()]
active_indices = list(active_reports.index)

default_index = (active_indices.index(st.session_state["selected_index"])
                 if st.session_state["selected_index"] in active_indices else 0) if active_indices else 0

if active_reports.empty:
    st.info("No active reports to update.")
else:
    selected_option = st.selectbox("Select a report to update:", dropdown_options, index=default_index)
    selected_index = int(selected_option.split('#')[1].split('|')[0].strip())
    new_status = st.selectbox("Set new status:", ["Reported", "Removed"], index=0)

    remover_name = ""
    after_image_b64 = ""
    if new_status == "Removed":
        remover_name = st.text_input("🧹 Remover's Name (Optional)", value=data.at[selected_index, "remover"])
        after_photo = st.file_uploader("📷 Upload 'After' Photo (Optional)", type=["jpg", "jpeg", "png"])
        if after_photo:
            after_image_b64 = base64.b64encode(after_photo.read()).decode("utf-8")

    if st.button("🔄 Update Status"):
        data.at[selected_index, "status"] = new_status
        data.at[selected_index, "remover"] = remover_name.strip() if new_status == "Removed" else ""
        if after_image_b64:
            data.at[selected_index, "after_image"] = after_image_b64
        st.session_state["data"] = data
        st.session_state["selected_index"] = None
        st.success("✅ Status updated.")

# Final report viewer
st.markdown("---")
st.markdown("### 📋 All Graffiti Reports (History)")

if not data.empty:
    for i, row in data.iterrows():
        cols = st.columns([2, 3, 1])
        cols[0].markdown(f"**{row['reporter']}**  \n*{row['location_desc']}*\n\nStatus: `{row['status']}`")
        if row["before_image"]:
            cols[1].image(base64.b64decode(row["before_image"]), caption="Before", width=150)
        if row["after_image"]:
            cols[2].image(base64.b64decode(row["after_image"]), caption="After", width=150)
else:
    st.info("No reports yet.")
