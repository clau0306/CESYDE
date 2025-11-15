import serial
import time

# Configure your serial ports
# Replace COM3 and COM4 with your actual ports
source_port = 'COM6'    # Port to read from
dest_port = 'COM5'      # Port to write to
baud_rate = 9600        # Make sure both devices use the same baud rate

# Open the serial ports
ser_in = serial.Serial(source_port, baud_rate, timeout=1)
ser_out = serial.Serial(dest_port, baud_rate, timeout=1)

print(f"Forwarding data from {source_port} to {dest_port}...")

try:
    while True:
        if ser_in.in_waiting:  # Check if there's data to read
            data = ser_in.read(ser_in.in_waiting)  # Read all available data
            ser_out.write(data.strip())                     # Write to the destination
            print(f"Forwarded: {data}")
        time.sleep(0.01)  # Slight delay to avoid busy waiting
except KeyboardInterrupt:
    print("Stopping...")
finally:
    ser_in.close()
    ser_out.close()