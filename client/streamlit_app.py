# client/streamlit_app.py
import streamlit as st
import requests
import base64
from PIL import Image
import io
import pandas as pd
import os

API_BASE = st.secrets.get("api_base_url", "http://backend:8000")  # when running in docker use service name
st.set_page_config(page_title="WSParts Client", layout="wide")
st.title("Warehouse Spare Parts — Client")

# --- Auth ---
if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.username = None

def login_ui():
    st.sidebar.header("Sign in")
    uname = st.sidebar.text_input("Username")
    pwd = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Sign in"):
        try:
            r = requests.post(f"{API_BASE}/users/login", data={"username": uname, "password": pwd})
            r.raise_for_status()
            st.session_state.token = r.json()["access_token"]
            st.session_state.username = uname
            st.success("Signed in")
        except Exception as e:
            st.error(f"Login failed: {e}")
            st.session_state.token = None

if not st.session_state.token:
    login_ui()
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# --- File uploads ---
st.sidebar.header("Upload files")
pdf_file = st.sidebar.file_uploader("Layout PDF", type=["pdf"])
bom_file = st.sidebar.file_uploader("BOM (xlsx)", type=["xlsx"])
error_file = st.sidebar.file_uploader("Error codes (csv/xlsx)", type=["csv", "xlsx"])

# Basic tabs
tab1, tab2, tab3 = st.tabs(["Parts & Order", "PDF Viewer", "Service Requests"])

with tab1:
    st.header("Parts & Order")
    if bom_file:
        bom_df = pd.read_excel(bom_file)
        search = st.text_input("Search parts")
        df = bom_df[bom_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)] if search else bom_df
        parts = st.multiselect("Select Parts", df["Part Number"].tolist())
        if parts:
            sel = df[df["Part Number"].isin(parts)].copy()
            for i, r in sel.iterrows():
                qty = st.number_input(f"{r['Part Number']} qty", min_value=1, value=1, key=f"qty_{i}")
                sel.loc[i, "Qty"] = qty
            st.dataframe(sel)
            if st.button("📩 Send Order Email"):
                # call backend /users to send email (not implemented) - show local CSV
                st.success("Order prepared. Implement backend email integration to send.")
    else:
        st.info("Upload a BOM to use this tab.")

with tab2:
    st.header("PDF Viewer & Annotations")
    if not pdf_file:
        st.info("Upload a PDF in the sidebar.")
    else:
        # send to backend to render png
        files = {"file": ("layout.pdf", pdf_file.getvalue(), "application/pdf")}
        params = {"page": 0, "zoom": 1.5}
        try:
            r = requests.post(f"{API_BASE}/pdf/render", files=files, params=params, timeout=30)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
            w, h = img.size
            st.image(img, use_column_width=True)
            st.write(f"Image size: {w}px x {h}px")

            # Annotation manual entry
            st.subheader("Add Annotation")
            ann_x = st.number_input("X (px)", min_value=0, max_value=w, value=int(w*0.1))
            ann_y = st.number_input("Y (px)", min_value=0, max_value=h, value=int(h*0.1))
            ann_text = st.text_input("Text")
            ann_color = st.color_picker("Color", "#FF0000")
            if st.button("Add Annotation"):
                payload = {"page": 0, "x": int(ann_x), "y": int(ann_y), "text": ann_text, "color": ann_color}
                resp = requests.post(f"{API_BASE}/annotations", json=payload, headers=headers)
                if resp.status_code == 201:
                    st.success("Annotation saved")
                else:
                    st.error(f"Failed: {resp.text}")
            if st.button("Refresh annotations"):
                resp = requests.get(f"{API_BASE}/annotations?page=0", headers=headers)
                if resp.ok:
                    anns = resp.json()
                    st.table(pd.DataFrame(anns))
                else:
                    st.error("Failed to fetch annotations")

            # Calibration example
            if 'px_per_unit' not in st.session_state:
                st.session_state.px_per_unit = None
            with st.expander("Calibration (optional)"):
                p1 = st.number_input("Point1 x", value=0)
                p2 = st.number_input("Point1 y", value=0)
                p3 = st.number_input("Point2 x", value=w)
                p4 = st.number_input("Point2 y", value=h)
                real_dist = st.number_input("Real distance between points", value=0.0)
                unit = st.text_input("Unit (e.g. mm)", value="mm")
                if st.button("Compute scale"):
                    if real_dist > 0:
                        px_dist = ((p1 - p3)**2 + (p2 - p4)**2)**0.5
                        st.session_state.px_per_unit = px_dist / real_dist
                        st.success(f"{st.session_state.px_per_unit:.4f} px per {unit}")
                    else:
                        st.error("Enter a real distance > 0")

        except Exception as e:
            st.error(f"Rendering error: {e}")

with tab3:
    st.header("Request Service")
    subject = st.text_input("Subject")
    desc = st.text_area("Description")
    if st.button("Request Service"):
        payload = {"subject": subject, "description": desc, "metadata": {"user": st.session_state.username}}
        r = requests.post(f"{API_BASE}/service/request", json=payload, headers=headers)
        if r.status_code == 201:
            st.success("Service request submitted")
        else:
            st.error(f"Failed: {r.text}")
