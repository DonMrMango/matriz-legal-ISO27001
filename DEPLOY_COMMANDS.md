# 🚀 Comandos para Crear Repositorio y Desplegar

## Paso 1: Inicializar Repositorio Git

Ejecuta estos comandos en terminal desde el directorio del proyecto:

```bash
# Navegar al directorio del proyecto
cd ~/Desktop/matriz-legal-ISO27001

# Inicializar repositorio Git
git init

# Agregar todos los archivos
git add .

# Crear primer commit
git commit -m "🚀 Initial commit: Matriz Legal ISO27001 - Plataforma de normatividad colombiana

✅ 24 normas procesadas (Leyes, Decretos, Resoluciones, Circulares)
✅ Dashboard interactivo con métricas
✅ Chatbot legal con IA (Groq + Qwen)
✅ Política de datos conforme Ley 1581/2012
✅ Seguridad profesional (API keys protegidas)

🔧 Stack: Python Flask + Alpine.js + Tailwind CSS
👨‍💻 Por: Daniel Alejandro Mejía (C.C. 1.053.854.091)"

# Crear branch main
git branch -M main
```

## Paso 2: Crear Repositorio en GitHub

1. **Ve a GitHub.com** y haz clic en "New repository"
2. **Nombre:** `matriz-legal-ISO27001`
3. **Descripción:** `Plataforma web profesional para consulta de normatividad colombiana ISO 27001`
4. **Público/Privado:** Tu elección
5. **NO inicializar** con README (ya tenemos uno)
6. **Crear repositorio**

## Paso 3: Conectar con GitHub

```bash
# Agregar origen remoto (REEMPLAZA 'tu-usuario' con tu usuario de GitHub)
git remote add origin https://github.com/tu-usuario/matriz-legal-ISO27001.git

# Subir al repositorio
git push -u origin main
```

## Paso 4: Desplegar en Vercel

1. **Ve a [vercel.com](https://vercel.com)** e inicia sesión
2. **Clic en "New Project"**
3. **Importar desde GitHub:** Selecciona `matriz-legal-ISO27001`
4. **Framework Preset:** Other
5. **Root Directory:** . (punto)
6. **Build Command:** (dejar vacío)
7. **Output Directory:** (dejar vacío)

## Paso 5: Configurar Variables de Entorno en Vercel

En la sección "Environment Variables" agrega:

```
Name: GROQ_API_KEY
Value: [INGRESA_TU_GROQ_API_KEY_AQUI]

Name: FLASK_ENV  
Value: production

Name: OPENAI_API_KEY
Value: [INGRESA_TU_QWEN_KEY_AQUI] (opcional)

Name: OPENAI_BASE_URL
Value: https://dashscope-intl.aliyuncs.com/compatible-mode/v1

Name: OPENAI_MODEL
Value: qwen-max
```

## Paso 6: Deploy

1. **Clic en "Deploy"**
2. **Esperar 2-3 minutos**
3. **¡Listo!** Tu app estará en `https://tu-proyecto.vercel.app`

---

## 🎯 Resultado Final

Tu plataforma estará disponible públicamente con:
- ✅ **URL profesional** de Vercel
- ✅ **SSL automático** (HTTPS)
- ✅ **CDN global** para velocidad
- ✅ **Escalabilidad automática**
- ✅ **24 normas** funcionando
- ✅ **Chatbot IA** activo
- ✅ **Política de datos** integrada

## 🔄 Actualizaciones Futuras

Para actualizar la aplicación:

```bash
# Hacer cambios en el código
# Commit y push
git add .
git commit -m "📝 Descripción de cambios"
git push

# Vercel autodespliega automáticamente
```

**¡Todo listo para impresionar a los ingenieros!** 🚀