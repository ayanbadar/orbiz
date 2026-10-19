from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.products.channel3 import Channel3Error, Channel3NotConfigured
from apps.products.models import InventoryAdjustment, Product
from apps.stores.services import create_store_for_user

PASSWORD = "Orb1z-pass"

TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    CHANNEL3_API_KEY="test-key",
)


@override_settings(**TEST_SETTINGS)
class ProductApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="seller@example.com", password=PASSWORD, first_name="S")
        self.other = User.objects.create_user(email="other@example.com", password=PASSWORD, first_name="O")
        self.store = create_store_for_user(
            user=self.user,
            name="Demo Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )
        self.other_store = create_store_for_user(
            user=self.other,
            name="Other Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )

    def test_unauthenticated_rejected(self):
        response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_store_returns_404(self):
        lonely = User.objects.create_user(email="lonely@example.com", password=PASSWORD, first_name="L")
        self.client.force_authenticate(lonely)
        response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_list_and_scope(self):
        self.client.force_authenticate(self.user)
        created = self.client.post(
            "/api/v1/products/",
            {
                "name": "Black Hoodie",
                "sku": "hood-blk-m",
                "price": "49.00",
                "stock_quantity": 12,
                "low_stock_threshold": 5,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["sku"], "HOOD-BLK-M")
        self.assertEqual(created.data["currency"], "USD")
        self.assertFalse(created.data["is_low_stock"])

        listed = self.client.get("/api/v1/products/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        results = listed.data["results"] if isinstance(listed.data, dict) else listed.data
        self.assertEqual(len(results), 1)

        self.client.force_authenticate(self.other)
        other_list = self.client.get("/api/v1/products/")
        other_results = other_list.data["results"] if isinstance(other_list.data, dict) else other_list.data
        self.assertEqual(len(other_results), 0)

        foreign = self.client.get(f"/api/v1/products/{created.data['id']}/")
        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_name_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/products/",
            {"name": "   ", "sku": "X1", "price": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_adjust_stock_and_block_negative(self):
        self.client.force_authenticate(self.user)
        product = Product.objects.create(
            store=self.store,
            name="Tee",
            sku="TEE-1",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=3,
        )
        ok = self.client.post(
            f"/api/v1/products/{product.id}/adjust-stock/",
            {"delta": -1, "reason": "Sold offline"},
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 2)
        self.assertEqual(InventoryAdjustment.objects.filter(product=product).count(), 1)

        bad = self.client.post(
            f"/api/v1/products/{product.id}/adjust-stock/",
            {"delta": -10, "reason": "Too much"},
            format="json",
        )
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 2)

    def test_zero_delta_rejected(self):
        self.client.force_authenticate(self.user)
        product = Product.objects.create(
            store=self.store,
            name="Tee",
            sku="TEE-Z",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=3,
        )
        response = self.client.post(
            f"/api/v1/products/{product.id}/adjust-stock/",
            {"delta": 0, "reason": "noop"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_sku_rejected(self):
        self.client.force_authenticate(self.user)
        Product.objects.create(
            store=self.store,
            name="A",
            sku="SKU-1",
            price=Decimal("1.00"),
            currency="USD",
        )
        response = self.client.post(
            "/api/v1/products/",
            {"name": "B", "sku": "sku-1", "price": "2.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_low_stock_filter(self):
        self.client.force_authenticate(self.user)
        Product.objects.create(
            store=self.store,
            name="Low",
            sku="LOW",
            price=Decimal("1.00"),
            currency="USD",
            stock_quantity=2,
            low_stock_threshold=5,
        )
        Product.objects.create(
            store=self.store,
            name="Ok",
            sku="OK",
            price=Decimal("1.00"),
            currency="USD",
            stock_quantity=20,
            low_stock_threshold=5,
        )
        response = self.client.get("/api/v1/products/?low_stock=true")
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["sku"], "LOW")

    def test_list_query_count_bounded(self):
        self.client.force_authenticate(self.user)
        for i in range(8):
            Product.objects.create(
                store=self.store,
                name=f"P{i}",
                sku=f"SKU-{i}",
                price=Decimal("1.00"),
                currency="USD",
            )
        # Membership + count + page — must not scale with catalog size.
        with self.assertNumQueries(3):
            response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("apps.products.serializers.search_products")
    def test_channel3_search(self, mock_search):
        mock_search.return_value = {
            "results": [
                {
                    "channel3_product_id": "abc",
                    "title": "Hoodie",
                    "description": "",
                    "image_url": "",
                    "suggested_price": "40.00",
                    "currency": "USD",
                    "brand": None,
                    "availability": "InStock",
                }
            ],
            "next_page_token": None,
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/products/channel3/search/",
            {"query": "hoodie"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["channel3_product_id"], "abc")

    @patch("apps.products.serializers.search_products")
    def test_channel3_not_configured_returns_503(self, mock_search):
        mock_search.side_effect = Channel3NotConfigured("Channel3 is not configured (CHANNEL3_API_KEY).")
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/products/channel3/search/",
            {"query": "hoodie"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("Channel3", response.data["detail"])

    @patch("apps.products.serializers.search_products")
    def test_channel3_unreachable_returns_502(self, mock_search):
        mock_search.side_effect = Channel3Error("Channel3 is unreachable right now.")
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/products/channel3/search/",
            {"query": "hoodie"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    @patch("apps.products.serializers.retrieve_product")
    def test_import_from_channel3(self, mock_retrieve):
        mock_retrieve.return_value = {
            "channel3_product_id": "c3-1",
            "title": "Imported Hoodie",
            "description": "Soft",
            "image_url": "https://example.com/h.jpg",
            "suggested_price": "55.00",
            "currency": "USD",
            "brand": "Brand",
            "availability": "InStock",
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/products/import-from-channel3/",
            {
                "channel3_product_id": "c3-1",
                "sku": "IMP-1",
                "price": "49.00",
                "stock_quantity": 8,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["channel3_product_id"], "c3-1")
        self.assertEqual(response.data["name"], "Imported Hoodie")
        self.assertTrue(Product.objects.filter(store=self.store, sku="IMP-1").exists())

    @patch("apps.products.serializers.retrieve_product")
    def test_duplicate_channel3_import_returns_409(self, mock_retrieve):
        Product.objects.create(
            store=self.store,
            name="Existing",
            sku="EXIST",
            price=Decimal("10.00"),
            currency="USD",
            channel3_product_id="c3-dup",
        )
        mock_retrieve.return_value = {
            "channel3_product_id": "c3-dup",
            "title": "Dup",
            "description": "",
            "image_url": "",
            "suggested_price": "10.00",
            "currency": "USD",
            "brand": None,
            "availability": "InStock",
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/products/import-from-channel3/",
            {
                "channel3_product_id": "c3-dup",
                "sku": "NEW-SKU",
                "price": "12.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data.get("existing_sku"), "EXIST")

    @patch("apps.products.serializers.retrieve_product")
    def test_import_sanitizes_bad_image_url(self, mock_retrieve):
        mock_retrieve.return_value = {
            "channel3_product_id": "c3-img",
            "title": "No Image",
            "description": "",
            "image_url": "not-a-url",
            "suggested_price": "10.00",
            "currency": "USD",
            "brand": None,
            "availability": "InStock",
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/products/import-from-channel3/",
            {
                "channel3_product_id": "c3-img",
                "sku": "IMG-1",
                "price": "10.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["image_url"], "")

    def test_check_stock_available(self):
        self.client.force_authenticate(self.user)
        product = Product.objects.create(
            store=self.store,
            name="In Stock",
            sku="CHK-OK",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=5,
        )
        response = self.client.post(
            f"/api/v1/products/{product.id}/check-stock/",
            {"quantity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["available"])
        self.assertEqual(response.data["stock_quantity"], 5)
        self.assertEqual(response.data["requested_quantity"], 3)

    def test_check_stock_insufficient(self):
        self.client.force_authenticate(self.user)
        product = Product.objects.create(
            store=self.store,
            name="Low",
            sku="CHK-LOW",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=2,
        )
        response = self.client.post(
            f"/api/v1/products/{product.id}/check-stock/",
            {"quantity": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)

    def test_check_stock_inactive_rejected(self):
        self.client.force_authenticate(self.user)
        product = Product.objects.create(
            store=self.store,
            name="Off",
            sku="CHK-OFF",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=10,
            is_active=False,
        )
        response = self.client.post(
            f"/api/v1/products/{product.id}/check-stock/",
            {"quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivate_product(self):
        self.client.force_authenticate(self.user)
        product = Product.objects.create(
            store=self.store,
            name="Live",
            sku="DEACT-1",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=4,
        )
        response = self.client.delete(f"/api/v1/products/{product.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_active"])
        product.refresh_from_db()
        self.assertFalse(product.is_active)

    def test_out_of_stock_filter(self):
        self.client.force_authenticate(self.user)
        Product.objects.create(
            store=self.store,
            name="Gone",
            sku="OOS-1",
            price=Decimal("1.00"),
            currency="USD",
            stock_quantity=0,
        )
        Product.objects.create(
            store=self.store,
            name="Has Stock",
            sku="OOS-2",
            price=Decimal("1.00"),
            currency="USD",
            stock_quantity=4,
        )
        response = self.client.get("/api/v1/products/?out_of_stock=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["sku"], "OOS-1")

    def test_list_pagination(self):
        self.client.force_authenticate(self.user)
        for i in range(3):
            Product.objects.create(
                store=self.store,
                name=f"Page item {i}",
                sku=f"PAGE-{i}",
                price=Decimal("1.00"),
                currency="USD",
            )
        page1 = self.client.get("/api/v1/products/?page_size=2&ordering=sku")
        self.assertEqual(page1.status_code, status.HTTP_200_OK)
        self.assertEqual(page1.data["count"], 3)
        self.assertEqual(len(page1.data["results"]), 2)
        self.assertIsNotNone(page1.data["next"])
        self.assertIsNone(page1.data["previous"])

        page2 = self.client.get("/api/v1/products/?page_size=2&page=2&ordering=sku")
        self.assertEqual(page2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(page2.data["results"]), 1)
        self.assertIsNone(page2.data["next"])
        self.assertIsNotNone(page2.data["previous"])

    def test_reactivate_via_patch(self):
        self.client.force_authenticate(self.user)
        product = Product.objects.create(
            store=self.store,
            name="Off",
            sku="REACT-1",
            price=Decimal("1.00"),
            currency="USD",
            stock_quantity=2,
            is_active=False,
        )
        response = self.client.patch(
            f"/api/v1/products/{product.id}/",
            {"is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_active"])


