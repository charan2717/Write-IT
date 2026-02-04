# Write It - A Simple Notes App
# Copyright (C) 2025 Charan Achanta
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# <- These are the requirements that are used ->
import tkinter as tk
from tkinter import messagebox, filedialog, font, ttk, scrolledtext, simpledialog
import sqlite3
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from datetime import datetime
import time
import os
from PIL import Image, ImageTk, ImageGrab
import io
import base64
import json

DATABASE = 'advanced_notes.db'

def create_tables():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # <- Tables are created for saving the file ->
    c.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            images TEXT,
            formatting TEXT
        )
    ''')
    
    # <- Table for settings ->
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            theme TEXT DEFAULT 'dark',
            font_family TEXT DEFAULT 'Arial',
            font_size INTEGER DEFAULT 12
        )
    ''')
    
    # <- This checks whether there is a table or not. If no table found then it will create a table ->
    cursor = conn.execute('PRAGMA table_info(notes)')
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'images' not in columns:
        try:
            c.execute('ALTER TABLE notes ADD COLUMN images TEXT')
        except sqlite3.Error as e:
            print(f"Database migration error: {e}")
    
    # <- Checking for formatting. If not done then the code does it ->
    if 'formatting' not in columns:
        try:
            c.execute('ALTER TABLE notes ADD COLUMN formatting TEXT')
        except sqlite3.Error as e:
            print(f"Database migration error: {e}")
    
    # <- Whether the settings have one row or not ->
    c.execute('SELECT COUNT(*) FROM settings')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO settings (theme, font_family, font_size) VALUES (?, ?, ?)', 
                ('dark', 'Arial', 12))
    
    conn.commit()
    conn.close()

def get_settings():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT theme, font_family, font_size FROM settings WHERE id = 1')
    settings = c.fetchone()
    conn.close()
    
    if not settings:
        return {'theme': 'dark', 'font_family': 'Arial', 'font_size': 12}
    
    return {
        'theme': settings[0],
        'font_family': settings[1],
        'font_size': settings[2]
    }

def save_settings(settings):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('UPDATE settings SET theme = ?, font_family = ?, font_size = ? WHERE id = 1', 
            (settings['theme'], settings['font_family'], settings['font_size']))
    conn.commit()
    conn.close()

def save_note_to_db(title, content, images_data, formatting_data):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # <- Images are being converted into JSON Strings ->
    images_str = json.dumps(images_data) if images_data else "{}"
    
    # <- Formatting data coverting into JSON Strings ->
    formatting_str = json.dumps(formatting_data) if formatting_data else "{}"
    
    c.execute('INSERT INTO notes (title, content, updated_at, images, formatting) VALUES (?, ?, ?, ?, ?)', 
            (title, content, datetime.now(), images_str, formatting_str))
    
    conn.commit()
    conn.close()

def update_note_in_db(note_id, title, content, images_data, formatting_data):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # <- Images are being converted into JSON Strings ->
    images_str = json.dumps(images_data) if images_data else "{}"
    
    # <- Formatting data coverting into JSON Strings ->
    formatting_str = json.dumps(formatting_data) if formatting_data else "{}"
    
    c.execute('UPDATE notes SET title = ?, content = ?, updated_at = ?, images = ?, formatting = ? WHERE id = ?', 
            (title, content, datetime.now(), images_str, formatting_str, note_id))
    
    conn.commit()
    conn.close()

def get_notes_from_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT id, title FROM notes ORDER BY updated_at DESC')
    
    notes = c.fetchall()
    conn.close()
    return notes

def get_recent_notes_from_db(limit=6):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT id, title, updated_at FROM notes ORDER BY updated_at DESC LIMIT ?', (limit,))
    
    notes = c.fetchall()
    conn.close()
    return notes

def get_note_content(note_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT title, content, images, formatting FROM notes WHERE id = ?', (note_id,))
    note = c.fetchone()
    conn.close()
    return note

def delete_note_from_db(note_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()

class NotesApp:
    def __init__(self, root):
        self.root = root  
        self.root.title("Write It")
        self.root.geometry("1200x800")
        
        # <- Initialize database first to ensure schema is updated ->
        create_tables()
        
        # <- Load settings ->
        self.settings = get_settings()
        
        # <- Set theme based on settings(Dark mode or light mode) ->
        self.theme = self.settings['theme']
        self.style = tb.Style(theme="darkly" if self.theme == 'dark' else "flatly")
        
        # <- Initialize variables ->
        self.current_note_id = None
        self.images_data = {}  
        self.image_counter = 0  
        self.formatting_data = {}  
        self.open_notes = []  
        self.active_tab = None  
        
        self.current_format = {
            'bold': False,
            'italic': False,
            'underline': False,
            'font_size': self.settings['font_size'],
            'font_family': self.settings['font_family']
        }
        
        # <- color schemes for light and dark modes ->
        self.color_schemes = {
            'dark': {
                'bg_primary': '#1a1a2e',
                'bg_secondary': '#1a1a2e',  
                'bg_tertiary': '#0f3460',
                'text_primary': '#ffffff',
                'text_secondary': '#cccccc',
                'text_accent': '#e94560',
                'button_primary': '#e94560',
                'button_secondary': '#0f3460',
                'editor_bg': '#0d1117',
                'editor_text': '#ffffff',
                'tab_active': '#533483',
                'tab_inactive': '#16213e',
                'success': '#4caf50',
                'warning': '#ff9800',
                'danger': '#f44336',
                'info': '#2196f3',
                'frame_border': '#0f3460'  
            },
            'light': {
                'bg_primary': '#ffffff',  
                'bg_secondary': '#ffffff',  
                'bg_tertiary': '#3f72af',
                'text_primary': '#112d4e',
                'text_secondary': '#3f72af',
                'text_accent': '#112d4e',
                'button_primary': '#112d4e',
                'button_secondary': '#3f72af',
                'editor_bg': '#ffffff',
                'editor_text': '#112d4e',
                'tab_active': '#112d4e',
                'tab_inactive': '#dbe2ef',
                'success': '#4caf50',
                'warning': '#ff9800',
                'danger': '#f44336',
                'info': '#2196f3',
                'frame_border': '#dbe2ef'  
            }
        }
        
        # Get current color scheme
        self.colors = self.color_schemes[self.theme]
        
        # Menu Bar
        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)
        
        # File Menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], 
                                activebackground=self.colors['bg_tertiary'], activeforeground=self.colors['text_primary'])
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Home", command=self.show_homepage)
        self.file_menu.add_command(label="New", command=self.new_note)
        self.file_menu.add_command(label="Open", command=self.open_note_dialog)
        self.file_menu.add_command(label="Save", command=self.save_note)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=root.quit)
        
        # Edit Menu
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                activebackground=self.colors['bg_tertiary'], activeforeground=self.colors['text_primary'])
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Bold (Ctrl+B)", command=self.toggle_bold)
        self.edit_menu.add_command(label="Italic (Ctrl+I)", command=self.toggle_italic)
        self.edit_menu.add_command(label="Underline (Ctrl+U)", command=self.toggle_underline)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Insert Image", command=self.insert_image)
        
        # View Menu
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                activebackground=self.colors['bg_tertiary'], activeforeground=self.colors['text_primary'])
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="Toggle Theme", command=self.toggle_theme)

        # Create main container
        self.main_container = tk.Frame(root, bg=self.colors['bg_primary'])
        self.main_container.pack(fill="both", expand=True)
        
        # Create frames for different "pages"
        self.homepage_frame = tk.Frame(self.main_container, bg=self.colors['bg_primary'])
        self.editor_page_frame = tk.Frame(self.main_container, bg=self.colors['bg_primary'])
        
        # Initialize both pages
        self.setup_homepage()
        self.setup_editor_page()
        
        # Show homepage by default
        self.show_homepage()

        # Bind keyboard shortcuts
        self.root.bind('<Control-b>', self.toggle_bold)
        self.root.bind('<Control-i>', self.toggle_italic)
        self.root.bind('<Control-u>', self.toggle_underline)
        self.root.bind('<Control-v>', self.paste_from_clipboard)

        # Bind window resize event
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Bind text insertion to maintain formatting
        self.text_area.bind("<<Modified>>", self.on_text_modified)

    def setup_homepage(self):
        # Header with app title and theme toggle
        self.header_frame = tk.Frame(self.homepage_frame, bg=self.colors['bg_tertiary'], height=100)
        self.header_frame.pack(fill="x")
        
        self.app_title = tk.Label(
            self.header_frame,
            text="Write It",
            font=("Helvetica", 48, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        self.app_title.place(relx=0.5, rely=0.5, anchor="center")
        
        # Welcome section - now with plain background
        self.welcome_frame = tk.Frame(self.homepage_frame, bg=self.colors['bg_primary'], height=150)
        self.welcome_frame.pack(fill="x", pady=20, padx=100)
        
        self.welcome_title = tk.Label(
            self.welcome_frame,
            text="Welcome to Write It Beta-2a",
            font=("Helvetica", 24, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_primary']
        )
        self.welcome_title.pack(pady=(20, 5))

        self.welcome_subtitle = tk.Label(
            self.welcome_frame,
            text="Your ideas, written simply. A beautiful note-taking experience.",
            font=("Helvetica", 14),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_primary']
        )
        self.welcome_subtitle.pack(pady=(0, 20))

        # Action buttons
        self.action_center = tk.Frame(self.homepage_frame, bg=self.colors['bg_primary'])
        self.action_center.pack(pady=20, fill="x")
        
        # Create a container for centered buttons
        self.button_container = tk.Frame(self.action_center, bg=self.colors['bg_primary'])
        self.button_container.pack()
        
        # New note button
        self.new_note_btn = tk.Button(
            self.button_container,
            text="Create New Note",
            command=self.new_note,
            bg=self.colors['button_primary'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 12),
            relief="flat",
            padx=20,
            pady=10
        )
        self.new_note_btn.pack(side="left", padx=20)
        
        # Open note button
        self.open_note_btn = tk.Button(
            self.button_container,
            text="View All Notes",
            command=self.open_note_dialog,
            bg=self.colors['button_secondary'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 12),
            relief="flat",
            padx=20,
            pady=10
        )
        self.open_note_btn.pack(side="left", padx=20)

        # Recent Notes section
        self.recent_title_frame = tk.Frame(self.homepage_frame, bg=self.colors['bg_primary'])
        self.recent_title_frame.pack(fill="x", pady=(40, 10))
        
        self.recent_title = tk.Label(
            self.recent_title_frame,
            text="Recent Notes",
            font=("Helvetica", 22, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_primary']
        )
        self.recent_title.pack()
        
        # Recent notes container
        self.recent_frame = tk.Frame(self.homepage_frame, bg=self.colors['bg_primary'])
        self.recent_frame.pack(fill="both", expand=True, padx=30, pady=10)

        self.recent_grid = tk.Frame(self.recent_frame, bg=self.colors['bg_primary'])
        self.recent_grid.pack(fill="both", expand=True)

        # Status bar
        self.status_frame = tk.Frame(self.homepage_frame, bg=self.colors['bg_tertiary'], height=30)
        self.status_frame.pack(fill="x", side="bottom")
        
        self.home_status_bar = tk.Label(
            self.status_frame,
            text="Ready",
            font=("Helvetica", 10),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary'],
            anchor="w",
            padx=10
        )
        self.home_status_bar.pack(side="left")

        self.update_recent_notes()

    def setup_editor_page(self):
        # Header with app title and navigation
        self.editor_header_frame = tk.Frame(self.editor_page_frame, bg=self.colors['bg_tertiary'], height=60)
        self.editor_header_frame.pack(fill="x")
        
        self.editor_app_title = tk.Label(
            self.editor_header_frame, 
            text="Write It", 
            font=("Helvetica", 20, "bold"),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        self.editor_app_title.place(x=20, rely=0.5, anchor="w")
        
        # Theme toggle button
        self.editor_theme_toggle = tk.Button(
            self.editor_header_frame,
            text="🌙" if self.theme == 'light' else "☀️",
            command=self.toggle_theme,
            font=("Helvetica", 12),
            bg=self.colors['bg_tertiary'],
            fg=self.colors['text_primary'],
            relief="flat",
            bd=0,
            padx=10,
            pady=5
        )
        self.editor_theme_toggle.place(relx=0.95, rely=0.5, anchor="e")
        
        # Home button
        self.home_button = tk.Button(
            self.editor_header_frame,
            text="Back to Home",
            command=self.show_homepage,
            bg=self.colors['button_secondary'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 10),
            relief="flat",
            padx=10,
            pady=5
        )
        self.home_button.place(relx=0.85, rely=0.5, anchor="e")

        # Tab bar for open notes - with minimal styling
        self.tab_frame = tk.Frame(self.editor_page_frame, bg=self.colors['bg_primary'], height=40)
        self.tab_frame.pack(fill="x")
        
        # Create a canvas for the tab bar with horizontal scrolling
        self.tab_canvas = tk.Canvas(self.tab_frame, height=40, bg=self.colors['bg_primary'], highlightthickness=0)
        self.tab_canvas.pack(fill="x", side="top")
        
        # Create a frame inside the canvas for the tabs
        self.tabs_container = ttk.Frame(self.tab_canvas)
        # Create a style for the tabs container instead of directly setting background
        self.style.configure('TabsContainer.TFrame', background=self.colors['bg_primary'])
        self.tabs_container.configure(style='TabsContainer.TFrame')
        self.tab_canvas.create_window((0, 0), window=self.tabs_container, anchor="nw")
        
        # Configure scrolling for the tab bar
        self.tab_scrollbar = ttk.Scrollbar(self.tab_frame, orient="horizontal", command=self.tab_canvas.xview)
        self.tab_scrollbar.pack(fill="x", side="bottom")
        self.tab_canvas.configure(xscrollcommand=self.tab_scrollbar.set)
        
        # Bind events for scrolling
        self.tabs_container.bind("<Configure>", lambda e: self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox("all")))
        self.tab_canvas.bind("<Configure>", self.on_tab_canvas_configure)
        
        # Bind mouse wheel for horizontal scrolling
        self.tab_canvas.bind("<MouseWheel>", self.on_mousewheel)

        # Toolbar - with frame
        self.toolbar_frame = tk.Frame(
            self.editor_page_frame, 
            bg=self.colors['bg_tertiary'], 
            height=40,
            bd=1,
            relief="raised"
        )
        self.toolbar_frame.pack(fill="x")
        
        # Formatting buttons
        btn_bg = self.colors['button_secondary']
        btn_fg = self.colors['text_primary']
        btn_width = 3
        
        self.bold_button = tk.Button(
            self.toolbar_frame, 
            text="B", 
            command=self.toggle_bold, 
            bg=btn_bg,
            fg=btn_fg,
            font=("Helvetica", 10, "bold"),
            relief="flat",
            width=btn_width
        )
        self.bold_button.place(x=20, rely=0.5, anchor="w")
        
        self.italic_button = tk.Button(
            self.toolbar_frame, 
            text="I", 
            command=self.toggle_italic, 
            bg=btn_bg,
            fg=btn_fg,
            font=("Helvetica", 10, "italic"),
            relief="flat",
            width=btn_width
        )
        self.italic_button.place(x=60, rely=0.5, anchor="w")
        
        self.underline_button = tk.Button(
            self.toolbar_frame, 
            text="U", 
            command=self.toggle_underline, 
            bg=btn_bg,
            fg=btn_fg,
            font=("Helvetica", 10, "underline"),
            relief="flat",
            width=btn_width
        )
        self.underline_button.place(x=100, rely=0.5, anchor="w")
        
        # Image button
        self.image_button = tk.Button(
            self.toolbar_frame,
            text="Image",
            command=self.insert_image,
            bg=btn_bg,
            fg=btn_fg,
            font=("Helvetica", 10),
            relief="flat",
            padx=10
        )
        self.image_button.place(x=150, rely=0.5, anchor="w")

        # Font controls
        self.font_size_label = tk.Label(
            self.toolbar_frame, 
            text="Size:", 
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary'],
            font=("Helvetica", 10)
        )
        self.font_size_label.place(x=220, rely=0.5, anchor="w")

        self.font_size_combo = ttk.Combobox(
            self.toolbar_frame, 
            values=[8, 10, 12, 14, 16, 18, 20, 24], 
            width=5
        )
        self.font_size_combo.set(self.current_format['font_size'])
        self.font_size_combo.place(x=260, rely=0.5, anchor="w")
        self.font_size_combo.bind("<<ComboboxSelected>>", self.change_font_size)
        self.font_size_combo.bind("<Return>", self.change_font_size)
        self.font_size_combo.bind("<FocusOut>", self.change_font_size)

        self.font_family_label = tk.Label(
            self.toolbar_frame, 
            text="Font:", 
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary'],
            font=("Helvetica", 10)
        )
        self.font_family_label.place(x=320, rely=0.5, anchor="w")

        # Get available system fonts
        available_fonts = sorted(list(font.families()))
        self.font_family_combo = ttk.Combobox(
            self.toolbar_frame, 
            values=available_fonts,
            width=15
        )
        self.font_family_combo.set(self.current_format['font_family'])
        self.font_family_combo.place(x=360, rely=0.5, anchor="w")
        self.font_family_combo.bind("<<ComboboxSelected>>", self.change_font_family)
        self.font_family_combo.bind("<Return>", self.change_font_family)
        self.font_family_combo.bind("<FocusOut>", self.change_font_family)

        # Quick action buttons on the right side
        self.delete_button = tk.Button(
            self.toolbar_frame, 
            text="Delete Note", 
            command=self.delete_note, 
            bg=self.colors['danger'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 10),
            relief="flat",
            padx=10
        )
        self.delete_button.place(relx=0.98, rely=0.5, anchor="e")
        
        self.save_button = tk.Button(
            self.toolbar_frame, 
            text="Save Note", 
            command=self.save_note, 
            bg=self.colors['success'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 10),
            relief="flat",
            padx=10
        )
        self.save_button.place(relx=0.88, rely=0.5, anchor="e")

        self.new_button = tk.Button(
            self.toolbar_frame, 
            text="New Note", 
            command=self.new_note, 
            bg=self.colors['info'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 10),
            relief="flat",
            padx=10
        )
        self.new_button.place(relx=0.78, rely=0.5, anchor="e")

        # Content area with editor - plain background
        self.content_container = tk.Frame(self.editor_page_frame, bg=self.colors['bg_primary'])
        self.content_container.pack(fill="both", expand=True, pady=(10, 0))

        # Text Area
        self.text_frame = tk.Frame(self.content_container, bg=self.colors['bg_primary'])
        self.text_frame.pack(fill="both", expand=True)
        
        self.text_area = tk.Text(
            self.text_frame, 
            font=(self.current_format['font_family'], self.current_format['font_size']), 
            wrap="none",  # Changed to none for horizontal scrolling
            undo=True,
            bg=self.colors['editor_bg'],
            fg=self.colors['editor_text'],
            insertbackground=self.colors['text_accent'],  # cursor color
            selectbackground=self.colors['bg_tertiary'],
            selectforeground=self.colors['text_primary'],
            padx=15,
            pady=15,
            relief="flat",
            borderwidth=0
        )
        self.text_area.pack(fill="both", expand=True)
        
        # Add vertical scrollbar to text area
        self.text_v_scrollbar = ttk.Scrollbar(
            self.text_area, 
            command=self.text_area.yview
        )
        self.text_area.config(yscrollcommand=self.text_v_scrollbar.set)
        self.text_v_scrollbar.pack(side="right", fill="y")
        
        # Add horizontal scrollbar to text area
        self.text_h_scrollbar = ttk.Scrollbar(
            self.text_frame, 
            orient="horizontal",
            command=self.text_area.xview
        )
        self.text_area.config(xscrollcommand=self.text_h_scrollbar.set)
        self.text_h_scrollbar.pack(side="bottom", fill="x")
        
        # Configure text tags for formatting
        self.text_area.tag_configure("bold", font=(self.current_format['font_family'], self.current_format['font_size'], "bold"))
        self.text_area.tag_configure("italic", font=(self.current_format['font_family'], self.current_format['font_size'], "italic"))
        self.text_area.tag_configure("underline", font=(self.current_format['font_family'], self.current_format['font_size'], "underline"))
        self.text_area.tag_configure("bold-italic", font=(self.current_format['font_family'], self.current_format['font_size'], "bold italic"))
        self.text_area.tag_configure("bold-underline", font=(self.current_format['font_family'], self.current_format['font_size'], "bold underline"))
        self.text_area.tag_configure("italic-underline", font=(self.current_format['font_family'], self.current_format['font_size'], "italic underline"))
        self.text_area.tag_configure("bold-italic-underline", font=(self.current_format['font_family'], self.current_format['font_size'], "bold italic underline"))

        # Status bar
        self.editor_status_frame = tk.Frame(self.editor_page_frame, bg=self.colors['bg_tertiary'], height=30)
        self.editor_status_frame.pack(fill="x", side="bottom")
        
        self.editor_status_bar = tk.Label(
            self.editor_status_frame,
            text="Ready",
            font=("Helvetica", 10),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary'],
            anchor="w",
            padx=10
        )
        self.editor_status_bar.pack(side="left")

        # Add keyboard shortcut info to status bar
        self.shortcut_info = tk.Label(
            self.editor_status_frame,
            text="Shortcuts: Ctrl+B (Bold) | Ctrl+I (Italic) | Ctrl+U (Underline)",
            font=("Helvetica", 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_tertiary'],
            anchor="e",
            padx=10
        )
        self.shortcut_info.pack(side="right")

    def toggle_theme(self):
        # Toggle theme
        self.theme = 'light' if self.theme == 'dark' else 'dark'
        
        # Update colors
        self.colors = self.color_schemes[self.theme]
        
        # Update theme in settings
        self.settings['theme'] = self.theme
        save_settings(self.settings)
        
        # Update style
        self.style.theme_use("darkly" if self.theme == 'dark' else "flatly")
        
        # Update theme toggle buttons
        self.theme_toggle_btn.configure(text="🌙" if self.theme == 'light' else "☀️")
        self.editor_theme_toggle.configure(text="🌙" if self.theme == 'light' else "☀️")
        
        # Recreate the UI with new colors
        # First, save the current state
        current_page = "homepage" if self.homepage_frame.winfo_ismapped() else "editor"
        
        # Clear existing frames
        for widget in self.homepage_frame.winfo_children():
            widget.destroy()
        for widget in self.editor_page_frame.winfo_children():
            widget.destroy()
        
        # Recreate the UI
        self.setup_homepage()
        self.setup_editor_page()
        
        # Restore the current state
        if current_page == "homepage":
            self.show_homepage()
        else:
            self.show_editor_page()
            
            # Restore open tabs
            for note_id, title in self.open_notes:
                self.add_tab(note_id, title)
            
            # Restore active tab
            if self.active_tab is not None:
                self.activate_tab(self.active_tab)
        
        # Update text area colors
        self.text_area.configure(
            bg=self.colors['editor_bg'],
            fg=self.colors['editor_text'],
            insertbackground=self.colors['text_accent'],
            selectbackground=self.colors['bg_tertiary'],
            selectforeground=self.colors['text_primary']
        )
        
        # Show animation
        self.animate_status_bar(f"Theme changed to {self.theme} mode")

    def on_text_modified(self, event=None):
        if not self.text_area.edit_modified():
            return

        # Reset the modified flag
        self.text_area.edit_modified(False)

        # Apply formatting to the most recently inserted character(s)
        insert_pos = self.text_area.index(tk.INSERT)
        start_pos = self.text_area.index(f"{insert_pos}-1c")
        if self.text_area.compare(start_pos, "<", "1.0"):
            start_pos = "1.0"
        if self.text_area.compare(start_pos, "<", insert_pos):
            self.apply_current_formatting(start_pos, insert_pos)

    def apply_current_formatting(self, start_pos, end_pos):
        # Apply bold formatting if active
        if self.current_format['bold']:
            self.text_area.tag_add("bold", start_pos, end_pos)

        # Apply italic formatting if active
        if self.current_format['italic']:
            self.text_area.tag_add("italic", start_pos, end_pos)

        # Apply underline formatting if active
        if self.current_format['underline']:
            self.text_area.tag_add("underline", start_pos, end_pos)

        # Apply font size if different from default
        if self.current_format['font_size'] != self.settings['font_size']:
            tag_name = f"size_{self.current_format['font_size']}"
            self.text_area.tag_configure(
                tag_name,
                font=(self.current_format['font_family'], self.current_format['font_size'])
            )
            self.text_area.tag_add(tag_name, start_pos, end_pos)

        # Apply font family if different from default
        if self.current_format['font_family'] != self.settings['font_family']:
            tag_name = f"family_{self.current_format['font_family']}"
            self.text_area.tag_configure(
                tag_name,
                font=(self.current_format['font_family'], self.current_format['font_size'])
            )
            self.text_area.tag_add(tag_name, start_pos, end_pos)

    def on_tab_canvas_configure(self, event):
        # Update the scrollregion to encompass the inner frame
        self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox("all"))
        # Set the canvas width to match the window width
        self.tab_canvas.itemconfig(self.tab_canvas.find_withtag("all")[0], width=event.width)

    def on_mousewheel(self, event):
        # Scroll horizontally with the mouse wheel
        self.tab_canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    def add_tab(self, note_id, title):
        # Check if tab already exists
        for tab_id, tab_title in self.open_notes:
            if tab_id == note_id:
                # Tab already exists, just activate it
                self.activate_tab(note_id)
                return
        
        # Create a new tab
        tab_frame = ttk.Frame(self.tabs_container)
        # Use style instead of direct background configuration
        self.style.configure('TabFrame.TFrame', background=self.colors['bg_primary'])
        tab_frame.configure(style='TabFrame.TFrame')
        tab_frame.pack(side="left", padx=2, pady=2)
        
        # Add tab to the list of open notes
        self.open_notes.append((note_id, title))
        
        # Create tab button with title and close button
        tab_button = tk.Button(
            tab_frame,
            text=title,
            bg=self.colors['tab_inactive'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 10),
            relief="flat",
            padx=10,
            command=lambda id=note_id: self.activate_tab(id)
        )
        tab_button.pack(side="left", padx=0)
        
        close_button = tk.Button(
            tab_frame,
            text="×",
            bg=self.colors['tab_inactive'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 10, "bold"),
            relief="flat",
            padx=5,
            command=lambda id=note_id: self.close_tab(id)
        )
        close_button.pack(side="left", padx=0)
        
        # Store references to the tab components
        if not hasattr(self, 'tab_references'):
            self.tab_references = {}
        
        self.tab_references[note_id] = {
            'frame': tab_frame,
            'button': tab_button,
            'close': close_button
        }
        
        # Activate the new tab
        self.activate_tab(note_id)
        
        # Update the tab canvas scrollregion
        self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox("all"))

    def activate_tab(self, note_id):
        # Deactivate current tab if any
        if self.active_tab is not None and self.active_tab in self.tab_references:
            self.tab_references[self.active_tab]['button'].configure(bg=self.colors['tab_inactive'])
            self.tab_references[self.active_tab]['close'].configure(bg=self.colors['tab_inactive'])
        
        # Activate the selected tab
        if note_id in self.tab_references:
            self.tab_references[note_id]['button'].configure(bg=self.colors['tab_active'])
            self.tab_references[note_id]['close'].configure(bg=self.colors['tab_active'])
            self.active_tab = note_id
            
            # Load the note content
            self.open_note_by_id(note_id)

    def close_tab(self, note_id):
        # Remove the tab from the UI
        if note_id in self.tab_references:
            self.tab_references[note_id]['frame'].destroy()
            del self.tab_references[note_id]
        
        # Remove from open notes list
        self.open_notes = [(id, title) for id, title in self.open_notes if id != note_id]
        
        # If this was the active tab, activate another one if available
        if self.active_tab == note_id:
            self.active_tab = None
            if self.open_notes:
                self.activate_tab(self.open_notes[0][0])
            else:
                # No tabs left, clear the editor
                self.current_note_id = None
                self.text_area.delete(1.0, tk.END)
                self.images_data = {}
                self.image_counter = 0
                self.formatting_data = {}
                
                # Reset current formatting
                self.current_format = {
                    'bold': False,
                    'italic': False,
                    'underline': False,
                    'font_size': self.settings['font_size'],
                    'font_family': self.settings['font_family']
                }
                
                # Update formatting buttons
                self.bold_button.configure(bg=self.colors['button_secondary'])
                self.italic_button.configure(bg=self.colors['button_secondary'])
                self.underline_button.configure(bg=self.colors['button_secondary'])
                self.font_size_combo.set(self.current_format['font_size'])
                self.font_family_combo.set(self.current_format['font_family'])
        
        # Update the tab canvas scrollregion
        self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox("all"))

    def show_homepage(self):
        # Hide editor page and show homepage
        self.editor_page_frame.pack_forget()
        self.homepage_frame.pack(fill="both", expand=True)
        self.update_recent_notes()
        self.animate_status_bar("Welcome to Write It")
        
    def show_editor_page(self):
        # Hide homepage and show editor page
        self.homepage_frame.pack_forget()
        self.editor_page_frame.pack(fill="both", expand=True)
        self.animate_status_bar("Editor ready")
        
    def animate_status_bar(self, message):
        # Animate status bar text
        if self.homepage_frame.winfo_ismapped():
            status_bar = self.home_status_bar
        else:
            status_bar = self.editor_status_bar
            
        status_bar.config(text="")
        
        def update_text(index=0):
            if index <= len(message):
                status_bar.config(text=message[:index])
                self.root.after(30, update_text, index + 1)
        
        update_text()
        
    def update_recent_notes(self):
        # Clear existing widgets in the grid
        for widget in self.recent_grid.winfo_children():
            widget.destroy()
            
        # Get recent notes
        recent_notes = get_recent_notes_from_db(6)
        
        # Create note cards
        row, col = 0, 0
        for note in recent_notes:
            note_id, title, date_str = note
            
            # Format the date - handle both string and datetime formats
            try:
                if isinstance(date_str, str):
                    # Try to parse the date string
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        # If that fails, try without microseconds
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    formatted_date = date_obj.strftime('%b %d, %Y')
                else:
                    # If it's already a datetime object
                    formatted_date = date_str.strftime('%b %d, %Y')
            except (ValueError, TypeError):
                # If all parsing fails, use a default
                formatted_date = "Unknown date"
            
            # Create a card frame with border
            card = tk.Frame(
                self.recent_grid, 
                bg=self.colors['bg_primary'], 
                bd=1, 
                relief="solid",
                highlightbackground=self.colors['frame_border'],
                highlightthickness=1
            )
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # Add title
            note_title = tk.Label(
                card,
                text=title if len(title) < 20 else title[:17] + "...",
                font=("Helvetica", 14, "bold"),
                bg=self.colors['bg_primary'],
                fg=self.colors['text_primary'],
                anchor="w",
                padx=10,
                pady=5
            )
            note_title.pack(fill="x")
            
            # Add date
            note_date = tk.Label(
                card,
                text=f"Last edited: {formatted_date}",
                font=("Helvetica", 10),
                bg=self.colors['bg_primary'],
                fg=self.colors['text_secondary'],
                anchor="w",
                padx=10,
                pady=5
            )
            note_date.pack(fill="x")
            
            # Add open button
            open_btn = tk.Button(
                card,
                text="Open",
                bg=self.colors['button_secondary'],
                fg=self.colors['text_primary'],
                font=("Helvetica", 10),
                relief="flat",
                padx=10,
                pady=5,
                command=lambda id=note_id, t=title: self.open_note_in_tab(id, t)
            )
            open_btn.pack(pady=10)
            
            # Update grid position
            col += 1
            if col > 2:  # 3 cards per row
                col = 0
                row += 1
                
        # Configure grid weights for responsiveness
        for i in range(3):
            self.recent_grid.columnconfigure(i, weight=1)
        for i in range(2):
            self.recent_grid.rowconfigure(i, weight=1)
            
    def new_note(self):
        self.current_note_id = None
        self.text_area.delete(1.0, tk.END)
        self.images_data = {}  # Clear image data
        self.image_counter = 0
        self.formatting_data = {}  # Clear formatting data
        
        # Reset current formatting
        self.current_format = {
            'bold': False,
            'italic': False,
            'underline': False,
            'font_size': self.settings['font_size'],
            'font_family': self.settings['font_family']
        }
        
        # Update formatting buttons
        self.bold_button.configure(bg=self.colors['button_secondary'])
        self.italic_button.configure(bg=self.colors['button_secondary'])
        self.underline_button.configure(bg=self.colors['button_secondary'])
        self.font_size_combo.set(self.current_format['font_size'])
        self.font_family_combo.set(self.current_format['font_family'])
        
        self.show_editor_page()
        self.animate_status_bar("New note created")
        
        # Add a new tab for the unsaved note
        self.add_tab(None, "Untitled")

    def save_note(self):
        content = self.text_area.get(1.0, tk.END)

        if not content.strip():
            self.animate_status_bar("Error: Note must have content")
            return
            
        # Prompt for title
        title = simpledialog.askstring("Save Note", "Enter a title for your note:", 
                                      parent=self.root)
        
        if not title:
            self.animate_status_bar("Error: Note must have a title")
            return

        # Save formatting information
        self.save_formatting_data()

        if self.current_note_id is None:
            save_note_to_db(title, content, self.images_data, self.formatting_data)
            # Get the new note ID (last inserted row)
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('SELECT last_insert_rowid()')
            new_id = c.fetchone()[0]
            conn.close()
            
            self.current_note_id = new_id
            
            # Update the tab with the new title and ID
            if self.active_tab is None:
                self.add_tab(new_id, title)
            else:
                # Update the existing tab
                self.close_tab(self.active_tab)
                self.add_tab(new_id, title)
            
            self.animate_status_bar(f"Note '{title}' saved successfully")
        else:
            update_note_in_db(self.current_note_id, title, content, self.images_data, self.formatting_data)
            
            # Update the tab title if it exists
            if self.current_note_id in self.tab_references:
                self.tab_references[self.current_note_id]['button'].configure(text=title)
                
                # Update in open_notes list
                self.open_notes = [(id, title if id == self.current_note_id else t) for id, t in self.open_notes]
            
            self.animate_status_bar(f"Note '{title}' updated successfully")
                
        # Show success message
        messagebox.showinfo("Success", f"Note '{title}' saved successfully")
    
    def save_formatting_data(self):
        # Get all formatting tags and their ranges
        self.formatting_data = {
            "bold": [],
            "italic": [],
            "underline": [],
            "font_size": {},
            "font_family": {}
        }
        
        # Save bold formatting
        bold_ranges = self.text_area.tag_ranges("bold")
        for i in range(0, len(bold_ranges), 2):
            start = bold_ranges[i]
            end = bold_ranges[i+1]
            self.formatting_data["bold"].append((str(start), str(end)))
        
        # Save italic formatting
        italic_ranges = self.text_area.tag_ranges("italic")
        for i in range(0, len(italic_ranges), 2):
            start = italic_ranges[i]
            end = italic_ranges[i+1]
            self.formatting_data["italic"].append((str(start), str(end)))
        
        # Save underline formatting
        underline_ranges = self.text_area.tag_ranges("underline")
        for i in range(0, len(underline_ranges), 2):
            start = underline_ranges[i]
            end = underline_ranges[i+1]
            self.formatting_data["underline"].append((str(start), str(end)))
        
        # Save font size formatting
        for size in [8, 10, 12, 14, 16, 18, 20, 24]:
            tag_name = f"size_{size}"
            size_ranges = self.text_area.tag_ranges(tag_name)
            for i in range(0, len(size_ranges), 2):
                start = size_ranges[i]
                end = size_ranges[i+1]
                if str(size) not in self.formatting_data["font_size"]:
                    self.formatting_data["font_size"][str(size)] = []
                self.formatting_data["font_size"][str(size)].append((str(start), str(end)))
        
        # Save font family formatting
        # Get all available font families
        available_fonts = font.families()
        for family in available_fonts:
            tag_name = f"family_{family}"
            family_ranges = self.text_area.tag_ranges(tag_name)
            for i in range(0, len(family_ranges), 2):
                start = family_ranges[i]
                end = family_ranges[i+1]
                if family not in self.formatting_data["font_family"]:
                    self.formatting_data["font_family"][family] = []
                self.formatting_data["font_family"][family].append((str(start), str(end)))

    def open_note_dialog(self):
        # Create a dialog to select a note
        dialog = tk.Toplevel(self.root)
        dialog.title("Open Note")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create a frame for the dialog content
        dialog_frame = tk.Frame(dialog, bg=self.colors['bg_primary'], padx=20, pady=20)
        dialog_frame.pack(fill="both", expand=True)
        
        # Add a title
        title_label = tk.Label(
            dialog_frame,
            text="Select a Note to Open",
            font=("Helvetica", 16, "bold"),
            bg=self.colors['bg_primary'],
            fg=self.colors['text_primary']
        )
        title_label.pack(pady=(0, 20))
        
        # Create a listbox for notes
        notes_frame = tk.Frame(dialog_frame, bg=self.colors['bg_primary'])
        notes_frame.pack(fill="both", expand=True)
        
        notes_listbox = tk.Listbox(
            notes_frame,
            font=("Helvetica", 12),
            bg=self.colors['bg_primary'],
            fg=self.colors['text_primary'],
            selectbackground=self.colors['bg_tertiary'],
            selectforeground=self.colors['text_primary'],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors['frame_border']
        )
        notes_listbox.pack(side="left", fill="both", expand=True)
        
        # Add scrollbar
        notes_scrollbar = ttk.Scrollbar(
            notes_frame,
            command=notes_listbox.yview
        )
        notes_listbox.config(yscrollcommand=notes_scrollbar.set)
        notes_scrollbar.pack(side="right", fill="y")
        
        # Populate the listbox with notes
        notes = get_notes_from_db()
        for note in notes:
            notes_listbox.insert(tk.END, note[1])
        
        # Add buttons
        button_frame = tk.Frame(dialog_frame, bg=self.colors['bg_primary'])
        button_frame.pack(fill="x", pady=(20, 0))
        
        cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            bg=self.colors['button_secondary'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 10),
            relief="flat",
            padx=10,
            pady=5,
            command=dialog.destroy
        )
        cancel_button.pack(side="right", padx=5)
        
        open_button = tk.Button(
            button_frame,
            text="Open",
            bg=self.colors['button_primary'],
            fg=self.colors['text_primary'],
            font=("Helvetica", 10),
            relief="flat",
            padx=10,
            pady=5,
            command=lambda: self.open_selected_note(notes_listbox, notes, dialog)
        )
        open_button.pack(side="right", padx=5)
        
        # Double-click to open
        notes_listbox.bind("<Double-1>", lambda e: self.open_selected_note(notes_listbox, notes, dialog))
        
        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        dialog.geometry(f"+{x}+{y}")
        
        # Show the dialog
        self.show_editor_page()
        
    def open_selected_note(self, listbox, notes, dialog):
        if not listbox.curselection():
            return
            
        note_index = listbox.curselection()[0]
        note = notes[note_index]
        note_id = note[0]
        note_title = note[1]
        
        # Open the note in a tab
        self.open_note_in_tab(note_id, note_title)
        
        # Close the dialog
        dialog.destroy()

    def open_note_in_tab(self, note_id, title):
        # Add a tab for this note
        self.add_tab(note_id, title)
        self.show_editor_page()

    def open_note_by_id(self, note_id):
        self.current_note_id = note_id
        note_content = get_note_content(note_id)
        
        if note_content:
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(1.0, note_content[1])
            
            # Reset current formatting
            self.current_format = {
                'bold': False,
                'italic': False,
                'underline': False,
                'font_size': self.settings['font_size'],
                'font_family': self.settings['font_family']
            }
            
            # Update formatting buttons
            self.bold_button.configure(bg=self.colors['button_secondary'])
            self.italic_button.configure(bg=self.colors['button_secondary'])
            self.underline_button.configure(bg=self.colors['button_secondary'])
            self.font_size_combo.set(self.current_format['font_size'])
            self.font_family_combo.set(self.current_format['font_family'])
            
            # Load images if any
            self.images_data = {}
            self.image_counter = 0
            
            if note_content[2] and note_content[2] != "{}":
                try:
                    # Parse JSON string to dict
                    self.images_data = json.loads(note_content[2])
                    
                    # Display images in text area
                    for img_id, img_data in self.images_data.items():
                        try:
                            # Find the image placeholder in the text
                            start_idx = "1.0"
                            while True:
                                start_idx = self.text_area.search(f"[IMAGE:{img_id}]", start_idx, tk.END)
                                if not start_idx:
                                    break
                                    
                                # Calculate end index
                                end_idx = f"{start_idx}+{len(f'[IMAGE:{img_id}]')}c"
                                
                                # Delete the placeholder
                                self.text_area.delete(start_idx, end_idx)
                                
                                # Insert the image
                                img_data_bytes = base64.b64decode(img_data)
                                img = Image.open(io.BytesIO(img_data_bytes))
                                # Resize if too large
                                if img.width > 500:
                                    ratio = 500 / img.width
                                    img = img.resize((500, int(img.height * ratio)), Image.LANCZOS)
                                photo = ImageTk.PhotoImage(img)
                                
                                # Store the image to prevent garbage collection
                                if not hasattr(self, 'image_references'):
                                    self.image_references = {}
                                self.image_references[img_id] = photo
                                
                                # Insert the image
                                self.text_area.image_create(start_idx, image=photo)
                                
                                # Move to next position
                                start_idx = end_idx
                        except Exception as e:
                            print(f"Error displaying image {img_id}: {e}")
                    
                    # Update image counter
                    if self.images_data:
                        self.image_counter = max([int(k) for k in self.images_data.keys() if k.isdigit()], default=0) + 1
                except Exception as e:
                    print(f"Error parsing images data: {e}")
            
            # Load formatting if any
            self.formatting_data = {}
            if note_content[3] and note_content[3] != "{}":
                try:
                    # Parse JSON string to dict
                    self.formatting_data = json.loads(note_content[3])
                    
                    # Apply bold formatting
                    for start, end in self.formatting_data.get("bold", []):
                        self.text_area.tag_add("bold", start, end)
                    
                    # Apply italic formatting
                    for start, end in self.formatting_data.get("italic", []):
                        self.text_area.tag_add("italic", start, end)
                    
                    # Apply underline formatting
                    for start, end in self.formatting_data.get("underline", []):
                        self.text_area.tag_add("underline", start, end)
                    
                    # Apply font size formatting
                    for size, ranges in self.formatting_data.get("font_size", {}).items():
                        tag_name = f"size_{size}"
                        self.text_area.tag_configure(tag_name, font=(self.current_format['font_family'], int(size)))
                        for start, end in ranges:
                            self.text_area.tag_add(tag_name, start, end)
                    
                    # Apply font family formatting
                    for family, ranges in self.formatting_data.get("font_family", {}).items():
                        tag_name = f"family_{family}"
                        self.text_area.tag_configure(tag_name, font=(family, self.current_format['font_size']))
                        for start, end in ranges:
                            self.text_area.tag_add(tag_name, start, end)
                except Exception as e:
                    print(f"Error applying formatting: {e}")
            
            self.animate_status_bar(f"Opened note: {note_content[0]}")
            
    def delete_note(self):
        if self.current_note_id is None:
            self.animate_status_bar("No note is currently open")
            return
            
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this note?"):
            note_content = get_note_content(self.current_note_id)
            if note_content:
                delete_note_from_db(self.current_note_id)
                self.animate_status_bar(f"Note '{note_content[0]}' deleted")
                
                # Close the tab
                self.close_tab(self.current_note_id)
                
                # Clear the editor if this was the active note
                if self.active_tab is None:
                    self.current_note_id = None
                    self.text_area.delete(1.0, tk.END)
                    self.images_data = {}
                    self.image_counter = 0
                    self.formatting_data = {}
                
                # Show delete message
                messagebox.showinfo("Success", f"Note '{note_content[0]}' deleted successfully")

    def toggle_bold(self, event=None):
        try:
            # Toggle the current format state
            self.current_format['bold'] = not self.current_format['bold']
            
            # Update button appearance
            if self.current_format['bold']:
                self.bold_button.configure(bg=self.colors['button_primary'])
            else:
                self.bold_button.configure(bg=self.colors['button_secondary'])
            
            # Check if text is selected
            try:
                sel_start = self.text_area.index("sel.first")
                sel_end = self.text_area.index("sel.last")
                has_selection = True
            except tk.TclError:
                # No selection, use current insert position
                has_selection = False
                sel_start = self.text_area.index("insert")
                sel_end = self.text_area.index("insert + 1c")
                has_selection = False
            
            # Apply or remove formatting based on current state
            if self.current_format['bold']:
                self.text_area.tag_add("bold", sel_start, sel_end)
            else:
                self.text_area.tag_remove("bold", sel_start, sel_end)
                
        except Exception as e:
            print(f"Error in toggle_bold: {e}")
        
        return "break"  # Prevent default behavior

    def toggle_italic(self, event=None):
        try:
            # Toggle the current format state
            self.current_format['italic'] = not self.current_format['italic']
            
            # Update button appearance
            if self.current_format['italic']:
                self.italic_button.configure(bg=self.colors['button_primary'])
            else:
                self.italic_button.configure(bg=self.colors['button_secondary'])
            
            # Check if text is selected
            try:
                sel_start = self.text_area.index("sel.first")
                sel_end = self.text_area.index("sel.last")
                has_selection = True
            except tk.TclError:
                # No selection, use current insert position
                has_selection = False
                sel_start = self.text_area.index("insert")
                sel_end = self.text_area.index("insert + 1c")
            
            # Apply or remove formatting based on current state
            if self.current_format['italic']:
                self.text_area.tag_add("italic", sel_start, sel_end)
            else:
                self.text_area.tag_remove("italic", sel_start, sel_end)
                
        except Exception as e:
            print(f"Error in toggle_italic: {e}")
        
        return "break"  # Prevent default behavior

    def toggle_underline(self, event=None):
        try:
            # Toggle the current format state
            self.current_format['underline'] = not self.current_format['underline']
            
            # Update button appearance
            if self.current_format['underline']:
                self.underline_button.configure(bg=self.colors['button_primary'])
            else:
                self.underline_button.configure(bg=self.colors['button_secondary'])
            
            # Check if text is selected
            try:
                sel_start = self.text_area.index("sel.first")
                sel_end = self.text_area.index("sel.last")
                has_selection = True
            except tk.TclError:
                # No selection, use current insert position
                has_selection = False
                sel_start = self.text_area.index("insert")
                sel_end = self.text_area.index("insert + 1c")
            
            # Apply or remove formatting based on current state
            if self.current_format['underline']:
                self.text_area.tag_add("underline", sel_start, sel_end)
            else:
                self.text_area.tag_remove("underline", sel_start, sel_end)
                
        except Exception as e:
            print(f"Error in toggle_underline: {e}")
        
        return "break"  # Prevent default behavior

    def change_font_size(self, event=None):
        try:
            # Get the selected font size
            try:
                font_size = int(self.font_size_combo.get())
            except ValueError:
                self.animate_status_bar("Please enter a valid number for font size")
                return
            
            # Update current format state
            self.current_format['font_size'] = font_size
            
            # Check if text is selected
            try:
                sel_start = self.text_area.index("sel.first")
                sel_end = self.text_area.index("sel.last")
                has_selection = True
            except tk.TclError:
                # No selection, change default font size
                has_selection = False
                
                # Change the default font size for the text area
                current_font = font.nametofont(self.text_area["font"])
                new_font = font.Font(family=current_font.cget("family"), size=font_size)
                self.text_area.configure(font=new_font)
                
                # Update all formatting tags with the new base font size
                self.text_area.tag_configure("bold", font=(current_font.cget("family"), font_size, "bold"))
                self.text_area.tag_configure("italic", font=(current_font.cget("family"), font_size, "italic"))
                self.text_area.tag_configure("underline", font=(current_font.cget("family"), font_size, "underline"))
                self.text_area.tag_configure("bold-italic", font=(current_font.cget("family"), font_size, "bold italic"))
                self.text_area.tag_configure("bold-underline", font=(current_font.cget("family"), font_size, "bold underline"))
                self.text_area.tag_configure("italic-underline", font=(current_font.cget("family"), font_size, "italic underline"))
                self.text_area.tag_configure("bold-italic-underline", font=(current_font.cget("family"), font_size, "bold italic underline"))
                
                # Update settings
                self.settings['font_size'] = font_size
                save_settings(self.settings)
                
                self.animate_status_bar(f"Default font size changed to {font_size}")
                return
            
            # If there's a selection, apply the font size to the selected text
            if has_selection:
                # Remove any existing font size tags from the selection
                for size in [8, 10, 12, 14, 16, 18, 20, 24]:
                    tag_name = f"size_{size}"
                    self.text_area.tag_remove(tag_name, sel_start, sel_end)
                
                # Create a new tag for this font size
                tag_name = f"size_{font_size}"
                
                # Get the current font family from the selection or use default
                current_family = self.current_format['font_family']
                for tag in self.text_area.tag_names(sel_start):
                    if tag.startswith("family_"):
                        current_family = tag[7:]  # Remove "family_" prefix
                        break
                
                # Configure the tag with the selected font size and current family
                self.text_area.tag_configure(tag_name, font=(current_family, font_size))
                
                # Apply the tag to the selected text
                self.text_area.tag_add(tag_name, sel_start, sel_end)
            
            # Update status bar
            self.animate_status_bar(f"Font size changed to {font_size}")
            
        except Exception as e:
            print(f"Error in change_font_size: {e}")

    def change_font_family(self, event=None):
        try:
            # Get the selected font family
            font_family = self.font_family_combo.get()
            
            # Update current format state
            self.current_format['font_family'] = font_family
            
            # Check if text is selected
            try:
                sel_start = self.text_area.index("sel.first")
                sel_end = self.text_area.index("sel.last")
                has_selection = True
            except tk.TclError:
                # No selection, change default font family
                has_selection = False
                
                # Change the default font family for the text area
                current_font = font.nametofont(self.text_area["font"])
                new_font = font.Font(family=font_family, size=current_font.cget("size"))
                self.text_area.configure(font=new_font)
                
                # Update all formatting tags with the new base font family
                self.text_area.tag_configure("bold", font=(font_family, current_font.cget("size"), "bold"))
                self.text_area.tag_configure("italic", font=(font_family, current_font.cget("size"), "italic"))
                self.text_area.tag_configure("underline", font=(font_family, current_font.cget("size"), "underline"))
                self.text_area.tag_configure("bold-italic", font=(font_family, current_font.cget("size"), "bold italic"))
                self.text_area.tag_configure("bold-underline", font=(font_family, current_font.cget("size"), "bold underline"))
                self.text_area.tag_configure("italic-underline", font=(font_family, current_font.cget("size"), "italic underline"))
                self.text_area.tag_configure("bold-italic-underline", font=(font_family, current_font.cget("size"), "bold italic underline"))
                
                # Update settings
                self.settings['font_family'] = font_family
                save_settings(self.settings)
                
                self.animate_status_bar(f"Default font changed to {font_family}")
                return
            
            # If there's a selection, apply the font family to the selected text
            if has_selection:
                # Remove any existing font family tags from the selection
                for tag in list(self.text_area.tag_names(sel_start)):
                    if tag.startswith("family_"):
                        self.text_area.tag_remove(tag, sel_start, sel_end)
                
                # Create a new tag for this font family
                tag_name = f"family_{font_family}"
                
                # Get the current font size from the selection or use default
                current_size = self.current_format['font_size']
                for tag in self.text_area.tag_names(sel_start):
                    if tag.startswith("size_"):
                        try:
                            current_size = int(tag[5:])  # Remove "size_" prefix
                        except ValueError:
                            pass
                        break
                
                # Configure the tag with the selected font family and current size
                self.text_area.tag_configure(tag_name, font=(font_family, current_size))
                
                # Apply the tag to the selected text
                self.text_area.tag_add(tag_name, sel_start, sel_end)
            
            # Update status bar
            self.animate_status_bar(f"Font changed to {font_family}")
            
        except Exception as e:
            print(f"Error in change_font_family: {e}")
            
    def insert_image(self):
        # Open file dialog to select an image
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        
        if file_path:
            try:
                # Open and resize the image if needed
                img = Image.open(file_path)
                
                # Resize if too large
                if img.width > 500:
                    ratio = 500 / img.width
                    img = img.resize((500, int(img.height * ratio)), Image.LANCZOS)
                
                # Convert image to PhotoImage for display
                photo = ImageTk.PhotoImage(img)
                
                # Store the image to prevent garbage collection
                if not hasattr(self, 'image_references'):
                    self.image_references = {}
                
                # Generate a unique ID for this image
                img_id = str(self.image_counter)
                self.image_counter += 1
                
                # Store the reference
                self.image_references[img_id] = photo
                
                # Insert the image at the current cursor position
                current_position = self.text_area.index(tk.INSERT)
                self.text_area.image_create(current_position, image=photo)
                
                # Store the image data in base64 format
                with open(file_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    self.images_data[img_id] = img_data
                
                # Insert a hidden marker for the image position
                # This will be used when saving/loading the note
                self.text_area.insert(current_position, f"[IMAGE:{img_id}]")
                self.text_area.delete(current_position, f"{current_position}+{len(f'[IMAGE:{img_id}]')}c")
                
                self.animate_status_bar(f"Image inserted successfully")
                
            except Exception as e:
                print(f"Error inserting image: {e}")
        
    def on_window_resize(self, event=None):
        # Only respond to the root window's resize events
        if event and event.widget == self.root:
            # Update the layout for responsiveness
            if hasattr(self, 'recent_grid') and self.homepage_frame.winfo_ismapped():
                self.update_recent_notes()
            
            # Update the tab canvas scrollregion
            if hasattr(self, 'tab_canvas'):
                self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox("all"))

    def paste_from_clipboard(self, event=None):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                if img.width > 500:
                    ratio = 500 / img.width
                    img = img.resize((500, int(img.height * ratio)), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                # Insert image
                current_position = self.text_area.index(tk.INSERT)
                img_id = str(self.image_counter)
                self.image_counter += 1

                if not hasattr(self, 'image_references'):
                    self.image_references = {}
                self.image_references[img_id] = photo

                self.text_area.image_create(current_position, image=photo)
                self.text_area.insert(current_position, f"[IMAGE:{img_id}]")
                self.text_area.delete(current_position, f"{current_position}+{len(f'[IMAGE:{img_id}]')}c")

                # Store base64 image data
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                self.images_data[img_id] = img_data

                self.animate_status_bar("Image pasted from clipboard")
            else:
                # fallback to text
                text = self.root.clipboard_get()
                self.text_area.insert(tk.INSERT, text)
        except Exception as e:
            print(f"Paste error: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    root.configure(bg="#1a1a2e")  # Set background color for the root window
    app = NotesApp(root)
    
    # Make the window responsive to resizing
    def on_resize(event):
        if event.widget == root:
            app.on_window_resize(event)
    
    root.bind("<Configure>", on_resize)
    
    # Set window icon
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            icon = ImageTk.PhotoImage(file=icon_path)
            root.iconphoto(True, icon)
    except Exception as e:
        print(f"Error setting icon: {e}")
    
    root.mainloop()
