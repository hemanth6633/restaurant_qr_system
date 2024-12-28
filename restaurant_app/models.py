from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import pytz
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime

# Add timezone constant
IST = pytz.timezone('Asia/Kolkata')

class Waiter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='waiter_photos/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    joining_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    upi_id = models.CharField(max_length=50, blank=True, help_text="UPI ID for receiving tips")
    bank_account_number = models.CharField(max_length=20, blank=True)
    bank_ifsc_code = models.CharField(max_length=11, blank=True)
    bank_account_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def photo_url(self):
        if self.photo:
            return self.photo.url
        return None

class Bill(models.Model):
    bill_number = models.CharField(max_length=50, unique=True)
    table_number = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed')
    ])
    payment_method = models.CharField(max_length=20, choices=[
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('CASH', 'Cash')
    ], default='CASH')
    stripe_payment_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Bill #{self.bill_number} - Table {self.table_number}"

class Tip(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ]
    
    waiter = models.ForeignKey(Waiter, on_delete=models.CASCADE, related_name='tips')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Tip of {self.amount} for {self.waiter.full_name} ({self.payment_status})"

class Review(models.Model):
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    google_review_id = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"Review for Bill #{self.bill.bill_number}"

class WaiterReview(models.Model):
    waiter = models.ForeignKey(Waiter, on_delete=models.CASCADE, related_name='reviews')
    tip = models.OneToOneField(Tip, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.waiter.full_name} - {self.rating} stars"

    def get_rating_display(self):
        return '★' * self.rating + '☆' * (5 - self.rating)

    def get_formatted_datetime(self):
        return self.created_at.strftime('%d %B, %Y %I:%M %p IST')

class Feedback(models.Model):
    waiter = models.ForeignKey(Waiter, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.waiter.user.get_full_name()} - {self.rating} stars"

class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    google_review_link = models.URLField(help_text="Link to the restaurant's Google review page")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
