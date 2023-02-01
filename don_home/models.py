from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Test(models.Model):
    pass

class Ably_token(models.Model):
    ably_id = models.CharField(max_length=100)
    ably_pw = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
class Cafe24(models.Model):
    cafe24_id = models.CharField('아이디', max_length=200)
    cafe24_pw = models.CharField('비밀번호', max_length=200)
    cafe24_clientid = models.CharField(max_length=200 , default='none')
    cafe24_client_secret = models.CharField(max_length=200, default='none')
    cafe24_mallid = models.CharField(max_length=200, default='none')
    cafe24_encode_csrf_token = models.CharField(max_length=50 , null=True)
    cafe24_redirect_uri = models.CharField(max_length=200 , default='none')
    service_key = models.CharField(max_length=200, default='none')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    

class AblySalesInfo(models.Model):
    paymentDate = models.CharField(max_length=50)
    productOrderNumber = models.IntegerField()
    orderNumber = models.CharField(max_length=50)
    productName = models.CharField(max_length=150)
    options = models.CharField(max_length=50)
    total = models.IntegerField()
    orderName = models.CharField(max_length=20)
    phoneNumber = models.CharField(max_length=30)
    orderStatus = models.CharField(max_length=20)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class AblyProductInfo(models.Model):
    productNumber = models.CharField(max_length=100)
    productName = models.CharField(max_length=150)
    price = models.CharField(max_length=100)
    discountPeriod = models.CharField(max_length=100)
    discountPrice = models.CharField(max_length=100)
    registrationDate = models.CharField(max_length=100)
    statusDisplay = models.CharField(max_length=100)
    stock = models.CharField(max_length=100)
    totalReview = models.CharField(max_length=100)
    parcel = models.CharField(max_length=100)
    returnShippingCost = models.CharField(max_length=100)
    extraShippingCost = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class NaverProductInfo(models.Model):
    productNumber = models.CharField(max_length=100)
    productName = models.CharField(max_length=100)
    price = models.CharField(max_length=100)	
    discountPrice = models.CharField(max_length=100)	
    basicShippingCost = models.CharField(max_length=100)	
    returnShippingCost = models.CharField(max_length=100)	
    exchangeShippingCost = models.CharField(max_length=100)	
    largeCategory = models.CharField(max_length=100)
    smallCategory = models.CharField(max_length=100)
    productRegistrationDate = models.CharField(max_length=100)
    productModificationDate = models.CharField(max_length=100)	
    user = models.CharField(max_length=100)	      

class NaverSalesPerformance(models.Model):
    saleDate = models.CharField(max_length=100)	
    totalBuyer = models.IntegerField()
    totalPayments = models.IntegerField()
    price = models.IntegerField()
    totalpaymentProduct = models.IntegerField()
    basicShippingCost = models.IntegerField()
    productCoupons = models.IntegerField()
    numberRefunds = models.IntegerField()
    refundAmount = models.IntegerField()
    totalRefund = models.IntegerField()
    user = models.CharField(max_length=100)	

class Cafe24Category(models.Model):
    category_no = models.IntegerField()
    category_depth = models.IntegerField()
    parent_category_no = models.IntegerField()
    category_name = models.TextField()
    display_type = models.TextField()
    large_category = models.TextField()
    mid_category = models.TextField()
    small_category = models.TextField()
    sub_category = models.TextField()
    large_catetgory_no = models.IntegerField()
    mid_category_no = models.IntegerField()
    small_category_no = models.IntegerField()
    sub_category_no = models.IntegerField()
    root_category_no = models.IntegerField()
    use_main = models.CharField(max_length=50)
    display_order = models.IntegerField()

class Cafe24Product(models.Model):
    product_no = models.IntegerField()
    product_code = models.CharField(max_length=50)
    categoty_no = models.IntegerField()
    product_name = models.CharField(max_length=100)
    price_excluding_tax = models.IntegerField()
    price = models.IntegerField()
    retail_price = models.IntegerField()
    supply_price = models.IntegerField()
    display = models.CharField(max_length=100)
    selling = models.CharField(max_length=50)
    product_condition = models.CharField(max_length=50)
    create_date = models.DateTimeField()
    sold_out = models.CharField(max_length=50)

class Cafe24Order(models.Model):
    order_id = models.IntegerField()
    product_no = models.IntegerField()
    product_code = models.CharField(max_length=50)
    benefit_price = models.IntegerField()
    member_id = models.CharField(max_length=50)
    member_email = models.CharField(max_length=100)
    payment_method_name = models.CharField(max_length=100)
    paid = models.CharField(max_length=50)
    canceled = models.CharField(max_length=50)
    order_date = models.CharField(max_length=100)
    first_order = models.CharField(max_length=50)
    order_from_modbil = models.CharField(max_length=50)
    inital_order_amount = models.IntegerField()
    actual_order_amount = models.IntegerField()
    payment_amount = models.IntegerField()
    order_place_name = models.CharField(max_length=50)
    quantity = models.IntegerField()

class Cafe24Coupon(models.Model):
    coupon_no = models.IntegerField()
    benefit_price = models.IntegerField()
    coupon_type = models.CharField(max_length=100)
    coupon_name = models.CharField(max_length=100)
    created_date = models.CharField(max_length=100)
    deleted = models.CharField(max_length=50)
    benefit_text = models.CharField(max_length=100)
    benefit_percentage = models.IntegerField()
    issue_meneber_join = models.CharField(max_length=50)
    issued_count = models.IntegerField()


