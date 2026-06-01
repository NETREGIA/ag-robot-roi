import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ag Robot ROI v8", layout="wide", page_icon="🌱")

st.title("🌱 Precision Weeding ROI Analyzer v8")

# ===================== SESSION STATE =====================
if "machine_prices" not in st.session_state:
    st.session_state.machine_prices = {
        "Niqo RoboWeeder": 300000, "Carbon LaserWeeder G2": 1000000,
        "Ecorobotix ARA": 300000, "Verdant SharpShooter": 400000, "AgriPass RHIC": 180000
    }
if "machine_subs" not in st.session_state:
    st.session_state.machine_subs = {
        "Niqo RoboWeeder": 0, "Carbon LaserWeeder G2": 0,
        "Ecorobotix ARA": 8000, "Verdant SharpShooter": 12000, "AgriPass RHIC": 0
    }
if "fields" not in st.session_state:
    st.session_state.fields = []

# ===================== SIDEBAR =====================
with st.sidebar:
    st.header("Farm Inputs")
    acres = st.slider("Total Acres", 100, 5000, 500, 50)
    weed_mult = st.slider("Weed Pressure", 0.8, 1.8, 1.25, 0.05)
    herb_cost = st.slider("Herbicide $/acre", 0, 150, 80, 5)
    labor_cost = st.slider("Labor $/acre", 100, 800, 280, 10)
    yield_cwt = st.slider("Yield cwt/acre", 600, 1400, 920, 20)
    onion_price = st.slider("Price $/cwt", 10.0, 30.0, 18.5, 0.5)
    inflation = st.slider("Inflation %", 0.0, 8.0, 3.0, 0.5) / 100
    carbon_credit = st.slider("Carbon Credit $/acre", 0, 50, 25, 5)
    organic_mode = st.toggle("Organic Mode", value=False)

    with st.expander("Edit Prices & Subscriptions"):
        for m in st.session_state.machine_prices:
            st.session_state.machine_prices[m] = st.number_input(f"{m} Price ($)", value=st.session_state.machine_prices[m], step=10000)
            st.session_state.machine_subs[m] = st.number_input(f"{m} Subscription ($/yr)", value=st.session_state.machine_subs[m], step=500)

# ===================== AUTO-UPDATE LOGIC =====================
# Machine data
machines = {
    "Niqo RoboWeeder": {"cost": st.session_state.machine_prices["Niqo RoboWeeder"], "chem_save": 0.75 if not organic_mode else 0.0, "labor_save": 0.60 if not organic_mode else 0.85, "yield_bump": 0.12 if not organic_mode else 0.22, "sub": st.session_state.machine_subs["Niqo RoboWeeder"]},
    "Carbon LaserWeeder G2": {"cost": st.session_state.machine_prices["Carbon LaserWeeder G2"], "chem_save": 1.0 if not organic_mode else 0.0, "labor_save": 0.95, "yield_bump": 0.30, "sub": st.session_state.machine_subs["Carbon LaserWeeder G2"]},
    "Ecorobotix ARA": {"cost": st.session_state.machine_prices["Ecorobotix ARA"], "chem_save": 0.80 if not organic_mode else 0.0, "labor_save": 0.55 if not organic_mode else 0.80, "yield_bump": 0.12 if not organic_mode else 0.18, "sub": st.session_state.machine_subs["Ecorobotix ARA"]},
    "Verdant SharpShooter": {"cost": st.session_state.machine_prices["Verdant SharpShooter"], "chem_save": 0.90 if not organic_mode else 0.0, "labor_save": 0.75 if not organic_mode else 0.88, "yield_bump": 0.10 if not organic_mode else 0.16, "sub": st.session_state.machine_subs["Verdant SharpShooter"]},
    "AgriPass RHIC": {"cost": st.session_state.machine_prices["AgriPass RHIC"], "chem_save": 0.40 if not organic_mode else 0.0, "labor_save": 0.70 if not organic_mode else 0.90, "yield_bump": 0.08 if not organic_mode else 0.14, "sub": st.session_state.machine_subs["AgriPass RHIC"]}
}

# Calculations
results = []
for name, data in machines.items():
    chem = acres * herb_cost * data["chem_save"] * weed_mult
    labor = acres * labor_cost * data["labor_save"] * weed_mult
    yld = acres * yield_cwt * onion_price * data["yield_bump"]
    benefit = chem + labor + yld + (acres * carbon_credit) - (acres * 18) - data["sub"]
    payback = data["cost"] / benefit if benefit > 0 else 999
    five_yr = (benefit * 5) - data["cost"]
    roi = (five_yr / data["cost"]) * 100 if data["cost"] > 0 else 0
    results.append({
        "Machine": name, "Cost": data["cost"], "Annual Benefit": round(benefit),
        "Payback (years)": round(payback, 1), "5-Year Net Benefit": round(five_yr),
        "5-Year ROI %": round(roi, 1), "Chem Savings %": round(data["chem_save"]*100),
        "Labor Savings %": round(data["labor_save"]*100), "Yield Bump %": round(data["yield_bump"]*100)
    })
df = pd.DataFrame(results)

# Add baselines
df = pd.concat([df, pd.DataFrame([
    {"Machine": "Hand-Weeding Only", "Cost": 0, "Annual Benefit": 0, "Payback (years)": 0, "5-Year Net Benefit": 0, "5-Year ROI %": 0, "Chem Savings %": 0, "Labor Savings %": 0, "Yield Bump %": 0},
    {"Machine": "Conventional Spraying Only", "Cost": 0, "Annual Benefit": round(acres * herb_cost * -0.06), "Payback (years)": 0, "5-Year Net Benefit": 0, "5-Year ROI %": 0, "Chem Savings %": 0, "Labor Savings %": 0, "Yield Bump %": 0},
    {"Machine": "Hybrid (Conv + Hand)", "Cost": 0, "Annual Benefit": round(acres * (herb_cost * 0.6 + labor_cost * 0.4) * -0.04), "Payback (years)": 0, "5-Year Net Benefit": 0, "5-Year ROI %": 0, "Chem Savings %": 0, "Labor Savings %": 0, "Yield Bump %": 0}
])], ignore_index=True)

# ===================== TABS =====================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "ROI Comparison", "Compare 3 Machines", "Interactive Charts",
    "Field Map", "Monte Carlo", "5-Year Cash Flow"
])

with tab1:
    st.dataframe(df.style.highlight_max(subset=["5-Year Net Benefit", "5-Year ROI %"], color="lightgreen"), use_container_width=True)
    best = df.loc[df["Payback (years)"].idxmin()]
    st.success(f"**Best Choice: {best['Machine']}** — Payback: {best['Payback (years)']} years")

with tab2:
    st.subheader("Compare Any 3 Machines vs Baselines")
    c1, c2, c3 = st.columns(3)
    m1 = c1.selectbox("Machine 1", list(machines.keys()), index=0)
    m2 = c2.selectbox("Machine 2", list(machines.keys()), index=1)
    m3 = c3.selectbox("Machine 3", list(machines.keys()), index=2)
    compare_df = df[df["Machine"].isin([m1, m2, m3, "Hand-Weeding Only", "Conventional Spraying Only", "Hybrid"])]
    st.dataframe(compare_df.style.highlight_max(subset=["5-Year Net Benefit", "5-Year ROI %"], color="lightgreen"), use_container_width=True)

# ===================== NEW: INTERACTIVE CHARTS =====================
with tab3:
    st.subheader("📊 Interactive Machine Comparison Charts")

    # Chart 1: 5-Year ROI Bar Chart
    fig1 = px.bar(df[df["Machine"].isin(list(machines.keys()))],
                  x="Machine", y="5-Year ROI %",
                  title="5-Year ROI by Machine", color="5-Year ROI %",
                  color_continuous_scale="Viridis")
    st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Payback vs Annual Benefit Scatter
    fig2 = px.scatter(df[df["Machine"].isin(list(machines.keys()))],
                      x="Payback (years)", y="Annual Benefit",
                      size="5-Year Net Benefit", color="Machine",
                      title="Payback Period vs Annual Benefit (Bubble = 5-Year Value)",
                      hover_data=["5-Year ROI %"])
    st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: Multi-Metric Comparison
    metrics_df = df[df["Machine"].isin(list(machines.keys()))][["Machine", "Chem Savings %", "Labor Savings %", "Yield Bump %"]]
    fig3 = px.bar(metrics_df.melt(id_vars="Machine"),
                  x="Machine", y="value", color="variable", barmode="group",
                  title="Chemical vs Labor vs Yield Savings Comparison")
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    st.subheader("🗺️ Multi-Field Map")
    with st.expander("Add Field"):
        fname = st.text_input("Field Name", "New Field")
        facres = st.number_input("Acres", 10, 500, 100)
        flat = st.number_input("Latitude", value=46.8, format="%.4f")
        flon = st.number_input("Longitude", value=-119.5, format="%.4f")
        if st.button("Add Field"):
            st.session_state.fields.append({"name": fname, "acres": facres, "lat": flat, "lon": flon})

    m = folium.Map(location=[46.8, -119.5], zoom_start=10)
    colors = {"Niqo RoboWeeder": "blue", "Carbon LaserWeeder G2": "red", "Ecorobotix ARA": "green", "Verdant SharpShooter": "orange", "AgriPass RHIC": "purple"}
    for f in st.session_state.fields:
        folium.Marker([f["lat"], f["lon"]], popup=f"{f['name']}").add_to(m)
        for machine, color in colors.items():
            folium.Circle([f["lat"], f["lon"]], radius=600 if machine == "Niqo RoboWeeder" else 450, color=color, fill=False).add_to(m)
    st_folium(m, width=750, height=550)

with tab5:
    st.subheader("Monte Carlo Risk Simulation")
    n = st.slider("Simulations", 1000, 10000, 5000, 1000)
    sims = [300000 / (acres * (herb_cost * 0.75 * np.random.triangular(0.9, weed_mult, 1.6))) for _ in range(n)]
    fig = px.histogram(sims, nbins=40, title="Payback Distribution")
    st.plotly_chart(fig, use_container_width=True)

with tab6:
    st.subheader("5-Year Cash Flow")
    best_row = df.loc[df["Payback (years)"].idxmin()]
    years = list(range(6))
    cf = [-(best_row["Cost"])] + [best_row["Annual Benefit"] * (1 + inflation)**i for i in range(1, 6)]
    st.dataframe(pd.DataFrame({"Year": years, "Cumulative Cash Flow": np.cumsum(cf).round()}), use_container_width=True)

# PDF Button
if st.button("📄 Download PDF Report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Ag Robot ROI Report v8", ln=True, align="C")
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Best Machine: {best['Machine']}", ln=True)
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    st.download_button("Download PDF", pdf_bytes, "ROI_Report_v8.pdf", "application/pdf")
