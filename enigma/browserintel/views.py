from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import render
from django.db.models import Count, Q
from django.db.models import F

import json

from .fp import Fingerprint
from .models import FingerprintData
from .utils import check_compromised_email, check_compromised_password

def fp_analyse(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Do some processing with the data
            fp = Fingerprint(data)
             # Replace with your own logic
            response_data = {'result': fp.summary()}
            return JsonResponse(response_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'})
    else:
        return JsonResponse({'error': 'Invalid request method'})
    

@csrf_exempt
def decode(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Do some processing with the data
            #fp = Fingerprint(data)
            fp_data = FingerprintData(fingerprint=data, 
                                      access_time=timezone.now(), 
                                      ip_address=request.META.get('REMOTE_ADDR', None),
                                      user_identifier="anonymous", 
                                      )
            fp_data.save()

            queryset = FingerprintData.objects.filter(user_identifier="anonymous").values('device', 'browser', 'ip_address').annotate(
                num_accesses=Count('id'),
                num_bot_accesses=Count('id', filter=Q(is_bot=True))
            ).distinct()
            queryset = queryset.order_by('-num_accesses')

            # Convert the queryset to a dictionary
            associated_devices = []
            ip_addresses = []
            total_visits = 0
            total_anomalies = 0
            for item in queryset:
                associated_devices.append(f"{item['device']}|{item['browser']}")
                ip_addresses.append(item['ip_address'])
                total_visits += item['num_accesses']
                total_anomalies += item['num_bot_accesses']
            result = {
                'associated_devices': associated_devices,
                'associated ips': ip_addresses,
                'total_visits': total_visits,
                'total_anomalies': total_anomalies
            }

            response_data = {'result': {**fp_data.to_dict(), **result}}
            return JsonResponse(response_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'})
    else:
        return JsonResponse({'error': 'Invalid request method'})


def index(request):
    return render(request, 'creep_custom.html')

# make everything ready to run


def get_chart_data(request):
    data = FingerprintData.objects.filter(user_identifier="anonymous").values('access_time', 'browser', 'device')
    chart_data = []
    for item in data:
        chart_data.append({
            'x': item['access_time'].strftime('%Y-%m-%d %H:%M:%S'),
            'y': item['access_time'].strftime('%Y-%m-%d %H:%M:%S'),
            'browser': item['browser'],
            'device': item['device']
        })
    return JsonResponse(chart_data, safe=False)


@csrf_exempt
def evaluate_fp(request):
    """
    Evaluates a fingerprint for potential fraud.

    Args:
        request: A Django request object.

    Returns:
        A JSON response indicating the status of the fingerprint evaluation.
        If the fingerprint is accepted, the response will have a status code of 200
        and a 'status' key with a value of 'Accept'.
        If the fingerprint requires review, the response will have a status code of 302
        and a 'status' key with a value of 'Review'.
        If the fingerprint is blocked, the response will have a status code of 401
        and a 'status' key with a value of 'Blocked'.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password_hash = request.POST.get('password_hash')
        ip = request.POST.get('ip')
        user_id = request.POST.get('user_id')
        endpoint = request.POST.get('endpoint')
        fp_id = request.POST.get('fp_id')

        # Retrieve the FingerprintData object with the specified ID
        fingerprint_data = FingerprintData.objects.get(id=fp_id)

        # Check if the fingerprint data belongs to a bot
        if fingerprint_data.is_bot:
            #add log
            print("bot detected")
            return JsonResponse({'status': 'Blocked'}, status=401)

        # Check if the stable fingerprint exists in the fingerprint data
        if not FingerprintData.objects.filter(stable_fp=fingerprint_data.stable_fp).exists():
            print("stable fingerprint not found")
            return JsonResponse({'status': 'Review'}, status=302)

        # Check if the IP address exists for the stable fingerprint
        if FingerprintData.objects.filter(stable_fp=fingerprint_data.stable_fp, ip_address=fingerprint_data.ip_address).count() > 1:
            print("IP address not found")
            return JsonResponse({'status': 'Review'}, status=302)
        
        # Check if the email is in a compromised credential list
        if check_compromised_email(email) and fingerprint_data.is_bot:
            print("email found in compromised list")
            return JsonResponse({'status': 'Blocked'}, status=401)

        # Check if the password hash is in a compromised credential list
        if check_compromised_password(password_hash) and fingerprint_data.is_bot:
            print("password hash found in compromised list")
            return JsonResponse({'status': 'Blocked'}, status=401)
        
        elif check_compromised_password(password_hash):
            print("password hash found in compromised list")
            return JsonResponse({'status': 'Review'}, status=302)

        # If none of the above conditions are met, return an Accept response
        return JsonResponse({'status': 'Accept'}, status=200)