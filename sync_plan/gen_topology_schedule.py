import opsync_ as opsync
import numpy as np
import json
import matplotlib.pyplot as plt

path = "testbed"
path = "."

schedule_name = "flat"
schedule_name = "opsync"

tor_num = 192
tor_num = 1024
upper_link = 16
upper_link = 32

upper_link_list = [6,8,12,16]
drift_id_list = [0,1,2,3]

tor_num = 1024
upper_link = 32

hop_err = 10

show_sim = False

seed_tor_num = int(tor_num/upper_link)
slice_num = int(tor_num/upper_link)
assert seed_tor_num % 2 == 0, "Odd seed tor number"
assert seed_tor_num * upper_link == tor_num, "Invalid input"

seed_tor_num = tor_num


schedule = opsync.generate_schedule(seed_tor_num)
schedule = opsync.to_multi_upperlink(schedule, upper_link)
opsync.check_schedule(schedule, upper_link)

sync_count = []
label = []

#add random schedules
np.random.shuffle(schedule)
opsync.check_schedule(schedule, upper_link)

opsync.save_schedule(schedule, f"{path}/schedule_{tor_num}tor_{upper_link}links_random1.txt")
