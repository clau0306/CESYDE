import serial
import threading
import time
from flask import Flask


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
    ser.write(msg)      # COM6
    ser_out.write(msg)  # COM5


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
        if ser_in.in_waiting:
            data = ser_in.read(ser_in.in_waiting)


            # 1. Forward to Arduino 1 (COM5)
            ser_out.write(data)
            print(f"[FORWARDED] {data}")


            # 2. Interpret for Flask
            try:
                line = data.decode(errors="ignore").strip()
                if line.startswith("R"):      # example: R1
                    readable_request = BUTTON_MAP.get(line, line)  # Decode button code
                    history.append(readable_request)
                    process_request(line)
            except Exception as e:
                print("Decode error:", e)


        time.sleep(0.01)


# Start unified handler
threading.Thread(target=serial_handler, daemon=True).start()


# ---------------------------------------------------------
# 5. FLASK ROUTES
# ---------------------------------------------------------
@app.route("/")
def home():
    return {
        "status": "running",
        "latest_led_message": latest_led_message,
        "history": history
    }


# ---------------------------------------------------------
# 6. RUN FLASK SERVER
# ---------------------------------------------------------


if __name__ == "__main__":
    print("Flask server running on http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)





