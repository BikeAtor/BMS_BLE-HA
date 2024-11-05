# 
Cause of many changes from 1.6 to 1.8 in patman15 project i will only provide the class for supervolt BMS (old one with black top of case).

You have to edit manifest.json
 add:
,
    {
      "local_name": "libatt*",
      "service_uuid": "0000fff0-0000-1000-8000-00805f9b34fb"
    }

const.py
add:
"supervolt_bms",

and copy the bms-file to plugins

