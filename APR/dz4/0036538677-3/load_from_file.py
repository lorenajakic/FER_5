import os

def load_config(config_file):
    e, alfa, t = 1e-6, 1.3, 1
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, config_file)

    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            key, value = line.split('=', 1)
            key = key.strip()
            if key == 'e': e = float(value.strip())
            elif key == 'alfa': alfa = float(value.strip())
            elif key == 't': t = float(value.strip())

    return e, alfa, t
