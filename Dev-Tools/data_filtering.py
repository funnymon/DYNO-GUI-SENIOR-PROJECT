# This script filters data from a CSV file using a low pass Butterworth filter.
# It converts temperature readings from Celsius to Fahrenheit and saves the filtered data to a new CSV file.
# Time is adjusted to start from 0 seconds.
# Usage: Run the script and select a CSV file when prompted.

import pandas as pd
from scipy.signal import butter, filtfilt
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import os

def low_pass_filter(data, cutoff, fs, order=4):
    """
    Applies a Butterworth low pass filter with a given cutoff frequency.
    
    Parameters:
    - data: array of data values.
    - cutoff: cutoff frequency in Hz.
    - fs: sampling frequency in Hz.
    - order: order of the filter (default is 4).
    
    Returns:
    - filtered_data: the filtered data array.
    """
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    filtered_data = filtfilt(b, a, data)
    return filtered_data

def main():
    # Open a file selector dialog to choose the input CSV file
    Tk().withdraw()  # Hide the root Tkinter window
    input_file = askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv")])
    
    if not input_file:
        print("No file selected. Exiting.")
        return
    
    # Read the selected CSV file
    df = pd.read_csv(input_file, sep=",")
    
    # Ensure the "Time" column is numeric
    df["Time"] = pd.to_numeric(df["Time"], errors="coerce")
    
    # Adjust the "Time" column to start from 0
    df["Time"] = df["Time"] - df["Time"].iloc[0]
    
    # # Convert temperatures from Celsius to Fahrenheit
    # temp_columns = ["IR1", "IR2", "IR3", "IR4", "IR5", "IR6", "IR7", "IR8", "PAD", "Caliper"]
    # for col in temp_columns:
    #     if col in df.columns:
    #         df[col] = df[col] * 9 / 5 + 32  # Celsius to Fahrenheit conversion
    
    # Compute the sampling interval and frequency from the "Time" column
    # Assumes the time column is sorted and has uniform sampling intervals
    dt = df["Time"].iloc[1] - df["Time"].iloc[0]
    fs = 1.0 / dt
    
    # Define the cutoff frequency (in Hz)
    cutoff = 0.1
    
    # Select columns to filter: exclude the first and last column
    columns_to_filter = df.columns[1:-1]
    
    # Apply the low pass filter to each selected column
    for col in columns_to_filter:
        df[col] = low_pass_filter(df[col].values, cutoff, fs, order=4)
    
    # Generate the output filename with '_filtered' appended
    base_name, ext = os.path.splitext(input_file)
    output_file = f"{base_name}_filtered{ext}"
    
    # Save the filtered DataFrame to a new CSV file
    df.to_csv(output_file, index=False, sep=",")
    print(f"Filtering complete. Output saved to '{output_file}'.")

if __name__ == '__main__':
    main()
