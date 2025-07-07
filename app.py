import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import base64
import json

# Import your custom modules (make sure these exist)
try:
    from utils.bom_parser import parse_bom
    from utils.email_utils import send_email
except ImportError:
    st.error("Missing required modules: utils.bom_parser and utils.email_utils")
    st.stop()

# Page configuration
st.set_page_config(page_title="Warehouse Spare Parts", layout="wide")
st.title("📦 Warehouse Spare Parts Order System")

# Initialize session state
if 'part_quantities' not in st.session_state:
    st.session_state.part_quantities = {}
if 'maintenance_records' not in st.session_state:
    st.session_state.maintenance_records = []
if 'pdf_annotations' not in st.session_state:
    st.session_state.pdf_annotations = []
if 'annotation_mode' not in st.session_state:
    st.session_state.annotation_mode = False
if 'selected_annotation_type' not in st.session_state:
    st.session_state.selected_annotation_type = "Part Location"

# Enhanced PDF annotation component
def create_clickable_pdf_viewer(pdf_file, page_num=0, zoom=1.0):
    """Create an interactive PDF viewer with clickable annotations"""
    
    # Custom CSS for annotation styling
    st.markdown("""
    <style>
    .pdf-container {
        position: relative;
        display: inline-block;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .annotation-marker {
        position: absolute;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: 2px solid #fff;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 12px;
        color: white;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        z-index: 10;
    }
    
    .annotation-marker:hover {
        transform: scale(1.2);
        transition: transform 0.2s ease;
    }
    
    .annotation-tooltip {
        position: absolute;
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        white-space: nowrap;
        z-index: 20;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease;
    }
    
    .annotation-marker:hover + .annotation-tooltip {
        opacity: 1;
    }
    
    .annotation-form {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin: 10px 0;
    }
    
    .annotation-list {
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
    }
    
    .annotation-item {
        background: white;
        padding: 10px;
        margin: 5px 0;
        border-radius: 6px;
        border: 1px solid #e0e0e0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .annotation-item:hover {
        background: #f0f0f0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        import io
        
        # Convert PDF to images
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        page = pdf_document.load_page(page_num)
        
        # Render page as image
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to base64 for HTML display
        img_base64 = base64.b64encode(img_data).decode()
        
        # Get page dimensions
        page_width = int(page.rect.width * zoom)
        page_height = int(page.rect.height * zoom)
        
        # Create interactive PDF viewer with JavaScript
        pdf_viewer_html = f"""
        <div class="pdf-container" id="pdf-container">
            <img id="pdf-image" src="data:image/png;base64,{img_base64}" 
                 style="width: {page_width}px; height: {page_height}px; display: block;" 
                 onclick="addAnnotation(event)">
            <div id="annotations-overlay"></div>
        </div>
        
        <script>
        let annotationMode = false;
        let annotationCounter = 0;
        
        function toggleAnnotationMode() {{
            annotationMode = !annotationMode;
            const img = document.getElementById('pdf-image');
            if (annotationMode) {{
                img.style.cursor = 'crosshair';
                img.style.border = '3px solid #007bff';
            }} else {{
                img.style.cursor = 'default';
                img.style.border = 'none';
            }}
        }}
        
        function addAnnotation(event) {{
            if (!annotationMode) return;
            
            const rect = event.target.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            // Create annotation marker
            const marker = document.createElement('div');
            marker.className = 'annotation-marker';
            marker.style.left = (x - 10) + 'px';
            marker.style.top = (y - 10) + 'px';
            marker.style.backgroundColor = '#ff6b6b';
            marker.innerHTML = ++annotationCounter;
            
            // Add click event for editing
            marker.onclick = function(e) {{
                e.stopPropagation();
                editAnnotation(marker, x, y);
            }};
            
            document.getElementById('annotations-overlay').appendChild(marker);
            
            // Store annotation data
            window.parent.postMessage({{
                type: 'annotation_added',
                x: x,
                y: y,
                id: annotationCounter
            }}, '*');
        }}
        
        function editAnnotation(marker, x, y) {{
            const text = prompt('Enter annotation text:');
            if (text) {{
                marker.title = text;
                // Update annotation data
                window.parent.postMessage({{
                    type: 'annotation_updated',
                    x: x,
                    y: y,
                    text: text,
                    id: marker.innerHTML
                }}, '*');
            }}
        }}
        
        // Load existing annotations
        function loadAnnotations(annotations) {{
            const overlay = document.getElementById('annotations-overlay');
            overlay.innerHTML = '';
            
            annotations.forEach((ann, index) => {{
                const marker = document.createElement('div');
                marker.className = 'annotation-marker';
                marker.style.left = (ann.x - 10) + 'px';
                marker.style.top = (ann.y - 10) + 'px';
                marker.style.backgroundColor = ann.color || '#ff6b6b';
                marker.innerHTML = index + 1;
                marker.title = ann.text;
                
                marker.onclick = function(e) {{
                    e.stopPropagation();
                    editAnnotation(marker, ann.x, ann.y);
                }};
                
                overlay.appendChild(marker);
            }});
            
            annotationCounter = annotations.length;
        }}
        </script>
        """
        
        # Display the PDF viewer
        st.components.v1.html(pdf_viewer_html, height=page_height + 50)
        
        pdf_document.close()
        return page_width, page_height
        
    except ImportError:
        st.error("Missing required libraries. Please install: `pip install PyMuPDF pillow`")
        return 0, 0
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return 0, 0

# Sidebar for file uploads
st.sidebar.header("📁 Upload Files")
pdf_file = st.sidebar.file_uploader("Layout PDF", type=["pdf"])
bom_file = st.sidebar.file_uploader("BOM (Excel)", type=["xlsx"])
error_file = st.sidebar.file_uploader("Error Codes (optional)", type=["xlsx", "csv"])

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📋 Parts Selection", "🔧 Assembly View", "📊 Quantities", "🛠️ Maintenance"])

# Tab 1: Parts Selection (keeping your existing logic)
with tab1:
    st.header("Parts Selection & Ordering")
    
    if bom_file:
        try:
            bom_df = parse_bom(bom_file)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Available Spare Parts")
                
                search_term = st.text_input("🔍 Search parts:", placeholder="Enter part number, description, or category")
                
                if search_term:
                    filtered_df = bom_df[
                        bom_df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)
                    ]
                else:
                    filtered_df = bom_df
                
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
                    
                    for part in selected_parts:
                        qty = st.number_input(
                            f"Qty for {part}:", 
                            min_value=1, 
                            value=st.session_state.part_quantities.get(part, 1),
                            key=f"qty_{part}"
                        )
                        st.session_state.part_quantities[part] = qty
                    
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
                        
                        try:
                            send_email(to=email, subject="Spare Parts Order", body=body)
                            st.success("📩 Order email sent!")
                        except Exception as e:
                            st.error(f"Error sending email: {str(e)}")
                        
                        st.dataframe(order_df)
        except Exception as e:
            st.error(f"Error processing BOM file: {str(e)}")
    else:
        st.info("📄 Upload a BOM Excel file to see available parts")

# Tab 2: Enhanced Assembly View with Clickable Annotations
with tab2:
    st.header("🔧 Interactive PDF Assembly Viewer")
    
    if pdf_file:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("📄 Assembly Layout")
            
            # PDF controls
            pdf_controls_col1, pdf_controls_col2, pdf_controls_col3 = st.columns(3)
            
            with pdf_controls_col1:
                try:
                    import fitz
                    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
                    page_count = pdf_document.page_count
                    
                    if page_count > 1:
                        selected_page = st.selectbox("📄 Select Page:", range(1, page_count + 1)) - 1
                    else:
                        selected_page = 0
                        st.info(f"PDF has {page_count} page(s)")
                    
                    pdf_document.close()
                except:
                    selected_page = 0
                    page_count = 1
            
            with pdf_controls_col2:
                zoom = st.slider("🔍 Zoom Level", 0.5, 3.0, 1.0, 0.1)
            
            with pdf_controls_col3:
                annotation_mode = st.toggle("✏️ Annotation Mode", value=st.session_state.annotation_mode)
                st.session_state.annotation_mode = annotation_mode
            
            # Annotation type selector
            if annotation_mode:
                annotation_type = st.selectbox(
                    "📝 Annotation Type:",
                    ["Part Location", "Maintenance Point", "Warning", "Note", "Measurement"]
                )
                st.session_state.selected_annotation_type = annotation_type
            
            # Create the interactive PDF viewer
            if pdf_file:
                pdf_file.seek(0)  # Reset file pointer
                page_width, page_height = create_clickable_pdf_viewer(pdf_file, selected_page, zoom)
            
            # Manual annotation form (enhanced)
            with st.expander("📍 Manual Annotation Entry", expanded=annotation_mode):
                ann_col1, ann_col2 = st.columns(2)
                
                with ann_col1:
                    ann_x = st.number_input("X Position (pixels)", min_value=0, max_value=page_width, value=100)
                    ann_y = st.number_input("Y Position (pixels)", min_value=0, max_value=page_height, value=100)
                
                with ann_col2:
                    ann_text = st.text_input("Annotation Text:", placeholder="Enter description")
                    ann_color = st.selectbox("Color:", ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"])
                
                if st.button("➕ Add Manual Annotation") and ann_text:
                    annotation = {
                        "page": selected_page,
                        "x": ann_x,
                        "y": ann_y,
                        "text": ann_text,
                        "color": ann_color,
                        "type": st.session_state.selected_annotation_type,
                        "timestamp": datetime.now().isoformat()
                    }
                    st.session_state.pdf_annotations.append(annotation)
                    st.success(f"✅ Added annotation: {ann_text}")
                    st.rerun()
        
        with col2:
            st.subheader("📋 Annotation Manager")
            
            # Annotation statistics
            if st.session_state.pdf_annotations:
                ann_df = pd.DataFrame(st.session_state.pdf_annotations)
                
                # Filter annotations by current page
                current_page_annotations = ann_df[ann_df["page"] == selected_page]
                
                st.metric("Total Annotations", len(st.session_state.pdf_annotations))
                st.metric("Current Page", len(current_page_annotations))
                
                # Annotation type distribution
                if len(ann_df) > 0:
                    type_counts = ann_df["type"].value_counts()
                    fig = px.pie(values=type_counts.values, names=type_counts.index, 
                               title="Annotation Types")
                    st.plotly_chart(fig, use_container_width=True)
            
            # Quick BOM part linking
            if bom_file:
                st.subheader("🔗 Link BOM Parts")
                
                try:
                    bom_df = parse_bom(bom_file)
                    part_options = bom_df["Part Number"].tolist()
                    selected_part = st.selectbox("Select BOM Part:", [""] + part_options)
                    
                    if selected_part:
                        part_info = bom_df[bom_df["Part Number"] == selected_part].iloc[0]
                        st.write(f"**Part:** {selected_part}")
                        st.write(f"**Description:** {part_info.get('Description', 'N/A')}")
                        
                        if st.button("📍 Quick Add to Center"):
                            annotation = {
                                "page": selected_page,
                                "x": page_width // 2,
                                "y": page_height // 2,
                                "text": f"{selected_part} - {part_info.get('Description', 'N/A')}",
                                "color": "#FF6B6B",
                                "type": "Part Location",
                                "timestamp": datetime.now().isoformat()
                            }
                            st.session_state.pdf_annotations.append(annotation)
                            st.success(f"✅ Added {selected_part}")
                            st.rerun()
                
                except Exception as e:
                    st.error(f"Error linking BOM: {str(e)}")
            
            # Annotation list for current page
            if st.session_state.pdf_annotations:
                current_page_annotations = [ann for ann in st.session_state.pdf_annotations if ann["page"] == selected_page]
                
                if current_page_annotations:
                    st.subheader("📌 Current Page Annotations")
                    
                    for i, ann in enumerate(current_page_annotations):
                        with st.container():
                            st.markdown(f"""
                            <div style="background: white; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 4px solid {ann['color']};">
                                <strong>{ann['text']}</strong><br>
                                <small>Type: {ann['type']} | Position: ({ann['x']}, {ann['y']})</small>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("🗑️ Remove", key=f"del_ann_{i}"):
                                st.session_state.pdf_annotations.remove(ann)
                                st.rerun()
                else:
                    st.info("No annotations on this page")
            
            # Export options
            if st.session_state.pdf_annotations:
                st.subheader("💾 Export Annotations")
                
                ann_df = pd.DataFrame(st.session_state.pdf_annotations)
                
                # Export as CSV
                csv = ann_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"pdf_annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
                # Export as JSON
                json_data = json.dumps(st.session_state.pdf_annotations, indent=2)
                st.download_button(
                    label="📥 Download as JSON",
                    data=json_data,
                    file_name=f"pdf_annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
                
                # Clear all annotations
                if st.button("🗑️ Clear All Annotations"):
                    st.session_state.pdf_annotations = []
                    st.rerun()
    
    else:
        st.info("📄 Upload a PDF layout file to start annotating")
        st.markdown("""
        **Enhanced Features:**
        - ✏️ Click directly on PDF to add annotations
        - 🎨 Color-coded annotation types
        - 🔗 Link BOM parts to PDF locations
        - 📊 Annotation statistics and visualization
        - 💾 Export annotations as CSV/JSON
        - 🔍 Zoom and pan controls
        """)

# Tab 3: Quantities (keeping your existing logic)
with tab3:
    st.header("📊 Quantity Management")
    
    if bom_file:
        try:
            bom_df = parse_bom(bom_file)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Inventory Overview")
                
                # Mock inventory data
                if 'Stock' not in bom_df.columns:
                    stock_values = [50, 25, 100, 15, 30]
                    while len(stock_values) < len(bom_df):
                        stock_values.append(20)
                    bom_df['Stock'] = stock_values[:len(bom_df)]
                
                if 'Min_Stock' not in bom_df.columns:
                    min_stock_values = [10, 5, 20, 5, 10]
                    while len(min_stock_values) < len(bom_df):
                        min_stock_values.append(5)
                    bom_df['Min_Stock'] = min_stock_values[:len(bom_df)]
                
                bom_df['Status'] = bom_df.apply(
                    lambda row: 'Low Stock' if row['Stock'] <= row['Min_Stock'] 
                    else 'Good' if row['Stock'] > row['Min_Stock'] * 2 
                    else 'Medium', axis=1
                )
                
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
            
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='W')
            usage_data = pd.DataFrame({
                'Date': dates,
                'Parts_Used': [15 + i % 10 + (i // 10) % 5 for i in range(len(dates))]
            })
            
            fig = px.line(usage_data, x='Date', y='Parts_Used', title='Weekly Parts Usage Trend')
            st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.error(f"Error processing quantities: {str(e)}")
    else:
        st.info("📄 Upload a BOM file to see quantity management")

# Tab 4: Maintenance (keeping your existing logic)
with tab4:
    st.header("🛠️ Maintenance Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📅 Maintenance Schedule")
        
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
        
        if st.session_state.maintenance_records:
            maint_df = pd.DataFrame(st.session_state.maintenance_records)
            
            status_filter = st.multiselect(
                "Filter by Status:",
                ["Scheduled", "In Progress", "Completed", "Overdue"],
                default=["Scheduled", "In Progress"]
            )
            
            if status_filter:
                filtered_maint = maint_df[maint_df["Status"].isin(status_filter)]
            else:
                filtered_maint = maint_df
            
            for idx, record in filtered_maint.iterrows():
                with st.container():
                    col_info, col_status, col_actions = st.columns([3, 1, 1])
                    
                    with col_info:
                        st.write(f"**{record['Part']}** - {record['Type']}")
                        st.write(f"📅 {record['Date']} | 👤 {record['Technician']}")
                        st.write(f"📝 {record['Description']}")
                    
                    with col_status:
                        status_options = ["Scheduled", "In Progress", "Completed", "Overdue"]
                        current_status_idx = status_options.index(record["Status"]) if record["Status"] in status_options else 0
                        
                        new_status = st.selectbox(
                            "Status:",
                            status_options,
                            index=current_status_idx,
                            key=f"status_{idx}"
                        )
                        if new_status != record["Status"]:
                            original_idx = maint_df.index[maint_df.index == idx].tolist()[0]
                            st.session_state.maintenance_records[original_idx]["Status"] = new_status
                    
                    with col_actions:
                        if st.button("🗑️ Delete", key=f"del_{idx}"):
                            original_idx = maint_df.index[maint_df.index == idx].tolist()[0]
                            del st.session_state.maintenance_records[original_idx]
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No maintenance records yet. Add one above!")
    
    with col2:
        st.subheader("📊 Maintenance Stats")
        
        if st.session_state.maintenance_records:
            maint_df = pd.DataFrame(st.session_state.maintenance_records)
            
            status_counts = maint_df["Status"].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index, title="Maintenance Status Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            type_counts = maint_df["Type"].value_counts()
            fig = px.bar(x=type_counts.index, y=type_counts.values, title="Maintenance Types")
            st.plotly_chart(fig, use_container_width=True)
            
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

# Error codes section
if error_file:
    st.subheader("📋 Common Error Codes")
    try:
        if error_file.name.endswith("xlsx"):
            err_df = pd.read_excel(error_file)
        else:
            err_df = pd.read_csv(error_file)
        
        error_search = st.text_input("🔍 Search error codes:", placeholder="Enter error
