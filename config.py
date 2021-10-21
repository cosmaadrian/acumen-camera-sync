import os
import psutil

partitions = psutil.disk_partitions()
for partition in partitions:

    # record on ssd if available
    if 'ADATA SE800' in partition.mountpoint:
        RECORD_PATH = os.path.join(partition.mountpoint, 'recordings')
        break
else:
    RECORD_PATH = 'recordings'

print(f'::::: RECORD_PATH = {RECORD_PATH}')

RECORD_QUALITY = 'HQ'

HQ_WIDTH = 1920
HQ_HEIGHT = 1080

LQ_WIDTH = 640
LQ_HEIGHT = 360

CAMERAS = [
    {
        'name': 'eye-1',
        'user': 'acumen-eye-1',
        'password': "aczsc7p+tapo-1",
        'host': "192.168.42.201",
        'symbol': '.'
    },
    {
        'name': 'eye-2',
        'user': 'acumen-eye-2',
        'password': "aczsc7p+tapo-2",
        'host': "192.168.42.202",
        'symbol': ','
    },
    {
        'name': 'eye-3',
        'user': 'acumen-eye-3',
        'password': "aczsc7p+tapo-3",
        'host': "192.168.42.203",
        'symbol': '\''
    }
]

