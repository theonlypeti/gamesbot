def mapvalues(x, in_min, in_max, out_min, out_max) -> float:
    return float((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)