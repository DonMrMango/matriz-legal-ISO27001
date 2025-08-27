# Integración de Chatbot ISO 27001/27002

Este documento describe la integración del Chatbot ISO 27001/27002 con el repositorio de Matriz Legal para ofrecer una plataforma completa de consulta normativa.

## Descripción general

La integración añade un chatbot especializado en ISO 27001/27002 a la plataforma existente de Matriz Legal, permitiendo:

- Consultas interactivas sobre controles de seguridad ISO 27001/27002
- Identificación de controles específicos por código o temática
- Búsqueda semántica en el texto completo de los estándares
- Interfaz web dedicada y accesible desde la página principal

## Archivos modificados/añadidos

### Endpoints API
- **api/iso_chat.py**: Módulo principal del chatbot ISO (backend)
- **api/iso_endpoint.py**: Integración con la API existente
- **api/index.py**: Modificado para incorporar endpoints ISO

### Interfaz web
- **templates/iso_chatbot.html**: Interfaz dedicada al chatbot ISO
- **static/iso_script.js**: Lógica de cliente para el chatbot ISO
- **index_modified.html**: Versión actualizada de la página principal con enlaces al chatbot ISO

### Configuración Vercel
- **vercel.json**: Actualizado para incluir rutas ISO y configuración
- **vercel_build.sh**: Script para preparar BD_ISO.txt durante el despliegue

## Requisitos

1. Archivo **BD_ISO.txt** con el contenido de la normativa ISO 27001/27002
2. API key de Groq configurada en las variables de entorno de Vercel
3. Acceso a la API de Groq para consultas LLM

## Estructura de rutas

- `/`: Página principal (con enlace al chatbot ISO)
- `/iso`: Chatbot ISO 27001/27002
- `/api/iso/chat`: Endpoint para consultas ISO
- `/api/iso/status`: Endpoint para verificar estado del chatbot ISO

## Uso del chatbot

1. Accede a la página principal y haz clic en "Chatbot ISO 27001/27002"
2. Escribe consultas como:
   - "¿Qué es el control 5.23 de ISO 27002?"
   - "Háblame sobre la protección de datos en ISO 27002"
   - "Explica el enmascaramiento de datos"
   - "¿Cuáles son los controles de seguridad física?"
3. El chatbot utilizará el contexto ISO para responder a tus preguntas
4. Puedes ver el contexto completo utilizado haciendo clic en "Ver contexto completo"

## Implementación técnica

- **Motor IA**: Utiliza Groq con modelo Llama 3.1 8B Instant
- **Contexto**: Carga el archivo BD_ISO.txt completo (se utiliza búsqueda semántica para encontrar información relevante)
- **API**: Endpoints RESTful integrados con la API existente
- **Interfaz**: Diseño responsive compatible con móviles y escritorio

## Configuración en Vercel

Después de desplegar:

1. Añadir la variable de entorno `GROQ_API_KEY` en la configuración de Vercel
2. Verificar que el archivo BD_ISO.txt se copió correctamente durante el despliegue (usando vercel_build.sh)
3. Comprobar el correcto funcionamiento accediendo a `/api/iso/status`

## Troubleshooting

Si el chatbot ISO no funciona correctamente:

1. **Verificar archivo BD_ISO.txt**:
   - Debe estar en la raíz del proyecto
   - Debe contener el texto completo de ISO 27001/27002

2. **Verificar API key de Groq**:
   - Configurada en variables de entorno de Vercel

3. **Verificar logs de Vercel**:
   - Cualquier error en la inicialización será visible en los logs

4. **Probar endpoint de estado**:
   - Visitar `/api/iso/status` para verificar carga del contexto