from tkinter.constants import DISABLED, HORIZONTAL, NORMAL
from PIL import Image, ImageTk # numpy to GUI element
import tkinter as tk
from tkinter import ttk
import threading
import multiprocessing as mp
import numpy as np
import athesim_functions as asf
import time
from pycromanager import Bridge # camera control
import torch

class ML_App:
    def __init__(self,master):

        self.master = master
        tabControl = ttk.Notebook(self.master)
        master.geometry("800x620") # size of gui
        self.tab1 = ttk.Frame(tabControl)
        self.tab2 = ttk.Frame(tabControl)
        tabControl.add(self.tab1, text ='Tab 1')
        tabControl.add(self.tab2, text ='Tab 2')
        tabControl.pack(expand = 1, fill ="both")


        #Defining Queues needed for communication 
        self.stop_signal = mp.Queue()
        self.output = mp.Queue()
        self.stack = mp.Queue()

        
        self.live = tk.Button(self.tab1, width=10, text='Start', command = self.start_live)
        self.live.place(x=15, y=10)
        self.Stop_live = tk.Button(self.tab1, width=10, text='Stop', command = self.stop_live)
        self.Stop_live.place(x=15, y=40)
        blank = np.zeros((512,512))
        img =  ImageTk.PhotoImage(image=Image.fromarray(blank)) # image
        self.panel = tk.Label(self.tab1, image=img)
        self.panel.pack(side = "top")

        self.live_decon = tk.Button(self.tab1,width=10, text='Live ML-SIM', command = self.start_live) # start live sim
        self.live_decon.place(x=15, y=250)

        self.quit_button = tk.Button(self.tab1,width=10, text='Quit',command=self.quit_gui) # start live sim
        self.quit_button.place(x=15, y=250)       

        self.start_live_decon = tk.Button(self.tab1,width=10, text='Live ML-SIM', command = self.start_ml_sim) # start live sim
        self.start_live_decon.place(x=15, y=280)

        self.update_ROI = tk.Button(self.tab2,width=10, text='Update ROI') # start live sim
        self.update_ROI.place(x=15, y=220)

        self.expTime = tk.IntVar()
        self.expTime.set(30)
        self.exposure = tk.Entry(self.tab1,textvariable=self.expTime) # exposure time field
        self.exposure.place(x=20, y=130, width=50)
        self.exposure_label = tk.Label(self.tab1, text = "Exposure time (ms)")
        self.exposure_label.place(x = 15,y = 110)

        self.xOff = tk.IntVar()
        self.xOff.set(30)
        self.xoffset = tk.Entry(self.tab2,textvariable=self.xOff) # ROI input
        self.xoffset.place(x=20, y=174, width=50)
        self.xoffset_label = tk.Label(self.tab2, text = "ROI offset")
        self.xoffset_label.place(x = 15,y = 154)

        self.yOff = tk.IntVar()
        self.yOff.set(30)
        self.yoffset = tk.Entry(self.tab2,textvariable=self.yOff) # ROI input
        self.yoffset.place(x=20, y=195, width=50)
        
        if not torch.cuda.is_available():
            self.start_live_decon['state'] = DISABLED
            print('A valid GPU is required for live ML-SIM')
        else:
            dev = torch.cuda.get_device_name(0)
            print('Using device:')
            print(dev)
        
    def update_roi(self):
        xOffset = self.xOff.get() # get ROI variables from the GUI input
        yOffset = self.yOff.get()
        if xOffset < 1500 and yOffset < 1500: # make sure ROI is valid
            self.stop_live()
            time.sleep(0.1) #wait for other processes to stop
            with Bridge() as bridge: # load camera control library
                core = bridge.get_core()
                ROI = [xOffset, yOffset, 512, 512] # build ROI 
                core.set_roi(*ROI) # set ROI    
        
    def start_live(self):
        exposure_time = self.expTime.get()
        self.live_process = mp.Process(target= asf.live_view, args = (self.stop_signal,self.output,exposure_time))
        self.live_process.start()
        self.plotting_process = threading.Thread(target= self.plot)
        self.plotting_process.start()

    def start_ml_sim(self):
        exposure_time = self.expTime.get()
        self.live_process = mp.Process(target= asf.live_ml_sim, args = (self.stack,self.stop_signal,self.output,exposure_time))
        self.live_process.start()
        self.plotting_process = threading.Thread(target= self.plot)
        self.plotting_process.start()    

    def quit_gui(self):
        self.stop_signal.put(False)
        time.sleep(1)
        self.master.destroy()

    def stop_live(self):
        self.stop_signal.put(False)

    def plot(self):
        while True: 
            if not self.output.empty():
                image_array = self.output.get() # empty data from reconstruction pool
                if isinstance(image_array, bool):
                    print('imArray was bool')
                    break
                else:
                    # run the update function 
                    img =  ImageTk.PhotoImage(image=Image.fromarray(image_array)) # convert numpy array to tikner object 
                    self.panel.configure(image=img) # update the GUI element
                    self.panel.image = img  
            # else:
                # print('imArray was empty')

if __name__ == '__main__':
    root = tk.Tk()
    my_gui = ML_App(root)
    root.mainloop()

