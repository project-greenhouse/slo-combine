import streamlit as st

from forms.form_data_upload import csv_upload_form, show_cached_datasets
from functions.utility import list_cached_datasets, get_cached_dataset

st.title("Vertical Jump Data", anchor=False)

# --- CSV UPLOAD FORM ---
@st.dialog(title="Upload Vertical Jump Data")
def upload_vertical_jump_data():
    csv_upload_form()

# --- Page Content ---
st.subheader("Upload Vertical Jump Data", anchor=False)
if st.button("Enter Data"):
    upload_vertical_jump_data()

# Display Uploaded Data
st.subheader("Uploaded Data", anchor=False)

# Check if there are any cached datasets
cached_datasets = list_cached_datasets()

if cached_datasets:
    # Create a selectbox to choose which dataset to display
    dataset_names = list(cached_datasets.keys())
    selected_dataset = st.selectbox(
        "Select a dataset to display:",
        options=dataset_names,
        index=len(dataset_names) - 1  # Default to most recent upload
    )
    
    if selected_dataset:
        # Get and display the selected dataset
        data = get_cached_dataset(selected_dataset)
        
        if data is not None:
            # Display dataset information
            dataset_info = cached_datasets[selected_dataset]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", dataset_info['shape'][0])
            with col2:
                st.metric("Columns", dataset_info['shape'][1])
            with col3:
                st.metric("Upload Time", dataset_info['upload_time'].strftime('%H:%M'))
            
            # Display the actual data
            st.dataframe(data, use_container_width=True, hide_index=True)
            
            # Optional: Add some basic statistics if it looks like vertical jump data
            if any(col.lower() in ['jump', 'height', 'vertical', 'distance'] for col in data.columns):
                st.subheader("Quick Stats")
                numeric_columns = data.select_dtypes(include=['number']).columns
                if len(numeric_columns) > 0:
                    st.write(data[numeric_columns].describe())
        else:
            st.error("Could not load the selected dataset.")
    
    # Show cached datasets management section
    with st.expander("Manage Cached Datasets"):
        show_cached_datasets()
        
else:
    st.info("No data uploaded yet. Click 'Enter Data' above to upload a CSV file.")
