# EDRC

https://stackoverflow.com/questions/43477681/how-to-speed-up-tkinter-embedded-matplot-lib-and-python
import Tkinter as tk import serial from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg from
matplotlib.figure import Figure from matplotlib import pyplot as plt import matplotlib.animation as animation from
collections import deque import random

HISTORY_LEN = 200

class App(tk.Frame):
def __init__(self, master=None, **kwargs):
tk.Frame.__init__(self, master, **kwargs)

        self.running = False
        self.ani = None

        btns = tk.Frame(self)
        btns.pack()

        lbl = tk.Label(btns, text="Number of points")
        lbl.pack(side=tk.LEFT)

        self.points_ent = tk.Entry(btns, width=5)
        self.points_ent.insert(0, '500')
        self.points_ent.pack(side=tk.LEFT)

        lbl = tk.Label(btns, text="update interval (ms)")
        lbl.pack(side=tk.LEFT)

        self.interval = tk.Entry(btns, width=5)
        self.interval.insert(0, '30')
        self.interval.pack(side=tk.LEFT)

        self.btn = tk.Button(btns, text='Start', command=self.on_click)
        self.btn.pack(side=tk.LEFT)

        self.fig = plt.Figure()
        self.ax1 = self.fig.add_subplot(111)
        self.line, = self.ax1.plot([], [], lw=2)
        self.canvas = FigureCanvasTkAgg(self.fig,master=master)
        self.canvas.show()
        self.canvas.get_tk_widget().pack()

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
        self.xdata = deque([], maxlen=HISTORY_LEN)
        self.ydata = deque([], maxlen=HISTORY_LEN)
        #~ self.arduinoData = serial.Serial('com5', 115200)
        #~ self.arduinoData.flushInput()
        self.points = int(self.points_ent.get()) + 1
        self.ani = animation.FuncAnimation(
            self.fig,
            self.update_graph,
            frames=self.points,
            interval=int(self.interval.get()),
            repeat=False)
        self.running = True
        self.btn.config(text='Pause')
        self.ani._start()

    def update_graph(self, i):
        self.xdata.append(i)
        #~ self.ydata.append(int(self.arduinoData.readline()))
        self.ydata.append(random.randrange(100)) # DEBUG
        self.line.set_data(self.xdata, self.ydata)
        self.ax1.set_ylim(min(self.ydata), max(self.ydata))
        self.ax1.set_xlim(min(self.xdata), max(self.xdata))
        if i >= self.points - 1:
            #~ self.arduinoData.close()
            self.btn.config(text='Start')
            self.running = False
            self.ani = None
        return self.line,

def main():
root = tk.Tk()
app = App(root)
app.pack()
root.mainloop()

if __name__ == '__main__':
main()

# tkinter Frame
https://stackoverflow.com/questions/45122244/having-frames-next-to-each-other-in-tkinter/45123029