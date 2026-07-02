"""
Traffic Eye — AI Signal Detection & Violation System
Made by Nitin Kumar
"""

import tkinter as tk
from tkinter import filedialog
import math
import random
import time
from collections import deque

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageTk
    CV2_OK = True
except ImportError:
    CV2_OK = False

# ================================================================
# THEME
# ================================================================
C = {
    'bg1': '#0a0e17', 'bg2': '#111827', 'card': '#1a2234',
    'green': '#00e676', 'red': '#ff1744', 'amber': '#ffab00',
    'cyan': '#00e5ff', 'txt': '#e8eaf6', 'muted': '#7986cb',
    'border': '#2a3550', 'road': '#2d333b', 'dark': '#0d1117',
    'bldg': '#151a23', 'side': '#1c2128'
}
VTYPES = ['Car', 'Bike', 'Truck', 'Bus']
VCOLS = {'Car': ['#e53935','#1e88e5','#43a047','#fb8c00','#8e24aa','#00acc1','#f5f5f5','#424242'],
         'Bike': ['#ff6f00','#e65100','#37474f','#212121'],
         'Truck': ['#ff8f00','#5d4037','#455a64','#d84315'],
         'Bus': ['#1565c0','#c62828','#2e7d32','#f9a825']}
VSZ = {'Car': (50,28), 'Bike': (30,16), 'Truck': (70,32), 'Bus': (75,34)}
STOP_X, CW, CH = 350, 800, 400
SIG_TIMINGS = {'RED': 5000, 'YELLOW': 2000, 'GREEN': 5000}
SIG_COLS = {'RED': '#ff1744', 'YELLOW': '#ffab00', 'GREEN': '#00e676'}
SIG_OFF = {'RED': '#331111', 'YELLOW': '#332200', 'GREEN': '#003311'}


# ================================================================
# VEHICLE
# ================================================================
class Vehicle:
    _id = 0
    def __init__(self, sig):
        Vehicle._id += 1
        self.vid = Vehicle._id
        self.type = random.choice(VTYPES)
        self.color = random.choice(VCOLS[self.type])
        w, h = VSZ[self.type]
        self.w = w + random.randint(-5, 5)
        self.h = h + random.randint(-3, 3)
        self.lane = random.randint(0, 2)
        self.ly = 120 + self.lane * 75
        self.x = CW + random.randint(0, 100)
        self.y = self.ly - self.h // 2
        self.spd = 1.5 + random.random() * 3
        self.kmh = round(self.spd * 15 + random.random() * 20)
        self.detected = False
        self.counted = False
        self.vcheck = False
        self.conf = round(0.82 + random.random() * 0.17, 2)
        self.dalpha = 0.0
        self.violator = False
        self.stopped = False
        self.will_viol = (sig == 'RED' and random.random() < 0.15)

    def update(self, sig):
        if sig in ('RED', 'YELLOW') and not self.counted:
            if self.x - self.w // 2 <= STOP_X and self.x + self.w // 2 >= STOP_X - 60:
                if not self.will_viol and not self.stopped:
                    self.stopped = True
        if sig == 'GREEN' and self.stopped:
            self.stopped = False
        if not self.stopped:
            self.x -= self.spd
        if abs(self.x - STOP_X) < 80:
            self.detected = True
            self.dalpha = min(1.0, self.dalpha + 0.1)
        if self.x < STOP_X and not self.counted:
            self.counted = True
        if not self.vcheck and self.x < STOP_X - 5 and sig == 'RED':
            self.vcheck = True
            if self.will_viol:
                self.violator = True
        if self.x < STOP_X - 150:
            self.dalpha = max(0, self.dalpha - 0.03)

    def off(self):
        return self.x < -100


# ================================================================
# MAIN APP
# ================================================================
class TrafficEyeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Traffic Eye — AI Signal Detection & Violation System")
        self.root.configure(bg=C['bg1'])
        self.root.geometry("1420x870")
        self.root.minsize(1100, 700)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.total_v = 0
        self.total_viol = 0
        self.sig = 'GREEN'
        self.sig_method = 'simulation'
        self.sig_conf = 0
        self.sig_start = time.time()
        self.avg_conf = 0.0
        self.speeds = []
        self.vlog = []
        self.cnts = {'Car': 0, 'Bike': 0, 'Truck': 0, 'Bus': 0}
        self.t0 = time.time()
        self.vehs = []
        self.last_spawn = 0
        self.fps_q = deque(maxlen=30)
        self.last_ft = time.time()
        self.running = True
        self.mode = 'simulation'
        self.cap = None
        self.cam_on = False
        self.photo = None
        self.timeline = deque(maxlen=15)
        self.tl_v = 0
        self.tl_vl = 0
        self.manual_sig_region = None

        self._build()
        self._loop()

    # ---- UI BUILDING ----
    def _build(self):
        self._build_header()
        self._build_stats()
        self._build_main()
        self._build_footer()

    def _lbl(self, p, text, fg='txt', bg='card', font=('Helvetica', 10), **kw):
        return tk.Label(p, text=text, fg=C.get(fg, fg), bg=C.get(bg, bg), font=font,
                        highlightthickness=0, borderwidth=0, **kw)

    def _build_header(self):
        h = tk.Frame(self.root, bg=C['bg2'], highlightbackground=C['border'], highlightthickness=1)
        h.pack(fill='x')
        inner = tk.Frame(h, bg=C['bg2'])
        inner.pack(fill='x', padx=16, pady=10)
        left = tk.Frame(inner, bg=C['bg2'])
        left.pack(side='left')
        icon = tk.Canvas(left, width=38, height=38, bg=C['bg2'], highlightthickness=0)
        icon.pack(side='left', padx=(0, 10))
        icon.create_rectangle(0, 0, 38, 38, fill=C['cyan'], outline='')
        icon.create_text(19, 19, text='🚦', font=('Helvetica', 16))
        self._lbl(left, 'TRAFFIC EYE', fg='txt', bg='bg2', font=('Consolas', 16, 'bold')).pack(side='left')
        self._lbl(left, 'AI SIGNAL DETECTION & VIOLATION SYSTEM', fg='muted', bg='bg2',
                  font=('Helvetica', 8)).pack(side='left', padx=(12, 0))
        right = tk.Frame(inner, bg=C['bg2'])
        right.pack(side='right')
        dot = tk.Canvas(right, width=10, height=10, bg=C['bg2'], highlightthickness=0)
        dot.pack(side='left', padx=(0, 4))
        dot.create_oval(0, 0, 10, 10, fill=C['green'], outline='')
        self._lbl(right, 'LIVE', fg='green', bg='bg2', font=('Helvetica', 10, 'bold')).pack(side='left', padx=(0, 16))
        self.time_lbl = self._lbl(right, '', fg='cyan', bg='bg2', font=('Consolas', 12))
        self.time_lbl.pack(side='left')
        self.date_lbl = self._lbl(right, '', fg='muted', bg='bg2', font=('Helvetica', 8))
        self.date_lbl.pack(side='left', padx=(8, 0))
        tk.Button(right, text='⟳ RESET', bg='#331111', fg=C['red'], font=('Helvetica', 9, 'bold'),
                  relief='flat', padx=12, pady=4, command=self._reset,
                  activebackground='#551111', cursor='hand2').pack(side='left', padx=(16, 0))

    def _build_stats(self):
        sf = tk.Frame(self.root, bg=C['bg1'])
        sf.pack(fill='x', padx=12, pady=(8, 4))
        self.stat_vals = {}
        self.stat_subs = {}
        cards = [
            ('Total Vehicles', '🚗', 'cyan', 'vehicleRate'),
            ('Red Light Violations', '🚫', 'red', 'violRate'),
            ('Signal Status', '🚦', 'green', 'sigTimer'),
            ('Detection Confidence', '🎯', 'green', 'confBar'),
        ]
        for title, icon, color, sub_id in cards:
            f = tk.Frame(sf, bg=C['card'], highlightbackground=C['border'], highlightthickness=1)
            f.pack(side='left', fill='both', expand=True, padx=3)
            top = tk.Frame(f, bg=C['card'])
            top.pack(fill='x', padx=12, pady=(10, 2))
            self._lbl(top, title.upper(), fg='muted', font=('Helvetica', 7)).pack(side='left')
            ic = tk.Canvas(top, width=26, height=26, bg=C['card'], highlightthickness=0)
            ic.pack(side='right')
            ic.create_oval(1, 1, 25, 25, fill=C[color], outline='')
            vl = self._lbl(f, '0', fg=color, font=('Consolas', 26, 'bold'))
            vl.pack(padx=12, anchor='w')
            self.stat_vals[title] = vl
            sl = self._lbl(f, '0/min', fg='green', font=('Helvetica', 8))
            sl.pack(padx=12, anchor='w', pady=(0, 8))
            self.stat_subs[title] = sl

    def _build_main(self):
        mf = tk.Frame(self.root, bg=C['bg1'])
        mf.pack(fill='both', expand=True, padx=12, pady=4)
        mf.columnconfigure(0, weight=3)
        mf.columnconfigure(1, weight=0)
        mf.rowconfigure(0, weight=1)
        # Left
        left = tk.Frame(mf, bg=C['bg1'])
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
        left.rowconfigure(1, weight=1)
        # Tabs
        tabs = tk.Frame(left, bg=C['bg1'])
        tabs.grid(row=0, column=0, sticky='ew')
        self.tab_btns = {}
        for m, icon in [('simulation', '▶'), ('camera', '📹'), ('video', '🎬')]:
            b = tk.Button(tabs, text=f' {icon} {m.capitalize()} ', bg=C['bg1'], fg=C['muted'],
                          font=('Helvetica', 10, 'bold'), relief='flat', padx=14, pady=6,
                          activebackground=C['card'], cursor='hand2',
                          command=lambda m=m: self._switch_mode(m))
            b.pack(side='left')
            self.tab_btns[m] = b
        self._highlight_tab('simulation')
        # Controls frame
        self.ctrl_frame = tk.Frame(left, bg=C['card'], highlightbackground=C['border'], highlightthickness=1)
        self.ctrl_frame.grid(row=1, column=0, sticky='nsew', pady=(2, 0))
        self.ctrl_inner = tk.Frame(self.ctrl_frame, bg=C['card'])
        self.ctrl_inner.pack(fill='x', padx=8, pady=6)
        self._show_sim_controls()
        # Canvas
        self.canvas = tk.Canvas(self.ctrl_frame, width=CW, height=CH, bg='black',
                                highlightthickness=0)
        self.canvas.pack(padx=8, pady=(0, 8))
        self.canvas.bind('<Button-1>', self._canvas_click)
        self.canvas.bind('<Double-Button-1>', self._canvas_dblclick)
        # Charts
        cf = tk.Frame(left, bg=C['bg1'])
        cf.grid(row=2, column=0, sticky='ew', pady=(4, 0))
        cf.columnconfigure(0, weight=1)
        cf.columnconfigure(1, weight=1)
        pie_f = tk.Frame(cf, bg=C['card'], highlightbackground=C['border'], highlightthickness=1)
        pie_f.grid(row=0, column=0, sticky='nsew', padx=(0, 2))
        self._lbl(pie_f, '  Vehicle Distribution', fg='amber', font=('Helvetica', 9, 'bold')).pack(anchor='w', padx=8, pady=(8, 0))
        self.pie_canvas = tk.Canvas(pie_f, width=200, height=190, bg=C['card'], highlightthickness=0)
        self.pie_canvas.pack(padx=8, pady=8)
        bar_f = tk.Frame(cf, bg=C['card'], highlightbackground=C['border'], highlightthickness=1)
        bar_f.grid(row=0, column=1, sticky='nsew', padx=(2, 0))
        self._lbl(bar_f, '  Detection Timeline', fg='green', font=('Helvetica', 9, 'bold')).pack(anchor='w', padx=8, pady=(8, 0))
        self.bar_canvas = tk.Canvas(bar_f, width=300, height=190, bg=C['card'], highlightthickness=0)
        self.bar_canvas.pack(padx=8, pady=8)
        # Right panel
        right = tk.Frame(mf, bg=C['bg1'], width=280)
        right.grid(row=0, column=1, sticky='ns')
        right.grid_propagate(False)
        self._build_signal_panel(right)
        self._build_speed_panel(right)
        self._build_cat_panel(right)
        self._build_log_panel(right)

    def _build_signal_panel(self, parent):
        f = tk.Frame(parent, bg=C['card'], highlightbackground=C['border'], highlightthickness=1)
        f.pack(fill='x', pady=(0, 4))
        self._lbl(f, '  🧠 Signal AI Analysis', fg='amber', font=('Helvetica', 9, 'bold')).pack(anchor='w', pady=(8, 4))
        self.sig_light_cv = tk.Canvas(f, width=60, height=60, bg=C['card'], highlightthickness=0)
        self.sig_light_cv.pack(pady=4)
        self.sig_big_lbl = self._lbl(f, 'GREEN', fg='green', font=('Consolas', 16, 'bold'))
        self.sig_big_lbl.pack()
        self.sig_method_lbl = self._lbl(f, 'Auto Cycle (Simulation)', fg='muted', font=('Helvetica', 7))
        self.sig_method_lbl.pack(pady=(0, 4))
        sep = tk.Frame(f, bg=C['border'], height=1)
        sep.pack(fill='x', padx=10)
        self.tl_found_lbl = self._lbl(f, 'Traffic Light Found: N/A', fg='muted', font=('Helvetica', 8))
        self.tl_found_lbl.pack(anchor='w', padx=12, pady=(6, 0))
        self.tl_conf_lbl = self._lbl(f, 'Color Confidence: N/A', fg='muted', font=('Helvetica', 8))
        self.tl_conf_lbl.pack(anchor='w', padx=12)
        self.tl_meth_lbl = self._lbl(f, 'Detection Method: Simulation', fg='muted', font=('Helvetica', 8))
        self.tl_meth_lbl.pack(anchor='w', padx=12, pady=(0, 8))

    def _build_speed_panel(self, parent):
        f = tk.Frame(parent, bg=C['card'], highlightbackground=C['border'], highlightthickness=1)
        f.pack(fill='x', pady=4)
        self._lbl(f, '  ⚡ Speed Analysis', fg='amber', font=('Helvetica', 9, 'bold')).pack(anchor='w', padx=8, pady=(8, 4))
        self.spd_bars = {}
        for label, color in [('Avg Speed', 'cyan'), ('Max Speed', 'red'), ('Min Speed', 'green')]:
            row = tk.Frame(f, bg=C['card'])
            row.pack(fill='x', padx=12, pady=2)
            self._lbl(row, label, fg='muted', font=('Helvetica', 8)).pack(side='left')
            vl = self._lbl(row, '0 km/h', fg=color, font=('Consolas', 9))
            vl.pack(side='right')
            bar_bg = tk.Canvas(row, width=100, height=4, bg=C['bg1'], highlightthickness=0)
            bar_bg.pack(side='right', padx=8)
            bar_bg.create_rectangle(0, 0, 0, 4, fill=C[color], outline='', tags='bar')
            self.spd_bars[label] = (vl, bar_bg)
        tk.Frame(f, bg=C['border'], height=1).pack(fill='x', padx=10, pady=4)
        r = tk.Frame(f, bg=C['card'])
        r.pack(fill='x', padx=12, pady=(0, 8))
        self._lbl(r, 'Speed Limit', fg='muted', font=('Helvetica', 8)).pack(side='left')
        self._lbl(r, '60 km/h', fg='amber', font=('Consolas', 9)).pack(side='right')

    def _build_cat_panel(self, parent):
        f = tk.Frame(parent, bg=C['card'], highlightbackground=C['border'], highlightthickness=1)
        f.pack(fill='x', pady=4)
        self._lbl(f, '  📋 Category Breakdown', fg='cyan', font=('Helvetica', 9, 'bold')).pack(anchor='w', padx=8, pady=(8, 4))
        self.cat_lbls = {}
        icons = {'Car': '🚗', 'Bike': '🏍️', 'Truck': '🚛', 'Bus': '🚌'}
        colors = {'Car': 'cyan', 'Bike': 'green', 'Truck': 'amber', 'Bus': 'red'}
        for t in ['Car', 'Bike', 'Truck', 'Bus']:
            row = tk.Frame(f, bg=C['bg1'])
            row.pack(fill='x', padx=10, pady=1)
            self._lbl(row, f'  {icons[t]} {t}', fg='txt', bg='bg1', font=('Helvetica', 9)).pack(side='left', pady=3)
            vl = self._lbl(row, '0', fg=colors[t], bg='bg1', font=('Consolas', 12, 'bold'))
            vl.pack(side='right', padx=10)
            self.cat_lbls[t] = vl
        tk.Frame(f, bg=C['card'], height=6).pack()

    def _build_log_panel(self, parent):
        f = tk.Frame(parent, bg=C['card'], highlightbackground=C['border'], highlightthickness=1)
        f.pack(fill='both', expand=True, pady=4)
        top = tk.Frame(f, bg=C['card'])
        top.pack(fill='x', padx=8, pady=(8, 4))
        self._lbl(top, '  ⚠ Violation Log', fg='red', font=('Helvetica', 9, 'bold')).pack(side='left')
        self.log_count_lbl = self._lbl(top, '0 entries', fg='red', font=('Helvetica', 8))
        self.log_count_lbl.pack(side='right')
        self.log_text = tk.Text(f, bg=C['bg1'], fg=C['txt'], font=('Consolas', 8),
                                wrap='word', highlightthickness=0, borderwidth=0,
                                state='disabled', cursor='arrow')
        self.log_text.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.log_text.tag_configure('red', foreground=C['red'])
        self.log_text.tag_configure('muted', foreground=C['muted'])
        self.log_text.tag_configure('amber', foreground=C['amber'])
        self.log_text.insert('end', '  Violations will appear here...\n', 'muted')

    def _build_footer(self):
        f = tk.Frame(self.root, bg=C['bg2'], highlightbackground=C['border'], highlightthickness=1)
        f.pack(fill='x', side='bottom')
        self._lbl(f, 'Made by Nitin Kumar', fg='cyan', bg='bg2',
                  font=('Consolas', 11, 'bold')).pack(pady=8)

    # ---- TABS & MODES ----
    def _highlight_tab(self, mode):
        for m, b in self.tab_btns.items():
            if m == mode:
                b.configure(bg=C['card'], fg=C['cyan'])
            else:
                b.configure(bg=C['bg1'], fg=C['muted'])

    def _clear_controls(self):
        for w in self.ctrl_inner.winfo_children():
            w.destroy()

    def _show_sim_controls(self):
        self._clear_controls()
        self._lbl(self.ctrl_inner, 'ℹ  Auto simulation — vehicles spawn and get detected automatically', fg='muted', font=('Helvetica', 8)).pack(side='left')
        self.fps_lbl = self._lbl(self.ctrl_inner, '-- FPS', fg='muted', font=('Consolas', 8))
        self.fps_lbl.pack(side='right')

    def _show_cam_controls(self):
        self._clear_controls()
        if not CV2_OK:
            self._lbl(self.ctrl_inner, '⚠ Install opencv-python: pip install opencv-python numpy pillow', fg='red', font=('Helvetica', 9, 'bold')).pack(side='left')
            return
        self.cam_start_btn = tk.Button(self.ctrl_inner, text='📹 Start Camera', bg='#0a2a3a', fg=C['cyan'],
                                        font=('Helvetica', 9, 'bold'), relief='flat', padx=12, pady=3,
                                        command=self._start_cam, cursor='hand2')
        self.cam_start_btn.pack(side='left')
        self.cam_stop_btn = tk.Button(self.ctrl_inner, text='⏹ Stop', bg='#3a1111', fg=C['red'],
                                       font=('Helvetica', 9, 'bold'), relief='flat', padx=12, pady=3,
                                       command=self._stop_cam, cursor='hand2', state='disabled')
        self.cam_stop_btn.pack(side='left', padx=4)
        self._lbl(self.ctrl_inner, 'Signal auto-detected from video. Double-click to mark traffic light.', fg='muted', font=('Helvetica', 8)).pack(side='right')

    def _show_vid_controls(self):
        self._clear_controls()
        if not CV2_OK:
            self._lbl(self.ctrl_inner, '⚠ Install opencv-python: pip install opencv-python numpy pillow', fg='red', font=('Helvetica', 9, 'bold')).pack(side='left')
            return
        tk.Button(self.ctrl_inner, text='📁 Choose Video', bg='#3a2a00', fg=C['amber'],
                  font=('Helvetica', 9, 'bold'), relief='flat', padx=12, pady=3,
                  command=self._upload_vid, cursor='hand2').pack(side='left')
        self.vid_name_lbl = self._lbl(self.ctrl_inner, 'No file selected', fg='muted', font=('Helvetica', 8))
        self.vid_name_lbl.pack(side='left', padx=8)
        self._lbl(self.ctrl_inner, 'Double-click on traffic light to mark it.', fg='muted', font=('Helvetica', 8)).pack(side='right')

    def _switch_mode(self, mode):
        self._stop_cam()
        self.mode = mode
        self.manual_sig_region = None
        self._highlight_tab(mode)
        if mode == 'simulation':
            self._show_sim_controls()
            self.sig = 'GREEN'
            self.sig_method = 'simulation'
            self.sig_start = time.time()
        elif mode == 'camera':
            self._show_cam_controls()
            self.sig = 'GREEN'
            self.sig_method = 'not_found'
        elif mode == 'video':
            self._show_vid_controls()
            self.sig = 'GREEN'
            self.sig_method = 'not_found'

    # ---- CAMERA / VIDEO ----
    def _start_cam(self):
        if not CV2_OK:
            return
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            return
        self.cam_on = True
        self.cam_start_btn.configure(state='disabled')
        self.cam_stop_btn.configure(state='normal')

    def _stop_cam(self):
        self.cam_on = False
        if self.cap:
            self.cap.release()
            self.cap = None
        if hasattr(self, 'cam_start_btn'):
            self.cam_start_btn.configure(state='normal')
        if hasattr(self, 'cam_stop_btn'):
            self.cam_stop_btn.configure(state='disabled')

    def _upload_vid(self):
        path = filedialog.askopenfilename(filetypes=[('Video', '*.mp4 *.avi *.mkv *.webm')])
        if not path:
            return
        if not CV2_OK:
            return
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            return
        self.vid_name_lbl.configure(text=path.split('/')[-1])
        self.cam_on = True

    def _canvas_click(self, e):
        if self.mode == 'simulation':
            return
        rect = self.canvas.winfo_width()
        if rect > 0:
            self.det_line_y_frac = e.y / self.canvas.winfo_height()

    def _canvas_dblclick(self, e):
        if self.mode == 'simulation':
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw > 0 and ch > 0:
            fx = e.x / cw
            fy = e.y / ch
            self.manual_sig_region = (fx - 0.03, fy - 0.12, 0.06, 0.24)

    # ---- SIGNAL ----
    def _update_sim_signal(self):
        if self.mode != 'simulation':
            return
        elapsed = (time.time() - self.sig_start) * 1000
        dur = SIG_TIMINGS[self.sig]
        rem = max(0, math.ceil((dur - elapsed) / 1000))
        if elapsed >= dur:
            if self.sig == 'RED':
                self.sig = 'GREEN'
            elif self.sig == 'GREEN':
                self.sig = 'YELLOW'
            else:
                self.sig = 'RED'
            self.sig_start = time.time()
        self.stat_subs['Signal Status'].configure(text=f'Changes in {rem}s')

    def _detect_signal_hsv(self, frame):
        if frame is None:
            return None
        if self.manual_sig_region:
            fx, fy, fw, fh = self.manual_sig_region
            h, w = frame.shape[:2]
            y1 = max(0, int(fy * h))
            y2 = min(h, int((fy + fh) * h))
            x1 = max(0, int(fx * w))
            x2 = min(w, int((fx + fw) * w))
            roi = frame[y1:y2, x1:x2]
        else:
            roi = frame
        if roi.size == 0:
            return None
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mr = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])) | \
             cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        mg = cv2.inRange(hsv, np.array([35, 100, 100]), np.array([85, 255, 255]))
        my = cv2.inRange(hsv, np.array([20, 100, 100]), np.array([35, 255, 255]))
        rc, gc, yc = cv2.countNonZero(mr), cv2.countNonZero(mg), cv2.countNonZero(my)
        mx = max(rc, gc, yc)
        if mx < 10:
            return None
        total = rc + gc + yc
        conf = round(mx / total * 100)
        if rc >= gc and rc >= yc:
            return 'RED', conf
        elif yc >= rc and yc >= gc:
            return 'YELLOW', conf
        else:
            return 'GREEN', conf

    # ---- SIMULATION DRAWING ----
    def _draw_sim(self):
        c = self.canvas
        c.delete('all')
        # Sky
        for i in range(4):
            y0 = i * 20
            shade = 13 + i * 3
            c.create_rectangle(0, y0, CW, y0 + 20, fill=f'#{shade:02x}{shade+4:02x}{shade+10:02x}', outline='')
        # Road
        c.create_rectangle(0, 80, CW, 320, fill=C['road'], outline='')
        # Road edges
        c.create_line(0, 82, CW, 82, fill='#4a5568', width=2)
        c.create_line(0, 318, CW, 318, fill='#4a5568', width=2)
        # Lane dividers
        for ly in [155, 235]:
            for x in range(0, CW, 35):
                c.create_line(x, ly, x + 20, ly, fill='#4a5568', width=1, dash=(1,))
        # Stop line
        c.create_line(STOP_X, 82, STOP_X, 318, fill='white', width=4)
        # Zebra
        for i in range(6):
            c.create_rectangle(STOP_X + 8 + i * 14, 82, STOP_X + 16 + i * 14, 318, fill='#3a3a3a', outline='')
        # Detection line
        pulse = 0.3 + math.sin(time.time() * 3) * 0.2
        dc = self._blend(C['cyan'], C['bg1'], 1 - pulse)
        for y in range(80, 320, 10):
            c.create_line(STOP_X, y, STOP_X, y + 5, fill=dc, width=1)
        c.create_text(STOP_X - 50, 76, text='DETECTION LINE', fill=dc, font=('Consolas', 7))
        # Traffic light
        c.create_rectangle(STOP_X + 100, 20, STOP_X + 106, 85, fill='#4a5568', outline='')
        c.create_rectangle(STOP_X + 88, 8, STOP_X + 118, 68, fill='#1a1a2e', outline='#333')
        sx = STOP_X + 103
        for i, (s, yy) in enumerate([('RED', 22), ('YELLOW', 38), ('GREEN', 54)]):
            col = SIG_COLS[s] if self.sig == s else SIG_OFF[s]
            c.create_oval(sx - 7, yy - 7, sx + 7, yy + 7, fill=col, outline='')
        # Buildings
        for i in range(8):
            bx = i * 110 + 10
            bh = 30 + int(math.sin(i * 2.3) * 20)
            c.create_rectangle(bx, 80 - bh, bx + 80, 80, fill=C['bldg'], outline='')
            for wy in range(80 - bh + 5, 76, 10):
                for wx in range(bx + 5, bx + 75, 15):
                    if random.random() > 0.3:
                        c.create_rectangle(wx, wy, wx + 8, wy + 6, fill='#332800', outline='')
        # Sidewalk
        c.create_rectangle(0, 0, CW, 80, fill=C['side'], outline='')
        c.create_rectangle(0, 320, CW, CH, fill=C['side'], outline='')
        # Vehicles
        for v in self.vehs:
            self._draw_veh(c, v)
        # Timestamp
        c.create_text(10, CH - 10, text=f'SIM | {time.strftime("%H:%M:%S")}', fill='#555', font=('Consolas', 8), anchor='w')
        if int(time.time() * 1.5) % 2 == 0:
            c.create_oval(CW - 25, CH - 19, CW - 15, CH - 9, fill=C['red'], outline='')
            c.create_text(CW - 50, CH - 14, text='SIM', fill='white', font=('Consolas', 8))

    def _draw_veh(self, c, v):
        x, y = v.x - v.w / 2, v.y
        # Shadow
        c.create_rectangle(x + 3, y + 3, x + v.w + 3, y + v.h + 3, fill='#111', outline='')
        # Body
        c.create_rectangle(x, y, x + v.w, y + v.h, fill=v.color, outline='')
        # Windshield
        if v.type == 'Car':
            c.create_rectangle(x + v.w * 0.55, y + 3, x + v.w * 0.75, y + v.h - 3, fill='#64c8ff', outline='')
        elif v.type == 'Truck':
            c.create_rectangle(x + v.w * 0.7, y + 3, x + v.w * 0.85, y + v.h - 3, fill='#64c8ff', outline='')
        elif v.type == 'Bus':
            for i in range(4):
                c.create_rectangle(x + 8 + i * 16, y + 3, x + 18 + i * 16, y + v.h - 3, fill='#64c8ff', outline='')
        # Headlight
        hl = '#ffee58' if v.x > STOP_X else '#ef5350'
        c.create_oval(x - 2, y + v.h / 2 - 2, x + 4, y + v.h / 2 + 2, fill=hl, outline='')
        # Violator box
        if v.violator and v.x > -50:
            c.create_rectangle(x - 4, y - 4, x + v.w + 4, y + v.h + 4, outline=C['red'], width=2, dash=(4, 4))
        # Detection box
        if v.dalpha > 0 and v.detected:
            bc = C['red'] if v.violator else C['cyan']
            alpha_hex = format(int(v.dalpha * 200), '02x')
            c.create_rectangle(x - 6, y - 6, x + v.w + 6, y + v.h + 6, outline=bc, width=1)
            # Corner accents
            cl = 8
            c.create_line(x - 6, y - 6 + cl, x - 6, y - 6, x - 6 + cl, y - 6, fill=bc, width=2)
            c.create_line(x + v.w + 6 - cl, y - 6, x + v.w + 6, y - 6, x + v.w + 6, y - 6 + cl, fill=bc, width=2)
            # Labels
            lbl = f"{v.type} {int(v.conf * 100)}%"
            c.create_rectangle(x - 6, y - 20, x + 6 + len(lbl) * 6, y - 6, fill=bc, outline='')
            c.create_text(x, y - 13, text=lbl, fill='white', font=('Consolas', 7), anchor='w')
            sl = f"{v.kmh} km/h"
            c.create_rectangle(x - 6, y + v.h + 8, x + 6 + len(sl) * 6, y + v.h + 20, fill=bc, outline='')
            c.create_text(x, y + v.h + 14, text=sl, fill='white', font=('Consolas', 7), anchor='w')

    def _blend(self, c1, c2, t):
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 * t + r2 * (1 - t))
        g = int(g1 * t + g2 * (1 - t))
        b = int(b1 * t + b2 * (1 - t))
        return f'#{r:02x}{g:02x}{b:02x}'

    # ---- CAMERA/VIDEO FRAME ----
    def _process_cv(self):
        if not CV2_OK or not self.cam_on or not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            if self.mode == 'video':
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return
        frame = cv2.resize(frame, (CW, CH))
        # Signal detection
        if int(time.time() * 4) % 4 == 0:
            result = self._detect_signal_hsv(frame)
            if result:
                self.sig, self.sig_conf = result
                self.sig_method = 'manual_mark' if self.manual_sig_region else 'ai_detected'
        # Convert for display
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        c = self.canvas
        c.delete('all')
        c.create_image(0, 0, anchor='nw', image=self.photo)
        # Detection line
        if hasattr(self, 'det_line_y_frac'):
            ly = int(self.det_line_y_frac * CH)
            c.create_line(0, ly, CW, ly, fill=C['cyan'], width=2, dash=(10, 6))
            c.create_text(10, ly - 8, text='DETECTION LINE', fill=C['cyan'], font=('Consolas', 8), anchor='w')
        # Signal overlay
        sig_txt = f'SIGNAL: {self.sig} ({self.sig_conf}%)'
        sc = C['red'] if self.sig == 'RED' else C['green'] if self.sig == 'GREEN' else C['amber']
        c.create_rectangle(CW - 200, 10, CW - 10, 30, fill=sc, outline='')
        c.create_text(CW - 105, 20, text=sig_txt, fill='white', font=('Consolas', 9, 'bold'))
        # Timestamp
        c.create_text(10, CH - 10, text=f'{self.mode.upper()} | {time.strftime("%H:%M:%S")}', fill='#555', font=('Consolas', 8), anchor='w')
        if int(time.time() * 1.5) % 2 == 0:
            c.create_oval(CW - 25, CH - 19, CW - 15, CH - 9, fill=C['red'], outline='')
            c.create_text(CW - 50, CH - 14, text='REC', fill='white', font=('Consolas', 8))

    # ---- CHARTS ----
    def _draw_pie(self):
        c = self.pie_canvas
        c.delete('all')
        cx, cy, r = 80, 80, 55
        data = [max(1, self.cnts[k]) for k in ['Car', 'Bike', 'Truck', 'Bus']]
        colors = [C['cyan'], C['green'], C['amber'], C['red']]
        labels = ['Car', 'Bike', 'Truck', 'Bus']
        total = sum(data)
        start = 90
        for val, col, lbl in zip(data, colors, labels):
            ext = (val / total) * 360
            if ext > 0.5:
                c.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=ext,
                             fill=col, outline=C['card'], width=2, style='pieslice')
            start += ext
        c.create_oval(cx - 28, cy - 28, cx + 28, cy + 28, fill=C['card'], outline='')
        c.create_text(cx, cy - 5, text=str(total), fill=C['txt'], font=('Consolas', 10, 'bold'))
        c.create_text(cx, cy + 8, text='total', fill=C['muted'], font=('Helvetica', 6))
        for i, (lbl, col) in enumerate(zip(labels, colors)):
            yy = 150 + i * 14
            c.create_rectangle(10, yy - 4, 18, yy + 4, fill=col, outline='')
            c.create_text(24, yy, text=f'{lbl}: {data[i]}', fill=C['txt'], font=('Helvetica', 8), anchor='w')

    def _draw_bar(self):
        c = self.bar_canvas
        c.delete('all')
        w, h = 280, 160
        ox, oy = 30, 10
        bw = max(8, (w - ox - 10) / max(1, len(self.timeline)) - 4)
        max_val = max((max(v, vl) for v, vl in self.timeline), default=1) or 1
        for i, (v, vl) in enumerate(self.timeline):
            x = ox + i * (bw + 4)
            # Vehicle bar
            vh = (v / max_val) * (h - 30)
            c.create_rectangle(x, oy + h - 20 - vh, x + bw, oy + h - 20, fill=C['cyan'], outline='')
            # Violation bar
            if vl > 0:
                vhl = (vl / max_val) * (h - 30)
                c.create_rectangle(x, oy + h - 20 - vhl, x + bw, oy + h - 20, fill=C['red'], outline='')
            # Label
            c.create_text(x + bw / 2, oy + h - 8, text=str(i + 1), fill=C['muted'], font=('Helvetica', 6))
        c.create_text(ox + w / 2, oy + h - 2, text='Time intervals', fill=C['muted'], font=('Helvetica', 7))
        # Legend
        c.create_rectangle(w - 90, 2, w - 80, 10, fill=C['cyan'], outline='')
        c.create_text(w - 75, 6, text='Vehicles', fill=C['txt'], font=('Helvetica', 7), anchor='w')
        c.create_rectangle(w - 90, 14, w - 80, 22, fill=C['red'], outline='')
        c.create_text(w - 75, 18, text='Violations', fill=C['txt'], font=('Helvetica', 7), anchor='w')

    # ---- STATS UPDATE ----
    def _update_stats(self):
        self.stat_vals['Total Vehicles'].configure(text=str(self.total_v))
        self.stat_vals['Red Light Violations'].configure(text=str(self.total_viol))
        em = max(1, (time.time() - self.t0) / 60)
        self.stat_subs['Total Vehicles'].configure(text=f'{round(self.total_v / em)}/min')
        self.stat_subs['Red Light Violations'].configure(text=f'{round(self.total_viol / em)}/min')
        # Signal
        sc = C['red'] if self.sig == 'RED' else C['amber'] if self.sig == 'YELLOW' else C['green']
        self.stat_vals['Signal Status'].configure(text=self.sig, fg=sc)
        if self.sig_method == 'simulation':
            self.stat_subs['Signal Status'].configure(text=f'Changes in {max(0, math.ceil((SIG_TIMINGS[self.sig] - (time.time() - self.sig_start) * 1000) / 1000))}s')
        elif self.sig_method == 'ai_detected':
            self.stat_subs['Signal Status'].configure(text=f'Identified from video ({self.sig_conf}%)')
        elif self.sig_method == 'manual_mark':
            self.stat_subs['Signal Status'].configure(text=f'Manually marked ({self.sig_conf}%)')
        else:
            self.stat_subs['Signal Status'].configure(text='Traffic light not found')
        # Confidence
        det = [v for v in self.vehs if v.detected]
        if det:
            self.avg_conf = sum(v.conf for v in det) / len(det)
        cp = f'{self.avg_conf * 100:.1f}%'
        self.stat_vals['Detection Confidence'].configure(text=cp)
        # Signal panel
        self.sig_light_cv.delete('all')
        col = SIG_COLS.get(self.sig, C['green'])
        self.sig_light_cv.create_oval(5, 5, 55, 55, fill=col, outline=C['border'], width=2)
        self.sig_big_lbl.configure(text=self.sig, fg=sc)
        methods = {'simulation': 'Auto Cycle (Simulation)', 'ai_detected': 'AI Color Detection (Video)',
                   'manual_mark': 'Manual Mark (User)', 'not_found': 'Traffic Light Not Found'}
        self.sig_method_lbl.configure(text=methods.get(self.sig_method, '--'))
        self.tl_found_lbl.configure(text=f'Traffic Light Found: {"Yes" if self.sig_method in ("ai_detected", "manual_mark") else "No" if self.sig_method == "not_found" else "N/A"}')
        self.tl_conf_lbl.configure(text=f'Color Confidence: {self.sig_conf}%' if self.sig_method != 'simulation' else 'Color Confidence: N/A')
        self.tl_meth_lbl.configure(text=f'Detection Method: {"COCO-SSD + Pixel" if self.sig_method == "ai_detected" else "Manual Mark" if self.sig_method == "manual_mark" else "Simulation" if self.sig_method == "simulation" else "--"}')
        # Categories
        for t in ['Car', 'Bike', 'Truck', 'Bus']:
            self.cat_lbls[t].configure(text=str(self.cnts[t]))
        # Speed
        if self.speeds:
            avg = round(sum(self.speeds) / len(self.speeds))
            mx, mn = max(self.speeds), min(self.speeds)
            for lbl, val in [('Avg Speed', avg), ('Max Speed', mx), ('Min Speed', mn)]:
                vl, bar = self.spd_bars[lbl]
                vl.configure(text=f'{val} km/h')
                bar.delete('bar')
                bar.create_rectangle(0, 0, int(val / 80 * 100), 4, fill=vl.cget('fg'), outline='', tags='bar')
        # Time
        now = time.time()
        self.time_lbl.configure(text=time.strftime('%H:%M:%S'))
        self.date_lbl.configure(text=time.strftime('%a %d %b'))
        # Log count
        self.log_count_lbl.configure(text=f'{len(self.vlog)} entries')

    def _add_violation(self, vtype, speed, conf):
        t = time.strftime('%H:%M:%S')
        self.vlog.insert(0, (t, vtype, speed, f'{conf * 100:.0f}'))
        if len(self.vlog) > 50:
            self.vlog.pop()
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        for i, (t, vt, sp, cf) in enumerate(self.vlog):
            prefix = '🔴 ' if i == 0 else '   '
            self.log_text.insert('end', f'{prefix}{vt} | {sp} km/h | {t} | Conf: {cf}%\n', 'red' if i == 0 else 'muted')
        self.log_text.configure(state='disabled')

    # ---- RESET ----
    def _reset(self):
        self.total_v = 0
        self.total_viol = 0
        self.speeds = []
        self.vlog = []
        self.cnts = {'Car': 0, 'Bike': 0, 'Truck': 0, 'Bus': 0}
        self.t0 = time.time()
        self.vehs = []
        self.timeline.clear()
        self.tl_v = 0
        self.tl_vl = 0
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.insert('end', '  Violations will appear here...\n', 'muted')
        self.log_text.configure(state='disabled')

    # ---- MAIN LOOP ----
    def _loop(self):
        if not self.running:
            return
        now = time.time()
        dt = now - self.last_ft
        self.last_ft = now
        if self.mode == 'simulation':
            self.fps_q.append(1 / max(dt, 0.001))
            if hasattr(self, 'fps_lbl'):
                self.fps_lbl.configure(text=f'{round(sum(self.fps_q) / len(self.fps_q))} FPS')
            self._update_sim_signal()
            # Spawn
            if now - self.last_spawn > 0.8 + random.random() * 0.6 and len(self.vehs) < 8:
                self.vehs.append(Vehicle(self.sig))
                self.last_spawn = now
            # Update vehicles
            for v in self.vehs:
                v.update(self.sig)
                if v.counted and not getattr(v, '_cnt_done', False):
                    v._cnt_done = True
                    self.total_v += 1
                    self.cnts[v.type] += 1
                    self.speeds.append(v.kmh)
                if v.violator and not getattr(v, '_viol_done', False):
                    v._viol_done = True
                    self.total_viol += 1
                    self._add_violation(v.type, v.kmh, v.conf)
            self.vehs = [v for v in self.vehs if not v.off()]
            self._draw_sim()
        elif self.mode in ('camera', 'video'):
            self._process_cv()

        self._update_stats()
        self.root.after(33, self._loop)

    # Timeline chart update every 5s
    def _timeline_tick(self):
        if not self.running:
            return
        nv = self.total_v - self.tl_v
        nvl = self.total_viol - self.tl_vl
        self.tl_v = self.total_v
        self.tl_vl = self.total_viol
        self.timeline.append((nv, nvl))
        self._draw_pie()
        self._draw_bar()
        self.root.after(5000, self._timeline_tick)

    def _on_close(self):
        self.running = False
        self._stop_cam()
        self.root.destroy()


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == '__main__':
    root = tk.Tk()
    app = TrafficEyeApp(root)
    app._draw_pie()
    app._draw_bar()
    root.after(5000, app._timeline_tick)
    print("=" * 50)
    print("  Traffic Eye — AI Signal Detection System")
    print("  Made by Nitin Kumar")
    print("=" * 50)
    print("\n  App running. Close window to exit.\n")
    print("=" * 50)
    root.mainloop()
