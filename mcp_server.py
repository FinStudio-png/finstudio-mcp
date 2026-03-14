"""
FinStudio MCP Server — Financial Models
=========================================
4 tools:
  - dcf_valuation — DCF оценка стоимости бизнеса
  - unit_economics — LTV, CAC, MRR, payback period
  - pnl_forecast — P&L прогноз на 12 месяцев
  - tax_calculator — налоги по юрисдикциям

Deploy: Railway or any Python host
Run: python mcp_server.py
"""

from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("FinStudio Financial Models")


# ─────────────────────────────────────────────
# TOOL 1: DCF Valuation
# ─────────────────────────────────────────────

@mcp.tool()
def dcf_valuation(
    revenue_year1: float,
    growth_rate: float = 0.15,
    profit_margin: float = 0.20,
    discount_rate: float = 0.12,
    terminal_growth: float = 0.03,
    forecast_years: int = 5
) -> str:
    """
    DCF (Discounted Cash Flow) valuation of a business.
    
    Args:
        revenue_year1: Current annual revenue in EUR
        growth_rate: Annual revenue growth rate (0.15 = 15%)
        profit_margin: Net profit margin (0.20 = 20%)
        discount_rate: WACC / discount rate (0.12 = 12%)
        terminal_growth: Long-term growth rate (0.03 = 3%)
        forecast_years: Number of forecast years (default 5)
    
    Returns:
        DCF valuation with detailed breakdown
    """
    if discount_rate <= terminal_growth:
        return "Error: Discount rate must be greater than terminal growth rate"
    
    results = {
        "input": {
            "revenue_year1": revenue_year1,
            "growth_rate": f"{growth_rate*100:.1f}%",
            "profit_margin": f"{profit_margin*100:.1f}%",
            "discount_rate": f"{discount_rate*100:.1f}%",
            "terminal_growth": f"{terminal_growth*100:.1f}%",
            "forecast_years": forecast_years,
        },
        "yearly_forecast": [],
        "valuation": {}
    }
    
    total_pv = 0
    revenue = revenue_year1
    
    for year in range(1, forecast_years + 1):
        revenue = revenue * (1 + growth_rate) if year > 1 else revenue
        fcf = revenue * profit_margin
        pv_factor = 1 / (1 + discount_rate) ** year
        pv = fcf * pv_factor
        total_pv += pv
        
        results["yearly_forecast"].append({
            "year": year,
            "revenue": round(revenue),
            "free_cash_flow": round(fcf),
            "pv_factor": round(pv_factor, 4),
            "present_value": round(pv),
        })
    
    # Terminal value
    final_fcf = revenue * (1 + growth_rate) * profit_margin
    terminal_value = final_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** forecast_years
    
    enterprise_value = total_pv + pv_terminal
    
    # Multiples for reference
    ev_revenue = enterprise_value / revenue_year1
    ev_ebitda = enterprise_value / (revenue_year1 * profit_margin) if profit_margin > 0 else 0
    
    results["valuation"] = {
        "pv_forecast_cashflows": round(total_pv),
        "terminal_value": round(terminal_value),
        "pv_terminal_value": round(pv_terminal),
        "enterprise_value_EUR": round(enterprise_value),
        "ev_to_revenue": round(ev_revenue, 2),
        "ev_to_ebitda": round(ev_ebitda, 2),
    }
    
    # Sensitivity analysis
    sensitivities = []
    for dr in [discount_rate - 0.02, discount_rate, discount_rate + 0.02]:
        for gm in [profit_margin - 0.05, profit_margin, profit_margin + 0.05]:
            if dr > terminal_growth and gm > 0:
                r = revenue_year1
                tpv = 0
                for y in range(1, forecast_years + 1):
                    r = r * (1 + growth_rate) if y > 1 else r
                    tpv += (r * gm) / (1 + dr) ** y
                ff = r * (1 + growth_rate) * gm
                tv = ff * (1 + terminal_growth) / (dr - terminal_growth)
                pvt = tv / (1 + dr) ** forecast_years
                sensitivities.append({
                    "discount_rate": f"{dr*100:.0f}%",
                    "profit_margin": f"{gm*100:.0f}%",
                    "enterprise_value_EUR": round(tpv + pvt),
                })
    
    results["sensitivity_analysis"] = sensitivities
    
    return json.dumps(results, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# TOOL 2: Unit Economics
# ─────────────────────────────────────────────

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
    """
    Calculate unit economics: LTV, CAC, MRR, payback period, LTV/CAC ratio.
    
    Args:
        monthly_revenue: Total monthly recurring revenue in EUR
        total_customers: Current number of paying customers
        new_customers_per_month: New customers acquired per month
        monthly_churn_rate: Monthly customer churn rate (0.05 = 5%)
        customer_acquisition_cost: Cost to acquire one customer in EUR (0 = auto-calculate from marketing spend)
        gross_margin: Gross margin (0.70 = 70%)
        monthly_marketing_spend: Monthly marketing budget in EUR
    
    Returns:
        Unit economics analysis with key metrics
    """
    # Calculate ARPU
    arpu = monthly_revenue / total_customers if total_customers > 0 else 0
    
    # Calculate CAC
    if customer_acquisition_cost > 0:
        cac = customer_acquisition_cost
    elif monthly_marketing_spend > 0 and new_customers_per_month > 0:
        cac = monthly_marketing_spend / new_customers_per_month
    else:
        cac = 0
    
    # Calculate LTV
    avg_lifetime_months = 1 / monthly_churn_rate if monthly_churn_rate > 0 else 60
    ltv = arpu * gross_margin * avg_lifetime_months
    
    # LTV/CAC ratio
    ltv_cac_ratio = ltv / cac if cac > 0 else float('inf')
    
    # Payback period
    monthly_gross_per_customer = arpu * gross_margin
    payback_months = cac / monthly_gross_per_customer if monthly_gross_per_customer > 0 else 0
    
    # MRR metrics
    mrr = monthly_revenue
    arr = mrr * 12
    mrr_growth = arpu * new_customers_per_month - mrr * monthly_churn_rate
    
    # Net revenue retention
    nrr = (1 - monthly_churn_rate) * 100
    
    # Health assessment
    health = []
    if ltv_cac_ratio >= 3:
        health.append("LTV/CAC >= 3x — ОТЛИЧНО, бизнес-модель здоровая")
    elif ltv_cac_ratio >= 1.5:
        health.append("LTV/CAC 1.5-3x — НОРМАЛЬНО, есть потенциал для роста")
    else:
        health.append("LTV/CAC < 1.5x — ВНИМАНИЕ, юнит-экономика не сходится")
    
    if payback_months <= 6:
        health.append("Payback <= 6 мес — ОТЛИЧНО")
    elif payback_months <= 12:
        health.append("Payback 6-12 мес — НОРМАЛЬНО")
    else:
        health.append("Payback > 12 мес — ДОЛГО, нужна оптимизация")
    
    if monthly_churn_rate <= 0.03:
        health.append("Churn <= 3% — ОТЛИЧНО")
    elif monthly_churn_rate <= 0.07:
        health.append("Churn 3-7% — НОРМАЛЬНО для B2C")
    else:
        health.append("Churn > 7% — ВЫСОКИЙ, нужна работа над retention")
    
    results = {
        "metrics": {
            "MRR_EUR": round(mrr),
            "ARR_EUR": round(arr),
            "ARPU_EUR": round(arpu, 2),
            "total_customers": total_customers,
            "new_per_month": new_customers_per_month,
            "monthly_churn": f"{monthly_churn_rate*100:.1f}%",
        },
        "unit_economics": {
            "LTV_EUR": round(ltv),
            "CAC_EUR": round(cac),
            "LTV_CAC_ratio": round(ltv_cac_ratio, 2),
            "payback_months": round(payback_months, 1),
            "gross_margin": f"{gross_margin*100:.0f}%",
            "avg_lifetime_months": round(avg_lifetime_months, 1),
        },
        "growth": {
            "MRR_growth_EUR": round(mrr_growth),
            "net_revenue_retention": f"{nrr:.1f}%",
        },
        "health_assessment": health,
        "recommendations": []
    }
    
    # Recommendations
    if ltv_cac_ratio < 3 and cac > 0:
        target_cac = ltv / 3
        results["recommendations"].append(f"Снизить CAC до {round(target_cac)} EUR для достижения LTV/CAC = 3x")
    if monthly_churn_rate > 0.05:
        results["recommendations"].append(f"Снизить churn до 3-5% — это увеличит LTV на {round((1/0.03 - avg_lifetime_months) * arpu * gross_margin)} EUR")
    if payback_months > 12:
        results["recommendations"].append("Оптимизировать воронку для ускорения payback до 6-12 мес")
    
    return json.dumps(results, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# TOOL 3: P&L Forecast
# ─────────────────────────────────────────────

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
    """
    P&L and Cash Flow forecast for 12 months.
    
    Args:
        monthly_revenue: Starting monthly revenue in EUR
        revenue_growth_monthly: Monthly revenue growth rate (0.05 = 5%)
        cogs_percent: Cost of goods sold as % of revenue (0.30 = 30%)
        salaries: Monthly salary expenses in EUR
        rent: Monthly rent in EUR
        marketing: Monthly marketing spend in EUR
        other_opex: Other monthly operating expenses in EUR
        tax_rate: Corporate tax rate (0.125 = 12.5% Cyprus)
        forecast_months: Number of months to forecast (default 12)
    
    Returns:
        Monthly P&L forecast with totals and key ratios
    """
    monthly_data = []
    total_revenue = 0
    total_cogs = 0
    total_opex = 0
    total_tax = 0
    total_net = 0
    cumulative_cash = 0
    
    revenue = monthly_revenue
    fixed_opex = salaries + rent + marketing + other_opex
    
    for month in range(1, forecast_months + 1):
        if month > 1:
            revenue = revenue * (1 + revenue_growth_monthly)
        
        cogs = revenue * cogs_percent
        gross_profit = revenue - cogs
        gross_margin = gross_profit / revenue * 100 if revenue > 0 else 0
        
        opex = fixed_opex
        ebitda = gross_profit - opex
        ebitda_margin = ebitda / revenue * 100 if revenue > 0 else 0
        
        tax = max(0, ebitda * tax_rate)
        net_profit = ebitda - tax
        net_margin = net_profit / revenue * 100 if revenue > 0 else 0
        
        cumulative_cash += net_profit
        
        total_revenue += revenue
        total_cogs += cogs
        total_opex += opex
        total_tax += tax
        total_net += net_profit
        
        monthly_data.append({
            "month": month,
            "revenue": round(revenue),
            "cogs": round(cogs),
            "gross_profit": round(gross_profit),
            "opex": round(opex),
            "ebitda": round(ebitda),
            "tax": round(tax),
            "net_profit": round(net_profit),
            "cumulative_cash": round(cumulative_cash),
        })
    
    # Find break-even month
    breakeven_month = None
    cum = 0
    r = monthly_revenue
    for m in range(1, forecast_months + 1):
        if m > 1: r = r * (1 + revenue_growth_monthly)
        gp = r * (1 - cogs_percent)
        net = (gp - fixed_opex) * (1 - tax_rate)
        cum += net
        if cum > 0 and breakeven_month is None:
            breakeven_month = m
    
    # Stress test: 3 scenarios
    scenarios = {}
    for name, growth_adj in [("optimistic", 0.03), ("base", 0), ("pessimistic", -0.03)]:
        adj_growth = revenue_growth_monthly + growth_adj
        r = monthly_revenue
        t_rev = 0
        t_net = 0
        for m in range(1, forecast_months + 1):
            if m > 1: r = r * (1 + adj_growth)
            gp = r * (1 - cogs_percent)
            net = (gp - fixed_opex) * (1 - tax_rate)
            t_rev += r
            t_net += net
        scenarios[name] = {
            "total_revenue": round(t_rev),
            "total_net_profit": round(t_net),
            "avg_monthly_profit": round(t_net / forecast_months),
        }
    
    results = {
        "summary": {
            "total_revenue_EUR": round(total_revenue),
            "total_net_profit_EUR": round(total_net),
            "avg_gross_margin": f"{(1 - cogs_percent) * 100:.0f}%",
            "avg_net_margin": f"{total_net / total_revenue * 100:.1f}%" if total_revenue > 0 else "0%",
            "breakeven_month": breakeven_month,
            "tax_rate": f"{tax_rate * 100:.1f}%",
        },
        "monthly_forecast": monthly_data,
        "stress_test": scenarios,
    }
    
    return json.dumps(results, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# TOOL 4: Tax Calculator
# ─────────────────────────────────────────────

TAX_DATA = {
    "Cyprus": {"corporate": 0.125, "ip_box": 0.025, "vat": 0.19, "dividend_withholding": 0, "min_wage": 0, "setup_cost": 3000, "annual_cost": 5000, "notes": "15% from 2026. IP Box 2.5% for qualifying IP. No dividend withholding tax. EU member."},
    "UAE": {"corporate": 0.09, "ip_box": None, "vat": 0.05, "dividend_withholding": 0, "min_wage": 0, "setup_cost": 5000, "annual_cost": 8000, "notes": "9% above 375K AED (~93K EUR). Free zones may have 0% for qualifying activities. No personal income tax."},
    "Hong_Kong": {"corporate": 0.165, "ip_box": None, "vat": 0, "dividend_withholding": 0, "min_wage": 0, "setup_cost": 2000, "annual_cost": 4000, "notes": "8.25% on first 2M HKD (~235K EUR), 16.5% above. No VAT/GST. Territorial taxation."},
    "Estonia": {"corporate": 0, "ip_box": None, "vat": 0.22, "dividend_withholding": 0.20, "min_wage": 820, "setup_cost": 1500, "annual_cost": 3000, "notes": "0% on retained profits. 20% on distributed profits (14% for regular distributions). E-residency available."},
    "Spain": {"corporate": 0.25, "ip_box": 0.10, "vat": 0.21, "dividend_withholding": 0.19, "min_wage": 1134, "setup_cost": 3500, "annual_cost": 6000, "notes": "25% standard. 15% for first 2 years. Patent Box 10%. Beckham Law for expats."},
    "Portugal": {"corporate": 0.21, "ip_box": None, "vat": 0.23, "dividend_withholding": 0.28, "min_wage": 870, "setup_cost": 3000, "annual_cost": 5000, "notes": "21% standard. 17% for first 50K EUR (SME). NHR regime for 10 years (flat 20% on Portuguese income)."},
    "Malta": {"corporate": 0.35, "ip_box": None, "vat": 0.18, "dividend_withholding": 0, "min_wage": 835, "setup_cost": 3000, "annual_cost": 5000, "notes": "35% nominal but 5% effective through refund system. EU member. Gaming/fintech hub."},
    "Ireland": {"corporate": 0.125, "ip_box": 0.0625, "vat": 0.23, "dividend_withholding": 0.25, "min_wage": 2080, "setup_cost": 4000, "annual_cost": 7000, "notes": "12.5% trading income. 15% from 2024 for large multinationals (Pillar 2). IP regime 6.25%. EU member."},
}


@mcp.tool()
def tax_calculator(
    annual_revenue: float,
    profit_margin: float = 0.30,
    jurisdictions: str = "Cyprus,UAE,Estonia,Hong_Kong",
    distribute_profits: bool = False,
    has_ip: bool = False
) -> str:
    """
    Compare tax burden across jurisdictions for a business.
    
    Args:
        annual_revenue: Annual revenue in EUR
        profit_margin: Net profit margin before tax (0.30 = 30%)
        jurisdictions: Comma-separated list of countries (Cyprus,UAE,Estonia,Hong_Kong,Spain,Portugal,Malta,Ireland)
        distribute_profits: Whether profits will be distributed as dividends
        has_ip: Whether the business has qualifying intellectual property
    
    Returns:
        Tax comparison across selected jurisdictions
    """
    profit = annual_revenue * profit_margin
    countries = [j.strip() for j in jurisdictions.split(",")]
    
    comparison = []
    
    for country in countries:
        data = TAX_DATA.get(country)
        if not data:
            comparison.append({"country": country, "error": f"Unknown jurisdiction. Available: {', '.join(TAX_DATA.keys())}"})
            continue
        
        # Determine effective rate
        if has_ip and data.get("ip_box"):
            effective_rate = data["ip_box"]
            rate_type = "IP Box"
        else:
            effective_rate = data["corporate"]
            rate_type = "Standard"
        
        corporate_tax = profit * effective_rate
        
        # Dividend withholding
        dividend_tax = 0
        if distribute_profits:
            after_corporate = profit - corporate_tax
            dividend_tax = after_corporate * data["dividend_withholding"]
        
        total_tax = corporate_tax + dividend_tax
        total_rate = total_tax / profit * 100 if profit > 0 else 0
        after_tax_profit = profit - total_tax
        
        # Total cost of ownership
        total_annual_cost = total_tax + data["annual_cost"]
        
        comparison.append({
            "country": country.replace("_", " "),
            "rate_type": rate_type,
            "effective_corporate_rate": f"{effective_rate*100:.1f}%",
            "corporate_tax_EUR": round(corporate_tax),
            "dividend_withholding_EUR": round(dividend_tax),
            "total_tax_EUR": round(total_tax),
            "effective_total_rate": f"{total_rate:.1f}%",
            "after_tax_profit_EUR": round(after_tax_profit),
            "setup_cost_EUR": data["setup_cost"],
            "annual_maintenance_EUR": data["annual_cost"],
            "total_annual_cost_EUR": round(total_annual_cost),
            "vat_rate": f"{data['vat']*100:.0f}%",
            "notes": data["notes"],
        })
    
    # Sort by total tax
    comparison.sort(key=lambda x: x.get("total_tax_EUR", 999999))
    
    # Summary
    if comparison and "error" not in comparison[0]:
        best = comparison[0]
        worst = comparison[-1]
        savings = worst.get("total_tax_EUR", 0) - best.get("total_tax_EUR", 0)
    else:
        savings = 0
    
    results = {
        "input": {
            "annual_revenue_EUR": annual_revenue,
            "profit_margin": f"{profit_margin*100:.0f}%",
            "taxable_profit_EUR": round(profit),
            "distribute_profits": distribute_profits,
            "has_ip": has_ip,
        },
        "comparison": comparison,
        "summary": {
            "best_jurisdiction": comparison[0].get("country", "N/A") if comparison else "N/A",
            "potential_annual_savings_EUR": round(savings),
        }
    }
    
    return json.dumps(results, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="sse")
