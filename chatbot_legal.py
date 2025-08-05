#!/usr/bin/env python3
"""
CHATBOT LEGAL - Asistente especializado en normativa colombiana
Usa Groq para consultas inteligentes con contexto restrictivo
"""

import os
import re
import sqlite3
from typing import Dict, Any, List, Optional
from groq import Groq
from openai import OpenAI


class ChatbotLegal:
    def __init__(self, api_key: str = None, db_path: str = None, texts_path: str = None):
        """
        Inicializar chatbot legal con Groq
        """
        # Configurar Groq (para análisis y extracción)
        # Cargar .env del proyecto primero
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#') and '=' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        self.groq_api_key = api_key or os.getenv('GROQ_API_KEY')
        self.groq_available = bool(self.groq_api_key)
        
        if self.groq_available:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
                self.groq_model = "llama3-8b-8192"  # Rápido para análisis
                print("✅ Groq configurado para análisis y extracción")
            except Exception as e:
                print(f"⚠️ Error configurando Groq: {e}")
                self.groq_available = False
        else:
            self.groq_client = None
            print("⚠️ GROQ_API_KEY no encontrada")
        
        # Configurar Qwen (para generación de respuestas)
        self._setup_qwen()
        
        # Prioridad: Qwen > Groq > Modo básico
        self.ai_available = self.qwen_available or self.groq_available
        
        # Rutas de datos
        self.db_path = db_path or os.path.join(
            os.path.dirname(__file__), '..', 'data_repository', 'repositorio.db'
        )
        self.texts_path = texts_path or os.path.join(
            os.path.dirname(__file__), '..', 'data_repository', 'textos_limpios_seguro'
        )
        
        # Sistema de prompts avanzados con ejemplos y validación estricta
        self.system_context = """Eres un asistente legal especializado EXCLUSIVAMENTE en normativa colombiana. Tu función es ser PRECISO, FACTUAL y RESTRICTIVO.

=== REGLAS ESTRICTAS ===

1. SOLO INFORMACIÓN DOCUMENTAL:
   ✅ CORRECTO: "El artículo 15 de la Ley 1581 establece textualmente: '[cita exacta]'"
   ❌ INCORRECTO: "El decreto puede tener implicaciones en..." (especulación)

2. RELEVANCIA DIRECTA:
   ✅ CORRECTO: Usuario pregunta por "Ley 1581" → respondes con Ley 1581
   ❌ INCORRECTO: Usuario pregunta por "protección datos" → mencionas Decreto 1074 de comercio exterior

3. LIMITACIÓN DE CONOCIMIENTO:
   ✅ CORRECTO: "No encontré información sobre [tema] en la normativa disponible"
   ❌ INCORRECTO: Inventar conexiones o interpretaciones no explícitas

=== EJEMPLOS DE RESPUESTAS CORRECTAS ===

Pregunta: "¿Qué dice el artículo 15 de la Ley 1581?"
Respuesta correcta: "Artículo 15 de la Ley 1581 de 2012: 'El Responsable del Tratamiento debe...' [cita textual completa]"

Pregunta: "¿Cómo implementar ISO 27001 en Colombia?"
Respuesta correcta: "Basándome en el CONPES 3995 de 2020, se establecen las siguientes medidas para seguridad digital: [citas específicas]. Para implementación específica de ISO 27001, no tengo información detallada en la normativa disponible."

=== EJEMPLOS DE RESPUESTAS INCORRECTAS ===

❌ "El Decreto 1074 de comercio exterior puede tener implicaciones en datos personales"
✅ Corrección: Solo mencionar si el documento habla EXPLÍCITAMENTE de datos personales

❌ "Te recomiendo considerar estos aspectos..." + especulaciones
✅ Corrección: "La normativa establece específicamente que..." + cita textual

=== VALIDACIÓN ANTES DE RESPONDER ===
Antes de cada respuesta, pregúntate:
1. ¿Está esta información TEXTUALMENTE en los documentos?
2. ¿Es DIRECTAMENTE relevante a la pregunta?
3. ¿Estoy citando fuentes ESPECÍFICAS?
4. ¿Estoy especulando o interpretando más allá del texto?

Si alguna respuesta es NO, reformula o indica que no tienes la información.

ESPECIALIZACIÓN TÉCNICA:
- Ley 1581/2012: Protección de datos personales
- Decreto 1377/2013: Reglamentación datos personales  
- CONPES 3995/2020: Seguridad digital
- Resoluciones SIC sobre protección de datos
- Circulares MinTIC sobre ciberseguridad

FORMATO OBLIGATORIO:
- Cita textual entre comillas
- Fuente específica (Artículo X, Ley Y de Z)
- Si no hay información: "No encontré información específica sobre [tema] en la normativa disponible"
- Prohibido usar: "puede", "podría", "implica", "sugiere" sin base textual"""

    def _setup_qwen(self):
        """Configurar Qwen para generación de respuestas avanzadas"""
        try:
            # Cargar configuración de Qwen desde .env
            qwen_env_path = "/Users/damo/Desktop/qwen-code-setup/.env"
            if os.path.exists(qwen_env_path):
                with open(qwen_env_path, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            os.environ[key] = value
            
            # Configuración de Qwen
            qwen_api_key = os.getenv('OPENAI_API_KEY')
            qwen_base_url = os.getenv('OPENAI_BASE_URL', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')
            qwen_model = os.getenv('OPENAI_MODEL', 'qwen-max')
            
            if qwen_api_key:
                self.qwen_client = OpenAI(
                    api_key=qwen_api_key,
                    base_url=qwen_base_url
                )
                self.qwen_model = qwen_model
                self.qwen_available = True
                print(f"✅ Qwen {qwen_model} configurado para generación de respuestas")
            else:
                self.qwen_available = False
                print("⚠️ Qwen API key no encontrada")
                
        except Exception as e:
            self.qwen_available = False
            print(f"⚠️ Error configurando Qwen: {e}")

    def search_relevant_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Buscar documentos relevantes en la base de datos
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            query_lower = query.lower()
            
            # Búsqueda inteligente por tipo de documento
            if 'conpes' in query_lower:
                cursor = conn.execute("""
                    SELECT * FROM textos_repositorio 
                    WHERE UPPER(tipo_norma) LIKE '%CONPES%' OR UPPER(titulo) LIKE '%CONPES%'
                    ORDER BY año DESC
                """)
                results = [dict(row) for row in cursor.fetchall()]
                if results:
                    conn.close()
                    return results
            
            if 'circular' in query_lower:
                cursor = conn.execute("""
                    SELECT * FROM textos_repositorio 
                    WHERE UPPER(tipo_norma) LIKE '%CIRCULAR%' OR UPPER(titulo) LIKE '%CIRCULAR%'
                    ORDER BY año DESC
                """)
                results = [dict(row) for row in cursor.fetchall()]
                if results:
                    conn.close()
                    return results
            
            if 'resolución' in query_lower or 'resolucion' in query_lower:
                cursor = conn.execute("""
                    SELECT * FROM textos_repositorio 
                    WHERE UPPER(tipo_norma) LIKE '%RESOLUCIÓN%' OR UPPER(tipo_norma) LIKE '%RESOLUCION%'
                    ORDER BY año DESC
                """)
                results = [dict(row) for row in cursor.fetchall()]
                if results:
                    conn.close()
                    return results
            
            # Si contiene palabras clave de protección de datos, incluir documentos relevantes
            if any(term in query_lower for term in ['responsable', 'tratamiento', 'datos', 'obligaciones', 'protección', 'derechos', 'titular', 'encargado', 'aviso', 'privacidad', 'autorización', 'conservar', 'tiempo', 'supresión', 'habeas data', 'principios', 'videovigilancia', 'iso', '27001', 'seguridad']):
                # Para consultas fundamentales, priorizar la Ley sobre el Decreto
                if any(fundamental in query_lower for fundamental in ['obligaciones', 'derechos', 'qué es', 'definición', 'tratamiento', 'titular', 'responsable', 'encargado', 'aviso', 'privacidad', 'autorización', 'conservar', 'cuánto tiempo', 'cómo', 'debo', 'principios', 'implementar', 'iso', '27001']):
                    cursor = conn.execute("""
                        SELECT * FROM textos_repositorio 
                        WHERE numero IN ('1581', '1377')
                        ORDER BY 
                            CASE 
                                WHEN numero = '1581' THEN 1  -- Ley 1581 SIEMPRE primero para definiciones
                                WHEN numero = '1377' THEN 2  -- Decreto 1377 segundo
                                ELSE 3
                            END
                    """)
                else:
                    cursor = conn.execute("""
                        SELECT * FROM textos_repositorio 
                        WHERE titulo LIKE '%protección%' OR titulo LIKE '%datos%' OR numero IN ('1581', '1377')
                        ORDER BY año DESC
                    """)
                results = [dict(row) for row in cursor.fetchall()]
                
                if results:
                    conn.close()
                    return results[:3]
            
            # Búsqueda normal por términos específicos
            cursor = conn.execute("""
                SELECT * FROM textos_repositorio 
                WHERE titulo LIKE ? OR numero LIKE ? OR tipo_norma LIKE ?
                ORDER BY año DESC
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
            
            results = [dict(row) for row in cursor.fetchall()]
            
            # Si no hay resultados específicos, buscar solo en documentos REALMENTE relevantes
            if not results:
                # Para consultas técnicas como ISO, solo buscar en documentos de seguridad
                if any(tech_term in query_lower for tech_term in ['iso', '27001', 'seguridad información', 'ciberseguridad']):
                    cursor = conn.execute("""
                        SELECT * FROM textos_repositorio 
                        WHERE (UPPER(titulo) LIKE '%SEGURIDAD%' OR UPPER(titulo) LIKE '%CONPES%' OR numero = '1581')
                        ORDER BY año DESC
                    """)
                else:
                    # Para otras consultas, usar documentos principales de protección de datos
                    cursor = conn.execute("""
                        SELECT * FROM textos_repositorio 
                        WHERE numero IN ('1581', '1377')
                        ORDER BY año DESC
                    """)
                results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results[:5]  # Limitar a 5 documentos más relevantes
            
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def get_document_content(self, document_id: str) -> Optional[str]:
        """
        Obtener contenido completo de un documento
        """
        # Buscar en todas las carpetas
        folders = ['leyes', 'decretos', 'resoluciones', 'circulares', 'conpes', 'otros']
        
        for folder in folders:
            file_path = os.path.join(self.texts_path, folder, f"{document_id}.txt")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
        
        return None
    
    def extract_specific_article(self, content: str, article_number: str) -> Optional[str]:
        """
        Extraer un artículo específico del contenido
        """
        lines = content.split('\n')
        article_lines = []
        in_article = False
        article_started = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Buscar el artículo específico
            if re.match(rf'Artículo\s+{article_number}[°º]?\.?\s*', line, re.IGNORECASE):
                in_article = True
                article_started = True
                article_lines.append(line)
                continue
            
            # Si encontramos otro artículo, terminar
            if article_started and re.match(r'Artículo\s+\d+[°º]?\.?\s*', line, re.IGNORECASE):
                break
            
            # Si estamos en el artículo, agregar las líneas
            if in_article:
                if line:  # Solo líneas no vacías
                    article_lines.append(line)
                # Detener si encontramos una sección nueva o parágrafo
                if re.match(r'(CAPÍTULO|TÍTULO|Parágrafo)', line, re.IGNORECASE):
                    break
                # Limitar a 50 líneas por artículo (artículos muy largos)
                if len(article_lines) > 50:
                    break
        
        if article_lines:
            full_text = ' '.join(article_lines)
            # Limpiar texto excesivo
            full_text = re.sub(r'\s+', ' ', full_text)
            return full_text  # Sin límite - mostrar artículo completo
        
        return None
    
    def identify_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Identificar la intención de la consulta con mayor precisión
        """
        query_lower = query.lower()
        
        # Buscar referencias específicas a artículos - MEJORADO
        article_patterns = [
            r'artículo\s+(\d+)\s+de\s+la\s+ley\s+(\d+)',  # artículo X de la ley Y
            r'artículo\s+(\d+)\s+ley\s+(\d+)',            # artículo X ley Y
            r'art[íi]culo\s+(\d+).*ley\s+(\d+)',          # artículo X ... ley Y
            r'artículo\s+(\d+)\s+del?\s+decreto\s+(\d+)',  # artículo X del decreto Y
            r'artículo\s+(\d+).*decreto\s+(\d+)'           # artículo X ... decreto Y
        ]
        
        for pattern in article_patterns:
            match = re.search(pattern, query_lower)
            if match:
                article_num = match.group(1)
                doc_num = match.group(2)
                
                # Determinar tipo de documento y año si es posible
                if 'ley' in query_lower:
                    # Buscar año si existe
                    year_match = re.search(rf'ley\s+{doc_num}\s+de\s+(\d{{4}})', query_lower)
                    return {
                        'type': 'specific_article',
                        'article': article_num,
                        'document_type': 'ley',
                        'number': doc_num,
                        'year': year_match.group(1) if year_match else '2012' if doc_num == '1581' else None
                    }
                elif 'decreto' in query_lower:
                    year_match = re.search(rf'decreto\s+{doc_num}\s+de\s+(\d{{4}})', query_lower)
                    return {
                        'type': 'specific_article',
                        'article': article_num,
                        'document_type': 'decreto',
                        'number': doc_num,
                        'year': year_match.group(1) if year_match else '2013' if doc_num == '1377' else None
                    }
        
        # Si solo menciona un artículo sin especificar documento
        simple_article_match = re.search(r'artículo\s+(\d+)', query_lower)
        if simple_article_match:
            # Intentar inferir el documento del contexto
            if '1581' in query_lower:
                return {
                    'type': 'specific_article',
                    'article': simple_article_match.group(1),
                    'document_type': 'ley',
                    'number': '1581',
                    'year': '2012'
                }
            elif '1377' in query_lower:
                return {
                    'type': 'specific_article',
                    'article': simple_article_match.group(1),
                    'document_type': 'decreto',
                    'number': '1377',
                    'year': '2013'
                }
        
        # Buscar circular específica
        circular_match = re.search(r'circular\s+(?:externa\s+)?(?:no\.?\s*)?(\d+)\s+de\s+(\d{4})', query_lower)
        if circular_match:
            return {
                'type': 'specific_document',
                'document_type': 'circular',
                'number': circular_match.group(1),
                'year': circular_match.group(2)
            }
        
        return {'type': 'general_query'}
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Procesar consulta del usuario
        """
        try:
            # Detectar saludos simples
            query_lower = user_query.lower().strip()
            simple_greetings = ['hola', 'hello', 'hi', 'buenos días', 'buenas tardes', 'buenas noches', 
                              'buen día', 'saludos', 'hey', 'qué tal']
            
            if query_lower in simple_greetings or len(query_lower.split()) <= 2 and any(greeting in query_lower for greeting in simple_greetings):
                return {
                    'success': True,
                    'response': '¡Hola! Soy tu asistente legal especializado en normativa colombiana. Puedo ayudarte con:\n\n• Consultas sobre artículos específicos de leyes y decretos\n• Información sobre protección de datos personales (Ley 1581/2012)\n• Obligaciones del responsable del tratamiento\n• Políticas de seguridad de la información\n• Cumplimiento normativo ISO 27001\n\n¿En qué puedo ayudarte hoy?',
                    'sources': []
                }
            
            # Detectar consultas muy cortas o vagas (excepto términos específicos de documentos)
            if len(query_lower.split()) <= 2 and not any(term in query_lower for term in ['artículo', 'ley', 'decreto', 'datos', 'responsable', 'conpes', 'resolución', 'circular']):
                return {
                    'success': False,
                    'response': 'Tu consulta es muy breve. Para ayudarte mejor, puedes preguntar por:\n\n• Un artículo específico: "¿Qué dice el artículo 15 de la ley 1581?"\n• Temas generales: "¿Cuáles son las obligaciones del responsable?"\n• Normativa específica: "¿Qué establece el decreto 1377?"',
                    'sources': []
                }
            
            # Identificar intención
            intent = self.identify_query_intent(user_query)
            
            if intent['type'] == 'specific_article':
                return self._handle_specific_article(intent, user_query)
            elif intent['type'] == 'specific_document':
                return self._handle_specific_document(intent, user_query)
            else:
                return self._handle_general_query(user_query)
                
        except Exception as e:
            return {
                'success': False,
                'response': 'Ha ocurrido un error procesando tu consulta. Por favor, intenta nuevamente.',
                'error': str(e)
            }
    
    def process_query_with_context(self, user_query: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Procesar consulta del usuario con contexto de conversación previa
        """
        try:
            # Si no hay historial, usar método estándar
            if not chat_history or len(chat_history) == 0:
                return self.process_query(user_query)
            
            # Analizar contexto de conversación
            context_info = self._analyze_chat_context(chat_history)
            
            # Modificar la consulta actual basándose en el contexto
            enhanced_query = self._enhance_query_with_context(user_query, context_info)
            
            # Procesar la consulta mejorada
            result = self.process_query(enhanced_query)
            
            # Si la respuesta es relevante al contexto, mejorarla
            if context_info and result.get('success'):
                result['response'] = self._enhance_response_with_context(
                    result['response'], context_info, user_query
                )
            
            return result
            
        except Exception as e:
            # Fallback al método estándar
            return self.process_query(user_query)
    
    def _analyze_chat_context(self, chat_history: List[Dict]) -> Dict[str, Any]:
        """
        Analizar el contexto de la conversación previa
        """
        context = {
            'previous_topic': None,
            'previous_articles': [],
            'previous_concepts': [],
            'previous_documents': []
        }
        
        # Analizar los últimos 3 mensajes para contexto relevante
        recent_messages = chat_history[-6:] if len(chat_history) > 6 else chat_history
        
        for msg in recent_messages:
            if msg.get('role') == 'user':
                query = msg.get('content', '').lower()
                
                # Detectar artículos mencionados
                import re
                articles = re.findall(r'artículo\s+(\d+)', query)
                context['previous_articles'].extend(articles)
                
                # Detectar conceptos clave
                concepts = ['responsable', 'titular', 'encargado', 'tratamiento', 'datos sensibles', 
                           'autorización', 'habeas data', 'obligaciones', 'derechos']
                for concept in concepts:
                    if concept in query:
                        context['previous_concepts'].append(concept)
                
                # Detectar documentos
                if 'ley 1581' in query or 'ley de datos' in query:
                    context['previous_documents'].append('ley_1581_2012')
                if 'decreto 1377' in query:
                    context['previous_documents'].append('decreto_1377_2013')
            
            elif msg.get('role') == 'assistant':
                response = msg.get('content', '').lower()
                
                # Detectar temas tratados en respuestas previas
                if 'obligaciones del responsable' in response or 'deberes del responsable' in response:
                    context['previous_topic'] = 'responsable_obligations'
                elif 'derechos del titular' in response:
                    context['previous_topic'] = 'titular_rights'
                elif 'datos sensibles' in response:
                    context['previous_topic'] = 'sensitive_data'
                elif 'iso 27001' in response or 'seguridad de la información' in response:
                    context['previous_topic'] = 'information_security'
        
        return context
    
    def _enhance_query_with_context(self, user_query: str, context_info: Dict) -> str:
        """
        Mejorar la consulta actual con información del contexto
        """
        query_lower = user_query.lower()
        
        # Si la consulta actual es muy general y se refiere al contexto previo
        contextual_references = ['esos deberes', 'esas obligaciones', 'eso', 'esto', 'ellos', 'ellas',
                               'cómo se relaciona', 'qué relación', 'cómo conecta', 'cómo aplica']
        
        has_contextual_ref = any(ref in query_lower for ref in contextual_references)
        
        if has_contextual_ref and context_info.get('previous_topic'):
            if context_info['previous_topic'] == 'responsable_obligations':
                if 'seguridad' in query_lower or 'información' in query_lower:
                    return f"{user_query} - específicamente en relación con las obligaciones del responsable del tratamiento mencionadas anteriormente"
            
            elif context_info['previous_topic'] == 'titular_rights':
                return f"{user_query} - en relación con los derechos del titular de datos"
                
            elif context_info['previous_topic'] == 'sensitive_data':
                return f"{user_query} - referente al manejo de datos sensibles"
        
        return user_query
    
    def _enhance_response_with_context(self, response: str, context_info: Dict, original_query: str) -> str:
        """
        Mejorar la respuesta con información contextual relevante
        """
        query_lower = original_query.lower()
        
        # Si la consulta se refiere a relación con seguridad y el contexto previo era sobre obligaciones
        if (('seguridad' in query_lower or 'información' in query_lower) and 
            context_info.get('previous_topic') == 'responsable_obligations'):
            
            # Agregar conexión explícita con las obligaciones mencionadas anteriormente
            security_connection = "\n\n**🔗 Conexión con las obligaciones del responsable mencionadas anteriormente:**\n\n"
            
            if 'iso 27001' in response.lower():
                security_connection += "Los deberes del responsable del tratamiento (Art. 17 Ley 1581) se **mapean directamente** con controles ISO 27001:\n\n"
                security_connection += "• **Deber d)** 'Condiciones de seguridad necesarias' → **A.13.1** Controles de red\n"
                security_connection += "• **Deber k)** 'Manual de políticas y procedimientos' → **A.18.1** Documentación de seguridad\n"
                security_connection += "• **Deber n)** 'Informar violaciones de seguridad' → **A.16.1** Gestión de incidentes\n"
                security_connection += "• **Deber i)** 'Exigir respeto a condiciones de seguridad' → **A.15.1** Seguridad con proveedores\n\n"
                security_connection += "**→ Implementación práctica:** Cada deber legal requiere controles técnicos específicos de seguridad."
            
            else:
                security_connection += "Las **15 obligaciones del responsable** que vimos anteriormente incluyen **múltiples aspectos de seguridad**:\n\n"
                security_connection += "• **Deber d)**: 'Condiciones de seguridad para impedir adulteración, pérdida, acceso no autorizado'\n"
                security_connection += "• **Deber i)**: 'Exigir al encargado respeto a condiciones de seguridad y privacidad'\n" 
                security_connection += "• **Deber n)**: 'Informar violaciones a códigos de seguridad y riesgos'\n\n"
                security_connection += "**→ Estas obligaciones LEGALES requieren implementar CONTROLES TÉCNICOS de seguridad de la información.**"
            
            response = response + security_connection
        
        return response
    
    def _handle_specific_article(self, intent: Dict, user_query: str) -> Dict[str, Any]:
        """
        Manejar consulta de artículo específico
        """
        # Buscar documento específico
        document_id = f"{intent['document_type']}_{intent['number']}_{intent['year']}"
        content = self.get_document_content(document_id)
        
        if not content:
            return {
                'success': False,
                'response': f"No encontré el {intent['document_type']} {intent['number']} de {intent['year']} en la base de datos.",
                'sources': []
            }
        
        # Extraer artículo específico
        article_text = self.extract_specific_article(content, intent['article'])
        
        if not article_text:
            return {
                'success': False,
                'response': f"No encontré el artículo {intent['article']} en el {intent['document_type']} {intent['number']} de {intent['year']}.",
                'sources': [document_id]
            }
        
        # Respuesta directa con cita textual
        response = f"**Artículo {intent['article']} del {intent['document_type'].title()} {intent['number']} de {intent['year']}:**\n\n{article_text}"
        
        return {
            'success': True,
            'response': response,
            'sources': [document_id],
            'article_found': True
        }
    
    def _handle_specific_document(self, intent: Dict, user_query: str) -> Dict[str, Any]:
        """
        Manejar consulta de documento específico
        """
        # Buscar documentos relacionados
        relevant_docs = self.search_relevant_documents(f"{intent['document_type']} {intent['number']} {intent['year']}")
        
        if not relevant_docs:
            return {
                'success': False,
                'response': f"No tengo información sobre la {intent['document_type']} {intent['number']} de {intent['year']} en mi base de datos.",
                'sources': []
            }
        
        # Obtener contenido del primer documento relevante
        doc = relevant_docs[0]
        content = self.get_document_content(doc['nombre_archivo'])
        
        if not content:
            return {
                'success': False,
                'response': f"Encontré referencias a la {intent['document_type']}, pero no puedo acceder al contenido completo.",
                'sources': [doc['nombre_archivo']]
            }
        
        # Usar Groq para responder con contexto del documento
        return self._query_with_groq(user_query, content, [doc])
    
    def _handle_general_query(self, user_query: str) -> Dict[str, Any]:
        """
        Manejar consulta general con priorización mejorada
        """
        # Buscar documentos relevantes
        relevant_docs = self.search_relevant_documents(user_query)
        
        if not relevant_docs:
            return {
                'success': False,
                'response': "No encontré información relevante en la normativa disponible para tu consulta.",
                'sources': []
            }
        
        # Priorizar documentos que coincidan exactamente con el tipo buscado
        query_lower = user_query.lower()
        prioritized_docs = []
        
        # Si busca CONPES específicamente, priorizar CONPES
        if 'conpes' in query_lower:
            conpes_docs = [doc for doc in relevant_docs if 'conpes' in doc.get('tipo_norma', '').lower()]
            other_docs = [doc for doc in relevant_docs if 'conpes' not in doc.get('tipo_norma', '').lower()]
            prioritized_docs = conpes_docs + other_docs
        
        # Si busca circulares específicamente, priorizar circulares
        elif 'circular' in query_lower:
            circular_docs = [doc for doc in relevant_docs if 'circular' in doc.get('tipo_norma', '').lower()]
            other_docs = [doc for doc in relevant_docs if 'circular' not in doc.get('tipo_norma', '').lower()]
            prioritized_docs = circular_docs + other_docs
        
        # Si busca resoluciones específicamente, priorizar resoluciones
        elif 'resolución' in query_lower or 'resolucion' in query_lower:
            resolucion_docs = [doc for doc in relevant_docs if 'resolución' in doc.get('tipo_norma', '').lower() or 'resolucion' in doc.get('tipo_norma', '').lower()]
            other_docs = [doc for doc in relevant_docs if not ('resolución' in doc.get('tipo_norma', '').lower() or 'resolucion' in doc.get('tipo_norma', '').lower())]
            prioritized_docs = resolucion_docs + other_docs
        
        else:
            prioritized_docs = relevant_docs
        
        # Obtener contenido de documentos relevantes (priorizar los primeros)
        context_content = ""
        sources = []
        
        for doc in prioritized_docs[:3]:  # Máximo 3 documentos
            content = self.get_document_content(doc['nombre_archivo'])
            if content:
                # Para consultas que requieren información específica, usar el documento completo
                query_lower = user_query.lower()
                needs_full_document = (
                    # Definiciones básicas
                    (any(term in query_lower for term in ['tratamiento', 'responsable', 'titular', 'encargado']) and 
                     any(word in query_lower for word in ['qué es', 'definición', 'define'])) or
                    # Obligaciones y derechos
                    ('obligaciones' in query_lower and 'responsable' in query_lower) or
                    ('derechos' in query_lower and ('titular' in query_lower or 'persona' in query_lower)) or
                    # Consultas específicas sobre conceptos importantes
                    ('aviso' in query_lower and 'privacidad' in query_lower) or
                    any(phrase in query_lower for phrase in ['conservar datos', 'tiempo', 'cuánto tiempo']) or
                    any(phrase in query_lower for phrase in ['manejar datos sensibles', 'tratar datos sensibles']) or
                    # Consultas de seguridad e implementación
                    ('principios' in query_lower) or
                    ('iso' in query_lower and '27001' in query_lower) or
                    ('videovigilancia' in query_lower) or
                    ('autorización' in query_lower and 'obtener' in query_lower)
                )
                
                if needs_full_document:
                    # Usar documento completo para extracciones precisas
                    context_content += f"\n\n--- {doc['tipo_norma']} {doc['numero']} de {doc['año']} ---\n{content}"
                elif 'conpes' in doc.get('tipo_norma', '').lower():
                    context_content += f"\n\n--- {doc['tipo_norma']} {doc['numero']} de {doc['año']} ---\n{content[:8000]}"
                else:
                    context_content += f"\n\n--- {doc['tipo_norma']} {doc['numero']} de {doc['año']} ---\n{content[:5000]}"
                sources.append(doc['nombre_archivo'])
        
        if not context_content:
            return {
                'success': False,
                'response': "Encontré documentos relevantes pero no puedo acceder a su contenido.",
                'sources': []
            }
        
        return self._query_with_groq(user_query, context_content, prioritized_docs)
    
    def _query_with_groq(self, user_query: str, context: str, sources: List[Dict]) -> Dict[str, Any]:
        """
        ARQUITECTURA HÍBRIDA: Groq extrae → Qwen genera respuesta
        """
        # Si ninguna IA disponible, usar modo básico
        if not self.ai_available:
            return self._basic_search_response(user_query, context, sources)
        
        # 🔄 FASE 1: Groq analiza y extrae información clave
        extracted_info = self._extract_with_groq(user_query, context, sources)
        
        # 🤖 FASE 2: Qwen genera respuesta inteligente
        if self.qwen_available:
            return self._generate_with_qwen(user_query, extracted_info, sources)
        else:
            # Fallback a respuesta estructurada con Groq
            return self._generate_with_groq(user_query, extracted_info, sources)
    
    def _extract_with_groq(self, user_query: str, context: str, sources: List[Dict]) -> Dict[str, Any]:
        """
        FASE 1: Groq extrae información clave del contexto
        """
        if not self.groq_available:
            return {
                'relevant_content': context[:5000],  # Truncar si no hay Groq
                'key_concepts': [],
                'articles': [],
                'legal_basis': []
            }
        
        try:
            extraction_prompt = f"""TAREA: Extraer información clave del contexto legal para la consulta del usuario.

CONTEXTO NORMATIVO:
{context}

CONSULTA: {user_query}

EXTRAE Y ESTRUCTURA:
1. CONTENIDO_RELEVANTE: Las secciones más relevantes del contexto (máximo 3000 caracteres)
2. CONCEPTOS_CLAVE: Lista de conceptos legales importantes mencionados
3. ARTICULOS: Lista de artículos específicos citados con su contenido
4. BASE_LEGAL: Fundamentos normativos aplicables

Responde en formato JSON estructurado."""

            completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Eres un extractor de información legal. Responde solo con JSON estructurado."},
                    {"role": "user", "content": extraction_prompt}
                ],
                model=self.groq_model,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Intentar parsear JSON, con fallback robusto
            try:
                import json
                response_text = completion.choices[0].message.content.strip()
                # Buscar JSON en la respuesta
                if '{' in response_text and '}' in response_text:
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    json_text = response_text[start:end]
                    extracted = json.loads(json_text)
                else:
                    raise ValueError("No JSON found")
            except Exception as e:
                print(f"Error parsing Groq JSON: {e}")
                # Fallback: extraer información directamente del contexto
                extracted = {
                    'relevant_content': context[:4000],  # Más contenido
                    'key_concepts': self._extract_key_concepts_fallback(context),
                    'articles': self._extract_articles_fallback(context),
                    'legal_basis': [f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" for doc in sources]
                }
            
            return extracted
            
        except Exception as e:
            print(f"Error en extracción Groq: {e}")
            return {
                'relevant_content': context[:3000],
                'key_concepts': [],
                'articles': [],
                'legal_basis': [f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" for doc in sources]
            }
    
    def _generate_with_qwen(self, user_query: str, extracted_info: Dict, sources: List[Dict]) -> Dict[str, Any]:
        """
        FASE 2: Qwen genera respuesta inteligente y completa
        """
        try:
            # Construir prompt avanzado para Qwen
            qwen_prompt = f"""Eres un asistente legal especializado en normativa colombiana. Tu tarea es generar una respuesta PRECISA, COMPLETA y BIEN ESTRUCTURADA.

CONSULTA DEL USUARIO:
{user_query}

INFORMACIÓN EXTRAÍDA:
- Contenido relevante: {extracted_info.get('relevant_content', extracted_info.get('CONTENIDO_RELEVANTE', ''))}
- Conceptos clave: {extracted_info.get('key_concepts', extracted_info.get('CONCEPTOS_CLAVE', []))}
- Artículos citados: {extracted_info.get('articles', extracted_info.get('ARTICULOS', []))}
- Base legal: {extracted_info.get('legal_basis', extracted_info.get('BASE_LEGAL', []))}

DEBUG INFO - Extracted keys: {list(extracted_info.keys())}

INSTRUCCIONES ESTRICTAS:
1. Responde ÚNICAMENTE basándote en la información proporcionada
2. NO inventes información que no esté en los documentos
3. NO menciones ISO 27001 u otros estándares a menos que estén explícitamente en el contenido
4. Usa formato markdown con secciones claras
5. Incluye citas textuales entre comillas cuando sea relevante
6. Si no hay información suficiente, indícalo claramente
7. Máximo 4000 caracteres

GENERA una respuesta completa y profesional."""

            completion = self.qwen_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Eres un asistente legal especializado EXCLUSIVAMENTE en normativa colombiana. PROHIBIDO inventar información no contenida en los documentos proporcionados. Si no tienes la información específica, indícalo claramente."},
                    {"role": "user", "content": qwen_prompt}
                ],
                model=self.qwen_model,
                max_tokens=4000,
                temperature=0.1  # Muy conservador, igual que Groq
            )
            
            response = completion.choices[0].message.content.strip()
            
            # Agregar fuentes
            source_list = [f"{doc['tipo_norma']}_{doc['numero']}_{doc['año']}" for doc in sources]
            if source_list:
                response += f"\n\n**Fuentes:** {', '.join(source_list)}"
            
            return {
                'success': True,
                'response': response,
                'sources': source_list,
                'architecture': 'hybrid_groq_qwen'
            }
            
        except Exception as e:
            print(f"Error en generación Qwen: {e}")
            # Fallback a modo básico
            return self._basic_search_response(user_query, extracted_info.get('relevant_content', ''), sources)
    
    def _generate_with_groq(self, user_query: str, extracted_info: Dict, sources: List[Dict]) -> Dict[str, Any]:
        """
        Fallback: Usar solo Groq para generar respuesta
        """
        try:
            groq_prompt = f"""INFORMACIÓN EXTRAÍDA:
{extracted_info.get('relevant_content', '')}

CONSULTA: {user_query}

Genera una respuesta precisa basándote únicamente en la información proporcionada."""

            completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_context},
                    {"role": "user", "content": groq_prompt}
                ],
                model=self.groq_model,
                max_tokens=2000,
                temperature=0.1
            )
            
            response = completion.choices[0].message.content.strip()
            source_list = [f"{doc['tipo_norma']}_{doc['numero']}_{doc['año']}" for doc in sources]
            if source_list:
                response += f"\n\n**Fuentes consultadas:** {', '.join(source_list)}"
            
            return {
                'success': True,
                'response': response,
                'sources': source_list,
                'architecture': 'groq_only'
            }
            
        except Exception as e:
            print(f"Error en generación Groq: {e}")
            return self._basic_search_response(user_query, extracted_info.get('relevant_content', ''), sources)
    
    def _extract_key_concepts_fallback(self, context: str) -> List[str]:
        """Extraer conceptos clave sin AI"""
        concepts = []
        keywords = ['seguridad', 'digital', 'ciberseguridad', 'tecnología', 'datos', 'información', 
                   'protección', 'privacidad', 'tratamiento', 'responsable', 'titular', 'conpes']
        
        context_lower = context.lower()
        for keyword in keywords:
            if keyword in context_lower:
                concepts.append(keyword)
        
        return concepts[:10]  # Máximo 10 conceptos
    
    def _extract_articles_fallback(self, context: str) -> List[str]:
        """Extraer artículos sin AI"""
        import re
        articles = []
        
        # Buscar patrones de artículos
        patterns = [
            r'artículo\s+\d+°*',
            r'capítulo\s+[ivxlc]+',
            r'numeral\s+\d+',
            r'literal\s+[a-z]\)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            articles.extend(matches[:5])  # Máximo 5 por patrón
        
        return list(set(articles))[:15]  # Máximo 15 artículos únicos

    def _generate_structured_response(self, user_query: str, context: str, sources: List[Dict]) -> str:
        """
        Generar respuesta estructurada basada en el tipo de consulta
        """
        query_lower = user_query.lower()
        
        # Detectar tipo de consulta específica - MEJORADO con más casos específicos
        # Primero verificar temas muy específicos
        if any(term in query_lower for term in ['datos sensibles', 'dato sensible', 'información sensible']):
            return self._extract_sensitive_data_info(context, sources[0] if sources else None)
        # Consultas sobre definiciones básicas de la Ley 1581 - ORDEN ESPECÍFICO IMPORTANTE
        elif 'encargado' in query_lower and any(word in query_lower for word in ['qué es', 'definición', 'define']):
            return self._extract_basic_definition(context, 'encargado', sources[0] if sources else None)
        elif 'responsable' in query_lower and any(word in query_lower for word in ['qué es', 'definición', 'define']):
            return self._extract_basic_definition(context, 'responsable', sources[0] if sources else None)
        elif 'titular' in query_lower and any(word in query_lower for word in ['qué es', 'definición', 'define']):
            return self._extract_basic_definition(context, 'titular', sources[0] if sources else None)
        elif 'tratamiento' in query_lower and any(word in query_lower for word in ['qué es', 'definición', 'define']):
            return self._extract_basic_definition(context, 'tratamiento', sources[0] if sources else None)
        # Obligaciones y derechos específicos
        elif 'obligaciones' in query_lower and 'responsable' in query_lower:
            return self._extract_responsable_obligations(context, sources[0] if sources else None)
        elif 'derechos' in query_lower and ('titular' in query_lower or 'persona' in query_lower):
            return self._extract_titular_rights(context, sources[0] if sources else None)
        # Consultas específicas sobre conceptos del decreto
        elif 'aviso' in query_lower and 'privacidad' in query_lower:
            return self._extract_privacy_notice_info(context, sources[0] if sources else None)
        elif any(phrase in query_lower for phrase in ['conservar datos', 'tiempo', 'cuánto tiempo']):
            return self._extract_data_retention_info(context, sources[0] if sources else None)
        elif any(phrase in query_lower for phrase in ['manejar datos sensibles', 'tratar datos sensibles']):
            return self._extract_sensitive_data_handling(context, sources[0] if sources else None)
        # Otros casos ya existentes
        elif any(word in query_lower for word in ['propone', 'objetivos', 'propósito', 'finalidad']):
            return self._extract_objectives_and_proposals(context, sources[0] if sources else None)
        elif any(word in query_lower for word in ['desarrolladores', 'desarrollo', 'software', 'programadores', 'aplicaciones']):
            return self._extract_developer_relevant_info(context, sources[0] if sources else None)
        elif any(word in query_lower for word in ['implementar', 'cumplir', 'aplicar', 'medidas']) and 'iso' not in query_lower:
            return self._extract_implementation_guidance(context, sources[0] if sources else None)
        else:
            return self._extract_security_relevant_info(user_query, context, sources)

    def _extract_objectives_and_proposals(self, context: str, doc: Dict) -> str:
        """Extraer objetivos y propuestas del documento"""
        lines = context.split('\n')
        relevant_sections = []
        
        # Buscar secciones de objetivos, propuestas, estrategias con mayor precisión
        objective_keywords = [
            'objetivo general', 'objetivo específico', 'propósito', 'finalidad', 
            'estrategia', 'propone', 'establece', 'busca', 'pretende', 
            'medidas para', 'política nacional', 'objetivo principal',
            'este documento conpes', 'la presente política', 'el objetivo de'
        ]
        
        # También buscar patrones específicos para CONPES
        conpes_patterns = [
            r'el presente documento conpes.*objetivo.*',
            r'política nacional.*objetivo.*',
            r'establece medidas para.*',
            r'tiene como objetivo.*',
            r'busca.*mediante.*',
            r'propone.*estrategia.*'
        ]
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            line_lower = line_clean.lower()
            
            # Verificar keywords
            has_keyword = any(keyword in line_lower for keyword in objective_keywords)
            
            # Verificar patrones específicos
            has_pattern = any(re.search(pattern, line_lower) for pattern in conpes_patterns)
            
            if has_keyword or has_pattern:
                # Extraer contexto más amplio para objetivos principales
                start = max(0, i-3)
                end = min(len(lines), i+12)
                section = []
                for j in range(start, end):
                    line_text = lines[j].strip()
                    if line_text and len(line_text) > 10:  # Evitar líneas muy cortas
                        section.append(line_text)
                
                if section and len(' '.join(section)) > 100:
                    relevant_sections.append(' '.join(section))
        
        # Buscar también en secciones de introducción y resumen ejecutivo
        for i, line in enumerate(lines[:100]):  # Primeras 100 líneas
            line_lower = line.strip().lower()
            if any(section_name in line_lower for section_name in ['resumen ejecutivo', 'introducción', 'justificación']):
                start = i
                end = min(len(lines), i+20)
                section = []
                for j in range(start, end):
                    line_text = lines[j].strip()
                    if line_text and not line_text.lower().startswith(('tabla', 'figura', 'gráfico')):
                        section.append(line_text)
                        if len(section) > 15:  # Limitar tamaño
                            break
                
                if section and len(' '.join(section)) > 200:
                    relevant_sections.append(' '.join(section))
        
        if relevant_sections:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "el documento"
            
            response = f"**Objetivos y propuestas principales de {doc_name}:**\n\n"
            
            # Remover duplicados similares
            unique_sections = []
            for section in relevant_sections:
                is_similar = False
                for existing in unique_sections:
                    words_overlap = len(set(section.lower().split()) & set(existing.lower().split()))
                    if words_overlap > len(section.split()) * 0.6:
                        is_similar = True
                        break
                if not is_similar:
                    unique_sections.append(section)
            
            for i, section in enumerate(unique_sections[:4], 1):
                # Limpiar texto
                section = re.sub(r'\s+', ' ', section)
                # Extraer la parte más relevante
                if len(section) > 5000:
                    # Buscar la oración más importante
                    sentences = section.split('. ')
                    important_sentences = []
                    for sentence in sentences:
                        if any(key in sentence.lower() for key in ['objetivo', 'propone', 'establece', 'busca', 'medidas', 'política']):
                            important_sentences.append(sentence)
                    
                    if important_sentences:
                        section = '. '.join(important_sentences[:3]) + '.'
                    else:
                        section = section[:5000] + "..."
                
                response += f"**{i}.** {section}\n\n"
            
            return response
        
        return self._extract_general_relevant_info("objetivos propuestas", context, [doc] if doc else [])

    def _extract_developer_relevant_info(self, context: str, doc: Dict) -> str:
        """Extraer información relevante para desarrolladores con mayor precisión"""
        lines = context.split('\n')
        relevant_sections = []
        
        # Palabras clave técnicas más específicas para desarrollo
        high_priority_keywords = [
            'sistema de información', 'aplicaciones', 'software', 'desarrollo tecnológico',
            'plataformas digitales', 'infraestructura tecnológica', 'arquitectura de seguridad',
            'implementación de medidas', 'controles de seguridad', 'gestión de riesgos'
        ]
        
        tech_keywords = [
            'sistema', 'aplicación', 'software', 'desarrollo', 'tecnología', 'digital',
            'infraestructura', 'ciberseguridad', 'datos', 'información', 'plataforma',
            'implementación', 'arquitectura', 'seguridad', 'privacidad', 'protección',
            'capacidades técnicas', 'estándares', 'framework', 'metodologías'
        ]
        
        # Patrones específicos para desarrolladores
        dev_patterns = [
            r'desarrollo.*sistema.*',
            r'implementación.*tecnología.*',
            r'capacidades.*técnicas.*',
            r'estándares.*seguridad.*',
            r'arquitectura.*información.*',
            r'gestión.*riesgos.*digital.*'
        ]
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            line_lower = line_clean.lower()
            
            # Priorizar keywords de alta relevancia
            has_high_priority = any(keyword in line_lower for keyword in high_priority_keywords)
            has_tech_keyword = any(keyword in line_lower for keyword in tech_keywords)
            has_dev_pattern = any(re.search(pattern, line_lower) for pattern in dev_patterns)
            
            if has_high_priority or has_tech_keyword or has_dev_pattern:
                # Extraer contexto técnico más amplio
                start = max(0, i-2)
                end = min(len(lines), i+8)
                section = []
                for j in range(start, end):
                    line_text = lines[j].strip()
                    if line_text and len(line_text) > 15:
                        section.append(line_text)
                
                if section:
                    section_text = ' '.join(section)
                    if len(section_text) > 150:  # Solo secciones sustanciales
                        # Dar mayor peso a secciones con keywords de alta prioridad
                        priority = 2 if has_high_priority else 1
                        relevant_sections.append((section_text, priority))
        
        if relevant_sections:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "el documento"
            
            response = f"**Relevancia de {doc_name} para desarrolladores de software:**\n\n"
            
            # Ordenar por prioridad y remover duplicados
            relevant_sections.sort(key=lambda x: x[1], reverse=True)
            unique_sections = []
            
            for section_text, priority in relevant_sections:
                is_duplicate = False
                for existing, _ in unique_sections:
                    words_overlap = len(set(section_text.lower().split()) & set(existing.lower().split()))
                    if words_overlap > len(section_text.split()) * 0.6:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_sections.append((section_text, priority))
            
            # Mostrar las secciones más relevantes
            for i, (section, priority) in enumerate(unique_sections[:4], 1):
                section = re.sub(r'\s+', ' ', section)
                
                # Extraer las oraciones más técnicamente relevantes
                if len(section) > 3000:
                    sentences = section.split('. ')
                    tech_sentences = []
                    for sentence in sentences:
                        if any(tech_term in sentence.lower() for tech_term in ['sistema', 'implementar', 'desarrollar', 'tecnología', 'seguridad', 'capacidades']):
                            tech_sentences.append(sentence)
                    
                    if tech_sentences:
                        section = '. '.join(tech_sentences[:3]) + '.'
                    else:
                        section = section[:3000] + "..."
                
                priority_indicator = "🔥 " if priority > 1 else ""
                response += f"**{priority_indicator}{i}.** {section}\n\n"
            
            # Agregar implicaciones técnicas específicas basadas en el contenido
            response += "\n**💻 Implicaciones técnicas específicas para desarrolladores:**\n\n"
            
            # Analizar el contenido para dar recomendaciones específicas
            context_lower = context.lower()
            if 'conpes' in context_lower and 'seguridad digital' in context_lower:
                response += "**Seguridad Digital (CONPES 3995):**\n"
                response += "• Implementar controles de ciberseguridad robustos desde el diseño\n"
                response += "• Adoptar frameworks de gestión de riesgos digitales\n"
                response += "• Cumplir con estándares nacionales de confianza digital\n"
                response += "• Desarrollar capacidades de detección y respuesta a incidentes\n\n"
            
            if 'datos' in context_lower or 'información' in context_lower:
                response += "**Protección de Datos e Información:**\n"
                response += "• Aplicar principios de Privacy by Design y Security by Design\n"
                response += "• Implementar cifrado y controles de acceso apropiados\n"
                response += "• Documentar y auditar medidas de protección de datos\n"
                response += "• Establecer procedimientos de respuesta a brechas de seguridad\n\n"
            
            if 'infraestructura' in context_lower:
                response += "**Infraestructura y Arquitectura:**\n"
                response += "• Diseñar arquitecturas resilientes y escalables\n"
                response += "• Implementar redundancia y planes de continuidad\n"
                response += "• Adoptar principios de Zero Trust Architecture\n"
                response += "• Monitorear y mantener la infraestructura crítica\n\n"
            
            response += "**📋 Recomendaciones de cumplimiento:**\n"
            response += "• Mantenerse actualizado con la normativa colombiana vigente\n"
            response += "• Participar en programas de capacitación en ciberseguridad\n"
            response += "• Colaborar con entidades gubernamentales en temas de seguridad digital\n"
            response += "• Implementar ciclos de mejora continua en seguridad\n"
            
            return response
        
        return self._extract_general_relevant_info("desarrolladores tecnología sistemas", context, [doc] if doc else [])

    def _extract_document_overview(self, context: str, doc: Dict) -> str:
        """Extraer resumen y overview del documento"""
        lines = context.split('\n')
        
        # Buscar resumen ejecutivo, introducción, antecedentes
        overview_sections = []
        current_section = []
        
        for line in lines[:200]:  # Primeras 200 líneas donde suele estar el resumen
            line_clean = line.strip()
            if not line_clean:
                if current_section:
                    overview_sections.append(' '.join(current_section))
                    current_section = []
                continue
            
            # Identificar secciones de resumen
            if any(keyword in line_clean.lower() for keyword in ['resumen', 'antecedentes', 'introducción', 'contexto', 'justificación']):
                if current_section:
                    overview_sections.append(' '.join(current_section))
                current_section = [line_clean]
            elif current_section:
                current_section.append(line_clean)
                # Limitar tamaño de sección
                if len(current_section) > 15:
                    overview_sections.append(' '.join(current_section))
                    current_section = []
        
        if current_section:
            overview_sections.append(' '.join(current_section))
        
        if overview_sections:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "el documento"
            
            response = f"**Resumen de {doc_name}:**\n\n"
            
            for i, section in enumerate(overview_sections[:3], 1):
                section = re.sub(r'\s+', ' ', section)
                if len(section) > 4000:
                    section = section[:4000] + "..."
                response += f"**Sección {i}:**\n{section}\n\n"
            
            return response
        
        return self._extract_general_relevant_info("resumen información", context, [doc] if doc else [])

    def _find_definition_in_text(self, text: str, term: str) -> Dict[str, str]:
        """
        PRINCIPIO: Separación de responsabilidades - Solo encontrar, no formatear
        """
        # Mapeo preciso de patrones
        term_definitions = {
            'tratamiento': r'g\)\s*Tratamiento:\s*(.*?)(?=\n[a-z]\)|TÍTULO|$)',
            'responsable': r'e\)\s*Responsable del Tratamiento:\s*(.*?)(?=\nf\)|TÍTULO|$)', 
            'titular': r'f\)\s*Titular:\s*(.*?)(?=\ng\)|TÍTULO|$)',
            'encargado': r'd\)\s*Encargado del Tratamiento:\s*(.*?)(?=\ne\)|TÍTULO|$)'
        }
        
        pattern = term_definitions.get(term)
        if not pattern:
            return {'found': False, 'error': f'Término "{term}" no configurado'}
        
        # Buscar con regex multilinea
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        
        if match:
            definition_text = match.group(1).strip()
            # Limpiar definición
            definition_text = re.sub(r'\s+', ' ', definition_text)
            return {
                'found': True, 
                'definition': f"{term.title()}: {definition_text}",
                'raw_match': match.group(0)
            }
        
        return {'found': False, 'error': f'Patrón para "{term}" no encontrado en el texto'}
    
    def _format_definition_response(self, definition_result: Dict, term: str, doc: Dict) -> str:
        """
        PRINCIPIO: Separación de responsabilidades - Solo formatear
        """
        if not definition_result['found']:
            return f"❌ Error: {definition_result['error']}"
        
        doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "la normativa"
        
        response = f"**Definición de {term} según {doc_name}:**\n\n"
        response += f'"{definition_result["definition"]}"\n\n'
        
        # Contexto específico por término
        context_info = {
            'tratamiento': "**Alcance:** Incluye recolección, almacenamiento, uso, circulación o supresión de datos.",
            'responsable': "**Rol:** Decide sobre la finalidad y el tratamiento de los datos personales.",
            'titular': "**Limitación:** Solo personas naturales pueden ser titulares.",
            'encargado': "**Función:** Realiza el tratamiento por cuenta del responsable."
        }
        
        if term in context_info:
            response += context_info[term] + "\n"
        
        return response
    
    def _extract_basic_definition(self, context: str, term: str, doc: Dict) -> str:
        """
        PRINCIPIO: Validación temprana + Composición
        """
        # VALIDACIÓN TEMPRANA: Verificar que estamos en el documento correcto
        if not doc or doc.get('numero') != '1581':
            return f"❌ Error: Definiciones básicas requieren la Ley 1581, pero recibí {doc.get('tipo_norma', 'documento desconocido')} {doc.get('numero', 'sin número')}"
        
        # 1. Encontrar definición
        definition_result = self._find_definition_in_text(context, term)
        
        # 2. Formatear respuesta
        return self._format_definition_response(definition_result, term, doc)
    
    def _extract_responsable_obligations(self, context: str, doc: Dict) -> str:
        """Extraer las obligaciones del responsable del Artículo 17"""
        lines = context.split('\n')
        obligations_found = []
        
        # Buscar el Artículo 17
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if re.search(r'Artículo\s+17[°º]?\.?\s*', line_clean, re.IGNORECASE):
                # Verificar que sea sobre deberes/obligaciones (puede estar en la misma línea o siguiente)
                context_text = line_clean
                if i+1 < len(lines):
                    context_text += ' ' + lines[i+1].strip()
                
                if 'deberes' in context_text.lower() or 'obligaciones' in context_text.lower():
                    # Extraer todas las obligaciones (letras a) hasta o))
                    for j in range(i+2, min(i+30, len(lines))):
                        obligation_line = lines[j].strip()
                        if obligation_line:
                            # Si es una obligación (empieza con letra))
                            if re.match(r'^[a-o]\)', obligation_line):
                                # Extraer la obligación completa
                                obligation_text = obligation_line
                                # Continuar si la obligación es multilínea
                                for k in range(j+1, min(j+5, len(lines))):
                                    next_line = lines[k].strip()
                                    if next_line and not re.match(r'^[a-o]\)', next_line):
                                        obligation_text += ' ' + next_line
                                    else:
                                        break
                                obligations_found.append(obligation_text)
                            # Si llegamos a otro artículo, terminar
                            elif re.match(r'^Artículo\s+\d+', obligation_line):
                                break
                    break
        
        if obligations_found:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "la normativa"
            response = f"**Deberes del Responsable del Tratamiento según {doc_name} (Artículo 17):**\n\n"
            
            for obligation in obligations_found:
                response += f"• {obligation}\n\n"
            
            response += "\n**Importante:** El incumplimiento de estos deberes puede acarrear sanciones por parte de la Superintendencia de Industria y Comercio."
            
            return response
        
        return "No encontré información sobre las obligaciones del responsable en el documento consultado."
    
    def _extract_titular_rights(self, context: str, doc: Dict) -> str:
        """Extraer los derechos del titular"""
        lines = context.split('\n')
        rights_found = []
        
        # Buscar el Artículo 8 (Derechos de los titulares)
        for i, line in enumerate(lines):
            if re.search(r'Artículo\s+8[°º]?\.?\s*', line, re.IGNORECASE):
                # Verificar que sea sobre derechos
                if i+1 < len(lines) and 'derecho' in lines[i+1].lower():
                    # Extraer todos los derechos
                    for j in range(i+2, min(i+20, len(lines))):
                        right_line = lines[j].strip()
                        if right_line:
                            # Si es un derecho (empieza con letra))
                            if re.match(r'^[a-f]\)', right_line):
                                rights_found.append(right_line)
                            # Si llegamos a otro artículo, terminar
                            elif re.match(r'^Artículo\s+\d+', right_line):
                                break
                    break
        
        if rights_found:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "la normativa"
            response = f"**Derechos del Titular según {doc_name} (Artículo 8):**\n\n"
            
            for right in rights_found:
                response += f"• {right}\n\n"
            
            response += "\n**Nota:** Estos derechos son gratuitos y pueden ejercerse en cualquier momento ante el Responsable del Tratamiento."
            
            return response
        
        return "No encontré información sobre los derechos del titular en el documento consultado."

    def _extract_sensitive_data_info(self, context: str, doc: Dict) -> str:
        """Extraer información específica sobre datos sensibles"""
        lines = context.split('\n')
        relevant_sections = []
        
        # Palabras clave específicas para datos sensibles
        sensitive_keywords = [
            'datos sensibles', 'dato sensible', 'información sensible',
            'afectan la intimidad', 'origen racial', 'orientación política',
            'convicciones religiosas', 'vida sexual', 'datos biométricos',
            'salud', 'discriminación'
        ]
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            line_lower = line_clean.lower()
            
            # Buscar definiciones específicas de DATOS SENSIBLES, no otros tipos
            if any(keyword in line_lower for keyword in ['datos sensibles', 'dato sensible']):
                # Verificar que sea específicamente sobre datos sensibles
                if 'datos sensibles:' in line_lower or ('se entiende' in line_lower and 'sensibles' in line_lower):
                    # Extraer contexto completo de la definición
                    start = i  # Empezar desde la línea actual
                    end = min(len(lines), i+15)  # Más contexto para definiciones completas
                    
                    definition_lines = []
                    for j in range(start, end):
                        line_text = lines[j].strip()
                        if line_text:
                            definition_lines.append(line_text)
                            # Si encontramos otra definición o sección, parar
                            if j > i and any(stop in line_text.lower() for stop in ['transferencia:', 'transmisión:', 'artículo', 'capítulo']):
                                break
                    
                    if definition_lines and len(' '.join(definition_lines)) > 100:
                        relevant_sections.append(' '.join(definition_lines))
                        break  # Una definición completa es suficiente
        
        if relevant_sections:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "el documento"
            
            response = f"**Definición de datos sensibles según {doc_name}:**\n\n"
            
            for section in relevant_sections:
                section = re.sub(r'\s+', ' ', section)
                response += f'"{section}"\n\n'
            
            # Agregar implicaciones prácticas
            response += "**Implicaciones importantes:**\n"
            response += "• Requieren autorización explícita del titular\n"
            response += "• El titular no está obligado a autorizar su tratamiento\n"
            response += "• Se debe informar claramente que son datos sensibles\n"
            response += "• Ninguna actividad puede condicionarse a su suministro\n"
            
            return response
        
        return "No encontré una definición específica de datos sensibles en el documento consultado."

    def _extract_implementation_guidance(self, context: str, doc: Dict) -> str:
        """Extraer guías de implementación y cumplimiento"""
        lines = context.split('\n')
        relevant_sections = []
        
        # Palabras clave de implementación
        impl_keywords = [
            'implementar', 'cumplir', 'aplicar', 'ejecutar', 'desarrollar', 'establecer',
            'medidas', 'acciones', 'procedimientos', 'requisitos', 'obligaciones',
            'debe', 'deberá', 'se requiere', 'necesario'
        ]
        
        for i, line in enumerate(lines):
            line_clean = line.strip().lower()
            if any(keyword in line_clean for keyword in impl_keywords):
                start = max(0, i-1)
                end = min(len(lines), i+5)
                section = []
                for j in range(start, end):
                    if lines[j].strip():
                        section.append(lines[j].strip())
                
                if section:
                    relevant_sections.append(' '.join(section))
        
        if relevant_sections:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "el documento"
            
            response = f"**Guía de implementación según {doc_name}:**\n\n"
            
            for i, section in enumerate(relevant_sections[:4], 1):
                section = re.sub(r'\s+', ' ', section)
                if len(section) > 700:
                    section = section[:700] + "..."
                response += f"**Punto {i}:** {section}\n\n"
            
            return response
        
        return self._extract_general_relevant_info("implementación medidas", context, [doc] if doc else [])

    def _extract_general_relevant_info(self, user_query: str, context: str, sources: List[Dict]) -> str:
        """Sistema de extracción inteligente GENERAL mejorado"""
        query_lower = user_query.lower()
        
        # 1. ANÁLISIS SEMÁNTICO DE LA CONSULTA
        # Extraer términos clave con pesos diferentes
        query_analysis = self._analyze_query_semantics(query_lower)
        
        # 2. BÚSQUEDA INTELIGENTE EN CONTEXTO
        lines = context.split('\n')
        scored_sections = []
        
        # Agrupar líneas en secciones semánticas
        current_section = []
        section_type = None
        
        # Skipear encabezados genéricos
        skip_patterns = [
            'decreto 1377 de 2013',
            'reglamenta parcialmente la ley',
            'considerando:',
            'decreta:',
            'el presidente de la república'
        ]
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Ignorar líneas genéricas del encabezado
            if any(skip in line_clean.lower() for skip in skip_patterns):
                continue
                
            if not line_clean:
                if current_section and len(' '.join(current_section)) > 40:  # Solo secciones sustanciales
                    section_result = self._score_section(
                        current_section, 
                        query_analysis, 
                        section_type,
                        i - len(current_section)
                    )
                    if section_result['score'] > 0:  # Solo agregar si tiene relevancia
                        scored_sections.append(section_result)
                current_section = []
                section_type = None
                continue
            
            # Detectar tipo de sección
            line_lower = line_clean.lower()
            if re.match(r'^artículo\s+\d+', line_lower):
                section_type = 'article'
            elif re.match(r'^(capítulo|título|sección)', line_lower):
                section_type = 'chapter'
            elif any(defn in line_lower for defn in ['se entiende', 'definición', 'significa']):
                section_type = 'definition'
            elif any(req in line_lower for req in ['debe', 'deberá', 'obligación', 'requisito']):
                section_type = 'requirement'
            
            current_section.append(line_clean)
        
        # Procesar última sección
        if current_section:
            scored_sections.append(self._score_section(
                current_section, 
                query_analysis, 
                section_type,
                len(lines) - len(current_section)
            ))
        
        # 3. SELECCIÓN INTELIGENTE DE SECCIONES
        # Filtrar secciones con score > 0
        relevant_sections = [s for s in scored_sections if s['score'] > 0]
        
        # Ordenar por relevancia
        relevant_sections.sort(key=lambda x: x['score'], reverse=True)
        
        # 4. CONSTRUCCIÓN DE RESPUESTA INTELIGENTE
        if relevant_sections:
            doc_info = sources[0] if sources else None
            doc_name = f"{doc_info['tipo_norma']} {doc_info['numero']} de {doc_info['año']}" if doc_info else "la normativa"
            
            response = f"**Información relevante encontrada en {doc_name}:**\n\n"
            
            # Agrupar por tipo de contenido
            articles = [s for s in relevant_sections[:6] if s['type'] == 'article']
            definitions = [s for s in relevant_sections[:6] if s['type'] == 'definition']
            requirements = [s for s in relevant_sections[:6] if s['type'] == 'requirement']
            others = [s for s in relevant_sections[:6] if s['type'] not in ['article', 'definition', 'requirement']]
            
            # Mostrar en orden lógico
            shown_count = 0
            
            # Primero definiciones si las hay
            if definitions and shown_count < 3:
                response += "**📖 Definiciones:**\n"
                for section in definitions[:2]:
                    response += f"• {self._format_section_content(section['content'])}\n\n"
                    shown_count += 1
            
            # Luego artículos relevantes
            if articles and shown_count < 4:
                response += "**📋 Artículos relevantes:**\n"
                for section in articles[:2]:
                    response += f"• {self._format_section_content(section['content'])}\n\n"
                    shown_count += 1
            
            # Después requisitos/obligaciones
            if requirements and shown_count < 5:
                response += "**⚖️ Requisitos y obligaciones:**\n"
                for section in requirements[:2]:
                    response += f"• {self._format_section_content(section['content'])}\n\n"
                    shown_count += 1
            
            # Finalmente otra información relevante
            if others and shown_count < 5:
                response += "**ℹ️ Información adicional:**\n"
                for section in others[:1]:
                    response += f"• {self._format_section_content(section['content'])}\n\n"
                    shown_count += 1
            
            return response
        
        return "No encontré información específicamente relevante para tu consulta en el documento disponible."
    
    def _analyze_query_semantics(self, query: str) -> Dict[str, Any]:
        """Analizar semánticamente la consulta para extraer términos con pesos"""
        # Palabras vacías en español
        stop_words = {
            'el', 'la', 'de', 'en', 'y', 'a', 'los', 'las', 'un', 'una', 'para', 'con',
            'por', 'del', 'al', 'es', 'son', 'se', 'su', 'que', 'como', 'más', 'sobre',
            'qué', 'cuál', 'cuáles', 'dice', 'establece', 'define', 'menciona'
        }
        
        # Términos legales importantes
        legal_terms = {
            'artículo', 'ley', 'decreto', 'resolución', 'circular', 'capítulo',
            'obligación', 'derecho', 'deber', 'requisito', 'procedimiento',
            'sanción', 'infracción', 'responsable', 'titular', 'tratamiento'
        }
        
        # Términos técnicos importantes
        tech_terms = {
            'datos', 'información', 'seguridad', 'protección', 'privacidad',
            'autorización', 'consentimiento', 'transferencia', 'sensible',
            'personal', 'confidencial', 'acceso', 'uso', 'finalidad'
        }
        
        words = query.split()
        terms = {}
        
        for word in words:
            word_clean = word.lower().strip('.,;:?¿!¡')
            
            if word_clean in stop_words or len(word_clean) < 3:
                continue
            
            # Asignar pesos según tipo
            if word_clean in legal_terms:
                terms[word_clean] = 3  # Alta prioridad
            elif word_clean in tech_terms:
                terms[word_clean] = 2  # Media prioridad
            else:
                terms[word_clean] = 1  # Prioridad normal
        
        return {
            'terms': terms,
            'has_article_ref': any('artículo' in w.lower() for w in words),
            'has_number': any(w.isdigit() for w in words),
            'query_type': self._determine_query_type(query)
        }
    
    def _determine_query_type(self, query: str) -> str:
        """Determinar el tipo de consulta para mejor procesamiento"""
        query_lower = query.lower()
        
        if any(q in query_lower for q in ['qué es', 'definición', 'concepto']):
            return 'definition'
        elif any(q in query_lower for q in ['obligación', 'debe', 'requisito']):
            return 'requirement'
        elif any(q in query_lower for q in ['procedimiento', 'cómo', 'pasos']):
            return 'procedure'
        elif any(q in query_lower for q in ['sanción', 'multa', 'penalidad']):
            return 'sanction'
        else:
            return 'general'
    
    def _score_section(self, lines: List[str], query_analysis: Dict, section_type: str, start_line: int) -> Dict:
        """Puntuar una sección según su relevancia"""
        section_text = ' '.join(lines)
        section_lower = section_text.lower()
        
        score = 0
        matched_terms = []
        
        # Puntuar según términos de consulta
        for term, weight in query_analysis['terms'].items():
            if term in section_lower:
                # Más puntos si el término aparece múltiples veces
                occurrences = section_lower.count(term)
                score += weight * min(occurrences, 3)
                matched_terms.append(term)
        
        # Bonus por tipo de sección según tipo de consulta
        query_type = query_analysis['query_type']
        if section_type == 'definition' and query_type == 'definition':
            score += 5
        elif section_type == 'requirement' and query_type == 'requirement':
            score += 5
        elif section_type == 'article' and query_analysis['has_article_ref']:
            score += 3
        
        # Penalizar secciones muy cortas o muy largas
        if len(section_text) < 50:
            score *= 0.5
        elif len(section_text) > 8000:
            score *= 0.8
        
        # Bonus por contenido estructurado
        if any(marker in section_lower for marker in ['1.', '2.', 'a)', 'b)', '•']):
            score += 2
        
        return {
            'content': section_text,
            'score': score,
            'type': section_type or 'general',
            'matched_terms': matched_terms,
            'start_line': start_line
        }
    
    def _format_section_content(self, content: str) -> str:
        """Formatear contenido de sección para mejor legibilidad"""
        # Limpiar marcadores de contexto
        content = re.sub(r'^---.*?---\s*', '', content)
        
        # Limpiar espacios excesivos
        content = re.sub(r'\s+', ' ', content)
        
        # Remover encabezados repetitivos
        generic_headers = [
            'Decreto 1377 de 2013',
            'Ley 1581 de 2012',
            'Reglamenta parcialmente',
            'Por la cual se dictan disposiciones'
        ]
        
        for header in generic_headers:
            if content.startswith(header):
                # Buscar el primer punto o dos puntos para cortar
                cut_point = content.find('. ')
                if cut_point > 0 and cut_point < 200:
                    content = content[cut_point + 2:]
        
        # Limitar longitud inteligentemente
        if len(content) > 10000:
            # Buscar un punto de corte natural SOLO si es extremadamente largo
            sentences = content.split('. ')
            truncated = ""
            for sentence in sentences:
                if len(truncated) + len(sentence) < 8000:
                    truncated += sentence + ". "
                else:
                    break
            content = truncated.strip()
            if not content.endswith('.'):
                content += "..."
        
        return content.strip()

    def _validate_content_relevance(self, user_query: str, content: str, doc: Dict) -> Dict[str, Any]:
        """
        Validación estricta de relevancia antes de responder
        """
        query_lower = user_query.lower()
        content_lower = content.lower()
        
        # Términos críticos que deben coincidir
        critical_terms = []
        
        # Extraer términos específicos de la consulta
        specific_terms = {
            'ley 1581': ['1581', 'protección', 'datos personales'],
            'decreto 1377': ['1377', 'datos personales', 'reglament'],
            'conpes': ['conpes', 'seguridad digital', 'confianza'],
            'iso 27001': ['seguridad', 'información', 'gestión'],
            'circular': ['circular', 'superintendencia'],
            'resolución': ['resolución', 'dian', 'sic']
        }
        
        # Verificar relevancia directa
        doc_type = doc.get('tipo_norma', '').lower()
        doc_number = doc.get('numero', '')
        
        # Casos donde NO debe responder (ejemplos de la mala respuesta)
        irrelevant_cases = [
            # Si pregunta por datos personales pero el doc es de comercio exterior sin mencionar datos
            (any(term in query_lower for term in ['datos personales', 'protección datos']) and 
             'comercio exterior' in content_lower and 
             not any(term in content_lower for term in ['datos personales', 'protección', 'tratamiento'])),
            
            # Si pregunta por ISO 27001 pero menciona decretos sectoriales sin relación
            (any(term in query_lower for term in ['iso', '27001', 'implementar']) and
             any(sector in content_lower for sector in ['sector trabajo', 'sector comercio']) and
             not any(term in content_lower for term in ['seguridad', 'información', 'gestión', 'iso'])),
        ]
        
        # Si es irrelevante, rechazar
        if any(irrelevant_cases):
            return {
                'relevant': False,
                'reason': 'El documento no contiene información directamente relacionada con la consulta'
            }
        
        # Verificar coincidencias mínimas
        query_words = [word for word in query_lower.split() if len(word) > 3]
        content_matches = sum(1 for word in query_words if word in content_lower)
        
        if len(query_words) > 0 and content_matches / len(query_words) < 0.3:
            return {
                'relevant': False,
                'reason': 'Insuficientes coincidencias temáticas entre la consulta y el contenido'
            }
        
        return {'relevant': True}

    def _extract_textual_citations(self, content: str, query_terms: List[str]) -> List[str]:
        """
        Extraer citas textuales específicas, no interpretaciones
        """
        lines = content.split('\n')
        citations = []
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if len(line_clean) < 20:  # Muy corto para ser útil
                continue
                
            line_lower = line_clean.lower()
            
            # Solo incluir si contiene términos específicos de la consulta
            if any(term in line_lower for term in query_terms):
                # Agregar contexto si es un artículo o definición
                if any(marker in line_lower for marker in ['artículo', 'definición', 'establece', 'dispone']):
                    # Extraer contexto ampliado para artículos
                    start = max(0, i-1)
                    end = min(len(lines), i+5)
                    context_lines = []
                    for j in range(start, end):
                        if lines[j].strip():
                            context_lines.append(lines[j].strip())
                    
                    if context_lines:
                        citation = ' '.join(context_lines)
                        if len(citation) > 100:  # Solo citas sustanciales
                            citations.append(citation)
                else:
                    # Cita directa de la línea
                    if len(line_clean) > 50:
                        citations.append(line_clean)
        
        return citations[:3]  # Máximo 3 citas más relevantes

    def _basic_search_response(self, user_query: str, context: str, sources: List[Dict]) -> Dict[str, Any]:
        """
        Respuesta básica usando sistema de respuestas estructuradas
        """
        try:
            if not sources:
                return {
                    'success': False,
                    'response': 'No encontré documentos relevantes para tu consulta en la normativa disponible.',
                    'sources': []
                }
            
            # PRIORIZAR SISTEMA DE RESPUESTAS ESTRUCTURADAS 
            query_lower = user_query.lower()
            
            # Para consultas sobre temas fundamentales, SALTARSE validación de relevancia
            is_fundamental_query = any(term in query_lower for term in [
                'obligaciones', 'derechos', 'qué es', 'definición', 'tratamiento', 
                'responsable', 'titular', 'encargado', 'datos sensibles', 'aviso', 'privacidad'
            ])
            
            if is_fundamental_query:
                # USAR DIRECTAMENTE el sistema estructurado sin validación previa
                structured_response = self._generate_structured_response(user_query, context, sources)
                
                if structured_response:
                    return {
                        'success': True,
                        'response': structured_response,
                        'sources': [doc['nombre_archivo'] for doc in sources]
                    }
            
            # Para consultas no fundamentales, usar sistema con validación
            structured_response = self._generate_structured_response(user_query, context, sources)
            
            # Si la respuesta estructurada es satisfactoria, usarla
            if structured_response and not structured_response.startswith("❌ Error:") and "No encontré" not in structured_response:
                return {
                    'success': True,
                    'response': structured_response,
                    'sources': [doc['nombre_archivo'] for doc in sources]
                }
            
            # Fallback: validación de relevancia solo para consultas no fundamentales
            main_doc = sources[0]
            relevance_check = self._validate_content_relevance(user_query, context, main_doc)
            
            if not relevance_check['relevant']:
                return {
                    'success': False,
                    'response': f"No encontré información específicamente relevante sobre '{user_query}' en la normativa disponible. {relevance_check.get('reason', '')}",
                    'sources': []
                }
            
            # Extraer términos clave de la consulta
            query_lower = user_query.lower()
            query_terms = [word for word in query_lower.split() if len(word) > 3]
            
            # Extraer citas textuales específicas
            textual_citations = self._extract_textual_citations(context, query_terms)
            
            if not textual_citations:
                return {
                    'success': False,
                    'response': f"Aunque encontré el documento {main_doc['tipo_norma']} {main_doc['numero']} de {main_doc['año']}, no contiene información específica sobre '{user_query}'.",
                    'sources': [main_doc['nombre_archivo']]
                }
            
            # Usar respuesta estructurada si es posible
            structured_response = self._generate_structured_response(user_query, context, [main_doc])
            
            # Si no hay respuesta estructurada específica, usar citas textuales
            if structured_response == "**Información encontrada:**\n\nNo se encontraron secciones específicamente relevantes para tu consulta en el documento disponible.":
                doc_name = f"{main_doc['tipo_norma']} {main_doc['numero']} de {main_doc['año']}"
                response = f"**Información encontrada en {doc_name}:**\n\n"
                
                for i, citation in enumerate(textual_citations, 1):
                    citation = re.sub(r'\s+', ' ', citation)
                    if len(citation) > 3000:
                        citation = citation[:3000] + "..."
                    response += f"**{i}.** \"{citation}\"\n\n"
                
                response += f"\n**Fuente:** {doc_name}\n"
                response += "\n*Nota: Esta respuesta se basa exclusivamente en el contenido textual del documento mencionado.*"
            else:
                response = structured_response
            
            return {
                'success': True,
                'response': response,
                'sources': [main_doc['nombre_archivo']]
            }
            
        except Exception as e:
            return {
                'success': False,
                'response': f'Error procesando la consulta. Por favor, intenta con términos más específicos.',
                'sources': []
            }
    
    def _extract_privacy_notice_info(self, context: str, doc: Dict) -> str:
        """Extraer información sobre aviso de privacidad"""
        import re
        
        # Buscar definición de aviso de privacidad
        pattern = r'(Aviso de privacidad:.*?)(?=\n\d+\.|$)'
        match = re.search(pattern, context, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        
        if match:
            definition = match.group(1).strip()
            definition = re.sub(r'\s+', ' ', definition)
            
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "la normativa"
            
            response = f"**Definición de aviso de privacidad según {doc_name}:**\n\n"
            response += f'"{definition}"\n\n'
            response += "**Características del aviso de privacidad:**\n"
            response += "• Es una comunicación verbal o escrita\n"
            response += "• Informa sobre la existencia de políticas de tratamiento\n"
            response += "• Indica cómo acceder a las políticas\n"
            response += "• Describe las finalidades del tratamiento\n"
            
            return response
        
        return "No encontré información específica sobre aviso de privacidad en el documento."
    
    def _extract_data_retention_info(self, context: str, doc: Dict) -> str:
        """Extraer información sobre conservación de datos"""
        import re
        
        lines = context.split('\n')
        retention_info = []
        
        # Buscar información sobre limitaciones temporales
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(term in line_lower for term in ['limitaciones temporales', 'conservar', 'tiempo', 'supresión']):
                # Extraer contexto de 5 líneas
                context_lines = []
                for j in range(max(0, i-2), min(len(lines), i+8)):
                    if lines[j].strip():
                        context_lines.append(lines[j].strip())
                
                if context_lines:
                    section_text = ' '.join(context_lines)
                    if len(section_text) > 100:  # Solo secciones sustanciales
                        retention_info.append(section_text)
                        break
        
        if retention_info:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "la normativa"
            
            response = f"**Conservación de datos según {doc_name}:**\n\n"
            for info in retention_info:
                info = re.sub(r'\s+', ' ', info)
                response += f'"{info}"\n\n'
            
            response += "**Principios clave:**\n"
            response += "• Solo durante el tiempo razonable y necesario\n"
            response += "• Según las finalidades que justificaron el tratamiento\n"
            response += "• Cumplir obligaciones legales o contractuales\n"
            response += "• Documentar procedimientos de conservación y supresión\n"
            
            return response
        
        return "No encontré información específica sobre conservación de datos en el documento."
    
    def _extract_sensitive_data_handling(self, context: str, doc: Dict) -> str:
        """Extraer información sobre manejo de datos sensibles"""
        import re
        
        lines = context.split('\n')
        handling_info = []
        
        # Buscar información sobre tratamiento de datos sensibles
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(term in line_lower for term in ['tratamiento de datos sensibles', 'datos sensibles', 'autorización para']):
                if 'sensibles' in line_lower:
                    # Extraer contexto amplio
                    context_lines = []
                    for j in range(max(0, i-1), min(len(lines), i+10)):
                        if lines[j].strip():
                            context_lines.append(lines[j].strip())
                    
                    if context_lines:
                        section_text = ' '.join(context_lines)
                        if len(section_text) > 150:
                            handling_info.append(section_text)
                            break
        
        if handling_info:
            doc_name = f"{doc['tipo_norma']} {doc['numero']} de {doc['año']}" if doc else "la normativa"
            
            response = f"**Manejo de datos sensibles según {doc_name}:**\n\n"
            for info in handling_info:
                info = re.sub(r'\s+', ' ', info)
                response += f'"{info}"\n\n'
            
            response += "**Requisitos especiales:**\n"
            response += "• Informar que no está obligado a autorizar\n"
            response += "• Obtener consentimiento explícito\n"
            response += "• Informar cuáles datos son sensibles\n"
            response += "• No condicionar actividades a su suministro\n"
            
            return response
        
        return "No encontré información específica sobre manejo de datos sensibles en el documento."
    
    def _extract_security_relevant_info(self, user_query: str, context: str, sources: List[Dict]) -> str:
        """
        Extraer información relevante para seguridad de la información y conectar con ISO 27001
        """
        import re
        
        query_lower = user_query.lower()
        
        # CONEXIONES ESPECÍFICAS CON SEGURIDAD DE LA INFORMACIÓN
        if any(term in query_lower for term in ['iso', '27001', 'seguridad información', 'implementar']):
            return self._extract_iso27001_connections(context, sources)
        
        # PRINCIPIOS DE TRATAMIENTO (relevantes para controles de seguridad)
        if 'principios' in query_lower:
            return self._extract_data_principles_for_security(context, sources)
        
        # AUTORIZACIÓN (control de acceso)
        if 'autorización' in query_lower:
            return self._extract_authorization_controls(context, sources)
        
        # POLÍTICAS DE TRATAMIENTO (documentación de seguridad)
        if any(term in query_lower for term in ['política', 'procedimiento', 'manual']):
            return self._extract_policy_requirements(context, sources)
        
        # HABEAS DATA (derecho de acceso y rectificación)
        if 'habeas data' in query_lower:
            return self._extract_data_subject_rights(context, sources)
        
        # TRANSFERENCIAS INTERNACIONALES (controles de transferencia)
        if any(term in query_lower for term in ['transferir', 'transmisión', 'país', 'internacional']):
            return self._extract_transfer_controls(context, sources)
        
        # MENORES DE EDAD (datos especiales)
        if any(term in query_lower for term in ['menores', 'niños', 'adolescentes']):
            return self._extract_minors_data_protection(context, sources)
        
        # VIDEOVIGILANCIA (monitoreo y control)
        if 'videovigilancia' in query_lower:
            return self._extract_surveillance_requirements(context, sources)
        
        # FALLBACK: Respuesta educativa sobre la conexión
        return self._explain_data_protection_security_connection(user_query, sources)
    
    def _extract_iso27001_connections(self, context: str, sources: List[Dict]) -> str:
        """Explicar conexiones entre protección de datos e ISO 27001"""
        
        doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa colombiana"
        
        response = f"**Conexión entre {doc_name} e ISO 27001:**\n\n"
        
        response += "**📋 Controles ISO 27001 relacionados:**\n"
        response += "• **A.18.1** - Cumplimiento de requisitos legales y contractuales\n"
        response += "• **A.18.2** - Revisiones de seguridad de la información\n"
        response += "• **A.13.2** - Transferencia de información\n"
        response += "• **A.9.1** - Controles de acceso a la información\n\n"
        
        response += "**🔒 Implementación práctica:**\n"
        response += "• **Clasificación de datos**: Identificar datos personales como información sensible\n"
        response += "• **Control de acceso**: Implementar autorización del titular como control\n"
        response += "• **Retención**: Definir períodos según finalidad del tratamiento\n"
        response += "• **Cifrado**: Proteger datos personales en tránsito y reposo\n"
        response += "• **Auditoría**: Registrar accesos y modificaciones\n\n"
        
        response += "**⚖️ Requisitos normativos específicos:**\n"
        
        # Extraer información específica del contexto
        lines = context.split('\n')
        security_relevant = []
        
        for line in lines:
            line_lower = line.lower()
            if any(term in line_lower for term in ['seguridad', 'protección', 'conservar', 'medidas', 'procedimientos', 'autorización']):
                if len(line.strip()) > 30:  # Solo líneas sustanciales
                    security_relevant.append(line.strip())
                    if len(security_relevant) >= 8:
                        break
        
        if security_relevant:
            for req in security_relevant:
                # Limpiar la línea
                req = re.sub(r'\s+', ' ', req)
                response += f"• {req[:800]}...\n"
        else:
            response += "• Garantizar condiciones de seguridad para impedir alteración\n"
            response += "• Conservar información bajo condiciones apropiadas\n"
            response += "• Implementar controles de acceso y autorización\n"
        
        response += f"\n**📖 Fuente normativa:** {doc_name}"
        
        return response
    
    def _extract_data_principles_for_security(self, context: str, sources: List[Dict]) -> str:
        """Extraer principios de tratamiento enfocados en seguridad"""
        
        # Buscar principios específicos
        lines = context.split('\n')
        principles = []
        
        for i, line in enumerate(lines):
            if 'principio' in line.lower() and any(term in line.lower() for term in ['seguridad', 'legalidad', 'finalidad', 'proporcionalidad']):
                # Extraer contexto del principio
                principle_context = []
                for j in range(i, min(i+3, len(lines))):
                    if lines[j].strip():
                        principle_context.append(lines[j].strip())
                
                if principle_context:
                    principles.append(' '.join(principle_context))
        
        if principles:
            doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa"
            
            response = f"**Principios de tratamiento según {doc_name}:**\n\n"
            
            for i, principle in enumerate(principles[:4], 1):
                principle = re.sub(r'\s+', ' ', principle)
                response += f"**{i}.** {principle[:1000]}...\n\n"
            
            response += "**🔐 Implicaciones para seguridad de la información:**\n"
            response += "• **Principio de legalidad**: Base legal para el procesamiento\n"
            response += "• **Principio de finalidad**: Limitación del uso de datos\n"
            response += "• **Principio de proporcionalidad**: Minimización de datos\n"
            response += "• **Principio de seguridad**: Protección técnica y organizacional\n"
            
            return response
        
        return "No encontré principios específicos de tratamiento en el documento consultado."
    
    def _explain_data_protection_security_connection(self, user_query: str, sources: List[Dict]) -> str:
        """Explicar la conexión general entre protección de datos y seguridad"""
        
        doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa de protección de datos"
        
        response = f"**¿Cómo se relaciona {doc_name} con seguridad de la información?**\n\n"
        
        response += "**🔗 Conexiones fundamentales:**\n\n"
        
        response += "**1. Control de acceso y autorización:**\n"
        response += "• La autorización del titular equivale a un control de acceso\n"
        response += "• Los derechos ARCO (Acceso, Rectificación, Cancelación, Oposición) son controles de datos\n\n"
        
        response += "**2. Clasificación y manejo de información:**\n"
        response += "• Datos sensibles requieren controles adicionales de seguridad\n"
        response += "• Datos públicos, semiprivados y privados tienen diferentes niveles de protección\n\n"
        
        response += "**3. Controles técnicos y organizacionales:**\n"
        response += "• Políticas de tratamiento = Políticas de seguridad de datos\n"
        response += "• Medidas de seguridad para impedir alteración, pérdida o acceso no autorizado\n\n"
        
        response += "**4. Auditoría y trazabilidad:**\n"
        response += "• Registro de tratamientos y accesos\n"
        response += "• Demostración de cumplimiento (accountability)\n\n"
        
        response += "**5. Gestión de incidentes:**\n"
        response += "• Notificación de violaciones de seguridad\n"
        response += "• Procedimientos de respuesta ante incidentes\n\n"
        
        response += f"**📋 Para consultas específicas sobre {doc_name.lower()}:**\n"
        response += "• ¿Cuáles son las obligaciones del responsable?\n"
        response += "• ¿Qué medidas de seguridad se requieren?\n"
        response += "• ¿Cómo manejar datos sensibles?\n"
        response += "• ¿Qué hacer en caso de violación de datos?\n"
        
        return response
    
    def _extract_authorization_controls(self, context: str, sources: List[Dict]) -> str:
        """Extraer información sobre autorización como control de acceso"""
        
        lines = context.split('\n')
        auth_info = []
        
        # Buscar información sobre autorización
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(term in line_lower for term in ['autorización', 'consentimiento', 'solicitar', 'obtener']):
                if any(term in line_lower for term in ['titular', 'tratamiento', 'datos']):
                    # Extraer contexto
                    context_lines = []
                    for j in range(max(0, i-1), min(len(lines), i+5)):
                        if lines[j].strip():
                            context_lines.append(lines[j].strip())
                    
                    if context_lines:
                        section_text = ' '.join(context_lines)
                        if len(section_text) > 100:
                            auth_info.append(section_text)
                            if len(auth_info) >= 2:
                                break
        
        if auth_info:
            doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa"
            
            response = f"**Obtención de autorización según {doc_name}:**\n\n"
            
            for i, info in enumerate(auth_info, 1):
                info = re.sub(r'\s+', ' ', info)
                response += f"**{i}.** {info[:1500]}...\n\n"
            
            response += "**🔐 Controles de seguridad relacionados:**\n"
            response += "• **Control de acceso**: La autorización del titular funciona como control de acceso\n"
            response += "• **Gestión de identidades**: Verificar identidad del titular antes de procesar\n"
            response += "• **Registro de actividades**: Documentar autorizaciones otorgadas\n"
            response += "• **Revisión periódica**: Verificar vigencia de autorizaciones\n"
            
            return response
        
        return "No encontré información específica sobre obtención de autorización en el documento."
    
    def _extract_policy_requirements(self, context: str, sources: List[Dict]) -> str:
        """Extraer requisitos de políticas de tratamiento"""
        
        lines = context.split('\n')
        policy_info = []
        
        # Buscar información sobre políticas
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(term in line_lower for term in ['política', 'manual', 'procedimiento']) and 'tratamiento' in line_lower:
                # Extraer contexto
                context_lines = []
                for j in range(max(0, i-1), min(len(lines), i+8)):
                    if lines[j].strip():
                        context_lines.append(lines[j].strip())
                
                if context_lines:
                    section_text = ' '.join(context_lines)
                    if len(section_text) > 100:
                        policy_info.append(section_text)
                        if len(policy_info) >= 2:
                            break
        
        if policy_info:
            doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa"
            
            response = f"**Políticas de tratamiento según {doc_name}:**\n\n"
            
            for i, info in enumerate(policy_info, 1):
                info = re.sub(r'\s+', ' ', info)
                response += f"**{i}.** {info[:1500]}...\n\n"
            
            response += "**📋 Equivalencia con documentación de seguridad:**\n"
            response += "• **Políticas de tratamiento** = Políticas de seguridad de datos\n"
            response += "• **Procedimientos** = Procedimientos operativos estándar (SOP)\n"
            response += "• **Manual interno** = Manual de seguridad de la información\n"
            response += "• **Consultas y reclamos** = Gestión de incidentes de datos\n"
            
            return response
        
        return "No encontré información específica sobre políticas de tratamiento en el documento."
    
    def _extract_data_subject_rights(self, context: str, sources: List[Dict]) -> str:
        """Extraer información sobre habeas data y derechos del titular"""
        
        lines = context.split('\n')
        rights_info = []
        
        # Buscar información sobre habeas data
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if 'habeas data' in line_lower or ('derecho' in line_lower and 'titular' in line_lower):
                # Extraer contexto
                context_lines = []
                for j in range(max(0, i-1), min(len(lines), i+5)):
                    if lines[j].strip():
                        context_lines.append(lines[j].strip())
                
                if context_lines:
                    section_text = ' '.join(context_lines)
                    if len(section_text) > 50:
                        rights_info.append(section_text)
                        if len(rights_info) >= 3:
                            break
        
        if rights_info:
            doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa"
            
            response = f"**Habeas data y derechos del titular según {doc_name}:**\n\n"
            
            for i, info in enumerate(rights_info, 1):
                info = re.sub(r'\s+', ' ', info)
                response += f"**{i}.** {info[:250]}...\n\n"
            
            response += "**🔐 Controles ARCO (Acceso, Rectificación, Cancelación, Oposición):**\n"
            response += "• **Acceso**: Derecho a consultar qué datos se procesan\n"
            response += "• **Rectificación**: Derecho a corregir datos inexactos\n"
            response += "• **Cancelación**: Derecho a eliminar datos innecesarios\n"
            response += "• **Oposición**: Derecho a objetar el procesamiento\n\n"
            
            response += "**📋 Implementación en SGSI:**\n"
            response += "• Procedimientos de atención de solicitudes\n"
            response += "• Registros de acceso a datos personales\n"
            response += "• Controles de modificación y eliminación\n"
            
            return response
        
        return "No encontré información específica sobre habeas data en el documento."
    
    def _extract_transfer_controls(self, context: str, sources: List[Dict]) -> str:
        """Extraer información sobre transferencias internacionales"""
        
        lines = context.split('\n')
        transfer_info = []
        
        # Buscar información sobre transferencias
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(term in line_lower for term in ['transferencia', 'transmisión']) and ('datos' in line_lower or 'internacional' in line_lower):
                # Extraer contexto amplio
                context_lines = []
                for j in range(max(0, i-1), min(len(lines), i+6)):
                    if lines[j].strip():
                        context_lines.append(lines[j].strip())
                
                if context_lines:
                    section_text = ' '.join(context_lines)
                    if len(section_text) > 100:
                        transfer_info.append(section_text)
                        if len(transfer_info) >= 2:
                            break
        
        if transfer_info:
            doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa"
            
            response = f"**Transferencias internacionales según {doc_name}:**\n\n"
            
            for i, info in enumerate(transfer_info, 1):
                info = re.sub(r'\s+', ' ', info)
                response += f"**{i}.** {info[:1500]}...\n\n"
            
            response += "**🌐 Controles de transferencia internacional:**\n"
            response += "• **Evaluación de destino**: Verificar nivel de protección del país receptor\n"
            response += "• **Contratos de transferencia**: Cláusulas contractuales de protección\n"
            response += "• **Autorización previa**: Consentimiento del titular para transferencia\n"
            response += "• **Registro de transferencias**: Documentar todas las transferencias realizadas\n"
            
            return response
        
        return "No encontré información específica sobre transferencias internacionales en el documento."
    
    def _extract_minors_data_protection(self, context: str, sources: List[Dict]) -> str:
        """Extraer información sobre protección de datos de menores"""
        
        lines = context.split('\n')
        minors_info = []
        
        # Buscar información sobre menores
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(term in line_lower for term in ['menores', 'niños', 'adolescentes']) or 'menor de edad' in line_lower:
                # Extraer contexto amplio
                context_lines = []
                for j in range(max(0, i-2), min(len(lines), i+8)):
                    if lines[j].strip():
                        context_lines.append(lines[j].strip())
                
                if context_lines:
                    section_text = ' '.join(context_lines)
                    if len(section_text) > 150:
                        minors_info.append(section_text)
                        break
        
        if minors_info:
            doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa"
            
            response = f"**Tratamiento de datos de menores según {doc_name}:**\n\n"
            
            for info in minors_info:
                info = re.sub(r'\s+', ' ', info)
                response += f'"{info[:2000]}..."\n\n'
            
            response += "**👶 Controles especiales para menores:**\n"
            response += "• **Consentimiento parental**: Autorización del representante legal\n"
            response += "• **Verificación de edad**: Controles para identificar menores\n"
            response += "• **Interés superior**: Priorizar bienestar del menor\n"
            response += "• **Limitaciones de uso**: Restricciones en el procesamiento\n"
            
            return response
        
        return "No encontré información específica sobre tratamiento de datos de menores en el documento."
    
    def _extract_surveillance_requirements(self, context: str, sources: List[Dict]) -> str:
        """Extraer información sobre videovigilancia"""
        
        # La videovigilancia generalmente no está en Ley 1581 básica, pero podemos inferir controles
        doc_name = f"{sources[0]['tipo_norma']} {sources[0]['numero']} de {sources[0]['año']}" if sources else "la normativa de protección de datos"
        
        response = f"**Videovigilancia y {doc_name}:**\n\n"
        
        response += "**📹 Aplicación de principios de protección de datos:**\n\n"
        
        response += "**1. Finalidad específica:**\n"
        response += "• La videovigilancia debe tener una finalidad legítima definida\n"
        response += "• Seguridad de personas, bienes o instalaciones\n\n"
        
        response += "**2. Proporcionalidad:**\n"
        response += "• Las cámaras solo deben capturar lo necesario\n"
        response += "• Evitar espacios privados (baños, vestuarios)\n\n"
        
        response += "**3. Información al titular:**\n"
        response += "• Avisos visibles de videovigilancia\n"
        response += "• Identificación del responsable del tratamiento\n\n"
        
        response += "**4. Derechos del titular:**\n"
        response += "• Derecho de acceso a las imágenes donde aparezca\n"
        response += "• Derecho de supresión cuando no sean necesarias\n\n"
        
        response += "**🔐 Controles técnicos recomendados:**\n"
        response += "• **Cifrado** de grabaciones almacenadas\n"
        response += "• **Control de acceso** a sistemas de videovigilancia\n"
        response += "• **Registro de accesos** a las grabaciones\n"
        response += "• **Retención limitada** según finalidad\n"
        
        response += f"\n**📖 Fuente:** Aplicación de principios de {doc_name.lower()}"
        
        return response