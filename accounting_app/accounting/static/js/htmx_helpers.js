// HTMX Helper Functions

// Initialize tooltips after HTMX swaps
document.body.addEventListener('htmx:afterSwap', function(event) {
    // Re-initialize any JavaScript components here
    initializeComponents();
});

// Show toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    const bgColor = {
        'error': 'bg-red-100 text-red-700 border-red-400',
        'success': 'bg-green-100 text-green-700 border-green-400',
        'warning': 'bg-yellow-100 text-yellow-700 border-yellow-400',
        'info': 'bg-blue-100 text-blue-700 border-blue-400'
    }[type] || 'bg-blue-100 text-blue-700 border-blue-400';
    
    toast.className = `mb-4 rounded-lg p-4 shadow-lg border transform transition-all duration-300 translate-x-full ${bgColor}`;
    
    toast.innerHTML = `
        <div class="flex items-center justify-between">
            <span>${message}</span>
            <button onclick="removeToast(this)" class="mr-2 focus:outline-none">
                <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.remove('translate-x-full');
        toast.classList.add('translate-x-0');
    }, 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        removeToast(toast.querySelector('button'));
    }, 5000);
}

function removeToast(button) {
    const toast = button.closest('div').parentElement;
    toast.classList.add('translate-x-full');
    setTimeout(() => toast.remove(), 300);
}

// Handle HTMX responses
document.body.addEventListener('htmx:afterRequest', function(event) {
    if (event.detail.xhr && event.detail.xhr.response) {
        try {
            const data = JSON.parse(event.detail.xhr.response);
            if (data.message) {
                showToast(data.message, event.detail.successful ? 'success' : 'error');
            }
            if (data.redirect) {
                window.location.href = data.redirect;
            }
        } catch (e) {
            // Response is not JSON
        }
    }
});

// Handle form validation
function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('border-red-500');
            isValid = false;
        } else {
            input.classList.remove('border-red-500');
        }
    });
    
    return isValid;
}

// Format numbers with thousands separator
function formatNumber(num) {
    return new Intl.NumberFormat('ar-EG').format(num);
}

// Initialize components
function initializeComponents() {
    // Format all numbers with data-format-number attribute
    document.querySelectorAll('[data-format-number]').forEach(el => {
        const num = parseFloat(el.textContent);
        if (!isNaN(num)) {
            el.textContent = formatNumber(num);
        }
    });
    
    // Initialize date inputs with today's date if empty
    document.querySelectorAll('input[type="date"]:not([value])').forEach(input => {
        if (!input.value) {
            input.value = new Date().toISOString().split('T')[0];
        }
    });
}

// Initial load
document.addEventListener('DOMContentLoaded', initializeComponents);