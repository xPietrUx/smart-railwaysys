<div class="skeleton-wrapper" aria-busy="true" aria-label="Ładowanie systemu">
    <!--  pasek nawigacji -->
    <header class="sk-header">
        <div class="sk-bubble"></div>
        <div class="sk-pills">
            <div class="sk-pill"></div>
            <div class="sk-pill"></div>
            <div class="sk-pill"></div>
            <div class="sk-pill"></div>
        </div>
        <div class="sk-actions">
            <div class="sk-circle"></div>
            <div class="sk-circle"></div>
            <div class="sk-btn"></div>
        </div>
    </header>

    <!--  panele w narożnikach -->
    <div class="sk-corner top-left">
        <div class="sk-searchbar"></div>
    </div>

    <div class="sk-corner top-right">
        <div class="sk-card"></div>
        <div class="sk-circle-large"></div>
    </div>

    <div class="sk-corner bottom-right">
        <div class="sk-zoom">
            <div class="sk-circle-sm"></div>
            <div class="sk-circle-sm"></div>
            <div class="sk-circle-sm"></div>
        </div>
    </div>
</div>

<style>
    .skeleton-wrapper {
        position: absolute;
        inset: 0;
        z-index: 120;
        background: #141414;
        overflow: hidden;
        pointer-events: all;
    }

    :global(html.light-mode) .skeleton-wrapper {
        background: #f4f5f3;
    }

    /* bloczki */
    .sk-bubble, .sk-pill, .sk-circle, .sk-btn,
    .sk-searchbar, .sk-card, .sk-circle-large, .sk-circle-sm {
        background: rgba(255, 255, 255, 0.04);
        position: relative;
        overflow: hidden;
        animation: pulse 1.6s ease-in-out infinite;
    }

    :global(html.light-mode) .sk-bubble,
    :global(html.light-mode) .sk-pill,
    :global(html.light-mode) .sk-circle,
    :global(html.light-mode) .sk-btn,
    :global(html.light-mode) .sk-searchbar,
    :global(html.light-mode) .sk-card,
    :global(html.light-mode) .sk-circle-large,
    :global(html.light-mode) .sk-circle-sm {
        background: rgba(0, 0, 0, 0.05);
    }

    @keyframes pulse {
        0%, 100% { opacity: 0.45; }
        50% { opacity: 0.9; }
    }

    /* uklad */
    .sk-header {
        height: 76px;
        padding: 0 clamp(20px, 5vw, 72px);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .sk-bubble { width: 36px; height: 36px; border-radius: 50%; }
    .sk-pills { display: flex; gap: 8px; }
    .sk-pill { width: 68px; height: 28px; border-radius: 8px; }
    .sk-actions { display: flex; gap: 10px; align-items: center; }
    .sk-circle { width: 34px; height: 34px; border-radius: 50%; }
    .sk-btn { width: 90px; height: 32px; border-radius: 8px; }

    /*  panele */
    .sk-corner { position: absolute; pointer-events: none; }
    .top-left { top: 96px; left: 28px; }
    .top-right {
        top: 96px;
        right: 28px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        align-items: flex-end;
    }
    .bottom-right { bottom: 28px; right: 28px; }

    .sk-searchbar { width: 380px; height: 44px; border-radius: 999px; }
    .sk-card { width: 280px; height: 320px; border-radius: 14px; }
    .sk-circle-large { width: 140px; height: 140px; border-radius: 50%; margin-right: 70px; }
    .sk-zoom { display: flex; flex-direction: column; gap: 10px; }
    .sk-circle-sm { width: 40px; height: 40px; border-radius: 50%; }

    @media (max-width: 900px) {
        .sk-pills, .top-right { display: none; }
        .sk-searchbar { width: 260px; }
    }
</style>