import streamlit as st
import pandas as pd
from functions.utility import store_uploaded_data, list_cached_datasets, get_cached_dataset, delete_cached_dataset

def csv_upload_form():
    with st.form("data_upload"):
        st.write("Upload your CSV files here.")
        file = st.file_uploader("Choose a CSV file", type="csv")
        
        # Optional dataset name input
        dataset_name = st.text_input(
            "Dataset Name (optional)", 
            placeholder="Leave empty for auto-generated name",
            help="Provide a custom name for easy access later"
        )
        
        submit_button = st.form_submit_button("Upload", icon=":material/upload_file:")

        if submit_button and file is not None:
            if dataset_name.strip():
                store_uploaded_data(file, dataset_name.strip())
            else:
                store_uploaded_data(file)
            
            # Auto-close dialog after successful upload
            st.success("Upload successful! Closing dialog...")
            st.rerun()

def show_cached_datasets():
    """Display a sidebar or section showing all cached datasets"""
    st.subheader("Cached Datasets")
    
    cached_datasets = list_cached_datasets()
    
    if cached_datasets:
        for name, info in cached_datasets.items():
            with st.expander(f"📊 {name}"):
                st.write(f"**Filename:** {info['filename']}")
                st.write(f"**Upload Time:** {info['upload_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**Shape:** {info['shape'][0]} rows, {info['shape'][1]} columns")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"View Data", key=f"view_{name}"):
                        data = get_cached_dataset(name)
                        st.write(data)
                with col2:
                    if st.button(f"Delete", key=f"delete_{name}"):
                        if delete_cached_dataset(name):
                            st.success(f"Deleted {name}")
                            st.rerun()
    else:
        st.info("No datasets cached yet. Upload a CSV file to get started!")
