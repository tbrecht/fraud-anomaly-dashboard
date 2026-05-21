import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

OUTPUT_FILE = "fraud_analysis_output.xlsx"

st.set_page_config(
    page_title="Fraud Risk Dashboard",
    layout="wide"
)

st.title("Fraud & Anomaly Detection Dashboard")
st.caption("Explainable transaction risk scoring and fraud investigation interface")

executive = pd.read_excel(OUTPUT_FILE, sheet_name="Executive_Summary")
top_suspicious = pd.read_excel(OUTPUT_FILE, sheet_name="Top_Suspicious")
risk_summary = pd.read_excel(OUTPUT_FILE, sheet_name="Risk_Summary")
fraud_by_risk = pd.read_excel(OUTPUT_FILE, sheet_name="Fraud_By_Risk")
model_evaluation = pd.read_excel(OUTPUT_FILE, sheet_name="Model_Evaluation")
score_dist = pd.read_excel(OUTPUT_FILE, sheet_name="Score_Distribution")
model_breakdown = pd.read_excel(OUTPUT_FILE, sheet_name="Model_Breakdown")
limitations = pd.read_excel(OUTPUT_FILE, sheet_name="Limitations")

total_transactions = risk_summary["transaction_count"].sum()
known_fraud = fraud_by_risk["fraud_count"].sum()
fraud_rate = known_fraud / total_transactions * 100
highest_score = top_suspicious["composite_risk_score"].max()

critical_count = (
    risk_summary.loc[
        risk_summary["risk_level"] == "Critical",
        "transaction_count"
    ].sum()
    if "Critical" in risk_summary["risk_level"].values
    else 0
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Transactions Reviewed", f"{total_transactions:,}")
c2.metric("Known Fraud", f"{known_fraud:,}")
c3.metric("Fraud Rate", f"{fraud_rate:.2f}%")
c4.metric("Critical Risk Transactions", f"{critical_count:,}")

st.divider()

left, right = st.columns([1, 1])

with left:
    st.subheader("Risk Level Mix")

    fig_donut = px.pie(
        risk_summary,
        names="risk_level",
        values="transaction_count",
        hole=0.55,
        title="Share of Transactions by Risk Level"
    )

    fig_donut.update_layout(height=430)
    st.plotly_chart(fig_donut, use_container_width=True)

with right:
    st.subheader("Fraud Enrichment by Review Group")

    fig_eval = px.bar(
        model_evaluation,
        x="evaluation_group",
        y="fraud_rate_percent",
        title="Observed Fraud Rate in Highest-Scored Transactions",
        labels={
            "evaluation_group": "Review Group",
            "fraud_rate_percent": "Observed Fraud Rate %"
        }
    )

    fig_eval.update_layout(
        height=430,
        xaxis_tickangle=-25
    )

    st.plotly_chart(fig_eval, use_container_width=True)

st.divider()

st.subheader("Fraud Rate by Risk Level")

fig_capture = px.line(
    fraud_by_risk.sort_values("fraud_rate_percent"),
    x="risk_level",
    y="fraud_rate_percent",
    markers=True,
    title="Observed Fraud Rate Across Risk Groups",
    labels={
        "risk_level": "Risk Level",
        "fraud_rate_percent": "Fraud Rate %"
    }
)

fig_capture.update_traces(
    line=dict(width=4),
    marker=dict(size=12)
)

fig_capture.update_layout(height=430)
st.plotly_chart(fig_capture, use_container_width=True)

st.divider()

st.subheader("Suspicious Transaction Map")

map_sample = top_suspicious.head(500).copy()

if "merch_lat" in map_sample.columns and "merch_long" in map_sample.columns:
    fig_map = px.scatter_mapbox(
        map_sample,
        lat="merch_lat",
        lon="merch_long",
        color="risk_level",
        size="composite_risk_score",
        hover_data=[
            "merchant",
            "category",
            "amt",
            "composite_risk_score",
            "primary_driver",
            "is_fraud",
            "online_like_transaction"
        ],
        zoom=3,
        height=500,
        title="Top Suspicious Merchant Locations"
    )

    fig_map.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=50, b=0)
    )

    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning("Merchant latitude/longitude columns were not found in the output.")

st.divider()

st.subheader("Fraud Investigator")

selected_index = st.selectbox(
    "Select a suspicious transaction to inspect:",
    top_suspicious.index
)

selected = top_suspicious.loc[selected_index]

i1, i2, i3, i4 = st.columns(4)

i1.metric("Risk Score", round(selected["composite_risk_score"], 1))
i2.metric("Risk Level", selected["risk_level"])
i3.metric("Actual Fraud", int(selected["is_fraud"]))
i4.metric("Amount", f"${selected['amt']:,.2f}")

gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=selected["composite_risk_score"],
        title={"text": "Selected Transaction Risk Score"},
        gauge={
            "axis": {"range": [0, 100]},
            "steps": [
                {"range": [0, 25], "color": "lightgreen"},
                {"range": [25, 50], "color": "khaki"},
                {"range": [50, 75], "color": "orange"},
                {"range": [75, 100], "color": "tomato"}
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": selected["composite_risk_score"]
            }
        }
    )
)

gauge.update_layout(height=350)
st.plotly_chart(gauge, use_container_width=True)

st.markdown("### Why this transaction was flagged")

st.info(selected["human_readable_explanation"])

details_left, details_right = st.columns([1, 1])

with details_left:
    st.markdown(
        f"""
        **Primary driver:** {selected['primary_driver']}  
        **Merchant:** {selected['merchant']}  
        **Category:** {selected['category']}  
        **Distance from home:** {selected['distance_miles']:.1f} miles  
        **Distance used in score:** {selected['adjusted_distance_miles']:.1f} miles  
        """
    )

with details_right:
    st.markdown(
        f"""
        **Amount ratio:** {selected['amount_ratio']:.1f}x customer average  
        **Transactions last 1 hour:** {selected['transactions_last_1h']}  
        **Transactions last 24 hours:** {selected['transactions_last_24h']}  
        **Online-style transaction:** {int(selected['online_like_transaction'])}  
        **Transaction time:** {selected['trans_date_trans_time']}  
        """
    )

st.divider()

left2, right2 = st.columns([1, 1])

with left2:
    st.subheader("Primary Risk Drivers")

    driver_counts = (
        top_suspicious["primary_driver"]
        .value_counts()
        .reset_index()
    )

    driver_counts.columns = ["primary_driver", "count"]

    fig_treemap = px.treemap(
        driver_counts,
        path=["primary_driver"],
        values="count",
        title="Most Common Drivers Among Top Suspicious Transactions"
    )

    fig_treemap.update_layout(height=430)
    st.plotly_chart(fig_treemap, use_container_width=True)

with right2:
    st.subheader("Risk Score vs Transaction Amount")

    fig_scatter = px.scatter(
        top_suspicious.head(1000),
        x="amt",
        y="composite_risk_score",
        color="is_fraud",
        hover_data=[
            "merchant",
            "category",
            "primary_driver",
            "distance_miles",
            "online_like_transaction"
        ],
        title="Do Higher Dollar Transactions Also Carry Higher Risk?",
        labels={
            "amt": "Transaction Amount",
            "composite_risk_score": "Risk Score",
            "is_fraud": "Actual Fraud"
        }
    )

    fig_scatter.update_layout(height=430)
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

st.subheader("Top Suspicious Transactions")

display_cols = [
    "composite_risk_score",
    "risk_level",
    "primary_driver",
    "amt",
    "distance_miles",
    "adjusted_distance_miles",
    "amount_ratio",
    "transactions_last_1h",
    "transactions_last_24h",
    "online_like_transaction",
    "merchant",
    "category",
    "is_fraud"
]

st.dataframe(
    top_suspicious[display_cols].head(25),
    use_container_width=True
)

with st.expander("Model Breakdown"):
    st.dataframe(model_breakdown, use_container_width=True)

with st.expander("Evaluation Details"):
    st.dataframe(model_evaluation, use_container_width=True)
    st.dataframe(fraud_by_risk, use_container_width=True)

with st.expander("Limitations"):
    st.dataframe(limitations, use_container_width=True)

with st.expander("Executive Summary"):
    st.dataframe(executive, use_container_width=True)

with st.expander("Score Distribution"):
    st.dataframe(score_dist, use_container_width=True)