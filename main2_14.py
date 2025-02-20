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

# Enable auto light/dark mode
ctk.set_appearance_mode("System")

# Global Font Constants
FONT_TITLE = ("Arial", 16, "bold")
FONT_HEADER = ("Arial", 14, "bold")
FONT_SMALL = ("Arial", 14)
FONT_BUTTON = ("Arial", 14, "bold")
FONT_CHECKBOX = ("Arial", 14)

# Global Text Colors for light/dark modes
DARK_TEXT_COLOR = "white"
LIGHT_TEXT_COLOR = "black"

def get_text_color():
    return DARK_TEXT_COLOR if ctk.get_appearance_mode() == "Dark" else LIGHT_TEXT_COLOR

# Global widget foreground color constants
WIDGET_FG_COLOR_DARK = "#2B2B2B"
WIDGET_FG_COLOR_LIGHT = "white"

def get_widget_fg_color():
    return WIDGET_FG_COLOR_DARK if ctk.get_appearance_mode() == "Dark" else WIDGET_FG_COLOR_LIGHT

# Global image height constants
LEFT_ICON_HEIGHT = 150
RIGHT_ICON_HEIGHT = 120

def resize_image_to_height(image, height):
    original_width, original_height = image.size
    new_width = int((original_width / original_height) * height)
    return image.resize((new_width, height), Image.Resampling.LANCZOS)

# Global constants for plotting
PLOT_UPDATE_INTERVAL = 1000  # milliseconds
MAX_PLOT_POINTS = 10000

class SerialHandler:
    def __init__(self):
        self.port = None
        self.baudrate = 230400
        self.serial_connection = None
        self.running = False

        # Save all received data here (all data are saved continuously)
        self.data = {
            "time": [],
            "laptop_time": [],
            "ir_temp": [[] for _ in range(8)],
            "tc_temp": [[], []],
            "load": [],
            "brake_pressure": [],
            "rotor_rpm": []
        }
        # File handle for export (active only while exporting)
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

                        # Append data (all data are stored)
                        self.data["time"].append(time_measured)
                        self.data["laptop_time"].append(current_time)
                        for i in range(8):
                            self.data["ir_temp"][i].append(ir_temps[i])
                        for i in range(2):
                            self.data["tc_temp"][i].append(tc_temps[i])
                        self.data["load"].append(load_cell)
                        self.data["brake_pressure"].append(brake_pressure)
                        self.data["rotor_rpm"].append(rotor_rpm)

                        # Write to CSV if export is active (data from this point onward)
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
        self.plot_frame = None
        self.canvas = None
        self.animation = None
        self.serial_handler = None
        # All plots visible by default; these names are used in the checkboxes
        self.visible_plots = ["ir_temp", "load", "rpm", "tc1", "tc2"]
        # Dictionary to hold plot objects for efficient updating
        self.plot_objects = {}

        # Create figure
        self.fig = plt.figure(figsize=(10, 20))
        self.plots_info = {
            'ir_temp': {
                'visible': BooleanVar(value=True),
                'title': "IR Temperature Readings",
                'ylabel': "Temp (°F)",
                'xlabel': "Sensors"
            },
            'load': {
                'visible': BooleanVar(value=True),
                'title': "Load Cell Force vs Time",
                'ylabel': "Force (N)",
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
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'tc2': {
                'visible': BooleanVar(value=True),
                'title': "Caliper Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            }
        }
        self.ir_labels = [f"IR {i+1}" for i in range(8)]
        self.setup_average_frame()
        self.setup_control_panel()

    def setup_average_frame(self):
        self.average_frame = ctk.CTkFrame(self.root, fg_color=get_widget_fg_color(), corner_radius=15)
        self.average_frame.pack(side="left", fill="y", padx=10, pady=10)
        title_label = ctk.CTkLabel(self.average_frame, text="Running Averages", font=FONT_TITLE, text_color=get_text_color())
        title_label.pack(pady=10)

        # IR Sensors frame
        ir_frame = ctk.CTkFrame(self.average_frame, fg_color=get_widget_fg_color())
        ir_frame.pack(pady=5, padx=10, fill="x")
        self.ir_average_label = ctk.CTkLabel(ir_frame, text="IR Temperatures", font=FONT_HEADER, text_color=get_text_color())
        self.ir_average_label.pack(pady=5)
        self.ir_average_values = []
        for i in range(8):
            label = ctk.CTkLabel(ir_frame, text=f"IR {i+1}: 0.00", font=FONT_SMALL, text_color=get_text_color())
            label.pack(pady=1)
            self.ir_average_values.append(label)

        # Thermocouple frame
        tc_frame = ctk.CTkFrame(self.average_frame, fg_color=get_widget_fg_color(), corner_radius=0)
        tc_frame.pack(pady=10, padx=10, fill="x")
        self.tc_average_label = ctk.CTkLabel(tc_frame, text="Thermocouple Temperatures", font=FONT_HEADER, text_color=get_text_color())
        self.tc_average_label.pack(pady=5)
        self.pad_average_label = ctk.CTkLabel(tc_frame, text="Pad Average: 0.00", font=FONT_SMALL, text_color=get_text_color())
        self.pad_average_label.pack(pady=2)
        self.caliper_average_label = ctk.CTkLabel(tc_frame, text="Caliper Average: 0.00", font=FONT_SMALL, text_color=get_text_color())
        self.caliper_average_label.pack(pady=1)

        # Load Cell frame
        load_frame = ctk.CTkFrame(self.average_frame, fg_color=get_widget_fg_color(), corner_radius=0)
        load_frame.pack(pady=10, padx=10, fill="x")
        self.load_average_label = ctk.CTkLabel(load_frame, text="Load Cell Average: 0.00", font=FONT_HEADER, text_color=get_text_color())
        self.load_average_label.pack(pady=1)

        # RPM frame
        rpm_frame = ctk.CTkFrame(self.average_frame, fg_color=get_widget_fg_color(), corner_radius=0)
        rpm_frame.pack(pady=10, padx=10, fill="x")
        self.rpm_average_label = ctk.CTkLabel(rpm_frame, text="RPM Average: 0.00", font=FONT_HEADER, text_color=get_text_color())
        self.rpm_average_label.pack(pady=1)

    def setup_control_panel(self):
        control_frame = ctk.CTkFrame(self.average_frame, fg_color=get_widget_fg_color(), corner_radius=0)
        control_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(control_frame, text="Display Graphs", font=FONT_TITLE, text_color=get_text_color()).pack(pady=5)
        for plot_name, info in self.plots_info.items():
            ctk.CTkCheckBox(
                control_frame,
                text=info['title'],
                variable=info['visible'],
                command=self.update_plot_layout,
                font=FONT_CHECKBOX,
                text_color=get_text_color()
            ).pack(anchor='w', pady=10)
        # A button to force refresh the plot layout
        self.refresh_button = ctk.CTkButton(
            control_frame,
            text="Refresh Plots",
            command=self.update_plot_layout,
            font=FONT_BUTTON,
            text_color=get_text_color()
        )
        self.refresh_button.pack(pady=10)

    def update_plot_layout(self):
        # Recreate the subplots based on current checkbox selections
        self.visible_plots = [name for name, info in self.plots_info.items() if info['visible'].get()]
        self.plot_objects = {}  # clear previous plot objects
        self.fig.clf()
        num_visible = len(self.visible_plots)
        if num_visible == 0:
            self.canvas.draw()
            return
        for i, plot_name in enumerate(self.visible_plots):
            ax = self.fig.add_subplot(num_visible, 1, i + 1)
            ax.set_title(self.plots_info[plot_name]['title'], fontsize=16)
            ax.set_xlabel(self.plots_info[plot_name]['xlabel'], fontsize=14)
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
                latest_ir_temps = [self.serial_handler.data["ir_temp"][i][-1] for i in range(8)]
                if "ir_temp" in self.plot_objects:
                    for rect, h in zip(self.plot_objects["ir_temp"], latest_ir_temps):
                        rect.set_height(h)
                else:
                    bars = ax.bar(self.ir_labels, latest_ir_temps, color="blue")
                    self.plot_objects["ir_temp"] = bars
                ax.set_ylim(min(latest_ir_temps) - 10, max(latest_ir_temps) + 10)
            elif plot_name == 'load':
                y_data = self.serial_handler.data["load"][-MAX_PLOT_POINTS:]
                if "load" in self.plot_objects:
                    line = self.plot_objects["load"]
                    line.set_data(plot_times, y_data)
                else:
                    line, = ax.plot(plot_times, y_data, label="Load (N)", color="red")
                    self.plot_objects["load"] = line
                ax.relim()
                ax.autoscale_view()
                ax.legend()
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
                ax.legend()
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
                ax.legend()
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
                ax.legend()
        self.update_averages()
        self.canvas.draw()

    def update_averages(self):
        for i in range(8):
            data = self.serial_handler.data["ir_temp"][i]
            avg = sum(data) / len(data) if data else 0
            self.ir_average_values[i].configure(text=f"IR {i+1}: {avg:.2f}")
        for key, label in [("load", self.load_average_label),
                           ("rotor_rpm", self.rpm_average_label)]:
            data = self.serial_handler.data[key]
            avg = sum(data) / len(data) if data else 0
            label.configure(text=f"{key.replace('_', ' ').title()} Average: {avg:.2f}")
        for idx, lbl in enumerate([self.pad_average_label, self.caliper_average_label]):
            data = self.serial_handler.data["tc_temp"][idx]
            avg = sum(data) / len(data) if data else 0
            lbl.configure(text=f"{'Pad' if idx == 0 else 'Caliper'} Average: {avg:.2f}")

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
        self.root.title("DAQ Data Readings")
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
        icon_frame = ctk.CTkFrame(self.root, fg_color=get_widget_fg_color(), corner_radius=15)
        icon_frame.pack(fill="x", padx=10, pady=10)
        left_icon_label = ctk.CTkLabel(icon_frame, image=self.left_icon_ctk, text="", text_color=get_text_color())
        left_icon_label.pack(side="left", padx=20)
        center_frame = ctk.CTkFrame(icon_frame, fg_color=get_widget_fg_color(), corner_radius=15)
        center_frame.pack(side="left", expand=True, fill="x", padx=20)
        button_frame = ctk.CTkFrame(center_frame, fg_color=get_widget_fg_color(), corner_radius=15)
        button_frame.pack(pady=5)
        ctk.CTkButton(
            button_frame, text="START", font=FONT_BUTTON,
            command=self.start_reading, fg_color="#baffc9", text_color=get_text_color()
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            button_frame, text="STOP", font=FONT_BUTTON,
            command=self.stop_reading, fg_color="#ffb3ba", text_color=get_text_color()
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            button_frame, text="Select Export Folder", font=FONT_BUTTON,
            command=self.select_export_folder, fg_color="#d0d0ff", text_color=get_text_color()
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            button_frame, text="EXPORT", font=FONT_BUTTON,
            command=self.start_export, fg_color="#baffc9", text_color=get_text_color()
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            button_frame, text="STOP EXPORT", font=FONT_BUTTON,
            command=self.stop_export, fg_color="#ffb3ba", text_color=get_text_color()
        ).pack(side="left", padx=10)
        com_frame = ctk.CTkFrame(center_frame, fg_color=get_widget_fg_color(), corner_radius=0)
        com_frame.pack(pady=5)
        ctk.CTkLabel(com_frame, text="Select COM Port:", font=FONT_HEADER, text_color=get_text_color()).pack(side="left", padx=5)
        available_ports = self.get_available_ports()
        self.com_port_dropdown = ctk.CTkComboBox(com_frame, values=available_ports, font=FONT_HEADER,
                                                  width=100, command=self.update_port_selection)
        if available_ports:
            self.com_port_dropdown.set(available_ports[0])
            self.serial_handler.set_port(available_ports[0])
        self.com_port_dropdown.pack(side="left", padx=10)
        right_icon_label = ctk.CTkLabel(icon_frame, image=self.right_icon_ctk, text="", text_color=get_text_color())
        right_icon_label.pack(side="right", padx=20, pady=10)
        plot_frame = ctk.CTkFrame(self.root, fg_color=get_widget_fg_color(), corner_radius=15)
        plot_frame.pack(expand=True, fill="both", padx=10, pady=10)
        # Instead of calling create_plots(), manually create the canvas and call update_plot()
        self.plot_handler.canvas = FigureCanvasTkAgg(self.plot_handler.fig, master=plot_frame)
        self.plot_handler.canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)
        self.plot_handler.update_plot(0)

    def select_export_folder(self):
        folder = filedialog.askdirectory(title="Select Export Folder")
        if folder:
            self.export_folder = folder
            print(f"Export folder set to: {folder}")
        else:
            self.export_folder = None
            print("No folder selected.")

    def start_reading(self):
        selected_port = self.com_port_dropdown.get()
        if selected_port:
            self.serial_handler.set_port(selected_port)
            self.serial_handler.start_serial()
            self.plot_handler.start_plotting(self.serial_handler)
        else:
            print("Please select a COM port.")

    def start_export(self):
        if not self.export_folder:
            print("Please select a valid export folder first.")
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
        csv_filename = os.path.join(self.export_folder, f"data_{timestamp}.csv")
        try:
            f = open(csv_filename, "w")
            header = "Time,IR1,IR2,IR3,IR4,IR5,IR6,IR7,IR8,PAD,Caliper,Load,Brake_Pressure,Rotor_RPM,Laptop_Time\n"
            f.write(header)
            self.serial_handler.export_file = f
            print(f"Export file created: {csv_filename}")
        except Exception as e:
            print(f"Error creating export file: {e}")

    def stop_export(self):
        if self.serial_handler.export_file is not None:
            self.serial_handler.export_file.close()
            self.serial_handler.export_file = None
            print("Export stopped.")
        else:
            print("No export active.")

    def stop_reading(self):
        self.serial_handler.stop_serial()
        self.plot_handler.stop_plotting()

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
