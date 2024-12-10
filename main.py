import streamlit as st
import sqlite3
import time
from datetime import datetime
import pandas as pd  # For working with data
import board
import busio
import os
from stts22h import STTS22H
import RPi.GPIO as GPIO
import sys
import math
import numpy as np
import plotly.graph_objects as go
import qwiic_relay
from streamlit_autorefresh import st_autorefresh
from streamlit_echarts import st_echarts



GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
TRIG = 21
ECHO = 20

st.set_page_config(page_title="Water Tank", layout="wide")
#page_count = st_autorefresh(interval=20000, limit=1000, key="pagerefreshcounter")
st.cache_data(persist=True, ttl=None)

# Initialize temp_sensor
i2c = busio.I2C(board.SCL, board.SDA)
temp_sensor = STTS22H(i2c)

# Initialize Relay
plug_relay = qwiic_relay.QwiicRelay(0x18)

# Initialize SQLite database
DB_FILE = "database.db"

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    st.write("New Database Created")

def record_temperature():
    """Record the current temperature and timestamp in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temperature = temp_sensor.temperature
    cursor.execute("INSERT INTO temperature_records (timestamp, temperature) VALUES (?, ?)", (timestamp, temperature))
    conn.commit()
    conn.close()

def update_setting(key, value):

    conn = sqlite3.connect(DB_FILE)
    conn.set_trace_callback(log_query)
    cursor = conn.cursor()

    # Upsert with ON CONFLICT clause
    cursor.execute("""
        INSERT INTO settings (key, value, timestamp)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            timestamp = CURRENT_TIMESTAMP
    """, (key, value))

    try:
        # commit the sql
        conn.commit()

        # update state
        st.session_state[key] = value
    except Exception as e:
        print("Failed to commit:", e)

    conn.close()

def fetch_records(table_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    #query = f"SELECT * FROM {table_name} ORDER BY id DESC"

    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]

        # Fetch data
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp ASC")
        records = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        records = []
    finally:
        conn.close()

    return records, columns

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

def tank_gallons_full():
    return round((math.pi * (float(st.session_state['tank_diameter']) / 2) ** 2 * float(st.session_state['tank_height']) / 3785.41),1)

def gallons_remaining(centimeters):
    #remaining_cm = st.session_state['tank_diameter'] - centimeters
    remaining_cm = st.session_state['height_of_water']

    gallons_remaining = (math.pi * (float(st.session_state['tank_diameter']) / 2) ** 2 * remaining_cm / 3785.41)
    return round(gallons_remaining)

def percentage_remaining(centimeters):
    return 100 - round((centimeters / float(st.session_state['tank_height']) * 100))

def celsius_fahrenheit(c):
    c = float(c)
    if c == 0:
        return None
    return c * 9 / 5 + 32

def toggle_relay(arg):
    if arg == 'on':
        plug_relay.set_relay_on()
    elif arg == 'off':
        plug_relay.set_relay_off()
    else:
        plug_relay.set_relay_off()

def log_query(query):
    print("SQL executed:", query)

def init():

    if plug_relay.begin() == False:
        print("The Qwiic Relay isn't connected to the system. Please check your connection", \
            file=sys.stderr)
        return

    if 'tank_height' not in st.session_state:
        # # Initialize database
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT * from settings;")
            result = cur.fetchone()
            conn.close()
        except sqlite3.Error:
            print("SQLite database does not exist")
            # TODO only need to do this once.
            initialize_db()
            update_setting("tank_diameter", 240)
            update_setting("tank_height", 260)
            update_setting("relay_temp_on", 2)
            update_setting("relay_temp_off", 10)


        data, columns = fetch_records("settings")
        db_settings = {key: value for key, value, _ in data}

        st.session_state = {
            "tank_height": db_settings.get('tank_height'),
            "tank_diameter": db_settings.get('tank_diameter'),
            "relay_temp_on": db_settings.get('relay_temp_on'),
            "relay_temp_off": db_settings.get('relay_temp_off'),
        }

    st.session_state['current_temp'] = temp_sensor.temperature
    st.session_state['distance'] = get_distance()
    st.session_state['height_of_water'] = float(st.session_state['tank_height']) - st.session_state['distance']

init()



# -----------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------- UI -----------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


st.title("VALLEY WATER TANK MONITORING SYSTEM")


c1,c2,c3,c4,c5  = st.columns(5)
with c1:
    with st.container(border=True):

        if st.toggle("Relay"):
            toggle_relay('on')
        else:
            toggle_relay('off')
        if st.button("Reset Session State"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        if st.button("Record Temp"):
            record_temperature()
            st.success("Temperature added successfully!")

with c2:
    with st.container(border=True):
        st.write(f"Distance: {st.session_state['distance']} cm ")
        st.write(f"Percent Remaining: {percentage_remaining(st.session_state['distance'])}%")
with c3:
    with st.container(border=True):
        st.write(f"tank_gallons_full: {tank_gallons_full()} ")
        st.write(f"Current Temperature: {st.session_state['current_temp']} °C")
with c4:
    "State Settings"

    df = pd.DataFrame(
        list(st.session_state.items()),  # Convert dictionary to a list of tuples
        columns=["Setting", "Value"]  # Define column names
    )
    df["Value"] = df["Value"].astype(str)
    st.write(df)


with c5:

    "Settings"
    recorded_data, columns = fetch_records('settings')
    df = pd.DataFrame(recorded_data, columns=columns)
    df["value"] = df["value"].astype(str)
    st.write(df)


col1, col2, col3 = st.columns(3)
with col1:
    # Static ish bargraph for gallons in tank
    st.subheader("Gallons Remaining")
    value = gallons_remaining(st.session_state['height_of_water'])

    gallons_fig = go.Figure()
    gallons_fig.add_bar(x=["Value"], y=[value], name="Gallons", marker_color="blue", text= value)
    gallons_fig.update_yaxes(range=[0, tank_gallons_full()])  # Set y-axis bounds (lower: 0, upper: 100)
    gallons_fig.update_layout(
        title="",
        yaxis_title="Gallons",
        xaxis_title=""

    )
    st.plotly_chart(gallons_fig)



with col2:
    st.subheader("Interior Temperature")

    recorded_data, columns = fetch_records('temperature_records')
    timestamps = [row[1] for row in recorded_data]  # Extract timestamps
    temperatures = [row[2] for row in recorded_data]  # Extract temperatures
    relay_on_temp = [st.session_state['relay_temp_on']] * len(recorded_data)
    relay_off_temp = [st.session_state['relay_temp_off']] * len(recorded_data)

    # https://echarts.streamlit.app/
    # https://github.com/andfanilo/streamlit-echarts
    options = {
        "ID": "C",
        "xAxis": {
            "type": "category",
            "data": timestamps,
        },
        "yAxis": {"type": "value"},
        "series": [
            {"data": temperatures, "type": "line", "areaStyle":{}},
            {"data": relay_on_temp, "type": "line"},
            {"data": relay_off_temp, "type": "line"}

        ],
    }
    st_echarts(options=options)




with col3:
    st.subheader("Interior Temperature F")

    recorded_data, columns = fetch_records('temperature_records')
    timestamps = [row[1] for row in recorded_data]  # Extract timestamps
    temperatures = [celsius_fahrenheit(row[2]) for row in recorded_data]  # Extract temperatures
    relay_on_temp = [celsius_fahrenheit(st.session_state['relay_temp_on'])] * len(recorded_data)
    relay_off_temp = [celsius_fahrenheit(st.session_state['relay_temp_off'])] * len(recorded_data)

    # https://echarts.streamlit.app/
    # https://github.com/andfanilo/streamlit-echarts
    options = {
        "ID": "F",
        "xAxis": {
            "type": "category",
            "data": timestamps,
        },
        "yAxis": {"type": "value"},
        "series": [
            {"data": temperatures, "type": "line", "areaStyle":{}},
            {"data": relay_on_temp, "type": "line"},
            {"data": relay_off_temp, "type": "line"}

        ],
    }
    st_echarts(options=options)


st.subheader("Ext Temperature")

chart_data = pd.DataFrame(
    {
        "col1": np.random.randn(20),
        "col2": np.random.randn(20),
        "col3": np.random.choice(["A", "B", "C"], 20),
    }
)

st.area_chart(chart_data, x="col1", y="col2", color="col3")








