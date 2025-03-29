from typing import Optional, List
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


class UserProfile(BaseModel):
    """User profile model with field validations"""
    class Meta:
        strict = True
        name = "user_profiles"
        schema = "public"

    # String validations
    username: str = Field(
        required=True,
        min_length=3,
        max_length=20,
        pattern=r'^[a-zA-Z0-9_]+$'  # Alphanumeric and underscore only
    )

    email: str = Field(
        required=True,
        pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'  # Basic email pattern
    )

    password: str = Field(
        required=True,
        min_length=8,
        max_length=100
    )

    # Numeric validations
    age: int = Field(
        required=True,
        ge=18,  # Must be at least 18
        lt=120  # Must be less than 120
    )

    score: float = Field(
        default=0.0,
        ge=0.0,  # Must be non-negative
        le=100.0  # Must not exceed 100
    )

    # Fixed length validation
    verification_code: str = Field(
        default=None,
        nullable=True,
        length=6  # Must be exactly 6 characters
    )

    # Equal to validation
    account_status: int = Field(
        default=1,
        eq=1  # Must be exactly 1 (active status)
    )

    # Not equal to validation
    access_level: int = Field(
        default=0,
        ne=-1  # Must not be -1 (banned)
    )

    # Custom validator function
    def validate_username_not_admin(field, value, annotated_type, val_type):
        if value.lower() == 'admin':
            return False
        return True

    admin_name: str = Field(
        default="",
        validator=validate_username_not_admin
    )


class Product(BaseModel):
    """Product model with comprehensive field validations"""
    class Meta:
        strict = True
        name = "products"
        schema = "inventory"

    # String validations
    sku: str = Field(
        required=True,
        min_length=6,
        max_length=20,
        pattern=r'^[A-Z]{2}-\d{3,}-[A-Z0-9]+$'  # Format: XX-###-XXXX
    )

    name: str = Field(
        required=True,
        min_length=3,
        max_length=100
    )

    description: str = Field(
        default="",
        max_length=1000
    )

    # Numeric validations with parsers
    price: Decimal = Field(
        required=True,
        gt=0,           # Price must be positive
        le=9999.99      # Maximum price
    )

    weight: float = Field(
        default=0.0,
        ge=0.0,         # Weight must be non-negative
        lt=1000.0       # Max weight
    )

    stock: int = Field(
        default=0,
        ge=0            # Stock can't be negative
    )

    # Date validations (with parser)
    created_at: datetime = Field(
        default=datetime.now,
        le=datetime.now()  # Can't be in the future
    )

    release_date: date = Field(
        default=date.today,
        ge=date(2000, 1, 1)  # Products released after 2000
    )

    discontinue_date: Optional[date] = Field(
        default=None,
        nullable=True
    )

    # UUID validation (with parser)
    product_id: UUID = Field(
        required=True,
        primary_key=True
    )

    # Fixed length validation
    barcode: str = Field(
        default=None,
        nullable=True,
        length=13      # EAN-13 barcode
    )

    # Equal to validation
    status: int = Field(
        default=1,
        eq=1           # Must be active (1)
    )

    # Not equal to validation
    category_id: int = Field(
        default=0,
        ne=-1          # Must not be uncategorized (-1)
    )

    # Custom validator function
    def validate_restricted_name(field, value, annotated_type, val_type):
        restricted = ["sample", "test", "dummy", "placeholder"]
        if value.lower() in restricted:
            return False
        return True

    display_name: str = Field(
        default="",
        validator=validate_restricted_name
    )


def test_field_validations():
    # Valid user
    valid_user = UserProfile(
        username="john_doe",
        email="john@example.com",
        password="secure_password",
        age=30,
        score=85.5,
        verification_code="123456",
        admin_name="moderator"
    )
    print("Valid user:", valid_user)

    try:
        # Invalid username (too short)
        UserProfile(
            username="jo",  # Too short
            email="john@example.com",
            password="secure_password",
            age=30
        )
    except ValidationError as e:
        print("\nValidation Error (short username):", e.payload)

    try:
        # Invalid username (invalid characters)
        UserProfile(
            username="john@doe",  # @ not allowed
            email="john@example.com",
            password="secure_password",
            age=30
        )
    except ValidationError as e:
        print("\nValidation Error (invalid username chars):", e.payload)

    try:
        # Invalid age (too young)
        UserProfile(
            username="john_doe",
            email="john@example.com",
            password="secure_password",
            age=16  # Under 18
        )
    except ValidationError as e:
        print("\nValidation Error (underage):", e.payload)

    try:
        # Invalid verification code (wrong length)
        UserProfile(
            username="john_doe",
            email="john@example.com",
            password="secure_password",
            age=30,
            verification_code="12345"  # Should be 6 digits
        )
    except ValidationError as e:
        print("\nValidation Error (wrong code length):", e.payload)

    try:
        # Invalid admin name (can't be 'admin')
        UserProfile(
            username="john_doe",
            email="john@example.com",
            password="secure_password",
            age=30,
            admin_name="admin"  # Not allowed by custom validator
        )
    except ValidationError as e:
        print("\nValidation Error (reserved admin name):", e.payload)


def test_product_validations():
    """Test various field validations with parsing and constraints"""
    try:
        # Valid product
        valid_product = Product(
            sku="AB-12345-XYZ",
            name="Ergonomic Keyboard",
            description="A comfortable keyboard for long typing sessions",
            price="159.99",  # String that will be parsed to Decimal
            weight="2.5",    # String that will be parsed to float
            stock="25",      # String that will be parsed to int
            release_date="2023-01-15",  # String that will be parsed to date
            product_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",  # String that will be parsed to UUID
            barcode="1234567890123",  # Exactly 13 chars
            display_name="Premium Keyboard"
        )
        print("Valid product created:")
        print(f"  SKU: {valid_product.sku}")
        print(f"  Name: {valid_product.name}")
        print(f"  Price: {valid_product.price} (type: {type(valid_product.price).__name__})")
        print(f"  Weight: {valid_product.weight} (type: {type(valid_product.weight).__name__})")
        print(f"  Stock: {valid_product.stock} (type: {type(valid_product.stock).__name__})")
        print(f"  Product ID: {valid_product.product_id} (type: {type(valid_product.product_id).__name__})")
        print(f"  Release Date: {valid_product.release_date} (type: {type(valid_product.release_date).__name__})")
        print(f"  Barcode: {valid_product.barcode}")
        print()

        validation_tests = [
            # Test invalid SKU format
            (
                "Invalid SKU format",
                lambda: Product(
                    sku="invalid",
                    name="Test Product",
                    price="10.99",
                    product_id="f47ac10b-58cc-4372-a567-0e02b2c3d479"
                )
            ),

            # Test negative price
            ("Negative price",
             lambda: Product(
                 sku="AB-12345-XYZ",
                 name="Test Product",
                 price="-10.99",
                 product_id="f47ac10b-58cc-4372-a567-0e02b2c3d479"
             )),

            # Test future created_at date
            ("Future creation date",
             lambda: Product(
                 sku="AB-12345-XYZ",
                 name="Test Product",
                 price="10.99",
                 created_at="2030-01-01",
                 product_id="f47ac10b-58cc-4372-a567-0e02b2c3d479"
             )),

            # Test invalid barcode length
            ("Invalid barcode length",
             lambda: Product(
                 sku="AB-12345-XYZ",
                 name="Test Product",
                 price="10.99",
                 product_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
                 barcode="12345"  # Too short
             )),

            # Test restricted display name
            ("Restricted display name",
             lambda: Product(
                 sku="AB-12345-XYZ",
                 name="Test Product",
                 price="10.99",
                 product_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
                 display_name="test"  # Restricted name
             )),

            # Test invalid status
            ("Invalid status",
             lambda: Product(
                 sku="AB-12345-XYZ",
                 name="Test Product",
                 price="10.99",
                 product_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
                 status=0  # Must be 1
             )),

            # Test invalid release date
            ("Invalid early release date",
             lambda: Product(
                 sku="AB-12345-XYZ",
                 name="Test Product",
                 price="10.99",
                 product_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
                 release_date="1999-12-31"  # Before 2000
             )),
        ]

        for test_name, test_fn in validation_tests:
            print(f"Testing: {test_name}")
            try:
                test_fn()
                print("  ERROR: Validation should have failed but it passed!")
            except ValidationError as e:
                print(f"  Validation failed as expected: {e.payload}")
            except Exception as e:
                print(f"  Unexpected error: {e}")
            print()

    except ValidationError as e:
        print(f"Validation Error: {e.payload}")
    except Exception as e:
        print(f"Unexpected Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_field_validations()
    test_product_validations()
