import streamlit as st
import sqlite3
import time
from datetime import datetime
import pandas as pd  # For working with data
import board
import busio
from stts22h import STTS22H
import RPi.GPIO as GPIO
import sys
import math
import numpy as np
from streamlit_lightweight_charts import renderLightweightCharts
import streamlit_lightweight_charts.dataSamples as dataSamples
import plotly.graph_objects as go


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
TRIG = 21
ECHO = 20

st.set_page_config(page_title="Water Tank", layout="wide")




def initialize_db():
    """Initialize the SQLite database and create a table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temperature_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def record_temperature():
    """Record the current temperature and timestamp in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temperature = temp_sensor.temperature
    cursor.execute("INSERT INTO temperature_records (timestamp, temperature) VALUES (?, ?)", (timestamp, temperature))
    conn.commit()
    conn.close()


def fetch_records():
    """Fetch all temperature records from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, temperature FROM temperature_records ORDER BY id DESC")
    records = cursor.fetchall()
    conn.close()
    return records

def get_distance():
  # print("Distance Measurment in Progress")
  try:
    pulse_end= 0
    pulse_start= 0
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)

    GPIO.output(TRIG, False)
    # print("Waiting for Sensor")
    time.sleep(.5)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    timeout = time.time() + 1
    while GPIO.input(ECHO) == 0 and time.time() < timeout:
        pulse_start = time.time()

    timeout = time.time() + 1
    while GPIO.input(ECHO) == 1 and time.time() < timeout:
        pulse_end = time.time()

    if pulse_end == 0 or pulse_start == 0:
        return None

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 17150
    distance = round(distance, 2)

    #print("Distance: ", distance, " cm")
    GPIO.cleanup()
    return distance
  except Exception as e:
    print("An error occurred:", e)
    GPIO.cleanup()
    sys.exit(1)


def set_readings():
    global current_temp
    global distance
    global tank_settings

    current_temp    = temp_sensor.temperature
    distance        = get_distance()
    tank_settings   = {"tank_height": 260, "tank_diameter": 240}



def gallons_remaining(centimeters):
    remaining_cm = tank_settings["tank_height"] - centimeters

    gallons_remaining = (math.pi * (tank_settings["tank_diameter"] / 2) ** 2 * remaining_cm / 3785.41)
    return round(gallons_remaining)

def gallons_used(centimeters):
    return round(tank_gallons - self.gallons_remaining(centimeters))


def percentage_remaining(centimeters):
    return 100 - round((centimeters / tank_settings["tank_height"]) * 100)

def celsius_fahrenheit(c):
    c = float(c)
    if c == 0:
        return None
    return c * 9 / 5 + 32


# Initialize temp_sensor
i2c = busio.I2C(board.SCL, board.SDA)
temp_sensor = STTS22H(i2c)

# Initialize SQLite database
DB_FILE = "temperature_data.db"

# Initialize database
initialize_db()

# set global variable values
set_readings()
recorded_data = fetch_records()


# -----------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------- UI -----------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


st.title("VALLEY WATER TANK MONITORING SYSTEM")
st.subheader(f"Current Temperature: {current_temp} °C")
st.subheader(f"Distance: {distance} cm ")


st.subheader(f"Gallons Remaining: {gallons_remaining(0)}")
st.subheader(f"Perfect Remaining: {percentage_remaining(0)}%")

col1, col2, col3 = st.columns(3)
with col1:
    # Static ish bargraph for gallons in tank

    value = distance
    gallons_fig = go.Figure()
    gallons_fig.add_bar(x=["Value"], y=[value], name="Gallons", marker_color="blue")

    gallons_fig.update_yaxes(range=[0, 100])  # Set y-axis bounds (lower: 0, upper: 100)
    gallons_fig.update_layout(
        title="Gallons in Tank",
        yaxis_title="Gallons",
        xaxis_title="",
    )
    st.plotly_chart(gallons_fig)


with col2:
    df = pd.DataFrame(recorded_data, columns=["Timestamp", "Temperature"])  # Requires pandas
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    # Plot line graph
    st.subheader("Interior Temperature")
    if not df.empty:
        st.area_chart(df.set_index("Timestamp")["Temperature"])
    else:
        st.write("No data available to display.")

    if st.button("Record Temp"):
        record_temperature()
        st.success("Temperature added successfully!")

with col3:
    st.subheader("Ext Temperature")
    series = [
        {
            "type": 'Area',
            "data": dataSamples.priceVolumeSeriesArea,
            "options": {
                "topColor": 'rgba(38,198,218, 0.56)',
                "bottomColor": 'rgba(204,9,238, 0.56)',
                "lineColor": 'rgba(38,198,218, 1)',
                "lineWidth": 2,
            }
        }
    ]
    options = {
        "height": 400,
        "rightPriceScale": {
            "scaleMargins": {
                "top": 0.1,
                "bottom": 0.1,
            },
            "mode": 2, # PriceScaleMode: 0-Normal, 1-Logarithmic, 2-Percentage, 3-IndexedTo100
            "borderColor": 'rgba(197, 203, 206, 0.4)',
        },
        "timeScale": {
            "borderColor": 'rgba(197, 203, 206, 0.4)',
        },
        "layout": {
            "background": {
                "type": 'solid',
                "color": '#100841'
            },
            "textColor": '#ffffff',
        },
        "grid": {
            "vertLines": {
                "color": 'rgba(197, 203, 206, 0.4)',
                "style": 1, # LineStyle: 0-Solid, 1-Dotted, 2-Dashed, 3-LargeDashed
            },
            "horzLines": {
                "color": 'rgba(197, 203, 206, 0.4)',
                "style": 1, # LineStyle: 0-Solid, 1-Dotted, 2-Dashed, 3-LargeDashed
            }
        }
    }


    renderLightweightCharts(
            [
                {
                    "series": series,
                    "chart": options
                }
            ], 'Exterior Temp'
        )






st.write('---')



col1, col2 = st.columns(2)

with col1:
    # Streamlit UI
    st.title("Distance")
    st.subheader(f"{distance} CM")


    chart_data = pd.DataFrame(
        {
            "col1": np.random.randn(20),
            "col2": np.random.randn(20),
            "col3": np.random.choice(["A", "B", "C"], 20),
        }
    )

    st.area_chart(chart_data, x="col1", y="col2", color="col3")
    #st.area_chart(df, x="Timestamp", y="Temperature")



with col2:
    priceVolumeSeries = [
        {
            "type": 'Area',
            "data": dataSamples.priceVolumeSeriesArea,
            "options": {
                "topColor": 'rgba(38,198,218, 0.56)',
                "bottomColor": 'rgba(204,9,238, 0.56)',
                "lineColor": 'rgba(38,198,218, 1)',
                "lineWidth": 2,
            }
        }
    ]
    overlaidAreaSeriesOptions = {
        "height": 400,
        "rightPriceScale": {
            "scaleMargins": {
                "top": 0.1,
                "bottom": 0.1,
            },
            "mode": 2, # PriceScaleMode: 0-Normal, 1-Logarithmic, 2-Percentage, 3-IndexedTo100
            "borderColor": 'rgba(197, 203, 206, 0.4)',
        },
        "timeScale": {
            "borderColor": 'rgba(197, 203, 206, 0.4)',
        },
        "layout": {
            "background": {
                "type": 'solid',
                "color": '#100841'
            },
            "textColor": '#ffffff',
        },
        "grid": {
            "vertLines": {
                "color": 'rgba(197, 203, 206, 0.4)',
                "style": 1, # LineStyle: 0-Solid, 1-Dotted, 2-Dashed, 3-LargeDashed
            },
            "horzLines": {
                "color": 'rgba(197, 203, 206, 0.4)',
                "style": 1, # LineStyle: 0-Solid, 1-Dotted, 2-Dashed, 3-LargeDashed
            }
        }
    }


    renderLightweightCharts(
            [
                {
                    "series": priceVolumeSeries,
                    "chart": overlaidAreaSeriesOptions
                }
            ], 'priceAndVolume'
        )









# Background loop to record data every hour
# if st.button("Start Hourly Recording"):
#     st.write("Recording temperature every hour. Keep this app running!")
#     while True:
#         record_temperature()
#         st.write(f"Recorded: {temp_sensor.temperature:.2f} °C at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
#         time.sleep(3600)  # Wait for 1 hour
