import matplotlib.pyplot as plt
import numpy as np
import os

def plot_results(path):
    if not os.path.exists(path): return
    files = [f for f in os.listdir(path) if f.endswith('.csv')]
    if not files: return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    for f in files:
        name = f.replace('.csv', '').split('_')[0]
        d = np.loadtxt(os.path.join(path, f), delimiter=',', skiprows=1)
        ax1.plot(d[:,0], d[:,1], label=name)
        ax2.plot(d[:,0], d[:,2], label=name)
    
    ax1.set_title(f'{path} - x1'); ax2.set_title(f'{path} - x2')
    ax1.grid(True); ax2.grid(True)
    ax1.legend(); ax2.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(path, 'plot.png'))
    plt.close()

if __name__ == "__main__":
    for i in range(1, 5):
        plot_results(f'results/{i}')
    #plot_results('results/2/0.01')