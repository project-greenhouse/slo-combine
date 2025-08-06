import pandas as pd
from pyparsing import col
import streamlit as st
from functions.db_client import GetSupaTableCached
from hdforce import AuthManager, GetTests, GetAthletes
from functions.func_swift import ProAgilityData, Sprint40Data, VertJumpData, BroadJumpData
from functions.func_player_info import AthleteSignUpData
import views.valor_data as valor


#-----Initial Auth and Data Calls-----
# Authentication for Hawking Dynamic -----
AuthManager(authMethod="manual", refreshToken=st.secrets["HD_TOKEN"])

# Authnentication for Valor -----
ValorTokenDF = valor.get_jwt_token()
if not ValorTokenDF.empty:
    valorIDToken = ValorTokenDF['id_token'].values[0]
    valorAccessToken = ValorTokenDF['access_token'].values[0]

##-----Get Supabase Tables-----
#  Force Plate Percentiles-----
try:
    ForcePlatePercentiles = pd.DataFrame(GetSupaTableCached("ForcePlatePercentiles"))
except Exception as e:
    st.error(f"Failed to load Force Plate Percentiles table: {e}")
    ForcePlatePercentiles = pd.DataFrame()

# Combine Data Percentiles -----
try:
    CombinePercentiles = pd.DataFrame(GetSupaTableCached("CombinePercentiles"))
except Exception as e:
    st.error(f"Failed to load Combine Percentiles table: {e}")
    CombinePercentiles = pd.DataFrame()

# Athlete Sign Up Data -----
try:
    dfAthleteSignUp = AthleteSignUpData()
except Exception as e:
    st.error(f"Failed to load athlete sign up worksheet: {e}")
    raise
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
    dfValorAthletes = valor.ValorAthletes(token=valorIDToken)
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

#-----Athlete Info Functions-----

# Athlete Info Data -----
def AthleteInfoData(athlete: str=None, athlete_data=dfAthleteSignUp):
    """
    Fetches Athlete Info data for a specific athlete.
    Args:
        athlete (str): Name of the athlete to filter by.
        athlete_data (pd.DataFrame): DataFrame containing Athlete Info data.
    Returns:
        pd.DataFrame: Filtered DataFrame for the specified athlete.
    """
    if athlete and not athlete_data.empty:
        df = athlete_data[athlete_data["Name"] == athlete]
        return df
    return pd.DataFrame()  # Return empty DataFrame if no athlete is selected or data is empty
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
        # Function to get external percentile using interpolation
        def get_external_percentile(value, metric_col):
            import numpy as np
            ref_df = ForcePlatePercentiles.dropna(subset=[metric_col, "Percentile"]).sort_values(by=metric_col)
            if ref_df.empty:
                return None
            # Use interpolation to get exact percentile for the athlete's value
            percentile = np.interp(value, ref_df[metric_col].values, ref_df["Percentile"].values)
            return percentile
        
        # Create DataFrame with all data first to calculate population-based percentiles
        data = pd.DataFrame({
            "Date-Time": pd.to_datetime(cmj_data["timestamp"], unit='s').dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Test Type": cmj_data["segment"],
            "Athlete Name": cmj_data["athlete_name"],
            "Jump Height (in)": cmj_data["jump_height_m"] * 39.3701,  # Convert meters to inches
            "Jump Height SLO Rank": cmj_data["jump_height_m"].rank(method='average', ascending=True, na_option='keep', pct=True) * 100,
            "Jump Height Elite Rank": cmj_data["jump_height_m"].apply(lambda x: get_external_percentile(x, "JumpHeight")),
            "mRSI": cmj_data["mrsi"],
            "mRSI SLO Rank": cmj_data["mrsi"].rank(method='average', ascending=True, na_option='keep', pct=True) * 100,
            "mRSI Elite Rank": cmj_data["mrsi"].apply(lambda x: get_external_percentile(x, "mRSI")),
            "Peak Rel Prop Power (W/kg)": cmj_data["peak_relative_propulsive_power_w_kg"],
            "Peak Rel Power SLO Rank": cmj_data["peak_relative_propulsive_power_w_kg"].rank(method='average', ascending=True, na_option='keep', pct=True) * 100,
            "Peak Rel Power Elite Rank": cmj_data["peak_relative_propulsive_power_w_kg"].apply(lambda x: get_external_percentile(x, "PeakRelPropPower")),
            "Braking Asymmetry": cmj_data["lr_braking_impulse_index"].round(0),
            "Asymmetry SLO Rank": (1 - cmj_data["lr_braking_impulse_index"].rank(method='average', ascending=False, na_option='keep', pct=True)) * 100,  # Lower asymmetry is better
            "Asymmetry Elite Rank": cmj_data["lr_braking_impulse_index"].apply(lambda x: get_external_percentile(x, "BrakingAsymm")),
        })

        # Now filter for the specific athlete
        athlete_data = data[data["Athlete Name"] == athlete]
        
        # Remove the athlete name column since it's not needed in the output
        athlete_data = athlete_data.drop(columns=["Athlete Name"])
        
        return athlete_data
    else:
        return pd.DataFrame()  # Return empty DataFrame if no athlete is selected or data is empty

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

# Define updated versions of the swiftSprint and proAgility functions with percentile logic
def swiftSprint(data, player_name):
    external_percentiles = CombinePercentiles

    data.columns = data.columns.str.strip()
    split_time_pivot = data.pivot(index=["Name", "ActivityIdentifier"], columns="Distance", values="Split")
    total_time_pivot = data.pivot(index=["Name", "ActivityIdentifier"], columns="Distance", values="Total")
    split_time_pivot.columns = [f"split_time_{int(dist)}yd" for dist in split_time_pivot.columns]
    total_time_pivot.columns = [f"total_time_{int(dist)}yd" for dist in total_time_pivot.columns]
    df_all = pd.concat([split_time_pivot, total_time_pivot], axis=1).reset_index()

    df_all["perc_40yd"] = (1 - df_all["total_time_40yd"].rank(pct=True)) * 100
    df_all["perc_10yd"] = (1 - df_all["total_time_10yd"].rank(pct=True)) * 100

    def get_external_percentile(time_val, col):
        #.reset_index(drop=True)
        match = ref_df[ref_df[col] >= time_val]
        if match.empty:
            return 0
        return match.iloc[0]["Percentile"]

    df_out = df_all[df_all["Name"] == player_name].copy()

    # Get best rep for 40yd
    best_rep = df_out["total_time_40yd"].min()

    # filter to best rep
    df_out = df_out[df_out["total_time_40yd"] == best_rep].copy()

    # Get external percentile
    ref_df = external_percentiles.sort_values(by="Sprint40", ascending=True)

    # Match the best rep to the reference DataFrame
    match = ref_df[ref_df["Sprint40"] >= best_rep]
    
    if match.empty:
        df_out["ext_perc_40yd"] = 0
    else:
        df_out["ext_perc_40yd"] = match.iloc[0]["Percentile"]
   
    return df_out


#--------------------------------------#

# Pro Agility -----

## Individual Pro Agility Data
def proAgility(data, player_name):
    external_percentiles = CombinePercentiles

    data.columns = data.columns.str.strip()
    # Check if the player exists in the data
    if data.empty:
        return pd.DataFrame()

    split_time_pivot = data.pivot(index=["Name", "ActivityIdentifier"], columns="Distance", values="Split")
    total_time_pivot = data.pivot(index=["Name", "ActivityIdentifier"], columns="Distance", values="Total")
    split_time_pivot.columns = [f"split_time_{int(s)}yd" for s in split_time_pivot.columns]
    total_time_pivot.columns = [f"total_time_{int(s)}yd" for s in total_time_pivot.columns]
    df_out = pd.concat([total_time_pivot, split_time_pivot], axis=1).reset_index()
    df_out["5_0_5_time"] = df_out["total_time_20yd"] - df_out["total_time_10yd"]
    df_out = df_out.rename(columns={"total_time_20yd": "total_time"})
    df_out["Trial"] = range(1, len(df_out) + 1)

    print(df_out)
    # Only calculate percentiles if we have the total_time column
    if "total_time" in df_out.columns:
        df_out["perc_proAgility"] = (1 - df_out["total_time"].rank(pct=True)) * 100
    
        df_out = df_out[df_out["Name"] == player_name].copy()
        print(df_out["total_time"])

        # Get Fastest Rep
        best_rep = df_out["total_time"].min()

        # filter to best rep
        df_out = df_out[df_out["total_time"] == best_rep].copy()

        # Get external percentile
        ref_df = external_percentiles.sort_values(by="ProAgility", ascending=True)

        # Match the best rep to the reference DataFrame
        match = ref_df[ref_df["ProAgility"] >= best_rep]

        print(match)
        if match.empty:
            df_out["ext_perc_proAgility"] = 0
        else:
            df_out["ext_perc_proAgility"] = match.iloc[0]["Percentile"]

    return df_out

#----------------------------------------------------------------------------#

#-----Vertical Jump Data Functions-----

## Individual Vertical Jump Data
def verticalJump(player_name=None):
    data = dfVerticalJump

    # Calculate percentile ranks for all values in BestBroadJump then filter for the value of player_name
    if player_name and not data.empty:
        data["VerticalJump"] = data["VerticalJump"].astype(float)
        data["perc_vert"] = (data["VerticalJump"].rank(pct=True)) * 100
        data["VerticalJump"] = data["VerticalJump"].round(1)
    else:
        return pd.DataFrame()
    
    if player_name:
        df = data[data["Name"] == player_name].copy()
    else:
        return pd.DataFrame()

    # Normalize column names
    df.columns = df.columns.str.strip()
    df_all = df[["Name", "VerticalJump", "perc_vert"]].copy()
    # Calculate external percentiles
    if df_all.empty:
        return pd.DataFrame()
    
    external_percentiles = CombinePercentiles

    def get_external_percentile(val, col):
        ref_df = external_percentiles.sort_values(by=col, ascending=True).reset_index(drop=True)
        match = ref_df[ref_df[col] >= val]
        if match.empty:
            return 100
        return match.iloc[0]["Percentile"]
    
    df_out = df_all[df_all["Name"] == player_name].copy()
    df_out["ext_perc_vert"] = df_out["VerticalJump"].apply(lambda x: get_external_percentile(x, "VerticalJump"))

    return df_out

#--------------------------------------#

#-----Broad Jump Data Functions-----

## Individual Broad Jump Data
def broadJump(player_name=None):
    data = dfBroadJump

    # Calculate percentile ranks for all values in BestBroadJump then filter for the value of player_name
    if player_name and not data.empty:
        data["BestBroadJump"] = data["BestBroadJump"].astype(float)
        data["perc_broad"] = (data["BestBroadJump"].rank(pct=True)) * 100
        data["BestBroadJump"] = data["BestBroadJump"].round(2)
    else:
        return pd.DataFrame()

    if player_name:
        df = data[data["Name"] == player_name].copy()
    else:
        return pd.DataFrame()

    # Normalize column names
    df.columns = df.columns.str.strip()
    df_all = df[["Name", "BestBroadJump", "perc_broad"]].copy()

    external_percentiles = CombinePercentiles

    def get_external_percentile(val, col):
        ref_df = external_percentiles.sort_values(by=col, ascending=True).reset_index(drop=True)
        match = ref_df[ref_df[col] >= val]
        if match.empty:
            return 100
        return match.iloc[0]["Percentile"]
    
    df_out = df_all[df_all["Name"] == player_name].copy()
    df_out["ext_perc_broad"] = df_out["BestBroadJump"].apply(lambda x: get_external_percentile(x, "BroadJump"))

    return df_out

#----------------------------------------------------------------------------#
