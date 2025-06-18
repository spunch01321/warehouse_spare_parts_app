import streamlit as st
import pandas as pd
import tempfile
from utils.bom_parser import parse_bom
from utils.email_utils import send_email

st.set_page_config(page_title="Warehouse Spare Parts", layout="wide")
st.title("📦 Warehouse Spare Parts Order System")

st.sidebar.header("Upload Files")
pdf_file = st.sidebar.file_uploader("Layout PDF", type=["pdf"])
bom_file = st.sidebar.file_uploader("BOM (Excel)", type=["xlsx"])
error_file = st.sidebar.file_uploader("Error Codes (optional)", type=["xlsx", "csv"])

if bom_file:
    bom_df = parse_bom(bom_file)
    st.subheader("Available Spare Parts")
    selected = st.multiselect("Select parts:", bom_df["Part Number"].tolist())

    if selected:
        sel_df = bom_df[bom_df["Part Number"].isin(selected)]
        st.write("✅ You selected:")
        st.dataframe(sel_df)

        st.subheader("Order Submission")
        email = st.text_input("Your email address")
        if st.button("Send Order"):
            body = sel_df.to_csv(index=False)
            send_email(to=email, subject="Spare Parts Order", body=body)
            st.success("📩 Order email sent!")

if error_file:
    st.subheader("Common Error Codes")
    err_df = (pd.read_excel(error_file)
              if error_file.name.endswith("xlsx")
              else pd.read_csv(error_file))
    st.dataframe(err_df)

if pdf_file:
    st.subheader("Layout Preview")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.read())
        st.markdown(f"[📁 Open uploaded layout]({tmp.name})")
