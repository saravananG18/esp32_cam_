import cv2
import numpy as np
import urllib.request
from pyzbar import pyzbar

# ==========================================================
# CONFIGURATION SETTINGS
# ==========================================================
ESP32_IP = "esp32cam_ip_address"  # Update if your IP changes again
STREAM_URL = f"http://{ESP32_IP}/"
# ==========================================================

print(f"Connecting to ESP32 stream at: {STREAM_URL}")

try:
    # Open the network socket channel natively
    stream = urllib.request.urlopen(STREAM_URL, timeout=10)
    print("✅ Direct socket linked successfully! Processing video stream...")
except Exception as e:
    print(f"❌ Connection Failed: {e}")
    exit()

# Use a dynamic bytearray to prevent network data stalls
bytes_accumulator = bytearray()

while True:
    try:
        # Pull raw chunks from the network card buffer array
        chunk = stream.read(2048)
        if not chunk:
            print("⚠️ Out of stream data.")
            break
            
        bytes_accumulator.extend(chunk)
        
        # Continuously search for JPEG frame delimiters inside the array
        start_idx = bytes_accumulator.find(b'\xff\xd8') # Start of JPEG frame
        end_idx = bytes_accumulator.find(b'\xff\xd9')   # End of JPEG frame
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            # Extract the isolated image payload data block
            jpg_bytes = bytes_accumulator[start_idx:end_idx+2]
            
            # Flush the processed bytes out of memory immediately
            bytes_accumulator = bytes_accumulator[end_idx+2:]
            
            # Decode the compressed image block into screen pixels
            frame = cv2.imdecode(np.frombuffer(jpg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            if frame is None:
                continue

            # Check the screen pixel grid array for any active QR patterns
            detected_qrs = pyzbar.decode(frame)
            for qr in detected_qrs:
                qr_text = qr.data.decode('utf-8')
                print("========================================")
                print(f"🎉 QR CODE DETECTED: {qr_text}")
                print("========================================")

                # Draw tracking layout borders around the code target
                pts = np.array([qr.polygon], np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

            # Display the video monitoring frame window layout
            cv2.imshow("ESP32-CAM Core Feed", frame)
            
            # Press 'q' on your physical keyboard to safely exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as error:
        print(f"\nNetwork transaction broken: {error}")
        break

cv2.destroyAllWindows()
print("Scanner operational loop terminated.")
