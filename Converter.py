import pandas as pd
from docx.shared import Pt
from fpdf import FPDF
from docx import Document

class Converter:
    def __init__(self, path=""):
        self.path = path
        self.columns = []

    def open_file(self):
        df = pd.read_excel(self.path)
        return df

    def adjust_columns(self):
        df = self.open_file()
        self.columns = df.columns.to_list()
        return df

    def remove_empty_lines(self, text):
        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip() != '']
        return '\n'.join(non_empty_lines)

    def convert_into_pdf(self, font_size=10, interval=20, title="", file_name="mygfg.pdf", include_unnamed=True):
        df = self.adjust_columns()
        pdf = FPDF()
        pdf.set_font("Arial", size=font_size)
        pdf.add_page()
        pdf.set_font("Arial", size=font_size + 4)  # Slightly larger font for the title
        pdf.cell(0, 10, title, ln=True, align='C')
        pdf.set_font("Arial", size=font_size)  # Reset font size

        for index, row in df.iterrows():
            for col, value in row.items():
                if not include_unnamed and "Unnamed" in col:
                    continue
                if "Name" in str(col):
                    pdf.add_page()
                pdf.set_font("Arial", 'B', size=font_size)  # Bold font for column names
                pdf.cell(50, interval, f"{col}: ", ln=False)
                pdf.set_font("Arial", size=font_size)  # Regular font for other text
                pdf.multi_cell(0, interval, str(value).encode('utf-8').decode('latin-1'))
        pdf.output(file_name)

    def convert_into_word(self, font_size=10, title="", file_name="TextToWord.docx", include_unnamed=True):
        df = self.adjust_columns()
        doc = Document()
        doc.add_heading(title, level=1)
        first_page = True

        for index, row in df.iterrows():
            for col, value in row.items():
                if not include_unnamed and "Unnamed" in col:
                    continue
                if "Name" in str(col) and not first_page:
                    doc.add_page_break()
                first_page = False
                paragraph = doc.add_paragraph()
                run = paragraph.add_run(f"{col}: ")
                run.bold = True  # Bold font for column names
                run.font.size = Pt(font_size)
                run = paragraph.add_run(str(value))
                run.font.size = Pt(font_size)
        doc.save(file_name)