import threading

import datetime

import serial
import functions
from queue import Queue

rf_port = 'COM4'

ser_rf = serial.Serial(rf_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1, xonxoff=0)

iver = '3089'

send_through_rf_every = 2

def read_rf():
    """Read RF port"""
    ser_rf.reset_input_buffer()
    send_through_rf()
    osi_rec, osd_ak = 0, 0
    while True:
        try:
            frm_iver = ser_rf.readline().decode()
            if len(frm_iver) > 1:
                if functions.received_stream(frm_iver) == 'osi':
                    osi_return = functions.osi(frm_iver)
                    if functions.osi(frm_iver) is not None:
                        print(datetime.datetime.now(), ': RF: lat:', osi_return['Latitude'],
                              'lng:', osi_return['Longitude'], ', speed:', osi_return['Speed'],
                              ', Battery:', osi_return['Battery'], ', nxtWP:', osi_return['NextWp'],
                              ', DistantNxt WP: ', osi_return['DistanceToNxtWP'])
                        print(datetime.datetime.now(), f': OSI received RF: {osi_rec} / requested: {rf_i}')
                        osi_rec += 1
                elif functions.received_stream(frm_iver) == 'osdAck':
                    if functions.osd_ack(frm_iver) == 0:
                        print(datetime.datetime.now(), ': OSI Ack received RF ', osd_ak)
                        osd_ak += 1
        except Exception as e:
            # q_log.put([datetime.datetime.now().strftime("%H:%M:%S:%f"), ':', e])
            ser_rf.reset_input_buffer()
            continue
rf_i = 0
def send_through_rf():
    # send_through_ac_every = 15
    inst_snd = '$AC;Iver3-' + iver + ';' + '$' + functions.osd() + '\r\n'
    ser_rf.reset_output_buffer()
    ser_rf.write(inst_snd.encode())
    global rf_i
    print(datetime.datetime.now(), ': Sending through RF: ', rf_i)
    rf_i += 1
    threading.Timer(send_through_rf_every, send_through_rf).start()

read_rf()