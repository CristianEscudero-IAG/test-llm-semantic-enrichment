import pandas as pd
import sqlite3
from sqlalchemy import create_engine
import os

def export_table_to_csv(table_name, db_path='aircraft_data.db', output_dir='exports'):
    """
    Exporta una tabla de SQLite a CSV
    
    Args:
        table_name: Nombre de la tabla a exportar
        db_path: Ruta a la base de datos SQLite
        output_dir: Directorio donde guardar los archivos CSV
    """
    # Crear directorio de exportación si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Conectar a la base de datos SQLite
        engine = create_engine(f'sqlite:///{db_path}')
        
        # Leer la tabla completa
        print(f"Exportando tabla '{table_name}'...")
        df = pd.read_sql_table(table_name, engine)
        
        # Crear nombre del archivo CSV
        csv_filename = os.path.join(output_dir, f'{table_name}.csv')
        
        # Exportar a CSV
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        
        print(f"✅ Tabla '{table_name}' exportada exitosamente")
        print(f"📁 Archivo: {csv_filename}")
        print(f"📊 Filas exportadas: {len(df)}")
        print(f"📋 Columnas: {len(df.columns)}")
        print(f"🔍 Columnas disponibles: {list(df.columns)}")
        print("-" * 60)
        
        return df
        
    except Exception as e:
        print(f"❌ Error exportando tabla '{table_name}': {str(e)}")
        return None

def export_all_tables(db_path='aircraft_data.db', output_dir='exports'):
    """
    Exporta todas las tablas de la base de datos a CSV
    """
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener lista de todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"🗄️  Base de datos: {db_path}")
        print(f"📊 Tablas encontradas: {len(tables)}")
        print("=" * 60)
        
        exported_tables = []
        
        for table in tables:
            table_name = table[0]
            df = export_table_to_csv(table_name, db_path, output_dir)
            if df is not None:
                exported_tables.append(table_name)
        
        conn.close()
        
        print("=" * 60)
        print(f"🎉 Exportación completada!")
        print(f"✅ Tablas exportadas: {len(exported_tables)}")
        print(f"📁 Directorio de salida: {output_dir}")
        
        return exported_tables
        
    except Exception as e:
        print(f"❌ Error accediendo a la base de datos: {str(e)}")
        return []

def main():
    """Función principal"""
    print("🔄 EXPORTADOR DE TABLAS SQLITE A CSV")
    print("=" * 60)
    
    # Especificar qué exportar
    export_specific = input("¿Exportar solo 'finding_description_tasks'? (s/n): ").lower().strip()
    
    if export_specific in ['s', 'si', 'yes', 'y']:
        # Exportar solo la tabla específica
        export_table_to_csv('finding_description_tasks')
        
        # También exportar finding_work_orders si existe
        export_table_to_csv('finding_work_orders')
        
    else:
        # Exportar todas las tablas
        export_all_tables()

if __name__ == '__main__':
    main()
