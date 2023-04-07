
from repair_schedules.scheduling_optimization.synchronous_alloc import synchronous_alloc
from typing import Dict, Any

import numpy as np

def get_optimized_repair_schedule_diff_start(demand : np.ndarray,
                                             capacity : np.ndarray,
                                             nFloor : int,
                                             nWorker : float,
                                             ready : np.ndarray,
                                             struc_repair_days : float,
                                             n_non_struc_sequence : int,
                                             now : float=0.0) -> Dict[str,Any] :
                                             
    r = synchronous_alloc(demand = demand.T.flatten(), 
                          constraint = capacity.T.flatten(), 
                          nWorker=nWorker, 
                          ready=ready.T.flatten(),
                          now=now)
        
    
    r["starts"] = reshape_by_floor(list=r["starts"],
                                   nFloor=nFloor,
                                   n_non_struc_sequence=n_non_struc_sequence)
                                   
    r["ends"] = reshape_by_floor(list=r["ends"],
                                 nFloor=nFloor,
                                 n_non_struc_sequence=n_non_struc_sequence)
                                 
    r["span_by_seq"] = reshape_by_floor(list=r["span_by_seq"],
                                        nFloor=nFloor,
                                        n_non_struc_sequence=n_non_struc_sequence)
    
    allocation = dict()
    for original_alloc in r["allocation"].items():
        allocation[original_alloc[0]] = reshape_by_floor(list = original_alloc[1],
                                                         nFloor=nFloor,
                                                         n_non_struc_sequence=n_non_struc_sequence)
        
    r["allocation"] = allocation
    r["struct_repairs"] = struc_repair_days
    
    assert "allocation" in r.keys()
    
    return r


def reshape_by_floor(list : np.ndarray, 
                     nFloor : int,
                     n_non_struc_sequence : int):

    return np.reshape(list, (nFloor, n_non_struc_sequence), order='F')

