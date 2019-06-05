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
from scipy.spatial import distance
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

def send_image_face(frame,face_url):
    eye = 0
    pitch = 0
    
    headers = {'Content-Type': 'application/octet-stream'}

    imencoded = cv2.imencode('.jpg',frame)[1]
    try:
        response = requests.post(face_url, headers = headers, data = imencoded.tostring())
        jsonres = response.json()
        eye, pitch = process_face_json(jsonres)

        return eye, pitch

    except Exception as e:
        print(e)
        return 100, 100


def process_face_json(jsonres):
    leftOutX = jsonres[0]['faceLandmarks']['eyeLeftOuter']['x']
    leftOutY = jsonres[0]['faceLandmarks']['eyeLeftOuter']['y']
    leftInX = jsonres[0]['faceLandmarks']['eyeLeftInner']['x']
    leftInY = jsonres[0]['faceLandmarks']['eyeLeftInner']['y']
    leftTopX = jsonres[0]['faceLandmarks']['eyeLeftTop']['x']
    leftTopY = jsonres[0]['faceLandmarks']['eyeLeftTop']['y']
    leftBotX = jsonres[0]['faceLandmarks']['eyeLeftBottom']['x']
    leftBotY = jsonres[0]['faceLandmarks']['eyeLeftBottom']['y']

    leftOut = (leftOutX, leftOutY)
    leftIn = (leftInX, leftInY)
    leftTop = (leftTopX, leftTopY)
    leftBot = (leftBotX, leftBotY)

    eye1 = distance.euclidean(leftTop,leftBot) / distance.euclidean(leftOut,leftIn)

    rightOutX = jsonres[0]['faceLandmarks']['eyeRightOuter']['x']
    rightOutY = jsonres[0]['faceLandmarks']['eyeRightOuter']['y']
    rightInX = jsonres[0]['faceLandmarks']['eyeRightInner']['x']
    rightInY = jsonres[0]['faceLandmarks']['eyeRightInner']['y']
    rightTopX = jsonres[0]['faceLandmarks']['eyeRightTop']['x']
    rightTopY = jsonres[0]['faceLandmarks']['eyeRightTop']['y']
    rightBotX = jsonres[0]['faceLandmarks']['eyeRightBottom']['x']
    rightBotY = jsonres[0]['faceLandmarks']['eyeRightBottom']['y']

    rightOut = (rightOutX, rightOutY)
    rightIn = (rightInX, rightInY)
    rightTop = (rightTopX, rightTopY)
    rightBot = (rightBotX, rightBotY)

    eye2 = distance.euclidean(rightTop,rightBot) / distance.euclidean(rightOut,rightIn)

    eye = (eye1 + eye2) / 2
    eye = round(eye,3)

    pitch = jsonres[0]['faceAttributes']['headPose']['pitch']

    return eye,pitch

def capture_image_send_message(eye_thres, pitch_thres, video_src, face_url, hubManager):

    webcam = VideoStream(video_src).start()
    print("Taking camera from input %s" % video_src)
    print("Setting Eye threshold as %s" % eye_thres)
    print("Setting Pitch threshold as %s" % pitch_thres)
    time.sleep(2)
    print("Camera initialized...")

    eye_thres = float(eye_thres)
    pitch_thres = float(pitch_thres)

    while(True):
        image = webcam.read()
        d1 = datetime.datetime.now()
        try:
            eye, pitch = send_image_face(image,face_url)
            msg = ""
            d2 = datetime.datetime.now()
            d = d2 - d1
            duration = int(round(d.seconds * 1000 + d.microseconds / 1000, 0))
            if eye < eye_thres and pitch < pitch_thres:
                print("[%s ms] WARNING! Drowsiness detected! Eye: %f, Pitch: %f" % (duration,eye,pitch))
                result = {}
                result['timestamp'] = str(datetime.datetime.now().time())
                result['eye'] = eye
                result['pitch'] = pitch
                result['status'] = 'warning'
                msg = json.dumps(result)

            else:
                print("[%s ms] Eye: %f, Pitch: %f" % ((duration,eye,pitch)))
                result = {}
                result['timestamp'] = str(datetime.datetime.now().time())
                result['eye'] = eye
                result['pitch'] = pitch
                result['status'] = 'safe'
                msg = json.dumps(result)

        except Exception as e:
            result = "safe"
    
        message = IoTHubMessage(str(msg))
        hubManager.forward_event_to_output("outputs",message,0)
        time.sleep(0.25)

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
        FACE_URL = os.getenv('faceapi',"")
        EYE_THRES = os.getenv('eyethres',"")
        PITCH_THRES = os.getenv('pitchthres',"")

        hub_manager = HubManager(protocol)
    
        print ( "Starting the IoT Hub Python Apps using protocol %s..." % hub_manager.client_protocol )

        while True:
            capture_image_send_message(EYE_THRES, PITCH_THRES, VIDEO_SOURCE,FACE_URL, hub_manager)
            time.sleep(1)

    except IoTHubError as iothub_error:
        print ( "Unexpected error %s from IoTHub" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubModuleClient sample stopped" )

if __name__ == '__main__':
    main(PROTOCOL)