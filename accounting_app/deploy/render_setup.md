# دليل نشر التطبيق على Render

## الخطوات:

### 1. إعداد الملفات المطلوبة

#### أ) إنشاء `render.yaml`:
```yaml
services:
  - type: web
    name: arabic-accounting-system
    runtime: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python manage.py migrate && gunicorn core.wsgi"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: DATABASE_URL
        fromDatabase:
          name: accounting-db
          property: connectionString
      - key: DJANGO_SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: False
      - key: ALLOWED_HOSTS
        value: .onrender.com

databases:
  - name: accounting-db
    plan: free
    databaseName: accounting
    user: accounting_user
```

#### ب) تحديث `requirements.txt` (إضافة gunicorn إذا لم يكن موجود):
```
gunicorn==21.2.0
```

#### ج) إنشاء `build.sh`:
```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

### 2. إعداد المشروع

#### تحديث `settings.py` للإنتاج:
```python
# في نهاية الملف
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
```

### 3. النشر على Render

1. اذهب إلى [render.com](https://render.com)
2. أنشئ حساب جديد
3. اربط حساب GitHub
4. اختر "New +" > "Blueprint"
5. اختر المستودع الخاص بك
6. Render سيكتشف `render.yaml` تلقائياً
7. اضغط "Apply"

### 4. بعد النشر

في Render Shell، قم بتشغيل:
```bash
python manage.py createsuperuser
python manage.py seed_demo
```

### المميزات:
- ✅ مجاني للمشاريع الصغيرة
- ✅ PostgreSQL مجاني
- ✅ SSL تلقائي
- ✅ نشر تلقائي من GitHub
- ✅ سهل الإعداد

التطبيق سيكون متاح على: `https://arabic-accounting-system.onrender.com`