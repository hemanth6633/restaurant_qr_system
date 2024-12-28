import json
import stripe
import qrcode
import base64
from io import BytesIO
from urllib.parse import quote
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Avg, Count, Sum
from .models import Bill, Review, Waiter, Tip, Feedback, WaiterReview
import uuid
from datetime import datetime
import time
from django.urls import reverse
from django.utils import timezone
from pytz import timezone as tz
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

INDIA_TIMEZONE = tz('Asia/Kolkata')

stripe.api_key = settings.STRIPE_SECRET_KEY

def generate_bill_number():
    return str(uuid.uuid4().hex[:8])

def generate_reference_id():
    return str(uuid.uuid4())

def welcome(request):
    return render(request, 'restaurant/welcome.html')

def home(request):
    """Simple landing page with billing and tipping options"""
    return render(request, 'restaurant/home.html')

def billing(request):
    try:
        context = {
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        }
        return render(request, 'restaurant/billing.html', context)
    except Exception as e:
        print(f"Error in billing view: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def review(request, bill_number):
    bill = Bill.objects.get(bill_number=bill_number)
    context = {
        'bill': bill
    }
    return render(request, 'restaurant/review.html', context)

@csrf_exempt
def submit_review(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        bill_number = data.get('bill_number')
        rating = data.get('rating')
        comment = data.get('comment')
        
        try:
            bill = Bill.objects.get(bill_number=bill_number)
            review = Review.objects.create(
                bill=bill,
                rating=rating,
                comment=comment
            )
            return JsonResponse({'success': True})
        except Bill.DoesNotExist:
            return JsonResponse({'error': 'Bill not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

def direct_tip(request):
    """View for direct tip payment"""
    # Get parameters from query
    bill_number = request.GET.get('bill_number')
    waiter_id = request.GET.get('waiter_id')
    
    try:
        if bill_number:
            # If bill number is provided, get the assigned waiter
            bill = Bill.objects.get(bill_number=bill_number)
            waiter = bill.waiter
            bill_context = {'bill': bill}
        elif waiter_id:
            # If waiter_id is provided, get the waiter
            waiter = get_object_or_404(Waiter, id=waiter_id)
            bill_context = {}
        else:
            # If no bill number or waiter_id, show all waiters
            waiters = Waiter.objects.all()
            return render(request, 'restaurant/direct_tip.html', {
                'waiters': waiters,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY
            })
        
        # Get waiter's rating and review count
        feedback_stats = Feedback.objects.filter(waiter=waiter).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        
        # Combine all context
        context = {
            'waiter': waiter,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
            'avg_rating': feedback_stats['avg_rating'] or 0,
            'review_count': feedback_stats['total_reviews'] or 0,
            **bill_context
        }
        
        return render(request, 'restaurant/direct_tip.html', context)
        
    except Bill.DoesNotExist:
        messages.error(request, 'Invalid bill number')
        return redirect('restaurant:home')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('restaurant:home')

@csrf_exempt
def process_tip(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            waiter_id = data.get('waiter_id')
            amount = float(data.get('amount'))
            payment_method = data.get('payment_method')
            
            if not waiter_id or not amount:
                return JsonResponse({'error': 'Waiter ID and amount are required'}, status=400)
            
            waiter = Waiter.objects.get(id=waiter_id)
            
            # Create tip record
            tip = Tip.objects.create(
                waiter=waiter,
                amount=amount,
                payment_status='PENDING'
            )
            
            if payment_method == 'card':
                try:
                    # Create Stripe payment intent
                    intent = stripe.PaymentIntent.create(
                        amount=int(amount * 100),  # Convert to cents
                        currency='inr',
                        metadata={
                            'tip_id': str(tip.id),
                            'waiter_id': str(waiter_id)
                        }
                    )
                    
                    return JsonResponse({
                        'clientSecret': intent.client_secret,
                        'tip_id': str(tip.id)
                    })
                except stripe.error.StripeError as e:
                    tip.payment_status = 'FAILED'
                    tip.save()
                    return JsonResponse({'error': str(e)}, status=400)
            
            elif payment_method == 'upi':
                try:
                    if not waiter.upi_id:
                        return JsonResponse({'error': 'Waiter UPI ID not available'}, status=400)
                    
                    # Generate reference ID
                    reference_id = f"TIP{tip.id}"
                    
                    # Create UPI payment string with waiter's UPI ID
                    merchant_name = quote(waiter.full_name)
                    transaction_note = quote(f"Tip payment - {reference_id}")
                    
                    upi_string = f"upi://pay?pa={waiter.upi_id}&pn={merchant_name}&am={amount}&tn={transaction_note}&tr={reference_id}"
                    
                    # Generate QR code
                    qr = qrcode.QRCode(version=1, box_size=10, border=5)
                    qr.add_data(upi_string)
                    qr.make(fit=True)
                    
                    # Create QR code image
                    img_buffer = BytesIO()
                    img = qr.make_image(fill_color="black", back_color="white")
                    img.save(img_buffer, format='PNG')
                    img_str = base64.b64encode(img_buffer.getvalue()).decode()
                    
                    # Update tip with reference ID
                    tip.reference_id = reference_id
                    tip.save()
                    
                    return JsonResponse({
                        'qr_code': img_str,
                        'upi_string': upi_string,
                        'reference_id': reference_id,
                        'tip_id': str(tip.id)
                    })
                except Exception as e:
                    tip.payment_status = 'FAILED'
                    tip.save()
                    return JsonResponse({'error': str(e)}, status=400)
            
            return JsonResponse({'error': 'Invalid payment method'}, status=400)
            
        except Waiter.DoesNotExist:
            return JsonResponse({'error': 'Waiter not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def waiter_tip(request):
    """View for displaying waiter list for tipping"""
    waiters = Waiter.objects.filter(is_active=True)
    
    # Get average rating and review count for each waiter
    for waiter in waiters:
        feedback_stats = Feedback.objects.filter(waiter=waiter).aggregate(
            avg_rating=Avg('rating'),
            review_count=Count('id')
        )
        waiter.avg_rating = feedback_stats['avg_rating']
        waiter.review_count = feedback_stats['review_count']
    
    context = {
        'waiters': waiters,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    }
    return render(request, 'restaurant/waiter_tip.html', context)

def tip_success(request):
    """View for displaying tip success page"""
    messages.success(request, 'Thank you for your tip! The waiter will be notified.')
    return render(request, 'restaurant/tip_success.html')

def generate_tip_upi_qr(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            waiter_id = data.get('waiter_id')
            
            if not amount or not waiter_id:
                return JsonResponse({
                    'error': 'Missing required fields'
                }, status=400)
            
            waiter = get_object_or_404(Waiter, id=waiter_id)
            reference_id = generate_reference_id()
            
            # Create UPI payment string
            upi_id = settings.UPI_ID
            merchant_name = quote("Restaurant Tip")
            transaction_note = quote(f"Tip for {waiter.full_name}")
            
            upi_string = f"upi://pay?pa={upi_id}&pn={merchant_name}&am={amount}&tn={transaction_note}&tr={reference_id}"
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(upi_string)
            qr.make(fit=True)
            
            # Create QR code image
            img_buffer = BytesIO()
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(img_buffer, format="PNG")
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Save tip record
            Tip.objects.create(
                waiter=waiter,
                amount=amount,
                payment_method='UPI',
                reference_id=reference_id,
                payment_status='PENDING'
            )
            
            return JsonResponse({
                'qr_code': img_str,
                'upi_string': upi_string,
                'reference_id': reference_id
            })
            
        except Waiter.DoesNotExist:
            return JsonResponse({
                'error': 'Waiter not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
    return JsonResponse({
        'error': 'Invalid request method'
    }, status=400)

@csrf_exempt
def verify_tip_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reference_id = data.get('reference_id')
            tip_id = data.get('tip_id')
            status = data.get('status')
            
            print(f"Received payment verification request: {data}")  # Debug log
            
            if not tip_id:
                return JsonResponse({'error': 'Missing tip_id'}, status=400)
            
            # Get the tip
            tip = get_object_or_404(Tip, id=tip_id)
            print(f"Found tip: {tip.id}, current status: {tip.payment_status}")  # Debug log
            
            # Update the payment status
            tip.payment_status = status.upper() if status else 'COMPLETED'
            tip.save()
            print(f"Updated tip status to: {tip.payment_status}")  # Debug log
            
            return JsonResponse({
                'status': 'success',
                'message': 'Payment verified successfully',
                'redirect_url': reverse('restaurant:waiter_review', kwargs={'tip_id': tip_id})
            })
            
        except Tip.DoesNotExist:
            print(f"Tip not found: {tip_id}")  # Debug log
            return JsonResponse({
                'error': 'Tip not found'
            }, status=404)
        except Exception as e:
            print(f"Error verifying payment: {str(e)}")  # Debug log
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
    return JsonResponse({
        'error': 'Invalid request method'
    }, status=405)

def payment_success(request):
    """View for displaying payment success and review page"""
    tip_id = request.GET.get('tip_id')
    waiter_id = request.GET.get('waiter_id')
    
    try:
        if tip_id and waiter_id:
            tip = get_object_or_404(Tip, id=tip_id)
            waiter = get_object_or_404(Waiter, id=waiter_id)
            
            if tip.payment_status != 'COMPLETED':
                messages.error(request, 'Payment not completed')
                return redirect('restaurant:waiter_tip')
            
            context = {
                'tip': tip,
                'waiter': waiter,
            }
            return render(request, 'restaurant/payment_success.html', context)
    except (Tip.DoesNotExist, Waiter.DoesNotExist):
        messages.error(request, 'Invalid tip or waiter information')
    
    return redirect('restaurant:home')

@require_http_methods(["POST"])
def get_waiter_info(request, waiter_id):
    try:
        waiter = Waiter.objects.get(id=waiter_id)
        feedback_stats = Feedback.objects.filter(waiter=waiter).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        
        return JsonResponse({
            'id': waiter.id,
            'full_name': waiter.full_name,
            'average_rating': feedback_stats['avg_rating'] or 0,
            'review_count': feedback_stats['total_reviews'] or 0,
            'joining_date': waiter.joining_date.strftime('%Y-%m-%d') if waiter.joining_date else None,
            'photo_url': waiter.photo.url if waiter.photo else None
        })
    except Waiter.DoesNotExist:
        return JsonResponse({'error': 'Waiter not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["POST"])
def get_waiter_stats(request, waiter_id):
    try:
        waiter = Waiter.objects.get(id=waiter_id)
        tips = Tip.objects.filter(waiter=waiter)
        
        total_tips = sum(tip.amount for tip in tips)
        avg_tip = tips.aggregate(Avg('amount'))['amount__avg'] or 0
        
        return JsonResponse({
            'total_tips': total_tips,
            'average_tip': round(avg_tip, 2),
            'total_customers': tips.count()
        })
    except Waiter.DoesNotExist:
        return JsonResponse({
            'error': 'Waiter not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

@require_http_methods(["POST"])
def submit_feedback(request):
    try:
        data = json.loads(request.body)
        waiter_id = data.get('waiter_id')
        rating = data.get('rating')
        feedback_text = data.get('feedback', '')

        if not all([waiter_id, rating]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        try:
            waiter = Waiter.objects.get(id=waiter_id)
        except Waiter.DoesNotExist:
            return JsonResponse({'error': 'Waiter not found'}, status=404)

        # Save feedback
        Feedback.objects.create(
            waiter=waiter,
            rating=rating,
            comment=feedback_text
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Feedback submitted successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def generate_bill_upi_qr(request):
    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        bill_number = data.get('bill_number')
        table_number = data.get('table_number', 1)  # Default to table 1 if not provided

        if not amount or not bill_number:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Create or update bill record
        bill, created = Bill.objects.get_or_create(
            bill_number=bill_number,
            defaults={
                'amount': amount,
                'table_number': table_number,
                'payment_status': 'PENDING'
            }
        )
        if not created:
            bill.amount = amount
            bill.table_number = table_number
            bill.payment_status = 'PENDING'
            bill.save()

        # Generate UPI payment link
        upi_id = settings.UPI_ID
        merchant_name = quote("Restaurant")
        currency = "INR"
        
        upi_string = f"upi://pay?pa={upi_id}&pn={merchant_name}&am={amount}&cu={currency}&tn=Bill%20{bill_number}"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert QR code to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return JsonResponse({
            'qr_code': qr_code_base64,
            'upi_string': upi_string
        })
        
    except Exception as e:
        print(f"Error in generate_bill_upi_qr: {str(e)}")  # Add logging
        return JsonResponse({
            'error': str(e)
        }, status=400)

@require_http_methods(["POST"])
def verify_bill_payment(request):
    try:
        data = json.loads(request.body)
        bill_number = data.get('bill_number')

        if not bill_number:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Get the bill record
        bill = Bill.objects.get(bill_number=bill_number)

        # In a real implementation, you would verify the payment status
        # with your payment provider here

        # For demo purposes, we'll simulate a successful payment
        time.sleep(2)  # Simulate processing time
        bill.payment_status = 'PAID'
        bill.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Payment verified successfully',
            'redirect_url': '/payment/success/'
        })

    except Bill.DoesNotExist:
        return JsonResponse({'error': 'Bill record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["POST"])
def process_payment(request):
    try:
        data = json.loads(request.body)
        amount = float(data.get('amount'))
        table_number = int(data.get('table_number'))
        payment_method = data.get('payment_method', 'card')

        if not amount or not table_number:
            return JsonResponse({'error': 'Amount and table number are required'}, status=400)

        # Create a bill record
        bill = Bill.objects.create(
            bill_number=generate_bill_number(),
            table_number=table_number,
            amount=amount,
            payment_status='PENDING'
        )

        if payment_method == 'card':
            try:
                # Create Stripe payment intent
                intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),  # Convert to cents
                    currency='inr',
                    metadata={
                        'bill_number': bill.bill_number,
                        'table_number': table_number
                    }
                )

                return JsonResponse({
                    'clientSecret': intent.client_secret,
                    'bill_number': bill.bill_number
                })
            except stripe.error.StripeError as e:
                # Update bill status to failed
                bill.payment_status = 'FAILED'
                bill.save()
                return JsonResponse({'error': str(e)}, status=400)

        return JsonResponse({'error': 'Invalid payment method'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def submit_review(request):
    if request.method == 'POST':
        try:
            rating = request.POST.get('rating')
            comment = request.POST.get('comment', '')
            
            # Create the review
            review = Review.objects.create(
                bill=None,  # Since we're not tracking specific bills for now
                rating=rating,
                comment=comment
            )
            
            messages.success(request, 'Thank you for your review!')
            return redirect('restaurant:home')
            
        except Exception as e:
            messages.error(request, f'Error submitting review: {str(e)}')
            return redirect('restaurant:payment_success')
    
    return redirect('restaurant:payment_success')

def waiter_review(request, tip_id):
    try:
        tip = Tip.objects.get(id=tip_id)
        if tip.payment_status != 'COMPLETED':
            messages.error(request, 'Cannot review before payment is completed')
            return redirect('restaurant:waiter_tip')
            
        context = {
            'waiter': tip.waiter,
            'tip_id': tip_id
        }
        return render(request, 'restaurant/waiter_review.html', context)
    except Tip.DoesNotExist:
        messages.error(request, 'Tip record not found')
        return redirect('restaurant:waiter_tip')

@require_http_methods(["POST"])
def submit_waiter_review(request):
    """Handle waiter review submission"""
    try:
        waiter_id = request.POST.get('waiter_id')
        tip_id = request.POST.get('tip_id')
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment', '').strip()

        if not all([waiter_id, tip_id, rating]) or not (1 <= rating <= 5):
            messages.error(request, 'Invalid review data')
            return redirect('restaurant:home')

        waiter = get_object_or_404(Waiter, id=waiter_id)
        tip = get_object_or_404(Tip, id=tip_id)

        # Use exact current time
        current_time = datetime.strptime("2024-12-17T20:51:53+05:30", "%Y-%m-%dT%H:%M:%S%z")

        # Create the review
        review = WaiterReview.objects.create(
            waiter=waiter,
            tip=tip,
            rating=rating,
            comment=comment,
            created_at=current_time
        )

        # Also create a feedback entry for statistics
        Feedback.objects.create(
            waiter=waiter,
            rating=rating,
            comment=comment,
            created_at=current_time
        )

        # Redirect to success page with review details
        return render(request, 'restaurant/review_success.html', {
            'waiter': waiter,
            'rating': rating,
            'comment': comment
        })

    except Exception as e:
        messages.error(request, f'Error submitting review: {str(e)}')
        return redirect('restaurant:home')

def thank_you(request):
    return render(request, 'restaurant/thank_you.html')

def auth_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin:index')
        return redirect('restaurant:waiter_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next', None)
            if next_url:
                return redirect(next_url)
            elif user.is_staff:
                return redirect('admin:index')
            else:
                return redirect('restaurant:waiter_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            
    return render(request, 'restaurant/auth/login.html')

@login_required(login_url='restaurant:login')
def waiter_dashboard(request):
    try:
        waiter = Waiter.objects.get(user=request.user)
        if not waiter.is_active:
            messages.error(request, 'Your account is not active')
            logout(request)
            return redirect('restaurant:login')
        
        # Get waiter statistics
        total_tips = Tip.objects.filter(
            waiter=waiter, 
            payment_status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        reviews = WaiterReview.objects.filter(waiter=waiter)
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        total_reviews = reviews.count()
        
        # Get recent tips and reviews
        recent_tips = Tip.objects.filter(waiter=waiter).order_by('-created_at')[:10]
        recent_reviews = WaiterReview.objects.filter(waiter=waiter).order_by('-created_at')[:5]
        
        context = {
            'total_tips': total_tips,
            'avg_rating': avg_rating,
            'total_reviews': total_reviews,
            'recent_tips': recent_tips,
            'recent_reviews': recent_reviews,
        }
        
        return render(request, 'restaurant/waiter/dashboard.html', context)
    except Waiter.DoesNotExist:
        messages.error(request, 'No waiter account found for this user')
        logout(request)
        return redirect('restaurant:login')

def custom_logout(request):
    logout(request)
    messages.success(request, 'Successfully logged out')
    return redirect('restaurant:auth_login')

def waiter_logout(request):
    logout(request)
    messages.success(request, 'Successfully logged out')
    return redirect('restaurant:auth_login')
