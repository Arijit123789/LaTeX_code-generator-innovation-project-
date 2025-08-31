document.addEventListener('DOMContentLoaded', () => {

    // --- Section 1: Landing Page Elements & Animations ---
    const landingPage = document.getElementById('landing-page');
    const startButton = document.getElementById('start-button');
    const generatorInterface = document.getElementById('generator-interface');
    const aboutUsBtn = document.getElementById('about-us-btn');
    const latexRainContainer = document.querySelector('.latex-rain');

    // LaTeX Rain Animation
    const latexSymbols = ['\\sum', '\\int', '\\alpha', '\\beta', '\\gamma', '\\delta', 'x^2', '\\frac{a}{b}', '\\sqrt{x}', '\\lim_{x\\to\\infty}', '\\sin(x)', '\\cos(x)', '\\log(n)'];

    function createLatexChar() {
        const char = document.createElement('div');
        char.classList.add('latex-char');
        char.innerText = latexSymbols[Math.floor(Math.random() * latexSymbols.length)];
        char.style.left = `${Math.random() * 100}vw`;
        char.style.animationDuration = `${Math.random() * 5 + 5}s`;
        char.style.animationDelay = `${Math.random() * 3}s`;
        latexRainContainer.appendChild(char);

        setTimeout(() => {
            char.remove();
        }, 10000);
    }

    const rainInterval = setInterval(createLatexChar, 150);

    // Start Button Click Event
    startButton.addEventListener('click', () => {
        clearInterval(rainInterval);
        landingPage.style.opacity = '0';
        landingPage.style.transform = 'scale(0.9)';
        setTimeout(() => {
            landingPage.classList.add('hidden');
            document.body.style.overflow = 'auto';
            generatorInterface.classList.remove('hidden');
            aboutUsBtn.classList.remove('hidden');
            generatorInterface.style.animation = 'fadeIn 1s';
            aboutUsBtn.style.animation = 'fadeIn 1s';
        }, 1000);
    });

    // --- Section 2: Generator Interface Logic (Connects to Real AI) ---
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    let conversationHistory = []; // This will store the chat history for follow-up questions

    // Handles sending the user's prompt to the backend API
    const handleUserInput = async () => {
        const query = userInput.value.trim();
        if (query === "") return;

        addMessage(query, 'user');
        userInput.value = '';

        try {
            // IMPORTANT: Make sure the port number (e.g., 5000 or 5001) matches your running Python server.
            const response = await fetch('http://127.0.0.1:5001/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: query,
                    history: conversationHistory
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Add the AI's complex response to the page
            addAiMessage(data.response);
            
            // Update the conversation history with the new data from the server
            conversationHistory = data.history;

        } catch (error) {
            console.error("Error fetching from API:", error);
            addAiMessage("Sorry, I encountered an error. Please try again.");
        }
    };

    sendBtn.addEventListener('click', handleUserInput);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleUserInput();
        }
    });
    
    // This function parses the AI's response and prepares it for display
    function addAiMessage(responseText) {
        const mermaidRegex = /```mermaid([\s\S]*?)```/;
        const mermaidMatch = responseText.match(mermaidRegex);

        let codeToDisplay = responseText.replace(mermaidRegex, '').trim();
        let previewHtml;

        if (mermaidMatch) {
            const mermaidCode = mermaidMatch[1].trim();
            previewHtml = `<div class="mermaid">${mermaidCode}</div>`;
            codeToDisplay = mermaidCode;
        } else {
            previewHtml = `<div>${responseText}</div>`;
        }

        const aiContent = {
            text: "Here's what I generated for you:",
            code: codeToDisplay,
            previewHtml: previewHtml
        };
        
        addMessage(aiContent, 'ai');

        if (mermaidMatch) {
            // This tells the Mermaid library to find and render the diagram
            mermaid.run({
                nodes: document.querySelectorAll('.mermaid')
            });
        }
    }

    // This function builds the HTML for all messages
    function addMessage(content, sender) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('message', `${sender}-message`);

        if (sender === 'ai') {
            messageWrapper.innerHTML = `
                <p>${content.text}</p>
                <div class="response-columns">
                    <div class="code-column">
                        <div class="column-title">Generated Code</div>
                        <div class="latex-code">${content.code.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</div>
                    </div>
                    <div class="preview-column">
                        <div class="column-title">Visual Output</div>
                        <div class="rendered-preview">${content.previewHtml}</div>
                    </div>
                </div>
            `;
            MathJax.typesetPromise();
        } else {
            messageWrapper.innerHTML = `<p>${content}</p>`;
        }
        chatBox.insertBefore(messageWrapper, chatBox.firstChild);
    }


    // --- Section 3: About Us Logic ---
    const aboutSection = document.getElementById('about-section');
    const backToGeneratorBtn = document.getElementById('back-to-generator');
    const teamMembers = document.querySelectorAll('.team-member');

    aboutUsBtn.addEventListener('click', () => {
        aboutSection.classList.remove('hidden');
    });

    backToGeneratorBtn.addEventListener('click', () => {
        aboutSection.classList.add('hidden');
    });

    teamMembers.forEach(member => {
        member.addEventListener('click', () => {
            if (member.classList.contains('active')) {
                member.classList.remove('active');
            } else {
                teamMembers.forEach(m => m.classList.remove('active'));
                member.classList.add('active');
            }
        });
    });

});