// Toast notification system
const Toast = {
    // Configuration
    defaultDuration: 5000,
    maxToasts: 3,

    // Icons for different types
    icons: {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    },

    /**
     * Show a toast notification
     * @param {string} type - Type of toast: 'success', 'error', 'warning', 'info'
     * @param {string} title - Toast title
     * @param {string} message - Toast message (optional)
     * @param {number} duration - Duration in milliseconds (optional)
     */
    show: function(type, title, message = '', duration = null) {
        const container = document.getElementById('toast-container');
        if (!container) {
            console.error('Toast container not found');
            return;
        }

        // Limit number of toasts
        const existingToasts = container.querySelectorAll('.toast');
        if (existingToasts.length >= this.maxToasts) {
            existingToasts[0].remove();
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        // Create icon
        const icon = document.createElement('div');
        icon.className = 'toast-icon';
        icon.textContent = this.icons[type] || this.icons.info;

        // Create content
        const content = document.createElement('div');
        content.className = 'toast-content';

        const titleElement = document.createElement('div');
        titleElement.className = 'toast-title';
        titleElement.textContent = title;
        content.appendChild(titleElement);

        if (message) {
            const messageElement = document.createElement('div');
            messageElement.className = 'toast-message';
            messageElement.textContent = message;
            content.appendChild(messageElement);
        }

        // Create close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.innerHTML = '×';
        closeBtn.onclick = () => this.hide(toast);

        // Assemble toast
        toast.appendChild(icon);
        toast.appendChild(content);
        toast.appendChild(closeBtn);

        // Add progress bar if duration is set
        const toastDuration = duration || this.defaultDuration;
        if (toastDuration > 0) {
            const progress = document.createElement('div');
            progress.className = 'toast-progress';
            progress.style.animationDuration = `${toastDuration}ms`;
            toast.appendChild(progress);
        }

        // Add to container
        container.appendChild(toast);

        // Auto-hide after duration
        if (toastDuration > 0) {
            setTimeout(() => this.hide(toast), toastDuration);
        }

        return toast;
    },

    /**
     * Hide a toast notification
     * @param {HTMLElement} toast - Toast element to hide
     */
    hide: function(toast) {
        if (!toast) return;

        toast.classList.add('hiding');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    },

    /**
     * Show success toast
     */
    success: function(title, message = '', duration = null) {
        return this.show('success', title, message, duration);
    },

    /**
     * Show error toast
     */
    error: function(title, message = '', duration = null) {
        return this.show('error', title, message, duration);
    },

    /**
     * Show warning toast
     */
    warning: function(title, message = '', duration = null) {
        return this.show('warning', title, message, duration);
    },

    /**
     * Show info toast
     */
    info: function(title, message = '', duration = null) {
        return this.show('info', title, message, duration);
    },

    /**
     * Clear all toasts
     */
    clearAll: function() {
        const container = document.getElementById('toast-container');
        if (container) {
            container.innerHTML = '';
        }
    }
};

// Make Toast globally available
window.Toast = Toast;
