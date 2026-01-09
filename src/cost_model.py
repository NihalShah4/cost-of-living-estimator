from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import json
from pathlib import Path

@dataclass
class Inputs:
    state: str
    adults: int
    kids: int
    housing_mode: str          # "Rent" or "Own"
    bedrooms: str              # "Studio" "1BR" "2BR" "3BR+"
    premium_area: bool
    cars: int
    transit: str               # "Low" "Medium" "High"
    groceries: str             # "Budget" "Standard" "Premium"
    dining_out: str            # "Low" "Medium" "High"
    insurance: str             # "Basic" "Standard" "Premium"
    gym: bool
    entertainment: str         # "Low" "Medium" "High"
    travel: str                # "None" "Occasional" "Frequent"

def load_base_basket() -> Dict:
    p = Path("data/base_basket_us.json")
    return json.loads(p.read_text())

def multipliers(i: Inputs) -> Dict[str, float]:
    # Housing
    bedroom_mult = {"Studio": 0.80, "1BR": 1.00, "2BR": 1.35, "3BR+": 1.70}[i.bedrooms]
    premium_mult = 1.15 if i.premium_area else 1.00
    own_mult = 1.00 if i.housing_mode == "Rent" else 0.95  # simplistic: owning may reduce monthly outlay vs rent in some cases

    # Groceries & dining
    groceries_mult = {"Budget": 0.85, "Standard": 1.00, "Premium": 1.25}[i.groceries]
    dining_mult = {"Low": 0.70, "Medium": 1.00, "High": 1.50}[i.dining_out]

    # Transit (affects transport category baseline)
    transit_mult = {"Low": 1.10, "Medium": 1.00, "High": 0.85}[i.transit]

    # Insurance
    insurance_mult = {"Basic": 0.85, "Standard": 1.00, "Premium": 1.25}[i.insurance]

    # Entertainment & travel
    entertainment_mult = {"Low": 0.80, "Medium": 1.00, "High": 1.35}[i.entertainment]
    travel_add = {"None": 0, "Occasional": 120, "Frequent": 320}[i.travel]  # monthly add-on

    return {
        "housing_mult": bedroom_mult * premium_mult * own_mult,
        "groceries_mult": groceries_mult,
        "dining_mult": dining_mult,
        "transit_mult": transit_mult,
        "insurance_mult": insurance_mult,
        "entertainment_mult": entertainment_mult,
        "travel_add": float(travel_add),
    }

def estimate_monthly_cost(i: Inputs, rpp_index: float) -> Dict[str, float]:
    base = load_base_basket()
    b = base["monthly_usd_single_adult"]
    c = base["child_monthly"]

    rpp = rpp_index / 100.0  # convert index to multiplier

    m = multipliers(i)

    # Household scaling
    extra_adults = max(i.adults - 1, 0)
    adult_groceries_scale = 1.0 + 0.70 * extra_adults
    adult_misc_scale = 1.0 + 0.60 * extra_adults
    adult_health_scale = 1.0 + 0.55 * extra_adults

    # Housing: bedrooms already captures much of household sizing
    housing = b["housing_1br"] * m["housing_mult"] * rpp

    utilities = b["utilities"] * (1.0 + 0.35 * extra_adults + 0.20 * i.kids) * rpp
    groceries = b["groceries"] * adult_groceries_scale * m["groceries_mult"] * rpp + (c["groceries_per_child"] * i.kids * rpp)
    dining = b["dining_out_base"] * (1.0 + 0.35 * extra_adults) * m["dining_mult"] * rpp

    # Transport: baseline + cars (cars are expensive), reduced if high transit usage
    transport = b["transport_base"] * m["transit_mult"] * (1.0 + 0.35 * extra_adults) * rpp
    car_add = i.cars * 450 * rpp  # proxy all-in (payment/insurance/fuel/maintenance)
    transport += car_add

    healthcare = b["healthcare"] * adult_health_scale * m["insurance_mult"] * rpp + (c["healthcare_per_child"] * i.kids * rpp)

    childcare = (c["childcare_per_child"] * i.kids * rpp) if i.kids > 0 else 0.0

    misc = b["misc"] * adult_misc_scale * rpp
    if i.gym:
        misc += 45 * rpp
    misc *= m["entertainment_mult"]

    travel = m["travel_add"] * rpp

    out = {
        "Housing": housing,
        "Utilities": utilities,
        "Groceries": groceries,
        "Dining Out": dining,
        "Transportation": transport,
        "Healthcare": healthcare,
        "Childcare": childcare,
        "Misc": misc,
        "Travel": travel,
    }
    out["Total"] = sum(out.values())
    return out
def recommend_income(monthly_cost: float, savings_rate: float, effective_tax_rate: float, buffer: float = 0.0) -> dict:
    """
    Computes gross income needed to cover:
      - monthly_cost (expenses)
      - savings_rate (as % of net income)
      - effective_tax_rate (as % of gross income)
      - optional buffer on costs (e.g., 0.05 => +5%)

    Model:
      gross_income * (1 - tax_rate) = net_income
      net_income = expenses_adjusted + savings_rate * net_income
      => net_income * (1 - savings_rate) = expenses_adjusted
      => net_income = expenses_adjusted / (1 - savings_rate)
      => gross = net_income / (1 - tax_rate)
    """
    expenses_adjusted = monthly_cost * (1.0 + max(buffer, 0.0))

    # Guardrails
    savings_rate = min(max(savings_rate, 0.0), 0.80)
    effective_tax_rate = min(max(effective_tax_rate, 0.0), 0.60)

    if savings_rate >= 1.0:
        raise ValueError("Savings rate must be < 100%.")

    net_needed = expenses_adjusted / (1.0 - savings_rate)
    gross_needed = net_needed / (1.0 - effective_tax_rate) if effective_tax_rate < 1.0 else float("inf")

    return {
        "expenses_adjusted": expenses_adjusted,
        "net_monthly": net_needed,
        "gross_monthly": gross_needed,
        "gross_annual": gross_needed * 12
    }
