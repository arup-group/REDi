import json, os, sys

file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)

from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np

from utils.stat_utils import set_seed, sample_dist, get_percentile, gen_random
from building import Building, ComponentsLibrary
from impeding_delays import get_impeding_delays
from repair_schedules.get_repair_schedule import get_repair_schedule

components_lib=None

def go_redi(building_dict : dict, 
            components_lib_dict : Optional[dict]=None, 
            seed=None, 
            burn_in=None) :

    if seed or burn_in : 
        set_seed(seed, burn_in) 

    global components_lib

    if not components_lib_dict and not components_lib :
        print("Loading components\n")

        # Get the directory of the current script
        current_dir = Path(__file__).resolve().parent
        filepath =current_dir/'data/components_library.json'

        # open the JSON file
        f = open(filepath)
        components_lib_dict = json.load(f)
        f.close()
        components_lib = ComponentsLibrary(components_lib_dict=components_lib_dict)
        
    elif components_lib_dict and not components_lib :
        components_lib = ComponentsLibrary(components_lib_dict=components_lib_dict) 

    print(f"******* Running REDi™ for building {building_dict['_id']} *******\n")

    building = Building(building_dict=building_dict)
    
    # Get the total number of floors
    nTotalFloor = building.nTotalFloor

    # Get the total floor area 
    building.total_floor_area = np.sum(building.floor_areas)

    # Get the component damage states
    comp_damage = building.damage_by_component

    # Get the damage by component_all_floors
    building.damage_by_component_all_floors = get_damage_by_component_all_floors(comp_damage)

    # Re-organize damage states
    building.damage_by_component_all_DS = get_damage_by_component_all_DS(comp_damage, nTotalFloor)

    # Calculate parameters before repair scheduling
    pre_calc = calculate_before_scheduling(building=building,components_lib=components_lib)

    # Calculate repair schedule (function in get_repair_schedule.jl)
    repair_schedule = get_repair_schedule(building=building,
                                          components_lib=components_lib,
                                          struc_repair_days=pre_calc["struc_repair_days"], 
                                          nonstruct_contractor_delays=pre_calc["nonstruct_contractor_delays"],
                                          max_workers=pre_calc["max_workers"])
    

    building.repair_schedule = repair_schedule
    n_repair_goal = building.n_repair_goal
    
    # Get total downtime, including delays and repair time
    building_total_downtime = process_downtime(repair_schedule, 
                                               building.max_delay, 
                                               pre_calc["struc_repair_days"],
                                               n_repair_goal=n_repair_goal)

    # If repair time exceeds replacement time, assign replacement time
    building_total_downtime = np.minimum(building_total_downtime, building.replacement_time)

    building.building_total_downtime = building_total_downtime

    return output_results(building=building)



def get_damage_by_component_all_floors(component_damage : Dict[str,List[List[float]]]) : 

    damage_by_component_all_floors = {}

    for NISTR, DS_by_floor in component_damage.items():

        num_ds = len(DS_by_floor)

        floor_sums = np.zeros(num_ds-1)
        for floor in range(1, num_ds) : 
            floor_ds = DS_by_floor[floor]
            sum_floor = np.sum(floor_ds)
            floor_sums[floor-1] = sum_floor

        damage_by_component_all_floors[NISTR] = floor_sums

    return damage_by_component_all_floors



def get_damage_by_component_all_DS(component_damage : Dict[str,List[List[float]]], 
                                   nTotalFloor : int):
    
    DS_by_component_all_DS = {}
    
    for NISTR, DS_by_floor in component_damage.items():

        DS_by_floor_t = list(zip(*DS_by_floor))

        # compObj = components_lib[NISTR]
        # n_ds = compObj["n_ds"]

        sum_ds = []

        for floor in range(0, nTotalFloor) : 
            floor_ds = DS_by_floor_t[floor][1:]
            sum_ds.append(np.sum(floor_ds) )
         
        DS_by_component_all_DS[NISTR] = sum_ds

    return DS_by_component_all_DS



def calculate_before_scheduling(building : Building, 
                                components_lib : ComponentsLibrary) :
    
    # Get the total floor 
    nTotalFloor = building.nTotalFloor

    # Get total quantity of every component across the entire building
    component_qty = get_component_qty_all_floor(building.components)
    building.component_qty = component_qty

    # assign repair class
    repair_class = assign_repair_class(building=building,components_lib=components_lib)
    building.repair_class = repair_class

    # Get the total building cost
    total_cost = building.total_consequences

    # Get consequence by component by component by floor
    consequence_by_component_by_floor = get_consequence_by_component_by_floor(total_cost)
    building.consequence_by_component_by_floor = consequence_by_component_by_floor
    
    n_sequences = building.n_sequences
    n_repair_goal = building.n_repair_goal

    # Get repair sequence by floor
    repair_sequence_by_floor = get_repair_sequence_by_floor(repair_class_by_component=repair_class, 
                                                            consequence_by_component_by_floor=building.consequence_by_component_by_floor, 
                                                            nTotalFloor=nTotalFloor,
                                                            components_lib=components_lib,
                                                            n_sequences=n_sequences,
                                                            n_repair_goal=n_repair_goal)
    
    building.repair_sequence_by_floor = repair_sequence_by_floor
          
    # Get the global repair sequence by floor
    repair_sequence = get_repair_sequence(repair_sequence_by_floor=repair_sequence_by_floor, 
                                          nTotalFloor=nTotalFloor,
                                          n_sequences=n_sequences,
                                          n_repair_goal=n_repair_goal)
    
    building.repair_sequence = repair_sequence

    # Get impeding delays (function in impeding_delays.jl)
    max_delay, impeding_delays = get_impeding_delays(building=building, 
                                                     components_lib=components_lib,
                                                     repair_sequence=repair_sequence, 
                                                     component_qty=component_qty)

    # Store impeding delays and max delay
    building.impeding_delays = impeding_delays
    building.max_delay = [max_delay]

    # Get structural and nonstructural delays
    max_workers = get_max_workers(building=building)
    struc_workers = get_struct_workers(building=building)
    struc_repair_time = repair_sequence[0]
    struc_repair_days = get_structural_repair_time(building=building, 
                                                   max_workers=max_workers, 
                                                   struc_workers=struc_workers, 
                                                   struc_repair=struc_repair_time, 
                                                   nTotalFloor=nTotalFloor,
                                                   components_lib=components_lib)
                                                   
    n_repair_goal = building.n_repair_goal
    struct_downtime = [struc_repair_days[goal]+max_delay for goal in range(n_repair_goal)]

    return {
            "max_workers": max_workers,
            "struc_repair_days": struc_repair_days,
            "nonstruct_contractor_delays": impeding_delays["nonstruct_contractor_mobilization_delays"],
            "struct_downtime": struct_downtime
            }



def get_component_qty_all_floor(components_by_floor : List[Dict[str,Any]]):
    # Initialize result
    component_qty = {}
    
    # Loop over every floor
    for floor_index in range(len(components_by_floor)):
        for component in components_by_floor[floor_index]:
            # Get component data
            nistr = component["NISTR"]
            qty = component["Qty"]
            
            # If NISTR isn't already in dictionary, add it and initialize with zero
            if nistr not in component_qty:
                component_qty[nistr] = 0.0
            
            # Add quantity of component to entry in dictionary
            component_qty[nistr] += sum(qty)
    
    return component_qty



def assign_repair_class(building : Building, 
                        components_lib : ComponentsLibrary):
    
    damage = building.damage_by_component_all_floors

    component_qty = building.component_qty

    # Initialize result
    repair_class_by_component = {}

    # Extract repair class risk parameters
    distribution_rc = building.distribution_rc
    theta_rc = building.theta_rc
    beta_rc = building.beta_rc

    for NISTR, comp_damage in damage.items():
        
        # Get component data
        compObj = components_lib[NISTR]
        rds = compObj["rds"]

        # print('NISTR',NISTR)

        # Extract first realization (TODO: Edit this once realizations are removed)
        comp_damage = [comp_damage[0]]

        # print('comp_damage',comp_damage)
 
        # Identify the index of the maximum damage state
        DS_max_index = next((i for i in reversed(range(len(comp_damage))) if comp_damage[i] > 0), None)

        # print('DS_max_index',DS_max_index)

        # If no damage, set repair class to zero
        if DS_max_index is None:
            repair_class_by_component[NISTR] = 0
        else:
            # Extract repair class of maximum damage state
            rDS_max = rds[DS_max_index]

            # Get proportion of components in maximum damage state
            DS_max_ratio = comp_damage[DS_max_index] / component_qty[NISTR]

            # Get probability of being in the repair class of the max damage state
            p_rDS_max = get_percentile(distribution_rc, theta_rc, beta_rc, DS_max_ratio)

            rnd_num = gen_random()
            # print('rnd',rnd_num)

            # Sample repair class
            if p_rDS_max > rnd_num :
                # Assign max repair class
                repair_class_by_component[NISTR] = rDS_max
            else:
                # Get the repair class index that is one notch lower than the repair class of the max damage state
                rDS_prev_max_index = next((i for i in range(DS_max_index - 1, -1, -1) if rds[i] < rDS_max), None)

                # If there is no previous repair, asesign repair class to zero
                if rDS_prev_max_index is None:
                    repair_class_by_component[NISTR] = 0
                # If there is a previous repair class, assign that one!
                else:
                    repair_class_by_component[NISTR] = rds[rDS_prev_max_index]

    return repair_class_by_component


# Sums consequences across all damage states for each component on each floor
def get_consequence_by_component_by_floor(consequence_total_cost : Dict[str,List[List[float]]]):
    
    consequence_by_component_by_floor = {}
    for NISTR, damage in consequence_total_cost.items() :
        consequence_by_component_by_floor[NISTR] = [[np.sum(floor) for floor in damage_type] for damage_type in damage]

    return consequence_by_component_by_floor



# Consequence_by_component_by_floor: nComponents x {NISTR: [ nRealization x [[total_cost, total_time] x nTotalFloor ]}
# repair_class_by_component:         nComponents x {NISTR: [ nRealization]]}
def get_repair_sequence_by_floor(repair_class_by_component : Dict[str, int], 
                                 consequence_by_component_by_floor : Dict[str,Any], 
                                 nTotalFloor : int, 
                                 components_lib : ComponentsLibrary,
                                 n_sequences : int,
                                 n_repair_goal : int):

    repair_sequence = [[[0]*n_repair_goal for _ in range(n_sequences)] for _ in range(nTotalFloor)]

    for NISTR, repair_class in repair_class_by_component.items():
         
        repair_class = int(repair_class)
        if repair_class > 0 :
            compObj = components_lib[NISTR]
            sequence_index = int(compObj["seq"][0])
            
            # sequence_index = components_lib[NISTR]["seq"][1] + 1 # +1 to convert 0->1
            # repair_time: [nRealization x [nTotalFloor]]
            repair_time = consequence_by_component_by_floor[NISTR][1]
            
            # add_repair_sequence_contribution_each_component(sequence_index, repair_class, repair_time, repair_sequence, filters, nTotalFloor)
            # realizations_for_goal = [findall(filter, repair_class) for filter in filters]
            for goal_index in range(repair_class):
                for floor in range(nTotalFloor):
                    repair_sequence[floor][sequence_index][goal_index] += repair_time[floor]

    return repair_sequence



def get_repair_sequence(repair_sequence_by_floor : List[List[float]], 
                        nTotalFloor : int,
                        n_sequences : int,
                        n_repair_goal : int):

    result = []
    for seq in range(n_sequences):
        inner_result = []
        for goal in range(n_repair_goal):
            goal_sum = 0
            for floor in range(nTotalFloor):
                goal_sum += repair_sequence_by_floor[floor][seq][goal]
            inner_result.append(goal_sum)
        result.append(inner_result)

    return result



def get_structural_repair_time(building : Building, 
                               components_lib : ComponentsLibrary, 
                               max_workers : float, 
                               struc_workers : List[float], 
                               struc_repair : List[float], 
                               nTotalFloor : int):
    
    damage_qty = building.damage_by_component_all_DS

    means_STRUCT = get_recommende_means_STRUCT(building=building, 
                                               components_lib=components_lib,
                                               damage_qty=damage_qty, 
                                               nTotalFloor=nTotalFloor)


    # Get relevant risk parameters
    distribution = building.workers_cap_distribution
    beta = building.workers_cap_beta

    worker_cap = [0. for _ in range(nTotalFloor)]
    for floor in range(nTotalFloor) :
        means_struct_floor = means_STRUCT[floor]
        # if means_struct_floor : 
        sample = sample_dist(distribution,means_struct_floor,beta)
        # else : 
        #     sample = 0.0
        worker_cap[floor] = sample
    
    recommended_worker_sum = np.sum(worker_cap)

    sum_struct_workers = np.sum(struc_workers)
    result = [0. for _ in range(len(struc_repair))]
    for j in range(len(struc_repair)):
        if struc_repair[j] > 0.0:
            result[j] = struc_repair[j] / min(recommended_worker_sum, max_workers, sum_struct_workers)
        else:
            result[j] = 0.0

    return result



def get_recommende_means_STRUCT(building : Building, 
                                components_lib : ComponentsLibrary, 
                                damage_qty : Dict[str,Any], 
                                nTotalFloor : int):

    means = [0. for _ in range(nTotalFloor)]
    for NISTR, damage in damage_qty.items() :
    
        seq = components_lib[NISTR]["seq"][0]
        if seq > 0:
            continue
        add_component_recommended_workers_STRUCT(building, means, damage)
    return means



def add_component_recommended_workers_STRUCT(building : Building, 
                                             means : List[float], 
                                             damage_qty : List[float]):

    nTotalFloor = building.nTotalFloor

    nWorker_per_unit = building.nworkers_recommended_mean_struct
    
    for floor in range(nTotalFloor):
        means[floor] += nWorker_per_unit * damage_qty[floor]



def get_max_workers(building : Building):

    totalArea = building.total_floor_area

    # Extract relevant risk parameters
    max_workers_minimum = building.max_workers_minimum
    max_workers_slope = building.max_workers_slope
    max_workers_x_cutoff = building.max_workers_x_cutoff
    max_workers_sigma = building.max_workers_sigma

    # Calculate mean
    mean = max_workers_minimum + max(0, totalArea - max_workers_x_cutoff) * max_workers_slope

    # Sample max workers
    return sample_dist("Normal", mean, max_workers_sigma)



def get_struct_workers(building : Building):
    
    floorareas = building.floor_areas

    # Get risk parameters
    max_workers_per_struct_divider = building.max_workers_per_struct_divider
    distribution = building.workers_cap_distribution
    beta = building.workers_cap_beta

    mean_by_floor = [floor  / max_workers_per_struct_divider for floor in floorareas]  

    # Sample the number of workers
    results = []
    for j in range(len(mean_by_floor)) :
        results.append(sample_dist(distribution, mean_by_floor[j], beta))

    return results



def process_downtime(repair_schedule : List[Dict[str,float]], 
                     max_delay : List[float], 
                     struc_days : List[float],
                     n_repair_goal : int):
    
    # print("max delay is " + str(max_delay))
    spans = np.zeros((n_repair_goal))
    for goal in range(n_repair_goal):
        x = repair_schedule[goal]["ends"]

        if len(x) == 0 :
            if struc_days[goal] == 0 :
                spans[goal] = 0
            else :
                spans[goal] = struc_days[goal] + max_delay[0]
        else :
            spans[goal] = np.max(x)    

    return spans



def output_results(building : Building) -> dict : 

    repair_schedule = building.repair_schedule
        
    keys_to_keep = ["struct_repairs", "total_span"]

    filtered_repair_schedule = [{key: value for key, value in item.items() if key in keys_to_keep} for item in repair_schedule]


    resultsDict = {
        "repair_class" :  building.repair_class,
        "damage_by_component_all_DS" :  building.damage_by_component_all_DS,
        "repair_schedule" :  filtered_repair_schedule,
        "component_qty" :  building.component_qty,
        "consequence_by_component_by_floor" :  building.consequence_by_component_by_floor,
        "impeding_delays" :  building.impeding_delays,
        "max_delay" :  building.max_delay[0],
        "building_total_downtime" :  building.building_total_downtime,
    }

    print('Analysis done!\n')
    print(f'Time to full recovery [days] {building.building_total_downtime[0]}')
    print(f'Time to functional recovery [days]  {building.building_total_downtime[1]}')
    print(f'Time to immediate occupancy [days]  {building.building_total_downtime[2]}\n')

    return resultsDict

