"""
Strict function-calling mode (tools._to_strict): every TOOL_SCHEMAS entry must satisfy OpenAI's
actual constraints structurally — django.test.TestCase, not AssistantTestCase, since this
doesn't touch the DB or a store at all — plus the None-safety of the handful of dispatch
functions whose Python default isn't None, since strict mode means the model sends an explicit
null for an unset optional argument instead of omitting the key.
"""

from django.test import TestCase

from apps.assistant import tools
from apps.assistant.tests.base import AssistantTestCase
from apps.products.models import Product


def _walk_object_schemas(schema: dict):
    """Every object-with-properties schema in a tool's parameter tree, including nested ones."""
    if not isinstance(schema, dict):
        return
    if schema.get("type") == "object" and "properties" in schema:
        yield schema
        for prop in schema["properties"].values():
            yield from _walk_object_schemas(prop)
    elif schema.get("type") == "array" and "items" in schema:
        yield from _walk_object_schemas(schema["items"])


class ToolSchemaStrictModeTests(TestCase):
    def test_every_tool_is_marked_strict(self):
        for schema in tools.TOOL_SCHEMAS:
            self.assertTrue(schema.get("strict"), schema["name"])

    def test_every_object_forbids_additional_properties_and_requires_every_key(self):
        for tool_schema in tools.TOOL_SCHEMAS:
            for obj in _walk_object_schemas(tool_schema["parameters"]):
                with self.subTest(tool=tool_schema["name"]):
                    self.assertIs(obj["additionalProperties"], False)
                    self.assertEqual(set(obj["required"]), set(obj["properties"].keys()))

    def test_a_property_that_was_not_originally_required_is_nullable(self):
        schema = next(s for s in tools.TOOL_SCHEMAS if s["name"] == "list_unpaid_orders")
        prop = schema["parameters"]["properties"]["min_days_unpaid"]
        self.assertIn("null", prop["type"])

    def test_a_property_that_was_always_required_stays_non_nullable(self):
        schema = next(s for s in tools.TOOL_SCHEMAS if s["name"] == "get_order")
        prop = schema["parameters"]["properties"]["order_number"]
        self.assertEqual(prop["type"], "string")

    def test_nested_object_properties_are_also_strict(self):
        schema = next(s for s in tools.TOOL_SCHEMAS if s["name"] == "create_draft_order")
        customer = schema["parameters"]["properties"]["customer"]
        self.assertIs(customer["additionalProperties"], False)
        self.assertEqual(set(customer["required"]), set(customer["properties"].keys()))
        # "id" was never required inside the customer object — must be nullable.
        self.assertIn("null", customer["properties"]["id"]["type"])

    def test_every_zero_argument_tool_is_still_a_valid_strict_object(self):
        schema = next(s for s in tools.TOOL_SCHEMAS if s["name"] == "order_status_summary")
        self.assertEqual(schema["parameters"]["required"], [])
        self.assertIs(schema["parameters"]["additionalProperties"], False)

    def test_an_optional_array_of_objects_still_strictifies_its_items(self):
        # Regression test: update_draft_order's `lines` is an optional (nullable) array of
        # objects. OpenAI rejected the very first live schema with "'additionalProperties' is
        # required to be supplied and to be false" for exactly this property — _nullable()
        # turned `lines`' type into ["array", "null"] *before* _to_strict() saw it, and the old
        # `schema.get("type") == "array"` check didn't match a list, so the array branch (and
        # therefore the recursion into `items`) never ran.
        schema = next(s for s in tools.TOOL_SCHEMAS if s["name"] == "update_draft_order")
        lines = schema["parameters"]["properties"]["lines"]
        self.assertIn("array", lines["type"])
        self.assertIn("null", lines["type"])
        items = lines["items"]
        self.assertIs(items["additionalProperties"], False)
        self.assertEqual(set(items["required"]), set(items["properties"].keys()))

    def test_a_nullable_enum_property_adds_null_to_both_type_and_enum(self):
        # Regression-shaped test for a bug class, not a bug that's shipped yet: a nullable
        # property with an `enum` needs null added to the enum's own values too, not just the
        # type — `enum` is a flat allow-list independent of `type`, and OpenAI rejects a
        # schema where the model is required to be *able* to send null but null isn't itself an
        # allowed enum value. list_unpaid_orders' `payment_status` is the first property in this
        # codebase that's both optional and has an enum, so it's the one this must hold for.
        schema = next(s for s in tools.TOOL_SCHEMAS if s["name"] == "list_unpaid_orders")
        payment_status = schema["parameters"]["properties"]["payment_status"]
        self.assertIn("null", payment_status["type"])
        self.assertIn(None, payment_status["enum"])
        self.assertIn("unpaid", payment_status["enum"])
        self.assertIn("pending", payment_status["enum"])


class NullArgumentSafetyTests(AssistantTestCase):
    """
    Strict mode means a model that doesn't have a value for an optional argument sends it as
    None, not omitted. Each dispatch function below has a non-None Python default, so each
    needs its own check that an explicit None behaves exactly like the argument being absent.
    """

    def test_list_unpaid_orders_treats_null_min_days_unpaid_as_zero(self):
        with_default, _ = tools._tool_list_unpaid_orders(store=self.store, user=self.user, conversation=None)
        with_null, _ = tools._tool_list_unpaid_orders(
            store=self.store, user=self.user, conversation=None, min_days_unpaid=None
        )
        self.assertEqual(with_null, with_default)

    def test_list_recent_orders_treats_null_limit_as_the_default(self):
        with_default, _ = tools._tool_list_recent_orders(store=self.store, user=self.user, conversation=None)
        with_null, _ = tools._tool_list_recent_orders(
            store=self.store, user=self.user, conversation=None, limit=None
        )
        self.assertEqual(with_null, with_default)

    def test_transition_order_status_treats_null_allow_unpaid_as_false(self):
        order_id = self.confirmed_order()
        output, _ = tools._tool_transition_order_status(
            store=self.store,
            user=self.user,
            conversation=None,
            order_id=order_id,
            fulfilment_status="processing",
            allow_unpaid=None,
        )
        # Unpaid and allow_unpaid=None (≡ False) — the service must still refuse, not crash.
        self.assertIn("error", output)

    def test_create_product_treats_null_optional_fields_as_their_defaults(self):
        output, side_effect = tools._tool_create_product(
            store=self.store,
            user=self.user,
            conversation=None,
            name="Null Test Product",
            sku="NULL-TEST-1",
            price="9.99",
            description=None,
            stock_quantity=None,
            low_stock_threshold=None,
            is_active=None,
        )
        self.assertIsNone(side_effect)
        self.assertNotIn("error", output)
        product = Product.objects.get(sku="NULL-TEST-1")
        self.assertEqual(product.description, "")
        self.assertEqual(product.stock_quantity, 0)
        self.assertEqual(product.low_stock_threshold, 5)
        self.assertTrue(product.is_active)

    def test_add_customer_treats_null_notes_as_empty_not_a_db_error(self):
        output, _ = tools._tool_add_customer(
            store=self.store,
            user=self.user,
            conversation=None,
            name="Null Notes Customer",
            notes=None,
        )
        self.assertNotIn("error", output)

    def test_create_draft_order_treats_null_customer_fields_as_empty(self):
        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"id": None, "name": "Null Field Customer", "email": None, "phone": None, "confirmed_new": None},
            lines=[{"product": self.product.sku, "quantity": 1}],
            delivery_notes=None,
            internal_notes=None,
            source_message=None,
        )
        self.assertIsNone(output.get("error"))
        self.assertEqual(side_effect["kind"], "order_created")
