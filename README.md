# Cost of Living Estimator (Lifestyle-Based)

A small Streamlit app that estimates cost of living from lifestyle choices.

## What it uses
- U.S. state price-level adjustment using BEA Regional Price Parities (RPP)
- A transparent baseline basket + multipliers for lifestyle choices

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
