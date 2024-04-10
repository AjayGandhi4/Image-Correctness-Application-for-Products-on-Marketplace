from django.shortcuts import render,redirect
from django.http import JsonResponse
import json
import datetime
from .models import *
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm
from django.core.files.storage import FileSystemStorage
import cv2
import numpy as np
import base64
from PIL import Image
from io import BytesIO


# Create your views here.

def store(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total':0, 'get_cart_items':0, 'shipping':False}
        cartItems = order['get_cart_items']

    products = Product.objects.all()
    context = {'products':products,'cartItems':cartItems}
    return render(request, 'store/store.html',context)

def cart(request):
    if request.user.is_authenticated:
        try:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            items = order.orderitem_set.all()
            cartItems = order.get_cart_items
        except Customer.DoesNotExist:
            # If the user doesn't have a customer object, create one
            customer = Customer.objects.create(user=request.user)  # Assuming Customer model has a ForeignKey to User
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            items = order.orderitem_set.all()
            cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0, 'shipping': False}
        cartItems = order['get_cart_items']
        
    context = {'items': items,'order': order, 'cartItems': cartItems}
    return render(request, 'store/cart.html', context)




def checkout(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
        
    else:
        items = []
        order = {'get_cart_total':0, 'get_cart_items':0}
        cartItems = order['get_cart_items']
        
    context = {'items': items,'order':order, 'cartItems':cartItems}
    return render(request, 'store/checkout.html',context)

def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    
    print('Action:', action)
    print('productId:', productId)
    
    customer = request.user.customer
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)
    
    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)
    
    if action == 'add':
        orderItem.quantity = (orderItem.quantity+1)
    elif action == 'remove':
        orderItem.quantity = (orderItem.quantity-1)
        
    orderItem.save()
    
    if orderItem.quantity <= 0:
        orderItem.delete()
        
    return JsonResponse('Item was added', safe=False)

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)
    
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        total = float(data['form']['total'])
        order.transaction_id = transaction_id
        
        if total == order.get_cart_total:
            order.complete = True
        order.save()
        
        if order.shipping == True:
            ShippingAddress.objects.create(
                customer=customer,
                order=order,
                address=data['shipping']['address'],
                city=data['shipping']['city'],
                state=data['shipping']['state'],
                zipcode=data['shipping']['zipcode'],
            )
            
    else:
        print('User is not logged in..')
        
    return JsonResponse('Payment complete!', safe=False)

def color_correction(image):
    lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab_image)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl_image = clahe.apply(l_channel)
    enhanced_lab_image = cv2.merge([cl_image, a_channel, b_channel])
    corrected_image = cv2.cvtColor(enhanced_lab_image, cv2.COLOR_LAB2BGR)
    return corrected_image

def adjust_contrast(image, alpha=1.5, beta=25):
    adjusted_image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    return adjusted_image

def sharpen_image(image):
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    sharpened_image = cv2.filter2D(image, -1, kernel)
    return sharpened_image

def process_image(request):
    if request.method == 'POST' and request.FILES['image']:
        image_file = request.FILES['image']
        fs = FileSystemStorage()
        filename = fs.save(image_file.name, image_file)

        # Read the uploaded image
        input_image = cv2.imread(fs.path(filename))

        # Apply color correction
        color_corrected_image = color_correction(input_image)

        # Adjust contrast
        contrast_adjusted_image = adjust_contrast(color_corrected_image)

        # Sharpen the image
        sharpened_image = sharpen_image(contrast_adjusted_image)

        # Convert processed image to base64 for displaying in HTML
        _, processed_image_data = cv2.imencode('.jpg', sharpened_image)
        processed_image_base64 = base64.b64encode(processed_image_data).decode()

        return render(request, 'store/processed_image.html', {'processed_image': processed_image_base64})

    return render(request, 'store/upload_image.html')

# def login_user(request):
#     if request.method == 'POST':
#         username = request.POST['username']
#         password = request.POST['password']
    
#         # Authenticate
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             messages.success(request, "You have been logged in.")
#             return redirect('store')
#         else:
#             messages.error(request, "There was an error. Please try again....")
#             return redirect('login')
#     else:
#         return render(request, 'login.html', {})

   
# def logout_user(request):
#     logout(request)
#     messages.success(request,"You have been logged out..")
#     return redirect('store')

# def register_user(request):
#     if request.method == 'POST':
#         form = SignUpForm(request.POST)
#         if form.is_valid():
#             form.save()
#             username = form.cleaned_data['username']
#             password = form.cleaned_data['password1']
#             user = authenticate(username=username, password=password)
#             login(request, user)
#             messages.success(request, "You have successfully registered! Welcome!!")
#             return redirect('login')
#     else:
#         form = SignUpForm()
#     return render(request, 'register.html', {'form': form})