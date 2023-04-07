from pathlib import Path
import json
import csv


path_to_pelicun_resources = '/Users/stevan.gavrilovic/Desktop/PBE.app/Contents/MacOS/applications/performDL/pelicun3/pelicun/resources'


path_to_fragility_json = Path(path_to_pelicun_resources,'fragility_DB_FEMA_P58_2nd.json')
path_to_fragility_csv = Path(path_to_pelicun_resources,'fragility_DB_FEMA_P58_2nd.csv')

path_to_arup_fragility = '/Users/stevan.gavrilovic/Desktop/pyREDi/data/components_library_private.json'

file_path_out = '/Users/stevan.gavrilovic/Desktop/pyREDi/data/components_library.json'


keys_to_include = ['seq','rds','n_ds','theta_ds','beta_ds','repairdesc','param','paramunits']


with open(path_to_fragility_json, 'r') as f:
    pelicun_data = json.load(f)


with open(path_to_arup_fragility, 'r') as f:
    iris_data = json.load(f)
    
pelicun_clean = {}
for nistr, component in pelicun_data.items() :

    nistr = nistr.replace('.','',2)
    
    pelicun_clean[nistr] = component
    
    print(nistr)
    

# Open the pelicun csv
with open(path_to_fragility_csv, 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        # do something with each row
        print(row)
    

# These two not found in Iris implementation
pelicun_clean.pop('D5092.033i')
pelicun_clean.pop('F1012.001')

#print(json.dumps(pelicun_clean))


final_component_lib = {}
for nistr, component in pelicun_clean.items() :
    
    try:
        iris_comp = iris_data[nistr]
    except:
        print(f'Error, could not find component {nistr}')
        pass
    
    # Add the keys
    for key in keys_to_include :
        component[key] = iris_comp[key]
        
    # Add long lead if applicable
    if 'long_lead' in iris_comp :
        component['long_lead'] = iris_comp['long_lead']

    final_component_lib[nistr] = component
    
# Output to file
# Write the dictionary to the JSON file
with open(file_path_out, 'w') as f:
    json.dump(final_component_lib, f)
