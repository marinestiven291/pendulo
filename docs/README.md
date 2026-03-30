# Guía de modularización del proyecto Péndulo

## Objetivo

Transformar `main.py` (monolítico) en un diseño donde cada responsabilidad vive en un módulo propio. Resultado: código más fácil de leer, probar y reutilizar.

> **Documentación de referencia general:**
> - [Tutorial oficial de módulos en Python](https://docs.python.org/es/3/tutorial/modules.html)
> - [Guía de estilo PEP 8 (convenciones de nombres y estructura)](https://peps.python.org/pep-0008/)

---

## Estado actual — diagnóstico real archivo por archivo

### [main.py](../main.py) — hace todo junto (el problema)

Contiene en un solo archivo:
- definición de parámetros físicos (`g`, `L`)
- condiciones iniciales (`theta0`, `omega0`)
- la ecuación diferencial (`def pendulo`)
- la resolución numérica (`solve_ivp`)
- la conversión a coordenadas cartesianas
- la configuración de la figura de matplotlib
- las funciones de animación (`init`, `actualizar`)
- el lanzamiento de la animación (`FuncAnimation`, `plt.show()`)

**Problema concreto:** si quisieras cambiar solo el ángulo inicial, tendrías que abrir el mismo archivo donde también está toda la animación. No hay separación de capas.

---

### [modulo_val_inicial.py](../modulo_val_inicial.py) — casi correcto

```python
import numpy as np

g = 9.81
L = 1.0

theta0 = np.pi / 4
omega0 = 0
```

**Lo que falta:** no define `t_inicio`, `t_fin`, `num_puntos`. Esos valores terminan hardcodeados en `main.py` aunque también son "condiciones iniciales" del experimento.

---

### [modulo_diferencilal.py](../modulo_diferencilal.py) — roto en varios niveles

```python
import numpy as np
from scipy.integrate import solve_ivp
from modulo_diferencilal import pendulo      # ← ERROR 1
from modulo_val_inicial import g, L, theta0, omega0

def pendulo(t, y):                           # ← ERROR 2
#importo los valores
    angulo, vel_angular = val_sistema        # ← ERROR 3
```

**Error 1 — importación circular:** el archivo se importa a sí mismo (`from modulo_diferencilal import pendulo`). Python lanzaría `ImportError: cannot import name 'pendulo' from partially initialized module`.

**Error 2 — función incompleta:** `def pendulo(t, y):` nunca tiene un `return`. Sin `return`, la función devuelve `None`, y `solve_ivp` fallaría con `TypeError`.

**Error 3 — variable inexistente:** `val_sistema` no está definida en ningún lado. Lanzaría `NameError: name 'val_sistema' is not defined` en el primer frame.

**Error de diseño adicional:** `g` y `L` se importan como variables globales del módulo. Esto acopla la función ODE directamente a ese módulo de configuración — no puedes reutilizarla con otros valores sin editar los imports.

---

### [modulo_grafico.py](../modulo_grafico.py) — vacío

Sin implementación. Toda la lógica de animación sigue en `main.py`.

---

## Flujo de datos E2E — cómo debe fluir la información

```
modulo_val_inicial.py
        │
        │  g, L, theta0, omega0, t_inicio, t_fin, num_puntos
        ▼
    main.py  ──────────────────────────────────────────┐
        │                                               │
        │  construye y0, t_span, t_eval                │
        │  llama a resolver_pendulo(...)                │
        ▼                                               │
modulo_simulacion.py                                    │
        │  recibe: y0, t_span, t_eval, g, L            │
        │  llama internamente a pendulo(t, y, g, L)    │
        │  de modulo_diferencial.py                     │
        │  devuelve: objeto sol (OdeResult)             │
        ▼                                               │
    main.py                                            │
        │  recibe sol                                   │
        │  llama a crear_animacion(sol, L)             │
        ▼                                               │
modulo_grafico.py                                      │
        │  recibe: sol, L                              │
        │  calcula x[], y[] (coordenadas cartesianas)  │
        │  construye fig, ax, FuncAnimation            │
        │  devuelve: ani (objeto animación)            │
        ▼                                               │
    main.py ◄──────────────────────────────────────────┘
        │  llama plt.show()
        ▼
   [ventana con animación]
```

**Punto clave:** los datos físicos (`g`, `L`) viajan como **argumentos de función**, no como variables globales importadas dentro de los módulos de lógica. Esto se hace con el parámetro `args=(g, L)` de `solve_ivp`.

---

## Plan de implementación — paso a paso E2E

### Paso 1 — Corregir y completar `modulo_val_inicial.py`

> **Referencias:** [Constantes en Python (PEP 8)](https://peps.python.org/pep-0008/#constants) · [numpy.pi](https://numpy.org/doc/stable/reference/constants.html)

**Qué hacer:** agregar las variables de tiempo que ahora están sueltas en `main.py`.

```python
import numpy as np

# Parámetros físicos del sistema
G = 9.81   # aceleración gravitacional [m/s²]
L = 1.0    # longitud de la varilla [m]

# Condiciones iniciales
theta0 = np.pi / 4   # ángulo inicial = 45° en radianes
omega0 = 0.0         # velocidad angular inicial [rad/s]

# Parámetros de simulación temporal
t_inicio = 0.0
t_fin = 10.0
num_puntos = 300
```

**Por qué `G` en mayúscula:** en Python, las mayúsculas indican constante por convención (PEP 8). También evita colisionar con la variable local `g` que podrías usar dentro de funciones.

**Por qué separar el tiempo aquí:** `t_fin` y `num_puntos` son parámetros del experimento igual que `theta0`. Si cambias el experimento, modificas solo este archivo.

**Cómo verificarlo:** ejecuta en la terminal:
```bash
python -c "from modulo_val_inicial import G, L, theta0, omega0, t_inicio, t_fin, num_puntos; print(G, L, theta0)"
# Salida esperada: 9.81 1.0 0.7853981633974483
```

---

### Paso 2 — Reescribir `modulo_diferencial.py` (corregir el nombre también)

> **Referencias:** [Definir funciones en Python](https://docs.python.org/es/3/tutorial/controlflow.html#defining-functions) · [numpy.sin](https://numpy.org/doc/stable/reference/generated/numpy.sin.html) · [Sistemas de EDOs (Wikipedia)](https://es.wikipedia.org/wiki/Ecuaci%C3%B3n_diferencial_ordinaria)

**Qué hacer:** eliminar todo el contenido roto y reemplazar por la función ODE correcta.

> Nota: el archivo original se llama `modulo_diferencilal.py` (con errata). Puedes renombrarlo a `modulo_diferencial.py` para consistencia. Si lo renombras, actualiza todos los imports.

```python
import numpy as np


def pendulo(t, y, g, L):
    """
    Sistema de ecuaciones diferenciales del péndulo simple.

    Parámetros
    ----------
    t : float
        Tiempo actual (solve_ivp lo pasa automáticamente, no lo usas
        directamente aquí pero la firma lo exige).
    y : list [theta, omega]
        Estado actual: ángulo theta [rad] y velocidad angular omega [rad/s].
    g : float
        Aceleración gravitacional [m/s²].
    L : float
        Longitud de la varilla [m].

    Retorna
    -------
    [dtheta/dt, domega/dt] : list
        Derivadas del estado. solve_ivp las integra numéricamente.
    """
    theta, omega = y
    dtheta_dt = omega
    domega_dt = -(g / L) * np.sin(theta)
    return [dtheta_dt, domega_dt]
```

**Por qué `g` y `L` como argumentos y no importados:** la función ODE debe ser "pura" — sin dependencias ocultas de módulos externos. Esto permite:
- Probarla con cualquier valor de `g` y `L` sin tocar imports.
- Reutilizarla en un péndulo en la Luna (`g=1.62`) cambiando solo la llamada.
- `solve_ivp` la recibe a través del parámetro `args=(g, L)`.

**Por qué `t` aparece aunque no se usa:** `solve_ivp` siempre llama a la función ODE con la firma `f(t, y)`. Al agregar `args=(g, L)`, la firma se convierte en `f(t, y, g, L)`. El argumento `t` es obligatorio aunque en el péndulo simple la ecuación no depende explícitamente del tiempo (sistema autónomo).

**Cómo verificarlo:**
```bash
python -c "
from modulo_diferencial import pendulo
import numpy as np
# Estado: theta=45°, omega=0
resultado = pendulo(0, [np.pi/4, 0], 9.81, 1.0)
print(resultado)
# Salida esperada: [0, -6.937...]
# (omega=0 → dtheta/dt=0; aceleración negativa porque el péndulo cae)
"
```

---

### Paso 3 — Crear `modulo_simulacion.py` (módulo nuevo)

> **Referencias:** [scipy.integrate.solve_ivp — documentación completa](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html) · [Métodos de integración numérica disponibles en solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html#scipy.integrate.solve_ivp) · [numpy.linspace](https://numpy.org/doc/stable/reference/generated/numpy.linspace.html)

**Qué hace:** envuelve la llamada a `solve_ivp` en una función con nombre descriptivo.

```python
from scipy.integrate import solve_ivp
from modulo_diferencial import pendulo


def resolver_pendulo(y0, t_span, t_eval, g, L):
    """
    Resuelve la ODE del péndulo entre t_span[0] y t_span[1].

    Parámetros
    ----------
    y0 : list [theta0, omega0]
        Condiciones iniciales.
    t_span : tuple (t_inicio, t_fin)
        Intervalo de integración.
    t_eval : array
        Instantes donde se quieren resultados (numpy linspace).
    g, L : float
        Parámetros físicos pasados a la función ODE.

    Retorna
    -------
    sol : OdeResult
        Objeto de scipy. Accedes a sol.t (tiempos) y sol.y (estados).
        sol.y tiene forma (2, num_puntos): fila 0 = theta, fila 1 = omega.
    """
    sol = solve_ivp(
        pendulo,
        t_span,
        y0,
        t_eval=t_eval,
        args=(g, L),
        dense_output=False
    )
    return sol
```

**Por qué `args=(g, L)`:** este es el mecanismo de `solve_ivp` para pasar parámetros extra a la función ODE. Sin esto, `pendulo` recibiría solo `(t, y)` y fallaría con `TypeError: pendulo() missing 2 required positional arguments: 'g' and 'L'`.

**Qué contiene `sol` (el objeto de retorno):**
```
sol.t          → array de tiempos, forma (300,)
sol.y          → array de estados, forma (2, 300)
sol.y[0]       → array de ángulos theta en cada instante
sol.y[1]       → array de velocidades angulares omega en cada instante
sol.success    → True si la integración convergió sin error
sol.message    → mensaje del solver (útil para depuración)
```

**Cómo verificarlo:**
```bash
python -c "
import numpy as np
from modulo_simulacion import resolver_pendulo

y0 = [np.pi/4, 0.0]
t_span = (0.0, 10.0)
t_eval = np.linspace(0, 10, 300)

sol = resolver_pendulo(y0, t_span, t_eval, 9.81, 1.0)
print('Éxito:', sol.success)
print('Forma de sol.y:', sol.y.shape)   # (2, 300)
print('Theta inicial:', sol.y[0][0])    # ~0.785 rad = 45°
print('Theta en t=5s:', sol.y[0][150])  # valor oscilante
"
```

---

### Paso 4 — Implementar `modulo_grafico.py`

> **Referencias:** [matplotlib.animation.FuncAnimation](https://matplotlib.org/stable/api/_as_gen/matplotlib.animation.FuncAnimation.html) · [matplotlib.pyplot.subplots](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html) · [Guardar animaciones como .gif o .mp4](https://matplotlib.org/stable/api/_as_gen/matplotlib.animation.Animation.save.html)

**Qué hace:** recibe el resultado de la simulación y construye la animación. Devuelve el objeto `ani` para que `main.py` lo muestre.

```python
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


def crear_animacion(sol, L):
    """
    Construye la animación del péndulo a partir de la solución ODE.

    Parámetros
    ----------
    sol : OdeResult
        Resultado de solve_ivp. Debe contener sol.t y sol.y.
    L : float
        Longitud de la varilla. Determina los límites del gráfico.

    Retorna
    -------
    ani : FuncAnimation
        Objeto de animación. main.py debe mantener una referencia a él
        (no descartarlo), o matplotlib lo destruye y la animación no corre.
    """
    # Extraer ángulos y convertir a coordenadas cartesianas
    theta = sol.y[0]
    x = L * np.sin(theta)    # posición horizontal de la masa
    y = -L * np.cos(theta)   # posición vertical (negativa = hacia abajo)

    # Crear figura y configurar ejes
    fig, ax = plt.subplots()
    ax.set_xlim(-1.2 * L, 1.2 * L)
    ax.set_ylim(-1.2 * L, 0.2 * L)
    ax.set_aspect('equal')   # evita que el péndulo parezca ovalado
    ax.grid()

    # Elementos gráficos: línea = varilla+masa, trayectoria = rastro
    linea, = ax.plot([], [], 'o-', lw=2)
    trayectoria, = ax.plot([], [], '--', lw=1, alpha=0.5)
    texto_tiempo = ax.text(0.05, 0.9, '', transform=ax.transAxes)

    # Lista mutable para acumular la trayectoria frame a frame
    x_tray = []
    y_tray = []

    def init():
        """Estado inicial vacío. blit=True la llama al arrancar."""
        linea.set_data([], [])
        trayectoria.set_data([], [])
        texto_tiempo.set_text('')
        return linea, trayectoria, texto_tiempo

    def actualizar(frame):
        """Se llama una vez por frame. frame va de 0 a len(sol.t)-1."""
        x_p = x[frame]
        y_p = y[frame]

        # Varilla: desde el pivote (0,0) hasta la masa (x_p, y_p)
        linea.set_data([0, x_p], [0, y_p])

        # Trayectoria: acumula todas las posiciones anteriores
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
        blit=True,      # solo redibuja los artistas que cambiaron (más rápido)
        interval=30     # milisegundos entre frames (~33 fps)
    )

    return ani
```

**Por qué devolver `ani` en lugar de llamar `plt.show()` aquí:** `modulo_grafico.py` es responsable de construir la animación, no de mostrarla. Mostrarla es responsabilidad de `main.py`. Esto permite, por ejemplo, guardar la animación como `.gif` o `.mp4` desde `main.py` sin modificar `modulo_grafico.py`.

**Por qué `x_tray` y `y_tray` son listas (no arrays):** se usan `.append()` dentro de `actualizar()`, que es un closure. Las listas de Python son mutables y el closure las captura por referencia. Si fueran arrays de numpy, necesitarías reasignarlos (lo que no funcionaría en un closure de la misma forma).

**Por qué `blit=True`:** con `blit=True`, matplotlib solo redibuja los artistas que devuelve `actualizar()`. Sin él, redibuja toda la figura en cada frame, lo que es mucho más lento.

---

### Paso 5 — Reescribir `main.py` como orquestador puro

> **Referencias:** [Sistema de imports de Python — referencia completa](https://docs.python.org/es/3/reference/import.html) · [`if __name__ == '__main__'` explicado](https://docs.python.org/es/3/library/__main__.html)

```python
import numpy as np
import matplotlib.pyplot as plt

from modulo_val_inicial import G as g, L, theta0, omega0, t_inicio, t_fin, num_puntos
from modulo_simulacion import resolver_pendulo
from modulo_grafico import crear_animacion


# Construir condiciones iniciales y grilla temporal
y0 = [theta0, omega0]
t_span = (t_inicio, t_fin)
t_eval = np.linspace(t_inicio, t_fin, num_puntos)

# Resolver la ODE
sol = resolver_pendulo(y0, t_span, t_eval, g, L)

# Crear y mostrar la animación
ani = crear_animacion(sol, L)   # IMPORTANTE: guardar referencia a ani
plt.show()
```

**Por qué `G as g`:** `modulo_val_inicial.py` exporta `G` (mayúscula por convención de constante). Al importarlo con alias `g`, el resto de `main.py` puede usar `g` como si fuera la variable original, sin cambiar ningún otro código.

**Por qué `ani = crear_animacion(...)` en lugar de solo `crear_animacion(...)`:** si no guardas la referencia al objeto `FuncAnimation`, Python's garbage collector puede destruirlo antes de que la ventana termine de mostrar la animación. Esto produce una animación congelada o que no corre. Guardar `ani = ...` mantiene la referencia viva.

---

## Errores comunes y cómo evitarlos

| Error | Causa | Solución |
|-------|-------|----------|
| `ImportError: cannot import name 'pendulo' from partially initialized module 'modulo_diferencilal'` | El módulo se importa a sí mismo | Eliminar `from modulo_diferencilal import pendulo` dentro de ese mismo archivo |
| `TypeError: pendulo() missing 2 required positional arguments: 'g' and 'L'` | `solve_ivp` no tiene `args=(g, L)` | Agregar `args=(g, L)` en la llamada a `solve_ivp` |
| `NameError: name 'np' is not defined` en `modulo_grafico.py` | Falta `import numpy as np` | Agregar el import al inicio del módulo |
| Animación congelada | No se guarda referencia a `ani` | Asignar `ani = crear_animacion(...)` |
| `NameError: name 'val_sistema' is not defined` | Variable inventada en el código roto | Reemplazar con `theta, omega = y` |

---

## Flujo de imports — quién importa a quién

```
main.py
  ├── from modulo_val_inicial  → G, L, theta0, omega0, t_inicio, t_fin, num_puntos
  ├── from modulo_simulacion   → resolver_pendulo
  └── from modulo_grafico      → crear_animacion

modulo_simulacion.py
  └── from modulo_diferencial  → pendulo

modulo_diferencial.py
  └── import numpy             (sin imports propios del proyecto)

modulo_val_inicial.py
  └── import numpy             (sin imports propios del proyecto)

modulo_grafico.py
  ├── import numpy
  └── import matplotlib        (sin imports propios del proyecto)
```

**Regla de oro:** ningún módulo de lógica (`modulo_diferencial`, `modulo_grafico`) importa de otro módulo del proyecto. Solo `main.py` y `modulo_simulacion.py` coordinan módulos. Esto evita importaciones circulares y dependencias ocultas.

---

## Estructura final de archivos

```
pendulo/
  main.py                ← orquestador: importa todo, no tiene lógica propia
  modulo_val_inicial.py  ← constantes y condiciones del experimento
  modulo_diferencial.py  ← función ODE pura (sin imports del proyecto)
  modulo_simulacion.py   ← resuelve la ODE, llama a solve_ivp
  modulo_grafico.py      ← construye la animación matplotlib
  docs/
    README.md
```

---

## Pasos concretos de reemplazo (resumen ejecutable)

1. **`modulo_val_inicial.py`** — agregar `t_inicio`, `t_fin`, `num_puntos`; renombrar `g` a `G`.
2. **`modulo_diferencial.py`** — borrar todo; escribir `def pendulo(t, y, g, L)` con el `return` correcto; sin imports del proyecto.
3. **`modulo_simulacion.py`** — crear archivo nuevo; escribir `def resolver_pendulo(...)` que llama a `solve_ivp` con `args=(g, L)`.
4. **`modulo_grafico.py`** — implementar `def crear_animacion(sol, L)` que retorna `ani`.
5. **`main.py`** — borrar toda la lógica; dejar solo imports y tres llamadas: `resolver_pendulo`, `crear_animacion`, `plt.show()`.

---

## Verificación del flujo completo

Desde la carpeta `pendulo/`, ejecutar:

```bash
python main.py
```

Si todo está bien, se abre la ventana de matplotlib con el péndulo animado. Si aparece cualquier error de import, verificar el diagrama de imports de arriba para identificar qué módulo tiene el problema.

---

## Cómo importar y exportar entre archivos — guía desde cero

> **Referencias:** [Tutorial de módulos e imports (Python oficial)](https://docs.python.org/es/3/tutorial/modules.html) · [Sentencia `import` — referencia técnica](https://docs.python.org/es/3/reference/simple_stmts.html#the-import-statement) · [Guía de imports en Real Python (inglés, muy completa)](https://realpython.com/python-import/)

En Python no existe una palabra clave `export` como en otros lenguajes. **Todo lo que defines en un archivo (variable, función, clase) queda disponible automáticamente para ser importado desde otro archivo.** No hay que hacer nada especial para "exportar".

El trabajo es solo del lado del que **importa**: decir de dónde traer qué cosa.

---

### Concepto base: qué es un módulo

Cada archivo `.py` es un módulo. Su nombre como módulo es el nombre del archivo sin la extensión:

```
modulo_val_inicial.py  →  nombre del módulo: modulo_val_inicial
modulo_grafico.py      →  nombre del módulo: modulo_grafico
```

Para usar algo de otro archivo, usas `import` o `from ... import`.

---

### Forma 1 — `import modulo` (importar el módulo completo)

Traes el archivo entero. Para usar algo de él, escribes `modulo.cosa`.

```python
# En main.py
import modulo_val_inicial

print(modulo_val_inicial.G)        # → 9.81
print(modulo_val_inicial.theta0)   # → 0.785...
```

**Cuándo usarlo:** cuando vas a usar muchas cosas del mismo módulo y quieres dejar claro de dónde viene cada cosa.

---

### Forma 2 — `from modulo import cosa` (importar solo lo que necesitas)

Traes una o varias cosas puntuales. Las usas directamente, sin prefijo.

```python
# En main.py
from modulo_val_inicial import G, L, theta0

print(G)       # → 9.81       (sin prefijo)
print(L)       # → 1.0
print(theta0)  # → 0.785...
```

**Cuándo usarlo:** cuando solo necesitas algunas cosas del módulo. Hace el código más limpio.

---

### Forma 3 — `from modulo import cosa as alias` (importar con otro nombre)

Le das un nombre distinto a lo que importas. Útil para evitar colisiones o acortar nombres.

```python
# En main.py
from modulo_val_inicial import G as g   # G se llama g dentro de este archivo

print(g)   # → 9.81
```

**Por qué se usa en este proyecto:** `modulo_val_inicial.py` define `G` (mayúscula, convención de constante). `main.py` lo importa como `g` (minúscula) para pasarlo a funciones que esperan `g`.

---

### Forma 4 — importar una función y llamarla

Las funciones se importan igual que las variables.

```python
# modulo_diferencial.py define:
def pendulo(t, y, g, L):
    theta, omega = y
    return [omega, -(g / L) * np.sin(theta)]


# modulo_simulacion.py la importa y la usa:
from modulo_diferencial import pendulo

resultado = pendulo(0, [0.785, 0], 9.81, 1.0)
print(resultado)   # → [0, -6.937...]
```

---

### Forma 5 — importar múltiples cosas en una línea

```python
from modulo_val_inicial import G, L, theta0, omega0, t_inicio, t_fin, num_puntos
```

Cada nombre separado por coma. Si son muchos, puedes partirlo en varias líneas con paréntesis:

```python
from modulo_val_inicial import (
    G,
    L,
    theta0,
    omega0,
    t_inicio,
    t_fin,
    num_puntos,
)
```

---

### Forma 6 — `from modulo import *` (importar todo, no recomendado)

```python
from modulo_val_inicial import *   # trae G, L, theta0, omega0...
```

**Por qué evitarlo:** no queda claro qué variables vinieron de dónde. Si dos módulos definen `L`, una sobreescribe a la otra sin aviso. Solo se usa en casos muy específicos.

---

### Qué NO hace falta hacer para "exportar"

En Python **no necesitas** ninguna de estas cosas para que otro archivo pueda importar tu código:

- No existe `export` ni `module.exports`
- No hay que registrar el archivo en ningún lado
- No hay que agregar nada al final del archivo
- Solo define la variable o función normalmente, y ya está disponible

```python
# modulo_val_inicial.py — simplemente defines y listo
G = 9.81        # cualquier otro archivo puede hacer: from modulo_val_inicial import G
L = 1.0
theta0 = 0.785
```

---

### Condición para que el import funcione: los archivos deben estar en la misma carpeta

Si `main.py` y `modulo_val_inicial.py` están en la misma carpeta `pendulo/`, el import funciona directamente:

```
pendulo/
  main.py
  modulo_val_inicial.py   ← mismo nivel, import directo
```

```python
# main.py
from modulo_val_inicial import G   # ✓ funciona
```

Si estuvieran en carpetas distintas, necesitarías configuración extra (no es el caso aquí).

---

### Resumen visual — qué formas usar en cada situación

| Situación | Forma recomendada | Ejemplo |
|-----------|-------------------|---------|
| Usar pocas cosas de un módulo | `from modulo import x, y` | `from modulo_val_inicial import G, L` |
| Importar función para usar | `from modulo import funcion` | `from modulo_diferencial import pendulo` |
| Renombrar al importar | `from modulo import X as x` | `from modulo_val_inicial import G as g` |
| Usar muchas cosas, dejar claro el origen | `import modulo` + `modulo.x` | `import modulo_val_inicial` → `modulo_val_inicial.G` |
| Exportar algo | (nada, es automático) | solo define la variable o función en el archivo |

---

### Ejemplo completo aplicado al proyecto

```
modulo_val_inicial.py       →  define G, L, theta0, omega0, t_inicio, t_fin, num_puntos
modulo_diferencial.py       →  define pendulo(t, y, g, L)
modulo_simulacion.py        →  define resolver_pendulo(y0, t_span, t_eval, g, L)
modulo_grafico.py           →  define crear_animacion(sol, L)
```

```python
# main.py — importa de cada módulo lo que necesita

from modulo_val_inicial import G as g, L, theta0, omega0, t_inicio, t_fin, num_puntos
#                              ↑ variable  ↑ alias   ↑ más variables del mismo módulo

from modulo_simulacion import resolver_pendulo
#                              ↑ función definida en modulo_simulacion.py

from modulo_grafico import crear_animacion
#                          ↑ función definida en modulo_grafico.py
```

```python
# modulo_simulacion.py — importa solo lo que necesita de modulo_diferencial

from modulo_diferencial import pendulo
#                              ↑ función ODE que solve_ivp va a llamar internamente
```

Cada archivo importa **solo lo que realmente usa**. Nada más.

---

## Cómo decidir qué extraer a un módulo — el criterio de diseño

> **Referencias:** [Principio de responsabilidad única (Wikipedia)](https://es.wikipedia.org/wiki/Principio_de_responsabilidad_%C3%BAnica) · [Cómo estructurar proyectos Python (Real Python, inglés)](https://realpython.com/python-application-layouts/)

Saber la sintaxis del import no alcanza. La pregunta real es: **¿cuándo tiene sentido separar código en otro archivo?**

### La pregunta que debes hacerte

> "¿Podría describir lo que hace este bloque en una sola frase sin usar 'y'?"

Si la frase necesita un "y", el bloque hace dos cosas distintas y probablemente debería dividirse.

```
"Calcula la posición del péndulo"          → una responsabilidad ✓
"Calcula la posición y dibuja la gráfica"  → dos responsabilidades, separar ✗
"Define los parámetros y los imprime"      → dos responsabilidades, separar ✗
```

### Ejemplos malos vs buenos

**Mal — un módulo hace demasiado:**
```python
# modulo_todo.py
G = 9.81
L = 1.0

def pendulo(t, y, g, L):       # ecuación diferencial
    ...

def crear_animacion(sol, L):   # gráfico
    ...
```
Mezcla datos, física y visualización. Si cambias el gráfico, abres el mismo archivo donde está la física.

**Bien — cada módulo tiene una responsabilidad:**
```python
# modulo_val_inicial.py  → solo datos y constantes
# modulo_diferencial.py  → solo la ecuación física
# modulo_grafico.py      → solo la visualización
```

### Señales de que algo debería ser su propio módulo

- Lo vas a reutilizar en otro proyecto o script.
- Tiene sus propias dependencias (`import`) que el resto no necesita.
- Podrías probarlo de forma independiente sin ejecutar todo el programa.
- Tiene más de ~50 líneas y hace una sola cosa claramente nombrable.

### Señales de que NO vale la pena separar

- Es una sola línea o un cálculo trivial.
- Solo lo usas en un lugar y nunca lo reutilizarás.
- Separarlo obligaría a pasar 10 argumentos entre archivos — eso es señal de que el diseño no está listo todavía.

---

## `if __name__ == '__main__'` — la trampa silenciosa más común

> **Referencias:** [`__main__` — documentación oficial](https://docs.python.org/es/3/library/__main__.html) · [Explicación detallada de `__name__` (Real Python, inglés)](https://realpython.com/if-name-main-python/)

Este es el error que más destroza módulos de principiantes y es difícil de diagnosticar porque **no lanza ningún error**, simplemente hace cosas inesperadas.

### El problema: código suelto en un módulo

Cuando importas un archivo, Python **ejecuta todo el código que está fuera de funciones**.

```python
# modulo_val_inicial.py — versión con bug silencioso
G = 9.81
L = 1.0

print("Parámetros cargados")           # ← código suelto
sol = resolver_algo()                  # ← código suelto — se ejecuta al importar
```

Si `main.py` hace `from modulo_val_inicial import G`, Python ejecuta el archivo entero, incluyendo el `print` y la llamada a `resolver_algo()`. Eso pasa **cada vez** que cualquier archivo importe ese módulo.

### La solución: `if __name__ == '__main__'`

```python
# modulo_val_inicial.py — versión correcta
G = 9.81
L = 1.0

def mostrar_parametros():
    print(f"G={G}, L={L}")

# Este bloque SOLO se ejecuta si corres este archivo directamente
# No se ejecuta cuando otro archivo lo importa
if __name__ == '__main__':
    mostrar_parametros()
```

### Cómo funciona

Python asigna a la variable `__name__` el valor:
- `'__main__'` → cuando ejecutas ese archivo directamente (`python modulo_val_inicial.py`)
- `'modulo_val_inicial'` → cuando otro archivo lo importa

```
python modulo_val_inicial.py   →  __name__ == '__main__'  →  el bloque SÍ corre
python main.py (que lo importa) →  __name__ == 'modulo_val_inicial'  →  el bloque NO corre
```

### Regla práctica

**Todo código que "hace cosas" (print, cálculos, llamadas a funciones) que no sea una definición, debe ir dentro de una función o dentro de `if __name__ == '__main__'`.**

```python
# ✓ Correcto — solo definiciones en el nivel del módulo
G = 9.81          # asignación de constante: ok
L = 1.0

def pendulo(t, y, g, L):
    return [...]

# ✗ Incorrecto — código que "hace algo" suelto
print(G)                        # se ejecuta al importar
sol = solve_ivp(pendulo, ...)   # se ejecuta al importar — tarda y puede fallar
```

### Aplicado al proyecto

```python
# main.py — usa if __name__ == '__main__' para proteger el flujo principal

import numpy as np
import matplotlib.pyplot as plt
from modulo_val_inicial import G as g, L, theta0, omega0, t_inicio, t_fin, num_puntos
from modulo_simulacion import resolver_pendulo
from modulo_grafico import crear_animacion

if __name__ == '__main__':
    y0 = [theta0, omega0]
    t_eval = np.linspace(t_inicio, t_fin, num_puntos)
    sol = resolver_pendulo(y0, (t_inicio, t_fin), t_eval, g, L)
    ani = crear_animacion(sol, L)
    plt.show()
```

Así, si otro script importa algo de `main.py` en el futuro, la simulación no arranca sola.

---

## `return` vs variable global — cómo pasar datos entre módulos correctamente

> **Referencias:** [Sentencia `return` en Python](https://docs.python.org/es/3/reference/simple_stmts.html#the-return-statement) · [Variables y scope en Python (Real Python, inglés)](https://realpython.com/python-scope-legb-rule/) · [Por qué evitar variables globales (Stack Overflow)](https://stackoverflow.com/questions/19158339/why-are-global-variables-evil)

Este es el segundo error de diseño más común. Un módulo que "guarda" su resultado en una variable global en lugar de devolverlo con `return` rompe la independencia entre módulos.

### El problema: resultado guardado como global

```python
# modulo_simulacion.py — versión con bug de diseño
from modulo_val_inicial import G, L, theta0, omega0   # acoplado a un solo set de valores

y0 = [theta0, omega0]
sol = solve_ivp(pendulo, ...)   # ejecuta la simulación al importar

# Cualquier otro archivo importa así:
from modulo_simulacion import sol   # ← trae el resultado, no la capacidad de calcular
```

**Problemas:**
- La simulación corre sola cuando importas el módulo (el bug anterior).
- Solo puedes tener un resultado, con los valores de `modulo_val_inicial`. No puedes cambiar `theta0` sin editar el módulo.
- No puedes reutilizar este módulo para otro péndulo con distintos parámetros.

### La solución: función con `return`

```python
# modulo_simulacion.py — versión correcta
from scipy.integrate import solve_ivp
from modulo_diferencial import pendulo

def resolver_pendulo(y0, t_span, t_eval, g, L):
    sol = solve_ivp(pendulo, t_span, y0, t_eval=t_eval, args=(g, L))
    return sol   # ← devuelve el resultado, no lo guarda como global
```

```python
# main.py — recibe el resultado y decide qué hacer con él
sol = resolver_pendulo(y0, t_span, t_eval, g, L)   # ← captura lo que devuelve
```

### La regla de oro del flujo de datos entre módulos

```
módulo A  →  define una función  →  recibe parámetros  →  devuelve resultado
módulo B  →  importa la función  →  la llama con sus propios valores  →  captura el return
```

Los datos viajan como **argumentos de entrada** y **valores de retorno**. No como variables globales compartidas entre archivos.

### Cómo devolver múltiples valores

Python permite devolver varios valores a la vez con una tupla:

```python
def calcular_posicion(theta, L):
    x = L * np.sin(theta)
    y = -L * np.cos(theta)
    return x, y   # devuelve dos valores

# Quien llama la función los recibe así:
x_pos, y_pos = calcular_posicion(0.785, 1.0)
```

---

## Importaciones circulares — cómo evitar el error más frustrante

> **Referencias:** [Importaciones circulares en Python — explicación oficial](https://docs.python.org/es/3/faq/programming.html#what-are-the-best-practices-for-using-import-in-a-module) · [Cómo resolver circular imports (Real Python, inglés)](https://realpython.com/python-import/#handle-cyclical-imports)

Una importación circular ocurre cuando el archivo A importa de B, y B importa de A. Python no puede resolver el orden de carga y lanza `ImportError`.

### El error

```python
# modulo_diferencial.py
from modulo_simulacion import resolver_pendulo   # importa de simulacion

# modulo_simulacion.py
from modulo_diferencial import pendulo           # importa de diferencial
```

Python intenta cargar `modulo_diferencial` → necesita `modulo_simulacion` → necesita `modulo_diferencial` → bucle infinito → `ImportError`.

### La regla que elimina el 100% de los casos

Dibuja una flecha de A → B por cada "A importa de B". **Las flechas nunca deben formar un ciclo.**

```
main.py  →  modulo_simulacion  →  modulo_diferencial
main.py  →  modulo_grafico
main.py  →  modulo_val_inicial
```

Sin ciclos. Ningún módulo de lógica importa de otro módulo de lógica en dirección contraria.

### Señal de que vas a tener un ciclo

Si sientes que el módulo A "necesita saber" algo del módulo B y el módulo B ya importa de A, la solución no es cruzar la importación — es **mover ese dato compartido a un tercer módulo** (como `modulo_val_inicial.py`) del que ambos pueden importar sin depender entre sí.

```
              modulo_val_inicial
              ↑              ↑
    modulo_A                   modulo_B
```

Ambos importan de la fuente común. Nunca se importan entre sí.

---

## Checklist para crear un módulo nuevo desde cero

> **Referencias:** [Convenciones de nombres de archivos/módulos (PEP 8)](https://peps.python.org/pep-0008/#package-and-module-names) · [Cómo testear un módulo de forma aislada](https://docs.python.org/es/3/library/unittest.html)

Cuando quieras extraer algo a un nuevo archivo, seguí estos pasos:

```
[ ] 1. Dale un nombre que describa su responsabilidad (sustantivo o verbo)
        ✓ modulo_graficos.py, modulo_exportar.py
        ✗ modulo_misc.py, helpers.py, utils.py (demasiado vago)

[ ] 2. Define todo como funciones o constantes — sin código suelto

[ ] 3. Si querés probar el módulo solo, usá if __name__ == '__main__'

[ ] 4. Las funciones reciben sus datos como parámetros, no los importan
        de otros módulos del proyecto (excepto constantes de configuración)

[ ] 5. Las funciones devuelven su resultado con return

[ ] 6. Verifica que no haya ciclo de imports dibujando las flechas

[ ] 7. Prueba el módulo de forma aislada antes de integrarlo:
        python -c "from mi_modulo import mi_funcion; print(mi_funcion(...))"
```
