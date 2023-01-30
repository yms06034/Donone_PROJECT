from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.contrib import auth
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required

from rest_framework.parsers import JSONParser

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_text
from .tokens import account_activation_token

from don_home.models import Ably_token, Cafe24
from don_home.apis.ably import AblyDataInfo


# Create your views here.
def index(request):
    username = request.session.get('user')
    if username:
        log = User.objects.get(pk=username)
    else:
        log = '로그인이 필요합니다.'
    return render(request, 'index.html', {'login' : log})

def signup(request):
    if request.method == 'POST':
        if request.POST['password1'] == request.POST['password2']:
            user = User.objects.create_user(
                username=request.POST['username'], 
                password=request.POST['password1'], 
                first_name = request.POST['fullname'],
                email=request.POST['email'])
            user.is_active = False 
            user.save()
            current_site = get_current_site(request) 
            message = render_to_string('account_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            mail_title = "계정 활성화 확인 이메일"
            mail_to = request.POST["email"]
            email = EmailMessage(mail_title, message, to=[mail_to])
            email.send()
            return HttpResponse(
                '<div style="font-size: 40px; width: 100%; height:100%; display:flex; text-align:center; '
                'justify-content: center; align-items: center;">'
                '입력하신 이메일<span>로 인증 링크가 전송되었습니다.</span>'
                '</div>'
            )

    return render(request, 'register/signup.html')

def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        msg = '아이디 또는 패스워드가 일치하지 않습니다.'
        if form.is_valid():
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password')
            user = auth.authenticate(username=username, password=raw_password)
            if user is not None:
                msg = '로그인 성공'
                auth.login(request, user)
                return redirect('app:index')
        return render(request, "register/login.html", {"form": form, "msg" : msg})
    else:
        form = AuthenticationForm()
        return render(request, 'register/login.html', {'form' : form})

def logout(request):
    auth.logout(request)
    return redirect('app:index')


def activate(request, uid64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uid64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        auth.login(request, user)
        return redirect('app:index')
    else:
        return render(request, 'index.hmlt', {'error' : '계정 활성화 오류'})

def checkeusername(request):
    try:
        user = User.objects.get(username=request.GET['username'])
    except Exception as e:
        user = None
    result = {
        'result':'success',
        # 'data' : model_to_dict(user)  # console에서 확인
        'data' : "not exist" if user is None else "exist"
    }
    return JsonResponse(result)

# ABLY
def ably(request):
    if request.method == 'POST':
        ably_user = Ably_token(
            ably_id=request.POST['ablyid'], 
            ably_pw=request.POST['ablypw'],
            user_id = request.user.id)
        ably_user.save()
        return render(request, 'user/ably.html')
    else:
        return render(request, 'user/ably.html')

def ably_crawling(request):
    AblyDataInfo()

# CAFE24
def cafe24(request):
    if request.method == 'POST':
        cafe24_user = Cafe24(
            cafe24_id = request.POST['cafe24id'],
            cafe24_pw = request.POST['cafe24pw'],
            cafe24_clientid = request.POST['cafe24_clientid'],
            cafe24_client_secret = request.POST['cafe24_client_secret'],
            cafe24_mallid = request.POST['cafe24_mallid'],
            cafe24_encode_csrf_token = request.POST['cafe24_encode_csrf_token'],
            cafe24_redirect_uri = request.POST['cafe24_redirect_uri'],
            user_id = request.user.id)
        cafe24_user.save()
        return render(request, 'user/cafe24.html')
    else:
        return render(request, 'user/cafe24.html')

