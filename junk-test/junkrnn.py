# import sys
# import tensorflow
# import keras
# import pandas as pd
# import numpy as np
# import math
# import random
# import matplotlib.pyplot as plt
#
#
# # print('System version: ', sys.version)
# # print('tensorflow version: ', tensorflow.__version__)
# # print('keras version: ', keras.__version__)
#
#
# def noisy_sin(steps_per_cycle=50, number_of_cycles=500, random_factor=0.4):
#     """
#     random_factor    : amont of noise in sign wave. 0 = no noise
#     number_of_cycles : The number of steps required for one cycle
#
#     Return :
#     pd.DataFrame() with column sin_t containing the generated sin wave
#     """
#     random.seed(0)
#     df = pd.DataFrame(np.arange(steps_per_cycle * number_of_cycles + 1), columns=["t"])
#     df["sin_t"] = df.t.apply(
#         lambda x: math.sin(x * (2 * math.pi / steps_per_cycle) + random.uniform(-1.0, +1.0) * random_factor))
#     df["sin_t_clean"] = df.t.apply(lambda x: math.sin(x * (2 * math.pi / steps_per_cycle)))
#     print("create period-{} sin wave with {} cycles".format(steps_per_cycle, number_of_cycles))
#     print("In total, the sin wave time series length is {}".format(steps_per_cycle * number_of_cycles + 1))
#     return df
#
#
# steps_per_cycle = 10
# df = noisy_sin(steps_per_cycle=steps_per_cycle, random_factor=0)
#
# n_plot = 8
# df[["sin_t"]].head(steps_per_cycle * n_plot).plot(title="Generated first {} cycles".format(n_plot), figsize=(15, 3))
import numpy as np
import matplotlib.pyplot as plt

X_train = np.arange(0, 100, 0.5)
y_train = np.sin(X_train)

X_test = np.arange(100, 200, 0.5)
y_test = np.sin(X_test)

n_features = 1

train_series = y_train.reshape((len(y_train), n_features))
test_series = y_test.reshape((len(y_test), n_features))

# fig, ax = plt.subplots(1, 1, figsize=(15, 4))
# ax.plot(X_train, y_train, lw=3, label='train data')
# ax.plot(X_test, y_test, lw=3, label='test data')
# ax.legend(loc="lower left")

from keras.preprocessing.sequence import TimeseriesGenerator

look_back = 20

train_generator = TimeseriesGenerator(train_series, train_series,
                                      length=look_back,
                                      sampling_rate=1,
                                      stride=1,
                                      batch_size=10)

test_generator = TimeseriesGenerator(test_series, test_series,
                                     length=look_back,
                                     sampling_rate=1,
                                     stride=1,
                                     batch_size=10)
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM

n_neurons = 4
model = Sequential()
model.add(LSTM(n_neurons, input_shape=(look_back, n_features)))
model.add(Dense(1))
model.compile(optimizer='adam', loss='mse')

model.fit(train_generator, epochs=300, verbose=0)

test_predictions  = model.predict(test_generator)


x = np.arange(110,200,0.5)
fig, ax = plt.subplots(1, 1, figsize=(15, 5))
ax.plot(X_train,y_train, lw=2, label='train data')
ax.plot(X_test,y_test, lw=3, c='y', label='test data')
ax.plot(x,test_predictions, lw=3, c='r',linestyle = ':', label='predictions')
ax.legend(loc="lower left")
plt.show()
plt.show()
