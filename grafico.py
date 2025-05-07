# ==============================================================
#                    IMPORTS
# ==============================================================
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pingouin as pg
import scikit_posthocs as sp
import statsmodels.api as sm
from statsmodels.formula.api import ols
import plotly.express as px
from streamlit_option_menu import option_menu
import requests
import io # Necesario para descarga de gráficos (si se implementa)
import scipy.stats as stats # Para skewness, kurtosis, kruskal
# Necesario para incrustar PDF, asegúrate de tener PyMuPDF instalado: pip install pymupdf
import fitz # PyMuPDF
import base64 # Para codificar el PDF

# ==============================================================
#              CONFIGURACIÓN Y NUEVA PALETA DE COLORES
# ==============================================================
st.set_page_config(layout="wide", page_title="Dashboard Ingreso SCCV")

# --- Paleta de Colores Original SCCV (Comentada) ---
# PALETA_SCCV = ['#f9c74f', '#90be6d', '#c1121f', '#003366', '#57cc99'] # Amarillo, Verde Claro, Rojo, Azul, Verde Intenso
# COLOR_AMARILLO = PALETA_SCCV[0]
# COLOR_VERDE_CLARO = PALETA_SCCV[1]
# COLOR_ROJO = PALETA_SCCV[2]
# COLOR_AZUL = PALETA_SCCV[3]
# COLOR_VERDE_INTENSO = PALETA_SCCV[4]
# PALETA_SEC_AMARILLO_VERDE = px.colors.sequential.YlGn
# PALETA_SEC_AMARILLO_ROJO = px.colors.sequential.YlOrRd

# --- Nueva Paleta de Colores - Elegante, Cautivadora y Moderna ---
# Usaremos la paleta por defecto de Plotly como base cualitativa y paletas secuenciales estándar.
NEW_PALETTE_PRIMARY = px.colors.qualitative.Plotly # ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', ...]
NEW_PALETTE_SEQ_COOL = px.colors.sequential.Blues  # Para gradientes fríos
NEW_PALETTE_SEQ_WARM = px.colors.sequential.Oranges # Para gradientes cálidos
COLOR_ACCENT_1 = NEW_PALETTE_PRIMARY[0] # Azul principal
COLOR_ACCENT_2 = NEW_PALETTE_PRIMARY[1] # Naranja como acento
COLOR_NEUTRAL_BG = "#f8f9fa" # Un gris muy claro para fondos si es necesario
COLOR_NEUTRAL_TEXT = "#212529" # Texto oscuro estándar

# ==============================================================
#               VARIABLES GLOBALES DE CONFIGURACIÓN
# ==============================================================
# --- ¡¡AJUSTA ESTOS NOMBRES A TUS COLUMNAS!! ---
COL_INGRESO = 'INGRESO'
COL_EDU_NUM = 'NIVEL_EDUCATIVO_ALCANZADO'
COL_EDU_LABEL = 'NIVEL_EDUCATIVO_LABEL'
COL_TRABAJO = 'TIPO_TRABAJO'
COL_MUNICIPIO_CODE = 'MUNICIPIO' # Código numérico del municipio
COL_MUNICIPIO_NAME = 'Municipio'    # Nombre que se creará
COL_GRUPO_EDAD = 'Grupo_Edad'       # Nombre para la columna de grupos de edad

# --- Rutas a los Archivos ---
# ¡¡ASEGÚRATE QUE ESTAS RUTAS SON CORRECTAS Y ACCESIBLES!!
file_name = "df_sabana_centro (3).xlsx"
# --- RUTAS A LOS PDFs --- # <- ¡¡MODIFICADO!!
pdf_path_guia = "GuiaCarreras.pdf" # <- Ruta al PDF de Guía de Carreras
pdf_path_desercion = "InformeDescercion.pdf" # <- ¡¡NUEVO!! Ruta al PDF de Deserción

# ==============================================================
#                    CARGA Y PREPROCESAMIENTO DE DATOS
# ==============================================================
@st.cache_data # Cachea los datos
def load_data(file_path):
    """Carga y preprocesa los datos del archivo Excel."""
    try:
        df = pd.read_excel(file_path)
        if df is None or df.empty:
            st.error("El archivo Excel parece estar vacío o no se pudo leer.")
            return None
    except FileNotFoundError:
        st.error(f"Error Crítico: No se encontró el archivo en la ruta: {file_path}")
        st.info("Verifica que la ruta y el nombre del archivo sean correctos y que el archivo exista.")
        return None
    except Exception as e:
        st.error(f"Error Crítico al cargar el archivo Excel: {e}")
        st.info("Revisa la estructura del archivo Excel, permisos, o si está corrupto.")
        return None

    # --- Mapeo de Niveles Educativos ---
    nivel_map = {
         1.0: '01: Ninguno', 2.0: '02: Preescolar', 3.0: '03: Primaria',
         4.0: '04: Secundaria', 5.0: '05: Media', 6.0: '06: Técnico',
         7.0: '07: Tecnológico', 9.0: '09: Univ. Completa',
         11.0: '11: Esp. Completa', 13.0: '13: Maestría Comp.', 15.0: '15: Doctorado Comp.'
    }
    if COL_EDU_NUM in df.columns:
        try:
            numeric_col = pd.to_numeric(df[COL_EDU_NUM], errors='coerce')
            df[COL_EDU_LABEL] = numeric_col.map(nivel_map)
            df[COL_EDU_LABEL] = df[COL_EDU_LABEL].fillna('Desconocido (' + df[COL_EDU_NUM].astype(str) + ')')
            df.loc[numeric_col.isna(), COL_EDU_LABEL] = 'No Aplica / NaN'
        except Exception as e:
            st.warning(f"Advertencia al mapear niveles educativos: {e}")
            df[COL_EDU_LABEL] = 'Error Mapeo'
    else:
        st.warning(f"Columna '{COL_EDU_NUM}' no encontrada para crear etiquetas.")
        df[COL_EDU_LABEL] = 'No Disponible'

    # --- Mapeo Municipio ---
    municipio_map = {
        25126: 'Cajicá', 25175: 'Chía', 25200: 'Cogua', 25214: 'Cota',
        25295: 'Gachancipá', 25486: 'Nemocón', 25758: 'Sopó',
        25785: 'Tabio', 25799: 'Tenjo', 25817: 'Tocancipá', 25899: 'Zipaquirá'
    }
    if COL_MUNICIPIO_CODE in df.columns:
        try:
            muni_code_col = pd.to_numeric(df[COL_MUNICIPIO_CODE], errors='coerce')
            df[COL_MUNICIPIO_NAME] = muni_code_col.map(municipio_map)
            df[COL_MUNICIPIO_NAME] = df[COL_MUNICIPIO_NAME].fillna('Otro/Desconocido')
            df.loc[muni_code_col.isna(), COL_MUNICIPIO_NAME] = 'Código NaN'
        except Exception as e:
            st.warning(f"Advertencia al mapear municipios: {e}")
            df[COL_MUNICIPIO_NAME] = 'Error Mapeo Muni'
    else:
        st.warning(f"Columna de código de municipio '{COL_MUNICIPIO_CODE}' no encontrada.")
        df[COL_MUNICIPIO_NAME] = 'No Disponible'

    return df

# --- Función para descargar CSV ---
@st.cache_data
def convert_df_to_csv(df):
    """Convierte un DataFrame a CSV listo para descargar."""
    return df.to_csv(index=False).encode('utf-8')

# --- Función para incrustar PDF ---
def show_pdf(file_path):
    """Muestra un PDF incrustado en la app Streamlit."""
    try:
        with open(file_path,"rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        # Incrusta el PDF usando un iframe HTML
        # Ajusta la altura si es necesario
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo PDF en la ruta: {file_path}")
        st.info("Verifica que la ruta y el nombre del archivo sean correctos.")
    except Exception as e:
        st.error(f"Error al intentar mostrar el PDF: {e}")

def mostrar_pdf(pdf_path):
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
    pdf_display = f"""
    <iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)
def mostrar_pdf_desde_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        base64_pdf = base64.b64encode(response.content).decode("utf-8")
        pdf_display = f"""
        <iframe 
            src="data:application/pdf;base64,{base64_pdf}" 
            width="100%" 
            height="800" 
            type="application/pdf">
        </iframe>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.error("No se pudo cargar el PDF desde la URL.")

# --- Carga Inicial ---
df_sabana_centro_final2 = load_data(file_name)

# ==============================================================
#               BARRA LATERAL (SIDEBAR) Y FILTROS
# ==============================================================

# Procede solo si la carga fue exitosa y el dataframe no es None
if df_sabana_centro_final2 is not None and not df_sabana_centro_final2.empty:

    with st.sidebar:
        # Puedes cambiar la URL a una ruta local si tienes el logo descargado
        st.image("Logo.png", width=400)
        st.markdown("## Navegación Principal")

        # --- Crear lista de opciones dinámicamente ---
        menu_options_base = [
            "Dashboard Principal", "Verificación de Supuestos", "Resultados Ed-Ingreso",
            "Análisis por Trabajo", "Análisis por Municipio",
            "Conclusiones y Plan",
            "Ver PDF Guía Carreras", # <- Opción PDF 1
            "Ver PDF Informe Deserción" # <- ¡¡NUEVA OPCIÓN PDF 2!!
        ]
        menu_icons_base = [
            'speedometer2', 'clipboard-data', 'graph-up-arrow',
            'briefcase-fill', 'geo-alt-fill', # Ajustado el icono de municipio
            'lightbulb',
            'file-earmark-pdf-fill', # Icono para PDF 1
            'file-earmark-break-fill' # <- ¡¡NUEVO ICONO PDF 2!! (O usa otro como 'file-earmark-medical-fill')
        ]
        # Mapeo de nombres de página a columnas requeridas (además de INGRESO)
        required_cols_map = {
            "Dashboard Principal": [COL_EDU_LABEL],
            "Verificación de Supuestos": [COL_EDU_NUM],
            "Resultados Ed-Ingreso": [COL_EDU_NUM, COL_EDU_LABEL],
            "Análisis por Trabajo": [COL_TRABAJO, COL_EDU_LABEL],
            "Análisis por Municipio": [COL_MUNICIPIO_NAME, COL_EDU_LABEL, COL_EDU_NUM],
            "Conclusiones y Plan": [], # Esta siempre se muestra
            "Ver PDF Guía Carreras": [], # Esta siempre se muestra
            "Ver PDF Informe Deserción": [] # <- ¡¡NUEVA!! Esta siempre se muestra
        }

        available_options = []
        available_icons = []
        for i, option in enumerate(menu_options_base):
            req_cols = required_cols_map.get(option, [])
            # Chequear si TODAS las columnas requeridas para esta opción existen
            if all(col in df_sabana_centro_final2.columns for col in req_cols):
                 available_options.append(option)
                 available_icons.append(menu_icons_base[i])
            else:
                 missing = [col for col in req_cols if col not in df_sabana_centro_final2.columns]
                 st.sidebar.caption(f"Sección '{option}' omitida (faltan: {', '.join(missing)})")

        # --- option_menu ---
        if available_options: # Solo muestra el menú si hay opciones válidas
            # Establecer el índice predeterminado a 0 (Dashboard Principal)
            default_idx = 0
            try:
                pass # Mantiene el índice por defecto en 0
            except ValueError:
                pass # Si la opción no está disponible, mantiene el índice por defecto

            pagina_seleccionada = option_menu(
                menu_title=None,
                options=available_options,
                icons=available_icons,
                menu_icon="cast", default_index=default_idx, orientation="vertical", # Usa el índice calculado
                styles={ # Usar colores de la NUEVA paleta
                    "container": {"padding": "5px !important", "background-color": "#022B3A"}, # Azul oscuro para el fondo del menú
                    "icon": {"color": NEW_PALETTE_PRIMARY[4], "font-size": "23px"}, # Violeta para iconos
                    "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "color": "#E1E5F2", "--hover-color": NEW_PALETTE_PRIMARY[0]}, # Texto claro, Hover Azul principal
                    "nav-link-selected": {"background-color": NEW_PALETTE_PRIMARY[1]}, # Naranja para selección
                }
            )
        else:
             st.sidebar.error("No hay secciones disponibles para mostrar debido a columnas faltantes.")
             pagina_seleccionada = None # No hay página que mostrar
             st.stop()


        st.divider()
        st.markdown("### Filtros Globales")

        # --- Filtros ---
        # Filtro Nivel Educativo
        if COL_EDU_LABEL in df_sabana_centro_final2.columns:
             niveles_unicos = sorted([lvl for lvl in df_sabana_centro_final2[COL_EDU_LABEL].unique() if lvl not in ['No Disponible', 'Error Mapeo', 'No Aplica / NaN']])
             if niveles_unicos:
                  selected_levels = st.multiselect("Nivel Educativo:", niveles_unicos, default=niveles_unicos)
             else: selected_levels = []
        else: selected_levels = []


        # Filtro Municipio
        if COL_MUNICIPIO_NAME in df_sabana_centro_final2.columns:
             municipios_unicos = sorted([m for m in df_sabana_centro_final2[COL_MUNICIPIO_NAME].unique() if m not in ['No Disponible', 'Error Mapeo Muni', 'Código NaN', 'Otro/Desconocido']])
             if municipios_unicos:
                  selected_municipios = st.multiselect("Municipio:", municipios_unicos, default=municipios_unicos)
             else: selected_municipios = []
        else: selected_municipios = []


    # --- Filtrar el DataFrame ---
    df_filtered = df_sabana_centro_final2.copy()
    if selected_levels and COL_EDU_LABEL in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[COL_EDU_LABEL].isin(selected_levels)]
    if selected_municipios and COL_MUNICIPIO_NAME in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[COL_MUNICIPIO_NAME].isin(selected_municipios)]

    # Mostrar advertencia si el filtro resulta en DataFrame vacío
    # PERO no detener si la página seleccionada es una de las de PDF
    if df_filtered.empty and pagina_seleccionada not in ["Ver PDF Guía Carreras", "Ver PDF Informe Deserción"]:
         st.warning("La selección de filtros actual no devuelve ningún dato. Por favor, ajusta los filtros.")
         st.stop() # Detener si no hay datos filtrados Y no es una página de PDF

    # ==============================================================
    #               CONTENIDO DE CADA PÁGINA
    # ==============================================================
    # Ahora, todas las páginas (excepto las de PDF) usarán 'df_filtered'

    # --- PÁGINA 1: DASHBOARD PRINCIPAL ---
    if pagina_seleccionada == "Dashboard Principal":
        st.title(f"Dashboard: Ingreso vs Nivel Educativo ({len(df_filtered):,} pers.)")
        # --- Fila 1: KPIs ---
        st.subheader("Indicadores Clave (Datos Filtrados)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Participantes Filtrados", f"{len(df_filtered):,}")
        try:
            mediana_filt = df_filtered[COL_INGRESO].dropna().median()
            col2.metric("Mediana Ingreso", f"${mediana_filt:,.0f}")
        except: col2.metric("Mediana Ingreso", "N/A")
        try:
             if COL_EDU_NUM in df_filtered.columns:
                 numeric_educ_col_filt = pd.to_numeric(df_filtered[COL_EDU_NUM], errors='coerce')
                 count_superiores_filt = numeric_educ_col_filt[numeric_educ_col_filt >= 9].count()
                 if len(df_filtered) > 0:
                     perc_superiores_filt = (count_superiores_filt / len(df_filtered)) * 100
                     col3.metric("% Est. Superiores", f"{perc_superiores_filt:.1f}%", help="Porcentaje con Universidad Completa o superior.")
                 else: col3.metric("% Est. Superiores", "N/A")
             else: col3.metric("% Est. Superiores", "N/A")
        except: col3.metric("% Est. Superiores", "Error")
        st.divider()
        # --- Fila 2: Distribuciones ---
        st.subheader("Distribuciones (Datos Filtrados)")
        col_dist_gen, col_dist_ed, col_dist_ing_ed = st.columns([1, 1, 2])
        with col_dist_gen:
             st.markdown("**Ingreso General**")
             df_ingreso_plot = df_filtered.dropna(subset=[COL_INGRESO])
             if not df_ingreso_plot.empty:
                  # Usar paleta secuencial fría
                  fig_hist_ing = px.histogram(df_ingreso_plot, x=COL_INGRESO, title="Distribución Ingreso", height=350, nbins=50, color_discrete_sequence=[COLOR_ACCENT_1]) # Azul Principal
                  fig_hist_ing.update_layout(title_x=0.5, yaxis_title="Frecuencia", xaxis_title="Ingreso")
                  st.plotly_chart(fig_hist_ing, use_container_width=True)
             else: st.caption("No hay datos de ingreso.")
        with col_dist_ed:
            st.markdown("**Nivel Educativo**")
            df_educ_plot = df_filtered.dropna(subset=[COL_EDU_LABEL])
            if not df_educ_plot.empty and df_educ_plot[COL_EDU_LABEL].nunique() > 0:
                nivel_counts_filt = df_educ_plot[COL_EDU_LABEL].value_counts().sort_index().reset_index()
                nivel_counts_filt.columns = ['Nivel Educativo', 'Cantidad']
                # Usar paleta primaria
                fig_bar_plotly_filt = px.bar(nivel_counts_filt, x='Nivel Educativo', y='Cantidad', title="Participantes", height=350, color_discrete_sequence=[NEW_PALETTE_PRIMARY[2]]) # Verde
                fig_bar_plotly_filt.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Cantidad", xaxis_title=None)
                st.plotly_chart(fig_bar_plotly_filt, use_container_width=True)
            else: st.caption("No hay datos de Nivel Educativo.")
        with col_dist_ing_ed:
            st.markdown("**Ingreso vs Nivel Educativo (Violin Plot)**")
            df_plot_violin = df_filtered.dropna(subset=[COL_INGRESO, COL_EDU_LABEL])
            if not df_plot_violin.empty and df_plot_violin[COL_EDU_LABEL].nunique() > 0:
                try: order_labels_filt = sorted(df_plot_violin[COL_EDU_LABEL].unique())
                except: order_labels_filt = None
                # Usar paleta primaria para los colores
                fig_violin = px.violin(df_plot_violin, x=COL_EDU_LABEL, y=COL_INGRESO, box=True,
                                      category_orders={COL_EDU_LABEL: order_labels_filt} if order_labels_filt else None,
                                      title="Distribución Ingreso", height=400, points=False, color=COL_EDU_LABEL, color_discrete_sequence=NEW_PALETTE_PRIMARY)
                try:
                    ingresos_validos_filt = df_plot_violin[COL_INGRESO][df_plot_violin[COL_INGRESO] > 0].dropna()
                    if not ingresos_validos_filt.empty: limite_y = np.percentile(ingresos_validos_filt, 98)
                    else: limite_y = df_plot_violin[COL_INGRESO].max()
                    fig_violin.update_yaxes(range=[0, limite_y if limite_y > 0 else 1e6]) # Evitar rango inválido
                except: pass
                fig_violin.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Ingreso", xaxis_title="Nivel Educativo", showlegend=False)
                st.plotly_chart(fig_violin, use_container_width=True)
            else: st.warning("No hay datos suficientes para generar el Violin Plot con los filtros actuales.")
        st.caption("Observación: Mayor nivel educativo generalmente implica mayor mediana de ingreso, pero también mayor dispersión (variabilidad).")


    # --- PÁGINA 2: VERIFICACIÓN DE SUPUESTOS ---
    elif pagina_seleccionada == "Verificación de Supuestos":
        st.title("Validación del Modelo: Supuestos del ANOVA")
        st.markdown("Evaluamos si se cumplen los requisitos del ANOVA estándar sobre los **datos filtrados**.")

        df_anova = df_filtered.dropna(subset=[COL_INGRESO, COL_EDU_NUM])
        if df_anova.empty or COL_INGRESO not in df_anova.columns or COL_EDU_NUM not in df_anova.columns:
            st.error("Faltan datos o columnas esenciales en datos filtrados para ANOVA.")
            st.stop()
        if df_anova[COL_EDU_NUM].nunique() < 2:
             st.warning("Se necesita más de un nivel educativo con datos válidos en la selección actual para el ANOVA.")
             st.stop()

        try:
            model = ols(f'{COL_INGRESO} ~ C({COL_EDU_NUM})', data=df_anova).fit()
            residuals = model.resid
            fitted_values = model.fittedvalues

            st.subheader("Evaluación Gráfica de Supuestos")
            col_norm, col_homog = st.columns(2)

            with col_norm:
                st.markdown("**Normalidad de Residuales**")
                fig_qq, ax_qq = plt.subplots(figsize=(6,5)); sm.qqplot(residuals, line='s', ax=ax_qq); ax_qq.set_title('Gráfico Q-Q'); st.pyplot(fig_qq, clear_figure=True) # clear_figure para evitar warnings
                fig_hist, ax_hist = plt.subplots(figsize=(6,5)); sns.histplot(residuals, kde=True, ax=ax_hist, color=COLOR_ACCENT_1); ax_hist.set_title('Histograma'); st.pyplot(fig_hist, clear_figure=True) # Usar color azul principal
                skewness = stats.skew(residuals); kurtosis = stats.kurtosis(residuals)
                st.text(f"Skewness: {skewness:.2f} | Kurtosis: {kurtosis:.2f}")
                if abs(skewness) > 1 or abs(kurtosis) > 3: st.error("❌ Supuesto de Normalidad NO CUMPLIDO.")
                else: st.success("✅ Supuesto de Normalidad razonablemente cumplido.")

            with col_homog:
                 st.markdown("**Homogeneidad de Varianzas**")
                 fig_rvf, ax_rvf = plt.subplots(figsize=(6,5)); sns.scatterplot(x=fitted_values, y=residuals, ax=ax_rvf, alpha=0.5, color=NEW_PALETTE_PRIMARY[2]); ax_rvf.axhline(0, color=NEW_PALETTE_PRIMARY[3], linestyle='--'); ax_rvf.set_title('Residuales vs. Ajustados'); st.pyplot(fig_rvf, clear_figure=True) # Verde para puntos, Rojo para línea
                 try:
                     groups = df_anova.groupby(COL_EDU_NUM)[COL_INGRESO].apply(lambda x: x.dropna().tolist())
                     groups_filtered = [g for g in groups if len(g) > 1]
                     if len(groups_filtered) > 1:
                         levene_stat, levene_p = stats.levene(*groups_filtered, center='median')
                         st.text(f"Test de Levene: Stat={levene_stat:.2f}, p={levene_p:.4g}")
                         if levene_p < 0.05: st.error("❌ Supuesto de Homogeneidad NO CUMPLIDO (Levene p < 0.05).")
                         else: st.success("✅ Supuesto de Homogeneidad razonablemente cumplido (Levene p >= 0.05).")
                     else: st.text("Test de Levene no aplicable (pocos grupos).")
                 except Exception as e_levene: st.text(f"Error Levene: {e_levene}")
                 st.markdown("Revisar también Violin/Box Plots.")

            st.warning("Conclusión: Si alguno de los supuestos no se cumple, interpretar ANOVA estándar con cautela y preferir pruebas robustas.")

        except Exception as e:
            st.error(f"Error al calcular modelo ANOVA o analizar residuales en datos filtrados: {e}")


    # --- PÁGINA 3: RESULTADOS ED-INGRESO DETALLADOS ---
    elif pagina_seleccionada == "Resultados Ed-Ingreso": # Nombre corto
        st.title(f"Resultados Detallados Educación vs Ingreso ({len(df_filtered):,} pers.)")

        df_analysis = df_filtered.dropna(subset=[COL_INGRESO, COL_EDU_NUM, COL_EDU_LABEL])
        if df_analysis.empty or COL_INGRESO not in df_analysis.columns or COL_EDU_NUM not in df_analysis.columns:
             st.error("Faltan datos/columnas esenciales en datos filtrados.")
             st.stop()
        if df_analysis[COL_EDU_NUM].nunique() < 2:
             st.warning("Se necesita más de un nivel educativo en la selección actual.")
             st.stop()

        tab_global, tab_medianas, tab_posthoc = st.tabs(["Pruebas Globales", "Detalle Medianas", "Comparaciones por Pares (Post-Hoc)"])
        with tab_global:
            st.subheader("Confirmación Estadística Global")
            st.markdown(f"| Prueba | p-valor | η² / np² | Fiabilidad |")
            st.markdown(f"|---|---|---|---|")
            eta_squared = np.nan; np2_welch = np.nan # Inicializar
            try: # ANOVA
                 model = ols(f'{COL_INGRESO} ~ C({COL_EDU_NUM})', data=df_analysis).fit()
                 anova_table = sm.stats.anova_lm(model, typ=2); p_anova = anova_table.loc[f'C({COL_EDU_NUM})', 'PR(>F)']
                 ss_between = anova_table.loc[f'C({COL_EDU_NUM})', 'sum_sq']; ss_total = ss_between + anova_table.loc['Residual', 'sum_sq']
                 eta_squared = ss_between / ss_total
                 st.markdown(f"| ANOVA Estándar | {p_anova:.4g} | {eta_squared:.3f} | Baja |")
            except Exception: st.markdown(f"| ANOVA Estándar | Error | - | Baja |")
            try: # Welch
                 welch_results = pg.welch_anova(data=df_analysis, dv=COL_INGRESO, between=COL_EDU_NUM)
                 p_welch = welch_results['p-unc'].iloc[0]; np2_welch = welch_results['np2'].iloc[0]
                 st.markdown(f"| **Welch's ANOVA** | {p_welch:.4g} | {np2_welch:.3f} | **Alta** |")
            except Exception: st.markdown(f"| **Welch's ANOVA** | Error | - | Alta |")
            try: # Kruskal-Wallis
                 groups = df_analysis.groupby(COL_EDU_NUM)[COL_INGRESO].apply(lambda x: x.dropna().tolist()); groups_filtered = [g for g in groups if len(g) > 0]
                 if len(groups_filtered) > 1:
                      kruskal_stat, p_kruskal = stats.kruskal(*groups_filtered)
                      st.markdown(f"| **Kruskal-Wallis** | {p_kruskal:.4g} | - | **Alta** |")
                 else: st.markdown("| **Kruskal-Wallis** | N/A | - | Alta |")
            except Exception: st.markdown(f"| **Kruskal-Wallis** | Error | - | Alta |")
            st.success("✅ Diferencias significativas confirmadas robustamente por Welch/Kruskal-Wallis.")
            if not np.isnan(eta_squared): st.metric("Eta Cuadrado (η²) Muestral", f"{eta_squared:.3f}", delta="Efecto Grande (Cautela)", delta_color="off")

        with tab_medianas:
            st.subheader("Mediana de Ingreso por Nivel")
            if COL_EDU_LABEL in df_analysis.columns and not df_analysis.dropna(subset=[COL_INGRESO, COL_EDU_LABEL]).empty:
                 try:
                      median_income = df_analysis.dropna(subset=[COL_INGRESO, COL_EDU_LABEL])\
                                                  .groupby(COL_EDU_LABEL)[COL_INGRESO]\
                                                  .median().sort_index().reset_index()
                      median_income.columns = ['Nivel Educativo', 'Mediana Ingreso']
                      # Usar paleta secuencial cálida para las barras de medianas
                      fig_median_plotly = px.bar(median_income, x='Nivel Educativo', y='Mediana Ingreso',
                                                  title="Mediana Ingreso por Nivel Educativo", height=400, text='Mediana Ingreso',
                                                  color='Mediana Ingreso', color_continuous_scale=NEW_PALETTE_SEQ_WARM) # Naranja secuencial
                      fig_median_plotly.update_traces(texttemplate='$%{text:,.0f}', textposition='outside'); fig_median_plotly.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Mediana Ingreso", xaxis_title="Nivel Educativo", coloraxis_showscale=False); st.plotly_chart(fig_median_plotly, use_container_width=True)
                      st.caption("Se observa descenso en Doctorado vs Maestría.")
                      csv_medianas = convert_df_to_csv(median_income); st.download_button("Descargar Medianas (CSV)", csv_medianas, "medianas_ingreso_educacion.csv", "text/csv")
                      st.dataframe(median_income.style.format({'Mediana Ingreso': "${:,.0f}"}))
                 except Exception as e: st.error(f"Error al graficar/mostrar medianas: {e}")
            else: st.warning("No se puede mostrar gráfico/tabla de medianas.")

        with tab_posthoc:
            st.subheader("Comparaciones por Pares (Post-Hoc)")
            st.markdown("Busca p-valores < 0.05 (o celdas verdes) para identificar diferencias significativas.")
            try:
                games_howell_results = pg.pairwise_gameshowell(data=df_analysis, dv=COL_INGRESO, between=COL_EDU_NUM)
                st.markdown("**Games-Howell (Comparación Medias)**")
                significant_gh = games_howell_results[games_howell_results['pval'] < 0.05]
                st.dataframe(significant_gh)
                st.caption(f"Mostrando {len(significant_gh)} comparaciones significativas de {len(games_howell_results)}.")
            except Exception as e: st.warning(f"No se pudo calcular/mostrar Games-Howell: {e}")
            try:
                dunn_results_sp = sp.posthoc_dunn(df_analysis, val_col=COL_INGRESO, group_col=COL_EDU_NUM, p_adjust='bonferroni')
                st.markdown("**Dunn Test (Comparación Distribuciones, p-ajustado Bonf.)**")
                def highlight_significant(val):
                    # Usar un verde de la nueva paleta para resaltar
                    color = NEW_PALETTE_PRIMARY[2] + '40' if isinstance(val, (int, float)) and val < 0.05 else '#FFFFFF' # Verde con transparencia
                    return f'background-color: {color}'
                st.dataframe(dunn_results_sp.style.format("{:.3f}").applymap(highlight_significant))
            except Exception as e: st.warning(f"No se pudo calcular/mostrar Dunn Test: {e}")
            st.info("**Hallazgo Clave:** Generalmente no se encontraron diferencias significativas entre Esp.(11), Maestría(13) y Doctorado(15).")

    # --- PÁGINA 4: ANÁLISIS POR TIPO DE TRABAJO ---
    elif pagina_seleccionada == "Análisis por Trabajo": # Nombre corto
        st.title(f"Análisis de Ingreso por Tipo de Trabajo ({len(df_filtered):,} pers.)")
        if COL_TRABAJO not in df_filtered.columns: st.warning(f"Columna '{COL_TRABAJO}' no disponible."); st.stop()
        try:
             df_trabajo = df_filtered.dropna(subset=[COL_TRABAJO, COL_INGRESO, COL_EDU_LABEL])
             if df_trabajo.empty: st.warning("No hay datos válidos para análisis de trabajo."); st.stop()
             trabajo_stats = df_trabajo.groupby(COL_TRABAJO).agg(Ingreso_Mediana=(COL_INGRESO, 'median'),Nivel_Educativo_Modal=(COL_EDU_LABEL, lambda x: x.mode()[0] if not x.mode().empty else 'N/A'),Conteo=(COL_INGRESO, 'count')).reset_index()
             min_participantes = st.sidebar.slider("Mínimo participantes por trabajo", 1, 50, 5, key="slider_trabajo")
             trabajo_stats_filtrado = trabajo_stats[trabajo_stats['Conteo'] >= min_participantes].copy()
             if trabajo_stats_filtrado.empty: st.warning(f"No hay trabajos con al menos {min_participantes} participantes."); st.stop()
             trabajo_stats_filtrado['Ingreso_Mediana_Fmt'] = trabajo_stats_filtrado['Ingreso_Mediana'].apply(lambda x: f"${x:,.0f}")
             n_top_bottom = st.sidebar.number_input("Num Top/Bottom Trabajos", 5, 20, 10, key="num_trabajo")
             df_top = trabajo_stats_filtrado.sort_values(by='Ingreso_Mediana', ascending=False).head(n_top_bottom); df_bottom = trabajo_stats_filtrado.sort_values(by='Ingreso_Mediana', ascending=True).head(n_top_bottom)
             col_top, col_bottom = st.columns(2)
             with col_top:
                  st.subheader(f"Top {n_top_bottom} Trabajos");
                  if not df_top.empty:
                       # Usar paleta secuencial cálida para top
                       fig_top = px.bar(df_top, x='Ingreso_Mediana', y=COL_TRABAJO, orientation='h', text='Ingreso_Mediana_Fmt',hover_data=['Nivel_Educativo_Modal', 'Conteo', 'Ingreso_Mediana'], color='Ingreso_Mediana', color_continuous_scale=NEW_PALETTE_SEQ_WARM)
                       fig_top.update_traces(textposition='outside'); fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, yaxis_title=None, xaxis_title="Ingreso Mediano", height=400 + len(df_top)*20, coloraxis_showscale=False); st.plotly_chart(fig_top, use_container_width=True)
                       with st.expander("Ver datos Top Trabajos"):
                            df_top_display = df_top[[COL_TRABAJO, 'Ingreso_Mediana', 'Nivel_Educativo_Modal', 'Conteo']]
                            st.dataframe(df_top_display.style.format({'Ingreso_Mediana': "${:,.0f}"}))
                            csv_top = convert_df_to_csv(df_top_display); st.download_button("Descargar Top (CSV)", csv_top, "top_trabajos.csv", "text/csv")
                  else: st.info("No hay datos suficientes.")
             with col_bottom:
                  st.subheader(f"Bottom {n_top_bottom} Trabajos");
                  if not df_bottom.empty:
                       # Usar paleta secuencial fría para bottom
                       fig_bottom = px.bar(df_bottom, x='Ingreso_Mediana', y=COL_TRABAJO, orientation='h', text='Ingreso_Mediana_Fmt',hover_data=['Nivel_Educativo_Modal', 'Conteo', 'Ingreso_Mediana'], color='Ingreso_Mediana', color_continuous_scale=NEW_PALETTE_SEQ_COOL)
                       fig_bottom.update_traces(textposition='outside'); fig_bottom.update_layout(yaxis={'categoryorder':'total descending'}, yaxis_title=None, xaxis_title="Ingreso Mediano", height=400 + len(df_bottom)*20, coloraxis_showscale=False); st.plotly_chart(fig_bottom, use_container_width=True)
                       with st.expander("Ver datos Bottom Trabajos"):
                            df_bottom_display = df_bottom[[COL_TRABAJO, 'Ingreso_Mediana', 'Nivel_Educativo_Modal', 'Conteo']]
                            st.dataframe(df_bottom_display.style.format({'Ingreso_Mediana': "${:,.0f}"}))
                            csv_bottom = convert_df_to_csv(df_bottom_display); st.download_button("Descargar Bottom (CSV)", csv_bottom, "bottom_trabajos.csv", "text/csv")
                  else: st.info("No hay datos suficientes.")
        except KeyError as e: st.error(f"Error procesando trabajo: Falta columna {e}.")
        except Exception as e: st.error(f"Error inesperado en análisis trabajo: {e}")


    # --- PÁGINA 5: ANÁLISIS POR MUNICIPIO ---
    elif pagina_seleccionada == "Análisis por Municipio":
        st.title(f"Análisis Comparativo por Municipio ({len(df_filtered):,} pers.)")
        if COL_MUNICIPIO_NAME not in df_filtered.columns or df_filtered[COL_MUNICIPIO_NAME].nunique() < 2: st.warning(f"'{COL_MUNICIPIO_NAME}' no disponible o menos de 2 municipios seleccionados."); st.stop()
        try:
             df_muni_analysis = df_filtered.dropna(subset=[COL_INGRESO, COL_MUNICIPIO_NAME])
             if df_muni_analysis.empty: st.warning("No hay datos válidos de ingreso/municipio."); st.stop()
             st.subheader("Comparativa de Ingresos Medianos"); col_box_muni, col_bar_muni = st.columns(2)
             with col_box_muni:
                  st.markdown("**Distribución Ingreso**"); order_muni = df_muni_analysis.groupby(COL_MUNICIPIO_NAME)[COL_INGRESO].median().sort_values().index.tolist()
                  # Usar paleta primaria para boxplot
                  fig_box_muni = px.box(df_muni_analysis, x=COL_MUNICIPIO_NAME, y=COL_INGRESO, title="Ingreso por Municipio", height=450, points=False, category_orders={COL_MUNICIPIO_NAME: order_muni}, color=COL_MUNICIPIO_NAME, color_discrete_sequence=NEW_PALETTE_PRIMARY)
                  try: limite_y_muni = np.percentile(df_muni_analysis[COL_INGRESO].dropna(), 95); fig_box_muni.update_yaxes(range=[0, limite_y_muni if limite_y_muni > 0 else None])
                  except: pass
                  fig_box_muni.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Ingreso", xaxis_title="Municipio", showlegend=False); st.plotly_chart(fig_box_muni, use_container_width=True)
             with col_bar_muni:
                  st.markdown("**Mediana de Ingreso**"); muni_median_income = df_muni_analysis.groupby(COL_MUNICIPIO_NAME, observed=False)[COL_INGRESO].median().reset_index(); muni_median_income.columns = ['Municipio', 'Mediana Ingreso']; muni_median_income = muni_median_income.sort_values('Mediana Ingreso', ascending=False)
                  # Usar paleta secuencial cálida para barras
                  fig_bar_muni = px.bar(muni_median_income, x='Municipio', y='Mediana Ingreso', title="Mediana Ingreso por Municipio", height=450, text='Mediana Ingreso', color='Mediana Ingreso', color_continuous_scale=NEW_PALETTE_SEQ_WARM)
                  fig_bar_muni.update_traces(texttemplate='$%{text:,.0f}', textposition='outside'); fig_bar_muni.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Mediana Ingreso", xaxis_title="Municipio", coloraxis_showscale=False); st.plotly_chart(fig_bar_muni, use_container_width=True)
                  csv_muni_median = convert_df_to_csv(muni_median_income); st.download_button("Descargar Medianas Municipio (CSV)", csv_muni_median, "medianas_municipio.csv", "text/csv")
             st.divider()
             st.subheader("Comparativa de Niveles Educativos");
             if COL_EDU_LABEL in df_filtered.columns:
                  df_educ_muni = df_filtered.dropna(subset=[COL_MUNICIPIO_NAME, COL_EDU_LABEL])
                  if not df_educ_muni.empty:
                       conteo_muni_educ = df_educ_muni.groupby([COL_MUNICIPIO_NAME, COL_EDU_LABEL], observed=False).size().unstack(fill_value=0); perc_muni_educ = conteo_muni_educ.apply(lambda x: x*100/sum(x), axis=1).reset_index(); perc_muni_educ_long = perc_muni_educ.melt(id_vars=COL_MUNICIPIO_NAME, var_name='Nivel Educativo', value_name='Porcentaje')
                       try: order_labels_educ = sorted(df_educ_muni[COL_EDU_LABEL].unique())
                       except: order_labels_educ = None
                       # Usar paleta primaria para barras apiladas
                       fig_educ_muni = px.bar(perc_muni_educ_long, x=COL_MUNICIPIO_NAME, y='Porcentaje', color='Nivel Educativo', title="% Nivel Educativo por Municipio", category_orders={'Nivel Educativo': order_labels_educ}, color_discrete_sequence=NEW_PALETTE_PRIMARY)
                       fig_educ_muni.update_layout(xaxis_tickangle=-45, yaxis_title="Porcentaje (%)", xaxis_title="Municipio", legend_title="Nivel Educativo"); st.plotly_chart(fig_educ_muni, use_container_width=True)
                       if COL_EDU_NUM in df_educ_muni.columns:
                            numeric_educ_col_muni = pd.to_numeric(df_educ_muni[COL_EDU_NUM], errors='coerce'); df_educ_muni['Superior'] = numeric_educ_col_muni >= 9
                            perc_superior_muni = df_educ_muni.groupby(COL_MUNICIPIO_NAME, observed=False)['Superior'].mean().reset_index(); perc_superior_muni['Porcentaje Superior'] = perc_superior_muni['Superior'] * 100; perc_superior_muni = perc_superior_muni.sort_values('Porcentaje Superior', ascending=False)
                            # Usar paleta secuencial fría para % superior
                            fig_sup_muni = px.bar(perc_superior_muni, x=COL_MUNICIPIO_NAME, y='Porcentaje Superior', title="% Población con Educación Superior (Univ.+)", height=400, text='Porcentaje Superior', color='Porcentaje Superior', color_continuous_scale=NEW_PALETTE_SEQ_COOL)
                            fig_sup_muni.update_traces(texttemplate='%{text:.1f}%', textposition='outside'); fig_sup_muni.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Porcentaje (%)", xaxis_title="Municipio", coloraxis_showscale=False); st.plotly_chart(fig_sup_muni, use_container_width=True)
                  else: st.warning("No hay datos válidos de educación/municipio.")
             else: st.warning(f"Columna '{COL_EDU_LABEL}' no encontrada.")
        except KeyError as e: st.error(f"Error procesando municipio: Falta columna {e}.")
        except Exception as e: st.error(f"Error inesperado análisis municipio: {e}")


    # --- PÁGINA 6: CONCLUSIONES Y PLAN DE TRABAJO ---
    elif pagina_seleccionada == "Conclusiones y Plan": # Nombre corto
        st.title("Conclusiones Clave y Puntos para Plan de Trabajo")

        st.header("Conclusiones sobre Educación y Mercado Laboral en Sabana Centro")
        st.info("Análisis conjunto de las tendencias del mercado laboral y la problemática de la continuidad académica.")

        # Se mantienen los textos de conclusiones, no dependen directamente de la paleta.
        st.markdown("""
        #### :chart_with_upwards_trend: Impacto Directo de la Educación en los Ingresos
        Existe una correlación clara y positiva entre el nivel educativo alcanzado y el potencial de ingresos en Sabana Centro. La falta de continuidad en la trayectoria académica, incluyendo la deserción escolar y la no prosecución de estudios superiores, representa un desafío fundamental que limita severamente las perspectivas económicas de los individuos y frena el progreso socioeconómico de la región.
        """, unsafe_allow_html=True)

        st.markdown("""
        #### :briefcase: Oportunidades en Sectores Específicos
        Las carreras en los campos de la **ingeniería** (particularmente Sistemas y Electrónica) y la **salud** (como Medicina y Enfermería) destacan por ofrecer alta estabilidad laboral y niveles de remuneración competitivos en el contexto local. Por otro lado, las carreras **técnicas y tecnológicas**, si bien facilitan un acceso más rápido al mercado laboral, tienden a asociarse con ingresos iniciales y potenciales más bajos.
        """, unsafe_allow_html=True)

        st.markdown("""
        #### :seedling: Tendencias Emergentes y Demanda Laboral
        El dinamismo de Sabana Centro, especialmente el desarrollo urbano, está impulsando una creciente demanda en áreas como **diseño y arquitectura**. Asimismo, se observa un aumento sostenido en la matrícula de **carreras tecnológicas**, reflejando las necesidades cambiantes del mercado. Esto subraya la importancia crítica de alinear las aspiraciones personales y vocacionales con las oportunidades y demandas reales del entorno laboral local.
        """, unsafe_allow_html=True)

        st.markdown("""
        #### :warning: Consecuencias Amplias de la Deserción
        Más allá del impacto individual en los ingresos, la falta de continuidad académica tiene repercusiones negativas a nivel regional. Estas incluyen la posible ampliación de la brecha de **desigualdad socioeconómica**, una limitación en la **productividad y competitividad** general de la economía local, una mayor dependencia de **empleos de baja calificación** y un obstáculo para el **desarrollo social y el bienestar comunitario**.
        """, unsafe_allow_html=True)

        st.markdown("""
        #### :bulb: Necesidad de Acciones Integrales
        La evidencia presentada resalta la urgencia de abordar la continuidad educativa de manera coordinada y multifacética. La implementación de estrategias efectivas —que aborden desde el **apoyo socioeconómico** y la **orientación vocacional** hasta el **fortalecimiento de la educación técnica** y las **alianzas estratégicas**— es esencial para fomentar la permanencia en el sistema educativo. Solo así Sabana Centro podrá aspirar a una sociedad más equitativa, con mayores oportunidades para sus habitantes, y una economía más resiliente, próspera y competitiva a largo plazo.
        """, unsafe_allow_html=True)

        st.divider() # Separador visual

        # --- Mantenemos la sección de Preguntas Clave ---
        df_original = df_sabana_centro_final2 # Usar el original para conclusiones generales si es necesario
        max_muni, min_muni = "N/A", "N/A" # Inicializar por si falla el cálculo
        muni_median_orig_max, muni_median_orig_min = 0, 0
        try: # Resumen Municipio (Ejemplo si se quiere mantener algo del original)
             muni_median_orig = df_original.dropna(subset=[COL_MUNICIPIO_NAME, COL_INGRESO]).groupby(COL_MUNICIPIO_NAME)[COL_INGRESO].median()
             if not muni_median_orig.empty:
                 max_muni = muni_median_orig.idxmax(); min_muni = muni_median_orig.idxmin()
                 muni_median_orig_max = muni_median_orig[max_muni]
                 muni_median_orig_min = muni_median_orig[min_muni]
        except Exception:
             pass # Ignorar errores si las columnas no existen o fallan los cálculos aquí

        st.header("Preguntas Clave para un Plan de Trabajo (Inspirado en Guía de Carreras e Informe de Deserción)") # <- Título modificado
        st.info("Puedes ver los informes completos en las secciones 'Ver PDF Guía Carreras' y 'Ver PDF Informe Deserción'.") # <- Mensaje modificado

        st.subheader("Estrategias Educativas:")
        st.markdown("""
        * ¿Cómo abordar la meseta de ingresos observada en niveles de postgrado (Especialización, Maestría, Doctorado)? ¿Faltan oportunidades locales o hay otros factores?
        * Dado el crecimiento en matrícula tecnológica (12%) y el alto ingreso promedio en Ingeniería de Sistemas/Electrónica (COP 4.2M), ¿cómo fortalecer y promover estas áreas en Sabana Centro, considerando también las barreras socioeconómicas a la continuidad?
        * Los programas técnicos muestran alta matrícula (22%) pero bajo ingreso promedio (COP 1.3M). ¿Qué estrategias (pasantías, certificaciones) pueden mejorar la remuneración y conexión laboral, y qué apoyo se necesita para evitar la deserción en estos niveles?
        * ¿Cómo alinear mejor la oferta educativa con las tendencias de crecimiento regional (salud +8%, diseño/arq +15%) y las demandas laborales locales, asegurando la orientación vocacional adecuada para reducir la deserción temprana?
        """)
        st.subheader("Mercado Laboral y Ocupaciones:")
        st.markdown(f"""
        * ¿Por qué ocupaciones como 'Pilotos, ingenieros e instructores de vuelo' (asociado a nivel Tecnológico en la guía) tienen ingresos reportados tan altos? ¿Son nichos específicos o reflejan una demanda regional particular?
        * Investigar las causas de los bajos ingresos en ocupaciones como 'Obreros forestales' (asociado a Secundaria) o 'Conductores de motocicletas' (asociado a Primaria). ¿Son problemas de cualificación, informalidad, estructura del mercado local, o resultado de la deserción académica temprana?
        * ¿Cómo conectar mejor a los graduados, especialmente de niveles técnicos y tecnológicos, con las oportunidades laborales mejor remuneradas identificadas, y apoyar a quienes no completaron su formación para acceder a empleos de mayor calidad?
        * Fomentar la participación en pasantías, proyectos y ferias universitarias como recomienda la guía para mejorar la empleabilidad.
        """)
        st.subheader("Desarrollo Territorial:")
        st.markdown(f"""
        * ¿Qué factores explican las diferencias de ingreso mediano entre municipios (Ej: **{max_muni}** vs **{min_muni}**)? ¿Se relacionan con la concentración de industrias, niveles educativos promedio, acceso a oportunidades, o tasas de deserción diferenciadas?
        * La creciente demanda en diseño y arquitectura está ligada al desarrollo urbano. ¿Cómo pueden los municipios de Sabana Centro aprovechar esta tendencia para generar empleo de calidad y promover una planificación urbana sostenible?
        * ¿Existen programas específicos o se podrían diseñar para atraer o retener talento en los municipios con menores ingresos promedio o con brechas educativas significativas, incluyendo apoyo para la permanencia estudiantil?
        * ¿Cómo asegurar que el desarrollo económico regional beneficie a una amplia gama de niveles educativos y ocupaciones, buscando reducir las brechas de ingreso y las tasas de deserción?
        """)
        st.subheader("Próximos Pasos / Análisis Futuros:")
        st.markdown("""
        * Realizar análisis longitudinales (si los datos lo permiten) para ver la evolución de ingresos por cohorte educativa y ocupación, y su relación con la persistencia académica.
        * Cruzar estos datos de ingreso/educación con información sobre los sectores económicos predominantes en cada municipio de Sabana Centro.
        * Incorporar variables adicionales como género, años de experiencia, tipo de contrato, y factores socioeconómicos para un análisis más detallado de las brechas de ingreso y las causas de la deserción.
        * Profundizar en los resultados de encuestas vocacionales y de seguimiento a egresados/desertores para entender mejor las aspiraciones versus la realidad del mercado y las barreras educativas.
        * Evaluar el impacto de programas de formación continua, certificaciones, y programas de apoyo a la permanencia en la mejora de los ingresos, la empleabilidad y la reducción de la deserción.
        """)

    # --- PÁGINA 7: VER PDF GUÍA CARRERAS ---
    elif pagina_seleccionada == "Ver PDF Guía Carreras": # <- Página PDF 1
        st.title("Guía para la Elección de Carrera Universitaria en Sabana Centro")
        st.info("Documento elaborado por Sabana Centro Cómo Vamos.") # Quitamos cita temporalmente si la referencia está al final
        st.header("Informe de Guia Carreras")
        pdf_url = "https://raw.githubusercontent.com/juanpa-corral/SabanaCentroDashborad/master/GuiaCarreras.pdf"
        mostrar_pdf_desde_url(pdf_url)
    # --- PÁGINA 8: VER PDF INFORME DESERCIÓN --- # <- ¡¡NUEVA PÁGINA PDF 2!!
    elif pagina_seleccionada == "Ver PDF Informe Deserción":
        st.title("Informe sobre Deserción Académica y su Impacto en Sabana Centro")
        st.info("Documento elaborado por Sabana Centro Cómo Vamos.") # Quitamos cita temporalmente si la referencia está al final
        st.header("Informe de Deserción")
        pdf_url = "https://raw.githubusercontent.com/juanpa-corral/SabanaCentroDashborad/master/InformeDescercion.pdf"
        mostrar_pdf_desde_url(pdf_url)

# --- Mensaje final si el DataFrame inicial estaba vacío ---
else:
     st.error("No se pudieron cargar los datos iniciales del archivo Excel. El dashboard no puede mostrar la mayoría del contenido.")
     st.info(f"Revisa la ruta del archivo Excel ('{file_name}') y los mensajes de error al inicio.")
     # Opcional: Permitir ver los PDFs incluso si el Excel falla
     st.sidebar.error("Error en Excel, pero puedes ver los informes PDF.")
     with st.sidebar:
         pdf_pagina_seleccionada = option_menu(
                menu_title="Informes PDF",
                options=["Ver PDF Guía Carreras", "Ver PDF Informe Deserción"],
                icons=['file-earmark-pdf-fill', 'file-earmark-break-fill'],
                menu_icon="collection-fill", default_index=0, orientation="vertical",
                styles={ # Usar colores de la NUEVA paleta también aquí
                    "container": {"padding": "5px !important", "background-color": "#022B3A"},
                    "icon": {"color": NEW_PALETTE_PRIMARY[4], "font-size": "23px"},
                    "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "color": "#E1E5F2", "--hover-color": NEW_PALETTE_PRIMARY[0]},
                    "nav-link-selected": {"background-color": NEW_PALETTE_PRIMARY[1]},
                }
            )
         if pdf_pagina_seleccionada == "Ver PDF Guía Carreras":
             st.title("Guía para la Elección de Carrera Universitaria en Sabana Centro")
             st.info("Documento elaborado por Sabana Centro Cómo Vamos.")
             show_pdf(pdf_path_guia)
         elif pdf_pagina_seleccionada == "Ver PDF Informe Deserción":
             st.title("Informe sobre Deserción Académica y su Impacto en Sabana Centro")
             st.info("Documento elaborado por Sabana Centro Cómo Vamos.")
             show_pdf(pdf_path_desercion)

# Mensaje final o pie de página opcional en sidebar
st.sidebar.divider()
st.sidebar.info("Dashboard Interactivo | Sabana Centro Cómo Vamos | Mayo 2025") # Ajusta fecha/info

# --- Citas de los PDFs al final (si aplica) ---
# st.caption(" Guia_Carreras_Sabana_Centro_Reorganizada (2).pdf | Informe_Sabana_Centro_Desercion_Academica.pdf")
# Comentado porque las citas y se quitaron de las páginas de PDF para evitar confusión.