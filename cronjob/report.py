import glob
import os
import shutil
import time
from datetime import datetime, timedelta

import pandas as pd
import pytz
import yagmail
from tinydb import Query, TinyDB

os.environ["TZ"] = "America/Montreal"
time.tzset()

RECORD_FILE_PATH = "/cronjob/lh3activitycronjob/results/"

yesterday_date = (datetime.now() - timedelta(days=2)).strftime("%b-%d-%Y")

dir_path = os.getcwd()
new_file_path = str(
    os.path.join("/root/lh3activitycronjob/", yesterday_date + "-" + "db.json")
)

db = TinyDB(new_file_path)

result = db.all()
df = pd.DataFrame(result)

try:
    activity_file_path = str(
        os.path.join(RECORD_FILE_PATH, yesterday_date + "-" + "activities.xlsx")
    )
    df.to_excel(activity_file_path, index=False)
    print(df)

    table = pd.pivot_table(
        df,
        values="day",
        index=["user", "queue"],
        columns=["hour"],
        aggfunc="count",
        fill_value=0,
    )
    pivot_tb_file_path = str(
        os.path.join(RECORD_FILE_PATH, yesterday_date + "-" + "pivot.xlsx")
    )
    table.to_excel(pivot_tb_file_path, sheet_name=yesterday_date)
except Exception as e:
    print(e)


try:
    # Email
    yag = yagmail.SMTP("guinslym", "jdhvbdavwnxrbxve")
    to = "guinsly@scholarsportal.info"
    excel = glob.glob(RECORD_FILE_PATH + yesterday_date + "*")
    subject = "Ask report " + datetime.now(pytz.timezone("America/Montreal")).strftime(
        "%A %d %B %Y"
    )

    contents = [yagmail.inline(excel)]

    yag.send(to=to, attachments=excel, subject=subject, contents=contents)
except Exception as e:
    print(e)

try:
    shutil.move(new_file_path, RECORD_FILE_PATH)
    shutil.move(activity_file_path, RECORD_FILE_PATH)
    shutil.move(pivot_tb_file_path, RECORD_FILE_PATH)
except Exception as e:
    print(e)
