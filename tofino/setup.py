import socket
from scapy.all import *
import numpy as np
import json

path = "/home/p4/path/Opsync/opsync_schedule"

physical_sw_count = 3

schedule_list = ["flat", "opsync", "jellyfish", "fattree", "clos"]
schedule_list = ["sundialexpander", "sundialfattree"]

#drift_id = 0

slice_duration = 300 #us
ppm = 200 # 50 ns drift per 1000 us
drift_err = ppm / (1000 / slice_duration)# x ns dirft per 50 us
print(f"drift error is {drift_err}")


hostname = socket.gethostname()
print(hostname)
host_id = int(hostname[6])
print(host_id)

tor_num = 192
#upper_link = 16
upper_link_list = [6,8,12,16]
drift_id_list = [0,1,2]
drift_id_list = ["0_1ms","1_1ms","2_1ms"]
#drift_id_list = [0]
#drift_id_list = ["2_err_10%_5ppm","2_err_10%_10ppm","2_err_10%_15ppm","2_err_10%_20ppm"]
#upper_link_list = [6]
#schedule_list = ["flat", "opsync", "jellyfish", "fattree"]

upper_link_list = [12]
drift_id_list = ["testbed"]

bfrt_pipe = bfrt.opsync_schedule.pipe

DPTP_PUSH_CLOCK = 0
DPTP_INIT = 1
DPTP_REQ = 2
DPTP_RESP = 3
DPTP_RESP_REC = 4

DPTP_SM_MASTER = 0x10
DPTP_SM_CLIENT = 0x11

def clear_all(pipe, verbose=True, batching=True):
    global bfrt
    
    # The order is important. We do want to clear from the top, i.e.
    # delete objects that use other objects, e.g. table entries use
    # selector groups and selector groups use action profile members

    for table_types in (['MATCH_DIRECT', 'MATCH_INDIRECT_SELECTOR'],
                        ['REGISTER'],
                        ['SELECTOR'],
                        ['ACTION_PROFILE']):
        for table in pipe.info(return_info=True, print_info=False):
            if table['type'] in table_types:
                if verbose:
                    print("Clearing table {:<40} ... ".
                          format(table['full_name']), end='', flush=True)
                table['node'].clear(batch=batching)
                if verbose:
                    print('Done')

clear_all(bfrt_pipe, verbose=False) 

#############################################
# Configure front-panel ports
#############################################


master_port = 32
client_port = 31


port_map = {
    4   :   160,
    8   :   192,
    12  :   296,
    16  :   264,
    20  :   408,
    24  :   440,
    25  :   56,
    26  :   64,
    27  :   40,
    28  :   48,
    29  :   24,
    30  :   32,
    31  :   8,
    32  :   16
    }

fp_port_configs = []
configs = [ 
    ('4/0', '100G', 'NONE', 2),
    ('8/0', '100G', 'NONE', 2),
    ('12/0', '100G', 'NONE', 2),
    ('16/0', '100G', 'NONE', 2),
    ('20/0', '100G', 'NONE', 2),
    ('22/0', '100G', 'NONE', 2),
    ('24/0', '100G', 'NONE', 2),
    ('25/0', '100G', 'NONE', 2),
    ('26/0', '100G', 'NONE', 2),
    ('27/0', '100G', 'NONE', 2),
    ('28/0', '100G', 'NONE', 2),
    ('29/0', '100G', 'NONE', 2),
    ('30/0', '100G', 'NONE', 2),
    ('31/0', '100G', 'NONE', 2),
    ('32/0', '100G', 'NONE', 2),
]

for config in configs:
    port = int(config[0][:-2])
    #print(f"port is {port}")
    if (port == master_port or port == client_port):
        #print(f"add port {port}")
        #print(f"config is {config}")
        fp_port_configs.append(config)

def add_port_config(port_config):
    speed_dict = {'10G':'BF_SPEED_10G', '25G':'BF_SPEED_25G', '40G':'BF_SPEED_40G', '50G':'BF_SPEED_50G', '100G':'BF_SPEED_100G'}
    fec_dict = {'NONE':'BF_FEC_TYP_NONE', 'FC':'BF_FEC_TYP_FC', 'RS':'BF_FEC_TYP_RS'}
    an_dict = {0:'PM_AN_DEFAULT', 1:'PM_AN_FORCE_ENABLE', 2:'PM_AN_FORCE_DISABLE'}
    lanes_dict = {'10G':(0,1,2,3), '25G':(0,1,2,3), '40G':(0,), '50G':(0,2), '100G':(0,)}
    
    # extract and map values from the config first
    conf_port = int(port_config[0].split('/')[0])
    lane = port_config[0].split('/')[1]
    conf_speed = speed_dict[port_config[1]]
    conf_fec = fec_dict[port_config[2]]
    conf_an = an_dict[port_config[3]]


    if lane == '-': # need to add all possible lanes
        lanes = lanes_dict[port_config[1]]
        for lane in lanes:
            dp = bfrt.port.port_hdl_info.get(CONN_ID=conf_port, CHNL_ID=lane, print_ents=False).data[b'$DEV_PORT']
            bfrt.port.port.add(DEV_PORT=dp, SPEED=conf_speed, FEC=conf_fec, AUTO_NEGOTIATION=conf_an, PORT_ENABLE=True)
    else: # specific lane is requested
        conf_lane = int(lane)
        dp = bfrt.port.port_hdl_info.get(CONN_ID=conf_port, CHNL_ID=conf_lane, print_ents=False).data[b'$DEV_PORT']
        bfrt.port.port.add(DEV_PORT=dp, SPEED=conf_speed, FEC=conf_fec, AUTO_NEGOTIATION=conf_an, PORT_ENABLE=True)

print(f"add ports {fp_port_configs}")
for config in fp_port_configs:
    add_port_config(config)


def load_tables(schedule, upper_link, drift_id):
    clear_all(bfrt_pipe, verbose=False) 
        
    tb_read_wire_delay = bfrt_pipe.Ingress.tb_read_wire_delay
    #tb_read_wire_delay.add_with_read_wire_delay(ingress_port = port_map[client_port], input_wire_delay = 163)
    tb_read_wire_delay.add_with_read_wire_delay(ingress_port = port_map[client_port], input_wire_delay = 168)


    #drifts = init_drift(tor_num = tor_num, drift = 0)
    drifts = np.loadtxt(f"{path}/drift_{drift_id}.txt", dtype=float)

    tb_read_drift = bfrt_pipe.Ingress.tb_read_drift
    for id in range(len(drifts)):
        if id == 0:
            tb_read_drift.add_with_read_drift(
                master_id = id,
                simulated_drift = 0
            )
        else:
            tb_read_drift.add_with_read_drift(
                master_id = id,
                simulated_drift = drifts[id]
            )

    tb_add_noise_to_drift = bfrt_pipe.Ingress.tb_add_noise_to_drift
    noise_list = [0,0,0,0,0,0,0,0,0,0,0,0,-1,-1,1,1]
    noise_list = [0,0,0,0,0,0,0,0,-1,-1,-1,-1,1,1,1,1]
    #noise_list = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    for id in range(16):
        tb_add_noise_to_drift.add_with_read_noise(random_value = id, noise_value = noise_list[id])

    slice_num = int(tor_num / upper_link)
    bfrt_pipe.Ingress.slice_number.set_default(value = slice_num-1)

    tb_check_sync_schedule = bfrt_pipe.Ingress.tb_check_sync_schedule
    if schedule == "chain":
        for slice_id in range(slice_num):
            for id in range(tor_num-1):
                tb_check_sync_schedule.add_with_set_client(
                    dptp_type = DPTP_SM_MASTER,
                    slice_id = slice_id,
                    master_id = id,
                    sync_dst_index = 0,
                    client = id + 1
                )
    elif schedule in schedule_list:
        file_pointer = open(f"{path}/sync_schedules/schedule_{schedule}_{tor_num}tor_{upper_link}links_drift{drift_id}.json")
        print(f"Load table {schedule}_{tor_num}tor_{upper_link}links_drift{drift_id}")
        json_object = json.load(file_pointer)
        table_content = json.dumps(json_object)
        tb_check_sync_schedule.add_from_json(table_content)
    else:
        assert 0, f"Invalid schedule: {schedule}"

    forward = bfrt_pipe.Ingress.forward

    forward.add_with_set_port(dptp_type = DPTP_SM_MASTER,
                                egress_port = port_map[master_port])

def write_arguments(schedule, upper_link, drift_id):
    path = "/home/p4/path/Opsync/opsync_schedule/measure"
    with open(f"{path}/arg.txt", 'w') as f:
        f.write(str(schedule)+"\n")
        f.write(str(upper_link)+"\n")
        f.write(str(drift_id)+"\n")

    #os.system(f"/home/p4/bf-sde-9.12.0/run_bfshell.sh -b {path}/read_error_json_file_input.py")

def sample_error(schedule, upper_link, drift_id):
    error_reg = bfrt.opsync_schedule.pipe.Ingress.offset_reg

    data = {}

    #for _ in range(1024):
    #for _ in range(128):
    for _ in range(2048):
        json_str = error_reg.dump(from_hw=True, json=True)
        json_obj = json.loads(json_str)

        index = 0

        for id, entry in enumerate(json_obj):
            observed_tors = list(range(192))
            if id not in observed_tors:
                continue

            error = entry['data']['Ingress.offset_reg.f1'][index]
            if error > 1<<31:
                error = - ((1<<32) - error)
            
            if id not in data.keys():
                data[id] = []

            data[id].append(error)

        time.sleep(0.01)

    #print(np.array(data).shape)

    path = "/home/p4/path/Opsync/opsync_schedule/measure/error"
    folder = f"{path}/{tor_num}tor_{upper_link}links_{schedule}_drift{drift_id}"
    if not os.path.exists(folder):
        os.mkdir(folder)

    for tor in observed_tors:
        file_name = f'{folder}/tor{tor}.txt'
        np.savetxt(file_name, np.array(data[tor]), fmt='%d', delimiter=' ')

time.sleep(5)

for schedule in schedule_list:
    for upperlink in upper_link_list:
        for drift_id in drift_id_list:
            load_tables(schedule, upperlink, drift_id)
            time.sleep(5)
            sample_error(schedule, upperlink, drift_id)