import json, time, argparse
from go_redi import go_redi
from utils.file_utils import write_results
from utils.stat_utils import set_seed
from pathlib import Path

def main(args):

    path_building=args.a
    path_components=args.c
    burn_in=args.b
    seed=args.s
    seed=args.s
    out_path=args.r

    # open the asset JSON file
    with open(path_building) as f:
        
        # load the JSON data as a list
        building_data = json.loads(f.read())

    # load components if provided
    component_data = None
    if path_components :
        with open(path_components) as f:
            # load the JSON data as a list
            component_data = json.loads(f.read())

    start_time = time.time()

    # set_seed(seed=123,burn_in=burn_in)

    # for i in range(100) :
        # res = go_redi(building_dict=building_data, components_lib_dict=component_data, seed=0,burn_in=0)
        # print('Total downtime :',res['building_total_downtime'],'\n')

    # run the REDi engine
    res = go_redi(building_dict=building_data, components_lib_dict=component_data, seed=seed,burn_in=burn_in)

    print('Total downtime :',res['building_total_downtime'],'\n')

    end_time = time.time()
    elapsed_time = end_time - start_time

    print("Elapsed time: ", elapsed_time)

    write_results(res=res, out_path=out_path)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='pyREDi Python Package. © ARUP 2023')
    parser.add_argument('-a', type=str, default=None, help='Path to the asset JSON file [str]')
    parser.add_argument('-c', type=str, default=None, help='Path to the components JSON file [str] (optional - REDi will use built-in FEMA P-58-2 component library if blank)')
    parser.add_argument('-r', type=str, default=None, help='Path of the results file (include the .json suffix in path)')
    parser.add_argument('-s', type=int, default=0, help='Seed for the random number generator, for deterministic output [int] (optional - leave blank for stochastic output)')
    parser.add_argument('-b', type=int, default=0, help='Burn-in number, i.e., how many times to generate and discard random numbers at random number generator initialization [int] (optional - mainly for testing purposes)')

    args = parser.parse_args()

    # Check for the required arguments
    if args.a is None or len(args.a) == 0:
        print("Path to asset JSON file is required")
        exit()

    if args.r is None or len(args.r) == 0:
        print("Path of the results file is required")
        exit()
    else :
        out_path = Path(args.r)

        if out_path.suffix != '.json':
            print(f"The results path provided {out_path} is invalid. The path needs to end in .json")
            exit()


    main(args)