from tkinter import *
from tkinter import filedialog as fd
from tkinter import ttk, filedialog
from tkinter.messagebox import showinfo
from tkinter.ttk import Combobox
from Converter import Converter

class Interface:

    def __init__(self):
        window = Tk()
        window.title("excel into word/pdf converter")
        window.geometry('1290x720')
        lbl = Label(window, text="Wybierz plik excel aby go przekonwertowac")
        lbl.grid(column=0, row=0)
        lbl = Label(window, text="Wybierz format na jaki chcesz przekonwertowac plik")
        lbl.grid(column=0, row=1)
        self.combo = Combobox(window)
        self.combo['values'] = ("docx", "pdf")
        self.combo.current(1)  # set the selected item
        self.combo.grid(column=1, row=1)
        btn = Button(window, text='open', command=self.chooseFile)
        btn.grid(column=1, row=0)
        btn1 = Button(window, text='save', command=self.saveFile)
        btn1.grid(column=1, row=2)
        window.mainloop()


    def chooseFile(self):
        self.file_path = filedialog.askopenfilename(title="Select file")
    def getFilepast(self):
        # open dialog box to select file
        self.pathpast = filedialog.askopenfilename(initialdir="/", title="Select file")

    def saveFile(self):
        files = [('wybrany typ', '*.'+self.combo.get())]
        save_path = filedialog.asksaveasfilename(filetypes=files)
        if self.file_path:
            if self.combo.get() == "pdf":
                pdf = Converter(self.file_path)
                pdf.convertIntoPdf(file_name=save_path+"."+str(self.combo.get()))
            else:
                pdf = Converter(self.file_path)
                pdf.convertIntoWord(file_name=save_path+"."+str(self.combo.get()))



