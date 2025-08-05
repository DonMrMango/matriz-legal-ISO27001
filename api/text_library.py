#!/usr/bin/env python3
"""
Text-Based Legal Library
Biblioteca que lee directamente los archivos de texto extraídos
Sin dependencia de base de datos - acceso directo a archivos
"""

import os
import json
import re
from typing import Dict, List, Any, Optional
from pathlib import Path

class TextLegalLibrary:
    def __init__(self, texts_path: str = None):
        """
        Inicializar biblioteca basada en archivos de texto
        """
        self.texts_path = texts_path or os.path.join(
            os.path.dirname(__file__), '..', 'data_repository', 'textos_limpios_seguro'
        )
        
        # Mapeo de carpetas a tipos de documentos
        self.folder_type_map = {
            'leyes': 'Ley',
            'decretos': 'Decreto', 
            'circulares': 'Circular',
            'resoluciones': 'Resolución',
            'conpes': 'Conpes',
            'otros': 'Otros'
        }
        
        # Cache para metadatos extraídos
        self._metadata_cache = {}
        
    def clear_cache(self):
        """Limpiar caché de metadatos"""
        self._metadata_cache = {}
        
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Obtener lista de todos los documentos disponibles
        """
        documents = []
        
        for folder_name, doc_type in self.folder_type_map.items():
            folder_path = os.path.join(self.texts_path, folder_name)
            
            if not os.path.exists(folder_path):
                continue
                
            for filename in os.listdir(folder_path):
                if filename.endswith('.txt'):
                    file_path = os.path.join(folder_path, filename)
                    
                    # Extraer metadatos del archivo
                    metadata = self._extract_metadata(file_path, doc_type)
                    if metadata:
                        documents.append(metadata)
        
        # Ordenar por año (descendente) y luego por número
        documents.sort(key=lambda x: (x.get('año', 0), x.get('numero', '')), reverse=True)
        
        return documents
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener documento específico por ID (nombre de archivo)
        """
        # Buscar en todas las carpetas
        for folder_name in self.folder_type_map.keys():
            file_path = os.path.join(self.texts_path, folder_name, f"{document_id}.txt")
            
            if os.path.exists(file_path):
                doc_type = self.folder_type_map[folder_name]
                return self._extract_metadata(file_path, doc_type)
        
        return None
    
    def get_document_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener contenido completo del documento
        """
        # Buscar archivo en todas las carpetas
        for folder_name in self.folder_type_map.keys():
            file_path = os.path.join(self.texts_path, folder_name, f"{document_id}.txt")
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extraer metadatos básicos
                    doc_type = self.folder_type_map[folder_name]
                    metadata = self._extract_metadata(file_path, doc_type)
                    
                    return {
                        'success': True,
                        'document_id': document_id,
                        'title': metadata.get('titulo', 'Documento Legal'),
                        'type': doc_type,
                        'raw_content': content,
                        'file_path': file_path,
                        'file_size': os.path.getsize(file_path),
                        'word_count': len(content.split()),
                        'metadata': metadata
                    }
                    
                except Exception as e:
                    return {
                        'success': False,
                        'error': f"Error leyendo archivo: {str(e)}"
                    }
        
        return {
            'success': False,
            'error': 'Documento no encontrado'
        }
    
    def search_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Búsqueda en todos los documentos
        """
        results = []
        all_docs = self.get_all_documents()
        
        query_lower = query.lower()
        
        for doc in all_docs:
            # Buscar en título
            if query_lower in doc.get('titulo', '').lower():
                doc['match_type'] = 'title'
                results.append(doc)
                continue
            
            # Buscar en número
            if query_lower in str(doc.get('numero', '')).lower():
                doc['match_type'] = 'number'
                results.append(doc)
                continue
            
            # Buscar en contenido (más costoso)
            content_result = self.get_document_content(doc['document_id'])
            if content_result['success']:
                if query_lower in content_result['raw_content'].lower():
                    doc['match_type'] = 'content'
                    results.append(doc)
        
        return results
    
    def get_documents_by_type(self, doc_type: str) -> List[Dict[str, Any]]:
        """
        Obtener documentos filtrados por tipo
        """
        all_docs = self.get_all_documents()
        return [doc for doc in all_docs if doc.get('tipo_norma') == doc_type]
    
    def get_documents_by_year(self, year: int) -> List[Dict[str, Any]]:
        """
        Obtener documentos filtrados por año
        """
        all_docs = self.get_all_documents()
        return [doc for doc in all_docs if doc.get('año') == year]
    
    def get_library_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de la biblioteca
        """
        all_docs = self.get_all_documents()
        
        # Contar por tipo
        by_type = {}
        by_year = {}
        total_words = 0
        
        for doc in all_docs:
            # Por tipo
            doc_type = doc.get('tipo_norma', 'Otros')
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
            
            # Por año
            year = doc.get('año', 0)
            if year:
                by_year[year] = by_year.get(year, 0) + 1
            
            # Contar palabras (solo para docs pequeños)
            content = self.get_document_content(doc['document_id'])
            if content['success'] and content['word_count'] < 10000:
                total_words += content['word_count']
        
        return {
            'total_documents': len(all_docs),
            'by_type': by_type,
            'by_year': dict(sorted(by_year.items())),
            'estimated_words': total_words,
            'library_path': self.texts_path
        }
    
    def _extract_metadata(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        """
        Extraer metadatos de un archivo de texto
        """
        if file_path in self._metadata_cache:
            return self._metadata_cache[file_path]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Leer primeras líneas para metadatos
                content = f.read(2000)  # Primeros 2KB
            
            filename = os.path.basename(file_path).replace('.txt', '')
            
            # Extraer título
            title = self._extract_title(content, filename)
            
            # Extraer número y año
            number, year = self._extract_number_year(title, filename)
            
            metadata = {
                'document_id': filename,
                'nombre_archivo': filename,
                'titulo': title,
                'numero': number,
                'año': year,
                'tipo_norma': doc_type,
                'file_path': file_path,
                'file_size': os.path.getsize(file_path)
            }
            
            # Cache result
            self._metadata_cache[file_path] = metadata
            
            return metadata
            
        except Exception as e:
            return {
                'document_id': os.path.basename(file_path).replace('.txt', ''),
                'titulo': f'Error: {str(e)}',
                'tipo_norma': doc_type,
                'error': True
            }
    
    def _extract_title(self, content: str, filename: str) -> str:
        """
        Extraer título del documento
        """
        lines = content.split('\n')
        
        # Para CONPES, buscar el patrón específico
        if 'conpes' in filename.lower():
            for i, line in enumerate(lines[:30]):
                if 'CONPES' in line and re.search(r'\d{4}', line):
                    # Puede estar en múltiples líneas
                    title_parts = []
                    if re.match(r'^CONPES\s*$', line.strip()):
                        # El número puede estar en la siguiente línea
                        if i + 1 < len(lines) and re.match(r'^\d{4}$', lines[i + 1].strip()):
                            return f"CONPES {lines[i + 1].strip()}"
                    elif re.match(r'^CONPES\s+\d{4}', line.strip()):
                        return line.strip()
        
        # Para Resoluciones, buscar patrones específicos
        if 'resolu' in filename.lower():
            for line in lines[:30]:
                line = line.strip()
                # Buscar "RESOLUCIÓN NÚMERO" o similar
                if re.search(r'RESOLUCI[OÓ]N\s+(NÚMERO|N[ÚU]MERO|No\.|#)?\s*\d+', line, re.IGNORECASE):
                    return line
                # Buscar solo número de resolución con año
                if re.search(r'^\d{3,6}\s*.*\d{4}', line) and 'resolu' in filename.lower():
                    return f"Resolución {line}"
        
        # Buscar líneas que parezcan títulos
        for line in lines[:20]:  # Primeras 20 líneas
            line = line.strip()
            
            # Patrones de títulos legales
            if re.match(r'^(LEY|DECRETO|CIRCULAR|RESOLUCIÓN|CONPES).*\d{4}', line, re.IGNORECASE):
                return line
            
            # Si contiene números y año
            if re.search(r'\d{3,4}.*\d{4}', line) and len(line) > 10:
                return line
        
        # Fallback al nombre del archivo
        return filename.replace('_', ' ').title()
    
    def _extract_number_year(self, title: str, filename: str) -> tuple:
        """
        Extraer número y año del título o filename
        """
        # Buscar patrón número/año en título
        match = re.search(r'(\d{3,4}).*?(\d{4})', title)
        if match:
            return match.group(1), int(match.group(2))
        
        # Buscar en filename
        match = re.search(r'(\d{3,4}).*?(\d{4})', filename)
        if match:
            return match.group(1), int(match.group(2))
        
        # Buscar solo año
        year_match = re.search(r'(\d{4})', title + filename)
        if year_match:
            return '', int(year_match.group(1))
        
        return '', 0
    
    def get_document_preview(self, document_id: str, max_chars: int = 500) -> Dict[str, Any]:
        """
        Obtener vista previa del documento
        """
        content_result = self.get_document_content(document_id)
        
        if not content_result['success']:
            return content_result
        
        raw_content = content_result['raw_content']
        
        # Limpiar contenido para preview
        lines = raw_content.split('\n')
        clean_lines = []
        
        for line in lines[:50]:  # Primeras 50 líneas
            line = line.strip()
            if line and not line.startswith('Descargar PDF') and not line.startswith('Fechas'):
                clean_lines.append(line)
            
            if len(' '.join(clean_lines)) > max_chars:
                break
        
        preview = ' '.join(clean_lines)[:max_chars]
        if len(preview) >= max_chars:
            preview += '...'
        
        return {
            'success': True,
            'preview': preview,
            'title': content_result['title'],
            'type': content_result['type']
        }