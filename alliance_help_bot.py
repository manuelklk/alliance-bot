import os
import time
import cv2
import numpy as np

# Configuration
TEMPLATE_PATH = "assets/alliance_help_btn.png"
DEBUG_OUTPUT = "debug_capture.png"
DOWNLOADS_PATH = "/sdcard/Download/debug_capture.png"
TEMP_CAPTURE = "/sdcard/Download/temp_screen.png"
DISPLAY_ID = "4619827677550801153"  # Active display ID
MATCH_THRESHOLD = 0.60               # Adjusted threshold (60%)
LOOP_INTERVAL = 2.0                  # Delay between checks (seconds)

# Global Counter
total_taps = 0

def initial_delay(seconds=10):
    """Gives you time to switch back to the game before automation starts."""
    print(f"\n[STARTUP] Get ready! Switching to the game in {seconds} seconds...")
    for i in range(seconds, 0, -1):
        print(f"  -> Starting in {i}...")
        time.sleep(1)
    print("  [ACTIVE] Automation loop started!\n")

def capture_screen():
    """Captures active display via ADB shell."""
    if os.path.exists(TEMP_CAPTURE):
        try:
            os.remove(TEMP_CAPTURE)
        except OSError:
            pass
        
    os.system(f"adb shell screencap -d {DISPLAY_ID} -p > {TEMP_CAPTURE}")

    if not os.path.exists(TEMP_CAPTURE) or os.path.getsize(TEMP_CAPTURE) == 0:
        print("[ERROR] Failed to capture screen buffer.")
        return None

    frame = cv2.imread(TEMP_CAPTURE)
    return frame

def process_and_tap(frame):
    """Matches template in grayscale, logs taps, and updates total counter."""
    global total_taps

    if not os.path.exists(TEMPLATE_PATH):
        print(f"[INFO] Template '{TEMPLATE_PATH}' not found. Saving debug frame...")
        cv2.imwrite(DEBUG_OUTPUT, frame)
        os.system(f"cp {DEBUG_OUTPUT} {DOWNLOADS_PATH} 2>/dev/null")
        os.system(f"adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{DOWNLOADS_PATH} >/dev/null 2>&1")
        return False

    template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_COLOR)
    if template is None:
        print("[ERROR] Failed to load template image.")
        return False

    # Convert both frame and template to Grayscale for far superior matching accuracy
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    th, tw = gray_template.shape[:2]
    res = cv2.matchTemplate(gray_frame, gray_template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    top_left = max_loc
    center_x = top_left[0] + (tw // 2)
    center_y = top_left[1] + (th // 2)

    # Annotate debug frame
    annotated_frame = frame.copy()
    color = (0, 255, 0) if max_val >= MATCH_THRESHOLD else (0, 0, 255)
    bottom_right = (top_left[0] + tw, top_left[1] + th)
    cv2.rectangle(annotated_frame, top_left, bottom_right, color, 3)
    cv2.putText(annotated_frame, f"Conf: {max_val:.2f} | Taps: {total_taps}", (top_left[0], max(30, top_left[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    cv2.imwrite(DEBUG_OUTPUT, annotated_frame)
    os.system(f"cp {DEBUG_OUTPUT} {DOWNLOADS_PATH} 2>/dev/null")

    if max_val >= MATCH_THRESHOLD:
        total_taps += 1
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [TAP #{total_taps}] Match found ({max_val:.2f}) -> Tapping ({center_x}, {center_y})")
        os.system(f"adb shell input tap {center_x} {center_y}")
        return True
    else:
        print(f"[SCAN] Confidence: {max_val:.4f} (Below {MATCH_THRESHOLD:.2f}) | Total Taps: {total_taps}")

    return False

def main():
    print("========================================")
    print("   Alliance Help Automation Bot Started ")
    print("========================================")
    
    initial_delay(10)
    
    try:
        while True:
            frame = capture_screen()
            if frame is not None:
                process_and_tap(frame)
            time.sleep(LOOP_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n[STOPPED] Bot paused by user.")
        print(f"========================================")
        print(f"   FINAL STATS: Total Alliance Helps Tapped = {total_taps}")
        print(f"========================================")

if __name__ == "__main__":
    main()
