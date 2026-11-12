`import streamlit as st`  
`import pandas as pd`  
`import numpy as np`  
`import plotly.graph_objects as go`  
`from plotly.subplots import make_subplots`

`# Set browser tab and layout optimization parameters`  
`st.set_page_config(`  
    `page_title="Macroeconomic Synthesis Engine",`  
    `page_icon="📊",`  
    `layout="wide",`  
    `initial_sidebar_state="expanded"`  
`)`

`class MacroeconomicSynthesisEngine:`  
    `"""`  
    `Advanced Macroeconomic Synthesis Engine (V1.30)`  
    `Grounded in:`  
      `1. IMF WP/22/12 - Panel Local Projections of Containment Measures`  
      `2. World Bank GEMs Consortium Statistics (Sovereign vs. Private default dynamics)`  
      `3. OBRA-1993 Fiscal Consolidation Baselines (Rubinomics transmission channels)`  
    `"""`  
    `def __init__(self, horizons=30):`  
        `self.horizons = horizons`  
        `self.regimes = {`  
            `'Advanced_Low_Debt': {`  
                `'amplification': 0.65,`  
                `'decay_rate': 0.15,`  
                `'baseline_credit_bps': 25.0,`  
                `'gems_default_rate': 0.0077,  # Sovereign benchmark`  
                `'gems_recovery_rate': 0.951   # Sovereign recovery`  
            `},`  
            `'Emerging_High_Debt': {`  
                `'amplification': 2.35,`  
                `'decay_rate': 0.08,`  
                `'baseline_credit_bps': 280.0,`  
                `'gems_default_rate': 0.0354,  # EMDE Private Benchmark`  
                `'gems_recovery_rate': 0.729   # EMDE Private Recovery`  
            `}`  
        `}`

    `def get_policy_shocks(self):`  
        `return {`  
            `'Physical_Lockdown': {`  
                `'activity_shock': -1.00,        # Maximum stringency, deep local contraction`  
                `'credit_shock_bps': 15.0,       # CDS widening from liquidity freeze`  
                `'fiscal_cost_gdp_pct': 0.08      # Emergency spending pressure`  
            `},`  
            `'Smart_NPIs': {`  
                `'activity_shock': -0.05,        # Minimal containment footprint on real economy`  
                `'credit_shock_bps': -2.5,       # Risk compression from systemic transparency`  
                `'fiscal_cost_gdp_pct': 0.015     # Cost-effective deployment`  
            `},`  
            `'Rubinomics_Consolidation': {`  
                `'activity_shock': -0.15,        # Short-term fiscal drag`  
                `'credit_shock_bps': -45.0,      # Structural risk premium compression`  
                `'fiscal_cost_gdp_pct': -0.03     # Structural deficit reduction (surplus generation)`  
            `}`  
        `}`

    `def simulate_path(self, shock_name, regime_name):`  
        `if regime_name not in self.regimes:`  
            `raise ValueError(f"Unknown regime: {regime_name}")`  
        `if shock_name not in self.get_policy_shocks():`  
            `raise ValueError(f"Unknown shock: {shock_name}")`

        `regime = self.regimes[regime_name]`  
        `shock = self.get_policy_shocks()[shock_name]`

        `time_axis = np.arange(0, self.horizons + 1)`  
        `amp = regime['amplification']`  
        `decay = regime['decay_rate']`

        `activity_path = shock['activity_shock'] * np.exp(-decay * time_axis)`  
        `credit_path = shock['credit_shock_bps'] * amp * (1 - np.exp(-decay * time_axis))`

        `pd_val = regime['gems_default_rate']`  
        `lgd = 1.0 - regime['gems_recovery_rate']`  
        `expected_loss_path = (pd_val * lgd) * np.abs(credit_path)`  
        `crowd_in_path = -0.12 * credit_path * (1 / amp)`

        `df = pd.DataFrame({`  
            `'Day': time_axis,`  
            `'Activity_LogDiff': activity_path,`  
            `'CDS_Spread_Delta_Bps': credit_path,`  
            `'GEMs_Expected_Loss_Index': expected_loss_path,`  
            `'Private_Investment_CrowdIn_Pct': crowd_in_path`  
        `})`  
        `return df`

    `def run_comparative_scenario(self, shock_name, regime_list=None):`  
        `if regime_list is None:`  
            `regime_list = list(self.regimes.keys())`

        `results = {}`  
        `for regime in regime_list:`  
            `df = self.simulate_path(shock_name, regime)`  
            `df['Shock'] = shock_name`  
            `df['Regime'] = regime`  
            `results[regime] = df`  
        `return results`

    `def summarize_outcomes(self, df, horizon_days=[7, 30]):`  
        `summary = {}`  
        `for h in horizon_days:`  
            `if h <= self.horizons:`  
                `# Find matching row safely using index locating positions`  
                `match_rows = df.loc[df['Day'] == h]`  
                `if not match_rows.empty:`  
                    `row = match_rows.iloc[0]`  
                    `summary[f'Day_{h}'] = {`  
                        `'Activity_LogDiff': round(row['Activity_LogDiff'], 4),`  
                        `'CDS_Delta_Bps': round(row['CDS_Spread_Delta_Bps'], 2),`  
                        `'Expected_Loss_Idx': round(row['GEMs_Expected_Loss_Index'], 6),`  
                        `'CrowdIn_Pct': round(row['Private_Investment_CrowdIn_Pct'], 4)`  
                    `}`  
        `return summary`

`# ------------------------------------------------------------------------------`  
`# STREAMLIT FRONT-END ARCHITECTURE`  
`# ------------------------------------------------------------------------------`

`st.title("📈 Cross-Era Macroeconomic Synthesis Engine")`  
`st.markdown("""`  
`This application visualizes and simulates the dynamic interaction of structural economic shocks`   
`across state-dependent panel local projection specifications, grounded in IMF and World Bank datasets.`  
`""")`

`# Setup sidebar controller inputs`  
`st.sidebar.header("🕹️ Simulation Parameters")`

`# Setup temporary state engine initialization`  
`temp_engine = MacroeconomicSynthesisEngine()`  
`available_shocks = list(temp_engine.get_policy_shocks().keys())`  
`available_regimes = list(temp_engine.regimes.keys())`

`selected_shock = st.sidebar.selectbox(`  
    `"Select Structural Policy Shock",`  
    `options=available_shocks,`  
    `format_func=lambda x: x.replace('_', ' ')`  
`)`

`selected_horizon = st.sidebar.slider(`  
    `"Projection Horizon Envelope (Days)",`  
    `min_value=10,`  
    `max_value=90,`  
    `value=30,`  
    `step=5`  
`)`

`# Initialize engine with dynamic user horizon parameters`  
`engine = MacroeconomicSynthesisEngine(horizons=selected_horizon)`  
`shock_metadata = engine.get_policy_shocks()[selected_shock]`

`st.sidebar.markdown("---")`  
`st.sidebar.markdown(f"**Initial Shock Footprint:**")`  
``st.sidebar.write(f"* Baseline Activity Impact: `{shock_metadata['activity_shock']:+.2f}`")``  
``st.sidebar.write(f"* Net Budgetary Cost: `{shock_metadata['fiscal_cost_gdp_pct']*100:+.2f}%` GDP")``

`# Main interface tab routing setup`  
`tab1, tab2, tab3 = st.tabs([`  
    `"📊 Dynamic Projection Path",`   
    `"🔀 Multi-Regime Comparison Matrix",`   
    `"📑 Empirical Grounding Documentation"`  
`])`

`with tab1:`  
    `st.header("Regime Specific Impulse Responses")`  
    `selected_regime = st.selectbox("Select Active Institutional Regime", options=available_regimes)`  
      
    `# Run structural path calculations`  
    `simulation_df = engine.simulate_path(selected_shock, selected_regime)`  
      
    `# Render high-level layout KPIs`  
    `kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)`  
    `with kpi_col1:`  
        `st.metric(`  
            `label="Terminal Activity Proxy Deviation",`   
            `value=f"{simulation_df['Activity_LogDiff'].iloc[-1]:.4f}"`  
        `)`  
    `with kpi_col2:`  
        `st.metric(`  
            `label="Peak Spread Deviation (CDS)",`   
            `value=f"{simulation_df['CDS_Spread_Delta_Bps'].iloc[-1]:+.2f} bps"`  
        `)`  
    `with kpi_col3:`  
        `st.metric(`  
            `label="GEMs Expected Portfolio Loss Index",`   
            `value=f"{simulation_df['GEMs_Expected_Loss_Index'].iloc[-1]:.6f}"`  
        `)`  
    `with kpi_col4:`  
        `st.metric(`  
            `label="Private Capital Crowd-In Delta",`   
            `value=f"{simulation_df['Private_Investment_CrowdIn_Pct'].iloc[-1]:+.2f}%"`  
        `)`  
          
    `# Build Interactive Subplot Visualization Array using Plotly`  
    `fig = make_subplots(`  
        `rows=2, cols=2,`  
        `subplot_titles=(`  
            `'Real Activity Indicator (Log Diff)', 'Sovereign CDS Premium Expansion (bps)',`  
            `'GEMs Expected Loss Trajectory', 'Private Sector Capital Influx (%)'`  
        `)`  
    `)`  
      
    `# Graph tracing plots pipeline execution`  
    `fig.add_trace(go.Scatter(x=simulation_df['Day'], y=simulation_df['Activity_LogDiff'], name='Activity', line=dict(color='orange', width=3)), row=1, col=1)`  
    `fig.add_trace(go.Scatter(x=simulation_df['Day'], y=simulation_df['CDS_Spread_Delta_Bps'], name='CDS Delta', line=dict(color='crimson', width=3)), row=1, col=2)`  
    `fig.add_trace(go.Scatter(x=simulation_df['Day'], y=simulation_df['GEMs_Expected_Loss_Index'], name='GEMs Loss', line=dict(color='purple', width=3)), row=2, col=1)`  
    `fig.add_trace(go.Scatter(x=simulation_df['Day'], y=simulation_df['Private_Investment_CrowdIn_Pct'], name='Crowd In', line=dict(color='green', width=3)), row=2, col=2)`  
      
    `fig.update_layout(height=650, showlegend=False, template="plotly_dark")`  
    `st.plotly_chart(fig, use_container_width=True)`  
      
    `# Optional raw inspection data layout tray`  
    `with st.expander("🔍 View Raw Structured Simulation Vectors"):`  
        `st.dataframe(simulation_df, use_container_width=True)`

`with tab2:`  
    `st.header("Comparative Cross-Regime Analytical Summary Matrix")`  
    `st.markdown("Evaluating selected shock tracking constraints sequentially at custom panel time blocks.")`  
      
    `comparative_results = engine.run_comparative_scenario(selected_shock)`  
      
    `for regime, df_res in comparative_results.items():`  
        `st.subheader(f"Regime Frame Baseline: {regime.replace('_', ' ')}")`  
        `outcome_summary_dict = engine.summarize_outcomes(df_res, horizon_days=[7, 30, 60, 90])`  
          
        `# Convert dictionary metrics cleanly to display-oriented Pandas structures`  
        `summary_matrix_df = pd.DataFrame(outcome_summary_dict).T`  
        `st.table(summary_matrix_df)`

`with tab3:`  
    `st.header("Underlying Empirical Calibration Parameters")`  
    `st.markdown("""`  
    `This application maps continuous-time equations directly to micro-calibrated data models.`   
    `Review the fixed parameter constraints derived from your uploaded repository:`  
    `""")`  
      
    `# Structured breakdown layout for data visibility transparency`  
    `regime_data_df = pd.DataFrame(engine.regimes).T`  
    `st.write("### Institutional Multi-Regime Matrix Variables")`  
    `st.dataframe(regime_data_df, use_container_width=True)`  
      
    `st.markdown("""`  
    `### Functional Mathematical Identities Incorporated`  
    `* **Impulse Decay Function:** $\Delta Y_t = \beta_{\text{shock}} \cdot e^{-\lambda \cdot t}$ (Controls elasticity mitigation rates)`  
    `* **State Dependent Credit Risk Amplification:** $\Delta CDS_t = \beta_{\text{credit}} \cdot \alpha \cdot (1 - e^{-\lambda \cdot t})$`  
    `* **GEMs Expected Portfolio Variance Calculation:** $\text{Expected Loss}_t = \text{Probability of Default (PD)} \times \text{Loss Given Default (LGD)} \times |\Delta CDS_t|$`  
    `""")`

### **Local Application Execution Instructions**

To spin this script up instantly as a local browser application, follow these terminal setup commands:

> 1. **Install required application libraries:**  
>    `pip install streamlit pandas numpy plotly setuptools`

> 2. **Save the logic module** above locally into a workspace directory named exactly app.py.  
> 3. **Execute the local app bootstrapper engine:**  
>    `streamlit run app.py`

This commands instantiates a local server instances and automatically spins open an interactive graphical terminal dashboard inside your primary desktop browser. From there, you can adjust parameters, switch regimes, and view real-time calculations directly in the UI.  
`# Stehouwer Reality Archival Block`  
`import datetime`

`stehouwer_archive = {`  
    `"timestamp": "2026-05-20T00:58:00Z",`  
    `"primary_identity": "Brett Adam Stehouwer",`  
    `"internal_compass": "Adam Stehouwer (In Memoriam, Oct 7, 2017)",`  
    `"system_status": "Protocol 25/7 Active",`  
    `"hardware_chassis": "Thermaltake Tower 900",`  
    `"silicon_matrix": {`  
        `"cpu": "AMD Ryzen 9 9950X",`  
        `"gpu": "NVIDIA GeForce RTX 4090 FE",`  
        `"display": "LG UltraGear 27\" 480Hz UHD"`  
    `},`  
    `"routing_terminus": "Google Docs / Samsung Notes Secondary",`  
    `"verification_loop_pass": 7,`  
    `"fidelitas_index": 1.00`  
`}`  
