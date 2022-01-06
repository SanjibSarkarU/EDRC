__author__ = 'Sanjib Sarkar'
__copyright__ = ''
__credits__ = ['', '']
__license__ = ''
__version__ = '1.0.0'
__date__ = '01/06/2022'
__maintainer__ = 'Sanjib Sarkar'
__email__ = 'sanjib.sarkar@usm.edu'
__status__ = 'Prototype'

from time import monotonic
import time
import geopy.distance
import serial
import pandas as pd
import numpy as np
import re
import warnings
from geographiclib.geodesic import Geodesic
import numpy.polynomial.polynomial as poly
import pymap3d as pm
from scipy import stats


def check_sum(instruction):
    """ Remove any newlines and $ and calculate checksum """
    if re.search("\n$", instruction):
        instruction = instruction[:-1]
    if re.search("\r$", instruction):
        instruction = instruction[:-1]
    if re.search("\$", instruction):
        instruction = instruction[1:]
    nmeadata, cksum = re.split('\*', instruction)
    calc_cksum = 0
    for s in nmeadata:
        calc_cksum ^= ord(s)
    """ Return the calculated checksum """
    return '{:02X}'.format(calc_cksum)


def received_stream(stream):
    if stream == '':
        # print(" Waiting")
        return 'None'
    else:
        if re.search("ACK", stream):
            acknowledgement = {'8': 'osdAck', '16': 'omwAck'}
            return acknowledgement[stream.split(';')[-1].split(',')[1]]
        elif re.search("OSI", stream):
            return 'osi'
        elif re.search("OSD", stream):
            return 'osd'
        elif re.search("OMW", stream):
            return 'omw'
        else:
            return 'not known keyword'


def omw_ack(stream):
    # print("omw_ack section: ", stream)
    rec_chksm = stream.split('*')[-1][0:3]
    cal_chksm = check_sum(stream.split(';')[-1][1:-2])
    if int(rec_chksm, 16) == int(cal_chksm, 16):
        # print('Right checksum')
        if int(stream.split(',')[2]) == 0:
            # print('The IVER has acknowledged the OMW command without an error')
            return 0
        else:
            # print(stream)
            print('The IVER has raised an error to execute the OMW command')
            return 1
    
    else:
        print('wrong checksum')
        print('Received checkSum: ' + rec_chksm + 'Calculated checkSum: ' + cal_chksm)


def osi(stream):
    try:
        # print(stream)
        if int(stream.split('*')[-1], 16) == int(check_sum(stream.split(';')[-1][1:-2]), 16):
            # print('Right checkSum')
            stream = stream.split(',')
            mode = {'N': 'Normal_UVC', 'S': 'Stopped', 'P': 'Parking',
                    'M': 'Manual_Override', 'mP': 'Manual_parking',
                    'A': 'Servo', 'W': 'Waypoint'}
            # print('Mode : {}'.format(mode[stream[2]]))
            # print('NextWp: ', stream[3])
            # print('Latitude: ', stream[4])
            # print('Longitude: ', stream[5])
            # print('Speed: {} Knots'.format(stream[6]))
            # print("Distance to next WP: {} meters".format(stream[7]))
            # print('Battery percent: ', stream[16])
            # osi_return = (stream[3], stream[4], stream[5], stream[6], stream[7], stream[16])
            osi_return = {'NextWp': stream[3], 'Latitude': float(stream[4]), 'Longitude': float(stream[5]),
                          'Speed': float(stream[6]), 'DistanceToNxtWP': float(stream[7]), 'Battery': float(stream[16])}
            # return mode[stream[2]], stream[3]
            return osi_return
        else:
            print('Wrong checkSum')
            print("Received checkSum: " + str(stream.split('*')[-1]) + 'Calculated checksum is : ' + str(
                check_sum(stream.split(';')[-1][1:-2])))
            print(" Wrong CheckSum: ", stream)
            # osi_return = {'NextWp': 0, 'Latitude': 00.00000, 'Longitude': 00.00000,
            #               'Speed': 0.00, 'DistanceToNxtWP': 0.00, 'Battery': 0.00}
            return None
    except Exception as osi_exception:
        print("Error: ", osi_exception)
        # osi_return = {'NextWp': 0, 'Latitude': 00.00000, 'Longitude': 00.00000,
        #               'Speed': 0.00, 'DistanceToNxtWP': 0.00, 'Battery': 0.00}
        return None


def osd():
    ins_osd = 'OSD,,,S,,,,,*'
    instruction = ins_osd + check_sum(ins_osd)
    return instruction


def osd_req_recvd(stream):
    stream = stream.strip()
    # print(stream)
    if int(stream.split('*')[-1], 16) == int(check_sum(stream.split(';')[-1][1:-2]), 16):
        # print(" right Check Sum")
        return 0
    else:
        print("wrong CheckSum")
        return 1


def osd_ack(stream: str):
    # print("osd_ack section: ", stream)
    rec_chksm = stream.split('*')[-1][0:3]
    cal_chksm = check_sum(stream.split(';')[-1][1:-2])
    if int(rec_chksm, 16) == int(cal_chksm, 16):
        # print('Right checksum')
        if int(stream.split(',')[2]) == 0:
            # print('The IVER has acknowledged the OSD command without an error.')
            return 0
        else:
            print('The IVER has raised an error to execute the OSD command')
            return 1
    
    else:
        print('wrong checksum')
        print('Received checkSum: ' + rec_chksm + 'Calculated checkSum: ' + cal_chksm)


def omw_stop():
    ins_omw_stop = 'OMW,STOP*'
    instruction = ins_omw_stop + check_sum(ins_omw_stop)
    return instruction


def omw_req_recvd(stream):
    # assert f"{stream} is not string"
    # $AC;Iver3-3089;$OMW,30.35197,-89.62897,0.0,,10,4.0,0, *64
    stream = stream.strip()
    # print(stream)
    if int(stream.split('*')[-1], 16) == int(check_sum(stream.split(';')[-1][1:-2]), 16):
        # print(" right Check Sum")
        return 0
    else:
        print("OMW Request Received: wrong CheckSum")
        return 1


def wamv_gpgll(stream):
    if int((stream.split('*')[-1]), 16) == int(check_sum(stream.split('*')[0] + '*'), 16):
        # print("right CheckSum")
        return 0
    else:
        print("Wamv_gpgll: Wrong CheckSum: received checkSum{}, calculated checkSum{}".format(
            stream.split('*')[-1], check_sum(stream.split('*')[0] + '*')))
        return 1


# ddm = degree, decimal minutes, dd = degree decimal
def ddm2dd(coordinates):
    """ Convert degree, decimal minutes to degree decimal; return 'Lat_dd': float(lat_dd), 'Lng_dd': float(lng_dd)}
    Input Ex.:  ['3020.1186383580', 'N', '0894.5222887340', 'W'],
    return: {'Lat_dd': float(lat_dd), 'Lng_dd': float(lng_dd)} """
    lat, lat_direction, lng, lng_direction = coordinates[0], coordinates[1], coordinates[2], coordinates[3]
    lat = lat[1:] if lat.startswith('0') else lat
    lat_ddm = lat[:2] + str(float(lat[2:]) / 60)[1:]
    lat_dd = '{}'.format(lat_ddm if lat_direction == 'N' else '-' + lat_ddm)
    lng = lng[1:] if lng.startswith('0') else lng
    lng_ddm = lng[:2] + str(float(lng[2:]) / 60)[1:]
    lng_dd = '{}'.format(lng_ddm if lng_direction == 'E' else '-' + lng_ddm)
    dd = {'Lat_dd': float(lat_dd), 'Lng_dd': float(lng_dd)}
    return dd


def dd2ddm(coordinates):
    """ Convert degree decimal to degree decimal minute;
     return: {'Lat_ddm': lat_ddm, 'N_S': 'S' if lat_sign else 'N',
           'Lng_ddm': lng_ddm, 'E_W': 'W' if lng_sign else 'E'}"""
    lat, lng = str(coordinates[0]), str(coordinates[1])
    lat_sign = lat.startswith('-')
    lat = '{}'.format(lat[1:] if lat.startswith('-') else lat)
    lat_ddm = lat[:2] + str(float(lat[2:]) * 60)
    lng_sign = lng.startswith('-')
    lng = '{}'.format(lng[1:] if lng.startswith('-') else lng)
    lng_ddm = lng[:2] + str(float(lng[2:]) * 60)
    lng_ddm = lng_ddm.zfill(len(lng_ddm) + 1)
    ddm = {'Lat_ddm': lat_ddm, 'N_S': 'S' if lat_sign else 'N',
           'Lng_ddm': lng_ddm, 'E_W': 'W' if lng_sign else 'E'}
    return ddm


def speed_ha_coordinates(coordinate1_withtimestamp, coordinate2_withtimestamp):
    """ Return heading angle, speed, and distance;
    input:coordinates with timestamp: ['30.35059', '-89.62995', '104139'],
                                      ['30.35059', '-89.62995', '104139'] """

    geod = Geodesic(6378388, 1 / 297.0)
    co1 = coordinate1_withtimestamp[0:2]
    co1_time = coordinate1_withtimestamp[-1]
    co2 = coordinate2_withtimestamp[0:2]
    co2_time = coordinate2_withtimestamp[-1]
    # l = geod.InverseLine(lat1, lng1, lat2, lng2)
    d = geod.Inverse(float(co1[0]), float(co1[1]), float(co2[0]), float(co2[1]))
    # print(d)
    distance = d['s12']
    ha = d['azi2']
    time_diff = (int(co2_time[0:2]) * 3600 + int(co2_time[2:4]) * 60 + int(co2_time[4:])) - \
                (int(co1_time[0:2]) * 3600 + int(co1_time[2:4]) * 60 + int(co1_time[4:]))
    # print(time_diff)
    # speed = distance / time_diff
    # result = {'speed': speed, 'ha': ha, 'dis12': distance}
    try:
        speed = distance / time_diff
        result = {'speed': speed, 'ha': ha, 'dis12': distance}
    except ZeroDivisionError:
        print('Time difference between two coordinates is zero.')
        result = None
    return result


def distance_in_m(coordinate_1, coordinate_2):
    return str(round(geopy.distance.GeodesicDistance(coordinate_1, coordinate_2).m, 1))


def haSpeed_ply(df):
    """ fitting ha & speed, example input: [[30.35158, -89.6296, '104511'], [30.3516, -89.62957, '104513'],
     [30.35162, -89.62954, '104515']]  """
    df = pd.DataFrame(df, columns=['lat', 'lon', 't'])
    # df['dt'] = df.t.diff()
    df['latlng'] = df[['lat', 'lon', 't']].values.tolist()
    ha, speed = [], []
    for i in range(len(df.latlng) - 1):
        h = speed_ha_coordinates(df.latlng[i], df.latlng[i + 1])
        # ha.append(h['ha'] + 360 if h['ha'] < 0 else np.nan if h['ha'] == 0 else h['ha'])
        ha.append(np.absolute(h['ha']) if h['ha'] < 0 else np.nan if h['ha'] == 0 else h['ha'])
        speed.append(h['speed'])
    ha.append(0)
    speed.append(0)
    df['speed'] = speed
    df['ha'] = ha
    # print(df)
    df = df[df['speed'].notna()]
    df = df[df['ha'].notna()]
    df = df.drop(df.index[len(df) - 1])
    # df['speed_'] = df['speed'].apply(lambda x: np.abs(x - df['speed'].mean()) / df['speed'].std())
    # print(df)
    deg = 5
    np_speed = df['speed'].to_numpy(dtype=np.float32)
    np_ha = df['ha'].to_numpy(dtype=np.float32)
    np_t = df['t'].to_numpy(dtype=np.float32)
    x = np.linspace(0, len(np_ha), len(np_ha))
    warnings.simplefilter('ignore', np.RankWarning)
    model_ha = np.poly1d(np.polyfit(x, np_ha, deg=deg))
    line_speed = np.linspace(x[0], x[-1], num=len(x) * 10)
    predict_ha = model_ha(len(np_ha))
    
    x = np.linspace(0, len(np_speed), len(np_speed))
    model_speed = np.poly1d(np.polyfit(x, np_speed, deg=deg))
    line_speed = np.linspace(x[0], x[-1], num=len(x) * 10)
    p_speed = model_speed(len(np_speed))
    
    coefs = poly.polyfit(x, np_speed, 4)
    x_new = np.linspace(x[0], x[-1], num=len(x) * 10)
    ffit = poly.polyval(x_new, coefs)
    result = {'speed': p_speed, 'ha': predict_ha}
    return result


def point_on_line(a, b, p):
    ap = p - a
    ab = b - a
    result = a + np.dot(ap, ab) / np.dot(ab, ab) * ab
    return result


def coordinate_fit(df, deg=1):
    """ Fitting coordinates; takes coordinates and return 2 coordinates with timestamp. Return
    [[lat1, lng1, t1], [lat2, lng2, t2]"""
    df = pd.DataFrame(df, columns=['lat', 'lon', 't'])
    df['h'] = df.apply(lambda h: 0, axis=1)
    ' Convert to cartesian coordinate'
    x_c, y_c, Az = [], [], []
    for i in range(len(df.lat)):
        l, n, a = pm.geodetic2enu(df.lat[i], df.lon[i], df.h[i], df.lat[0], df.lon[0], df.h[0], ell=None, deg=True)
        x_c.append(l)
        y_c.append(n)
    df['x_c'], df['y_c'] = x_c, y_c
    # df['Azm'] = Az
    m, n = df['x_c'], df['y_c']
    p1, p2 = np.array([df.x_c[0], df.y_c[0]]), np.array([df.x_c[len(df.x_c) - 1], df.y_c[len(df.x_c) - 1]])
    
    ' Apply linear regression'
    slope, intercept, r_value, p_value, std_err = stats.linregress(m, n)
    line = list(map(lambda b: intercept + slope * b, m))
    df['line'] = line
    'perpendicular on the '
    a = np.array([df['x_c'][0], df['line'][0]])
    b = np.array([df.x_c[len(df['x_c']) - 1], df.line[len(df['line']) - 1]])
    x_1, y_1 = point_on_line(a, b, p1)
    x_2, y_2 = point_on_line(a, b, p2)
    'Back to the lat lng'
    lat1, lng1, _h1 = pm.enu2geodetic(x_1, y_1, df.h[0], df.lat[0], df.lon[0], df.h[0], ell=None, deg=True)
    lat2, lng2, _h2 = pm.enu2geodetic(x_2, y_2, df.h[0], df.lat[0], df.lon[0], df.h[0], ell=None, deg=True)
    result = [[lat1, lng1, df.t[0]], [lat2, lng2, df.t[len(df.t) - 1]]]
    return result


def iver_status(iver='3089', port_rf='com7', port_ac='com4', time_out=1, time_wait_ac=14):
    try:
        osi_return = {'NextWp': 0, 'Latitude': 00.00000, 'Longitude': 00.00000,
                      'Speed': 0.00, 'DistanceToNxtWP': 0.00, 'Battery': 0.00}
        # time_wait = 14  # fetch this data from iverVariables.txt, we get responses after 12 sec.
        t_start = monotonic()
        count = 0
        try:
            ser_rf = serial.Serial(port_rf, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=time_out,
                                   xonxoff=0)
            ser_rf.reset_output_buffer()
        except Exception as e_rf:
            print("I am in the RF com port exception block.", e_rf)
            print("Will send through ACOMM...... ")
            ser_rf_open = 'notOpen'
        else:
            ser_rf_open = 'open'
        try:
            ser_ac = serial.Serial(port_ac, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=time_out,
                                   xonxoff=0)
            ser_ac.reset_output_buffer()
        except Exception as e_ac:
            print("I am in the AC com port exception block. ", e_ac)
            ser_ac_open = 'notOpen'
        else:
            ser_ac_open = 'open'
        break_innerloop = 'no'
        while ser_rf_open == 'open' or ser_ac_open == 'open':
            try:
                time.sleep(1)
                if ser_rf_open == 'open':
                    inst_snd = '$AC;Iver3-' + iver + ';' + '$' + osd() + '\r\n'
                    ser_rf.reset_output_buffer()
                    ser_rf.write(inst_snd.encode())
                    frm_iver = ser_rf.readline().decode()
                    frm_iver_OSDAck = ser_rf.readline().decode()
                if ser_rf_open == 'open' and len(frm_iver) >= 1:  # if rf com port is open and responded through rf comm
                    if received_stream(frm_iver_OSDAck) == 'osdAck' and osd_ack(frm_iver_OSDAck) == 0:
                        if received_stream(frm_iver) == 'osi':
                            osi_return = osi(frm_iver)
                            break
                    else:
                        count += 1
                # something other than osdAck and osi
                elif ser_ac_open == 'open' and (ser_rf_open == 'notOpen' or len(frm_iver) < 1) and \
                        monotonic() - t_start >= time_wait_ac:  # send osd through ac comm
                    # print("Sent")
                    inst_snd = '$AC;Iver3-' + iver + ';' + '$' + osd() + '\r\n'
                    ser_ac.write(inst_snd.encode())
                    print("Sent")
                    i = 0
                    print("waiting for a response from the Iver...")
                    while True:
                        frm_iver = ser_ac.readline().decode()
                        frm_iver_OSDAck = ser_ac.readline().decode()
                        # print(frm_iver, frm_iver_OSDAck)
                        if received_stream(frm_iver_OSDAck) == 'osdAck' and osd_ack(frm_iver_OSDAck) == 0:
                            if received_stream(frm_iver) == 'osi':
                                osi_return = osi(frm_iver)
                                # print(osi_return)
                                t_start = monotonic()
                                i = 0
                                break_innerloop = 'yes'
                                break
                        else:
                            print(i)
                            i += 1
                            if i == 15:  # wait 15 sec to get the response from the iver through AC;can fetch data from file
                                break
                            else:
                                continue
                else:
                    if break_innerloop == 'yes':
                        break
                    else:
                        continue
            except Exception as loop:
                print("I am in the exception loop block.", loop)
                ser_rf.reset_input_buffer()
                ser_ac.reset_input_buffer()
                continue
        
        return osi_return
    except Exception as iverStatus:
        return osi_return
