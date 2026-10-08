"""
generate_dataset.py
-------------------
Generates a realistic synthetic network monitoring dataset for the
AI-Based Network Capacity Planning System.

Produces ~8,000 records covering 10 devices over 60 days with:
- Gradual traffic growth trends
- Higher utilization during working hours (8am-6pm)
- Occasional random spikes
- Device-specific usage profiles
- Realistic correlations between metrics
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

# ── Device definitions ──────────────────────────────────────────────────────
DEVICES = [
    {"id": 1, "name": "Core-Router-01",   "type": "Router",       "location": "DataCenter-A", "ip": "192.168.1.1",  "cpu_cap": 100, "mem_cap": 32,  "bw_cap": 1000},
    {"id": 2, "name": "Core-Router-02",   "type": "Router",       "location": "DataCenter-B", "ip": "192.168.1.2",  "cpu_cap": 100, "mem_cap": 32,  "bw_cap": 1000},
    {"id": 3, "name": "Dist-Switch-01",   "type": "Switch",       "location": "Floor-1",      "ip": "192.168.2.1",  "cpu_cap": 100, "mem_cap": 16,  "bw_cap": 500},
    {"id": 4, "name": "Dist-Switch-02",   "type": "Switch",       "location": "Floor-2",      "ip": "192.168.2.2",  "cpu_cap": 100, "mem_cap": 16,  "bw_cap": 500},
    {"id": 5, "name": "Edge-Firewall-01", "type": "Firewall",     "location": "DMZ",          "ip": "10.0.0.1",     "cpu_cap": 100, "mem_cap": 64,  "bw_cap": 2000},
    {"id": 6, "name": "App-Server-01",    "type": "Server",       "location": "DataCenter-A", "ip": "192.168.10.1", "cpu_cap": 100, "mem_cap": 128, "bw_cap": 10000},
    {"id": 7, "name": "App-Server-02",    "type": "Server",       "location": "DataCenter-A", "ip": "192.168.10.2", "cpu_cap": 100, "mem_cap": 128, "bw_cap": 10000},
    {"id": 8, "name": "DB-Server-01",     "type": "Server",       "location": "DataCenter-B", "ip": "192.168.10.3", "cpu_cap": 100, "mem_cap": 256, "bw_cap": 10000},
    {"id": 9, "name": "WiFi-AP-01",       "type": "Access Point", "location": "Office-Area",  "ip": "192.168.3.1",  "cpu_cap": 100, "mem_cap": 4,   "bw_cap": 300},
    {"id": 10,"name": "WiFi-AP-02",       "type": "Access Point", "location": "Conference",   "ip": "192.168.3.2",  "cpu_cap": 100, "mem_cap": 4,   "bw_cap": 300},
]

# Base utilization profiles per device type
DEVICE_PROFILES = {
    "Router":       {"cpu_base": 45, "mem_base": 55, "bw_base": 60,  "traffic_base": 500,  "latency_base": 5,   "pkt_loss_base": 0.1, "storage_base": 40},
    "Switch":       {"cpu_base": 30, "mem_base": 45, "bw_base": 50,  "traffic_base": 300,  "latency_base": 2,   "pkt_loss_base": 0.05,"storage_base": 30},
    "Firewall":     {"cpu_base": 55, "mem_base": 65, "bw_base": 70,  "traffic_base": 800,  "latency_base": 8,   "pkt_loss_base": 0.2, "storage_base": 50},
    "Server":       {"cpu_base": 60, "mem_base": 70, "bw_base": 40,  "traffic_base": 200,  "latency_base": 3,   "pkt_loss_base": 0.05,"storage_base": 65},
    "Access Point": {"cpu_base": 25, "mem_base": 40, "bw_base": 45,  "traffic_base": 150,  "latency_base": 10,  "pkt_loss_base": 0.3, "storage_base": 20},
}

def working_hour_multiplier(hour: int) -> float:
    """Return a load multiplier based on hour of day (peak 9-17)."""
    if 9 <= hour <= 17:
        peak_factor = 1.0 - abs(hour - 13) / 12.0   # peak at 13:00
        return 1.0 + 0.5 * peak_factor
    elif 7 <= hour <= 8 or 18 <= hour <= 20:
        return 1.1
    elif 0 <= hour <= 5:
        return 0.6
    else:
        return 0.8

def day_of_week_multiplier(dow: int) -> float:
    """0=Monday … 6=Sunday"""
    if dow in (5, 6):   # weekend
        return 0.55
    return 1.0

def growth_factor(day_index: int, total_days: int) -> float:
    """Simulate gradual traffic growth over the recording period."""
    return 1.0 + 0.15 * (day_index / total_days)   # up to +15% growth

def add_spike(value: float, prob: float = 0.03) -> float:
    """Randomly inject a utilization spike."""
    if random.random() < prob:
        spike = random.uniform(15, 30)
        return min(value + spike, 99.5)
    return value

def generate_record(device: dict, ts: datetime, day_idx: int, total_days: int) -> dict:
    profile = DEVICE_PROFILES[device["type"]]
    hour = ts.hour
    dow  = ts.weekday()

    wh  = working_hour_multiplier(hour)
    dw  = day_of_week_multiplier(dow)
    gf  = growth_factor(day_idx, total_days)
    noise = lambda s: np.random.normal(0, s)

    cpu_util  = profile["cpu_base"]  * wh * dw * gf + noise(4)
    mem_util  = profile["mem_base"]  * wh * dw * gf + noise(3)
    bw_util   = profile["bw_base"]   * wh * dw * gf + noise(5)
    traffic   = profile["traffic_base"] * wh * dw * gf + noise(20)
    latency   = profile["latency_base"] / (dw if dw > 0.5 else 1) + noise(1)
    pkt_loss  = profile["pkt_loss_base"] * (1 + (cpu_util / 100)) + abs(noise(0.05))
    storage   = profile["storage_base"] + day_idx * 0.05 + noise(1)   # slow growth

    # Clamp and spikes
    cpu_util = add_spike(np.clip(cpu_util, 5, 99))
    mem_util = add_spike(np.clip(mem_util, 5, 99), prob=0.02)
    bw_util  = add_spike(np.clip(bw_util,  5, 99), prob=0.04)
    traffic  = max(10, round(traffic, 2))
    latency  = round(max(0.5, latency), 2)
    pkt_loss = round(np.clip(pkt_loss, 0, 5), 3)
    storage  = round(np.clip(storage, 5, 99), 2)

    return {
        "device_id":            device["id"],
        "device_name":          device["name"],
        "device_type":          device["type"],
        "timestamp":            ts.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_utilization":      round(cpu_util, 2),
        "memory_utilization":   round(mem_util, 2),
        "bandwidth_utilization":round(bw_util, 2),
        "network_traffic":      round(traffic, 2),
        "latency":              latency,
        "packet_loss":          pkt_loss,
        "storage_utilization":  storage,
    }

def main():
    print("Generating synthetic network monitoring dataset...")

    start_date = datetime(2024, 1, 1, 0, 0, 0)
    total_days = 60
    interval_hours = 2   # one record every 2 hours -> 12/day x 10 devices x 60 days = 7,200 rows

    records = []
    total_steps = total_days * (24 // interval_hours)

    for day_idx in range(total_days):
        for hour_step in range(0, 24, interval_hours):
            ts = start_date + timedelta(days=day_idx, hours=hour_step)
            for device in DEVICES:
                rec = generate_record(device, ts, day_idx, total_days)
                records.append(rec)

    df = pd.DataFrame(records)
    df = df.sort_values(["timestamp", "device_id"]).reset_index(drop=True)

    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", "network_metrics.csv")
    df.to_csv(output_path, index=False)

    print(f"[OK] Dataset saved -> {output_path}")
    print(f"     Rows : {len(df):,}")
    print(f"     Cols : {list(df.columns)}")
    print(f"     Date range: {df['timestamp'].min()} -> {df['timestamp'].max()}")
    print(f"     Devices: {df['device_name'].nunique()}")
    print("\nSample statistics:")
    print(df[["cpu_utilization","memory_utilization","bandwidth_utilization","network_traffic"]].describe().round(2))

if __name__ == "__main__":
    main()
