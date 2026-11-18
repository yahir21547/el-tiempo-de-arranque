# Cálculo de Tiempo de Arranque de Motores · Streamlit

Migración de la calculadora original de **Tkinter** a una aplicación web desplegable en **Streamlit**. Mantiene el estilo bilingüe, paneles de equipo/motor, búsqueda por MLFB, campos derivados, diagnóstico, arranques consecutivos en frío y caliente, arranques por hora, gráficas y reporte PDF.

> **Fuente original:** https://github.com/yahir21547/el-verdadero-calculo-de-timepo-de-aranque
>
> El comparador independiente de MLFB se excluye intencionadamente: esta entrega se centra en el cálculo de tiempo de arranque. La búsqueda de motores por MLFB sigue incluida.

## Cómo ejecutarla localmente (Windows 11)

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Se abrirá normalmente `http://localhost:8501`.

## Despliegue con un repositorio nuevo

1. Crea un repositorio de GitHub, por ejemplo `motor-startup-streamlit`.
2. Extrae **todo el contenido** del ZIP en la raíz de ese repositorio. Deben quedar `streamlit_app.py`, `requirements.txt`, `.streamlit/` y las carpetas `core/`, `services/`, `reports/`, `assets/`, `data/`, `tests/`, `scripts/`.
3. En [Streamlit Community Cloud](https://share.streamlit.io/), selecciona el repositorio, rama `main` y archivo principal `streamlit_app.py`.
4. Despliega. El sistema descargará automáticamente el Excel V46 y las imágenes originales desde el repositorio fuente **la primera vez** que se necesiten.

No necesitas seleccionar ni subir un Excel al iniciar. La primera visita requiere acceso a `raw.githubusercontent.com` para descargar los recursos originales, salvo que ya se hayan incluido físicamente en el repositorio nuevo.

### Para empaquetar también el Excel y las imágenes dentro de TU nuevo repositorio

Antes de hacer commit ejecuta, desde una máquina con conexión a internet:

```bash
python scripts/prepare_resources.py
```

El script descargará en `data/` el XLSX original y en `assets/` las imágenes PNG originales. Es la opción más robusta: el deployment no dependerá de GitHub Raw en tiempo de ejecución. **No está obligado el usuario final a hacer esto ni a cargar el archivo manualmente.**

## Flujo completo

1. Menú inicial y acceso al cálculo.
2. Búsqueda MLFB mediante Excel. Busca código de 11 caracteres en hoja `Core Level Data 60 Hz`, encabezado 3.
3. Autollenado de HP, RPM, JM, factor de curvas, Stall HOT, Stall COLD. Por seguridad los campos se bloquean; opción para editarlos.
4. Captura de datos del equipo: RPM, WR2, MNV, modo bomba/ventilador, factor MMV. WR2 y MNV se desbloquean progresivamente.
5. Porcentaje de voltaje mediante campo numérico y deslizador sincronizados.
6. Adaptaciones: MMV nMot, GD2V, GD2V nMot, nGD2, ta y ta CEILING.
7. Diagnóstico de viabilidad en frío y caliente.
8. Activación opcional de arranques consecutivos: f, GFe, rotor, estator, factores, arranques y frecuencia.
9. Gráficas y tablas de frío, caliente y por hora, con bandas térmicas y estados.
10. PDF técnico y ventana de operaciones utilizadas.
11. Exportación/importación de proyecto JSON para conservar el trabajo después de cerrar el navegador.

## Base de datos y actualización

| Campo | Columna de Excel |
| --- | --- |
| MLFB | A |
| HP | C |
| Inercia | AS |
| Curvas | BT |
| Stall HOT | AN |
| Stall COLD | AO |

Es posible cargar un nuevo XLSX desde la configuración: se valida antes de activarlo, **solo para la sesión actual**. Para sustituir la base global del despliegue, cambia el fichero del repositorio o implementa un almacenamiento persistente con autorización. No uses una ruta local de la computadora del visitante como si fuera la ruta del servidor.

## Fórmulas y fidelidad

La ecuación central es:

```
ta = (nGD2 * RPM_motor) / [375 * (MMM - MMV_nMot)]
```

Se conservan las constantes de conversión del original (`23.731`, `7.233`), la obtención de JM desde Excel (`inercia/23.73`), el efecto cuadrático del voltaje y el redondeo de valores derivados. La simulación reproduce el primer enfriamiento especial, estados térmicos progresivos y la referencia fija `B5/60` en el descanso por hora.

**Correcciones deliberadas:**
- Se permite calcular el tiempo si el par de la carga vale cero (en el original se omitía por una condición booleana).
- Se detectan ciclos de más de 3600 s y se reportan como inviables.
- Se evita cualquier escritura global de `debug_log.txt` en entornos multiusuario.
- El botón Calcular es visible y funcional.
- Se permite introducir factor de curvas manualmente si no se usa MLFB.
- Se guardan también las columnas configurables de Stall HOT/COLD durante la sesión.

**Diferencias respecto a Windows/Tkinter:** los diálogos de archivos se reemplazan por subida/descarga web; la interfaz adapta anchos según el navegador; las ventanas de operaciones son modales web. Los proyectos JSON permiten recuperar datos entre sesiones. No hay persistencia compartida para reemplazos de Excel sin almacenamiento externo.

## Pruebas automáticas

```bash
pip install pytest
pytest -q
```

Los tests contrastan fórmulas principales, redondeos, conversiones, cero carga, secuencias de frío/caliente/hora, búsqueda MLFB y PDF. Como los archivos originales de Excel y las imágenes no se adjuntan al ZIP, las pruebas unitarias no dependen de descargas; debe hacerse una prueba adicional con MLFB reales del libro original.

## Estructura

```
streamlit_app.py               # Pantallas e interacción
core/engine.py                # Motor matemático y simulaciones
services/motors.py            # Lectura y búsqueda Excel
services/resources.py         # Descarga automática de recursos
services/charts.py            # Gráficas equivalentes
reports/pdf_report.py         # PDF en memoria
scripts/prepare_resources.py  # Descargar Excel e imágenes para el repo
.streamlit/config.toml        # Tema y configuración
requirements.txt              # Dependencias
```

## Límites de responsabilidad técnica

Este proyecto replica el modelo matemático del programa original, **no certifica que sus fórmulas sean adecuadas para cualquier motor o que el Excel original esté actualizado**. Valida resultados contra casos de ingeniería antes de tomar decisiones operativas.

## Actualizar el Excel de forma permanente (opcional)

En Streamlit Cloud, agrega estos secretos en **App settings > Secrets**:

```toml
GITHUB_REPO = "tuusuario/motor-startup-streamlit"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = "TOKEN_DE_GITHUB_CON_PERMISO_CONTENTS_WRITE"
ADMIN_PASSWORD = "CONTRASENA_ADMINISTRATIVA_LARGA"
```

Cuando cargues un nuevo XLSX válido, se habilitará el panel **Actualizar la base oficial permanentemente**. Tras introducir la contraseña, la aplicación hace un commit en el nuevo repositorio, sustituyendo `data/PMD NEMA V46 ADAPTED APPLICACION V1.xlsx` con los bytes del nuevo archivo. El nombre de ruta se conserva para que futuras versiones no rompan la búsqueda. El nuevo contenido se utilizará automáticamente al redesplegar la aplicación.

No introduzcas el token en el código fuente ni compartas la contraseña administrativa. Si no configuras secretos, la aplicación funciona normalmente y el reemplazo de Excel se limita a la sesión.
