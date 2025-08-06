import pandas as pd
import time
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from modules import load_pickle, write_to_pickle
from modules_ai import parse_descriptions_bulk_batched

from settings import defect_code_dict

# Initialize declarative base
Base = declarative_base()

class Taskbar(Base):
    __tablename__ = 'finding_description_tasks'
    id = Column(Integer, primary_key=True)
    taskbar_id = Column(String(50), unique=False, nullable=False)
    wo_number = Column(String(50), nullable=False)
    taskcard = Column(String(50))
    item_work_order = Column(String(50))
    location = Column(String(50))
    panel_code = Column(String(20))
    part_numbers = Column(Text)  # Coma separada, no lista JSON
    amm_task = Column(String(100))  # Primer código de tarea AMM
    amm_description = Column(Text)  # Primer descripción de tarea AMM
    amm_revisions_task = Column(String(50))  # Primer código de revisión AMM
    amm_revisions_code = Column(String(20))  # Primer código de revisión
    send_to_workshop = Column(Boolean)
    damage_out_of_limits = Column(Boolean)
    supply_new_material = Column(Boolean)
    raw_description = Column(Text)
    finding = Column(String(255))
    item = Column(String(50))
    fin = Column(String(50))
    serial_number = Column(String(100), nullable=True)
    repair_reference = Column(String(255), nullable=True)

    work_orders = relationship('WorkOrder', back_populates='taskbar')

class WorkOrder(Base):
    __tablename__ = 'finding_work_orders'
    id = Column(Integer, primary_key=True)
    # Corregir la referencia del ForeignKey al nombre real de la tabla
    taskbar_id = Column(String(50), ForeignKey('finding_description_tasks.taskbar_id'))
    wo_number = Column(String(50), nullable=False)
    ac = Column(String(10))
    date = Column(Date)
    ata = Column(String(10))
    flags = Column(String(50))
    non_relevant = Column(Boolean)
    reason = Column(Text)
    
    taskbar = relationship('Taskbar', back_populates='work_orders')

engine = create_engine('sqlite:///aircraft_data.db')
Base.metadata.create_all(engine)

def get_information_parsed_from_llm(descriptions, batch_size=2):
    parsed_list = []
    
    for i in range(0, len(descriptions), batch_size):
        batch_descriptions = descriptions[i:i+batch_size]

        batch_results = parse_descriptions_bulk_batched(
            batch_descriptions,
            batch_size,
              deepseek=False,
              prompt_template='prompts/extract_description_fields_iberia.txt'
              )
        
        parsed_list.extend(batch_results)
        time.sleep(1)
    write_to_pickle(parsed_list)
    return parsed_list


def process_findings(file_path):
    df_original = pd.read_excel(file_path, sheet_name='Sheet1')
    df = df_original.sample(n=100, random_state=42).reset_index(drop=True)
    df['Reason'] = df['Reason'].map(defect_code_dict)
    df['Reason'] = df['Reason'].str.lower()
    df['Description'] = df['Description'].str.lower()
    Session = sessionmaker(bind=engine)
    session = Session()

    # Verificar columnas requeridas
    required_columns = ['taskbar_id',
                        'Description',
                        'W/O', 'A/C',
                        'Date',
                        'ATA',
                        'Flags',
                        'Non-Relevant',
                        'Reason'
                    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Excel file is missing required columns: {missing_columns}")

    descriptions = df['Description'].tolist()
    #descriptions = list(map(parsing_regex_fields, descriptions))  # REGEX MODE (NO PERFORMA, MUCHA VARIACIÓN EN EL DATO)
    ##Procesar en lotes de 50 manteniendo el orden
    parsed_description_list = []
    parsed_description_list = get_information_parsed_from_llm(descriptions, batch_size=2)
    #parsed_list = load_pickle() # Cargar resultados procesados previamente

    for index, row in df.iterrows():
        try:
            taskbar_id = row['taskbar_id']
            taskbar = session.query(Taskbar).filter_by(taskbar_id=taskbar_id).first()
            parsed = parsed_description_list[index] if index < len(parsed_description_list) else {}

            # Extraer valores simples de los campos JSON
            part_numbers_str = ",".join(parsed.get('part_numbers', []))
            amm_tasks = parsed.get('amm_tasks', [])
            amm_task = None
            amm_description = None
            if amm_tasks:
                if isinstance(amm_tasks[0], dict):
                    amm_task = amm_tasks[0].get('task')
                    amm_description = amm_tasks[0].get('description')
                else:
                    amm_task = amm_tasks[0]
                    amm_description = None
            amm_revisions = parsed.get('amm_revisions', [])
            amm_revisions_task = amm_revisions[0]['task'] if amm_revisions else None
            amm_revisions_code = amm_revisions[0]['revision'] if amm_revisions else None
            actions = parsed.get('actions', {})
            send_to_workshop = actions.get('send_to_workshop', False)
            damage_out_of_limits = actions.get('damage_out_of_limits', False)
            supply_new_material = actions.get('supply_new_material', False)

            taskbar = Taskbar(
                taskbar_id=taskbar_id,
                wo_number=row.get('W/O'),
                raw_description=row['Description'],
                taskcard=parsed.get('taskcard'),
                item_work_order=parsed.get('work_order'),
                location=parsed.get('location'),
                panel_code=parsed.get('panel_code'),
                part_numbers=part_numbers_str,
                amm_task=amm_task,
                amm_description=amm_description,
                amm_revisions_task=amm_revisions_task,
                amm_revisions_code=amm_revisions_code,
                send_to_workshop=send_to_workshop,
                damage_out_of_limits=damage_out_of_limits,
                supply_new_material=supply_new_material,
                finding=parsed.get('finding'),
                item=parsed.get('item'),
                fin=parsed.get('fin'),
                serial_number=parsed.get('serial_number'),
                repair_reference=parsed.get('repair_reference')
            )
            session.add(taskbar)
            session.commit()
            
            work_order = WorkOrder(
                taskbar_id=taskbar_id,
                wo_number=row.get('W/O'),
                ac=row.get('A/C'),
                date=row.get('Date'),
                ata=row.get('ATA'),
                flags=row.get('Flags'),
                non_relevant=bool(row.get('Non-Relevant', False)),
                reason=row.get('Reason')
            )
            session.add(work_order)
        except KeyError as e:
            print(f"Error processing row {index}: Missing column {e}")
        except Exception as e:
            print(f"Error processing row {index}: {str(e)}")
    
    session.commit()
    print(f"Imported {len(df)} records successfully!")

if __name__ == '__main__':
    findings_file = "data/iberia/Findings_PP_compactado.xlsx"
    process_findings(findings_file)