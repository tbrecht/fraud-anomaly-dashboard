# Fraud & Anomaly Detection Dashboard

![Run Python Tests](https://github.com/tbrecht/fraud-anomaly-dashboard/actions/workflows/tests.yml/badge.svg)

Interactive fraud investigation and anomaly detection project built in Python using explainable risk scoring, behavioral analytics, transaction review workflows, and an investigator-style Streamlit dashboard.

This project demonstrates how suspicious activity can be prioritized using transparent fraud signals rather than a black-box model.

---

## Business Case

Fraud teams often need to review large volumes of transactions with limited investigation time. A useful analytics workflow should help answer:

1. Which transactions appear most suspicious?
2. Why was a transaction flagged?
3. Which risk signals are driving the score?
4. Are high-scoring transactions enriched for known fraud?
5. How can an investigator review suspicious activity quickly?

This project simulates that workflow using explainable scoring logic, transaction-level explanations, Excel reporting, automated tests, and an interactive dashboard.

---

## Dashboard Preview

### Dashboard Overview

![Dashboard Overview](screenshots/dashboard_overview.png)

Executive view showing transaction counts, fraud prevalence, risk distribution, and fraud enrichment.

### Fraud Investigator

![Fraud Investigator](screenshots/fraud_investigator.png)

Interactive investigation view showing composite risk score, risk gauge, human-readable explanations, velocity metrics, online transaction handling, and travel-aware scoring adjustments.

### Risk Map

![Risk Map](screenshots/risk_map.png)

Geographic review of suspicious merchant activity. Distance risk is automatically reduced for online-style transactions.

### Risk Driver Analysis

![Risk Driver Analysis](screenshots/risk_drivers_analysis.png)

Analytical layer showing primary fraud drivers, risk relationships, fraud enrichment, and amount-versus-score behavior.

---

## Sample Outputs

The repository includes a curated sample output workbook so reviewers can inspect results without running the full analysis locally.

| Output | Description |
|---|---|
| `sample_outputs/fraud_analysis_output.xlsx` | Excel workbook with executive summary, top suspicious transactions, risk summaries, fraud enrichment analysis, score distribution, model breakdown, and limitations |

---

## What This Project Demonstrates

- Building explainable fraud and anomaly detection logic
- Creating behavioral risk signals from transaction data
- Translating model outputs into investigator-friendly explanations
- Evaluating whether high-scoring transactions are enriched for known fraud
- Producing Excel reporting outputs for analyst review
- Designing an interactive Streamlit dashboard for fraud investigation
- Adding automated tests and GitHub Actions to verify key project assets

---

## Project Workflow

    Raw transaction data
        |
        v
    Configuration layer: fraud_config.json
        |
        v
    Feature engineering: fraud_analysis.py
        |
        v
    Behavioral signal creation
        |
        v
    Composite risk scoring
        |
        v
    Excel reporting output
        |
        v
    Streamlit dashboard: dashboard.py
        |
        v
    Investigator review

---

## Repository Structure

    fraud-anomaly-dashboard/

    .github/
    - workflows/
      - tests.yml

    fraud_analysis.py
    dashboard.py
    fraud_config.json
    requirements.txt
    README.md

    sample_outputs/
    - fraud_analysis_output.xlsx

    screenshots/
    - dashboard_overview.png
    - fraud_investigator.png
    - risk_map.png
    - risk_drivers_analysis.png

    tests/
    - test_config.py
    - test_sample_output.py

---

## Dataset

The project was developed using local transaction datasets:

    fraudTrain.csv
    fraudTest.csv

The raw datasets are intentionally excluded from the repository because they are large data files. The repository includes the code, configuration, screenshots, tests, and curated sample output workbook.

Training dataset size used locally:

    1,296,675 transactions

Testing dataset size used locally:

    555,719 transactions

Observed fraud prevalence:

    Approximately 0.58%

---

## Key Components

### 1. Configuration Layer

The project uses `fraud_config.json` to define source files, output files, and expected column mappings.

The configuration includes mappings for:

- Transaction timestamp
- Customer identifier
- Merchant
- Category
- Amount
- Customer latitude and longitude
- Merchant latitude and longitude
- Fraud label

This makes the workflow easier to inspect and adjust without hard-coding every field reference throughout the analysis.

---

### 2. Fraud Signal Engineering

The analysis creates several explainable transaction-level risk signals.

Signals include:

- Amount anomaly
- Transaction velocity
- Geographic distance
- Overnight activity
- Merchant rarity
- Online transaction adjustment
- Travel transaction adjustment

The goal is not only to rank suspicious transactions, but also to explain why each transaction was flagged.

---

## Fraud Signals

### Amount Risk

Amount risk measures how unusual a transaction amount is compared with the customer’s average transaction amount.

Large deviations increase risk. Travel-related transactions receive reduced amount sensitivity because higher spending may be expected in travel contexts.

Example:

    A customer who normally spends $40 makes a $600 hotel purchase.
    The amount is unusual, but travel context reduces the risk contribution.

---

### Velocity Risk

Velocity risk captures recent transaction bursts using behavioral windows.

The project evaluates:

    Transactions in the last 1 hour
    Transactions in the last 24 hours

This helps identify rapid activity that may require review.

---

### Distance Risk

Distance risk estimates the physical distance between the customer’s home location and the merchant location.

Online-style categories reduce distance impact because long customer-to-merchant distance can be normal for online purchases.

Examples of online-style categories:

    shopping_net
    misc_net
    grocery_net

---

### Time Risk

Time risk flags overnight transactions.

The overnight window used in this project is:

    11 PM to 5 AM

This signal is treated as one factor, not proof of fraud.

---

### Merchant Rarity Signal

Merchant rarity measures how frequently a merchant appears in the transaction history.

A rare merchant is not automatically fraudulent. It is one signal that should be interpreted alongside amount, velocity, distance, time, and transaction context.

---

## Composite Risk Score

The final composite risk score combines the explainable fraud signals.

| Risk Area | Weight | Description |
|---|---:|---|
| Amount Risk | 25% | Unusual transaction amount relative to customer average |
| Velocity Risk | 25% | Recent transaction frequency using 1-hour and 24-hour windows |
| Distance Risk | 15% | Customer-to-merchant distance, downweighted for online-style categories |
| Time Risk | 10% | Overnight transaction activity |
| Merchant Rarity Signal | 25% | Relative merchant rarity in the transaction history |

Score range:

    0 = Lowest relative concern
    100 = Highest relative concern

Risk bands:

| Score Range | Risk Band |
|---:|---|
| 0 to 24.9 | Low |
| 25 to 49.9 | Moderate |
| 50 to 74.9 | High |
| 75 to 100 | Critical |

A risk score of 70 does not mean there is a 70% probability of fraud. It means the transaction ranks high relative to other transactions based on the project’s weighted fraud signals.

---

## Evaluation Layer

The project evaluates whether higher-risk transactions show increased fraud concentration.

Evaluation groups include:

- Top 100 scored transactions
- Top 500 scored transactions
- Top 1,000 scored transactions
- Full dataset

This helps determine whether the risk scoring logic is meaningfully prioritizing suspicious transactions for review.

---

## Output Workbook

The analysis generates:

    fraud_analysis_output.xlsx

The curated sample version is available at:

    sample_outputs/fraud_analysis_output.xlsx

Workbook sheets include:

- `Executive_Summary`
- `Top_Suspicious`
- `Risk_Summary`
- `Fraud_By_Risk`
- `Model_Evaluation`
- `Score_Distribution`
- `Model_Breakdown`
- `Limitations`

---

## Dashboard Features

### Executive KPIs

The dashboard displays:

- Transactions reviewed
- Known fraud count
- Fraud rate
- Critical transaction count

### Fraud Investigator

The investigator view supports transaction-level review and displays:

- Risk score
- Fraud label
- Primary driver
- Merchant
- Category
- Distance
- Travel flag
- Online flag
- Velocity windows
- Human-readable explanation

### Visualizations

Dashboard visualizations include:

- Donut chart
- Fraud enrichment chart
- Risk trend analysis
- Geographic transaction map
- Risk gauge
- Treemap
- Scatter analysis
- Transaction review table

---

## Automated Testing

The project includes automated tests for configuration integrity and sample output validation. Tests run locally with `pytest` and automatically through GitHub Actions on pushes and pull requests to `master`.

Current test coverage includes:

### Configuration Tests

- Confirms `fraud_config.json` exists
- Confirms required top-level config keys exist
- Confirms required column mappings are populated

### Sample Output Tests

- Confirms the curated output workbook exists
- Confirms the workbook contains expected report sheets

Run tests locally with:

    PYTHONPATH=. python3 -m pytest tests/

---

## How To Run

Create a virtual environment:

    python3 -m venv .venv

Activate the environment:

    source .venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

Run the fraud analysis workflow:

    python3 fraud_analysis.py

Launch the dashboard:

    streamlit run dashboard.py

Run tests:

    PYTHONPATH=. python3 -m pytest tests/

---

## Skills Demonstrated

### Analytics

- Fraud detection
- Anomaly detection
- Behavioral scoring
- Feature engineering
- Explainable analytics
- Risk ranking
- Fraud enrichment evaluation

### Technical

- Python
- pandas
- NumPy
- OpenPyXL
- Streamlit
- Plotly
- pytest
- GitHub Actions
- Configuration-driven workflows

### Business

- Fraud investigation
- Risk communication
- Decision support
- Human-readable reporting
- Investigator workflow design
- Transparent model interpretation

---

## Why This Project Matters

Fraud analytics tools need to do more than assign scores. They need to help investigators understand what happened, why a transaction was flagged, and where to focus review time.

This project emphasizes explainability, reviewability, and practical decision support. It shows how transaction data can be transformed into fraud risk signals, prioritized review lists, workbook outputs, and an interactive dashboard.

---

## Limitations

This project is designed for portfolio and demonstration purposes.

Known limitations:

- Risk score is not a fraud probability
- Distance logic is simplified
- Travel logic is category-based
- Merchant rarity is contextual
- Rule-based scoring is used intentionally
- Production systems would benefit from card-present indicators, merchant network analysis, device data, account history, and supervised machine learning comparison layers

---

## Disclaimer

Created for portfolio and demonstration purposes.

Risk scores represent relative transaction ranking and should not be interpreted as fraud probabilities or production fraud decisions.