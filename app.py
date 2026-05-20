import streamlit as st
import quantale_core as core

# 1. Initialize the Quantale logic
q = core.build_project_quantale()

# --- Page Config ---
st.set_page_config(page_title="Project Resilience Analyzer", page_icon="🛡️")

st.title("🛡️ Project Resilience Analyzer")
st.markdown("""
This dashboard uses **Residuated Quantale** logic to calculate bottleneck risks 
and safety margins for your project dependencies.
""")

# --- Sidebar: Domain Info ---
with st.sidebar:
    st.header("Quantale Domain")
    st.info(f"**Domain:** Project Risk\n\n**Elements:** {', '.join(core.MY_ELEMENTS)}")
    st.write("---")
    st.write("**Math Check:**")
    adj = q.verify_adjunction()
    if adj["adjunction_holds"]:
        st.success("Adjunction Laws Verified ✅")

# --- Step 1: Bottleneck Assessment ---
st.header("1. Dependency Assessment")
st.subheader("What is the current health of your dependencies?")

col1, col2, col3 = st.columns(3)

with col1:
    dep1 = st.selectbox("Vendor A Status", core.MY_ELEMENTS, index=4)
with col2:
    dep2 = st.selectbox("Infrastructure Status", core.MY_ELEMENTS, index=4)
with col3:
    dep3 = st.selectbox("Team Status", core.MY_ELEMENTS, index=3)

# Calculate Bottleneck (Stage 6 - Monoid Product)
current_health = q.big_meet([dep1, dep2, dep3])

st.metric(label="AGGREGATED PROJECT HEALTH", value=current_health.upper())
st.caption("Determined by the 'Weakest Link' bottleneck logic (⊗).")

# --- Step 2: Risk Budgeting ---
st.write("---")
st.header("2. Risk Budgeting (The Residual)")
st.write("If you add a new sub-contractor, how much risk can you afford?")

limit = st.select_slider(
    "What is the MINIMUM status allowed for the final result?",
    options=core.MY_ELEMENTS,
    value="behind_schedule"
)

# Calculate the Right Residual (Stage 8: a → c)
# This solves: current_health ⊗ X ≤ limit
risk_budget = q.right_residual(current_health, limit)

st.subheader(f"Your Max Allowable Risk: :green[{risk_budget.upper()}]")

# --- Step 3: Actionable Advice ---
st.write("---")
st.header("3. Actionable Advice")

# Use Stage 3 (Poset Order) to give advice
if q.is_bottom(risk_budget):
    st.error("**CRITICAL:** You have NO safety margin. Any further risk will crash the project below your limit.")
elif q.le(risk_budget, current_health):
    st.warning(f"**CAUTION:** To stay safe, your next dependency must be at least as healthy as '{risk_budget}'.")
else:
    st.success("**STRATEGY:** You have a resilience buffer. You can afford some minor risks in new sub-tasks.")

# --- Step 4: Logic Table (Optional Visual) ---
with st.expander("View Right Residual Table (a → c)"):
    st.write("This table shows the 'Risk Budget' for every possible scenario in your domain.")
    # Create a simple markdown table
    header = "| a \ c | " + " | ".join(core.MY_ELEMENTS) + " |"
    sep = "|---|" + "---| " * len(core.MY_ELEMENTS)
    rows = []
    for a in core.MY_ELEMENTS:
        row = f"| **{a}** | " + " | ".join([q.right_residual(a, c) for c in core.MY_ELEMENTS]) + " |"
        rows.append(row)
    st.markdown(header + "\n" + sep + "\n" + "\n".join(rows))