#from asyncio.windows_events import NULL
from django.shortcuts import render
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from flask_session import Session
from datetime import date
import paho.mqtt.client as mqtt
from flask_mqtt import Mqtt

today = date.today()
d1 = today.strftime("%d")

app = Flask(__name__)
app.secret_key = "super secret key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


def on_publish(client, userdata, mid):
    print(f"Sent message!")


def get_db_connection():
    conn = psycopg2.connect(
        host="nope",
        database="nope",
        user="nope",
        password="nope"
    )

    return conn


print('Connecting to the PostgreSQL database...')


@app.route('/', methods=["POST", "GET"])
def login_page():  # Login Page
    # Check if there are user click on the log in button
    if request.method == 'POST':
        # Get the username and password
        username = request.form.get('username')
        password = request.form.get('password')
        # Connect to database and query all users from it
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM public.users")
        users = cur.fetchall()

        # For each username in the database
        for i in users:
            # Compare the username and password between user inputs and the one from database
            if (username == i[1] and password == i[2]):
                # Session data will be save and redirect to other pages
                session["loggedIn"] = True
                session["username"] = i[1]
                session["role"] = i[3]
                return redirect(url_for("homepage"))
        # Else will flash the notification
        flash("Wrong Username or Password", category='error')

        cur.close()
    return render_template('login_page.html')


@app.route('/logout')
def logout():
    # Remove session data, hence user will be logged out
    session.pop('loggedIn', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for("login_page"))


@app.route('/homepage', methods=["POST", "GET"])  # Homepage page
def homepage():
    if 'loggedIn' in session:
        # Sets up the MQTT connection
        client = mqtt.Client()
        client.on_publish = on_publish
        client.connect('broker.mqttdashboard.com', 1883)
        client.loop_start()
        if request.method == 'POST':
            if request.form.get('on') == 'On':
                client.publish("database/loc1", "A1")
            elif request.form.get('off') == 'Off':
                client.publish("database/loc1", "A0")
            elif request.form.get('lightOn') == 'Light On':
                client.publish("database/loc1", "L1")
            elif request.form.get('lightOff') == 'Light Off':
                client.publish("database/loc1", "L0")
            elif request.form.get('increaseTemp') == 'Increase Temp':
                client.publish("database/loc1", "AU")
            elif request.form.get('decreaseTemp') == 'Decrease Temp':
                client.publish("database/loc1", "AD")
        try:

            # Connects to the DB
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # Takes PM2.5 data set, group them per day and find the average
            query = '''
                SELECT date_trunc('day', Time), AVG (value)::NUMERIC(10,2)  
                FROM sensor_pm WHERE Time > now() - interval '1 week' 
                GROUP BY 1 
                ORDER BY 1;
                '''
            cur.execute(query)
            sensor_pm = cur.fetchall()
            barData = []
            colors = []
            for row in sensor_pm:
                if row[1] >= 150.0:
                    colors.append("rgba(237, 41, 56, 0.5)")
                elif row[1] >= 100.0 and row[1] <= 149.0:
                    colors.append("rgba(255, 170, 28, 0.5)")
                elif row[1] >= 50 and row[1] <= 99:
                    colors.append("rgba(255, 170, 28, 0.5)")
                else:
                    colors.append("rgba(103, 201, 151, 0.5)")
                barData.append({
                    'Label': row[0].strftime("%d/%m/%Y"),
                    'Values': row[1],
                })

            # Takes sensor data set, group them per day and find the average
            query = '''
                SELECT date_trunc('day', Time), AVG (value)::NUMERIC(10,2)  
                FROM sensor_humidity 
                WHERE Time > now() - interval '1 week' 
                GROUP BY 1 
                ORDER BY 1;
                '''
            cur.execute(query)
            humidity_bar = cur.fetchall()
            humidity_bar_data = []
            print(humidity_bar)

            # Takes humidity data set, group them per day and find the average
            for row in humidity_bar:
                humidity_bar_data.append({
                    'date': row[0].strftime("%d/%m/%Y, %H:%m"),
                    'Values': row[1]
                })

            # Takes latest data collected from the sensor
            queryA = "SELECT * from sensor_pm ORDER BY Time DESC;"
            cur.execute(queryA)
            recent_pm = cur.fetchone()
            queryB = "SELECT * from sensor_humidity ORDER BY Time DESC;"
            cur.execute(queryB)
            recent_humidity = cur.fetchone()
            queryC = "SELECT * from sensor_gas ORDER BY Time DESC;"
            cur.execute(queryC)
            recent_gas = cur.fetchone()
            queryD = "SELECT * from sensor_temp ORDER BY Time DESC;"
            cur.execute(queryD)
            recent_temperature = cur.fetchone()

            # Takes Temperature data set, group them per day and find the average
            query = '''
                SELECT date_trunc('day', Time), AVG (sensor_temp.value)::NUMERIC(10,2)  
                FROM sensor_temp
                WHERE Time > now() - interval '1 week' 
                GROUP BY 1 
                ORDER BY 1;
                '''
            cur.execute(query)
            temp_bar = cur.fetchall()
            temp_bar_data = []
            for row in temp_bar:
                temp_bar_data.append({
                    'date': row[0].strftime("%d/%m/%Y, %H:%m"),
                    'Values': row[1]
                })

            return render_template('homepage.html', barData=barData, barHomepageColors=colors,  humidityBarData=humidity_bar_data,
                                   recent_humidity=recent_humidity[2], recent_pm=recent_pm[2], recent_gas=recent_gas[2],
                                   recent_temperature=recent_temperature[2], temperatureBarData=temp_bar_data)
        except Exception as e:
            print(e)
        finally:
            cur.close()

    flash("Please Logged In First", category='error')
    return redirect(url_for("login_page"))


@app.route('/temperature')  # Temperature page
def temperature_page():
    if 'loggedIn' in session:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Collect average daily data of the past 7 days
        query = '''
        SELECT DATE_TRUNC('hour' ,Time) , AVG(value) 
        FROM sensor_temp WHERE Time > now() - interval '1 week' 
        GROUP BY DATE_TRUNC('hour' , Time) 
        ORDER BY DATE_TRUNC('hour' , Time) ;
        '''
        cur.execute(query)
        temp_bar = cur.fetchall()
        temp_bar_data = []
        for row in temp_bar:
            temp_bar_data.append({
                'date': row[0].strftime("%d/%m/%Y, %H:%m"),
                'Values': row[1]
            })

        return render_template('temperature_page.html', tempDataBar=temp_bar_data, username=session['username'])

    flash("Please Logged In First", category='error')
    return redirect(url_for("login_page"))

# Displays every dataset collected in a table


@app.route("/temp_table", methods=["POST", "GET"])
def temp_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if request.method == 'POST':
            draw = request.form['draw']
            row = int(request.form['start'])
            rowperpage = int(request.form['length'])
            searchValue = request.form["search[value]"]

            cur.execute(
                "SELECT count(*) as allcount from sensor_temp")

            rsallcount = cur.fetchone()
            totalTempRecords = rsallcount[0]

            likeString = "{}%".format(searchValue)

            cur.execute(
                "SELECT count(*) as allcount from sensor_temp WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s", (likeString,))
            rsallcount = cur.fetchone()
            totalTempRecordwithFilter = rsallcount[0]

            if searchValue == '':
                cur.execute(
                    "SELECT * FROM sensor_temp LIMIT {limit} OFFSET {offset}".format(limit=rowperpage, offset=row))
                temp_sensor = cur.fetchall()
            elif searchValue != '' and rowperpage == -1:
                cur.execute("SELECT * FROM sensor_temp WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s",
                            (likeString,))
                temp_sensor = cur.fetchall()
            else:
                cur.execute("SELECT * FROM sensor_temp WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s LIMIT %s OFFSET %s;",
                            (likeString, rowperpage, row,))
                temp_sensor = cur.fetchall()

            temp_data = []

            for row in temp_sensor:
                temp_data.append({
                    'Id': row[0],
                    'Time': row[1],
                    'Value': row[2],
                    'Location': row[3],
                    'Status': row[4]
                })
            response = {
                'draw': draw,
                'data': temp_data,
                'iTotalRecords': totalTempRecords,
                'iTotalDisplayRecords': totalTempRecordwithFilter
            }
            return jsonify(response)
    except Exception as e:
        print(e)
    finally:
        cur.close()


@app.route("/retrieve_temp_chart", methods=["POST", "GET"])
def retrieve_temp_chart():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if request.method == 'POST':
            # checks user selected option ranging from daily, weekly, monthly, quarterly and yearly
            From = request.form['temp_chart_range']
            # Get the temperature data and find the 30 min average for display
            if(From == "Daily"):
                query = '''
                SELECT date_trunc('hour',Time) + date_part('minute',Time)::int/30* interval '30 min', AVG (value)::NUMERIC(10,2)
                FROM sensor_temp
                WHERE Time > now()- interval '1 day'
                GROUP BY 1
                ORDER BY 1;'''
                cur.execute(query)
                temp_sensor = cur.fetchall()
                temp_data = []

                for row in temp_sensor:
                    temp_data.append({
                        'Label': row[0].strftime("%d/%m/%Y, %H:%M"),
                        'Values': row[1]
                    })
                return render_template("temperature_page.html", data=temp_data)

            elif(From == "Weekly"):
                # Get the temperature data and find the 4 hour average of the past week for display
                query = '''
                SELECT date_trunc('day',Time) + date_part('hour',Time)::int/4* interval '4 hours', AVG (sensor_temp.value)::NUMERIC(10,2)
                FROM sensor_temp 
                WHERE Time > now()- interval '1 week'
                GROUP BY 1
                ORDER BY 1;'''
                cur.execute(query)
                temp_sensor = cur.fetchall()
                temp_data = []

                for row in temp_sensor:
                    temp_data.append({
                        'Label': row[0].strftime("%d/%m/%Y, %H:%M"),
                        'Values': row[1]
                    })
                return render_template("temperature_page.html", data=temp_data)

            elif(From == "Monthly"):
                # Get the temperature data and find the daily average of the past month for display
                query = '''
                    SELECT date_trunc('day', Time), AVG (sensor_temp.value)::NUMERIC(10,2) 
                    FROM sensor_temp 
                    WHERE Time > now()- interval '1 month'
                    GROUP BY 1
                    ORDER BY 1;'''
                cur.execute(query)
                temp_sensor = cur.fetchall()
                temp_data = []

                for row in temp_sensor:
                    temp_data.append({
                        'Label': row[0].strftime("%d/%m/%Y"),
                        'Values': row[1]
                    })
                return render_template("temperature_page.html", data=temp_data)

            elif(From == "Quarterly"):
                # Get the temperature data and find the 10-day average of the past 3 months for display
                query = '''
                    SELECT date_trunc('month', Time) + date_part('day',Time)::int/3* interval '10 days', AVG (sensor_temp.value)::NUMERIC(10, 2)
                    FROM sensor_temp 
                    WHERE Time > now()- interval '3 months'
                    GROUP BY 1
                    ORDER BY 1;'''
                cur.execute(query)
                temp_sensor = cur.fetchall()
                temp_data = []

                for row in temp_sensor:
                    temp_data.append({
                        'Label': row[0].strftime("%d/%m/%Y"),
                        'Values': row[1]
                    })
                return render_template("temperature_page.html", data=temp_data)

            # Get the temperature data and find the 4 hour average of the past week for display
            query = '''
                SELECT date_trunc('month', Time) + date_part('day',Time)::int/2* interval '15 days', AVG (sensor_temp.value)::NUMERIC(10, 2)
                FROM sensor_temp 
                WHERE Time > now() - interval '1 year
                GROUP BY 1
                ORDER BY 1;'''
            cur.execute(query)
            temp_sensor = cur.fetchall()
            temp_data = []
            for row in temp_sensor:
                temp_data.append({
                    'Label': row[0].strftime("%d/%m/%Y"),
                    'Values': row[1]
                })

            return render_template("temperature_page.html", data=temp_data)
    except Exception as e:
        print(e)
    finally:
        cur.close()

# Renders the humidty page and table


@app.route('/humidity')  # Humidity page
def humidity_page():
    if 'loggedIn' in session:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Get the daily average humidity of the past 7 days
        query = '''
        SELECT DATE_TRUNC('hour' ,Time) , AVG(value) 
        FROM sensor_humidity 
        WHERE Time > now() - interval '1 week'
        GROUP BY DATE_TRUNC('hour' , Time) 
        ORDER BY DATE_TRUNC('hour' , Time) ;
        '''
        cur.execute(query)
        humidity_bar = cur.fetchall()
        humidity_bar_data = []
        for row in humidity_bar:
            humidity_bar_data.append({
                'date': row[0].strftime("%d/%m/%Y, %H:%M"),
                'Values': row[1]
            })

        return render_template('humidity_page.html', humidityDataBar=humidity_bar_data)

    flash("Please Logged In First", category='error')
    return redirect(url_for("login_page"))

# Renders the table containing every humidity dataset


@app.route("/humidity_table", methods=["POST", "GET"])
def humidity_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if request.method == 'POST':
            draw = request.form['draw']
            row = int(request.form['start'])
            rowperpage = int(request.form['length'])
            searchValue = request.form["search[value]"]

            cur.execute(
                "SELECT count(*) as allcount from sensor_humidity")

            rsallcount = cur.fetchone()
            totalHumidityRecords = rsallcount[0]

            likeString = "{}%".format(searchValue)

            cur.execute(
                "SELECT count(*) as allcount from sensor_humidity WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s", (likeString,))
            rsallcount = cur.fetchone()
            totalHumidityRecordwithFilter = rsallcount[0]

            if searchValue == '':
                cur.execute(
                    "SELECT * FROM sensor_humidity LIMIT {limit} OFFSET {offset}".format(limit=rowperpage, offset=row))
                humidity_sensor = cur.fetchall()
            elif searchValue != '' and rowperpage == -1:
                cur.execute("SELECT * FROM sensor_humidity WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s",
                            (likeString,))
                humidity_sensor = cur.fetchall()
            else:
                cur.execute("SELECT * FROM sensor_humidity WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s LIMIT %s OFFSET %s;",
                            (likeString, rowperpage, row,))
                humidity_sensor = cur.fetchall()

            humidity_data = []

            for row in humidity_sensor:
                humidity_data.append({
                    'Id': row[0],
                    'Time': row[1],
                    'Value': row[2],
                    'Location': row[3],
                    'Status': row[4]
                })
            response = {
                'draw': draw,
                'data': humidity_data,
                'iTotalRecords': totalHumidityRecords,
                'iTotalDisplayRecords': totalHumidityRecordwithFilter
            }

            return jsonify(response)
    except Exception as e:
        print(e)
    finally:
        cur.close()

# Renders the humidty dataset for creating the line chart


@app.route("/retrieve_humidity_chart", methods=["POST", "GET"])
def retrieve_humidity_chart():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if request.method == 'POST':
            From = request.form['humidity_chart_range']
            query = ''
            # Get the humidity data and find the 30min average of the past 24 hours for display
            if(From == "Daily"):
                query = '''
                SELECT date_trunc('hour',Time) + date_part('minute',Time)::int/30* interval '30 min', AVG (sensor_humidity.value)::NUMERIC(10,2)
                FROM sensor_humidity 
                WHERE Time > now()- interval '1 day'
                GROUP BY 1
                ORDER BY 1;'''
                cur.execute(query)
                humidity_sensor = cur.fetchall()
                humidity_data = []

                for row in humidity_sensor:
                    humidity_data.append({
                        'Label': row[0].strftime("%d/%m/%Y, %H:%M"),
                        'Values': row[1]
                    })
                return render_template("humidity_page.html", data=humidity_data)

            # Get the humidity data and find the 4 hour average of the past week for display
            elif(From == "Weekly"):
                query = '''
                SELECT date_trunc('day',Time) + date_part('hour',Time)::int/4* interval '4 hours', AVG (sensor_humidity.value)::NUMERIC(10,2)
                FROM sensor_humidity 
                WHERE Time > now()- interval '1 year'
                GROUP BY 1
                ORDER BY 1;'''
                cur.execute(query)
                humidity_sensor = cur.fetchall()
                humidity_data = []

                for row in humidity_sensor:
                    humidity_data.append({
                        'Label': row[0].strftime("%d/%m/%Y, %H:%M"),
                        'Values': row[1]
                    })
                return render_template("humidity_page.html", data=humidity_data)

            # Get the humidity data and find the daily average of the past month for display
            elif(From == "Monthly"):
                query = '''
                    SELECT date_trunc('day', Time), AVG (sensor_humidity.value)::NUMERIC(10,2) 
                    FROM sensor_humidity 
                    WHERE Time > now()- interval '1 month'
                    GROUP BY 1
                    ORDER BY 1;'''
                cur.execute(query)
                humidity_sensor = cur.fetchall()
                humidity_data = []

                for row in humidity_sensor:
                    humidity_data.append({
                        'Label': row[0].strftime("%d/%m/%Y"),
                        'Values': row[1]
                    })
                return render_template("humidity_page.html", data=humidity_data)

            # Get the humidity data and find the 10 day average of the past 3 months for display
            elif(From == "Quarterly"):
                query = '''
                    SELECT date_trunc('month', Time) + date_part('day',Time)::int/3* interval '10 days', AVG (sensor_humidity.value)::NUMERIC(10, 2)
                    FROM sensor_humidity 
                    WHERE Time > now()- interval '3 months'
                    GROUP BY 1
                    ORDER BY 1;'''
                cur.execute(query)
                humidity_sensor = cur.fetchall()
                humidity_data = []

                for row in humidity_sensor:
                    humidity_data.append({
                        'Label': row[0].strftime("%d/%m/%Y"),
                        'Values': row[1]
                    })
                return render_template("humidity_page.html", data=humidity_data)

            # Get the humidity data and find the 15 day average of the past year for display
            query = '''
                SELECT date_trunc('month', Time) + date_part('day',Time)::int/2* interval '15 days', AVG (sensor_humidity.value)::NUMERIC(10, 2)
                FROM sensor_humidity
                WHERE Time > now() - interval '1 year
                GROUP BY 1
                ORDER BY 1;'''
            cur.execute(query)
            humidity_sensor = cur.fetchall()
            humidity_data = []

            for row in humidity_sensor:
                humidity_data.append({
                    'Label': row[0].strftime("%d/%m/%Y"),
                    'Values': row[1]
                })
            return render_template("humidity_page.html", data=humidity_data)
    except Exception as e:
        print(e)
    finally:
        cur.close()

# Renders the PM2.5 page


@app.route('/pm_gas')  # PM/Gas Page
def pm_gas_page():
    if 'loggedIn' in session:
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # Get the PM2.5 data and find the daily average of the past 1 week for display
            query = '''
            SELECT date_trunc('day', Time), AVG (value)::NUMERIC(10,2)  
            FROM sensor_pm 
            WHERE Time > now() - interval '1 week' 
            GROUP BY 1;
            '''
            cur.execute(query)
            sensor_pm = cur.fetchall()
            barData = []
            colors = []
            for row in sensor_pm:
                if row[1] >= 150.0:
                    colors.append("rgba(237, 41, 56, 0.5)")
                elif row[1] >= 100.0 and row[1] <= 149.0:
                    colors.append("rgba(255, 170, 28, 0.5)")
                elif row[1] >= 50 and row[1] <= 99:
                    colors.append("rgba(255, 170, 28, 0.5)")
                else:
                    colors.append("rgba(103, 201, 151, 0.5)")
                barData.append({
                    'Label': row[0].strftime("%d/%m/%Y"),
                    'Values': row[1],
                })
            return render_template('pm_gas_page.html', barData=barData, colors=colors)
        except Exception as e:
            print(e)
        finally:
            cur.close()

    flash("Please Logged In First", category='error')
    return redirect(url_for("login_page"))

# Renders the table container everydata set collected by the PM2.5 sensr


@app.route("/pm_gas_table", methods=["POST", "GET"])
def data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if request.method == 'POST':
            draw = request.form['draw']
            row = int(request.form['start'])
            rowperpage = int(request.form['length'])
            searchValue = request.form["search[value]"]

            cur.execute(
                "SELECT count(*) as allcount from sensor_pm")

            rsallcount = cur.fetchone()
            totalRecords = rsallcount[0]

            likeString = "{}%".format(searchValue)

            cur.execute(
                "SELECT count(*) as allcount from sensor_pm WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s", (likeString,))
            rsallcount = cur.fetchone()
            totalRecordwithFilter = rsallcount[0]

            if searchValue == '':
                cur.execute(
                    "SELECT * FROM sensor_pm LIMIT {limit} OFFSET {offset}".format(limit=rowperpage, offset=row))
                sensor_pm = cur.fetchall()
            elif searchValue != '' and rowperpage == -1:
                cur.execute("SELECT * FROM sensor_pm WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s",
                            (likeString,))
                sensor_pm = cur.fetchall()
            else:
                cur.execute("SELECT * FROM sensor_pm WHERE to_char(Time, 'YYYY-MM-DD') LIKE %s LIMIT %s OFFSET %s;",
                            (likeString, rowperpage, row,))
                sensor_pm = cur.fetchall()

            data = []

            for row in sensor_pm:
                data.append({
                    'Id': row[0],
                    'Time': row[1],
                    'Value': row[2],
                    'Location': row[3],
                    'Status': row[4]
                })
            response = {
                'draw': draw,
                'data': data,
                'iTotalRecords': totalRecords,
                'iTotalDisplayRecords': totalRecordwithFilter
            }
            return jsonify(response)
    except Exception as e:
        print(e)
    finally:
        cur.close()

# Renders the line chart for PM2.5 gas values


@app.route("/retrieve_chart", methods=["POST", "GET"])
def retrieve_chart():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if request.method == 'POST':
            From = request.form['pm_chart_range']
            query = ''
            # Get the PM2.5 data and find the 30min average of the past 24hrs for display
            if(From == "Daily"):
                query = '''
                SELECT date_trunc('hour',Time) + date_part('minute',Time)::int/30* interval '30 min', AVG (value)::NUMERIC(10,2)
                FROM sensor_pm 
                WHERE Time > now()- interval '1 day'
                GROUP BY 1
                ORDER BY 1;'''
                cur.execute(query)
                sensor_pm = cur.fetchall()
                data = []

                for row in sensor_pm:
                    data.append({
                        'Label': row[0].strftime("%d/%m/%Y, %H:%M"),
                        'Values': row[1],
                    })
                return render_template("pm_gas_page.html", data=data)
            # Get the PM2.5 data and find the 4 hour average of the past week for display
            elif(From == "Weekly"):
                query = '''
                SELECT date_trunc('day',Time) + date_part('hour',Time)::int/4* interval '4 hours', AVG (value)::NUMERIC(10,2)
                FROM sensor_pm 
                WHERE Time > now() - interval '1 week'
                GROUP BY 1
                ORDER BY 1; '''
                cur.execute(query)
                sensor_pm = cur.fetchall()
                data = []

                for row in sensor_pm:
                    data.append({
                        'Label': row[0].strftime("%d/%m/%Y, %H:%M"),
                        'Values': row[1],
                    })
                return render_template("pm_gas_page.html", data=data)
            # Get the PM2.5 data and find the daily average of the past month for display
            elif(From == "Monthly"):
                query = '''
                SELECT date_trunc('day', Time), AVG (value)::NUMERIC(10,2)  
                FROM sensor_pm 
                WHERE Time > now() - interval '1 month'
                GROUP BY 1
                ORDER BY 1; '''
                cur.execute(query)
                sensor_pm = cur.fetchall()
                data = []

                for row in sensor_pm:
                    data.append({
                        'Label': row[0].strftime("%d/%m/%Y"),
                        'Values': row[1],
                    })
                return render_template("pm_gas_page.html", data=data)
            # Get the PM2.5 data and find the 10 day average of the past 3months for display
            elif(From == "Quarterly"):
                query = '''
                SELECT date_trunc('month', Time) + date_part('day',Time)::int/3* interval '10 days', AVG (value)::NUMERIC(10, 2)
                FROM sensor_pm 
                WHERE Time > now() - interval '3 months'
                GROUP BY 1
                ORDER BY 1; '''
                cur.execute(query)
                sensor_pm = cur.fetchall()
                data = []

                for row in sensor_pm:
                    data.append({
                        'Label': row[0].strftime("%d/%m/%Y"),
                        'Values': row[1],
                    })
                return render_template("pm_gas_page.html", data=data)
            # Get the PM2.5 data and find the 15 day average of the past year for display
            query = '''
            SELECT date_trunc('month', Time) + date_part('day',Time)::int/2* interval '15 days', AVG (value)::NUMERIC(10, 2)
            FROM sensor_pm 
            WHERE Time > now() - interval '1 year'
            GROUP BY 1
            ORDER BY 1; '''
            cur.execute(query)
            sensor_pm = cur.fetchall()
            data = []

            for row in sensor_pm:
                data.append({
                    'Label': row[0].strftime("%/d/%m/%Y"),
                    'Values': row[1],
                })
            return render_template("pm_gas_page.html", data=data)
    except Exception as e:
        print(e)
    finally:
        cur.close()


if __name__ == '__main__':
    app.run(debug=True)
