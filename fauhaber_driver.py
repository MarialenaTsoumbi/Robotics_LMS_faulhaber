import canopen
import time 
import tkinter as tk
import threading

BLACK = "#000000"
HOT_PINK = "#FF69B4"
DEEP_PINK = "#FF1493"
DARK_PINK = "#C71585"
DARK_GREY = "#2a2a2a"
FONT = ("Times New Roman", 16)
FONT_BOLD = ("Times New Roman", 18, "bold")

root = tk.Tk()
root.title("Motion Control")
root.geometry("640x520")
root.configure(bg=BLACK)

label = tk.Label(
    root,
    text="Faulhaber Motor Controller",
    bg=HOT_PINK,
    fg=DARK_GREY,
    font=("Times New Roman", 18, "bold", ),
)
label.pack(pady=40)


    



###################################### FIRST GRAPHICS #########################################################################################

#Setting up CAN connection & data receiving from the eds file
network= canopen.Network()
network.connect(interface= "pcan", channel= "PCAN_USBBUS1", bitrate= 250000)
node = network.add_node(3, r'C:\Users\maria\Documents\VS code projects\robotics\605.3150.69-C.eds')

def wait_status(mask, value, timeout=2.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if node.sdo[0x6041].raw & mask == value:
            return
        time.sleep(0.01)
    raise TimeoutError(f"Statusword = 0x{node.sdo[0x6041].raw:04X}")

def enable_drive():
    if node.sdo[0x6041].raw & 0x008F == 0x0008:            # fault -> reset
        node.sdo[0x6040].raw = 0x0080                      # Controlword
        time.sleep(0.1)
    node.sdo[0x6040].raw = 0x0006                          # Shutdown
    wait_status(0x006F, 0x0021)                            # Ready to switch on
    node.sdo[0x6040].raw = 0x0007                          # Switch on
    wait_status(0x006F, 0x0023)                            # Switched on
    node.sdo[0x6040].raw = 0x000F                          # Enable operation
    wait_status(0x006F, 0x0027)           

#enable_drive()

def start_func():

    node.nmt.state= 'OPERATIONAL'
    node.sdo['Controlword'].raw= 0x0006

    node.sdo['Controlword'].raw= 0x0007

    node.sdo['Controlword'].raw= 0x000F

    fw_version = node.sdo[0x100A].raw
    print(f"Current Firmware: {fw_version}")

    #initialize profile velocity mode
    node.sdo[0x6060].raw= 3

    I_current = node.sdo['Current Actual Value'].raw
    posi= node.sdo['Position Actual Value'].raw
    print(f"Inital Current value: {I_current}")
    j=0

    while I_current<200 and j==0:
        node.sdo['Target Velocity'].raw= -10
        I_current = node.sdo['Current Actual Value'].raw


    if I_current>=200:
        j=1
        posi= node.sdo['Position Actual Value'].raw
        print(f"pos: {posi}")
        node.sdo['Target Velocity'].raw= 0
        node.sdo['Controlword'].raw= 0x001F
        time.sleep(0.1)
        node.sdo[0x6060].raw= 1  #initialize profile position mode
        node.sdo[0x607A].raw= 1000 #new position
        node.sdo['Controlword'].raw= 0x000F
        node.sdo['Controlword'].raw= 0x007F
        print("stOOpped")
        posi= node.sdo['Position Actual Value'].raw
        print(f"pos: {posi}")
        
        
       
    time.sleep(0.1)

    vel= node.sdo['Velocity Actual Value'].raw
    print(f"Velocity: {vel}")   

    I_current = node.sdo['Current Actual Value'].raw
    print(f"Current value: {I_current}")


    i=0
    while i<20:
        I_current = node.sdo['Current Actual Value'].raw
        print(f"Current: {I_current}")
        time.sleep(0.5)
        i+=1
        if I_current ==0 :
            print("Zero Current")
            i=20


#homing
    node.sdo[0x6060].raw= 6  #initailize homing mode
    node.sdo[0x6098].raw= 35   #homing method 35
#end homing procedure
    node.sdo['Controlword'].raw= 0x000F
    node.sdo['Controlword'].raw= 0x001F
#New position
    posi= node.sdo['Position Actual Value'].raw
    print( f"pos: {posi}")


def endfunc():
    time.sleep(1)
    node.sdo['Controlword'].raw= 0x0006
    
    

button_st = tk.Button(
    root,
    text="Start Motor",
    bg=DEEP_PINK,
    fg="white",
    activebackground="#C71585",
    activeforeground="white",
    font=(FONT_BOLD, 10),
    relief="groove",
    padx=10,
    pady=4,
)
button_st.pack()
button_st.bind("<ButtonRelease-1>", lambda e: start_func())

button_stop = tk.Button(
    root,
    text="Stop Motor",
    bg=DEEP_PINK,
    fg="white",
    activebackground="#7F1257",
    activeforeground="white",
    font=(FONT_BOLD, 10),
    relief="groove",
    padx=10,
    pady=4,
)
button_stop.pack()
button_stop.bind("<ButtonRelease-1>", lambda e: endfunc())





# Last values the user confirmed with the buttons
confirmed_pos  = {"Target Position": None}
confirmed_vel  ={"Target Velocity": None}

global pos_value



motor_lock = threading.Lock()   

def move_to(position, relative=False, timeout=30.0):
    node.sdo[0x607A].raw = int(position)                   # Target position
    base = 0x4F if relative else 0x0F                      # bit 6 = relative
    node.sdo[0x6040].raw = base | 0x10                     # bit 4 = new set-point
    node.sdo[0x6040].raw = base                            # clear bit 4
    t0 = time.time()
    while not (node.sdo[0x6041].raw & 0x0400):             # bit 10 = target reached
        if time.time() - t0 > timeout:
            raise TimeoutError("target not reached")
        time.sleep(0.02)

    




def on_confirm_pos(name, value):
    """Called when a Confirm button is pressed. Put your own code here."""
    confirmed_pos[name] = value
    print(f"{name} confirmed: {value}")
    threading.Thread(target=pos_value, args=(value,), daemon=True).start()

def on_confirm_vel(name, value):
    """Called when a Confirm button is pressed. Put your own code here."""
    confirmed_vel[name] = value
    print(f"{name} confirmed: {value}")


def make_slider(parent, title, min_value, max_value, initial=0):
    """Titled integer slider with a synced number box and a Confirm button."""
    frame = tk.Frame(parent, bg=BLACK)
    frame.pack(fill="x", padx=30, pady=15)

    tk.Label(frame, text=title, bg=BLACK, fg=HOT_PINK, font=FONT_BOLD).pack(anchor="w")

    row = tk.Frame(frame, bg=BLACK)
    row.pack(fill="x")

    entry_text = tk.StringVar(value=str(initial))

    def on_slider(value):
        # Slider moved: update the number box
        entry_text.set(str(int(float(value))))

    slider = tk.Scale(
        row,
        from_=min_value,
        to=max_value,
        orient="horizontal",
        resolution=1,            # integers only
        showvalue=False,         # the number box shows the value instead
        command=on_slider,
        bg=BLACK,
        fg=HOT_PINK,
        troughcolor=DARK_GREY,
        activebackground=DEEP_PINK,
        highlightthickness=0,
        bd=0,
        font=FONT,
    )
    slider.pack(side="left", fill="x", expand=True)

    entry = tk.Entry(
        row,
        textvariable=entry_text,
        width=7,
        justify="right",
        bg=DARK_GREY,
        fg=HOT_PINK,
        insertbackground=HOT_PINK,          # text cursor colour
        selectbackground=DEEP_PINK,
        selectforeground="white",
        highlightthickness=1,
        highlightbackground=HOT_PINK,
        highlightcolor=DEEP_PINK,
        relief="flat",
        font=FONT,
    )
    entry.pack(side="left", padx=(15, 0))

    def apply_entry(_event=None):
        # Number box edited: clamp to the allowed range and move the slider
        try:
            pos_value = int(float(entry_text.get()))
        except ValueError:
            pos_value = slider.get()             # not a number: revert
        pos_value = max(min_value, min(max_value, pos_value))
        slider.set(pos_value)
        entry_text.set(str(pos_value))
        return pos_value

    entry.bind("<Return>", apply_entry)
    entry.bind("<KP_Enter>", apply_entry)
    entry.bind("<FocusOut>", apply_entry)

    # Status line showing the last confirmed value
    status = tk.Label(frame, text="Not confirmed yet", bg=BLACK, fg=DARK_PINK,
                      font=("Times New Roman", 13, "italic"))

    def confirmpos(_event=None):
        value = apply_entry()                # make sure typed text is applied
        on_confirm_pos(title, value)
        status.config(text=f"Confirmed: {value}", fg=HOT_PINK)

    def confirmvel(_event=None):
            value = apply_entry()                # make sure typed text is applied
            on_confirm_vel(title, value)
            status.config(text=f"Confirmed: {value}", fg=HOT_PINK)

    # A Label styled as a button, because native buttons ignore colours on macOS
    button = tk.Label(
        frame,
        text="Confirm",
        bg=DEEP_PINK,
        fg="white",
        font=("Times New Roman", 15, "bold"),
        padx=24,
        pady=6,
        cursor="hand2",
    )
    button.pack(pady=(10, 4))
    button.bind("<Button-1>", lambda e: button.config(bg=DARK_PINK))
    button.bind("<ButtonRelease-1>", lambda e: (button.config(bg=DEEP_PINK), confirmpos()))
    button.bind("<ButtonRelease-1>", lambda e: (button.config(bg=DEEP_PINK), on_confirm_pos()))
    button.bind("<ButtonRelease-1>", lambda e: (button.config(bg=DEEP_PINK), move_to(pos_value)))
    button.bind("<ButtonRelease-1>", lambda e: (button.config(bg=DEEP_PINK), confirmvel()))
    button.bind("<Enter>", lambda e: button.config(bg="#FF3EA5"))
    button.bind("<Leave>", lambda e: button.config(bg=DEEP_PINK))
    status.pack()

    # Pressing Enter in the number box also confirms
    entry.bind("<Return>", confirmpos)
    entry.bind("<KP_Enter>", confirmpos)
    entry.bind("<Return>", confirmvel)
    entry.bind("<KP_Enter>", confirmvel)

    slider.set(initial)
    return slider.get


get_position = make_slider(root, "Target Position", 0, 20000)
get_velocity = make_slider(root, "Target Velocity", -2000, 2000)




root.mainloop()




