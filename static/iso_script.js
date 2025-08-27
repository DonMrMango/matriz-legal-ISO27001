// script.js para ISO Chatbot (versión integrada con matriz-legal)

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const responseTimeElement = document.getElementById('response-time');
    const apiStatusElement = document.getElementById('apiStatus');
    const detailsModal = new bootstrap.Modal(document.getElementById('detailsModal'));
    
    // Variables para seguimiento de consultas
    let currentMessageId = 0;
    let lastQueryDetails = null;
    let isWaitingForResponse = false;
    
    // Inicializar
    userInput.focus();
    
    // Manejar envío del formulario
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const query = userInput.value.trim();
        if (!query || isWaitingForResponse) return;
        
        // Limpiar input
        userInput.value = '';
        
        // Añadir mensaje del usuario
        addMessage(query, 'user');
        
        // Mostrar indicador de escritura
        const typingIndicator = addTypingIndicator();
        
        // Establecer estado de espera
        isWaitingForResponse = true;
        userInput.disabled = true;
        
        // Enviar consulta al servidor
        sendQuery(query, typingIndicator);
    });
    
    // Función para añadir mensaje al chat
    function addMessage(content, sender, details = null) {
        const messageId = 'msg-' + (++currentMessageId);
        const messageDiv = document.createElement('div');
        messageDiv.id = messageId;
        messageDiv.className = `message ${sender}-message`;
        
        let messageHTML = `<div class="message-content">`;
        
        if (sender === 'assistant') {
            // Procesar markdown en respuestas del asistente
            messageHTML += marked.parse(content);
            
            // Añadir botón de detalles si hay información adicional
            if (details && details.context && details.context.length > 0) {
                lastQueryDetails = details;
                messageHTML += `
                    <div class="mt-2 text-end">
                        <button class="btn btn-sm btn-outline-secondary" onclick="showDetails()">
                            <i class="bi bi-info-circle"></i> Ver contexto completo
                        </button>
                    </div>
                `;
            }
        } else {
            // Texto plano para mensajes del usuario
            messageHTML += `<p>${escapeHTML(content)}</p>`;
        }
        
        messageHTML += `</div>`;
        messageDiv.innerHTML = messageHTML;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageId;
    }
    
    // Función para añadir indicador de escritura
    function addTypingIndicator() {
        const indicatorDiv = document.createElement('div');
        indicatorDiv.className = 'typing-indicator';
        indicatorDiv.innerHTML = `
            <span></span>
            <span></span>
            <span></span>
        `;
        
        chatMessages.appendChild(indicatorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return indicatorDiv;
    }
    
    // Función para enviar consulta al servidor
    function sendQuery(query, typingIndicator) {
        // Actualizar estado de API
        apiStatusElement.innerHTML = '<i class="bi bi-arrow-repeat text-warning"></i> Procesando';
        
        fetch('/api/iso/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error en la respuesta del servidor');
            }
            return response.json();
        })
        .then(data => {
            // Remover indicador de escritura
            typingIndicator.remove();
            
            // Añadir respuesta del asistente
            addMessage(data.response, 'assistant', data);
            
            // Mostrar tiempo de respuesta
            responseTimeElement.textContent = `Tiempo: ${data.elapsed_time}s`;
            
            // Actualizar estado
            apiStatusElement.innerHTML = '<i class="bi bi-circle-fill text-success"></i> Conectado';
            
            // Restaurar estado de entrada
            isWaitingForResponse = false;
            userInput.disabled = false;
            userInput.focus();
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Remover indicador de escritura
            typingIndicator.remove();
            
            // Mostrar mensaje de error
            const errorMessage = 'Lo siento, ocurrió un error al procesar tu consulta. Por favor, intenta de nuevo.';
            addMessage(errorMessage, 'assistant');
            
            // Actualizar estado
            apiStatusElement.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> Error';
            
            // Restaurar estado de entrada
            isWaitingForResponse = false;
            userInput.disabled = false;
            userInput.focus();
        });
    }
    
    // Función para mostrar detalles de la consulta
    window.showDetails = function() {
        if (!lastQueryDetails) return;
        
        // Actualizar contenido del contexto
        updateContextTab(lastQueryDetails.context || []);
        
        // Mostrar modal
        detailsModal.show();
    };
    
    // Función para actualizar pestaña de contexto
    function updateContextTab(context) {
        const contextContent = document.getElementById('context-content');
        
        if (!context.length) {
            contextContent.innerHTML = '<p class="text-muted">No hay contexto disponible para esta consulta.</p>';
            return;
        }
        
        let html = '<div class="context-item" style="white-space: pre-wrap; word-break: break-word;">';
        
        context.forEach((item, index) => {
            // Eliminar el mensaje de truncado si existe
            let fullContext = item;
            if (fullContext.includes("[Contenido truncado]")) {
                fullContext = fullContext.replace(/\.\.\.\n\[Contenido truncado\]/g, "");
            }
            
            html += escapeHTML(fullContext);
            
            // Añadir separador entre múltiples contextos
            if (index < context.length - 1) {
                html += '\n\n---\n\n';
            }
        });
        
        html += '</div>';
        
        contextContent.innerHTML = html;
    }
    
    // Función para establecer consulta de ejemplo
    window.setQuery = function(query) {
        userInput.value = query;
        userInput.focus();
    };
    
    // Función para escapar HTML
    function escapeHTML(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});