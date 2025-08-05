# 📊 Sistema de Monitoreo y Analytics - Matriz Legal INSOFT

## 🎯 Implementación Completa

Se ha implementado un sistema completo de monitoreo y analytics para administrador que incluye:

### ✅ Componentes Implementados

1. **Panel de Administrador** (`/admin`)
   - Dashboard en tiempo real con métricas clave
   - Autenticación segura con token
   - Gráficos interactivos con Chart.js
   - Interfaz dark theme profesional

2. **Tracking Automático de Sesiones**
   - IP, timestamp, user agent
   - Duración de sesiones
   - Páginas vistas por sesión
   - Actividad en tiempo real

3. **Monitoreo de Tokens y Performance**
   - Consumo de tokens Groq API por consulta
   - Tiempo de respuesta por endpoint
   - Métricas de rendimiento detalladas
   - Análisis de carga del sistema

4. **Estadísticas de Uso Completas**
   - Picos de tráfico por hora
   - Documentos más consultados
   - Tipos de consultas más frecuentes
   - Análisis de patrones de uso

5. **Sistema de Logging sin Datos Personales**
   - NO guarda preguntas específicas (privacidad)
   - Solo metadata: tipo, longitud, tiempo, documentos encontrados
   - Cumple con regulaciones de privacidad

6. **Base de Datos Analytics**
   - 5 tablas especializadas en SQLite
   - Queries optimizadas para reportes
   - Retención configurable de datos

## 🚀 Cómo Usar el Sistema

### 1. Iniciar el Servidor

```bash
cd /Users/damo/Desktop/matriz-legal-ISO27001
python api/index.py
```

El servidor iniciará en `http://localhost:5002`

### 2. Acceder al Panel de Administrador

1. Abrir navegador en: `http://localhost:5002/admin`
2. Usar token de acceso: `admin_daniel_2024`
3. Explorar las métricas en tiempo real

### 3. APIs de Analytics Disponibles

Todas requieren header: `Authorization: Bearer admin_daniel_2024`

- **Resumen General**: `GET /api/admin/analytics/overview?hours=24`
- **Sesiones**: `GET /api/admin/analytics/sessions?hours=24`
- **Performance**: `GET /api/admin/analytics/performance?hours=24`
- **Chat Analytics**: `GET /api/admin/analytics/chat?hours=24`
- **Documentos**: `GET /api/admin/analytics/documents?hours=24`
- **Tiempo Real**: `GET /api/admin/analytics/realtime`

## 📈 Métricas Disponibles

### Dashboard Principal
- **Sesiones Activas**: Usuarios activos en últimos 5 minutos
- **Consultas Recientes**: Queries de chat en tiempo real
- **Vistas de Página**: Accesos a documentos y endpoints
- **Tiempo de Respuesta**: Performance promedio del sistema

### Análisis Detallado
- **Sesiones por Hora**: Gráfico de tráfico temporal
- **Consultas Chat**: Análisis de uso del chatbot
- **Documentos Populares**: Ranking de contenido más consultado
- **Performance por Endpoint**: Métricas de rendimiento
- **Tipos de Consultas**: Categorización automática de queries

### Tiempo Real
- **Actividad en Vivo**: Stream de acciones de usuarios
- **Usuarios Activos**: Conteo de sesiones actuales
- **Alertas de Performance**: Monitoreo de respuesta lenta

## 🔧 Configuración

### Variables de Entorno (.env)
```bash
ADMIN_TOKEN=admin_daniel_2024
GROQ_API_KEY=tu_api_key_aqui
OPENAI_API_KEY=tu_openai_key_aqui
```

### Tablas de Base de Datos
- `analytics_sessions`: Sesiones de usuario
- `analytics_page_views`: Vistas de página/endpoint
- `analytics_chat_queries`: Consultas de chat (SIN contenido)
- `analytics_document_access`: Acceso a documentos
- `analytics_system_metrics`: Métricas del sistema

## 🛡️ Privacidad y Seguridad

### ✅ Protección de Datos
- **NO se almacenan preguntas específicas**
- Solo metadata: longitud, tipo, tiempo de respuesta
- IPs hasheadas para análisis de patrones
- Cumplimiento con regulaciones de privacidad

### 🔐 Seguridad
- Autenticación con token para admin
- CORS configurado para dominios específicos
- Headers de seguridad implementados
- Rate limiting por sesión

## 📊 Casos de Uso

### Para Daniel (Administrador)
1. **Monitoreo Diario**: Revisar dashboard cada mañana
2. **Análisis Semanal**: Identificar patrones de uso
3. **Optimización**: Mejorar documentos más consultados
4. **Alertas**: Detectar problemas de performance
5. **Reportes**: Generar estadísticas de uso

### Métricas Clave a Monitorear
- **Sesiones/día**: Indicador de adopción
- **Tiempo de respuesta**: Performance del sistema
- **Documentos populares**: Contenido más valioso
- **Tipos de consultas**: Necesidades de usuarios
- **Picos de tráfico**: Planificación de recursos

## 🔄 Mantenimiento

### Limpieza de Datos
- Los datos se acumulan automáticamente
- Recomendado: limpiar datos > 6 meses
- Script de limpieza disponible si necesario

### Respaldos
- La base de datos SQLite es un solo archivo
- Respaldar `data_repository/repositorio.db` regularmente
- Exportar métricas importantes antes de limpiar

## 🎯 Próximos Pasos

### Mejoras Futuras Sugeridas
1. **Alertas Automáticas**: Email/Slack cuando hay problemas
2. **Reportes PDF**: Generar reportes automáticos semanales
3. **Dashboard Móvil**: Versión responsive optimizada
4. **Machine Learning**: Predicción de patrones de uso

### Integración Vercel
- Sistema compatible con Vercel
- Variables de entorno configurables
- Logging optimizado para serverless

## 🆘 Soporte

### Problemas Comunes
1. **Server no inicia**: Verificar puerto 5002 libre
2. **Token inválido**: Revisar ADMIN_TOKEN en .env
3. **Sin datos**: Generar actividad primero con usuarios reales

### Testing
```bash
python test_analytics.py
```

## 📧 Contacto
Para soporte técnico o mejoras, contactar al desarrollador del sistema.

---

**✅ SISTEMA LISTO PARA PRODUCCIÓN**

Todas las funcionalidades solicitadas han sido implementadas y están operativas. El sistema está listo para monitorear el uso de la plataforma desde hoy mismo.