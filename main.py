import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import base64
import gspread
from google.oauth2.service_account import Credentials

# === Page Config and Styling ===
st.set_page_config(page_title="Graffiti Reporter", layout="wide")
# Visual debug: highlight all main container elements
st.markdown("""
<style>
/* Highlight container boxes for debugging */
[data-testid="stVerticalBlock"] {
    border: 2px dashed red !important;
    margin: 0 !important;
    padding: 0 !important;
}
section.main > div {
    background-color: #fef9e7 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@media (max-width: 768px) {
    section.main > div { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    /* Target the float-container and limit to one child */
    .float-container.single {
        height: 200px !important;
        overflow: hidden !important;
    }
    
    /* Hide all float-child divs except the first one */
    .float-container.single .float-child:nth-child(2) {
        display: none !important;
    }
    
    /* Force the container height */
    .float-container.single .float-child:first-child {
        height: 200px !important;
        max-height: 200px !important;
    }
}
</style>
""", unsafe_allow_html=True)
st.markdown("<h1 style='margin-bottom: 0.5rem;'>🚨 Graffiti Reporter - Silver Spring, MD</h1>", unsafe_allow_html=True)

# === Google Sheets Setup ===
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

sheet = load_sheet()
if "data" not in st.session_state:
    st.session_state["data"] = load_data(sheet)
data = st.session_state["data"]

if "selected_index" not in st.session_state:
    st.session_state["selected_index"] = None

# === 1. Submission Form ===
st.markdown("### ➕ Report New Graffiti")
with st.form("report_form", clear_on_submit=True):
    reporter = st.text_input("🧑 Your Name (Required)", key="rep_name")
    location_desc = st.text_input("📍 Location Description", key="loc_desc")
    notes = st.text_area("📝 Describe the graffiti", key="notes_field")
    before_photo = st.file_uploader("📷 Upload 'Before' Photo (Optional)", type=["jpg", "jpeg", "png"], key="before_upload")
    submit = st.form_submit_button("🚀 Submit Report")

# === 2. Map ===
st.markdown("### 🗺️ Graffiti Location Map")

with st.container():
    m = folium.Map(location=[38.9907, -77.0261], zoom_start=15, control_scale=True)
    for i, row in data.iterrows():
        color = "green" if row["status"] == "Removed" else "red"
        folium.Marker(
            location=[row["lat"], row["lng"]],
            tooltip=f"{row['location_desc']} ({row['status']}) by {row['reporter']}",
            popup=folium.Popup(f"<b>Report #{i}</b><br>{row['notes']}<br><i>{row['location_desc']}</i>", max_width=300),
            icon=folium.Icon(color=color)
        ).add_to(m)

    map_data = st_folium(m, height=250, width="100%", returned_objects=["last_clicked"])

st.markdown("""
<style>
/* Constrain outer Streamlit block */
section.main > div > div:has(.folium-map) {
    height: 250px !important;
    max-height: 250px !important;
    min-height: 250px !important;
    padding: 0 !important;
    margin-bottom: 0 !important;
    overflow: hidden !important;
}

/* Constrain map container */
.folium-map {
    height: 250px !important;
    max-height: 250px !important;
    min-height: 250px !important;
    margin-bottom: 0 !important;
    overflow: hidden !important;
}

/* Collapse outer div too (Streamlit-generated) */
div[data-testid="stVerticalBlock"] > div:has(.folium-map) {
    height: 250px !important;
    max-height: 250px !important;
    padding-bottom: 0 !important;
    margin-bottom: 0 !important;
}
</style>

<script>
setTimeout(() => {
  const mapDiv = window.document.querySelector('.folium-map');
  if (mapDiv) {
    mapDiv.style.height = '250px';
    mapDiv.style.maxHeight = '250px';
    mapDiv.style.minHeight = '250px';
    mapDiv.style.overflow = 'hidden';
    if (mapDiv.parentElement) {
      mapDiv.parentElement.style.height = '250px';
      mapDiv.parentElement.style.maxHeight = '250px';
      mapDiv.parentElement.style.overflow = 'hidden';
    }
    const outer = mapDiv.closest('section.main > div > div');
    if (outer) {
      outer.style.height = '250px';
      outer.style.maxHeight = '250px';
      outer.style.overflow = 'hidden';
    }
  }
}, 300);
</script>
""", unsafe_allow_html=True)


click = map_data.get("last_clicked") if map_data and map_data.get("last_clicked") else None

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

# === 3. Update Section ===
st.markdown("---")
st.markdown("### 🛠️ Update or Remove a Report")

active = data[data["status"] == "Reported"]
def make_label(row, idx):
    return f"Report #{idx} | '{row['location_desc']}' | Location: {row['location']}"

options = [make_label(row, i) for i, row in active.iterrows()]
indices = list(active.index)
default_index = indices.index(st.session_state["selected_index"]) if st.session_state["selected_index"] in indices else 0 if indices else 0

if active.empty:
    st.info("No active reports to update.")
else:
    selected = st.selectbox("Select a report to update:", options, index=default_index, key="update_select")
    selected_index = int(selected.split('#')[1].split('|')[0].strip())
    new_status = st.selectbox("Set new status:", ["Reported", "Removed"], index=0, key="status_select")

    remover = ""
    after_b64 = ""
    if new_status == "Removed":
        remover = st.text_input("🧹 Remover's Name (Optional)", value=data.at[selected_index, "remover"], key="remover_input")
        after_photo = st.file_uploader("📷 Upload 'After' Photo (Optional)", type=["jpg", "jpeg", "png"], key="after_upload")
        if after_photo:
            after_b64 = base64.b64encode(after_photo.read()).decode("utf-8")

    if st.button("🔄 Update Status", key="update_button"):
        data.at[selected_index, "status"] = new_status
        data.at[selected_index, "remover"] = remover.strip() if new_status == "Removed" else ""
        if after_b64:
            data.at[selected_index, "after_image"] = after_b64
        st.session_state["data"] = data
        save_data(sheet, data)
        st.session_state["selected_index"] = None
        st.success("✅ Status updated.")

# === 4. Report History and Charts ===
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

st.markdown("---")
st.markdown("### 📈 Status Breakdown")
if not data.empty:
    st.bar_chart(data["status"].value_counts())
else:
    st.info("No data available yet.")
