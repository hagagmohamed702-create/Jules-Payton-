from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.db.models import Q
from ..models import Partner, PartnersGroup, PartnersGroupMember
from ..services import TreasuryService


@login_required
def partners_list(request):
    """قائمة الشركاء"""
    search_query = request.GET.get('search', '')
    
    partners = Partner.objects.all()
    
    if search_query:
        partners = partners.filter(
            Q(code__icontains=search_query) |
            Q(name__icontains=search_query)
        )
    
    partners = partners.order_by('code')
    
    # حساب الرصيد الحالي لكل شريك
    for partner in partners:
        partner.current_balance = TreasuryService.get_partner_balance(partner)
    
    context = {
        'partners': partners,
        'search_query': search_query,
    }
    
    if request.htmx:
        return render(request, 'accounting/partners/_table.html', context)
    
    return render(request, 'accounting/partners/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def partner_create(request):
    """إنشاء شريك جديد"""
    from ..forms.partners import PartnerForm
    
    if request.method == 'POST':
        form = PartnerForm(request.POST)
        if form.is_valid():
            partner = form.save()
            messages.success(request, f'تم إنشاء الشريك {partner.name} بنجاح')
            
            if request.htmx:
                # إرجاع الصف الجديد للجدول
                partner.current_balance = TreasuryService.get_partner_balance(partner)
                html = render_to_string('accounting/partners/_row.html', {'partner': partner})
                return JsonResponse({
                    'html': html,
                    'message': f'تم إنشاء الشريك {partner.name} بنجاح'
                })
            
            return redirect('accounting:partners_list')
    else:
        form = PartnerForm()
    
    context = {'form': form, 'title': 'إضافة شريك جديد'}
    
    if request.htmx:
        return render(request, 'accounting/partners/_form.html', context)
    
    return render(request, 'accounting/partners/form.html', context)


@login_required 
@require_http_methods(["GET", "POST"])
def partner_edit(request, pk):
    """تعديل شريك"""
    from ..forms.partners import PartnerForm
    
    partner = get_object_or_404(Partner, pk=pk)
    
    if request.method == 'POST':
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            partner = form.save()
            messages.success(request, f'تم تحديث الشريك {partner.name} بنجاح')
            
            if request.htmx:
                # إرجاع الصف المحدث
                partner.current_balance = TreasuryService.get_partner_balance(partner)
                html = render_to_string('accounting/partners/_row.html', {'partner': partner})
                return JsonResponse({
                    'html': html,
                    'message': f'تم تحديث الشريك {partner.name} بنجاح'
                })
            
            return redirect('accounting:partners_list')
    else:
        form = PartnerForm(instance=partner)
    
    context = {
        'form': form,
        'partner': partner,
        'title': f'تعديل الشريك: {partner.name}'
    }
    
    if request.htmx:
        return render(request, 'accounting/partners/_form.html', context)
    
    return render(request, 'accounting/partners/form.html', context)


@login_required
@require_http_methods(["DELETE"])
def partner_delete(request, pk):
    """حذف شريك"""
    partner = get_object_or_404(Partner, pk=pk)
    
    try:
        partner_name = partner.name
        partner.delete()
        messages.success(request, f'تم حذف الشريك {partner_name} بنجاح')
        
        if request.htmx:
            return JsonResponse({
                'message': f'تم حذف الشريك {partner_name} بنجاح',
                'deleted': True
            })
    except Exception as e:
        messages.error(request, f'لا يمكن حذف الشريك: {str(e)}')
        
        if request.htmx:
            return JsonResponse({
                'message': f'لا يمكن حذف الشريك: {str(e)}',
                'deleted': False
            }, status=400)
    
    return redirect('accounting:partners_list')


@login_required
def partner_detail(request, pk):
    """تفاصيل الشريك"""
    partner = get_object_or_404(Partner, pk=pk)
    
    # الرصيد الحالي
    partner.current_balance = TreasuryService.get_partner_balance(partner)
    
    # المعاملات الأخيرة
    transactions = TreasuryService.get_partner_transactions(partner)[:20]
    
    # العضويات في المجموعات
    group_memberships = partner.group_memberships.select_related('group')
    
    context = {
        'partner': partner,
        'transactions': transactions,
        'group_memberships': group_memberships,
    }
    
    return render(request, 'accounting/partners/detail.html', context)


# مجموعات الشركاء
@login_required
def groups_list(request):
    """قائمة مجموعات الشركاء"""
    groups = PartnersGroup.objects.prefetch_related('members__partner').all()
    
    context = {
        'groups': groups,
    }
    
    return render(request, 'accounting/partners/groups_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def group_create(request):
    """إنشاء مجموعة شركاء"""
    from ..forms.partners import PartnersGroupForm, PartnersGroupMemberFormSet
    
    if request.method == 'POST':
        form = PartnersGroupForm(request.POST)
        formset = PartnersGroupMemberFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            group = form.save()
            formset.instance = group
            formset.save()
            
            # التحقق من مجموع النسب
            try:
                group.validate_total_percent()
                messages.success(request, f'تم إنشاء المجموعة {group.name} بنجاح')
                return redirect('accounting:groups_list')
            except Exception as e:
                group.delete()
                messages.error(request, str(e))
    else:
        form = PartnersGroupForm()
        formset = PartnersGroupMemberFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'إنشاء مجموعة شركاء'
    }
    
    return render(request, 'accounting/partners/group_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def group_edit(request, pk):
    """تعديل مجموعة شركاء"""
    from ..forms.partners import PartnersGroupForm, PartnersGroupMemberFormSet
    
    group = get_object_or_404(PartnersGroup, pk=pk)
    
    if request.method == 'POST':
        form = PartnersGroupForm(request.POST, instance=group)
        formset = PartnersGroupMemberFormSet(request.POST, instance=group)
        
        if form.is_valid() and formset.is_valid():
            group = form.save()
            formset.save()
            
            # التحقق من مجموع النسب
            try:
                group.validate_total_percent()
                messages.success(request, f'تم تحديث المجموعة {group.name} بنجاح')
                return redirect('accounting:groups_list')
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = PartnersGroupForm(instance=group)
        formset = PartnersGroupMemberFormSet(instance=group)
    
    context = {
        'form': form,
        'formset': formset,
        'group': group,
        'title': f'تعديل المجموعة: {group.name}'
    }
    
    return render(request, 'accounting/partners/group_form.html', context)