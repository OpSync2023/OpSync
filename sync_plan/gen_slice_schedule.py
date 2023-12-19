import opsync_ as opsync
import numpy as np
import json
import matplotlib.pyplot as plt

path = "testbed"

schedule_name = "flat"
schedule_name = "opsync_bound"
schedule_name = "opsync"

tor_num = 192
#upper_link = 16
#slice_duration = 300

upper_link_list = [6,8,12,16]
slice_duration_list = [1,10,50,100,300,500,1000]

hop_err = 10
bound_drift = 200

show_sim = False

#seed_tor_num = int(tor_num/upper_link)
#slice_num = int(tor_num/upper_link)
#assert seed_tor_num % 2 == 0, "Odd seed tor number"
#assert seed_tor_num * upper_link == tor_num, "Invalid input"

#seed_tor_num = tor_num

def ppm2drift(ppm):
    ppm = np.array(ppm)
    return ppm / (1000 / slice_duration)

def read_drift(name : str):
    return np.loadtxt("drift_slice/"+name+".txt", dtype=float)


DPTP_SM_MASTER = 0x0010

def save_schedule_as_json(sync_schedule, upper_link, drift_id):
    jsons = []
    table_name = f"pipe.Ingress.tb_check_sync_schedule"
    action = "Ingress.set_client"

    #print(sync_schedule)
    for master, ops in sync_schedule.items():
        #print(f"master {master}, ops {ops}")
        for slice_id, dsts in ops.items():
            
            for id, dst in enumerate(dsts):
                item = {
                    "table_name" : table_name,
                    "action" : action,
                    "key" : {
                        "dptp_type" : DPTP_SM_MASTER,
                        "slice_id" : slice_id,
                        "master_id" : master,
                        "sync_dst_index" : id
                    },
                    "data" : {
                        "client" : int(dst)
                    }
                }
                #print(item)
                jsons.append(item)
        
    #print(json.dumps(jsons, indent=2))
    #print(f"Length is for tor {tor_id} is {len(jsons)}")
    with open(f"testbed/schedule_{schedule_name}_{tor_num}tor_{upper_link}links_drift{drift_id}.json", "w") as outfile:
        json.dump(jsons, outfile, indent=2)


group_error = []
group_label = []

sync_schedule = []

max_estimated_err = []
max_sim_err = []

estimate_acc = [0, 0.2, 0.4, 0.6, 0.8, 1]
estimate_acc = [0]



#sim_drift = read_drift(f"drift_{tor_num}tor_random1")
def gen_schedule(upper_link, slice_duration):
    schedule = opsync.read_schedule(f"{path}/schedule_{tor_num}tor_{upper_link}links_random1.txt")

    sim_drift = read_drift(f"slice_{slice_duration}us")

    parent_sync_schedule, backup_children_sync_schedule, op_count = \
        opsync.testbed_gen_drift_schedule_estimated_drift(schedule, upper_link, hop_err, sim_drift, sim_drift, update_threshold = 0)

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

    print(f"Slice duration {slice_duration}, links {upper_link}, op count {op_count}")
    #print(f"Total operations: {total_len}")
    #print(f"Avg operation is: {total_len/len(parent_sync_schedule.keys())}")
    #print(f"Avg operation is: {total_len/tor_num}")
    #print(f"Longest ops have {max_op_num} ops.\n")

    #save_schedule_as_json(parent_sync_schedule, upper_link, drift_id)

for upper_link in upper_link_list:
    for slice_duration in slice_duration_list:
        gen_schedule(upper_link, slice_duration)