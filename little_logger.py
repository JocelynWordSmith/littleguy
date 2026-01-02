import time
import csv
import threading
import cv2
import numpy as np
from flask import Flask, Response, render_template_string
from mpu6050 import mpu6050
from picamera2 import Picamera2

# --- Configuration ---
USB_PATH = "/mnt/usb"
IMU_HZ = 50  # Frequency of IMU samples
app = Flask(__name__)

# Initialize Hardware
mpu = mpu6050(0x68)
picam2 = Picamera2()

# Configure dual streams: 
# 1. Main stream (720p) for H.264 recording
# 2. Lo-res stream (400x300) for web preview to save bandwidth/CPU
config = picam2.create_video_configuration(
    main={"format": "XRGB8888", "size": (1280, 720)},
    lores={"format": "XRGB8888", "size": (400, 300)}
)
picam2.configure(config)
picam2.start()

# Global State
is_recording = False
start_time_unix = 0

# --- IMU Logging Logic ---
def imu_logger_thread(csv_writer, stop_event):
    """Polls IMU at a fixed rate and writes to CSV."""
    interval = 1.0 / IMU_HZ
    while not stop_event.is_set():
        loop_start = time.time()
        
        # Get data with high-precision timestamp
        accel = mpu.get_accel_data()
        gyro = mpu.get_gyro_data()
        ts = time.time() - start_time_unix # Relative timestamp for vSLAM
        
        csv_writer.writerow([
            ts, 
            accel['x'], accel['y'], accel['z'],
            gyro['x'], gyro['y'], gyro['z']
        ])
        
        # Maintain frequency
        elapsed = time.time() - loop_start
        if interval > elapsed:
            time.sleep(interval - elapsed)

# --- Web Streaming Logic ---
def generate_frames():
    while True:
        # Pull from the low-res stream for the web
        frame = picam2.capture_array("lores")
        # Convert BGR to JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.1) # Limit web view to 10fps to save CPU

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template_string("""
        <html>
            <body style="background:#222; color:white; font-family:sans-serif; text-align:center;">
                <h1>Roomba vSLAM Capture</h1>
                <img src="/video_feed" style="border:2px solid #555; width:80%;">
                <div style="margin:20px;">
                    <a href="/toggle"><button style="padding:20px; font-size:20px;">
                        {{ 'STOP RECORDING' if recording else 'START RECORDING' }}
                    </button></a>
                </div>
            </body>
        </html>
    """, recording=is_recording)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle')
def toggle():
    global is_recording, start_time_unix, imu_stop_event, imu_thread, csv_f
    
    if not is_recording:
        # Setup Files
        ts_filename = int(time.time())
        video_path = f"{USB_PATH}/video_{ts_filename}.h264"
        csv_path = f"{USB_PATH}/imu_{ts_filename}.csv"
        
        csv_f = open(csv_path, 'w', newline='')
        writer = csv.writer(csv_f)
        writer.writerow(["ts_rel", "ax", "ay", "az", "gx", "gy", "gz"])
        
        # Start Sync
        start_time_unix = time.time()
        imu_stop_event = threading.Event()
        imu_thread = threading.Thread(target=imu_logger_thread, args=(writer, imu_stop_event))
        
        picam2.start_recording(video_path)
        imu_thread.start()
        is_recording = True
    else:
        # Stop everything
        picam2.stop_recording()
        imu_stop_event.set()
        imu_thread.join()
        csv_f.close()
        is_recording = False
        
    return index()

if __name__ == '__main__':
    # Run server on port 5000
    app.run(host='0.0.0.0', port=5000, threaded=True)
