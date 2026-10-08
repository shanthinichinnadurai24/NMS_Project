# AI-Based Network Capacity Planning and Resource Forecasting System

> **Wipro CoE NMS Project — 2024**  
> A full-stack AI-powered system to monitor, forecast, and plan network resource capacity.

---

## 📋 Problem Statement

Network operations teams struggle to proactively manage capacity before resources are exhausted. Reactive management causes outages, performance degradation, and costly emergency procurement. This system solves the problem by using machine learning to forecast future resource utilization and automatically generate capacity recommendations.

---

## 🎯 Objectives

- Collect and analyse historical network performance data (CPU, memory, bandwidth, traffic, latency, packet loss, storage)
- Detect resource usage trends across multiple device types
- Forecast future resource utilization using machine learning
- Predict when network resources will cross predefined capacity thresholds
- Recommend whether additional capacity/resources are required
- Display all results through an interactive enterprise-grade dashboard
- Generate risk alerts for potential future capacity issues

---

## ✨ Features

| Module | Features |
|--------|----------|
| **Dashboard** | 8 KPI cards, 6 real-time charts, quick actions |
| **Network Devices** | Full CRUD, search/filter, live utilization progress bars |
| **Network Metrics** | Date/device/metric filters, 4 trend charts, sortable data table |
| **AI Forecasting** | ML-powered 7/14/30-day forecasts per device and resource |
| **Capacity Planning** | SAFE/WARNING/CRITICAL status, bar charts, recommendations |
| **Risk & Alerts** | AI risk detection, resolve alerts, risk distribution chart |
| **AI Model Performance** | MAE/RMSE/R² metrics, feature importance charts |
| **Reports** | Executive summary, full CSV export, action plan |
| **Settings** | System info, threshold display, model management, API reference |

---

## 🏗️ Architecture

```
Network Metrics CSV
        │
        ▼
Data Preprocessing (Pandas + Feature Engineering)
        │
        ▼
ML Forecasting Engine (Random Forest Regressor)
        │
   ┌────┴────┐
   ▼         ▼
Capacity  Risk Detection
Planning  (Rule + ML)
   │         │
   └────┬────┘
        ▼
Recommendation Engine
        │
        ▼
Flask REST API
        │
        ▼
Web Dashboard (Chart.js + Bootstrap)
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, JavaScript, Bootstrap Icons, Chart.js 4 |
| Backend | Python 3.10+, Flask 3.0 |
| Database | SQLite (via sqlite3) |
| ML/Data | Scikit-learn, Pandas, NumPy |
| ML Model | Random Forest Regressor (150 estimators) |
| Deployment | Local (Windows), `python app.py` |

---

## 📊 Dataset Description

The synthetic dataset (`data/network_metrics.csv`) contains **7,200 records** covering:

- **10 devices**: Routers, Switches, Firewall, Servers, Access Points
- **60 days** of data at 2-hour intervals
- **9 metrics** per record: CPU, Memory, Bandwidth, Traffic, Latency, Packet Loss, Storage

**Realistic patterns included:**
- Gradual traffic growth (+15% over 60 days)
- Higher utilization during working hours (09:00–17:00)
- Reduced load on weekends (–45%)
- Random spikes (3% probability per step)
- Device-type specific profiles (Servers higher CPU/Memory, APs lower)

---

## 🤖 ML Methodology

### Model: Random Forest Regressor

**Why Random Forest?**
- Handles non-linear daily/weekly seasonality without explicit decomposition
- Robust to occasional network traffic spikes
- No GPU required — trains in <10 seconds on 7,200 records
- Provides feature importance for explainability
- Ensemble of 150 trees reduces overfitting

### Feature Engineering
| Feature | Description |
|---------|-------------|
| `hour` | Hour of day (0–23) — captures daily patterns |
| `dow` | Day of week (0=Mon, 6=Sun) — captures weekly patterns |
| `month` | Month of year |
| `day_index` | Days since first record — captures growth trend |
| `lag_1/2/3/6` | Previous 1/2/3/6 timestep values — autocorrelation |
| `roll_mean_3/6` | 3 and 6-step rolling mean — trend smoothing |
| `roll_std_3` | 3-step rolling standard deviation — volatility |
| `device_type_enc` | Device type as integer — device-specific patterns |

### Forecasting Strategy
Recursive forecasting: the model predicts one step ahead, then feeds that prediction back as a lag feature for the next step.

### Evaluation Metrics
- **MAE** (Mean Absolute Error): Average error magnitude
- **RMSE** (Root Mean Squared Error): Penalizes larger errors more
- **R²** (Coefficient of Determination): 1.0 = perfect, 0 = mean baseline

---

## 🗄️ Database Design

### `devices`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| device_name | TEXT UNIQUE | e.g., Core-Router-01 |
| device_type | TEXT | Router/Switch/Firewall/Server/AP |
| location | TEXT | DataCenter-A, Floor-1, etc. |
| ip_address | TEXT UNIQUE | IPv4 address |
| cpu_capacity | REAL | Max CPU % (default 100) |
| memory_capacity | REAL | RAM in GB |
| bandwidth_capacity | REAL | Bandwidth in Mbps |
| status | TEXT | Active/Maintenance/Offline |

### `network_metrics`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| device_id | INTEGER FK | References devices.id |
| timestamp | TEXT | ISO datetime |
| cpu_utilization | REAL | 0–100% |
| memory_utilization | REAL | 0–100% |
| bandwidth_utilization | REAL | 0–100% |
| network_traffic | REAL | Mbps |
| latency | REAL | Milliseconds |
| packet_loss | REAL | 0–5% |
| storage_utilization | REAL | 0–100% |

### `predictions`
Stores ML predictions for historical reference.

### `alerts`
Stores generated risk alerts with resolution status.

---

## 🔌 API Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/devices` | List all devices |
| POST | `/api/devices` | Add a device |
| GET | `/api/devices/:id` | Get device by ID |
| PUT | `/api/devices/:id` | Update device |
| DELETE | `/api/devices/:id` | Delete device |
| GET | `/api/metrics` | Get metrics (filterable by device, date) |
| GET | `/api/metrics/:device_id` | Metrics for specific device |
| GET | `/api/forecast/:device_id` | ML forecast (`?resource=cpu&days=7`) |
| GET | `/api/capacity` | Capacity analysis all devices |
| GET | `/api/capacity/:device_id` | Capacity for specific device |
| GET | `/api/alerts` | List alerts |
| POST | `/api/alerts/generate` | Trigger alert generation |
| POST | `/api/alerts/:id/resolve` | Resolve alert |
| GET | `/api/model/performance` | ML model metrics |
| POST | `/api/model/retrain` | Retrain all models |
| GET | `/api/dashboard/charts` | Dashboard chart data |
| GET | `/api/dashboard/device_utilization` | Per-device utilization |
| GET | `/api/reports/summary` | Report summary |
| GET | `/api/reports/export/csv` | Download CSV |
| GET | `/api/reports/capacity_summary` | Full capacity report |

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- pip

### Steps

```bash
# 1. Navigate to project directory
cd "d:\NMS - AI network-Capacity-Planner"

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment (Windows)
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Generate the dataset
python generate_dataset.py

# 6. Start the application
python app.py
```

### Access the Application
Open your browser and go to: **http://127.0.0.1:5000**

> **Note:** The first startup automatically:
> - Creates the SQLite database
> - Imports the CSV dataset (7,200 records)
> - Trains all 4 ML models (CPU, Memory, Bandwidth, Traffic)

---

## 📁 Project Structure

```
NMS - AI network-Capacity-Planner/
│
├── app.py                  # Main Flask application
├── database.py             # DB init, schema, CSV import
├── ml_model.py             # Random Forest forecasting engine
├── generate_dataset.py     # Synthetic dataset generator
├── requirements.txt        # Python dependencies
├── README.md               # This file
│
├── data/
│   └── network_metrics.csv # 7,200-row synthetic dataset
│
├── models/
│   ├── model_cpu.pkl       # Trained CPU model
│   ├── model_memory.pkl    # Trained memory model
│   ├── model_bandwidth.pkl # Trained bandwidth model
│   └── model_traffic.pkl   # Trained traffic model
│
├── database/
│   └── network.db          # SQLite database
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── devices.html
│   ├── metrics.html
│   ├── forecasting.html
│   ├── capacity.html
│   ├── alerts.html
│   ├── performance.html
│   ├── reports.html
│   └── settings.html
│
└── static/
    ├── css/
    │   └── style.css       # Enterprise dark theme
    └── js/
        └── (inline JS in templates)
```

---

## 🖼️ Screenshots

> Run the application and visit each page to take screenshots for your demo.

| Page | URL |
|------|-----|
| Dashboard | http://127.0.0.1:5000/dashboard |
| Network Devices | http://127.0.0.1:5000/devices |
| Network Metrics | http://127.0.0.1:5000/metrics |
| AI Forecasting | http://127.0.0.1:5000/forecasting |
| Capacity Planning | http://127.0.0.1:5000/capacity |
| Risk & Alerts | http://127.0.0.1:5000/alerts |
| Model Performance | http://127.0.0.1:5000/performance |
| Reports | http://127.0.0.1:5000/reports |

---

## 🔮 Future Enhancements

1. **LSTM/Prophet integration** for more accurate time-series forecasting
2. **Real-time data ingestion** via SNMP/NetFlow integration
3. **Email/SMS alerting** for critical threshold crossings
4. **Multi-tenant support** for multiple network domains
5. **Auto-scaling integration** with cloud APIs (AWS/Azure)
6. **Anomaly detection** using Isolation Forest
7. **PDF report export** with matplotlib chart embedding
8. **User authentication** with role-based access control

---

## 👥 Project Info

- **Project**: AI-Based Network Capacity Planning and Resource Forecasting System
- **Purpose**: Wipro CoE NMS College Project
- **Stack**: Python + Flask + SQLite + Scikit-learn + Chart.js
- **ML Model**: Random Forest Regressor
- **Dataset**: Synthetic (7,200 records, 10 devices, 60 days)
