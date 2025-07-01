import streamlit as st
import pandas as pd
import tempfile
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import base64
from utils.bom_parser import parse_bom
from utils.email_utils import send_email

# Page configuration
st.set_page_config(page_title="Warehouse Spare Parts", layout="wide")
st.title("📦 Warehouse Spare Parts Order System")

# Initialize session state for quantities and maintenance data
if 'part_quantities' not in st.session_state:
    st.session_state.part_quantities = {}
if 'maintenance_records' not in st.session_state:
    st.session_state.maintenance_records = []

# Sidebar for file uploads
st.sidebar.header("Upload Files")
pdf_file = st.sidebar.file_uploader("Layout PDF", type=["pdf"])
bom_file = st.sidebar.file_uploader("BOM (Excel)", type=["xlsx"])
error_file = st.sidebar.file_uploader("Error Codes (optional)", type=["xlsx", "csv"])

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📋 Parts Selection", "🔧 Assembly View", "📊 Quantities", "🛠️ Maintenance"])

with tab1:
    st.header("Parts Selection & Ordering")
    
    if bom_file:
        bom_df = parse_bom(bom_file)
        
        # Enhanced parts selection with search and filters
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Available Spare Parts")
            
            # Search functionality
            search_term = st.text_input("🔍 Search parts:", placeholder="Enter part number, description, or category")
            
            # Filter dataframe based on search
            if search_term:
                filtered_df = bom_df[
                    bom_df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)
                ]
            else:
                filtered_df = bom_df
            
            # Display parts with selection checkboxes
            selected_parts = []
            for idx, row in filtered_df.iterrows():
                col_check, col_info = st.columns([0.1, 0.9])
                with col_check:
                    if st.checkbox("", key=f"part_{idx}"):
                        selected_parts.append(row["Part Number"])
                with col_info:
                    st.write(f"**{row['Part Number']}** - {row.get('Description', 'N/A')}")
                    if 'Price' in row:
                        st.write(f"💰 ${row['Price']:.2f}")
        
        with col2:
            if selected_parts:
                st.subheader("Selected Parts Summary")
                sel_df = bom_df[bom_df["Part Number"].isin(selected_parts)]
                
                # Add quantity selection for each part
                for part in selected_parts:
                    qty = st.number_input(
                        f"Qty for {part}:", 
                        min_value=1, 
                        value=st.session_state.part_quantities.get(part, 1),
                        key=f"qty_{part}"
                    )
                    st.session_state.part_quantities[part] = qty
                
                # Calculate total cost if price available
                if 'Price' in sel_df.columns:
                    total_cost = sum([
                        sel_df[sel_df["Part Number"] == part]["Price"].iloc[0] * 
                        st.session_state.part_quantities[part] 
                        for part in selected_parts
                    ])
                    st.metric("Total Cost", f"${total_cost:.2f}")
                
                st.subheader("Order Submission")
                email = st.text_input("Your email address")
                
                if st.button("📩 Send Order", type="primary"):
                    # Create order summary with quantities
                    order_data = []
                    for part in selected_parts:
                        part_info = sel_df[sel_df["Part Number"] == part].iloc[0]
                        order_data.append({
                            "Part Number": part,
                            "Description": part_info.get("Description", "N/A"),
                            "Quantity": st.session_state.part_quantities[part],
                            "Unit Price": part_info.get("Price", 0),
                            "Total": part_info.get("Price", 0) * st.session_state.part_quantities[part]
                        })
                    
                    order_df = pd.DataFrame(order_data)
                    body = order_df.to_csv(index=False)
                    send_email(to=email, subject="Spare Parts Order", body=body)
                    st.success("📩 Order email sent!")
                    
                    # Display order summary
                    st.dataframe(order_df)

with tab2:
    st.header("Assembly Visualization")
    
    if pdf_file:
        st.subheader("Interactive Assembly View")
        
        # Create exploded assembly visualization
        # This is a mock visualization - in practice, you'd need to parse the PDF
        # and extract component positions/relationships
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Explosion factor slider
            explosion_factor = st.slider("Assembly Explosion Factor", 0.0, 2.0, 0.0, 0.1)
            
            # Mock assembly data (replace with actual PDF parsing)
            components = [
                {"name": "Housing", "x": 0, "y": 0, "z": 0, "color": "blue"},
                {"name": "Motor", "x": 10, "y": 5, "z": 2, "color": "red"},
                {"name": "Bearing A", "x": -5, "y": 3, "z": 1, "color": "green"},
                {"name": "Bearing B", "x": 15, "y": 3, "z": 1, "color": "green"},
                {"name": "Shaft", "x": 5, "y": 0, "z": 0, "color": "gray"},
                {"name": "Cover", "x": 0, "y": 0, "z": 10, "color": "orange"}
            ]
            
            # Apply explosion effect
            exploded_components = []
            center_x, center_y, center_z = 5, 2.5, 2.5
            
            for comp in components:
                # Calculate direction from center
                dx = comp["x"] - center_x
                dy = comp["y"] - center_y
                dz = comp["z"] - center_z
                
                # Apply explosion
                exploded_x = comp["x"] + dx * explosion_factor
                exploded_y = comp["y"] + dy * explosion_factor
                exploded_z = comp["z"] + dz * explosion_factor
                
                exploded_components.append({
                    **comp,
                    "exploded_x": exploded_x,
                    "exploded_y": exploded_y,
                    "exploded_z": exploded_z
                })
            
            # Create 3D scatter plot
            fig = go.Figure()
            
            for comp in exploded_components:
                fig.add_trace(go.Scatter3d(
                    x=[comp["exploded_x"]],
                    y=[comp["exploded_y"]],
                    z=[comp["exploded_z"]],
                    mode='markers+text',
                    marker=dict(size=15, color=comp["color"]),
                    text=[comp["name"]],
                    textposition="top center",
                    name=comp["name"]
                ))
            
            fig.update_layout(
                title="Assembly Exploded View",
                scene=dict(
                    xaxis_title="X",
                    yaxis_title="Y",
                    zaxis_title="Z"
                ),
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Component Details")
            
            # Component selection
            selected_component = st.selectbox(
                "Select Component:",
                [comp["name"] for comp in components]
            )
            
            if selected_component and bom_file:
                # Try to find matching part in BOM
                comp_info = next((comp for comp in components if comp["name"] == selected_component), None)
                if comp_info:
                    st.write(f"**Component:** {selected_component}")
                    st.write(f"**Color:** {comp_info['color']}")
                    st.write(f"**Position:** ({comp_info['x']}, {comp_info['y']}, {comp_info['z']})")
                    
                    # Try to find in BOM
                    bom_df = parse_bom(bom_file)
                    matching_parts = bom_df[bom_df["Description"].str.contains(selected_component, case=False, na=False)]
                    
                    if not matching_parts.empty:
                        st.write("**Related BOM Parts:**")
                        st.dataframe(matching_parts)
    
    else:
        st.info("📄 Upload a PDF layout file to see assembly visualization")

with tab3:
    st.header("Quantity Management")
    
    if bom_file:
        bom_df = parse_bom(bom_file)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Inventory Overview")
            
            # Mock inventory data (you can connect this to actual inventory system)
            if 'Stock' not in bom_df.columns:
                bom_df['Stock'] = [50, 25, 100, 15, 30] + [20] * (len(bom_df) - 5)
            if 'Min_Stock' not in bom_df.columns:
                bom_df['Min_Stock'] = [10, 5, 20, 5, 10] + [5] * (len(bom_df) - 5)
            
            # Stock level indicators
            bom_df['Status'] = bom_df.apply(
                lambda row: 'Low Stock' if row['Stock'] <= row['Min_Stock'] 
                else 'Good' if row['Stock'] > row['Min_Stock'] * 2 
                else 'Medium', axis=1
            )
            
            # Display stock chart
            fig = px.bar(
                bom_df.head(10), 
                x='Part Number', 
                y='Stock',
                color='Status',
                color_discrete_map={'Low Stock': 'red', 'Medium': 'orange', 'Good': 'green'},
                title="Current Stock Levels"
            )
            fig.update_xaxis(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("⚠️ Low Stock Alerts")
            
            low_stock = bom_df[bom_df['Status'] == 'Low Stock']
            if not low_stock.empty:
                for _, part in low_stock.iterrows():
                    st.error(f"**{part['Part Number']}**: {part['Stock']} units (Min: {part['Min_Stock']})")
            else:
                st.success("All parts are adequately stocked!")
        
        st.subheader("📈 Quantity Analytics")
        
        # Usage trends (mock data)
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='W')
        usage_data = pd.DataFrame({
            'Date': dates,
            'Parts_Used': [15 + i % 10 + (i // 10) % 5 for i in range(len(dates))]
        })
        
        fig = px.line(usage_data, x='Date', y='Parts_Used', title='Weekly Parts Usage Trend')
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("Maintenance Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📅 Maintenance Schedule")
        
        # Add new maintenance record
        with st.expander("➕ Add Maintenance Record"):
            maint_part = st.text_input("Part/Equipment:")
            maint_type = st.selectbox("Maintenance Type:", ["Preventive", "Corrective", "Emergency", "Inspection"])
            maint_date = st.date_input("Scheduled Date:")
            maint_desc = st.text_area("Description:")
            maint_tech = st.text_input("Technician:")
            
            if st.button("Add Record"):
                new_record = {
                    "Part": maint_part,
                    "Type": maint_type,
                    "Date": maint_date,
                    "Description": maint_desc,
                    "Technician": maint_tech,
                    "Status": "Scheduled",
                    "Created": datetime.now()
                }
                st.session_state.maintenance_records.append(new_record)
                st.success("Maintenance record added!")
        
        # Display maintenance records
        if st.session_state.maintenance_records:
            maint_df = pd.DataFrame(st.session_state.maintenance_records)
            
            # Filter options
            status_filter = st.multiselect(
                "Filter by Status:",
                ["Scheduled", "In Progress", "Completed", "Overdue"],
                default=["Scheduled", "In Progress"]
            )
            
            filtered_maint = maint_df[maint_df["Status"].isin(status_filter)]
            
            # Editable maintenance table
            for idx, record in filtered_maint.iterrows():
                with st.container():
                    col_info, col_status, col_actions = st.columns([3, 1, 1])
                    
                    with col_info:
                        st.write(f"**{record['Part']}** - {record['Type']}")
                        st.write(f"📅 {record['Date']} | 👤 {record['Technician']}")
                        st.write(f"📝 {record['Description']}")
                    
                    with col_status:
                        new_status = st.selectbox(
                            "Status:",
                            ["Scheduled", "In Progress", "Completed", "Overdue"],
                            index=["Scheduled", "In Progress", "Completed", "Overdue"].index(record["Status"]),
                            key=f"status_{idx}"
                        )
                        if new_status != record["Status"]:
                            st.session_state.maintenance_records[idx]["Status"] = new_status
                    
                    with col_actions:
                        if st.button("🗑️ Delete", key=f"del_{idx}"):
                            st.session_state.maintenance_records.pop(idx)
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No maintenance records yet. Add one above!")
    
    with col2:
        st.subheader("📊 Maintenance Stats")
        
        if st.session_state.maintenance_records:
            maint_df = pd.DataFrame(st.session_state.maintenance_records)
            
            # Status distribution
            status_counts = maint_df["Status"].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index, title="Maintenance Status Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Type distribution
            type_counts = maint_df["Type"].value_counts()
            fig = px.bar(x=type_counts.index, y=type_counts.values, title="Maintenance Types")
            st.plotly_chart(fig, use_container_width=True)
            
            # Upcoming maintenance
            st.subheader("🔔 Upcoming Maintenance")
            upcoming = maint_df[
                (maint_df["Status"] == "Scheduled") & 
                (pd.to_datetime(maint_df["Date"]) <= datetime.now() + timedelta(days=7))
            ]
            
            if not upcoming.empty:
                for _, record in upcoming.iterrows():
                    days_until = (pd.to_datetime(record["Date"]) - datetime.now()).days
                    if days_until <= 0:
                        st.error(f"⚠️ **{record['Part']}** - Overdue!")
                    elif days_until <= 3:
                        st.warning(f"🟡 **{record['Part']}** - Due in {days_until} days")
                    else:
                        st.info(f"🔵 **{record['Part']}** - Due in {days_until} days")
            else:
                st.success("No urgent maintenance scheduled!")

# Error codes section (moved to bottom)
if error_file:
    st.subheader("📋 Common Error Codes")
    err_df = (pd.read_excel(error_file) if error_file.name.endswith("xlsx") else pd.read_csv(error_file))
    
    # Search functionality for error codes
    error_search = st.text_input("🔍 Search error codes:", placeholder="Enter error code or description")
    if error_search:
        filtered_errors = err_df[err_df.apply(lambda row: error_search.lower() in str(row).lower(), axis=1)]
        st.dataframe(filtered_errors)
    else:
        st.dataframe(err_df)
