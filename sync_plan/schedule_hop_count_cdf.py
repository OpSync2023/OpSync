import opsync_ as opsync
import numpy as np
import json
import matplotlib.pyplot as plt
import time

path = "testbed"

schedule_name = "opsync_bound"
schedule_name = "flat"
schedule_name = "opsync"

tor_num = 192

#tor_num = 1024
#upper_link = 16
slice_duration = 50

#upper_link_list = [6,8,12,16]
upper_link_list = [6]

#upper_link_list = [32]


drift_id_list = ["0_1ms","1_1ms","2_1ms"]
drift_id_list = ["2_err_3ppm"]
drift_id_list = [1]

slice_duration_list = [1,50,100,300,500,1000]
slice_duration_list = [50,100,300,1000]

color_list = [ '#994F00','#0C7BDC', '#DC3220',  '#40B0A6',  ]

hop_err = 10
bound_drift = 200

show_sim = False


def ppm2drift(ppm):
    ppm = np.array(ppm)
    return ppm / (1000 / slice_duration)

def save_drift(drift, name : str):
    np.savetxt("testbed/"+name+".txt", drift, fmt="%f")

def read_drift(name : str):
    return np.loadtxt(name+".txt", dtype=float)

def draw_hop_count(hop_count_dict, duration, upper_link):
    print(hop_count_dict)

    slice_num = tor_num / upper_link
    oppotunity = slice_num * upper_link
    cycle = 20
    total_opptunity = oppotunity * cycle * tor_num

    #pdf = np.array(list(hop_count_dict.values()))/ total_opptunity
    #pdf = np.array(list(hop_count_dict.values()))/ cycle / slice_num / tor_num
    pdf = np.array(list(hop_count_dict.values()))/ sum(list(hop_count_dict.values()))
    plt.plot(hop_count_dict.keys(), pdf, label = f"{duration}us",
             color = color_list[id],
             linewidth=3.0)

def draw_hop_count_cdf(id, hop_count_dict, duration, upper_link):
    print(hop_count_dict)

    slice_num = tor_num / upper_link
    oppotunity = slice_num * upper_link
    cycle = 20
    total_opptunity = oppotunity * cycle * tor_num


    #pdf = np.array(list(hop_count_dict.values()))/ total_opptunity
    pdf = np.array(list(hop_count_dict.values()))/ sum(list(hop_count_dict.values()))
    cdf = np.cumsum(pdf)
    plt.plot(hop_count_dict.keys(), cdf, label = f"{duration}us",
             color = color_list[id],
             linewidth=3.0)
    

#sim_drift = read_drift(f"drift_{tor_num}tor_random1")
def gen_schedule(id, upper_link, slice_duration):
    schedule = opsync.read_schedule(f"{path}/schedule_{tor_num}tor_{upper_link}links_random1.txt")

    if schedule_name == "opsync_bound":
        sim_drift = [ppm2drift(bound_drift)] * tor_num
        sim_drift[0] = 0
    else:
        sim_drift = read_drift(f"drift_slice/slice_{slice_duration}us")

    if schedule_name == "flat":
        sim_drift, parent_sync_schedule = \
            opsync.testbed_gen_drift_flat_schedules(schedule, upper_link, hop_err, sim_drift, sim_drift, update_threshold = 0)
    elif schedule_name == "bound":
        drift_bound_per_slice = ppm2drift(bound_drift)
        parent_sync_schedule, backup_children_sync_schedule = \
            opsync.testbed_gen_drift_schedule_bound(schedule, upper_link, hop_err, drift_bound_per_slice, sim_drift, update_threshold = 0)
    else:
        start = time.time()
        parent_sync_schedule, backup_children_sync_schedule, op_count, hop_count_dict = \
            opsync.testbed_gen_drift_schedule_estimated_drift(schedule, upper_link, hop_err, sim_drift, sim_drift, update_threshold = 0)
        end = time.time()
        print(f"Time: {end-start}")
    #print(f"Drift: {sim_drift}")
    #print(f"Sync schedule: {f}")
    total_len = 0
    max_op_num = 0
    for src, ops in parent_sync_schedule.items():
        #print(f"src {src}: {ops}")
        ops_len = 0
        for slice_id, op in ops.items():
            ops_len += len(op)
        if ops_len > max_op_num:
            max_op_num = ops_len
        total_len += ops_len

    print(f"Slice {slice_duration}, links {upper_link}")
    print(f"Total operations: {total_len}")
    print(f"Avg operation is: {total_len/len(parent_sync_schedule.keys())}")
    #print(f"Avg operation is: {total_len/tor_num}")
    #print(f"Longest ops have {max_op_num} ops.\n")

    #draw_hop_count(hop_count_dict, slice_duration, upper_link)
    draw_hop_count_cdf(id, hop_count_dict, slice_duration, upper_link)
    return list(hop_count_dict.values())

hop_count_dicts = []
for upper_link in upper_link_list:
    #for drift_id in drift_id_list:
    for id, slice_duration in enumerate(slice_duration_list):
        hop_count_dicts.append(gen_schedule(id, upper_link, slice_duration))

#plt.xticks(range(1,10), size = 22)
#plt.xlim((0,8))
#plt.yticks(np.arange(0,0.61,0.1), size = 22)
hop_count_dicts = np.array(hop_count_dicts)
print(hop_count_dicts)
print(sum(hop_count_dicts))
data = sum(hop_count_dicts)

print(f"sum is {sum(data)}")

def cdf(data):
    cnt, b_cnt = np.histogram(data, bins=10000)
    pdf = cnt/sum(cnt)
    cdf = np.cumsum(pdf)
    #print(list(cdf))
#cdf(data)

plt.xticks(size = 22)
plt.xlim((0,8))
plt.yticks(np.arange(0,1.1,0.2), size = 22)
plt.ylim((0,1))

plt.xlabel("Clock Propagation Path Length (hop)", fontsize = 22)
plt.ylabel("Sync Actions per Slice per ToR", fontsize = 22)
#plt.ylabel("PDF", fontsize = 22)
plt.ylabel("CDF", fontsize = 22)
plt.grid()
plt.legend(fontsize = 22)
plt.subplots_adjust(bottom=0.16, left = 0.16, right = 0.95, top = 0.95, hspace = 0.0)
#plt.show()
#plt.savefig(f"hop_length.pdf")

plt.savefig(f"hop_length_cdf.pdf")