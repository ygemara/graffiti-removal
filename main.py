import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import base64
import gspread
from google.oauth2.service_account import Credentials

# === Styling and Layout ===
st.set_page_config(page_title="Graffiti Reporter", layout="wide")
st.markdown("""
<style>
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
}
</style>
""", unsafe_allow_html=True)
st.markdown("<h1 style='margin-bottom: 0.5rem;'>🚨 Graffiti Reporter - Silver Spring, MD</h1>", unsafe_allow_html=True)

# === Setup ===
required_columns = [
    "reporter", "location", "location_desc", "notes", "status",
    "lat", "lng", "remover", "before_image", "after_image"
]

def load_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(st.secrets["gspread"], scopes=scopes)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_url(st.secrets["sheets"]["sheet_url"]).sheet1
    return sheet

def load_data(sheet):
    raw = sheet.get_all_records()
    df = pd.DataFrame(raw)
    for col in required_columns:
        if col not in df.columns:
            df[col] = "" if col in ["reporter", "location", "location_desc", "notes", "status", "remover", "before_image", "after_image"] else 0.0
    return df

def save_data(sheet, df):
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# === Data Load ===
sheet = load_sheet()
if "data" not in st.session_state:
    st.session_state["data"] = load_data(sheet)
data = st.session_state["data"]

if "selected_index" not in st.session_state:
    st.session_state["selected_index"] = None

# === Map ===
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

map_data = st_folium(m, height=400, width="100%")

click = map_data.get("last_clicked") if map_data else None
if click:
    lat, lng = click["lat"], click["lng"]
    location = f"{lat:.5f}, {lng:.5f}"
    st.markdown(f"""
    <div style='background-color:#e8f5e9;padding:12px;border-radius:6px;border:1px solid #c8e6c9'>
    <strong>📍 Location Selected:</strong><br>
    <code>{location}</code>
    </div>
    """, unsafe_allow_html=True)
else:
    lat = lng = location = None

if map_data and map_data.get("last_clicked"):
    clicked_lat = round(map_data["last_clicked"]["lat"], 5)
    clicked_lng = round(map_data["last_clicked"]["lng"], 5)
    match = data[(data["lat"].round(5) == clicked_lat) & (data["lng"].round(5) == clicked_lng)]
    if not match.empty:
        st.session_state["selected_index"] = match.index[0]
        st.success(f"📌 Selected report #{match.index[0]} from the map.")

# === Report Form (Main page for mobile, not in sidebar) ===
st.markdown("### ➕ Report New Graffiti")
with st.form("report_form", clear_on_submit=True):
    reporter = st.text_input("🧑 Your Name (Required)")
    location_desc = st.text_input("📍 Location Description")
    notes = st.text_area("📝 Describe the graffiti")
    before_photo = st.file_uploader("📷 Upload 'Before' Photo (Optional)", type=["jpg", "jpeg", "png"])
    submit = st.form_submit_button("🚀 Submit Report")

    if submit:
        if not reporter.strip():
            st.error("Reporter name is required.")
        elif not click:
            st.error("You must select a location on the map.")
        else:
            before_b64 = base64.b64encode(before_photo.read()).decode("utf-8") if before_photo else ""
            new_row = pd.DataFrame([{
                "reporter": reporter.strip(),
                "location": location,
                "location_desc": location_desc.strip(),
                "notes": notes.strip(),
                "status": "Reported",
                "lat": lat,
                "lng": lng,
                "remover": "",
                "before_image": before_b64,
                "after_image": ""
            }])
            data = pd.concat([data, new_row], ignore_index=True)
            st.session_state["data"] = data
            save_data(sheet, data)
            st.success("✅ Report submitted!")

# === Update Section ===
st.markdown("---")
st.markdown("### 🛠️ Update or Remove a Report")

active = data[data["status"] == "Reported"]
def make_label(row, idx):
    return f"Report #{idx} | \"{row['location_desc']}\" | Location: {row['location']}"

options = [make_label(row, i) for i, row in active.iterrows()]
indices = list(active.index)
default_index = indices.index(st.session_state["selected_index"]) if st.session_state["selected_index"] in indices else 0 if indices else 0

if active.empty:
    st.info("No active reports to update.")
else:
    selected = st.selectbox("Select a report to update:", options, index=default_index)
    selected_index = int(selected.split('#')[1].split('|')[0].strip())
    new_status = st.selectbox("Set new status:", ["Reported", "Removed"], index=0)

    remover = ""
    after_b64 = ""
    if new_status == "Removed":
        remover = st.text_input("🧹 Remover's Name (Optional)", value=data.at[selected_index, "remover"])
        after_photo = st.file_uploader("📷 Upload 'After' Photo (Optional)", type=["jpg", "jpeg", "png"])
        if after_photo:
            after_b64 = base64.b64encode(after_photo.read()).decode("utf-8")

    if st.button("🔄 Update Status"):
        data.at[selected_index, "status"] = new_status
        data.at[selected_index, "remover"] = remover.strip() if new_status == "Removed" else ""
        if after_b64:
            data.at[selected_index, "after_image"] = after_b64
        st.session_state["data"] = data
        save_data(sheet, data)
        st.session_state["selected_index"] = None
        st.success("✅ Status updated.")

# === Report History ===
st.markdown("---")
st.markdown("### 📋 All Graffiti Reports (History)")

if not data.empty:
    for i, row in data.iterrows():
        with st.container():
            st.markdown(f"**{row['reporter']}** — *{row['location_desc']}*")
            st.markdown(f"Status: `{row['status']}`  |  Location: {row['location']}")
            if row["before_image"]:
                st.image(base64.b64decode(row["before_image"]), caption="Before", use_column_width=True)
            if row["after_image"]:
                st.image(base64.b64decode(row["after_image"]), caption="After", use_column_width=True)
else:
    st.info("No reports yet.")

# === Status Chart ===
st.markdown("---")
st.markdown("### 📈 Status Breakdown")
if not data.empty:
    st.bar_chart(data["status"].value_counts())
else:
    st.info("No data available yet.")
