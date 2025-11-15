import serial
import threading
import time
import os
from flask import Flask, jsonify, send_from_directory


# ---------------------------------------------------------
# 1. SERIAL SETUP (Open COM6 only ONCE)
# ---------------------------------------------------------


# NOTE: Since this environment cannot access physical ports,
# the serial commands may fail, but the application logic is updated.


source_port = 'COM6'  # Arduino with buttons (input)
dest_port = 'COM5'    # Arduino with LED (output)
baud_rate = 9600


# Try to initialize serial ports (handle potential error if ports don't exist)
try:
    ser_in = serial.Serial(source_port, baud_rate, timeout=1)
    ser_out = serial.Serial(dest_port, baud_rate, timeout=1)
    print(f"Forwarding data from {source_port} → {dest_port}")
    print(f"Flask connected to Arduino on {source_port}")
    ser = ser_in  # alias for Flask logic
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
    ser_in = ser_out = ser = MockSerial()
   
# ---------------------------------------------------------
# 2. FLASK APP SETUP
# ---------------------------------------------------------


app = Flask(__name__)


# Updated history structure: list of dicts:
# [{"request": "Water Request", "timestamp": 1700000000.123}, ...]
history = []             # store Arduino requests
latest_led_message = ""  # last message sent back to Arduino


# Button code mapping
BUTTON_MAP = {
    "R1": "Bathroom Request",
    "R2": "Water Request",
    "R3": "Food Request",
    "R4": "Blanket Request",
    "R5": "HELP! Emergency"
}


# ---------------------------------------------------------
# 3. PROCESS REQUEST (Flask logic)
# ---------------------------------------------------------


def process_request(request):
    """ Sends the command back to Arduinos to confirm/trigger action. """
    global latest_led_message


    led_message = request.strip()
    latest_led_message = led_message


    msg = (led_message + "\n").encode()


    # Send back to both Arduinos (if connected)
    try:
        ser.write(msg)      
        ser_out.write(msg)  
    except Exception as e:
        # Only print write error if not using MockSerial
        if not isinstance(ser, MockSerial):
            print("Write to serial failed:", e)


    print(f"[REQUEST PROCESSED] {request} → sent {led_message}")


# ---------------------------------------------------------
# 4. UNIFIED SERIAL HANDLER
# ---------------------------------------------------------


def serial_handler():
    """ Reads FROM COM6, forwards to COM5, and processes for Flask. """
    while True:
        try:
            if ser_in.in_waiting:
                data = ser_in.read(ser_in.in_waiting)
                current_time = time.time() # Capture time immediately upon reading


                # 1. Forward to Arduino 1 (COM5)
                ser_out.write(data)
                print(f"[FORWARDED] {data}")


                # 2. Interpret for Flask
                try:
                    line = data.decode(errors="ignore").strip()


                    if line.startswith("R"):
                        readable_request = BUTTON_MAP.get(line, line)
                        # Store object with request and timestamp
                        history.append({
                            "request": readable_request,
                            "timestamp": current_time
                        })
                        process_request(line)
                    elif "REQUEST:" in line:
                        readable_request = line.replace("REQUEST:", "").replace("_", " ").title()
                        # Store object with request and timestamp
                        history.append({
                            "request": readable_request,
                            "timestamp": current_time
                        })
                except Exception as e:
                    print("Decode/Process error:", e)
        except Exception as e:
            print("Serial read error:", e)


        time.sleep(0.01)


# Start unified handler
threading.Thread(target=serial_handler, daemon=True).start()


# ---------------------------------------------------------
# 5. FLASK ROUTES
# ---------------------------------------------------------


@app.route("/")
def serve_dashboard():
    # Serve the static main.html from the project root
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, "main.html")


# Helper to format timestamp
def format_timestamp(ts):
    """Converts a Unix timestamp float to a HH:MM:SS AM/PM string."""
    return time.strftime("%I:%M:%S %p", time.localtime(ts))




@app.route("/api/dashboard-data")
def dashboard_data():
    """ Returns the current dashboard data, including structured history with timestamps. """
   
    # Prioritize latest requests (last 5) - turn into tasks
    prioritized_tasks = [
        {"task": f"Handle {req['request']}", "urgency": "high"}
        for req in history[-5:]
    ]


    # Live request feed (last 10) - Now sending structured data with formatted timestamp
    request_feed = [
        {
            "request_text": req['request'],
            "timestamp_str": format_timestamp(req['timestamp']),
            # Assuming all serial requests are high urgency for this demo
            "urgency": "high"
        }
        for req in history[-10:]
    ]


    # Simple hardcoded AI insights + dynamic one if available
    ai_insights = []
    if history:
        latest_req = history[-1]
        ai_insights.append(f"Most recent: {latest_req['request']} at {format_timestamp(latest_req['timestamp'])}")
    else:
        ai_insights.append("No requests yet")
    # Keep an example insight (hardcoded) for unsupported features
    ai_insights.append("Insight: Check patient hydration if multiple water requests appear.")


    # Hardcoded wellbeing summary placeholders
    wellbeing_summary = {
        "score": f"{min(len(history), 10)}/10",  # simple proxy score
        "pain_trend": "Stable",
        "mobility": "Normal",
        "hydration": "Adequate"
    }


    return jsonify({
        "prioritized_tasks": prioritized_tasks,
        "request_feed": request_feed,
        "ai_insights": ai_insights,
        "wellbeing_summary": wellbeing_summary,
        "latest_led_message": latest_led_message
    })




@app.route("/api/status")
def status():
    # Preserve the old home JSON behavior at a new endpoint
    return jsonify({
        "status": "running",
        "latest_led_message": latest_led_message,
        "history": history
    })




# ---------------------------------------------------------
# 6. RUN FLASK SERVER
# ---------------------------------------------------------


if __name__ == "__main__":
    print("Flask server running on http://127.0.0.1:5000")
    # use_reloader=False is important when running threads
    app.run(debug=True, use_reloader=False)



