import json
from tkinter import *
from tkinter import filedialog as fd, filedialog
from tkinter import ttk
from tkinter.messagebox import showinfo

from Converter import Converter


class Interface:
    def __init__(self):
        self.chk_state = None
        self.file_path = ""
        self.converter = Converter()
        window = Tk()
        window.title("Excel to Word/PDF Converter")
        self.create_widgets(window)
        window.mainloop()

    def create_widgets(self, window):
        window.geometry("450x600")

        # Frame for file selection
        file_frame = Frame(window)
        file_frame.grid(column=0, row=0, columnspan=2, pady=10)
        Label(file_frame, text="Wybierz plik excel aby go przekonwertowac").grid(column=0, row=0)
        Button(file_frame, text='Open', command=self.choose_file).grid(column=1, row=0)

        # Frame for format selection
        format_frame = Frame(window)
        format_frame.grid(column=0, row=1, columnspan=2, pady=10)
        Label(format_frame, text="Wybierz format na jaki chcesz przekonwertowac plik").grid(column=0, row=0)
        self.combo = ttk.Combobox(format_frame)
        self.combo['values'] = ("docx", "pdf")
        self.combo.current(1)
        self.combo.grid(column=1, row=0)

        # Frame for settings buttons
        settings_frame = Frame(window)
        settings_frame.grid(column=0, row=2, columnspan=2, pady=10)
        Button(settings_frame, text='Save Settings', command=self.save_settings).grid(column=0, row=0, padx=5)
        Button(settings_frame, text='Load Settings', command=self.load_settings).grid(column=1, row=0, padx=5)

        # Frame for font size and line interval
        font_frame = Frame(window)
        font_frame.grid(column=0, row=3, columnspan=2, pady=10)
        Label(font_frame, text="Podaj wielkość znaków").grid(column=0, row=0)
        self.font_size = Entry(font_frame, width=10)
        self.font_size.grid(column=1, row=0)
        Label(font_frame, text="Podaj odstęp linii").grid(column=0, row=1)
        self.interval = Entry(font_frame, width=10)
        self.interval.grid(column=1, row=1)

        # Frame for title option
        title_frame = Frame(window)
        title_frame.grid(column=0, row=4, columnspan=2, pady=10)
        self.title_chk_state = BooleanVar()
        self.title_chk_state.set(False)
        Checkbutton(title_frame, text="Czy chcesz dodać tytuł?", var=self.title_chk_state,
                    command=self.toggle_title_entry).grid(column=0, row=0)
        self.title_label = Label(title_frame, text="Podaj tytuł dokumentu")
        self.title = Entry(title_frame, width=30)

        # Frame for column selection
        column_frame = Frame(window)
        column_frame.grid(column=0, row=5, columnspan=2, pady=10)
        Label(column_frame, text="Wybierz kolumny do uwzględnienia:").grid(column=0, row=0, columnspan=2)
        self.column_listbox = Listbox(column_frame, selectmode=MULTIPLE)
        self.column_listbox.grid(column=0, row=1, columnspan=2)

        # Frame for single line option
        single_line_frame = Frame(window)
        single_line_frame.grid(column=0, row=6, columnspan=2, pady=10)
        Label(single_line_frame, text="Czy tytuł kolumny i jej zawartość mają być w jednym wierszu?").grid(column=0,
                                                                                                           row=0)
        self.single_line = BooleanVar()
        self.single_line.set(True)
        Checkbutton(single_line_frame, text='Tak/Nie', var=self.single_line).grid(column=1, row=0)

        # Frame for text alignment
        alignment_frame = Frame(window)
        alignment_frame.grid(column=0, row=7, columnspan=2, pady=10)
        Label(alignment_frame, text="Wybierz wyrównanie tekstu:").grid(column=0, row=0)
        self.alignment = ttk.Combobox(alignment_frame)
        self.alignment['values'] = ("left", "center", "right")
        self.alignment.current(0)
        self.alignment.grid(column=1, row=0)

        # Save button
        Button(window, text='Save', command=self.save_file).grid(column=0, row=8, columnspan=2, pady=10)

    def choose_file(self):
        self.file_path = filedialog.askopenfilename(title="Select file")
        self.converter.path = self.file_path
        df = self.converter.open_file()
        self.column_listbox.delete(0, END)
        for col in df.columns:
            self.column_listbox.insert(END, col)
        # Select all columns by default
        self.column_listbox.select_set(0, END)

    def toggle_title_entry(self):
        if self.title_chk_state.get():
            self.title_label.grid(column=0, row=6)
            self.title.grid(column=1, row=6)
        else:
            self.title_label.grid_remove()
            self.title.grid_remove()

    def save_settings(self):
        settings = {
            'font_size': self.font_size.get(),
            'interval': self.interval.get(),
            'title': self.title.get() if self.title_chk_state.get() else "",
            'title_chk_state': self.title_chk_state.get(),
            'format': self.combo.get(),
            'alignment': self.alignment.get(),
            'single_line': self.single_line.get()
        }
        with open('settings.json', 'w') as file:
            json.dump(settings, file)

    def load_settings(self):
        with open('settings.json', 'r') as file:
            settings = json.load(file)
        self.font_size.delete(0, END)
        self.font_size.insert(0, settings['font_size'])
        self.interval.delete(0, END)
        self.interval.insert(0, settings['interval'])
        self.title_chk_state.set(settings['title_chk_state'])
        if settings['title_chk_state']:
            self.toggle_title_entry()
            self.title.delete(0, END)
            self.title.insert(0, settings['title'])
        self.combo.set(settings['format'])
        self.alignment.set(settings['alignment'])
        self.single_line.set(settings['single_line'])

    def save_file(self):
        files = [('Selected type', '*.' + self.combo.get())]
        save_path = filedialog.asksaveasfilename(filetypes=files)
        if self.file_path:
            font_size = int(self.font_size.get())
            interval = int(self.interval.get())
            title = self.title.get() if self.title_chk_state.get() else ""
            selected_columns = [self.column_listbox.get(i) for i in self.column_listbox.curselection()]
            single_line = self.single_line.get()
            alignment = self.alignment.get()
            if self.combo.get() == "pdf":
                self.converter.convert_into_pdf(font_size=font_size, interval=interval,
                                                title=title, file_name=save_path + "." + self.combo.get(),
                                                selected_columns=selected_columns, single_line=single_line,
                                                alignment=alignment)
            else:
                self.converter.convert_into_word(title=title, font_size=font_size,
                                                 file_name=save_path + "." + self.combo.get(),
                                                 selected_columns=selected_columns, line_spacing=interval,
                                                 single_line=single_line, alignment=alignment)