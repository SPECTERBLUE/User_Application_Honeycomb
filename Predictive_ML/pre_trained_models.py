
import pandas as pd 
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

##########################################################################################################
# file contains function to train specfic models for various assets.
##########################################################################################################


# label data specic to 60kW 3-phase Slipring Induction Motor 
'''
Based on your motor specifications (400V, 50Hz, 120A stator, 317V/121A rotor), we will simulate the following sensors:

* **Stator Current & Voltage:** To detect electrical imbalances or overload.
* **Rotor Current & Voltage:** Crucial for slipring motors to detect brush wear, slip ring degradation, or rotor winding issues.
* **Vibration (mm/s):** To detect mechanical faults like bearing wear or misalignment.
* **Temperature (°C):** Winding and bearing temperatures.

We will tag five distinct states:

* `0`: Healthy Operation
* `1`: Overload (High currents, rising temperatures)
* `2`: Rotor/Slipring Fault (Fluctuating rotor voltage/current, increased slip)
* `3`: Stator Fault (Unbalanced or spiking stator current)
* `4`: Mechanical Fault (High vibration and bearing temperature)
'''

# Mechanical > Stator > Rotor > Overload > Healthy

def label_motor_faults(window_df, thresholds):
    """
    Multi-class labeling for 60kW Slipring Induction Motor
    Works on WINDOWED (pivoted) dataframe rows.
    """

    labeled_rows = []

    for _, row in window_df.iterrows():

        label = 0  # Healthy default

        stator_i = row.get("Stator_Current_avg")
        stator_v = row.get("Stator_Voltage_avg")

        rotor_i = row.get("Rotor_Current_avg")
        rotor_v = row.get("Rotor_Voltage_avg")

        vib = row.get("Vibration_avg")
        temp = row.get("Temperature_avg")

        # -------------------------------
        # 1️ MECHANICAL FAULT (highest priority)
        # -------------------------------
        if (
            vib is not None and temp is not None and
            vib >= thresholds["vibration"]["mechanical"] and
            temp >= thresholds["temperature"]["mechanical"]
        ):
            label = 4

        # -------------------------------
        # 2️ STATOR FAULT
        # Current spike / electrical imbalance
        # -------------------------------
        elif (
            stator_i is not None and
            stator_i >= thresholds["stator_current"]["fault_spike"]
        ):
            label = 3

        # -------------------------------
        # 3️ ROTOR / SLIPRING FAULT
        # Rotor current abnormal OR voltage drop
        # -------------------------------
        elif (
            rotor_i is not None and
            rotor_i >= thresholds["rotor_current"]["fault"]
        ):
            label = 2

        # -------------------------------
        # 4️ OVERLOAD
        # High stator current + rising temperature
        # -------------------------------
        elif (
            stator_i is not None and temp is not None and
            stator_i >= thresholds["stator_current"]["overload"] and
            temp >= thresholds["temperature"]["overload"]
        ):
            label = 1

        labeled_rows.append({
            **row.to_dict(),
            "label": label
        })

    return pd.DataFrame(labeled_rows)

