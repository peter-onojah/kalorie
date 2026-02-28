from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db.models import Sum, Count, Q, Avg  # Make sure Avg is here
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
import csv
from datetime import datetime, timedelta
import json

from .models import Customer, Price, Stock, StockRecord, Transaction, AuditLog
from .forms import (
    LoginForm, CustomerForm, PriceForm, 
    StockRecordForm, TransactionForm, DateRangeForm, SearchForm
)
# Authentication Views
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Create audit log
                AuditLog.objects.create(
                    user=user,
                    action='LOGIN',
                    model_name='User',
                    details={'ip': request.META.get('REMOTE_ADDR')}
                )
                messages.success(request, f'Welcome back, {username}!')
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})

@login_required
def logout_view(request):
    AuditLog.objects.create(
        user=request.user,
        action='LOGOUT',
        model_name='User',
        details={}
    )
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

# Dashboard View
@login_required
def dashboard(request):
    # Get summary statistics
    total_customers = Customer.objects.count()
    
    # Get stock totals
    stocks = Stock.objects.all()
    stock_data = {stock.category: stock.quantity for stock in stocks}
    
    # Get total transactions and revenue
    transactions = Transaction.objects.all()
    total_transactions = transactions.count()
    total_revenue = transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # Get today's transactions
    today = timezone.now().date()
    today_transactions = transactions.filter(transaction_date__date=today)
    today_revenue = today_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # Check low stock alerts
    low_stock_alerts = [stock for stock in stocks if stock.is_low_stock()]

    # Get recent transactions
    recent_transactions = transactions[:10]

    # Get top customers
    top_customers = Customer.objects.annotate(
        total_spent=Sum('transaction__total_amount')
    ).order_by('-total_spent')[:5]

    # Prepare chart data
    last_7_days = []
    sales_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_total = Transaction.objects.filter(
            transaction_date__date=date
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        last_7_days.append(date.strftime('%Y-%m-%d'))
        sales_data.append(float(daily_total))

    context = {
        'total_customers': total_customers,
        'stock_small': stock_data.get('SMALL', 0),
        'stock_medium': stock_data.get('MEDIUM', 0),
        'stock_large': stock_data.get('LARGE', 0),
        'total_transactions': total_transactions,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'low_stock_alerts': low_stock_alerts,
        'recent_transactions': recent_transactions,
        'top_customers': top_customers,
        'chart_labels': json.dumps(last_7_days),
        'chart_data': json.dumps(sales_data),
    }
    return render(request, 'core/dashboard.html', context)

# Customer Views
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'core/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(nickname__icontains=search_query) |
                Q(phone_number__icontains=search_query)
            )
        return queryset.order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = SearchForm(self.request.GET)
        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'
    success_url = reverse_lazy('customer_list')

    def form_valid(self, form):
        messages.success(self.request, 'Customer created successfully!')
        return super().form_valid(form)

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'
    success_url = reverse_lazy('customer_list')

    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully!')
        return super().form_valid(form)

class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'core/customer_confirm_delete.html'
    success_url = reverse_lazy('customer_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Customer deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    transactions = customer.transaction_set.all().order_by('-transaction_date')
    
    context = {
        'customer': customer,
        'transactions': transactions,
        'total_spent': customer.total_purchases(),
    }
    return render(request, 'core/customer_detail.html', context)

# Stock Views
@login_required
def stock_list(request):
    stocks = Stock.objects.all()
    return render(request, 'core/stock_list.html', {'stocks': stocks})

@login_required
def add_stock(request):
    if request.method == 'POST':
        form = StockRecordForm(request.POST)
        if form.is_valid():
            category = form.cleaned_data['category']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']

            try:
                stock = Stock.objects.get(category=category)
                stock.add_stock(quantity, request.user, notes)
                
                messages.success(request, f'Added {quantity} crates to {stock.get_category_display()}')
                return redirect('stock_list')
            except Stock.DoesNotExist:
                messages.error(request, 'Stock category not found')
    else:
        form = StockRecordForm()

    return render(request, 'core/add_stock.html', {'form': form})

@login_required
def stock_history(request):
    records = StockRecord.objects.all().select_related('recorded_by')[:100]
    return render(request, 'core/stock_history.html', {'records': records})

# Price Views
@login_required
def price_list(request):
    prices = Price.objects.all()
    return render(request, 'core/price_list.html', {'prices': prices})

@login_required
def update_price(request, pk):
    price = get_object_or_404(Price, pk=pk)

    if request.method == 'POST':
        form = PriceForm(request.POST, instance=price)
        if form.is_valid():
            price = form.save(commit=False)
            price.updated_by = request.user
            price.save()
            messages.success(request, f'Price updated for {price.get_category_display()}')
            return redirect('price_list')
    else:
        form = PriceForm(instance=price)

    return render(request, 'core/price_form.html', {'form': form, 'price': price})

# Transaction Views
class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'core/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('customer', 'recorded_by')
        
        # Filter by date range
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(transaction_date__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transaction_date__date__lte=end_date)

        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(egg_category=category)

        # Search by customer
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer__full_name__icontains=search) |
                Q(customer__nickname__icontains=search) |
                Q(invoice_number__icontains=search)
            )

        return queryset.order_by('-transaction_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date_form'] = DateRangeForm(self.request.GET)
        context['search_form'] = SearchForm(self.request.GET)
        context['categories'] = Transaction.CATEGORY_CHOICES
        return context

@login_required
def create_transaction(request):
    # Get current stock levels to display in template
    stocks = Stock.objects.all()
    
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.recorded_by = request.user
            transaction.save()
            messages.success(request, 'Transaction completed successfully!')
            return redirect('transaction_list')
        else:
            # If form is invalid, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TransactionForm()

    return render(request, 'core/transaction_form.html', {
        'form': form,
        'stocks': stocks
    })

@login_required
def get_price(request):
    """AJAX view to get current price for a category"""
    category = request.GET.get('category')
    try:
        price = Price.objects.get(category=category)
        return JsonResponse({'price': float(price.price)})
    except Price.DoesNotExist:
        return JsonResponse({'error': 'Price not found'}, status=404)

@login_required
def transaction_invoice(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    return render(request, 'core/invoice.html', {'transaction': transaction})

# Reports Views
@login_required
def reports(request):
    # Date range filtering
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['start_date']:
                start_date = form.cleaned_data['start_date']
            if form.cleaned_data['end_date']:
                end_date = form.cleaned_data['end_date']
    else:
        form = DateRangeForm(initial={'start_date': start_date, 'end_date': end_date})

    # Get transactions in date range
    transactions = Transaction.objects.filter(
        transaction_date__date__gte=start_date,
        transaction_date__date__lte=end_date
    )

    # Daily sales
    daily_sales = transactions.values('transaction_date__date').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('transaction_date__date')

    # Category breakdown
    category_sales = transactions.values('egg_category').annotate(
        total=Sum('total_amount'),
        quantity=Sum('quantity'),
        count=Count('id')
    )

    # Top customers
    top_customers = transactions.values(
        'customer__full_name', 'customer__nickname'
    ).annotate(
        total=Sum('total_amount'),
        purchases=Count('id')
    ).order_by('-total')[:10]

    # Summary statistics
    summary = {
        'total_sales': transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'total_transactions': transactions.count(),
        'total_quantity': transactions.aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'average_transaction': transactions.aggregate(
            avg=Avg('total_amount')  # Changed from models.Avg to Avg
        )['avg'] or 0,
    }

    context = {
        'form': form,
        'daily_sales': daily_sales,
        'category_sales': category_sales,
        'top_customers': top_customers,
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'core/reports.html', context)

@login_required
def export_transactions(request):
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice Number', 'Date', 'Customer', 'Category',
        'Quantity', 'Price Per Unit', 'Total Amount', 'Recorded By'
    ])

    transactions = Transaction.objects.select_related('customer', 'recorded_by').all()
    for t in transactions:
        writer.writerow([
            t.invoice_number,
            t.transaction_date.strftime('%Y-%m-%d %H:%M'),
            t.customer.full_name,
            t.get_egg_category_display(),
            t.quantity,
            t.price_per_unit,
            t.total_amount,
            t.recorded_by.username if t.recorded_by else 'Unknown'
        ])

    return response

# Audit Log View
@login_required
def audit_log(request):
    logs = AuditLog.objects.select_related('user').all()[:100]
    return render(request, 'core/audit_log.html', {'logs': logs})

# Add this at the end of core/views.py
def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'core/404.html', status=404)