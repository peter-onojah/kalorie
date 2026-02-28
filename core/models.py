from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum, F
import logging

logger = logging.getLogger(__name__)

class Customer(models.Model):
    """Customer model for Kalories Kuisine"""
    full_name = models.CharField(max_length=200)
    nickname = models.CharField(max_length=100)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.full_name} ({self.nickname})"

    def total_purchases(self):
        """Calculate total purchases for this customer"""
        return self.transaction_set.aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0

class Price(models.Model):
    """Price management for egg categories"""
    CATEGORY_CHOICES = [
        ('SMALL', 'Small Eggs'),
        ('MEDIUM', 'Medium Eggs'),
        ('LARGE', 'Large Eggs'),
    ]

    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['category']

    def __str__(self):
        return f"{self.get_category_display()} - ₦{self.price}"

    def save(self, *args, **kwargs):
        """Log price changes"""
        if self.pk:
            try:
                old = Price.objects.get(pk=self.pk)
                if old.price != self.price:
                    logger.info(f"Price changed for {self.category}: {old.price} -> {self.price}")
            except Price.DoesNotExist:
                pass
        super().save(*args, **kwargs)

class Stock(models.Model):
    """Current stock levels"""
    CATEGORY_CHOICES = [
        ('SMALL', 'Small Eggs'),
        ('MEDIUM', 'Medium Eggs'),
        ('LARGE', 'Large Eggs'),
    ]

    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, unique=True)
    quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    last_updated = models.DateTimeField(auto_now=True)
    low_stock_threshold = models.PositiveIntegerField(default=50, help_text="Alert when stock below this")

    def __str__(self):
        return f"{self.get_category_display()}: {self.quantity} crates"

    def is_low_stock(self):
        """Check if stock is below threshold"""
        return self.quantity < self.low_stock_threshold

    def add_stock(self, quantity, user, notes=""):
        """Add stock and create record"""
        self.quantity = F('quantity') + quantity
        self.save()
        self.refresh_from_db()

        # Create stock record
        StockRecord.objects.create(
            stock=self,
            category=self.category,
            quantity_added=quantity,
            recorded_by=user,
            notes=notes
        )

    def remove_stock(self, quantity, user, transaction):
        """Remove stock for a transaction"""
        if self.quantity < quantity:
            raise ValueError(f"Insufficient stock. Available: {self.quantity}, Requested: {quantity}")

        self.quantity = F('quantity') - quantity
        self.save()
        self.refresh_from_db()

class StockRecord(models.Model):
    """History of stock additions"""
    CATEGORY_CHOICES = [
        ('SMALL', 'Small Eggs'),
        ('MEDIUM', 'Medium Eggs'),
        ('LARGE', 'Large Eggs'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='records')
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    quantity_added = models.PositiveIntegerField()
    date_recorded = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_recorded']

    def __str__(self):
        return f"{self.get_category_display()}: +{self.quantity_added} on {self.date_recorded.date()}"

class Transaction(models.Model):
    """Sales transactions"""
    CATEGORY_CHOICES = [
        ('SMALL', 'Small Eggs'),
        ('MEDIUM', 'Medium Eggs'),
        ('LARGE', 'Large Eggs'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    egg_category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    transaction_date = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ['-transaction_date']

    def save(self, *args, **kwargs):
        # Calculate total amount
        self.total_amount = self.quantity * self.price_per_unit

        # Generate invoice number if not set
        if not self.invoice_number:
            date_str = timezone.now().strftime('%Y%m%d')
            last_today = Transaction.objects.filter(
                transaction_date__date=timezone.now().date()
            ).count()
            self.invoice_number = f"INV-{date_str}-{last_today + 1:04d}"

        # Update stock
        if not self.pk:  # Only on creation
            try:
                stock = Stock.objects.get(category=self.egg_category)
                stock.remove_stock(self.quantity, self.recorded_by, self)
            except Stock.DoesNotExist:
                raise ValueError(f"No stock record found for {self.get_egg_category_display()}")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.customer} - ₦{self.total_amount}"

class AuditLog(models.Model):
    """Audit trail for important actions"""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"