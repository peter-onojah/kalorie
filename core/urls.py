from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Customer management
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/new/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),

    # Stock management
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/add/', views.add_stock, name='add_stock'),
    path('stock/history/', views.stock_history, name='stock_history'),

    # Price management
    path('prices/', views.price_list, name='price_list'),
    path('prices/<int:pk>/update/', views.update_price, name='update_price'),

    # Transactions
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/new/', views.create_transaction, name='create_transaction'),
    path('transactions/<int:pk>/invoice/', views.transaction_invoice, name='transaction_invoice'),
    path('api/get-price/', views.get_price, name='get_price'),

    # Reports
    path('reports/', views.reports, name='reports'),
    path('export/transactions/', views.export_transactions, name='export_transactions'),

    # Audit log
    path('audit-log/', views.audit_log, name='audit_log'),
]