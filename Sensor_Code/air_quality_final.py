# air quality library
import time
import sys
import aqi
import urllib2
import serial, struct, sys, time, json

# postgres database
import datetime
import psycopg2

DEBUG = 0
CMD_MODE = 2
CMD_QUERY_DATA = 4
CMD_SLEEP = 6
CMD_WORKING_PERIOD = 8
MODE_QUERY = 1

ser = serial.Serial()
ser.port = "/dev/ttyUSB0"
ser.baudrate = 9600

ser.open()
ser.flushInput()

byte, data = 0, ""

def dump(d, prefix=''):
    print(prefix + ' '.join(x.encode('hex') for x in d))

def construct_command(cmd, data=[]):
    assert len(data) <= 12
    data += [0,]*(12-len(data))
    checksum = (sum(data)+cmd-2)%256
    ret = "\xaa\xb4" + chr(cmd)
    ret += ''.join(chr(x) for x in data)
    ret += "\xff\xff" + chr(checksum) + "\xab"

    if DEBUG:
        dump(ret, '> ')
    return ret

def process_data(d):
    r = struct.unpack('<HHxxBB', d[2:])
    pm25 = r[0]/10.0
    pm10 = r[1]/10.0
    checksum = sum(ord(v) for v in d[2:8])%256
    return [pm25, pm10]

def read_response():
    byte = 0
    while byte != "\xaa":
        byte = ser.read(size=1)

    d = ser.read(size=9)

    if DEBUG:
        dump(d, '< ')
    return byte + d

def cmd_set_mode(mode=MODE_QUERY):
    ser.write(construct_command(CMD_MODE, [0x1, mode]))
    read_response()

def cmd_query_data():
    ser.write(construct_command(CMD_QUERY_DATA))
    d = read_response()
    values = []
    if d[1] == "\xc0":
        values = process_data(d)
    return values

def cmd_set_sleep(sleep=1):
    mode = 0 if sleep else 1
    ser.write(construct_command(CMD_SLEEP, [0x1, mode]))
    read_response()

def cmd_set_working_period(period):
    ser.write(construct_command(CMD_WORKING_PERIOD, [0x1, period]))
    read_response()
    
    
def connect(day,value,location):
    """ Connect to the PostgreSQL database server """
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

        #tested
        cursor.execute('''INSERT INTO sensor_pm(Time, Value, Location, Status)
                VALUES (%s, %s, %s, %s);''',
               (day, value, location, True))
        print("submit value to db")

        # close the communication with the PostgreSQL
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.commit()
            conn.close()
            print('Database connection closed.')

def loop():
    try:
        while True:
            cmd_set_sleep(0)
            cmd_set_mode(1);
            pm25 = None
            pm10 = None    
            
            
            values = cmd_query_data()
            if values is not None and len(values)==2:
                if values[0] is not None and values[1] is not None:
                    if not values[0] == " 0.0" and not values[1] == " 0.0":
                        pm25 = values[0]
                        pm10 = values[1]
                        myaqi = aqi.to_aqi([
                            (aqi.POLLUTANT_PM25, pm25),
                            (aqi.POLLUTANT_PM10, pm10)
                        ])
                        print("Total AQI: ", str(myaqi), ", PM2.5: ", pm25, ", PM10: ", pm10)
                
            connect(datetime.datetime.now(), myaqi,"home")
            print("Going to sleep for 60secs...")
            time.sleep(60)
            
    except KeyboardInterrupt:
          pass
    
    
if __name__ == "__main__":
    loop()
    
    
