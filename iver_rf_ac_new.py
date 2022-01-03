import threading
import datetime
import tkinter as tk
from rasterio.plot import show
import rasterio
import serial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import animation
import matplotlib.pyplot as plt
from queue import Queue
import threadartists as ta
import functions


filepath = r"C:\Log_files"
time_now = datetime.datetime.now()
fileName = filepath + '\\' + "log-RF-AC-test" + str(time_now.year) + str(time_now.month) + str(time_now.day) + \
           str(time_now.hour) + str(time_now.minute) + ".txt"
log_file = open(fileName, "a")
q_log = Queue()

TIMEOUT_RF = 1
TIMEOUT_AC = 1
rf_port = str(input('RF COMPort: '))  # 'COM2'
ac_port = str(input('AC COMPort: '))  # 'COM5'

ser_rf = serial.Serial(rf_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=TIMEOUT_RF, xonxoff=0)
ser_ac = serial.Serial(ac_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=TIMEOUT_AC, xonxoff=0)

iver = '3072'

send_through_rf_every = 2  # int(input('How often send OSD through RF in sec: '))
send_through_ac_every = 20  # int(input('How often send OSD through AC in sec: '))


def read_rf():
    """Read RF port"""
    scatter_artist = ta.ScatterArtist(q_art, s=10, label='scatter plot', c='r', marker='o')
    ser_rf.reset_input_buffer()
    send_through_rf()
    osi_rec, osd_ak = 0, 0
    while True:
        try:
            frm_iver = ser_rf.readline().decode()
            if len(frm_iver) > 1:
                q_log.put([datetime.datetime.now().strftime("%H:%M:%S.%f"), ': RF: ', frm_iver])
                if functions.received_stream(frm_iver) == 'osi':
                    osi_return = functions.osi(frm_iver)
                    if functions.osi(frm_iver) is not None:
                        print(datetime.datetime.now(), ': RF: lat:', osi_return['Latitude'],
                              'lng: ', osi_return['Longitude'], 'speed:', osi_return['Speed'],
                              'Battery: ', osi_return['Battery'], 'nxtWP: ', osi_return['NextWp'],
                              'DistantNxt WP: ', osi_return['DistanceToNxtWP'])
                        scatter_artist.add_data_to_artist((osi_return['Longitude'], osi_return['Latitude']))
                        q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ':', osi_return])
                        print(datetime.datetime.now(), f': OSI received RF: {osi_rec} / requested: {rf_i}')
                        osi_rec += 1
                elif functions.received_stream(frm_iver) == 'osdAck':
                    if functions.osd_ack(frm_iver) == 0:
                        q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ':', 'OSD Ack RF', osd_ak])
                        print(datetime.datetime.now(), ': OSI Ack received RF ', osd_ak)
                        osd_ak += 1
        except Exception as e:
            q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ':', e])
            ser_ac.reset_input_buffer()
            continue


def read_ac():
    """ Reading AC port """
    scatter_artist_ac = ta.ScatterArtist(q_art, s=10, label='scatter plot', color='b', marker='*')
    ser_ac.reset_input_buffer()
    send_through_ac()
    osi_rec, osd_ak = 0, 0
    while True:
        try:
            frm_iver = ser_ac.readline().decode()
            if len(frm_iver) > 1:
                q_log.put([datetime.datetime.now().strftime("%H:%M:%S.%f"), ': AC: ', frm_iver])
                if functions.received_stream(frm_iver) == 'osi':
                    osi_return = functions.osi(frm_iver)
                    if functions.osi(frm_iver) is not None:
                        print(datetime.datetime.now(), ': RF: lat:', osi_return['Latitude'],
                              'lng: ', osi_return['Longitude'], 'speed:', osi_return['Speed'],
                              'Battery: ', osi_return['Battery'], 'nxtWP: ', osi_return['NextWp'],
                              'DistantNxt WP: ', osi_return['DistanceToNxtWP'])
                        scatter_artist_ac.add_data_to_artist((osi_return['Longitude'], osi_return['Latitude']))
                        q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ':', osi_return])
                        print(datetime.datetime.now(), f': OSI received AC: {osi_rec} / requested: {ac_i}')
                        osi_rec += 1
                elif functions.received_stream(frm_iver) == 'osdAck':
                    if functions.osd_ack(frm_iver) == 0:
                        q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ':', 'OSD Ack', osd_ak])
                        print(datetime.datetime.now(), ': OSI Ack received AC', osd_ak)
                        osd_ak += 1
        except Exception as e:
            q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ':', e])
            ser_ac.reset_input_buffer()
            continue


rf_i = 0


def send_through_rf():
    # send_through_ac_every = 15
    threading.Timer(send_through_rf_every, send_through_rf).start()
    inst_snd = '$AC;Iver3-' + iver + ';' + '$' + functions.osd() + '\r\n'
    ser_rf.reset_output_buffer()
    ser_rf.write(inst_snd.encode())
    global rf_i
    print(datetime.datetime.now(), ': Sending through RF: ', rf_i)
    q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ': send trough RF: ', rf_i])
    rf_i += 1


ac_i = 0


def send_through_ac():
    # send_through_ac_every = 25
    threading.Timer(send_through_ac_every, send_through_ac).start()
    inst_snd = '$AC;Iver3-' + iver + ';' + '$' + functions.osd() + '\r\n'
    ser_ac.reset_output_buffer()
    ser_ac.write(inst_snd.encode())
    global ac_i
    print(datetime.datetime.now(), ': Sending through AC: ', ac_i)
    # q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ': send trough AC: '])
    ac_i +=1


def init(ax):
    # 'Cat_Island_Low.tif', 'Stennis_QW.tif'
    with rasterio.open('Cat_Island_Low.tif', driver='GTiff') as data:
        im = show(data, ax=ax)
        print(data.profile)
    return []


def log_data():
    while True:
        log = q_log.get()
        log_file.write(str(log) + '\n')
        log_file.flush()


if __name__ == '__main__':
    q_art = Queue(maxsize=0)

    root = tk.Tk()
    root.wm_title("RF-AC_COMM_IVER")

    fig = plt.Figure()
    ax = fig.add_subplot()

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    button = tk.Button(master=root, text="Quit", command=root.quit)
    button.pack(side=tk.BOTTOM)

    toolbar = NavigationToolbar2Tk(canvas, root, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    threading.Thread(target=read_rf, daemon=True).start()
    threading.Thread(target=read_ac, daemon=True).start()
    threading.Thread(target=log_data, daemon=True).start()

    anim = animation.FuncAnimation(fig, ta.animate, frames=ta.artist_manager(ax, fig, q_art),
                                   init_func=lambda: init(ax), interval=50, blit=True, repeat=True)

    tk.mainloop()