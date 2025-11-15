import serial
import threading
import time
import os
from flask import Flask, jsonify, send_from_directory




# ---------------------------------------------------------
# 1. SERIAL SETUP (Open COM6 only ONCE)
# ---------------------------------------------------------




source_port = 'COM6'  # Arduino with buttons (input)
dest_port = 'COM5'    # Arduino with LED (output)
baud_rate = 9600




# Main serial input (COM6)
ser_in = serial.Serial(source_port, baud_rate, timeout=1)
ser = ser_in  # alias for Flask logic




# Forward destination (COM5)
ser_out = serial.Serial(dest_port, baud_rate, timeout=1)




print(f"Forwarding data from {source_port} → {dest_port}")
print(f"Flask connected to Arduino on {source_port}")




# ---------------------------------------------------------
# 2. FLASK APP SETUP
# ---------------------------------------------------------




app = Flask(__name__)




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
    """
    Send the SAME command (like R1) back to Arduino.
    This is what triggers LED blinking on Arduino 1.
    """
    global latest_led_message


    led_message = request.strip()  # keep "R1" exactly
    latest_led_message = led_message


    msg = (led_message + "\n").encode()


    # Send back to both Arduinos
    try:
        ser.write(msg)      # COM6
    except Exception as e:
        print("Write to ser failed:", e)
    try:
        ser_out.write(msg)  # COM5
    except Exception as e:
        print("Write to ser_out failed:", e)


    print(f"[REQUEST PROCESSED] {request} → sent {led_message}")




# ---------------------------------------------------------
# 4. UNIFIED SERIAL HANDLER (CRITICAL FIX)
# ---------------------------------------------------------




def serial_handler():
    """
    Reads FROM COM6 ONCE and:
        ✔ Forwards raw bytes to COM5
        ✔ Processes request for Flask
    No double-reading!
    """
    while True:
        try:
            if ser_in.in_waiting:
                data = ser_in.read(ser_in.in_waiting)


                # 1. Forward to Arduino 1 (COM5)
                ser_out.write(data)
                print(f"[FORWARDED] {data}")


                # 2. Interpret for Flask
                try:
                    line = data.decode(errors="ignore").strip()
                    # The sending Arduino might send "REQUEST:BATHROOM" or "R1"
                    # Normalize: prefer R-codes (R1..R5) when present, else map REQUEST:...
                    if line.startswith("R"):
                        readable_request = BUTTON_MAP.get(line, line)
                        history.append(readable_request)
                        process_request(line)
                    elif "REQUEST:" in line:
                        # keep the original readable text in history, but also try to map back to R-codes
                        history.append(line.replace("REQUEST:", "").replace("_", " ").title())
                        # Optionally map to an R-code if you use the mapping (hardcoded fallback)
                        # e.g., if "BATHROOM" -> "R1"
                        # For now we won't auto-send back an R-code when only REQUEST: text arrives.
                except Exception as e:
                    print("Decode error:", e)
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




@app.route("/api/dashboard-data")
def dashboard_data():
    """
    Returns the current dashboard data consumed by main.html.
    Uses live history where available and hardcoded placeholders for unsupported
    AI/wellbeing features (per your instruction).
    """
    # Prioritize latest requests (last 5) - turn into tasks
    prioritized_tasks = [
        {"task": f"Handle {req}", "urgency": "high"}
        for req in history[-5:]
    ]


    # Live request feed (last 10), newest last for the frontend which reverses it
    request_feed = [
        {"log": req, "urgency": "high"}
        for req in history[-10:]
    ]


    # Simple hardcoded AI insights + dynamic one if available
    ai_insights = []
    if history:
        ai_insights.append(f"Most recent: {history[-1]}")
    else:
        ai_insights.append("No requests yet")
    # Keep an example insight (hardcoded) for unsupported features
    ai_insights.append("Insight: Check patient hydration if requests increase.")


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
    app.run(debug=True, use_reloader=False)



