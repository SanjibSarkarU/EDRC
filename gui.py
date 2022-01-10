import tkinter as tk
root = tk.Tk()
root.title('SVP')
root.geometry('800x600')
# label
root.columnconfigure(1, weight=1)
root.rowconfigure(2, weight=1)

menubar = tk.Menu(root)
root.config(menu=menubar)

# # Create a menu item
file_menu = tk.Menu(menubar)
menubar.add_cascade(label='File', menu=file_menu)
file_menu.add_command(label='New')
file_menu.add_command(label='Exit', command=root.quit)

# # Create an edit menu item
map_menu = tk.Menu(menubar)
menubar.add_cascade(label='Map', menu=map_menu)
map_menu.add_command(label='AddMap')

# # Create a help menu item
help_menu = tk.Menu(menubar)
menubar.add_cascade(label='Help', menu=help_menu)
help_menu.add_command(label='info')

# Create a label
var = tk.StringVar()
iver_coordinates = tk.Label(root, text='Iver position: ')
iver_coordinates.grid(row=0, column=2, sticky='we', padx=15, pady=5)

iver_name = tk.Entry(root)
iver_name.grid(row=0, column=3, sticky=tk.E + tk.W)

# #category
cat_var = tk.StringVar()
iver_lists = ['Iver-3089', 'Iver-3072']
iver_label = tk.Label(root, text='iver_lists: ', padx=5, pady=5)
iver_label.grid(row=1, column=2, sticky=tk.E + tk.W)

iver_input = tk.OptionMenu(root, cat_var, *iver_lists)
iver_input.grid(row=1, column=3,padx=5, pady=5, ipadx=10, ipady=1, sticky=tk.E + tk.W)

message = tk.Text(root)
message.grid(row=0, column=0, sticky='nesw')

# #Button
start_btn = tk.Button(root, text='Start', command=quit)
start_btn.grid(row=3, column=1, sticky=tk.E, ipadx=5, ipady=2.5)


root.mainloop()
