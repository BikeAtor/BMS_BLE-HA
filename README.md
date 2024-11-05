**do not use this files at the moment**

**Only compatible with patman15 version 1.6 and 1.7**

Support for Version 1.8.0 of patman15 repository isn't ready yet.

Only own files will be provided in the future.

You have to edit
**manifest.json**
add:
        ,
        {
          "local_name": "libatt*",
          "service_uuid": "0000fff0-0000-1000-8000-00805f9b34fb"
        }

**const.py**
add:
        "supervolt_bms",

and copy the bms-file to plugins

