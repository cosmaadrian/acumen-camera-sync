from pytapo import Tapo
from vidgear.gears import CamGear
from vidgear.gears import NetGear
import cv2
import urllib

user = "acumen-eye-1" # user you set in Advanced Settings -> Camera Account
password = "aczsc7p+tapo-1" # password you set in Advanced Settings -> Camera Account
host = "192.168.1.102"

tapo = Tapo(host, user, password)

print(tapo.getBasicInfo())

print(tapo.getStreamURL())
# stream = CamGear(source = 'https://' + tapo.getStreamURL(), stream_mode = True).start()
streamURL = f"rtsp://{user}:{password}@{host}:554/stream1"
stream = cv2.VideoCapture(streamURL)

while True:
    ret, frame = stream.read()
    print(frame)

    if frame is None:
        break

    cv2.imshow("Output", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

cv2.destroyAllWindows()
stream.stop()
