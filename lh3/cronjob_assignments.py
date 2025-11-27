import shutil

import pandas as pd
from lh3.api import *

filepath = "/usr/src/app/cron_results/"
client = Client()
client.set_options(version="v1")
users = client.all("users")
all_operators = list()
for user in users.get_list():
    values = users.one(user.get("id")).all("assignments").get_list()
    for op in values:
        all_operators.append(op)

df = pd.DataFrame(all_operators)
del df["queueShow"]
del df["userShow"]
del df["enabled"]
df.to_excel("/usr/src/app/cron_results/operator_assignments.xlsx", index=False)
