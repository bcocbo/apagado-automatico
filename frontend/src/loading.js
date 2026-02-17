// Loading Indicator Manager
class LoadingManager {
    constructor() {
        this.activeRequests = 0;
        this.loadingElement = null;
        this.init();
    }

    init() {
        // Create loading overlay
        this.loadingElement = document.createElement('div');
        this.loadingElement.id = 'loading-overlay';
        this.loadingElement.className = 'loading-overlay';
        this.loadingElement.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <div class="loading-text mt-2">Cargando...</div>
            </div>
        `;
        this.loadingElement.style.display = 'none';
        document.body.appendChild(this.loadingElement);

        // Add styles
        this.addStyles();
    }

    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }

            .loading-spinner {
                background: white;
                padding: 2rem;
                border-radius: 0.5rem;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }

            .loading-text {
                color: #333;
                font-weight: 500;
            }

            .btn-loading {
                position: relative;
                pointer-events: none;
                opacity: 0.6;
            }

            .btn-loading::after {
                content: "";
                position: absolute;
                width: 16px;
                height: 16px;
                top: 50%;
                left: 50%;
                margin-left: -8px;
                margin-top: -8px;
                border: 2px solid #ffffff;
                border-radius: 50%;
                border-top-color: transparent;
                animation: spinner 0.6s linear infinite;
            }

            @keyframes spinner {
                to {
                    transform: rotate(360deg);
                }
            }
        `;
        document.head.appendChild(style);
    }

    show() {
        this.activeRequests++;
        if (this.activeRequests > 0) {
            this.loadingElement.style.display = 'flex';
        }
    }

    hide() {
        this.activeRequests = Math.max(0, this.activeRequests - 1);
        if (this.activeRequests === 0) {
            this.loadingElement.style.display = 'none';
        }
    }

    showButton(button) {
        if (button) {
            button.classList.add('btn-loading');
            button.disabled = true;
        }
    }

    hideButton(button) {
        if (button) {
            button.classList.remove('btn-loading');
            button.disabled = false;
        }
    }
}

// Create singleton instance
const loadingManager = new LoadingManager();

// Register with API client
if (typeof apiClient !== 'undefined') {
    apiClient.onLoadingChange((isLoading) => {
        if (isLoading) {
            loadingManager.show();
        } else {
            loadingManager.hide();
        }
    });
}
