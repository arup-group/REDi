from go_redi import (go_redi,
                     get_damage_by_component_all_DS, 
                     get_component_qty_all_floor, 
                     assign_repair_class,
                     get_damage_by_component_all_floors,
                     get_consequence_by_component_by_floor,
                     get_repair_sequence_by_floor,
                     get_repair_sequence,
                     get_impeding_delays,
                     get_max_workers,
                     get_struct_workers,
                     get_structural_repair_time,
                     process_downtime)


from repair_schedules.get_repair_schedule import (get_worker_capacity,
                                                  get_constrained_workers,
                                                  get_repair_schedule_unit_realization)

from utils.stat_utils import set_seed


"""
   This tests the get_damage_by_component_all_DS
   
"""
def test_individual_functions(test_building_1,
                              test_component_library_1) :
   
   # Set the seed to ensure tests are deterministic
   # Do not change this seed value and burn in 
   set_seed(123,248)
  
   # Get the total number of floors
   nTotalFloor = test_building_1.nTotalFloor

   # Get the total floor area 
   test_building_1.total_floor_area = sum(test_building_1.floor_areas)

   # Get the component damage states
   comp_damage = test_building_1.damage_by_component

   # Get the damage by component_all_floors
   damage_by_component_all_floors = get_damage_by_component_all_floors(comp_damage)

   assert(damage_by_component_all_floors['C3027.002'][0] == 10817.0)
   assert(damage_by_component_all_floors['B1033.061b'][1] == 3.0)

   test_building_1.damage_by_component_all_floors = damage_by_component_all_floors

   damage_by_component_all_DS = get_damage_by_component_all_DS(component_damage=comp_damage, nTotalFloor=nTotalFloor)

   assert(damage_by_component_all_DS['C3027.002'][1] == 2365.0)
   assert(damage_by_component_all_DS['D2022.013a'][3] == 1.0)

   test_building_1.damage_by_component_all_DS = damage_by_component_all_DS

   # Get the total number of floors
   nTotalFloor = test_building_1.nTotalFloor

   # Get the total building cost
   total_cost = test_building_1.total_consequences

   # Get total quantity of every component across the entire building
   component_qty = get_component_qty_all_floor(test_building_1.components)
   test_building_1.component_qty = component_qty

   assert(component_qty["B1033.061b"]==16)
   assert(component_qty["B1031.011b"]==640)
   assert(component_qty["D3041.031b"]==82.8)

   repair_class = assign_repair_class(building=test_building_1, 
                                      components_lib=test_component_library_1)
   test_building_1.repair_class = repair_class

   assert(repair_class["D3041.031b"]==3)
   assert(repair_class["D4011.023a"]==2)
   assert(repair_class["B1031.011b"]==0)

   consequence_by_component_by_floor = get_consequence_by_component_by_floor(consequence_total_cost=total_cost)
   test_building_1.consequence_by_component_by_floor = consequence_by_component_by_floor

   assert(consequence_by_component_by_floor["B1033.061b"][0][0]==122668.65927427942)
   assert(consequence_by_component_by_floor["C3027.002"][1][2]==487.9801758638806)
   assert(consequence_by_component_by_floor["D3041.031b"][1][2]==30.117809623428833)


   repair_sequence_by_floor = get_repair_sequence_by_floor(repair_class_by_component=repair_class, 
                                                           consequence_by_component_by_floor=consequence_by_component_by_floor,
                                                           nTotalFloor=nTotalFloor,
                                                           components_lib=test_component_library_1)
   test_building_1.repair_sequence_by_floor = repair_sequence_by_floor

   assert(repair_sequence_by_floor[0][0][0]==81.62406341817247)
   assert(repair_sequence_by_floor[1][1][1]==397.850409057227)
   assert(repair_sequence_by_floor[2][1][2]==30.686167235287016)

   repair_sequence = get_repair_sequence(repair_sequence_by_floor=repair_sequence_by_floor, 
                                          nTotalFloor=nTotalFloor)
   test_building_1.repair_sequence = repair_sequence

   assert(repair_sequence[0][0]==349.70216765886994)
   assert(repair_sequence[2][1]==0)
   assert(repair_sequence[5][0]==47.42511337831366)

   max_delay, impeding_delays = get_impeding_delays(building=test_building_1,
                                                    components_lib=test_component_library_1,
                                                    repair_sequence=repair_sequence, 
                                                    component_qty=component_qty)
   
   assert(max_delay==174.4460786784853)
   assert(impeding_delays['inspection_delay']==0.9427842384564218)
   assert(impeding_delays['permit_delay']==1.5489606840065457)
   nonstruct_contractor_delays=impeding_delays["nonstruct_contractor_mobilization_delays"]
   assert(nonstruct_contractor_delays[0]==183.03043068836655)

   # Get structural and nonstructural delays
   max_workers = get_max_workers(building=test_building_1)
   assert(max_workers==52.95038890403064)
   
   struc_workers = get_struct_workers(building=test_building_1)
   assert(struc_workers[0]==67.13599283155008)
   assert(struc_workers[3]==53.271138525919454)

   struc_repair_time = repair_sequence[0]
   struc_repair_days = get_structural_repair_time(building=test_building_1, 
                                                  max_workers=max_workers, 
                                                  struc_workers=struc_workers, 
                                                  struc_repair=struc_repair_time, 
                                                  nTotalFloor=nTotalFloor,
                                                  components_lib=test_component_library_1)
   

   assert(struc_repair_days[0]==11.725659056092393)
   assert(struc_repair_days[2]==0.0)

   floor_areas = test_building_1.floor_areas       
   damage_qty = test_building_1.damage_by_component_all_DS

   # capacity: [nRealization x [ n_non_struc_repair_sequence]]
   capacity = get_worker_capacity(building=test_building_1,
                                 components_lib=test_component_library_1,
                                 floor_areas=floor_areas, 
                                 damage_qty=damage_qty, 
                                 nTotalFloor=nTotalFloor)
   
   assert(capacity[0][0]==19.171932617861405)

   constraint = get_constrained_workers(building = test_building_1)

   assert(constraint[1]==11.37661283387764)

   repair_schedule = get_repair_schedule_unit_realization(delay=[max_delay], 
                                                          struc_repair_days=struc_repair_days, 
                                                          nonstruct_contractor_delays=nonstruct_contractor_delays, 
                                                          sequence_demand=repair_sequence_by_floor, 
                                                          capacity=capacity, 
                                                          nWorker=max_workers,
                                                          nTotalFloor=nTotalFloor, 
                                                          constraint=constraint)
   
   assert(repair_schedule[1]['total_span']==404.9035212096834)

   test_building_1.repair_schedule = repair_schedule

    # Get total downtime, including delays and repair time
   building_total_downtime = process_downtime(repair_schedule, 
                                              max_delay=[max_delay], 
                                              struc_days=struc_repair_days)

   assert(building_total_downtime[2]==191.11405103396697)


def test_go_redi(test_building_2,
                 test_component_library_1) :
   
   res = go_redi(building_dict=test_building_2,
                 components_lib_dict=test_component_library_1,
                 seed=123,
                 burn_in=248)
   
   assert(res['building_total_downtime'][0]==426.509427488184)
   assert(res['building_total_downtime'][1]==404.9035212096834)
   assert(res['building_total_downtime'][2]==191.11405103396697)
