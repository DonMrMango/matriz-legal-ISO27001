#!/usr/bin/env python3
"""Simple test API to debug Vercel deployment"""

from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/api/test')
def test():
    return jsonify({
        'status': 'ok',
        'message': 'API is working',
        'env': os.getenv('FLASK_ENV', 'not set')
    })

@app.route('/api/documents')
def documents():
    return jsonify({
        'success': True,
        'documents': [
            {
                'nombre_archivo': 'test_doc',
                'titulo': 'Test Document',
                'tipo': 'Test',
                'ano': 2025
            }
        ]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)