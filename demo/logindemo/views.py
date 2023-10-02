from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import MyAuthenticationForm
from django.conf import settings

import requests

def login_view(request):
    if request.method == 'POST':
        form = MyAuthenticationForm(request, request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            fp_id = request.POST.get('id')
            print (f"#####id:{fp_id}  ")
            if fp_id is not None:
                response = requests.post('http://localhost:8000/enigma/b/evaluate_fp/', data={
                    'email': email,
                    'password_hash': password,
                    'ip': request.META.get('REMOTE_ADDR', None),
                    'user_id': email,
                    'endpoint': 'login',
                    'fp_id': fp_id
                })
                if response.status_code == 200 and response.json().get('status') == 'Accept':
                    user = authenticate(request, email=email, password=password)
                    if user is not None:
                        login(request, user)
                        return redirect('home')
                    else:
                        form.add_error(None, f"Invalid email or password: id is {user.id}")
                else:
                    form.add_error(None, f"Sorry BOT..you have been caught!!")
    else:
        form = MyAuthenticationForm(request)
    return render(request, 'login.html', {'form': form, 'FP_API_URL':settings.FP_API_URL})

@login_required
def home_view(request):
    return render(request, 'home.html')

def logout_view(request):
    logout(request)
    return redirect('login')