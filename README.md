# Restaurant QR Code Billing System

A modern restaurant management system that enables QR code-based billing, tipping, and review management.

## Features
- QR Code based table identification
- Digital bill generation
- Integrated Google Reviews
- Stripe payment processing
- Waiter-specific tipping system
- Manager dashboard for transaction monitoring

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a .env file with the following:
```
SECRET_KEY=your_django_secret_key
STRIPE_PUBLIC_KEY=your_stripe_public_key
STRIPE_SECRET_KEY=your_stripe_secret_key
MONGODB_URI=your_mongodb_connection_string
```

4. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Project Structure
- `/restaurant_app`: Main application code
- `/templates`: HTML templates
- `/static`: CSS, JavaScript, and image files
- `/media`: User-uploaded content
