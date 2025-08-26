# دليل نشر التطبيق على PythonAnywhere

## الخطوات:

### 1. إنشاء حساب على PythonAnywhere
- اذهب إلى [www.pythonanywhere.com](https://www.pythonanywhere.com)
- أنشئ حساب مجاني

### 2. رفع الكود
في PythonAnywhere console:
```bash
git clone https://github.com/hagagmohamed702-create/Jules-Payton-.git
cd Jules-Payton-/accounting_app
```

### 3. إنشاء البيئة الافتراضية
```bash
mkvirtualenv accounting --python=python3.11
pip install -r requirements.txt
```

### 4. إعداد قاعدة البيانات
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
```

### 5. إعداد Web App
- اذهب إلى "Web" tab
- أنشئ web app جديد
- اختر "Manual configuration"
- اختر Python 3.11

### 6. تكوين WSGI
في ملف WSGI configuration:
```python
import os
import sys

path = '/home/yourusername/Jules-Payton-/accounting_app'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 7. إعداد Static Files
- URL: `/static/`
- Directory: `/home/yourusername/Jules-Payton-/accounting_app/staticfiles/`

### 8. جمع الملفات الثابتة
```bash
python manage.py collectstatic
```

### 9. إعداد المتغيرات
في ملف `/home/yourusername/.env`:
```
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com
```

### 10. إعادة تحميل التطبيق
اضغط على "Reload" في Web tab

التطبيق سيكون متاح على: `https://yourusername.pythonanywhere.com`