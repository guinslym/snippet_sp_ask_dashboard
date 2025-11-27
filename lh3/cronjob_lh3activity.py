import os
import sys
import time
from datetime import datetime

import requests
from lh3 import *
from tinydb import Query, TinyDB

is_windows = sys.platform.startswith("win")
if not is_windows:
    os.environ["TZ"] = "America/Montreal"
    time.tzset()

CRONJOB_RESULT_LH3_ACTIVITY = "/usr/src/app/crontab/lh3activitycronjob"

try:
    client = Client()
    client.set_options(version="v1")
    users = client.all("users")
except requests.exceptions.ConnectionError:
    print("Site not rechable", url)
    # send email
except Exception as e:
    print(e)
    # send email
    import sys

    sys.exit()

now = datetime.now()
current_time = now.strftime("%H:%M:%S")
current_date = now.strftime("%b-%d-%Y")
current_date_name = now.strftime("%A")
current_hour = now.strftime("%H")

# Connect to DB instead
new_file_path = str(os.path.join(".", current_date + "-" + "db.json"))
db = TinyDB(new_file_path)


def add_activity_to_database():
    for user in users.get_list():
        if user["show"] != "unavailable":
            # Is that user staffing any queue?
            assignments = users.one(user["id"]).all("assignments").get_list()
            for assignment in assignments:
                if assignment["enabled"]:
                    activity = {
                        "date": current_date,
                        "day": current_date_name,
                        "time": current_time,
                        "hour": int(current_hour),
                        "user": assignment.get("user"),
                        "userid": assignment.get("id"),
                        "queue": assignment.get("queue"),
                        "show": assignment.get("userShow"),
                        "status": user.get("status"),
                    }
                    db.insert(activity)


if __name__ == "__main__":
    add_activity_to_database()
