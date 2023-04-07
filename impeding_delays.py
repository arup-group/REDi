
import numpy as np
from typing import Dict, List, Any

from utils.stat_utils import sample_dist

from building import Building, ComponentsLibrary

###################################
########## MAIN FUNCTION ##########
###################################


def get_impeding_delays(building : Building,
                        components_lib : ComponentsLibrary,
                        repair_sequence : List[List[float]],
                        component_qty : Dict[str,float]) :
    

    # Get the total building repair cost
    total_consequences = building.total_consequences

    total_repair_cost = 0.0
    for _,consequences in total_consequences.items() :
        
        cost_list = consequences[0]

        # Sum up the costs on each floor
        for cost_floor in cost_list :
            total_repair_cost+= np.sum(cost_floor)

    # Get the building replacement cost 
    replacement_cost = building.replacement_cost

    # Get the recovery parameters
    loss_thresh_ratio = building.loss_thresh_ratio
    available_fund_ratio = building.available_fund_ratio
    deductible_ratio = building.deductible_ratio
    insur_limit_ratio = building.insur_limit_ratio

    # Calculate values based on replacement cost (convert replacement cost to $ from $M)
    finance_cover = replacement_cost * loss_thresh_ratio * 1000000.0
    available_fund = replacement_cost * available_fund_ratio * 1000000.0
    deductible = replacement_cost * deductible_ratio * 1000000.0
    insurance_limit = replacement_cost * insur_limit_ratio * 1000000.0

    # Extract mitigation mitigation measures ?
    # eng_on_contract = building.miti_measures[0]
    # gc_on_contract = building.miti_measures[1]
    # BORP = building.miti_measures[2]

    # Initialize result
    impeding_delays = {}

    # Get the maximum repair classes associated with each repair sequence
    max_struct_rc, max_nonstruct_rc = get_max_rcs(repair_sequence=repair_sequence)

    # Get inspection delay
    insp_delay = get_inspection_delay(building=building)
    impeding_delays["inspection_delay"] = insp_delay
    
    # Engineer mobilization delay
    redesign_flag = total_repair_cost > finance_cover # Check to see if redesign is necessary
    eng_mob_delay = get_engineer_mob_delay(building=building, 
                                           max_struct_rc=max_struct_rc, 
                                           redesign_flag=redesign_flag)
    
    impeding_delays["engineering_mobilization_delay"] = eng_mob_delay

    # Finance delay
    finance_delay = get_finance_delay(building=building,
                                      building_cost=total_repair_cost, 
                                      deductible=deductible, 
                                      insurance_limit=insurance_limit, 
                                      available_fund=available_fund)
    
    impeding_delays["financing_delay"] = finance_delay

    # Permit delay
    permit_delay =  get_permit_delay(building=building,max_struct_rc=max_struct_rc)
    impeding_delays["permit_delay"] = permit_delay

    # Contractor delay (not yet including long lead times)
    contract_delay = get_contractor_mob_delay(building=building, max_nonstruct_rc=max_nonstruct_rc)
    contractor_delays = contract_delay

    # Add long lead times
    long_lead_times_by_seq = get_longlead_by_seq(building=building, 
                                                 component_qty=component_qty, 
                                                 components_lib=components_lib)
    

    # Add long lead times to contractor delays
    contractor_mobilization_delays = [sum(x) for x in zip(contractor_delays, long_lead_times_by_seq)]

    # Get the contractor delay for structural sequence
    impeding_delays["struct_contractor_mobilization_delays"] = contractor_mobilization_delays[0]

    # Get the contractor delays for the nonstructural sequences
    impeding_delays["nonstruct_contractor_mobilization_delays"] = contractor_mobilization_delays[1:]

    # Get max delay
    max_delay = get_max_delay(impeding_delays)

    return max_delay, impeding_delays


######################################
########## HELPER FUNCTIONS ##########
######################################


def get_max_rcs(repair_sequence : List[List[float]]):

    # Extract sequences
    struct_rc = repair_sequence[0]
    nonstruct_rc = repair_sequence

    # Initialize result (structural RC)
    max_struct_rc = 0

    # Extract maximum structural repair class
    for rc_index in range(len(struct_rc)):
        if struct_rc[rc_index] > 0.0:
            max_struct_rc += 1

    # Initialize result (nonstructural RCs)
    max_nonstruct_rc = [0 for seq in nonstruct_rc]

    # Extract maximum nonstructural repair class for each sequence
    for seq_index in range(len(nonstruct_rc)):
        for rc_index in range(len(nonstruct_rc[seq_index])):
            if nonstruct_rc[seq_index][rc_index] > 0.0:
                max_nonstruct_rc[seq_index] += 1

    return max_struct_rc, max_nonstruct_rc


def get_inspection_delay(building : Building) -> float :

    # Extract inspection distribution parameters
    inspection_distribution = building.inspection_distribution
    inspection_theta = building.inspection_theta
    inspection_beta = building.inspection_beta

    # Return sampled delay
    return sample_dist(inspection_distribution, inspection_theta, inspection_beta)


def get_engineer_mob_delay(building: Building, 
                           max_struct_rc: int, 
                           redesign_flag: bool) -> float:

    # get delay type based on max repair class
    if redesign_flag:
        delay_type = "redesign"
    elif max_struct_rc == 3:
        delay_type = "rc3"
    elif max_struct_rc == 1:
        delay_type = "rc1"
    else:
        delay_type = "none"
    
    # Sample only if structural repairs are required
    if delay_type == "none":
        delay = 0
    else:
        eng_mobilization_distribution = building.eng_mobilization_distribution
        eng_mobilization_theta = building.eng_mobilization_theta[delay_type]["theta"]
        eng_mobilization_beta = building.eng_mobilization_beta[delay_type]["beta"]
        delay = sample_dist(eng_mobilization_distribution, eng_mobilization_theta, eng_mobilization_beta)

    return delay


def get_finance_delay(building : Building, 
                      building_cost : float, 
                      deductible : float, 
                      insurance_limit : float, 
                      available_fund : float) -> float:

    # Determine if there is a lack of funding
    lack_fund_flag = (building_cost > available_fund)

    # Get finance method
    finance_method = building.finance_method

    financing_delay_params = building.finance_delay_params

    # Only a delay if there is a lack of funding
    if lack_fund_flag:

        finance_delay_distribution = financing_delay_params['distribution']

        # If the finance method is not insurance or if the total loss is less than the deductible...
        if finance_method != "insurance" or building_cost < deductible:

            # parameters for impeding curve
            finance_delay_theta = financing_delay_params['default']['theta']
            finance_delay_beta = financing_delay_params['default']['beta']

            # sample delay
            delay = sample_dist(finance_delay_distribution, finance_delay_theta, finance_delay_beta)

        # If the finance method is insurance and the total loss is more than the deductible...
        else:

            # If the financial loss is more than the insurance limit, then assume private loan delay (finance method 3)
            if building_cost > insurance_limit:

                # parameters for impeding curve
                finance_delay_theta = financing_delay_params["private_loans"]["theta"]
                finance_delay_beta = financing_delay_params["private_loans"]["beta"]

                # sample delay
                delay = sample_dist(finance_delay_distribution, finance_delay_theta, finance_delay_beta)

            # If the financial loss is less than the insurance limit...
            else:

                # If deductible is more than the available fund, then assume regular insurance delay
                if deductible > available_fund:

                    # parameters for impeding curve
                    finance_delay_theta = financing_delay_params['default']['theta']
                    finance_delay_beta = financing_delay_params['default']['beta']

                    # sample delay
                    delay = sample_dist(finance_delay_distribution, finance_delay_theta, finance_delay_beta)

                # If the available funds are more than the deductible, then no delay!
                else:
                    delay = 0.
    else:
        delay = 0.

    return delay


def get_permit_delay(building : Building, 
                     max_struct_rc : int) -> float :
    

    permit_delay_params = building.permit_delay_params

    # no delay if no structural damage
    if max_struct_rc == 0:
        delay = 0
    else:
        # Get delay distribution
        permit_delay_distribution = permit_delay_params["distribution"]
        
        # different parameters for different repair classes
        if max_struct_rc == 1:
            theta = permit_delay_params["rc1"]["theta"]
            beta = permit_delay_params["rc1"]["beta"]
        elif max_struct_rc == 3: # updated to reflect Ibbi discussion re: RC1 or RC3 for structural repairs only. No RC2 curve.
            theta = permit_delay_params["rc3"]["theta"]
            beta = permit_delay_params["rc3"]["beta"]
        
        # sample delay
        delay = sample_dist(permit_delay_distribution, theta, beta)
    
    return delay


def get_contractor_mob_delay(building : Building, 
                             max_nonstruct_rc) -> List[float] :
    
    # Get the number of sequences
    n_sequences = len(max_nonstruct_rc)

    # Initialize result
    delays = [0.0 for i in range(n_sequences)]

    con_delay_params = building.con_delay_params

    # Get distribution
    con_delay_distribution = con_delay_params["distribution"]

    # Loop over all sequences
    for seq_index in range(n_sequences):

        # no delay if no nonstructural damage
        if max_nonstruct_rc[seq_index] == 0:
            delays[seq_index] = 0.0
        else:
            # different parameters for different repair classes
            if max_nonstruct_rc == 1:

                # theta = params[1][seq_index,1]
                # sigma = params[1][seq_index,2]
                theta = con_delay_params["rc1"]["theta_by_seq"][seq_index]
                sigma = con_delay_params["rc1"]["sigma_by_seq"][seq_index]
            else:
                # theta = params[2][seq_index,1]
                # sigma = params[2][seq_index,2]
                theta = con_delay_params["rc23"]["theta_by_seq"][seq_index]
                sigma = con_delay_params["rc23"]["sigma_by_seq"][seq_index]

            # sample delay
            sample_delay = sample_dist(con_delay_distribution, theta, sigma)
            delays[seq_index] = sample_delay

    return delays


def get_longlead_by_seq(building : Building,
                        components_lib : ComponentsLibrary,
                        component_qty : Dict[str,float]) -> np.ndarray :

    # Get the number of sequences
    n_sequences = building.n_sequences
    
    # Initialize result
    longlead_by_seq = np.zeros(n_sequences)
    
    # Get the damage states across all floors
    damage_states_all_floors = building.damage_by_component_all_DS
    
    # Get long lead time risk parameters
    threshold = building.long_lead_threshold
    distribution = building.long_lead_distribution
    beta = building.long_lead_beta
    
    # loop over all the components with damage
    # for a given component pull the NISTR tag and damage state data
    for nistr, comp_damage in damage_states_all_floors.items() :

        component = components_lib[nistr]
     
        # Get long lead time for component (has units of days)
        if "long_lead" in component:
            longlead_comp = component["long_lead"]
        else:
            longlead_comp = [0. for ds_index in range(component["n_ds"]+1)]
        
        # find the largest damage state with a number of associated components above the long_lead threshold        
        DS_index = None
        for i in range(len(damage_states_all_floors[nistr])) :
            comp_quantity = component_qty[nistr]
            if damage_states_all_floors[nistr][i] > threshold * comp_quantity:
                DS_index = i

        if DS_index == None :
            longlead_component = 0.0
        else:
            # This check is just here to account for long_lead entries that appear to have been put in erroneously
            if DS_index >= len(longlead_comp) :
                longlead_component = 0.0
            else:
                longlead_component = sample_dist(distribution, longlead_comp[DS_index], beta)
        
        # compare to current sequence maximum, and replace if larger
        sequence_index = int(component["seq"][0]) 
        longlead_by_seq[sequence_index] = max(longlead_by_seq[sequence_index], longlead_component)


    return longlead_by_seq


def get_max_delay(impeding_delays : Dict[str,float]) -> float :

    # Calculate each delay path
    delay_paths = [impeding_delays["inspection_delay"] + impeding_delays["financing_delay"],
                    impeding_delays["inspection_delay"] + impeding_delays["engineering_mobilization_delay"] + impeding_delays["permit_delay"],
                    impeding_delays["inspection_delay"] + impeding_delays["struct_contractor_mobilization_delays"]]

    # Get the maximum delay of each of the delay paths
    max_delay = max(delay_paths)

    # Get the maximum delay
    return max_delay
