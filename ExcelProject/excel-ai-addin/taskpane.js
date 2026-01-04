// Generate a unique session ID for this Excel session
const sessionId = 'excel-session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

Office.onReady((info) => {
    if (info.host === Office.HostType.Excel) {
        // Wait for DOM to be ready
        setTimeout(() => {
            const runButton = document.getElementById("run-button");
            const agentSelect = document.getElementById("agent-select");
            const promptInput = document.getElementById("prompt-input");

            if (runButton) {
                runButton.onclick = runAnalysis;
            }
            if (agentSelect) {
                agentSelect.onchange = updateAgentDescription;
                // Initialize with default description
                updateAgentDescription();
            }
            if (promptInput) {
                // Auto-resize textarea
                promptInput.addEventListener('input', function() {
                    this.style.height = 'auto';
                    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
                });
                
                // Send on Enter (but allow Shift+Enter for new lines)
                promptInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        runAnalysis();
                    }
                });
            }
            
            // Load conversation history on startup
            loadConversationHistory();
        }, 100);
    }
});

function getBackendBaseUrl() {
    // Hardcoded backend URL for current session
    return 'https://1f362419eeb4.ngrok-free.app';
}

function updateAgentDescription() {
    const agentSelect = document.getElementById("agent-select");
    const statusText = document.getElementById("status-text");

    if (!agentSelect || !statusText) {
        console.log("Elements not found for agent description update");
        return;
    }

    const descriptions = {
        "assistant": "Ready to help with anything",
        "graph": "Ready to create visualizations",
        "cleaning": "Ready to clean your data",
        "formula": "Ready to generate formulas"
    };

    statusText.textContent = descriptions[agentSelect.value];
}

function sendSuggestion(text) {
    const promptInput = document.getElementById("prompt-input");
    if (promptInput) {
        promptInput.value = text;
        promptInput.style.height = 'auto';
        promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + 'px';
        runAnalysis();
    }
}

function addMessage(content, isUser = false, agent = null) {
    const chatMessages = document.getElementById("chat-messages");
    if (!chatMessages) return;

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    
    const now = new Date();
    const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    // Format content with proper line breaks
    const formattedContent = content.replace(/\n/g, '<br>');
    
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <div class="avatar-icon">${isUser ? '👤' : '+'}</div>
        </div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${isUser ? 'You' : 'Excel AI'}</span>
                <span class="message-time">${timeString}</span>
                ${agent && !isUser ? `<span class="message-agent">(${agent})</span>` : ''}
            </div>
            <div class="message-text">${formattedContent}</div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function loadConversationHistory() {
    try {
        const apiBase = getBackendBaseUrl();
        const response = await fetch(`${apiBase}/api/conversation/${sessionId}`);
        
        if (response.ok) {
            const conversation = await response.json();
            
            // Clear existing messages except the welcome message
            const chatMessages = document.getElementById("chat-messages");
            if (chatMessages) {
                // Keep only the first message (welcome message)
                const welcomeMessage = chatMessages.querySelector('.message');
                chatMessages.innerHTML = '';
                if (welcomeMessage) {
                    chatMessages.appendChild(welcomeMessage);
                }
                
                // Add conversation history
                if (conversation.messages && conversation.messages.length > 0) {
                    conversation.messages.forEach(msg => {
                        if (msg.role === 'user') {
                            addMessage(msg.content, true);
                        } else if (msg.role === 'assistant') {
                            addMessage(msg.content, false, msg.agent);
                        }
                    });
                }
            }
        }
    } catch (error) {
        console.log('Could not load conversation history:', error);
    }
}

async function saveMessageToHistory(role, content, agent = null) {
    try {
        const apiBase = getBackendBaseUrl();
        await fetch(`${apiBase}/api/conversation/${sessionId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                role: role,
                content: content,
                agent: agent
            })
        });
    } catch (error) {
        console.log('Could not save message to history:', error);
    }
}

function showStatus(message, type = 'processing') {
    const status = document.getElementById("status");
    if (status) {
        status.textContent = message;
        status.className = `status-panel ${type}`;
        status.classList.remove('hidden');
    }
}

function hideStatus() {
    const status = document.getElementById("status");
    if (status) {
        status.classList.add('hidden');
    }
}

async function runAnalysis() {
    try {
        const promptInput = document.getElementById("prompt-input");
        const agentSelect = document.getElementById("agent-select");
        
        if (!promptInput || !agentSelect) {
            throw new Error("Required UI elements not found");
        }

        const prompt = promptInput.value.trim();
        if (!prompt) {
            return;
        }

        // Add user message to chat
        addMessage(prompt, true);
        
        // Clear input and reset height
        promptInput.value = '';
        promptInput.style.height = 'auto';
        
        // Show processing status
        showStatus("Processing your request...", 'processing');

        await Excel.run(async (context) => {
            const range = context.workbook.getSelectedRange();
            range.load("values");
            await context.sync();

            const data = range.values;
            const agentSelect = document.getElementById("agent-select");
            const selectedAgent = agentSelect ? agentSelect.value : 'assistant';
            
            // Handle empty or no data selected
            if (!data || data.length === 0 || (data.length === 1 && data[0].length === 0)) {
                // For general questions without data, use a simple response
                addMessage("I can help with Excel questions! For data analysis, please select some data first.", false, selectedAgent);
                hideStatus();
                return;
            }

            const apiBase = getBackendBaseUrl();
            const response = await fetch(`${apiBase}/api/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    prompt: prompt, 
                    data: JSON.stringify(data),
                    agent: selectedAgent,
                    session_id: sessionId
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Hide status
            hideStatus();

            if (result.image) {
                // Handle chart creation
                const sheet = context.workbook.worksheets.getActiveWorksheet();
                sheet.shapes.addImage(result.image);
                addMessage("✅ Chart created and inserted into your spreadsheet!");
            } else if (result.action === "replace_data" && result.cleaned_data) {
                // Handle data cleaning
                const cleanedData = result.cleaned_data;
                range.values = cleanedData;
                addMessage(`✅ Data cleaned successfully! ${result.result}`);
            } else if (result.action === "update_cells" && result.cell_updates) {
                // Handle cell updates
                const cellUpdates = result.cell_updates;
                const startRow = range.rowIndex;
                const startCol = range.columnIndex;
                
                for (const update of cellUpdates) {
                    const targetRow = startRow + update.row;
                    const targetCol = startCol + update.col;
                    
                    const cell = range.worksheet.getCell(targetRow, targetCol);
                    cell.values = [[update.value]];
                }
                
                addMessage(`✅ Updated ${cellUpdates.length} cells! ${result.result}`);
            } else if (result.action === "no_changes") {
                addMessage(`ℹ️ ${result.result}`);
            } else if (result.result) {
                // Handle general responses
                addMessage(result.result);
            }
            
            await context.sync();
        });
    } catch (error) {
        hideStatus();
        addMessage(`❌ Error: ${error.message}`);
        console.error('Analysis error:', error);
    }
}