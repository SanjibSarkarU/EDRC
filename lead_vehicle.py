import threading
import time
import tkinter as tk
from queue import Queue
import functions
import pandas as pd
from matplotlib import pyplot as plt, animation
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import socket

import threadartists as ta

  # UDP

HISTORY_LEN = 200000


def plot_geotif():
    """Work in progress..."""
    noaachart = ta.GeoTifArtist(q_art, label='Stennis_QW', alpha=1, zorder=1)
    noaachart.add_data_to_artist('Cat_Island_Low_2.tif')   # Cat_Island_Low_2.tif , Stennis_QW.tif
    noaachart.set_xlim(noaachart.geotif_xlim[0], noaachart.geotif_xlim[1])
    noaachart.set_ylim(noaachart.geotif_ylim[0], noaachart.geotif_ylim[1])
    while True:
        time.sleep(2)


def lead():
    soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # daa = pd.read_csv("20210422_085502_original.csv")  # wamv log
    # lat_w = daa['Latitude (Deg N)']
    # lng_w = daa['Longitude (Deg W)']
    # log_time_w = daa['Time']
    #
    # IVERlog
    daa = pd.read_csv('20220104-212027-UTC_0-CAT3-IVER3-3089.log', header=0, delimiter=';')
    lat_w = daa['Latitude']
    lng_w = daa['Longitude']
    tme = daa['Time']

    time.sleep(3)
    lead_icon = ta.ImageArtist(q_art, label='wam-v icon', alpha=1, zorder=4)
    lead_trace = ta.LineArtist(q_art, label='vam-v trace', c='k', alpha=0.6, zorder=3)
    icon_size = 0.02
    lead_icon.add_data_to_artist('WAM-V_icon_small.png', icon_size, (0, 0), 0)
    i = 0
    print(len(lng_w))
    while i < len(lng_w):
        new_xy = (lng_w[i], lat_w[i])
        # print(new_xy, tme[i])
        deg = 10
        lead_icon.set_position(new_xy, deg)
        lead_trace.add_data_to_artist(new_xy)
        latlng = functions.dd2ddm((lat_w[i], lng_w[i]))
        data = "$GPGLL," + str(latlng['Lat_ddm']) + ',' + latlng['N_S'] + ',' + str(latlng['Lng_ddm']) + ',' + \
               latlng['E_W'] + ',' + str(''.join(str(tme[i]).split(':'))) + ',A,A*'
        wamv_nema = data + functions.check_sum(data) + '\r\n'
        soc.sendto(bytes(wamv_nema, 'utf-8'), ('localhost', 10000))
        # print(i, data)
        i += 1
        time.sleep(0.1)


def _quit():
    root.quit()  # stops mainloop
    root.destroy()


if __name__ == '__main__':
    q_art = Queue(maxsize=0)
    root = tk.Tk()
    root.wm_title("Lead Vehicle")
    fig = plt.Figure(figsize=(5, 4), dpi=100)
    ax = fig.add_subplot(111)

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    toolbar = NavigationToolbar2Tk(canvas, root)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    button = tk.Button(master=root, text="Quit", command=_quit)
    button.pack(side=tk.BOTTOM)

    threading.Thread(target=plot_geotif, daemon=True).start()
    threading.Thread(target=lead, daemon=True).start()

    anim = animation.FuncAnimation(fig, ta.animate, frames=ta.gallerist(ax, fig, q_art),
                                   interval=100, blit=True, repeat=False)

    tk.mainloop()

# # ****************************************** OLD VERSION**********************************
# class App(tk.Frame):
#     def __init__(self, master=None, **kwargs):
#         tk.Frame.__init__(self, master, **kwargs)
#
#         daa = pd.read_csv("20210422_085502_original.csv")
#         # daa = pd.read_csv("20211120_181214_modified_cat1.csv")
#         # daa = daa[(daa[['Latitude (Deg N)', 'Longitude (Deg W)']] != 0).all(axis=1)]  # delete all 0 values
#         # daa.reset_index()
#         self.lat_w = daa['Latitude (Deg N)']
#         self.lng_w = daa['Longitude (Deg W)']
#         self.log_time_w = daa['Time']
#
#         self.running = False
#         self.ani = None
#         btns = tk.Frame(self)
#         btns.pack()
#
#         lbl = tk.Label(btns, text="update interval (ms)")
#         lbl.pack(side=tk.LEFT)
#
#         self.interval = tk.Entry(btns, width=5)
#         self.interval.insert(0, '1000')
#         self.interval.pack(side=tk.LEFT)
#
#         self.btn = tk.Button(btns, text='Start', command=self.on_click)
#         self.btn.pack(side=tk.LEFT)
#
#         self.btn_exit = tk.Button(btns, text='Exit', command=quit)
#         self.btn_exit.pack(side=tk.LEFT)
#
#         # leadV = '{}, {}'.format(0.000, 0.0000)
#         # self.label_lat = tk.Label(master, text=lead_v).pack(side=tk.RIGHT, expand=1)
#         # self.label_iver_location = tk.Label(master, text='LeadVehicle:').pack(tk.RIGHT)
#
#         # settingscanvas = Canvas(master, bg="yellow")
#         # settingscanvas.pack(side='top', anchor='nw', expand=False, fill='x')
#
#         self.fig = plt.Figure()
#         # self.fig1 = plt.Figure(figsize=(1.5, 1.5))
#         self.ax1 = self.fig.add_subplot(111)
#
#         # self.line_lead, = self.ax1.plot([], [], 'k-', linewidth=2)
#         self.line_lead, = self.ax1.plot([], [], linewidth=2)
#         # self.line_lead = self.ax1.scatter(0, 0)
#         self.canvas = FigureCanvasTkAgg(self.fig, master=master)
#         # self.canvas1 = FigureCanvasTkAgg(self.fig1, master=master)
#
#         # img = rasterio.open('Stennis_QW.tif'), # 'Cat_Island_Low.tif'
#         show(rasterio.open('Stennis_QW.tif'), ax=self.ax1)
#         self.canvas.get_tk_widget().pack(expand=True)
#         # self.canvas1.get_tk_widget().pack(expand=True)
#         self.canvas.figure.tight_layout()
#
#         self.xdata = deque([], maxlen=HISTORY_LEN)
#         self.ydata = deque([], maxlen=HISTORY_LEN)
#         self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#
#     def on_click(self):
#         if self.ani is None:
#             return self.start()
#         if self.running:
#             self.ani.event_source.stop()
#             self.btn.config(text='Un-Pause')
#         else:
#             self.ani.event_source.start()
#             self.btn.config(text='Pause')
#         self.running = not self.running
#
#     def start(self):
#         self.ani = animation.FuncAnimation(
#             self.fig,
#             self.update_graph,
#             frames=self.lat_w.size - 1,
#             interval=int(self.interval.get()),
#             repeat=False,
#             blit=True)
#         self.running = True
#         self.btn.config(text='Pause')
#         # self.ani._start()
#
#     def update_graph(self, i):
#         # print(i, (self.lat_w[i], self.lng_w[i]))
#         latlng = functions.dd2ddm((self.lat_w[i], self.lng_w[i]))
#         self.xdata.append(self.lng_w[i])
#         self.ydata.append(self.lat_w[i])
#         self.line_lead.set_data(self.xdata, self.ydata)
#         self.line_lead.set_color('k')
#         data = "$GPGLL," + str(latlng['Lat_ddm']) + ',' + latlng['N_S'] + ',' + str(latlng['Lng_ddm']) + ',' + \
#                latlng['E_W'] + ',' + str(''.join(str(self.log_time_w[i]).split(':'))) + ',A,A*'
#         wamv_nema = data + functions.check_sum(data) + '\r\n'
#         self.soc.sendto(bytes(wamv_nema, 'utf-8'), ('localhost', 10000))
#         # print(self.lat_w[i], self.lng_w[i])
#         print(wamv_nema)
#         return self.line_lead,
#
#
# def main():
#     root = tk.Tk()
#     root.title('lead_v2')
#     root.iconbitmap('usm.ico')
#     app = App(root)
#     app.pack()
#     root.mainloop()
#
#
# if __name__ == '__main__':
#     main()
