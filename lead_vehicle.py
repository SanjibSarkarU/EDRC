import socket
from collections import deque
import rasterio
from matplotlib import pyplot as plt, animation
from rasterio.plot import show
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import functions
from tkinter import *

HISTORY_LEN = 20000


#
class App(tk.Frame):
    def __init__(self, master=None, **kwargs):
        tk.Frame.__init__(self, master, **kwargs)

        daa = pd.read_csv("20210422_085502_original.csv")
        # daa = pd.read_csv("20211120_181214_modified_cat1.csv")
        # daa = daa[(daa[['Latitude (Deg N)', 'Longitude (Deg W)']] != 0).all(axis=1)]  # delete all 0 values
        # daa.reset_index()
        self.lat_w = daa['Latitude (Deg N)']
        self.lng_w = daa['Longitude (Deg W)']
        self.log_time_w = daa['Time']

        self.running = False
        self.ani = None
        btns = tk.Frame(self)
        btns.pack()

        lbl = tk.Label(btns, text="update interval (ms)")
        lbl.pack(side=tk.LEFT)

        self.interval = tk.Entry(btns, width=5)
        self.interval.insert(0, '1000')
        self.interval.pack(side=tk.LEFT)

        self.btn = tk.Button(btns, text='Start', command=self.on_click)
        self.btn.pack(side=tk.LEFT)

        self.btn_exit = tk.Button(btns, text='Exit', command=quit)
        self.btn_exit.pack(side=tk.LEFT)

        # leadV = '{}, {}'.format(0.000, 0.0000)
        # self.label_lat = tk.Label(master, text=lead_v).pack(side=tk.RIGHT, expand=1)
        # self.label_iver_location = tk.Label(master, text='LeadVehicle:').pack(tk.RIGHT)

        # settingscanvas = Canvas(master, bg="yellow")
        # settingscanvas.pack(side='top', anchor='nw', expand=False, fill='x')

        self.fig = plt.Figure()
        # self.fig1 = plt.Figure(figsize=(1.5, 1.5))
        self.ax1 = self.fig.add_subplot(111)

        # self.line_lead, = self.ax1.plot([], [], 'k-', linewidth=2)
        self.line_lead, = self.ax1.plot([], [], linewidth=2)
        # self.line_lead = self.ax1.scatter(0, 0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        # self.canvas1 = FigureCanvasTkAgg(self.fig1, master=master)
        # img = rasterio.open('Stennis_QW.tif'), # 'Cat_Island_Low.tif'
        show(rasterio.open('Stennis_QW.tif'), ax=self.ax1)
        self.canvas.get_tk_widget().pack(expand=True)
        # self.canvas1.get_tk_widget().pack(expand=True)
        self.canvas.figure.tight_layout()

        self.xdata = deque([], maxlen=HISTORY_LEN)
        self.ydata = deque([], maxlen=HISTORY_LEN)
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def on_click(self):
        if self.ani is None:
            return self.start()
        if self.running:
            self.ani.event_source.stop()
            self.btn.config(text='Un-Pause')
        else:
            self.ani.event_source.start()
            self.btn.config(text='Pause')
        self.running = not self.running

    def start(self):
        self.ani = animation.FuncAnimation(
            self.fig,
            self.update_graph,
            frames=self.lat_w.size - 1,
            interval=int(self.interval.get()),
            repeat=False,
            blit=True)
        self.running = True
        self.btn.config(text='Pause')
        self.ani._start()

    def update_graph(self, i):
        # print(i, (self.lat_w[i], self.lng_w[i]))
        latlng = functions.dd2ddm((self.lat_w[i], self.lng_w[i]))
        self.xdata.append(self.lng_w[i])
        self.ydata.append(self.lat_w[i])
        self.line_lead.set_data(self.xdata, self.ydata)
        self.line_lead.set_color('k')
        data = "$GPGLL," + str(latlng['Lat_ddm']) + ',' + latlng['N_S'] + ',' + str(latlng['Lng_ddm']) + ',' + \
               latlng['E_W'] + ',' + str(''.join(str(self.log_time_w[i]).split(':'))) + ',A,A*'
        wamv_nema = data + functions.check_sum(data) + '\r\n'
        self.soc.sendto(bytes(wamv_nema, 'utf-8'), ('localhost', 10000))
        # print(self.lat_w[i], self.lng_w[i])
        print(wamv_nema)
        return self.line_lead,


def main():
    root = tk.Tk()
    root.title('lead_v2')
    root.iconbitmap('usm.ico')
    app = App(root)
    app.pack()
    root.mainloop()


if __name__ == '__main__':
    main()

