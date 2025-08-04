import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

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

# --- Valor ROM Tests ---
# Shoulder
def valorShoulderExtract(data: dict, side: str = "L") -> pd.DataFrame:
    """
    Extract AvgMax and Score from 'Ang' section for shoulder metrics.
    Handles missing 'Score' values (e.g., for Shoulder Rotation Arc).

    Parameters:
    - data (dict): JSON with 'WorkoutMetrics'
    - side (str): 'L' or 'R'

    Returns:
    - pd.DataFrame with columns: Metric, Side, AvgMax, Score
    """
    metrics_to_extract = [
        "Shoulder ER (°)",
        "Shoulder IR (°)",
        "Shoulder Rotation Arc"  # This one may not have a 'Score'
    ]

    ang_data = data.get("WorkoutMetrics", {}).get("Ang", {})
    results = []

    for metric in metrics_to_extract:
        side_data = ang_data.get(metric, {}).get(side, {})
        avg_max = side_data.get("AvgMax")
        score = side_data.get("Score", None)  # Safely default to None if missing

        if avg_max is not None:
            results.append({
                "Metric": metric,
                "Side": side,
                "AvgMax": avg_max,
                "Score": score  # Will be None for "Shoulder Rotation Arc"
            })

    return pd.DataFrame(results)

# Ankle
def valorAnkleExtraction(data: dict, side: str = "L") -> pd.DataFrame:
    """
    Extract AvgMax and Score from Ankle DF (°) in the 'Ang' section of WorkoutMetrics.

    Parameters:
    - data (dict): JSON structure containing 'WorkoutMetrics'
    - side (str): 'L' or 'R'

    Returns:
    - pd.DataFrame with columns: Metric, Side, AvgMax, Score
    """
    df_data = data.get("WorkoutMetrics", {}).get("Ang", {}).get("Ankle DF (°)", {}).get(side, {})
    avg_max = df_data.get("AvgMax")
    score = df_data.get("Score")

    if avg_max is None:
        return pd.DataFrame()

    return pd.DataFrame([{
        "Metric": "Ankle DF (°)",
        "Side": side,
        "AvgMax": avg_max,
        "Score": score
    }])

# Valor Extraction Utility
def ValorExtraction(data: dict) -> pd.DataFrame:
    """
    Extract AvgMax and Score for all joints and sides from 'Ang' in a Hip Hinge test.

    Parameters:
    - data (dict): JSON structure with 'WorkoutMetrics'

    Returns:
    - pd.DataFrame with columns: Metric, Side, AvgMax, Score
    """
    ang_data = data.get("WorkoutMetrics", {}).get("Ang", {})
    results = []

    for metric, side_dict in ang_data.items():
        for side in side_dict:  # Handles 'L', 'R', 'F', 'B'
            values = side_dict.get(side, {})
            avgmax = values.get("AvgMax")
            score = values.get("Score")

            if avgmax is not None:
                results.append({
                    "Metric": metric,
                    "Side": side,
                    "AvgMax": avgmax,
                    "Score": score
                })

    return pd.DataFrame(results)

def ScoreChart(score: float, show: bool = True, key: str = None) -> None:
    # Example: replace this with your actual value
    score = score  # assuming this is a float between 0–100

    # Determine color
    if score > 85:
        color = "#00A651"  # green
    elif score < 75:
        color = "#FF4B4B"  # red
    else:
        color = "#FFC107"  # amber


    # Create plotly bar chart
    fig = go.Figure(go.Bar(
        x=[""],
        y=[score],
        marker_color=color,
        width=[0.4],
        text=[str(int(round(score)))],
        textfont=dict(color="black", size=14),  # Text label color
        textposition="outside"
    ))

    # Add threshold lines at y = 70 and y = 85
    fig.update_layout(
        shapes=[
            # Line at y=70
            dict(
                type="line",
                x0=-0.5, x1=0.5,  # span entire bar width
                y0=70, y1=70,
                line=dict(color="#FFC107", width=2, dash="dash")
            ),
            # Line at y=85
            dict(
                type="line",
                x0=-0.5, x1=0.5,
                y0=85, y1=85,
                line=dict(color="#00A651", width=2, dash="dash")
            ),
        ],
        yaxis=dict(
            range=[0, 100]
        ),
        xaxis=dict(
            showticklabels=False
        ),
        height=175,
        margin=dict(t=5, l=10, r=10, b=5),
        showlegend=False
    )

    # Show y axis tick
    if show:
        fig.update_yaxes(tickfont=dict(size=14, color="black"))
    else:
        fig.update_yaxes(showticklabels=False)

    st.plotly_chart(fig, use_container_width=True, key=key)

#-----------------------------------------------------------------------------#
#----- ROM Test DataFrames -----
#------------------------------------------------------------------------------#
# Hip Hinge Ranges
HipHingeRanges = pd.DataFrame({
        "Metric": ["Hip ER (°)", "Hip Ext. (°)", "Hip Flex. (°)", "Hip IR (°)",  "Knee Flex. (°)", "Shin Angle (°)", "Torso Ext. (°)"],
        "Min": [0, 0, 70, 0, 15, 0, 0],
        "Max": [10, 5, 110, 180, 40, 10, 20],
        "Header": ["Hip ER (0°-10°)", "Hip Ext. (0°-5°)", "Hip Flex. (70°-110°)", "Hip IR (0°-180°)", "Knee Flex. (15°-40°)", "Shin Angle (0°-10°)", "Torso Ext. (0°-20°)"]
        })

# Shoulder Ranges
ShoulderRanges = pd.DataFrame({
        "Metric": ["Shoulder ER (°)", "Shoulder IR (°)", "Shoulder Rotation Arc"],
        "Min": [75, 70, 145],
        "Max": [105, 100, 205],
        "Header": ["Shoulder ER (75°-105°)", "Shoulder IR (70°-100°)", "Shoulder Rotation Arc (145°-205°)"]
        })

# Ankle Ranges
AnkleRanges = pd.DataFrame({
        "Metric": ["Ankle DF (°)", "Ankle PF (°)", "Shin Angle (°)"],
        "Min": [20, 0, 0],
        "Max": [45, 5, 40],
        "Header": ["Ankle DF (20°-45°)", "Ankle PF (0°-5°)", "Shin Angle (0°-40°)"]
})
