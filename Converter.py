import pandas as pd
from fpdf import FPDF
from docx import Document

class Converter:
    def __init__(self, path="C:/Users/thg/Downloads/Generated(1).xlsx"):
        self.path = path
        self.columns = []

    def open_file(self):
        df = pd.read_excel(self.path)
        return df

    def adjust_columns(self, num_of_col=4):
        df = self.open_file()
        j = 0
        output = ""
        self.columns = df.columns.to_list()
        for index, row in df.iterrows():
            row = row.to_list()
            for i in range(len(row)):
                if i % num_of_col == 0:
                    output += "\n"
                output += str(self.columns[i]) + ": " + str(row[i]) + ","
                i += 1
        output = self.remove_empty_lines(output)
        output = self.insert_newline_if_needed(output)
        return output

    def remove_empty_lines(self, text):
        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip() != '']
        return '\n'.join(non_empty_lines)

    def insert_newline_if_needed(self, text, max_length=100):
        last_nl = 0
        result = ""
        for i, char in enumerate(text):
            if char == '\n':
                last_nl = 0
            else:
                last_nl += 1
            result += char
            if last_nl == max_length:
                result += '\n'
                last_nl = 0
        return result


    def convertIntoPdf(self, num_of_col=2, file_name="mygfg.pdf"):
        output = self.adjust_columns(num_of_col)
        print(output)
        pdf = FPDF()
        output_list = output.split('\n')
        for x in output_list:
            if "Name:" in x:
                pdf.add_page()
                pdf.set_font("Arial", size=10)
            pdf.cell(h=10, w=0, txt=x.encode('utf-8').decode('latin-1'), ln=1, align='L')

        pdf.output(file_name)

    def convertIntoWord(self, num_of_col=2, file_name="TextToWord.docx"):
        output = self.adjust_columns(num_of_col)
        # Create a new Document
        doc = Document()

        # Split the output into lines
        output_list = output.split('\n')
        first_page = True
        for line in output_list:
            if "Name:" in line and not first_page:
                # Add a page break
                doc.add_page_break()
            first_page = False
            # Add a paragraph with the line
            doc.add_paragraph(line)

        # Save the document
        doc.save(file_name)
        print("poszlo")