from pdf2image import convert_from_path
import tkinter as tk
from PIL import ImageTk

# Convert PDF to list of images
images = convert_from_path('C:/Users/thg/Desktop/Maksymilian-Paluśkiewicz_CV.pdf')

# Initialize Tkinter
root = tk.Tk()
image = ImageTk.PhotoImage(images[0])

# Create a label to display the image
label = tk.Label(root, image=image)
label.pack()

root.mainloop()