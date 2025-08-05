import streamlit as st
import pandas as pd
import tempfile
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import base64

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
        try:
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
                        
                        try:
                            send_email(to=email, subject="Spare Parts Order", body=body)
                            st.success("📩 Order email sent!")
                        except Exception as e:
                            st.error(f"Error sending email: {str(e)}")
                        
                        # Display order summary
                        st.dataframe(order_df)
        except Exception as e:
            st.error(f"Error processing BOM file: {str(e)}")
    else:
        st.info("📄 Upload a BOM Excel file to see available parts")

with tab2:
    st.header("PDF Layout Viewer")
    
    if pdf_file:
        st.subheader("📄 Assembly Layout")
        
        # Add required imports at the top if not already imported
        try:
            import fitz  # PyMuPDF
            from PIL import Image
            import io
            
            # Convert PDF to images
            pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
            
            # Display PDF pages
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Page selection
                page_count = pdf_document.page_count
                if page_count > 1:
                    selected_page = st.selectbox("Select Page:", range(1, page_count + 1)) - 1
                else:
                    selected_page = 0
                    st.info(f"PDF has {page_count} page(s)")
                
                # Convert PDF page to image
                page = pdf_document.load_page(selected_page)
                
                # Get page dimensions and set zoom level
                page_rect = page.rect
                zoom = st.slider("Zoom Level", 0.5, 3.0, 1.0, 0.1)
                
                # Render page as image with annotations
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image for annotation overlay
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Add existing annotations to the image
                if 'pdf_annotations' in st.session_state:
                    from PIL import ImageDraw, ImageFont
                    draw = ImageDraw.Draw(img)
                    
                    current_page_annotations = [ann for ann in st.session_state.pdf_annotations if ann["page"] == selected_page]
                    for ann in current_page_annotations:
                        # Draw annotation marker
                        x, y = int(ann["x"]), int(ann["y"])
                        color = ann["color"]
                        
                        # Draw circle marker
                        radius = 8
                        draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color, outline="white", width=2)
                        
                        # Draw text label
                        try:
                            # Try to use a default font
                            font = ImageFont.load_default()
                        except:
                            font = None
                        
                        text = ann["text"][:20] + "..." if len(ann["text"]) > 20 else ann["text"]
                        draw.text((x+15, y-10), text, fill=color, font=font)
                
                # Convert back to bytes for display
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_data_with_annotations = img_bytes.getvalue()
                
                # Create clickable image using HTML and JavaScript
                img_width = int(page_rect.width * zoom)
                img_height = int(page_rect.height * zoom)
                
                # Encode image for HTML
                import base64
                img_b64 = base64.b64encode(img_data_with_annotations).decode()
                
                # Create HTML with clickable image
                html_code = f"""
                <div style="position: relative; display: inline-block;">
                    <canvas id="pdfCanvas" width="{img_width}" height="{img_height}" 
                            style="border: 1px solid #ccc; cursor: crosshair; max-width: 100%;">
                    </canvas>
                </div>
                
                <script>
                    const canvas = document.getElementById('pdfCanvas');
                    const ctx = canvas.getContext('2d');
                    
                    // Load and draw the PDF image
                    const img = new Image();
                    img.onload = function() {{
                        ctx.drawImage(img, 0, 0);
                    }};
                    img.src = 'data:image/png;base64,{img_b64}';
                    
                    // Store click coordinates
                    let clickX = null;
                    let clickY = null;
                    
                    canvas.addEventListener('click', function(e) {{
                        const rect = canvas.getBoundingClientRect();
                        const scaleX = canvas.width / rect.width;
                        const scaleY = canvas.height / rect.height;
                        
                        clickX = Math.round((e.clientX - rect.left) * scaleX);
                        clickY = Math.round((e.clientY - rect.top) * scaleY);
                        
                        // Visual feedback - draw temporary marker
                        ctx.save();
                        ctx.strokeStyle = '#FF0000';
                        ctx.fillStyle = '#FF0000';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.arc(clickX, clickY, 8, 0, 2 * Math.PI);
                        ctx.stroke();
                        ctx.fill();
                        ctx.restore();
                        
                        // Update Streamlit inputs
                        window.parent.postMessage({{
                            type: 'click_coordinates',
                            x: clickX,
                            y: clickY
                        }}, '*');
                        
                        console.log('Clicked at:', clickX, clickY);
                    }});
                </script>
                """
                
                st.components.v1.html(html_code, height=min(img_height + 50, 600))
                
                # Add annotation form with click coordinates
                st.subheader("📍 Add Annotations")
                
                # Initialize click coordinates in session state
                if 'click_x' not in st.session_state:
                    st.session_state.click_x = 100
                if 'click_y' not in st.session_state:
                    st.session_state.click_y = 100
                
                with st.expander("Add Part Annotation", expanded=True):
                    st.info("💡 Click on the PDF above to set annotation position, then fill in the details below")
                    
                    col_pos, col_text = st.columns([1, 2])
                    
                    with col_pos:
                        # Use session state for coordinates that can be updated by clicks
                        ann_x = st.number_input(
                            "X Position:", 
                            min_value=0, 
                            max_value=img_width, 
                            value=st.session_state.click_x,
                            key="ann_x_input"
                        )
                        ann_y = st.number_input(
                            "Y Position:", 
                            min_value=0, 
                            max_value=img_height, 
                            value=st.session_state.click_y,
                            key="ann_y_input"
                        )
                        
                        # Update session state when inputs change
                        st.session_state.click_x = ann_x
                        st.session_state.click_y = ann_y
                    
                    with col_text:
                        ann_text = st.text_input("Annotation Text:", placeholder="Enter part name or description")
                        ann_color = st.color_picker("Annotation Color", "#FF0000")
                        
                        # BOM part quick-select
                        if bom_file:
                            try:
                                bom_df = parse_bom(bom_file)
                                part_options = ["Custom Text"] + bom_df["Part Number"].tolist()
                                selected_quick_part = st.selectbox("Quick Select from BOM:", part_options)
                                
                                if selected_quick_part != "Custom Text":
                                    part_info = bom_df[bom_df["Part Number"] == selected_quick_part].iloc[0]
                                    ann_text = f"{selected_quick_part} - {part_info.get('Description', 'N/A')}"
                                    st.text_input("Auto-filled text:", value=ann_text, disabled=True)
                            except Exception as e:
                                st.error(f"Error loading BOM: {str(e)}")
                    
                    if st.button("📍 Add Annotation", type="primary") and ann_text:
                        # Store annotation in session state
                        if 'pdf_annotations' not in st.session_state:
                            st.session_state.pdf_annotations = []
                        
                        annotation = {
                            "page": selected_page,
                            "x": ann_x,
                            "y": ann_y,
                            "text": ann_text,
                            "color": ann_color
                        }
                        st.session_state.pdf_annotations.append(annotation)
                        st.success(f"Added annotation: {ann_text}")
                        st.rerun()
                
                # Display existing annotations for current page
                if 'pdf_annotations' in st.session_state:
                    current_page_annotations = [ann for ann in st.session_state.pdf_annotations if ann["page"] == selected_page]
                    if current_page_annotations:
                        st.subheader("📌 Current Page Annotations")
                        for i, ann in enumerate(current_page_annotations):
                            col_ann, col_edit, col_del = st.columns([3, 1, 1])
                            with col_ann:
                                st.write(f"• **{ann['text']}** at ({ann['x']}, {ann['y']})")
                            with col_edit:
                                if st.button("✏️", key=f"edit_ann_{i}", help="Edit annotation"):
                                    st.session_state.click_x = ann['x']
                                    st.session_state.click_y = ann['y']
                                    st.rerun()
                            with col_del:
                                if st.button("🗑️", key=f"del_ann_{i}", help="Delete annotation"):
                                    st.session_state.pdf_annotations.remove(ann)
                                    st.rerun()
            
            with col2:
                st.subheader("📋 PDF Information")
                
                # Display PDF metadata
                metadata = pdf_document.metadata
                st.write(f"**Title:** {metadata.get('title', 'N/A')}")
                st.write(f"**Author:** {metadata.get('author', 'N/A')}")
                st.write(f"**Pages:** {page_count}")
                st.write(f"**File size:** {len(pdf_file.getvalue()) / 1024:.1f} KB")
                
                # Page dimensions
                st.write(f"**Page size:** {page_rect.width:.0f} x {page_rect.height:.0f} pts")
                
                # Parts mapping section
                if bom_file:
                    st.subheader("🔗 Link to BOM Parts")
                    
                    try:
                        bom_df = parse_bom(bom_file)
                        
                        # Select part from BOM to link to PDF
                        part_options = bom_df["Part Number"].tolist()
                        selected_part = st.selectbox("Select BOM Part:", [""] + part_options)
                        
                        if selected_part:
                            part_info = bom_df[bom_df["Part Number"] == selected_part].iloc[0]
                            st.write(f"**Part:** {selected_part}")
                            st.write(f"**Description:** {part_info.get('Description', 'N/A')}")
                            
                            if 'Price' in part_info:
                                st.write(f"**Price:** ${part_info['Price']:.2f}")
                            
                            # Quick add to annotation
                            if st.button("📍 Add to Current View"):
                                if 'pdf_annotations' not in st.session_state:
                                    st.session_state.pdf_annotations = []
                                
                                annotation = {
                                    "page": selected_page,
                                    "x": 100,
                                    "y": 100,
                                    "text": f"{selected_part} - {part_info.get('Description', 'N/A')}",
                                    "color": "#FF0000"
                                }
                                st.session_state.pdf_annotations.append(annotation)
                                st.success(f"Added {selected_part} to annotations")
                                st.rerun()
                    
                    except Exception as e:
                        st.error(f"Error linking to BOM: {str(e)}")
                
                # Export annotations
                if 'pdf_annotations' in st.session_state and st.session_state.pdf_annotations:
                    st.subheader("💾 Export Annotations")
                    
                    # Convert annotations to DataFrame
                    ann_df = pd.DataFrame(st.session_state.pdf_annotations)
                    
                    # Download as CSV
                    csv = ann_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Annotations CSV",
                        data=csv,
                        file_name="pdf_annotations.csv",
                        mime="text/csv"
                    )
                    
                    # Clear all annotations
                    if st.button("🗑️ Clear All Annotations"):
                        st.session_state.pdf_annotations = []
                        st.rerun()
            
            pdf_document.close()
        
        except ImportError:
            st.error("Missing required libraries. Please install: `pip install PyMuPDF pillow`")
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
    
    else:
        st.info("📄 Upload a PDF layout file to view and annotate assembly drawings")
        st.write("**Features available after upload:**")
        st.write("• View PDF pages with zoom control")
        st.write("• Add interactive annotations")
        st.write("• Link BOM parts to PDF locations")
        st.write("• Export annotations as CSV")

with tab3:
    st.header("Quantity Management")
    
    if bom_file:
        try:
            bom_df = parse_bom(bom_file)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Inventory Overview")
                
                # Mock inventory data (you can connect this to actual inventory system)
                if 'Stock' not in bom_df.columns:
                    # Generate mock stock data based on dataframe length
                    stock_values = [50, 25, 100, 15, 30]
                    while len(stock_values) < len(bom_df):
                        stock_values.append(20)
                    bom_df['Stock'] = stock_values[:len(bom_df)]
                
                if 'Min_Stock' not in bom_df.columns:
                    # Generate mock min stock data
                    min_stock_values = [10, 5, 20, 5, 10]
                    while len(min_stock_values) < len(bom_df):
                        min_stock_values.append(5)
                    bom_df['Min_Stock'] = min_stock_values[:len(bom_df)]
                
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
        
        except Exception as e:
            st.error(f"Error processing quantities: {str(e)}")
    else:
        st.info("📄 Upload a BOM file to see quantity management")

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
            
            if status_filter:  # Only filter if user selected something
                filtered_maint = maint_df[maint_df["Status"].isin(status_filter)]
            else:
                filtered_maint = maint_df
            
            # Editable maintenance table
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
                            # Find the original index in the full list
                            original_idx = maint_df.index[maint_df.index == idx].tolist()[0]
                            st.session_state.maintenance_records[original_idx]["Status"] = new_status
                    
                    with col_actions:
                        if st.button("🗑️ Delete", key=f"del_{idx}"):
                            # Find the original index in the full list
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
    try:
        if error_file.name.endswith("xlsx"):
            err_df = pd.read_excel(error_file)
        else:
            err_df = pd.read_csv(error_file)
        
        # Search functionality for error codes
        error_search = st.text_input("🔍 Search error codes:", placeholder="Enter error code or description")
        if error_search:
            filtered_errors = err_df[err_df.apply(lambda row: error_search.lower() in str(row).lower(), axis=1)]
            st.dataframe(filtered_errors)
        else:
            st.dataframe(err_df)
    except Exception as e:
        st.error(f"Error reading error codes file: {str(e)}")
