import pandas as pd
import streamlit as st

from src.rpp import load_rpp_table, get_state_rpp
from src.cost_model import Inputs, estimate_monthly_cost

st.set_page_config(page_title="Cost of Living Estimator", layout="wide")

st.title("Lifestyle-Based Cost of Living Estimator")
st.caption("V1: United States (state-level) using BEA Regional Price Parities (RPP).")

with st.sidebar:
    st.header("Location")
    country = st.selectbox("Country", ["United States", "Other (coming soon)"])
    state = st.text_input("State (e.g., California, New Jersey, District of Columbia)", value="New Jersey")

    st.header("Household")
    adults = st.number_input("Adults", min_value=1, max_value=6, value=1, step=1)
    kids = st.number_input("Kids", min_value=0, max_value=6, value=0, step=1)

    st.header("Housing")
    housing_mode = st.selectbox("Housing mode", ["Rent", "Own"])
    bedrooms = st.selectbox("Bedrooms", ["Studio", "1BR", "2BR", "3BR+"])
    premium_area = st.checkbox("Premium neighborhood", value=False)

    st.header("Transportation")
    cars = st.number_input("Number of cars", min_value=0, max_value=4, value=0, step=1)
    transit = st.selectbox("Public transit usage", ["Low", "Medium", "High"], index=1)

    st.header("Food")
    groceries = st.selectbox("Groceries style", ["Budget", "Standard", "Premium"], index=1)
    dining_out = st.selectbox("Dining out", ["Low", "Medium", "High"], index=1)

    st.header("Health & extras")
    insurance = st.selectbox("Insurance level", ["Basic", "Standard", "Premium"], index=1)
    gym = st.checkbox("Gym membership", value=False)
    entertainment = st.selectbox("Entertainment", ["Low", "Medium", "High"], index=1)
    travel = st.selectbox("Travel", ["None", "Occasional", "Frequent"], index=0)

submitted = st.button("Estimate cost")

if country != "United States":
    st.warning("V1 only supports United States (state-level). Add other countries by extending the data model.")
    st.stop()

if submitted:
    rpp_df = load_rpp_table()
    try:
        rpp_index = get_state_rpp(rpp_df, state)
    except Exception as e:
        st.error(f"Could not resolve RPP for '{state}'. Try a full name (e.g., 'New Jersey'). Details: {e}")
        st.stop()

    inp = Inputs(
        state=state,
        adults=int(adults),
        kids=int(kids),
        housing_mode=housing_mode,
        bedrooms=bedrooms,
        premium_area=premium_area,
        cars=int(cars),
        transit=transit,
        groceries=groceries,
        dining_out=dining_out,
        insurance=insurance,
        gym=gym,
        entertainment=entertainment,
        travel=travel,
    )

    monthly = estimate_monthly_cost(inp, rpp_index)
    df = pd.DataFrame(
        [{"Category": k, "Monthly (USD)": v, "Annual (USD)": v * 12} for k, v in monthly.items() if k != "Total"]
    )
    total_monthly = monthly["Total"]
    total_annual = total_monthly * 12

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Breakdown")
        st.dataframe(df.style.format({"Monthly (USD)": "{:,.0f}", "Annual (USD)": "{:,.0f}"}), use_container_width=True)

    with col2:
        st.subheader("Summary")
        st.metric("State price level (RPP index)", f"{rpp_index:,.1f}")
        st.metric("Estimated monthly total", f"${total_monthly:,.0f}")
        st.metric("Estimated annual total", f"${total_annual:,.0f}")

    st.caption(
        "Note: This is an estimator using state-level price parity (BEA RPP) and configurable lifestyle assumptions; "
        "it is not a quote for rent, insurance, or taxes."
    )
