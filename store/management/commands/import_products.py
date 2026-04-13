import csv
import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Product, Category
from cloudinary.uploader import upload


class Command(BaseCommand):
    help = 'Bulk import products with Cloudinary support (URLs + local images, no duplicates)'

    def handle(self, *args, **kwargs):
        file_path = 'products.csv'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR('products.csv file not found'))
            return

        with open(file_path, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    # ----------------------------
                    # CATEGORY (must exist)
                    # ----------------------------
                    category = Category.objects.get(name=row['category'])

                    # ----------------------------
                    # CREATE PRODUCT (NO DUPLICATES)
                    # ----------------------------
                    product, created = Product.objects.get_or_create(
                        name=row['name'],
                        defaults={
                            'price': float(row['price']),
                            'description': row['description'],
                            'category': category,
                            'is_sale': str(row.get('is_sale', '')).lower() == 'true'
                        }
                    )

                    if not created:
                        self.stdout.write(f"Skipped (already exists): {product.name}")
                        continue

                    # ----------------------------
                    # IMAGE HANDLING (FINAL FIXED)
                    # ----------------------------
                    image_value = row.get('image')

                    if image_value:
                        try:
                            # CASE 1: Cloudinary URL
                            if image_value.startswith("http") and "res.cloudinary.com" in image_value:
                                match = re.search(r'/upload/(?:v\d+/)?(.+)', image_value)

                                if match:
                                    public_id = match.group(1)
                                    public_id = os.path.splitext(public_id)[0]

                                    product.image = public_id
                                else:
                                    self.stdout.write(
                                        self.style.WARNING(f"Invalid Cloudinary URL: {image_value}")
                                    )

                            # CASE 2: Local file → upload to Cloudinary
                            else:
                                image_path = os.path.join(
                                    settings.BASE_DIR,
                                    'media/uploads/product',
                                    image_value
                                )

                                if os.path.exists(image_path):
                                    result = upload(image_path)
                                    product.image = result.get('public_id')
                                else:
                                    self.stdout.write(
                                        self.style.WARNING(f"Image not found: {image_value}")
                                    )

                        except Exception as e:
                            self.stdout.write(
                                self.style.WARNING(f"Image handling failed for {image_value}: {e}")
                            )

                    # Save once at the end (clean + efficient)
                    product.save()

                    self.stdout.write(
                        self.style.SUCCESS(f"Added: {product.name}")
                    )

                except Category.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"Category not found: {row.get('category')}")
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing {row.get('name')}: {e}")
                    )

        self.stdout.write(self.style.SUCCESS('DONE importing products'))