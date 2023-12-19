import numpy as np
import random
import matplotlib.pyplot as plt
import copy
from matplotlib import cm
from enum import Enum
import networkx as nx

sim_circle = 20
porfile_gap = 5

def generate_schedule(tope : int):
    # modify the number of clubs
    clubes = []
    index_clubes = 0
    for i in range(0,tope):
        clubes.append(str(i))

    auxT = len(clubes)
    impar= True if auxT%2 != 0 else False

    if impar:
        auxT += 1

    totalP = int(auxT/2) # total matches in a matchday
    day = []
    reverseIndex = auxT-2


    for i in range(1,auxT):
        team = []
        list_team = {}
        for indiceP in range(0,totalP):
            if index_clubes > auxT-2:
                index_clubes = 0

            if reverseIndex < 0:
                reverseIndex = auxT-2

            if indiceP == 0: # he initial game of each date
                if impar:
                    team.append(clubes[index_clubes])
                else:
                    if (i+1)%2 == 0:
                        game = [clubes[index_clubes], clubes[auxT-1]]
                    else:
                        game = [clubes[auxT-1], clubes[index_clubes]]
                    team.append(" ".join(game))
            else:
                game = [clubes[index_clubes], clubes[reverseIndex]]
                team.append(" ".join(game))
                reverseIndex -= 1
            index_clubes += 1

        list_team = {
            'day': "day Nro.: " + str(i),
            'team': team
        }
        day.append(list_team)


    #print(day)
    ops = [[-1 for i in range(tope-1)] for j in range(tope)]
    for item in day:
        for key, value in item.items():
            if key == 'day':
                round_id = int(value.split(':')[-1])
            else:
                for teams in value:
                    team_1 = int(teams.split(' ')[0])
                    team_2 = int(teams.split(' ')[1])
                    ops[team_1][round_id-1] = team_2
                    ops[team_2][round_id-1] = team_1
        
    for i in range(tope):
        #print(ops[i])
        pass

    for i in range(tope):
        if i in ops[i]:
            debug_print('false')

    col_totals = [ sum(x) for x in zip(*ops)]
    for item in col_totals:
        if item != int((tope-1)*tope/2):
            debug_print('false')

    ops = np.array(ops).T
    #print(ops)
    return ops

def to_multi_upperlink(schedule:np.ndarray, upper_link:int):

    tor_num = schedule[0].shape[0]
    if upper_link == 1:
        return schedule
    else:
        #schedule = schedule.tolist()
        #schedule.append(list(range(tor_num)))
        #schedule = np.array(schedule)
        schedule = np.append(schedule, [list(range(tor_num))], axis=0)
    
    debug_print(schedule)
    
    multi_link_schedule = []
    for id in range(0, tor_num, upper_link):
        #print(schedule[id:id+upper_link])
        group_schedule = np.column_stack((schedule[id:id+upper_link]))
        #print(group_schedule)
        group_schedule = group_schedule.flatten()
        #print(group_schedule)
        multi_link_schedule.append(group_schedule)
    #print(multi_link_schedule)
    return np.array(multi_link_schedule)

debug_flag = False

def check_schedule(schedule, upper_link:int) -> bool:
    def check_connection_symmetry(slice_schedule, upper_link):
        tor_num = int(len(slice_schedule) / upper_link)
        #print(tor_num)
        assert (tor_num * upper_link) == len(slice_schedule)

        for tor_id in range(tor_num):
            for port_id in range(upper_link):
                dst_tor = slice_schedule[tor_id * upper_link + port_id]
                dst_index = dst_tor * upper_link + port_id
                assert slice_schedule[dst_index] == tor_id, f"tor {tor_id} port {port_id}"

    print(f"Tor num is {len(schedule[0])/upper_link}, upper links {upper_link}")
    #print(f"check \n{schedule}")
    for slice_schedule in schedule:
        check_connection_symmetry(slice_schedule, upper_link)


def save_schedule(schedule, name : str):
    np.savetxt(name, schedule, fmt="%d")

def read_schedule(name : str):
    return np.loadtxt(name, dtype=int)

def find_ocs_links(schedule, upper_link, ocs_id):
    
    links = []
    for slice_schedule in schedule:
        tor_num = int(len(slice_schedule) / upper_link)
        for tor_id in range(tor_num):
            dst_tor = slice_schedule[tor_id * upper_link + ocs_id]
            links.append((tor_id, dst_tor))

    return links

def debug_print(*str):
    if debug_flag == True:
        debug_print(str)

class Sync_algo(Enum):
    only_with_master = 1
    most_improvement = 2
    worst_err = 3
    as_many_as_possible = 4

def most_benefit_operations(sync_candidates, sync_limit):
    sync_candidates_items = sorted(sync_candidates.items(), key=lambda x:x[0], reverse=True)
    #print(f"sync_candidates_items {sync_candidates_items}")
    sync_candidates = []
    top_benifit_tor = []
    from_master = []

    for benefit, items in sync_candidates_items:
        for pair in items:
            src, dst = pair
            if src == 0:
                #sync master has priority
                from_master.append(pair)
            else:
                sync_candidates.append(pair)
    #print(f"sync candidates: {sync_candidates}")
    
    sync_operations = from_master
    num_to_sync = max(0, sync_limit - len(sync_operations))
    #print(num_to_sync)
    sync_operations += sync_candidates[:min(num_to_sync,len(sync_candidates))]
    assert len(sync_operations) <= sync_limit
    #print(f"sync operations: {sync_operations}")

    return sync_operations

def worst_err_operations(sync_candidates, cur_bound_err, sync_limit):
    sync_candidates = sorted(sync_candidates.items(), key=lambda x:x[0], reverse=True)

    flatten_candidates = []
    from_master = []
    dst_set = set()
    #print(sync_candidates)
    for benefit, pair_list in sync_candidates:
        for pair in pair_list:
            src, dst = pair
            if dst not in dst_set:
                dst_set.add(dst)
                if src == 0:
                    #sync master has priority
                    from_master.append(pair)
                else:
                    flatten_candidates.append(pair)
    #print(f"Flatten \n{flatten_candidates}")
    #print(f"current bound err \n{cur_bound_err}")
    top_worst_tor = from_master
    num_to_sync = max(0,sync_limit - len(top_worst_tor))
    top_worst_tor += sorted(flatten_candidates, key=lambda x:cur_bound_err[x[1]],reverse=True)[:min(num_to_sync,len(flatten_candidates))]
    assert len(top_worst_tor) <= sync_limit
    #top_worst_tor = sorted(flatten_candidates, key=lambda x:cur_bound_err[x[1]],reverse=True)[:min(sync_limit,len(flatten_candidates))]
    
    
    #print(f"worst {top_worst_tor}")
    #print(f"dst v {[cur_bound_err[dst] for src, dst in top_worst_tor]}")
    #print(f"src v {[cur_bound_err[src] for src, dst in top_worst_tor]}")
    #for src, dst in top_worst_tor:
        #print(f"src {src}, dst {dst}")
        #print(f"err {cur_bound_err[dst]}")
    return top_worst_tor

def only_to_master(sync_candidates):
    #print(sync_candidates)
    flatten_candidates = []
    for pair_list in sync_candidates:
        for pair in pair_list:
            flatten_candidates.append(pair)
    #print(flatten_candidates)
    sync_operations = [sync_pair for sync_pair in flatten_candidates if sync_pair[0] == 0]
    #print(sync_operations)
    return sync_operations
    
def optimal_operations(sync_candidates):
    #print(sync_candidates)
    flatten_candidates = []
    for pair_list in sync_candidates.values():
        for pair in pair_list:
            flatten_candidates.append(pair)
    #print(flatten_candidates)
    sync_operations = [sync_pair for sync_pair in flatten_candidates]
    #print(sync_operations)
    return sync_operations    

def level_schedule(optical_schedule: np.ndarray, upper_link:int, hop_err:int, drift:int, sync_limit:int):
    pass

def ppm2drift(ppm):
    slice_duration = 50
    return ppm / (1000 / slice_duration)

def init_drift(tor_num, sigma, es_acc):
    estimated_drift = []
    sim_drift = []

    for _ in range(tor_num):
        real_drift = random.gauss(0, sigma)
        if real_drift > 0:
            real_drift = min(real_drift, 200)
        else:
            real_drift = max(real_drift, -200)

        #real_drift = random.uniform(-drift, drift)
        #print(f"drift {real_drift}")
        #sim_drift.append(real_drift)
        estimation_error = random.gauss(0, sigma * es_acc / 100 / 2)
        #estimation_error = random.uniform(-drift * es_acc / 100, drift * es_acc / 100)
        if estimation_error > 0:
            estimation_error = min(estimation_error, 200 * es_acc)
        else:
            estimation_error = max(estimation_error, -200 * es_acc)
        #print(f"estimation error is {estimation_error}")

        sim_drift.append(real_drift + estimation_error)

        
        #variance = random.uniform(-es_acc, es_acc)
        estimated_drift.append(real_drift)
        sim_drift[0] = 0
        estimated_drift[0] = 0

    return estimated_drift, sim_drift

def sim_sync_err_estimated_drift(optical_schedule: np.ndarray, upper_link:int, hop_err:int, drift:int, es_acc:float, update_threshold:float) -> list[np.ndarray]:
    all_estimated_err = []
    all_sim_err = []
    #print(optical_schedule)
    tor_num = int(optical_schedule[0].shape[0] / upper_link)
    debug_print(f"There are {tor_num} nodes, {upper_link} upper link per tor, {len(optical_schedule)} time slices.")

    #inital error as inf
    cur_estimated_err = [drift * tor_num for _ in range(tor_num)]
    cur_estimated_err[0] = 0
    cur_sim_err = [0 for _ in range(tor_num)]

    max_estimated_err = [0 for _ in range(tor_num)]
    max_sim_err = [0 for _ in range(tor_num)]


    sync_schedule = {_:[] for _ in range(tor_num)}


        #sim_drift.append(drift) # using max drift rate
    #print(f"real drift is {sim_drift}")
    #master has no dirft to itself
    
    sync_count = 0

    #simulate 10 schedules to converge

    for slice_id, sync_array in enumerate(list(optical_schedule) * sim_circle):
        #debug_print(sync_array)
        circle = int(slice_id/len(optical_schedule))
        cur_slice = slice_id%len(optical_schedule)
        if circle % porfile_gap == 0:
            estimated_drift, sim_drift = init_drift(tor_num, drift, es_acc)

        sync_candidates = {}
        sync_operations = []
        #go through every node to calculate sync error in this slice
        estimated_error = copy.deepcopy(cur_estimated_err)
        sim_err = copy.deepcopy(cur_sim_err)
        for sync_dst_id in range(tor_num):
            #for matrix representation
            sync_src_port = sync_array[sync_dst_id * upper_link : (sync_dst_id+1) * upper_link]
            connected_ports = sync_src_port

            if sync_dst_id == 0:
                #master tor
                continue
            
            if len(connected_ports) == 0:
                #no sync this slice
                debug_print(f"Error: No connected node for node {sync_dst_id}. There's something wrong in schedule.")
                return []

            else:
                
                error_candidates = {}
                for src in connected_ports:
                    #key is abs of error, value is the index
                    error_candidates[abs(cur_estimated_err[src])] = src
                
                min_error = min(error_candidates.keys())
                sync_src = error_candidates[min_error]

                if 0 in connected_ports:
                    #print(connected_ports)
                    #print(cur_estimated_err[0], cur_estimated_err[sync_src])
                    #print(sync_src)
                    assert sync_src == 0

                sim_hop_err = random.gauss(0, hop_err/3)
                if sim_hop_err > 0:
                    sim_hop_err = min(sim_hop_err, hop_err)
                else:
                    sim_hop_err = max(sim_hop_err, -hop_err)

                if (abs(cur_estimated_err[sync_dst_id]) > abs(cur_estimated_err[sync_src]) + update_threshold):
                #if (abs(cur_estimated_err[sync_dst_id]) > abs(cur_estimated_err[sync_src]) + sim_hop_err):
                    #sync master has better bound error
                    #sync_operations.append((sync_src, sync_dst_id))
                    estimated_error[sync_dst_id] = cur_estimated_err[sync_src]
                    sim_err[sync_dst_id] = cur_sim_err[sync_src] + sim_hop_err


        for sync_dst in range(1,tor_num):
            estimated_error[sync_dst] += estimated_drift[sync_dst]
            sim_err[sync_dst] += sim_drift[sync_dst]
            #sim_err[sync_dst] += sim_drift[sync_dst] + random.uniform(-es_acc, es_acc)

            #actual_drift = sim_drift[sync_dst] + sim_drift[sync_dst] * random.gauss(0, es_acc / 4 / 100)
            #if abs(actual_drift) > 10:
            #    actual_drift /= 2
                
            #print(f"actual drift is {actual_drift}")
            #sim_drift[sync_dst] = actual_drift
            #sim_err[sync_dst] += actual_drift

            if circle != 0 and abs(max_estimated_err[sync_dst]) < abs(estimated_error[sync_dst]):
                max_estimated_err[sync_dst] = abs(estimated_error[sync_dst])

            if circle != 0 and abs(max_sim_err[sync_dst]) < abs(sim_err[sync_dst]):
                max_sim_err[sync_dst] = abs(sim_err[sync_dst])

        cur_estimated_err = estimated_error
        cur_sim_err = sim_err

        debug_print(cur_estimated_err)

        if circle != 0:
            all_estimated_err.append(cur_estimated_err)
            all_sim_err.append(cur_sim_err)
    
    sync_cnt_per_slice = sync_count / (len(optical_schedule) * sim_circle)
    return ((all_estimated_err, all_sim_err), sync_cnt_per_slice, sync_schedule, (max_estimated_err,max_sim_err))
    #return all_sim_err
    #return all_estimated_err


def sim_sync_err_flat(optical_schedule: np.ndarray, upper_link:int, hop_err:int, drift:int, es_acc:float, update_threshold:float) -> list[np.ndarray]:
    all_estimated_err = []
    all_sim_err = []
    #print(optical_schedule)
    tor_num = int(optical_schedule[0].shape[0] / upper_link)
    debug_print(f"There are {tor_num} nodes, {upper_link} upper link per tor, {len(optical_schedule)} time slices.")

    #inital error as inf
    cur_estimated_err = [drift * tor_num for _ in range(tor_num)]
    cur_estimated_err[0] = 0 
    cur_sim_err = [0 for _ in range(tor_num)]

    max_estimated_err = [0 for _ in range(tor_num)]
    max_sim_err = [0 for _ in range(tor_num)]


    sync_schedule = {_:[] for _ in range(tor_num)}


        #sim_drift.append(drift) # using max drift rate
    #print(f"real drift is {sim_drift}")
    #master has no dirft to itself
    
    sync_count = 0

    #simulate 10 schedules to converge

    for slice_id, sync_array in enumerate(list(optical_schedule) * sim_circle):
        #debug_print(sync_array)
        circle = int(slice_id/len(optical_schedule))
        cur_slice = slice_id%len(optical_schedule)
        if circle % porfile_gap == 0:
            estimated_drift, sim_drift = init_drift(tor_num, drift, es_acc)

        sync_candidates = {}
        sync_operations = []
        #go through every node to calculate sync error in this slice
        estimated_error = copy.deepcopy(cur_estimated_err)
        sim_err = copy.deepcopy(cur_sim_err)
        for sync_dst_id in range(tor_num):
            #for matrix representation
            sync_src_port = sync_array[sync_dst_id * upper_link : (sync_dst_id+1) * upper_link]
            connected_ports = sync_src_port

            if sync_dst_id == 0:
                #master tor
                continue
            
            if len(connected_ports) == 0:
                #no sync this slice
                debug_print(f"Error: No connected node for node {sync_dst_id}. There's something wrong in schedule.")
                return []

            else:
                for sync_dst in sync_array[0 : upper_link]:
                    if sync_dst == 0:
                        continue

                    sim_hop_err = random.gauss(0, hop_err/3)
                    if sim_hop_err > 0:
                        sim_hop_err = min(sim_hop_err, hop_err)
                    else:
                        sim_hop_err = max(sim_hop_err, -hop_err)
                        
                    sim_err[sync_dst_id] = cur_sim_err[0] + sim_hop_err


        for sync_dst in range(1,tor_num):
            estimated_error[sync_dst] += estimated_drift[sync_dst]
            sim_err[sync_dst] += sim_drift[sync_dst]

        cur_estimated_err = estimated_error
        cur_sim_err = sim_err

        debug_print(cur_estimated_err)

        if circle != 0:
            all_estimated_err.append(cur_estimated_err)
            all_sim_err.append(cur_sim_err)
    
    sync_cnt_per_slice = sync_count / (len(optical_schedule) * sim_circle)
    return ((all_estimated_err, all_sim_err), sync_cnt_per_slice, sync_schedule, (max_estimated_err,max_sim_err))
    #return all_sim_err
    #return all_estimated_err


def sim_sync_err_auto(optical_schedule: np.ndarray, upper_link:int, hop_err:int, drift:int, sync_algo:str, sync_limit:int) -> list[np.ndarray]:
    all_bound_err = []
    all_sim_err = []
    #print(optical_schedule)
    tor_num = int(optical_schedule[0].shape[0] / upper_link)
    debug_print(f"There are {tor_num} nodes, {upper_link} upper link per tor, {len(optical_schedule)} time slices.")
    cur_bound_err = [hop_err*1 for _ in range(tor_num)]
    cur_bound_err[0] = 0
    cur_sim_err = [0 for _ in range(tor_num)]

    max_err = [0 for _ in range(tor_num)]
    max_sim_err = [0 for _ in range(tor_num)]

    #tor_err = [0 for _ in range(tor_num)]
    #Record actual error
    tor_sim_err = []

    children_sync_schedule = {_:[] for _ in range(tor_num)}
    parent_sync_schedule = {_:[] for _ in range(tor_num)}

    sim_drift = []
    for _ in range(tor_num):
        real_drift = random.gauss(0, drift/4)
        if real_drift > 0:
            real_drift = min(real_drift, drift)
        else:
            real_drift = max(real_drift, -drift)

        sim_drift.append(real_drift)

    #master has no dirft to itself
    sim_drift[0] = 0
    sync_count = 0
    #drift_bound = 250

    #simulate 10 schedules to converge
    for slice_id, sync_array in enumerate(list(optical_schedule) * sim_circle):

        circle = int(slice_id/len(optical_schedule))
        cur_slice = slice_id%len(optical_schedule)
        if circle % porfile_gap == 0:
            estimated_drift, sim_drift = init_drift(tor_num, drift, es_acc = 0)

        #debug_print(sync_array)

        sync_candidates = {}
        #go through every node to calculate sync error in this slice
        for sync_dst_id in range(tor_num):
            #for matrix representation
            sync_src_port = sync_array[sync_dst_id * upper_link : (sync_dst_id+1) * upper_link]
            connected_ports = sync_src_port

            if sync_dst_id == 0:
                #master tor
                continue
            
            if len(connected_ports) == 0:
                #no sync this slice
                debug_print(f"Error: No connected node for node {sync_dst_id}. There's something wrong in schedule.")
                return []

            else:

                min_value = min([cur_bound_err[src] for src in connected_ports])
                sync_src = cur_bound_err.index(min_value)
                #print([bound_error[src] for src in connected_ports])
                #print(f"min value is {min_value}, min src = {sync_src}")
                    #min_sync_src = bound_error.index(min(bound_error[sync_src]))
                if (cur_bound_err[sync_dst_id] > cur_bound_err[sync_src] + hop_err):
                    #sync master has better bound error
                    
                    sync_benefit = cur_bound_err[sync_dst_id] - (cur_bound_err[sync_src] + hop_err)
                    if sync_benefit not in sync_candidates.keys():
                        sync_candidates[sync_benefit] = []
                    sync_candidates[sync_benefit].append((sync_src, sync_dst_id))

        if sync_algo == Sync_algo.only_with_master:
            sync_operations = only_to_master(sync_candidates.values())
        elif sync_algo == Sync_algo.most_improvement:
            sync_operations = most_benefit_operations(sync_candidates, sync_limit)
        elif sync_algo == Sync_algo.worst_err:
            sync_operations = worst_err_operations(sync_candidates, cur_bound_err, sync_limit)
        elif sync_algo == Sync_algo.as_many_as_possible:
            sync_operations = optimal_operations(sync_candidates)
        else:
            print(f"Invalid sync algo {sync_algo}, should be {Sync_algo.as_many_as_possible}")
            exit()
        sync_count += len(sync_operations)

        bound_error = copy.deepcopy(cur_bound_err)
        sim_err = copy.deepcopy(cur_sim_err)

        for sync_src, sync_dst in sync_operations:

            if circle == 10:
                children_sync_schedule[sync_dst].append(
                    (cur_slice,sync_src)
                    )
                
                parent_sync_schedule[sync_src].append(
                    (cur_slice,sync_dst)
                    )

            debug_print(f"slice {slice_id}, sync src {sync_src}, sync dst {sync_dst}")
            debug_print(f"before err {bound_error[sync_dst]}, after err {cur_bound_err[sync_src] + hop_err}")
            assert cur_bound_err[sync_dst] > cur_bound_err[sync_src] + hop_err
            bound_error[sync_dst] = cur_bound_err[sync_src] + hop_err

            sim_hop_err = random.gauss(0, hop_err/3)
            if sim_hop_err > 0:
                sim_hop_err = min(sim_hop_err, hop_err)
            else:
                sim_hop_err = max(sim_hop_err, -hop_err)

            sim_err[sync_dst] = cur_sim_err[sync_src] + sim_hop_err

        for sync_dst in range(1,tor_num):
            bound_error[sync_dst] += drift
            #bound_error[sync_dst] += drift_bound
            sim_err[sync_dst] += sim_drift[sync_dst]

            if circle != 0 and max_err[sync_dst] < bound_error[sync_dst]:
                max_err[sync_dst] = bound_error[sync_dst]

            if circle != 0 and max_sim_err[sync_dst] < sim_err[sync_dst]:
                max_sim_err[sync_dst] = sim_err[sync_dst]

        cur_bound_err = bound_error
        cur_sim_err = sim_err

        debug_print(cur_bound_err)
        if circle != 0:
            all_bound_err.append(cur_bound_err)
            all_sim_err.append(cur_sim_err)
        
    sync_cnt_per_slice = sync_count / (len(optical_schedule) * sim_circle)
    return ((all_bound_err, all_sim_err), sync_cnt_per_slice, (children_sync_schedule, parent_sync_schedule), (max_err,max_sim_err))
    #return all_sim_err
    #return all_bound_err

def testbed_gen_drift_schedule_bound(
        optical_schedule: np.ndarray, 
        upper_link:int, 
        hop_err:int, 
        drift_bound, 
        sim_drift,
        update_threshold:float) -> list[np.ndarray]:
    
    all_estimated_err = []
    all_sim_err = []
    #print(optical_schedule)
    tor_num = int(optical_schedule[0].shape[0] / upper_link)
    debug_print(f"There are {tor_num} nodes, {upper_link} upper link per tor, {len(optical_schedule)} time slices.")

    #inital error as inf
    cur_estimated_err = [hop_err * tor_num for _ in range(tor_num)]
    cur_estimated_err[0] = 0
    cur_sim_err = [0 for _ in range(tor_num)]


    #sync_schedule = {_:[] for _ in range(tor_num)}

    children_sync_schedule = {_:[] for _ in range(tor_num)}
    parent_sync_schedule = {_: {} for _ in range(tor_num)}
    backup_children_sync_schedule = {_:{} for _ in range(tor_num)}


    #sim_drift.append(drift) # using max drift rate
    #print(f"real drift is {sim_drift}")
    #master has no dirft to itself
    
    #simulate 10 schedules to converge

    for slice_id, sync_array in enumerate(list(optical_schedule) * sim_circle):
        #debug_print(sync_array)
        circle = int(slice_id/len(optical_schedule))
        cur_slice = slice_id%len(optical_schedule)

        #go through every node to calculate sync error in this slice
        estimated_error = copy.deepcopy(cur_estimated_err)
        sim_err = copy.deepcopy(cur_sim_err)
        for sync_dst_id in range(tor_num):
            #for matrix representation
            sync_src_port = sync_array[sync_dst_id * upper_link : (sync_dst_id+1) * upper_link]
            connected_ports = sync_src_port

            if sync_dst_id == 0:
                #master tor
                continue
            
            if len(connected_ports) == 0:
                #no sync this slice
                debug_print(f"Error: No connected node for node {sync_dst_id}. There's something wrong in schedule.")
                assert 0, "len(connected_ports) == 0"
                return []

            else:
                
                error_candidates = []
                for src in connected_ports:
                    #[0] is abs of error, [1] is the tor id.
                    error_candidates.append((abs(cur_estimated_err[src]), src))
                
                sorted_errors = sorted(error_candidates, key = lambda tup:(tup[0],tup[1]))

                #print(sorted_errors)
                min_error = sorted_errors[0][0]
                sync_src = sorted_errors[0][1]

                backup_error = sorted_errors[1][0]
                backup_src = sorted_errors[1][1]

                if 0 in connected_ports:
                    #print(connected_ports)
                    #print(cur_estimated_err[0], cur_estimated_err[sync_src])
                    #print(sync_src)
                    if sync_src != 0:
                        backup_src = sync_src
                        sync_src = 0
                    #assert sync_src == 0

                sim_hop_err = random.gauss(0, hop_err/3)
                if sim_hop_err > 0:
                    sim_hop_err = min(sim_hop_err, hop_err)
                else:
                    sim_hop_err = max(sim_hop_err, -hop_err)

                if (abs(cur_estimated_err[sync_dst_id]) > abs(cur_estimated_err[sync_src]) + hop_err
                    or sync_src == 0):
                    #sync master has better bound error
                    #parent_sync_schedule[sync_src].add((cur_slice, sync_dst_id))
                    #print(f"Add op master {sync_src} slice {cur_slice} dst {sync_dst_id}")

                    if circle != 0:
                        if cur_slice not in parent_sync_schedule[sync_src].keys():
                            parent_sync_schedule[sync_src][cur_slice] = set()

                        parent_sync_schedule[sync_src][cur_slice].add(sync_dst_id)
                    

                    estimated_error[sync_dst_id] = cur_estimated_err[sync_src]
                    sim_err[sync_dst_id] = cur_sim_err[sync_src] + sim_hop_err

                if (abs(cur_estimated_err[sync_dst_id]) > abs(cur_estimated_err[backup_src]) + hop_err):
                    if circle != 0:
                        if cur_slice not in backup_children_sync_schedule[sync_dst_id].keys():
                            backup_children_sync_schedule[sync_dst_id][cur_slice] = -1
                        backup_children_sync_schedule[sync_dst_id][cur_slice] = backup_src

        for sync_dst in range(1,tor_num):
            #estimated_error[sync_dst] += estimated_drift[sync_dst]
            estimated_error[sync_dst] += drift_bound
            sim_err[sync_dst] += sim_drift[sync_dst]

        cur_estimated_err = estimated_error
        cur_sim_err = sim_err

        debug_print(cur_estimated_err)

        if circle != 0:
            all_estimated_err.append(cur_estimated_err)
            all_sim_err.append(cur_sim_err)
    
    #for src in parent_sync_schedule.keys():
    #    parent_sync_schedule[src] = sorted(parent_sync_schedule[src])

    return parent_sync_schedule, backup_children_sync_schedule


def testbed_gen_drift_schedule_estimated_drift(
        optical_schedule: np.ndarray, 
        upper_link:int, 
        hop_err:int, 
        estimated_drift, 
        sim_drift,
        update_threshold:float) -> list[np.ndarray]:
    
    all_estimated_err = []
    all_sim_err = []
    #print(optical_schedule)
    tor_num = int(optical_schedule[0].shape[0] / upper_link)
    debug_print(f"There are {tor_num} nodes, {upper_link} upper link per tor, {len(optical_schedule)} time slices.")

    #inital error as inf
    cur_estimated_err = [hop_err * tor_num for _ in range(tor_num)]
    cur_estimated_err[0] = 0
    cur_sim_err = [0 for _ in range(tor_num)]

    #measure hop count
    clk_hop_tracker = [0 for _ in range(tor_num)]
    hop_count_dict = {_:0 for _ in range(15)}


    #sync_schedule = {_:[] for _ in range(tor_num)}

    children_sync_schedule = {_:[] for _ in range(tor_num)}
    parent_sync_schedule = {_: {} for _ in range(tor_num)}
    backup_children_sync_schedule = {_:{} for _ in range(tor_num)}


    #sim_drift.append(drift) # using max drift rate
    #print(f"real drift is {sim_drift}")
    #master has no dirft to itself
    
    #simulate 10 schedules to converge

    sync_count = {_: 0 for _ in range(sim_circle)}

    for slice_id, sync_array in enumerate(list(optical_schedule) * sim_circle):
        #debug_print(sync_array)
        circle = int(slice_id/len(optical_schedule))
        cur_slice = slice_id%len(optical_schedule)

        #go through every node to calculate sync error in this slice
        estimated_error = copy.deepcopy(cur_estimated_err)
        sim_err = copy.deepcopy(cur_sim_err)

        for sync_dst_id in range(tor_num):
            #for matrix representation
            sync_src_port = sync_array[sync_dst_id * upper_link : (sync_dst_id+1) * upper_link]
            connected_ports = sync_src_port

            if sync_dst_id == 0:
                #master tor
                continue
            
            if len(connected_ports) == 0:
                #no sync this slice
                debug_print(f"Error: No connected node for node {sync_dst_id}. There's something wrong in schedule.")
                assert 0, "len(connected_ports) == 0"
                return []

            else:
                
                error_candidates = []
                for src in connected_ports:
                    #[0] is abs of error, [1] is the tor id.
                    error_candidates.append((abs(cur_estimated_err[src]), src))
                
                sorted_errors = sorted(error_candidates, key = lambda tup:(tup[0],tup[1]))

                #print(sorted_errors)
                min_error = sorted_errors[0][0]
                sync_src = sorted_errors[0][1]

                backup_error = sorted_errors[1][0]
                backup_src = sorted_errors[1][1]

                if 0 in connected_ports:
                    #print(connected_ports)
                    #print(cur_estimated_err[0], cur_estimated_err[sync_src])
                    #print(sync_src)
                    if sync_src != 0:
                        backup_src = sync_src
                        sync_src = 0
                    #assert sync_src == 0

                sim_hop_err = random.gauss(0, hop_err/3)
                if sim_hop_err > 0:
                    sim_hop_err = min(sim_hop_err, hop_err)
                else:
                    sim_hop_err = max(sim_hop_err, -hop_err)

                assert clk_hop_tracker[0] == 0
                assert hop_count_dict[0] == 0

                if (abs(cur_estimated_err[sync_dst_id]) > abs(cur_estimated_err[sync_src]) + update_threshold
                    or sync_src == 0):
                    #sync master has better bound error
                    #parent_sync_schedule[sync_src].add((cur_slice, sync_dst_id))
                    #print(f"Add op master {sync_src} slice {cur_slice} dst {sync_dst_id}")

                    clk_hop_tracker[sync_dst_id] = clk_hop_tracker[sync_src] + 1
                    hop_count_dict[clk_hop_tracker[sync_dst_id]] += 1


                    if circle != 0:
                        if cur_slice not in parent_sync_schedule[sync_src].keys():
                            parent_sync_schedule[sync_src][cur_slice] = set()
                        
                        sync_count[circle] += 1
                        parent_sync_schedule[sync_src][cur_slice].add(sync_dst_id)
                    

                    estimated_error[sync_dst_id] = cur_estimated_err[sync_src]
                    sim_err[sync_dst_id] = cur_sim_err[sync_src] + sim_hop_err

                if (abs(cur_estimated_err[sync_dst_id]) > abs(cur_estimated_err[backup_src]) + update_threshold):
                    if circle != 0:
                        if cur_slice not in backup_children_sync_schedule[sync_dst_id].keys():
                            backup_children_sync_schedule[sync_dst_id][cur_slice] = -1
                        backup_children_sync_schedule[sync_dst_id][cur_slice] = backup_src

        
        for sync_dst in range(1,tor_num):
            estimated_error[sync_dst] += estimated_drift[sync_dst]
            sim_err[sync_dst] += sim_drift[sync_dst]

        cur_estimated_err = estimated_error
        cur_sim_err = sim_err

        debug_print(cur_estimated_err)

        if circle != 0:
            all_estimated_err.append(cur_estimated_err)
            all_sim_err.append(cur_sim_err)
    
    for item in sync_count.items():
        op_count = item[1]
        #print(f"Circle {item[0]}, sync count: {item[1]}")
    #for src in parent_sync_schedule.keys():
    #    parent_sync_schedule[src] = sorted(parent_sync_schedule[src])

    return parent_sync_schedule, backup_children_sync_schedule, op_count, hop_count_dict

def testbed_gen_drift_flat_schedules(
        optical_schedule: np.ndarray, 
        upper_link:int, 
        hop_err:int, 
        estimated_drift, 
        sim_drift,
        update_threshold:float) -> list[np.ndarray]:
    
    all_estimated_err = []
    all_sim_err = []
    #print(optical_schedule)
    tor_num = int(optical_schedule[0].shape[0] / upper_link)
    debug_print(f"There are {tor_num} nodes, {upper_link} upper link per tor, {len(optical_schedule)} time slices.")

    #sync_schedule = {_:[] for _ in range(tor_num)}

    parent_sync_schedule = {_:{} for _ in range(tor_num)}


    #sim_drift.append(drift) # using max drift rate
    #print(f"real drift is {sim_drift}")
    #master has no dirft to itself
    
    #simulate 10 schedules to converge

    for slice_id, sync_array in enumerate(list(optical_schedule)):
        #debug_print(sync_array)
        circle = int(slice_id/len(optical_schedule))
        cur_slice = slice_id%len(optical_schedule)

        print(f"Slice {slice_id} add {sync_array[0 : upper_link]}")
        for sync_dst in sync_array[0 : upper_link]:
            if sync_dst == 0:
                continue
            if slice_id not in parent_sync_schedule[0].keys():
                parent_sync_schedule[0][slice_id] = set()
            parent_sync_schedule[0][slice_id].add(sync_dst)


    #for src in parent_sync_schedule.keys():
    #    parent_sync_schedule[src] = sorted(parent_sync_schedule[src])

    return sim_drift, parent_sync_schedule

def process_sync_schedule(children_sync_schedule : dict, parent_sync_schedule : dict):

    #print(parent_sync_schedule)
    
    leaf_tor_set = set()

    for dst_tor, operations in parent_sync_schedule.items():
        print(operations)
        if len(operations) == 0:
            leaf_tor_set.add(dst_tor)
    print(f"leaves: {leaf_tor_set}")

    #leaf_tor_set = set(list(range(len(parent_sync_schedule))))
    #return
    group_list = []
    sync_list = []

    group_operations = {}
    for leaf in leaf_tor_set:

        group_operations[leaf] = set()
        synced_tors = set([leaf])

        last_len = -1
        now_len = len(synced_tors)
        while last_len != now_len: #new nodes added.
            #print(children_sync_schedule[leaf])
            #print(f"Current group is {group_operations[leaf]}")

            candidates = []
            for dst_tor in synced_tors:
                for slice_id, sync_src in children_sync_schedule[dst_tor]:
                    #print(f"src {sync_src}, dst {dst_tor}, slice {slice_id}")
                    candidates.append((sync_src, dst_tor, slice_id))

            for sync_src, dst_tor, slice_id in candidates:
                synced_tors.add(sync_src)
                group_operations[leaf].add((sync_src, dst_tor, slice_id))

            last_len = now_len
            now_len = len(synced_tors)
            #print(f"last_len {last_len}, now_len {now_len}")

        group_list.append(synced_tors)
        #sync_list.append(sorted(group_operations[leaf]))
    
    #for group in group_list:
        #print(group)
    #for operation in group_operations:
        #print(operation)

    #print(group_operations.keys())

    vis_schedule(group_operations)
    #vis_schedule_whole_graph(parent_sync_schedule)

    save_sync_schedule(group_operations)



leaf =27

def vis_schedule(sync_operations) :
    g = nx.DiGraph()

    nodes = set([leaf])
    operations = sorted(sync_operations[leaf])
    print(operations)
    for dst_tor, sync_src, slice_id in operations:
        nodes.add(sync_src)
        g.add_edge(dst_tor, sync_src,time_slice = slice_id)
    
    nx.draw_networkx(g)
    print(f"Leaf {leaf}")
    print(f"node: {nodes}, {len(nodes)}")

    
    pos = nx.spring_layout(g, seed=7)  # positions for all nodes - seed for reproducibility
    """
    # node labels
    nx.draw_networkx_labels(g, pos, font_size=5, font_family="sans-serif")
    # edge weight labels
    edge_labels = nx.get_edge_attributes(g, "weight")
    nx.draw_networkx_edge_labels(g, pos, edge_labels)
    """
    plt.show()

def vis_schedule_whole_graph(parent_sync_dict) :
    g = nx.DiGraph()

    for src_tor, syncs in parent_sync_dict.items():
        for slice_id, sync_dst in syncs:
            g.add_edge(src_tor, sync_dst, time_slice = slice_id)
    
    nx.draw_networkx(g)
    plt.show()

def vis_schedule_whole_schedule(parent_sync_dict) :
    g = nx.DiGraph()

    for src_tor, syncs in parent_sync_dict.items():
        for slice_id, sync_dsts in syncs.items():
            for dst in sync_dsts:
                g.add_edge(src_tor, dst, time_slice = slice_id)
    
    nx.draw_networkx(g)

    print(f"There are {len(g.nodes())} nodes.")
    plt.show()

def save_sync_schedule(sync_operations):

    parent_schedule = {}
    nodes = set([leaf])
    operations = sorted(sync_operations[leaf])
    #print(operations)
    for sync_src, dst_tor, slice_id in operations:
        if sync_src not in parent_schedule.keys():
            parent_schedule[sync_src] = []
        parent_schedule[sync_src].append((sync_src, dst_tor, slice_id))
    
    for item in parent_schedule.items():
        print(item)


linestyle_list = ["-","-","-.",":"]
color_group = ["Oranges","binary","Blues","spring"]
def draw_sync_report(multiple_sync_count, label:str, tor_num, upper_link):

    def draw_line(sync_count, label, group_id, cmap_id):

        sync_count = np.array(sync_count)
        tor_num = len(sync_count)

        #max_error = sync_count.T[0]
        #sync_count = sync_count.T[1]
        max_error = sync_count

        #print(f"max error {max_error}")
        
        cnt, b_cnt = np.histogram(max_error, bins=10000)
        pdf = cnt/sum(cnt)
        cdf = np.cumsum(pdf)
        #l, = plt.plot(b_cnt[1:], pdf, label = label, color = color_list[id], linestyle = linestyle_list[id])
        l, = plt.plot(b_cnt[1:], cdf, label = label,
                    color = plt.get_cmap(color_group[group_id])(0.5+cmap_id),
                    linestyle = linestyle_list[group_id],
                    linewidth=2.0)
    
    for group_id in range(len(multiple_sync_count)):
        for id in range(len(multiple_sync_count[group_id])):
            cmap_id = id/len(multiple_sync_count[group_id])/2
            draw_line(multiple_sync_count[group_id][id], label[group_id][id], group_id, cmap_id)


    plt.legend()
    plt.xlabel("Max Sync Error")
    plt.ylabel("CDF")
    plt.title(f"{tor_num} ToRs, {upper_link} upper links")
    plt.show()
    #plt.savefig(f"schedule_design/{tor_num}tor{upper_link}ports.pdf")

def draw_err(sync_errs):
    col = 1
    #fig, axs = plt.subplots(col, int(len(sync_errs)/col))
    fig, axs = plt.subplots(2)
    #subfig = []
    #subfig = axs

    #for x in range(1):
    #    subfig.append(axs[x])
    #for x in range(col):
    #    for y in range(int(len(sync_errs)/col)):
    #        subfig.append(axs[x][y])

    '''
    for id, err in enumerate(sync_errs):
        err = np.array(err)
        tor_num = len(err[0])
        for tor_id in range(tor_num):
            tor_err = err[:,tor_id]
            self.debug_print(tor_err)
            subfig[id].plot(range(len(tor_err)), tor_err, label = tor_id)
        subfig[id].legend()
    '''
    
    def draw_one(sync_errs, subfig, label):
        #for id, err in enumerate(sync_errs):
        err = np.array(sync_errs)
        tor_num = len(err[0])
        for tor_id in range(tor_num):
            tor_err = err[:,tor_id]
            #self.debug_print(tor_err)
            #subfig.plot(range(len(tor_err)), tor_err, label = f"ToR{tor_id} {label}")
            subfig.scatter(range(len(tor_err)), tor_err, label = f"ToR{tor_id} {label}", s = 5)
        #subfig.legend()
        subfig.title.set_text(label)
    #sync_errs = sync_errs[0]
    fig.supylabel("Sync Error (ns)", fontsize = 22)
    fig.supxlabel("slice", fontsize = 22)
    debug_print(len(sync_errs))
    draw_one(sync_errs[0], axs[0], "bound")
    draw_one(sync_errs[1], axs[1], "sim")
    plt.show()