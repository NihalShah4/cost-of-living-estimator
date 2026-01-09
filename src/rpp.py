from __future__ import annotations
import pandas as pd
import requests
import streamlit as st

BEA_RPP_URL = "https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area"

# Minimal fallback if the BEA page format changes or offline
FALLBACK_RPP = {
    "District of Columbia": 110.8,
    "California": 112.6,
    "New Jersey": 108.9,
    "Hawaii": 108.6,
    "Mississippi": 87.3,
    "Arkansas": 86.5,
    "South Dakota": 88.1
}

@st.cache_data(ttl=24 * 3600)
def load_rpp_table() -> pd.DataFrame:
    """
    Scrapes the BEA RPP page tables into DataFrames and returns the best match.
    If scraping fails, returns a small fallback table.
    """
    try:
        html = requests.get(BEA_RPP_URL, timeout=20).text
        tables = pd.read_html(html)

        # Heuristic: find a table that contains 'State' and 'RPP' or similar numeric index
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            if any("state" in c for c in cols) and (t.shape[0] >= 40):
                # Normalize common column names
                t = t.copy()
                t.columns = [str(c).strip() for c in t.columns]
                return t

        # If nothing matched, raise to fallback
        raise ValueError("No suitable RPP table found.")
    except Exception:
        # Fallback: create a small dataframe
        return pd.DataFrame({"State": list(FALLBACK_RPP.keys()), "RPP": list(FALLBACK_RPP.values())})

def get_state_rpp(df: pd.DataFrame, state_name: str) -> float:
    """
    Returns RPP value (index like 112.6). Tries multiple common column layouts.
    """
    # Standardize columns
    cols = {c.lower(): c for c in df.columns}
    state_col = None
    for key in cols:
        if "state" in key:
            state_col = cols[key]
            break
    if state_col is None:
        raise ValueError("State column not found in RPP table.")

    # Find numeric column candidate
    numeric_cols = []
    for c in df.columns:
        if c == state_col:
            continue
        if pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.6:
            numeric_cols.append(c)

    if not numeric_cols:
        raise ValueError("No numeric RPP column detected.")

    # Pick the first numeric column as best guess (BEA tables often have year columns)
    rpp_col = numeric_cols[0]

    match = df[df[state_col].astype(str).str.strip().str.lower() == state_name.strip().lower()]
    if match.empty:
        # Try contains-based match
        match = df[df[state_col].astype(str).str.lower().str.contains(state_name.strip().lower(), na=False)]
    if match.empty:
        raise ValueError(f"State '{state_name}' not found in RPP table.")

    val = float(pd.to_numeric(match.iloc[0][rpp_col], errors="coerce"))
    if not (50.0 <= val <= 200.0):
        # If parsing hit a weird number, fallback if present
        return float(FALLBACK_RPP.get(state_name, 100.0))
    return val
