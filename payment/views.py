from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from store.models import Product, Profile
import datetime


# Create your views here.
def orders(request, pk):
	if request.user.is_authenticated and request.user.is_superuser:
		# get the order
		order = Order.objects.get(id=pk)
		# get the order items
		items = OrderItem.objects.filter(order=pk)

		if request.POST:
			status = request.POST['shipping_status']
			# check if true or false
			if status == "true":
				# get the order
				order = Order.objects.filter(id=pk)
				# update the status
				now = datetime.datetime.now()
				order.update(shipped=True, date_shipped=now)

			else:
				# get the order
				order = Order.objects.filter(id=pk)
				# update the status
				order.update(shipped=False)
			return redirect('/?auth=order_success2')



		return render(request, 'payment/orders.html', {'order':order, 'items':items})

	else:
		return redirect('/?auth=billing_error')


def shipped_dash(request):
	if request.user.is_authenticated and request.user.is_superuser:
		orders = Order.objects.filter(shipped=True)

		if request.POST:
			status = request.POST['shipping_status']
			num = request.POST['num']
			# grab the order
			order = Order.objects.filter(id=num)
			# grab date & time
			now = datetime.datetime.now()
			# update order
			order.update(shipped=False)
			# redirect
			return redirect('/?auth=order_success2')

		return render(request, "payment/shipped_dash.html", {"orders":orders})
	else:
		return redirect('/?auth=billing_error') 


def not_shipped_dash(request):
	if request.user.is_authenticated and request.user.is_superuser:
		orders = Order.objects.filter(shipped=False)

		if request.POST:
			status = request.POST['shipping_status']
			num = request.POST['num']
			# grab the order
			order = Order.objects.filter(id=num)
			# grab date & time
			now = datetime.datetime.now()
			# update order
			order.update(shipped=True, date_shipped=now)
			# redirect
			return redirect('/?auth=order_success2')

		return render(request, "payment/not_shipped_dash.html", {"orders":orders})
	else:
		return redirect('/?auth=billing_error')


def process_order(request):
	if request.POST:
		# Get cart
		cart = Cart(request)
		cart_products = cart.get_prods
		quantities = cart.get_quants
		totals = cart.cart_total()

		# get billing info
		payment_form = PaymentForm(request.POST or None)
		# get shipping session data 
		my_shipping = request.session.get('my_shipping')

		# Gather Order info 
		full_name = my_shipping['shipping_full_name']
		email = my_shipping['shipping_email']
		# create shipping Address from session info
		shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_country']}"
		amount_paid = totals


		# create an order
		if request.user.is_authenticated:
			# logged in
			user = request.user
			# Create order 
			create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
			create_order.save()

			# Add order items
			# Get the order Id
			order_id = create_order.pk
			# get product info
			for product in cart_products():
				# Get product Id
				product_id = product.id
				# Get product price
				if product.is_sale:
					price = product.sales_price
				else:
					price = product.price

				# get Quantities
				for key, value in quantities().items():
					if int(key) == product.id:
						# Create order item
						create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value, price=price,)
						create_order_item.save()

			# ✅ Clear cart after checkout
			for key in list(request.session.keys()):
				if key == "session_key":
					# Delete the key
					del request.session[key]

			# delete cart from db (old_cart field)
			current_user = Profile.objects.filter(user__id=request.user.id)
			# delete shopping cart in db (old_cart field)
			current_user.update(old_cart="")



			return redirect('/?auth=order_success')

		else:
			# not logged in
			# Create order 
			create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
			create_order.save()

			# Add order items
			# Get the order Id
			order_id = create_order.pk
			# get product info
			for product in cart_products():
				# Get product Id
				product_id = product.id
				# Get product price
				if product.is_sale:
					price = product.sales_price
				else:
					price = product.price

				# get Quantities
				for key, value in quantities().items():
					if int(key) == product.id:
						# Create order item
						create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value, price=price,)
						create_order_item.save()

			# ✅ Clear cart after checkout
			for key in list(request.session.keys()):
				if key == "session_key":
					# Delete the key
					del request.session[key]

			return redirect('/?auth=order_success')


	else:
		return redirect('/?auth=billing_error')


def billing_info(request):
	if request.POST:
		# Get cart
		cart = Cart(request)
		cart_products = cart.get_prods
		quantities = cart.get_quants
		totals = cart.cart_total()

		# create a session with shipping info
		my_shipping = request.POST
		request.session['my_shipping'] = my_shipping

		# check if user is logged in
		if request.user.is_authenticated:
			# Get the billing Form
			billing_form = PaymentForm()
			return render(request, "payment/billing_info.html", {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_info':request.POST, 'billing_form':billing_form})

		else:
			#not logged in
			# Get the billing Form
			billing_form = PaymentForm()
			return render(request, "payment/billing_info.html", {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_info':request.POST, 'billing_form':billing_form})


		shipping_form = request.POST
		return render(request, "payment/billing_info.html", {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_form':shipping_form})

	else:
		return redirect('/?auth=billing_error')




def checkout(request):
	# Get the cart  
	cart = Cart(request)
	cart_products = cart.get_prods
	quantities = cart.get_quants
	totals = cart.cart_total()

	if request.user.is_authenticated:
		# checkout as logged in user
		# shipping user
		shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
		# shipping form
		shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
		return render(request, "payment/checkout.html", {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_form':shipping_form})

	else:
		# checkout as guest 
		shipping_form = ShippingForm(request.POST or None)
		return render(request, "payment/checkout.html", {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_form':shipping_form})




def payment_success(request):

	return render(request, "payment/payment_success.html", {})