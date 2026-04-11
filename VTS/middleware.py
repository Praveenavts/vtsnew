# middleware.py
import requests
from django.core.cache import cache
from django.utils import timezone
from .models import VisitorLog
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Extracts the actual IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class VisitorTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response

        ip = get_client_ip(request)
        if ip:
            cache_key = f"ip_location_{ip}"
            location_data = cache.get(cache_key)

            if not location_data:
                try:
                    res = requests.get(f'http://ip-api.com/json/{ip}', timeout=2)
                    if res.status_code == 200:
                        data = res.json()
                        location_data = {
                            'city': data.get('city', 'Unknown'),
                            'country': data.get('country', 'Unknown')
                        }
                        cache.set(cache_key, location_data, 86400)
                    else:
                        location_data = {'city': 'Unknown', 'country': 'Unknown'}
                except Exception as e:
                    logger.warning(f"Could not get location for IP {ip}: {e}")
                    location_data = {'city': 'Unknown', 'country': 'Unknown'}

            now = timezone.localtime(timezone.now())
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_log = VisitorLog.objects.filter(
                ip_address=ip,
                timestamp__gte=start_of_day 
            ).first()
            
            if not today_log:
                VisitorLog.objects.create(
                    ip_address=ip,
                    city=location_data.get('city', 'Unknown'),
                    country=location_data.get('country', 'Unknown'),
                    path=request.path
                )
            else:
                visited_paths = [p.strip() for p in today_log.path.split(',')]
                
                if request.path not in visited_paths:
                    new_path_string = f"{today_log.path}, {request.path}"

                    if len(new_path_string) <= 255:
                        today_log.path = new_path_string
                        today_log.save()
        return response