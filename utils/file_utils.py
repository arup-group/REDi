
import simplejson as json

import numpy as np

class CustomEncoder(json.JSONEncoder):
    
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()

        return json.JSONEncoder.default(self, obj)


def write_results(res : dict, out_path : str) :

    # as_json = json.dumps(res, cls=CustomEncoder, ignore_nan=True, sort_keys=True, indent=4 * ' ')

    # print(as_json)

    # Open a file for writing
    with open(out_path, "w") as f:
        # Write the JSON string to the file
        json.dump(obj=res, fp=f, cls=CustomEncoder, ignore_nan=True, sort_keys=True, indent=4 * ' ')