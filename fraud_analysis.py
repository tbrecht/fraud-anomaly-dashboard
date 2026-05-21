import pandas as pd
import numpy as np
import json

with open("fraud_config.json", "r") as f:
    CONFIG = json.load(f)

TRAIN_FILE = CONFIG["train_file"]
OUTPUT_FILE = CONFIG["output_file"]

COLUMNS = CONFIG["columns"]

TIME_COL = COLUMNS["transaction_time"]
CUSTOMER_COL = COLUMNS["customer"]
MERCHANT_COL = COLUMNS["merchant"]
CATEGORY_COL = COLUMNS["category"]
AMOUNT_COL = COLUMNS["amount"]
CUST_LAT = COLUMNS["customer_lat"]
CUST_LONG = COLUMNS["customer_long"]
MERCH_LAT = COLUMNS["merchant_lat"]
MERCH_LONG = COLUMNS["merchant_long"]
FRAUD_COL = COLUMNS["fraud_label"]


def normalize_score(series):
    series = pd.to_numeric(series, errors="coerce").fillna(0)

    if series.max() == series.min():
        return pd.Series(np.zeros(len(series)), index=series.index)

    return ((series - series.min()) / (series.max() - series.min())) * 100


def capped_normalize_score(series, upper_quantile=0.995):
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    cap = series.quantile(upper_quantile)
    capped = series.clip(upper=cap)
    return normalize_score(capped)


def haversine_distance(lat1, lon1, lat2, lon2):
    radius = 3959

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arcsin(np.sqrt(a))

    return radius * c


def risk_level(score):
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Moderate"
    return "Low"


def detect_online_like_transaction(category):
    category = str(category).lower()

    online_indicators = [
        "_net",
        "shopping_net",
        "grocery_net",
        "misc_net"
    ]

    return any(indicator in category for indicator in online_indicators)


def detect_travel_transaction(category):
    category = str(category).lower()

    travel_categories = [
        "travel",
        "airline",
        "hotel",
        "lodging",
        "transport",
        "taxi"
    ]

    return any(term in category for term in travel_categories)


def primary_driver(row):
    drivers = {
        "Unusual transaction amount (context-adjusted)": row["amount_risk"],
        "High recent transaction velocity": row["velocity_risk"],
        "Large physical-distance signal": row["distance_risk"],
        "Overnight transaction": row["time_risk"],
        "Merchant rarity signal": row["merchant_rarity_signal"]
    }

    return max(drivers, key=drivers.get)


def explanation(row):
    online_note = (
        " Because this appears to be an online-style transaction, geographic distance was downweighted."
        if row["online_like_transaction"] == 1
        else ""
    )

    travel_note = (
        " Because this appears to be a travel-related transaction, amount risk was reduced because higher spending may be expected in this context."
        if row["travel_transaction"] == 1
        else ""
    )

    return (
        f"This transaction was assigned a {row['risk_level']} risk level "
        f"with a composite score of {row['composite_risk_score']:.1f}. "
        f"The strongest driver was: {row['primary_driver']}. "
        f"The transaction amount was ${row[AMOUNT_COL]:,.2f}, "
        f"which was {row['amount_ratio']:.1f}x the customer's average transaction amount. "
        f"The merchant was approximately {row['distance_miles']:.1f} miles from the customer's home location."
        f"{online_note}"
        f"{travel_note}"
    )


print("\nLoading training dataset...")
df = pd.read_csv(TRAIN_FILE)

print(f"Rows loaded: {len(df):,}")

print("\nConverting timestamps...")
df[TIME_COL] = pd.to_datetime(df[TIME_COL])

print("\nBuilding customer baselines...")
customer_avg = (
    df.groupby(CUSTOMER_COL)[AMOUNT_COL]
    .mean()
    .reset_index(name="customer_avg_amount")
)

df = df.merge(customer_avg, on=CUSTOMER_COL, how="left")

df["amount_ratio"] = (
    df[AMOUNT_COL] / df["customer_avg_amount"]
).replace([np.inf, -np.inf], np.nan).fillna(1)

print("\nCalculating geographic distance...")
df["distance_miles"] = haversine_distance(
    df[CUST_LAT],
    df[CUST_LONG],
    df[MERCH_LAT],
    df[MERCH_LONG]
)

df["online_like_transaction"] = df[CATEGORY_COL].apply(
    detect_online_like_transaction
).astype(int)

df["travel_transaction"] = df[CATEGORY_COL].apply(
    detect_travel_transaction
).astype(int)

df["distance_applicable"] = np.where(
    df["online_like_transaction"] == 1,
    0,
    1
)

df["adjusted_distance_miles"] = np.where(
    df["distance_applicable"] == 1,
    df["distance_miles"],
    0
)

print("\nBuilding hourly behavior...")
df["hour"] = df[TIME_COL].dt.hour

df["overnight_flag"] = (
    (df["hour"] <= 5) |
    (df["hour"] >= 23)
).astype(int)

print("\nCalculating true transaction velocity windows...")
df = df.sort_values([CUSTOMER_COL, TIME_COL]).copy()

rolling_source = df.set_index(TIME_COL)

tx_count_1h = (
    rolling_source
    .groupby(CUSTOMER_COL)[AMOUNT_COL]
    .rolling("1h")
    .count()
    .reset_index(level=0, drop=True)
)

tx_count_24h = (
    rolling_source
    .groupby(CUSTOMER_COL)[AMOUNT_COL]
    .rolling("24h")
    .count()
    .reset_index(level=0, drop=True)
)

df["transactions_last_1h"] = np.maximum(tx_count_1h.to_numpy() - 1, 0)
df["transactions_last_24h"] = np.maximum(tx_count_24h.to_numpy() - 1, 0)

print("\nCalculating merchant frequency...")
merchant_counts = (
    df.groupby(MERCHANT_COL)
    .size()
    .reset_index(name="merchant_transaction_count")
)

df = df.merge(merchant_counts, on=MERCHANT_COL, how="left")

print("\nRisk scoring...")
base_amount_risk = capped_normalize_score(df["amount_ratio"])

travel_adjustment = np.where(
    df["travel_transaction"] == 1,
    0.60,
    1.00
)

df["amount_risk"] = base_amount_risk * travel_adjustment
df["distance_risk"] = capped_normalize_score(df["adjusted_distance_miles"])

df["velocity_risk"] = capped_normalize_score(
    (0.65 * df["transactions_last_1h"]) +
    (0.35 * df["transactions_last_24h"])
)

df["time_risk"] = df["overnight_flag"] * 100

merchant_inverse = 1 / df["merchant_transaction_count"]
df["merchant_rarity_signal"] = capped_normalize_score(merchant_inverse)

df["composite_risk_score"] = (
    0.25 * df["amount_risk"]
    + 0.25 * df["velocity_risk"]
    + 0.15 * df["distance_risk"]
    + 0.10 * df["time_risk"]
    + 0.25 * df["merchant_rarity_signal"]
).round(1)

df["risk_level"] = df["composite_risk_score"].apply(risk_level)
df["primary_driver"] = df.apply(primary_driver, axis=1)
df["human_readable_explanation"] = df.apply(explanation, axis=1)

output_cols = [
    TIME_COL,
    CUSTOMER_COL,
    MERCHANT_COL,
    CATEGORY_COL,
    AMOUNT_COL,
    MERCH_LAT,
    MERCH_LONG,
    "distance_miles",
    "adjusted_distance_miles",
    "distance_applicable",
    "online_like_transaction",
    "travel_transaction",
    "amount_ratio",
    "transactions_last_1h",
    "transactions_last_24h",
    "composite_risk_score",
    "risk_level",
    "primary_driver",
    "human_readable_explanation",
    FRAUD_COL
]

scored_output = df[output_cols].copy()

top_suspicious = (
    scored_output
    .sort_values("composite_risk_score", ascending=False)
    .head(1000)
)

risk_summary = (
    scored_output["risk_level"]
    .value_counts()
    .reset_index()
)

risk_summary.columns = ["risk_level", "transaction_count"]

risk_summary["percent_of_transactions"] = (
    risk_summary["transaction_count"] / len(scored_output) * 100
).round(2)

fraud_capture_by_risk = (
    scored_output
    .groupby("risk_level")[FRAUD_COL]
    .agg(
        fraud_count="sum",
        transaction_count="count"
    )
    .reset_index()
)

fraud_capture_by_risk["fraud_rate_percent"] = (
    fraud_capture_by_risk["fraud_count"]
    / fraud_capture_by_risk["transaction_count"]
    * 100
).round(2)

total_frauds = scored_output[FRAUD_COL].sum()

fraud_capture_by_risk["fraud_capture_rate_percent"] = (
    fraud_capture_by_risk["fraud_count"]
    / total_frauds
    * 100
).round(2)

score_distribution = pd.DataFrame({
    "metric": [
        "min_score",
        "q1",
        "median",
        "q3",
        "max_score",
        "mean_score"
    ],
    "value": [
        scored_output["composite_risk_score"].min(),
        scored_output["composite_risk_score"].quantile(0.25),
        scored_output["composite_risk_score"].median(),
        scored_output["composite_risk_score"].quantile(0.75),
        scored_output["composite_risk_score"].max(),
        scored_output["composite_risk_score"].mean()
    ]
})

top_100 = scored_output.sort_values("composite_risk_score", ascending=False).head(100)
top_500 = scored_output.sort_values("composite_risk_score", ascending=False).head(500)
top_1000 = scored_output.sort_values("composite_risk_score", ascending=False).head(1000)

model_evaluation = pd.DataFrame({
    "evaluation_group": [
        "Top 100 scored transactions",
        "Top 500 scored transactions",
        "Top 1,000 scored transactions",
        "Full dataset"
    ],
    "transaction_count": [
        len(top_100),
        len(top_500),
        len(top_1000),
        len(scored_output)
    ],
    "fraud_count": [
        int(top_100[FRAUD_COL].sum()),
        int(top_500[FRAUD_COL].sum()),
        int(top_1000[FRAUD_COL].sum()),
        int(scored_output[FRAUD_COL].sum())
    ],
    "fraud_rate_percent": [
        round(top_100[FRAUD_COL].mean() * 100, 2),
        round(top_500[FRAUD_COL].mean() * 100, 2),
        round(top_1000[FRAUD_COL].mean() * 100, 2),
        round(scored_output[FRAUD_COL].mean() * 100, 2)
    ]
})

executive_summary = pd.DataFrame({
    "section": [
        "Purpose",
        "Dataset size",
        "Fraud rate",
        "Risk scoring method",
        "Distance-risk adjustment",
        "Travel-risk adjustment",
        "Evaluation snapshot",
        "Important note"
    ],
    "summary": [
        "This analysis scores transactions for suspicious behavior using explainable fraud risk signals.",
        f"The training dataset contains {len(scored_output):,} transactions.",
        f"The observed fraud rate is {(scored_output[FRAUD_COL].mean() * 100):.2f}%.",
        "The model combines amount anomaly, recent transaction velocity, physical-distance signal, overnight activity, and merchant rarity signal.",
        "Distance risk is downweighted for online-style categories such as *_net transactions because long customer-to-merchant distance may be normal for online purchases.",
        "Amount risk is reduced for travel-related transactions because higher transaction amounts may be expected in travel contexts.",
        f"The top 1,000 scored transactions had an observed fraud rate of {model_evaluation.loc[2, 'fraud_rate_percent']:.2f}%, compared with {model_evaluation.loc[3, 'fraud_rate_percent']:.2f}% in the full dataset.",
        "The risk score is a relative ranking score, not a probability."
    ]
})

model_breakdown = pd.DataFrame({
    "component": [
        "Amount Risk",
        "Velocity Risk",
        "Distance Risk",
        "Time Risk",
        "Merchant Rarity Signal"
    ],
    "weight": [
        "25%",
        "25%",
        "15%",
        "10%",
        "25%"
    ],
    "description": [
        "How unusual the transaction amount is relative to the customer's average transaction amount. Travel-related transactions receive reduced amount sensitivity.",
        "True recent transaction velocity using 1-hour and 24-hour customer windows.",
        "Physical distance between customer home and merchant location, downweighted for online-style categories.",
        "Whether the transaction occurred overnight.",
        "How rare the merchant is in the full transaction history. This is a rarity signal, not proof of fraud."
    ]
})

limitations = pd.DataFrame({
    "limitation": [
        "Risk score is not probability",
        "Online transaction distance",
        "Travel transaction amounts",
        "Merchant rarity interpretation",
        "Velocity window limitations",
        "Rule-based scoring"
    ],
    "detail": [
        "A score of 70 does not mean a 70% chance of fraud. It means the transaction ranked high relative to other transactions.",
        "Distance is downweighted for online-style categories, but real production systems would use card-present/card-not-present indicators if available.",
        "Travel-related transactions receive reduced amount sensitivity, but real systems would benefit from itinerary, merchant type, and cardholder travel-notification data.",
        "Rare merchants are not automatically suspicious. Merchant rarity is only one signal and should be reviewed with other drivers.",
        "The velocity feature uses 1-hour and 24-hour windows, but future versions could include rolling customer baselines and merchant-specific velocity.",
        "This project intentionally uses transparent rule-based scoring rather than a black-box machine learning model."
    ]
})

print("\nSaving summarized Excel output...")

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    executive_summary.to_excel(writer, sheet_name="Executive_Summary", index=False)
    top_suspicious.to_excel(writer, sheet_name="Top_Suspicious", index=False)
    risk_summary.to_excel(writer, sheet_name="Risk_Summary", index=False)
    fraud_capture_by_risk.to_excel(writer, sheet_name="Fraud_By_Risk", index=False)
    model_evaluation.to_excel(writer, sheet_name="Model_Evaluation", index=False)
    score_distribution.to_excel(writer, sheet_name="Score_Distribution", index=False)
    model_breakdown.to_excel(writer, sheet_name="Model_Breakdown", index=False)
    limitations.to_excel(writer, sheet_name="Limitations", index=False)

print("\nComplete.")
print(f"Output saved to: {OUTPUT_FILE}")
print("\nRisk Summary:")
print(risk_summary)
print("\nFraud Capture by Risk:")
print(fraud_capture_by_risk)
print("\nModel Evaluation:")
print(model_evaluation)