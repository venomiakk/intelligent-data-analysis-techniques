import json
from tkinter import *
from tkinter import filedialog as fd, filedialog
from tkinter import ttk
from tkinter.messagebox import showinfo

from Converter import Converter


class Interface:
    def __init__(self):
        self.file_path = ""
        self.converter = Converter()
        window = Tk()
        window.title("Excel to Word/PDF Converter")
        window.geometry('600x400')
        self.create_widgets(window)
        window.mainloop()

    def create_widgets(self, window):
        Label(window, text="Wybierz plik excel aby go przekonwertowac").grid(column=0, row=0)
        Label(window, text="Wybierz format na jaki chcesz przekonwertowac plik").grid(column=0, row=1)
        Label(window, text="Podaj wielkość znaków").grid(column=0, row=2)
        self.font_size = Entry(window, width=10)
        self.font_size.grid(column=1, row=2)
        Label(window, text="Podaj odstęp linii").grid(column=0, row=3)
        self.interval = Entry(window, width=10)
        self.interval.grid(column=1, row=3)
        Label(window, text="Czy chcesz wyswietlac kolumny bez nazwy?").grid(column=0, row=4)
        self.chk_state = BooleanVar()
        self.chk_state.set(True)
        Checkbutton(window, text='Tak/Nie', var=self.chk_state).grid(column=1, row=4)
        Label(window, text="Podaj tytuł dokumentu").grid(column=0, row=6)
        self.title = Entry(window, width=30)
        self.title.grid(column=1, row=6)


        self.combo = ttk.Combobox(window)
        self.combo['values'] = ("docx", "pdf")
        self.combo.current(1)
        self.combo.grid(column=1, row=1)
        Button(window, text='Open', command=self.choose_file).grid(column=1, row=0)
        Button(window, text='Save Settings', command=self.save_settings).grid(column=0, row=5)
        Button(window, text='Load Settings', command=self.load_settings).grid(column=1, row=5)
        Button(window, text='Save', command=self.save_file).grid(column=1, row=8)

    def choose_file(self):
        self.file_path = filedialog.askopenfilename(title="Select file")
        self.converter.path = self.file_path

    def save_settings(self):
        settings = {
            'font_size': self.font_size.get(),
            'interval': self.interval.get(),
            'number_pages': self.chk_state.get(),
            'title': self.title.get(),
            'format': self.combo.get(),
            'num_of_col': self.num_of_col.get()
        }
        with open('settings.json', 'w') as file:
            json.dump(settings, file)

    def load_settings(self):
        with open('settings.json', 'r') as file:
            settings = json.load(file)
        self.font_size.insert(0, settings['font_size'])
        self.interval.insert(0, settings['interval'])
        self.chk_state.set(settings['number_pages'])
        self.title.insert(0, settings['title'])
        self.combo.set(settings['format'])

    def save_file(self):
        files = [('Selected type', '*.' + self.combo.get())]
        save_path = filedialog.asksaveasfilename(filetypes=files)
        if self.file_path:
            num_of_col = int(self.num_of_col.get())
            font_size = int(self.font_size.get())
            interval = int(self.interval.get())
            title = self.title.get()
            include_unnamed = self.chk_state.get()
            if self.combo.get() == "pdf":
                self.converter.convert_into_pdf(font_size=font_size, interval=interval,
                                                title=title, file_name=save_path + "." + self.combo.get(),
                                                include_unnamed=include_unnamed)
            else:
                self.converter.convert_into_word(title=title, font_size=font_size,
                                                 file_name=save_path + "." + self.combo.get(),
                                                 include_unnamed=include_unnamed)