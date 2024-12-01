import RPi.GPIO as GPIO
import time
import sys
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
TRIG = 21
ECHO = 20


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

# if __name__ == "__main__":
#     distance = get_distance()
#     print(distance)


if __name__ == "__main__":
    distance = get_distance()
    if distance is not None:
        print("Distance:", distance, "cm")
    else:
        print("No sensor found or error occurred.")
        sys.exit(1)
