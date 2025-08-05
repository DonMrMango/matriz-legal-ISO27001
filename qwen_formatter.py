#!/usr/bin/env python3
"""
QWEN Legal Text Formatter
Formateo inteligente de textos legales con extracción completa de metadata
Optimizado para documentos normativos colombianos usando Qwen real
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from openai import OpenAI

class QwenLegalFormatter:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        """
        Inicializar el formateador con Qwen real
        """
        # Cargar configuración de Qwen desde .env
        qwen_env_path = "/Users/damo/Desktop/qwen-code-setup/.env"
        if os.path.exists(qwen_env_path):
            with open(qwen_env_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        # Configuración de Qwen
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = base_url or os.getenv('OPENAI_BASE_URL', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')
        self.model = model or os.getenv('OPENAI_MODEL', 'qwen3-coder-plus')
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no encontrada. Configúrala en qwen-code-setup/.env")
        
        # Inicializar cliente OpenAI compatible con Qwen
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Configuración optimizada para análisis legal profundo
        self.temperature = float(os.getenv('QWEN_TEMPERATURE', '0.1'))
        self.max_tokens = int(os.getenv('QWEN_MAX_TOKENS', '30000'))  # Aumentado para documentos largos
        
    def format_and_extract_metadata(self, raw_text: str, document_title: str) -> Dict[str, Any]:
        """
        Formatear texto legal y extraer TODA la metadata usando Qwen
        """
        
        # Prompt especializado para formateo legal colombiano Y extracción de metadata
        system_prompt = """Eres un experto en análisis de documentos legales colombianos. Debes realizar DOS tareas:

## TAREA 1: EXTRACCIÓN DE METADATA COMPLETA

Extrae TODA la información estructurada del documento en formato JSON:

```json
{
  "metadata": {
    "tipo": "ley|decreto|resolucion|circular|conpes",
    "numero": "número del documento",
    "año": "año de expedición",
    "fecha_expedicion": "fecha completa de expedición",
    "fecha_vigencia": "fecha de entrada en vigencia",
    "entidad_expedidora": "entidad que expide",
    "firmantes": ["lista de personas que firman"],
    "titulo_completo": "título completo oficial del documento",
    "objeto": "objeto o propósito principal de la norma",
    "ambito_aplicacion": "ámbito de aplicación",
    "estado": "vigente|derogado|modificado"
  },
  "estructura": {
    "total_articulos": número_total,
    "articulos": [
      {
        "numero": "1",
        "titulo": "título del artículo si tiene",
        "contenido": "contenido completo del artículo",
        "paragrafos": ["lista de parágrafos si tiene"],
        "referencias": {
          "deroga": ["artículos o normas que deroga"],
          "modifica": ["artículos o normas que modifica"],
          "menciona": ["otras normas mencionadas"],
          "es_derogado_por": ["si este artículo está derogado"],
          "es_modificado_por": ["si este artículo está modificado"]
        }
      }
    ],
    "titulos": ["lista de títulos principales"],
    "capitulos": ["lista de capítulos"]
  },
  "referencias_cruzadas": {
    "normas_derogadas": ["lista completa de normas derogadas"],
    "normas_modificadas": ["lista completa de normas modificadas"],
    "normas_mencionadas": ["todas las normas mencionadas"],
    "concordancias": ["concordancias con otras normas"]
  }
}
```

## TAREA 2: FORMATO HTML LIMPIO

Convierte el texto a HTML semántico:

1. LIMPIEZA TOTAL:
   - Eliminar TODA la basura de metadata web
   - Eliminar "Descargar PDF", fechas duplicadas, temas, etc.
   - Mantener SOLO el contenido legal puro

2. ESTRUCTURA HTML:
   - <h1> para el título principal
   - <div class="metadata"> para información de expedición
   - <h2> para títulos y capítulos  
   - <article class="articulo" id="art-X" data-numero="X"> para cada artículo
   - <h3> para el encabezado del artículo
   - <p> para párrafos
   - <div class="paragrafo"> para parágrafos
   - <ul><li> para listas
   - <span class="referencia" data-tipo="deroga|modifica|menciona" data-norma="..."> para referencias

3. FORMATO COHERENTE:
   - Párrafos bien separados
   - Saltos de línea coherentes
   - Estructura navegable
   - Sin cortes abruptos

IMPORTANTE: 
- Procesa TODO el documento sin omitir artículos
- Identifica TODAS las referencias cruzadas
- Mantén la integridad del texto legal
- El JSON debe ser válido y completo

RESPONDE con:
===METADATA===
[JSON completo]
===HTML===
[HTML formateado]
"""

        # Limpiar texto antes de procesar
        clean_text = self._pre_clean_text(raw_text)
        
        user_prompt = f"""
DOCUMENTO: {document_title}

TEXTO COMPLETO A ANALIZAR:
{clean_text}

Realiza el análisis completo: extrae TODA la metadata en JSON y formatea el HTML limpio.
"""

        try:
            # Llamada a Qwen con prompts mejorados
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            response = chat_completion.choices[0].message.content
            
            # Parsear respuesta
            metadata, html = self._parse_qwen_response(response)
            
            # Post-procesamiento
            html = self._post_process_html(html)
            
            # Validar metadata
            metadata = self._validate_metadata(metadata, clean_text)
            
            return {
                'success': True,
                'metadata': metadata,
                'formatted_html': html,
                'word_count': len(raw_text.split()),
                'article_count': len(metadata.get('estructura', {}).get('articulos', []))
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'fallback_html': self._basic_fallback_format(raw_text),
                'metadata': self._extract_basic_metadata(raw_text)
            }
    
    def _parse_qwen_response(self, response: str) -> Tuple[Dict, str]:
        """
        Parsear la respuesta de Qwen para extraer metadata y HTML
        """
        metadata = {}
        html = ""
        
        # Buscar secciones
        if "===METADATA===" in response and "===HTML===" in response:
            parts = response.split("===METADATA===")
            if len(parts) > 1:
                remaining = parts[1].split("===HTML===")
                if len(remaining) >= 2:
                    metadata_str = remaining[0].strip()
                    html = remaining[1].strip()
                    
                    # Parsear JSON
                    try:
                        # Limpiar el JSON de posibles caracteres extra
                        metadata_str = re.sub(r'^```json\s*', '', metadata_str)
                        metadata_str = re.sub(r'\s*```$', '', metadata_str)
                        metadata = json.loads(metadata_str)
                    except:
                        metadata = {}
        
        return metadata, html
    
    def _validate_metadata(self, metadata: Dict, text: str) -> Dict:
        """
        Validar y completar metadata extraída
        """
        if not metadata:
            metadata = {}
        
        # Asegurar estructura básica
        if 'metadata' not in metadata:
            metadata['metadata'] = {}
        if 'estructura' not in metadata:
            metadata['estructura'] = {}
        if 'referencias_cruzadas' not in metadata:
            metadata['referencias_cruzadas'] = {}
        
        # Validar y extraer información faltante
        meta = metadata['metadata']
        
        # Detectar tipo si no está
        if not meta.get('tipo'):
            if re.search(r'\bLEY\b', text, re.IGNORECASE):
                meta['tipo'] = 'ley'
            elif re.search(r'\bDECRETO\b', text, re.IGNORECASE):
                meta['tipo'] = 'decreto'
            elif re.search(r'\bRESOLUCI[OÓ]N\b', text, re.IGNORECASE):
                meta['tipo'] = 'resolucion'
            elif re.search(r'\bCIRCULAR\b', text, re.IGNORECASE):
                meta['tipo'] = 'circular'
            elif re.search(r'\bCONPES\b', text, re.IGNORECASE):
                meta['tipo'] = 'conpes'
        
        # Extraer número si falta
        if not meta.get('numero'):
            num_match = re.search(r'(?:LEY|DECRETO|RESOLUCI[OÓ]N|CIRCULAR|CONPES)\s*(?:N[°º]?\s*)?(\d+)', text, re.IGNORECASE)
            if num_match:
                meta['numero'] = num_match.group(1)
        
        # Extraer año si falta
        if not meta.get('año'):
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
            if year_match:
                meta['año'] = year_match.group(1)
        
        # Contar artículos si falta
        if not metadata['estructura'].get('total_articulos'):
            articulos = re.findall(r'Art[íi]culo\s+\d+', text, re.IGNORECASE)
            metadata['estructura']['total_articulos'] = len(set(articulos))
        
        return metadata
    
    def _post_process_html(self, html: str) -> str:
        """
        Post-procesamiento para mejorar el HTML generado
        """
        # Limpiar HTML mal formado
        html = re.sub(r'\n\s*\n', '\n', html)
        html = re.sub(r'<p>\s*</p>', '', html)
        
        # Asegurar estructura de artículos
        def fix_article_structure(match):
            content = match.group(0)
            # Extraer número del artículo
            num_match = re.search(r'Art[íi]culo\s+(\d+)', content, re.IGNORECASE)
            if num_match:
                num = num_match.group(1)
                if 'id=' not in content:
                    content = re.sub(r'<article([^>]*)>', f'<article\\1 id="art-{num}" data-numero="{num}">', content)
            return content
        
        html = re.sub(r'<article[^>]*>.*?</article>', fix_article_structure, html, flags=re.DOTALL)
        
        return html.strip()
    
    def _extract_basic_metadata(self, text: str) -> Dict:
        """
        Extracción básica de metadata como fallback
        """
        metadata = {
            'metadata': {},
            'estructura': {},
            'referencias_cruzadas': {}
        }
        
        # Tipo de documento
        if re.search(r'\bLEY\b', text[:200], re.IGNORECASE):
            metadata['metadata']['tipo'] = 'ley'
        elif re.search(r'\bDECRETO\b', text[:200], re.IGNORECASE):
            metadata['metadata']['tipo'] = 'decreto'
        elif re.search(r'\bRESOLUCI[OÓ]N\b', text[:200], re.IGNORECASE):
            metadata['metadata']['tipo'] = 'resolucion'
        
        # Número y año
        num_match = re.search(r'(?:LEY|DECRETO|RESOLUCI[OÓ]N)\s*(?:N[°º]?\s*)?(\d+)\s*(?:DE|DEL)?\s*(\d{4})?', text[:500], re.IGNORECASE)
        if num_match:
            metadata['metadata']['numero'] = num_match.group(1)
            if num_match.group(2):
                metadata['metadata']['año'] = num_match.group(2)
        
        # Contar artículos
        articulos = re.findall(r'Art[íi]culo\s+(\d+)', text, re.IGNORECASE)
        metadata['estructura']['total_articulos'] = len(set(articulos))
        
        # Referencias básicas
        derogaciones = re.findall(r'(?:deroga|deróguese|derógase)\s+(?:el\s+)?(?:artículo|decreto|ley)\s+(\d+)', text, re.IGNORECASE)
        if derogaciones:
            metadata['referencias_cruzadas']['normas_derogadas'] = list(set(derogaciones))
        
        return metadata
    
    def _pre_clean_text(self, text: str) -> str:
        """
        Limpiar texto antes de enviar a Qwen
        """
        # Remover metadata web común
        cleanup_patterns = [
            r'Descargar PDF.*?\n',
            r'Fecha[s]?\s*(?:de\s*)?(?:Expedición|Entrada|Vigencia)?:.*?\n',
            r'Medio de Publicación:.*?\n',
            r'Diario Oficial.*?\n',
            r'Temas?\s*\(\d+\).*?\n',
            r'DATOS PERSONALES.*?\n',
            r'- Subtema:.*?\n',
            r'RÉGIMEN ESPECIAL.*?\n',
            r'Superintendencia.*?\n',
            r'Vigencias?\s*\(\d+\).*?\n',
            r'Los datos publicados.*?\n',
            r'Gestor Normativo.*?\n',
            r'Función Pública.*?\n',
            r'Inicio\s+Conc\s+Normas.*?\n',
            r'- Parte \d+.*?\n',
            r'^\s*-\s*$\n'  # Líneas con solo guiones
        ]
        
        for pattern in cleanup_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Limpiar múltiples líneas vacías
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Eliminar espacios al inicio y final
        text = text.strip()
        
        return text
    
    def _basic_fallback_format(self, text: str) -> str:
        """
        Formateo básico de respaldo si Qwen falla
        """
        lines = text.split('\n')
        html_lines = ['<div class="documento-legal">']
        in_article = False
        current_article_num = None
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_article:
                    html_lines.append('</article>')
                    in_article = False
                continue
            
            # Título principal
            if re.match(r'^(?:LEY|DECRETO|RESOLUCI[ÓO]N|CIRCULAR|CONPES).*\d{4}', line, re.IGNORECASE):
                html_lines.append(f'<h1>{line}</h1>')
            
            # Títulos y capítulos
            elif re.match(r'^T[ÍI]TULO\s+[IVXLC]+', line, re.IGNORECASE):
                if in_article:
                    html_lines.append('</article>')
                    in_article = False
                html_lines.append(f'<h2>{line}</h2>')
            
            elif re.match(r'^CAP[ÍI]TULO\s+[IVXLC]+', line, re.IGNORECASE):
                if in_article:
                    html_lines.append('</article>')
                    in_article = False
                html_lines.append(f'<h2>{line}</h2>')
            
            # Artículos
            elif re.match(r'^Art[íi]culo\s+\d+', line, re.IGNORECASE):
                if in_article:
                    html_lines.append('</article>')
                
                article_match = re.search(r'(\d+)', line)
                if article_match:
                    current_article_num = article_match.group(1)
                    html_lines.append(f'<article class="articulo" id="art-{current_article_num}" data-numero="{current_article_num}">')
                    html_lines.append(f'<h3>{line}</h3>')
                    in_article = True
            
            # Parágrafos
            elif re.match(r'^PAR[ÁA]GRAFO', line, re.IGNORECASE):
                html_lines.append(f'<div class="paragrafo"><h4>{line}</h4>')
            
            # Contenido normal
            else:
                html_lines.append(f'<p>{line}</p>')
        
        if in_article:
            html_lines.append('</article>')
        
        html_lines.append('</div>')
        
        return '\n'.join(html_lines)

def process_document_with_qwen(file_path: str, output_dir: str = None) -> Dict[str, Any]:
    """
    Procesar un documento completo con Qwen
    """
    formatter = QwenLegalFormatter()
    
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Obtener título del archivo
    filename = os.path.basename(file_path)
    document_title = filename.replace('.txt', '').replace('_', ' ').title()
    
    # Procesar con Qwen
    result = formatter.format_and_extract_metadata(text, document_title)
    
    if result['success'] and output_dir:
        # Guardar metadata
        metadata_file = os.path.join(output_dir, f"{filename}_metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(result['metadata'], f, ensure_ascii=False, indent=2)
        
        # Guardar HTML formateado
        html_file = os.path.join(output_dir, f"{filename}_formatted.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(result['formatted_html'])
        
        result['metadata_file'] = metadata_file
        result['html_file'] = html_file
    
    return result

if __name__ == "__main__":
    # Test con un archivo
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        
        print(f"Procesando {file_path} con Qwen...")
        result = process_document_with_qwen(file_path, output_dir)
        
        if result['success']:
            print(f"✅ Procesamiento exitoso")
            print(f"   - Artículos encontrados: {result['article_count']}")
            print(f"   - Metadata: {result.get('metadata_file', 'en memoria')}")
            print(f"   - HTML: {result.get('html_file', 'en memoria')}")
        else:
            print(f"❌ Error: {result['error']}")