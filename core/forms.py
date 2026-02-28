from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Customer, Price, Stock, Transaction, StockRecord
from django.core.exceptions import ValidationError
from decimal import Decimal

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['full_name', 'nickname', 'address', 'phone_number']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter nickname'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter address'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
        }

class PriceForm(forms.ModelForm):
    class Meta:
        model = Price
        fields = ['price']
        widgets = {
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

class StockRecordForm(forms.Form):
    CATEGORY_CHOICES = [
        ('SMALL', 'Small Eggs'),
        ('MEDIUM', 'Medium Eggs'),
        ('LARGE', 'Large Eggs'),
    ]

    category = forms.ChoiceField(choices=CATEGORY_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes'}))

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        return quantity

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['customer', 'egg_category', 'quantity', 'price_per_unit']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'egg_category': forms.Select(attrs={'class': 'form-control', 'id': 'egg_category'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'id': 'quantity'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'price_per_unit'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set price choices based on current prices
        self.fields['price_per_unit'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('egg_category')
        quantity = cleaned_data.get('quantity')

        if category and quantity:
            try:
                # Check if enough stock
                stock = Stock.objects.get(category=category)
                if stock.quantity < quantity:
                    raise ValidationError(f"Insufficient stock. Available: {stock.quantity} crates")

                # Get current price
                price = Price.objects.get(category=category)
                cleaned_data['price_per_unit'] = price.price

            except Stock.DoesNotExist:
                raise ValidationError(f"No stock record found for {category}")
            except Price.DoesNotExist:
                raise ValidationError(f"No price set for {category}")

        return cleaned_data

class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

class SearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search...'})
    )