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

def resize_image_to_height(image, height):
    original_width, original_height = image.size
    new_width = int((original_width / original_height) * height)
    return image.resize((new_width, height), Image.Resampling.LANCZOS)

# Global constants for plotting
PLOT_UPDATE_INTERVAL = 1000  # milliseconds, how often to update the plot
MAX_PLOT_POINTS = 6000       # Maximum number of points to display on the plot

class SerialHandler:
    def __init__(self):
        self.port = None
        self.baudrate = 230400
        self.serial_connection = None
        self.running = False
        self.data = {
            "time": [],
            "laptop_time": [],
            "ir_temp": [[] for _ in range(8)],
            "tc_temp": [[], []],
            "load": [],
            "brake_pressure": [],  # Brake pressure data (in PSI)
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
                        ir_temps = [float(values[i]) for i in range(1, 9)]
                        tc_temps = [float(values[9]), float(values[10])]
                        load_cell = float(values[11])
                        brake_pressure = float(values[12])
                        rotor_rpm = float(values[13])
                        self.data["time"].append(time_measured)
                        self.data["laptop_time"].append(current_time)
                        for i in range(8):
                            self.data["ir_temp"][i].append(ir_temps[i])
                        for i in range(2):
                            self.data["tc_temp"][i].append(tc_temps[i])
                        self.data["load"].append(load_cell)
                        self.data["brake_pressure"].append(brake_pressure)
                        self.data["rotor_rpm"].append(rotor_rpm)
                        # Save data as is (in °C for IR sensors)
                        csv_line = f"{time_measured}," + ",".join([f"{v}" for v in ir_temps]) + \
                                   f",{tc_temps[0]},{tc_temps[1]},{load_cell},{brake_pressure},{rotor_rpm},{current_time}\n"
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
        if self.export_file is not None:
            self.export_file.close()
            self.export_file = None

class PlotHandler:
    def __init__(self, root):
        self.root = root
        self.canvas = None
        self.animation = None
        self.serial_handler = None
        self.visible_plots = ["ir_temp", "load", "rpm", "tc1", "tc2", "brake_pressure"]  # Added brake pressure to visible_plots list
        self.visible_ir_sensors = []
        self.plot_objects = {}
        self.fig = plt.figure(figsize=(10, 20))
        self.plots_info = {
            'ir_temp': {
                'visible': BooleanVar(value=True),
                'title': "IR Temperature Readings",
                'ylabel': "Temp (°F)",  # Changed label to °F
                'xlabel': "Sensors"
            },
            'ir_sensor_1': {
            'visible': BooleanVar(value=False),
            'title': "IR Sensor 1 Temperature vs Time",
            'ylabel': "Temp (°F)",
            'xlabel': "Time (s)"
            },
            'ir_sensor_2': {
                'visible': BooleanVar(value=False),
                'title': "IR Sensor 2 Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'ir_sensor_3': {
                'visible': BooleanVar(value=False),
                'title': "IR Sensor 3 Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'ir_sensor_4': {
                'visible': BooleanVar(value=False),
                'title': "IR Sensor 4 Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'ir_sensor_5': {
                'visible': BooleanVar(value=False),
                'title': "IR Sensor 5 Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'ir_sensor_6': {
                'visible': BooleanVar(value=False),
                'title': "IR Sensor 6 Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'ir_sensor_7': {
                'visible': BooleanVar(value=False),
                'title': "IR Sensor 7 Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'ir_sensor_8': {
                'visible': BooleanVar(value=False),
                'title': "IR Sensor 8 Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'load': {
                'visible': BooleanVar(value=True),
                'title': "Load Cell Force vs Time",
                'ylabel': "Force (lbs)",
                'xlabel': "Time (s)"
            },
            'rpm': {
                'visible': BooleanVar(value=True),
                'title': "Rotor RPM vs Time",
                'ylabel': "RPM",
                'xlabel': "Time (s)"
            },
            'tc1': {
                'visible': BooleanVar(value=True),
                'title': "Pad Temperature vs Time",
                'ylabel': "Temp (°C)",
                'xlabel': "Time (s)"
            },
            'tc2': {
                'visible': BooleanVar(value=True),
                'title': "Caliper Temperature vs Time",
                'ylabel': "Temp (°C)",
                'xlabel': "Time (s)"
            },
            'brake_pressure': {  # New plot info for brake pressure
                'visible': BooleanVar(value=True),
                'title': "Brake Pressure vs Time",
                'ylabel': "Pressure (PSI)",
                'xlabel': "Time (s)"
            }
        }
        self.ir_labels = [f"IR {i+1}" for i in range(8)]
        self.setup_average_frame()
        self.setup_control_panel()

    

    def toggle_ir_sensor(self, sensor_num):
        """Toggle visibility of a specific IR sensor's time plot"""
        plot_name = f'ir_sensor_{sensor_num}'
        current_state = self.plots_info[plot_name]['visible'].get()
        self.plots_info[plot_name]['visible'].set(not current_state)
        self.update_plot_layout()
    def show_about_popup(self):
            # Create settings popup window
            popup = ctk.CTkToplevel(self.root)
            popup.title("Settings & About")
            popup.geometry("500x600")
    
            # Make it appear on top of the main window
            popup.transient(self.root)  # Set as transient to main window
            popup.grab_set()  # Make it modal
            popup.focus_set()  # Give it keyboard focus
    
            # Optional: Center the popup relative to the main window
            popup.geometry(f"+{self.root.winfo_x() + 50}+{self.root.winfo_y() + 50}")
    
            # Create a tabview to organize settings and about info
            tabview = ctk.CTkTabview(popup, width=480, height=550)
            tabview.pack(padx=10, pady=10, fill="both", expand=True)
    
            # Create tabs
            settings_tab = tabview.add("Settings")
            manual_tab = tabview.add("Manual")
            about_tab = tabview.add("About")
    
            # Settings Tab
            settings_tab.grid_columnconfigure(0, weight=1)
            settings_tab.grid_columnconfigure(1, weight=1)
    
            # Section 1: Units Settings
            units_frame = ctk.CTkFrame(settings_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
            units_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
    
            ctk.CTkLabel(units_frame, text="Display Units", font=FONT_HEADER, text_color=TEXT_COLOR).pack(pady=(10, 5))
    
            # Create a BooleanVar if it doesn't exist yet
            if not hasattr(self, 'use_imperial'):
                self.use_imperial = BooleanVar(value=True)  # Default to imperial (already showing °F)
    
            imperial_switch = ctk.CTkSwitch(
                units_frame, 
                text="Use Imperial Units (°F, lbs, psi)", 
                variable=self.use_imperial,
                command=self.toggle_units,
                font=FONT_SMALL,
                text_color=TEXT_COLOR,
                switch_width=60,
                button_color="#48aeff",
                button_hover_color="#2a80ff",
                fg_color="#d0d0d0"
    )
            imperial_switch.pack(pady=10, padx=20, anchor="w")
    
            # Section 2: Averaging Settings
            avg_frame = ctk.CTkFrame(settings_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
            avg_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
    
            ctk.CTkLabel(avg_frame, text="Averaging Settings", font=FONT_HEADER, text_color=TEXT_COLOR).pack(pady=(10, 5))
    
            avg_label = ctk.CTkLabel(avg_frame, text="Number of samples\nfor averaging:", font=FONT_SMALL, text_color=TEXT_COLOR)
            avg_label.pack(anchor="w", padx=20, pady=(10, 5))
    
            # Create IntVar if it doesn't exist yet
            if not hasattr(self, 'avg_samples'):
                self.avg_samples = ctk.IntVar(value=100)  # Default to 100 samples
    
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
    
            # Section 3: Plot Settings
            plot_frame = ctk.CTkFrame(settings_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
            plot_frame.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")
    
            ctk.CTkLabel(plot_frame, text="Plot Settings", font=FONT_HEADER, text_color=TEXT_COLOR).pack(pady=(10, 5))
    
            # Refresh rate setting
            refresh_label = ctk.CTkLabel(plot_frame, text="Plot refresh rate (ms):", font=FONT_SMALL, text_color=TEXT_COLOR)
            refresh_label.pack(anchor="w", padx=20, pady=(10, 5))
    
            if not hasattr(self, 'plot_refresh_rate'):
                self.plot_refresh_rate = ctk.IntVar(value=PLOT_UPDATE_INTERVAL)
    
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
    
            # Max points setting
            max_points_label = ctk.CTkLabel(plot_frame, text="Max data points shown:", font=FONT_SMALL, text_color=TEXT_COLOR)
            max_points_label.pack(anchor="w", padx=20, pady=(10, 5))
    
            if not hasattr(self, 'max_plot_points'):
                self.max_plot_points = ctk.IntVar(value=MAX_PLOT_POINTS)
    
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
            apply_button.grid(row=2, column=0, columnspan=2, pady=20)
    
        # Manual Tab - Simple layout with just the button
            manual_frame = ctk.CTkFrame(manual_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
            manual_frame.pack(padx=10, pady=10, fill="both", expand=True)
            
            manual_label = ctk.CTkLabel(
                manual_frame,
                text="Click the button below to open the\nBrake Dyno Instruction Manual",
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


                        # About Tab Content
            about_frame = ctk.CTkFrame(about_tab, fg_color=WIDGET_BG_COLOR, corner_radius=10)
            about_frame.pack(padx=10, pady=10, fill="both", expand=True)

            # Create a frame for the text to control its size
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
        """Open the instruction manual PDF"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            manual_path = os.path.join(script_dir, "Brake_Dyno_GUI_Instruction_Manual_2_27_25.pdf")
            
            # Check if file exists
            if os.path.exists(manual_path):
                # Use appropriate OS-specific command to open the PDF
                if sys.platform.startswith('darwin'):  # macOS
                    import subprocess
                    subprocess.call(('open', manual_path))
                elif sys.platform.startswith('win'):   # Windows
                    os.startfile(manual_path)
                else:  # Linux and other Unix-like systems
                    import subprocess
                    subprocess.call(('xdg-open', manual_path))
            else:
                # Show an error message if the manual file is not found
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
                ).pack(pady=(0, 20))
        except Exception as e:
            print(f"Error opening manual: {e}")
          
    def toggle_units(self):
            """Toggle between imperial and metric units for display"""
            # Update the labels in the PlotHandler
            is_imperial = self.use_imperial.get()
    
            # Update the IR temperature label
            ir_ylabel = "Temp (°F)" if is_imperial else "Temp (°C)"
            self.plot_handler.plots_info['ir_temp']['ylabel'] = ir_ylabel
            self.plot_handler.ir_average_label.configure(
            text=f"IR Temperatures ({ir_ylabel.split(' ')[1]})"
    )
    
            # Force update of plots and averages
            self.plot_handler.update_plot_layout()
            self.plot_handler.update_plot(0)

    def set_avg_samples(self, value):
            """Set the number of samples to use for averaging"""
            if value == "All":
                self.avg_samples.set(-1)  # Use all available samples
            else:
                self.avg_samples.set(int(value))

    def set_refresh_rate(self, value):
            """Set the plot refresh rate"""
            self.plot_refresh_rate.set(int(value))

    def set_max_points(self, value):
            """Set the maximum number of points to display"""
            self.max_plot_points.set(int(value))

    def apply_settings(self):
            """Apply all settings changes"""
            # Update the plot refresh interval
            if self.plot_handler.animation:
                self.plot_handler.animation.event_source.stop()
                self.plot_handler.animation = animation.FuncAnimation(
                    self.plot_handler.fig,
                    self.plot_handler.update_plot,
                    interval=self.plot_refresh_rate.get(),
                    cache_frame_data=False
        )
    
            # Update the MAX_PLOT_POINTS in PlotHandler
            global MAX_PLOT_POINTS
            MAX_PLOT_POINTS = self.max_plot_points.get()
    
            # Force redraw of the plots
            self.plot_handler.update_plot_layout()
            self.plot_handler.update_plot(0)

        # Add "About Program" button at the bottom of the left (average) frame.
            about_button = ctk.CTkButton(self.plot_handler.average_frame, text="About Program", font=FONT_BUTTON,
                                     fg_color="#eeeeee", hover_color="#48aeff", text_color="#131313",
                                     command=self.show_about_popup)
            about_button.pack(side="bottom", fill="x", padx=10, pady=(10,15))

    def setup_average_frame(self):
        self.average_frame = ctk.CTkFrame(self.root, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        self.average_frame.pack(side="left", fill="y", padx=(10, 0), pady=10)
        
        # Add a scrollable frame container inside average_frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self.average_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        self.scrollable_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        ir_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR)
        ir_frame.pack(pady=5, padx=10, fill="x")
        
        # Optionally, update the label to indicate °F
        self.ir_average_label = ctk.CTkLabel(ir_frame, text="IR Temperatures (°F)", font=FONT_HEADER, text_color=TEXT_COLOR)
        self.ir_average_label.pack(pady=(15,5))
        
        self.ir_average_values = []
        for i in range(8):
            label = ctk.CTkLabel(ir_frame, text=f"IR {i+1}: 0.00", font=FONT_SMALL, text_color=TEXT_COLOR)
            label.pack(pady=1)
            self.ir_average_values.append(label)
        
        tc_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        tc_frame.pack(pady=10, padx=10, fill="x")
        
        self.tc_average_label = ctk.CTkLabel(tc_frame, text="Thermocouple Temperatures", font=FONT_HEADER, text_color=TEXT_COLOR)
        self.tc_average_label.pack(pady=5)
        
        self.pad_average_label = ctk.CTkLabel(tc_frame, text="Pad Average: 0.00", font=FONT_SMALL, text_color=TEXT_COLOR)
        self.pad_average_label.pack(pady=2)
        
        self.caliper_average_label = ctk.CTkLabel(tc_frame, text="Caliper Average: 0.00", font=FONT_SMALL, text_color=TEXT_COLOR)
        self.caliper_average_label.pack(pady=1)
        
        load_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        load_frame.pack(pady=10, padx=10, fill="x")
        
        self.load_average_label = ctk.CTkLabel(load_frame, text="Load Cell Average: 0.00", font=FONT_HEADER, text_color=TEXT_COLOR)
        self.load_average_label.pack(pady=1)
        
        rpm_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
        rpm_frame.pack(pady=10, padx=10, fill="x")
        
        self.rpm_average_label = ctk.CTkLabel(rpm_frame, text="RPM Average: 0.00", font=FONT_HEADER, text_color=TEXT_COLOR)
        self.rpm_average_label.pack(pady=1)

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
            control_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=WIDGET_BG_COLOR, corner_radius=0)
            control_frame.pack(pady=10, padx=10, fill="x")
            ctk.CTkLabel(control_frame, text="Display Graphs", font=FONT_TITLE, text_color=TEXT_COLOR).pack(pady=5)
            for plot_name, info in self.plots_info.items():
                ctk.CTkCheckBox(
                    control_frame,
                    text=info['title'],
                    variable=info['visible'],
                    command=self.update_plot_layout,
                    font=FONT_CHECKBOX,
                    text_color=TEXT_COLOR,
                    fg_color="#ffffff",
                    checkmark_color="#48aeff",
                    hover_color="#eeeeee",
                    border_color="#48aeff",
                    border_width=2,
                    corner_radius=5
                ).pack(anchor='w', pady=10)
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
        if num_visible == 0:
            self.canvas.draw()
            return
        for i, plot_name in enumerate(self.visible_plots):
            ax = self.fig.add_subplot(num_visible, 1, i + 1)
            ax.set_ylabel(self.plots_info[plot_name]['ylabel'], fontsize=14)
            ax.grid(True, linestyle="--", alpha=0.7)
            self.plots_info[plot_name]['axis'] = ax
        self.fig.tight_layout()
        self.canvas.draw()

    def update_plot(self, frame):
        if not self.serial_handler or not self.serial_handler.data["time"]:
            return
        times = self.serial_handler.data["time"]
        start_time = times[0]
        rel_times = [t - start_time for t in times]
        plot_times = rel_times[-MAX_PLOT_POINTS:]
    
        for plot_name in self.visible_plots:
            ax = self.plots_info[plot_name]['axis']
        
            if plot_name == 'ir_temp':
                # Convert IR temperatures from °C to °F for display in the GUI.
                latest_ir_temps_C = [self.serial_handler.data["ir_temp"][i][-1] for i in range(8)]
                latest_ir_temps_F = [temp * 9/5 + 32 for temp in latest_ir_temps_C]
                if "ir_temp" in self.plot_objects:
                    for rect, h in zip(self.plot_objects["ir_temp"], latest_ir_temps_F):
                        rect.set_height(h)
                else:
                    bars = ax.bar(self.ir_labels, latest_ir_temps_F, color="blue")
                    self.plot_objects["ir_temp"] = bars
                ax.set_ylim(min(latest_ir_temps_F) - 10, max(latest_ir_temps_F) + 10)
            
            elif plot_name.startswith('ir_sensor_'):
                # Handle individual IR sensor plots
                sensor_idx = int(plot_name.split('_')[-1]) - 1  # Get 0-based index from plot name
            
                # Get temperature data for this sensor
                temp_data_C = self.serial_handler.data["ir_temp"][sensor_idx][-MAX_PLOT_POINTS:]
            
                # Convert to Fahrenheit if needed
                imperial = getattr(self.root, 'use_imperial', BooleanVar(value=True)).get()
                if imperial:
                    y_data = [temp * 9/5 + 32 for temp in temp_data_C]  # Convert to °F
                    unit = "°F"
                else:
                    y_data = temp_data_C  # Keep as °C
                    unit = "°C"
                
                # Update or create the plot
                if plot_name in self.plot_objects:
                    line = self.plot_objects[plot_name]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label=f"IR Sensor {sensor_idx+1} ({unit})", color=f"C{sensor_idx % 10}")
                    self.plot_objects[plot_name] = line
                
                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")

            elif plot_name == 'load':
                y_data = self.serial_handler.data["load"][-MAX_PLOT_POINTS:]
                if "load" in self.plot_objects:
                    line = self.plot_objects["load"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Load (lbs)", color="red")
                    self.plot_objects["load"] = line
                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")
            elif plot_name == 'rpm':
                y_data = self.serial_handler.data["rotor_rpm"][-MAX_PLOT_POINTS:]
                if "rpm" in self.plot_objects:
                    line = self.plot_objects["rpm"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Rotor RPM", color="green")
                    self.plot_objects["rpm"] = line
                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")
            elif plot_name == 'tc1':
                y_data = self.serial_handler.data["tc_temp"][0][-MAX_PLOT_POINTS:]
                if "tc1" in self.plot_objects:
                    line = self.plot_objects["tc1"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Pad Temperature", color="purple")
                    self.plot_objects["tc1"] = line
                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")
            elif plot_name == 'tc2':
                y_data = self.serial_handler.data["tc_temp"][1][-MAX_PLOT_POINTS:]
                if "tc2" in self.plot_objects:
                    line = self.plot_objects["tc2"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Caliper Temperature", color="orange")
                    self.plot_objects["tc2"] = line
                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")
            elif plot_name == 'brake_pressure':  # New branch for brake pressure plot
                y_data = self.serial_handler.data["brake_pressure"][-MAX_PLOT_POINTS:]
                if "brake_pressure" in self.plot_objects:
                    line = self.plot_objects["brake_pressure"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Brake Pressure (PSI)", color="brown")
                    self.plot_objects["brake_pressure"] = line
                ax.relim()
                ax.autoscale_view()
                ax.legend(loc="upper left")
        self.update_averages()
        self.canvas.draw()

        if not self.serial_handler or not self.serial_handler.data["time"]:
                return
    
            # Get settings from root if they exist
        max_points = getattr(self.root, 'max_plot_points', None)
        use_imperial = getattr(self.root, 'use_imperial', None)
    
            # Set defaults if the variables haven't been created yet
        if max_points is None:
            max_points = ctk.IntVar(value=MAX_PLOT_POINTS)
            self.root.max_plot_points = max_points
    
        if use_imperial is None:
            use_imperial = BooleanVar(value=True)  # Default to imperial (already showing °F)
            self.root.use_imperial = use_imperial
    
        # Use the settings
        max_plot_points = max_points.get()
        imperial = use_imperial.get()
    
        times = self.serial_handler.data["time"]
        start_time = times[0]
        rel_times = [t - start_time for t in times]
        plot_times = rel_times[-max_plot_points:]
    
        for plot_name in self.visible_plots:
            ax = self.plots_info[plot_name]['axis']
        
        if plot_name == 'ir_temp':
            # Get latest IR temperatures
            latest_ir_temps_C = [self.serial_handler.data["ir_temp"][i][-1] for i in range(8)]
            
            # Convert if needed
            if imperial:
                latest_ir_temps = [temp * 9/5 + 32 for temp in latest_ir_temps_C]  # Convert to °F
            else:
                latest_ir_temps = latest_ir_temps_C  # Keep as °C
            
            if "ir_temp" in self.plot_objects:
                for rect, h in zip(self.plot_objects["ir_temp"], latest_ir_temps):
                    rect.set_height(h)
            else:
                bars = ax.bar(self.ir_labels, latest_ir_temps, color="blue")
                self.plot_objects["ir_temp"] = bars
            
            ax.set_ylim(min(latest_ir_temps) - 10, max(latest_ir_temps) + 10)
            
        elif plot_name == 'load':
            y_data = self.serial_handler.data["load"][-max_plot_points:]
            if "load" in self.plot_objects:
                line = self.plot_objects["load"]
                line.set_data(plot_times, y_data)
            else:
                line, = ax.plot(plot_times, y_data, label="Load (lbs)", color="red")
                self.plot_objects["load"] = line
            ax.relim()
            ax.autoscale_view()
            ax.legend(loc="upper left")
            
        elif plot_name == 'rpm':
            y_data = self.serial_handler.data["rotor_rpm"][-max_plot_points:]
            if "rpm" in self.plot_objects:
                line = self.plot_objects["rpm"]
                line.set_data(plot_times, y_data)
            else:
                line, = ax.plot(plot_times, y_data, label="Rotor RPM", color="green")
                self.plot_objects["rpm"] = line
            ax.relim()
            ax.autoscale_view()
            ax.legend(loc="upper left")
            
        elif plot_name == 'tc1':
            # Get thermocouple data
            tc_data_C = self.serial_handler.data["tc_temp"][0][-max_plot_points:]
            
            # Convert if needed
            if imperial:
                y_data = [temp * 9/5 + 32 for temp in tc_data_C]  # Convert to °F
                if "tc1" in self.plot_objects:
                    line = self.plot_objects["tc1"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Pad Temperature (°F)", color="purple")
                    self.plot_objects["tc1"] = line
            else:
                y_data = tc_data_C  # Keep as °C
                if "tc1" in self.plot_objects:
                    line = self.plot_objects["tc1"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Pad Temperature (°C)", color="purple")
                    self.plot_objects["tc1"] = line
            
            ax.relim()
            ax.autoscale_view()
            ax.legend(loc="upper left")
            
        elif plot_name == 'tc2':
            # Get thermocouple data
            tc_data_C = self.serial_handler.data["tc_temp"][1][-max_plot_points:]
            
            # Convert if needed
            if imperial:
                y_data = [temp * 9/5 + 32 for temp in tc_data_C]  # Convert to °F
                if "tc2" in self.plot_objects:
                    line = self.plot_objects["tc2"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Caliper Temperature (°F)", color="orange")
                    self.plot_objects["tc2"] = line
            else:
                y_data = tc_data_C  # Keep as °C
                if "tc2" in self.plot_objects:
                    line = self.plot_objects["tc2"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Caliper Temperature (°C)", color="orange")
                    self.plot_objects["tc2"] = line
            
            ax.relim()
            ax.autoscale_view()
            ax.legend(loc="upper left")
            
        elif plot_name == 'brake_pressure':
            y_data = self.serial_handler.data["brake_pressure"][-max_plot_points:]
            if "brake_pressure" in self.plot_objects:
                line = self.plot_objects["brake_pressure"]
                line.set_data(plot_times, y_data)
            else:
                line, = ax.plot(plot_times, y_data, label="Brake Pressure (PSI)", color="brown")
                self.plot_objects["brake_pressure"] = line
            ax.relim()
            ax.autoscale_view()
            ax.legend(loc="upper left")
    
        self.update_averages()
        self.canvas.draw()

    def update_averages(self):
        for i in range(8):
            data = self.serial_handler.data["ir_temp"][i]
            if data:
                avg_C = sum(data) / len(data)
                avg_F = avg_C * 9/5 + 32  # Convert to °F
            else:
                avg_F = 0
            self.ir_average_values[i].configure(text=f"IR {i+1}: {avg_F:.2f}")
        for key, label in [("load", self.load_average_label),
                           ("rotor_rpm", self.rpm_average_label)]:
            data = self.serial_handler.data[key]
            avg = sum(data) / len(data) if data else 0
            label.configure(text=f"{key.replace('_', ' ').title()} Average: {avg:.2f}")
        for idx, lbl in enumerate([self.pad_average_label, self.caliper_average_label]):
            data = self.serial_handler.data["tc_temp"][idx]
            avg = sum(data) / len(data) if data else 0
            lbl.configure(text=f"{'Pad' if idx == 0 else 'Caliper'} Average: {avg:.2f}")

            # Get the number of samples to use for averaging
            avg_samples = getattr(self.root, 'avg_samples', None)
            use_imperial = getattr(self.root, 'use_imperial', None)
    
            # Set defaults if the variables haven't been created yet
            if avg_samples is None:
                avg_samples = ctk.IntVar(value=100)
                self.root.avg_samples = avg_samples
    
            if use_imperial is None:
                use_imperial = BooleanVar(value=True)  # Default to imperial (already showing °F)
                self.root.use_imperial = use_imperial
    
            sample_count = avg_samples.get()
            imperial = use_imperial.get()
    
            for i in range(8):
                data = self.serial_handler.data["ir_temp"][i]
                if data:
                    # Use all data or the specified number of samples
                    if sample_count <= 0 or sample_count >= len(data):
                        temp_data = data
                    else:
                        temp_data = data[-sample_count:]
                
                    avg_C = sum(temp_data) / len(temp_data)
            
                    # Display in the selected units
                    if imperial:
                        avg_temp = avg_C * 9/5 + 32  # Convert to °F
                        unit = "°F"
                    else:
                        avg_temp = avg_C  # Keep as °C
                        unit = "°C"
                else:
                    avg_temp = 0
                    unit = "°F" if imperial else "°C"
        
                self.ir_average_values[i].configure(text=f"IR {i+1}: {avg_temp:.2f} {unit}")
    
            # Update load cell average
            data = self.serial_handler.data["load"]
            if data:
                if sample_count <= 0 or sample_count >= len(data):
                    load_data = data
                else:
                    load_data = data[-sample_count:]
        
                avg = sum(load_data) / len(load_data)
            else:
                avg = 0
    
            self.load_average_label.configure(text=f"Load Cell Average: {avg:.2f} lbs")
    
            # Update RPM average
            data = self.serial_handler.data["rotor_rpm"]
            if data:
                if sample_count <= 0 or sample_count >= len(data):
                    rpm_data = data
                else:
                    rpm_data = data[-sample_count:]
        
                avg = sum(rpm_data) / len(rpm_data)
            else:
                avg = 0
    
            self.rpm_average_label.configure(text=f"RPM Average: {avg:.2f}")
    
            # Update thermocouple averages
            for idx, lbl in enumerate([self.pad_average_label, self.caliper_average_label]):
                data = self.serial_handler.data["tc_temp"][idx]
                if data:
                    if sample_count <= 0 or sample_count >= len(data):
                        tc_data = data
                    else:
                        tc_data = data[-sample_count:]
            
                avg_C = sum(tc_data) / len(tc_data)
            
                    # Display in the selected units
                if imperial:
                        avg_temp = avg_C * 9/5 + 32  # Convert to °F
                        unit = "°F"
                else:
                        avg_temp = avg_C  # Keep as °C
                        unit = "°C"
            else:
                    avg_temp = 0
                    unit = "°F" if imperial else "°C"
        
                    lbl.configure(text=f"{'Pad' if idx == 0 else 'Caliper'} Average: {avg_temp:.2f} {unit}")        

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
        ctk.set_appearance_mode("light")
        self.root.title("Brake Dyno Data Acquisition")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}")
        self.serial_handler = SerialHandler()
        self.plot_handler = PlotHandler(self.root)
        self.export_folder = None
        self.load_icons()
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

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
        # Outer main frame with adjustable background
        main_frame = ctk.CTkFrame(self.root, fg_color=ROOT_BG_COLOR, corner_radius=0)
        main_frame.pack(expand=True, fill="both")
        
        icon_frame = ctk.CTkFrame(main_frame, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        icon_frame.pack(fill="x", padx=10, pady=(10, 0))
        left_icon_label = ctk.CTkLabel(icon_frame, image=self.left_icon_ctk, text="", text_color=TEXT_COLOR)
        left_icon_label.pack(side="left", padx=20)
        center_frame = ctk.CTkFrame(icon_frame, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        center_frame.pack(side="left", expand=True, fill="x", padx=20)
        
        # Create a grid frame for the buttons (3 rows x 2 columns)
        grid_frame = ctk.CTkFrame(center_frame, fg_color=WIDGET_BG_COLOR, corner_radius=15)
        grid_frame.pack(pady=5, anchor="center")
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        
        # Row 0: COM dropdown, Select Export Folder
        self.com_port_dropdown = ctk.CTkComboBox(grid_frame, values=self.get_available_ports(), font=FONT_HEADER,
                                                  width=100, command=self.update_port_selection)
        if self.get_available_ports():
            self.com_port_dropdown.set(self.get_available_ports()[0])
            self.serial_handler.set_port(self.get_available_ports()[0])
        self.com_port_dropdown.grid(row=0, column=0, padx=10, pady=5)
        self.export_folder_button = ctk.CTkButton(grid_frame, text="Select Export Folder", font=FONT_BUTTON,
                                                  command=self.select_export_folder, fg_color="#d0d0ff", 
                                                  hover_color="#b0b0ff", text_color=TEXT_COLOR)
        self.export_folder_button.grid(row=0, column=1, padx=10, pady=5)
        
        # Row 1: START, EXPORT
        self.start_button = ctk.CTkButton(grid_frame, text="START", font=FONT_BUTTON,
                                          command=self.start_reading, fg_color="#baffc9", 
                                          hover_color="#89e4a4", text_color=TEXT_COLOR, text_color_disabled="#555555")
        self.start_button.grid(row=1, column=0, padx=10, pady=5)
        self.export_button = ctk.CTkButton(grid_frame, text="START EXPORT", font=FONT_BUTTON,
                                           command=self.start_export, fg_color="#baffc9", 
                                           hover_color="#89e4a4", text_color=TEXT_COLOR, state="disabled", text_color_disabled="#555555")
        self.export_button.grid(row=1, column=1, padx=10, pady=5)
        
        # Row 2: STOP, STOP EXPORT
        self.stop_button = ctk.CTkButton(grid_frame, text="STOP", font=FONT_BUTTON,
                                         command=self.stop_reading, fg_color="#ffb3ba", 
                                         hover_color="#ff8ca3", text_color=TEXT_COLOR, state="disabled", text_color_disabled="#555555")
        self.stop_button.grid(row=2, column=0, padx=10, pady=5)
        self.stop_export_button = ctk.CTkButton(grid_frame, text="STOP EXPORT", font=FONT_BUTTON,
                                                command=self.stop_export, fg_color="#ffb3ba", 
                                                hover_color="#ff8ca3", text_color=TEXT_COLOR, state="disabled", text_color_disabled="#555555")
        self.stop_export_button.grid(row=2, column=1, padx=10, pady=5)
        
        right_icon_label = ctk.CTkLabel(icon_frame, image=self.right_icon_ctk, text="", text_color=TEXT_COLOR)
        right_icon_label.pack(side="right", padx=20, pady=10)
        
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
            # Enable the start export button once a folder is selected
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
            # Toggle button states: disable start and enable stop for reading
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            # Optionally disable the COM port dropdown while running
            self.com_port_dropdown.configure(state="disabled")
        else:
            print("Please select a COM port.")

    def stop_reading(self):
        self.serial_handler.stop_serial()
        self.plot_handler.stop_plotting()
        # Toggle button states: enable start and disable stop for reading
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        # Re-enable the COM port dropdown after stopping
        self.com_port_dropdown.configure(state="normal")

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
            # Toggle export button states: disable export button and enable stop export button
            self.export_button.configure(state="disabled")
            self.stop_export_button.configure(state="normal")
        except Exception as e:
            print(f"Error creating export file: {e}")

    def stop_export(self):
        if self.serial_handler.export_file is not None:
            self.serial_handler.export_file.close()
            self.serial_handler.export_file = None
            print("Export stopped.")
            # Toggle export button states: enable export button and disable stop export button
            self.export_button.configure(state="normal")
            self.stop_export_button.configure(state="disabled")
        else:
            print("No export active.")

    

    def on_closing(self):
        self.stop_export()
        self.serial_handler.stop_serial()
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RootGUI()
    app.run()