import cv2
import time
import paho.mqtt.subscribe as subscribe
import datetime
from pylsl import StreamInfo, StreamOutlet

# Initialize video capture
cap = cv2.VideoCapture(0)
assert cap.isOpened(), "Error reading video file"

# Set video capture properties
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
cap.set(cv2.CAP_PROP_FPS, 60.0)

# Get video properties
w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))
print(w, h, fps)

# Get current date and time for filename
now = datetime.datetime.now()
date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
filename = fr"C:\Users\Admin\Desktop\DawgOs\videos\{date_time}.mp4"

# Initialize video writer
video_writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

# Initialize LSL stream
info = StreamInfo('FrameNumberStream', 'Markers', 1, 0, 'int32', 'myuidw43536')
outlet = StreamOutlet(info)

# Subscribe to MQTT topic
# msg = subscribe.simple("video", hostname="127.0.0.1")
# print(f"Message received: {msg.payload}")

# Start video capture loop
start_time = time.time()
counter = 0

while cap.isOpened():
    counter += 1
    success, im0 = cap.read()
    if not success:
        print("Video frame is empty or video processing has been successfully completed.")
        break

    print(counter)
    cv2.imshow('Frame', im0)
    video_writer.write(im0)

    # Send frame number to LSL stream
    outlet.push_sample([counter])

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
video_writer.release()
cv2.destroyAllWindows()

end_time = time.time()
elapsed_time = end_time - start_time
print(f'Time elapsed: {elapsed_time} seconds')
