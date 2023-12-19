import opsync_ as opsync
import numpy as np
import json
import matplotlib.pyplot as plt

path = "testbed"

schedule_name = "flat"
schedule_name = "opsync"

failure_recovery = True
failure_recovery = False

failure_types = ["node", "link"]
failure_types = [""]
failure_types = ["link"]
failure_types = ["node"]
failure_types = ["ocs"]
failure_types = ["node", "link", "ocs"]

failure_nodes = [50, 100]
failure_nodes = list(range(10,192,10))
failure_nodes = list(range(1,192,1))
failure_nodes = list(range(10,192,2))
failure_nodes = list(range(10,192,20))
failure_nodes = []
failure_nodes = [103,53,22,93,75,159,113,139,50,16,
                 40,32,13,97,71,42,110,44,117,62]
failure_nodes = [103,53,22,93,75,159,113,139,50,16]

failure_link_src = list(range(3, 192, 10))
failure_link_dst = list(range(9, 192, 10))

failure_links = list(zip(failure_link_src, failure_link_dst))
link_failure_count = 0

failure_links_magic_number = 0

failure_ocs = 0

failure_dict = {
    "" : "",
    "node" : failure_nodes,
    "link" : failure_links,
    "ocs" : failure_ocs
}
tor_num = 192
#upper_link = 16

upper_link_list = [6,8,12,16]
drift_id_list = [0,1,2,3]

upper_link_list = [8]
upper_link_list = [6]
drift_id_list = [1]
drift_id_list = [2]

hop_err = 10
update_threshold = 0

slice_num = int(tor_num/upper_link_list[0])
#assert seed_tor_num % 2 == 0, "Odd seed tor number"
#assert seed_tor_num * upper_link == tor_num, "Invalid input"

#seed_tor_num = tor_num

def save_drift(drift, name : str):
    np.savetxt("testbed/"+name+".txt", drift, fmt="%f")

def read_drift(name : str):
    return np.loadtxt("testbed/"+name+".txt", dtype=float)


DPTP_SM_MASTER = 0x0010

def save_schedule_as_json(schedule, sync_schedule, backup_children_sync_schedule, upper_link, drift_id):
    jsons = []
    table_name = f"pipe.Ingress.tb_check_sync_schedule"
    action = "Ingress.set_client"

    #print(sync_schedule)

    failure_count = 0
    link_failure_count = 0

    for master, ops in sync_schedule.items():
        print(f"master {master}, ops {ops}")
        for slice_id, dsts in ops.items():            
            for id, dst in enumerate(dsts):
                
                json_sync_src = master
                json_sync_dst = dst
                json_slice_id = slice_id
                json_id = id

                if "node" in failure_types and (master in failure_nodes):
                    print(f"Remove op src:{json_sync_src} dst:{json_sync_dst}, slice:{json_slice_id} because of the node failure of {master}")
                    failure_count += len(ops)
                    if failure_recovery == True and \
                        json_sync_dst in backup_children_sync_schedule.keys() and \
                        json_slice_id in backup_children_sync_schedule[json_sync_dst].keys() and \
                        backup_children_sync_schedule[json_sync_dst][json_slice_id] not in failure_nodes:

                        json_sync_src = backup_children_sync_schedule[json_sync_dst][json_slice_id]

                        json_id = 32 + (json_sync_dst) % 32 # avoid id conflict
                        print(f"Recovery item: src:{json_sync_src} dst:{json_sync_dst}, slice:{json_slice_id}")
                    else:
                        continue

                if "link" in failure_types and (json_sync_src + json_sync_dst) % 2 == failure_links_magic_number:
                    failure_count += 1
                    link_failure_count += 1
                    print(f"Remove op src:{json_sync_src} dst:{json_sync_dst}, slice:{json_slice_id} because of the link failure.")

                    if failure_recovery == True and \
                        json_sync_dst in backup_children_sync_schedule.keys() and \
                        json_slice_id in backup_children_sync_schedule[json_sync_dst].keys():

                        json_sync_src = backup_children_sync_schedule[json_sync_dst][json_slice_id]
                        json_id = 32 + (json_sync_dst) % 32 # avoid id conflict

                    else:
                        continue
                        
                if "ocs" in failure_types:
                    ocs_links = opsync.find_ocs_links(schedule, upper_link, failure_ocs)
                    if (json_sync_src, json_sync_dst) in ocs_links:
                        failure_count += 1
                        print(f"Remove op src:{json_sync_src} dst:{json_sync_dst}, slice:{json_slice_id} because of the OCS failure.")

                        if failure_recovery == True and \
                            json_sync_dst in backup_children_sync_schedule.keys() and \
                            json_slice_id in backup_children_sync_schedule[json_sync_dst].keys():

                            json_sync_src = backup_children_sync_schedule[json_sync_dst][json_slice_id]
                            json_id = 32 + (json_sync_dst) % 32 # avoid id conflict

                        else:
                            continue
                        
                
                
                item = {
                    "table_name" : table_name,
                    "action" : action,
                    "key" : {
                        "dptp_type" : DPTP_SM_MASTER,
                        "slice_id" : int(json_slice_id),
                        "master_id" : int(json_sync_src),
                        "sync_dst_index" : json_id
                    },
                    "data" : {
                        "client" : int(json_sync_dst)
                    }
                }
                #print(item)
                jsons.append(item)
        
    #print(json.dumps(jsons, indent=2))
    #print(f"Length is for tor {tor_id} is {len(jsons)}")
    print(f"Drop {failure_count} ops in total.")
    #print(f"Drop {failure_count} ops in total.")
    failure_name = ""
    for failure_type in failure_types:
        if failure_type == "link":
            link_failure_count = int(link_failure_count / slice_num)
            failure_name +=  f"_{link_failure_count}" + failure_type 
        elif failure_type == "ocs":
            failure_name +=  f"_{1}" + failure_type 
        else:
            failure_name +=  f"_{len(failure_dict[failure_type])}" + failure_type 
    
    print(f"Failure_name is {failure_name}")

    if failure_recovery == True:
        file_name =f"testbed_failure/schedule_{schedule_name}_{tor_num}tor_{upper_link}links_drift{drift_id}_failure{failure_name}_recovery.json"
    else:
        file_name =f"testbed_failure/schedule_{schedule_name}_{tor_num}tor_{upper_link}links_drift{drift_id}_failure{failure_name}.json"

    with open(file_name, "w") as outfile:
        json.dump(jsons, outfile, indent=2)


group_error = []
group_label = []

sync_schedule = []

max_estimated_err = []
max_sim_err = []

estimate_acc = [0]


#sim_drift = read_drift(f"drift_{tor_num}tor_random1")
def gen_schedule(upper_link, drift_id):
    schedule = opsync.read_schedule(f"{path}/schedule_{tor_num}tor_{upper_link}links_random1.txt")

    sim_drift = read_drift(f"drift_{drift_id}")

    if schedule_name == "flat":
        sim_drift, parent_sync_schedule = \
            opsync.testbed_gen_drift_flat_schedules(schedule, upper_link, hop_err, sim_drift, sim_drift, update_threshold)
    else:
        parent_sync_schedule, backup_children_sync_schedule = \
            opsync.testbed_gen_drift_schedule_estimated_drift(schedule, upper_link, hop_err, sim_drift, sim_drift, update_threshold)
    #print(f"Drift: {sim_drift}")
    print("Sync schedule")
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
    #print(f"Avg operation is: {total_len/len(parent_sync_schedule.keys())}")
    print(f"Avg operation is: {total_len/tor_num}")
    print(f"Longest ops have {max_op_num} ops.\n")

    save_schedule_as_json(schedule, parent_sync_schedule, backup_children_sync_schedule, upper_link, drift_id)
    return parent_sync_schedule

for upper_link in upper_link_list:
    for drift_id in drift_id_list:
        parent_sync_schedule = gen_schedule(upper_link, drift_id)
        #opsync.vis_schedule_whole_schedule(parent_sync_schedule)