graph TD
    A[User Types Prompt] --> B[Flask Serverless Backend]
    B --> C[Gemini AI Generates Raw Code]
    C --> D[Backend Cleans & Strips Markdown]
    D --> E{Frontend Smart Render}
    E -->|Math Formula| F[KaTeX Live Preview]
    E -->|Full Document/Diagram| G[latex.yt API to SVG]
    F --> H[Action: Copy / PDF / Overleaf]
    G --> H
    
    style A fill:#121212,stroke:#8e44ad,color:#fff
    style C fill:#2a1040,stroke:#8e44ad,color:#fff
    style H fill:#8e44ad,stroke:#000,color:#fff
