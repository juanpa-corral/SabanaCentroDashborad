import pandas as pd
import pywin32.client as win32

def copiar_correos_a_cc_por_lotes(archivo_excel, nombre_hoja='Hoja1', tamano_lote=400):
    """
    Copia correos electrónicos de un archivo de Excel y los pega en el campo CC de Outlook en lotes.

    Args:
        archivo_excel (str): Ruta al archivo de Excel.
        nombre_hoja (str, optional): Nombre de la hoja de cálculo. Defaults to 'Hoja1'.
        tamano_lote (int, optional): Tamaño de cada lote de correos. Defaults to 400.
    """
    try:
        df = pd.read_excel(archivo_excel, sheet_name=nombre_hoja)
        total_correos = len(df)
        inicio = 0

        while inicio < total_correos:
            fin = min(inicio + tamano_lote, total_correos)
            lote_correos = df['Correos'][inicio:fin].astype(str).tolist() #Reemplaza 'Correo electrónico' con el nombre de tu columna
            correos_cc = ';'.join(lote_correos)

            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)
            mail.CC = correos_cc
            mail.Display()

            inicio = fin

    except FileNotFoundError:
        print(f"Error: el archivo '{archivo_excel}' no se encontró.")
    except Exception as e:
        print(f"Error general: {e}")

# Ejemplo de uso
archivo_excel = "d:/Users/JuanPa/Downloads/Correos.xlsx"
copiar_correos_a_cc_por_lotes(archivo_excel)