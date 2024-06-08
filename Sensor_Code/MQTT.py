from sense_hat import SenseHat
from time import sleep
import paho.mqtt.client as mqtt

#MQTT message
mqtt_msg = ""           #default value, can be changed from MQTT

#light_Switch
light_Switch = False    #default value, can be changed from MQTT

#Aircon
ac_Switch = False       #default value, can be changed from MQTT
ac_Temp = 26            #default value, can be changed from MQTT


# The callback for when the client receives a CONNACK response from the server
def on_connect(client, userdata, flags, rc):
    print("connection ok")
    client.subscribe("database/loc1")      #Topic subscribed, change if necessary 

# The callback for when a PUBLISH message is received from the server
def on_message(client, userdata, msg):
    global mqtt_msg

    global light_Switch

    global ac_Switch
    global ac_Temp

    message_code = str(msg.payload)
    
    print("Message received: " + message_code)
    mqtt_msg = message_code
    
    # Only allow double-digit code to conduct instructions
    if len(message_code) == 2:
        first_char = message_code[0]

        # Light Instructions
        if first_char == "L":
            second_char = message_code[1]

            # L0,L1 code
            if second_char == "0":
                light_Switch = False  # Switch off light
                print("Turning off light...")
            elif second_char == "1":
                light_Switch = True  # Switch on light
                print("Turning on light...")
            else:
                print("Invalid message code")

        # Aircon instructions
        elif first_char == "A":
            second_char = message_code[1]
            
            # A0, A1 code
            if second_char == "0":
                ac_Switch = False   # Switch off aircon
                print("Turning off aircon...")
            elif second_char == "1":
                ac_Switch = True    # Switch on aircon
                print("Turning on aircon...")
            else:
                #AU, AD
                if ac_Switch == False:
                    print("Turn on the aircon first la")
                else:
                    if second_char == "U":
                        ac_Temp += 1
                    elif second_char == "D":
                        ac_Temp -= 1

        else:
            print("Invalid message code")
    else:
        print("Invalid message code")

    
    # Reset variable for the next publish
    first_char = None 
    second_char = None



#Main logic
def main():
    #####################################     MQTT    #####################################
    broker = "broker.mqttdashboard.com"  #Broker IP, change if necessary
    client = mqtt.Client("simulator") #create an instance with client id simulator, must be unique
    client.on_connect = on_connect
    client.on_message = on_message

    client.loop_start()  # Create a loop in another thread so that simulation while(1) loop is intact
    client.connect(broker, 1883, 60)
    ##################################### END OF MQTT #####################################

    #Emulator for Sensehat
    sense = SenseHat()
    mode = 1    # 1 = light, 2 = aircon

    while(1):
        #joystick click and mode traversal
        for event in sense.stick.get_events():
            if event.action == "pressed":
                if event.direction == "middle":
                    mode += 1
                    if mode == 3:
                        mode = 1

        if mode == 1:
            #Light activity
            if light_Switch == True:
                sense.clear((255, 255, 255))
            else:
                sense.clear()
        elif mode == 2:
            #Aircon activity
            if ac_Switch == True:
                temp = str(ac_Temp) + "C"
                sense.show_message(temp, text_colour=(0, 0, 255))
            else:
                sense.show_message("OFF", text_colour=(255, 0, 0))
        elif mode == 3:
            #MQTT message
            sense.show_message(mqtt_msg, text_colour=(255, 255, 255))
                
        else:
            sense.clear()
    

    
if __name__ == "__main__":
    main()