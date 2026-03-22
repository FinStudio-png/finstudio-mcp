"""
FinStudio MCP Server — Financial Models
=========================================
4 tools: dcf_valuation, unit_economics, pnl_forecast, tax_calculator
"""

import os
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("FinStudio Financial Models")


@mcp.tool()
def dcf_valuation(
    revenue_year1: float,
    growth_rate: float = 0.15,
    profit_margin: float = 0.20,
    discount_rate: float = 0.12,
    terminal_growth: float = 0.03,
    forecast_years: int = 5
) -> str:
    """DCF valuation of a business. Args: revenue_year1=annual revenue EUR, growth_rate=0.15 for 15%, profit_margin=0.20, discount_rate=0.12, terminal_growth=0.03, forecast_years=5."""
    if discount_rate <= terminal_growth:
        return json.dumps({"error": "Discount rate must exceed terminal growth rate"})
    total_pv = 0
    revenue = revenue_year1
    yearly = []
    for year in range(1, forecast_years + 1):
        revenue = revenue * (1 + growth_rate) if year > 1 else revenue
        fcf = revenue * profit_margin
        pv_factor = 1 / (1 + discount_rate) ** year
        pv = fcf * pv_factor
        total_pv += pv
        yearly.append({"year": year, "revenue": round(revenue), "fcf": round(fcf), "pv": round(pv)})
    final_fcf = revenue * (1 + growth_rate) * profit_margin
    tv = final_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_tv = tv / (1 + discount_rate) ** forecast_years
    ev = total_pv + pv_tv
    return json.dumps({"yearly_forecast": yearly, "valuation": {"pv_cashflows": round(total_pv), "terminal_value": round(tv), "pv_terminal": round(pv_tv), "enterprise_value_EUR": round(ev), "ev_to_revenue": round(ev / revenue_year1, 2)}}, indent=2)


@mcp.tool()
def unit_economics(
    monthly_revenue: float,
    total_customers: int,
    new_customers_per_month: int,
    monthly_churn_rate: float = 0.05,
    customer_acquisition_cost: float = 0,
    gross_margin: float = 0.70,
    monthly_marketing_spend: float = 0
) -> str:
    """Unit economics calculator. Args: monthly_revenue=MRR in EUR, total_customers, new_customers_per_month, monthly_churn_rate=0.05, customer_acquisition_cost=0, gross_margin=0.70, monthly_marketing_spend=0."""
    arpu = monthly_revenue / total_customers if total_customers > 0 else 0
    cac = customer_acquisition_cost if customer_acquisition_cost > 0 else (monthly_marketing_spend / new_customers_per_month if new_customers_per_month > 0 and monthly_marketing_spend > 0 else 0)
    lifetime = 1 / monthly_churn_rate if monthly_churn_rate > 0 else 60
    ltv = arpu * gross_margin * lifetime
    ltv_cac = ltv / cac if cac > 0 else 0
    payback = cac / (arpu * gross_margin) if arpu * gross_margin > 0 else 0
    health = []
    if ltv_cac >= 3: health.append("LTV/CAC >= 3x — EXCELLENT")
    elif ltv_cac >= 1.5: health.append("LTV/CAC 1.5-3x — OK")
    else: health.append("LTV/CAC < 1.5x — WARNING")
    return json.dumps({"metrics": {"MRR": round(monthly_revenue), "ARR": round(monthly_revenue * 12), "ARPU": round(arpu, 2), "customers": total_customers}, "unit_economics": {"LTV": round(ltv), "CAC": round(cac), "LTV_CAC_ratio": round(ltv_cac, 2), "payback_months": round(payback, 1), "avg_lifetime_months": round(lifetime, 1)}, "health": health}, indent=2)


@mcp.tool()
def pnl_forecast(
    monthly_revenue: float,
    revenue_growth_monthly: float = 0.05,
    cogs_percent: float = 0.30,
    salaries: float = 0,
    rent: float = 0,
    marketing: float = 0,
    other_opex: float = 0,
    tax_rate: float = 0.125,
    forecast_months: int = 12
) -> str:
    """P&L forecast. Args: monthly_revenue=starting MRR EUR, revenue_growth_monthly=0.05, cogs_percent=0.30, salaries/rent/marketing/other_opex=monthly EUR, tax_rate=0.125 Cyprus, forecast_months=12."""
    data = []
    total_rev = 0
    total_net = 0
    cum = 0
    rev = monthly_revenue
    opex = salaries + rent + marketing + other_opex
    for m in range(1, forecast_months + 1):
        if m > 1: rev = rev * (1 + revenue_growth_monthly)
        gp = rev * (1 - cogs_percent)
        ebitda = gp - opex
        tax = max(0, ebitda * tax_rate)
        net = ebitda - tax
        cum += net
        total_rev += rev
        total_net += net
        data.append({"month": m, "revenue": round(rev), "gross_profit": round(gp), "ebitda": round(ebitda), "net_profit": round(net), "cumulative": round(cum)})
    scenarios = {}
    for name, adj in [("optimistic", 0.03), ("base", 0), ("pessimistic", -0.03)]:
        r = monthly_revenue
        tn = 0
        for m in range(1, forecast_months + 1):
            if m > 1: r = r * (1 + revenue_growth_monthly + adj)
            tn += (r * (1 - cogs_percent) - opex) * (1 - tax_rate)
        scenarios[name] = round(tn)
    return json.dumps({"summary": {"total_revenue": round(total_rev), "total_net_profit": round(total_net), "margin": f"{total_net/total_rev*100:.1f}%" if total_rev else "0%"}, "monthly": data, "stress_test": scenarios}, indent=2)


TAX_DATA = {
    "Cyprus": {"rate": 0.125, "ip": 0.025, "div": 0, "setup": 3000, "annual": 5000, "notes": "15% from 2026. IP Box 2.5%. No div WHT. EU."},
    "UAE": {"rate": 0.09, "ip": None, "div": 0, "setup": 5000, "annual": 8000, "notes": "9% above 375K AED. Free zones 0%. No PIT."},
    "Hong_Kong": {"rate": 0.165, "ip": None, "div": 0, "setup": 2000, "annual": 4000, "notes": "8.25%/16.5%. No VAT. Territorial."},
    "Estonia": {"rate": 0, "ip": None, "div": 0.20, "setup": 1500, "annual": 3000, "notes": "0% retained. 20% distributed. E-residency."},
    "Spain": {"rate": 0.25, "ip": 0.10, "div": 0.19, "setup": 3500, "annual": 6000, "notes": "25%. 15% first 2yrs. Beckham Law."},
    "Portugal": {"rate": 0.21, "ip": None, "div": 0.28, "setup": 3000, "annual": 5000, "notes": "21%. 17% SME. NHR 10yrs."},
    "Malta": {"rate": 0.35, "ip": None, "div": 0, "setup": 3000, "annual": 5000, "notes": "35% nominal, 5% effective. Refund system."},
    "Ireland": {"rate": 0.125, "ip": 0.0625, "div": 0.25, "setup": 4000, "annual": 7000, "notes": "12.5%. IP 6.25%. EU."},
}

@mcp.tool()
def tax_calculator(
    annual_revenue: float,
    profit_margin: float = 0.30,
    jurisdictions: str = "Cyprus,UAE,Estonia,Hong_Kong",
    distribute_profits: bool = False,
    has_ip: bool = False
) -> str:
    """Compare taxes across jurisdictions. Args: annual_revenue EUR, profit_margin=0.30, jurisdictions='Cyprus,UAE,Estonia,Hong_Kong' (also: Spain,Portugal,Malta,Ireland), distribute_profits=false, has_ip=false."""
    profit = annual_revenue * profit_margin
    results = []
    for c in [j.strip() for j in jurisdictions.split(",")]:
        d = TAX_DATA.get(c)
        if not d:
            results.append({"country": c, "error": f"Unknown. Use: {','.join(TAX_DATA.keys())}"})
            continue
        rate = d["ip"] if has_ip and d.get("ip") else d["rate"]
        corp_tax = profit * rate
        div_tax = (profit - corp_tax) * d["div"] if distribute_profits else 0
        total = corp_tax + div_tax
        results.append({"country": c.replace("_"," "), "rate": f"{rate*100:.1f}%", "tax_EUR": round(total), "after_tax_EUR": round(profit - total), "setup_EUR": d["setup"], "annual_EUR": d["annual"], "notes": d["notes"]})
    results.sort(key=lambda x: x.get("tax_EUR", 999999))
    return json.dumps({"profit_EUR": round(profit), "comparison": results}, indent=2)


import uvicorn

app = mcp.sse_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
```
