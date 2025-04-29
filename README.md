# Brake Dynamometer DAQ GUI

This application is designed to read real-time data from a DAQ (Data Acquisition) system via a serial port. It allows users to visualize and analyze various sensor readings such as IR temperatures, load cell force, rotor RPM, brake pressure, and thermocouple temperatures through dynamic plots. Data can be exported to a CSV file for further analysis.

---

## Features

- **Real-time Data Visualization:**  
  View multiple plots for sensor data, including IR temperatures, load cell readings, rotor RPM, and thermocouple temperatures.

- **Dynamic Control Panel:**  
  Toggle between various plots and visualize data in real time.

- **Data Export:**  
  Save collected data to a CSV file for future analysis.

- **Running Averages:**  
  Display running averages of sensor values during operation.

---

## Installation

### Dependencies

This application requires the following Python libraries:
- `tkinter`
- `matplotlib`
- `pyserial`
- `pillow` (PIL)
- `numpy`
- `pandas`
- `scipy`

Install these dependencies using pip:

```bash
pip install customtkinter tkinter matplotlib pyserial pillow numpy pandas scipy
```

### COM Port Setup

Ensure you have a working COM port:
- The application requires a serial connection to a device that outputs data in a specific comma-separated format.
- Verify that your device is connected and accessible via a COM port.

### Environment Setup

Place the required icon files in the same directory as the Python script:
- `left_icon.png`
- `right_icon.jpg`

These icons are used in the GUI for visual appeal.

---

## Usage

1. **Start the Application:**  
   Run the Python script to launch the GUI:

   ```bash
   python your_script_name.py
   ```

2. **Select COM Port:**  
   Once the application is open, select the appropriate COM port for your device. A dropdown menu will list available ports, with the first one selected by default.

3. **Start Data Collection:**  
   Click the **START** button to begin reading data from the serial port. Data will be plotted in real time, and you can toggle different plots on or off.

4. **Stop Data Collection:**  
   Click the **STOP** button to end the data collection session. You can then review the data collected up to that point.

5. **Export Data:**  
   Click the **EXPORT** button to save the collected data as a CSV file. The filename will include a timestamp.

6. **Control Plot Visibility:**  
   Use the checkboxes in the control panel to toggle the visibility of different plots (e.g., IR temperature, load cell, rotor RPM, thermocouple temperatures).

---

## Data Format

The application expects data in a comma-separated format with the following fields:

- **Time:** (milliseconds)
- **8 IR sensor temperatures**
- **2 Thermocouple temperatures:** (Pad, Caliper)
- **Load cell force:** (N)
- **Brake pressure**
- **Rotor RPM**

### Example Data Format

```
1620294785, 25.4, 26.1, 27.3, 24.8, 25.6, 27.1, 26.5, 24.9, 300.4, 305.6, 125.3, 2.5, 3500
```

- **Time:** 1620294785 (milliseconds)
- **IR Temperatures:** 25.4, 26.1, 27.3, ...
- **Thermocouple Temperatures:** 300.4 (Pad), 305.6 (Caliper)
- **Load Cell Force:** 125.3 (N)
- **Brake Pressure:** 2.5
- **Rotor RPM:** 3500

---

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
