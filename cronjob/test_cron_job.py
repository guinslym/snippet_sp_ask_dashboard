import os.path
import pathlib
from datetime import datetime

ts = datetime.now().strftime(" - %m/%d/%Y, %H:%M:%S")
filename = "hello.txt"
filepath = os.path.join("/usr/src/app/sp_dashboard/tmp_file", filename)

with open(filepath, "a") as dumbfile:
    dumbfile.write("</br>hello.txt-cron" + str(ts))
