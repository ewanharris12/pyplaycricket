from playcric import alleyn
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd

# saturday_date = datetime(2023,7,8)
api_key = '215d26ef6150d4309491ee20ee28a437'
site_id = 672
acc = alleyn.acc(api_key=api_key, site_id=site_id)

lt = acc.get_league_table(117517, simple=True)

print(lt[0])
