import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.integrate import solve_ivp

# Parámetros
g = 9.81
L = 1.0

# Sistema del péndulo
def pendulo(t, y):
    theta, omega = y
    return [omega, -(g / L) * np.sin(theta)]

# Condiciones iniciales
theta0 = np.pi / 4   # 45 grados
omega0 = 0
y0 = [theta0, omega0]

# Tiempo de simulación
t_inicio = 0
t_fin = 10
num_puntos = 300
t_eval = np.linspace(t_inicio, t_fin, num_puntos)

# Resolver ecuación diferencial
sol = solve_ivp(pendulo, [t_inicio, t_fin], y0, t_eval=t_eval)

# Ángulo en el tiempo
theta = sol.y[0]

# Convertir a coordenadas cartesianas
x = L * np.sin(theta)
y = -L * np.cos(theta)

# Crear figura
fig, ax = plt.subplots()
ax.set_xlim(-1.2 * L, 1.2 * L)
ax.set_ylim(-1.2 * L, 0.2 * L)
ax.set_aspect('equal')
ax.grid()

# Elementos de la animación
linea, = ax.plot([], [], 'o-', lw=2)
trayectoria, = ax.plot([], [], '--', lw=1)
texto_tiempo = ax.text(0.05, 0.9, '', transform=ax.transAxes)

# Para guardar la trayectoria
x_tray = []
y_tray = []

def init():
    linea.set_data([], [])
    trayectoria.set_data([], [])
    texto_tiempo.set_text('')
    return linea, trayectoria, texto_tiempo

def actualizar(frame):
    x_p = x[frame]
    y_p = y[frame]

    # dibuja varilla y masa
    linea.set_data([0, x_p], [0, y_p])

    # guarda trayectoria de la masa
    x_tray.append(x_p)
    y_tray.append(y_p)
    trayectoria.set_data(x_tray, y_tray)

    texto_tiempo.set_text(f'Tiempo = {sol.t[frame]:.2f} s')
    return linea, trayectoria, texto_tiempo

ani = FuncAnimation(
    fig,
    actualizar,
    frames=len(sol.t),
    init_func=init,
    blit=True,
    interval=30
)

plt.show()