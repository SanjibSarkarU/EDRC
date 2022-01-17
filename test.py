# import functions as fn
#
# data = '$GPGLL,3001.0378,N,08937.806599999999996,W,104129,A,A*6E'
#
# data = data.rstrip('\r\n')
# # print(data)
# print(fn.gpglldecode(data))
import numpy as np
import pymap3d as pm
from scipy import stats
from geographiclib.geodesic import Geodesic


def point_on_line(a, b, p):
    ap = p - a
    ab = b - a
    result = a + np.dot(ap, ab) / np.dot(ab, ab) * ab
    return result


def heading(x, y):
    geod = Geodesic(6378388, 1 / 297.0)
    if not hasattr(heading, 'data'):
        heading.data = np.empty((y, len(x))) * np.nan
        heading.count = 0
        heading.e = heading.n = heading.u = np.empty(y) * np.nan
        heading.h = np.zeros(y)
    heading.data[0] = x
    heading.lat0, heading.ln0 = heading.data[heading.count][0], heading.data[heading.count][1]
    ' Convert to cartesian coordinate'
    heading.e[0], heading.n[0], heading.u[0] = pm.geodetic2enu(
        heading.data[0][0], heading.data[0][1], heading.h[heading.count],
        heading.lat0, heading.ln0, heading.h[heading.count], ell=None, deg=True)
    lat1, lng1 = heading.data[0][0], heading.data[0][1]
    lat2, lng2 = heading.data[heading.count][0], heading.data[heading.count][1]

    if heading.count > 1:
        p1 = np.array([heading.e[0], heading.n[0]])
        p2 = np.array([heading.e[heading.count], heading.n[heading.count]])
        # heading.e = heading.e[~np.isnan(heading.e)]
        # heading.n = heading.n[~np.isnan(heading.n)]
        ' Apply linear regression'
        slope, intercept, r_value, p_value, std_err = stats.linregress(np.array(heading.e[0:heading.count]),
                                                                       np.array(heading.n[0:heading.count]))
        # line = list(map(lambda b: intercept + slope * b, heading.e))
        line = intercept + slope * heading.e
        'perpendicular on the '
        a = np.array([heading.e[0], line[0]])
        b = np.array([heading.e[heading.count], line[heading.count]])
        x_1, y_1 = point_on_line(a, b, p1)
        x_2, y_2 = point_on_line(a, b, p2)
        'Back to the lat lng'
        lat1, lng1, _h1 = pm.enu2geodetic(x_1, y_1, heading.h[heading.count], heading.lat0, heading.ln0,
                                          heading.h[heading.count], ell=None, deg=True)
        lat2, lng2, _h2 = pm.enu2geodetic(x_2, y_2, heading.h[heading.count], heading.lat0, heading.ln0,
                                          heading.h[heading.count], ell=None, deg=True)
    tme_start = str(heading.data[heading.count][-1])
    tme_last =  str(heading.data[0][-1])
    d = geod.Inverse(float(lat1), float(lng1), float(lat2), float(lng2))
    distance = d['s12']
    ha = d['azi2']
    time_diff = (int(tme_last[0:2]) * 3600 + int(tme_last[2:4]) * 60 + float(tme_last[4:])) - \
                (int(tme_start[0:2]) * 3600 + int(tme_start[2:4]) * 60 + float(tme_start[4:]))
    try:
        speed = distance / time_diff
        # result = {'speed': speed, 'ha': ha, 'dis12': distance}
    except ZeroDivisionError:
        print('Time differences is zero.')
        speed = 0
    result = {'lat1': lat1, 'lng1': lng1, 'tme1': float(tme_start),
              'lat2': lat2, 'lng2': lng2, 'tme2': float(tme_last),
              'speed': speed, 'ha': ha, 'dis12': distance}

    heading.data = np.roll(heading.data, 1, axis=0)  # roll trough axis
    heading.e = np.roll(heading.e, 1)
    heading.n = np.roll(heading.n, 1)
    heading.u = np.roll(heading.u, 1)
    heading.count = heading.count if heading.count >= y-1 else heading.count + 1
    return result


if __name__ == '__main__':
    # for i in range(1, 10):
    #     print(heading(x=[i, i + 2, i + 3], y=3))
    import pandas as pd

    daa = pd.read_csv('20220104-212027-UTC_0-CAT3-IVER3-3089.log', header=0, delimiter=';')
    lat = daa['Latitude']
    lng = daa['Longitude']
    tme = daa['Time']

    for i in range(1, 20):
        print(heading(x=[lat[i], lng[i], ''.join(tme[i].split(':'))], y=9))
