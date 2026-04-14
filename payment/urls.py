from django.urls import path
from . import views

urlpatterns = [
	path('payment_success/', views.payment_success, name='payment_success'),
	path('payment/failed/', views.payment_failed, name='payment_failed'),
	path('checkout/', views.checkout, name='checkout'),
	path('billing_info/', views.billing_info, name='billing_info'),
	path('process_order/', views.process_order, name='process_order'),
	path('shipped_dash/', views.shipped_dash, name='shipped_dash'),
	path('not_shipped_dash/', views.not_shipped_dash, name='not_shipped_dash'),
	path('orders/<int:pk>/', views.orders, name='orders'),
	path('pay/<int:order_id>/', views.initialize_payment, name='initialize_payment'),
	path('verify/', views.verify_payment, name='verify_payment'),
	path('webhook/', views.paystack_webhook, name='paystack_webhook'),
]