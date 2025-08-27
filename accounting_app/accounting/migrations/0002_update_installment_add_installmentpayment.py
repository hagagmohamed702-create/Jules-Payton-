# Generated manually for Installment updates and InstallmentPayment model

from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0001_initial'),
    ]

    operations = [
        # Add is_paid field to Installment if it doesn't exist
        migrations.AddField(
            model_name='installment',
            name='is_paid',
            field=models.BooleanField(default=False, verbose_name='مدفوع'),
        ),
        
        # Update amount field to match specifications
        migrations.AlterField(
            model_name='installment',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name='المبلغ'),
        ),
        
        # Update __str__ representation
        migrations.AlterField(
            model_name='installment',
            name='paid_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='المبلغ المدفوع'),
        ),
        
        # Create InstallmentPayment model
        migrations.CreateModel(
            name='InstallmentPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('paid_on', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الدفع')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='المبلغ المدفوع')),
                ('method', models.CharField(default='cash', max_length=50, verbose_name='طريقة الدفع')),
                ('note', models.CharField(blank=True, default='', max_length=255, verbose_name='ملاحظة')),
                ('installment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='accounting.installment', verbose_name='القسط')),
            ],
            options={
                'verbose_name': 'دفعة قسط',
                'verbose_name_plural': 'دفعات الأقساط',
                'ordering': ['-paid_on'],
            },
        ),
    ]