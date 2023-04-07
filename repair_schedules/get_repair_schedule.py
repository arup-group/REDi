import numpy as np
from typing import List, Dict, Any

from building import Building, ComponentsLibrary
from utils.stat_utils import sample_dist, deepArray2matrix
from repair_schedules.scheduling_optimization.get_optimized_repair_schedule import get_optimized_repair_schedule_diff_start

def get_repair_schedule(building : Building,
                        components_lib : ComponentsLibrary, 
                        struc_repair_days : np.ndarray,
                        nonstruct_contractor_delays : np.ndarray,
                        max_workers : float) -> List[Dict[str,Any]] :
    
    n_non_struc_sequence =  building.n_non_struc_sequence
    n_repair_goal = building.n_repair_goal
    n_sequence = building.n_sequences

    # Get the total number of floors
    nTotalFloor = building.nTotalFloor
    max_delay = building.max_delay
    damage_qty = building.damage_by_component_all_DS
    repair_sequence_by_floor = building.repair_sequence_by_floor
    floor_areas = building.floor_areas       
                        
    # capacity: [nRealization x [ n_non_struc_sequence]]
    capacity = get_worker_capacity(building=building,
                                   components_lib=components_lib,
                                   floor_areas=floor_areas, 
                                   damage_qty=damage_qty, 
                                   nTotalFloor=nTotalFloor,
                                   n_non_struc_sequence=n_non_struc_sequence)
    

    # [nRealization x [ n_non_struc_sequence]]
    constraint = get_constrained_workers(building=building)
    
    return get_repair_schedule_unit_realization(delay=max_delay, 
                                                struc_repair_days=struc_repair_days, 
                                                nonstruct_contractor_delays=nonstruct_contractor_delays, 
                                                sequence_demand=repair_sequence_by_floor, 
                                                capacity=capacity, 
                                                nWorker=max_workers,
                                                nTotalFloor=nTotalFloor, 
                                                constraint=constraint,
                                                n_non_struc_sequence=n_non_struc_sequence,
                                                n_repair_goal=n_repair_goal,
                                                n_sequence=n_sequence)


def get_repair_schedule_unit_realization(delay : List[float],
                                         struc_repair_days : np.ndarray,
                                         nonstruct_contractor_delays : np.ndarray,
                                         sequence_demand : np.ndarray[float],
                                         capacity : np.ndarray,
                                         nWorker : float,
                                         nTotalFloor : int,
                                         constraint : np.ndarray,
                                         n_non_struc_sequence : int,
                                         n_repair_goal : int,
                                         n_sequence : int) -> List[Dict[str,Any]]:
                                             
    sequence_demand_by_goal = np.zeros((n_repair_goal,nTotalFloor,n_sequence-1))
    for goal in range(n_repair_goal) :
        for floor in range(nTotalFloor) :
            for seq in range(1, n_sequence) :
                sequence_demand_by_goal[goal][floor][seq-1] = sequence_demand[floor][seq][goal]
    
    list_demand_seq = [deepArray2matrix(demand, nTotalFloor, n_non_struc_sequence) for demand in sequence_demand_by_goal]
    sequence_demand_by_goal_matrixed = np.stack(list_demand_seq)

    struct_days = [delay[0]+days for days in struc_repair_days]
    

    res = []
    for i in range(n_repair_goal) :

        seq_dem = sequence_demand_by_goal_matrixed[i]
        struct_d =  struct_days[i]
        struc_repair_d = struc_repair_days[i]
        unit_goal =  get_repair_schedule_unit_goal(nonstructural_delays=nonstruct_contractor_delays,
                                                   sequence_demand_by_goal_matrixed=seq_dem,
                                                   capacity=capacity,
                                                   nTotalFloor=nTotalFloor,
                                                   nWorker=nWorker,
                                                   struct_days=struct_d,
                                                   constraint=constraint,
                                                   struc_repair_days=struc_repair_d,
                                                   n_non_struc_sequence=n_non_struc_sequence)
                                  
    
        res.append(unit_goal)
    
    return res


def get_repair_schedule_unit_goal(nonstructural_delays :np.ndarray,
                                  sequence_demand_by_goal_matrixed : np.ndarray,
                                  capacity : np.ndarray,
                                  nTotalFloor : int,
                                  nWorker : float,
                                  struct_days : float,
                                  constraint : np.ndarray,
                                  struc_repair_days : float,
                                  n_non_struc_sequence : int) -> Dict[str,Any] :
                                  
    # seq_with_demand = [i+1 for i in range(len(sequence_demand_by_goal_matrixed)) if any([sequence_demand_by_goal_matrixed[i][j][k] > 0 for j in range(1, n_non_struc_sequence) for k in range(nTotalFloor)])]
    # seq_with_demand =  np.where(sequence_demand_by_goal_matrixed > 0)[0]
    # seq_with_demand  = [x for row in sequence_demand_by_goal_matrixed for x in row if x > 0]

    seq_with_demand = []
    for i in range(len(sequence_demand_by_goal_matrixed)) :
        row = sequence_demand_by_goal_matrixed[i]
        for j in range(len(row)) :
            val = row[j]
            if val > 0 :
                seq_with_demand.append((i,j))

    
    capacity = adjust_capacity(capacity=capacity, 
                               nTotalFloor=nTotalFloor,
                               constraint=constraint,
                               n_non_struc_sequence=n_non_struc_sequence)
        

    if len(seq_with_demand) == 0:
        return {"total_span": 0, "span_by_seq": reshape_by_floor([0 for i in range(nTotalFloor*n_non_struc_sequence)],nTotalFloor), "allocation": {}, "ends":[], "starts":[], "struct_repairs": struc_repair_days, "ready": nonstructural_delays}
        
    # sequences_exceeding_struct = [i for i in range(len(nonstructural_delays)) if nonstructural_delays[i] > struct_days]
    sequences_exceeding_struct = []
    for i in range(len(nonstructural_delays)):
        if nonstructural_delays[i] > struct_days:
            sequences_exceeding_struct.append(i)
        
    ready_per_floor = [struct_days] * n_non_struc_sequence
    
    for seq in sequences_exceeding_struct:
        ready_per_floor[seq] = nonstructural_delays[seq]
        
    ready = np.array([ready_per_floor[:] for i in range(nTotalFloor)])
    
    ready = deepArray2matrix(ready, nTotalFloor, n_non_struc_sequence)
    
    return get_optimized_repair_schedule_diff_start(demand=sequence_demand_by_goal_matrixed,
                                                    capacity=capacity,
                                                    nFloor=nTotalFloor,
                                                    nWorker=nWorker,
                                                    ready=ready,
                                                    struc_repair_days=struc_repair_days,
                                                    n_non_struc_sequence=n_non_struc_sequence,
                                                    now=struct_days)
        

def adjust_capacity(capacity : np.ndarray, 
                    nTotalFloor : int, 
                    constraint : np.ndarray,
                    n_non_struc_sequence : int) -> np.ndarray :
    
    # Loop over all sequences
    for seq in range(n_non_struc_sequence) :

        # Initialize the floors that have worker demand
        floors_w_demand = []

        # Initialize the total worker demand for this sequence
        worker_demand = 0.0

        # Loop over all floors
        for floor_index in range(nTotalFloor) :

            # If the floor has worker demand
            if capacity[floor_index][seq] > 0.0:
                
                # Add to the floors with demand
                floors_w_demand.append(floor_index)

                # Add to the total worker demand
                worker_demand += capacity[floor_index][seq]

        # If the total worker demand is larger than the building-level constraint...
        if worker_demand > constraint[seq] :

            # Calculate new worker capacity per floor
            new_capacity_per_floor = constraint[seq] / float(len(floors_w_demand))

            # Assign new capacity per floor to each floor with demand
            for floor_index in floors_w_demand:

                capacity[floor_index][seq] = new_capacity_per_floor
                
    # Need to store as matrix in order for synchronous_alloc to work
    return deepArray2matrix(capacity, nTotalFloor, n_non_struc_sequence)


def get_worker_capacity(building : Building, 
                        components_lib : ComponentsLibrary,
                        floor_areas : List[float], 
                        damage_qty : Dict[str, Any], 
                        nTotalFloor : int,
                        n_non_struc_sequence : int) -> np.ndarray :

    recommended = get_recommended_workers(building=building, 
                                          components_lib=components_lib,
                                          floor_areas=floor_areas, 
                                          damage_qty=damage_qty, 
                                          nTotalFloor=nTotalFloor,
                                          n_non_struc_sequence=n_non_struc_sequence)

    return recommended


def get_recommended_workers(building : Building, 
                            components_lib : ComponentsLibrary, 
                            floor_areas : List[float], 
                            damage_qty : Dict[str,Any], 
                            nTotalFloor : int,
                            n_non_struc_sequence : int) -> np.ndarray :

    # Get data from risk parameters    
    nwork_perfloor_divider = building.nwork_perfloor_divider
    recommended_workers_floor_area = [np.zeros(n_non_struc_sequence) for _ in range(nTotalFloor)]
    for floor in range(nTotalFloor) :
        for seq in range(n_non_struc_sequence) :
            recommended_workers_floor_area[floor][seq] = floor_areas[floor] / nwork_perfloor_divider[seq] 
    
    # Get the risk parameters
    nworkers_recommended_mean = building.nworkers_recommended_mean
    recommended_workers_per_comp = [nworkers_recommended_mean[seq] for seq in range(n_non_struc_sequence)]
    recommended_workers_distribution = building.recommended_workers_distribution
    recommended_workers_beta = building.recommended_workers_beta

    # Initialize result (total number of workers based on the number of damaged components)
    recommended_workers_damaged_comp = [np.zeros(n_non_struc_sequence) for _ in range(nTotalFloor)]

    # Loop over all components to get damaged quantity in each sequence
    for  NISTR, damage in damage_qty.items():

        # Get the sequence from the component
        seq = components_lib[NISTR]["seq"][0]

        # Only proceed if a nonstructural component (i.e. seq > 0)
        if seq > 0:

            # Add workers to each floor based on the number of damaged components
            for floor in range(nTotalFloor):
                recommended_workers_damaged_comp[floor-1][seq-1] += recommended_workers_per_comp[seq-1] * damage[floor-1]

    # Finalize the mean recommended workers in each sequence as the minimum of the floor area estimate and the damaged components estimate
    recommended_workers_mean_nonstruct = [np.zeros(n_non_struc_sequence) for _ in range(nTotalFloor)]
    for floor in range(nTotalFloor) :
        for seq in range(n_non_struc_sequence) :
            recommended_workers_mean_nonstruct[floor][seq] = min(recommended_workers_floor_area[floor][seq], recommended_workers_damaged_comp[floor][seq])
    
    recommended_workers = np.array([np.zeros(n_non_struc_sequence) for _ in range(nTotalFloor)])
    for floor in range(nTotalFloor) :
        for seq in range(n_non_struc_sequence) :
            var1 = recommended_workers_mean_nonstruct[floor][seq]
            var2 = recommended_workers_beta
            sample = sample_dist(recommended_workers_distribution, var1, var2)
            recommended_workers[floor][seq] =sample


    # return recommended_wodrkers
    return recommended_workers


def get_worker_constraint_mean(building : Building) -> List[int]:
    
    nTotalFloor = building.nTotalFloor

    # Get height index (0 if < 5 floors; 1 if 5-20 floors; 2 if 20+ floors)
    if nTotalFloor <= 5 :
        height_index = 0 
    elif nTotalFloor <= 20 :
        height_index = 1
    else :
        height_index = 2

    return building.max_workers_by_sequence[height_index]


def get_constrained_workers(building : Building) -> np.ndarray :
    
    mean = get_worker_constraint_mean(building=building)

    # Get risk parameters
    distribution = building.workers_cap_distribution
    beta = building.workers_cap_beta

    return np.array([sample_dist(distribution, m, beta) for m in mean])


def reshape_by_floor(lst, n_floor) :

    n = len(lst)
    n_cols = n // n_floor

    return np.reshape(lst[:n_floor*n_cols], (n_floor, n_cols))
