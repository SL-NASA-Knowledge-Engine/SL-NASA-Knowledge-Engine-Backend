# scripts/3_create_mapping.py
import json
import re
import logging
import sys
import os

# Añade la raíz del proyecto al path para que los imports funcionen
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from infrastructure.openai_service import OpenAIMessageService

# --- CONFIGURACIÓN ---
# Archivos de entrada y salida dentro de la carpeta /resources
RESOURCES_DIR = "resources"
TOP_RELATIONS_FILE = os.path.join(RESOURCES_DIR, "top_relations.txt")
OUTPUT_MAPPING_FILE = os.path.join(RESOURCES_DIR, "relation_map.json")

def generate_mapping_with_ai(openai_service: OpenAIMessageService, relations_text: str):
    """
    Usa la IA para leer una lista de relaciones y proponer una agrupación canónica.
    """
    if not openai_service or not relations_text.strip():
        return {}

    system_prompt = """
    Eres un experto en modelado de datos y ontologías para grafos de conocimiento.
    Tu tarea es analizar una lista de frases de relaciones extraídas de textos científicos y agruparlas en categorías semánticas consistentes.
    """

    user_prompt = f"""
    **Instrucciones:**
    1.  Analiza la siguiente lista de relaciones y sus frecuencias.
    2.  Agrupa las relaciones que tengan un significado similar.
    3.  Para cada grupo, crea una etiqueta canónica (un nombre para la categoría). Esta etiqueta debe ser corta, descriptiva, en mayúsculas y en inglés (ej. CAUSES, AFFECTS, USES_METHOD).
    4.  El resultado final debe ser un único objeto JSON. Las claves del JSON deben ser las etiquetas canónicas que creaste, y el valor para cada clave debe ser una lista de las relaciones originales que pertenecen a ese grupo.

    **Ejemplo de formato de salida:**
    {{
      "CAUSES": ["causes", "induces", "leads to", "resulted in"],
      "USES_METHOD": ["was measured using", "measures", "was conducted on"],
      "IS_ASSOCIATED_WITH": ["is associated with", "related to"]
    }}

    **Lista de relaciones a analizar:**
    ---
    {relations_text}
    ---

    **Resultado en formato JSON:**
    """

    try:
        # Pide al servicio de IA que genere la respuesta en modo JSON si es posible
        response_text = openai_service.generate_message(system_prompt, user_prompt, json_mode=True)
        
        # Extraer el bloque JSON de la respuesta del modelo
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            mapping = json.loads(json_str)
            return mapping
        else:
            logging.error("No se pudo encontrar un objeto JSON en la respuesta del modelo.")
            return {}
    except Exception as e:
        logging.error(f"Error al generar o procesar el mapeo con IA: {e}")
        return {}

def main():
    """Función principal para generar el mapa de relaciones."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Cargar la lista de relaciones del archivo
    try:
        with open(TOP_RELATIONS_FILE, 'r', encoding='utf-8') as f:
            # Leemos las primeras 150 relaciones más comunes para no saturar el prompt
            relations_list = f.readlines()[2:152] # Omitimos las primeras 2 líneas de encabezado
            relations_text = "".join(relations_list)
    except FileNotFoundError:
        logging.error(f"Error: El archivo '{TOP_RELATIONS_FILE}' no existe. Ejecuta '2_build_triplets.py' primero.")
        return
    
    # Inicializar el servicio de IA
    try:
        openai_service = OpenAIMessageService()
    except Exception as e:
        logging.error(f"No se pudo inicializar OpenAIMessageService: {e}")
        return

    # Generar el mapeo con IA
    print("Pidiéndole a la IA que genere el mapa de relaciones... 🤖")
    canonical_map = generate_mapping_with_ai(openai_service, relations_text)

    if canonical_map:
        # Guardar el resultado en el archivo JSON
        with open(OUTPUT_MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(canonical_map, f, indent=2, ensure_ascii=False)
        print(f"¡Éxito! El mapa de relaciones ha sido generado por la IA y guardado en '{OUTPUT_MAPPING_FILE}'.")
        print("\nRecomendación: Abre el archivo para revisarlo y hacer ajustes si es necesario antes de poblar la base de datos.")
    else:
        print("La IA no pudo generar un mapa de relaciones válido. Revisa los logs de error.")

if __name__ == "__main__":
    main()