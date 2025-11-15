import serial
import threading
import time
import os
from flask import Flask, jsonify, send_from_directory

# Import the cached version of our AI prioritizer
from ai_prioritizer import get_ai_prioritized_tasks


# ---------------------------------------------------------
# 1. SERIAL SETUP
# ---------------------------------------------------------

source_port = 'COM6'  # Arduino with buttons (input)
dest_port = 'COM5'    # Arduino with LED (output)
baud_rate = 9600

try:
    ser_in = serial.Serial(source_port, baud_rate, timeout=1)
    ser_out = serial.Serial(dest_port, baud_rate, timeout=1)
    print(f"Flask connected. Forwarding data from {source_port} -> {dest_port}")
except serial.SerialException as e:
    print(f"WARNING: Could not open serial ports {source_port} or {dest_port}. ({e})")
    print("Dashboard will run, but serial I/O will be disabled.")

    class MockSerial:
        def write(self, data): pass
        @property
        def in_waiting(self): return 0

    ser_in = ser_out = MockSerial()


# ---------------------------------------------------------
# 2. FLASK APP & DATA SETUP
# ---------------------------------------------------------

app = Flask(__name__)

# Example structure:
# [{"request": "Water Request", "timestamp": 1700000000.123}]
history = []
latest_led_message = ""

BUTTON_MAP = {
    "R1": "Bathroom Request",
    "R2": "Water Request",
    "R3": "Food Request",
    "R4": "Blanket Request",
    "R5": "HELP! Emergency"
}


# ---------------------------------------------------------
# 3. BACKGROUND SERIAL THREAD
# ---------------------------------------------------------

def serial_handler():
    global latest_led_message, history

    while True:
        try:
            if ser_in.in_waiting:
                data = ser_in.read(ser_in.in_waiting)
                current_time = time.time()

                # Forward raw byte signal to Arduino LED controller
                ser_out.write(data)

                # Convert byte data → string
                try:
                    line = data.decode(errors="ignore").strip()

                    if line in BUTTON_MAP:
                        readable = BUTTON_MAP[line]

                        history.append({
                            "request": readable,
                            "timestamp": current_time
                        })

                        latest_led_message = line
                        print(f"[Request Logged] {line} -> {readable}")

                except Exception as e:
                    print("Error decoding serial:", e)

        except Exception as e:
            print("Serial read error:", e)

        time.sleep(0.01)


threading.Thread(target=serial_handler, daemon=True).start()


# ---------------------------------------------------------
# 4. FLASK ROUTES
# ---------------------------------------------------------

@app.route("/")
def serve_dashboard():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, "main.html")


def format_timestamp(ts):
    return time.strftime("%I:%M:%S %p", time.localtime(ts))


@app.route("/api/dashboard-data")
def dashboard_data():

    # --------- SMART AI INTEGRATION ----------
    # If history hasn't changed, Gemini will NOT be called.
    ai_output = get_ai_prioritized_tasks(history)

    prioritized_tasks = ai_output.get("prioritized_tasks", [])
    ai_insights = ai_output.get("ai_insights", [])
    wellbeing_summary = ai_output.get("wellbeing_summary", {})

    # Send last 10 requests to frontend
    request_feed = [
        {
            "request_text": req['request'],
            "timestamp_str": format_timestamp(req['timestamp']),
            "urgency": "high" if req['request'] == "HELP! Emergency" else "medium"
        }
        for req in history[-10:]
    ]

    return jsonify({
        "prioritized_tasks": prioritized_tasks,
        "request_feed": request_feed,
        "ai_insights": ai_insights,
        "wellbeing_summary": wellbeing_summary,
        "latest_led_message": latest_led_message
    })


@app.route("/api/status")
def status():
    return jsonify({
        "status": "running",
        "latest_led_message": latest_led_message,
        "history_count": len(history),
        "history_preview": history[-5:]
    })


# ---------------------------------------------------------
# 5. RUN SERVER
# ---------------------------------------------------------

if __name__ == "__main__":
    print("Flask server running at http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)
