
from typing import Dict, Any


class ComponentsLibrary() : 
     
     def __init__(self, components_lib_dict) :
          self.library = components_lib_dict

     def __getitem__(self, index):
        return self.library[index]


class Building() :
    
     def __init__(self, building_dict) :

          # Required inputs
          self.building_dict = building_dict
          self.nFloor = building_dict['nFloor']
          self.components = building_dict['components']

          # component_damage is a list of lists, 
          # the lowest-level list (length 5) is associated with the number of stories. 
          # the highest-level list (length 2) is associated with the number of damage states. 
          # The first list corresponds to Damage State 0 (i.e. undamaged) and the rest of the list corresponds to the remaining Damage States
          self.damage_by_component = building_dict['component_damage']

          self.total_consequences = building_dict['total_consequences']

          self.floor_areas = building_dict['floor_areas']
          self.replacement_cost = building_dict['replacement_cost']
          self.replacement_time = building_dict['replacement_time']

          if 'risk_parameters' not in building_dict :
               raise ValueError("Error, missing the 'risk_parameters in the input")
          
          risk_parameters = building_dict['risk_parameters']

          if 'business' not in risk_parameters :
               raise ValueError("Error, missing the 'business' parameters in the risk_parameters dictionary")
          
          self.loss_thresh_ratio = risk_parameters['business']['loss_thresh_ratio']
          self.available_fund_ratio = risk_parameters['business']['available_fund_ratio']
          self.deductible_ratio = risk_parameters['business']['deductible_ratio']
          self.insur_limit_ratio = risk_parameters['business']['insur_limit_ratio']
          self.finance_method = risk_parameters['business']['finance_method']

          if 'repair' not in risk_parameters :
               raise ValueError("Error, missing the 'repair' parameters in the risk_parameters dictionary")
          
          self.distribution_rc = risk_parameters['repair']['repair_class_fragility']['distribution']
          self.theta_rc = risk_parameters['repair']['repair_class_fragility']['theta']
          self.beta_rc = risk_parameters['repair']['repair_class_fragility']['beta']
          
          # Worker repair parameters
          self.max_workers_minimum = risk_parameters["repair"]["max_workers_per_building"]["minimum"]
          self.max_workers_slope = risk_parameters["repair"]["max_workers_per_building"]["slope"]
          self.max_workers_x_cutoff = risk_parameters["repair"]["max_workers_per_building"]["x_cutoff"]
          self.max_workers_sigma = risk_parameters["repair"]["max_workers_per_building"]["sigma"]

          self.max_workers_per_struct_divider = risk_parameters["repair"]["max_workers_per_struct_divider"]
          self.workers_cap_distribution = risk_parameters["repair"]["workers_capacity"]["distribution"]
          self.workers_cap_beta = risk_parameters["repair"]["workers_capacity"]["beta"]

          self.nworkers_recommended_mean = risk_parameters["repair"]["nworkers_recommended_mean"]
          self.nworkers_recommended_mean_struct = risk_parameters["repair"]["nworkers_recommended_mean_struct"]
          self.nwork_perfloor_divider = risk_parameters["repair"]["nwork_perfloor_divider"]

          self.recommended_workers_distribution = risk_parameters["repair"]["workers_capacity"]["distribution"]
          self.recommended_workers_beta = risk_parameters["repair"]["workers_capacity"]["beta"]

          self.max_workers_by_sequence = risk_parameters["repair"]["max_workers_by_sequence"]

          if 'impeding_factors' not in risk_parameters :
               raise ValueError("Error, missing the 'impeding_factors' parameters in the risk_parameters dictionary")
          
          # Inspection parameters
          self.inspection_distribution = risk_parameters['impeding_factors']['inspection_delay']['distribution']
          self.inspection_theta = risk_parameters['impeding_factors']['inspection_delay']['theta']
          self.inspection_beta = risk_parameters['impeding_factors']['inspection_delay']['beta']

          # Eng mobilization parameters
          self.eng_mobilization_distribution = risk_parameters['impeding_factors']['engineer_mobilization_delay_seismic']['distribution']
          self.eng_mobilization_theta = risk_parameters['impeding_factors']['engineer_mobilization_delay_seismic']
          self.eng_mobilization_beta = risk_parameters['impeding_factors']['engineer_mobilization_delay_seismic']

          # Financing delay parameters
          self.finance_delay_params = risk_parameters['impeding_factors']['financing_delay']
          
          # Permit delay parameters
          self.permit_delay_params = risk_parameters["impeding_factors"]["permit_delay_seismic"]

          # Construction delay parameters
          self.con_delay_params = risk_parameters["impeding_factors"]["contractor_mobilization_delay_seismic"]

          # Long lead time parameters
          self.long_lead_threshold = risk_parameters["impeding_factors"]["longlead"]["threshold"]
          self.long_lead_distribution = risk_parameters["impeding_factors"]["longlead"]["distribution"]
          self.long_lead_beta = risk_parameters["impeding_factors"]["longlead"]["beta"]

          # Attributes that will be calculated here or in the REDi workflow
          self.nTotalFloor = self.nFloor + 1
          self.damage_by_component_all_floors = None
          self.repair_class = None
          self.total_floor_area = None
          self.damage_by_component_all_DS = None
          self.repair_schedule = None
          self.component_qty = None
          self.consequence_by_component_by_floor = None
          self.repair_sequence_by_floor = None
          self.repair_sequence = None
          self.impeding_delays = None
          self.max_delay = None
          self.n_repair_goal = 3 # Number of repair goals
          self.n_sequences = 8 # Total number of sequences
          self.n_non_struc_sequence = 7 # Number of non-structural sequences
