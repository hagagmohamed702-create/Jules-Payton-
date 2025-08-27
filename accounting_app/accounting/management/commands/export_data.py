import json
import csv
from django.core.management.base import BaseCommand
from django.core.serializers import serialize
from django.utils import timezone
from ...models import (
    Customer, Contract, Installment, Unit, 
    ReceiptVoucher, PaymentVoucher, Project, Item
)


class Command(BaseCommand):
    help = 'يصدر بيانات النظام إلى ملفات JSON أو CSV'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'csv'],
            default='json',
            help='صيغة التصدير (json أو csv)'
        )
        parser.add_argument(
            '--model',
            type=str,
            choices=[
                'customers', 'contracts', 'installments', 
                'units', 'receipts', 'payments', 'projects', 'items'
            ],
            help='النموذج المراد تصديره (اتركه فارغاً لتصدير الكل)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='exports',
            help='مجلد حفظ الملفات المصدرة'
        )
    
    def handle(self, *args, **options):
        format_type = options['format']
        model_name = options['model']
        output_dir = options['output_dir']
        
        # إنشاء مجلد التصدير
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        if model_name:
            # تصدير نموذج واحد
            self._export_model(model_name, format_type, output_dir, timestamp)
        else:
            # تصدير جميع النماذج
            models = [
                'customers', 'contracts', 'installments', 
                'units', 'receipts', 'payments', 'projects', 'items'
            ]
            for model in models:
                self._export_model(model, format_type, output_dir, timestamp)
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ تم تصدير البيانات إلى مجلد {output_dir}')
        )
    
    def _export_model(self, model_name, format_type, output_dir, timestamp):
        """تصدير نموذج معين"""
        model_map = {
            'customers': Customer,
            'contracts': Contract,
            'installments': Installment,
            'units': Unit,
            'receipts': ReceiptVoucher,
            'payments': PaymentVoucher,
            'projects': Project,
            'items': Item,
        }
        
        model_class = model_map.get(model_name)
        if not model_class:
            return
        
        queryset = model_class.objects.all()
        count = queryset.count()
        
        if count == 0:
            self.stdout.write(
                self.style.WARNING(f'لا توجد بيانات في {model_name}')
            )
            return
        
        filename = f'{model_name}_{timestamp}.{format_type}'
        filepath = os.path.join(output_dir, filename)
        
        if format_type == 'json':
            self._export_to_json(queryset, filepath)
        else:
            self._export_to_csv(queryset, filepath, model_name)
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ تم تصدير {count} سجل من {model_name} إلى {filename}')
        )
    
    def _export_to_json(self, queryset, filepath):
        """تصدير إلى JSON"""
        data = serialize('json', queryset, indent=2, ensure_ascii=False)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)
    
    def _export_to_csv(self, queryset, filepath, model_name):
        """تصدير إلى CSV"""
        # تحديد الحقول حسب النموذج
        field_maps = {
            'customers': ['id', 'name', 'phone', 'email', 'is_active', 'created_at'],
            'contracts': [
                'id', 'contract_number', 'customer__name', 'unit__name',
                'unit_price', 'down_payment', 'installments_count', 'contract_date'
            ],
            'installments': [
                'id', 'contract__contract_number', 'installment_number',
                'amount', 'paid_amount', 'due_date', 'status'
            ],
            'units': [
                'id', 'name', 'building_number', 'unit_type',
                'total_price', 'unit_group'
            ],
            'receipts': [
                'id', 'voucher_number', 'customer__name', 'amount',
                'payment_date', 'safe__name'
            ],
            'payments': [
                'id', 'voucher_number', 'supplier__name', 'amount',
                'payment_date', 'expense_type'
            ],
            'projects': [
                'id', 'name', 'project_type', 'budget',
                'start_date', 'status'
            ],
            'items': [
                'id', 'code', 'name', 'unit', 'unit_price',
                'current_stock', 'minimum_stock'
            ],
        }
        
        fields = field_maps.get(model_name, [])
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # كتابة العناوين
            headers = [field.replace('__', ' - ').replace('_', ' ').title() for field in fields]
            writer.writerow(headers)
            
            # كتابة البيانات
            for obj in queryset:
                row = []
                for field in fields:
                    if '__' in field:
                        # حقل علاقة
                        parts = field.split('__')
                        value = obj
                        for part in parts:
                            value = getattr(value, part, '') if value else ''
                    else:
                        value = getattr(obj, field, '')
                    
                    # تنسيق التواريخ
                    if hasattr(value, 'strftime'):
                        value = value.strftime('%Y-%m-%d')
                    
                    row.append(str(value))
                
                writer.writerow(row)