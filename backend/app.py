import serial
import threading
import time
from flask import Flask, render_template

# -----------------------------
# 1. SERIAL SETUP (Arduino USB)
# -----------------------------
# CHANGE "COM3" TO YOUR PORT (COM3, COM4 on Windows, /dev/tty.usbmodem on Mac)
SERIAL_PORT = "COM3"
BAUD_RATE = 9600


ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
print(f"Connected to Arduino on {SERIAL_PORT}")


# -----------------------------
# 2. FLASK APP SETUP
# -----------------------------
app = Flask(__name__)

# Store all incoming patient requests
history = []

# Store message sent back to Arduino for the LED display
latest_led_message = ""

# -----------------------------
# 3. HANDLE ARDUINO REQUEST
# -----------------------------
def process_request(request):
    """
    This function receives a request string like:
    'WATER', 'PAIN:3', 'BLANKET'
    You will later extend this to include AI.
    """
    global latest_led_message

    # Just echo the request for now (simple logic before AI)
    led_message = f"{request[:12]}"  # trim for LED

    latest_led_message = led_message

    # Send LED message back to Arduino
    if ser:
        ser.write((led_message + "\n").encode())

    print(f"[REQUEST] {request} → LED msg: {led_message}")


# -----------------------------
# 4. SERIAL READER THREAD
# -----------------------------
def serial_reader():
    """Reads messages from Arduino in the background."""
    while True:
        if ser:
            line = ser.readline().decode(errors="ignore").strip()

            if line.startswith("REQUEST:"):
                # Remove prefix
                request = line.replace("REQUEST:", "")
                history.append(request)

                # Process request (later include AI)
                process_request(request)

        time.sleep(0.1)


# Start the reader thread
threading.Thread(target=serial_reader, daemon=True).start()

