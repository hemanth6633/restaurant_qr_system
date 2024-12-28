from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Waiter, Bill, Review, Tip, Feedback, WaiterReview

class FeedbackInline(admin.TabularInline):
    model = Feedback
    extra = 0
    readonly_fields = ['created_at']
    can_delete = False

class TipInline(admin.TabularInline):
    model = Tip
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    can_delete = False

@admin.register(Waiter)
class WaiterAdmin(admin.ModelAdmin):
    list_display = ('display_photo', 'get_full_name', 'phone_number', 'display_rating', 'total_tips', 'is_active')
    list_filter = ('is_active', 'joining_date')
    search_fields = ('user__first_name', 'user__last_name', 'phone_number')
    readonly_fields = ('display_rating_details', 'total_tips', 'total_reviews', 'rating_chart')
    inlines = [FeedbackInline, TipInline]
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'phone_number', 'photo', 'joining_date', 'is_active')
        }),
        ('Payment Information', {
            'fields': ('upi_id', 'bank_account_number', 'bank_ifsc_code', 'bank_account_name')
        }),
        ('Rating Information', {
            'fields': ('display_rating_details', 'rating_chart'),
            'classes': ('wide',)
        }),
        ('Statistics', {
            'fields': ('total_tips', 'total_reviews'),
        }),
    )

    def display_photo(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />', obj.photo.url)
        return format_html('<div style="width: 50px; height: 50px; border-radius: 50%; background-color: #ccc; display: flex; align-items: center; justify-content: center;">No photo</div>')
    display_photo.short_description = 'Photo'

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

    def display_rating(self, obj):
        avg = obj.feedback.aggregate(Avg('rating'))['rating__avg']
        if avg:
            stars = '★' * int(round(avg))
            empty_stars = '☆' * (5 - int(round(avg)))
            rating_str = f"{avg:.1f}"  
            return format_html(
                '<span style="color: #FFD700;">{}</span>'
                '<span style="color: #DDD;">{}</span>'
                '<span> ({}) </span>',
                stars, empty_stars, rating_str
            )
        return 'No ratings'
    display_rating.short_description = 'Rating'

    def display_rating_details(self, obj):
        ratings = obj.feedback.values('rating').annotate(count=Count('rating')).order_by('-rating')
        total_ratings = obj.feedback.count()
        avg_rating = obj.feedback.aggregate(Avg('rating'))['rating__avg']
        
        if not total_ratings:
            return 'No ratings yet'
        
        html = f'<div style="margin-bottom: 20px;"><h3 style="margin-bottom: 10px;">Average Rating: {avg_rating:.1f} / 5.0</h3>'
        html += f'<p>Total Reviews: {total_ratings}</p></div>'
        
        html += '<div style="margin-bottom: 20px;">'
        for r in range(5, 0, -1):
            count = next((item['count'] for item in ratings if item['rating'] == r), 0)
            percentage = (count / total_ratings * 100) if total_ratings > 0 else 0
            stars = '★' * r + '☆' * (5 - r)
            html += f'''
                <div style="margin-bottom: 8px;">
                    <span style="color: #FFD700; min-width: 100px; display: inline-block;">{stars}</span>
                    <div style="display: inline-block; width: 200px; height: 20px; background-color: #f0f0f0; margin: 0 10px;">
                        <div style="width: {percentage}%; height: 100%; background-color: #FFD700;"></div>
                    </div>
                    <span>{count} ({percentage:.1f}%)</span>
                </div>
            '''
        html += '</div>'
        
        # Recent reviews
        recent_reviews = obj.feedback.order_by('-created_at')[:5]
        if recent_reviews:
            html += '<div><h4 style="margin-bottom: 10px;">Recent Reviews</h4>'
            for review in recent_reviews:
                stars = '★' * review.rating + '☆' * (5 - review.rating)
                date = review.created_at.strftime('%Y-%m-%d')
                comment = review.comment if review.comment else 'No comment'
                html += f'''
                    <div style="margin-bottom: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
                        <div style="color: #FFD700; margin-bottom: 5px;">{stars}</div>
                        <div style="color: #666; font-size: 0.9em;">{date}</div>
                        <div style="margin-top: 5px;">{comment}</div>
                    </div>
                '''
            html += '</div>'
        
        return format_html(html)
    display_rating_details.short_description = 'Rating Details'

    def rating_chart(self, obj):
        # Get the current date and date 6 months ago
        end_date = timezone.now()
        start_date = end_date - timedelta(days=180)
        
        # Get all feedback within the last 6 months
        ratings = obj.feedback.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).order_by('-created_at')
        
        if not ratings:
            return 'No rating history available'
        
        # Group ratings by month manually
        monthly_data = {}
        for rating in ratings:
            month_key = rating.created_at.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'total': rating.rating,
                    'count': 1,
                    'month_name': rating.created_at.strftime('%B %Y')
                }
            else:
                monthly_data[month_key]['total'] += rating.rating
                monthly_data[month_key]['count'] += 1
        
        # Calculate averages and format the HTML
        html = '<div><h4>Rating History (Last 6 Months)</h4>'
        for month_key in sorted(monthly_data.keys(), reverse=True):
            data = monthly_data[month_key]
            avg = data['total'] / data['count']
            stars = '★' * int(round(avg))
            empty_stars = '☆' * (5 - int(round(avg)))
            html += f'''
                <div style="margin-bottom: 10px;">
                    <strong>{data['month_name']}</strong>: 
                    <span style="color: #FFD700;">{stars}</span>
                    <span style="color: #DDD;">{empty_stars}</span>
                    ({avg:.1f} from {data['count']} reviews)
                </div>
            '''
        html += '</div>'
        return format_html(html)
    rating_chart.short_description = 'Rating History'

    def total_tips(self, obj):
        total = obj.tips.filter(payment_status='COMPLETED').aggregate(Sum('amount'))['amount__sum']
        return f'₹{total:.2f}' if total else '₹0.00'
    total_tips.short_description = 'Total Tips'

    def total_reviews(self, obj):
        return obj.feedback.count()
    total_reviews.short_description = 'Total Reviews'

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'table_number', 'amount', 'payment_status', 'created_at')
    list_filter = ('payment_status', 'created_at')
    search_fields = ('bill_number', 'table_number')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Bill Information', {
            'fields': ('bill_number', 'table_number', 'amount')
        }),
        ('Payment Details', {
            'fields': ('payment_status', 'payment_method', 'created_at')
        }),
    )

@admin.register(Tip)
class TipAdmin(admin.ModelAdmin):
    list_display = ('waiter', 'amount', 'payment_status', 'created_at', 'reference_id')
    list_filter = ('payment_status', 'created_at')
    search_fields = ('waiter__user__first_name', 'waiter__user__last_name', 'reference_id')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Tip Information', {
            'fields': ('waiter', 'amount')
        }),
        ('Payment Details', {
            'fields': ('payment_status', 'reference_id', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('waiter')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('waiter', 'rating', 'created_at', 'comment')
    list_filter = ('rating', 'created_at')
    search_fields = ('waiter__user__first_name', 'waiter__user__last_name', 'comment')
    readonly_fields = ('created_at',)

@admin.register(WaiterReview)
class WaiterReviewAdmin(admin.ModelAdmin):
    list_display = ('waiter', 'display_rating', 'display_created_at', 'comment')
    list_filter = ('rating', 'created_at')
    search_fields = ('waiter__user__first_name', 'waiter__user__last_name', 'comment')
    readonly_fields = ('created_at', 'rating', 'waiter', 'tip')

    def display_rating(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #FFD700;">{}</span> ({})', stars, obj.rating)
    display_rating.short_description = 'Rating'

    def display_created_at(self, obj):
        return obj.created_at.astimezone(timezone.get_default_timezone()).strftime('%Y-%m-%d %H:%M:%S')
    display_created_at.admin_order_field = 'created_at'
    display_created_at.short_description = 'Review Time (IST)'

# Customize admin site
admin.site.site_header = 'Restaurant Management System'
admin.site.site_title = 'Restaurant Admin'
admin.site.index_title = 'Restaurant Management'
