import numpy as np
import matplotlib.pyplot as plt

# evenly sampled time at 200ms intervals
t = np.arange(0., 10., 1)

# red dashes, blue squares and green triangles
plt.plot(t, t, t, t**2)
plt.show()