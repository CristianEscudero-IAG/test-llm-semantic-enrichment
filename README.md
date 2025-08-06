# 🛩️ Sistema de Procesamiento de Datos de Mantenimiento de Aeronaves

## 📋 Descripción General

Este proyecto procesa y analiza datos de hallazgos de mantenimiento de aeronaves de **Aerlingus** e **Iberia** utilizando técnicas de procesamiento de lenguaje natural (NLP) y modelos de inteligencia artificial para extraer información estructurada de descripciones en texto libre.

## 🏗️ Arquitectura del Sistema

El sistema consta de dos pipelines principales de procesamiento:

### 1. Pipeline Aerlingus (`aerlingus_findings_to_db.py`)
### 2. Pipeline Iberia (`iberia_findings_to_db.py`)

## 📁 Estructura del Proyecto

```
eda/
├── aerlingus_findings_to_db.py     # Procesamiento de datos Aerlingus
├── iberia_findings_to_db.py        # Procesamiento de datos Iberia
├── modules_ai.py                   # Funciones de IA y LLM
├── modules.py                      # Utilidades generales
├── settings.py                     # Configuraciones y mapeos
├── eda_jupyter.ipynb              # Análisis exploratorio
├── requirements.txt               # Dependencias
├── aircraft_data.db               # Base de datos SQLite
├── data/
│   ├── aerlingus/                 # Datos CSV de Aerlingus
│   └── iberia/                    # Datos Excel de Iberia
├── exports/                       # Archivos de salida
└── prompts/                       # Templates de prompts para LLM
    ├── extract_description_fields_aerlingus_v1.txt
    ├── extract_description_fields_iberia.txt
    └── generate_extraction_examples_aerlingus.txt
```

## 🚀 Instalación y Configuración

### 1. Requisitos del Sistema
- Python 3.8+
- SQLite
- Acceso a Azure OpenAI o DeepSeek API

### 2. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 3. Variables de Entorno
Crear archivo `.env` con:
```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=tu_clave_azure
AZURE_OPENAI_ENDPOINT=tu_endpoint_azure
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# OpenRouter/DeepSeek (opcional)
OPENROUTER_API_KEY=tu_clave_openrouter
```

## 📊 Pipeline Aerlingus

### 🎯 Objetivo
Procesar archivos CSV de Aerlingus para extraer información estructurada de descripciones de mantenimiento y acciones correctivas.

### 📥 Datos de Entrada
- **Archivos**: `ohf_ei_data_export_v0_1.csv`, `ohf_ei_data_export_v0_2.csv`
- **Ubicación**: `data/aerlingus/`

### 🔄 Proceso
1. **Carga de Datos**: Combina múltiples archivos CSV
2. **Concatenación de Campos**: Crea campos unificados:
   - `description_custom`: `header_text` + `text_plain` + `text_html`
   - `action_custom`: `action_header_text` + `action_text` + `action_comment`
3. **Procesamiento LLM**: Extrae campos estructurados usando IA
4. **Exportación**: Guarda resultados en `exports/aerlingus_processed.csv`

### ⚙️ Configuración Disponible
```python
# En aerlingus_findings_to_db.py
USE_LLM = True          # Activar procesamiento con IA
MAX_RECORDS = 200       # Límite de registros (None = todos)
BATCH_SIZE = 5          # Tamaño de lote para LLM
USE_DEEPSEEK = False    # Usar DeepSeek en lugar de Azure OpenAI
```

### 🏃 Ejecución
```bash
python aerlingus_findings_to_db.py
```

### 📋 Campos Extraídos por LLM
- `llm_component`: Componente afectado
- `llm_location`: Ubicación del hallazgo
- `llm_defect_type`: Tipo de defecto
- `llm_severity`: Severidad del problema
- `llm_action_taken`: Acción realizada
- `llm_parts_required`: Partes necesarias

## 📊 Pipeline Iberia

### 🎯 Objetivo
Procesar archivos Excel de Iberia para crear base de datos estructurada con tablas relacionales para hallazgos y órdenes de trabajo.

### 📥 Datos de Entrada
- **Archivo**: `Findings_PP_compactado.xlsx`
- **Ubicación**: `data/iberia/`

### 🏗️ Esquema de Base de Datos
#### Tabla `finding_description_tasks`
- `taskbar_id` (PK): Identificador único de tarea
- `wo_number`: Número de orden de trabajo
- `raw_description`: Descripción original
- `taskcard`: Código de tarjeta de tarea
- `location`: Ubicación del hallazgo
- `part_numbers`: Números de parte (CSV)
- `amm_task`: Tarea AMM
- `finding`: Hallazgo identificado
- `serial_number`: Número de serie
- Flags booleanos: `send_to_workshop`, `damage_out_of_limits`, `supply_new_material`

#### Tabla `finding_work_orders`
- `taskbar_id` (FK): Referencia a tarea
- `wo_number`: Número de orden de trabajo
- `ac`: Aeronave
- `date`: Fecha
- `ata`: Código ATA
- `flags`: Banderas
- `reason`: Razón codificada

### 🔄 Proceso
1. **Carga**: Lee Excel con datos de hallazgos
2. **Muestreo**: Selecciona 100 registros aleatorios para prueba
3. **Mapeo de Códigos**: Convierte códigos de defecto usando `defect_code_dict`
4. **Procesamiento LLM**: Extrae campos estructurados en lotes
5. **Persistencia**: Guarda en base de datos SQLite con relaciones

### 🏃 Ejecución
```bash
python iberia_findings_to_db.py
```

### 📋 Campos Extraídos por LLM
- `taskcard`: Código de tarjeta de tarea
- `location`: Ubicación del problema
- `panel_code`: Código del panel
- `part_numbers`: Lista de números de parte
- `amm_tasks`: Tareas AMM con descripción
- `actions`: Acciones requeridas
- `finding`: Hallazgo específico
- `repair_reference`: Referencia de reparación

## 🤖 Módulo de IA (`modules_ai.py`)

### 🔧 Funciones Principales

#### `parse_descriptions_bulk_batched()`
- **Propósito**: Procesa descripciones en lotes usando LLM
- **Parámetros**:
  - `descriptions`: Lista de textos a procesar
  - `batch_size`: Tamaño del lote
  - `prompt_template`: Archivo de prompt a usar
  - `deepseek`: Usar DeepSeek API (True/False)

#### `deepseek_request()`
- **Propósito**: Realiza peticiones a DeepSeek vía OpenRouter
- **Modelo**: `deepseek/deepseek-r1-0528:free`

#### `load_prompt()`
- **Propósito**: Carga templates de prompts desde carpeta `prompts/`

### 📝 Templates de Prompts
- `extract_description_fields_aerlingus_v1.txt`: Para datos Aerlingus
- `extract_description_fields_iberia.txt`: Para datos Iberia
- `generate_extraction_examples_aerlingus.txt`: Generación de ejemplos

## 📈 Análisis Exploratorio

### 🔍 Notebook Jupyter (`eda_jupyter.ipynb`)
Contiene análisis completo con:
- **Estadísticas descriptivas** de ambos datasets
- **Visualizaciones comparativas** entre Descriptions vs Actions
- **Análisis de calidad de datos**
- **Evaluación de completitud de campos**
- **N-gramas y frecuencias de palabras**
- **Detección de residuos HTML**

### 📊 Métricas Clave
- **Aerlingus Descriptions**: 82,806 registros (146.9 chars promedio)
- **Aerlingus Actions**: 34,812 registros (200.2 chars promedio)
- **Residuos HTML detectados**: 26,670 registros

## ⚡ Optimizaciones y Configuración

### 🎛️ Parámetros de Rendimiento
```python
# Tamaños de lote recomendados
AERLINGUS_BATCH_SIZE = 5    # Óptimo para Azure OpenAI
IBERIA_BATCH_SIZE = 2       # Conservador para textos complejos

# Límites de procesamiento
MAX_RECORDS_DEV = 200       # Para desarrollo/pruebas
MAX_RECORDS_PROD = None     # Para producción completa
```

### 🔄 Estrategias de Recuperación
- **Reintento automático** en caso de fallo de API
- **Guardado de progreso** en archivos pickle
- **Procesamiento incremental** por lotes

## 🛡️ Gestión de Errores

### 🚨 Errores Comunes
1. **API Key faltante**: Verificar variables de entorno
2. **Límites de API**: Reducir `batch_size`
3. **Columnas faltantes**: Verificar estructura de datos de entrada
4. **Timeout de LLM**: Aumentar delays entre llamadas

### 🔧 Logs y Debugging
```python
# Activar logs detallados
import logging
logging.basicConfig(level=logging.INFO)
```

## 📁 Archivos de Salida

### Aerlingus
- `exports/aerlingus_processed.csv`: Datos procesados con campos LLM

### Iberia
- `aircraft_data.db`: Base de datos SQLite con tablas relacionales
- `data/iberia/parsed_list.pkl`: Resultados de procesamiento LLM (backup)

## 🔮 Próximas Mejoras

- [ ] **Procesamiento de acciones** para Aerlingus
- [ ] **Validación de campos extraídos** por LLM
- [ ] **Dashboard interactivo** para visualización
- [ ] **API REST** para consultas
- [ ] **Integración con más aerolíneas**
- [ ] **Métricas de calidad** de extracción LLM

## 🤝 Contribución

Para contribuir al proyecto:
1. Fork del repositorio
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📞 Soporte

Para dudas o problemas:
- Revisar logs de ejecución
- Verificar configuración de API keys
- Consultar documentación de prompts en `prompts/README.md`

---

**🔧 Última actualización**: Agosto 2025  
**✅ Estado**: Funcional y optimizado  
**🎯 Versión**: 1.0.0
