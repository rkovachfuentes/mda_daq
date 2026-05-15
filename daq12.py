#!/usr/bin/env python3

"""
Changes done in daq11.py
- HV voltage added 
"""

import csv
from datetime import datetime
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for integration with tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
import os
import pyvisa
import time
import threading
from tkinter import Tk, Button, Label, Frame, Entry

# Tektronix Oscilloscope Configuration
ip_address = "10.10.10.2"
resource_string = f"TCPIP::{ip_address}::INSTR"
verbose=1

# Connect to the oscilloscope
rm = pyvisa.ResourceManager()
scope = rm.open_resource(resource_string)
scope.timeout = 200000  # 20 seconds timeout

# Global control flags
acquire_data        = False
channel_2_on        = False # Changed to false 


def generate_file_name(directory):
    # Get the current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    base_name = f"scope-results-{current_date}-"
    file_pattern = f"{base_name}????.csv"

    # List files in the directory matching the pattern
    existing_files = [
        f for f in os.listdir(directory) 
        if f.startswith(base_name) and f.endswith(".csv") and len(f) == len(file_pattern)
    ]

    # Extract the numbers from existing files and find the highest
    highest_number = 0
    for file in existing_files:
        try:
            number = int(file[-8:-4])  # Extract the 4-digit number
            highest_number = max(highest_number, number)
        except ValueError:
            pass  # Skip files that don't match the naming pattern

    # Generate the new file name
    new_number = highest_number + 1
    new_file_name = f"{base_name}{new_number:04d}.csv"

    full_path = os.path.join(directory, new_file_name)
    return full_path

# Function to acquire waveform data
def acquire_waveform():
    global acquire_data
    global data_directory

    print("acquire_waveform")
    while acquire_data:
        try:
            # Start acquisition and wait for trigger
            #scope.write("ACQ:STATE ON")  # Start acquisition
            scope.write("ACQUIRE:STATE ON")  # Equivalent to pressing Run
            time.sleep(0.01)  # With this time parameter we can took data of 110V and 191V
            
            start_time = time.time()
            acquire_state = scope.query("ACQUIRE:STATE?").strip()  #
            #print("before loop2 setting state ", acquire_state)
            while acquire_state == "0" :
               print("inside loop acquire_state ", acquire_state)
               scope.write("ACQUIRE:STATE ON")  # Equivalent to pressing Run
               acquire_state = scope.query("ACQUIRE:STATE?").strip()  #
               time.sleep(1)

            trigger_state="GO"
            #while trigger_state != "READY" and trigger_state != "ARMED" and trigger_state != "TRIGGER" :

            waiting_time.config(text="0 s")
            while trigger_state != "ARMED" and trigger_state != "TRIGGER" :
                trigger_state=scope.query("TRIG:STATE?").strip() 
                delta_time = time.time() - start_time 
                if verbose>3:
                   print(" delta_time ", delta_time,"time out ", scope.timeout, " trigger_state ", trigger_state)
                waiting_time.config(text=f"{int(delta_time)} s")
                if delta_time > scope.timeout:
                    raise TimeoutError("Failed to capture triggered waveform in time.")
                acquire_state = scope.query("ACQUIRE:STATE?").strip()  #
                if ( acquire_state == "0" and trigger_state != "ARMED" ): scope.write("ACQUIRE:STATE ON")  # Equivalent to pressing Run
                time.sleep(0.1)
                if not acquire_data: break

            if not acquire_data: break
            # Acquire waveform data
            print("Success trigger found " );
            horiz_scale = float(scope.query("HOR:MAIN:SCALE?"))    # seconds/div
            horiz_position = float(scope.query("HOR:MAIN:POS?"))   # position in seconds

         # Calculate time and voltage values
            x_origin = float(scope.query('WFMPRE:XZERO?'))
            x_incr = float(scope.query('WFMPRE:XINCR?'))
            y_offset = float(scope.query('WFMPRE:YOFF?'))
            y_offset = float(scope.query('WFMPRE:YOFF?'))  # Voltage offset
            y_mult = float(scope.query('WFMPRE:YMULT?'))
            y_zero = float(scope.query('WFMPRE:YZERO?'))   # Reference voltage

            display_time_range = horiz_scale * 10
            start_time = horiz_position - display_time_range / 2
            stop_time = horiz_position + display_time_range / 2
            start_time = - display_time_range / 2
            stop_time  = + display_time_range / 2
            start_point = int((start_time - x_origin) / x_incr)
            stop_point = int((stop_time - x_origin) / x_incr)

            scope.write(f"DATA:START {start_point}")
            scope.write(f"DATA:STOP {stop_point}")
            
            scope.query("*OPC?")  # Confirm readiness
            scope.write("DATA:SOURCE CH1")
            raw_data_ch1 = scope.query("CURVE?")  # Retrieve ASCII data as a string
            raw_data_array_ch1 = np.array([float(val) for val in raw_data_ch1.split(',')])

            if channel_2_on:
               scope.write("DATA:SOURCE CH2")
               raw_data_ch2 = scope.query("CURVE?")  # Retrieve ASCII data as a string
               raw_data_array_ch2 = np.array([float(val) for val in raw_data_ch2.split(',')])
            if verbose>4:
               print("Curves retrieved " );

    # Decode waveform data
  
   

            if verbose>4:
                print("get times and volts")
            time_vals_ch1 = start_time + np.arange(len(raw_data_array_ch1)) * x_incr
            voltage_vals_ch1 = (raw_data_array_ch1 - y_offset) * y_mult + y_zero

            if channel_2_on:
               time_vals_ch2 = start_time + np.arange(len(raw_data_array_ch2)) * x_incr
               voltage_vals_ch2 = (raw_data_array_ch2 - y_offset) * y_mult + y_zero


            #if np.array_equal(time_vals_ch1, time_vals_ch2):
            #   print("time_vals_ch1 and time_vals_ch2 are the same")
            #else:
            #   print("time_vals_ch1 and time_vals_ch2 are different")
            #   print("time_vals_ch1 and time_vals_ch2 are different")
            
            # Update canvas plot
            #update_canvas()

            if verbose>3:
                print("end:before setting state on")
            scope.write("ACQUIRE:STATE ON")  # Equivalent to pressing Run

            # Save data to CSV
            if verbose>1:
                print("before writting log")
            csv_filename = generate_file_name(data_directory)
            #csv_filename = "triggered_waveform_data.csv"
            with open(csv_filename, "w", newline="") as csv_file:
               writer = csv.writer(csv_file)
               writer.writerow(["TIME", "CH1"])

               if channel_2_on:
                  writer.writerows(zip(time_vals_ch1, voltage_vals_ch1, voltage_vals_ch2))    # Write data rows
               else:
                  writer.writerows(zip(time_vals_ch1, voltage_vals_ch1))    # Write data rows

#
            #if verbose>2: print(f"Waveform data saved to {csv_filename}")
            print(f"Waveform data saved to {csv_filename}")
            log_info(csv_filename)

            time.sleep(0.1)

        except Exception as e:
            print(f"An error occurred during waveform acquisition: {e}")

# Function to update the canvas with the latest waveform
def read_csv(file_path):
        """Reads the oscilloscope CSV file and extracts time and channel data."""
        time = []
        ch1 = []
        ch2 = []
        try:
            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                data_started = False
                for row in reader:
                    if row and row[0] == "TIME":
                        data_started = True
                        continue
                    if data_started and row:
                        try:
                            time.append(float(row[0]))
                            ch1.append(float(row[1]))
                            if channel_2_on:
                               ch2.append(float(row[2]))
                        except ValueError:
                            print(f"Skipping invalid data row: {row}")
        except Exception:
            print(f"Error: File not found at {file_path}")
            return np.array([]), np.array([]), np.array([])

        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return np.array([]), np.array([]), np.array([])

        return np.array(time), np.array(ch1), np.array(ch2)
#=================================================================================================
#
#=================================================================================================
def update_canvas(csv_file):

    time, ch1, ch2 = read_csv(csv_file)

    if len(ch1)>0:
        ax.clear()  # Clear the previous plot
        ax.plot(time, ch1, color="blue")
        if channel_2_on:
           ax.plot(time, ch2, color="black")
        basename = os.path.basename(csv_file)
        ax.set_title(f"Waveform {basename}")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.grid()
        canvas.draw()  # Redraw the canvas with the updated plot

def get_last_log_entry(log_file_name):
    """Retrieve the last entry from the log file."""
    if not os.path.exists(log_file_name):
        print(f"Log file {log_file_name} does not exist.")
        return None  # Return None if file doesn't exist

    try:
        with open(log_file_name, "r", newline="") as log_file:
            reader = csv.DictReader(log_file)
            rows = list(reader)  # Convert reader to a list to access the last row
            if rows:
                return rows[-1]  # Return the last row
            else:
                print("Log file is empty.")
                return None
    except Exception as e:
        print(f"Error reading log file: {e}")
        return None
#==================================================================================
#
#==================================================================================
def log_info(csv_file):
    Z = Z_entry.get().strip()
    X = X_entry.get().strip()
    Detector = Detector_entry.get().strip()
    Channel = Channel_entry.get().strip()
    Beam = Beam_entry.get().strip()
    Shield = Shield_entry.get().strip()
    Pulse = Pulse_entry.get().strip()
    Comment = Comment_entry.get().strip()
    Dose = Dose_entry.get().strip()
    
    HV = HV_entry.get().strip()

    headers = ["Detector", "Channel", "Beam", "Z", "HV", "X", "Shield", "Pulse", "Dose", "Comment", "FileMin", "FileMax"]
    
    file_exists = os.path.exists(log_file_name)
    last_entry = None

    # Read the last line of the file if it exists
    if file_exists:
        with open(log_file_name, "r", newline="") as log_file:
            reader = csv.reader(log_file)
            rows = list(reader)
            if len(rows) > 1:  # Ensure there is at least one entry beyond headers
                last_entry = rows[-1]  # Get the last logged entry

    new_entry = [Detector, Channel, Beam, HV, Z, X, Shield, Pulse, Dose, Comment]

    with open(log_file_name, "a", newline="") as log_file:
        writer = csv.writer(log_file)

        # If the file doesn't exist, write the headers first
        if not file_exists:
            writer.writerow(headers)

        # If last_entry exists and matches new_entry (excluding FileMin and FileMax)
        if last_entry and last_entry[:9] == new_entry:  
            last_entry[10] = csv_file  # Update FileMax in the last row
            rows[-1] = last_entry  # Replace last row with updated FileMax

            # Rewrite the file with the updated data
            with open(log_file_name, "w", newline="") as log_file:
                writer = csv.writer(log_file)
                writer.writerows(rows)  # Write the entire updated content

        else:
            # Write new row with FileMin and FileMax being the same
            writer.writerow(new_entry + [csv_file, csv_file])

    if verbose>1:
       print(f"Data successfully logged to {log_file_name}")

#====================================================================================================
def update_dose_button_action():
        dose_value = Dose_entry.get().strip()
        if dose_value:  # Ensure Dose value is not empty
            update_dose_in_log(log_file_name, dose_value)
        else:
            print("Dose value is empty. Please enter a value.")
#====================================================================================================
def update_dose_in_log0(log_file_name, dose_value):
    """
    Update the Dose column in the log file with the given dose_value for rows 
    that are empty in the Dose column, after the last row with a value in the Dose column.
    """
    if not os.path.exists(log_file_name):
        print(f"Log file {log_file_name} does not exist.")
        return

    try:
        # Read the log file and find rows to update
        updated_rows = []
        last_dose_row_index = -1

        with open(log_file_name, "r", newline="") as log_file:
            reader = csv.DictReader(log_file)
            rows = list(reader)  # Convert reader to a list to access indices
            fieldnames = reader.fieldnames  # Get headers
            
            # Determine the index of the last row with a value in the Dose column
            last_dose_row_index=-1
            for i, row in enumerate(rows):
                value=row.get("Dose").strip()
                if row.get("Dose").strip()!="":  # Check if the Dose column is not empty
                    last_dose_row_index = i

            # Update rows after the last row with Dose information
            for i, row in enumerate(rows):
                z_value = Z_entry.get().strip()
                pulse_value = Pulse_entry.get().strip()
                if i > last_dose_row_index:  # Consider only rows after the last Dose row
                    if row.get("Dose").strip()=="" and row.get("Z") == z_value and row.get("Pulse")== pulse_value:  # If Dose column is empty
                        row["Dose"] = dose_value
                updated_rows.append(row)

        # Write the updated rows back to the log file
        with open(log_file_name, "w", newline="") as log_file:
            writer = csv.DictWriter(log_file, fieldnames=fieldnames)
            writer.writeheader()  # Write headers
            writer.writerows(updated_rows)  # Write updated rows

        print(f"Dose column updated successfully with value: {dose_value}")
    except Exception as e:
        print(f"Error updating Dose column: {e}")
#====================================================================================================
def update_dose_in_log(log_file_name, dose_value):
    """Update the Dose field if the last row matches all other columns, or add a new row."""
    Z = Z_entry.get().strip()
    X = X_entry.get().strip()
    Detector = Detector_entry.get().strip()
    Channel = Channel_entry.get().strip()
    Beam = Beam_entry.get().strip()
    Shield = Shield_entry.get().strip()
    Pulse = Pulse_entry.get().strip()
    Comment = Comment_entry.get().strip()
   
    HV = HV_entry.get().strip()	

    headers = ["Detector", "Channel", "Beam", "Z", "HV", "X", "Shield", "Pulse", "Dose", "Comment", "FileMin", "FileMax"]
    
    file_exists = os.path.exists(log_file_name)
    last_entry = None

    # Read the last line of the file if it exists
    if not file_exists:
        print(f"{log_file_name} does not exist ")
        return

    new_entry = [Detector, Channel, Beam, Z, HV, X, Shield, Pulse, dose_value, Comment]
    with open(log_file_name, "a", newline="") as log_file:
        writer = csv.writer(log_file)

        # If the file doesn't exist, write the headers first
        if file_exists:
           with open(log_file_name, "r", newline="") as log_file:
              reader = csv.reader(log_file)
              rows = list(reader)
              if len(rows) > 1:  # Ensure there is at least one entry beyond headers
                  last_entry = rows[-1]  # Get the last logged entry
        else:
             print(f"{log_file_name} does not exist ")
             return

        # If last_entry exists and matches new_entry (excluding Dose and FileMin/FileMax)
        print("last_entry ", last_entry)
        print("new_entry ", new_entry)
        if last_entry and last_entry[:7] + last_entry[8:9] == new_entry[:7] + new_entry[8:9]:  
            last_entry[7] = dose_value  # Update Dose in the last row
            rows[-1] = last_entry  # Replace last row with updated Dose

            # Rewrite the file with updated content
            with open(log_file_name, "w", newline="") as log_file:
                writer = csv.writer(log_file)
                writer.writerows(rows)  # Write the entire updated content
            print(f"Dose successfully logged in {log_file_name}")
        else:
            print("Update Dose: No matching row found")
            # Write new row with the new Dose value

# Start acquisition loop
def start_acquisition():
    global acquire_data, look_for_new_file_seconds
    acquire_data = True
    Dose_entry.delete(0, "end")  # Clears the content of the Dose Entry field
    threading.Thread(target=acquire_waveform, daemon=True).start()
    threading.Thread(target=show_plots, daemon=True).start()
    stop_daq.config(state="normal")
    start_daq.config(state="disabled")
    status_label.config(text="Running")
    look_for_new_file_seconds=1

# Stop acquisition loop
def stop_acquisition():
    global acquire_data, look_for_new_file_seconds
    acquire_data = False
    stop_daq.config(state="disabled")
    start_daq.config(state="normal")
    status_label.config(text="Idle")
    look_for_new_file_seconds=100000

# Main GUI setup
def create_gui():
    global canvas, figure, ax
    global data_directory ;
    global log_file_name
    global Detector_entry, Channel_entry, Beam_entry, Z_entry, HV_entry, X_entry, Shield_entry, Pulse_entry, Dose_entry, Comment_entry
    global start_daq, stop_daq, status_label, waiting_time


    # Get today's date in YYYY-MM-DD format
    today = datetime.today().strftime('%Y-%m-%d')

    # Define directory and file paths based on today's date
    data_directory = f"/home/lgad/data/{today}"
    log_file_name = f"/home/lgad/data/lgad-{today}-log.csv"

    # Create the directory if it doesn't exist
    os.makedirs(data_directory, exist_ok=True)

    print(f"Data directory: {data_directory}")
    print(f"Log file: {log_file_name}")

    root = Tk()
    root.title("Oscilloscope Control Panel")
    root.geometry("1000x900")  # Set the window size explicitly (w

    last_entry = get_last_log_entry(log_file_name)

    # Create main frame
    frame = Frame(root)
    frame.pack()

 # Input fields for global variables
    input_frame = Frame(root)
    input_frame.pack(pady=10)

    Label(input_frame, text="Detector:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    Detector_entry = Entry(input_frame)
    Detector_entry.grid(row=0, column=1, padx=5, pady=5)

    Label(input_frame, text="Channel:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
    Channel_entry = Entry(input_frame)
    Channel_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    Label(input_frame, text="Beam:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
    Beam_entry = Entry(input_frame)
    Beam_entry.grid(row=0, column=5, padx=5, pady=5, sticky="w")

    Label(input_frame, text="Z:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    Z_entry = Entry(input_frame)
    Z_entry.grid(row=1, column=1, padx=5, pady=5)

    Label(input_frame, text="HV:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
    HV_entry = Entry(input_frame)
    HV_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")

    Label(input_frame, text="X:").grid(row=1, column=4, padx=5, pady=5, sticky="e")
    X_entry = Entry(input_frame)
    X_entry.grid(row=1, column=5, padx=5, pady=5, sticky="w")

    Label(input_frame, text="Shield:").grid(row=1, column=6, padx=5, pady=5, sticky="e")
    Shield_entry = Entry(input_frame)
    Shield_entry.grid(row=1, column=7, padx=5, pady=5)

    Label(input_frame, text="Pulse:").grid(row=2, column=0, padx=5, pady=5)
    Pulse_entry = Entry(input_frame)
    Pulse_entry.grid(row=2, column=1, padx=5, pady=5)

    Label(input_frame, text="Comment:").grid(row=2, column=2, padx=5, pady=5)
    Comment_entry = Entry(input_frame, width=30)
    Comment_entry.grid(row=2, column=3, padx=5, pady=5)

    Label(input_frame, text="Dose:").grid(row=3, column=0, padx=5, pady=5)
    Dose_entry = Entry(input_frame)
    Dose_entry.grid(row=3, column=1, padx=5, pady=5)

    update_button = Button(input_frame, text="Update Dose", command=update_dose_button_action, bg="blue", fg="white")
    update_button.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky="w")


    # Prepopulate the Entry fields with values from the last log entry
    if last_entry:
        Detector_entry.insert(0, last_entry.get("Detector", ""))
        Channel_entry.insert(0, last_entry.get("Channel", ""))
        Beam_entry.insert(0, last_entry.get("Beam", ""))
        Z_entry.insert(0, last_entry.get("Z", ""))
        X_entry.insert(0, last_entry.get("X", ""))
        HV_entry.insert(0, last_entry.get("HV", ""))
        Shield_entry.insert(0, last_entry.get("Shield", ""))
        Pulse_entry.insert(0, last_entry.get("Pulse", ""))
        Comment_entry.insert(0, last_entry.get("Comment", ""))
        Dose_entry.insert(0, last_entry.get("Dose", ""))

    # Control buttons
    start_daq = Button(frame, text="Start Acquisition", command=start_acquisition, bg="green", fg="white")
    start_daq.pack(side="left", padx=10, pady=10)
    stop_daq = Button(frame, text="Stop Acquisition", command=stop_acquisition, bg="red", fg="white")
    stop_daq.pack(side="left", padx=10, pady=10)
    stop_daq.config(state="disabled")
    status_label = Label(frame, text="Idle", font=("Arial", 12))
    status_label.pack(side="left", pady=10)

    waiting_label = Label(frame, text="Time:", font=("Arial", 12))
    waiting_label.pack(side="left", pady=10, padx=40)

    waiting_time = Label(frame, text="0 s", font=("Arial", 12))
    waiting_time.pack(side="left", pady=10, padx=3)

    # Matplotlib figure and canvas
    figure = plt.Figure(figsize=(8, 4), dpi=100)
    ax = figure.add_subplot(111)
    ax.set_title("Latest Waveform")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage (V)")
    ax.set_xlim(-10E-6, 10E-6)
    ax.grid()

    canvas = FigureCanvasTkAgg(figure, root)
    canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    # Handle window close event
    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()
#================================================================================================
#
#================================================================================================
def show_plots():
    global look_for_new_file_seconds
    look_for_new_file_seconds=1
    """Continuously monitor a directory for new files and update the canvas."""
    latest_file = None
    if verbose>2: print("We are in show_plots")

    while True:
        files = [os.path.join(data_directory, f) for f in os.listdir(data_directory) if os.path.isfile(os.path.join(data_directory, f))]
        if files:
            new_file = max(files, key=os.path.getmtime)  # Get the most recently modified file
            if verbose>5:
               print("New file to be displayed ", new_file)
            if new_file != latest_file:  # If a new file is detected
                latest_file = new_file
                update_canvas(latest_file)  # Call update_canvas with the new file
        time.sleep(look_for_new_file_seconds)  # Wait before checking again
def on_close():
    global acquire_data
    acquire_data = False  # Stop acquisition loop
    scope.close()  # Close oscilloscope connection
    rm.close()  # Close resource manager
    print("Program closed successfully.")
    exit()  # Exit the program

# GUI and scope initialization
try:
    # Oscilloscope initialization
    scope.write("DATA:SOURCE CH1")
    scope.write("DATA:ENC ASCII")  # Binary encoding
    scope.write("TRIG:A:SOURCE CH1")  # Trigger source
    scope.write("TRIG:EDGE:SLOPE NEG")  # Negative slope
    #scope.write("TRIG:LEVEL 0.05")  # Trigger level
    scope.write("ACQ:STOPA SEQ")  # Single acquisition mode

    print("Oscilloscope initialized.")
    create_gui()

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Ensure resources are closed on any unexpected exception
    scope.close()
    rm.close()

