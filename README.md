**Only compatible with patman15 version 1.8.0**

Only own files will be provided in the future.

You have to edit

**manifest.json**

add:
```
  ,
  {
    "local_name": "libatt*",
    "service_uuid": "0000fff0-0000-1000-8000-00805f9b34fb"
  }
```

**const.py**

add:
```
  "supervolt_bms",
```

and copy the file **supervolt_bms.py** to plugins directory.

