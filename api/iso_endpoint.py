#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoint de integración ISO para la API de matriz-legal-ISO27001
"""

from flask import request, jsonify
from api.iso_chat import process_iso_chat_request
import time

def register_iso_endpoints(app):
    """Registra los endpoints del chatbot ISO en la aplicación Flask principal"""
    
    @app.route('/api/iso/chat', methods=['POST'])
    def iso_chat():
        """Endpoint para consultas al chatbot ISO 27001/27002"""
        start_time = time.time()
        
        try:
            # Obtener datos de la solicitud
            data = request.json
            
            # Procesar la solicitud usando el módulo de chat ISO
            result, status_code = process_iso_chat_request(data)
            
            # Tracking de uso (si está disponible la función en el app principal)
            if hasattr(app, 'track_chat_query') and callable(app.track_chat_query):
                query_type = 'iso_direct' if result.get('direct_match') else 'iso_semantic'
                query_length = len(data.get('query', ''))
                response_time = int((time.time() - start_time) * 1000)
                documents_found = 1 if result.get('direct_match') else 0
                tokens_used = result.get('tokens', {}).get('total', 0)
                success = result.get('success', False)
                
                app.track_chat_query(query_type, query_length, response_time, documents_found, tokens_used, success)
            
            return jsonify(result), status_code
            
        except Exception as e:
            error_response = {
                "success": False,
                "error": str(e),
                "response": "Error en el procesamiento de la consulta ISO"
            }
            return jsonify(error_response), 500
    
    @app.route('/api/iso/status', methods=['GET'])
    def iso_status():
        """Endpoint para verificar el estado del chatbot ISO"""
        from api.iso_chat import ISO_CONTEXTO, GROQ_API_KEY, MODEL
        
        return jsonify({
            "success": True,
            "status": "active",
            "context_size": len(ISO_CONTEXTO),
            "context_lines": len(ISO_CONTEXTO.split('\n')),
            "api_configured": bool(GROQ_API_KEY),
            "model": MODEL
        })
    
    print("✅ Endpoints de ISO 27001/27002 registrados correctamente")