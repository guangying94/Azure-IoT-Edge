# Driver Drowsiness Detection on IoT Edge

This is a sample demostrating how to deploy [Azure Cognitive Services Containers](https://docs.microsoft.com/en-us/azure/cognitive-services/cognitive-services-container-support) in [Azure IoT Edge](https://docs.microsoft.com/en-us/azure/iot-edge/).

This sample is targeted for Linux based machine due to the needs of accessing hardware, in this case, camera. This sample is tested on Raspberry Pi 3, and Ubuntu 18.04. Linux container on Windows X64 will not run due to the restriction of accessing hardware.

## How to use this sample

The following image shows the high level view of connection from Microsoft Azure to IoT Edge devices:

![Overview]()

### Camera
A python script is written to grab image from camera, and send it to Face API to detect face landmarks and head pose. This will determine if the driver is sleepy. 2 conditions are considered, head is facing downwards, and eye aspect ratio. More info can be found here: [Real-Time Eye Blink Detection using Facial Landmarks](http://vision.fe.uni-lj.si/cvww2016/proceedings/papers/05.pdf).

Depending on the setup and naming, you will need to setup the environment variables in your implementation.

This module has 4 inputs:

1. videosource

    This is to access video source from your device. A quick way to check the video source is **v4l-utils** package.

    ```console
    sudo apt-get install v4l-utils
    v4l2-ctl --list-devices
    ```

    In my case, I use **/dev/video0**.

1. faceapi

    This is the endpoint where the code will send the image to for inferencing. Refer to section below for more details.

    In my case, my input is **http://faceapi:5000/face/v1.0/detect?returnFaceId=false&returnFaceLandmarks=true&returnFaceAttributes=headPose&recognitionModel=recognition_02&returnRecognitionModel=false**.

1. eyethres

    You may want to configure the eye aspect ratio threshold based on your camera placement, actual feeds etc. I use **0.3**.

1. pitchthres

    Similarly, you can configure the head pose pitch ratio threshold. You may want to adjust this based on camera placement. In my deployment, I use **-8**.

So the complete environment variables are as below:

```json
{
    "videosource": "/dev/video0",
    "faceapi": "http://faceapi:5000/face/v1.0/detect?returnFaceId=false&returnFaceLandmarks=true&returnFaceAttributes=headPose&recognitionModel=recognition_02&returnRecognitionModel=false",
    "eyethres": 0.3,
    "pitchthres": -8
}
```

### Face API
This is leveraging on Container support for Azure Cognitive Services. Some modules are still in preview, but you can request the access from [here](https://docs.microsoft.com/en-us/azure/cognitive-services/cognitive-services-container-support).

In Face API, there are several options to configure depending on the use case. In this sample, we detect face landmark and head pose. Hence query string is as below:

```json
{
    "returnFaceId": false,
    "returnFaceLandmarks": true,
    "returnFaceAttributes": "headPose",
    "recognitionModel": "recognition_02",
    "returnRecognitionModel": false
}
```

With the settings above, the url is __http://faceapi:5000/face/v1.0/detect?returnFaceId=false&returnFaceLandmarks=true&returnFaceAttributes=headPose&recognitionModel=recognition_02&returnRecognitionModel=false__.

More details on detailed breakdown of the above options can be found [here](https://docs.microsoft.com/en-us/azure/cognitive-services/Face/concepts/face-detection).

When deploying modules to edge devices, you will need to set the following environment variables:

1. Eula

    As this is still in preview, developers are required to accept the eula.
1. Billing

    This is the billing endpoint, which can be found in the Azure portal. In my case, it's __https://southeastasia.api.cognitive.microsoft.com/face/v1.0__
1. ApiKey

    This is the API Key obtained from Azure portal.

Your environmental variables will be as below:

```json
{
    "Eula": "accept",
    "Billing": "https://southeastasia.api.cognitive.microsoft.com/face/v1.0",
    "ApiKey": "<API KEY>"
}
````

### Demo

![Demo]()

The console will output 4 items:

1. Time taken for face api results in milliseconds
1. Eye aspect ratio
1. Head pitch value
1. Status (either Warning or safe)

Sample output for camera module logs:
```console
[63 ms] WARNING! Drowsiness detected! Eye: 0.267000, Pitch: -12.900000
```

The telemetrey is streamed to IoT Hub as well.

```json
{
    "status": "warning",
    "pitch": -12.9,
    "timestamp": "08:59:46.732355",
    "eye": 0.267
}