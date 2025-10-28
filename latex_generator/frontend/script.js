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

    // --- Function to update the live preview ---
    // --- Function to update the live preview ---
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
            // 2. If KaTeX fails, check if it's an "environment" error
            if (e.message.includes('environment')) {
                // e.g., "No such environment: itemize"
                // e.g., "Unknown environment 'tikzpicture'"
                
                // 3. If so, hide the KaTeX area and show the full "Render" button
                livePreview.classList.add('hidden');
                diagramRenderer.classList.remove('hidden');
            } else {
                // 4. Otherwise, it's a real math syntax error, so show the error
                livePreview.innerHTML = `<span style="color:red;">${e.message}</span>`;
            }
        }
    };

    // --- Function to handle the "Render Diagram" button click ---
    const handleRenderClick = async () => {
        const code = editor.getValue();
        livePreview.innerHTML = '<p>Compiling diagram...</p>';
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
                throw new Error(errorData.error || 'Failed to render diagram.');
            }

            const data = await response.json();
            livePreview.innerHTML = data.svgImage;

        } catch (error) {
            console.error("Diagram Render Error:", error);
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
        // CHANGED: Get text from editor, not the static <pre> block
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

   exportOverleafBtn.addEventListener('click', () => {
        const code = editor.getValue();
        if (code.trim() === '') {
            alert("Editor is empty. Nothing to send to Overleaf.");
            return;
        }

        // --- NEW: Wrap the code in a full document template ---
        // This makes it instantly compilable on Overleaf
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
        
        // Use the 'docs' endpoint which accepts a GET request with a 'snip' parameter
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
