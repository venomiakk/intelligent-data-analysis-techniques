import json
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox, QLineEdit, QListWidget, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from Converter import Converter

class Interface(QWidget):
    def __init__(self):
        super().__init__()
        self.file_path = ""
        self.converter = Converter()
        self.settings_file = "settings.json"
        self.initUI()
        self.load_settings()

    def initUI(self):
        self.setWindowTitle("Excel to Word/PDF Converter")
        self.setGeometry(100, 100, 450, 600)
        layout = QVBoxLayout()

        # File selection
        layout.addWidget(QLabel("Wybierz plik excel aby go przekonwertowac"))
        self.file_button = QPushButton('Open')
        self.file_button.clicked.connect(self.choose_file)
        layout.addWidget(self.file_button)

        # Format selection
        layout.addWidget(QLabel("Wybierz format na jaki chcesz przekonwertowac plik"))
        self.combo = QComboBox()
        self.combo.addItems(["docx", "pdf"])
        layout.addWidget(self.combo)

        # Font size and line interval
        layout.addWidget(QLabel("Podaj wielkość znaków"))
        self.font_size = QLineEdit()
        layout.addWidget(self.font_size)
        layout.addWidget(QLabel("Podaj odstęp linii"))
        self.interval = QLineEdit()
        layout.addWidget(self.interval)

        # Title option
        self.title_chk_state = QCheckBox("Czy chcesz dodać tytuł?")
        self.title_chk_state.stateChanged.connect(self.toggle_title_entry)
        layout.addWidget(self.title_chk_state)
        self.title_label = QLabel("Podaj tytuł dokumentu")
        self.title = QLineEdit()
        layout.addWidget(self.title_label)
        layout.addWidget(self.title)
        self.title_label.hide()
        self.title.hide()

        # Title page option
        self.title_page_chk_state = QCheckBox("Czy chcesz stronę tytułową?")
        layout.addWidget(self.title_page_chk_state)

        # Description option
        self.description_chk_state = QCheckBox("Czy chcesz opis?")
        self.description_chk_state.stateChanged.connect(self.toggle_description_entry)
        layout.addWidget(self.description_chk_state)
        self.description_label = QLabel("Podaj opis dokumentu")
        self.description = QLineEdit()
        layout.addWidget(self.description_label)
        layout.addWidget(self.description)
        self.description_label.hide()
        self.description.hide()

        # Column selection
        layout.addWidget(QLabel("Wybierz kolumny do uwzględnienia:"))
        self.column_listbox = QListWidget()
        self.column_listbox.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.column_listbox)

        # Single line option
        layout.addWidget(QLabel("Czy tytuł kolumny i jej zawartość mają być w jednym wierszu?"))
        self.single_line = QCheckBox('Tak/Nie')
        layout.addWidget(self.single_line)

        # Add page numbering option before text alignment
        layout.addWidget(QLabel("Czy chcesz numerowanie stron?"))
        self.page_numbering = QCheckBox('Tak/Nie')
        layout.addWidget(self.page_numbering)
        
        # Text alignment
        layout.addWidget(QLabel("Wybierz wyrównanie tekstu:"))
        self.alignment = QComboBox()
        self.alignment.addItems(["left", "center", "right"])
        layout.addWidget(self.alignment)

        # Save button
        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(self.save_file)
        layout.addWidget(self.save_button)

        # Save settings button
        self.save_settings_button = QPushButton('Save Settings')
        self.save_settings_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_settings_button)

        # Load settings button
        self.load_settings_button = QPushButton('Load Settings')
        self.load_settings_button.clicked.connect(self.load_settings)
        layout.addWidget(self.load_settings_button)

        self.setLayout(layout)
        self.show()

    def choose_file(self):
        options = QFileDialog.Options()
        self.file_path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if self.file_path:
            self.converter.path = self.file_path
            df = self.converter.open_file()
            self.column_listbox.clear()
            self.column_listbox.addItems(df.columns)
            for i in range(self.column_listbox.count()):
                self.column_listbox.item(i).setSelected(True)

    def toggle_title_entry(self):
        if self.title_chk_state.isChecked():
            self.title_label.show()
            self.title.show()
        else:
            self.title_label.hide()
            self.title.hide()

    def toggle_description_entry(self):
        if self.description_chk_state.isChecked():
            self.description_label.show()
            self.description.show()
        else:
            self.description_label.hide()
            self.description.hide()

    def save_file(self):
        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(self, "Save file", "", f"{self.combo.currentText().upper()} Files (*.{self.combo.currentText()});;All Files (*)", options=options)
        if self.file_path and save_path:
            font_size = int(self.font_size.text())
            interval = int(self.interval.text())
            title = self.title.text() if self.title_chk_state.isChecked() else ""
            add_title_page = self.title_page_chk_state.isChecked()
            description = self.description.text() if self.description_chk_state.isChecked() else ""
            selected_columns = [item.text() for item in self.column_listbox.selectedItems()]
            single_line = self.single_line.isChecked()
            alignment = self.alignment.currentText()
            enable_page_numbers = self.page_numbering.isChecked()
            
            if self.combo.currentText() == "pdf":
                self.converter.convert_into_pdf(font_size=font_size, interval=interval,
                                                title=title, file_name=save_path,
                                                selected_columns=selected_columns, single_line=single_line,
                                                alignment=alignment, add_title_page=add_title_page,
                                                description=description, enable_page_numbers=enable_page_numbers)
            else:
                self.converter.convert_into_word(title=title, font_size=font_size,
                                                 file_name=save_path,
                                                 selected_columns=selected_columns, line_spacing=interval,
                                                 single_line=single_line, alignment=alignment,
                                                 add_title_page=add_title_page, description=description, 
                                                 enable_page_numbers=enable_page_numbers)

    def save_settings(self):
        settings = {
            "font_size": self.font_size.text(),
            "interval": self.interval.text(),
            "title_chk_state": self.title_chk_state.isChecked(),
            "title": self.title.text(),
            "title_page_chk_state": self.title_page_chk_state.isChecked(),
            "description_chk_state": self.description_chk_state.isChecked(),
            "description": self.description.text(),
            "single_line": self.single_line.isChecked(),
            "alignment": self.alignment.currentText(),
            "format": self.combo.currentText(),
            "page_numbering": self.page_numbering.isChecked()  # Add page numbering to settings
        }
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f)

    def load_settings(self):
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                self.font_size.setText(settings.get("font_size", ""))
                self.interval.setText(settings.get("interval", ""))
                self.title_chk_state.setChecked(settings.get("title_chk_state", False))
                self.title.setText(settings.get("title", ""))
                self.title_page_chk_state.setChecked(settings.get("title_page_chk_state", False))
                self.description_chk_state.setChecked(settings.get("description_chk_state", False))
                self.description.setText(settings.get("description", ""))
                self.single_line.setChecked(settings.get("single_line", False))
                self.alignment.setCurrentText(settings.get("alignment", "left"))
                self.combo.setCurrentText(settings.get("format", "docx"))
                self.page_numbering.setChecked(settings.get("page_numbering", False))

        except FileNotFoundError:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Interface()
    sys.exit(app.exec_())