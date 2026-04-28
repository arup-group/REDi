
import json
import math

import numpy as np


def _sanitize_for_json(obj):
    """Recursively prepare an object for stdlib JSON serialization.

    Replaces NaN and +/-Infinity with None (mirroring simplejson's
    ``ignore_nan=True`` behavior) and converts numpy arrays to nested
    lists. Numpy integer/float scalars are coerced to native Python
    int/float so the stdlib encoder accepts them.
    """
    if isinstance(obj, np.ndarray):
        return _sanitize_for_json(obj.tolist())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(x) for x in obj]
    return obj


def write_results(res : dict, out_path : str) :

    # Open a file for writing
    with open(out_path, "w") as f:
        # Write the JSON string to the file
        json.dump(obj=_sanitize_for_json(res), fp=f, sort_keys=True, indent=4 * ' ')
