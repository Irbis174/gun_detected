import numpy as np
import torch

def zeros():
    return np.zeros(5)

def cuda():
    return torch.cuda.is_available()