import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')
django.setup()

from django.contrib.auth.models import User

# Reset password for admin user
admin_user = User.objects.get(username='admin')
new_password = 'Admin@123'  # This will be the new password
admin_user.set_password(new_password)
admin_user.save()

print(f"Password has been reset successfully!")
print(f"Username: admin")
print(f"New password: {new_password}")
