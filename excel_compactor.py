import pandas as pd

def concat_sheets_with_taskbar_id(excel_path):
    # Lee todas las hojas en un diccionario de DataFrames
    all_sheets = pd.read_excel(excel_path, sheet_name=None)
    # Lista para almacenar los DataFrames modificados
    dfs = []
    for sheet_name, df in all_sheets.items():
        df['taskbar_id'] = sheet_name  # Añade la columna con el nombre de la hoja
        dfs.append(df)
    # Concatena todos los DataFrames en uno solo
    df_concat = pd.concat(dfs, ignore_index=True)
    return df_concat

if __name__ == "__main__":
    excel_path1 = r"C:\Users\CristianEscudero\Downloads\Findings.xlsx"
    excel_path2 = r"C:\Users\CristianEscudero\Downloads\Findings_PP.xlsx"
    findings_pp = concat_sheets_with_taskbar_id(excel_path2)
    # Puedes guardar el resultado si lo deseas:
    findings_pp.to_excel(r"data\Findings_PP_compactado.xlsx", index=False)