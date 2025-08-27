from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, Q
from django.utils import timezone
from .serializers import *
from ..models import *
from ..services.installment_service import InstallmentService
from ..services.voucher_service import VoucherService
from ..services.notification_service import NotificationService


class PartnerViewSet(viewsets.ModelViewSet):
    """ViewSet للشركاء"""
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'balance', 'created_at']
    ordering = ['-created_at']


class PartnersGroupViewSet(viewsets.ModelViewSet):
    """ViewSet لمجموعات الشركاء"""
    queryset = PartnersGroup.objects.prefetch_related('members__partner')
    serializer_class = PartnersGroupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """إضافة عضو لمجموعة"""
        group = self.get_object()
        partner_id = request.data.get('partner_id')
        share_percentage = request.data.get('share_percentage')
        
        if not partner_id or not share_percentage:
            return Response(
                {'error': 'partner_id and share_percentage are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            partner = Partner.objects.get(pk=partner_id)
            member, created = PartnersGroupMember.objects.get_or_create(
                group=group,
                partner=partner,
                defaults={'share_percentage': share_percentage}
            )
            
            if not created:
                member.share_percentage = share_percentage
                member.save()
            
            serializer = PartnersGroupMemberSerializer(member)
            return Response(serializer.data)
            
        except Partner.DoesNotExist:
            return Response(
                {'error': 'Partner not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SafeViewSet(viewsets.ModelViewSet):
    """ViewSet للخزائن"""
    queryset = Safe.objects.all()
    serializer_class = SafeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """عرض حركات الخزينة"""
        safe = self.get_object()
        
        receipts = ReceiptVoucher.objects.filter(safe=safe, is_cancelled=False)
        payments = PaymentVoucher.objects.filter(safe=safe, is_cancelled=False)
        
        data = {
            'receipts': ReceiptVoucherSerializer(receipts, many=True).data,
            'payments': PaymentVoucherSerializer(payments, many=True).data,
            'total_receipts': receipts.aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_payments': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
        }
        
        return Response(data)


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet للعملاء"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['get'])
    def contracts(self, request, pk=None):
        """عرض عقود العميل"""
        customer = self.get_object()
        contracts = customer.contracts.all()
        serializer = ContractSerializer(contracts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def installments(self, request, pk=None):
        """عرض أقساط العميل"""
        customer = self.get_object()
        installments = Installment.objects.filter(
            contract__customer=customer
        ).select_related('contract')
        
        status_filter = request.query_params.get('status')
        if status_filter:
            installments = installments.filter(status=status_filter)
        
        serializer = InstallmentSerializer(installments, many=True)
        return Response(serializer.data)


class SupplierViewSet(viewsets.ModelViewSet):
    """ViewSet للموردين"""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'supplier_type']
    search_fields = ['name', 'company_name', 'phone', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']


class UnitViewSet(viewsets.ModelViewSet):
    """ViewSet للوحدات"""
    queryset = Unit.objects.select_related('partners_group')
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['unit_type', 'unit_group']
    search_fields = ['name', 'building_number']
    ordering_fields = ['name', 'total_price', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """عرض الوحدات المتاحة"""
        units = self.get_queryset().filter(contracts__isnull=True)
        serializer = self.get_serializer(units, many=True)
        return Response(serializer.data)


class ContractViewSet(viewsets.ModelViewSet):
    """ViewSet للعقود"""
    queryset = Contract.objects.select_related(
        'customer', 'unit', 'partners_group'
    ).prefetch_related('installments')
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['installment_type']
    search_fields = ['contract_number', 'customer__name', 'unit__name']
    ordering_fields = ['contract_date', 'created_at']
    ordering = ['-created_at']
    
    def create(self, request, *args, **kwargs):
        """إنشاء عقد جديد مع توليد الأقساط"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contract = serializer.save()
        
        # الأقساط ستُنشأ تلقائياً عبر signal
        
        return Response(
            self.get_serializer(contract).data,
            status=status.HTTP_201_CREATED
        )


class InstallmentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet للأقساط (قراءة فقط)"""
    queryset = Installment.objects.select_related(
        'contract__customer', 'contract__unit'
    )
    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'contract']
    search_fields = ['contract__contract_number', 'contract__customer__name']
    ordering_fields = ['due_date', 'amount']
    ordering = ['due_date']
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """عرض الأقساط المتأخرة"""
        today = timezone.now().date()
        installments = self.get_queryset().filter(
            due_date__lt=today,
            status__in=['pending', 'partial']
        )
        serializer = self.get_serializer(installments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """دفع قسط"""
        installment = self.get_object()
        amount = request.data.get('amount')
        safe_id = request.data.get('safe_id')
        payment_date = request.data.get('payment_date', timezone.now().date())
        
        if not amount or not safe_id:
            return Response(
                {'error': 'amount and safe_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            safe = Safe.objects.get(pk=safe_id)
            payment = InstallmentService.process_payment(
                installment=installment,
                amount=amount,
                payment_date=payment_date,
                safe=safe,
                notes=request.data.get('notes', '')
            )
            
            return Response({
                'message': 'Payment processed successfully',
                'payment_id': payment.id,
                'remaining': installment.amount - installment.paid_amount
            })
            
        except Safe.DoesNotExist:
            return Response(
                {'error': 'Safe not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet للمشاريع"""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'project_type']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'budget', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['get'])
    def expenses(self, request, pk=None):
        """عرض مصروفات المشروع"""
        project = self.get_object()
        expenses = project.payment_vouchers.filter(is_cancelled=False)
        serializer = PaymentVoucherSerializer(expenses, many=True)
        return Response(serializer.data)


class ItemViewSet(viewsets.ModelViewSet):
    """ViewSet للأصناف"""
    queryset = Item.objects.select_related('supplier')
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['name', 'current_stock', 'unit_price']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """عرض الأصناف منخفضة المخزون"""
        items = self.get_queryset().filter(
            current_stock__lte=F('minimum_stock')
        )
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


class StockMoveViewSet(viewsets.ModelViewSet):
    """ViewSet لحركات المخزون"""
    queryset = StockMove.objects.select_related('item', 'project')
    serializer_class = StockMoveSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['move_type', 'item', 'project']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """تحديث رصيد الصنف عند إنشاء حركة"""
        stock_move = serializer.save()
        item = stock_move.item
        
        if stock_move.move_type == 'in':
            item.current_stock += stock_move.quantity
        else:
            if item.current_stock < stock_move.quantity:
                raise serializers.ValidationError(
                    'الكمية المطلوبة أكبر من المتوفر'
                )
            item.current_stock -= stock_move.quantity
        
        item.save()


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet للإشعارات"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'priority', 'is_read']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """عرض إشعارات المستخدم الحالي فقط"""
        return self.request.user.notifications.all()
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """وضع علامة مقروء على إشعار"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'message': 'Notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """وضع علامة مقروء على جميع الإشعارات"""
        request.user.notifications.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'message': 'All notifications marked as read'})
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """ملخص الإشعارات"""
        summary = NotificationService.get_notification_summary(request.user)
        return Response(summary)