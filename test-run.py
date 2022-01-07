import functions as fn

data = '$GPGLL,3021.0378,N,08937.806599999999996,W,104129,A,A*6E'

data = data.rstrip('\r\n')
# print(data)
print(fn.gpglldecode(data))