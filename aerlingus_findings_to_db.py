import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, Boolean, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from modules_ai import extract_maintenance_fields_with_examples, generate_extraction_examples, parse_descriptions_bulk_batched, parse_description_deepseek
import json

def process_results(df_to_process,df_with_content, results_descriptions, results_actions):
    try:
        for idx, (result_desc, result_action) in enumerate(zip(results_descriptions, results_actions)):
            if idx < len(df_with_content):
                df_index = df_with_content.index[idx]
                
                # Agregar campos extraídos como nuevas columnas
                if isinstance(result_desc, dict):
                    for key, value in result_desc.items():
                        df_to_process.loc[df_index, f'llm_{key}'] = str(value) if value is not None else None

                if isinstance(result_action, dict):
                    for key, value in result_action.items():
                        df_to_process.loc[df_index, f'llm_action_{key}'] = str(value) if value is not None else None

        # Mostrar algunos ejemplos de los resultados
        llm_columns = [col for col in df_to_process.columns if col.startswith('llm_')]
        if llm_columns:
            print(f"\nCampos extraídos por LLM: {llm_columns}")
            print("\nEjemplos de resultados:")
            for i, idx in enumerate(df_with_content.index[:3]):
                print(f"  Registro {i+1}:")
                print(f"    Original: {df_to_process.loc[idx, 'description_custom'][:80]}...")
                for col in llm_columns[:5]:  # Mostrar solo los primeros 5 campos
                    value = df_to_process.loc[idx, col]
                    print(f"    {col}: {value}")
                print()
        
    except Exception as e:
        print(f"Error procesando con LLM: {e}")
        print("Continuando sin procesamiento LLM...")
    
    return df_to_process

def create_custom_descriptions(df):
    """
    Crear columnas concatenadas para descripción y acción
    """
    # Crear description_custom concatenando header_text, text_plain y text_html
    df['description_custom'] = df[['header_text', 'text_plain', 'text_html']].fillna('').apply(
        lambda x: ' '.join([str(val).strip() for val in x if str(val).strip() != '' and str(val).strip() != 'nan']), axis=1
    )
    
    # Crear action_custom concatenando action_header_text, action_text, action_comment
    df['action_custom'] = df[['action_header_text', 'action_text', 'action_comment']].fillna('').apply(
        lambda x: ' '.join([str(val).strip() for val in x if str(val).strip() != '' and str(val).strip() != 'nan']), axis=1
    )
    
    return df

def process_with_llm(df, batch_size=5, max_records=None, use_deepseek=False):
    """
    Procesar los textos concatenados con LLM para extraer campos estructurados
    """
    # Limitar el número de registros si se especifica
    if max_records:
        df_to_process = df.head(max_records).copy()
    else:
        df_to_process = df.copy()
    
    # Filtrar registros que tengan contenido en description_custom
    df_with_content = df_to_process[
        (df_to_process['description_custom'].str.len() > 10) & 
        (df_to_process['description_custom'] != '')
    ].copy()
    
    print(f"Procesando {len(df_with_content)} registros con LLM...")
    print(f"Usando {'DeepSeek' if use_deepseek else 'Azure OpenAI'}")
    
    if len(df_with_content) == 0:
        print("No hay registros con contenido suficiente para procesar")
        return df_to_process
    
    # Crear lista de descripciones para procesar
    descriptions = df_with_content['description_custom'].tolist()
    actions = df_with_content['action_custom'].tolist()

    # if use_deepseek:
    #     # Procesar una por una con DeepSeek
    #     results = []
    #     for i, description in enumerate(descriptions):
    #         print(f"Procesando registro {i+1}/{len(descriptions)} con DeepSeek...")
    #         try:
    #             result_json = parse_description_deepseek(description)
    #             result = json.loads(result_json)
    #             results.append(result)
    #         except Exception as e:
    #             print(f"Error procesando registro {i+1}: {e}")
    #             results.append({})
    # else:
        # Procesar con Azure OpenAI en batches

    
    # Opción 1: Solo generar ejemplos para análisis
    #examples = generate_extraction_examples(descriptions=descriptions)
    #print(json.dumps(examples, indent=2))

    # Opción 2: Usar extracción con ejemplos dinámicos
    #results = extract_maintenance_fields_with_examples(descriptions, use_deepseek=False)
    

    results_descriptions = parse_descriptions_bulk_batched(
        descriptions,
        batch_size=batch_size,
        prompt_template='extract_description_fields_aerlingus_v1.txt',
        deepseek=use_deepseek
                )
        # results_actions = parse_descriptions_bulk_batched(   #TODO FALTA EL PROMPT
        #     actions,
        #     batch_size=batch_size
        #     prompt_template= 'parse_action_deepseek.txt',
        #     deepseek=use_deepseek
        #           )


###################################################################################################################


    #     process_results(
    #         df_to_process, 
    #         df_with_content, 
    #         results_descriptions, 
    #         results_actions
    #     )
    #     # Aplicar los resultados al dataframe
    # except Exception as e:
    #     print(f"Error procesando con LLM: {e}")
    #     print("Continuando sin procesamiento LLM...")
    



def process_aerlingus(use_llm=True, max_records=None, batch_size=3, use_deepseek=False):
    file_path1 = "data/aerlingus/ohf_ei_data_export_v0_2.csv"

    df1 = pd.read_csv(file_path1)
    df2 = pd.read_csv(file_path2)

    df_total = pd.concat([df1,df2])
    df_total = df_total.sample(n=200, random_state=42).reset_index(drop=True)
    # Mostrar información básica del dataframe
    # print(f"Shape del dataframe: {df_total.shape}")
    # print(f"Columnas disponibles: {list(df_total.columns)}")
    
    # Verificar si las columnas necesarias existen
    required_cols_desc = ['header_text', 'text_plain', 'text_html']
    required_cols_action = ['action_header_text', 'action_text', 'action_comment']
    
    desc_cols_exist = all(col in df_total.columns for col in required_cols_desc)
    action_cols_exist = all(col in df_total.columns for col in required_cols_action)
    
    # print(f"Columnas de descripción disponibles: {desc_cols_exist}")
    # print(f"Columnas de acción disponibles: {action_cols_exist}")
    
    if desc_cols_exist or action_cols_exist:
        # Crear las columnas concatenadas
        df_total = create_custom_descriptions(df_total)
        
        print(f"Columnas creadas exitosamente!")
        
        # Mostrar algunas muestras de las nuevas columnas

        # if 'description_custom' in df_total.columns:
        #     print(f"\nEjemplos de description_custom:")
        #     for i, desc in enumerate(df_total['description_custom'].head(3)):
        #         print(f"  {i+1}: {desc[:100]}...")
        
        # if 'action_custom' in df_total.columns:
        #     print(f"\nEjemplos de action_custom:")
        #     for i, action in enumerate(df_total['action_custom'].head(3)):
        #         print(f"  {i+1}: {action[:100]}...")
        
        # Procesar con LLM si se solicita
        if use_llm:
            print(f"\n{'='*50}")
            print("INICIANDO PROCESAMIENTO CON LLM")
            print(f"{'='*50}")

            df_total = process_with_llm(
                df_total, 
                batch_size=batch_size, 
                max_records=max_records, 
                use_deepseek=use_deepseek
            )
            
            # Guardar resultados en CSV para análisis posterior
            output_file = "exports/aerlingus_processed.csv"
            df_total.to_csv(output_file, index=False)
            print(f"\nResultados guardados en: {output_file}")
    else:
        print("No se encontraron las columnas necesarias para crear los campos concatenados")
    
    return df_total

 

if __name__ == '__main__':
    # Configuración del procesamiento
    USE_LLM = True          # True para usar LLM, False solo para crear campos concatenados
    MAX_RECORDS = 200         # Número máximo de registros a procesar (None para todos)
    BATCH_SIZE = 5          # Tamaño del batch para LLM
    USE_DEEPSEEK = False     # True para usar DeepSeek, False para Azure OpenAI
    
    print("PROCESAMIENTO DE DATOS AERLINGUS")
    print(f"Configuración:")
    print(f"  - Usar LLM: {USE_LLM}")
    print(f"  - Máximo registros: {MAX_RECORDS if MAX_RECORDS else 'Todos'}")
    print(f"  - Tamaño de batch: {BATCH_SIZE}")
    print(f"  - Usar DeepSeek: {USE_DEEPSEEK}")
    print("-" * 50)
    
    df_result = process_aerlingus(
        use_llm=USE_LLM, 
        max_records=MAX_RECORDS, 
        batch_size=BATCH_SIZE,
        use_deepseek=USE_DEEPSEEK
    )
    
    print(f"\nProcesamiento completado. Shape final: {df_result.shape}")