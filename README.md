# 📈 Real-Time Stock Market Data Pipeline on Azure

> An end-to-end real-time data engineering pipeline built on Azure that ingests live stock market data from the Alpha Vantage API, streams it through Azure Event Hubs and Stream Analytics, processes it through a Medallion Architecture using Databricks Delta Live Tables, and delivers daily insights through a Databricks Lakeview Dashboard.

---

##  What is this project?

This project demonstrates how to build a **production-style real-time streaming pipeline** using modern cloud and big data tools. Every day, the pipeline automatically:

1. Fetches real-time stock prices from Alpha Vantage API (MSFT, AAPL, GOOGL, AMZN, TSLA)
2. Streams data through Azure Event Hubs to Stream Analytics
3. Stores raw JSON files in Azure Data Lake Storage Gen2
4. Processes data through Bronze → Silver → Gold layers using Databricks
5. Serves analytics through a live Databricks Lakeview Dashboard

---

## 🏗️ Architecture

![Architecture](https://github.com/PusaAkshay/RealTime-StockMarket-Pipeline/blob/684983c6ec213c44e7105a2149a6d882280ce9f7/Architecture.png)

```
Alpha Vantage API (Stock Prices)
              ↓
  Databricks Notebook (Producer)
  → fetches 5 stocks daily
  → sends to Event Hubs
              ↓
  Azure Event Hubs
  (real-time stream ingestion)
              ↓
  Azure Stream Analytics
  (Event Hubs → ADLS raw/)
              ↓
  ADLS Gen2 — Raw Container
  (stocks/YYYY/MM/DD/HH/*.json)
              ↓
  Databricks Job (Orchestrated)
  ├── Task 1: Autoloader
  │           raw JSON → Bronze Delta Table
  └── Task 2: DLT Pipeline (ETL)
              Bronze → Silver → Gold
              ↓
  Databricks Lakeview Dashboard
  (Stock Market Monitor)
```

---

## 🥉🥈🥇 Medallion Architecture

| Layer | Container | Description |
|-------|-----------|-------------|
| **Raw** | `raw` | Original JSON files from Alpha Vantage API — never modified |
| **Bronze** | `bronze` | Parsed Delta table via Autoloader — raw schema preserved |
| **Silver** | Unity Catalog (`silver` ext. location) | Cleaned and validated data — DLT quality rules applied |
| **Gold** | Unity Catalog (`silver` ext. location) | Enriched analytics-ready table — business logic, deduplication |

> **Note:** Unity Catalog was configured using the `silver` ADLS container as the external location. All DLT pipeline tables (bronze_stocks, silver_stocks, gold_stocks) are governed by Unity Catalog under the `stockmarket.stockmarket_db` schema.

---

## ⚙️ Tech Stack

| Tool | Purpose |
|------|---------|
| **Alpha Vantage API** | Real-time stock price data source (FREE tier) |
| **Azure Event Hubs** | Real-time stream ingestion |
| **Azure Stream Analytics** | Event Hubs → ADLS raw container |
| **ADLS Gen2** | Scalable cloud data lake (raw/bronze/silver/gold) |
| **Azure Databricks** | Autoloader, Delta Live Tables, Jobs |
| **Delta Live Tables (DLT)** | Declarative Bronze → Silver → Gold ETL pipeline |
| **Unity Catalog** | Data governance — external locations, catalog, schema |
| **Azure Data Factory** | Pipeline orchestration — daily scheduling |
| **Databricks Lakeview Dashboard** | Real-time stock analytics visualization |
| **GitHub** | Version control — ADF pipelines + Databricks notebooks |

---

## 📁 Repository Structure

```
RealTime-StockMarket-Pipeline/
├
├── ADF/
│   ├
│   ├── factory/
│   ├── linked_services/
│   └── pipelines/          
│   
├── Databricks/
│   ├── stock_producer.py        # Producer: API → Event Hubs
│   ├── Autoloader.ipynb         # Autoloader: raw → bronze
│   └── ETL.py                   # DLT Pipeline: bronze → silver → gold
├── Architecture.png             # Architecture diagram
├── ADF.png                      # ADF pipeline screenshot
├── dp_pipeline.png              # DLT pipeline screenshot
├── JOBS.png                     # Databricks Job screenshot
├── Dashboard.png                # Databricks Dashboard screenshot
└── README.md
```

---

## 🔄 Pipeline Deep Dive

### 1️⃣ ADF Pipeline (Daily Schedule Trigger)

![ADF](https://github.com/PusaAkshay/RealTime-StockMarket-Pipeline/blob/0744745e5204e3b605f98ca551a8d131b7b77f1e/ADF.png)

| Activity | Type | Description |
|----------|------|-------------|
| Start_StreamAnalytics | Web (POST) | Starts Stream Analytics job via REST API |
| Stock_producer | Databricks Notebook | Fetches 5 stock prices → sends to Event Hubs |
| Wait1 | Wait (3 mins) | Allows Stream Analytics to write data to ADLS |
| Stop_StreamAnalytics | Web (POST) | Stops Stream Analytics job to save costs |
| stock_market_bronze_silver_dp | Databricks Job | Runs Autoloader + DLT pipeline |

---

### 2️⃣ Producer Notebook (API → Event Hubs)

Fetches real-time stock data from Alpha Vantage and sends to Event Hubs once per day:

```python
STOCKS = ["MSFT", "AAPL", "GOOGL", "AMZN", "TSLA"]

# Fetch from Alpha Vantage API
# Send each stock as JSON to Event Hubs
# Runs ONCE per day (no while loop)
# ADF schedule trigger = daily automation
```

---

### 3️⃣ Autoloader (raw → bronze)


Databricks Autoloader incrementally ingests raw JSON files from ADLS into a Bronze Delta table.

- Uses cloudFiles for scalable file ingestion
- Automatically infers and evolves schema
- Maintains checkpoint for fault tolerance

**Key Features:**
- Incremental ingestion (only new files processed)
- Schema evolution support
- Exactly-once processing guarantee


---

### 4️⃣ DLT Pipeline (bronze → silver → gold)

![DLT Pipeline](https://github.com/PusaAkshay/RealTime-StockMarket-Pipeline/blob/0744745e5204e3b605f98ca551a8d131b7b77f1e/dlt_pipeline.png)

**Bronze Table** — Casts all fields to correct data types

**Silver Table** — Applies DLT data quality rules:

| Rule | Condition |
|------|-----------|
| rule_1 | `ticker IS NOT NULL` |
| rule_2 | `current_price IS NOT NULL` |
| rule_3 | `current_price > 0` |
| rule_4 | `timestamp IS NOT NULL` |
| rule_5 | `volume >= 0` |

**Gold Table** — Enriches data with business logic:

| Column | Logic |
|--------|-------|
| `price_change_category` | Big Gain (≥2%) / Gain (≥0%) / Loss (<0%) / Big Loss (<-2%) |
| `volume_category` | High (≥50M) / Medium (≥10M) / Low (<10M) |
| `volatility` | high_price - low_price |
| `price_range_pct` | (high-low)/low × 100 |
| `market_status` | Bull (change≥0) / Bear (change<0) |

Deduplication by `ticker + trade_date` — one record per stock per day.

---

### 5️⃣ Databricks Job

![Jobs](https://github.com/PusaAkshay/RealTime-StockMarket-Pipeline/blob/0744745e5204e3b605f98ca551a8d131b7b77f1e/JOBS.png)

```
stock_market_pipeline (Job)
├── Task 1: Autoloader    → raw → bronze (17s)
└── Task 2: ETL Pipeline  → bronze → silver → gold (41s)
           (depends on Task 1)
Total execution time: ~1 minute ✅
```

---



## 📈 Dashboard

![Dashboard](https://github.com/PusaAkshay/RealTime-StockMarket-Pipeline/blob/0744745e5204e3b605f98ca551a8d131b7b77f1e/Dashboard.png)

Built using **Databricks Lakeview Dashboard** connected directly to `stockmarket.stockmarket_db.gold_stocks`.

**Visuals:**
- 🔢 **KPI Cards** — Live prices for MSFT, AAPL, GOOGL, AMZN, TSLA
- 📊 **Current Stock Prices** — Bar chart comparing all 5 stocks
- 📉 **% Change Today** — Bar chart showing daily gains/losses
- 🌊 **Trading Volume** — Bar chart by stock
- 🥧 **Bull vs Bear Sentiment** — Donut chart
- 📋 **Stock Details Table** — Full analytics table

---

---
## 📡 Data Source

**Alpha Vantage — Free Stock Market API**

| Property | Value |
|----------|-------|
| Endpoint | `https://www.alphavantage.co/query?function=GLOBAL_QUOTE` |
| Stocks Tracked | MSFT, AAPL, GOOGL, AMZN, TSLA |
| Free Tier Limit | 25 API calls/day |
| Authentication | Free API key (alphavantage.co) |
| Update Frequency | Daily (market hours) |

---


---
## 🔑 Key Concepts Demonstrated

| Concept | Implementation |
|--------|---------------|
| Real-time Streaming | Azure Event Hubs + Stream Analytics |
| Scalable Ingestion | Databricks Autoloader (incremental file processing) |
| Medallion Architecture | Raw → Bronze → Silver → Gold |
| Data Quality Enforcement | Delta Live Tables expectations (`@dp.expect_all_or_drop`) |
| Data Governance | Unity Catalog (external locations, schema control) |
| Orchestration | Azure Data Factory pipeline automation |
| Cost Optimization | Dynamic start/stop of Stream Analytics |
| Deduplication | Ensures one record per stock per day |
---

---
## 🧠 Challenges & Learnings

- Optimized pipeline cost by dynamically starting/stopping Stream Analytics
- Ensured reliable incremental ingestion using Autoloader checkpoints
- Enforced data quality using Delta Live Tables expectations

---

## 👤 Author

**Akshay Pusa**
- GitHub: [PusaAkshay](https://github.com/PusaAkshay)
- Project: [RealTime-StockMarket-Pipeline](https://github.com/PusaAkshay/RealTime-StockMarket-Pipeline)
