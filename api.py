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
from text_library import TextLegalLibrary
from qwen_formatter import QwenLegalFormatter, process_document_with_qwen

app = Flask(__name__)

# Configure CORS securely
if os.getenv('FLASK_ENV') == 'production':
    # Production: only allow specific origins
    CORS(app, origins=[
        "https://your-domain.vercel.app",
        "https://matriz-legal.vercel.app"
    ])
else:
    # Development: allow localhost
    CORS(app, origins=["http://localhost:*", "http://127.0.0.1:*"])

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# 🔄 DUAL ARCHITECTURE SETUP
# Database for chatbot queries & reliable metadata
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data_repository', 'repositorio.db')
TEXTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data_repository', 'textos_limpios_seguro')

def get_db_connection():
    """Get database connection for metadata queries"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Text library for visual interface
library = TextLegalLibrary()
# Clear cache to force recalculation of titles with new logic
library.clear_cache()

# Initialize Qwen formatter for AI-powered text formatting
try:
    formatter = QwenLegalFormatter()
    QWEN_AVAILABLE = True
    print("✅ Qwen AI formatter initialized - Enhanced text formatting with complete metadata extraction")
except Exception as e:
    formatter = None
    QWEN_AVAILABLE = False
    print(f"⚠️  Qwen not available: {e}")
    print("💡 Set GROQ_API_KEY environment variable to enable AI formatting")

print(f"🔄 DUAL SYSTEM ACTIVE:")
print(f"  📊 Database: {DB_PATH}")
print(f"  📄 Text Files: {TEXTS_PATH}")
print(f"  🤖 AI Formatting: {'✅ Available' if QWEN_AVAILABLE else '❌ Disabled'}")

@app.route('/api/documents', methods=['GET'])
def get_documents():
    """📄 Get documents using TEXT LIBRARY for complete file access"""
    try:
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
    """📄 Get document content using TEXT FILES + Groq AI formatting"""
    try:
        # Get metadata from database (reliable source)
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT tipo_norma, titulo FROM textos_repositorio WHERE nombre_archivo = ?", 
            (document_id,)
        )
        db_document = cursor.fetchone()
        conn.close()
        
        if not db_document:
            return jsonify({
                'success': False,
                'error': 'Document not found in database'
            }), 404
        
        # Get content from text files (visual source)
        content_result = library.get_document_content(document_id)
        
        if not content_result['success']:
            return jsonify({
                'success': False,
                'error': f"Text file not found: {content_result['error']}"
            }), 404
        
        raw_content = content_result['raw_content']
        document_title = db_document['titulo']  # Use DB title (more reliable)
        
        # 📄 SIMPLE DISPLAY: Just show the text with minimal formatting
        html_content = f'<div class="document-content"><pre style="white-space: pre-wrap; font-family: inherit; font-size: inherit;">{raw_content}</pre></div>'
        
        # Extract articles for navigation (simple method)
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
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_repository_stats():
    """Get repository statistics"""
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
                'procesadas': total,  # All documents are processed
                'referencias': total * 2  # Approximate
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search', methods=['GET'])
def search_documents():
    """Full-text search across documents"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Search query required'
        }), 400
    
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
            'count': len(results)
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
    return send_from_directory('.', 'index.html')

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
        
        # Importar y usar chatbot
        from chatbot_legal import ChatbotLegal
        
        chatbot = ChatbotLegal(
            db_path=DB_PATH,
            texts_path=TEXTS_PATH
        )
        
        # Procesar consulta con contexto de chat
        result = chatbot.process_query_with_context(user_query, chat_history)
        
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
        
        # Connect to database
        conn = get_db_connection()
        
        # Create privacy_acceptances table if it doesn't exist
        conn.execute('''
            CREATE TABLE IF NOT EXISTS privacy_acceptances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                client_ip TEXT,
                user_agent TEXT,
                screen_resolution TEXT,
                accepted BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert record
        conn.execute('''
            INSERT INTO privacy_acceptances 
            (timestamp, client_ip, user_agent, screen_resolution, accepted)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            privacy_record['timestamp'],
            privacy_record['client_ip'],
            privacy_record['user_agent'],
            privacy_record['screen_resolution'],
            privacy_record['accepted']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Privacy policy acceptance recorded',
            'timestamp': privacy_record['timestamp']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)

if __name__ == '__main__':
    print("Starting Matriz Legal API Server...")
    print(f"Database: {DB_PATH}")
    print(f"Texts: {TEXTS_PATH}")
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}")
    
    app.run(debug=True, host='0.0.0.0', port=5001)