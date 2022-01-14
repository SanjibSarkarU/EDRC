# import functions as fn
#
# data = '$GPGLL,3001.0378,N,08937.806599999999996,W,104129,A,A*6E'
#
# data = data.rstrip('\r\n')
# # print(data)
# print(fn.gpglldecode(data))
import numpy as np
import pandas as pd
import pymap3d as pm
from scipy import stats


def point_on_line(a, b, p):
    ap = p - a
    ab = b - a
    result = a + np.dot(ap, ab) / np.dot(ab, ab) * ab
    return result


def heading(x, y):
    if not hasattr(heading, 'data'):
        heading.data = np.empty((y, len(x))) * np.nan
        heading.df = pd.DataFrame([], columns=['Lat', 'Lon', 'tme'])
        heading.lat0, heading.ln0 = x[0], x[1]
        heading.count = 0
        heading.e, heading.n, heading.u = np.empty(y) * np.nan, np.empty(y) * np.nan, np.empty(y) * np.nan

    heading.count = heading.count if heading.count>=y else heading.count+1
    heading.data = np.roll(heading.data, len(x))
    heading.data[0] = x
    heading.e = np.roll(heading.e, 1)
    heading.n = np.roll(heading.n, 1)
    heading.u = np.roll(heading.u, 1)
    ' Convert to cartesian coordinate'
    heading.e[0], heading.n[0], heading.u[0] = pm.geodetic2enu(heading.data[0][0], heading.data[0][1], 0,
                                                               heading.lat0, heading.ln0, 0, ell=None, deg=True)
    p1, p2 = np.array([heading.e[0], heading.n[0]]), np.array([heading.e[heading.count-1], heading.n[heading.count-1]])

    ' Apply linear regression'
    # mask = ~np.isnan(heading.e) & ~np.isnan(heading.n)
    slope, intercept, r_value, p_value, std_err = stats.linregress(heading.e, heading.n)
    line = list(map(lambda b: intercept + slope * b, heading.e))

    'perpendicular on the '
    a = np.array([heading.e[0], line[0]])
    b = np.array([heading.e[heading.count-1], line[-1]])
    x_1, y_1 = point_on_line(a, b, p1)
    x_2, y_2 = point_on_line(a, b, p2)
    lat1, lng1, _h1 = pm.enu2geodetic(x_1, y_1, 0, heading.lat0, heading.ln0, 0, ell=None, deg=True)
    lat2, lng2, _h2 = pm.enu2geodetic(x_2, y_2, 0, heading.lat0, heading.ln0, 0, ell=None, deg=True)
    result = [[lat1, lng1, heading.data[0][-1]], [lat2, lng2, heading.data[-1][-1]]]

    return result


if __name__ == '__main__':
    for i in range(1, 10):
        print(heading(x=[i, i + 2, i + 3], y=3))

