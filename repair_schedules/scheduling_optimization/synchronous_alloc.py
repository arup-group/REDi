import numpy as np
from typing import Dict, Any

def synchronous_alloc(demand : np.ndarray, 
                      constraint : np.ndarray, 
                      nWorker : float, 
                      ready : np.ndarray,
                      now : float = 0.0) -> Dict[Any,Any] :
   
    N = len(demand)
    demand, constraint, ready = demand.copy(), constraint.copy(), ready.copy()
    time2finish = np.full(N, np.inf) # initialized as [Inf]
    workers_assigned = np.zeros(N).astype(np.float64) # vary in each step
    starts = np.full(N, -1.0) # initialized as [-1]
    ends = time2finish.copy() # initialized as [Inf]
    workers_assigned_all_step : Dict[Any,Any] = {}
    constraint = constraint.astype(np.float64)
    demand = demand.astype(np.float64)
    capacity = constraint.copy()
    synchronous_alloc_assign_repair_sequence(demand=demand, 
                                             constraint=constraint, 
                                             capacity=capacity,  
                                             time2finish=time2finish, 
                                             now=now, 
                                             starts=starts,  
                                             ends=ends,  
                                             workers_assigned=workers_assigned,  
                                             nWorker=nWorker, 
                                             workers_assigned_all_step=workers_assigned_all_step, 
                                             ready=ready)
        

    total_span_list = np.zeros((len(starts)))

    for i in range(len(starts)) : 
        v = starts[i]
        if v >= 0.0 :
            total_span_list[i] = ends[i]

    total_span = np.max(total_span_list)

    # extract the span of each sequence
    span_by_seq = ends.copy()
    span_by_seq[np.isinf(span_by_seq)] = 0.0

    #TODO: check this
    ends = span_by_seq

    return {"total_span":total_span, "span_by_seq":span_by_seq, "allocation":workers_assigned_all_step, "starts":starts, "ends":ends, "ready":ready}


def synchronous_alloc_assign_repair_sequence(demand : np.ndarray, 
                                             constraint : np.ndarray, 
                                             capacity : np.ndarray,  
                                             time2finish : np.ndarray, 
                                             now : float, 
                                             starts : np.ndarray,  
                                             ends : np.ndarray,  
                                             workers_assigned : np.ndarray,  
                                             nWorker : float, 
                                             workers_assigned_all_step : Dict[Any,Any], 
                                             ready : np.ndarray):
    
    if np.max(demand) <= 0.0000001:
        return

    seq_ready = np.where(ready <= now)[0]
    seq_not_ready = np.where(ready > now)[0]

    if len(seq_ready) > 0:
        while nWorker > 0.01 and np.sum(capacity) > 0.01:
            seq_with_demand = np.where(demand > 0.0000001)[0]
            seq_with_capacity = np.where(capacity > 0)[0]
            available = np.intersect1d(np.intersect1d(seq_ready, seq_with_demand), seq_with_capacity)

            if len(available) == 0:
                break

            seq_to_assign = available
            nWorker = synchronous_alloc_assign_workers(demand=demand,  
                                                       capacity=capacity,  
                                                       time2finish=time2finish,  
                                                       now=now, 
                                                       starts=starts,  
                                                       nWorker=nWorker, 
                                                       sequences_index=seq_to_assign, 
                                                       workers_assigned=workers_assigned,
                                                       workers_assigned_all_step=workers_assigned_all_step)
                                     

    seq_index_to_finish = np.argmin(time2finish)
    time_to_finish_next = time2finish[seq_index_to_finish]

    time2nextReady = np.inf
    if len(seq_not_ready) > 0:
        seq_next_ready = seq_not_ready[np.argmin(ready[seq_not_ready])]
        time2nextReady = ready[seq_next_ready] - now

    if time_to_finish_next <= time2nextReady:

        now += time_to_finish_next
        time2finish -= time_to_finish_next

        nWorker = synchronous_alloc_finish_sequence(demand=demand, 
                                      time2finish=time2finish, 
                                      now=now, 
                                      ends=ends, 
                                      time=time_to_finish_next, 
                                      nWorker=nWorker, 
                                      workers_assigned=workers_assigned, 
                                      workers_assigned_all_step=workers_assigned_all_step)
            
    else:

        now += time2nextReady
        time2finish -= time2nextReady
        demand -= time2nextReady * workers_assigned
        capacity = constraint.copy()
        nWorker += np.sum(workers_assigned)
        workers_assigned[:] = 0

    synchronous_alloc_assign_repair_sequence(demand=demand, 
                                             constraint=constraint, 
                                             capacity=capacity,  
                                             time2finish=time2finish, 
                                             now=now, 
                                             starts=starts,  
                                             ends=ends,  
                                             workers_assigned=workers_assigned,  
                                             nWorker=nWorker, 
                                             workers_assigned_all_step=workers_assigned_all_step, 
                                             ready=ready)
                                             

def synchronous_alloc_assign_workers(demand : np.ndarray,  
                                     capacity : np.ndarray,  
                                     time2finish : np.ndarray,  
                                     now : float, 
                                     starts : np.ndarray,  
                                     nWorker : float, 
                                     sequences_index : np.ndarray, 
                                     workers_assigned : np.ndarray,
                                     workers_assigned_all_step : Dict[Any,Any]) -> float :
    
    total_demand = sum(demand[sequences_index])

    first_alloc = nWorker / total_demand * demand[sequences_index]

    alloc = np.zeros(len(first_alloc))
    for i in range(len(alloc)) :
       alloc[i] = np.minimum(first_alloc[i], capacity[sequences_index[i]])

    workers_assigned[sequences_index] += alloc
    capacity[sequences_index] -= alloc
    
    # udpate starts
    old_starts = starts[sequences_index]
    starts[sequences_index] = [old_start if old_start >= 0 else now for old_start in old_starts]
    
    time2finish[sequences_index] = demand[sequences_index] / workers_assigned[sequences_index]

    workers_assigned_all_step[str(now)] = workers_assigned.copy()

    return nWorker - sum(alloc)  # update workers available


def synchronous_alloc_finish_sequence(demand : np.ndarray, 
                                      time2finish : np.ndarray, 
                                      now : float, 
                                      ends : np.ndarray, 
                                      time : float, 
                                      nWorker : float, 
                                      workers_assigned : np.ndarray, 
                                      workers_assigned_all_step : Dict[Any,Any]) -> float :
    
    seq_to_finish = np.where(np.abs(time2finish) < 0.000000001)[0]
    ends[seq_to_finish] = now
    demand -= time * workers_assigned
    time2finish[seq_to_finish] = np.inf  # set time2finish of this sequence to Inf, i.e. finished
    n_works_spared = np.sum(workers_assigned[seq_to_finish])
    workers_assigned[seq_to_finish] = 0
    workers_assigned_all_step[now] = workers_assigned.copy()
    return nWorker + n_works_spared


