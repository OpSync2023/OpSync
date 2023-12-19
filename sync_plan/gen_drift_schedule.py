import opsync_ as opsync
import numpy as np
import json
import matplotlib.pyplot as plt

path = "testbed"

schedule_name = "opsync_bound"
schedule_name = "flat"
schedule_name = "opsync"

tor_num = 192
#upper_link = 16
slice_duration = 300

#upper_link_list = [6,8,12,16]
upper_link_list = [6]
drift_id_list = ["0_1ms","1_1ms","2_1ms"]
drift_id_list = ["2_err_3ppm"]

#drift_id_list = ["2_err_10%_5ppm","2_err_10%_10ppm","2_err_10%_15ppm","2_err_10%_20ppm"]

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

def save_drift(drift, name : str):
    np.savetxt("testbed/"+name+".txt", drift, fmt="%f")

def read_drift(name : str):
    return np.loadtxt("testbed/"+name+".txt", dtype=float)


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
    print(f"Save path: testbed/schedule_{schedule_name}_{tor_num}tor_{upper_link}links_drift{drift_id}.json")
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
def gen_schedule(upper_link, drift_id):
    schedule = opsync.read_schedule(f"{path}/schedule_{tor_num}tor_{upper_link}links_random1.txt")

    if schedule_name == "opsync_bound":
        sim_drift = [ppm2drift(bound_drift)] * tor_num
        sim_drift[0] = 0
    else:
        sim_drift = read_drift(f"drift_{drift_id}")

    if schedule_name == "flat":
        sim_drift, parent_sync_schedule = \
            opsync.testbed_gen_drift_flat_schedules(schedule, upper_link, hop_err, sim_drift, sim_drift, update_threshold = 0)
    elif schedule_name == "bound":
        drift_bound_per_slice = ppm2drift(bound_drift)
        parent_sync_schedule, backup_children_sync_schedule = \
            opsync.testbed_gen_drift_schedule_bound(schedule, upper_link, hop_err, drift_bound_per_slice, sim_drift, update_threshold = 0)
    else:
        parent_sync_schedule, backup_children_sync_schedule, op_count, hop_count_dict = \
            opsync.testbed_gen_drift_schedule_estimated_drift(schedule, upper_link, hop_err, sim_drift, sim_drift, update_threshold = 0)
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

    print(f"drift {drift_id}, links {upper_link}")
    print(f"Total operations: {total_len}")
    print(f"Avg operation is: {total_len/len(parent_sync_schedule.keys())}")
    #print(f"Avg operation is: {total_len/tor_num}")
    #print(f"Longest ops have {max_op_num} ops.\n")

    save_schedule_as_json(parent_sync_schedule, upper_link, drift_id)

for upper_link in upper_link_list:
    for drift_id in drift_id_list:
        gen_schedule(upper_link, drift_id)