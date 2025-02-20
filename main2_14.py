import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import os
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk, filedialog
from datetime import datetime

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
            "brake_pressure": [],
            "rotor_rpm": []
        }

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
                        # Get current laptop time
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

                except Exception as e:
                    print(f"Data read error: {e}")

    def stop_serial(self):
        self.running = False
        if self.serial_connection:
            self.serial_connection.close()

class PlotHandler:
    def __init__(self, root):
        self.root = root
        self.plot_frame = None
        self.canvas = None
        self.animation = None
        self.serial_handler = None
        self.all_plots_visible = True
        self.visible_plots = []

        # Create figure
        self.fig = plt.figure(figsize=(10, 20))
        
        # Create axes but don't assign positions yet
        self.ax_ir = self.fig.add_subplot(111)
        self.ax_load = self.fig.add_subplot(111)
        self.ax_rpm = self.fig.add_subplot(111)
        self.ax_tc1 = self.fig.add_subplot(111)
        self.ax_tc2 = self.fig.add_subplot(111)

        # Dictionary to store plot information
        self.plots_info = {
            'ir_temp': {
                'visible': tk.BooleanVar(value=False),
                'axis': self.ax_ir,
                'title': "IR Temperature Readings",
                'ylabel': "Temp (°F)",
                'xlabel': "Sensors"
            },
            'load': {
                'visible': tk.BooleanVar(value=False),
                'axis': self.ax_load,
                'title': "Load Cell Force vs Time",
                'ylabel': "Force (N)",
                'xlabel': "Time (s)"
            },
            'rpm': {
                'visible': tk.BooleanVar(value=False),
                'axis': self.ax_rpm,
                'title': "Rotor RPM vs Time",
                'ylabel': "RPM",
                'xlabel': "Time (s)"
            },
            'tc1': {
                'visible': tk.BooleanVar(value=False),
                'axis': self.ax_tc1,
                'title': "Pad Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            },
            'tc2': {
                'visible': tk.BooleanVar(value=False),
                'axis': self.ax_tc2,
                'title': "Caliper Temperature vs Time",
                'ylabel': "Temp (°F)",
                'xlabel': "Time (s)"
            }
        }

        # Initialize average display frame
        self.setup_average_frame()
        
        # Initialize control panel
        self.setup_control_panel()

        # Initialize IR temperature bars
        self.ir_labels = [f"IR {i+1}" for i in range(8)]
        self.ir_bars = self.ax_ir.bar(self.ir_labels, [0] * 8, color="blue")

    def setup_average_frame(self):
        self.average_frame = tk.Frame(self.root, relief="ridge", borderwidth=2)
        self.average_frame.pack(side="left", fill="y", padx=20, pady=10)

        title_label = tk.Label(self.average_frame, text="Running Averages", 
                             font=("Arial", 14, "bold"), pady=10)
        title_label.pack()

        # IR Sensors frame
        ir_frame = tk.Frame(self.average_frame, relief="solid", borderwidth=1)
        ir_frame.pack(pady=5, padx=10, fill="x")
        
        self.ir_average_label = tk.Label(ir_frame, text="IR Temperatures", 
                                       font=("Arial", 12, "bold"))
        self.ir_average_label.pack(pady=5)
        
        self.ir_average_values = []
        for i in range(8):
            label = tk.Label(ir_frame, text=f"IR {i+1}: 0.00", 
                           font=("Arial", 10, "bold"))
            label.pack(pady=2)
            self.ir_average_values.append(label)
        
        # Thermocouple frame
        tc_frame = tk.Frame(self.average_frame, relief="solid", borderwidth=1)
        tc_frame.pack(pady=10, padx=10, fill="x")
    
        self.tc_average_label = tk.Label(tc_frame, text="Thermocouple Temperatures", 
                                   font=("Arial", 12, "bold"))
        self.tc_average_label.pack(pady=5)
    
        self.pad_average_label = tk.Label(tc_frame, text="Pad Average: 0.00", 
                                    font=("Arial", 10, "bold"))
        self.pad_average_label.pack(pady=2)
    
        self.caliper_average_label = tk.Label(tc_frame, text="Caliper Average: 0.00", 
                                        font=("Arial", 10, "bold"))
        self.caliper_average_label.pack(pady=2)

        # Load Cell frame
        load_frame = tk.Frame(self.average_frame, relief="solid", borderwidth=1)
        load_frame.pack(pady=10, padx=10, fill="x")
        self.load_average_label = tk.Label(load_frame, text="Load Cell Average: 0.00", 
                                         font=("Arial", 12, "bold"))
        self.load_average_label.pack(pady=5)

        # RPM frame
        rpm_frame = tk.Frame(self.average_frame, relief="solid", borderwidth=1)
        rpm_frame.pack(pady=10, padx=10, fill="x")
        self.rpm_average_label = tk.Label(rpm_frame, text="RPM Average: 0.00", 
                                        font=("Arial", 12, "bold"))
        self.rpm_average_label.pack(pady=5)

    def setup_control_panel(self):
        control_frame = tk.Frame(self.average_frame, relief="solid", borderwidth=1)
        control_frame.pack(pady=10, padx=10, fill="x")
        
        tk.Label(control_frame, text="Display Graphs", 
                font=("Arial", 12, "bold")).pack(pady=5)
        
        # Create checkboxes
        for plot_name, info in self.plots_info.items():
            tk.Checkbutton(
                control_frame,
                text=info['title'],
                variable=info['visible'],
                command=self.update_plot_layout,
                font=("Arial", 14)
            ).pack(anchor='w')

        # Add Open/Close All button
        self.toggle_all_button = tk.Button(
            control_frame,
            text="Open/Close All Plots",
            command=self.toggle_all_plots,
            font=("Arial", 14)
        )
        self.toggle_all_button.pack(pady=10)

    def toggle_all_plots(self):
        self.all_plots_visible = not self.all_plots_visible
        for plot_info in self.plots_info.values():
            plot_info['visible'].set(self.all_plots_visible)
        self.update_plot_layout()

    def update_plot_layout(self):
        # Get currently visible plots
        
        self.visible_plots = [
            name for name, info in self.plots_info.items()
            if info['visible'].get()
        ]
        
        num_visible = len(self.visible_plots)
        
        if num_visible == 0:
            self.hide_all_plots()
            return
        
        # Clear the figure
        self.fig.clear()
        
        # Create new subplot layout
        for i, plot_name in enumerate(self.visible_plots):
            # Create new subplot
            ax = self.fig.add_subplot(num_visible, 1, i+1)
            
            # Update axis reference in plots_info
            self.plots_info[plot_name]['axis'] = ax
            
            # Set up axis properties
            ax.set_title(self.plots_info[plot_name]['title'], fontsize=16)
            ax.set_xlabel(self.plots_info[plot_name]['xlabel'], fontsize=14)
            ax.set_ylabel(self.plots_info[plot_name]['ylabel'], fontsize=14)
            ax.grid(True, linestyle="--", alpha=0.7)
            
            if plot_name == 'ir_temp':
                self.ir_bars = ax.bar(self.ir_labels, [0] * 8, color="blue")

        self.fig.tight_layout()
        if self.canvas:
            self.canvas.draw()

    def hide_all_plots(self):
        self.fig.clear()
        if self.canvas:
            self.canvas.draw()

    def create_plots(self, frame):
        self.plot_frame = frame
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.update_plot_layout()

    def update_plot(self, frame):
        if not self.serial_handler or not self.serial_handler.data["time"]:
            return

        times = self.serial_handler.data["time"]
        if not times:
            return

        start_time = times[0]
        adjusted_times = [t - start_time for t in times]

         # Ensure all arrays have the same length
        min_length = min(
        len(adjusted_times),
        len(self.serial_handler.data["load"]),
        len(self.serial_handler.data["rotor_rpm"]),
        len(self.serial_handler.data["tc_temp"][0]),
        len(self.serial_handler.data["tc_temp"][1])
    )
        adjusted_times = adjusted_times[:min_length]
        self.serial_handler.data["load"] = self.serial_handler.data["load"][:min_length]
        self.serial_handler.data["rotor_rpm"] = self.serial_handler.data["rotor_rpm"][:min_length]
        self.serial_handler.data["tc_temp"][0] = self.serial_handler.data["tc_temp"][0][:min_length]
        self.serial_handler.data["tc_temp"][1] = self.serial_handler.data["tc_temp"][1][:min_length]
        
        for plot_name in self.visible_plots:
            ax = self.plots_info[plot_name]['axis']
            ax.clear()
            
            if plot_name == 'ir_temp':
                latest_ir_temps = [self.serial_handler.data["ir_temp"][i][-1] for i in range(8)]
                self.ir_bars = ax.bar(self.ir_labels, latest_ir_temps, color="blue")
                ax.set_ylim(min(latest_ir_temps) - 10, max(latest_ir_temps) + 10)
            
            elif plot_name == 'load':
                load_data = self.serial_handler.data["load"]
                min_length = min(len(adjusted_times), len(load_data))
                adjusted_times = adjusted_times[:min_length]
                load_data = load_data[:min_length]
                ax.plot(adjusted_times, load_data, label="Load (N)", color="red")
                if load_data:
                    y_min, y_max = min(load_data), max(load_data)
                    y_min, y_max = min(load_data), max(load_data)
                    if y_min == y_max:  # If the min and max are identical, adjust the limits
                        y_min -= 1
                        y_max += 1
                    margin = (y_max - y_min) * 0.1  # 10% margin
                    ax.set_ylim(y_min - margin, y_max + margin)

                
            elif plot_name == 'rpm':
                rpm_data = self.serial_handler.data["rotor_rpm"]
                min_length = min(len(adjusted_times), len(rpm_data))
                adjusted_times = adjusted_times[:min_length]
                rpm_data = rpm_data[:min_length]
                ax.plot(adjusted_times, rpm_data, label="Rotor RPM", color="green")
                if rpm_data:
                    y_min, y_max = min(rpm_data), max(rpm_data)
                    if y_min == y_max:  # If the min and max are identical, adjust the limits
                        y_min -= 1
                        y_max += 1
                    margin = (y_max - y_min) * 0.1
                    ax.set_ylim(y_min - margin, y_max + margin)
                
            elif plot_name == 'Thermo Pad':
                tc_data = self.serial_handler.data["tc_temp"][0]
                min_length = min(len(adjusted_times), len(tc_data))
                adjusted_times = adjusted_times[:min_length]
                tc_data = tc_data[:min_length]
                ax.plot(adjusted_times, tc_data, label="Pad Temperature", color="purple")
                if tc_data:
                    y_min, y_max = min(tc_data), max(tc_data)
                    if y_min == y_max:  # If the min and max are identical, adjust the limits
                        y_min -= 1
                        y_max += 1
                    margin = (y_max - y_min) * 0.1
                    ax.set_ylim(y_min - margin, y_max + margin)
                
            elif plot_name == 'Caliper':
                tc_data = self.serial_handler.data["tc_temp"][1]
                min_length = min(len(adjusted_times), len(tc_data))
                adjusted_times = adjusted_times[:min_length]
                tc_data = tc_data[:min_length]
                ax.plot(adjusted_times, tc_data, label="Caliper Temperature", color="orange")
                if tc_data:
                    y_min, y_max = min(tc_data), max(tc_data)
                    if y_min == y_max:  # If the min and max are identical, adjust the limits
                        y_min -= 1
                        y_max += 1
                    margin = (y_max - y_min) * 0.1
                    ax.set_ylim(y_min - margin, y_max + margin)
            
            # Restore axis properties
            ax.set_title(self.plots_info[plot_name]['title'], fontsize=16)
            ax.set_xlabel(self.plots_info[plot_name]['xlabel'], fontsize=14)
            ax.set_ylabel(self.plots_info[plot_name]['ylabel'], fontsize=14)
            ax.grid(True, linestyle="--", alpha=0.7)
            ax.legend()

        self.update_averages()
        self.canvas.draw()

    def update_averages(self):
        if not self.serial_handler or not self.serial_handler.data["time"]:
            return

        for i in range(8):
            ir_avg = self.calculate_running_average(self.serial_handler.data["ir_temp"][i])
            self.ir_average_values[i].config(text=f"IR {i+1}: {ir_avg:.2f}")

        load_avg = self.calculate_running_average(self.serial_handler.data["load"])
        self.load_average_label.config(text=f"Load Cell Average: {load_avg:.2f}")

        rpm_avg = self.calculate_running_average(self.serial_handler.data["rotor_rpm"])
        self.rpm_average_label.config(text=f"RPM Average: {rpm_avg:.2f}")

        # Update Pad and Caliper averages
        pad_avg = self.calculate_running_average(self.serial_handler.data["tc_temp"][0])
        caliper_avg = self.calculate_running_average(self.serial_handler.data["tc_temp"][1])
        self.pad_average_label.config(text=f"Pad Average: {pad_avg:.2f}")
        self.caliper_average_label.config(text=f"Caliper Average: {caliper_avg:.2f}")

    def calculate_running_average(self, data):
        return sum(data) / len(data) if data else 0

    def start_plotting(self, serial_handler):
        self.serial_handler = serial_handler
        self.animation = animation.FuncAnimation(
            self.fig, self.update_plot, interval=0.1, cache_frame_data=False
        )

    def stop_plotting(self):
        if self.animation:
            self.animation.event_source.stop()

class RootGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DAQ Data Readings")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}")

        self.serial_handler = SerialHandler()
        self.running = False
        self.plot_handler = PlotHandler(self.root)

        self.load_icons()
        self.create_widgets()

    def load_icons(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        left_icon_path = os.path.join(script_dir, "left_icon.png")
        self.left_icon = Image.open(left_icon_path)
        self.left_icon = self.left_icon.resize((373, 169), Image.Resampling.LANCZOS)
        self.left_icon_tk = ImageTk.PhotoImage(self.left_icon)

        right_icon_path = os.path.join(script_dir, "right_icon.jpg")
        self.right_icon = Image.open(right_icon_path)
        self.right_icon = self.right_icon.resize((200, 200), Image.Resampling.LANCZOS)
        self.right_icon_tk = ImageTk.PhotoImage(self.right_icon)

    def get_available_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def update_port_selection(self, event):
        selected_port = self.com_port_var.get()
        self.serial_handler.set_port(selected_port)

    def create_widgets(self):
        # Icon frame for top of window
        icon_frame = tk.Frame(self.root, bg="white")
        icon_frame.pack(fill="x", pady=10)

        # Left icon
        left_icon_label = tk.Label(icon_frame, image=self.left_icon_tk, bg="white")
        left_icon_label.pack(side="left", padx=20)

        # Center frame for controls
        center_frame = tk.Frame(icon_frame, bg="white")
        center_frame.pack(side="left", expand=True, fill="x", padx=20)

        button_frame = tk.Frame(center_frame, bg="white")
        button_frame.pack(pady=5)
        
        # Control buttons
        tk.Button(button_frame, text="START", font=("Arial", 14), command=self.start_reading,
              bg="green", fg="white").pack(side="left", padx=10)
              
        tk.Button(button_frame, text="STOP", font=("Arial", 14), command=self.stop_reading,
              bg="red", fg="white").pack(side="left", padx=10)
              
        tk.Button(button_frame, text="EXPORT", font=("Arial", 14), 
              command=self.export_data).pack(side="left", padx=10)
        
        # COM Port selection
        com_frame = tk.Frame(center_frame, bg="white")
        com_frame.pack(pady=5)
        tk.Label(com_frame, text="Select COM Port:", font=("Arial", 12), bg="white").pack(side="left", padx=5)
        
        self.com_port_var = tk.StringVar()
        self.com_port_dropdown = ttk.Combobox(com_frame, 
                                            textvariable=self.com_port_var,
                                            font=("Arial", 12),
                                            width=10,
                                            state="readonly")
        
        # Populate dropdown with available ports
        available_ports = self.get_available_ports()
        self.com_port_dropdown['values'] = available_ports
        if available_ports:
            self.com_port_dropdown.set(available_ports[0])
            self.serial_handler.set_port(available_ports[0])
        
        self.com_port_dropdown.pack(side="left", padx=10)
        self.com_port_dropdown.bind('<<ComboboxSelected>>', self.update_port_selection)

        # Right icon
        right_icon_label = tk.Label(icon_frame, image=self.right_icon_tk, bg="white")
        right_icon_label.pack(side="right", padx=20)
        
        # Plot frame
        plot_frame = tk.Frame(self.root)
        plot_frame.pack(expand=True, fill="both")
        self.plot_handler.create_plots(plot_frame)

    def start_reading(self):
        selected_port = self.com_port_var.get()
        if selected_port:
            self.serial_handler.set_port(selected_port)
            self.serial_handler.start_serial()
            self.plot_handler.start_plotting(self.serial_handler)
        else:
            print("Please select a COM port.")

    def stop_reading(self):
        self.serial_handler.stop_serial()
        self.plot_handler.stop_plotting()

    def export_data(self):
        if not self.serial_handler.data["time"]:
            print("No data to export")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
        default_filename = f"data_{timestamp}.csv"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("Text files", "*.csv"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    # Write header
                    header = "Time,IR1,IR2,IR3,IR4,IR5,IR6,IR7,IR8,PAD,Caliper,Load,Brake_Pressure,Rotor_RPM,Laptop_Time\n"
                    f.write(header)

                    # Adjust time to start at 0
                    start_time = self.serial_handler.data["time"][0]
                    adjusted_times = [t - start_time for t in self.serial_handler.data["time"]]

                    # Write data
                    for i in range(len(self.serial_handler.data["time"])):
                        line = f"{adjusted_times[i]}"
                        for j in range(8):
                            line += f",{self.serial_handler.data['ir_temp'][j][i]}"
                        for j in range(2):
                            line += f",{self.serial_handler.data['tc_temp'][j][i]}"
                        
                        line += f",{self.serial_handler.data['load'][i]}"
                        line += f",{self.serial_handler.data['brake_pressure'][i]}"
                        line += f",{self.serial_handler.data['rotor_rpm'][i]}"
                        line += f",{self.serial_handler.data['laptop_time'][i]}\n"
                        f.write(line)

                print(f"Data exported successfully to {file_path}")
            except Exception as e:
                print(f"Error exporting data: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RootGUI()
    app.run()