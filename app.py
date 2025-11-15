import serial
import threading
import time
import os
from flask import Flask, jsonify, send_from_directory
# This script assumes 'ai_prioritizer.py' is in the same directory
from ai_prioritizer import get_ai_prioritized_tasks


# ---------------------------------------------------------
# 1. SERIAL SETUP
# ---------------------------------------------------------

source_port = 'COM6'  # Arduino with buttons (input)
dest_port = 'COM5'    # Arduino with LED (output)
baud_rate = 9600

# Try to initialize serial ports
try:
    ser_in = serial.Serial(source_port, baud_rate, timeout=1)
    ser_out = serial.Serial(dest_port, baud_rate, timeout=1)
    print(f"Flask connected. Forwarding data from {source_port} -> {dest_port}")
except serial.SerialException as e:
    print(f"WARNING: Could not open serial ports {source_port} or {dest_port}. ({e})")
    print("Dashboard will run, but serial I/O will be disabled.")
    # Create mock serial objects to prevent application crash
    class MockSerial:
        def write(self, data):
            # print(f"[MOCK SERIAL] Writing: {data}")
            pass
        def in_waiting(self):
            return 0
    ser_in = ser_out = MockSerial()
   
# ---------------------------------------------------------
# 2. FLASK APP & DATA SETUP
# ---------------------------------------------------------

app = Flask(__name__)

# Structure: [{"request": "Water Request", "timestamp": 1700000000.123}, ...]
history = []
latest_led_message = ""  # last message sent to Arduino (e.g., "R1")

# Button code mapping
BUTTON_MAP = {
    "R1": "Bathroom Request",
    "R2": "Water Request",
    "R3": "Food Request",
    "R4": "Blanket Request",
    "R5": "HELP! Emergency"
}

# ---------------------------------------------------------
# 3. BACKGROUND SERIAL HANDLER THREAD
# ---------------------------------------------------------

def serial_handler():
    """ 
    Reads FROM COM6, forwards to COM5, and processes for Flask.
    This runs in a separate thread.
    """
    global latest_led_message
    
    while True:
        try:
            if ser_in.in_waiting:
                data = ser_in.read(ser_in.in_waiting)
                current_time = time.time() # Capture time immediately

                # 1. Forward to Arduino 2 (COM5)
                ser_out.write(data)
                
                # 2. Interpret for Flask
                try:
                    line = data.decode(errors="ignore").strip()

                    if line in BUTTON_MAP:
                        readable_request = BUTTON_MAP.get(line)
                        # Store object with request and timestamp
                        history.append({
                            "request": readable_request,
                            "timestamp": current_time
                        })
                        latest_led_message = line
                        print(f"[Request Logged] {line} -> {readable_request}")
                        
                except Exception as e:
                    print(f"Error processing serial data: {e}")
        except Exception as e:
            print(f"Serial read error: {e}")

        time.sleep(0.01) # Avoid busy-waiting

# Start the background thread
threading.Thread(target=serial_handler, daemon=True).start()

# ---------------------------------------------------------
# 4. FLASK ROUTES
# ---------------------------------------------------------

@app.route("/")
def serve_dashboard():
    """Serves the main.html file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, "main.html")


def format_timestamp(ts):
    """Converts a Unix timestamp float to a HH:MM:SS AM/PM string."""
    return time.strftime("%I:%M:%S %p", time.localtime(ts))


@app.route("/api/dashboard-data")
def dashboard_data():
    """ 
    Returns the current dashboard data.
    This is the endpoint called by the front-end JavaScript.
    """
   
    # Get AI analysis of the current history
    ai_output = get_ai_prioritized_tasks(history)

    # Get all data directly from the AI output
    prioritized_tasks = ai_output.get("prioritized_tasks", [])
    ai_insights = ai_output.get("ai_insights", [])
    wellbeing_summary = ai_output.get("wellbeing_summary", {})

    # Create the live request feed (last 10)
    request_feed = [
        {
            "request_text": req['request'],
            "timestamp_str": format_timestamp(req['timestamp']),
            # Assign urgency based on request type
            "urgency": "high" if req['request'] == "HELP! Emergency" else "medium"
        }
        for req in history[-10:]
    ]

    # --- THIS IS THE FIX ---
    # The old code had hardcoded placeholders here.
    # This new version sends the *real* AI data directly.
    return jsonify({
        "prioritized_tasks": prioritized_tasks, # <-- FIX 1: Fixed typo
        "request_feed": request_feed,
        "ai_insights": ai_insights,             # <-- FIX 2: Now uses real AI insights
        "wellbeing_summary": wellbeing_summary, # <-- FIX 3: Now uses real AI summary
        "latest_led_message": latest_led_message
    })


@app.route("/api/status")
def status():
    """A simple endpoint to check history (for debugging)."""
    return jsonify({
        "status": "running",
        "latest_led_message": latest_led_message,
        "history_count": len(history),
        "history_preview": history[-5:] # Show last 5 requests
    })

# ---------------------------------------------------------
# 5. RUN FLASK SERVER
# ---------------------------------------------------------

if __name__ == "__main__":
    print("Flask server running on http://127.0.0.1:5000")
    # use_reloader=False is important to prevent the serial thread from running twice
    app.run(debug=True, use_reloader=False)