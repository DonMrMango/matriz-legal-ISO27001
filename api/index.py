#!/usr/bin/env python3
"""
Dual-Architecture API server for Matriz Legal INSOFT + ISO 27001/27002
🔄 DUAL SYSTEM:
  📊 SQLite Database → Chatbot queries & metadata 
  📄 Text Files + Groq AI → Visual interface & formatting
  🔐 ISO 27001/27002 → Specialized security standards chatbot
Best of both worlds: reliability + optimal presentation
"""

import sqlite3
import json
import os
import time
import hashlib
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory, g
from flask_cors import CORS
from functools import wraps

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

# NUEVO: Importar módulo de ISO
try:
    from api.iso_endpoint import register_iso_endpoints
    ISO_ENDPOINTS_AVAILABLE = True
    print("✅ iso_endpoint imported successfully")
except Exception as e:
    print(f"Warning: Could not import iso_endpoint: {e}")
    ISO_ENDPOINTS_AVAILABLE = False
    register_iso_endpoints = None

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

def init_analytics_tables():
    """Initialize analytics tables in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Sessions table - track user sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                page_views INTEGER DEFAULT 0,
                queries_count INTEGER DEFAULT 0
            )
        ''')
        
        # Page views table - track page/endpoint access
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_page_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                endpoint TEXT,
                method TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time_ms INTEGER,
                status_code INTEGER,
                document_id TEXT,
                FOREIGN KEY (session_id) REFERENCES analytics_sessions(session_id)
            )
        ''')
        
        # Chat queries table - track chatbot usage (NO personal data)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_chat_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                query_type TEXT,
                query_length INTEGER,
                response_time_ms INTEGER,
                documents_found INTEGER,
                tokens_used INTEGER,
                success BOOLEAN,
                FOREIGN KEY (session_id) REFERENCES analytics_sessions(session_id)
            )
        ''')
        
        # Document access table - track which documents are consulted
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_document_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                document_id TEXT,
                document_title TEXT,
                document_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_type TEXT,
                FOREIGN KEY (session_id) REFERENCES analytics_sessions(session_id)
            )
        ''')
        
        # System metrics table - performance and usage stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metric_name TEXT,
                metric_value REAL,
                metric_unit TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Analytics tables initialized successfully")
        
    except Exception as e:
        print(f"❌ Error initializing analytics tables: {e}")

def get_or_create_session():
    """Get or create analytics session"""
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id:
        # Create new session ID
        session_data = f"{request.remote_addr}_{time.time()}_{request.user_agent}"
        session_id = hashlib.md5(session_data.encode()).hexdigest()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get client IP (handle proxy headers)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        user_agent = request.headers.get('User-Agent', '')
        
        # Try to get existing session
        cursor.execute('SELECT * FROM analytics_sessions WHERE session_id = ?', (session_id,))
        session = cursor.fetchone()
        
        if session:
            # Update last activity
            cursor.execute('''
                UPDATE analytics_sessions 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_id = ?
            ''', (session_id,))
        else:
            # Create new session
            cursor.execute('''
                INSERT INTO analytics_sessions (session_id, ip_address, user_agent)
                VALUES (?, ?, ?)
            ''', (session_id, client_ip, user_agent))
        
        conn.commit()
        conn.close()
        
        return session_id
        
    except Exception as e:
        print(f"Session tracking error: {e}")
        return session_id

def track_request(endpoint, method, document_id=None, response_time=None, status_code=200):
    """Track page view/endpoint access"""
    try:
        session_id = g.get('session_id')
        if not session_id:
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert page view
        cursor.execute('''
            INSERT INTO analytics_page_views 
            (session_id, endpoint, method, response_time_ms, status_code, document_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, endpoint, method, response_time, status_code, document_id))
        
        # Update session page views count
        cursor.execute('''
            UPDATE analytics_sessions 
            SET page_views = page_views + 1, last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Request tracking error: {e}")

def track_chat_query(query_type, query_length, response_time, documents_found, tokens_used, success=True):
    """Track chatbot query (NO personal data stored)"""
    try:
        session_id = g.get('session_id')
        if not session_id:
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analytics_chat_queries 
            (session_id, query_type, query_length, response_time_ms, documents_found, tokens_used, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, query_type, query_length, response_time, documents_found, tokens_used, success))
        
        # Update session queries count
        cursor.execute('''
            UPDATE analytics_sessions 
            SET queries_count = queries_count + 1, last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Chat tracking error: {e}")

def track_document_access(document_id, document_title, document_type, access_type='view'):
    """Track document access"""
    try:
        session_id = g.get('session_id')
        if not session_id:
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analytics_document_access 
            (session_id, document_id, document_title, document_type, access_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, document_id, document_title, document_type, access_type))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Document tracking error: {e}")

# Authentication decorator for admin endpoints
def require_admin_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Simple admin authentication - can be enhanced
        auth_token = request.headers.get('Authorization')
        admin_token = os.getenv('ADMIN_TOKEN', 'admin_daniel_2024')
        
        if auth_token != f'Bearer {admin_token}':
            return jsonify({'error': 'Unauthorized'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# Middleware to track all requests
@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.session_id = get_or_create_session()

@app.after_request
def after_request(response):
    # Track request performance and details
    if hasattr(g, 'request_start_time'):
        response_time = int((time.time() - g.request_start_time) * 1000)  # ms
        endpoint = request.endpoint or request.path
        
        # Skip tracking for admin endpoints to avoid noise
        if not endpoint.startswith('/api/admin'):
            track_request(
                endpoint=endpoint,
                method=request.method,
                response_time=response_time,
                status_code=response.status_code
            )
    
    return response

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

# Initialize analytics tables
# Exponemos la función de track_chat_query para que pueda ser utilizada por los módulos ISO
app.track_chat_query = track_chat_query

# 🆕 INTEGRACIÓN ISO 27001/27002
# Registrar endpoints ISO si están disponibles
if ISO_ENDPOINTS_AVAILABLE:
    register_iso_endpoints(app)
    print("🔐 Chatbot ISO 27001/27002 integrado correctamente")
else:
    print("⚠️ Endpoints ISO no disponibles. Chatbot ISO no estará activo.")

init_analytics_tables()

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
    
    # NUEVO: Test ISO chat
    iso_status = 'unknown'
    try:
        if ISO_ENDPOINTS_AVAILABLE:
            from api.iso_chat import ISO_CONTEXTO
            iso_status = f'working ({len(ISO_CONTEXTO)} chars)'
        else:
            iso_status = 'module not available'
    except Exception as e:
        iso_status = f'failed: {str(e)}'
    
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
            'iso_chatbot': ISO_ENDPOINTS_AVAILABLE,
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
        },
        'iso_chatbot': {
            'status': iso_status,
            'endpoints': ['/api/iso/chat', '/api/iso/status'] if ISO_ENDPOINTS_AVAILABLE else []
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
                
                # Track document access
                track_document_access(document_id, document_title, document_type, 'view')
                
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

# ================== ADMIN ANALYTICS ENDPOINTS ==================

@app.route('/api/admin/analytics/overview', methods=['GET'])
@require_admin_auth
def get_analytics_overview():
    """Get general analytics overview"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get time range
        hours = int(request.args.get('hours', 24))  # Default 24 hours
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Total sessions
        cursor.execute('''
            SELECT COUNT(*) as total_sessions,
                   COUNT(CASE WHEN created_at >= ? THEN 1 END) as recent_sessions
            FROM analytics_sessions
        ''', (start_time,))
        sessions_data = cursor.fetchone()
        
        # Total page views
        cursor.execute('''
            SELECT COUNT(*) as total_views,
                   COUNT(CASE WHEN timestamp >= ? THEN 1 END) as recent_views,
                   AVG(response_time_ms) as avg_response_time
            FROM analytics_page_views
        ''', (start_time,))
        views_data = cursor.fetchone()
        
        # Chat queries
        cursor.execute('''
            SELECT COUNT(*) as total_queries,
                   COUNT(CASE WHEN timestamp >= ? THEN 1 END) as recent_queries,
                   AVG(response_time_ms) as avg_query_time,
                   SUM(tokens_used) as total_tokens,
                   AVG(documents_found) as avg_docs_found
            FROM analytics_chat_queries
        ''', (start_time,))
        queries_data = cursor.fetchone()
        
        # Most accessed documents
        cursor.execute('''
            SELECT document_id, document_title, document_type, COUNT(*) as access_count
            FROM analytics_document_access
            WHERE timestamp >= ?
            GROUP BY document_id, document_title, document_type
            ORDER BY access_count DESC
            LIMIT 10
        ''', (start_time,))
        top_documents = [dict(row) for row in cursor.fetchall()]
        
        # Query types breakdown
        cursor.execute('''
            SELECT query_type, COUNT(*) as count
            FROM analytics_chat_queries
            WHERE timestamp >= ?
            GROUP BY query_type
            ORDER BY count DESC
        ''', (start_time,))
        query_types = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'time_range_hours': hours,
                'sessions': {
                    'total': sessions_data['total_sessions'],
                    'recent': sessions_data['recent_sessions']
                },
                'page_views': {
                    'total': views_data['total_views'],
                    'recent': views_data['recent_views'],
                    'avg_response_time_ms': round(views_data['avg_response_time'] or 0, 2)
                },
                'chat_queries': {
                    'total': queries_data['total_queries'],
                    'recent': queries_data['recent_queries'],
                    'avg_response_time_ms': round(queries_data['avg_query_time'] or 0, 2),
                    'total_tokens_used': queries_data['total_tokens'] or 0,
                    'avg_documents_found': round(queries_data['avg_docs_found'] or 0, 2)
                },
                'top_documents': top_documents,
                'query_types': query_types
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/analytics/sessions', methods=['GET'])
@require_admin_auth
def get_sessions_analytics():
    """Get detailed session analytics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hours = int(request.args.get('hours', 24))
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Recent sessions with details
        cursor.execute('''
            SELECT session_id, ip_address, user_agent, created_at, last_activity,
                   page_views, queries_count,
                   CAST((julianday(last_activity) - julianday(created_at)) * 86400 AS INTEGER) as session_duration_sec
            FROM analytics_sessions
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT 100
        ''', (start_time,))
        sessions = [dict(row) for row in cursor.fetchall()]
        
        # Sessions per hour
        cursor.execute('''
            SELECT strftime('%Y-%m-%d %H:00:00', created_at) as hour,
                   COUNT(*) as session_count
            FROM analytics_sessions
            WHERE created_at >= ?
            GROUP BY strftime('%Y-%m-%d %H:00:00', created_at)
            ORDER BY hour
        ''', (start_time,))
        sessions_by_hour = [dict(row) for row in cursor.fetchall()]
        
        # Top IPs
        cursor.execute('''
            SELECT ip_address, COUNT(*) as session_count,
                   MAX(created_at) as last_seen
            FROM analytics_sessions
            WHERE created_at >= ?
            GROUP BY ip_address
            ORDER BY session_count DESC
            LIMIT 20
        ''', (start_time,))
        top_ips = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'recent_sessions': sessions,
                'sessions_by_hour': sessions_by_hour,
                'top_ips': top_ips
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/analytics/performance', methods=['GET'])
@require_admin_auth
def get_performance_analytics():
    """Get performance metrics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hours = int(request.args.get('hours', 24))
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Response times by endpoint
        cursor.execute('''
            SELECT endpoint, 
                   COUNT(*) as request_count,
                   AVG(response_time_ms) as avg_response_time,
                   MIN(response_time_ms) as min_response_time,
                   MAX(response_time_ms) as max_response_time
            FROM analytics_page_views
            WHERE timestamp >= ? AND response_time_ms IS NOT NULL
            GROUP BY endpoint
            ORDER BY request_count DESC
        ''', (start_time,))
        endpoint_performance = [dict(row) for row in cursor.fetchall()]
        
        # Response times over time
        cursor.execute('''
            SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                   AVG(response_time_ms) as avg_response_time,
                   COUNT(*) as request_count
            FROM analytics_page_views
            WHERE timestamp >= ? AND response_time_ms IS NOT NULL
            GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
            ORDER BY hour
        ''', (start_time,))
        response_times_by_hour = [dict(row) for row in cursor.fetchall()]
        
        # Status codes distribution
        cursor.execute('''
            SELECT status_code, COUNT(*) as count
            FROM analytics_page_views
            WHERE timestamp >= ?
            GROUP BY status_code
            ORDER BY count DESC
        ''', (start_time,))
        status_codes = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'endpoint_performance': endpoint_performance,
                'response_times_by_hour': response_times_by_hour,
                'status_codes': status_codes
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/analytics/chat', methods=['GET'])
@require_admin_auth
def get_chat_analytics():
    """Get chatbot usage analytics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hours = int(request.args.get('hours', 24))
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Chat queries over time
        cursor.execute('''
            SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                   COUNT(*) as query_count,
                   AVG(response_time_ms) as avg_response_time,
                   SUM(tokens_used) as tokens_used
            FROM analytics_chat_queries
            WHERE timestamp >= ?
            GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
            ORDER BY hour
        ''', (start_time,))
        queries_by_hour = [dict(row) for row in cursor.fetchall()]
        
        # Query types analysis
        cursor.execute('''
            SELECT query_type, 
                   COUNT(*) as count,
                   AVG(response_time_ms) as avg_response_time,
                   AVG(documents_found) as avg_documents_found,
                   AVG(query_length) as avg_query_length
            FROM analytics_chat_queries
            WHERE timestamp >= ?
            GROUP BY query_type
            ORDER BY count DESC
        ''', (start_time,))
        query_type_stats = [dict(row) for row in cursor.fetchall()]
        
        # Success rate
        cursor.execute('''
            SELECT success,
                   COUNT(*) as count,
                   ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM analytics_chat_queries WHERE timestamp >= ?), 2) as percentage
            FROM analytics_chat_queries
            WHERE timestamp >= ?
            GROUP BY success
        ''', (start_time, start_time))
        success_rate = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'queries_by_hour': queries_by_hour,
                'query_type_stats': query_type_stats,
                'success_rate': success_rate
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/analytics/documents', methods=['GET'])
@require_admin_auth
def get_document_analytics():
    """Get document access analytics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hours = int(request.args.get('hours', 24))
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Most accessed documents
        cursor.execute('''
            SELECT document_id, document_title, document_type,
                   COUNT(*) as access_count,
                   COUNT(DISTINCT session_id) as unique_sessions
            FROM analytics_document_access
            WHERE timestamp >= ?
            GROUP BY document_id, document_title, document_type
            ORDER BY access_count DESC
            LIMIT 20
        ''', (start_time,))
        most_accessed = [dict(row) for row in cursor.fetchall()]
        
        # Document access by type
        cursor.execute('''
            SELECT document_type,
                   COUNT(*) as access_count,
                   COUNT(DISTINCT document_id) as unique_documents
            FROM analytics_document_access
            WHERE timestamp >= ?
            GROUP BY document_type
            ORDER BY access_count DESC
        ''', (start_time,))
        access_by_type = [dict(row) for row in cursor.fetchall()]
        
        # Document access over time
        cursor.execute('''
            SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                   COUNT(*) as access_count
            FROM analytics_document_access
            WHERE timestamp >= ?
            GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
            ORDER BY hour
        ''', (start_time,))
        access_by_hour = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'most_accessed_documents': most_accessed,
                'access_by_type': access_by_type,
                'access_by_hour': access_by_hour
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/analytics/realtime', methods=['GET'])
@require_admin_auth
def get_realtime_analytics():
    """Get real-time analytics data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Last 5 minutes activity
        last_5_min = datetime.now() - timedelta(minutes=5)
        
        # Active sessions (activity in last 5 minutes)
        cursor.execute('''
            SELECT COUNT(*) as active_sessions
            FROM analytics_sessions
            WHERE last_activity >= ?
        ''', (last_5_min,))
        active_sessions = cursor.fetchone()['active_sessions']
        
        # Recent page views
        cursor.execute('''
            SELECT COUNT(*) as recent_views
            FROM analytics_page_views
            WHERE timestamp >= ?
        ''', (last_5_min,))
        recent_views = cursor.fetchone()['recent_views']
        
        # Recent chat queries
        cursor.execute('''
            SELECT COUNT(*) as recent_queries
            FROM analytics_chat_queries
            WHERE timestamp >= ?
        ''', (last_5_min,))
        recent_queries = cursor.fetchone()['recent_queries']
        
        # Latest activity
        cursor.execute('''
            SELECT 'page_view' as activity_type, endpoint as details, timestamp
            FROM analytics_page_views
            WHERE timestamp >= ?
            UNION ALL
            SELECT 'chat_query' as activity_type, 
                   query_type || ' (' || documents_found || ' docs)' as details, 
                   timestamp
            FROM analytics_chat_queries
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (last_5_min, last_5_min))
        latest_activity = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'timestamp': datetime.now().isoformat(),
                'active_sessions': active_sessions,
                'recent_views': recent_views,
                'recent_queries': recent_queries,
                'latest_activity': latest_activity
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/')
def serve_frontend():
    """Serve the main frontend file"""
    return send_from_directory(project_root, 'index.html')

@app.route('/admin')
def serve_admin():
    """Serve the admin dashboard"""
    return send_from_directory(project_root, 'admin.html')

@app.route('/api/chat', methods=['POST'])
def chat_legal():
    """
    Endpoint del chatbot legal especializado
    """
    start_time = time.time()
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            track_chat_query('invalid', 0, 0, 0, 0, False)
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        user_query = data['query'].strip()
        chat_history = data.get('chat_history', [])  # Historial de mensajes previos
        
        if len(user_query) < 3:
            track_chat_query('too_short', len(user_query), 0, 0, 0, False)
            return jsonify({
                'success': False,
                'error': 'Query too short'
            }), 400
        
        # Búsqueda en archivos de texto - COMPATIBLE CON VERCEL
        if not library:
            track_chat_query('system_error', len(user_query), int((time.time() - start_time) * 1000), 0, 0, False)
            return jsonify({
                'success': False,
                'response': 'Sistema de archivos no disponible',
                'sources': []
            })
        
        # Obtener todos los documentos
        all_docs = library.get_all_documents()
        documents = []
        
        # SISTEMA DE BÚSQUEDA INTELIGENTE CON SCORING
        query_lower = user_query.lower()
        query_terms = query_lower.split()
        document_scores = []
        
        for doc in all_docs:
            content_result = library.get_document_content(doc['nombre_archivo'])
            if content_result['success']:
                content = content_result['raw_content'].lower()
                title = doc['titulo'].lower()
                filename = doc['nombre_archivo'].lower()
                
                # SISTEMA DE PUNTUACIÓN INTELIGENTE
                score = 0
                relevance_factors = []
                
                # 1. BÚSQUEDA EXACTA EN TÍTULO (MÁXIMA PRIORIDAD)
                for term in query_terms:
                    if term in title:
                        if term.isdigit():
                            score += 100  # Números exactos en título = altísima relevancia
                            relevance_factors.append(f"Number '{term}' in title")
                        else:
                            score += 50   # Palabras exactas en título = alta relevancia
                            relevance_factors.append(f"Term '{term}' in title")
                
                # 2. BÚSQUEDA EXACTA EN NOMBRE DE ARCHIVO
                for term in query_terms:
                    if term in filename:
                        if term.isdigit():
                            score += 80   # Números en filename = muy alta relevancia
                            relevance_factors.append(f"Number '{term}' in filename")
                        else:
                            score += 30   # Palabras en filename = buena relevancia
                            relevance_factors.append(f"Term '{term}' in filename")
                
                # 3. BÚSQUEDA EN CONTENIDO (MENOR PRIORIDAD)
                content_matches = 0
                for term in query_terms:
                    if term in content:
                        content_matches += 1
                
                if content_matches > 0:
                    score += content_matches * 5  # Cada match en contenido suma 5 puntos
                    relevance_factors.append(f"{content_matches} terms in content")
                
                # 4. FILTROS ESPECÍFICOS POR TIPO DE CONSULTA
                if "decreto" in query_lower:
                    if "decreto" in filename:
                        score += 60  # Boost para decretos cuando se buscan decretos
                        relevance_factors.append("Decreto type match")
                
                if "ley" in query_lower:
                    if "ley" in filename:
                        score += 60  # Boost para leyes cuando se buscan leyes
                        relevance_factors.append("Ley type match")
                
                if "circular" in query_lower:
                    if "circular" in filename:
                        score += 60  # Boost para circulares
                        relevance_factors.append("Circular type match")
                
                # Solo incluir documentos con score mínimo
                if score >= 30:  # Umbral mínimo de relevancia
                    document_scores.append({
                        'doc': doc,
                        'content': content_result['raw_content'],
                        'score': score,
                        'relevance_factors': relevance_factors
                    })
        
        # ORDENAR POR RELEVANCIA (SCORE MÁS ALTO PRIMERO)
        document_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # TOMAR SOLO LOS MÁS RELEVANTES
        documents = []
        for scored_doc in document_scores[:3]:  # Solo top 3 documentos más relevantes
            documents.append({
                'nombre_archivo': scored_doc['doc']['nombre_archivo'],
                'titulo': scored_doc['doc']['titulo'],
                'contenido_texto': scored_doc['content'],  # CONTENIDO COMPLETO para mejor contexto
                'tipo_norma': scored_doc['doc'].get('tipo', 'Norma'),
                'score': scored_doc['score'],
                'relevance': scored_doc['relevance_factors']
            })
        
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
                
                # BÚSQUEDA ESPECÍFICA DE ARTÍCULOS SI SE PREGUNTA POR UNO
                if "artículo" in query_lower or "articulo" in query_lower:
                    article_numbers = []
                    for term in query_terms:
                        if term.isdigit():
                            article_numbers.append(term)
                    
                    if article_numbers:
                        # Buscar artículos específicos en el contenido
                        content_lines = doc['contenido_texto'].split('\n')
                        relevant_content = []
                        
                        for line in content_lines:
                            line_lower = line.lower()
                            for art_num in article_numbers:
                                if f"artículo {art_num}" in line_lower or f"articulo {art_num}" in line_lower or f"art. {art_num}" in line_lower or f"art {art_num}" in line_lower:
                                    # Incluir el artículo y las siguientes 10 líneas
                                    start_idx = content_lines.index(line)
                                    end_idx = min(start_idx + 10, len(content_lines))
                                    relevant_content.extend(content_lines[start_idx:end_idx])
                                    break
                        
                        if relevant_content:
                            context += f"Documento: {doc['titulo']}\n" + "\n".join(relevant_content) + "\n\n"
                        else:
                            context += f"Documento: {doc['titulo']}\n{doc['contenido_texto'][:3000]}\n\n"
                    else:
                        context += f"Documento: {doc['titulo']}\n{doc['contenido_texto'][:3000]}\n\n"
                else:
                    context += f"Documento: {doc['titulo']}\n{doc['contenido_texto'][:3000]}\n\n"
            
            # Respuesta inteligente usando Groq AI
            if os.getenv('GROQ_API_KEY'):
                try:
                    from groq import Groq
                    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
                    
                    # CONSTRUIR LISTADO DE DOCUMENTOS DISPONIBLES
                    available_docs = []
                    for scored_doc in document_scores:
                        doc = scored_doc['doc']
                        available_docs.append(f"- {doc['titulo']} ({doc['nombre_archivo']})")
                    
                    available_list = "\n".join(available_docs[:10])  # Primeros 10 para referencia
                    
                    prompt = f"""Eres un asistente legal especializado en normativa colombiana ISO 27001.

DOCUMENTOS DISPONIBLES EN LA BASE LEGAL:
{available_list}

CONTEXTO LEGAL RELEVANTE PARA TU RESPUESTA:
{context}

INSTRUCCIONES IMPORTANTES:
1. Responde ÚNICAMENTE basándote en el contexto legal proporcionado arriba
2. Si el documento específico mencionado en la pregunta NO está en el contexto, menciona qué documentos SÍ tienes disponibles que son relevantes
3. Cita artículos, números de norma y fechas cuando sean específicos
4. Si no encuentras información específica, sugiere documentos alternativos del listado disponible
5. Sé preciso y profesional

PREGUNTA DEL USUARIO: {user_query}

RESPUESTA:"""
                    
                    completion = client.chat.completions.create(
                        model="llama3-8b-8192",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    
                    ai_response = completion.choices[0].message.content
                    
                    # Track AI-powered query with token usage estimation
                    estimated_tokens = len(prompt.split()) + len(ai_response.split())
                    track_chat_query('ai_powered', len(user_query), int((time.time() - start_time) * 1000), 
                                   len(documents), estimated_tokens, True)
                    
                    result = {
                        'success': True,
                        'response': ai_response,
                        'sources': sources
                    }
                except Exception as ai_error:
                    # Fallback sin AI
                    track_chat_query('fallback', len(user_query), int((time.time() - start_time) * 1000), 
                                   len(documents), 0, True)
                    result = {
                        'success': True,
                        'response': f"Encontré información relevante en {len(documents)} documentos. Los temas principales incluyen: {', '.join([doc['titulo'] for doc in documents[:3]])}",
                        'sources': sources
                    }
            else:
                # Sin AI - respuesta básica
                track_chat_query('basic', len(user_query), int((time.time() - start_time) * 1000), 
                               len(documents), 0, True)
                result = {
                    'success': True,  
                    'response': f"Encontré información relevante en {len(documents)} documentos: {', '.join([doc['titulo'] for doc in documents[:3]])}",
                    'sources': sources
                }
        else:
            # No documents found
            track_chat_query('no_results', len(user_query), int((time.time() - start_time) * 1000), 
                           0, 0, True)
            result = {
                'success': False,
                'response': 'No encontré información relevante en la normativa disponible para tu consulta.',
                'sources': []
            }
        
        return jsonify(result)
        
    except Exception as e:
        track_chat_query('error', len(user_query) if 'user_query' in locals() else 0, 
                        int((time.time() - start_time) * 1000), 0, 0, False)
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
    print("Starting Matriz Legal + ISO 27001/27002 API Server...")
    print(f"Database: {DB_PATH}")
    print(f"Texts: {TEXTS_PATH}")
    if ISO_ENDPOINTS_AVAILABLE:
        from api.iso_chat import ISO_CONTEXTO
        print(f"ISO Context: {len(ISO_CONTEXTO)} characters, {len(ISO_CONTEXTO.split('\n'))} lines")
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}")
    
    app.run(debug=True, host='0.0.0.0', port=5002)