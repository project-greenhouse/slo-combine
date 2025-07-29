import pandas as pd
import streamlit as st
from hdforce import AuthManager, GetTests, GetAthletes
from functions.func_swift import ProAgilityData, Sprint40Data, VertJumpData, BroadJumpData
from functions.func_valor import get_jwt_token, ValorAthletes


#-----Initial Auth and Data Calls-----
# Authentication for Hawking Dynamic -----
AuthManager(authMethod="manual", refreshToken=st.secrets["HD_TOKEN"])

# Authnentication for Valor -----
valorToken = get_jwt_token()

#-----
## Pro Agility CSV Data
try:
    dfProAgility = ProAgilityData()
except Exception as e:
    st.error(f"Failed to load pro-agility worksheet: {e}")
    raise
#-----
## Sprint CSV Data
try:
    dfSprint = Sprint40Data()
except Exception as e:
    st.error(f"Failed to load sprint40 worksheet: {e}")
    raise
#-----
## Vertical Jump -----
try:
    dfVerticalJump = VertJumpData()
except Exception as e:
    st.error(f"Failed to load standing-vert worksheet: {e}")
    raise
#-----
## Broad Jump -----
try:
    dfBroadJump = BroadJumpData()
except Exception as e:
    st.error(f"Failed to load broad-jump worksheet: {e}")
    raise

#-----Roster Management-----
# HD Athletes -----
HawkinRoster = GetAthletes()
HawkinRoster["Name"] = HawkinRoster["name"]
HawkinAthletes = HawkinRoster  # <-- keep full DataFrame

# Valor Athletes -----
try:
    dfValorAthletes = ValorAthletes(token=valorToken)
except Exception as e:
    st.error(f"Failed to load Valor athletes: {e}")
    dfValorAthletes = pd.DataFrame()  # Fallback to empty DataFrame


SprintAthletes = dfSprint  # <-- keep full DataFrame
ProAgilAthletes = dfProAgility
VerticalJumpAthletes = dfVerticalJump
BroadJumpAthletes = dfBroadJump
Valor_Athletes = dfValorAthletes

def rosterCheck():
    hdnames = HawkinAthletes["Name"].unique().tolist()
    sprintnames = SprintAthletes["Name"].unique().tolist()
    proagilnames = ProAgilAthletes["Name"].unique().tolist()
    verticalnames = VerticalJumpAthletes["Name"].unique().tolist()
    broadnames = BroadJumpAthletes["Name"].unique().tolist()
    valor_names = Valor_Athletes["Name"].unique().tolist()

    # Find the maximum length among all lists
    max_count = max(len(hdnames), len(sprintnames), len(proagilnames), 
                   len(verticalnames), len(broadnames), len(valor_names))

    # Pad each list with "NA" to match the maximum length
    hdnames_padded = hdnames + ["NA"] * (max_count - len(hdnames))
    sprintnames_padded = sprintnames + ["NA"] * (max_count - len(sprintnames))
    proagilnames_padded = proagilnames + ["NA"] * (max_count - len(proagilnames))
    verticalnames_padded = verticalnames + ["NA"] * (max_count - len(verticalnames))
    broadnames_padded = broadnames + ["NA"] * (max_count - len(broadnames))
    valor_names_padded = valor_names + ["NA"] * (max_count - len(valor_names))

    # Create and return a DataFrame with each column's values sorted alphabetically
    roster_df = pd.DataFrame({
        "Hawkin": sorted(hdnames_padded),
        "Sprint": sorted(sprintnames_padded),
        "ProAgil": sorted(proagilnames_padded),
        "VerticalJump": sorted(verticalnames_padded),
        "BroadJump": sorted(broadnames_padded),
        "Valor": sorted(valor_names_padded)
    })
    
    return roster_df
#-----Clean Roster-----
# Get single athlete list from SprintAthletes, HawkinAthletes, ProAgilAthletes, VerticalJumpAthletes, and BroadJumpAthletes with no duplicates
def clean_roster():

    # Combine all names
    all_names = []

    for df in [SprintAthletes, HawkinAthletes, ProAgilAthletes, VerticalJumpAthletes, BroadJumpAthletes]:
        if isinstance(df, pd.DataFrame) and "Name" in df.columns:
            all_names.extend(df["Name"].dropna().unique().tolist())

    roster = list(set(all_names))

    # Helper to safely get ID
    def get_id(df, name, id_col):
        if isinstance(df, pd.DataFrame) and "Name" in df.columns:
            match = df[df["Name"] == name]
            if not match.empty:
                return match[id_col].values[0]
        return None

    hawkin_ids = {athlete: get_id(HawkinAthletes, athlete, "id") for athlete in roster}
    proagil_ids = {athlete: get_id(ProAgilAthletes, athlete, "AthleteId") for athlete in roster}
    sprint_ids = {athlete: get_id(SprintAthletes, athlete, "AthleteId") for athlete in roster}
    valor_ids = {athlete: get_id(Valor_Athletes, athlete, "ValorID") for athlete in roster}

    roster_df = pd.DataFrame({
        "Name": roster,
        "HawkinID": [hawkin_ids.get(name) for name in roster],
        "ProAgilID": [proagil_ids.get(name) for name in roster],
        "SprintID": [sprint_ids.get(name) for name in roster],
        "ValorID": [valor_ids.get(name) for name in roster]
    })

    return roster_df

#----------------------------------------------------------------------------#

#-----Hawking Data Functions-----

# Get CMJ Tests -----
@st.cache_data(ttl=3600)  # 3600 seconds = 60 minutes
def HawkinCMJ(typeId: str="CMJ", fromDate: str="2025-07-23", toDate: str="2025-07-27"):
    """
    Fetches CMJ tests from Hawking Dynamic.
    Args:
        typeId (str): Type of test to fetch, default is "CMJ".
        fromDate (str): Start date for fetching tests.
        toDate (str): End date for fetching tests.
    """
    return GetTests(typeId=typeId, from_=fromDate, to_=toDate)

# Filter Athlete CMJ -----
def AthleteCMJ(athlete: str, cmj_data = HawkinCMJ()):
    """
    Filters CMJ data for a specific athlete.
    Args:
        athlete (str): Name of the athlete to filter by.
        cmj_data (pd.DataFrame): DataFrame containing CMJ data.
    Returns:
        pd.DataFrame: Filtered DataFrame for the specified athlete.
    """
    if athlete and not cmj_data.empty:
        df = cmj_data[cmj_data["athlete_name"] == athlete]
        data = pd.DataFrame({
            "Date-Time": pd.to_datetime(df["timestamp"], unit='s').dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Test Type": df["segment"],
            "Jump Height (in)": df["jump_height_m"] * 39.3701,  # Convert meters to inches
            "mRSI": df["mrsi"],
            "Peak Rel Prop Power (W/kg)": df["peak_relative_propulsive_power_w_kg"],
            "Braking Asymmetry": df["lr_braking_impulse_index"].round(0)
        })
        return data
    else:
        df = cmj_data
        return df # Return empty DataFrame if no athlete is selected or data is empty

# Get MR Tests -----
@st.cache_data(ttl=3600)  # 3600 seconds = 60 minutes
def HawkinMR(typeId: str="MR", fromDate: str="2025-07-23", toDate: str="2025-07-27"):
    """
    Fetches MR tests from Hawking Dynamic.
    Args:
        typeId (str): Type of test to fetch, default is "MR".
        fromDate (str): Start date for fetching tests.
        toDate (str): End date for fetching tests.
    """
    return GetTests(typeId=typeId, from_=fromDate, to_=toDate)

# Filter Athlete MR -----
def AthleteMR(athlete: str, mr_data = HawkinMR()):
    """
    Filters MR data for a specific athlete.
    Args:
        athlete (str): Name of the athlete to filter by.
        mr_data (pd.DataFrame): DataFrame containing MR data.
    Returns:
        pd.DataFrame: Filtered DataFrame for the specified athlete.
    """
    if athlete and not mr_data.empty:
        df = mr_data[mr_data["athlete_name"] == athlete]
        data = pd.DataFrame({
            "Date-Time": pd.to_datetime(df["timestamp"], unit='s').dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Test Type": df["segment"],
            "Number of Jumps": df["number_of_jumps_count"],
            "Avg Jump Height (in)": df["avg_jump_height_m"]* 39.3701,  # Convert meters to inches
            "Peak Jump Height (in)": df["peak_jump_height_m"] * 39.3701,  # Convert meters to inches
            "Avg RSI": df["avg_rsi"],
            "Peak RSI": df["peak_rsi"]
        })
        return data
    return pd.DataFrame()  # Return empty DataFrame if no athlete is selected or data is empty
#----------------------------------------------------------------------------#

#------Swift Data Functions------

# 40-Yard Sprint -----

## Individual Sprint Data
def swiftSprint(data=dfSprint, player_name=None):
    if player_name:
        df = data[data["Name"] == player_name].copy()
    else:
        return pd.DataFrame()

    # Normalize column names
    df.columns = df.columns.str.strip()

    # Pivot time and velocity values separately
    time_pivot = df.pivot(index="ActivityIdentifier", columns="Distance", values="Split")
    velocity_pivot = df.pivot(index="ActivityIdentifier", columns="Distance", values="Velocity")

    # Rename columns to reflect split distances
    time_pivot.columns = [f"time_{int(dist)}yd" for dist in time_pivot.columns]
    velocity_pivot.columns = [f"velocity_{int(dist)}yd" for dist in velocity_pivot.columns]

    # Combine the pivoted tables
    df_out = pd.concat([time_pivot, velocity_pivot], axis=1).reset_index()

    df_out.insert(0, "Name", player_name)
    # Replace 'ActivityIdentifier' with 'Name' for clarity and add "Trial #" by index
    df_out["Trial"] = df_out.index + 1
    # Remove 0yd time and velocity columns, and remove activity identifier
    df_out = df_out.loc[:, ~df_out.columns.str.endswith("_0yd")]
    df_out = df_out.loc[:, ~df_out.columns.str.contains("ActivityIdentifier")]
    # Reorder columns to have Name and Trial first
    df_out = df_out[["Name", "Trial"] + [col for col in df_out.columns if col not in ["Name", "Trial"]]]

    return df_out

#--------------------------------------#

# Pro Agility -----

## Individual Pro Agility Data
def proAgility(data=dfProAgility, player_name=None):
    if player_name:
        df = data[data["Name"] == player_name].copy()
    else:
        return pd.DataFrame()

    # Normalize column names
    df.columns = df.columns.str.strip()

    # Pivot split Time and Velocity
    time_pivot = df.pivot(index="ActivityIdentifier", columns="Distance", values="Split")
    velocity_pivot = df.pivot(index="ActivityIdentifier", columns="Distance", values="Velocity")

    # Rename columns
    time_pivot.columns = [f"time_{int(s)}yd" for s in time_pivot.columns]
    velocity_pivot.columns = [f"velocity_{int(s)}yd" for s in velocity_pivot.columns]

    # Combine both
    df_out = pd.concat([time_pivot, velocity_pivot], axis=1)

    # Add total time from 20yd split (or rename for clarity)
    if "time_20yd" in df_out.columns:
        df_out = df_out.rename(columns={"time_20yd": "total_time"})

    df_out = df_out.reset_index()
    df_out.insert(0, "Name", player_name)
    # Replace 'ActivityIdentifier' with 'Name' for clarity and add "Trial #" by index
    df_out["Trial"] = df_out.index + 1
    # Remove 0yd time and velocity columns, and remove activity identifier
    df_out = df_out.loc[:, ~df_out.columns.str.contains("0yd")]
    df_out = df_out.loc[:, ~df_out.columns.str.contains("ActivityIdentifier")]
    # Reorder columns to have Name and Trial first
    df_out = df_out[["Name", "Trial"] + [col for col in df_out.columns if col not in ["Name", "Trial"]]]

    return df_out

#----------------------------------------------------------------------------#

#-----Vertical Jump Data Functions-----

## Individual Vertical Jump Data
def verticalJump(data=dfVerticalJump, player_name=None):
    if player_name:
        df = data[data["Name"] == player_name].copy()
    else:
        return pd.DataFrame()

    # Normalize column names
    df.columns = df.columns.str.strip()

    return df

#--------------------------------------#

#-----Broad Jump Data Functions-----

## Individual Broad Jump Data
def broadJump(data=dfBroadJump, player_name=None):
    if player_name:
        df = data[data["Name"] == player_name].copy()
    else:
        return pd.DataFrame()

    # Normalize column names
    df.columns = df.columns.str.strip()

    return df

#----------------------------------------------------------------------------#
