import os
import time
import threading
import re
import cv2
import numpy as np

# Navigation & Base Assets
MAP_BTN = "assets/world_map_btn.png"
HOME_BASE_BTN = "assets/home_base_btn.png"
RESOURCE_ICON = "assets/resource_collect_icon.png"

# Help & Rally Assets
HELP_TEMPLATE = "assets/alliance_help_btn.png"
RALLY_ICON = "assets/rally_icon.png"
RALLY_JOIN = "assets/rally_join_btn.png"
MARCH_BTN = "assets/march_btn.png"

# Start Rally Assets
SEARCH_LENS = "assets/search_lens.png"
DOOM_ELITE_TAB = "assets/doom_elite_tab.png"
SEARCH_BTN = "assets/search_btn.png"
ATTACK_BTN = "assets/attack_btn.png"
START_RALLY_BTN = "assets/start_rally_btn.png"

# Zombie Invasion Event Assets
EVENTS_ICON = "assets/events_icon.png"
ZOMBIE_INVASION_BTN = "assets/zombie_invasion_btn.png"
GOLDEN_ZOMBIE_ACTIVE_TAB = "assets/golden_zombie_active_tab.png"
ZOMBIE_SEARCH_BTN = "assets/zombie_search_btn.png"
ZOMBIE_ATTACK_BTN = "assets/zombie_attack_btn.png"

# Multi-Squad Assets
SQUAD_BTNS = {
    1: "assets/squad_1_btn.png",
    2: "assets/squad_2_btn.png",
    3: "assets/squad_3_btn.png",
    4: "assets/squad_4_btn.png"
}
NO_QUEUE_WARN = "assets/no_march_warning.png"

TEMP_CAPTURE = "/sdcard/Download/temp_screen.png"

# Thresholds & Delays
STRICT_THRESHOLD = 0.50
HELP_THRESHOLD = 0.65
RALLY_THRESHOLD = 0.55
RESOURCE_THRESHOLD = 0.45

STEP_DELAY = 1.2
MARCH_DELAY = 1.5

JOIN_COOLDOWN = 30
RETRY_INTERVAL = 60
GOLDEN_RETRY_INTERVAL = 90
RESOURCE_INTERVAL = 1800

# Global Toggles - ALL DISABLED BY DEFAULT
bot_active = False
help_enabled = False
join_enabled = False
start_enabled = False
golden_enabled = False
resource_enabled = False

bot_running = True
total_helps = 0
total_joined = 0
total_started = 0
total_golden = 0
total_resources = 0

last_join_time = 0
last_start_time = 0
last_golden_time = 0
last_resource_time = 0
last_action = "Idle - Select an option from menu"
action_lock = threading.Lock()

def update_status(text):
    global last_action
    with action_lock:
        last_action = text

def get_screen_resolution():
    try:
        output = os.popen("adb shell wm size").read()
        match = re.search(r"Physical size:\s*(\d+)x(\d+)", output)
        if match:
            return int(match.group(1)), int(match.group(2))
    except Exception:
        pass
    return 1080, 2400

def countdown(seconds=10, reason="Switch to game"):
    print(f"\n[COUNTDOWN] {reason}! Starting in {seconds} seconds...")
    for i in range(seconds, 0, -1):
        print(f"  -> Starting in {i}...", end="\r")
        time.sleep(1)
    print("  -> Countdown finished! Executing action...\n")

def capture_screen():
    if os.path.exists(TEMP_CAPTURE):
        try:
            os.remove(TEMP_CAPTURE)
        except OSError:
            pass
        
    os.system(f"adb shell screencap -p 2>/dev/null > {TEMP_CAPTURE}")
    time.sleep(0.15)
    
    if not os.path.exists(TEMP_CAPTURE) or os.path.getsize(TEMP_CAPTURE) == 0:
        return None
    return cv2.imread(TEMP_CAPTURE)

def find_template(frame, template_path, threshold=0.50):
    if not os.path.exists(template_path):
        return None, 0.0

    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None or frame is None:
        return None, 0.0

    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    best_val = 0.0
    best_coords = None

    for scale in [0.75, 1.0, 1.25]:
        tw = int(gray_template.shape[1] * scale)
        th = int(gray_template.shape[0] * scale)
        
        if tw > gray_frame.shape[1] or th > gray_frame.shape[0] or tw == 0 or th == 0:
            continue

        resized_template = cv2.resize(gray_template, (tw, th), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(gray_frame, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val > best_val:
            best_val = max_val
            center_x = max_loc[0] + (tw // 2)
            center_y = max_loc[1] + (th // 2)
            best_coords = (center_x, center_y)

    if best_val >= threshold:
        return best_coords, best_val

    return None, best_val

def find_with_strict_check(asset_paths, threshold=STRICT_THRESHOLD, retries=2):
    if isinstance(asset_paths, str):
        asset_paths = [asset_paths]

    for _ in range(retries):
        frame = capture_screen()
        if frame is not None:
            for path in asset_paths:
                coords, conf = find_template(frame, path, threshold)
                if coords:
                    return coords, conf, frame
        time.sleep(0.8)

    return None, 0.0, None

def launch_golden_zombie_via_event(squad_num):
    global total_golden

    _, active_conf, _ = find_with_strict_check(GOLDEN_ZOMBIE_ACTIVE_TAB, retries=1)
    if active_conf:
        update_status(f"[GOLDEN HUNT] Active tab detected ({active_conf:.2f}). Proceeding...")
    else:
        e_coords, e_conf, _ = find_with_strict_check(EVENTS_ICON, retries=2)
        if e_coords:
            os.system(f"adb shell input tap {e_coords[0]} {e_coords[1]}")
            time.sleep(STEP_DELAY)
        else:
            update_status(f"[GOLDEN HUNT] Events icon missing ({e_conf:.2f}). Aborting.")
            return False

        t_coords, t_conf, _ = find_with_strict_check([ZOMBIE_INVASION_BTN, GOLDEN_ZOMBIE_ACTIVE_TAB], retries=2)
        if t_coords:
            os.system(f"adb shell input tap {t_coords[0]} {t_coords[1]}")
            time.sleep(STEP_DELAY)
        else:
            update_status(f"[GOLDEN HUNT] Tab missing ({t_conf:.2f}). Aborting.")
            return False

    s_coords, s_conf, _ = find_with_strict_check([ZOMBIE_SEARCH_BTN, SEARCH_BTN], retries=2)
    if s_coords:
        os.system(f"adb shell input tap {s_coords[0]} {s_coords[1]}")
        time.sleep(STEP_DELAY)
    else:
        update_status(f"[GOLDEN HUNT] Search button missing ({s_conf:.2f}). Aborting.")
        return False

    a_coords, a_conf, _ = find_with_strict_check([ZOMBIE_ATTACK_BTN, ATTACK_BTN], retries=2)
    if a_coords:
        os.system(f"adb shell input tap {a_coords[0]} {a_coords[1]}")
        time.sleep(STEP_DELAY)
    else:
        update_status(f"[GOLDEN HUNT] Attack button missing ({a_conf:.2f}). Aborting.")
        return False

    frame_sq = capture_screen()
    if frame_sq is not None:
        if os.path.exists(NO_QUEUE_WARN):
            _, warn_conf = find_template(frame_sq, NO_QUEUE_WARN, 0.60)
            if warn_conf >= 0.60:
                update_status("[GOLDEN HUNT] Queue Full!")
                return "QUEUE_FULL"

        sq_asset = SQUAD_BTNS.get(squad_num)
        if sq_asset and os.path.exists(sq_asset):
            sq_coords, _ = find_template(frame_sq, sq_asset, STRICT_THRESHOLD)
            if sq_coords:
                os.system(f"adb shell input tap {sq_coords[0]} {sq_coords[1]}")
                time.sleep(0.5)

    m_coords, m_conf, _ = find_with_strict_check(MARCH_BTN, retries=2)
    if m_coords:
        os.system(f"adb shell input tap {m_coords[0]} {m_coords[1]}")
        total_golden += 1
        update_status(f"[GOLDEN HUNT] March #{total_golden} sent with Squad {squad_num}!")
        time.sleep(MARCH_DELAY)
        return "SUCCESS"

    update_status(f"[GOLDEN HUNT] March button missing ({m_conf:.2f}). Aborting.")
    return False

def execute_golden_zombie_chain():
    global last_golden_time
    w, h = get_screen_resolution()
    update_status(f"Executing Zombie Invasion Hunt ({w}x{h})...")

    for sq_num in [2, 3, 4]:
        res = launch_golden_zombie_via_event(sq_num)
        if res == "QUEUE_FULL" or res != "SUCCESS":
            break

    last_golden_time = time.time()
    update_status("[GOLDEN HUNT] Sequence finished. Cooldown active (1m 30s)...")

def ensure_inside_base():
    frame = capture_screen()
    if frame is None:
        return False

    hb_coords, hb_conf = find_template(frame, HOME_BASE_BTN, STRICT_THRESHOLD)
    if hb_coords:
        update_status(f"[SMART NAV] Returning to Base ({hb_conf:.2f})...")
        os.system(f"adb shell input tap {hb_coords[0]} {hb_coords[1]}")
        time.sleep(2.0)
        return True

    map_coords, map_conf = find_template(frame, MAP_BTN, STRICT_THRESHOLD)
    if map_coords:
        update_status(f"[SMART NAV] Already inside Base ({map_conf:.2f}).")
        return True

    return False

def collect_base_resources():
    global total_resources, last_resource_time
    update_status("Initiating Auto-Resource Collection...")

    if not ensure_inside_base():
        last_resource_time = time.time()
        return False

    collected_count = 0
    for _ in range(3):
        frame = capture_screen()
        if frame is None:
            break

        coords, conf = find_template(frame, RESOURCE_ICON, RESOURCE_THRESHOLD)
        if coords:
            os.system(f"adb shell input tap {coords[0]} {coords[1]}")
            collected_count += 1
            time.sleep(0.8)
        else:
            break

    total_resources += collected_count
    last_resource_time = time.time()
    update_status(f"Resource Sweeper complete! Collected {collected_count} nodes.")
    return True

def launch_single_rally(squad_num, is_first_rally=False):
    global total_started

    steps = []
    if is_first_rally:
        steps.append(("World Map Icon", MAP_BTN, STEP_DELAY))

    steps.extend([
        ("Search Lens", SEARCH_LENS, STEP_DELAY),
        ("Doom Elite Tab", DOOM_ELITE_TAB, STEP_DELAY),
        ("Search Button", SEARCH_BTN, STEP_DELAY),
        ("Attack / Rally Button", ATTACK_BTN, STEP_DELAY)
    ])

    for step_name, asset_path, delay in steps:
        coords, conf, _ = find_with_strict_check(asset_path, retries=2)
        if coords:
            os.system(f"adb shell input tap {coords[0]} {coords[1]}")
            time.sleep(delay)
        else:
            update_status(f"[RALLY LOOP] Missing '{step_name}' ({conf:.2f}). Aborting.")
            return False

    frame_sq = capture_screen()
    if frame_sq is not None:
        if os.path.exists(NO_QUEUE_WARN):
            _, warn_conf = find_template(frame_sq, NO_QUEUE_WARN, 0.60)
            if warn_conf >= 0.60:
                update_status("[SMART QUEUE] Queue Full detected!")
                return "QUEUE_FULL"

        sq_asset = SQUAD_BTNS.get(squad_num)
        if sq_asset and os.path.exists(sq_asset):
            sq_coords, _ = find_template(frame_sq, sq_asset, STRICT_THRESHOLD)
            if sq_coords:
                os.system(f"adb shell input tap {sq_coords[0]} {sq_coords[1]}")
                time.sleep(0.5)

    r_coords, r_conf, _ = find_with_strict_check(START_RALLY_BTN, retries=2)
    if r_coords:
        os.system(f"adb shell input tap {r_coords[0]} {r_coords[1]}")
        total_started += 1
        update_status(f"Rally #{total_started} Dispatched using Squad {squad_num}!")
        time.sleep(MARCH_DELAY)
        return "SUCCESS"

    return False

def execute_continuous_rally_chain():
    global last_start_time
    w, h = get_screen_resolution()
    update_status(f"Starting Rally Loop ({w}x{h})...")

    for squad_num in range(1, 5):
        is_first = (squad_num == 1)
        result = launch_single_rally(squad_num, is_first_rally=is_first)

        if result == "QUEUE_FULL" or result != "SUCCESS":
            break

    last_start_time = time.time()

def bot_worker():
    global total_helps, total_joined, last_join_time, last_start_time, last_golden_time, last_resource_time

    while bot_running:
        if not bot_active:
            time.sleep(0.5)
            continue

        current_time = time.time()

        if resource_enabled and (current_time - last_resource_time >= RESOURCE_INTERVAL):
            collect_base_resources()
            continue

        if golden_enabled and (current_time - last_golden_time >= GOLDEN_RETRY_INTERVAL):
            execute_golden_zombie_chain()
            continue

        if start_enabled and (current_time - last_start_time >= RETRY_INTERVAL):
            execute_continuous_rally_chain()
            continue

        if not help_enabled and not join_enabled:
            time.sleep(1.0)
            continue

        frame = capture_screen()
        if frame is None:
            time.sleep(1.0)
            continue

        if join_enabled and (current_time - last_join_time >= JOIN_COOLDOWN):
            rally_coords, rally_conf = find_template(frame, RALLY_ICON, RALLY_THRESHOLD)
            if rally_coords:
                timestamp = time.strftime("%H:%M:%S")
                update_status(f"[{timestamp}] [JOIN STEP 1] Rally Icon ({rally_conf:.2f}) -> Tapping {rally_coords}")
                os.system(f"adb shell input tap {rally_coords[0]} {rally_coords[1]}")
                time.sleep(1.2)

                frame_s2 = capture_screen()
                if frame_s2 is not None:
                    join_coords, join_conf = find_template(frame_s2, RALLY_JOIN, RALLY_THRESHOLD)
                    if join_coords:
                        update_status(f"[{timestamp}] [JOIN STEP 2] Join Btn ({join_conf:.2f}) -> Tapping {join_coords}")
                        os.system(f"adb shell input tap {join_coords[0]} {join_coords[1]}")
                        time.sleep(1.2)

                        frame_s3 = capture_screen()
                        if frame_s3 is not None:
                            march_coords, march_conf = find_template(frame_s3, MARCH_BTN, RALLY_THRESHOLD)
                            if march_coords:
                                total_joined += 1
                                last_join_time = time.time()
                                update_status(f"[{timestamp}] [JOIN STEP 3] Joined Rally #{total_joined}.")
                                os.system(f"adb shell input tap {march_coords[0]} {march_coords[1]}")
                                time.sleep(1.5)
                                continue

        if help_enabled:
            help_coords, help_conf = find_template(frame, HELP_TEMPLATE, HELP_THRESHOLD)
            if help_coords:
                total_helps += 1
                timestamp = time.strftime("%H:%M:%S")
                update_status(f"[{timestamp}] [HELP #{total_helps}] Match ({help_conf:.2f}) -> Tapping {help_coords}")
                os.system(f"adb shell input tap {help_coords[0]} {help_coords[1]}")
                time.sleep(1.0)
                continue

        time.sleep(1.0)

def print_menu():
    os.system("clear")
    w, h = get_screen_resolution()
    
    b_status = "\033[92m[RUNNING]\033[0m" if bot_active else "\033[91m[STOPPED]\033[0m"
    h_status = "\033[92m[ON]\033[0m" if help_enabled else "\033[91m[OFF]\033[0m"
    j_status = "\033[92m[ON]\033[0m" if join_enabled else "\033[91m[OFF]\033[0m"
    s_status = "\033[92m[ON]\033[0m" if start_enabled else "\033[91m[OFF]\033[0m"
    g_status = "\033[92m[ON]\033[0m" if golden_enabled else "\033[91m[OFF]\033[0m"
    r_status = "\033[92m[ON]\033[0m" if resource_enabled else "\033[91m[OFF]\033[0m"

    print("==================================================")
    print(f"  ALLIANCE AUTOMATION (Pixel Fold Display: {w}x{h}) ")
    print("==================================================")
    print(f" [0] MASTER BOT STATE    : {b_status}")
    print("--------------------------------------------------")
    print(f" [1] Alliance Help       : {h_status} | Count: \033[93m{total_helps}\033[0m")
    print(f" [2] Auto-Join Rally     : {j_status} | Count: \033[96m{total_joined}\033[0m")
    print(f" [3] Auto-Start Rally    : {s_status} | Count: \033[95m{total_started}\033[0m")
    print(f" [4] Zombie Invasion Hunt: {g_status} | Count: \033[94m{total_golden}\033[0m")
    print(f" [5] Auto-Collect Res    : {r_status} | Count: \033[92m{total_resources}\033[0m")
    print("--------------------------------------------------")
    print(f" Last Action : {last_action}")
    print("--------------------------------------------------")
    print(" [6] Switch to Game (10s Countdown)")
    print(" [7] Manual Test: Doom Elite Chain")
    print(" [8] Manual Test: Base Resource Sweeper")
    print(" [9] Reset Counters")
    print(" [Q] Quit Program")
    print("==================================================")

def main():
    global help_enabled, join_enabled, start_enabled, golden_enabled, resource_enabled, bot_active, bot_running
    global total_helps, total_joined, total_started, total_golden, total_resources
    global last_golden_time, last_start_time, last_resource_time

    worker = threading.Thread(target=bot_worker, daemon=True)
    worker.start()

    try:
        while bot_running:
            print_menu()
            choice = input("\nSelect Option > ").strip().lower()

            if choice == "0":
                bot_active = not bot_active
                if bot_active:
                    countdown(10, "Master Bot Loop STARTED! Switch to Game")
                    last_golden_time = 0
                    last_start_time = 0
                    last_resource_time = 0
                else:
                    update_status("Master Bot Loop STOPPED.")
            elif choice == "1":
                help_enabled = not help_enabled
            elif choice == "2":
                join_enabled = not join_enabled
            elif choice == "3":
                start_enabled = not start_enabled
            elif choice == "4":
                golden_enabled = not golden_enabled
            elif choice == "5":
                resource_enabled = not resource_enabled
            elif choice == "6":
                countdown(10, "Switching to Game")
            elif choice == "7":
                countdown(10, "Manual Test Starting! Switch to Game")
                execute_continuous_rally_chain()
            elif choice == "8":
                countdown(10, "Manual Resource Sweeper Starting!")
                collect_base_resources()
            elif choice == "9":
                total_helps = 0
                total_joined = 0
                total_started = 0
                total_golden = 0
                total_resources = 0
                update_status("Counters reset to 0.")
            elif choice == "q":
                bot_running = False
                break

    except KeyboardInterrupt:
        bot_running = False

    print("\nScript exited successfully.\n")

if __name__ == "__main__":
    main()
