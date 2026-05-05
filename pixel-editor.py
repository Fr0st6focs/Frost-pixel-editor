import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter.colorchooser import askcolor
from PIL import Image, ImageColor
import copy

GRID_W = 64
GRID_H = 64
pixels = []
undo_stack = []
redo_stack = []
zoom = 1.0
pan_x = 0
pan_y = 0

selected_palette_index = 0
palette_buttons = []

# Brush + symmetry
brush_size = 1
mirror_mode = False

# Preview globals
preview_window = None
preview_canvas = None
preview_zoom = 4  # default zoom
PREVIEW_BG = "#C8C8C8"  # your chosen light gray

COLORS = [
    "#000000", "#FFFFFF", "#FF0000", "#00FF00",
    "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
    "#804000", "#00A000", "#A000A0", "#0080FF",
    "#FF8080", "#80FF80", "#8080FF", "#C0C0C0"
]

current_color = COLORS[0]
tool = "pen"

root = tk.Tk()
root.title("Frost Pixel Editor v1.0")
root.configure(bg="#2b2b2b")

root.bind("<Control-o>", lambda e: open_file())
root.bind("<Control-n>", lambda e: new_file())
root.bind("<Control-s>", lambda e: save_file())

root.bind("<Left>", lambda e: move_view(-40, 0))
root.bind("<Right>", lambda e: move_view(40, 0))
root.bind("<Up>", lambda e: move_view(0, -40))
root.bind("<Down>", lambda e: move_view(0, 40))

root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

def push_undo():
    undo_stack.append(copy.deepcopy(pixels))
    redo_stack.clear()

def undo():
    if undo_stack:
        redo_stack.append(copy.deepcopy(pixels))
        pixels[:] = undo_stack.pop()
        redraw()
        update_preview()

def redo():
    if redo_stack:
        undo_stack.append(copy.deepcopy(pixels))
        pixels[:] = redo_stack.pop()
        redraw()
        update_preview()

menu = tk.Menu(root)
root.config(menu=menu)

file_menu = tk.Menu(menu, tearoff=0)
file_menu.add_command(label="New", command=lambda: new_file())
file_menu.add_command(label="Open", command=lambda: open_file())
file_menu.add_command(label="Save As", command=lambda: save_file())
menu.add_cascade(label="File", menu=file_menu)

menu.add_command(label="Undo", command=undo)
menu.add_command(label="Redo", command=redo)
menu.add_command(label="Preview", command=lambda: open_preview())

def new_file():
    global GRID_W, GRID_H, pixels, pan_x, pan_y

    win = tk.Toplevel(root)
    win.title("New File")
    win.geometry("200x120")
    win.configure(bg="#2b2b2b")

    tk.Label(win, text="Choose grid size:", fg="white", bg="#2b2b2b").pack(pady=10)

    def choose(size):
        nonlocal win
        global GRID_W, GRID_H, pixels, pan_x, pan_y

        if size == "64":
            GRID_W, GRID_H = 64, 64
        else:
            GRID_W, GRID_H = 32, 64

        pixels = [[None for _ in range(GRID_W)] for _ in range(GRID_H)]
        pan_x = 0
        pan_y = 0

        undo_stack.clear()
        redo_stack.clear()
        win.destroy()
        redraw()
        update_preview()

    tk.Button(win, text="64 x 64", width=12, command=lambda: choose("64")).pack(pady=5)
    tk.Button(win, text="32 x 64", width=12, command=lambda: choose("32")).pack(pady=5)

def open_file():
    global GRID_W, GRID_H, pixels, pan_x, pan_y

    path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png")])
    if not path:
        return

    img = Image.open(path).convert("RGB")
    w, h = img.size

    if (w, h) not in [(64, 64), (32, 64)]:
        messagebox.showerror("Error", "Only 64x64 or 32x64 PNG allowed")
        return

    GRID_W, GRID_H = w, h
    pixels = [[None for _ in range(GRID_W)] for _ in range(GRID_H)]

    for y in range(GRID_H):
        for x in range(GRID_W):
            r, g, b = img.getpixel((x, y))
            pixels[y][x] = f"#{r:02x}{g:02x}{b:02x}"

    pan_x = 0
    pan_y = 0

    undo_stack.clear()
    redo_stack.clear()
    redraw()
    update_preview()

def save_file():
    path = filedialog.asksaveasfilename(
        title="Save PNG",
        defaultextension=".png",
        filetypes=[("PNG Files", "*.png")]
    )

    if not path:
        return

    if not path.lower().endswith(".png"):
        path += ".png"

    img = Image.new("RGB", (GRID_W, GRID_H))

    for y in range(GRID_H):
        for x in range(GRID_W):
            col = pixels[y][x] if pixels[y][x] else "#000000"
            img.putpixel((x, y), ImageColor.getrgb(col))

    img.save(path, "PNG")

def change_zoom(amount):
    global zoom
    zoom *= amount
    zoom = max(0.2, min(zoom, 8))
    redraw()

def move_view(dx, dy):
    global pan_x, pan_y
    pan_x += dx
    pan_y += dy
    redraw()

def highlight_palette():
    for i, btn in enumerate(palette_buttons):
        if i == selected_palette_index:
            btn.config(highlightthickness=3, highlightbackground="white")
        else:
            btn.config(highlightthickness=1, highlightbackground="#1e1e1e")

def choose_color(c, index=None):
    global current_color, selected_palette_index
    current_color = c
    if index is not None:
        selected_palette_index = index
    highlight_palette()

def replace_color_in_art(old_color, new_color):
    for y in range(GRID_H):
        for x in range(GRID_W):
            if pixels[y][x] == old_color:
                pixels[y][x] = new_color

def pick_custom_color():
    global current_color, COLORS, selected_palette_index

    color = askcolor(title="Choose a color")
    if color[1] is None:
        return

    new_color = color[1]
    old_color = COLORS[selected_palette_index]

    COLORS[selected_palette_index] = new_color
    current_color = new_color

    replace_color_in_art(old_color, new_color)

    refresh_palette()
    redraw()
    update_preview()

def refresh_palette():
    global palette_buttons
    palette_buttons = []

    for widget in palette_frame.winfo_children():
        widget.destroy()

    for i, c in enumerate(COLORS):
        r = i // 4
        col = i % 4

        btn = tk.Button(
            palette_frame, bg=c, width=2, height=1,
            highlightthickness=1,
            highlightbackground="#1e1e1e",
            command=lambda col=c, idx=i: choose_color(col, idx)
        )
        btn.grid(row=r, column=col, padx=1, pady=1)
        palette_buttons.append(btn)

    highlight_palette()

toolbar = tk.Frame(root, bg="#1e1e1e", width=80)
toolbar.grid(row=0, column=0, sticky="ns")
toolbar.grid_propagate(False)

tk.Label(toolbar, text="Tools", fg="white", bg="#1e1e1e").pack(pady=5)

def set_tool(name):
    global tool
    tool = name

tk.Button(toolbar, text="✎", fg="white", bg="#3a3a3a",
          width=4, command=lambda: set_tool("pen")).pack(pady=2)
tk.Button(toolbar, text="⌫", fg="white", bg="#3a3a3a",
          width=4, command=lambda: set_tool("eraser")).pack(pady=2)
tk.Button(toolbar, text="🪣", fg="white", bg="#3a3a3a",
          width=4, command=lambda: set_tool("bucket")).pack(pady=2)

tk.Button(toolbar, text="＋", fg="white", bg="#3a3a3a",
          width=4, command=lambda: change_zoom(1.25)).pack(pady=2)
tk.Button(toolbar, text="－", fg="white", bg="#3a3a3a",
          width=4, command=lambda: change_zoom(0.8)).pack(pady=2)

tk.Button(toolbar, text="🎨", fg="white", bg="#3a3a3a",
          width=4, command=pick_custom_color).pack(pady=2)

# Brush size controls
def set_brush_size(size):
    global brush_size
    brush_size = size

tk.Label(toolbar, text="Brush Size", fg="white", bg="#1e1e1e").pack(pady=10)

tk.Button(toolbar, text="1×", fg="white", bg="#3a3a3a",
          width=4, command=lambda: set_brush_size(1)).pack(pady=2)
tk.Button(toolbar, text="2×", fg="white", bg="#3a3a3a",
          width=4, command=lambda: set_brush_size(2)).pack(pady=2)
tk.Button(toolbar, text="4×", fg="white", bg="#3a3a3a",
          width=4, command=lambda: set_brush_size(4)).pack(pady=2)
tk.Button(toolbar, text="8×", fg="white", bg="#3a3a3a",
          width=4, command=lambda: set_brush_size(8)).pack(pady=2)

# Symmetry toggle
def toggle_mirror():
    global mirror_mode
    mirror_mode = not mirror_mode
    mirror_button.config(text=f"Symmetry: {'ON' if mirror_mode else 'OFF'}")

mirror_button = tk.Button(
    toolbar, text="Symmetry: OFF",
    fg="white", bg="#3a3a3a", width=12,
    command=toggle_mirror
)
mirror_button.pack(pady=10)

tk.Label(toolbar, text="Colors", fg="white", bg="#1e1e1e").pack(pady=10)

palette_frame = tk.Frame(toolbar, bg="#1e1e1e")
palette_frame.pack()

refresh_palette()

canvas = tk.Canvas(root, bg="black", highlightthickness=0)
canvas.grid(row=0, column=1, sticky="nsew")

pixels = [[None for _ in range(GRID_W)] for _ in range(GRID_H)]

def redraw():
    canvas.delete("all")

    w = canvas.winfo_width()
    h = canvas.winfo_height()

    pixel_size = int(min(w // GRID_W, h // GRID_H) * zoom)
    pixel_size = max(pixel_size, 1)

    for x in range(GRID_W + 1):
        canvas.create_line(
            x * pixel_size + pan_x, pan_y,
            x * pixel_size + pan_x, GRID_H * pixel_size + pan_y,
            fill="#303030"
        )

    for y in range(GRID_H + 1):
        canvas.create_line(
            pan_x, y * pixel_size + pan_y,
            GRID_W * pixel_size + pan_x, y * pixel_size + pan_y,
            fill="#303030"
        )

    for y in range(GRID_H):
        for x in range(GRID_W):
            color = pixels[y][x]
            if color:
                canvas.create_rectangle(
                    x * pixel_size + 1 + pan_x, y * pixel_size + 1 + pan_y,
                    (x + 1) * pixel_size - 1 + pan_x, (y + 1) * pixel_size - 1 + pan_y,
                    fill=color, outline=color
                )

def bucket_fill(x, y, target_color, replacement):
    if target_color == replacement:
        return
    if pixels[y][x] != target_color:
        return

    stack = [(x, y)]

    while stack:
        cx, cy = stack.pop()

        if pixels[cy][cx] != target_color:
            continue

        pixels[cy][cx] = replacement

        if cx > 0: stack.append((cx - 1, cy))
        if cx < GRID_W - 1: stack.append((cx + 1, cy))
        if cy > 0: stack.append((cx, cy - 1))
        if cy < GRID_H - 1: stack.append((cx, cy + 1))

def paint(event):
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    pixel_size = int(min(w // GRID_W, h // GRID_H) * zoom)

    gx = (event.x - pan_x) // pixel_size
    gy = (event.y - pan_y) // pixel_size

    if not (0 <= gx < GRID_W and 0 <= gy < GRID_H):
        return

    push_undo()

    if tool == "pen":
        for dy in range(brush_size):
            for dx in range(brush_size):
                px = gx + dx
                py = gy + dy

                # Normal draw
                if 0 <= px < GRID_W and 0 <= py < GRID_H:
                    pixels[py][px] = current_color

                # Mirror draw
                if mirror_mode:
                    mx = (GRID_W - 1) - px
                    if 0 <= mx < GRID_W and 0 <= py < GRID_H:
                        pixels[py][mx] = current_color

    elif tool == "eraser":
        pixels[gy][gx] = None

    elif tool == "bucket":
        bucket_fill(gx, gy, pixels[gy][gx], current_color)

    redraw()
    update_preview()

canvas.bind("<Button-1>", paint)
canvas.bind("<B1-Motion>", lambda e: paint(e) if tool != "bucket" else None)
canvas.bind("<Configure>", lambda e: redraw())

# -------------------------
# PREVIEW WINDOW FUNCTIONS
# -------------------------

def open_preview():
    global preview_window, preview_canvas

    if preview_window and tk.Toplevel.winfo_exists(preview_window):
        preview_window.lift()
        return

    preview_window = tk.Toplevel(root)
    preview_window.title("Preview")
    preview_window.geometry("256x256")
    preview_window.resizable(False, False)
    preview_window.configure(bg=PREVIEW_BG)

    # Zoom buttons
    btn_frame = tk.Frame(preview_window, bg=PREVIEW_BG)
    btn_frame.pack(pady=5)

    tk.Button(btn_frame, text="1×", command=lambda: set_preview_zoom(1)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="2×", command=lambda: set_preview_zoom(2)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="4×", command=lambda: set_preview_zoom(4)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="8×", command=lambda: set_preview_zoom(8)).pack(side="left", padx=5)

    preview_canvas = tk.Canvas(preview_window, width=256, height=256, bg=PREVIEW_BG, highlightthickness=0)
    preview_canvas.pack()

    update_preview()

def set_preview_zoom(z):
    global preview_zoom
    preview_zoom = z
    update_preview()

def update_preview():
    if not preview_canvas:
        return

    preview_canvas.delete("all")

    size = preview_zoom
    offset_x = (256 - GRID_W * size) // 2
    offset_y = (256 - GRID_H * size) // 2

    for y in range(GRID_H):
        for x in range(GRID_W):
            col = pixels[y][x]
            if col:
                preview_canvas.create_rectangle(
                    offset_x + x * size,
                    offset_y + y * size,
                    offset_x + (x + 1) * size,
                    offset_y + (y + 1) * size,
                    fill=col,
                    outline=col
                )

root.mainloop()
