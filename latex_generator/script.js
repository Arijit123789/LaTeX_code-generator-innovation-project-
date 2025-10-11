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
    const renderedOutputCanvas = document.getElementById('rendered-output-canvas');
    
    // Skeleton loader elements
    const codeSkeleton = document.querySelector('.code-skeleton');
    const previewSkeleton = document.querySelector('.preview-skeleton');

    // Other UI elements
    const copyCodeBtn = document.getElementById('copy-code-btn');
    const menuBtn = document.getElementById('menu-btn');
    const backBtn = document.getElementById('back-btn');
    const sideMenu = document.getElementById('side-menu');
    const closeMenuBtn = document.getElementById('close-menu-btn');
    const aboutUsBtn = document.getElementById('about-us-btn');
    const aboutView = document.getElementById('about-view');
    const closeAboutBtn = document.getElementById('close-about-btn');

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
        // Hide content, show skeletons
        latexOutputContainer.classList.add('hidden');
        renderedOutputCanvas.classList.add('hidden');
        codeSkeleton.classList.remove('hidden');
        previewSkeleton.classList.remove('hidden');

        try {
            const result = await getLatexFromClaude(prompt);
            
            // Populate content
            latexOutput.textContent = result.latexCode;
            renderedOutputCanvas.innerHTML = result.renderedHtml;
            MathJax.typesetPromise([renderedOutputCanvas]);

        } catch (error) {
            console.error("Error from AI:", error);
            renderedOutputCanvas.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            latexOutput.textContent = "An error occurred.";
        } finally {
            // --- END LOADING STATE ---
            // Hide skeletons, show content
            codeSkeleton.classList.add('hidden');
            previewSkeleton.classList.add('hidden');
            latexOutputContainer.classList.remove('hidden');
            renderedOutputCanvas.classList.remove('hidden');
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

    // --- Backend Simulation (No changes here) ---
    async function getLatexFromClaude(prompt) {
        console.log(`Simulating API call for prompt: "${prompt}"`);
        await new Promise(resolve => setTimeout(resolve, 2000)); // Increased delay to better see the loader
        const simulatedResponse = {
            latexCode: "\\int_{a}^{b} x^2 dx = \\frac{b^3}{3} - \\frac{a^3}{3}",
            renderedHtml: "$$\\int_{a}^{b} x^2 dx = \\frac{b^3}{3} - \\frac{a^3}{3}$$"
        };
        if (prompt.toLowerCase() === "error") throw new Error("Simulated API error.");
        return simulatedResponse;
    }
});