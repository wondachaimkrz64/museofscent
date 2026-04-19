from django.shortcuts import render, redirect
from .models import Category, Product, Profile
from django.contrib.auth import authenticate, login, logout
#from django.contrib import messages
from django.contrib.auth.models import User 
from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django import forms
from django.db.models import Q 
import json
from cart.cart import Cart
from django.core.paginator import Paginator


# Create your views here.
def search(request):
	# Determine if they filled out the form
	if request.method == "POST":
		searched = request.POST['searched']
		# Query the Product DB Model
		searched = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
		# test for null
		if not searched:
			#messages.success(request, "That product does not exist... try searching for something else!")
			#return render(request, "search.html", {})
			return redirect('/search/?auth=search_error')

		else:
			return render(request, "search.html", {'searched':searched})
	else:
		return render(request, "search.html", {})



def update_info(request):
	if request.user.is_authenticated:
		# Get Current User
		current_user = Profile.objects.get(user__id=request.user.id)
		# Get Current User's Shipping Info 
		shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
		# Get Original User Form 
		form = UserInfoForm(request.POST or None, instance=current_user)
		# Get User's Shipping Form 
		shipping_form = ShippingForm(request.POST or None, instance=shipping_user)

		if form.is_valid() or shipping_form.is_valid():
			# Save Original Form
			form.save()
			# Save Shipping Form
			shipping_form.save()
			return redirect('/?auth=info_updated')
		return render(request, 'update_info.html', {'form':form, 'shipping_form':shipping_form})

	else:
		return redirect('/?auth=login_required')



def update_password(request):
	if request.user.is_authenticated:
		current_user = request.user 
		# Did they fill out the form 
		if request.method == 'POST':
			form = ChangePasswordForm(current_user, request.POST)
			# is the form valid
			if form.is_valid():
				form.save()
				login(request, current_user)
				return redirect('/update_user/?auth=password_updated')
			else:
				return redirect('/update_password/?auth=password_error')


		else:
			form = ChangePasswordForm(current_user)
			return render(request, 'update_password.html', {'form':form})

	else:
		return redirect('/?auth=login_required')

def update_user(request):
	if request.user.is_authenticated:
		current_user = User.objects.get(id=request.user.id)
		user_form = UpdateUserForm(request.POST or None, instance=current_user)

		if user_form.is_valid():
			user_form.save()

			login(request, current_user)
			return redirect('/?auth=profile_updated')
		return render(request, 'update_user.html', {'user_form':user_form})

	else:
		return redirect('/?auth=login_required')


def category_summary(request):
	categories = Category.objects.all()
	return render(request, 'category_summary.html', {'categories':categories})


def category(request, foo):
	#Replace hyphens with spaces
	foo = foo.replace('-', ' ')
	#Grab the category from the url
	try:
		# Look up the category
		category = Category.objects.get(name__iexact=foo)
		products = Product.objects.filter(category=category)
		return render(request, 'category.html', {'products':products, 'category':category})

	except Category.DoesNotExist:
		return redirect('/?auth=category_error')


def product(request, pk):
	product = Product.objects.get(id=pk)
	return render(request, 'product.html', {'product':product})


def home(request):
    product_list = Product.objects.all().order_by('-id')

    paginator = Paginator(product_list, 8)  # number of products per page

    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    return render(request, 'home.html', {
        'products': products
    })

def about(request):
	return render(request, 'about.html', {})



def login_user(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Do some shopping cart stuff
            current_user = Profile.objects.get(user__id=request.user.id)
            # Get their saved cart From database
            saved_cart = current_user.old_cart
            # Convert database string to python dic
            if saved_cart:
            	# convert to dictionary using json
            	converted_cart = json.loads(saved_cart)
            	# Add the loaded cart dictionary to our session
            	# Get the cart
            	cart = Cart(request)
            	# loop through the cart and add the item from the db

            	for key, value in converted_cart.items():
            		cart.db_add(product=key, quantity=value)



            return redirect('/?auth=login_success')
        else:
        	return redirect('/login/?auth=login_error')

    return render(request, 'login.html', {})



def logout_user(request):
	logout(request)
	return redirect('/?auth=logout_success')

def register_user(request):
	form = SignUpForm()
	if request.method == "POST":
		form =SignUpForm(request.POST)
		if form.is_valid():
			form.save()
			username = form.cleaned_data['username']
			password = form.cleaned_data['password1']
			# log in user
			user = authenticate(username=username, password=password)
			login(request, user)

			return redirect('/update_info/?auth=register_success')
		else:
			return redirect('/register/?auth=register_error')
	else:
		return render(request, 'register.html', {'form':form})
		
