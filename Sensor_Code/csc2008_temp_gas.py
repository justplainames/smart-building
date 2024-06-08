import Adafruit_DHT
import time
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import board
from datetime import datetime
import psycopg2
import pytz

def main():
    #Temperature & Humidity sensor
    DHT_SENSOR = Adafruit_DHT.DHT11
    DHT_PIN = 4 #GPIO4

    #Gas sensor
    # Create the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the ADC object using the I2C bus
    #ads = ADS.ADS1115(i2c)
    # you can specify an I2C adress instead of the default 0x48
    ads = ADS.ADS1115(i2c, address=0x49)

    # Create single-ended input on channel 0
    chan = AnalogIn(ads, ADS.P0)

    # Create differential input between channel 0 and 1
    # chan = AnalogIn(ads, ADS.P0, ADS.P1)

    #print("{:>5}\t{:>5}".format("raw", "v"))

    co2now = []
    cow2raw = 0
    co2ppm = 0
    zzz = 0
    i = 0

    while True:
        humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)

        if i < 10:
            #Calculating PPM, requires 10 sample value
            co2now.append(chan.value)
            i += 1
        else:
            #co2now has 10 data 
            for x in range(10):
                zzz += co2now[x]
            
            #Gas sensor logic
            cow2raw = zzz/10
            co2ppm = cow2raw - 55
            print("Air Quality: " + str(co2ppm) + " PPM")
            
            #Temp & Humidity logic
            if humidity is not None and temperature is not None:
                print("Temp={0:0.1f}C Humidity={1:0.1f}%".format(temperature, humidity))

                #Upload to db
                connect(temperature, humidity, co2ppm)
            else:
                print("Sensor failure. Check wiring.");


            #Reset value
            i = 0
            zzz = 0
            cow2raw = 0
            co2ppm = 0
            co2now.clear() #Clear for the next 10 set
        
        #print(str(chan.value))
        time.sleep(0.5)


def connect(temp, humidity, gas):
    #tz_SG = pytz.timezone('Asia/Singapore') 

    #Connect to the PostgreSQL database server
    conn = None
    try:
        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(
            host="ec2-23-20-73-25.compute-1.amazonaws.com",
            database="dbvbq9l542v62g",
            user="snjckpbyhvvhza",
            password="6d1291e6ec645cc6ba76e60474ecb69c601220a0fa9fa352501c3989821cee8b"
        )

        # create a cursor
        cursor = conn.cursor()
        print(str(datetime.now()))
        #insert temperature values
        cursor.execute('''INSERT INTO sensor_temp(Time, Value, Location, Status)
                 VALUES (%s, %s, %s, %s);''',
                (datetime.now(), temp, 'toilet', True))

        #insert humidity values
        cursor.execute('''INSERT INTO sensor_humidity(Time, Value, Location, Status)
                 VALUES (%s, %s, %s, %s);''',
                (datetime.now(), humidity, 'bathroom', True))

        #insert gas values
        cursor.execute('''INSERT INTO sensor_gas(Time, Value, Location, Status)
                 VALUES (%s, %s, %s, %s);''',
                (datetime.now(), gas, 'lavatory', True))

        # close the communication with the PostgreSQL
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.commit()

            conn.close()
            print('Database connection closed.')

if __name__ == "__main__":
    main()