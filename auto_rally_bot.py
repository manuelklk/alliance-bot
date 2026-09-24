import os
import time
import cv2
import numpy as np

# Configuration
DEBUG_OUTPUT = "debug_capture.png"
DOWNLOADS_PATH = "/sdcard/Download/debug_capture.png"
TEMP_CAPTURE = "/sdcard/Download/temp_screen.png"
DISPLAY_ID = "4619827677550801153"  # Your active display ID
MATCH_THRESHOLD = 0.55               # Confidence threshold

# Asset Pipeline Steps (In Order)
RALLY_STEPS = [
    {"name": "Rally Notification/Icon", "file": "assets/rally_icon.png"},
    {"name": "Join Rally Button",       "file": "assets/rally_join_btn.png"},
    {"name": "March/Deploy Button",      "file": "assets/march_btn.png"},
]

total_rallies_joined = 0

def capture_screen():
    """Captures the active screen directly via ADB shell."""
    if os.path.exists(TEMP_CAPTURE):
        try:
            os.remove(TEMP_CAPTURE)
        except OSError:
            pass
        
    os.system(f"adb shell screencap -d {DISPLAY_ID} -p > {TEMP_CAPTURE}")

    if not os.path.exists(TEMP_CAPTURE) or os.path.getsize(TEMP_CAPTURE) == 0:
        return None

    return cv2.imread(TEMP_CAPTURE)

def find_and_tap(frame, template_path):
    """Performs grayscale matching for a specific target asset."""
    if not os.path.exists(template_path):
        return None, 0.0

    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        return None, 0.0

    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    th, tw = gray_template.shape[:2]
    res = cv2.matchTemplate(gray_frame, gray_template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    if max_val >= MATCH_THRESHOLD:
        center_x = max_loc[0] + (tw // 2)
        center_y = max_loc[1] + (tw // 2)
        return (center_x, center_y), max_val

    return None, max_val

def run_rally_sequence():
    """Executes the rally join sequence step-by-step."""
    global total_rallies_joined

    frame = capture_screen()
    if frame is None:
        return

    # Check Step 1: Look for Rally Icon/Notification
    coords, conf = find_and_tap(frame, RALLY_STEPS[0]["file"])
    
    if coords:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [STEP 1] Rally detected ({conf:.2f})! Tapping icon at {coords}...")
        os.system(f"adb shell input tap {coords[0]} {coords[1]}")
        time.sleep(1.5)  # Wait for menu animation

        # Check Step 2: Look for Join Button
        frame_step2 = capture_screen()
        if frame_step2 is not None:
            coords2, conf2 = find_and_tap(frame_step2, RALLY_STEPS[1]["file"])
            if coords2:
                print(f"[{timestamp}] [STEP 2] Tapping Join Button ({conf2:.2f}) at {coords2}...")
                os.system(f"adb shell input tap {coords2[0]} {coords2[1]}")
                time.sleep(1.5)  # Wait for squad screen

                # Check Step 3: Look for March/Deploy Button
                frame_step3 = capture_screen()
                if frame_step3 is not None:
                    coords3, conf3 = find_and_tap(frame_step3, RALLY_STEPS[2]["file"])
                    if coords3:
                        total_rallies_joined += 1
                        print(f"[{timestamp}] [STEP 3] Tapping March ({conf3:.2f}) at {coords3}!")
                        os.system(f"adb shell input tap {coords3[0]} {coords3[1]}")
                        print(f"==> Successfully joined rally #{total_rallies_joined}!\n")
                        time.sleep(3.0)
    else:
        print(f"[SCANNING] Searching for rallies... Highest Conf: {conf:.4f}", end="\r")

def main():
    print("========================================")
    print("      Auto-Rally Automation Bot        ")
    print("========================================")
    print("Required Assets in assets/ folder:")
    for step in RALLY_STEPS:
        print(f" - {step['file']}")
    print("----------------------------------------")

    print("\n[STARTUP] Switch to game! Starting in 10 seconds...")
    for i in range(10, 0, -1):
        print(f"  -> Starting in {i}...", end="\r")
        time.sleep(1)
    print("\n[ACTIVE] Auto-Rally loop running!\n")

    try:
        while True:
            run_rally_sequence()
            time.sleep(2.5)

    except KeyboardInterrupt:
        print(f"\n\n[STOPPED] Bot paused by user.")
        print(f"Total Rallies Joined: {total_rallies_joined}\n")

if __name__ == "__main__":
    main()
