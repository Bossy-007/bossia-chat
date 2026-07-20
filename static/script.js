document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatBox = document.getElementById("chat-box");
    
    let conversationHistory = [];

    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        // Mostrar mensaje del usuario
        appendMessage(message, "user-message");
        userInput.value = "";

        // Crear indicador de carga para la IA
        const loadingDiv = appendMessage("Pensando...", "bot-message");

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    history: conversationHistory
                })
            });

            const data = await response.json();

            if (data.response) {
                loadingDiv.textContent = data.response;
                // Guardar en el historial
                conversationHistory.push({ role: "user", content: message });
                conversationHistory.push({ role: "assistant", content: data.response });
            } else {
                loadingDiv.textContent = "Error: " + (data.error || "No se pudo obtener respuesta.");
            }
        } catch (error) {
            loadingDiv.textContent = "Error de conexión con el servidor.";
        }

        chatBox.scrollTop = chatBox.scrollHeight;
    });

    function appendMessage(text, className) {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", className);
        msgDiv.textContent = text;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        return msgDiv;
    }
});
