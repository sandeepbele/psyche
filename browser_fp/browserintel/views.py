from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import render
from django.db.models import Count, Q
from django.db.models import F

import json
from random import randint
import pytz
import uuid

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

# include paramater a in the url

@csrf_exempt
def get_raw(request, request_id,r=None):
    try:
        fp_data = FingerprintData.objects.get(request_id=request_id)
        #fp_json = json.loads(fp_data.fingerprint)
        if r is None:
            return JsonResponse(fp_data.fingerprint, json_dumps_params={'indent': 4})
        else:
            return JsonResponse(Fingerprint(fp_data.fingerprint).bot_type(), json_dumps_params={'indent': 4}, safe=False)
    except FingerprintData.DoesNotExist:
        return JsonResponse({'error': 'Fingerprint data not found'})


@csrf_exempt
def decode(request, a=None):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # filter by stable_fp , if found get user_identifier
            # if not found, create new record with user_identifier = anonymous

            # Retrieve the FingerprintData object with the specified ID
            fp = Fingerprint(data)
            fingerprint_data = FingerprintData.objects.filter(stable_fp=fp.stable_digest()).first()
            if fingerprint_data:
                user = fingerprint_data.user_identifier
            else:
                while True:
                    # Generate a random user identifier
                    user = "anon_{randid}".format(randid=randint(1,10000000))
                    if not FingerprintData.objects.filter(user_identifier=user).exists():
                        break
            
            last_visit_record = FingerprintData.objects.filter(user_identifier=user).order_by('-access_time').first()

            # add this request to the database
            fp_data = FingerprintData(fingerprint=data, 
                                      request_id=request.META.get('HTTP_X_REQUEST_ID', uuid.uuid4()),
                                      access_time=timezone.now(), 
                                      ip_address= request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1')),
                                      user_identifier=user, 
                                      )
            fp_data.save()

            if a is None:
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

            elif a == 'short':
                
                greeting = "Welcome!"
                visit_gist = "This is your first visit."
                if last_visit_record:
                    print(last_visit_record.access_time)
                    # Convert the timezone name to a standard timezone name
                    tz = pytz.timezone(fp_data.timezone)  
                    access_time_tz = last_visit_record.access_time.astimezone(tz)
                    greeting =  "Welcome back!"
                    visit_gist =  "Your last visit was on {last_visit}.".format(last_visit=access_time_tz.strftime('%Y-%m-%d %H:%M %Z'))

                bot_text = "You are a <strong>BOT</strong>!" if fp_data.is_bot else "You are <strong>not</strong> a BOT!"

                msg = """<h4 class="alert-heading mb-2">{greeting}</h4>
                    <p>Hello <em>{user}</em>, you are visiting from {ip_address} using <strong>{browser}</strong> on <strong>{device}</strong>. {visit_gist} You have visited <em>{total_visits}</em> times so far and {bot_text}</p>
                    <hr>
                    <p class="mb-0"><small>Reference Id for this visit is {ref}</small></p>""".format(    
                    user=fp_data.user_identifier,
                    greeting=greeting,
                    ip_address=fp_data.ip_address,
                    device=fp_data.device,
                    browser=fp_data.browser,
                    visit_gist=visit_gist,
                    total_visits=FingerprintData.objects.filter(user_identifier=user).count(),
                    bot_text=bot_text,
                    timezone=fp_data.timezone,
                    ref=fp_data.request_id,
                )

                response_data = {'result': {'type':'short', 'msg':msg } }

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