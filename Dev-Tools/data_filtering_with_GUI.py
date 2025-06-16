import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.signal import butter, filtfilt

# Appearance settings for CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def low_pass_filter(data, cutoff, fs, order=4):
    """
    Applies a Butterworth low pass filter with a given cutoff frequency.
    - data: array of data values.
    - cutoff: cutoff frequency in Hz.
    - fs: sampling frequency in Hz.
    - order: order of the filter.
    """
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    filtered_data = filtfilt(b, a, data)
    return filtered_data

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Signal Filters and Statistics")
        self.geometry("950x950")
        
        # Instance variables to store the data and time vector
        self.data = None
        self.time = None
        
        # Top frame for file selection, signal column selection, and axis controls
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(pady=10, fill="x", padx=10)
        
        # Button to select CSV file
        self.select_button = ctk.CTkButton(top_frame, text="Select CSV File", command=self.select_file)
        self.select_button.pack(side=tk.LEFT, padx=5)
        
        # Label and dropdown for selecting the signal column
        self.signal_label = ctk.CTkLabel(top_frame, text="Signal Column:")
        self.signal_label.pack(side=tk.LEFT, padx=5)
        self.signal_option = ctk.CTkOptionMenu(top_frame, values=[], command=lambda x: self.update_plot())
        self.signal_option.pack(side=tk.LEFT, padx=5)
        
        # Frame for axis limit controls
        limits_frame = ctk.CTkFrame(top_frame)
        limits_frame.pack(side=tk.LEFT, padx=20)
        
        # X-axis controls
        self.xmin_entry = ctk.CTkEntry(limits_frame, placeholder_text="X min", width=100)
        self.xmin_entry.pack(side=tk.LEFT, padx=5)
        self.xmax_entry = ctk.CTkEntry(limits_frame, placeholder_text="X max", width=100)
        self.xmax_entry.pack(side=tk.LEFT, padx=5)
        
        # Y-axis controls
        self.ymin_entry = ctk.CTkEntry(limits_frame, placeholder_text="Y min", width=100)
        self.ymin_entry.pack(side=tk.LEFT, padx=5)
        self.ymax_entry = ctk.CTkEntry(limits_frame, placeholder_text="Y max", width=100)
        self.ymax_entry.pack(side=tk.LEFT, padx=5)
        
        # Button to update both axis limits
        self.limits_button = ctk.CTkButton(limits_frame, text="Set Axis Limits", command=self.update_limits)
        self.limits_button.pack(side=tk.LEFT, padx=5)
        
        # Frame for matplotlib figure (plots)
        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create a matplotlib figure for 3 subplots
        self.figure = plt.Figure(figsize=(8, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Frame for the statistics table
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.pack(fill="x", padx=10, pady=10)
        
        self.stats_tree = ttk.Treeview(self.stats_frame, columns=("Dataset", "Mean", "Max", "Min", "Std", "Median"), show="headings")
        for col in ("Dataset", "Mean", "Max", "Min", "Std", "Median"):
            self.stats_tree.heading(col, text=col)
            self.stats_tree.column(col, width=120, anchor="center")
        self.stats_tree.pack(fill="x")
        
        # To store the current axes for axis limit updates
        self.axes = None
        
    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path:
            try:
                data = pd.read_csv(file_path)
                if data.shape[1] < 2:
                    messagebox.showerror("Error", "CSV file must have at least 2 columns (time and one signal column).")
                    return
                self.data = data
                # Assume the first column is time
                self.time = data.iloc[:, 0].to_numpy()
                # Populate the dropdown with the remaining columns (signal columns)
                signal_cols = list(data.columns)[1:]
                self.signal_option.configure(values=signal_cols)
                self.signal_option.set(signal_cols[0])
                self.update_plot()
            except Exception as e:
                messagebox.showerror("Error", f"Error processing file: {e}")
    
    def update_plot(self):
        if self.data is None or self.time is None:
            return
        
        try:
            # Get selected signal column from the dropdown
            signal_col = self.signal_option.get()
            signal_data = self.data[signal_col].to_numpy()
            
            # Calculate average time step and sampling frequency
            dt = np.mean(np.diff(self.time))
            fs = 1.0 / dt
            
            # 1. Moving Average Filter (1 second window)
            window_samples = max(1, int(round(1.0 / dt)))
            ma_filter = pd.Series(signal_data).rolling(window=window_samples, min_periods=1).mean().to_numpy()
            
            # 2. Low Pass Filter with 1 Hz cutoff
            lp1_filter = low_pass_filter(signal_data, cutoff=1.0, fs=fs, order=4)
            
            # 3. Low Pass Filter with 0.1 Hz cutoff (kept as is)
            lp01_filter = low_pass_filter(signal_data, cutoff=0.1, fs=fs, order=4)
            
            # Compute statistics for each dataset
            stats = {}
            stats["Raw"] = {
                "mean": np.mean(signal_data),
                "max": np.max(signal_data),
                "min": np.min(signal_data),
                "std": np.std(signal_data),
                "median": np.median(signal_data)
            }
            stats["Moving Average (1 sec)"] = {
                "mean": np.mean(ma_filter),
                "max": np.max(ma_filter),
                "min": np.min(ma_filter),
                "std": np.std(ma_filter),
                "median": np.median(ma_filter)
            }
            stats["Low Pass Filter (1 Hz)"] = {
                "mean": np.mean(lp1_filter),
                "max": np.max(lp1_filter),
                "min": np.min(lp1_filter),
                "std": np.std(lp1_filter),
                "median": np.median(lp1_filter)
            }
            stats["Low Pass Filter (0.1 Hz)"] = {
                "mean": np.mean(lp01_filter),
                "max": np.max(lp01_filter),
                "min": np.min(lp01_filter),
                "std": np.std(lp01_filter),
                "median": np.median(lp01_filter)
            }
            
            # Update statistics table
            for row in self.stats_tree.get_children():
                self.stats_tree.delete(row)
            for key, value in stats.items():
                self.stats_tree.insert("", "end", values=(key,
                                                          f"{value['mean']:.2f}",
                                                          f"{value['max']:.2f}",
                                                          f"{value['min']:.2f}",
                                                          f"{value['std']:.2f}",
                                                          f"{value['median']:.2f}"))
            
            # Clear and re-create the figure with 3 subplots
            self.figure.clf()
            axes = self.figure.subplots(nrows=3, ncols=1, sharex=True)
            self.axes = axes  # store axes for limit updates
            
            # Panel 1: 1-second Moving Average Filter
            axes[0].plot(self.time, signal_data, color="#DDDDDD", linestyle="-", label="Raw Data")
            axes[0].plot(self.time, ma_filter, color="red", linestyle="-", label="Moving Average (1 sec)")
            axes[0].set_title("Moving Average (1 sec)")
            axes[0].set_ylabel(signal_col)
            axes[0].legend()
            
            # Panel 2: Low Pass Filter (1 Hz cutoff)
            axes[1].plot(self.time, signal_data, color="#DDDDDD", linestyle="-", label="Raw Data")
            axes[1].plot(self.time, lp1_filter, color="green", linestyle="-", label="Low Pass Filter (1 Hz)")
            axes[1].set_title("Low Pass Filter (1 Hz)")
            axes[1].set_ylabel(signal_col)
            axes[1].legend()
            
            # Panel 3: Low Pass Filter (0.1 Hz cutoff)
            axes[2].plot(self.time, signal_data, color="#DDDDDD", linestyle="-", label="Raw Data")
            axes[2].plot(self.time, lp01_filter, color="magenta", linestyle="-", label="Low Pass Filter (0.1 Hz)")
            axes[2].set_title("Low Pass Filter (0.1 Hz)")
            axes[2].set_xlabel("Time (seconds)")
            axes[2].set_ylabel(signal_col)
            axes[2].legend()
            
            # Redraw the canvas with updated plots
            self.canvas.draw()
        except Exception as e:
            messagebox.showerror("Error", f"Error updating plot: {e}")
    
    def update_limits(self):
        """
        Reads the x and y min/max values from the text boxes and updates
        the axis limits on all subplots.
        """
        try:
            xmin_str = self.xmin_entry.get().strip()
            xmax_str = self.xmax_entry.get().strip()
            ymin_str = self.ymin_entry.get().strip()
            ymax_str = self.ymax_entry.get().strip()
            if not xmin_str or not xmax_str or not ymin_str or not ymax_str:
                messagebox.showerror("Error", "Please enter values for X min, X max, Y min, and Y max.")
                return
            xmin = float(xmin_str)
            xmax = float(xmax_str)
            ymin = float(ymin_str)
            ymax = float(ymax_str)
            if self.axes is not None:
                for ax in self.axes:
                    ax.set_xlim(xmin, xmax)
                    ax.set_ylim(ymin, ymax)
                self.canvas.draw()
            else:
                messagebox.showinfo("Info", "No plot available to update. Please load a CSV file first.")
        except ValueError:
            messagebox.showerror("Error", "Invalid number format for axis limits.")

if __name__ == "__main__":
    app = App()
    app.mainloop()
