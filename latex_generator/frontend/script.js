document.addEventListener('DOMContentLoaded', () => {
    
    // ADDED: Make jsPDF available globally
    window.jsPDF = window.jspdf.jsPDF;

    // --- Element References ---
    const appContainer = document.getElementById('app-container');
    const promptView = document.getElementById('prompt-view');
    const resultsView = document.getElementById('results-view');
    const userPromptInput = document.getElementById('user-prompt');
    const generateBtn = document.getElementById('generate-btn');
    const latexOutputContainer = document.querySelector('#code-panel pre');
    const latexOutput = document.getElementById('latex-output');
    const livePreview = document.getElementById('live-preview');
    const codeSkeleton = document.querySelector('.code-skeleton');
    const copyCodeBtn = document.getElementById('copy-code-btn');
    const menuBtn = document.getElementById('menu-btn');
    const backBtn = document.getElementById('back-btn');
    const sideMenu = document.getElementById('side-menu');
    const closeMenuBtn = document.getElementById('close-menu-btn');
    const aboutUsBtn = document.getElementById('about-us-btn');
    const aboutView = document.getElementById('about-view');
    const closeAboutBtn = document.getElementById('close-about-btn');
    const diagramRenderer = document.getElementById('diagram-renderer');
    const renderBtn = document.getElementById('render-btn');

    // ADDED: New export button references
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const exportOverleafBtn = document.getElementById('export-overleaf-btn');

    // --- Initialize CodeMirror Editor ---
    const editor = CodeMirror.fromTextArea(document.getElementById('latex-editor'), {
        lineNumbers: true,
        mode: 'stex',
        theme: 'darcula',
        lineWrapping: true
    });

    // --- UPDATED: Function to update the live preview ---
    // This now includes your new friendly error message logic.
    const updatePreview = () => {
        const code = editor.getValue();
        diagramRenderer.classList.add('hidden');
        livePreview.classList.remove('hidden');

        if (code.trim() === '') {
            livePreview.innerHTML = '';
            return;
        }

        try {
            // 1. Try to render with KaTeX
            katex.render(code, livePreview, {
                throwOnError: true,
                displayMode: true
            });
        } catch (e) {
            // 2. CHECK 1: Is it a full document? (Your new logic)
            if (code.trim().startsWith('\\documentclass')) {
                const friendlyMessage = `
                <div style="color: #FFB300; padding: 10px; font-family: sans-serif; text-align: left; font-size: 0.9rem;">
                  <strong>Preview Error!</strong>
                  <p>This previewer can only render <b>math formulas</b>.</p>
                  <p>It looks like you've generated a <b>full document</b> (starting with <code>\\documentclass</code>).</p>
                  <hr style="border-color: #555; margin: 10px 0;">
                  <p>Please use the <b>Overleaf</b> or <b>PDF</b> buttons to compile the full document.</p>
                </div>
              `;
                livePreview.innerHTML = friendlyMessage;
            } 
            // 3. CHECK 2: Is it an "environment" that needs the "Render" button?
            else if (e.message.includes('environment')) {
                livePreview.classList.add('hidden');
                diagramRenderer.classList.remove('hidden');
            } 
            // 4. CHECK 3: Otherwise, it's just a simple math typo
            else {
                livePreview.innerHTML = `<span style="color:red;">${e.message}</span>`;
            }
        }
    };

    editor.on('change', updatePreview);

    // --- Function to handle the "Render Diagram" button click ---
    const handleRenderClick = async () => {
        const code = editor.getValue();
        livePreview.innerHTML = '<p>Compiling...</p>'; // Updated text
        livePreview.classList.remove('hidden');
        diagramRenderer.classList.add('hidden');

        try {
            const response = await fetch('/api/render', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ latexCode: code })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to render.');
            }

            const data = await response.json();
            livePreview.innerHTML = data.svgImage;

        } catch (error) {
            console.error("Render Error:", error);
            livePreview.innerHTML = `<p style="color:red;">${error.message}</p>`;
        }
    };

    renderBtn.addEventListener('click', handleRenderClick);

    // --- Main Generation Logic ---
    const handleGeneration = async () => {
        const prompt = userPromptInput.value.trim();
        if (prompt === "") return;

        appContainer.classList.add('search-active');
        promptView.classList.add('hidden');
        resultsView.classList.remove('hidden');
        menuBtn.classList.add('hidden');
        backBtn.classList.remove('hidden');

        latexOutputContainer.classList.add('hidden');
        codeSkeleton.classList.remove('hidden');
        editor.setValue("Generating...");
        livePreview.innerHTML = '<p>Loading...</p>';

        try {
            const result = await getLatexFromClaude(prompt);
            
            latexOutput.textContent = result.latexCode;
            editor.setValue(result.latexCode);
            editor.refresh(); // Important for CodeMirror

            // This call fixes the "Loading..." bug
            updatePreview(); 

        } catch (error) {
            console.error("Error from AI:", error);
            editor.setValue(`% An error occurred:\n% ${error.message}`);
            livePreview.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            latexOutput.textContent = "An error occurred.";
        } finally {
            codeSkeleton.classList.add('hidden');
            latexOutputContainer.classList.remove('hidden');
        }
    };
    
    // --- Event Listeners ---
    generateBtn.addEventListener('click', handleGeneration);
    userPromptInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleGeneration();
    });

    copyCodeBtn.addEventListener('click', () => {
        // UPDATED: Get text from editor
        navigator.clipboard.writeText(editor.getValue()).then(() => {
            copyCodeBtn.textContent = 'Copied!';
            setTimeout(() => { copyCodeBtn.textContent = 'Copy'; }, 2000);
        });
    });

    backBtn.addEventListener('click', () => {
        appContainer.classList.remove('search-active');
        resultsView.classList.add('hidden');
        promptView.classList.remove('hidden');
        backBtn.classList.add('hidden');
        menuBtn.classList.remove('hidden');
        userPromptInput.focus();
    });

    menuBtn.addEventListener('click', () => sideMenu.classList.add('open'));
    closeMenuBtn.addEventListener('click', () => sideMenu.classList.remove('open'));

    aboutUsBtn.addEventListener('click', () => {
        aboutView.classList.remove('hidden');
        sideMenu.classList.remove('open');
    });
    closeAboutBtn.addEventListener('click', () => aboutView.classList.add('hidden'));
    
    // --- ADDED: Export Listeners ---

    exportPdfBtn.addEventListener('click', () => {
        const code = editor.getValue();
        if (code.trim() === '') {
            alert("Editor is empty. Nothing to export.");
            return;
        }

        try {
            const doc = new window.jsPDF();
            doc.setFont('Courier', 'normal');
            doc.setFontSize(12);
            const lines = doc.splitTextToSize(code, 180); // 180mm width
            doc.text(lines, 10, 10); // 10mm margin
            doc.save('latex-code.pdf');
        } catch (e) {
            console.error("Error generating PDF:", e);
            alert("An error occurred while generating the PDF.");
        }
    });

    exportOverleafBtn.addEventListener('click', () => {
        const code = editor.getValue();
        if (code.trim() === '') {
            alert("Editor is empty. Nothing to send to Overleaf.");
            return;
        }

        // --- UPDATED: Wrap code in a full document ---
        const fullLatexCode = `\\documentclass{article}
\\usepackage{amsmath}
\\usepackage{tikz}
\\usepackage{graphicx}
\\pagestyle{empty}

\\begin{document}

${code}

\\end{document}
`;
        
        // URL-encode the full template
        const encodedCode = encodeURIComponent(fullLatexCode);
        
        // Use the 'docs' endpoint which accepts a GET request
        const overleafUrl = `https://www.overleaf.com/docs?snip=${encodedCode}`;

        // Open the URL in a new tab
        window.open(overleafUrl, '_blank');
    });

    // --- Backend Function for Vercel ---
    async function getLatexFromClaude(prompt) {
        const API_ENDPOINT = '/api/generate';
        
        try {
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: prompt })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        
        } catch (error) {
            console.error("Failed to fetch from backend:", error);
            throw error;
        }
    }
});
