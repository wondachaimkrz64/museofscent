from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from store.models import Product, Profile
import datetime
import requests
from django.conf import settings
from django.utils import timezone
import uuid
import hmac
import hashlib
import json
from django.http import HttpResponse
from django.core.mail import send_mail


# Create your views here.
def orders(request, pk):
	if request.user.is_authenticated and request.user.is_superuser:
		try:
			order = Order.objects.get(id=pk)
		except Order.DoesNotExist:
			return redirect('/?auth=billing_error')

		items = OrderItem.objects.filter(order=pk)

		if request.POST:
			status = request.POST['shipping_status']

			if status == "true":
				now = datetime.datetime.now()
				Order.objects.filter(id=pk).update(shipped=True, date_shipped=now)
			else:
				Order.objects.filter(id=pk).update(shipped=False)

			return redirect('/?auth=order_success2')

		return render(request, 'payment/orders.html', {'order':order, 'items':items})

	return redirect('/?auth=billing_error')


def shipped_dash(request):
	if request.user.is_authenticated and request.user.is_superuser:
		orders = Order.objects.filter(shipped=True)

		if request.POST:
			num = request.POST['num']
			Order.objects.filter(id=num).update(shipped=False)
			return redirect('/?auth=order_success2')

		return render(request, "payment/shipped_dash.html", {"orders":orders})

	return redirect('/?auth=billing_error') 


def not_shipped_dash(request):
	if request.user.is_authenticated and request.user.is_superuser:
		orders = Order.objects.filter(shipped=False)

		if request.POST:
			num = request.POST['num']
			now = datetime.datetime.now()
			Order.objects.filter(id=num).update(shipped=True, date_shipped=now)
			return redirect('/?auth=order_success2')

		return render(request, "payment/not_shipped_dash.html", {"orders":orders})

	return redirect('/?auth=billing_error')


def process_order(request):
	if request.POST:
		cart = Cart(request)
		cart_products = cart.get_prods
		quantities = cart.get_quants
		totals = cart.cart_total()

		my_shipping = request.session.get('my_shipping')

		if not my_shipping:
			return redirect('/?auth=billing_error')

		full_name = my_shipping['shipping_full_name']
		email = my_shipping['shipping_email']

		shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_country']}"
		amount_paid = totals

		reference = str(uuid.uuid4())

		if request.user.is_authenticated:
			user = request.user
			create_order = Order.objects.create(
				user=user,
				full_name=full_name,
				email=email,
				shipping_address=shipping_address,
				amount_paid=amount_paid,
				reference=reference
			)

			order_id = create_order.pk

			for product in cart_products():
				price = product.sales_price if product.is_sale else product.price

				for key, value in quantities().items():
					if int(key) == product.id:
						OrderItem.objects.create(
							order_id=order_id,
							product_id=product.id,
							user=user,
							quantity=value,
							price=price
						)

			for key in list(request.session.keys()):
				if key == "session_key":
					del request.session[key]

			Profile.objects.filter(user__id=request.user.id).update(old_cart="")

			return redirect('initialize_payment', order_id=create_order.id)

		else:
			create_order = Order.objects.create(
				full_name=full_name,
				email=email,
				shipping_address=shipping_address,
				amount_paid=amount_paid,
				reference=reference
			)

			order_id = create_order.pk

			for product in cart_products():
				price = product.sales_price if product.is_sale else product.price

				for key, value in quantities().items():
					if int(key) == product.id:
						OrderItem.objects.create(
							order_id=order_id,
							product_id=product.id,
							quantity=value,
							price=price
						)

			for key in list(request.session.keys()):
				if key == "session_key":
					del request.session[key]

			return redirect('initialize_payment', order_id=create_order.id)

	return redirect('/?auth=billing_error')


def initialize_payment(request, order_id):
	try:
		order = Order.objects.get(id=order_id)
	except Order.DoesNotExist:
		return redirect('payment_failed')

	url = "https://api.paystack.co/transaction/initialize"
	headers = {
		"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
		"Content-Type": "application/json",
	}

	data = {
		"email": order.email,
		"amount": int(order.amount_paid * 100),
		"reference": order.reference,
		"callback_url": "https://museofscent.com/payment/verify/",
	}

	try:
		response = requests.post(url, json=data, headers=headers)
		res_data = response.json()

		if res_data.get("status"):
			return redirect(res_data["data"]["authorization_url"])
	except Exception:
		pass

	return redirect('payment_failed')


def verify_payment(request):
	reference = request.GET.get("reference")

	if not reference:
		return redirect('payment_failed')

	try:
		order = Order.objects.get(reference=reference)
	except Order.DoesNotExist:
		return redirect('payment_failed')

	# Prevent duplicate processing
	if order.paid:
		return redirect('payment_success')

	url = f"https://api.paystack.co/transaction/verify/{reference}"
	headers = {
		"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
	}

	try:
		response = requests.get(url, headers=headers)
		res_data = response.json()

		if not res_data.get("status"):
			return redirect('payment_failed')

		data = res_data.get("data", {})

		if (
			data.get("status") == "success"
			and data.get("amount") == int(order.amount_paid * 100)
			and data.get("currency") == "NGN"
		):
			order.paid = True
			order.payment_date = timezone.now()
			order.save()

			# ✅ SEND EMAIL HERE
			send_order_email(order)

			return redirect('payment_success')

	except Exception:
		pass

	return redirect('payment_failed')


def paystack_webhook(request):
	secret_key = settings.PAYSTACK_SECRET_KEY

	hash = hmac.new(
		secret_key.encode('utf-8'),
		request.body,
		hashlib.sha512
	).hexdigest()

	paystack_signature = request.headers.get('x-paystack-signature')

	if hash != paystack_signature:
		return HttpResponse(status=400)

	payload = json.loads(request.body)

	if payload["event"] == "charge.success":
		data = payload["data"]
		reference = data["reference"]

		try:
			order = Order.objects.get(reference=reference)

			# ✅ Prevent duplicate webhook processing
			if not order.paid:
				order.paid = True
				order.payment_date = timezone.now()
				order.save()

		except Order.DoesNotExist:
			pass

	return HttpResponse(status=200)


def payment_failed(request):
	return render(request, "payment/payment_failed.html", {})


def billing_info(request):
	if request.POST:
		cart = Cart(request)
		cart_products = cart.get_prods
		quantities = cart.get_quants
		totals = cart.cart_total()

		request.session['my_shipping'] = request.POST
		billing_form = PaymentForm()

		return render(request, "payment/billing_info.html", {
			'cart_products':cart_products,
			'quantities':quantities,
			'totals':totals,
			'shipping_info':request.POST,
			'billing_form':billing_form
		})

	return redirect('/?auth=billing_error')


def checkout(request):
	cart = Cart(request)
	cart_products = cart.get_prods
	quantities = cart.get_quants
	totals = cart.cart_total()

	if request.user.is_authenticated:
		shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
		shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
	else:
		shipping_form = ShippingForm(request.POST or None)

	return render(request, "payment/checkout.html", {
		'cart_products':cart_products,
		'quantities':quantities,
		'totals':totals,
		'shipping_form':shipping_form
	})


def send_order_email(order):
	subject = "Your Order Confirmation - MuseOfScent"

	message = f"""
Hi {order.full_name},

Thank you for your purchase!

Order Details:
-------------------------
Order Reference: {order.reference}
Amount Paid: ₦{order.amount_paid}

Shipping Address:
{order.shipping_address}

-------------------------
Your order is being processed and will be shipped soon.

Thank you for shopping with us!
MuseOfScent
"""

	send_mail(
		subject,
		message,
		settings.EMAIL_HOST_USER,
		[order.email],
		fail_silently=True,
	)





def payment_success(request):
	return render(request, "payment/payment_success.html", {})