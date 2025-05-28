# Brake Dynamometer DAQ GUI

This application is designed to read real-time data from a DAQ (Data Acquisition) system via a serial port. It allows users to visualize and analyze various sensor readings such as IR temperatures, load cell force, rotor RPM, brake pressure, and thermocouple temperatures through dynamic plots. Data can be exported to a CSV file for further analysis.

![alt text](<Assets/Screenshot of GUI.png>)
---

## Features

-   **Real-time Data Visualization:**  
    View multiple plots for sensor data, including IR temperatures, load cell readings, rotor RPM, and thermocouple temperatures.

-   **Dynamic Control Panel:**  
    Toggle between various plots and visualize data in real time.

-   **Data Export:**  
    Save collected data to a CSV file for future analysis.

-   **Running Averages:**  
    Display running averages of sensor values during operation.

---

## Installation Guide for Beginners

This guide will walk you through setting up the Brake Dynamometer DAQ GUI on your system. Follow these steps to get the application running.

### 1. Install Visual Studio Code (VS Code)

-   **Download VS Code:** Go to the [VS Code website](https://code.visualstudio.com/) and download the installer for your operating system.
-   **Install VS Code:** Run the installer and follow the on-screen instructions.

### 2. Install Git

-   **Download Git:** Go to the [Git website](https://git-scm.com/downloads) and download the installer for your operating system.
-   **Install Git:** Run the installer and follow the on-screen instructions. Ensure that Git is added to your system's PATH during installation.
-   **Verify Installation:** Open a terminal or command prompt and type `git --version`. If Git is installed correctly, you should see the Git version number.

### 3. Clone the Repository

-   **Open a Terminal or Command Prompt:**
      -   **Windows:** Press `Win + R`, type `cmd`, and press Enter.
      -   **macOS:** Press `Cmd + Space`, type `terminal`, and press Enter.
-   **Navigate to the Desired Directory:** Use the `cd` command to navigate to the directory where you want to store the project. For example, to clone into a folder named "DYNO" in your Documents directory, you would use:

      ```bash
      cd Documents
      mkdir DYNO
      cd DYNO
      ```

-   **Clone the Repository:** Use the following command to clone the repository:

      ```bash
      git clone "https://github.com/funnymon/DYNO-GUI-SENIOR-PROJECT"
      ```


### 4. Set Up VS Code for Python

-   **Install the Python Extension:**
    -   Open VS Code.
    -   Go to the Extensions view by clicking on the Extensions icon in the Activity Bar on the side of the window (or press `Ctrl+Shift+X`).
    -   Search for "Python" and install the Microsoft Python extension.
-   **Open the Project Folder:**
    -   In VS Code, click on `File` \> `Open Folder...` and select the folder where you cloned the repository.

### 5. Install Required Python Libraries

-   **Open a Terminal in VS Code:**
    -   In VS Code, click on `View` \> `Terminal` to open the integrated terminal.
-   **Install Dependencies:**
    -   Use the following command to install the required Python libraries:

        ```bash
        pip install customtkinter matplotlib pyserial pillow numpy pandas scipy
        ```

        This command installs the following libraries:
        -   `customtkinter`: For creating the GUI.
        -   `matplotlib`: For plotting data.
        -   `pyserial`: For serial communication.
        -   `pillow` (PIL): For image processing.
        -   `numpy`: For numerical computations.
        -   `pandas`: For data manipulation and analysis.
        -   `scipy`: For scientific computing and signal processing.

### 6. Run the Application

-   **Open the Main Python File:** In VS Code, navigate to the main Python file (e.g., `main2_14.py`).
-   **Run the Script:**
    -   Click on the play icon on the top right.
    -   Right-click in the editor and select "Run Python File in Terminal".
    -   Alternatively, you can use the keyboard shortcut `Ctrl+Shift+P` to open the Command Palette, type "Run Python File in Terminal", and press Enter.

### 7. Configure COM Port

-   **Identify COM Port:** Determine the COM port that the DAQ board (Adafruit) is connected to.
-   **Select COM Port in the GUI:** In the GUI, select the appropriate COM port from the dropdown menu.

---

## Usage

1.  **Start the Application:** Run the Python script to launch the GUI.
2.  **Select COM Port:** Choose the appropriate COM port from the dropdown menu.
3.  **Select Export Folder:** Click the "Select Export Folder" button to choose a folder for saving the exported data.
4.  **Start Reading Data:** Click the "START" button to begin reading data from the serial port and visualizing it in the plots.
5.  **Export Data:** Click the "START EXPORT" button to start exporting the data to a CSV file.
6.  **Stop Reading/Exporting:** Click the "STOP" and "STOP EXPORT" buttons to halt the respective processes.

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
