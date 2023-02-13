DATABASES = {
    'default' : {
        'ENGINE'  : 'django.db.backends.mysql',
        'NAME'    : 'dononedb',
        'USER'    : 'root',
        'PASSWORD': '&donone1!K&',
        'HOST'    : 'donone-db.cyfp8pevwfx6.ap-northeast-1.rds.amazonaws.com',
        'PORT'    : '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset'     : 'utf8mb4',
            'use_unicode' : True,
        },
    }
}

MYSQL_CONN = "mysql+pymysql://root:&donone1!K&@donone-db.cyfp8pevwfx6.ap-northeast-1.rds.amazonaws.com:3306/dononedb"

SECRET_KEY = {
    'secret'   :'django-insecure-m7%ce0hnimxn*)+o#6e76cb28^7k*-+bx6jvxl6#vm=m)$h!iv',
    'algorithm':'HS256' 
}


EMAIL = {
    'EMAIL_BACKEND'      :'django.core.mail.backends.smtp.EmailBackend', 
    'EMAIL_USE_TLS'      : True,      
    'EMAIL_PORT'         : 587,                   
    'EMAIL_HOST'         : 'smtp.gmail.com',
    'EMAIL_HOST_USER'    : 'donone0127@gmail.com',
    'EMAIL_HOST_PASSWORD': 'fazrblhekbzosnzi',
    'SERVER_EMAIL'       : 'donone0127',
    'REDIRECT_PAGE'      : 'http://127.0.0.1:8000',
    'DEFAULT_FROM_EMAIL' : 'donone0127@gmail.com',
}