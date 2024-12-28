from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'restaurant'

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('home/', views.home, name='home'),
    path('billing/', views.billing, name='billing'),
    path('review/<str:bill_number>/', views.review, name='review'),
    path('submit-review/', views.submit_review, name='submit_review'),
    path('process-payment/', views.process_payment, name='process_payment'),
    path('generate-bill-upi-qr/', views.generate_bill_upi_qr, name='generate_bill_upi_qr'),
    path('verify-bill-payment/', views.verify_bill_payment, name='verify_bill_payment'),
    # Tip-related URLs
    path('waiters/tip/', views.waiter_tip, name='waiter_tip'),
    path('process-tip/', views.process_tip, name='process_tip'),
    path('verify-tip-payment/', views.verify_tip_payment, name='verify_tip_payment'),
    path('tip/success/', views.tip_success, name='tip_success'),
    path('tip/review/<str:tip_id>/', views.waiter_review, name='waiter_review'),
    path('tip/submit-review/', views.submit_waiter_review, name='submit_waiter_review'),
    path('tip/thank-you/', views.thank_you, name='thank_you'),
    # Feedback URLs
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('get-waiter-stats/<int:waiter_id>/', views.get_waiter_stats, name='get_waiter_stats'),
    path('api/waiter/<int:waiter_id>/', views.get_waiter_info, name='get_waiter_info'),
    path('payment/success/', views.payment_success, name='payment_success'),
    
    # Authentication URLs
    path('auth/login/', views.auth_login, name='auth_login'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='restaurant/auth/login.html'), name='login'),
    path('accounts/logout/', views.custom_logout, name='logout'),
    path('waiter/dashboard/', views.waiter_dashboard, name='waiter_dashboard'),
]
