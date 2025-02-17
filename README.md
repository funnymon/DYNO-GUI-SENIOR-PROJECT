DAQ Data Readings Application
This application is designed to read real-time data from a DAQ (Data Acquisition) system connected via a serial port. It allows users to visualize and analyze various sensor readings such as IR temperatures, load cell force, rotor RPM, brake pressure, and thermocouple temperatures through dynamic plots. The data is collected via a COM port and can be exported to a CSV file for further analysis.

Features:

Real-time data visualization: View multiple plots of sensor data (IR temperatures, load cell, rotor RPM, and thermocouple temperatures).

Dynamic control panel: Toggle between various plots and visualize data in real time.

Data export: Save collected data to a CSV file for future analysis.

Running averages: Display running averages of sensor values while the system is running.

Installation

Install Dependencies: This application uses tkinter, matplotlib, serial, and PIL (Pillow). You can install these dependencies using pip:


pip install tkinter matplotlib pyserial pillow

Ensure you have a COM port: The application requires a serial connection to a device that provides data in a specific format. Make sure your device is connected and accessible via a COM port.

Setup the Environment:

Place the required icons (left_icon.png, right_icon.jpg) in the same directory as the Python script. These icons are used in the GUI for visual appeal.
Usage

Start the Application: Run the Python script to launch the GUI:

python your_script_name.py

Select COM Port: Once the application is open, select the appropriate COM port for the device you want to connect to. The dropdown will list available ports, and the application will automatically choose the first one by default.

Start Data Collection: Click the "START" button to begin reading data from the serial port. The data will be plotted in real time, and you can toggle different plots on or off.

Stop Data Collection: Click the "STOP" button to stop data collection. You can view the collected data up to that point.

Export Data: Click the "EXPORT" button to save the collected data as a CSV file. The file will be saved with a timestamp in the filename.

Control Plot Visibility: Use the checkboxes in the control panel to toggle the visibility of different plots (IR temperature, load cell, rotor RPM, thermocouple temperatures).

Data Format

The data is expected to be in a comma-separated format from the serial connection, with the following fields:

Time (ms)

8 IR sensor temperatures

2 thermocouple temperatures (Pad, Caliper)

Load cell force (N)

Brake pressure

Rotor RPM

Example Data Format

1620294785, 25.4, 26.1, 27.3, 24.8, 25.6, 27.1, 26.5, 24.9, 300.4, 305.6, 125.3, 2.5, 3500
Time: 1620294785 (milliseconds)
IR temperatures: 25.4, 26.1, 27.3, ...
Thermocouple temperatures: 300.4 (Pad), 305.6 (Caliper)
Load cell force: 125.3 (N)
Brake pressure: 2.5
Rotor RPM: 3500


License
This project is licensed under the MIT License - see the LICENSE file for details.

