#!/usr/bin/env python3
"""
Dual-Architecture API server for Matriz Legal INSOFT
🔄 DUAL SYSTEM:
  📊 SQLite Database → Chatbot queries & metadata 
  📄 Text Files + Groq AI → Visual interface & formatting
Best of both worlds: reliability + optimal presentation
"""

import sqlite3
import json
import os
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Try to import custom modules with error handling - Vercel compatible
import sys
import os

# Add current directory to path for Vercel compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add parent directory for local development
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from text_library import TextLegalLibrary
    TEXT_LIBRARY_AVAILABLE = True
    print("✅ text_library imported successfully")
except Exception as e:
    print(f"Warning: Could not import text_library: {e}")
    TEXT_LIBRARY_AVAILABLE = False
    TextLegalLibrary = None

try:
    from qwen_formatter import QwenLegalFormatter, process_document_with_qwen
    QWEN_FORMATTER_AVAILABLE = True
    print("✅ qwen_formatter imported successfully")
except Exception as e:
    print(f"Warning: Could not import qwen_formatter: {e}")
    QWEN_FORMATTER_AVAILABLE = False
    QwenLegalFormatter = None
    process_document_with_qwen = None

app = Flask(__name__)

# Configure CORS securely
if os.getenv('VERCEL_ENV') == 'production' or os.getenv('FLASK_ENV') == 'production':
    # Production: only allow specific origins
    CORS(app, origins=[
        "https://matriz-legal-iso-27001.vercel.app",
        "https://matriz-legal-iso-27001-*.vercel.app"
    ])
else:
    # Development: allow localhost and any Vercel preview
    CORS(app, origins=[
        "http://localhost:*", 
        "http://127.0.0.1:*",
        "https://matriz-legal-iso-27001-*.vercel.app"
    ])

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# 🔄 DUAL ARCHITECTURE SETUP - Vercel compatible paths
# Database for chatbot queries & reliable metadata
api_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(api_dir)

DB_PATH = os.path.join(project_root, 'data_repository', 'repositorio.db')
TEXTS_PATH = os.path.join(project_root, 'data_repository', 'textos_limpios_seguro')

print(f"🔍 Path Configuration:")
print(f"   API dir: {api_dir}")
print(f"   Project root: {project_root}")
print(f"   DB path: {DB_PATH}")
print(f"   Texts path: {TEXTS_PATH}")
print(f"   DB exists: {os.path.exists(DB_PATH)}")
print(f"   Texts exists: {os.path.exists(TEXTS_PATH)}")

def get_db_connection():
    """Get database connection for metadata queries - VERCEL COMPATIBLE"""
    try:
        # Try primary path
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        
        # Try alternative paths for Vercel
        alternative_paths = [
            os.path.join(os.getcwd(), 'data_repository', 'repositorio.db'),
            os.path.join(os.path.dirname(__file__), 'data_repository', 'repositorio.db'),
            os.path.join('/', 'var', 'task', 'data_repository', 'repositorio.db'),
            './data_repository/repositorio.db'
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                print(f"Using alternative DB path: {alt_path}")
                conn = sqlite3.connect(alt_path)
                conn.row_factory = sqlite3.Row
                return conn
        
        # If no database found, raise an exception
        raise FileNotFoundError(f"Database not found. Tried paths: {[DB_PATH] + alternative_paths}")
        
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise

# Text library for visual interface
if TEXT_LIBRARY_AVAILABLE:
    try:
        library = TextLegalLibrary(texts_path=TEXTS_PATH)
        # Clear cache to force recalculation of titles with new logic
        library.clear_cache()
        print(f"✅ TextLegalLibrary initialized with {len(library.get_all_documents())} documents")
    except Exception as e:
        print(f"❌ Error initializing TextLegalLibrary: {e}")
        import traceback
        traceback.print_exc()
        library = None
else:
    library = None

# Initialize Qwen formatter for AI-powered text formatting (only if API key available)
if QWEN_FORMATTER_AVAILABLE and os.getenv('OPENAI_API_KEY'):
    try:
        formatter = QwenLegalFormatter()
        QWEN_AVAILABLE = True
        print("✅ Qwen AI formatter initialized - Enhanced text formatting with complete metadata extraction")
    except Exception as e:
        formatter = None
        QWEN_AVAILABLE = False
        print(f"⚠️  Qwen initialization failed: {e}")
else:
    formatter = None
    QWEN_AVAILABLE = False
    if not QWEN_FORMATTER_AVAILABLE:
        print("⚠️  Qwen formatter module not available")
    elif not os.getenv('OPENAI_API_KEY'):
        print("💡 Set OPENAI_API_KEY environment variable to enable AI formatting")

print(f"🔄 DUAL SYSTEM ACTIVE:")
print(f"  📊 Database: {DB_PATH}")
print(f"  📄 Text Files: {TEXTS_PATH}")
print(f"  🤖 AI Formatting: {'✅ Available' if QWEN_AVAILABLE else '❌ Disabled'}")

@app.route('/api/test')
def test():
    """Test endpoint to check what's working"""
    # Test database connection
    db_status = 'unknown'
    db_error = None
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT COUNT(*) as count FROM textos_repositorio")
        db_count = cursor.fetchone()['count']
        conn.close()
        db_status = f'working ({db_count} docs)'
    except Exception as e:
        db_status = 'failed'
        db_error = str(e)
    
    # Test text files
    text_files_count = 0
    text_files_status = 'unknown'
    try:
        if os.path.exists(TEXTS_PATH):
            for folder in ['leyes', 'decretos', 'circulares', 'resoluciones', 'conpes', 'otros']:
                folder_path = os.path.join(TEXTS_PATH, folder)
                if os.path.exists(folder_path):
                    text_files_count += len([f for f in os.listdir(folder_path) if f.endswith('.txt')])
            text_files_status = f'working ({text_files_count} files)'
        else:
            text_files_status = 'path not found'
    except Exception as e:
        text_files_status = f'failed: {str(e)}'
    
    return jsonify({
        'status': 'ok',
        'environment': {
            'vercel_env': os.getenv('VERCEL_ENV', 'not set'),
            'flask_env': os.getenv('FLASK_ENV', 'not set'),
            'cwd': os.getcwd(),
            'api_dir': os.path.dirname(__file__)
        },
        'components': {
            'text_library': TEXT_LIBRARY_AVAILABLE,
            'qwen_formatter': QWEN_FORMATTER_AVAILABLE,
            'library_initialized': library is not None,
            'formatter_initialized': 'formatter' in globals() and formatter is not None
        },
        'database': {
            'status': db_status,
            'path': DB_PATH,
            'exists': os.path.exists(DB_PATH),
            'error': db_error
        },
        'text_files': {
            'status': text_files_status,
            'path': TEXTS_PATH,
            'exists': os.path.exists(TEXTS_PATH),
            'count': text_files_count
        }
    })

@app.route('/api/documents', methods=['GET'])
def get_documents():
    """📄 Get documents using TEXT LIBRARY for complete file access"""
    try:
        # Check if library is available
        if not library:
            return jsonify({
                'success': False,
                'error': 'Text library not initialized',
                'documents': []
            }), 500
            
        # Get all documents from text library
        all_documents = library.get_all_documents()
        
        # Apply filters
        filtered_docs = all_documents
        
        # Filter by type
        if request.args.get('tipo'):
            filtered_docs = [doc for doc in filtered_docs 
                           if doc.get('tipo_norma') == request.args.get('tipo')]
        
        # Filter by year
        if request.args.get('año'):
            year = int(request.args.get('año'))
            filtered_docs = [doc for doc in filtered_docs 
                           if doc.get('año') == year]
        
        # Search in title
        if request.args.get('search'):
            search_term = request.args.get('search').lower()
            filtered_docs = [doc for doc in filtered_docs 
                           if search_term in doc.get('titulo', '').lower()]
        
        return jsonify({
            'success': True,
            'data': filtered_docs,
            'count': len(filtered_docs),
            'total_available': len(all_documents),
            'source': 'text_files',
            'architecture': 'file_based'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/documents/<document_id>', methods=['GET'])
def get_document(document_id):
    """📊 Get document metadata using DATABASE"""
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT * FROM textos_repositorio WHERE nombre_archivo = ?", 
            (document_id,)
        )
        document = cursor.fetchone()
        conn.close()
        
        if not document:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': dict(document),
            'source': 'database'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/documents/<document_id>/content', methods=['GET'])
def get_document_content(document_id):
    """📄 Get document content - VERCEL COMPATIBLE with fallback"""
    try:
        # SOLUTION 1: Try text files first (most reliable for Vercel)
        if library:
            content_result = library.get_document_content(document_id)
            
            if content_result['success']:
                raw_content = content_result['raw_content']
                document_title = content_result['title']
                document_type = content_result['type']
                
                # 📄 SIMPLE DISPLAY with basic formatting
                html_content = f'<div class="document-content"><pre style="white-space: pre-wrap; font-family: inherit; font-size: inherit;">{raw_content}</pre></div>'
                
                # Extract articles for navigation
                articles = extract_articles_simple(raw_content)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'titulo': document_title,
                        'contenido': html_content,
                        'articles': articles,
                        'raw_content': raw_content,
                        'word_count': len(raw_content.split()),
                        'formatting': 'basic',
                        'architecture': 'text_files_only',
                        'type': document_type
                    }
                })
        
        # SOLUTION 2: Fallback to database (if available and working)
        try:
            conn = get_db_connection()
            cursor = conn.execute(
                "SELECT tipo_norma, titulo FROM textos_repositorio WHERE nombre_archivo = ?", 
                (document_id,)
            )
            db_document = cursor.fetchone()
            conn.close()
            
            if db_document and library:
                # Try to get content from files again with DB metadata
                content_result = library.get_document_content(document_id)
                if content_result['success']:
                    raw_content = content_result['raw_content']
                    document_title = db_document['titulo']  # Use DB title
                    
                    html_content = f'<div class="document-content"><pre style="white-space: pre-wrap; font-family: inherit; font-size: inherit;">{raw_content}</pre></div>'
                    articles = extract_articles_simple(raw_content)
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'titulo': document_title,
                            'contenido': html_content,
                            'articles': articles,
                            'raw_content': raw_content,
                            'word_count': len(raw_content.split()),
                            'formatting': 'basic',
                            'architecture': 'dual_system'
                        }
                    })
        except Exception as db_error:
            print(f"Database fallback failed: {db_error}")
            # Continue to final fallback
        
        # SOLUTION 3: Direct file system access (emergency fallback)
        try:
            # Try to find file directly in filesystem
            for folder in ['leyes', 'decretos', 'circulares', 'resoluciones', 'conpes', 'otros']:
                file_path = os.path.join(TEXTS_PATH, folder, f"{document_id}.txt")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    
                    # Basic title extraction
                    lines = raw_content.split('\n')[:10]
                    document_title = document_id.replace('_', ' ').title()
                    for line in lines:
                        if len(line.strip()) > 10 and any(word in line.upper() for word in ['LEY', 'DECRETO', 'CIRCULAR', 'RESOLUCIÓN', 'CONPES']):
                            document_title = line.strip()
                            break
                    
                    html_content = f'<div class="document-content"><pre style="white-space: pre-wrap; font-family: inherit; font-size: inherit;">{raw_content}</pre></div>'
                    articles = extract_articles_simple(raw_content)
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'titulo': document_title,
                            'contenido': html_content,
                            'articles': articles,
                            'raw_content': raw_content,
                            'word_count': len(raw_content.split()),
                            'formatting': 'basic',
                            'architecture': 'direct_filesystem'
                        }
                    })
        except Exception as fs_error:
            print(f"Direct filesystem access failed: {fs_error}")
        
        # Final error if all methods fail
        return jsonify({
            'success': False,
            'error': 'Document not found',
            'tried_methods': ['text_library', 'database_fallback', 'direct_filesystem']
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Content retrieval failed: {str(e)}",
            'debug_info': {
                'document_id': document_id,
                'library_available': library is not None,
                'texts_path_exists': os.path.exists(TEXTS_PATH),
                'db_path_exists': os.path.exists(DB_PATH)
            }
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_repository_stats():
    """Get repository statistics - VERCEL COMPATIBLE with fallback"""
    try:
        # Try database first
        try:
            conn = get_db_connection()
            
            # Total documents
            cursor = conn.execute("SELECT COUNT(*) as total FROM textos_repositorio")
            total = cursor.fetchone()['total']
            
            # Documents by type
            cursor = conn.execute("""
                SELECT tipo_norma, COUNT(*) as count 
                FROM textos_repositorio 
                GROUP BY tipo_norma
            """)
            by_type = {row['tipo_norma']: row['count'] for row in cursor.fetchall()}
            
            # Documents by year
            cursor = conn.execute("""
                SELECT año, COUNT(*) as count 
                FROM textos_repositorio 
                GROUP BY año 
                ORDER BY año
            """)
            by_year = {row['año']: row['count'] for row in cursor.fetchall()}
            
            conn.close()
            
            return jsonify({
                'success': True,
                'data': {
                    'total': total,
                    'by_type': by_type,
                    'by_year': by_year,
                    'procesadas': total,
                    'referencias': total * 2,
                    'source': 'database'
                }
            })
            
        except Exception as db_error:
            print(f"Database stats failed: {db_error}")
            
            # Fallback to text library
            if library:
                stats = library.get_library_stats()
                return jsonify({
                    'success': True,
                    'data': {
                        'total': stats['total_documents'],
                        'by_type': stats['by_type'],
                        'by_year': stats['by_year'],
                        'procesadas': stats['total_documents'],
                        'referencias': stats['total_documents'] * 2,
                        'source': 'text_files'
                    }
                })
            
            # Final fallback: count files directly
            total = 0
            by_type = {}
            for folder_name in ['leyes', 'decretos', 'circulares', 'resoluciones', 'conpes', 'otros']:
                folder_path = os.path.join(TEXTS_PATH, folder_name)
                if os.path.exists(folder_path):
                    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
                    count = len(txt_files)
                    total += count
                    by_type[folder_name.title()] = count
            
            return jsonify({
                'success': True,
                'data': {
                    'total': total,
                    'by_type': by_type,
                    'by_year': {},
                    'procesadas': total,
                    'referencias': total * 2,
                    'source': 'direct_filesystem'
                }
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search', methods=['GET'])
def search_documents():
    """Full-text search across documents - VERCEL COMPATIBLE"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Search query required'
        }), 400
    
    try:
        # Try database first
        try:
            conn = get_db_connection()
            
            # Search in title and load content for full-text search
            cursor = conn.execute("""
                SELECT * FROM textos_repositorio 
                WHERE titulo LIKE ? OR numero LIKE ?
            """, (f"%{query}%", f"%{query}%"))
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return jsonify({
                'success': True,
                'data': results,
                'query': query,
                'count': len(results),
                'source': 'database'
            })
            
        except Exception as db_error:
            print(f"Database search failed: {db_error}")
            
            # Fallback to text library search
            if library:
                results = library.search_documents(query)
                return jsonify({
                    'success': True,
                    'data': results,
                    'query': query,
                    'count': len(results),
                    'source': 'text_files'
                })
            
            # Final fallback: basic file search
            results = []
            query_lower = query.lower()
            
            for folder_name in ['leyes', 'decretos', 'circulares', 'resoluciones', 'conpes', 'otros']:
                folder_path = os.path.join(TEXTS_PATH, folder_name)
                if not os.path.exists(folder_path):
                    continue
                    
                for filename in os.listdir(folder_path):
                    if filename.endswith('.txt') and query_lower in filename.lower():
                        results.append({
                            'document_id': filename.replace('.txt', ''),
                            'titulo': filename.replace('_', ' ').title(),
                            'tipo_norma': folder_name.title(),
                            'match_type': 'filename'
                        })
            
            return jsonify({
                'success': True,
                'data': results[:20],  # Limit results
                'query': query,
                'count': len(results),
                'source': 'direct_filesystem'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def format_legal_text_basic(text):
    """SMART basic legal text formatting - processes complete document fast"""
    if not text:
        return ""
    
    import re
    
    # 🧹 CLEAN METADATA TRASH first
    cleanup_patterns = [
        r'Descargar PDF.*?\n',
        r'Fechas.*?\n', 
        r'Fecha de Expedición:.*?\n',
        r'Fecha de Entrada en Vigencia:.*?\n',
        r'Medio de Publicación:.*?\n',
        r'Temas \(\d+\).*?\n',
        r'DATOS PERSONALES.*?\n',
        r'- Subtema:.*?\n',
        r'RÉGIMEN ESPECIAL.*?\n',
        r'Superintendencia de Industria y Comercio.*?\n',
        r'Vigencias\(\d+\).*?\n',
        r'Los datos publicados tienen propósitos.*?\n',
        r'Gestor Normativo.*?\n',
        r'Función Pública.*?\n',
        r'- Parte \d+.*?\n'
    ]
    
    for pattern in cleanup_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # 🔧 SMART PREPROCESSING - aggressively separate articles
    text = re.sub(r'(Artículo\s+\d+°*\.?)', r'\n\n\1', text)
    text = re.sub(r'(TÍTULO\s+[IVXLC]+)', r'\n\n\1', text) 
    text = re.sub(r'(Parágrafo\.?)', r'\n\n\1', text)
    text = re.sub(r'([a-z])\)\s*([A-Z])', r'\1)\n\2', text)  # Better list separation
    text = re.sub(r'(\.\s+)([A-Z][a-z])', r'\1\n\n\2', text)  # New paragraphs on capitals
    text = re.sub(r'(;\s*)([a-z])', r'\1\n\2', text)  # Semicolon lists
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Clean multiple breaks
    
    lines = text.split('\n')
    html_lines = []
    article_count = 0
    in_article = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip metadata lines that slipped through
        if any(skip in line.lower() for skip in ['descargar pdf', 'fecha de', 'medio de publicación', 
                                                'temas (', 'datos personales', 'subtema:', 
                                                'régimen especial', 'vigencias(']):
            continue
        
        # 📋 LEGAL STRUCTURE DETECTION
        if re.match(r'^LEY\s+(ESTATUTARIA\s+)?\d+\s+DE\s+\d{4}', line, re.IGNORECASE):
            html_lines.append(f'<h1 class="ley-titulo">{line}</h1>')
        elif re.match(r'^TÍTULO\s+[IVXLC]+', line, re.IGNORECASE):
            if in_article:
                html_lines.append('</div>')
                in_article = False
            html_lines.append(f'<h2 class="titulo">{line}</h2>')
        elif re.match(r'^Artículo\s+\d+°*\.?', line, re.IGNORECASE):
            if in_article:
                html_lines.append('</div>')
            article_count += 1
            article_id = f"art-{article_count}"
            # Extract article number
            art_match = re.search(r'Artículo\s+(\d+)', line, re.IGNORECASE)
            art_num = art_match.group(1) if art_match else str(article_count)
            html_lines.append(f'<div class="articulo" id="{article_id}" data-article="{art_num}"><h3>{line}</h3>')
            in_article = True
        elif re.match(r'^Parágrafo', line, re.IGNORECASE):
            html_lines.append(f'<div class="paragrafo"><h4>{line}</h4></div>')
        elif line.upper() in ['EL CONGRESO DE COLOMBIA', 'DECRETA:', 'CONSIDERANDO:']:
            html_lines.append(f'<p class="congreso-decreta"><strong>{line}</strong></p>')
        elif re.match(r'^[a-z]\)', line):
            # List item
            html_lines.append(f'<li class="legal-list-item">{line}</li>')
        elif re.match(r'^Por la cual', line, re.IGNORECASE):
            html_lines.append(f'<h2 class="ley-descripcion">{line}</h2>')
        else:
            # Regular paragraph - but smarter
            if len(line) > 10:  # Skip very short lines that might be metadata
                html_lines.append(f'<p>{line}</p>')
    
    # Close any open article divs
    if in_article:
        html_lines.append('</div>')
    
    return '\n'.join(html_lines)

def extract_articles_simple(text_content):
    """Extract articles from plain text for navigation"""
    import re
    articles = []
    
    # Find all articles in the text
    pattern = r'Artículo\s+(\d+)°*\.?\s*([^\n]*)'
    matches = re.findall(pattern, text_content, re.IGNORECASE)
    
    for i, (art_num, art_title) in enumerate(matches):
        articles.append({
            'id': f'art-{art_num}',
            'number': art_num,
            'title': f'Artículo {art_num}°. {art_title[:50]}...' if len(art_title) > 50 else f'Artículo {art_num}°. {art_title}',
            'anchor': f"#art-{art_num}"
        })
    
    return articles

@app.route('/')
def serve_frontend():
    """Serve the main frontend file"""
    return send_from_directory(project_root, 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat_legal():
    """
    Endpoint del chatbot legal especializado
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        user_query = data['query'].strip()
        chat_history = data.get('chat_history', [])  # Historial de mensajes previos
        
        if len(user_query) < 3:
            return jsonify({
                'success': False,
                'error': 'Query too short'
            }), 400
        
        # Búsqueda en archivos de texto - COMPATIBLE CON VERCEL
        if not library:
            return jsonify({
                'success': False,
                'response': 'Sistema de archivos no disponible',
                'sources': []
            })
        
        # Obtener todos los documentos
        all_docs = library.get_all_documents()
        documents = []
        
        # Buscar en contenido de archivos con múltiples términos
        query_lower = user_query.lower()
        query_terms = query_lower.split()
        for doc in all_docs:
            content_result = library.get_document_content(doc['nombre_archivo'])
            if content_result['success']:
                content = content_result['raw_content'].lower()
                title = doc['titulo'].lower()
                filename = doc['nombre_archivo'].lower()
                
                # Búsqueda más inteligente: cualquier término o combinaciones
                found = False
                for term in query_terms:
                    if term in content or term in title or term in filename:
                        found = True
                        break
                
                # Búsqueda específica para decretos
                if "decreto" in query_lower and any(term.isdigit() for term in query_terms):
                    numbers = [term for term in query_terms if term.isdigit()]
                    for num in numbers:
                        if num in filename or num in title:
                            found = True
                            break
                
                if found:
                    documents.append({
                        'nombre_archivo': doc['nombre_archivo'],
                        'titulo': doc['titulo'],
                        'contenido_texto': content_result['raw_content'][:1000],  # Primeros 1000 chars
                        'tipo_norma': doc.get('tipo', 'Norma')
                    })
                    
                    if len(documents) >= 5:  # Limitar a 5 documentos
                        break
        
        if documents:
            # Construir respuesta con documentos encontrados
            sources = []
            context = ""
            
            for doc in documents:
                sources.append({
                    'nombre_archivo': doc['nombre_archivo'],
                    'titulo': doc['titulo'],
                    'tipo': doc['tipo_norma']
                })
                context += f"Documento: {doc['titulo']}\n{doc['contenido_texto'][:500]}\n\n"
            
            # Respuesta inteligente usando Groq AI
            if os.getenv('GROQ_API_KEY'):
                try:
                    from groq import Groq
                    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
                    
                    prompt = f"""Eres un asistente legal especializado en normativa colombiana. 
                    Basándote únicamente en el siguiente contexto legal, responde la pregunta del usuario de manera precisa y profesional.
                    
                    CONTEXTO LEGAL:
                    {context}
                    
                    PREGUNTA: {user_query}
                    
                    Responde de manera clara y cita los artículos o secciones relevantes."""
                    
                    completion = client.chat.completions.create(
                        model="llama3-8b-8192",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    
                    ai_response = completion.choices[0].message.content
                    
                    result = {
                        'success': True,
                        'response': ai_response,
                        'sources': sources
                    }
                except Exception as ai_error:
                    # Fallback sin AI
                    result = {
                        'success': True,
                        'response': f"Encontré información relevante en {len(documents)} documentos. Los temas principales incluyen: {', '.join([doc['titulo'] for doc in documents[:3]])}",
                        'sources': sources
                    }
            else:
                # Sin AI - respuesta básica
                result = {
                    'success': True,  
                    'response': f"Encontré información relevante en {len(documents)} documentos: {', '.join([doc['titulo'] for doc in documents[:3]])}",
                    'sources': sources
                }
        else:
            result = {
                'success': False,
                'response': 'No encontré información relevante en la normativa disponible para tu consulta.',
                'sources': []
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'response': 'Error interno del servidor. Por favor, intenta nuevamente.'
        }), 500

@app.route('/api/privacy/accept', methods=['POST'])
def accept_privacy_policy():
    """Record privacy policy acceptance"""
    try:
        data = request.get_json()
        
        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Create record
        privacy_record = {
            'timestamp': data.get('timestamp', datetime.now().isoformat()),
            'client_ip': client_ip,
            'user_agent': data.get('user_agent', ''),
            'screen_resolution': data.get('screen_resolution', ''),
            'accepted': True
        }
        
        # For production, just log and return success
        # TODO: Add proper database handling later
        print(f"Privacy acceptance: {privacy_record}")
        
        return jsonify({
            'success': True,
            'message': 'Privacy policy acceptance recorded',
            'timestamp': privacy_record['timestamp']
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(project_root, filename)

if __name__ == '__main__':
    print("Starting Matriz Legal API Server...")
    print(f"Database: {DB_PATH}")
    print(f"Texts: {TEXTS_PATH}")
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}")
    
    app.run(debug=True, host='0.0.0.0', port=5001)