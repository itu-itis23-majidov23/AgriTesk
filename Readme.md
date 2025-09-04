Pair

bluetoothctl
pair 00:24:09:01:00:A4
trust 00:24:09:01:00:A4
quit


Bind to /dev/rfcomm0 using RFCOMM channel 1

sudo rfcomm bind /dev/rfcomm0 00:24:09:01:00:A4 1


Now /dev/rfcomm0 should exist.

Test connection

screen /dev/rfcomm0 9600


If Arduino is sending "Hello", it should appear here.

Exit screen with CTRL+A then K.