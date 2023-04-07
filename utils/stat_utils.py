
import numpy as np
from scipy.stats import lognorm, truncnorm, uniform
from typing import List

# Global values
RANDOM_SEED = None
rng = np.random.default_rng()


def set_seed(seed : int = 0, 
             burn_in : int = 0):
    
    global rng
    global RANDOM_SEED

    if seed : 
        RANDOM_SEED = seed
        rng = np.random.default_rng(seed=seed)
    
    if burn_in :
       test = rng.random(burn_in)
    #    for val in test : 
    #        print(val)


def gen_random() -> float :
    rnd_num = rng.random()
    # print(rnd_num)

    return rnd_num


def sample_dist(distribution : str,
                var1 : float,
                var2 : float) :

    # Lognormal sample
    if distribution.lower() in ["lognormal", "log normal"]:
        mean = var1
        beta = var2

        rnd_num = gen_random()

        if mean == 0.0 : 
            return 0.0 

        return lognorm.ppf(rnd_num, s=beta, scale=np.exp(np.log(mean)))

    # Normal sample
    # We are assuming every normally distributed variable is actually truncated at zero
    elif distribution.lower() == "normal":
        mean = var1
        stdev = var2
        rnd_num = gen_random()
        return truncnorm.ppf(rnd_num, a=0, b=np.inf, loc=mean, scale=stdev)

    # Uniform sample
    elif distribution.lower() == "uniform":
        lower_bound = var1
        upper_bound = var2
        rnd_num = gen_random()
        return uniform.ppf(rnd_num, loc=lower_bound, scale=upper_bound-lower_bound)

    # Return error if the distribution doesn't exist
    else:
        raise ValueError(f"Error: Invalid distribution specified. {distribution} does not have a sampling function")


def get_percentile(distribution : str,
                   var1 : float,
                   var2: float,
                   x : float) :

    """
    Gets the percentile (from CDF) associated with a distribution and random variable x
    
    Args:
    distribution (str): type of distribution
    var1 (float): first parameter of distribution
    var2 (float): second parameter of distribution
    x (float): random variable
    
    Returns:
    float: percentile (from CDF) associated with a distribution and random variable x
    """
    
    # Lognormal distribution
    if distribution.lower() == "lognormal":
        mean = var1
        beta = var2
        return lognorm.cdf(x, s=beta, scale=np.exp(np.log(mean)))
    
    # Normal distribution
    # We are assuming every normally distributed variable is actually truncated at zero
    elif distribution.lower() == "normal":
        mean = var1
        stdev = var2
        return truncnorm.cdf(0, np.inf, loc=mean, scale=stdev, a=(0-mean)/stdev, b=np.inf)
    
    # Uniform distribution
    elif distribution.lower() == "uniform":
        lower_bound = var1
        upper_bound = var2
        return uniform.cdf(x, loc=lower_bound, scale=upper_bound-lower_bound)
    
    # Return error if the distribution doesn't exist
    else:
        raise ValueError(f"Error: Invalid distribution specified. {distribution} does not have a sampling function")


def deepArray2matrix(ndarray : np.ndarray,
                     nRow : int,
                     nCol : int) :
    
    r = np.zeros((nRow, nCol))
    
    for i in range(nRow):
        r[i,:] = ndarray[i].T
        
    return r
