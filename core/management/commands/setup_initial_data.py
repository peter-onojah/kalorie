from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Price, Stock
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Setup initial data for Kalories Kuisine'

    def handle(self, *args, **kwargs):
        # Create superuser if not exists
        if not User.objects.filter(username='Loveth').exists():
            User.objects.create_superuser(
                username='Loveth',
                password='Onojah123',
                email='loveth@kalorieskuisine.com'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created successfully'))
        else:
            self.stdout.write('Superuser already exists')

        # Create initial price records
        categories = [
            ('SMALL', 1200),  # Small eggs price
            ('MEDIUM', 1500),  # Medium eggs price
            ('LARGE', 1800),   # Large eggs price
        ]

        for category, price in categories:
            price_obj, created = Price.objects.get_or_create(
                category=category,
                defaults={'price': price}
            )
            if created:
                self.stdout.write(f'Created price for {category}: ₦{price}')
            else:
                self.stdout.write(f'Price for {category} already exists: ₦{price_obj.price}')

        # Create initial stock records
        categories_stock = [
            ('SMALL', 0),
            ('MEDIUM', 0),
            ('LARGE', 0),
        ]

        for category, quantity in categories_stock:
            stock, created = Stock.objects.get_or_create(
                category=category,
                defaults={'quantity': quantity}
            )
            if created:
                self.stdout.write(f'Created stock record for {category}')
            else:
                self.stdout.write(f'Stock for {category} already exists: {stock.quantity}')

        self.stdout.write(self.style.SUCCESS('Initial setup completed successfully'))