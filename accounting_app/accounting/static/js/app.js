// تطبيق المحاسبة - JavaScript رئيسي

// تهيئة HTMX
document.addEventListener('DOMContentLoaded', function() {
    // إعدادات HTMX
    document.body.addEventListener('htmx:configRequest', function(event) {
        // إضافة CSRF token لجميع الطلبات
        event.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
    });
    
    // عرض رسائل النجاح/الخطأ
    document.body.addEventListener('htmx:afterSwap', function(event) {
        // تشغيل أي رسائل توست
        showToasts();
        
        // تحديث الأرقام العربية
        updateArabicNumbers();
        
        // تهيئة التواريخ
        initializeDatePickers();
    });
    
    // تهيئة العناصر عند التحميل
    initializeApp();
});

// الحصول على CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// تهيئة التطبيق
function initializeApp() {
    // تهيئة منتقي التواريخ
    initializeDatePickers();
    
    // تهيئة الإشعارات
    initializeNotifications();
    
    // تهيئة البحث المباشر
    initializeLiveSearch();
    
    // تهيئة الفلاتر
    initializeFilters();
    
    // تحديث الأرقام العربية
    updateArabicNumbers();
}

// تهيئة منتقي التواريخ
function initializeDatePickers() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        // يمكن إضافة مكتبة تواريخ عربية هنا
        input.addEventListener('change', function() {
            // تنسيق التاريخ بالعربية
            const date = new Date(this.value);
            const arabicDate = formatArabicDate(date);
            
            // عرض التاريخ بالعربية بجانب الحقل
            let dateDisplay = this.nextElementSibling;
            if (!dateDisplay || !dateDisplay.classList.contains('arabic-date')) {
                dateDisplay = document.createElement('span');
                dateDisplay.classList.add('arabic-date', 'text-sm', 'text-gray-600', 'mr-2');
                this.parentNode.insertBefore(dateDisplay, this.nextSibling);
            }
            dateDisplay.textContent = arabicDate;
        });
    });
}

// تنسيق التاريخ بالعربية
function formatArabicDate(date) {
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long'
    };
    return date.toLocaleDateString('ar-SA', options);
}

// تحديث الأرقام للعربية
function updateArabicNumbers() {
    const arabicNumbers = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
    
    document.querySelectorAll('.arabic-number').forEach(element => {
        let text = element.textContent;
        for (let i = 0; i < 10; i++) {
            text = text.replace(new RegExp(i, 'g'), arabicNumbers[i]);
        }
        element.textContent = text;
    });
}

// تهيئة الإشعارات
function initializeNotifications() {
    // فحص الإشعارات الجديدة كل 30 ثانية
    setInterval(checkNewNotifications, 30000);
    
    // النقر على أيقونة الإشعارات
    const notificationIcon = document.getElementById('notification-icon');
    if (notificationIcon) {
        notificationIcon.addEventListener('click', function() {
            toggleNotificationDropdown();
        });
    }
}

// فحص الإشعارات الجديدة
function checkNewNotifications() {
    fetch('/notifications/check-new/')
        .then(response => response.json())
        .then(data => {
            updateNotificationBadge(data.unread_count);
            
            if (data.notifications.length > 0) {
                showNotificationToast(data.notifications[0]);
            }
        });
}

// تحديث شارة الإشعارات
function updateNotificationBadge(count) {
    const badge = document.getElementById('notification-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
}

// عرض إشعار منبثق
function showNotificationToast(notification) {
    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    toast.innerHTML = `
        <div class="bg-white shadow-lg rounded-lg p-4 max-w-sm">
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <i class="fas fa-bell text-blue-500"></i>
                </div>
                <div class="mr-3 w-0 flex-1">
                    <p class="text-sm font-medium text-gray-900">${notification.title}</p>
                    <p class="mt-1 text-sm text-gray-500">${notification.message}</p>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // إخفاء التوست بعد 5 ثوان
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// تهيئة البحث المباشر
function initializeLiveSearch() {
    const searchInputs = document.querySelectorAll('[data-live-search]');
    
    searchInputs.forEach(input => {
        let timeout;
        
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            
            timeout = setTimeout(() => {
                const searchValue = this.value;
                const targetId = this.dataset.liveSearch;
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    // تشغيل حدث HTMX للبحث
                    htmx.trigger(targetElement, 'search', {value: searchValue});
                }
            }, 300); // تأخير 300ms
        });
    });
}

// تهيئة الفلاتر
function initializeFilters() {
    const filterForms = document.querySelectorAll('[data-filter-form]');
    
    filterForms.forEach(form => {
        const inputs = form.querySelectorAll('input, select');
        
        inputs.forEach(input => {
            input.addEventListener('change', function() {
                // إرسال النموذج تلقائياً عند التغيير
                htmx.trigger(form, 'submit');
            });
        });
    });
}

// عرض رسائل التوست
function showToasts() {
    const toasts = document.querySelectorAll('[data-toast]');
    
    toasts.forEach(toast => {
        // إضافة أنيميشن الظهور
        toast.classList.add('toast-show');
        
        // إخفاء التوست بعد 3 ثوان
        setTimeout(() => {
            toast.classList.add('toast-hide');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    });
}

// تأكيد الحذف
function confirmDelete(message) {
    return confirm(message || 'هل أنت متأكد من الحذف؟');
}

// طباعة العنصر
function printElement(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const printWindow = window.open('', '', 'height=600,width=800');
    printWindow.document.write('<html dir="rtl"><head><title>طباعة</title>');
    printWindow.document.write('<link rel="stylesheet" href="/static/css/print.css">');
    printWindow.document.write('</head><body>');
    printWindow.document.write(element.innerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
}

// تصدير جدول إلى Excel
function exportTableToExcel(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // استخدام مكتبة XLSX إذا كانت متوفرة
    if (typeof XLSX !== 'undefined') {
        const wb = XLSX.utils.table_to_book(table, {sheet: "Sheet1"});
        XLSX.writeFile(wb, filename + '.xlsx');
    } else {
        // تصدير بسيط كـ CSV
        let csv = [];
        const rows = table.querySelectorAll('tr');
        
        rows.forEach(row => {
            const cols = row.querySelectorAll('td, th');
            const rowData = Array.from(cols).map(col => col.textContent.trim());
            csv.push(rowData.join(','));
        });
        
        downloadCSV(csv.join('\n'), filename);
    }
}

// تحميل CSV
function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], {type: "text/csv;charset=utf-8;"});
    const downloadLink = document.createElement("a");
    downloadLink.download = filename + '.csv';
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = "none";
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// تبديل العرض
function toggleVisibility(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.toggle('hidden');
    }
}

// تنسيق الأرقام بالفواصل
function formatNumber(number) {
    return new Intl.NumberFormat('ar-SA').format(number);
}

// تنسيق العملة
function formatCurrency(amount) {
    return new Intl.NumberFormat('ar-SA', {
        style: 'currency',
        currency: 'SAR'
    }).format(amount);
}