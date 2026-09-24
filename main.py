import os
import time
import threading
import re
import cv2
import numpy as np

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.switch import Switch
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

# Core Navigation & Base Assets
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

status_logs = []
log_lock = threading.Lock()

def log_message(text):
    global status_logs
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {text}"
    with log_lock:
        status_logs.append(formatted)
        if len(status_logs) > 40:
            status_logs.pop(0)

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
        log_message(f"[GOLDEN HUNT] Active tab detected ({active_conf:.2f}). Proceeding...")
    else:
        e_coords, e_conf, _ = find_with_strict_check(EVENTS_ICON, retries=2)
        if e_coords:
            os.system(f"adb shell input tap {e_coords[0]} {e_coords[1]}")
            time.sleep(STEP_DELAY)
        else:
            log_message(f"[GOLDEN HUNT] Events icon missing ({e_conf:.2f}). Aborting.")
            return False

        t_coords, t_conf, _ = find_with_strict_check([ZOMBIE_INVASION_BTN, GOLDEN_ZOMBIE_ACTIVE_TAB], retries=2)
        if t_coords:
            os.system(f"adb shell input tap {t_coords[0]} {t_coords[1]}")
            time.sleep(STEP_DELAY)
        else:
            log_message(f"[GOLDEN HUNT] Tab missing ({t_conf:.2f}). Aborting.")
            return False

    s_coords, s_conf, _ = find_with_strict_check([ZOMBIE_SEARCH_BTN, SEARCH_BTN], retries=2)
    if s_coords:
        os.system(f"adb shell input tap {s_coords[0]} {s_coords[1]}")
        time.sleep(STEP_DELAY)
    else:
        log_message(f"[GOLDEN HUNT] Search button missing ({s_conf:.2f}). Aborting.")
        return False

    a_coords, a_conf, _ = find_with_strict_check([ZOMBIE_ATTACK_BTN, ATTACK_BTN], retries=2)
    if a_coords:
        os.system(f"adb shell input tap {a_coords[0]} {a_coords[1]}")
        time.sleep(STEP_DELAY)
    else:
        log_message(f"[GOLDEN HUNT] Attack button missing ({a_conf:.2f}). Aborting.")
        return False

    frame_sq = capture_screen()
    if frame_sq is not None:
        if os.path.exists(NO_QUEUE_WARN):
            _, warn_conf = find_template(frame_sq, NO_QUEUE_WARN, 0.60)
            if warn_conf >= 0.60:
                log_message("[GOLDEN HUNT] Queue Full!")
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
        log_message(f"[GOLDEN HUNT] March #{total_golden} sent with Squad {squad_num}!")
        time.sleep(MARCH_DELAY)
        return "SUCCESS"

    log_message(f"[GOLDEN HUNT] March button missing ({m_conf:.2f}). Aborting.")
    return False

def execute_golden_zombie_chain():
    global last_golden_time
    log_message("Executing Zombie Invasion Hunt...")
    for sq_num in [2, 3, 4]:
        res = launch_golden_zombie_via_event(sq_num)
        if res == "QUEUE_FULL" or res != "SUCCESS":
            break
    last_golden_time = time.time()
    log_message("[GOLDEN HUNT] Cooldown active (1m 30s)...")

def collect_base_resources():
    global total_resources, last_resource_time
    log_message("Initiating Auto-Resource Collection...")
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
    log_message(f"Resource Sweeper complete! Collected {collected_count} nodes.")

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

        if not help_enabled and not join_enabled:
            time.sleep(1.0)
            continue

        frame = capture_screen()
        if frame is None:
            time.sleep(1.0)
            continue

        if help_enabled:
            help_coords, help_conf = find_template(frame, HELP_TEMPLATE, HELP_THRESHOLD)
            if help_coords:
                total_helps += 1
                log_message(f"[HELP #{total_helps}] Match ({help_conf:.2f}) -> Tapping {help_coords}")
                os.system(f"adb shell input tap {help_coords[0]} {help_coords[1]}")
                time.sleep(1.0)
                continue

        time.sleep(1.0)

class AllianceBotUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        self.add_widget(Label(text="Alliance Automation Master Controller", font_size=20, size_hint_y=None, height=40))

        # Master Switch
        master_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        self.btn_master = Button(text="START BOT", background_color=(0, 1, 0, 1))
        self.btn_master.bind(on_press=self.toggle_master)
        master_layout.add_widget(self.btn_master)
        self.add_widget(master_layout)

        # Feature Toggles Grid
        grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=220)

        grid.add_widget(Label(text="1. Alliance Help"))
        sw_help = Switch(active=False)
        sw_help.bind(active=self.toggle_help)
        grid.add_widget(sw_help)

        grid.add_widget(Label(text="2. Auto-Join Rally"))
        sw_join = Switch(active=False)
        sw_join.bind(active=self.toggle_join)
        grid.add_widget(sw_join)

        grid.add_widget(Label(text="3. Auto-Start Rally"))
        sw_start = Switch(active=False)
        sw_start.bind(active=self.toggle_start)
        grid.add_widget(sw_start)

        grid.add_widget(Label(text="4. Zombie Invasion Hunt"))
        sw_golden = Switch(active=False)
        sw_golden.bind(active=self.toggle_golden)
        grid.add_widget(sw_golden)

        grid.add_widget(Label(text="5. Auto-Collect Res (30m)"))
        sw_res = Switch(active=False)
        sw_res.bind(active=self.toggle_res)
        grid.add_widget(sw_res)

        self.add_widget(grid)

        # Status Logs
        self.add_widget(Label(text="Action Logs:", size_hint_y=None, height=20))
        self.log_label = Label(text="Bot stopped. Enable features & hit START.", size_hint_y=None)
        self.log_label.bind(width=lambda*x: setattr(self.log_label, 'text_size', (self.log_label.width, None)))
        self.log_label.bind(texture_size=lambda*x: setattr(self.log_label, 'height', self.log_label.texture_size[1]))

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.log_label)
        self.add_widget(scroll)

        Clock.schedule_interval(self.update_logs, 0.5)

    def toggle_help(self, instance, value):
        global help_enabled
        help_enabled = value

    def toggle_join(self, instance, value):
        global join_enabled
        join_enabled = value

    def toggle_start(self, instance, value):
        global start_enabled
        start_enabled = value

    def toggle_golden(self, instance, value):
        global golden_enabled
        golden_enabled = value

    def toggle_res(self, instance, value):
        global resource_enabled
        resource_enabled = value

    def toggle_master(self, instance):
        global bot_active, last_golden_time
        bot_active = not bot_active
        if bot_active:
            self.btn_master.text = "STOP BOT"
            self.btn_master.background_color = (1, 0, 0, 1)
            last_golden_time = 0
            log_message("Master Bot Loop STARTED!")
        else:
            self.btn_master.text = "START BOT"
            self.btn_master.background_color = (0, 1, 0, 1)
            log_message("Master Bot Loop STOPPED.")

    def update_logs(self, dt):
        with log_lock:
            self.log_label.text = "\n".join(status_logs)

class MainApp(App):
    def build(self):
        threading.Thread(target=bot_worker, daemon=True).start()
        return AllianceBotUI()

if __name__ == "__main__":
    MainApp().run()
