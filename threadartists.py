"""
A library to allow the sending of artists from threads to matplotlib.animation.FuncAnimation
During registration of the various X_Artits objects, the artists get registered by the
ArtistManager function. When an object gets out of scope, the artist gets deleted from
the list of artists.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
import threading
import logging
import time
from matplotlib import pyplot as plt
import numpy as np
import queue
import rasterio
from matplotlib import transforms

__author__ = 'Gero Nootz'
__copyright__ = ''
__credits__ = ['', '']
__license__ = ''
__version__ = '1.0.0'
__date__ = '12/26/2021'
__maintainer__ = 'Gero Nootz'
__email__ = 'gero.nootz@usm.edu'
__status__ = 'Prototype'


class Add_del_art(Enum):
    add = auto()
    delete = auto()

class Artist(ABC):
    """
    Abstract base class for sending a new artist to artist_manager() function to be added to a list of artists
    When the destructor of Artist(ABC) is called the artist is deleted from the
    list of artists. !! However, deleting is currently not working reliably (and I
    do not know why) !!
    """

    def __init__(self, q_art, **kwargs):
        self.q_art = q_art
        self.kwargs = kwargs
        self.add_or_del_artist = Add_del_art.add
        self.artist_exsits = False
        self.art_data = np.array([], dtype=float).reshape(0, 2)
        self.q_art.put(self)
        while self.artist_exsits == False: # wait for artist cration 
            time.sleep(0.1)

    def __del__(self):
        self.add_or_del_artist = Add_del_art.delete
        self.q_art.put(self)
        while self.artist_exsits == True: #wait for deletion of artist by artist_manager()
            time.sleep(0.1)   

    @abstractmethod
    def create_artist(self):
        pass

    @abstractmethod
    def add_data_to_artist(self, new_data):
        pass

    @abstractmethod
    def clear_data(self):
        pass

    def register_ax(self, ax: plt.axes):
            self.ax = ax

    def register_fig(self, fig: plt.figure):
        self.fig = fig
    
    def set_artist_exsits(self, artist_exsits):
        self.artist_exsits = artist_exsits

    def set_xlim(self, min: float, max: float):
        """ set x axis limits"""
        self.ax.set_xlim(min, max)
        self.fig.canvas.draw()

    def set_ylim(self, min: float, max: float):
        """ set y axis limits"""
        self.ax.set_ylim(min, max)
        self.fig.canvas.draw()

class ImageArtist(Artist):
    """ 
    Create an image artist and send the artist_maager() function.
    Manipulate the data from within a thread using the methods provided, e.g., 
    add_data_to_artist()
    """

    def create_artist(self):
        self.artist = self.ax.imshow([[]], origin='upper',
                zorder=10, animated=True, **self.kwargs)
        # print(plt.getp(self.artist))
        # print(plt.getp(ax))
        return self.artist

    def add_data_to_artist(self, fname: str, size: float, position):
        
        # print('pos: ', position)
        self.size = size
        left, right = self.ax.get_xlim() 
        bottom, top = self.ax.get_ylim()

        del_x = (right - left)*self.size
        del_y = (top - bottom)*self.size
        aspect = del_x/del_y  
        aspect = 1 
        left = -del_x + position[0]
        right = del_x + position[0]
        bottom = -del_x*aspect + position[1]
        top = del_x*aspect + position[1]
        # print('LRBT1: ', left, right, bottom, top)        
        plt.setp(self.artist, extent=(left, right, bottom, top))
        self.image = plt.imread(fname)
        self.artist.set_array(self.image)
    
    def set_position(self, position, deg):
        # print('pos: ', position)
        left, right = self.ax.get_xlim() 
        bottom, top = self.ax.get_ylim()

        del_x = (right - left)*self.size
        del_y = (top - bottom)*self.size
        aspect = del_x/del_y         
        aspect = 1 
        left = -del_x + position[0]
        right = del_x + position[0]
        bottom = -del_x*aspect + position[1]
        top = del_x*aspect + position[1]

        trans_data = transforms.Affine2D().rotate_deg_around(
            position[0], position[1], deg) + self.ax.transData
        self.artist.set_transform(trans_data)
        # print('LRBT: ', left, right, bottom, top)
        plt.setp(self.artist, extent=(left, right, bottom, top))
        
        
    def clear_data(self):
        self.artist.set_array([[]])
        pass

class GeoTifArtist(Artist):
    """ 
    Create an GeoTif artist and send the artist_maager() function.
    Manipulate the data from within a thread using the methods provided, e.g., 
    add_data_to_artist()
    """
    
    def create_artist(self):
        self.artist = self.ax.imshow([[]], extent=(
                                         0, 1, 0, 1), origin='upper', **self.kwargs)
        # self.artist = self.ax.imshow([[]], origin='upper', zorder=10, animated=True)
        # print(plt.getp(self.artist))
        # print(plt.getp(ax))
        return self.artist

    def add_data_to_artist(self, fname: str):
        with rasterio.open(fname, driver='GTiff') as geotif: 
            if geotif.crs != 'EPSG:4326':
                logging.error('the file origon of %s is not EPSG:4326', fname)
                raise Warning('the file origon of the geotif is not EPSG:4326')  
            self.geotif_xlim=(geotif.bounds.left, geotif.bounds.right)
            self.geotif_ylim=(geotif.bounds.bottom, geotif.bounds.top)
            rgb = np.dstack((geotif.read(1), geotif.read(2), geotif.read(3)))
        
        plt.setp(self.artist, extent=(
            geotif.bounds.left, geotif.bounds.right, geotif.bounds.bottom, geotif.bounds.top))
        self.artist.set_array(rgb)
    
    def clear_data(self):
        self.artist.set_array([[]])
        pass

class ScatterArtist(Artist):
    """
    Create a scatter artist and send to the artist_manger() function.
    Manipulate the data from within a thread using the methods provided, e.g., 
    add_data_to_artist()
    """

    def create_artist(self):
        self.artist = self.ax.scatter([], [], animated=True, **self.kwargs)
        return self.artist

    def add_data_to_artist(self, new_data):
        self.art_data = np.vstack(
            [self.art_data, [[new_data[0], new_data[1]]]])
        self.artist.set_offsets(self.art_data)

    def clear_data(self):
        self.art_data = np.array([], dtype=float).reshape(
            0, 2)  # prepare (N,2) array
        self.artist.set_offsets(self.art_data)

class LineArtist(Artist):
    """ 
    Create a line plot artist and send to artist_manger() function.
    Manipulate the data from within a thread using the methods provided, e.g., 
    add_data_to_artist()
    """

    def create_artist(self):
        self.artist, = self.ax.plot([], [], animated=True, **self.kwargs)
        return self.artist

    def add_data_to_artist(self, new_data):
        self.art_data = np.vstack(
            [self.art_data, [[new_data[0], new_data[1]]]])
        self.artist.set_data(self.art_data[:, 0], self.art_data[:, 1])

    def clear_data(self):
        self.art_data = np.array([], dtype=float).reshape(
            0, 2)  # prepare (N,2) array
        self.artist.set_data(self.art_data[:, 0], self.art_data[:, 1])

def artist_manager(ax: plt.axes, fig: plt.figure,q_art: queue.Queue) -> list:
    """
    Collects new artists received from ABC Artist(ABC) via a queue
    into a list of artists to be animated in matplotlib.animation.FuncAnimation.
    When the destructor of Artist(ABC) is called the artist is deleted from the
    list of artists. !! However, deleting is currently not working reliably and I
    do not know why !!
    -> returns a list of artists
    """
    artists = []
    artist_ids: int = []
    i: int = 0

    while True:
        try:
            art_obj = q_art.get(False)
        except queue.Empty:
            pass
        else:
            if art_obj.add_or_del_artist == Add_del_art.add:
                logging.info('adding artist with label: %s', art_obj.kwargs['label'])
                art_obj.register_ax(ax)
                art_obj.register_fig(fig)
                artist = art_obj.create_artist()
                artist_ids.append(id(art_obj))
                artists.append(artist)
                art_obj.set_artist_exsits(True)
            elif art_obj.add_or_del_artist == Add_del_art.delete:
                logging.info('deleting artist with label: %s', art_obj.kwargs['label'])
                index = artist_ids.index(id(art_obj))
                del artist_ids[index]
                del artists[index]
                art_obj.set_artist_exsits(False)
            else:
                logging.error('not of enum type Add_del_art')

            art_obj = None # delete ref to object so destructor can be called
            q_art.task_done()


        yield artists

def animate(artists: list) -> list:
    """
    Receives a list of artists to be animated in matplotlib.animation.FuncAnimation
    -> returns the list of artists
    """
    return artists

def init():
    return []

if __name__ == '__main__':
    """
    Demonstrate how to update a matplotlib graph from inside a thread
    """
    import tkinter as tk
    from matplotlib.backends.backend_tkagg import (
        FigureCanvasTkAgg, NavigationToolbar2Tk)
    from matplotlib import animation

    logging.basicConfig(level=logging.INFO) # print to console
    # logging.basicConfig(filename='main.log', encoding='utf-8', level=logging.DEBUG) # append to file
    # logging.basicConfig(filename='example.log', filemode='w', level=logging.INFO) # overide file each run

    
    def plot_geotif(): 
        time.sleep(10)
        """Work in progress..."""
        artist = GeoTifArtist(q_art, label='GeoTif plot')
        artist.add_data_to_artist('Stennis_QW.tif')
        artist.set_xlim(artist.geotif_xlim[0], artist.geotif_xlim[1])
        artist.set_ylim(artist.geotif_ylim[0], artist.geotif_ylim[1])
        while True: 
            time.sleep(2)

    def plot_image(): 
        """Work in progress..."""
        # image = plt.imread('yota.png')    
        artist = ImageArtist(q_art, label='image plot')
        artist.add_data_to_artist('yota.png', 0.1, (1,0))
        while True: 
            data = np.random.rand(2)    
            new_xy = (data[0]*2, data[1]*2 - 1) 
            artist.set_position(new_xy, np.random.rand()*360)
            time.sleep(1)            

    def plot_rand_line(): 
        """ 
        Demonstrate how to plot a line artist from a thread
        """
        delay = np.random.rand()*10    
        sleep = np.random.rand() 
    
        artist = LineArtist(q_art, label='line plot')
        logging.debug('createdg artist %i for provide_line1', id(artist))

        time.sleep(delay)   

        i = 0
        while True:        
            data = np.random.rand(2)    
            new_xy = (data[0]*2, data[1]*2 - 1) 
            artist.add_data_to_artist(new_xy)
            if i%10 == 0:
                artist.clear_data()
            i += 1
            time.sleep(sleep)

    def plot_rand_scatter(): 
        """ 
        Demonstrates how to plot a scatter artist from a thread
        """
        delay = np.random.rand()*10    
        sleep = np.random.rand()         
        scatter_artist = ScatterArtist(q_art, s=60, marker='x', label='scatter plot')
        logging.debug('createdg artist %i for provide_scatter1', id(scatter_artist))
        time.sleep(delay) 
        i = 0
        while True:        
            data = np.random.rand(2)    
            new_xy = (data[0]*2, data[1]*2-1) 
            scatter_artist.add_data_to_artist(new_xy)
            if i%10 == 0:
                scatter_artist.clear_data()
            i += 1
            time.sleep(sleep)

    def plot_temp_scatter(): 
        '''
        Demonstrate deleting objects and with it removing  artistsclear
        after some time via the destructor
        '''

        delay = np.random.rand()*10
        sleep = np.random.rand() 

        scatter_artist = ScatterArtist(q_art, s=60, marker='o', label='temp scatter plot')
        logging.debug('createdg artist %i for provide_scatter2', id(scatter_artist))

        time.sleep(delay)
        
        for i in range(10):          
            data = np.random.rand(2)    
            new_xy = (data[0]*2, data[1]*2-1) 
            scatter_artist.add_data_to_artist(new_xy)
            time.sleep(sleep)     

    q_art = queue.Queue(maxsize=0)  

    root = tk.Tk()
    root.wm_title("Update mpl in Tk via queue")

    fig = plt.Figure()
    ax = fig.add_subplot(xlim=(0, 2), ylim=(-1.1, 1.1))
    ax.set_xlabel('x-data')
    ax.set_ylabel('y-data')
    # ax.axis('equal')

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    button = tk.Button(master=root, text="Quit", command=root.quit)
    button.pack(side=tk.BOTTOM)

    toolbar = NavigationToolbar2Tk(canvas, root, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    threading.Thread(target=plot_rand_line, daemon = True).start()        
    threading.Thread(target=plot_temp_scatter, daemon = True).start()        
    threading.Thread(target=plot_rand_scatter, daemon = True).start()        
    threading.Thread(target=plot_image, daemon = True).start()   
    threading.Thread(target=plot_geotif, daemon = True).start()   
    
    anim = animation.FuncAnimation(fig, animate, frames=artist_manager(ax, fig, q_art), init_func=init, 
                                                        interval=50, blit=True)
    tk.mainloop()