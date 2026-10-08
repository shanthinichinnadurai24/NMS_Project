"""
app.py
------
Main Flask application for the AI-Based Network Capacity Planning System.
Run with:  python app.py
"""

import os
import json
import csv
import io
import sqlite3
import traceback
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, send_file, Response,
)
from database import init_db, get_connection, rows_to_list, row_to_dict, DB_PATH
import ml_model as ml

app = Flask(__name__)
app.secret_key = "ncp-secret-key-wipro-2024"


# ═══════════════════════════════════════════════════════════════════════════════
#  Startup
# ═══════════════════════════════════════════════════════════════════════════════

def startup():
    """Initialise DB and train models on first run."""
    print("\n========================================================")
    print("   AI Network Capacity Planning System -- Starting      ")
    print("========================================================\n")
    init_db()
    print("  Training ML models (if not already trained) ...")
    try:
        ml.train_all_models(force=False)
        print("  [OK] ML models ready\n")
    except Exception as e:
        print(f"  [WARN] ML training skipped: {e}\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper utilities
# ═══════════════════════════════════════════════════════════════════════════════

def db():
    return get_connection()


def _risk_color(level):
    return {"LOW": "success", "MEDIUM": "warning",
            "HIGH": "danger", "CRITICAL": "danger"}.get(level, "secondary")


def _status_color(status):
    return {"SAFE": "success", "WARNING": "warning", "CRITICAL": "danger"}.get(status, "secondary")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    conn = db()
    c = conn.cursor()

    devices = rows_to_list(c.execute("SELECT * FROM devices").fetchall())
    total_devices = len(devices)

    # Latest metric per device
    latest_rows = []
    for d in devices:
        row = c.execute(
            "SELECT * FROM network_metrics WHERE device_id=? ORDER BY timestamp DESC LIMIT 1",
            (d["id"],)
        ).fetchone()
        if row:
            latest_rows.append(dict(row))

    avg_cpu = round(sum(r["cpu_utilization"] for r in latest_rows) / max(len(latest_rows), 1), 1)
    avg_mem = round(sum(r["memory_utilization"] for r in latest_rows) / max(len(latest_rows), 1), 1)
    avg_bw  = round(sum(r["bandwidth_utilization"] for r in latest_rows) / max(len(latest_rows), 1), 1)
    avg_trf = round(sum(r["network_traffic"] for r in latest_rows) / max(len(latest_rows), 1), 1)

    devices_at_risk = sum(1 for r in latest_rows if r["cpu_utilization"] > 70 or r["memory_utilization"] > 70)

    active_alerts = c.execute(
        "SELECT COUNT(*) FROM alerts WHERE status='Active'"
    ).fetchone()[0]

    # Health score
    if avg_cpu < 60 and avg_mem < 60 and avg_bw < 60:
        health = "Healthy"
        health_color = "success"
    elif avg_cpu < 80 and avg_mem < 80:
        health = "Warning"
        health_color = "warning"
    else:
        health = "Critical"
        health_color = "danger"

    conn.close()
    return render_template(
        "dashboard.html",
        total_devices=total_devices,
        avg_cpu=avg_cpu, avg_mem=avg_mem, avg_bw=avg_bw, avg_trf=avg_trf,
        devices_at_risk=devices_at_risk,
        active_alerts=active_alerts,
        health=health, health_color=health_color,
    )


@app.route("/devices")
def devices_page():
    conn = db()
    devices = rows_to_list(conn.execute("SELECT * FROM devices ORDER BY id").fetchall())
    # Attach latest utilisation
    for d in devices:
        row = conn.execute(
            "SELECT cpu_utilization, memory_utilization, bandwidth_utilization "
            "FROM network_metrics WHERE device_id=? ORDER BY timestamp DESC LIMIT 1",
            (d["id"],)
        ).fetchone()
        if row:
            d["cpu_current"]  = round(row["cpu_utilization"], 1)
            d["mem_current"]  = round(row["memory_utilization"], 1)
            d["bw_current"]   = round(row["bandwidth_utilization"], 1)
        else:
            d["cpu_current"] = d["mem_current"] = d["bw_current"] = 0
    conn.close()
    return render_template("devices.html", devices=devices)


@app.route("/metrics")
def metrics_page():
    conn = db()
    devices = rows_to_list(conn.execute("SELECT id, device_name FROM devices ORDER BY id").fetchall())
    conn.close()
    return render_template("metrics.html", devices=devices)


@app.route("/forecasting")
def forecasting_page():
    conn = db()
    devices = rows_to_list(conn.execute("SELECT id, device_name FROM devices ORDER BY id").fetchall())
    conn.close()
    return render_template("forecasting.html", devices=devices)


@app.route("/capacity")
def capacity_page():
    conn = db()
    devices = rows_to_list(conn.execute("SELECT * FROM devices ORDER BY id").fetchall())
    conn.close()
    return render_template("capacity.html", devices=devices)


@app.route("/alerts")
def alerts_page():
    conn = db()
    alerts = rows_to_list(
        conn.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 200").fetchall()
    )
    conn.close()
    for a in alerts:
        a["risk_color"] = _risk_color(a.get("risk_level", "LOW"))
    return render_template("alerts.html", alerts=alerts)


@app.route("/performance")
def performance_page():
    metrics_data = {}
    for resource in ml.RESOURCE_COLUMNS:
        metrics_data[resource] = ml.load_model_meta(resource)
    return render_template("performance.html", metrics_data=metrics_data)


@app.route("/reports")
def reports_page():
    conn = db()
    c = conn.cursor()
    total_devices = c.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    active_alerts = c.execute("SELECT COUNT(*) FROM alerts WHERE status='Active'").fetchone()[0]
    critical_alerts = c.execute("SELECT COUNT(*) FROM alerts WHERE risk_level='CRITICAL'").fetchone()[0]
    conn.close()
    return render_template(
        "reports.html",
        total_devices=total_devices,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.route("/settings")
def settings_page():
    return render_template("settings.html")


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API — Devices
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/devices", methods=["GET"])
def api_get_devices():
    conn = db()
    rows = rows_to_list(conn.execute("SELECT * FROM devices ORDER BY id").fetchall())
    conn.close()
    return jsonify({"status": "ok", "data": rows, "count": len(rows)})


@app.route("/api/devices", methods=["POST"])
def api_add_device():
    data = request.json or request.form
    required = ["device_name", "device_type", "ip_address"]
    for field in required:
        if not data.get(field):
            return jsonify({"status": "error", "message": f"Missing field: {field}"}), 400
    try:
        conn = db()
        conn.execute(
            "INSERT INTO devices (device_name, device_type, location, ip_address, "
            "cpu_capacity, memory_capacity, bandwidth_capacity, status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                data["device_name"], data["device_type"],
                data.get("location", ""),
                data["ip_address"],
                float(data.get("cpu_capacity", 100)),
                float(data.get("memory_capacity", 32)),
                float(data.get("bandwidth_capacity", 1000)),
                data.get("status", "Active"),
            ),
        )
        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return jsonify({"status": "ok", "message": "Device added", "id": new_id}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/devices/<int:device_id>", methods=["GET"])
def api_get_device(device_id):
    conn = db()
    row = conn.execute("SELECT * FROM devices WHERE id=?", (device_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "error", "message": "Device not found"}), 404
    return jsonify({"status": "ok", "data": row_to_dict(row)})


@app.route("/api/devices/<int:device_id>", methods=["PUT"])
def api_update_device(device_id):
    data = request.json or {}
    conn = db()
    row = conn.execute("SELECT * FROM devices WHERE id=?", (device_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Device not found"}), 404
    fields = ["device_name", "device_type", "location", "ip_address",
              "cpu_capacity", "memory_capacity", "bandwidth_capacity", "status"]
    updates = {f: data.get(f, row[f]) for f in fields}
    conn.execute(
        "UPDATE devices SET device_name=?, device_type=?, location=?, ip_address=?, "
        "cpu_capacity=?, memory_capacity=?, bandwidth_capacity=?, status=? WHERE id=?",
        (*updates.values(), device_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Device updated"})


@app.route("/api/devices/<int:device_id>", methods=["DELETE"])
def api_delete_device(device_id):
    conn = db()
    row = conn.execute("SELECT id FROM devices WHERE id=?", (device_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Device not found"}), 404
    conn.execute("DELETE FROM devices WHERE id=?", (device_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Device deleted"})


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API — Metrics
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/metrics", methods=["GET"])
def api_get_metrics():
    device_id = request.args.get("device_id", type=int)
    limit     = request.args.get("limit", 500, type=int)
    start     = request.args.get("start")
    end       = request.args.get("end")

    query = "SELECT m.*, d.device_name FROM network_metrics m JOIN devices d ON d.id=m.device_id WHERE 1=1"
    params = []
    if device_id:
        query += " AND m.device_id=?"; params.append(device_id)
    if start:
        query += " AND m.timestamp >= ?"; params.append(start)
    if end:
        query += " AND m.timestamp <= ?"; params.append(end)
    query += " ORDER BY m.timestamp DESC LIMIT ?"
    params.append(limit)

    conn = db()
    rows = rows_to_list(conn.execute(query, params).fetchall())
    conn.close()
    return jsonify({"status": "ok", "data": rows, "count": len(rows)})


@app.route("/api/metrics/<int:device_id>", methods=["GET"])
def api_get_device_metrics(device_id):
    limit = request.args.get("limit", 200, type=int)
    conn = db()
    rows = rows_to_list(
        conn.execute(
            "SELECT * FROM network_metrics WHERE device_id=? ORDER BY timestamp DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
    )
    conn.close()
    if not rows:
        return jsonify({"status": "error", "message": "No metrics found"}), 404
    return jsonify({"status": "ok", "data": rows})


@app.route("/api/metrics/chart/<int:device_id>", methods=["GET"])
def api_chart_data(device_id):
    """Return time-series chart data for a single device."""
    limit = request.args.get("limit", 84, type=int)   # 7 days × 12/day
    conn = db()
    rows = rows_to_list(
        conn.execute(
            "SELECT timestamp, cpu_utilization, memory_utilization, "
            "bandwidth_utilization, network_traffic, latency, packet_loss "
            "FROM network_metrics WHERE device_id=? ORDER BY timestamp DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
    )
    conn.close()
    rows.reverse()
    return jsonify({"status": "ok", "data": rows})


@app.route("/api/dashboard/charts", methods=["GET"])
def api_dashboard_charts():
    """Aggregate chart data for the main dashboard."""
    conn = db()
    # Last 7 days, averaged across all devices per timestamp
    rows = rows_to_list(
        conn.execute(
            """
            SELECT timestamp,
                   AVG(cpu_utilization)       AS avg_cpu,
                   AVG(memory_utilization)    AS avg_mem,
                   AVG(bandwidth_utilization) AS avg_bw,
                   SUM(network_traffic)       AS total_traffic
            FROM   network_metrics
            WHERE  timestamp >= datetime('now', '-8 days')
               OR  timestamp >= (SELECT MIN(timestamp) FROM (
                                    SELECT timestamp FROM network_metrics
                                    ORDER BY timestamp DESC LIMIT 1000))
            GROUP  BY timestamp
            ORDER  BY timestamp DESC
            LIMIT  84
            """,
        ).fetchall()
    )
    conn.close()
    rows.reverse()
    return jsonify({"status": "ok", "data": rows})


@app.route("/api/dashboard/device_utilization", methods=["GET"])
def api_device_utilization():
    """Latest CPU/Memory/BW per device for bar chart."""
    conn = db()
    devices = rows_to_list(conn.execute("SELECT id, device_name FROM devices").fetchall())
    result = []
    for d in devices:
        row = conn.execute(
            "SELECT cpu_utilization, memory_utilization, bandwidth_utilization "
            "FROM network_metrics WHERE device_id=? ORDER BY timestamp DESC LIMIT 1",
            (d["id"],)
        ).fetchone()
        if row:
            result.append({
                "device_name": d["device_name"],
                "cpu":  round(row["cpu_utilization"], 1),
                "mem":  round(row["memory_utilization"], 1),
                "bw":   round(row["bandwidth_utilization"], 1),
            })
    conn.close()
    return jsonify({"status": "ok", "data": result})


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API — Forecasting
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/forecast/<int:device_id>", methods=["GET"])
def api_forecast(device_id):
    resource = request.args.get("resource", "cpu").lower()
    days     = request.args.get("days", 7, type=int)

    if resource not in ml.RESOURCE_COLUMNS:
        return jsonify({"status": "error", "message": f"Invalid resource. Choose from: {list(ml.RESOURCE_COLUMNS.keys())}"}), 400
    if days not in (7, 14, 30):
        return jsonify({"status": "error", "message": "Invalid days. Choose 7, 14, or 30."}), 400

    try:
        result = ml.forecast(device_id, resource, days)
        return jsonify({"status": "ok", "data": result})
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "ML model not trained yet. Restart the server."}), 503
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"Forecast error: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API — Capacity
# ═══════════════════════════════════════════════════════════════════════════════

_capacity_cache = {"timestamp": 0, "data": None}

@app.route("/api/capacity", methods=["GET"])
def api_capacity():
    global _capacity_cache
    now = datetime.now().timestamp()
    force = request.args.get("force", "false").lower() == "true"

    if not force and _capacity_cache["data"] is not None and (now - _capacity_cache["timestamp"]) < 120:
        return jsonify({"status": "ok", "data": _capacity_cache["data"], "cached": True})

    conn = db()
    devices = rows_to_list(conn.execute("SELECT * FROM devices ORDER BY id").fetchall())
    conn.close()

    results = []
    for d in devices:
        try:
            analysis = ml.capacity_analysis(d["id"], days=30)
            row = {"device_id": d["id"], "device_name": d["device_name"],
                   "device_type": d["device_type"]}
            for resource, info in analysis.items():
                if "error" not in info:
                    row[f"{resource}_predicted"] = info["peak_predicted"]
                    row[f"{resource}_status"]    = info["status"]
                    row[f"{resource}_growth"]    = info["growth_pct"]
                    row[f"{resource}_rec"]       = info["recommendation"]
            results.append(row)
        except Exception as e:
            results.append({"device_id": d["id"], "device_name": d["device_name"], "error": str(e)})

    _capacity_cache = {"timestamp": now, "data": results}
    return jsonify({"status": "ok", "data": results, "cached": False})


@app.route("/api/capacity/<int:device_id>", methods=["GET"])
def api_capacity_device(device_id):
    days = request.args.get("days", 30, type=int)
    try:
        result = ml.capacity_analysis(device_id, days)
        return jsonify({"status": "ok", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API — Alerts
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/alerts", methods=["GET"])
def api_alerts():
    status = request.args.get("status", "Active")
    conn = db()
    rows = rows_to_list(
        conn.execute(
            "SELECT * FROM alerts WHERE status=? ORDER BY timestamp DESC LIMIT 500",
            (status,)
        ).fetchall()
    )
    conn.close()
    return jsonify({"status": "ok", "data": rows, "count": len(rows)})


@app.route("/api/alerts/generate", methods=["POST"])
def api_generate_alerts():
    """Trigger fresh alert generation via ML forecasting."""
    try:
        # Clear old active alerts
        conn = db()
        conn.execute("DELETE FROM alerts WHERE status='Active'")
        conn.commit()
        conn.close()
        new_alerts = ml.generate_alerts()
        return jsonify({"status": "ok", "message": f"Generated {len(new_alerts)} alerts", "data": new_alerts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def api_resolve_alert(alert_id):
    conn = db()
    conn.execute("UPDATE alerts SET status='Resolved' WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Alert resolved"})


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API — Model Performance
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/model/performance", methods=["GET"])
def api_model_performance():
    data = {}
    for resource in ml.RESOURCE_COLUMNS:
        data[resource] = ml.load_model_meta(resource)
    return jsonify({"status": "ok", "data": data})


@app.route("/api/model/retrain", methods=["POST"])
def api_retrain():
    """Retrain all models (may take 10–30 seconds)."""
    try:
        metrics = ml.train_all_models(force=True)
        return jsonify({"status": "ok", "message": "Models retrained", "data": metrics})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API — Reports
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/reports/summary", methods=["GET"])
def api_report_summary():
    conn = db()
    c = conn.cursor()
    total_devices   = c.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    active_alerts   = c.execute("SELECT COUNT(*) FROM alerts WHERE status='Active'").fetchone()[0]
    critical_alerts = c.execute("SELECT COUNT(*) FROM alerts WHERE risk_level='CRITICAL'").fetchone()[0]
    high_alerts     = c.execute("SELECT COUNT(*) FROM alerts WHERE risk_level='HIGH'").fetchone()[0]

    latest = rows_to_list(c.execute(
        "SELECT device_id, AVG(cpu_utilization) as avg_cpu, AVG(memory_utilization) as avg_mem, "
        "AVG(bandwidth_utilization) as avg_bw "
        "FROM network_metrics WHERE timestamp >= (SELECT MAX(timestamp) FROM network_metrics) "
        "GROUP BY device_id"
    ).fetchall())
    conn.close()

    return jsonify({
        "status": "ok",
        "data": {
            "total_devices":   total_devices,
            "active_alerts":   active_alerts,
            "critical_alerts": critical_alerts,
            "high_alerts":     high_alerts,
            "latest_metrics":  latest,
            "generated_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    })


@app.route("/api/reports/export/csv", methods=["GET"])
def api_export_csv():
    """Export all device metrics as CSV download."""
    conn = db()
    rows = rows_to_list(conn.execute(
        "SELECT m.*, d.device_name, d.device_type FROM network_metrics m "
        "JOIN devices d ON d.id=m.device_id ORDER BY m.timestamp DESC LIMIT 5000"
    ).fetchall())
    conn.close()

    si = io.StringIO()
    if rows:
        writer = csv.DictWriter(si, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=network_capacity_report.csv"},
    )


@app.route("/api/reports/capacity_summary", methods=["GET"])
def api_capacity_summary():
    """Run capacity analysis for all devices and return JSON summary."""
    conn = db()
    devices = rows_to_list(conn.execute("SELECT * FROM devices ORDER BY id").fetchall())
    conn.close()

    summary = []
    for d in devices:
        try:
            analysis = ml.capacity_analysis(d["id"], 30)
            worst_status = "SAFE"
            recs = []
            for resource, info in analysis.items():
                if "error" not in info:
                    if info["status"] == "CRITICAL":
                        worst_status = "CRITICAL"
                    elif info["status"] == "WARNING" and worst_status != "CRITICAL":
                        worst_status = "WARNING"
                    recs.append(info["recommendation"])
            summary.append({
                "device_id":   d["id"],
                "device_name": d["device_name"],
                "device_type": d["device_type"],
                "location":    d["location"],
                "status":      worst_status,
                "analysis":    analysis,
                "top_recommendation": recs[0] if recs else "No action required.",
            })
        except Exception as e:
            summary.append({"device_id": d["id"], "device_name": d["device_name"], "error": str(e)})

    return jsonify({"status": "ok", "data": summary, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


# ═══════════════════════════════════════════════════════════════════════════════
#  Error handlers
# ═══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "Endpoint not found"}), 404
    return render_template("base.html"), 404


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    return render_template("base.html"), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    startup()
    print("  Server starting on http://127.0.0.1:5000\n")
    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False, threaded=True)
