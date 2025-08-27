#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoint API para el Chatbot ISO 27001/27002
Diseñado para integrarse con el repositorio matriz-legal-ISO27001
"""

import os
import time
import re
from flask import Flask, jsonify, request, g
from groq import Groq
import sys
from pathlib import Path

# Configuración de rutas para Vercel
# Añadir directorios al path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Cargar variables de entorno (si existen)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuración
# Usar una clave de prueba para entorno de desarrollo (límite de uso bajo)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "gsk_zIFx9l0MN2pqNe7BfE2eO1DL8Q0aPaOSYn2QObr9e9MPb8j0")
MODEL = "llama-3.1-8b-instant"  # Modelo rápido con 128K de contexto

# Determinación de ruta de BD_ISO.txt para funcionar tanto en desarrollo como en Vercel
def get_iso_bd_path():
    """Determina la ruta correcta al archivo BD_ISO.txt en diferentes entornos"""
    possible_paths = [
        # Desarrollo local
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "BD_ISO.txt"),
        # Vercel - raíz del proyecto
        os.path.join(os.path.dirname(parent_dir), "BD_ISO.txt"),
        # Alternativa - mismo directorio que el script
        os.path.join(parent_dir, "BD_ISO.txt"),
        # Alternativa - directorio data
        os.path.join(parent_dir, "data", "BD_ISO.txt"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ BD_ISO.txt encontrado en: {path}")
            return path
    
    # Último recurso: crear un archivo de prueba temporal
    if os.getenv('VERCEL_ENV') == 'production':
        temp_path = "/tmp/BD_ISO.txt"
        if not os.path.exists(temp_path):
            with open(temp_path, "w") as f:
                f.write("[5.23] Enmascaramiento de datos\n    Las técnicas de enmascaramiento de datos deberían aplicarse a la información que necesite protección.")
        print(f"⚠️ Usando BD_ISO.txt temporal en: {temp_path}")
        return temp_path
        
    print("❌ No se pudo encontrar BD_ISO.txt")
    return None

# Cargar contexto ISO
ISO_CONTEXTO = ""
iso_bd_path = get_iso_bd_path()
if iso_bd_path:
    try:
        with open(iso_bd_path, "r") as f:
            ISO_CONTEXTO = f.read()
        print(f"✅ Contexto ISO cargado: {len(ISO_CONTEXTO)} caracteres")
    except Exception as e:
        print(f"❌ Error al cargar contexto ISO: {e}")
        ISO_CONTEXTO = "[5.23] Enmascaramiento de datos\n    Las técnicas de enmascaramiento de datos deberían aplicarse a la información que necesite protección."

# System prompt
SYSTEM_PROMPT = """Eres un experto en ISO 27001:2022 (SGSI) e ISO 27002:2022 (93 controles de seguridad).
Tu tarea es responder preguntas sobre estos estándares basándote EXCLUSIVAMENTE en el contexto proporcionado.
Responde de manera precisa, clara y directa, citando siempre el control o sección específica.

IMPORTANTE:
- Si preguntan por un control específico (ej. "5.23"), proporciona todos los detalles disponibles
- Si preguntan por un tema (ej. "cifrado"), identifica todos los controles relevantes
- Usa formato estructurado con títulos, viñetas y citas para mejorar la legibilidad
- Si no tienes la información exacta en el contexto, indícalo claramente
"""

# Detector de patrones para búsqueda directa
def extract_control_code(query):
    """Extrae un código de control de la consulta si existe"""
    control_pattern = r'\b(\d+\.\d+)\b'
    match = re.search(control_pattern, query)
    if match:
        return match.group(1)
    return None

def get_control_context(control_code):
    """Busca un control específico en el contexto ISO"""
    if not control_code:
        return None
    
    # Buscar el control en el texto completo
    control_pattern = r'\[\s*' + re.escape(control_code) + r'\s*\](.*?)(?=\[\s*\d+\.\d+\s*\]|$)'
    match = re.search(control_pattern, ISO_CONTEXTO, re.DOTALL)
    
    if match:
        # Devolver el control con su código
        return f"[{control_code}] {match.group(1).strip()}"
    
    return None

def extract_relevant_context(query, max_size=20000):
    """Extrae contexto relevante para una consulta basada en palabras clave"""
    # Lista de palabras de parada en español
    stop_words = {'a', 'al', 'algo', 'algunas', 'algunos', 'ante', 'antes', 'como', 'con', 'contra', 
                'cual', 'cuando', 'de', 'del', 'desde', 'donde', 'durante', 'e', 'el', 'ella', 
                'ellas', 'ellos', 'en', 'entre', 'era', 'erais', 'eran', 'eras', 'eres', 'es', 
                'esa', 'esas', 'ese', 'eso', 'esos', 'esta', 'estaba', 'estabais', 'estaban', 
                'estabas', 'estad', 'estada', 'estadas', 'estado', 'estados', 'estamos', 'estando', 
                'estar', 'estaremos', 'estará', 'estarán', 'estarás', 'estaré', 'estaréis', 
                'estaría', 'estaríais', 'estaríamos', 'estarían', 'estarías', 'estas', 'este', 
                'estemos', 'esto', 'estos', 'estoy', 'estuve', 'estuviera', 'estuvierais', 
                'estuvieran', 'estuvieras', 'estuvieron', 'estuviese', 'estuvieseis', 'estuviesen', 
                'estuvieses', 'estuvimos', 'estuviste', 'estuvisteis', 'estuviéramos', 'estuviésemos', 
                'estuvo', 'está', 'estábamos', 'estáis', 'están', 'estás', 'esté', 'estéis', 'estén', 
                'estés', 'fue', 'fuera', 'fuerais', 'fueran', 'fueras', 'fueron', 'fuese', 'fueseis', 
                'fuesen', 'fueses', 'fui', 'fuimos', 'fuiste', 'fuisteis', 'fuéramos', 'fuésemos', 
                'ha', 'habida', 'habidas', 'habido', 'habidos', 'habiendo', 'habremos', 'habrá', 
                'habrán', 'habrás', 'habré', 'habréis', 'habría', 'habríais', 'habríamos', 'habrían', 
                'habrías', 'habéis', 'había', 'habíais', 'habíamos', 'habían', 'habías', 'han', 'has', 
                'hasta', 'hay', 'haya', 'hayamos', 'hayan', 'hayas', 'hayáis', 'he', 'hemos', 'hube', 
                'hubiera', 'hubierais', 'hubieran', 'hubieras', 'hubieron', 'hubiese', 'hubieseis', 
                'hubiesen', 'hubieses', 'hubimos', 'hubiste', 'hubisteis', 'hubiéramos', 'hubiésemos', 
                'hubo', 'la', 'las', 'le', 'les', 'lo', 'los', 'me', 'mi', 'mis', 'mucho', 'muchos', 
                'muy', 'más', 'mí', 'mía', 'mías', 'mío', 'míos', 'nada', 'ni', 'no', 'nos', 'nosotras', 
                'nosotros', 'nuestra', 'nuestras', 'nuestro', 'nuestros', 'o', 'os', 'otra', 'otras', 
                'otro', 'otros', 'para', 'pero', 'poco', 'por', 'porque', 'que', 'quien', 'quienes', 
                'qué', 'se', 'sea', 'seamos', 'sean', 'seas', 'seremos', 'será', 'serán', 'serás', 
                'seré', 'seréis', 'sería', 'seríais', 'seríamos', 'serían', 'serías', 'seáis', 'sido', 
                'siendo', 'sin', 'sobre', 'sois', 'somos', 'son', 'soy', 'su', 'sus', 'suya', 'suyas', 
                'suyo', 'suyos', 'sí', 'también', 'tanto', 'te', 'tendremos', 'tendrá', 'tendrán', 
                'tendrás', 'tendré', 'tendréis', 'tendría', 'tendríais', 'tendríamos', 'tendrían', 
                'tendrías', 'tened', 'tenemos', 'tenga', 'tengamos', 'tengan', 'tengas', 'tengo', 
                'tengáis', 'tenida', 'tenidas', 'tenido', 'tenidos', 'teniendo', 'tenéis', 'tenía', 
                'teníais', 'teníamos', 'tenían', 'tenías', 'ti', 'tiene', 'tienen', 'tienes', 'todo', 
                'todos', 'tu', 'tus', 'tuve', 'tuviera', 'tuvierais', 'tuvieran', 'tuvieras', 
                'tuvieron', 'tuviese', 'tuvieseis', 'tuviesen', 'tuvieses', 'tuvimos', 'tuviste', 
                'tuvisteis', 'tuviéramos', 'tuviésemos', 'tuvo', 'tuya', 'tuyas', 'tuyo', 'tuyos', 
                'tú', 'un', 'una', 'uno', 'unos', 'vosotras', 'vosotros', 'vuestra', 'vuestras', 
                'vuestro', 'vuestros', 'y', 'ya', 'yo', 'él', 'éramos'}
    
    # Extraer palabras clave de la consulta
    words = query.lower().split()
    keywords = [word for word in words if word not in stop_words and len(word) > 3]
    
    # Si no hay palabras clave, devolver un extracto del inicio
    if not keywords:
        return ISO_CONTEXTO[:max_size]
    
    # Buscar secciones relevantes que contengan las palabras clave
    control_sections = []
    current_pos = 0
    
    while True:
        # Buscar el siguiente control
        next_control = re.search(r'\[\s*(\d+\.\d+)\s*\]', ISO_CONTEXTO[current_pos:])
        if not next_control:
            break
        
        start_pos = current_pos + next_control.start()
        control_code = next_control.group(1)
        
        # Buscar el siguiente control para determinar el final de la sección actual
        end_search = re.search(r'\[\s*\d+\.\d+\s*\]', ISO_CONTEXTO[start_pos + 10:])
        if end_search:
            end_pos = start_pos + 10 + end_search.start()
        else:
            end_pos = len(ISO_CONTEXTO)
        
        # Extraer la sección del control
        control_section = ISO_CONTEXTO[start_pos:end_pos]
        
        # Verificar si contiene alguna palabra clave
        if any(keyword in control_section.lower() for keyword in keywords):
            control_sections.append(control_section)
        
        # Avanzar a la siguiente posición
        current_pos = start_pos + 10
    
    # Si no encontramos secciones relevantes, devolver un extracto general
    if not control_sections:
        return ISO_CONTEXTO[:max_size]
    
    # Combinar las secciones relevantes
    relevant_context = "\n\n".join(control_sections)
    
    return relevant_context

def handle_iso_chat_request(request_data):
    """Maneja una solicitud de chat ISO y devuelve la respuesta"""
    start_time = time.time()
    
    try:
        # Verificar que hay una consulta
        if not request_data or 'query' not in request_data:
            return {
                "success": False,
                "error": "Query is required"
            }, 400
        
        user_query = request_data['query'].strip()
        
        # Detectar si se pregunta por un control específico
        control_code = extract_control_code(user_query)
        control_context = None
        used_context = None
        
        if control_code:
            control_context = get_control_context(control_code)
            if control_context:
                used_context = control_context
        
        # Si no es un control específico, extraer contexto relevante
        if not used_context:
            used_context = extract_relevant_context(user_query)
        
        # Preparar el prompt
        if control_context:
            # Si encontramos el control específico, enfocamos el contexto
            prompt = f"""CONTEXTO ESPECÍFICO PARA EL CONTROL {control_code}:

{control_context}

---

Pregunta: {user_query}

Responde de manera detallada y estructurada basándote EXCLUSIVAMENTE en el contexto proporcionado sobre el control {control_code}."""
        else:
            # Si no, usamos el contexto más relevante
            prompt = f"""CONTEXTO ISO 27001/27002:

{used_context}

---

Pregunta: {user_query}

Responde de manera precisa y detallada basándote EXCLUSIVAMENTE en el contexto proporcionado.
Si preguntan por un control específico, asegúrate de citar su código y título exactos."""
        
        # Verificar si hay API key de Groq
        if not GROQ_API_KEY:
            # Respuesta de prueba si no hay API key
            return {
                "success": True,
                "response": f"Este es un texto de prueba ya que no hay API key configurada. La consulta fue sobre: {user_query}",
                "elapsed_time": round(time.time() - start_time, 2),
                "tokens": {
                    "input": 0,
                    "output": 0,
                    "total": 0
                },
                "model": "none",
                "direct_match": control_context is not None,
                "control_code": control_code,
                "context": [used_context],
                "sources": [{"code": control_code, "title": "Control ISO 27002", "content_type": "control"}] if control_code else []
            }, 200
        
        # Realizar la consulta a Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Determinista para precisión
            max_completion_tokens=2000
        )
        
        # Extraer la respuesta
        response = completion.choices[0].message.content
        
        # Calcular estadísticas
        elapsed_time = time.time() - start_time
        input_tokens = completion.usage.prompt_tokens
        output_tokens = completion.usage.completion_tokens
        total_tokens = completion.usage.total_tokens
        
        # Construir respuesta
        result = {
            "success": True,
            "response": response,
            "elapsed_time": round(elapsed_time, 2),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens
            },
            "model": MODEL,
            "direct_match": control_context is not None,
            "control_code": control_code,
            "context": [used_context],
            "sources": [{"code": control_code, "title": "Control ISO 27002", "content_type": "control"}] if control_code else []
        }
        
        return result, 200
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "response": "Lo siento, ocurrió un error al procesar tu consulta. Por favor, intenta de nuevo."
        }, 500

# Función para integrarse con el sistema principal
def process_iso_chat_request(request_data):
    """Procesa una solicitud de chat ISO (para integración)"""
    result, status_code = handle_iso_chat_request(request_data)
    return result, status_code

# Punto de entrada para pruebas
if __name__ == "__main__":
    test_query = "¿Qué es el control 5.23 de ISO 27002?"
    result, _ = handle_iso_chat_request({"query": test_query})
    print(f"Query: {test_query}")
    print(f"Response: {result['response']}")