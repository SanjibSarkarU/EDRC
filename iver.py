import datetime
import re
import time

from matplotlib import pyplot as plt, animation
import rasterio
import serial

from rasterio.plot import show
import tkinter as tk
from tkinter import *
import threading
from geographiclib.geodesic import Geodesic
from time import monotonic
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import MRC_Iver
from queue import Queue
import pandas as pd
from collections import deque

rf, ac = 'COM1', 'COM4'
# rf, ac = 'COM5', 'COM7'

ser_rf = serial.Serial(rf, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1, xonxoff=0)
ser_ac = serial.Serial(ac, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1, xonxoff=0)


class App(tk.Frame):
    def __init__(self, master=None, **kwargs):
        tk.Frame.__init__(self, master, **kwargs)
        self.event_plot = threading.Event()
        self.q_plot = Queue()
        self.current_position_iver = {}
        self.disnc_remaining = 0
        self.wp_nxt = '1'
        self.auv = '3089'
        self.omw_clear = False
        self.q_wp_omw = Queue()
        self.send_through_rf = True
        self.send_through_ac = False
        
        self.running = False
        self.ani = None
        btns = tk.Frame(self)
        btns.pack()
        
        lbl = tk.Label(btns, text="update interval (ms)")
        lbl.pack(side=tk.LEFT)
        
        self.interval = tk.Entry(btns, width=5)
        self.intervl = 20
        self.interval.insert(0, str(self.intervl))
        self.interval.pack(side=tk.LEFT)
        
        self.btn = tk.Button(btns, text='Start', command=self.on_click)
        self.btn.pack(side=tk.LEFT)
        
        self.btn_rf = tk.Button(btns, text='RF', command=self.rf)
        self.btn_rf.pack(side=tk.LEFT)

        self.btn_ac = tk.Button(btns, text='AC', command=self.ac)
        self.btn_ac.pack(side=tk.LEFT)
        
        self.btn_exit = tk.Button(btns, text='Exit', command=quit)
        self.btn_exit.pack(side=tk.LEFT)
        
        self.fig = plt.Figure()
        self.ax1 = self.fig.add_subplot(111)
        self.line_iver, = self.ax1.plot([], [], 'r-', linewidth=1.5)
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        img = rasterio.open('Stennis_QW.tif')  # 'Cat_Island_Low.tif' , 'Stennis_QW.tif'
        show(img, ax=self.ax1)
        self.canvas.get_tk_widget().pack(expand=True)
        self.canvas.figure.tight_layout()
        self.geod = Geodesic(6378388, 1 / 297.0)
        # self.waypoints_iver = [[30.35099, -89.63138, 3], [30.35125, -89.63079, 3.5]]
        # self.waypoints_iver = [[30.3603, -89.0942, 10.5], [30.3546, -89.0734, 14.5],
        #                   [30.3151, -89.0589, 5.5], [30.2833, -89.0693, 3.0]]
        self.waypoints_iver = [[30.35099, -89.63138, 3], [30.35125, -89.63079, 3.5],
                               [30.35173, -89.63064, 3], [30.35203, -89.62992, 3],
                               [30.35247, -89.62979, 4], [30.35270, -89.62917, 4],
                               [30.35322, -89.62920, 3.5], [30.35345, -89.62827, 4],
                               [30.35099, -89.63138, 3.5]]
        # self.waypoints_iver = [[30.3612, -89.1002, 9], [30.3569, -89.1003, 9.5],
        #                   [30.3666, -89.1004, 5]]
        self.total_WPs = len(self.waypoints_iver)
        df = pd.DataFrame(self.waypoints_iver, columns=['lat', 'lon', 'speed'])
        self.ax1.scatter(df['lon'], df['lat'], color='red', marker='.', s=250, linewidths=0.05) # facecolors='none', edgecolors='r',
        for i in range(len(df)):
            self.ax1.scatter(df.lon[i], df.lat[i], marker="$"+str(i+1)+"$", color='black', linewidths=.09)
        
        HISTORY_LEN = 2000000
        self.xdata = deque([], maxlen=HISTORY_LEN)
        self.ydata = deque([], maxlen=HISTORY_LEN)
    
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
        threading.Thread(target=self.iver, daemon=True).start()
        threading.Thread(target=self.read_comports, daemon=True).start()
        self.ani = animation.FuncAnimation(
            self.fig,
            self.update_graph,
            # frames=self.lat_w.size - 1,
            interval=int(self.interval.get()),
            repeat=False,
            blit=True)
        self.running = True
        self.btn.config(text='Pause')
        self.ani._start()

    def iver_status(self):
        # print (nxt_wp)
        # 1 m/s = 1.94384 Knot
        iver_sta = '$OSI,8080808080,S,' + self.wp_nxt + ',' + \
                   str(self.current_position_iver['Latitude']) + ',' + str(self.current_position_iver['Longitude']) \
                   + ',' + str(self.current_position_iver['speed'] * 1.94384) + ',' + str(self.disnc_remaining) \
                   + ',N,0.000,P0,-1.4743,,0,292.5,0.0,94.3,False,IVER3-3089,2.5,True,False ' + '*'
        return '$AC;IVER3-' + self.auv + ';' + iver_sta + MRC_Iver.check_sum(iver_sta) + '\r\n'

    def osd_ACK(self):
        return '$AC;IVER3-' + self.auv + ';$ACK,8,0,0*5D' + '\r\n'

    def omw_Ack(self):
        ack = '$ACK,16,0,0*'
        return '$AC;IVER3-' + self.auv + ';' + ack + MRC_Iver.check_sum(ack) + '\r\n'
    
    def rf(self):
        if self.send_through_rf:
            self.send_through_rf = False
            self.send_through_ac = True
            self.btn_rf.config(text='RF-stop')
            self.btn_ac.config(text='AC-on')
        else:
            self.send_through_rf = True
            self.send_through_ac = False
            self.btn_rf.config(text='RF-on')
            self.btn_ac.config(text='AC-stop')
    
    def ac(self):
        if self.send_through_ac:
            self.send_through_ac = False
            self.send_through_rf = True
            self.btn_ac.config(text='AC-stop')
            self.btn_ac.config(text='AC-on')
        else:
            self.send_through_ac = True
            self.send_through_rf = False
            self.btn_ac.config(text='AC-on')
            self.btn_rf.config(text='RF-stop')

    def iver(self):
        print(datetime.datetime.now(), ': started')
        lat_i_past, lng_i_past, _ = self.waypoints_iver[0]
        while self.waypoints_iver:
            t_start = monotonic()
            lat_i_nxt, lng_i_nxt, speed_i = self.waypoints_iver[0]
            # speed_i *= 0.51  # * 1 knot = 0.514 m/s
            l = self.geod.InverseLine(lat_i_past, lng_i_past, lat_i_nxt, lng_i_nxt)
            nxt_wp_disnc = l.s13
            distance_travelled = 0
            while distance_travelled <= nxt_wp_disnc:
                g = l.Position(distance_travelled, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
                lat_i, lng_i = g['lat2'], g['lon2']
                self.current_position_iver = {'Latitude': lat_i, 'Longitude': lng_i, 'speed': speed_i}
                # self.q_plot.put(self.current_position_iver)
                self.event_plot.set()
                # t_elapsed = monotonic() - t_start
                # distance_travelled = speed_i * t_elapsed
                # self.disnc_remaining = nxt_wp_disnc - distance_travelled
                # time.sleep(self.intervl * 0.009)
                while not self.q_wp_omw.empty():
                    wp_omw = self.q_wp_omw.get()
                    lat_i_r, lng_i_r, speed_i_r = wp_omw['lat'], wp_omw['lon'], wp_omw['speed']
                    # speed_i_r *= 0.51  # 1 knot = 0.514 m/s
                    self.wp_nxt = 'WP1'
                    l_i_r = self.geod.InverseLine(self.current_position_iver['Latitude'],
                                                  self.current_position_iver['Longitude'],
                                                  lat_i_r, lng_i_r)
                    omw_distance = l_i_r.s13
                    omw_dstnce_travld = 0
                    t_start_r = monotonic()
                    while omw_dstnce_travld < omw_distance:
                        if self.omw_clear:
                            self.omw_clear = False
                            print('OMW_CLEAR')
                            break
                        g_i_r = l_i_r.Position(omw_dstnce_travld, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
                        lat_i_r, lng_i_r = g_i_r['lat2'],  g_i_r['lon2']
                        self.current_position_iver = {'Latitude': lat_i_r, 'Longitude': lng_i_r, 'speed': speed_i_r}
                        # self.q_plot.put(self.current_position_iver)
                        t_elapsed_r = monotonic() - t_start_r
                        omw_dstnce_travld = speed_i_r * t_elapsed_r
                        omw_distance_remaining = omw_distance - omw_dstnce_travld
                        self.disnc_remaining = omw_distance_remaining
                        time.sleep(self.intervl * 0.009)
                    if self.q_wp_omw.qsize() == 0:
                        self.waypoints_iver.insert(0, self.waypoints_iver[0])
                t_elapsed = monotonic() - t_start
                distance_travelled = speed_i * t_elapsed
                self.disnc_remaining = nxt_wp_disnc - distance_travelled
                time.sleep(self.intervl * 0.009)
                lat_i_past, lng_i_past = self.current_position_iver['Latitude'], self.current_position_iver['Longitude']
            self.waypoints_iver.pop(0)
            remaining_WPs = self.total_WPs - len(self.waypoints_iver)
            print(datetime.datetime.now(), ': Total WPs: {}, remaining WPs: {}/{}'.format(self.total_WPs, len(self.waypoints_iver), remaining_WPs))
            self.wp_nxt = str(remaining_WPs)
            print(datetime.datetime.now(), ': nxt_WP: ', self.wp_nxt)

    def read_comports(self):
        while True:
            # print('Status: RF: {}, AC {}'.format(self.send_through_rf, self.send_through_ac))
            try:
                if (self.send_through_rf and ser_rf.inWaiting() > 0) or (self.send_through_ac and ser_ac.inWaiting() > 0):
                    received_data_through = 'RF' if ser_rf.inWaiting() > 0 else 'AC'
                    read_com = ser_rf.readline().decode().strip() if received_data_through == 'RF' else ser_ac.readline().decode().strip()
                    print(datetime.datetime.now(), ': ComPort received: ', received_data_through, read_com)
                    # print('Status: RF: {}, AC {}', self.send_through_rf, self.send_through_ac)
                    if MRC_Iver.received_stream(read_com) == 'osd' and MRC_Iver.osd_req_recvd(read_com) == 0:
                        print("Current Status:", self.iver_status())
                        ser_rf.write(self.iver_status().encode()) if received_data_through == 'RF' else ser_ac.write(
                            self.iver_status().encode())
                        ser_rf.write(self.osd_ACK().encode()) if received_data_through == 'RF' else ser_ac.write(self.osd_ACK().encode())
                        # print("Time write:{} sec".format(time.perf_counter() - toc_CS))
                    elif MRC_Iver.received_stream(read_com) == 'omw' and MRC_Iver.omw_req_recvd(read_com) == 0:
                        omw_rec = read_com.split(";")[2].split(',')
                        ser_rf.write(self.omw_Ack().encode()) if received_data_through == 'RF' else ser_ac.write(self.omw_Ack().encode())
                        print(datetime.datetime.now(), ': OMW requeest acknowledgment send:', self.omw_Ack())
                        if re.search('CLEAR', read_com):
                            self.q_wp_omw.queue.clear()
                            self.omw_clear = True
                            self.q_wp_omw.put({'lat': float(omw_rec[2]), 'lon': float(omw_rec[3]),
                                               'speed': float(omw_rec[7])})
                        else:
                            self.q_wp_omw.put({'lat': float(omw_rec[2]), 'lon': float(omw_rec[3]),
                                               'speed': float(omw_rec[7])})
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(" Exception raised", e)
                continue
                
    def update_graph(self, i):
        self.event_plot.wait()
        self.xdata.append(self.current_position_iver['Longitude'])
        self.ydata.append(self.current_position_iver['Latitude'])
        # plot_inbox = self.q_plot.get()
        # self.xdata.append(plot_inbox['Longitude'])
        # self.ydata.append(plot_inbox['Latitude'])
        # ax.plot([lng_i_p, current_position_iver['Longitude']], [lat_i_p, current_position_iver['Latitude']], 'r') if \
        #     lat_i_p != 0.0 else ax.plot(plot_inbox['Longitude'], plot_inbox['Latitude'], 'r')
        # lat_i_p, lng_i_p = current_position_iver['Latitude'], current_position_iver['Longitude']
        
        self.line_iver.set_data(self.xdata, self.ydata)
        return self.line_iver,


def main():
    root = tk.Tk()
    root.title('Iver_v2')
    root.iconbitmap('usm.ico')
    app = App(root)
    app.pack()
    root.mainloop()


if __name__ == '__main__':
    main()
