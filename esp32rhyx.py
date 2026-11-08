
import cv2
import numpy as np
import urllib.request
import time

# ==========================================
# ESP32-CAM CONFIGURATION
# ==========================================

ESP32_IP = "esp32cam_ip_address"  # Replace with IP from Serial Monitor

STREAM_URL = f"http://{ESP32_IP}/stream"

print("===================================")
print("       RHYX ESP32 QR SCANNER")
print("===================================")

print("Connecting to:", STREAM_URL)

# ==========================================
# CONNECT TO ESP32 CAMERA
# ==========================================

try:
    stream = urllib.request.urlopen(
        STREAM_URL, timeout=15
    )

    print("Camera connected successfully!")
    print("Scanning for QR codes...")

except Exception as e:
    print("Connection failed:", e)
    raise SystemExit

# ==========================================
# QR CODE DETECTOR
# ==========================================

qr_detector = cv2.QRCodeDetector()

# Store previously detected QR text
last_qr = ""
last_time = 0

# Buffer for incoming JPEG data
buffer = bytearray()

# ==========================================
# MAIN SCANNING LOOP
# ==========================================

try:

    while True:

        chunk = stream.read(2048)

        if not chunk:
            print("Camera stream disconnected.")
            break

        buffer.extend(chunk)

        # Find JPEG frame boundaries
        start = buffer.find(b'\xff\xd8')
        end = buffer.find(b'\xff\xd9')

        if start != -1 and end != -1 and end > start:

            # Extract complete JPEG frame
            jpg_data = buffer[start:end + 2]

            # Remove processed data
            del buffer[:end + 2]

            # Convert JPEG into OpenCV image
            frame = cv2.imdecode(
                np.frombuffer(jpg_data, dtype=np.uint8),
                cv2.IMREAD_COLOR
            )

            if frame is None:
                continue

            # ==================================
            # DETECT QR CODES
            # ==================================

            found, decoded_info, points, _ = (
                qr_detector.detectAndDecodeMulti(frame)
            )

            if found and points is not None:

                for i, qr_text in enumerate(decoded_info):

                    if not qr_text:
                        continue

                    current_time = time.time()

                    # Print only when QR changes
                    if (qr_text != last_qr or
                            current_time - last_time > 3):

                        print("\n================================")
                        print("QR CODE DETECTED!")
                        print("QR DATA:", qr_text)
                        print("================================")

                        last_qr = qr_text
                        last_time = current_time

                    # Draw QR boundary
                    polygon = points[i].astype(
                        np.int32
                    ).reshape((-1, 1, 2))

                    cv2.polylines(
                        frame,
                        [polygon],
                        True,
                        (0, 255, 0),
                        3
                    )

                    # Display decoded text
                    x, y = polygon[0][0]

                    cv2.putText(
                        frame,
                        qr_text[:40],
                        (int(x), max(25, int(y) - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2
                    )

            else:

                # Fallback for a single QR code
                qr_text, points, _ = (
                    qr_detector.detectAndDecode(frame)
                )

                if qr_text and points is not None:

                    current_time = time.time()

                    if (qr_text != last_qr or
                            current_time - last_time > 3):

                        print("\nQR CODE DETECTED:", qr_text)

                        last_qr = qr_text
                        last_time = current_time

                    polygon = points.astype(
                        np.int32
                    ).reshape((-1, 1, 2))

                    cv2.polylines(
                        frame,
                        [polygon],
                        True,
                        (0, 255, 0),
                        3
                    )

            # ==================================
            # DISPLAY CAMERA
            # ==================================

            cv2.imshow(
                "RHYX ESP32 QR Scanner",
                frame
            )

            # Press Q to exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Prevent unlimited buffer growth
        if len(buffer) > 2 * 1024 * 1024:
            buffer.clear()

except KeyboardInterrupt:
    print("\nScanner stopped by user.")

except Exception as e:
    print("Scanner error:", e)

finally:

    stream.close()
    cv2.destroyAllWindows()

    print("QR scanner terminated.")
