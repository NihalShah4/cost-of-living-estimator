import pandas as pd
import streamlit as st

from src.rpp import load_rpp_table, get_state_rpp
from src.cost_model import Inputs, estimate_monthly_cost, recommend_income

st.set_page_config(page_title="Cost of Living Estimator", layout="wide")

st.title("Lifestyle-Based Cost of Living Estimator")
st.caption("V1: United States (state-level) using BEA Regional Price Parities (RPP).")

# ---------- Load RPP + derive states list ----------
rpp_df = load_rpp_table()

# Try to get a robust state list from the scraped table; fallback list if needed
def _extract_states(df: pd.DataFrame) -> list[str]:
    cols = {c.lower(): c for c in df.columns}
    state_col = None
    for k in cols:
        if "state" in k:
            state_col = cols[k]
            break
    if state_col is None:
        return []
    states = (
        df[state_col]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    # Keep only plausible names
    states = [s for s in states if len(s) >= 4 and s.lower() not in ("state",)]
    return sorted(set(states))

STATE_OPTIONS = _extract_states(rpp_df)
if not STATE_OPTIONS:
    STATE_OPTIONS = [
        "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware",
        "District of Columbia","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa",
        "Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota",
        "Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico",
        "New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island",
        "South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington",
        "West Virginia","Wisconsin","Wyoming"
    ]

# ---------- Sidebar inputs ----------
with st.sidebar:
    st.header("Location")
    country = st.selectbox("Country", ["United States", "Other (coming soon)"])
    default_state = "New Jersey" if "New Jersey" in STATE_OPTIONS else STATE_OPTIONS[0]
    state = st.selectbox("State", STATE_OPTIONS, index=STATE_OPTIONS.index(default_state))

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

    st.header("Income planning")
    savings_rate = st.slider("Savings rate target (%)", min_value=0, max_value=40, value=15, step=1)
    effective_tax_rate = st.slider("Estimated effective tax rate (%)", min_value=0, max_value=40, value=22, step=1)
    include_buffer = st.checkbox("Add contingency buffer (5%)", value=True)

submitted = st.button("Estimate cost")

# ---------- Main ----------
if country != "United States":
    st.warning("V1 only supports United States (state-level). Add other countries by extending the data model.")
    st.stop()

if submitted:
    try:
        rpp_index = get_state_rpp(rpp_df, state)
    except Exception as e:
        st.error(f"Could not resolve RPP for '{state}'. Details: {e}")
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

    # Breakdown table (excluding Total)
    df = pd.DataFrame(
        [{"Category": k, "Monthly (USD)": v, "Annual (USD)": v * 12}
         for k, v in monthly.items() if k != "Total"]
    )

    total_monthly = monthly["Total"]
    total_annual = total_monthly * 12

    # Income recommendation
    income = recommend_income(
        monthly_cost=total_monthly,
        savings_rate=savings_rate / 100.0,
        effective_tax_rate=effective_tax_rate / 100.0,
        buffer=0.05 if include_buffer else 0.0,
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Cost breakdown")
        st.dataframe(
            df.style.format({"Monthly (USD)": "{:,.0f}", "Annual (USD)": "{:,.0f}"}),
            use_container_width=True
        )

    with col2:
        st.subheader("Summary")
        st.metric("State price level (RPP index)", f"{rpp_index:,.1f}")
        st.metric("Estimated monthly total", f"${total_monthly:,.0f}")
        st.metric("Estimated annual total", f"${total_annual:,.0f}")

        st.divider()
        st.subheader("Income recommendation")
        st.caption("Based on your savings + tax assumptions.")
        st.metric("Gross monthly needed", f"${income['gross_monthly']:,.0f}")
        st.metric("Gross annual needed", f"${income['gross_annual']:,.0f}")
        st.caption(
            f"Assumptions: savings {savings_rate}%, effective tax {effective_tax_rate}%, "
            + ("+ 5% buffer." if include_buffer else "no buffer.")
        )

    st.caption(
        "Note: This is an estimator using state-level price parity (BEA RPP) and configurable lifestyle assumptions; "
        "it is not a quote for rent, insurance, or taxes."
    )
