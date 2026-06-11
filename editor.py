import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk, ImageFont, ImageFilter, ImageColor
from matplotlib import font_manager as fm
import os
from collections import deque

class SimpleImageEditor:
    def __init__(self, master):
        self.master = master
        master.title("🎨 Простой Редактор Изображений (Dark Blue)")
        
        # --- ТЕМЫ И СТИЛИ ---
        self.setup_styles()
        
        # --- Настройки адаптивного дизайна ---
        master.grid_rowconfigure(1, weight=1) 
        master.grid_columnconfigure(1, weight=1) 

        # --- Настройки полотна ---
        self.canvas_width = 800
        self.canvas_height = 600
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.tk_image = ImageTk.PhotoImage(self.image)
        
        # --- Настройки инструментов ---
        self.current_tool = 'pencil'
        self.line_color = 'black'
        self.last_color = 'black'
        self.line_thickness = 5
        self.old_x, self.old_y = None, None
        self.start_x, self.start_y = None, None
        self.fill_shape = tk.BooleanVar(value=False)
        
        # --- Настройки для текста ---
        self.font_paths = {}
        self.load_system_fonts()
        self.default_font_name = "Arial"
        self.current_font_path = self.font_paths.get(self.default_font_name, None)
        self.current_font_size = 20
        self.set_current_font(self.current_font_path, self.current_font_size)
        
        # --- Переменные для выделения/перемещения ---
        self.selection_active = False
        self.selection_rect = None
        self.selected_area_image = None
        self.selection_start_coords = None
        self.lasso_points = []

        # --- История ---
        self.history = []
        self.history_pointer = -1

        # --- Настройка интерфейса ---
        self.setup_menu()
        self.setup_layout() 
        self.bind_shortcuts()
        
        self.save_history()
        self.canvas.focus_set()

    def setup_styles(self):
        """Устанавливает контрастную темную тему в синих тонах."""
        style = ttk.Style(self.master)
        style.theme_use('clam') 

        self.BG_COLOR = "#121212"       # Фон главного окна
        self.TOOL_BG_COLOR = "#1f1f1f"  # Фон панелей
        self.TEXT_COLOR = "#e0e0e0"     # Светлый текст
        self.ACCENT_BLUE = "#4A90E2"    # Яркий акцентный синий
        self.ACCENT_HOVER = "#0078D7"   # Синий при наведении

        self.master.config(bg=self.BG_COLOR)
        
        style.configure('Dark.TFrame', background=self.TOOL_BG_COLOR)
        style.configure('Dark.TLabel', background=self.TOOL_BG_COLOR, foreground=self.TEXT_COLOR, font=('Arial', 10))
        style.configure('Dark.TSeparator', background=self.TOOL_BG_COLOR)
        
        style.configure('Dark.TCheckbutton', background=self.TOOL_BG_COLOR, foreground=self.TEXT_COLOR, font=('Arial', 10))
        style.map('Dark.TCheckbutton', background=[('active', self.TOOL_BG_COLOR)]) 

        style.configure('Accent.TButton', 
                        font=('Arial', 10, 'bold'), 
                        background=self.TOOL_BG_COLOR, 
                        foreground=self.ACCENT_BLUE,
                        relief="flat",
                        padding=[8, 5])
        style.map('Accent.TButton', 
                  background=[('active', self.ACCENT_HOVER), ('pressed', self.ACCENT_HOVER)], 
                  foreground=[('active', self.TEXT_COLOR), ('pressed', self.TEXT_COLOR)])

        style.configure('Dark.TEntry', fieldbackground="#333333", foreground=self.TEXT_COLOR, bordercolor=self.ACCENT_BLUE)
        style.map('Dark.TEntry', fieldbackground=[('focus', '#444444')])
        
        style.configure('Dark.TMenubutton', fieldbackground="#333333", foreground=self.TEXT_COLOR, background="#333333", bordercolor=self.ACCENT_BLUE, padding=[5, 5])
        style.map('Dark.TMenubutton', background=[('active', '#444444')])

        style.configure('TScale', background=self.TOOL_BG_COLOR, troughcolor='#333333', slidercolor=self.ACCENT_BLUE)

    def setup_menu(self):
        menubar = tk.Menu(self.master, bg=self.TOOL_BG_COLOR, fg=self.TEXT_COLOR)
        self.master.config(menu=menubar)

        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.TOOL_BG_COLOR, fg=self.TEXT_COLOR)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Новый", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Открыть...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Сохранить как...", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.master.quit)

        # Меню Правка
        edit_menu = tk.Menu(menubar, tearoff=0, bg=self.TOOL_BG_COLOR, fg=self.TEXT_COLOR)
        menubar.add_cascade(label="Правка", menu=edit_menu)
        edit_menu.add_command(label="Отмена (Undo)", command=self.undo_action, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Повтор (Redo)", command=self.redo_action, accelerator="Ctrl+Y")

        # Меню Изображение
        image_menu = tk.Menu(menubar, tearoff=0, bg=self.TOOL_BG_COLOR, fg=self.TEXT_COLOR)
        menubar.add_cascade(label="Изображение", menu=image_menu)
        image_menu.add_command(label="Изменить размер холста...", command=self.resize_canvas_dialog)
        image_menu.add_command(label="Обрезать по выделению", command=self.crop_to_selection, accelerator="Ctrl+Enter")
        image_menu.add_separator()
        image_menu.add_command(label="Повернуть на 90° по часовой", command=self.rotate_clockwise)
        image_menu.add_command(label="Повернуть на 90° против часовой", command=self.rotate_counter_clockwise)
        image_menu.add_command(label="Отразить по горизонтали", command=self.flip_horizontal)
        image_menu.add_command(label="Отразить по вертикали", command=self.flip_vertical)

        # Меню Фильтры
        filter_menu = tk.Menu(menubar, tearoff=0, bg=self.TOOL_BG_COLOR, fg=self.TEXT_COLOR)
        menubar.add_cascade(label="Фильтры", menu=filter_menu)
        filter_menu.add_command(label="Черно-белый", command=self.apply_grayscale_filter)
        filter_menu.add_command(label="Инверсия (Негатив)", command=self.apply_invert_filter)
        filter_menu.add_command(label="Размытие (Blur)", command=self.apply_blur_filter)
        filter_menu.add_command(label="Пикселизация...", command=self.pixelate_dialog)

    def setup_layout(self):
        # 1. Горизонтальная панель (Top Toolbar)
        top_toolbar = ttk.Frame(self.master, style='Dark.TFrame')
        top_toolbar.grid(row=0, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        self.setup_top_toolbar(top_toolbar)
        
        # 2. Вертикальная панель (Sidebar)
        tool_sidebar = ttk.Frame(self.master, style='Dark.TFrame')
        tool_sidebar.grid(row=1, column=0, sticky='ns', padx=(5, 2), pady=(0, 5))
        self.setup_tool_sidebar(tool_sidebar)

        # 3. Canvas Frame
        canvas_frame = ttk.Frame(self.master, relief='flat', style='Dark.TFrame')
        canvas_frame.grid(row=1, column=1, sticky='nsew', padx=(2, 5), pady=(0, 5))
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, width=self.canvas_width,
                                height=self.canvas_height, bg='white', cursor='cross', takefocus=1, 
                                highlightthickness=0) 
        self.canvas.grid(row=0, column=0, sticky='nsew', padx=5, pady=5) 
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw", tags="image_id")
        
        self.canvas.bind('<Button-1>', self.start_draw)
        self.canvas.bind('<Double-Button-1>', lambda e: self.unselect_area())

    def setup_top_toolbar(self, toolbar):
        ttk.Button(toolbar, text="Выбрать цвет", command=self.choose_color, style='Accent.TButton').pack(side=tk.LEFT, padx=(5, 2))
        self.color_display = tk.Label(toolbar, text="■", fg=self.line_color, font=('Arial', 16, 'bold'), width=2, relief='sunken', bg='white', bd=2)
        self.color_display.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL, style='Dark.TSeparator').pack(side=tk.LEFT, padx=10, fill='y')

        ttk.Label(toolbar, text="Толщина:", style='Dark.TLabel').pack(side=tk.LEFT, padx=5)
        self.thickness_scale = ttk.Scale(toolbar, from_=1, to=30, orient=tk.HORIZONTAL,
                                         command=self.set_thickness, length=150)
        self.thickness_scale.set(self.line_thickness)
        self.thickness_scale.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL, style='Dark.TSeparator').pack(side=tk.LEFT, padx=10, fill='y')

        ttk.Checkbutton(toolbar, text="Заливка фигур", variable=self.fill_shape, style='Dark.TCheckbutton').pack(side=tk.LEFT, padx=5)

    def setup_tool_sidebar(self, sidebar):
        ttk.Label(sidebar, text="ИНСТРУМЕНТЫ", style='Dark.TLabel', font=('Arial', 10, 'bold')).pack(side=tk.TOP, pady=(5, 10), padx=10)
        
        tools = [
            ("Карандаш (Ctrl+1)", 'pencil'),
            ("Линия (Ctrl+2)", 'line'),
            ("Прямоугольник (Ctrl+3)", 'rectangle'),
            ("Овал (Ctrl+4)", 'oval'),
            ("Заливка (Ctrl+5)", 'fill'),
            ("Выделение (Ctrl+6)", 'select_rect'),
            ("Текст (Ctrl+7)", 'text'),
            ("Пипетка (Ctrl+8)", 'picker'),
            ("Ластик (Ctrl+9)", 'eraser')
        ]

        for text, tool_name in tools:
            btn = ttk.Button(sidebar, text=text, command=lambda t=tool_name: self.set_tool(t), style='Accent.TButton')
            btn.pack(side=tk.TOP, fill=tk.X, padx=10, pady=4)

    def bind_shortcuts(self):
        """Глобальная привязка горячих клавиш ко всему приложению."""
        self.master.bind_all('<Control-z>', lambda event: self.undo_action())
        self.master.bind_all('<Control-y>', lambda event: self.redo_action())
        self.master.bind_all('<Control-s>', lambda event: self.save_file())
        self.master.bind_all('<Control-n>', lambda event: self.new_file())
        self.master.bind_all('<Control-o>', lambda event: self.open_file())

        self.master.bind_all('<Control-1>', lambda event: self.set_tool('pencil'))
        self.master.bind_all('<Control-2>', lambda event: self.set_tool('line'))
        self.master.bind_all('<Control-3>', lambda event: self.set_tool('rectangle'))
        self.master.bind_all('<Control-4>', lambda event: self.set_tool('oval'))
        self.master.bind_all('<Control-5>', lambda event: self.set_tool('fill'))
        self.master.bind_all('<Control-6>', lambda event: self.set_tool('select_rect'))
        self.master.bind_all('<Control-7>', lambda event: self.set_tool('text'))
        self.master.bind_all('<Control-8>', lambda event: self.set_tool('picker'))
        self.master.bind_all('<Control-9>', lambda event: self.set_tool('eraser'))
        
        self.master.bind_all('<Control-Return>', lambda event: self.crop_to_selection())

        if hasattr(self, 'canvas'):
            self.canvas.focus_set()

    def set_tool(self, tool):
        self.current_tool = tool
        self.unselect_area()
        self.reset_coords(None)

        if tool in ['pencil', 'line', 'rectangle', 'oval']:
            self.canvas.config(cursor='cross')
            self.line_color = self.last_color
        elif tool == 'eraser':
            self.canvas.config(cursor='circle')
            self.line_color = 'white'
        elif tool in ['fill', 'picker']:
            self.canvas.config(cursor='dot')
            self.line_color = self.last_color
        elif tool == 'text':
            self.canvas.config(cursor='xterm')
            self.line_color = self.last_color
        elif tool in ['select_rect', 'select_lasso']:
            self.canvas.config(cursor='tcross')
            
        self.canvas.focus_set()

    def set_thickness(self, val):
        self.line_thickness = int(float(val))

    def choose_color(self):
        color_code = colorchooser.askcolor(title="Выбор цвета", color=self.last_color)
        if color_code:
            hex_color = color_code[1]
            self.last_color = hex_color
            self.color_display.config(fg=hex_color)
            if self.current_tool not in ['eraser', 'picker']:
                 self.line_color = hex_color
        self.canvas.focus_set()

    def start_draw(self, event):
        self.canvas.focus_set()
        self.old_x, self.old_y = event.x, event.y
        self.start_x, self.start_y = event.x, event.y
        
        self.canvas.bind('<B1-Motion>', lambda e: None)
        self.canvas.bind('<ButtonRelease-1>', lambda e: None)
        
        if self.current_tool in ['pencil', 'eraser']:
            self.canvas.bind('<B1-Motion>', self.paint_pencil)
            self.canvas.bind('<ButtonRelease-1>', self.reset_coords)
        elif self.current_tool == 'line':
            self.canvas.bind('<B1-Motion>', self.paint_line)
            self.canvas.bind('<ButtonRelease-1>', self.finalize_line)
        elif self.current_tool in ['rectangle', 'oval']:
            self.canvas.bind('<B1-Motion>', self.paint_shape)
            self.canvas.bind('<ButtonRelease-1>', self.finalize_shape)
        elif self.current_tool == 'fill':
            self.fill_area(event.x, event.y)
            self.reset_coords(None)
        elif self.current_tool == 'picker':
            self.color_pick(event.x, event.y)
            self.set_tool('pencil')
            self.reset_coords(None)
        elif self.current_tool == 'text':
            self.text_dialog(event.x, event.y)
            self.reset_coords(None)
        elif self.current_tool == 'select_rect':
            self._handle_select_start(event.x, event.y, 'rect')

    def _handle_select_start(self, x, y, mode):
        if self.selection_active and self.is_inside_selection(x, y):
            self.selection_start_coords = (x, y)
            self.canvas.bind('<B1-Motion>', self.move_selection)
            self.canvas.bind('<ButtonRelease-1>', self.stop_move)
        else:
            self.unselect_area()
            self.start_x, self.start_y = x, y
            if mode == 'rect':
                self.canvas.bind('<B1-Motion>', self.draw_selection)
                self.canvas.bind('<ButtonRelease-1>', self.capture_selection_rect)

    def reset_coords(self, event):
        if self.current_tool in ['pencil', 'eraser'] and self.old_x is not None and self.old_y is not None:
             self.save_history()

        if self.selection_active:
             self.canvas.bind('<B1-Motion>', lambda e: None)
             self.canvas.bind('<ButtonRelease-1>', lambda e: None)
             return

        self.canvas.bind('<B1-Motion>', lambda e: None)
        self.canvas.bind('<ButtonRelease-1>', lambda e: None)
        
        self.old_x, self.old_y = None, None
        self.start_x, self.start_y = None, None
        self.canvas.delete("temp_line")
        self.canvas.delete("temp_shape")
        
        self.canvas.bind('<Button-1>', self.start_draw)
    
    def paint_pencil(self, event):
        if self.old_x is not None and self.old_y is not None:
            self.draw.line([self.old_x, self.old_y, event.x, event.y],
                            fill=self.line_color, width=self.line_thickness, joint="round")
            self.update_canvas()
        self.old_x = event.x
        self.old_y = event.y

    def paint_line(self, event):
        self.canvas.delete("temp_line")
        self.canvas.create_line(self.start_x, self.start_y, event.x, event.y,
                                 fill=self.line_color, width=self.line_thickness, tags="temp_line")

    def finalize_line(self, event):
        self.canvas.delete("temp_line")
        self.draw.line([self.start_x, self.start_y, event.x, event.y],
                        fill=self.line_color, width=self.line_thickness)
        self.update_canvas()
        self.save_history()
        self.reset_coords(None)

    def paint_shape(self, event):
        self.canvas.delete("temp_shape")
        outline_color = self.line_color
        fill = self.line_color if self.fill_shape.get() else ""
        coords = (self.start_x, self.start_y, event.x, event.y)
        
        if self.current_tool == 'rectangle':
            self.canvas.create_rectangle(coords, outline=outline_color, fill=fill, tags="temp_shape", width=self.line_thickness)
        elif self.current_tool == 'oval':
            self.canvas.create_oval(coords, outline=outline_color, fill=fill, tags="temp_shape", width=self.line_thickness)

    def finalize_shape(self, event):
        self.canvas.delete("temp_shape")
        coords = (self.start_x, self.start_y, event.x, event.y)
        fill = self.line_color if self.fill_shape.get() else None
        
        if self.current_tool == 'rectangle':
            self.draw.rectangle(coords, outline=self.line_color, fill=fill, width=self.line_thickness)
        elif self.current_tool == 'oval':
            self.draw.ellipse(coords, outline=self.line_color, fill=fill, width=self.line_thickness)
            
        self.update_canvas()
        self.save_history()
        self.reset_coords(None)

    def fill_area(self, x, y):
        try:
            target_color = self.image.getpixel((x, y))
            fill_color = ImageColor.getrgb(self.line_color)
            
            if target_color == fill_color:
                messagebox.showinfo("Заливка", "Цвет заливки совпадает с цветом в точке клика.")
                return

            width, height = self.image.size
            queue = deque([(x, y)])
            max_pixels = width * height
            processed_pixels = 0
            
            while queue and processed_pixels < max_pixels * 2:
                px, py = queue.popleft()
                if not (0 <= px < width and 0 <= py < height): continue

                if self.image.getpixel((px, py)) == target_color:
                    self.image.putpixel((px, py), fill_color)
                    processed_pixels += 1
                    queue.append((px + 1, py))
                    queue.append((px - 1, py))
                    queue.append((px, py + 1))
                    queue.append((px, py - 1))
            
            self.update_canvas()
            self.save_history()
        except Exception as e:
            messagebox.showerror("Ошибка заливки", f"Не удалось выполнить заливку: {e}")
            
    def color_pick(self, x, y):
        try:
            rgb_tuple = self.image.getpixel((x, y))
            hex_color = '#%02x%02x%02x' % rgb_tuple
            self.last_color = hex_color
            self.line_color = hex_color
            self.color_display.config(fg=hex_color)
        except IndexError:
            pass

    def load_system_fonts(self):
        font_files = fm.findSystemFonts(fontext='ttf')
        for font_path in font_files:
            try:
                if not os.path.exists(font_path): continue
                prop = fm.FontProperties(fname=font_path)
                font_name = prop.get_name()
                if font_name not in self.font_paths:
                    self.font_paths[font_name] = font_path
            except Exception:
                continue

    def set_current_font(self, path, size):
        self.current_font_size = size
        if path:
            try:
                self.current_font = ImageFont.truetype(path, size)
                self.current_font_path = path
            except IOError:
                self.current_font = ImageFont.load_default()
                self.current_font_path = None
        else:
            self.current_font = ImageFont.load_default()
            self.current_font_path = None

    def draw_text_on_image(self, x, y, text_content):
        self.draw.text((x, y), text_content, fill=self.line_color, font=self.current_font)
        self.update_canvas()
        self.save_history()

    def text_dialog(self, x, y):
        dialog = tk.Toplevel(self.master)
        dialog.title("Добавить текст")
        dialog.config(bg=self.TOOL_BG_COLOR) 
        dialog.transient(self.master)
        
        text_var = tk.StringVar(value="Введите текст")
        size_var = tk.IntVar(value=self.current_font_size)
        
        font_names = sorted(self.font_paths.keys())
        current_font_name = next((name for name, path in self.font_paths.items() if path == self.current_font_path), self.default_font_name)
        selected_font_name = tk.StringVar(value=current_font_name if current_font_name in font_names else (font_names[0] if font_names else ""))
        
        ttk.Label(dialog, text="Текст:", style='Dark.TLabel').grid(row=0, column=0, padx=10, pady=5, sticky='w')
        ttk.Entry(dialog, textvariable=text_var, width=40, style='Dark.TEntry').grid(row=0, column=1, columnspan=2, padx=10, pady=5)
        
        ttk.Label(dialog, text="Шрифт:", style='Dark.TLabel').grid(row=1, column=0, padx=10, pady=5, sticky='w')
        if font_names:
            font_menu = ttk.OptionMenu(dialog, selected_font_name, selected_font_name.get(), *font_names)
            font_menu.config(width=25, style='Dark.TMenubutton')
            font_menu.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky='ew')
        else:
            ttk.Label(dialog, text="Шрифты не найдены.", style='Dark.TLabel').grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky='ew')

        ttk.Label(dialog, text="Размер:", style='Dark.TLabel').grid(row=2, column=0, padx=10, pady=5, sticky='w')
        ttk.Entry(dialog, textvariable=size_var, width=5, style='Dark.TEntry').grid(row=2, column=1, padx=10, pady=5, sticky='w')

        def apply_text():
            try:
                text_content = text_var.get()
                font_size = size_var.get()
                font_name = selected_font_name.get()
                
                if not text_content or font_size <= 0:
                    raise ValueError("Необходимо ввести текст и корректный размер.")
                    
                new_font_path = self.font_paths.get(font_name)
                self.set_current_font(new_font_path, font_size)
                self.draw_text_on_image(x, y, text_content)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка текста", str(e), parent=dialog)

        ttk.Button(dialog, text="Добавить", command=apply_text, style='Accent.TButton').grid(row=3, column=0, padx=10, pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy, style='Accent.TButton').grid(row=3, column=1, padx=10, pady=10)
        
        dialog.focus_set()
        dialog.grab_set()
        self.master.wait_window(dialog)

    def unselect_area(self):
        if self.selected_area_image is not None:
              self.finalize_paste(self.selected_area_image)
        
        self.selection_active = False
        self.selected_area_image = None
        self.selection_start_coords = None
        self.canvas.delete("selection_box")
        self.canvas.delete("selection_image")
        self.update_canvas()

    def is_inside_selection(self, x, y):
        if not self.selection_active or self.selection_rect is None:
            return False
        coords = self.canvas.coords("selection_box")
        if not coords: return False
        x1, y1, x2, y2 = coords
        return min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)

    def move_selection(self, event):
        if self.selection_start_coords is None: return
        dx = event.x - self.selection_start_coords[0]
        dy = event.y - self.selection_start_coords[1]
        
        self.canvas.move("selection_box", dx, dy)
        self.canvas.move("selection_image", dx, dy)
        self.selection_start_coords = (event.x, event.y)
        
    def stop_move(self, event):
        self.canvas.bind('<B1-Motion>', lambda e: None)
        self.canvas.bind('<ButtonRelease-1>', lambda e: None)
        self.selection_start_coords = None
        self.canvas.bind('<Button-1>', self.start_draw) 

    def finalize_paste(self, img):
        img_coords = self.canvas.coords("selection_image")
        if not img_coords: return
        x, y = int(img_coords[0]), int(img_coords[1])
        self.image.paste(img, (x, y))
        self.update_canvas()
        self.save_history()

    def display_selected_image(self, img, x, y):
        self.canvas.delete("selection_image")
        self.selected_tk_image = ImageTk.PhotoImage(img)
        self.canvas.create_image(x, y, image=self.selected_tk_image, anchor="nw", tags="selection_image")

    def draw_selection(self, event):
        self.canvas.delete("selection_box")
        coords = (self.start_x, self.start_y, event.x, event.y)
        self.canvas.create_rectangle(coords, outline='black', dash=(5, 5), tags="selection_box")

    def capture_selection_rect(self, event):
        coords = self.canvas.coords("selection_box")
        if not coords: return
        
        x1, y1, x2, y2 = [int(c) for c in coords]
        xmin, ymin = min(x1, x2), min(y1, y2)
        xmax, ymax = max(x1, x2), max(y1, y2)
        
        self.selected_area_image = self.image.crop((xmin, ymin, xmax, ymax))
        self.draw.rectangle((xmin, ymin, xmax, ymax), fill='white')
        
        self.selection_active = True
        self.update_canvas()
        self.display_selected_image(self.selected_area_image, xmin, ymin)
        
        self.canvas.delete("selection_box")
        self.selection_rect = self.canvas.create_rectangle(xmin, ymin, xmax, ymax, outline='black', dash=(5, 5), tags="selection_box")
        
        self.save_history()
        self.reset_coords(None)

    def apply_transformation(self, method):
        self.unselect_area()
        try:
            self.image = self.image.transpose(method)
            self.draw = ImageDraw.Draw(self.image)
            
            new_w, new_h = self.image.size
            if new_w != self.canvas_width or new_h != self.canvas_height:
                self.canvas_width, self.canvas_height = new_w, new_h
                self.canvas.config(width=self.canvas_width, height=self.canvas_height)

            self.update_canvas()
            self.save_history()
        except Exception as e:
            messagebox.showerror("Ошибка трансформации", f"Не удалось применить трансформацию.\n{e}")

    def rotate_clockwise(self):
        self.apply_transformation(Image.Transpose.ROTATE_90)
    def rotate_counter_clockwise(self):
        self.apply_transformation(Image.Transpose.ROTATE_270)
    def flip_horizontal(self):
        self.apply_transformation(Image.Transpose.FLIP_LEFT_RIGHT)
    def flip_vertical(self):
        self.apply_transformation(Image.Transpose.FLIP_TOP_BOTTOM)

    def crop_to_selection(self):
        if not self.selection_active or self.selection_rect is None:
            messagebox.showinfo("Обрезка", "Сначала выделите область с помощью инструмента выделения.")
            return

        coords = self.canvas.coords("selection_box")
        if not coords: return

        x1, y1, x2, y2 = [int(c) for c in coords]
        xmin, ymin = min(x1, x2), min(y1, y2)
        xmax, ymax = max(x1, x2), max(y1, y2)

        try:
            self.image = self.image.crop((xmin, ymin, xmax, ymax))
            self.draw = ImageDraw.Draw(self.image)
            
            self.canvas_width, self.canvas_height = self.image.size
            self.canvas.config(width=self.canvas_width, height=self.canvas_height)
            
            self.unselect_area()
            self.update_canvas()
            self.save_history()
        except Exception as e:
            messagebox.showerror("Ошибка обрезки", f"Не удалось обрезать изображение.\n{e}")

    def resize_canvas(self, new_w, new_h):
        new_image = Image.new("RGB", (new_w, new_h), "white")
        new_image.paste(self.image, (0, 0))
        self.image = new_image
        self.draw = ImageDraw.Draw(self.image)
        
        self.canvas_width, self.canvas_height = new_w, new_h
        self.canvas.config(width=self.canvas_width, height=self.canvas_height)
        self.update_canvas()
        self.save_history()

    def resize_canvas_dialog(self):
        dialog = tk.Toplevel(self.master)
        dialog.title("Изменить размер холста")
        dialog.config(bg=self.TOOL_BG_COLOR)
        dialog.transient(self.master)
        
        current_w, current_h = self.canvas_width, self.canvas_height
        new_width_var = tk.IntVar(value=current_w)
        new_height_var = tk.IntVar(value=current_h)
        
        ttk.Label(dialog, text=f"Текущий размер: {current_w} x {current_h} px", style='Dark.TLabel').grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        ttk.Label(dialog, text="Новая ширина:", style='Dark.TLabel').grid(row=1, column=0, padx=10, pady=5, sticky='w')
        ttk.Entry(dialog, textvariable=new_width_var, width=10, style='Dark.TEntry').grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="Новая высота:", style='Dark.TLabel').grid(row=2, column=0, padx=10, pady=5, sticky='w')
        ttk.Entry(dialog, textvariable=new_height_var, width=10, style='Dark.TEntry').grid(row=2, column=1, padx=10, pady=5)

        def apply_resize():
            try:
                new_w = new_width_var.get()
                new_h = new_height_var.get()
                if new_w <= 0 or new_h <= 0: raise ValueError()
                self.resize_canvas(new_w, new_h)
                dialog.destroy()
            except Exception:
                messagebox.showerror("Ошибка ввода", "Размеры должны быть положительными числами.", parent=dialog)

        ttk.Button(dialog, text="Применить", command=apply_resize, style='Accent.TButton').grid(row=3, column=0, padx=10, pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy, style='Accent.TButton').grid(row=3, column=1, padx=10, pady=10)
        
        dialog.focus_set()
        dialog.grab_set()
        self.master.wait_window(dialog)

    def apply_grayscale_filter(self):
        self.apply_filter("grayscale")
    def apply_invert_filter(self):
        self.apply_filter("invert")
    def apply_blur_filter(self):
        self.apply_filter(ImageFilter.BLUR)

    def apply_filter(self, filter_method):
        self.unselect_area()
        try:
            if filter_method == "grayscale":
                self.image = self.image.convert("L").convert("RGB")
            elif filter_method == "invert":
                self.image = Image.eval(self.image, lambda x: 255 - x)
            else:
                self.image = self.image.filter(filter_method)

            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
            self.save_history()
        except Exception as e:
            messagebox.showerror("Ошибка фильтра", f"Не удалось применить фильтр.\n{e}")

    def pixelate_dialog(self):
        dialog = tk.Toplevel(self.master)
        dialog.title("Пикселизация")
        dialog.config(bg=self.TOOL_BG_COLOR)
        dialog.transient(self.master)

        pixel_size_var = tk.IntVar(value=10)
        ttk.Label(dialog, text="Размер пиксельного блока:", style='Dark.TLabel').grid(row=0, column=0, padx=10, pady=5, sticky='w')
        ttk.Entry(dialog, textvariable=pixel_size_var, width=10, style='Dark.TEntry').grid(row=0, column=1, padx=10, pady=5)
        
        def apply_pixelation():
            try:
                size = pixel_size_var.get()
                if size <= 0: raise ValueError()
                self.apply_pixelation_filter(size)
                dialog.destroy()
            except Exception:
                messagebox.showerror("Ошибка ввода", "Размер должен быть больше нуля.", parent=dialog)

        ttk.Button(dialog, text="Применить", command=apply_pixelation, style='Accent.TButton').grid(row=1, column=0, padx=10, pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy, style='Accent.TButton').grid(row=1, column=1, padx=10, pady=10)
        
        dialog.focus_set()
        dialog.grab_set()
        self.master.wait_window(dialog)

    def apply_pixelation_filter(self, size):
        if size <= 0: return
        self.unselect_area()
        try:
            width, height = self.image.size
            small_width = max(1, width // size)
            small_height = max(1, height // size)
            
            self.image = self.image.resize((small_width, small_height), Image.Resampling.BILINEAR)
            self.image = self.image.resize((width, height), Image.Resampling.NEAREST)
            
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
            self.save_history()
        except Exception as e:
            messagebox.showerror("Ошибка пикселизации", f"Не удалось выполнить.\n{e}")

    def save_history(self):
        if self.history_pointer < len(self.history) - 1:
            self.history = self.history[:self.history_pointer + 1]
            
        MAX_HISTORY = 30
        if len(self.history) >= MAX_HISTORY:
            self.history.pop(0)
            self.history_pointer -= 1

        self.history.append(self.image.copy())
        self.history_pointer += 1

    def load_history_state(self):
        if 0 <= self.history_pointer < len(self.history):
            self.image = self.history[self.history_pointer].copy()
            self.draw = ImageDraw.Draw(self.image)
            self.canvas_width, self.canvas_height = self.image.size
            self.canvas.config(width=self.canvas_width, height=self.canvas_height)
            self.update_canvas()

    def undo_action(self):
        if self.history_pointer > 0:
            self.unselect_area()
            self.history_pointer -= 1
            self.load_history_state()

    def redo_action(self):
        if self.history_pointer < len(self.history) - 1:
            self.unselect_area()
            self.history_pointer += 1
            self.load_history_state()

    def update_canvas(self):
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.delete("image_id")
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw", tags="image_id")

    def new_file(self):
        self.unselect_area()
        self.canvas_width = 800
        self.canvas_height = 600
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.canvas.config(width=self.canvas_width, height=self.canvas_height)
        self.update_canvas()
        self.history = []
        self.history_pointer = -1
        self.save_history()

    def open_file(self):
        self.unselect_area()
        filepath = filedialog.askopenfilename(defaultextension=".png",
                                              filetypes=[("PNG files", "*.png"),
                                                         ("JPEG files", "*.jpg;*.jpeg"),
                                                         ("All files", "*.*")])
        if filepath:
            try:
                self.image = Image.open(filepath).convert("RGB")
                self.draw = ImageDraw.Draw(self.image)
                self.canvas_width, self.canvas_height = self.image.size
                self.canvas.config(width=self.canvas_width, height=self.canvas_height)
                self.update_canvas()
                self.history = []
                self.history_pointer = -1
                self.save_history()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")

    def save_file(self):
        self.unselect_area()
        filepath = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG file", "*.png"),
                                                            ("JPEG file", "*.jpg"),
                                                            ("BMP file", "*.bmp")])
        if filepath:
            try:
                save_format = filepath.split('.')[-1].upper()
                if save_format in ['JPG', 'JPEG']:
                    self.image.convert('RGB').save(filepath, "JPEG")
                elif save_format == 'BMP':
                    self.image.save(filepath, "BMP")
                else:
                    self.image.save(filepath, "PNG")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry('950x750') 
    editor = SimpleImageEditor(root)
    root.mainloop()