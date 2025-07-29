import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib

#-----Gogglesheets Connection-----
# My Gsheets connection
def GetGsheet(sheet_name: str=None):
    """
    Creates a connection object for Google Sheets.
    Returns:
        GSheetsConnection: A connection object to interact with Google Sheets.
    """
    url = st.secrets["SHEET_URL"]
    df = pd.read_csv(f"{url}{sheet_name}")
    return df


# --- Store Uploaded CSV Data with Named Caching ---
"""
This function stores the uploaded CSV data in Streamlit session state with a user-defined name.
It reads the CSV file, stores it with a name, and displays its content.
It also provides feedback to the user about the upload status.

Args:
    uploaded_file: The uploaded file object from Streamlit
    dataset_name: Optional name for the dataset. If None, auto-generates based on filename and timestamp

Returns:
    pd.DataFrame: The data read from the uploaded CSV file.
"""
def store_uploaded_data(uploaded_file, dataset_name=None) -> pd.DataFrame:
    if uploaded_file is not None:
        # Read the CSV file
        data = pd.read_csv(uploaded_file)
        
        # Generate dataset name if not provided
        if dataset_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = uploaded_file.name.replace('.csv', '')
            dataset_name = f"{filename}_{timestamp}"
        
        # Store in session state for easy access
        if 'uploaded_datasets' not in st.session_state:
            st.session_state.uploaded_datasets = {}
        
        st.session_state.uploaded_datasets[dataset_name] = {
            'data': data,
            'filename': uploaded_file.name,
            'upload_time': datetime.now(),
            'shape': data.shape
        }
        
        # Display the data and success message
        st.write(f"**Dataset Name:** `{dataset_name}`")
        st.write(f"**Shape:** {data.shape[0]} rows, {data.shape[1]} columns")
        st.write(data)
        st.success(f"File uploaded successfully and cached as '{dataset_name}'!")
        
        return data
    else:
        st.warning("Please upload a CSV file.")
        return None

def get_cached_dataset(dataset_name: str) -> pd.DataFrame:
    """
    Retrieve a cached dataset by name.
    
    Args:
        dataset_name: The name of the cached dataset
        
    Returns:
        pd.DataFrame: The cached dataset or None if not found
    """
    if 'uploaded_datasets' in st.session_state:
        if dataset_name in st.session_state.uploaded_datasets:
            return st.session_state.uploaded_datasets[dataset_name]['data']
    return None

def list_cached_datasets() -> dict:
    """
    List all cached datasets with their metadata.
    
    Returns:
        dict: Dictionary of dataset names and their metadata
    """
    if 'uploaded_datasets' in st.session_state:
        return {name: {k: v for k, v in info.items() if k != 'data'} 
                for name, info in st.session_state.uploaded_datasets.items()}
    return {}

def delete_cached_dataset(dataset_name: str) -> bool:
    """
    Delete a cached dataset by name.
    
    Args:
        dataset_name: The name of the dataset to delete
        
    Returns:
        bool: True if deleted successfully, False if not found
    """
    if 'uploaded_datasets' in st.session_state:
        if dataset_name in st.session_state.uploaded_datasets:
            del st.session_state.uploaded_datasets[dataset_name]
            return True
    return False

def clear_all_cached_datasets():
    """Clear all cached datasets from session state."""
    if 'uploaded_datasets' in st.session_state:
        st.session_state.uploaded_datasets = {}
