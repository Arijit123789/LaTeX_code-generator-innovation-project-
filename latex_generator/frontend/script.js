document.addEventListener('DOMContentLoaded', () => {
    
    // --- Element References ---
    const appContainer = document.getElementById('app-container');
    const promptView = document.getElementById('prompt-view');
    const resultsView = document.getElementById('results-view');
    const userPromptInput = document.getElementById('user-prompt');
    const generateBtn = document.getElementById('generate-btn');
    
    // Content elements
    const latexOutputContainer = document.querySelector('#code-panel pre');
    const latexOutput = document.getElementById('latex-output');
    const livePreview = document.getElementById('live-preview');
    
    // Skeleton loader elements
    const codeSkeleton = document.querySelector('.code-skeleton');
    
    // Other UI elements
    const copyCodeBtn = document.getElementById('copy-code-btn');
    const menuBtn = document.getElementById('menu-btn');
    const backBtn = document.getElementById('back-btn');
    const sideMenu = document.getElementById('side-menu');
    const closeMenuBtn = document.getElementById('close-menu-btn');
    const aboutUsBtn = document.getElementById('about-us-btn');
    const aboutView = document.getElementById('about-view');
    const closeAboutBtn = document.getElementById('close-about-btn');

    // --- Initialize CodeMirror Editor ---
    const editor = CodeMirror.fromTextArea(document.getElementById('latex-editor'), {
        lineNumbers: true,
        mode: 'stex',
        theme: 'darcula',
        lineWrapping: true
    });

    // --- Function to update the live preview ---
    const updatePreview = () => {
        const code = editor.getValue();
        if (code.trim() === '') {
            livePreview.innerHTML = '';
            return;
        }
        try {
            katex.render(code, livePreview, {
                throwOnError: false,
                displayMode: true
            });
        } catch (e) {
            console.error("KaTeX Error:", e);
            livePreview.innerHTML = `<span style="color:red;">${e.message}</span>`;
        }
    };

    // --- Add event listener to update preview on change ---
    editor.on('change', updatePreview);

    // --- Main Generation Logic ---
    const handleGeneration = async () => {
        const prompt = userPromptInput.value.trim();
        if (prompt === "") return;

        // --- UI TRANSITION ---
        appContainer.classList.add('search-active');
        promptView.classList.add('hidden');
        resultsView.classList.remove('hidden');
        menuBtn.classList.add('hidden');
        backBtn.classList.remove('hidden');

        // --- START LOADING STATE ---
        latexOutputContainer.classList.add('hidden');
        codeSkeleton.classList.remove('hidden');
        editor.setValue("Generating..."); // Show loading state in editor
        livePreview.innerHTML = '<p>Loading...</p>';

        try {
            const result = await getLatexFromClaude(prompt);
            
            // Populate content
            latexOutput.textContent = result.latexCode;
            editor.setValue(result.latexCode); // This automatically triggers the 'change' event and updates the preview
            editor.refresh(); // Sometimes needed to ensure the editor displays correctly

        } catch (error) {
            console.error("Error from AI:", error);
            editor.setValue(`% An error occurred:\n% ${error.message}`);
            livePreview.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            latexOutput.textContent = "An error occurred.";
        } finally {
            // --- END LOADING STATE ---
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
        navigator.clipboard.writeText(latexOutput.textContent).then(() => {
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