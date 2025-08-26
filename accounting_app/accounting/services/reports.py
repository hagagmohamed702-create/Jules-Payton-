import csv
import io
from datetime import date, datetime
from decimal import Decimal
from django.http import HttpResponse
from django.template.loader import render_to_string
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
import os
from django.conf import settings


class ReportService:
    """خدمة إنشاء التقارير"""
    
    @staticmethod
    def setup_arabic_font():
        """إعداد الخط العربي للتقارير PDF"""
        try:
            # محاولة تحميل خط عربي
            font_path = os.path.join(settings.STATIC_ROOT, 'fonts', 'NotoSansArabic-Regular.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Arabic', font_path))
                return 'Arabic'
        except:
            pass
        return 'Helvetica'
    
    @staticmethod
    def generate_treasury_report_csv(from_date, to_date, safe=None):
        """توليد تقرير الخزينة بصيغة CSV"""
        from .treasury import TreasuryService
        
        # الحصول على بيانات التدفق النقدي
        cash_flow = TreasuryService.get_cash_flow(from_date, to_date, safe)
        
        # إنشاء ملف CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # العناوين
        writer.writerow([
            'التاريخ',
            'رقم السند',
            'النوع',
            'البيان',
            'قبض',
            'صرف',
            'الرصيد',
            'الخزنة'
        ])
        
        # البيانات
        for item in cash_flow:
            writer.writerow([
                item['date'].strftime('%Y-%m-%d'),
                item['voucher_number'],
                'قبض' if item['type'] == 'receipt' else 'صرف',
                item['description'],
                str(item['amount_in']),
                str(item['amount_out']),
                str(item['balance']),
                item['safe']
            ])
        
        # إنشاء الاستجابة
        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="treasury_report_{from_date}_{to_date}.csv"'
        
        # إضافة BOM لدعم Excel مع UTF-8
        response.content = '\ufeff' + output.getvalue()
        
        return response
    
    @staticmethod
    def generate_treasury_report_pdf(from_date, to_date, safe=None):
        """توليد تقرير الخزينة بصيغة PDF"""
        from .treasury import TreasuryService
        
        # الحصول على بيانات التدفق النقدي
        cash_flow = TreasuryService.get_cash_flow(from_date, to_date, safe)
        
        # إنشاء ملف PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="treasury_report_{from_date}_{to_date}.pdf"'
        
        # إعداد الوثيقة
        doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        # الخط العربي
        arabic_font = ReportService.setup_arabic_font()
        
        # الأنماط
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a202c'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=arabic_font
        )
        
        # العناصر
        elements = []
        
        # العنوان
        title_text = f"تقرير الخزينة من {from_date} إلى {to_date}"
        if safe:
            title_text += f" - {safe.name}"
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 20))
        
        # الجدول
        data = [['الرصيد', 'صرف', 'قبض', 'البيان', 'النوع', 'رقم السند', 'التاريخ']]
        
        for item in cash_flow:
            data.append([
                f"{item['balance']:,.2f}",
                f"{item['amount_out']:,.2f}" if item['amount_out'] > 0 else '-',
                f"{item['amount_in']:,.2f}" if item['amount_in'] > 0 else '-',
                item['description'][:50],
                'قبض' if item['type'] == 'receipt' else 'صرف',
                item['voucher_number'],
                item['date'].strftime('%Y-%m-%d')
            ])
        
        # إنشاء الجدول
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), arabic_font),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), arabic_font),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(table)
        
        # بناء PDF
        doc.build(elements)
        
        return response
    
    @staticmethod
    def generate_installments_report_csv(from_date=None, to_date=None, status=None, customer=None):
        """توليد تقرير الأقساط بصيغة CSV"""
        from ..models import Installment
        
        # فلترة الأقساط
        installments = Installment.objects.select_related('contract', 'contract__customer')
        
        if from_date:
            installments = installments.filter(due_date__gte=from_date)
        if to_date:
            installments = installments.filter(due_date__lte=to_date)
        if status:
            installments = installments.filter(status=status)
        if customer:
            installments = installments.filter(contract__customer=customer)
        
        # إنشاء ملف CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # العناوين
        writer.writerow([
            'رقم العقد',
            'العميل',
            'رقم القسط',
            'تاريخ الاستحقاق',
            'قيمة القسط',
            'المدفوع',
            'المتبقي',
            'الحالة'
        ])
        
        # البيانات
        for installment in installments:
            writer.writerow([
                installment.contract.code,
                installment.contract.customer.name,
                installment.seq_no,
                installment.due_date.strftime('%Y-%m-%d'),
                str(installment.amount),
                str(installment.paid_amount),
                str(installment.get_remaining_amount()),
                installment.get_status_display()
            ])
        
        # إنشاء الاستجابة
        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="installments_report.csv"'
        
        # إضافة BOM
        response.content = '\ufeff' + output.getvalue()
        
        return response
    
    @staticmethod
    def generate_partners_balances_report(as_of_date=None):
        """توليد تقرير أرصدة الشركاء"""
        from .treasury import TreasuryService
        from ..models import Partner
        
        if not as_of_date:
            as_of_date = date.today()
        
        partners = Partner.objects.all()
        balances = []
        
        for partner in partners:
            balance = TreasuryService.get_partner_balance(partner)
            balances.append({
                'partner': partner,
                'balance': balance,
                'share_percent': partner.share_percent
            })
        
        # إنشاء ملف CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # العناوين
        writer.writerow([
            'كود الشريك',
            'اسم الشريك',
            'نسبة الشراكة %',
            'الرصيد'
        ])
        
        # البيانات
        total_balance = Decimal('0')
        for item in balances:
            writer.writerow([
                item['partner'].code,
                item['partner'].name,
                str(item['share_percent']),
                str(item['balance'])
            ])
            total_balance += item['balance']
        
        # الإجمالي
        writer.writerow(['', '', 'الإجمالي:', str(total_balance)])
        
        # إنشاء الاستجابة
        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="partners_balances_{as_of_date}.csv"'
        
        # إضافة BOM
        response.content = '\ufeff' + output.getvalue()
        
        return response
    
    @staticmethod
    def generate_project_expenses_report(project, from_date=None, to_date=None):
        """توليد تقرير مصروفات المشروع"""
        from ..models import PaymentVoucher, StockMove
        
        # فلترة المصروفات
        expenses = PaymentVoucher.objects.filter(project=project)
        if from_date:
            expenses = expenses.filter(date__gte=from_date)
        if to_date:
            expenses = expenses.filter(date__lte=to_date)
        
        # فلترة المواد
        materials = StockMove.objects.filter(project=project, direction='OUT')
        if from_date:
            materials = materials.filter(date__gte=from_date)
        if to_date:
            materials = materials.filter(date__lte=to_date)
        
        # إنشاء ملف CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # معلومات المشروع
        writer.writerow(['تقرير مصروفات المشروع'])
        writer.writerow(['كود المشروع:', project.code])
        writer.writerow(['اسم المشروع:', project.name])
        writer.writerow(['الميزانية:', str(project.budget)])
        writer.writerow([])
        
        # المصروفات النقدية
        writer.writerow(['المصروفات النقدية'])
        writer.writerow(['التاريخ', 'رقم السند', 'البيان', 'المبلغ'])
        
        total_cash = Decimal('0')
        for expense in expenses:
            writer.writerow([
                expense.date.strftime('%Y-%m-%d'),
                expense.voucher_number,
                expense.description,
                str(expense.amount)
            ])
            total_cash += expense.amount
        
        writer.writerow(['', '', 'إجمالي المصروفات النقدية:', str(total_cash)])
        writer.writerow([])
        
        # المواد المستخدمة
        writer.writerow(['المواد المستخدمة'])
        writer.writerow(['التاريخ', 'الصنف', 'الكمية', 'سعر الوحدة', 'القيمة'])
        
        total_materials = Decimal('0')
        for material in materials:
            value = material.get_move_value()
            writer.writerow([
                material.date.strftime('%Y-%m-%d'),
                material.item.name,
                f"{material.qty} {material.item.uom}",
                str(material.item.unit_price),
                str(value)
            ])
            total_materials += value
        
        writer.writerow(['', '', '', 'إجمالي قيمة المواد:', str(total_materials)])
        writer.writerow([])
        
        # الملخص
        total_expenses = total_cash + total_materials
        remaining_budget = project.budget - total_expenses
        
        writer.writerow(['ملخص المشروع'])
        writer.writerow(['إجمالي المصروفات:', str(total_expenses)])
        writer.writerow(['المتبقي من الميزانية:', str(remaining_budget)])
        writer.writerow(['نسبة الاستهلاك:', f"{project.get_budget_percentage():.2f}%"])
        
        # إنشاء الاستجابة
        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="project_expenses_{project.code}.csv"'
        
        # إضافة BOM
        response.content = '\ufeff' + output.getvalue()
        
        return response