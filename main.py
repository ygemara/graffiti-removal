import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import base64
import gspread
from google.oauth2.service_account import Credentials

# === CONFIGURATION ===
st.set_page_config(page_title="Graffiti Reporter", layout="wide")

REQUIRED_COLUMNS = [
    "reporter", "location", "location_desc", "notes", "status",
    "lat", "lng", "remover", "before_image", "after_image"
]

# === GOOGLE SHEETS SETUP ===
def load_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(st.secrets["gspread"], scopes=scopes)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_url(st.secrets["sheets"]["sheet_url"]).sheet1
    return sheet

def load_data(sheet):
    raw = sheet.get_all_records()
    df = pd.DataFrame(raw)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col in [
                "reporter", "location", "location_desc", "notes", "status",
                "remover", "before_image", "after_image"
            ] else 0.0
    return df

def save_data(sheet, df):
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

sheet = load_sheet()
if "data" not in st.session_state:
    st.session_state["data"] = load_data(sheet)
data = st.session_state["data"]

# === HEADER + STYLING ===
st.markdown("<h1 style='margin-bottom: 0.5rem;'>🚨 Graffiti Reporter - Silver Spring, MD</h1>", unsafe_allow_html=True)
st.markdown("""
<style>
/* Responsive padding on mobile */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
}
/* Shrink map whitespace */
div[data-testid="stVerticalBlock"] iframe {
    height: 300px !important;
    max-height: 300px !important;
    margin-bottom: -30px !important;
}
</style>
""", unsafe_allow_html=True)

# === MAP SECTION ===
st.markdown("### 🗺️ Click the map to select graffiti location")
m = folium.Map(location=[38.9907, -77.0261], zoom_start=15)
for _, row in data.iterrows():
    color = "green" if row["status"] == "Removed" else "red"
    folium.Marker(
        location=[row["lat"], row["lng"]],
        tooltip=f"{row['location_desc']} ({row['status']}) by {row['reporter']}",
        icon=folium.Icon(color=color)
    ).add_to(m)

map_data = st_folium(m, height=300)
click = map_data.get("last_clicked") if map_data and map_data.get("last_clicked") else None

if click:
    lat, lng = click["lat"], click["lng"]
    location = f"{lat:.5f}, {lng:.5f}"
    st.success(f"📍 Selected location: {location}")
else:
    lat = lng = location = None
    st.info("Click a location on the map to report graffiti.")

# === SUBMIT REPORT ===
st.markdown("### ➕ Submit a New Graffiti Report")
with st.form("report_form", clear_on_submit=True):
    reporter = st.text_input("🧑 Your Name (Required)")
    location_desc = st.text_input("📍 Description of Location")
    notes = st.text_area("📝 Describe the graffiti")
    before_photo = st.file_uploader("📷 Upload 'Before' Photo", type=["jpg", "jpeg", "png"])
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

# === UPDATE SECTION ===
st.markdown("---")
st.markdown("### 🛠️ Update Existing Reports")

active = data[data["status"] == "Reported"]
if not active.empty:
    options = [f"#{i} | {row['location_desc']} ({row['location']})" for i, row in active.iterrows()]
    selected = st.selectbox("Select a report to update", options)
    selected_index = int(selected.split("|")[0].replace("#", "").strip())

    new_status = st.selectbox("New status:", ["Reported", "Removed"])
    remover = st.text_input("🧹 Remover Name", value=data.at[selected_index, "remover"])
    after_photo = st.file_uploader("📷 Upload 'After' Photo", type=["jpg", "jpeg", "png"])

    if st.button("🔄 Update Report"):
        data.at[selected_index, "status"] = new_status
        data.at[selected_index, "remover"] = remover.strip()
        if after_photo:
            data.at[selected_index, "after_image"] = base64.b64encode(after_photo.read()).decode("utf-8")
        st.session_state["data"] = data
        save_data(sheet, data)
        st.success("✅ Report updated.")
else:
    st.info("No active reports to update.")

# === HISTORY VIEW ===
st.markdown("---")
st.markdown("### 📋 Report History")
if not data.empty:
    for _, row in data.iterrows():
        st.markdown(f"**{row['reporter']}** — *{row['location_desc']}*")
        st.markdown(f"Status: `{row['status']}` | Location: {row['location']}")
        if row["before_image"]:
            st.image(base64.b64decode(row["before_image"]), caption="Before", use_column_width=True)
        if row["after_image"]:
            st.image(base64.b64decode(row["after_image"]), caption="After", use_column_width=True)
else:
    st.info("No reports submitted yet.")

# === CHART ===
st.markdown("### 📈 Status Breakdown")
if not data.empty:
    st.bar_chart(data["status"].value_counts())
