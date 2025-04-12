import customtkinter as ctk
from tkinter import BooleanVar, filedialog
import serial
import serial.tools.list_ports
import threading
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import os
from PIL import Image
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import sys
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt

# Fixed colors for light mode!
TEXT_COLOR = "black"              # Text color for all widgets
WIDGET_BG_COLOR = "white"         # Background color for all widgets
ROOT_BG_COLOR = "#ebebeb"         # Outer frame background

# Global Font Constants
FONT_TITLE = ("Arial", 16, "bold")
FONT_HEADER = ("Arial", 14, "bold")
FONT_SMALL = ("Arial", 14)
FONT_BUTTON = ("Arial", 14, "bold")
FONT_CHECKBOX = ("Arial", 14)

# Global image height constants
LEFT_ICON_HEIGHT = 150
RIGHT_ICON_HEIGHT = 120

# Global filtering constants
FILTER_CUTOFF = 1  # Cutoff frequency for low-pass filter

def resize_image_to_height(image, height):
    original_width, original_height = image.size
    new_width = int((original_width / original_height) * height)
    return image.resize((new_width, height), Image.Resampling.LANCZOS)

# Global constants for plotting
PLOT_UPDATE_INTERVAL = 1000  # milliseconds
MAX_PLOT_POINTS = 6000       # Maximum number of points to display on the plot

def low_pass_filter(data, cutoff, fs, order=4):
    """
    Applies a 4th order Butterworth low pass filter with a given cutoff frequency.
    """
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    filtered_data = filtfilt(b, a, data)
    return filtered_data

class SerialHandler:
    def __init__(self):
        self.port = None
        self.baudrate = 230400
        self.serial_connection = None
        self.running = False
        # All temperature data are stored in °F
        self.data = {
            "time": [],
            "laptop_time": [],
            "ir_temp": [[] for _ in range(8)],
            "tc_temp": [[], []],
            "load": [],
            "brake_pressure": [],
            "rotor_rpm": []
        }
        self.export_file = None

    def set_port(self, port):
        self.port = port

    def start_serial(self):
        if self.port:
            try:
                self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
                self.running = True
                threading.Thread(target=self.read_serial_data, daemon=True).start()
            except serial.SerialException as e:
                print(f"Error: {e}")

    def read_serial_data(self):
        while self.running:
            if self.serial_connection and self.serial_connection.in_waiting:
                try:
                    line = self.serial_connection.readline().decode().strip()
                    values = line.split(",")
                    if len(values) == 14:
                        current_time = datetime.now().strftime('%H:%M:%S:%f')[:-3]
                        time_measured = float(values[0]) / 1000

                        # Convert from °C to °F immediately
                        ir_temps_F = [(float(values[i]) * 9/5 + 32) for i in range(1, 9)]
                        tc_temps_F = [(float(values[9]) * 9/5 + 32), (float(values[10]) * 9/5 + 32)]
                        load_cell = float(values[11])
                        brake_pressure = float(values[12])
                        rotor_rpm = float(values[13])

                        self.data["time"].append(time_measured)
                        self.data["laptop_time"].append(current_time)
                        for i in range(8):
                            self.data["ir_temp"][i].append(ir_temps_F[i])
                        for i in range(2):
                            self.data["tc_temp"][i].append(tc_temps_F[i])
                        self.data["load"].append(load_cell)
                        self.data["brake_pressure"].append(brake_pressure)
                        self.data["rotor_rpm"].append(rotor_rpm)

                        # Write CSV line (temperatures in °F)
                        csv_line = (
                            f"{time_measured}," +
                            ",".join([f"{v}" for v in ir_temps_F]) +
                            f",{tc_temps_F[0]},{tc_temps_F[1]},{load_cell},{brake_pressure},{rotor_rpm},{current_time}\n"
                        )
                        if self.export_file is not None:
                            self.export_file.write(csv_line)
                            self.export_file.flush()
                    time.sleep(0.001)
                except Exception as e:
                    print(f"Data read error: {e}")

    def stop_serial(self):
        self.running = False
        if self.serial_connection:
            self.serial_connection.close()
        if self.export_file:
            self.export_file.close()
            self.export_file = None

class PlotHandler:
    def __init__(self, root):
        self.root = root
        self.canvas = None
        self.animation = None
        self.serial_handler = None

        # Defaults for user-changeable settings:
        self.avg_samples = ctk.IntVar(value=100)
        self.plot_refresh_rate = ctk.IntVar(value=PLOT_UPDATE_INTERVAL)
        self.max_plot_points = ctk.IntVar(value=MAX_PLOT_POINTS)

        # We'll store references to the new checkboxes
        # so we can update their text with average values
        self.checkbox_map = {}

        # Visible plots
        self.visible_plots = ["ir_temp", "load", "rpm", "tc1", "tc2", "brake_pressure", "ir_sensor_time"]
        self.plot_objects = {}
        self.fig = plt.figure(figsize=(10, 20))

        self.plots_info = {
            'ir_temp': {
                'visible': BooleanVar(value=True),
                'title': "IR Temperature Readings",
                'ylabel': "Temp (°F)",
                'xlabel': "Sensors"
            },
            'ir_sensor_time': {
                'visible': BooleanVar(value=True),
                'title': "IR Sensor Temperatures vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'load': {
                'visible': BooleanVar(value=True),
                'title': "Load (this label will be overridden)",
                'ylabel': "Force (lbf)",
                'xlabel': "Time (s)"
            },
            'rpm': {
                'visible': BooleanVar(value=True),
                'title': "RPM (this label will be overridden)",
                'ylabel': "RPM",
                'xlabel': "Time (s)"
            },
            'tc1': {
                'visible': BooleanVar(value=True),
                'title': "TC1 (Pad) (overridden label)",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'tc2': {
                'visible': BooleanVar(value=True),
                'title': "TC2 (Caliper) (overridden label)",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'brake_pressure': {
                'visible': BooleanVar(value=True),
                'title': "Brake Pressure (overridden label)",
                'ylabel': "Pressure (psi)",
                'xlabel': "Time (s)"
            }
        }
        # For combined IR sensor time plot
        self.ir_channel_vars = [BooleanVar(value=True) for _ in range(8)]
        self.ir_labels = [f"IR {i+1}" for i in range(8)]

        self.setup_average_frame()
        self.setup_control_panel()

    # ------------------------------------------------------
    # Additional dictionaries to manage the new labels & units
    # for the line plots (NOT IR) that you want to show in the
    # control panel checkboxes.
    # ------------------------------------------------------
    # Plot name -> descriptive label
    label_map = {
        'load':           "Load Cell Force",
        'rpm':            "Rotor Speed",
        'tc1':            "Pad Temperature",
        'tc2':            "Caliper Temperature",
        'brake_pressure': "Brake Pressure"
    }
    # Plot name -> corresponding unit
    unit_map = {
        'load':           "lbf",
        'rpm':            "RPM",
        'tc1':            "°F",
        'tc2':            "°F",
        'brake_pressure': "psi"
    }

    # ---------------------------
    # Settings, Manual, About Popup
    # ---------------------------
    def show_about_popup(self):
        popup = ctk.CTkToplevel(self.root)
        popup.title("Settings & About")
        popup.geometry("500x600")
        popup.transient(self.root)
        popup.grab_set()
        popup.focus_set()
        popup.geometry(f"+{self.root.winfo_x() + 50}+{self.root.winfo_y() + 50}")

        tabview = ctk.CTkTabview(popup, width=480, height=550)
        tabview.pack(padx=10, pady=10, fill="both", expand=True)

        # Create tabs
        settings_tab = tabview.add("Settings")
        manual_tab   = tabview.add("Manual")
        about_tab    = tabview.add("About")

        # ---------- Settings Tab ----------
        settings_tab.grid_columnconfigure(0, weight=1)
        settings_tab.grid_columnconfigure(1, weight=1)

        # Averaging frame
        avg_frame = ctk.CTkFrame(settings_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
        avg_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        ctk.CTkLabel(avg_frame, text="Averaging Settings", font=FONT_HEADER, text_color=TEXT_COLOR).pack(pady=(10, 5))
        avg_label = ctk.CTkLabel(avg_frame, text="Number of samples\nfor averaging:", font=FONT_SMALL, text_color=TEXT_COLOR)
        avg_label.pack(anchor="w", padx=20, pady=(10, 5))

        avg_options = ["10", "20", "50", "100", "200", "500", "1000", "All"]
        avg_dropdown = ctk.CTkComboBox(
            avg_frame,
            values=avg_options,
            font=FONT_SMALL,
            command=self.set_avg_samples,
            width=100
        )
        avg_dropdown.set(str(self.avg_samples.get()))
        avg_dropdown.pack(pady=(0, 10))

        # Plot Settings frame
        plot_frame = ctk.CTkFrame(settings_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
        plot_frame.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="nsew")
        ctk.CTkLabel(plot_frame, text="Plot Settings", font=FONT_HEADER, text_color=TEXT_COLOR).pack(pady=(10, 5))

        # Plot refresh rate
        refresh_label = ctk.CTkLabel(plot_frame, text="Plot refresh rate (ms):", font=FONT_SMALL, text_color=TEXT_COLOR)
        refresh_label.pack(anchor="w", padx=20, pady=(10, 5))
        refresh_options = ["200", "500", "1000", "2000", "5000"]
        refresh_dropdown = ctk.CTkComboBox(
            plot_frame,
            values=refresh_options,
            font=FONT_SMALL,
            command=self.set_refresh_rate,
            width=100
        )
        refresh_dropdown.set(str(self.plot_refresh_rate.get()))
        refresh_dropdown.pack(pady=(0, 10))

        # Max data points
        max_points_label = ctk.CTkLabel(plot_frame, text="Max data points shown:", font=FONT_SMALL, text_color=TEXT_COLOR)
        max_points_label.pack(anchor="w", padx=20, pady=(10, 5))
        max_points_options = ["100", "500", "1000", "2000", "5000", "10000"]
        max_points_dropdown = ctk.CTkComboBox(
            plot_frame,
            values=max_points_options,
            font=FONT_SMALL,
            command=self.set_max_points,
            width=100
        )
        max_points_dropdown.set(str(self.max_plot_points.get()))
        max_points_dropdown.pack(pady=(0, 10))

        # Apply button
        apply_button = ctk.CTkButton(
            settings_tab,
            text="Apply Settings",
            command=self.apply_settings,
            font=FONT_BUTTON,
            fg_color="#baffc9",
            hover_color="#89e4a4",
            text_color=TEXT_COLOR
        )
        apply_button.grid(row=1, column=0, columnspan=2, pady=20)

        # ---------- Manual Tab ----------
        manual_frame = ctk.CTkFrame(manual_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
        manual_frame.pack(padx=10, pady=10, fill="both", expand=True)

        manual_label = ctk.CTkLabel(
            manual_frame,
            text="Click below to open the\nBrake Dyno Instruction Manual:",
            font=FONT_HEADER,
            text_color=TEXT_COLOR,
            justify="center"
        )
        manual_label.pack(pady=(50, 30))

        manual_button = ctk.CTkButton(
            manual_frame,
            text="Open Instruction Manual",
            command=self.open_manual,
            font=FONT_BUTTON,
            fg_color="#d0d0ff",
            hover_color="#b0b0ff",
            text_color=TEXT_COLOR,
            width=300,
            height=50
        )
        manual_button.pack(pady=20)

        # ---------- About Tab ----------
        about_frame = ctk.CTkFrame(about_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
        about_frame.pack(padx=10, pady=10, fill="both", expand=True)

        text_frame = ctk.CTkFrame(about_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        text_frame.pack(padx=20, pady=(0, 0), fill="both", expand=True)

        about_text = (
            "Brake Dyno Data Acquisition\n\n"
            "Version: 1.0.0\n\n"
            "This program allows real-time acquisition and visualization of brake dynamometer data.\n\n"
            "Features:\n"
            "• Real-time data acquisition from sensors\n"
            "• Multiple visualization options\n"
            "• Data export to CSV\n"
            "• Customizable display settings\n\n"
            "© 2024 DynoCO"
        )
        about_label = ctk.CTkLabel(
            text_frame, 
            text=about_text,
            font=FONT_SMALL,
            text_color=TEXT_COLOR,
            justify="left",
            wraplength=400
        )
        about_label.pack(fill="both", expand=True)

    def open_manual(self):
        """
        Attempt to open a local PDF manual (update filename/path as needed).
        """
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            manual_path = os.path.join(script_dir, "Brake_Dyno_GUI_Instruction_Manual_2_27_25.pdf")

            if os.path.exists(manual_path):
                if sys.platform.startswith('darwin'):  # macOS
                    import subprocess
                    subprocess.call(('open', manual_path))
                elif sys.platform.startswith('win'):   # Windows
                    os.startfile(manual_path)
                else:  # Linux / other
                    import subprocess
                    subprocess.call(('xdg-open', manual_path))
            else:
                # Show an error popup if file not found
                error_popup = ctk.CTkToplevel(self.root)
                error_popup.title("Manual Not Found")
                error_popup.geometry("400x150")
                error_popup.transient(self.root)
                error_popup.grab_set()

                ctk.CTkLabel(
                    error_popup,
                    text=f"The instruction manual file was not found at:\n{manual_path}",
                    font=FONT_SMALL,
                    text_color=TEXT_COLOR,
                    wraplength=350
                ).pack(padx=20, pady=20)

                ctk.CTkButton(
                    error_popup,
                    text="OK",
                    command=error_popup.destroy,
                    font=FONT_BUTTON,
                    fg_color="#ffb3ba",
                    hover_color="#ff8ca3",
                    text_color=TEXT_COLOR
                ).pack(pady=(0,20))
        except Exception as e:
            print(f"Error opening manual: {e}")

    def set_avg_samples(self, value):
        """Set how many samples to use for averaging (or -1 to use all)."""
        if value == "All":
            self.avg_samples.set(-1)
        else:
            self.avg_samples.set(int(value))

    def set_refresh_rate(self, value):
        """Set the plot refresh rate (in ms)."""
        self.plot_refresh_rate.set(int(value))

    def set_max_points(self, value):
        """Set the maximum number of data points to display for each plot."""
        self.max_plot_points.set(int(value))

    def apply_settings(self):
        """Apply user settings for averaging, plot refresh, and max points."""
        if self.animation:
            self.animation.event_source.stop()
            self.animation = animation.FuncAnimation(
                self.fig,
                self.update_plot,
                interval=self.plot_refresh_rate.get(),
                cache_frame_data=False
            )
        global MAX_PLOT_POINTS
        MAX_PLOT_POINTS = self.max_plot_points.get()
        self.update_plot_layout()
        self.update_plot(0)
        # self.set_avg_samples.set(self,)

    def setup_average_frame(self):
        screen_width = self.root.winfo_screenwidth()
        frame_width = int(screen_width * 0.15)

        self.average_frame = ctk.CTkFrame(self.root, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        self.average_frame.pack(side="left", fill="y", padx=(10, 0), pady=10)

        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.average_frame,
            fg_color=WIDGET_BG_COLOR,
            corner_radius=0,
            width=frame_width,
            scrollbar_button_color="#efefef",
            scrollbar_button_hover_color="#48aeff"
        )
        self.scrollable_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # IR sensor average section
        ir_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR)
        ir_frame.pack(pady=5, padx=10, fill="x")

        self.ir_average_label = ctk.CTkLabel(ir_frame, text="IR Temperatures (°F)", font=FONT_HEADER, text_color=TEXT_COLOR)
        self.ir_average_label.pack(pady=(15,5))

        # Create a new subframe to use grid for the 8 labels.
        grid_frame = ctk.CTkFrame(ir_frame, fg_color=WIDGET_BG_COLOR)
        grid_frame.pack(anchor="center")

        self.ir_average_values = []
        for i in range(8):
            label = ctk.CTkLabel(grid_frame, text=f"{i+1}: 0.00 °F", font=FONT_SMALL, text_color=TEXT_COLOR)
            label.grid(row=i // 2, column=i % 2, padx=5, pady=1, sticky="w")
            self.ir_average_values.append(label)

        # # Thermocouples
        # tc_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        # tc_frame.pack(pady=10, padx=10, fill="x")
        # self.tc_average_label = ctk.CTkLabel(tc_frame, text="Thermocouple Temperatures (°F)", font=FONT_HEADER, text_color=TEXT_COLOR)
        # self.tc_average_label.pack(pady=5)

        # self.pad_average_label = ctk.CTkLabel(tc_frame, text="Pad Average: 0.00 °F", font=FONT_SMALL, text_color=TEXT_COLOR)
        # self.pad_average_label.pack(pady=2)

        # self.caliper_average_label = ctk.CTkLabel(tc_frame, text="Caliper Average: 0.00 °F", font=FONT_SMALL, text_color=TEXT_COLOR)
        # self.caliper_average_label.pack(pady=1)

        # # Load
        # load_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        # load_frame.pack(pady=10, padx=10, fill="x")
        # self.load_average_label = ctk.CTkLabel(load_frame, text="Load Cell Average: 0.00 lbf", font=FONT_HEADER, text_color=TEXT_COLOR)
        # self.load_average_label.pack(pady=1)

        # # RPM
        # rpm_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        # rpm_frame.pack(pady=10, padx=10, fill="x")
        # self.rpm_average_label = ctk.CTkLabel(rpm_frame, text="RPM Average: 0.00 RPM", font=FONT_HEADER, text_color=TEXT_COLOR)
        # self.rpm_average_label.pack(pady=1)

        # "About Program" button
        self.about_button = ctk.CTkButton(
            self.average_frame, 
            text="About Program", 
            font=FONT_BUTTON,
            fg_color="#eeeeee",
            hover_color="#48aeff",
            text_color="#131313",
            command=self.show_about_popup
        )
        self.about_button.pack(side="bottom", fill="x", padx=10, pady=(10,15))

    def setup_control_panel(self):
        """
        Adds a 'Display Graphs' section with new checkboxes that dynamically
        include the average values for load, rpm, pad temp, caliper temp,
        and brake pressure (the IR ones remain the same).
        """
        control_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        control_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(control_frame, text="Display Graphs", font=FONT_TITLE, text_color=TEXT_COLOR).pack(pady=5)

        # We'll create the checkboxes for each plot
        # If the plot name is one of the 5 (load, rpm, tc1, tc2, brake_pressure),
        # we will store references so we can update the label with the average value.
        for plot_name, info in self.plots_info.items():
            # Create default text from the existing 'title'
            checkbox_text = info['title']

            # If this is one of the 5 we want to show average for, we override text
            # The real text will be updated in update_averages with the format you want.
            if plot_name in ["load", "rpm", "tc1", "tc2", "brake_pressure"]:
                # We'll start with an empty or placeholder text,
                # then in update_averages we'll fill the average.
                checkbox_text = self.label_map[plot_name] 

            checkbox_var = info['visible']  # The BooleanVar controlling visibility
            chk = ctk.CTkCheckBox(
                control_frame,
                text=checkbox_text,
                variable=checkbox_var,
                command=self.update_plot_layout,
                font=FONT_CHECKBOX,
                text_color=TEXT_COLOR,
                fg_color="#ffffff",
                checkmark_color="#48aeff",
                hover_color="#eeeeee",
                border_color="#48aeff",
                border_width=2,
                corner_radius=5
            )
            chk.pack(anchor='w', pady=5)

            # If it's one of the 5, store a reference so we can dynamically update
            if plot_name in ["load", "rpm", "tc1", "tc2", "brake_pressure"]:
                self.checkbox_map[plot_name] = chk

        # IR Sensor Channels
        ctk.CTkLabel(control_frame, text="IR Sensor Channels", font=FONT_TITLE, text_color=TEXT_COLOR).pack(pady=(5,5))
        for i in range(8):
            ctk.CTkCheckBox(
                control_frame,
                text=f"IR Sensor {i+1}",
                variable=self.ir_channel_vars[i],
                command=self.update_plot_layout,
                font=FONT_CHECKBOX,
                text_color=TEXT_COLOR,
                fg_color="#ffffff",
                checkmark_color="#48aeff",
                hover_color="#eeeeee",
                border_color="#48aeff",
                border_width=2,
                corner_radius=5
            ).pack(anchor='w', pady=5)

        self.refresh_button = ctk.CTkButton(
            control_frame,
            text="Refresh Plots",
            command=self.update_plot_layout,
            font=FONT_BUTTON,
            fg_color="#eeeeee",
            text_color="#131313",
            hover_color="#48aeff",
        )
        self.refresh_button.pack(pady=10)

    def update_plot_layout(self):
        self.visible_plots = [name for name, info in self.plots_info.items() if info['visible'].get()]
        self.plot_objects = {}
        self.fig.clf()

        num_visible = len(self.visible_plots)
        if num_visible == 0 and self.canvas:
            self.canvas.draw()
            return

        for i, plot_name in enumerate(self.visible_plots):
            ax = self.fig.add_subplot(num_visible, 1, i + 1)
            # Keep y-label ONLY for the IR bar plot ("ir_temp")
            if plot_name == "ir_temp":
                ax.set_ylabel(self.plots_info[plot_name]['ylabel'], fontsize=14)
            else:
                ax.set_ylabel("")
            ax.grid(True, linestyle="--", alpha=0.7)
            self.plots_info[plot_name]['axis'] = ax

        self.fig.tight_layout()
        if self.canvas:
            self.canvas.draw()

    def update_plot(self, frame):
        if not self.serial_handler or not self.serial_handler.data["time"]:
            return

        times = np.array(self.serial_handler.data["time"])
        if len(times) < 1:
            return

        start_time = times[0]
        rel_times = times - start_time
        plot_times = rel_times[-MAX_PLOT_POINTS:]
        dt = np.mean(np.diff(times)) if len(times) > 1 else 1.0
        fs = 1.0 / dt

        for plot_name in self.visible_plots:
            ax = self.plots_info[plot_name]['axis']

            if plot_name == 'ir_temp':
                # IR bar plot
                raw_values = []
                for i in range(8):
                    sensor_data = self.serial_handler.data["ir_temp"][i]
                    value = sensor_data[-1] if sensor_data else 0
                    raw_values.append(value)

                if "ir_temp" in self.plot_objects:
                    for rect, h in zip(self.plot_objects["ir_temp"], raw_values):
                        rect.set_height(h)
                else:
                    bars = ax.bar(self.ir_labels, raw_values, color="#DDDDDD")
                    self.plot_objects["ir_temp"] = bars

                ax.set_ylim(min(raw_values) - 10, max(raw_values) + 10)

            elif plot_name == 'load':
                # Load line plot
                raw_data = np.array(self.serial_handler.data["load"])[-MAX_PLOT_POINTS:]
                n = min(len(plot_times), len(raw_data))
                pt_sync = plot_times[-n:]
                raw_sync = raw_data[-n:]

                try:
                    filtered_data = low_pass_filter(raw_sync, FILTER_CUTOFF, fs, order=4) if len(raw_sync) > 3 else raw_sync
                except Exception:
                    filtered_data = raw_sync

                if "load_raw" in self.plot_objects:
                    self.plot_objects["load_raw"].set_data(pt_sync, raw_sync)
                else:
                    r_line, = ax.plot(pt_sync, raw_sync, color="#DDDDDD", label="_nolegend_")
                    self.plot_objects["load_raw"] = r_line

                if "load_filtered" in self.plot_objects:
                    self.plot_objects["load_filtered"].set_data(pt_sync, filtered_data)
                else:
                    f_line, = ax.plot(pt_sync, filtered_data, label="Load (lbf)", color="red")
                    self.plot_objects["load_filtered"] = f_line

                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")

            elif plot_name == 'rpm':
                # RPM line plot
                raw_data = np.array(self.serial_handler.data["rotor_rpm"])[-MAX_PLOT_POINTS:]
                n = min(len(plot_times), len(raw_data))
                pt_sync = plot_times[-n:]
                raw_sync = raw_data[-n:]

                try:
                    filtered_data = low_pass_filter(raw_sync, FILTER_CUTOFF, fs, order=4) if len(raw_sync) > 3 else raw_sync
                except Exception:
                    filtered_data = raw_sync

                if "rpm_raw" in self.plot_objects:
                    self.plot_objects["rpm_raw"].set_data(pt_sync, raw_sync)
                else:
                    r_line, = ax.plot(pt_sync, raw_sync, color="#DDDDDD", label="_nolegend_")
                    self.plot_objects["rpm_raw"] = r_line

                if "rpm_filtered" in self.plot_objects:
                    self.plot_objects["rpm_filtered"].set_data(pt_sync, filtered_data)
                else:
                    f_line, = ax.plot(pt_sync, filtered_data, label="Rotor RPM", color="green")
                    self.plot_objects["rpm_filtered"] = f_line

                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")

            elif plot_name == 'tc1':
                # Pad temperature line plot
                raw_data = np.array(self.serial_handler.data["tc_temp"][0])[-MAX_PLOT_POINTS:]
                n = min(len(plot_times), len(raw_data))
                pt_sync = plot_times[-n:]
                raw_sync = raw_data[-n:]

                try:
                    filtered_data = low_pass_filter(raw_sync, FILTER_CUTOFF, fs, order=4) if len(raw_sync) > 3 else raw_sync
                except Exception:
                    filtered_data = raw_sync

                if "tc1_raw" in self.plot_objects:
                    self.plot_objects["tc1_raw"].set_data(pt_sync, raw_sync)
                else:
                    r_line, = ax.plot(pt_sync, raw_sync, color="#DDDDDD", label="_nolegend_")
                    self.plot_objects["tc1_raw"] = r_line

                if "tc1_filtered" in self.plot_objects:
                    self.plot_objects["tc1_filtered"].set_data(pt_sync, filtered_data)
                else:
                    f_line, = ax.plot(pt_sync, filtered_data, label="Pad Temp. (°F)", color="purple")
                    self.plot_objects["tc1_filtered"] = f_line

                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")

            elif plot_name == 'tc2':
                # Caliper temperature line plot
                raw_data = np.array(self.serial_handler.data["tc_temp"][1])[-MAX_PLOT_POINTS:]
                n = min(len(plot_times), len(raw_data))
                pt_sync = plot_times[-n:]
                raw_sync = raw_data[-n:]

                try:
                    filtered_data = low_pass_filter(raw_sync, FILTER_CUTOFF, fs, order=4) if len(raw_sync) > 3 else raw_sync
                except Exception:
                    filtered_data = raw_sync

                if "tc2_raw" in self.plot_objects:
                    self.plot_objects["tc2_raw"].set_data(pt_sync, raw_sync)
                else:
                    r_line, = ax.plot(pt_sync, raw_sync, color="#DDDDDD", label="_nolegend_")
                    self.plot_objects["tc2_raw"] = r_line

                if "tc2_filtered" in self.plot_objects:
                    self.plot_objects["tc2_filtered"].set_data(pt_sync, filtered_data)
                else:
                    f_line, = ax.plot(pt_sync, filtered_data, label="Caliper Temp. (°F)", color="orange")
                    self.plot_objects["tc2_filtered"] = f_line

                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")

            elif plot_name == 'brake_pressure':
                # Brake pressure line plot
                raw_data = np.array(self.serial_handler.data["brake_pressure"])[-MAX_PLOT_POINTS:]
                n = min(len(plot_times), len(raw_data))
                pt_sync = plot_times[-n:]
                raw_sync = raw_data[-n:]

                try:
                    filtered_data = low_pass_filter(raw_sync, FILTER_CUTOFF, fs, order=4) if len(raw_sync) > 3 else raw_sync
                except Exception:
                    filtered_data = raw_sync

                if "brake_pressure_raw" in self.plot_objects:
                    self.plot_objects["brake_pressure_raw"].set_data(pt_sync, raw_sync)
                else:
                    r_line, = ax.plot(pt_sync, raw_sync, color="#DDDDDD", label="_nolegend_")
                    self.plot_objects["brake_pressure_raw"] = r_line

                if "brake_pressure_filtered" in self.plot_objects:
                    self.plot_objects["brake_pressure_filtered"].set_data(pt_sync, filtered_data)
                else:
                    f_line, = ax.plot(pt_sync, filtered_data, label="Brake Pressure (psi)", color="brown")
                    self.plot_objects["brake_pressure_filtered"] = f_line

                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")

            elif plot_name == 'ir_sensor_time':
                # Combined IR sensor channels
                for i in range(8):
                    if self.ir_channel_vars[i].get():
                        raw_data = np.array(self.serial_handler.data["ir_temp"][i])
                        n = min(len(plot_times), len(raw_data))
                        pt_sync = plot_times[-n:]
                        raw_sync = raw_data[-n:]

                        try:
                            filtered_data = low_pass_filter(raw_sync, FILTER_CUTOFF, fs, order=4) if len(raw_sync) > 3 else raw_sync
                        except Exception:
                            filtered_data = raw_sync

                        key_raw = f"ir_sensor_time_raw_{i}"
                        if key_raw in self.plot_objects:
                            self.plot_objects[key_raw].set_data(pt_sync, raw_sync)
                        else:
                            r_line, = ax.plot(pt_sync, raw_sync, color="#DDDDDD", label="_nolegend_")
                            self.plot_objects[key_raw] = r_line

                        key_filt = f"ir_sensor_time_filtered_{i}"
                        label_str = f"IR Channel {i+1} (°F)"
                        if key_filt in self.plot_objects:
                            self.plot_objects[key_filt].set_data(pt_sync, filtered_data)
                        else:
                            f_line, = ax.plot(pt_sync, filtered_data, label=label_str, color="blue")
                            self.plot_objects[key_filt] = f_line

                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")

        # Update average labels
        self.update_averages()
        if self.canvas:
            self.canvas.draw()

    def update_averages(self):
        times = self.serial_handler.data["time"]
        if len(times) > 1:
            dt = np.mean(np.diff(times))
        else:
            dt = 1.0
        fs = 1.0 / dt

        # IR sensor averages
        for i in range(8):
            data = np.array(self.serial_handler.data["ir_temp"][i])
            if len(data) > 3:
                try:
                    filtered = low_pass_filter(data, FILTER_CUTOFF, fs=fs, order=4)
                    avg = filtered[-1]
                except:
                    avg = data[-1]
            else:
                avg = 0
            self.ir_average_values[i].configure(text=f"IR {i+1}: {avg:.2f} °F")

        # # Load / RPM
        # for key, label in [("load", self.load_average_label), ("rotor_rpm", self.rpm_average_label)]:
        #     data = self.serial_handler.data[key]
        #     avg = sum(data)/len(data) if data else 0
        #     if key == "load":
        #         label.configure(text=f"Load Cell Average: {avg:.2f} lbf")
        #     else:
        #         label.configure(text=f"Rpm Average: {avg:.2f} RPM")

        # # Thermocouples (Pad / Caliper)
        # sample_count = self.avg_samples.get()
        # for idx, lbl in enumerate([self.pad_average_label, self.caliper_average_label]):
        #     data = self.serial_handler.data["tc_temp"][idx]
        #     if data:
        #         if sample_count <= 0 or sample_count >= len(data):
        #             tc_data = data
        #         else:
        #             tc_data = data[-sample_count:]
        #         avg_temp = sum(tc_data)/len(tc_data)
        #     else:
        #         avg_temp = 0
        #     if idx == 0:
        #         lbl.configure(text=f"Pad Average: {avg_temp:.2f} °F")
        #     else:
        #         lbl.configure(text=f"Caliper Average: {avg_temp:.2f} °F")


        # # We'll define a small helper function to get the average of a data array
        # def get_average_data(key):
        #     arr = np.array(self.serial_handler.data[key]) if key in ["load", "brake_pressure", "rotor_rpm"] else None
        #     if arr is not None and len(arr) > 0:
        #         return sum(arr)/len(arr)
        #     return 0.0
        
        def get_average_data(key, N):
            # Only process if key is one of the specified keys.
            if key in ["load", "brake_pressure", "rotor_rpm"]:
                data = self.serial_handler.data[key]
                if len(data) > 0:
                    # If there are at least N values, take the last N; otherwise take all.
                    arr = np.array(data[-N:]) if len(data) >= N else np.array(data)
                    return sum(arr) / len(arr)
            return 0.0

        # For thermocouples, we have separate data structures
        # tc1 = pad = self.serial_handler.data["tc_temp"][0]
        # tc2 = caliper = self.serial_handler.data["tc_temp"][1]
        def get_tc_average(idx, N):
            data = self.serial_handler.data["tc_temp"][idx]
            if len(data) > 0:
                arr = np.array(data[-N:]) if len(data) >= N else np.array(data)
                return sum(arr) / len(arr)
            return 0.0


        # For each key in our dictionary that references the checkboxes:
        # produce the new text with the average value
        if "load" in self.checkbox_map:
            avg_load = get_average_data("load", self.avg_samples.get())
            new_label = f"Load Cell Force: {avg_load:.2f} lbf"
            self.checkbox_map["load"].configure(text=new_label)

        if "rpm" in self.checkbox_map:
            avg_rpm = get_average_data("rotor_rpm", self.avg_samples.get())
            new_label = f"Rotor Speed: {avg_rpm:.2f} RPM"
            self.checkbox_map["rpm"].configure(text=new_label)

        if "tc1" in self.checkbox_map:
            avg_pad = get_tc_average(0, self.avg_samples.get())
            new_label = f"Pad Temperature: {avg_pad:.2f} °F"
            self.checkbox_map["tc1"].configure(text=new_label)

        if "tc2" in self.checkbox_map:
            avg_caliper = get_tc_average(1, self.avg_samples.get())
            new_label = f"Caliper Temperature: {avg_caliper:.2f} °F"
            self.checkbox_map["tc2"].configure(text=new_label)

        if "brake_pressure" in self.checkbox_map:
            avg_bp = get_average_data("brake_pressure", self.avg_samples.get())
            new_label = f"Brake Pressure: {avg_bp:.2f} psi"
            self.checkbox_map["brake_pressure"].configure(text=new_label)
        # End new code

    def start_plotting(self, serial_handler):
        self.serial_handler = serial_handler
        self.animation = animation.FuncAnimation(
            self.fig, self.update_plot, interval=PLOT_UPDATE_INTERVAL, cache_frame_data=False
        )

    def stop_plotting(self):
        if self.animation:
            self.animation.event_source.stop()

class RootGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.state('zoomed')
         
        ctk.set_appearance_mode("light")
        self.root.title("UTA Racing Brake Dyno DAQ GUI")

        # screen_width = self.root.winfo_screenwidth()
        # screen_height = self.root.winfo_screenheight()
        # self.root.geometry(f"{screen_width}x{screen_height}")

        self.serial_handler = SerialHandler()
        self.plot_handler = PlotHandler(self.root)
        self.export_folder = None
        self.export_status_box = None

        self.load_icons()
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Update export status periodically
        self.update_export_status_loop()

    def load_icons(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        left_icon_path = os.path.join(script_dir, "left_icon.png")
        left_img = Image.open(left_icon_path)
        left_img_resized = resize_image_to_height(left_img, LEFT_ICON_HEIGHT)
        self.left_icon_ctk = ctk.CTkImage(light_image=left_img_resized, dark_image=left_img_resized, size=left_img_resized.size)

        right_icon_path = os.path.join(script_dir, "right_icon.jpg")
        right_img = Image.open(right_icon_path)
        right_img_resized = resize_image_to_height(right_img, RIGHT_ICON_HEIGHT)
        self.right_icon_ctk = ctk.CTkImage(light_image=right_img_resized, dark_image=right_img_resized, size=right_img_resized.size)

    def get_available_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def update_port_selection(self, value):
        selected_port = self.com_port_dropdown.get()
        self.serial_handler.set_port(selected_port)

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self.root, fg_color=ROOT_BG_COLOR, corner_radius=0)
        main_frame.pack(expand=True, fill="both")

        # Icon frame (top)
        icon_frame = ctk.CTkFrame(main_frame, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        icon_frame.pack(fill="x", padx=10, pady=(10, 0))

        left_icon_label = ctk.CTkLabel(icon_frame, image=self.left_icon_ctk, text="", text_color=TEXT_COLOR)
        left_icon_label.pack(side="left", padx=20)

        center_frame = ctk.CTkFrame(icon_frame, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        center_frame.pack(side="left", expand=True, fill="x", padx=20)

        grid_frame = ctk.CTkFrame(center_frame, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        grid_frame.pack(pady=5, anchor="center")

        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(2, weight=1)
        grid_frame.grid_rowconfigure(0, weight=1)

        # COM Port dropdown
        self.com_port_dropdown = ctk.CTkComboBox(
            grid_frame,
            values=self.get_available_ports(),
            font=FONT_HEADER,
            width=100,
            command=self.update_port_selection
        )
        if self.get_available_ports():
            self.com_port_dropdown.set(self.get_available_ports()[0])
            self.serial_handler.set_port(self.get_available_ports()[0])

        self.com_port_dropdown.grid(row=0, column=0, padx=10, pady=5)

        # Export Folder Button
        self.export_folder_button = ctk.CTkButton(
            grid_frame, text="Select Export Folder", font=FONT_BUTTON,
            command=self.select_export_folder, fg_color="#d0d0ff",
            hover_color="#b0b0ff", text_color=TEXT_COLOR
        )
        self.export_folder_button.grid(row=0, column=1, padx=10, pady=5)

        # Export status box
        self.export_status_box = ctk.CTkLabel(
            grid_frame, text="", font=FONT_BUTTON, width=150,
            fg_color="#EEEEEE", text_color="black", corner_radius=5
        )
        self.export_status_box.grid(row=0, column=2, rowspan=3, padx=10, pady=5, sticky="nsew")

        # START / STOP
        self.start_button = ctk.CTkButton(
            grid_frame, text="START", font=FONT_BUTTON,
            command=self.start_reading, fg_color="#baffc9",
            hover_color="#89e4a4", text_color=TEXT_COLOR, text_color_disabled="#555555"
        )
        self.start_button.grid(row=1, column=0, padx=10, pady=5)

        self.export_button = ctk.CTkButton(
            grid_frame, text="START EXPORT", font=FONT_BUTTON,
            command=self.start_export, fg_color="#baffc9",
            hover_color="#89e4a4", text_color=TEXT_COLOR,
            state="disabled", text_color_disabled="#555555"
        )
        self.export_button.grid(row=1, column=1, padx=10, pady=5)

        self.stop_button = ctk.CTkButton(
            grid_frame, text="STOP", font=FONT_BUTTON,
            command=self.stop_reading, fg_color="#ffb3ba",
            hover_color="#ff8ca3", text_color=TEXT_COLOR,
            state="disabled", text_color_disabled="#555555"
        )
        self.stop_button.grid(row=2, column=0, padx=10, pady=5)

        self.stop_export_button = ctk.CTkButton(
            grid_frame, text="STOP EXPORT", font=FONT_BUTTON,
            command=self.stop_export, fg_color="#ffb3ba",
            hover_color="#ff8ca3", text_color=TEXT_COLOR,
            state="disabled", text_color_disabled="#555555"
        )
        self.stop_export_button.grid(row=2, column=1, padx=10, pady=5)

        right_icon_label = ctk.CTkLabel(icon_frame, image=self.right_icon_ctk, text="", text_color=TEXT_COLOR)
        right_icon_label.pack(side="right", padx=20, pady=10)

        # Plot Frame
        plot_frame = ctk.CTkFrame(main_frame, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        plot_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.plot_handler.canvas = FigureCanvasTkAgg(self.plot_handler.fig, master=plot_frame)
        self.plot_handler.canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)
        self.plot_handler.update_plot(0)

    def select_export_folder(self):
        folder = filedialog.askdirectory(title="Select Export Folder")
        if folder:
            self.export_folder = folder
            self.export_folder_button.configure(text=f"Export Folder: {os.path.basename(folder)}")
            self.export_button.configure(state="normal")
            print(f"Export folder set to: {folder}")
        else:
            self.export_folder = None
            self.export_folder_button.configure(text="Select Export Folder")
            self.export_button.configure(state="disabled")
            print("No folder selected.")

    def start_reading(self):
        self.plot_handler.update_plot_layout()
        selected_port = self.com_port_dropdown.get()
        if selected_port:
            self.serial_handler.set_port(selected_port)
            self.serial_handler.start_serial()
            self.plot_handler.start_plotting(self.serial_handler)
            self.root.after(100, self.plot_handler.update_plot, 0)

            self.start_button.configure(state="disabled", fg_color="#EEEEEE")
            self.stop_button.configure(state="normal", fg_color="#ffb3ba")
            self.com_port_dropdown.configure(state="disabled")

            # Show export status box
            self.export_status_box.grid()
        else:
            print("Please select a COM port.")

    def stop_reading(self):
        self.serial_handler.stop_serial()
        self.plot_handler.stop_plotting()

        self.start_button.configure(state="normal", fg_color="#baffc9")
        self.stop_button.configure(state="disabled", fg_color="#EEEEEE")
        self.com_port_dropdown.configure(state="normal")

        # Hide export status box when program stops
        self.export_status_box.grid_remove()

    def start_export(self):
        if not self.export_folder:
            print("Please select a valid export folder first.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
        csv_filename = os.path.join(self.export_folder, f"data--{timestamp}.csv")
        try:
            f = open(csv_filename, "w")
            header = "Time,IR1,IR2,IR3,IR4,IR5,IR6,IR7,IR8,PAD,Caliper,Load,Brake_Pressure,Rotor_RPM,Laptop_Time\n"
            f.write(header)
            self.serial_handler.export_file = f
            print(f"Export file created: {csv_filename}")

            self.export_button.configure(state="disabled", fg_color="#EEEEEE")
            self.stop_export_button.configure(state="normal", fg_color="#ffb3ba")
        except Exception as e:
            print(f"Error creating export file: {e}")

    def stop_export(self):
        if self.serial_handler.export_file is not None:
            self.serial_handler.export_file.close()
            self.serial_handler.export_file = None
            print("Export stopped.")

            self.export_button.configure(state="normal", fg_color="#baffc9")
            self.stop_export_button.configure(state="disabled", fg_color="#EEEEEE")
        else:
            print("No export active.")

    def update_export_status_box(self):
        # Only update if box is visible
        if not self.export_status_box.winfo_ismapped():
            return

        # If not running, hide
        if not self.serial_handler.running:
            self.export_status_box.grid_remove()
            return

        # Compute average RPM
        rpm_data = self.serial_handler.data["rotor_rpm"]
        avg_rpm = sum(rpm_data)/len(rpm_data) if rpm_data else 0
        export_active = (self.serial_handler.export_file is not None)

        # Set status
        if export_active:
            self.export_status_box.configure(text="EXPORT\nACTIVE", fg_color="green", text_color="white")
        else:
            if avg_rpm <= 0.5:
                self.export_status_box.configure(text="EXPORT\nINACTIVE", fg_color="#EEEEEE", text_color="black")
            else:
                self.export_status_box.configure(text="EXPORT\nINACTIVE", fg_color="red", text_color="black")

    def update_export_status_loop(self):
        self.update_export_status_box()
        self.root.after(500, self.update_export_status_loop)

    def on_closing(self):
        self.stop_export()
        self.serial_handler.stop_serial()
        try:
            self.root.destroy()
        except:
            pass
        sys.exit(0)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RootGUI()
    app.run()
