import os
import time
import cv2
import numpy as np

# Configuration
TEMPLATE_PATH = "assets/alliance_help_btn.png"
DEBUG_OUTPUT = "debug_capture.png"
DOWNLOADS_PATH = "/sdcard/Download/debug_capture.png"
TEMP_CAPTURE = "/sdcard/Download/temp_screen.png"
DISPLAY_ID = "4619827677550801153"  # Your active display ID
MATCH_THRESHOLD = 0.80               # Minimum confidence score (80%)
LOOP_INTERVAL = 3.0                  # Time in seconds between capture loops

def initial_delay(seconds=10):
    """Gives you time to switch back to the game before automation starts."""
    print(f"\n[STARTUP] Get ready! Switching to the game in {seconds} seconds...")
    for i in range(seconds, 0, -1):
        print(f"  -> Starting in {i}...")
        time.sleep(1)
    print("  [ACTIVE] Automation loop started!\n")

def capture_screen():
    """Captures the active screen directly to storage via ADB shell."""
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
    if frame is None:
        print("[ERROR] OpenCV could not read capture file.")
        return None

    return frame

def process_and_tap(frame):
    """Searches for the target template and taps screen coordinates if found."""
    if not os.path.exists(TEMPLATE_PATH):
        print(f"[INFO] Template '{TEMPLATE_PATH}' not found in assets/ directory.")
        print("  -> Saving current frame to Downloads/debug_capture.png for cropping...")
        cv2.imwrite(DEBUG_OUTPUT, frame)
        os.system(f"cp {DEBUG_OUTPUT} {DOWNLOADS_PATH} 2>/dev/null")
        os.system(f"adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{DOWNLOADS_PATH} >/dev/null 2>&1")
        return False

    template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_COLOR)
    if template is None:
        print("[ERROR] Failed to load template image.")
        return False

    th, tw = template.shape[:2]
    res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    top_left = max_loc
    center_x = top_left[0] + (tw // 2)
    center_y = top_left[1] + (th // 2)

    print(f"[SCAN] Confidence: {max_val:.4f} | Target: ({center_x}, {center_y})")

    # Annotate debug frame
    annotated_frame = frame.copy()
    color = (0, 255, 0) if max_val >= MATCH_THRESHOLD else (0, 0, 255)
    bottom_right = (top_left[0] + tw, top_left[1] + th)
    cv2.rectangle(annotated_frame, top_left, bottom_right, color, 3)
    cv2.putText(annotated_frame, f"Conf: {max_val:.2f}", (top_left[0], top_left[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.imwrite(DEBUG_OUTPUT, annotated_frame)
    os.system(f"cp {DEBUG_OUTPUT} {DOWNLOADS_PATH} 2>/dev/null")

    if max_val >= MATCH_THRESHOLD:
        print(f"  [ACTION] Match detected! Tapping coordinates ({center_x}, {center_y})...")
        os.system(f"adb shell input tap {center_x} {center_y}")
        return True

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
        print("\n[STOPPED] Automation loop ended by user (CTRL+C).")

if __name__ == "__main__":
    main()
