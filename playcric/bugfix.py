from playcric import playcricket

api_key = '215d26ef6150d4309491ee20ee28a437'
site_id = 672
# acc = alleyn.acc(api_key=api_key, site_id=site_id)
pc = playcricket.pc(api_key=api_key, site_id=site_id)

batting, bowling, fielding = pc.get_stat_totals([6237030], group_by_team=True)
