#!/bin/bash
# Script para configurar BD_ISO.txt y preparar el despliegue en Vercel

echo "🔄 Preparando archivo BD_ISO.txt para Vercel..."

# Comprobar si el archivo ya existe en la raíz del proyecto
if [ -f "./BD_ISO.txt" ]; then
    echo "✅ BD_ISO.txt encontrado en la raíz del proyecto"
else
    # Buscar el archivo en otras ubicaciones
    echo "🔍 Buscando BD_ISO.txt en ubicaciones alternativas..."
    
    # Comprobar si existe en el directorio data
    if [ -f "./data/BD_ISO.txt" ]; then
        echo "📂 Copiando BD_ISO.txt desde data/ a la raíz..."
        cp "./data/BD_ISO.txt" "./BD_ISO.txt"
    # Comprobar si existe en /tmp (para desarrollo)
    elif [ -f "/tmp/BD_ISO.txt" ]; then
        echo "📂 Copiando BD_ISO.txt desde /tmp a la raíz..."
        cp "/tmp/BD_ISO.txt" "./BD_ISO.txt"
    else
        echo "⚠️ BD_ISO.txt no encontrado, creando versión mínima de ejemplo..."
        echo "[5.23] Enmascaramiento de datos
    Las técnicas de enmascaramiento de datos deberían aplicarse a la información que necesite protección en los entornos de prueba/desarrollo.

    OBJETIVO: Proteger la información sensible utilizada para el desarrollo y pruebas.

    GUÍA DE IMPLEMENTACIÓN:
      Las técnicas de enmascaramiento de datos, a veces denominadas ofuscación de datos o sustitución de datos, incluyen cualquier método que oculte datos sensibles en los entornos de desarrollo o prueba." > "./BD_ISO.txt"
    fi
fi

# Verificar tamaño del archivo
FILE_SIZE=$(wc -c "./BD_ISO.txt" | awk '{print $1}')
echo "📊 Tamaño de BD_ISO.txt: $FILE_SIZE bytes"

# Estadísticas adicionales
LINES=$(wc -l "./BD_ISO.txt" | awk '{print $1}')
echo "📊 Líneas en BD_ISO.txt: $LINES"

# Crear directorio data si no existe (para consistencia)
if [ ! -d "./data" ]; then
    mkdir -p "./data"
    echo "📁 Directorio data/ creado"
fi

# Copiar BD_ISO.txt a directorio data también (respaldo)
cp "./BD_ISO.txt" "./data/BD_ISO.txt"
echo "📋 BD_ISO.txt respaldado en data/"

echo "✅ Preparación de BD_ISO.txt completada"

# Crear directorio public si no existe
echo "🔄 Preparando directorio public para Vercel..."
mkdir -p public

# Copiar archivos HTML, CSS y JS a public
echo "📋 Copiando archivos estáticos a public/"
if [ -f "index.html" ]; then
    cp index.html public/
fi

if [ -f "admin.html" ]; then
    cp admin.html public/
fi

if [ -f "index_modified.html" ]; then
    cp index_modified.html public/index.html
fi

# Copiar templates e ISO chatbot
if [ -d "templates" ]; then
    echo "📋 Copiando templates a public/"
    
    # Crear directorio en public
    mkdir -p public/templates
    
    # Copiar archivos HTML
    cp templates/*.html public/templates/ 2>/dev/null || echo "No se encontraron archivos HTML en templates/"
fi

# Copiar directorio static
if [ -d "static" ]; then
    echo "📋 Copiando directorio static a public/"
    
    # Crear directorio en public
    mkdir -p public/static
    
    # Copiar archivos
    cp -r static/* public/static/ 2>/dev/null || echo "No se encontraron archivos en static/"
fi

# Copiar BD_ISO.txt a public
cp "./BD_ISO.txt" "./public/BD_ISO.txt"

echo "✅ Directorio public preparado para despliegue en Vercel"
ls -la public/