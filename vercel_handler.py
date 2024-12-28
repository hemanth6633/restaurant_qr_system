from restaurant_project.wsgi import application

# This is the Vercel handler
def handler(request, **kwargs):
    return application(request, **kwargs)
