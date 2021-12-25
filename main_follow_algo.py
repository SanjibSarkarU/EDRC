import datetime
import re
import socket
# import winsound
from collections import deque
import matplotlib.pyplot as plt
import rasterio
import serial
# from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib import animation
from rasterio.plot import show
# import datetime as dt
import tkinter as tk
import threading
from tkinter import *
# from threading import Event
import time
# import geopy.distance
import MRC_Iver
from time import monotonic
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from queue import Queue
import pandas as pd
from geographiclib.geodesic import Geodesic

HISTORY_LEN = 20000
# ............Read UDP port to collect WAM-V data.................
UDP_IP = 'localhost'
UDP_PORT = 10000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.bind((UDP_IP, UDP_PORT))
TIMEOUT_RF = 2
TIMEOUT_AC = 2

# ............Communicate through ACOM and RF through comports...................
ser_rf = serial.Serial('COM2', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=TIMEOUT_RF, xonxoff=0)
ser_ac = serial.Serial('COM5', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=TIMEOUT_AC, xonxoff=0)
# ser_rf = serial.Serial('COM8', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=TIMEOUT_RF, xonxoff=0)
# ser_ac = serial.Serial('COM9', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=TIMEOUT_AC, xonxoff=0)
iver = '3089'


class App(tk.Frame):
    def __init__(self, master=None, **kwargs):
        tk.Frame.__init__(self, master, **kwargs)
        
        self.running = False
        self.ani = None
        self.q_plot, self.q_iver_comm, self.q_lead, self.q_log = Queue(), Queue(), Queue(), Queue()
        self.q_iverupdate_sim_IC, self.q_ivrsim_ivrcomm = Queue(), Queue()
        self.q_wp_omw_simu, self.current_position_iver = Queue(), {}
        self.xdata, self.ydata = deque([], maxlen=HISTORY_LEN), deque([], maxlen=HISTORY_LEN)
        self.xdata_iver, self.ydata_iver = deque([], maxlen=HISTORY_LEN), deque([], maxlen=HISTORY_LEN)
        self.x_simulation, self.y_simulation = deque([], maxlen=HISTORY_LEN), deque([], maxlen=HISTORY_LEN)
        self.x_p, self.y_p = deque([], maxlen=HISTORY_LEN), deque([], maxlen=HISTORY_LEN)
        
        self.allowed_discrepancy = 17
        self.event_iver = threading.Event()
        self.latlng_iver = []
        self.inst_snd = None
        btns = tk.Frame(self)
        btns.pack()
        
        lbl = tk.Label(btns, text="update interval (ms)")
        lbl.pack(side=tk.LEFT)
        
        self.interval = tk.Entry(btns, width=5)
        self.interval.insert(0, '50')
        self.interval.pack(side=tk.LEFT)
        
        self.btn = tk.Button(btns, text='Start', command=self.on_click)
        self.btn.pack(side=tk.LEFT)
        
        self.btn_exit = tk.Button(btns, text='Exit', command=quit)
        self.btn_exit.pack(side=tk.LEFT)
        
        self.fig = plt.Figure()
        self.ax1 = self.fig.add_subplot(111)
        line_width = 0.9
        self.line_lead, = self.ax1.plot([], [], 'k-', lw=line_width)
        self.line_iver, = self.ax1.plot([], [], 'r-', lw=line_width)
        self.scatter_prdctd, = self.ax1.plot([], [], '*', color='lavender', lw=.5)
        self.line_simulation, = self.ax1.plot([], [], '--', color='yellow', lw=line_width)   #  'fuchsia'
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        
        img = rasterio.open('Stennis_QW.tif')  # 'Cat_Island_Low.tif', 'Stennis_QW.tif'
        x = show(img, ax=self.ax1)
        self.canvas.get_tk_widget().pack(expand=True)
        self.canvas.figure.tight_layout()
        self.geod = Geodesic(6378388, 1 / 297.0)
        # self.ax1.scatter(df['lon'], df['lat'], c="red", marker="X", linewidths=0.15)

        # threading.Thread(target=self.lead_vehicle_communication, daemon=True).start()
       
    def on_click(self):
        if self.ani is None:
            return self.start()
        if self.running:
            self.ani.event_source.stop()
            self.btn.config(text='following')
        else:
            self.ani.event_source.start()
            self.btn.config(text='Pause')
        self.running = not self.running
    
    def start(self):
        threading.Thread(target=self.lead_vehicle_communication, daemon=True).start()
        threading.Thread(target=self.iver_communication, daemon=True).start()
        threading.Thread(target=self.brain, daemon=True).start()
        threading.Thread(target=self.iver_simulation, daemon=True).start()
        
        self.ani = animation.FuncAnimation(
            self.fig,
            self.update_graph,
            # frames=self.points,
            interval=int(self.interval.get()),
            repeat=False,
            blit=True)
        self.running = True
        self.btn.config(text='Pause')
        self.ani._start()
    
    def lead_vehicle_communication(self):
        """ Chase/Lead vehicle data  """
        # print(datetime.datetime.now(), ': Chase vehicle data')
        while True:
            data, addr = sock.recvfrom(1350)  # buffer size is 1024
            data_w_recived = data.decode()
            # print("WAMv data received message: ", data_w_recived)
            if MRC_Iver.wamv_gpgll(data_w_recived) == 0:
                data_w_recived = data_w_recived.split(',')
                data_recived = data_w_recived[1:5]
                coordinates_w_c = MRC_Iver.ddm2dd(data_recived)
                time_stamp_w = data_w_recived[5].split('.')[0] if re.search('.', data_w_recived[5]) else data_w_recived[
                    5]
                lat_w_c = coordinates_w_c['Lat_dd']
                lng_w_c = coordinates_w_c['Lng_dd']
                self.q_lead.put([lat_w_c, lng_w_c, time_stamp_w])
                self.q_plot.put({'lat': lat_w_c, 'lon': lng_w_c, 'key': 'lead', 'color': 'k'})
                self.q_log.put({'Time': datetime.datetime.now().strftime("%H:%M:%S.%f"), 'Latitude': lat_w_c,
                                'Longitude': lng_w_c, 'TimeFrom_Lead': time_stamp_w, 'key': 'lead_vehicle'})
            lead_comm_time = monotonic()
    
    def iver_communication(self):
        ser_rf.reset_output_buffer()
        ser_rf.reset_input_buffer()
        ser_ac.reset_input_buffer()
        ser_ac.reset_output_buffer()
        lst_osd, lst_omw = [], []
        send_flag = None  # Communication is going on
        send_through_AC_time_start = monotonic()
        send_through_AC_wait = 13
        AC_flag = False
        while True:
            while not self.q_iver_comm.empty():
                q_read = self.q_iver_comm.get()
                # print(q_read)
                if q_read['key'] == 'osd':
                    lst_osd.append(q_read)
                elif q_read['key'] == 'omw':
                    lst_omw.append(q_read)
                else:
                    print('Warning!! Not know keyword')
            print(datetime.datetime.now(), 'Eof the queue, length of the lst_omw {}, lst_osd {} ,snd flag {}'.format(len(lst_omw), len(lst_osd), send_flag))
            if len(lst_omw) > 0 and len(lst_osd) < 3 and send_flag is None:
                # '$AC;Iver3-3089;$OMW,CLEAR,30.35197,-89.62897,0.0,,10,4.0,0, *cc'
                omw_send = lst_omw[-1]
                # print(omw_send)
                # lst_omw.pop(-1)
                ins_omw = 'OMW,,' + str(omw_send['lat']) + ',' + str(omw_send['lon']) + ',0.0,,10,' + \
                          str(omw_send['speed']) + ',0, *' if omw_send['NC_r_C'] == 'NClear' else \
                    'OMW,CLEAR,' + str(omw_send['lat']) + ',' + str(omw_send['lon']) + ',0.0,,10,' + \
                    str(omw_send['speed']) + ',0, *'
                self.inst_snd = '$AC;Iver3-' + iver + ';' + '$' + ins_omw + MRC_Iver.check_sum(ins_omw) + '\r\n'
                
            elif len(lst_osd) > 0 and send_flag is None:
                # lst_osd.pop(-1)
                self.inst_snd = '$AC;Iver3-' + iver + ';' + '$' + MRC_Iver.osd() + '\r\n'
                
            if self.inst_snd is not None and (len(lst_osd) > 0 or len(lst_omw) > 0):
                # print('i am here')
                ser_rf.write(self.inst_snd.encode())
                print(datetime.datetime.now(), ': Sending through RF.', self.inst_snd.encode())
                send_flag = 'sending through RF'
                lst_omw.clear() if re.search('OMW', self.inst_snd) else lst_osd.clear() if re.search('OSD', self.inst_snd) else ''
                self.q_log.put({'Time': datetime.datetime.now().strftime("%H:%M:%S.%f"), 'info': 'OMW' if re.search(
                    'OMW', self.inst_snd) else 'OSD', 'key': 'sending through RF'})
                
            read_rf = ser_rf.readline().decode()
            read_ac = ser_ac.readline().decode()
            try:
                if len(read_rf) > 2:
                    self.q_log.put(
                        {'Time': datetime.datetime.now().strftime("%H:%M:%S.%f"), 'info': read_rf,
                         'key': 'received through RF'})
                    if MRC_Iver.received_stream(read_rf) == 'osi' and MRC_Iver.osi(read_rf) is not None:
                        send_flag = None
                        osi_return = MRC_Iver.osi(read_rf)
                        self.q_iverupdate_sim_IC.put({'lat': osi_return['Latitude'], 'lon': osi_return['Longitude'],
                                        'speed': osi_return['Speed'], 'key': 'updatedPositionFromIC'})
                        print(datetime.datetime.now(), ': RF:', osi_return)
                        self.q_plot.put({'lat': osi_return['Latitude'], 'lon': osi_return['Longitude'], 'key': 'iver',
                                         'color': 'r'})
                        self.event_iver.set()  # not required, event should be set by the iver simulation thread
                        self.q_log.put(
                            {'Time': datetime.datetime.now().strftime("%H:%M:%S.%f"), 'lat': osi_return['Latitude'],
                             'lon' : osi_return['Longitude'], 'key': 'iverPosition'})
                    elif MRC_Iver.received_stream(read_rf) == 'osdAck' and MRC_Iver.osd_ack(read_rf) == 0:
                        # send_flag = None
                        print(datetime.datetime.now(), ': OSD Acknowledgement from the IVER')
                    elif MRC_Iver.received_stream(read_rf) == 'omwAck':
                        send_flag = None
                        print(datetime.datetime.now(),
                              ': OMW acknowledged' if MRC_Iver.omw_ack(read_rf) == 0 else ('Error: ', read_rf))
                elif send_flag is not None:  # send_flag == 'sending through RF':
                    send_flag = 'send through AC'
                if len(read_ac) > 2:
                    if MRC_Iver.received_stream(read_ac) == 'osi' and MRC_Iver.osi(read_ac) is not None:
                        send_flag, AC_flag = None, False
                        osi_return = MRC_Iver.osi(read_rf)
                        # self.latlng_iver.append([osi_return['Latitude'], osi_return['Longitude'], osi_return['Speed']])
                        self.q_iverupdate_sim_IC.put({'lat': osi_return['Latitude'], 'lon': osi_return['Longitude'],
                                        'speed': osi_return['Speed'], 'key': 'updatedPositionFromIC'})
                        print(datetime.datetime.now(), ': AC:', osi_return)
                        self.q_plot.put({'lat': osi_return['Latitude'], 'lon': osi_return['Longitude'], 'key': 'iver',
                                         'color': 'r'})
                        self.event_iver.set()  # not required, event should be set by the iver simulation thread
                    elif MRC_Iver.received_stream(read_ac) == 'osdAck' and MRC_Iver.osd_ack(read_ac) == 0:
                        # send_flag = None
                        print(datetime.datetime.now(), ': OSD Acknowledgement from the IVER')
                    elif MRC_Iver.received_stream(read_ac) == 'omwAck':
                        send_flag, AC_flag = None, False
                        print(datetime.datetime.now(),
                              ': OMW acknowledged through AC' if MRC_Iver.omw_ack(read_rf) == 0 else ('Error: ', read_rf))
                elif AC_flag:
                    if monotonic() - send_through_AC_time_start > send_through_AC_wait:
                        print(datetime.datetime.now(), ': wait time is over, AC, was not successful')
                        AC_flag = False
                        send_flag = None
                        
                if send_flag is not None and not AC_flag and self.inst_snd is not None:
                    print('i am at AC, ', send_flag, 'AC_flase status: ', AC_flag)
                    ser_rf.write(self.inst_snd.encode())
                    send_through_AC_time_start = monotonic()
                    send_flag = 'send through AC'
                    AC_flag = True
                    print(datetime.datetime.now(), ': Sending through AC.', self.inst_snd.encode())
            except Exception as e:
                print(datetime.datetime.now(), ': Exception: ', e)
                ser_rf.reset_input_buffer()
                ser_ac.reset_input_buffer()
                continue
     
    def predictLoc(self, lat, lon, ha, speed, timetopredict, behind=0):
        """predict the location at the time specified from the current location,
        takes time as a datetime object python"""
        # self.geod = Geodesic(6378388, 1 / 297.0)
        if float((timetopredict - datetime.datetime.now()).total_seconds()) < 0:
            print(" Cannot change the past!!!!")
            return None
        else:
            t = (timetopredict - datetime.datetime.now()).total_seconds()
            predicted_p = self.geod.Direct(float(lat), float(lon), azi1=ha, s12=(t * speed) - behind)
            return {'lat': predicted_p['lat2'], 'lon': predicted_p['lon2']}
    
    def brain(self):
        """ Main Brain """
        latlng_lead = []
        while True:
            PREDICT_AFTER_SEC = 35.0
            predictAtTime = datetime.datetime.now() + datetime.timedelta(seconds=PREDICT_AFTER_SEC)  # prediction at
            # whcih time
            BEHIND = 10  # meters behind the predicted goal
            update_goal_loc_follower = True  # send the location to the follower vehicle
            omw_clear_flag = False
            loop = 1
            latlng_lead.append(self.q_lead.get())
            while len(latlng_lead) > 6 and len(self.current_position_iver) > 0:  # and self.event_iver.wait():
                latlng_lead.append(self.q_lead.get())
                # print(datetime.datetime.now(), ": *****IverFollowingLoop: ", loop, "*****")
                lV = MRC_Iver.coordinate_fit(latlng_lead[-6:])
                leadV_past, leadV_present = lV[0], lV[1]
                leadV_present_lat, leadV_present_lng = leadV_present[0], leadV_present[1]
                leadV_ha = MRC_Iver.speed_ha_coordinates(leadV_past, leadV_present)  # lead Vehicle's speed & HA
                leadV_predict_p = self.predictLoc(leadV_present_lat, leadV_present_lng, ha=leadV_ha['ha'],
                                                  speed=leadV_ha['speed'], timetopredict=predictAtTime)  #
                iver_goal = self.predictLoc(leadV_present_lat, leadV_present_lng, ha=leadV_ha['ha'],
                                            speed=leadV_ha['speed'],
                                            timetopredict=predictAtTime, behind=BEHIND)
                # print(datetime.datetime.now(),
                #       ": LeadVehicle's speed {} m/s & Heading angle {}".format(leadV_ha['speed'], leadV_ha['ha']))
                if update_goal_loc_follower:
                    iver_target = iver_goal
                    # calculating the desire speed of the chase vehicle
                    iver_current_pos = self.current_position_iver
                    disGoalCurrIver = self.geod.Inverse(iver_current_pos['Latitude'], iver_current_pos['Longitude'],
                                                   iver_target['lat'], iver_target['lon'])['s12']
                    desire_speed = (disGoalCurrIver / PREDICT_AFTER_SEC) * 0.514  # knots
                    # print(datetime.datetime.now(), ': Distance between goal and current position of the IVER: {}, '
                    #                                'Desire Speed: {} knots'.format(disGoalCurrIver, desire_speed))
                    self.q_iver_comm.put(
                        {'lat': iver_target['lat'], 'lon': iver_target['lon'], 'speed': desire_speed,
                         'NC_r_C': 'Clear' if omw_clear_flag else 'NClear', 'key': 'omw'})
                    self.q_plot.put({'lat': iver_target['lat'], 'lon': iver_target['lon'], 'key': 'predicted',
                                     'color': 'w'})
                    if omw_clear_flag:
                        self.q_wp_omw_simu.queue.clear()
                    self.q_wp_omw_simu.put({'lat': iver_target['lat'],
                                          'lon': iver_target['lon'], 'speed': desire_speed})
                    update_goal_loc_follower = False
                    omw_clear_flag = False
                dis_goal_target = self.geod.Inverse(iver_target['lat'], iver_target['lon'],
                                                    iver_goal['lat'], iver_goal['lon'])['s12']
                # global allowed_discrepancy
                # print(datetime.datetime.now(), ": Distance between Goal and Target:   ", dis_goal_target)
                if dis_goal_target > self.allowed_discrepancy or (
                        predictAtTime - datetime.datetime.now() < datetime.timedelta(seconds=6)):
                    update_goal_loc_follower = True
                    omw_clear_flag = True
                    self.q_plot.put({'lat': iver_goal['lat'], 'lon': iver_goal['lon'], 'key': 'out', 'color': 'r'})
                    predictAtTime = datetime.datetime.now() + datetime.timedelta(seconds=PREDICT_AFTER_SEC)
                else:
                    # distance between chase vehicle and target
                    iver_current_pos = self.current_position_iver
                    dis_current_target_iver = self.geod.Inverse(iver_target['lat'], iver_target['lon'],
                                                                iver_current_pos['Latitude'],
                                                                iver_current_pos['Longitude'])['s12']
                    dis_current_predicted_lead = self.geod.Inverse(leadV_predict_p['lat'], leadV_predict_p['lon'],
                                                              latlng_lead[-1][0], latlng_lead[-1][1])['s12']
                    # print(datetime.datetime.now(), ": Distance between current and Target:", dis_current_target)
                    MIN_DIS_TARGET = 10
                    if 0 < dis_current_target_iver < MIN_DIS_TARGET or dis_current_predicted_lead < self.allowed_discrepancy + BEHIND:
                        update_goal_loc_follower = True
                        predictAtTime = datetime.datetime.now() + datetime.timedelta(seconds=PREDICT_AFTER_SEC)
                loop += 1
            comm_time = monotonic()
    
    def log_data(self):
        log_inbox = self.q_log.get()
        # write on a text file from log_inbox
        
    def key_priority(self, key='default', priority=0):
        self.key = key
        self.priority = priority
        
    def iver_simulation(self):
        # self.q_iverupdate_sim_IC.put({'lat': osi_return['Latitude'], 'lon': osi_return['Longitude'],
        #                                         'speed': osi_return['Speed'], 'key': 'updatedPositionFromIC'})
        self.q_iver_comm.put({'Time:': datetime.datetime.now, 'key': 'osd'})
        updated_iver_pos = self.q_iverupdate_sim_IC.get()
        self.current_position_iver = {'Latitude': updated_iver_pos['lat'],
                                      'Longitude': updated_iver_pos['lon'],
                                      'speed': updated_iver_pos['speed']}
        self.update_iver_position()
        lat_i_past, lng_i_past = self.current_position_iver['Latitude'], self.current_position_iver['Longitude']
        wp_omw = self.q_wp_omw_simu.get()
        while True:
            t_start = monotonic()
            if not self.q_wp_omw_simu.empty():
                wp_omw = self.q_wp_omw_simu.get()
            lat_i_nxt, lng_i_nxt, speed_i = wp_omw['lat'], wp_omw['lon'], wp_omw['speed']
            # speed_i *= 0.51  # * 1 knot = 0.514 m/s
            l = self.geod.Inverse(lat_i_past, lng_i_past, lat_i_nxt, lng_i_nxt)
            azi1 = l['azi2']
            time.sleep(0.15)
            m = self.geod.Direct(lat_i_past, lng_i_past, azi1=azi1, s12=(monotonic()-t_start)*speed_i)
            self.current_position_iver = {'Latitude': m['lat2'], 'Longitude': m['lon2'], 'speed': speed_i}
            self.q_plot.put({'lat': self.current_position_iver['Latitude'],
                             'lon': self.current_position_iver['Longitude'], 'key': 'simulation', 'color': 'y'})
            if not self.q_iverupdate_sim_IC.empty():
                updated_iver_pos = self.q_iverupdate_sim_IC.get()
                self.current_position_iver = {'Latitude': updated_iver_pos['lat'],
                                              'Longitude': updated_iver_pos['lon'],
                                              'speed': updated_iver_pos['speed']}
            lat_i_past, lng_i_past = self.current_position_iver['Latitude'], self.current_position_iver['Longitude']
    
    def update_iver_position(self):
        called_every_insec = 20
        threading.Timer(called_every_insec, self.update_iver_position).start()
        self.q_iver_comm.put({'Time:': datetime.datetime.now, 'key': 'osd'})
            
    def update_graph(self, i):
        # Data inside queue: enum datatype
        plot_inbox = self.q_plot.get()
        # print(plot_inbox)
        if plot_inbox['key'] == 'lead':
            self.xdata.append(plot_inbox['lon'])
            self.ydata.append(plot_inbox['lat'])
            self.line_lead.set_data(self.xdata, self.ydata)
            self.line_lead.set_color(plot_inbox['color'])
        elif plot_inbox['key'] == 'iver':
            self.xdata_iver.append(plot_inbox['lon'])
            self.ydata_iver.append(plot_inbox['lat'])
            self.line_iver.set_data(self.xdata_iver, self.ydata_iver)
        elif plot_inbox['key'] == 'predicted':
            self.x_p.append(plot_inbox['lon'])
            self.y_p.append(plot_inbox['lat'])
            self.scatter_prdctd.set_data(self.x_p, self.y_p)
        elif plot_inbox['key'] == 'simulation':
            self.x_simulation.append(plot_inbox['lon'])
            self.y_simulation.append(plot_inbox['lat'])
            self.line_simulation.set_data(self.x_simulation, self.y_simulation)
            
        # if plot_inbox['key'] == 'out':
        #     self.xdata.append(plot_inbox['lon'])
        #     self.ydata.append(plot_inbox['lat'])
        #     self.line_lead.set_data(self.xdata, self.ydata)
        
        return self.line_lead, self.line_iver, self.scatter_prdctd, self.line_simulation,


def main():
    root = tk.Tk()
    root.title('MAIN')
    root.iconbitmap('usm.ico')
    app = App(root)
    app.pack()
    root.mainloop()


if __name__ == '__main__':
    main()
