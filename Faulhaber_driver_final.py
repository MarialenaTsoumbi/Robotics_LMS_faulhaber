import threading
import time
import tkinter as tk
import canopen



MIN_POS, MAX_POS = 0, 100000     # set to your travel range in user units
MIN_VEL, MAX_VEL = 1, 5000       # set to your allowed velocity range

BLACK = "#000000"
HOT_PINK = "#FF69B4"
DEEP_PINK = "#FF1493"
DARK_PINK = "#C71585"
DARK_GREY = "#2a2a2a"
FONT = ("Times New Roman", 16)
FONT_BOLD = ("Times New Roman", 18, "bold")

network= canopen.Network()
network.connect(interface= "pcan", channel= "PCAN_USBBUS1", bitrate= 250000)
node = network.add_node(3, r'C:\Users\maria\Documents\VS code projects\robotics\605.3150.69-C.eds')


def start_func():

    node.nmt.state = 'OPERATIONAL'
    node.sdo['Controlword'].raw = 0x0006

    node.sdo['Controlword'].raw = 0x0007

    node.sdo['Controlword'].raw = 0x000F

    fw_version = node.sdo[0x100A].raw
    print(f"Current Firmware: {fw_version}")

    # initialize profile velocity mode
    node.sdo[0x6060].raw = 3

    I_current = node.sdo['Current Actual Value'].raw
    posi = node.sdo['Position Actual Value'].raw
    print(f"Inital Current value: {I_current}")
    j = 0

    while I_current < 200 and j == 0:
        node.sdo['Target Velocity'].raw = -10
        I_current = node.sdo['Current Actual Value'].raw

    if I_current >= 200:
        j = 1
        posi = node.sdo['Position Actual Value'].raw
        print(f"pos: {posi}")
        node.sdo['Target Velocity'].raw = 0
        node.sdo['Controlword'].raw = 0x001F
        time.sleep(0.1)
        node.sdo[0x6060].raw = 1  # initialize profile position mode
        node.sdo[0x607A].raw = 1000  # new position
        node.sdo['Controlword'].raw = 0x000F
        node.sdo['Controlword'].raw = 0x007F
        print("stOOpped")
        posi = node.sdo['Position Actual Value'].raw
        print(f"pos: {posi}")

    time.sleep(0.1)

    vel = node.sdo['Velocity Actual Value'].raw
    print(f"Velocity: {vel}")

    I_current = node.sdo['Current Actual Value'].raw
    print(f"Current value: {I_current}")

    if I_current == 0:
        print("Zero Current")

    # homing
    node.sdo[0x6060].raw = 6  # initailize homing mode
    node.sdo[0x6098].raw = 35  # homing method 35
    # end homing procedure
    node.sdo['Controlword'].raw = 0x000F
    node.sdo['Controlword'].raw = 0x001F
    # New position
    posi = node.sdo['Position Actual Value'].raw
    print(f"pos: {posi}")


def endfunc():
    time.sleep(1)
    node.sdo['Controlword'].raw = 0x0006


def prepare_profile_position():
    # runs after start_func: homing left the drive in mode 6
    node.sdo[0x6060].raw = 1          # Modes of operation: Profile Position
    node.sdo[0x6083].raw = 5000       # Profile acceleration
    node.sdo[0x6084].raw = 5000       # Profile deceleration
    node.sdo[0x6040].raw = 0x000F     # clear homing start bit, keep operation enabled


class App:
    def __init__(self, root):
        self.root = root
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.busy = False             # True while start/end runs in its thread
        self.worker_done = None       # callback to run when the thread ends
        self.worker_error = None

        self.pos_var = tk.StringVar(value=f"Position: {MIN_POS}")
        self.vel_var = tk.StringVar(value=f"Velocity: {MIN_VEL}")
        self.actual_var = tk.StringVar(value="Actual position: -")
        self.status_var = tk.StringVar(value="Press Start")

        # Start / End buttons, directly below the title
        row = tk.Frame(root, bg=BLACK)
        row.pack(pady=(0, 10))
        self.start_btn = self.make_button(row, "Start", self.on_start)
        self.start_btn.pack(side="left", padx=10)
        self.end_btn = self.make_button(row, "End", self.on_end)
        self.end_btn.pack(side="left", padx=10)
        self.end_btn.config(state="disabled")

        self.pos_slider = self.make_slider(self.pos_var, MIN_POS, MAX_POS,
                                           self.on_pos_move)
        self.vel_slider = self.make_slider(self.vel_var, MIN_VEL, MAX_VEL,
                                           self.on_vel_move)

        self.confirm_btn = self.make_button(root, "Confirm", self.confirm)
        self.confirm_btn.pack(pady=15)
        self.confirm_btn.config(state="disabled")      # enabled after Start

        self.make_label(self.actual_var).pack()
        self.make_label(self.status_var).pack(pady=(0, 10))

        self.ack_tries = 0
        self.refresh()

    # ---------- widgets ----------
    def make_label(self, var):
        return tk.Label(self.root, textvariable=var, bg=BLACK, fg=HOT_PINK,
                        font=FONT)

    def make_button(self, parent, text, command):
        return tk.Button(
            parent, text=text, command=command,
            bg=HOT_PINK, fg=DARK_GREY,
            activebackground=DEEP_PINK, activeforeground=BLACK,
            disabledforeground=DARK_PINK, relief="flat", bd=0,
            font=FONT_BOLD, padx=30, pady=8)

    def make_slider(self, var, lo, hi, command):
        self.make_label(var).pack(padx=10, pady=(12, 0))
        slider = tk.Scale(
            self.root, from_=lo, to=hi, orient="horizontal", length=500,
            showvalue=False, command=command,
            bg=BLACK, fg=HOT_PINK, troughcolor=DARK_PINK,
            activebackground=DEEP_PINK, highlightthickness=0, bd=0,
            sliderrelief="flat")
        slider.pack(padx=10, pady=5)
        return slider

    def on_pos_move(self, value):
        self.pos_var.set(f"Position: {int(float(value))}")     # label only

    def on_vel_move(self, value):
        self.vel_var.set(f"Velocity: {int(float(value))}")     # label only

    # ---------- start / end (run in a thread so the window stays alive) ----------
    def run_in_thread(self, func, done_callback, status_text):
        self.busy = True
        self.worker_done = done_callback
        self.worker_error = None
        self.start_btn.config(state="disabled")
        self.end_btn.config(state="disabled")
        self.confirm_btn.config(state="disabled")
        self.status_var.set(status_text)

        def worker():
            try:
                func()
            except Exception as e:                  # report errors in the GUI
                self.worker_error = e
            finally:
                self.busy = False

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, self.poll_worker)

    def poll_worker(self):
        if self.busy:
            self.root.after(100, self.poll_worker)
            return
        if self.worker_error is not None:
            self.status_var.set(f"Error: {self.worker_error}")
            self.start_btn.config(state="normal")
            self.end_btn.config(state="normal")
        else:
            self.worker_done()

    def on_start(self):
        def sequence():
            start_func()
            prepare_profile_position()
        self.run_in_thread(sequence, self.after_start, "Starting / homing...")

    def after_start(self):
        self.status_var.set("Ready")
        self.confirm_btn.config(state="normal")
        self.end_btn.config(state="normal")

    def on_end(self):
        self.run_in_thread(endfunc, self.after_end, "Shutting down...")

    def after_end(self):
        self.status_var.set("Drive disabled")
        self.start_btn.config(state="normal")

    # ---------- move ----------
    def confirm(self):
        pos = int(self.pos_slider.get())
        vel = int(self.vel_slider.get())
        node.sdo[0x6081].raw = vel                         # Profile velocity
        node.sdo[0x607A].raw = pos                         # Target position
        node.sdo[0x6040].raw = 0x001F                      # bit 4 = new set-point (rising edge)
        self.confirm_btn.config(state="disabled")          # block a second press during handshake
        self.ack_tries = 0
        self.root.after(20, self.finish_handshake)

    def finish_handshake(self):
        # wait for set-point acknowledge (statusword bit 12), then clear bit 4
        if node.sdo[0x6041].raw & 0x1000:
            node.sdo[0x6040].raw = 0x000F
            self.confirm_btn.config(state="normal")
        elif self.ack_tries < 50:
            self.ack_tries += 1
            self.root.after(20, self.finish_handshake)
        else:
            node.sdo[0x6040].raw = 0x000F
            self.confirm_btn.config(state="normal")
            self.status_var.set("No set-point acknowledge from drive")

    def refresh(self):
        if not self.busy:                  # don't compete with start/end for the SDO channel
            try:
                sw = node.sdo[0x6041].raw
                self.actual_var.set(f"Actual position: {node.sdo[0x6064].raw}")
                if sw & 0x0008:
                    self.status_var.set("FAULT")
                elif sw & 0x0400:
                    self.status_var.set("Target reached")
                else:
                    self.status_var.set("Moving")
            except canopen.SdoError as e:
                self.status_var.set(f"SDO error: {e}")
        self.root.after(100, self.refresh)

    def on_close(self):
        try:
            node.sdo[0x6040].raw = 0x0006                  # disable operation
        finally:
            network.disconnect()
            self.root.destroy()


node.nmt.state = "PRE-OPERATIONAL"

root = tk.Tk()
root.title("Motion Control")
root.geometry("640x700")
root.configure(bg=BLACK)

label = tk.Label(
    root,
    text="Faulhaber Motor Controller",
    bg=HOT_PINK,
    fg=DARK_GREY,
    font=FONT_BOLD,
)
label.pack(pady=20)

App(root)
root.mainloop()