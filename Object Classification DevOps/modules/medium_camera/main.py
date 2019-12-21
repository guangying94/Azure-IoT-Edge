# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import os
import time
import sys
import iothub_client
from iothub_client import IoTHubModuleClient, IoTHubClientError, IoTHubTransportProvider
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError
import cv2
from cv2 import cv2
import requests
import json
import imutils
from imutils.video import VideoStream
import datetime

# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubModuleClient.send_event_async.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000
SEND_CALLBACKS = 0

# Choose HTTP, AMQP or MQTT as transport protocol.  Currently only MQTT is supported.
PROTOCOL = IoTHubTransportProvider.MQTT

# Callback received when the message that we're forwarding is processed.
def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    #print ( "Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    #print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    #print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )

def send_image(frame,classifier_url):
    
    headers = {'Content-Type': 'application/octet-stream'}

    imencoded = cv2.imencode('.jpg',frame)[1]
    try:
        response = requests.post(classifier_url, headers = headers, data = imencoded.tostring())
        prob, item = process_json(response)

        if prob > 0.8:
            return prob, item
        else:
            return 0, 'none'

    except Exception as e:
        return e

def process_json(output):
    max_probability = 0
    item = 'none'
    jsonres = output.json()
    for predict in jsonres['predictions']:
        if predict['probability'] > max_probability:
            max_probability = predict['probability']
            item = predict['tagName']
    
    return max_probability, item

def capture_image_send_message(video_src, classifier_url, hubManager):

    webcam = VideoStream(video_src).start()
    print("Taking camera from input %s" % video_src)
    time.sleep(2)
    print("Camera initialized...")

    while(True):
        image = webcam.read()
        d1 = datetime.datetime.now()
        try:
            prob, item = send_image(image,classifier_url)
            d2 = datetime.datetime.now()
            d = d2 - d1
            duration = int(round(d.seconds * 1000 + d.microseconds / 1000, 0))
            print("[%s ms] I see %s with %f confidence." % (duration, item, prob))

        except Exception as e:
            print('error')
    
        message = IoTHubMessage(str('test'))
        hubManager.forward_event_to_output("outputs",message,0)
        time.sleep(0.01)

class HubManager(object):

    def __init__(
            self,
            protocol=IoTHubTransportProvider.MQTT):
        self.client_protocol = protocol
        self.client = IoTHubModuleClient()
        self.client.create_from_environment(protocol)

        # set the time until a message times out
        self.client.set_option("messageTimeout", MESSAGE_TIMEOUT)

    # Forwards the message received onto the next stage in the process.
    def forward_event_to_output(self, outputQueueName, event, send_context):
        self.client.send_event_async(
            outputQueueName, event, send_confirmation_callback, send_context)

def main(protocol):
    try:
        print ( "\nPython %s\n" % sys.version )
        VIDEO_SOURCE = os.getenv('videosource',"")
        FACE_URL = os.getenv('classifierapi',"")

        hub_manager = HubManager(protocol)
    
        print ( "Starting the IoT Hub Python Apps using protocol %s..." % hub_manager.client_protocol )

        while True:
            capture_image_send_message(VIDEO_SOURCE,FACE_URL, hub_manager)
            time.sleep(1)

    except IoTHubError as iothub_error:
        print ( "Unexpected error %s from IoTHub" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubModuleClient sample stopped" )

if __name__ == '__main__':
    main(PROTOCOL)