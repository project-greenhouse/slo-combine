# supabase.py
"""
This module initializes a Supabase client using environment variables for the project URL and key.
"""

# Import necessary libraries
import pandas as pd
import streamlit as st
from supabase import create_client

# Supabase Project URL and Key
# Pull credentials from secrets.toml
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Create client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get Database Tables
def GetSupaTable(table_name: str, *args, **kwargs):
    """
    Get a specific table from Supabase with optional filtering and query operations.
    
    Args:
        table_name (str): The name of the table to query
        *args: Additional positional arguments (currently unused but available for future extension)
        **kwargs: Keyword arguments for Supabase query operations such as:
            - select: Columns to select (default: "*")
            - eq: Equal filter (column, value)
            - neq: Not equal filter (column, value)
            - gt: Greater than filter (column, value)
            - gte: Greater than or equal filter (column, value)
            - lt: Less than filter (column, value)
            - lte: Less than or equal filter (column, value)
            - like: Like filter (column, pattern)
            - ilike: Case insensitive like filter (column, pattern)
            - is_: Is filter (column, value)
            - in_: In filter (column, list)
            - contains: Contains filter (column, value)
            - contained_by: Contained by filter (column, value)
            - range_: Range filter (column, start, end)
            - order: Order by (column, desc=False)
            - limit: Limit results (count)
            - offset: Offset results (count)
    
    Returns:
        list: Query results as a list of dictionaries, or empty DataFrame on error
    """
    if not supabase:
        st.error("Supabase client is not initialized.")
        return pd.DataFrame()
    if not table_name:
        st.error("Table name is required.")
        return pd.DataFrame()
    
    try:
        # Start with the table
        query = supabase.table(table_name)
        
        # Handle select columns (default to all)
        select_columns = kwargs.get('select', '*')
        query = query.select(select_columns)
        
        # Apply filters based on kwargs
        if 'eq' in kwargs:
            column, value = kwargs['eq']
            query = query.eq(column, value)
        
        if 'neq' in kwargs:
            column, value = kwargs['neq']
            query = query.neq(column, value)
        
        if 'gt' in kwargs:
            column, value = kwargs['gt']
            query = query.gt(column, value)
        
        if 'gte' in kwargs:
            column, value = kwargs['gte']
            query = query.gte(column, value)
        
        if 'lt' in kwargs:
            column, value = kwargs['lt']
            query = query.lt(column, value)
        
        if 'lte' in kwargs:
            column, value = kwargs['lte']
            query = query.lte(column, value)
        
        if 'like' in kwargs:
            column, pattern = kwargs['like']
            query = query.like(column, pattern)
        
        if 'ilike' in kwargs:
            column, pattern = kwargs['ilike']
            query = query.ilike(column, pattern)
        
        if 'is_' in kwargs:
            column, value = kwargs['is_']
            query = query.is_(column, value)
        
        if 'in_' in kwargs:
            column, values = kwargs['in_']
            query = query.in_(column, values)
        
        if 'contains' in kwargs:
            column, value = kwargs['contains']
            query = query.contains(column, value)
        
        if 'contained_by' in kwargs:
            column, value = kwargs['contained_by']
            query = query.contained_by(column, value)
        
        if 'range_' in kwargs:
            column, start, end = kwargs['range_']
            query = query.range_(column, start, end)
        
        # Apply ordering
        if 'order' in kwargs:
            if isinstance(kwargs['order'], tuple):
                column, desc = kwargs['order']
                query = query.order(column, desc=desc)
            else:
                query = query.order(kwargs['order'])
        
        # Apply limit
        if 'limit' in kwargs:
            query = query.limit(kwargs['limit'])
        
        # Apply offset
        if 'offset' in kwargs:
            query = query.offset(kwargs['offset'])
        
        # Execute the query
        return query.execute().data
        
    except Exception as e:
        st.error(f"Failed to fetch table {table_name}: {e}")
        return pd.DataFrame()

# Get Database Tables (Cached version for static reference tables)
@st.cache_data(ttl=3600)
def GetSupaTableCached(table_name: str, *args, **kwargs):
    """
    Cached version of GetSupaTable for static reference tables that don't change frequently.
    Use this for tables like ForcePlatePercentiles, CombinePercentiles, etc.
    
    Args:
        Same as GetSupaTable
    
    Returns:
        list: Query results as a list of dictionaries, or empty DataFrame on error
    """
    return GetSupaTable(table_name, *args, **kwargs)

# Insert data into a table
def InsertSupaTable(table_name: str, data, **kwargs):
    """
    Insert one or more rows into a Supabase table.
    
    Args:
        table_name (str): The name of the table to insert into
        data (dict or list): A dictionary for single row or list of dictionaries for multiple rows
        **kwargs: Additional options such as:
            - upsert: Whether to upsert (insert or update) if conflict occurs
            - on_conflict: Column name(s) to check for conflicts during upsert
            - returning: Specify what to return after insert (default: "*")
    
    Returns:
        list: Inserted data if successful, empty list on error
    """
    if not supabase:
        st.error("Supabase client is not initialized.")
        return []
    if not table_name or not data:
        st.error("Table name and data are required.")
        return []
    
    try:
        query = supabase.table(table_name)
        
        # Handle upsert option
        if kwargs.get('upsert', False):
            on_conflict = kwargs.get('on_conflict', None)
            if on_conflict:
                result = query.upsert(data, on_conflict=on_conflict).execute()
            else:
                result = query.upsert(data).execute()
        else:
            result = query.insert(data).execute()
        
        return result.data
        
    except Exception as e:
        st.error(f"Failed to insert data into {table_name}: {e}")
        return []

# Update rows in a table
def UpdateSupaTable(table_name: str, data: dict, **kwargs):
    """
    Update rows in a Supabase table with flexible filtering.
    
    Args:
        table_name (str): The name of the table to update
        data (dict): A dictionary of column-value pairs to update
        **kwargs: Filtering options (same as GetSupaTable) such as:
            - eq: Equal filter (column, value)
            - neq: Not equal filter (column, value)
            - gt, gte, lt, lte: Comparison filters
            - like, ilike: Pattern matching filters
            - in_: In filter (column, list)
            - etc.
    
    Returns:
        list: Updated data if successful, empty list on error
    """
    if not supabase:
        st.error("Supabase client is not initialized.")
        return []
    if not table_name or not data:
        st.error("Table name and data are required.")
        return []
    
    try:
        # Start with the table and update operation
        query = supabase.table(table_name).update(data)
        
        # Apply filters based on kwargs (same logic as GetSupaTable)
        if 'eq' in kwargs:
            column, value = kwargs['eq']
            query = query.eq(column, value)
        
        if 'neq' in kwargs:
            column, value = kwargs['neq']
            query = query.neq(column, value)
        
        if 'gt' in kwargs:
            column, value = kwargs['gt']
            query = query.gt(column, value)
        
        if 'gte' in kwargs:
            column, value = kwargs['gte']
            query = query.gte(column, value)
        
        if 'lt' in kwargs:
            column, value = kwargs['lt']
            query = query.lt(column, value)
        
        if 'lte' in kwargs:
            column, value = kwargs['lte']
            query = query.lte(column, value)
        
        if 'like' in kwargs:
            column, pattern = kwargs['like']
            query = query.like(column, pattern)
        
        if 'ilike' in kwargs:
            column, pattern = kwargs['ilike']
            query = query.ilike(column, pattern)
        
        if 'is_' in kwargs:
            column, value = kwargs['is_']
            query = query.is_(column, value)
        
        if 'in_' in kwargs:
            column, values = kwargs['in_']
            query = query.in_(column, values)
        
        if 'contains' in kwargs:
            column, value = kwargs['contains']
            query = query.contains(column, value)
        
        if 'contained_by' in kwargs:
            column, value = kwargs['contained_by']
            query = query.contained_by(column, value)
        
        if 'range_' in kwargs:
            column, start, end = kwargs['range_']
            query = query.range_(column, start, end)
        
        # Execute the update query
        result = query.execute()
        return result.data
        
    except Exception as e:
        st.error(f"Failed to update rows in {table_name}: {e}")
        return []

# Delete rows from a table
def DeleteSupaTable(table_name: str, **kwargs):
    """
    Delete rows from a Supabase table with flexible filtering.
    
    Args:
        table_name (str): The name of the table to delete from
        **kwargs: Filtering options (same as GetSupaTable) such as:
            - eq: Equal filter (column, value)
            - neq: Not equal filter (column, value)
            - gt, gte, lt, lte: Comparison filters
            - like, ilike: Pattern matching filters
            - in_: In filter (column, list)
            - etc.
    
    Returns:
        list: Deleted data if successful, empty list on error
    """
    if not supabase:
        st.error("Supabase client is not initialized.")
        return []
    if not table_name:
        st.error("Table name is required.")
        return []
    
    # Require at least one filter to prevent accidental deletion of all rows
    filter_kwargs = {k: v for k, v in kwargs.items() if k in [
        'eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'like', 'ilike', 
        'is_', 'in_', 'contains', 'contained_by', 'range_'
    ]}
    
    if not filter_kwargs:
        st.error("At least one filter must be provided to delete rows (safety measure).")
        return []
    
    try:
        # Start with the table and delete operation
        query = supabase.table(table_name).delete()
        
        # Apply filters based on kwargs (same logic as GetSupaTable)
        if 'eq' in kwargs:
            column, value = kwargs['eq']
            query = query.eq(column, value)
        
        if 'neq' in kwargs:
            column, value = kwargs['neq']
            query = query.neq(column, value)
        
        if 'gt' in kwargs:
            column, value = kwargs['gt']
            query = query.gt(column, value)
        
        if 'gte' in kwargs:
            column, value = kwargs['gte']
            query = query.gte(column, value)
        
        if 'lt' in kwargs:
            column, value = kwargs['lt']
            query = query.lt(column, value)
        
        if 'lte' in kwargs:
            column, value = kwargs['lte']
            query = query.lte(column, value)
        
        if 'like' in kwargs:
            column, pattern = kwargs['like']
            query = query.like(column, pattern)
        
        if 'ilike' in kwargs:
            column, pattern = kwargs['ilike']
            query = query.ilike(column, pattern)
        
        if 'is_' in kwargs:
            column, value = kwargs['is_']
            query = query.is_(column, value)
        
        if 'in_' in kwargs:
            column, values = kwargs['in_']
            query = query.in_(column, values)
        
        if 'contains' in kwargs:
            column, value = kwargs['contains']
            query = query.contains(column, value)
        
        if 'contained_by' in kwargs:
            column, value = kwargs['contained_by']
            query = query.contained_by(column, value)
        
        if 'range_' in kwargs:
            column, start, end = kwargs['range_']
            query = query.range_(column, start, end)
        
        # Execute the delete query
        result = query.execute()
        return result.data
        
    except Exception as e:
        st.error(f"Failed to delete rows from {table_name}: {e}")
        return []
    