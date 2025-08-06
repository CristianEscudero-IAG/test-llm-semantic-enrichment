import os
import json
import time
from langchain_openai import AzureChatOpenAI
from openai import OpenAI
import re
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def load_prompt(filename):
    """Load prompt from prompts folder"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, 'prompts', filename)
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def deepseek_request(prompt):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY no encontrada. Configura la variable de entorno.")

    client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    )

    completion = client.chat.completions.create(
    extra_headers={
        "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
        "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    },
    extra_body={},
    model="deepseek/deepseek-r1-0528:free",
    messages=[
        {
          "role": "user",
          "content": f"{prompt}"
        }
  ]
     )
    return completion.choices[0].message.content
    #print(completion.choices[0].message.content)


def parse_description_deepseek(description):
    prompt_template = load_prompt('parse_description_deepseek_2.txt')
    prompt = prompt_template.format(description=description)
    response_json = deepseek_request(prompt)
    return response_json
    


def parse_descriptions_bulk_batched(descriptions, batch_size, prompt_template, deepseek):
    all_results = []
    for i in range(0, len(descriptions), batch_size):
        batch = descriptions[i:i+batch_size]
        results = parse_descriptions_bulk(prompt_template, batch, deepseek)
        all_results.extend(results)
        time.sleep(60)
    return all_results




def parse_descriptions_bulk(prompt_template_filename, descriptions: list, deepseek: bool) -> list:
    prompt_template = load_prompt(prompt_template_filename)
    
    # Prepare descriptions for the template
    descriptions_text = ""
    for i, desc in enumerate(descriptions, 1):
        descriptions_text += f"\nDescription {i}: {desc}"
    
    prompt = prompt_template.format(description=descriptions_text)

    if deepseek:
        content = deepseek_request(prompt)
    else:
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("OPENAI_API_ENDPOINT"),
            azure_deployment="gpt-4o-mini",
            api_version=os.getenv("OPENAI_API_VERSION"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
            max_tokens=4000,  # Aumentar tokens para respuestas más largas
        )

        response = llm.invoke(prompt)
        # Extraer el contenido correctamente del objeto AIMessage
        content = response.content if hasattr(response, 'content') else str(response)

    # Manejo robusto de la respuesta JSON
    def extract_json_array(text, num_expected_items):
        # Intenta limpiar bloques de código
        clean_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        
        try:
            # Intenta cargar el texto limpio directamente
            return json.loads(clean_text)
        except json.JSONDecodeError:
            try:
                # Busca el primer array JSON válido
                match = re.search(r'(\[\s*{.*}\s*\])', clean_text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            except Exception:
                pass
            
            try:
                # Si el JSON está incompleto, intenta completarlo
                if clean_text.strip().startswith('[') and not clean_text.strip().endswith(']'):
                    # Busca el último objeto completo
                    last_complete = clean_text.rfind('}')
                    if last_complete != -1:
                        truncated_json = clean_text[:last_complete + 1] + ']'
                        return json.loads(truncated_json)
            except Exception:
                pass
        
        # Si todo falla, devuelve array vacío con el número esperado de elementos
        print(f"Warning: No se pudo parsear el JSON. Devolviendo array vacío.")
        print(f"Contenido recibido: {text[:200]}...")
        return [{} for _ in range(num_expected_items)]
    
    data = extract_json_array(content, len(descriptions))
    
    # Asegurar que tenemos el número correcto de elementos
    if len(data) != len(descriptions):
        print(f"Warning: Se esperaban {len(descriptions)} elementos, pero se obtuvieron {len(data)}")
        # Ajustar la lista para que tenga la longitud correcta
        if len(data) < len(descriptions):
            data.extend([{} for _ in range(len(descriptions) - len(data))])
        else:
            data = data[:len(descriptions)]
    
    return data





def parsing_regex_fields(description):
    # Definir patrones regex
    taskcard_pattern = r"TASKCARD\\s([A-Z0-9\\-]+)"
    work_order_pattern = r"WO([0-9]+)"
    location_pattern = r"AFT CARGO"
    panel_code_pattern = r"SIDEWALLPANEL\\s([A-Z0-9]+)"
    part_number_pattern = r"P/N([A-Z0-9]+)"
    amm_task_pattern = r"AMM TASK ([0-9\\-]+)"
    amm_revision_pattern = r"AMM ([0-9\\-]+) REV ([0-9]+)"
    
    # Extraer campos usando regex
    taskcard = re.search(taskcard_pattern, description).group(1)
    work_order = re.search(work_order_pattern, description).group(1)
    location = re.search(location_pattern, description).group(0)
    panel_code = re.search(panel_code_pattern, description).group(1)
    part_numbers = re.findall(part_number_pattern, description)
    amm_tasks = re.findall(amm_task_pattern, description)
    amm_revisions = [{"task": match[0], "revision": match[1]} for match in re.findall(amm_revision_pattern, description)]
    
    # Determinar acciones
    send_to_workshop = "SEND TO WORKSHOP" in description
    damage_out_of_limits = "DAMAGES OUT OF LIMITS" in description
    supply_new_panel = "SUPPLY A NEW PANEL" in description
    
    # Crear el diccionario de resultados
    result = {
        "taskcard": taskcard,
        "work_order": work_order,
        "location": location,
        "panel_code": panel_code,
        "part_numbers": part_numbers,
        "amm_tasks": amm_tasks,
        "amm_revisions": amm_revisions,
        "actions": {
            "send_to_workshop": send_to_workshop,
            "damage_out_of_limits": damage_out_of_limits,
            "supply_new_panel": supply_new_panel
        }
    }
    
    return result

def test_json_parsing(response_content):
    """
    Función auxiliar para probar el parsing de JSON
    """
    def extract_json_array(text):
        clean_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            try:
                match = re.search(r'(\[\s*{.*}\s*\])', clean_text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            except Exception:
                pass
            
            try:
                if clean_text.strip().startswith('[') and not clean_text.strip().endswith(']'):
                    last_complete = clean_text.rfind('}')
                    if last_complete != -1:
                        truncated_json = clean_text[:last_complete + 1] + ']'
                        return json.loads(truncated_json)
            except Exception:
                pass
        
        return []
    
    try:
        parsed = extract_json_array(response_content)
        print(f"✅ JSON parseado exitosamente. {len(parsed)} elementos encontrados.")
        return parsed
    except Exception as e:
        print(f"❌ Error al parsear JSON: {e}")
        return []

def extract_maintenance_fields(descriptions: list, use_deepseek: bool = True) -> list:
    """
    Extrae campos de mantenimiento estandarizados de las descripciones
    """
    prompt_template = load_prompt('extract_maintenance_fields.txt')
    
    # Preparar las descripciones para el template
    descriptions_text = ""
    for i, desc in enumerate(descriptions, 1):
        descriptions_text += f"\nDescription {i}: {desc}"
    
    prompt = prompt_template.format(description=descriptions_text)

    if use_deepseek:
        content = deepseek_request(prompt)
    else:
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("OPENAI_API_ENDPOINT"),
            azure_deployment="gpt-4o-mini",
            api_version=os.getenv("OPENAI_API_VERSION"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
            max_tokens=4000,
        )

        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

    # Usar la función de extracción JSON existente
    def extract_json_array(text, num_expected_items):
        clean_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            try:
                match = re.search(r'(\[\s*{.*}\s*\])', clean_text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            except Exception:
                pass
            
            try:
                if clean_text.strip().startswith('[') and not clean_text.strip().endswith(']'):
                    last_complete = clean_text.rfind('}')
                    if last_complete != -1:
                        truncated_json = clean_text[:last_complete + 1] + ']'
                        return json.loads(truncated_json)
            except Exception:
                pass
        
        # Si todo falla, devuelve estructura vacía con todos los campos
        print(f"Warning: No se pudo parsear el JSON. Devolviendo estructura vacía.")
        empty_structure = {
            "description_id": None,
            "maintenance_type": None,
            "component": None,
            "part_number": None,
            "serial_number": None,
            "position": None,
            "action": None,
            "result": None,
            "reference": None,
            "location": None,
            "date": None,
            "finding": None,
            "taskcard": None,
            "finding_related": False,
            "task_type": None,
            "failure_description": None,
            "corrective_action": None,
            "engineering_order": None,
            "eo_revision": None,
            "task": None,
            "instructions": None,
            "reporting": None,
            "personnel": None,
            "findings": [],
            "additional_notes": None
        }
        return [empty_structure for _ in range(num_expected_items)]
    
    data = extract_json_array(content, len(descriptions))
    
    # Asegurar que todos los objetos tienen los campos requeridos
    required_fields = ['description_id', 'maintenance_type', 'component', 'part_number', 
                      'serial_number', 'position', 'action', 'result', 'reference', 
                      'location', 'date', 'finding', 'taskcard', 'finding_related', 'task_type', 
                      'failure_description', 'corrective_action', 'engineering_order', 'eo_revision', 
                      'task', 'instructions', 'reporting', 'personnel', 'additional_notes']
    
    for item in data:
        for field in required_fields:
            if field not in item:
                if field == 'finding_related':
                    item[field] = False
                else:
                    item[field] = None
        # Asegurar que findings es una lista
        if 'findings' not in item:
            item['findings'] = []
    
    return data

def generate_extraction_examples(descriptions: list, use_deepseek: bool = False) -> dict:
    """
    Genera ejemplos de extracción basados en las descripciones proporcionadas
    """
    prompt_template = load_prompt('generate_extraction_examples.txt')
    
    # Preparar las descripciones para el template (limitar a 10 para análisis)
    descriptions_text = ""
    sample_descriptions = descriptions[:10] if len(descriptions) > 10 else descriptions
    
    for i, desc in enumerate(sample_descriptions, 1):
        descriptions_text += f"\nDescription {i}: {desc}"
    
    prompt = prompt_template.format(description=descriptions_text)

    if use_deepseek:
        content = deepseek_request(prompt)
    else:
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("OPENAI_API_ENDPOINT"),
            azure_deployment="gpt-4o-mini",
            api_version=os.getenv("OPENAI_API_VERSION"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
            max_tokens=3000,
        )

        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

    try:
        # Limpiar y parsear JSON
        clean_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
        examples = json.loads(clean_content)
        return examples
    except Exception as e:
        print(f"Error parsing examples: {e}")
        return {
            "error": "Could not generate examples", 
            "raw_content": content[:500] + "..." if len(content) > 500 else content
        }

def create_enhanced_extraction_prompt(examples: dict) -> str:
    """
    Crea un prompt mejorado para extracción usando los ejemplos generados
    """
    if "error" in examples:
        return "Error: No se pudieron generar ejemplos válidos"
    
    # Extraer patrones de los ejemplos
    patterns = examples.get("extraction_patterns", {})
    field_rules = examples.get("field_identification_rules", {})
    example_extractions = examples.get("example_extractions", [])
    
    # Crear sección de ejemplos para el prompt
    examples_section = ""
    if example_extractions:
        examples_section = "\nEXTRACTION EXAMPLES:\n"
        for i, example in enumerate(example_extractions[:3], 1):
            examples_section += f"\nExample {i}:\n"
            examples_section += f"Text: {example.get('sample_text', 'N/A')}\n"
            examples_section += f"Extracted: {json.dumps(example.get('extracted_fields', {}), indent=2)}\n"
    
    # Crear sección de patrones
    patterns_section = ""
    if patterns:
        patterns_section = "\nCOMMON PATTERNS FOUND:\n"
        for pattern_type, pattern_list in patterns.items():
            if pattern_list:
                patterns_section += f"- {pattern_type}: {', '.join(pattern_list[:5])}\n"
    
    enhanced_prompt = f"""
FIELD IDENTIFICATION GUIDANCE:
{json.dumps(field_rules, indent=2) if field_rules else "Use standard aircraft maintenance field identification"}

{patterns_section}

{examples_section}

Use these patterns and examples to guide your field extraction from the maintenance descriptions.
"""
    
    return enhanced_prompt

def extract_maintenance_fields_with_examples(descriptions: list, use_deepseek: bool = False) -> list:
    """
    Extrae campos de mantenimiento usando ejemplos generados dinámicamente
    """
    print("Generando ejemplos de extracción...")
    
    # Paso 1: Generar ejemplos basados en las descripciones
    # examples = generate_extraction_examples(descriptions, use_deepseek)
    
    # if "error" in examples:
    #     print("Warning: No se pudieron generar ejemplos. Usando extracción estándar.")
    #     return extract_maintenance_fields(descriptions, use_deepseek)
    
    # print("Ejemplos generados exitosamente. Procediendo con extracción...")
    
    # Paso 2: Crear prompt mejorado con ejemplos
    # enhanced_guidance = create_enhanced_extraction_prompt(examples)
    
    # Paso 3: Usar extracción con el contexto mejorado
    return extract_maintenance_fields(descriptions, use_deepseek)

# def extract_maintenance_fields_enhanced(descriptions: list, use_deepseek: bool = True) -> list:
#     """
#     Extrae campos usando el prompt mejorado con ejemplos
#     """
#     # El prompt ya incorpora el enhanced_guidance, así que usamos la función estándar
#     return extract_maintenance_fields(descriptions, use_deepseek)

# Ejemplo de uso:
# parsed_data = test_json_parsing(response.content)
