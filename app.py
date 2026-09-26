import os
import uuid
from functools import wraps
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASE_DIR = os.path.join(BASE_DIR, "database")
UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads",
    "perfumes"
)

os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "perfume-store-secret-key-change-this"
)

database_url = os.getenv("DATABASE_URL")

if database_url:
    database_url = database_url.strip()

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///"
        + os.path.join(DATABASE_DIR, "perfume.db")
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)


# ============================================================
# CONSTANTS
# ============================================================

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
}

ORDER_STATUSES = [
    "Pending",
    "Confirmed",
    "Processing",
    "Out for Delivery",
    "Delivered",
    "Cancelled",
]


# ============================================================
# DATABASE MODELS
# ============================================================

class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<Admin {self.username}>"


class Perfume(db.Model):
    __tablename__ = "perfumes"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    brand = db.Column(
        db.String(100),
        nullable=True
    )

    category = db.Column(
        db.String(100),
        nullable=True
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    price = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    discount_price = db.Column(
        db.Float,
        nullable=True
    )

    stock = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    size = db.Column(
        db.String(50),
        nullable=True
    )

    image = db.Column(
        db.String(255),
        nullable=True
    )

    featured = db.Column(
        db.Boolean,
        default=False
    )

    active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    order_items = db.relationship(
        "OrderItem",
        backref="perfume",
        lazy=True
    )

    @property
    def selling_price(self):
        """
        Returns discount price if one exists,
        otherwise returns normal price.
        """

        if (
            self.discount_price is not None
            and self.discount_price > 0
            and self.discount_price < self.price
        ):
            return self.discount_price

        return self.price

    @property
    def has_discount(self):
        return (
            self.discount_price is not None
            and self.discount_price > 0
            and self.discount_price < self.price
        )

    def __repr__(self):
        return f"<Perfume {self.name}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    customer_name = db.Column(
        db.String(150),
        nullable=False
    )

    phone = db.Column(
        db.String(50),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        nullable=True
    )

    address = db.Column(
        db.Text,
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=True
    )

    state = db.Column(
        db.String(100),
        nullable=True
    )

    delivery_fee = db.Column(
        db.Float,
        default=0
    )

    subtotal = db.Column(
        db.Float,
        default=0
    )

    total = db.Column(
        db.Float,
        default=0
    )

    payment_method = db.Column(
        db.String(50),
        default="Cash on Delivery"
    )

    payment_status = db.Column(
        db.String(50),
        default="Pending"
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    notes = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    items = db.relationship(
        "OrderItem",
        backref="order",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Order {self.order_number}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False
    )

    perfume_id = db.Column(
        db.Integer,
        db.ForeignKey("perfumes.id"),
        nullable=False
    )

    perfume_name = db.Column(
        db.String(150),
        nullable=False
    )

    price = db.Column(
        db.Float,
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    total = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    def __repr__(self):
        return f"<OrderItem {self.perfume_name}>"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def allowed_file(filename):
    """
    Check whether uploaded file has an allowed extension.
    """

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def save_image(file):
    """
    Save uploaded perfume image and return its filename.
    """

    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        return None

    extension = file.filename.rsplit(".", 1)[1].lower()

    filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    filename = secure_filename(filename)

    file.save(
        os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )
    )

    return filename


def delete_image(filename):
    """
    Delete an image from the uploads folder.
    """

    if not filename:
        return

    path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def admin_required(function):
    """
    Protect admin pages.
    """

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):
            flash(
                "Please login as administrator.",
                "warning"
            )

            return redirect(
                url_for("admin_login")
            )

        return function(*args, **kwargs)

    return decorated_function


def get_cart():
    """
    Return the cart stored inside the user's session.

    Example:

    {
        "1": 2,
        "5": 1
    }

    Means:
    Perfume ID 1 = quantity 2
    Perfume ID 5 = quantity 1
    """

    return session.get("cart", {})


def save_cart(cart):
    """
    Save cart back into session.
    """

    session["cart"] = cart
    session.modified = True


def cart_items():
    """
    Get actual perfume objects and quantities
    from the session cart.
    """

    cart = get_cart()

    items = []

    for perfume_id, quantity in cart.items():

        perfume = db.session.get(
            Perfume,
            int(perfume_id)
        )

        if not perfume:
            continue

        if not perfume.active:
            continue

        quantity = int(quantity)

        if quantity <= 0:
            continue

        items.append({
            "perfume": perfume,
            "quantity": quantity,
            "price": perfume.selling_price,
            "total": perfume.selling_price * quantity,
        })

    return items


def cart_subtotal():
    """
    Calculate cart subtotal.
    """

    return sum(
        item["total"]
        for item in cart_items()
    )


def cart_count():
    """
    Calculate total number of products
    inside cart.
    """

    return sum(
        int(quantity)
        for quantity in get_cart().values()
    )


# ============================================================
# TEMPLATE CONTEXT
# ============================================================

@app.context_processor
def inject_global_values():

    return {
        "cart_count": cart_count(),
        "cart_subtotal": cart_subtotal(),
        "current_year": datetime.now().year,
    }


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():

    featured_perfumes = (
        Perfume.query
        .filter_by(
            active=True,
            featured=True
        )
        .order_by(
            Perfume.created_at.desc()
        )
        .limit(8)
        .all()
    )

    if not featured_perfumes:

        featured_perfumes = (
            Perfume.query
            .filter_by(active=True)
            .order_by(
                Perfume.created_at.desc()
            )
            .limit(8)
            .all()
        )

    return render_template(
        "index.html",
        perfumes=featured_perfumes
    )


# ============================================================
# SHOP
# ============================================================

@app.route("/shop")
def shop():

    search = request.args.get(
        "search",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()

    query = Perfume.query.filter_by(
        active=True
    )

    if search:

        search_pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Perfume.name.ilike(
                    search_pattern
                ),
                Perfume.brand.ilike(
                    search_pattern
                ),
                Perfume.category.ilike(
                    search_pattern
                )
            )
        )

    if category:

        query = query.filter(
            Perfume.category == category
        )

    perfumes = (
        query
        .order_by(
            Perfume.created_at.desc()
        )
        .all()
    )

    categories = (
        db.session.query(
            Perfume.category
        )
        .filter(
            Perfume.category.isnot(None),
            Perfume.category != "",
            Perfume.active == True
        )
        .distinct()
        .order_by(
            Perfume.category.asc()
        )
        .all()
    )

    categories = [
        item[0]
        for item in categories
    ]

    return render_template(
        "shop.html",
        perfumes=perfumes,
        categories=categories,
        search=search,
        selected_category=category
    )


# ============================================================
# PRODUCT DETAILS
# ============================================================

@app.route("/product/<int:perfume_id>")
def product(perfume_id):

    perfume = db.get_or_404(
        Perfume,
        perfume_id
    )

    if not perfume.active:

        flash(
            "This perfume is not available.",
            "warning"
        )

        return redirect(
            url_for("shop")
        )

    return render_template(
        "product.html",
        perfume=perfume
    )


# ============================================================
# ADD TO CART
# ============================================================

@app.route(
    "/cart/add/<int:perfume_id>",
    methods=["POST", "GET"]
)
def add_to_cart(perfume_id):

    perfume = db.get_or_404(
        Perfume,
        perfume_id
    )

    if not perfume.active:

        flash(
            "This perfume is currently unavailable.",
            "danger"
        )

        return redirect(
            url_for("shop")
        )

    if perfume.stock <= 0:

        flash(
            "This perfume is out of stock.",
            "danger"
        )

        return redirect(
            request.referrer
            or url_for("shop")
        )

    try:

        quantity = int(
            request.form.get(
                "quantity",
                1
            )
        )

    except ValueError:

        quantity = 1

    if quantity < 1:
        quantity = 1

    cart = get_cart()

    perfume_key = str(
        perfume.id
    )

    current_quantity = int(
        cart.get(
            perfume_key,
            0
        )
    )

    new_quantity = (
        current_quantity
        + quantity
    )

    if new_quantity > perfume.stock:

        new_quantity = perfume.stock

        flash(
            f"Only {perfume.stock} item(s) "
            f"are available.",
            "warning"
        )

    cart[perfume_key] = new_quantity

    save_cart(cart)

    flash(
        f"{perfume.name} added to your cart.",
        "success"
    )

    return redirect(
        request.referrer
        or url_for("shop")
    )


# ============================================================
# CART
# ============================================================

@app.route("/cart")
def cart():

    items = cart_items()

    return render_template(
        "cart.html",
        items=items,
        subtotal=cart_subtotal()
    )


# ============================================================
# UPDATE CART
# ============================================================

@app.route(
    "/cart/update",
    methods=["POST"]
)
def update_cart():

    cart = get_cart()

    for perfume_id in list(cart.keys()):

        field_name = (
            f"quantity_{perfume_id}"
        )

        if field_name not in request.form:
            continue

        try:

            quantity = int(
                request.form[field_name]
            )

        except ValueError:

            quantity = 1

        perfume = db.session.get(
            Perfume,
            int(perfume_id)
        )

        if not perfume:
            cart.pop(perfume_id, None)
            continue

        if quantity <= 0:

            cart.pop(
                perfume_id,
                None
            )

        else:

            if quantity > perfume.stock:

                quantity = perfume.stock

                flash(
                    f"{perfume.name}: "
                    f"only {perfume.stock} available.",
                    "warning"
                )

            cart[perfume_id] = quantity

    save_cart(cart)

    flash(
        "Cart updated.",
        "success"
    )

    return redirect(
        url_for("cart")
    )


# ============================================================
# REMOVE FROM CART
# ============================================================

@app.route(
    "/cart/remove/<int:perfume_id>",
    methods=["POST", "GET"]
)
def remove_from_cart(perfume_id):

    cart = get_cart()

    cart.pop(
        str(perfume_id),
        None
    )

    save_cart(cart)

    flash(
        "Item removed from cart.",
        "success"
    )

    return redirect(
        url_for("cart")
    )


# ============================================================
# CLEAR CART
# ============================================================

@app.route(
    "/cart/clear",
    methods=["POST", "GET"]
)
def clear_cart():

    session["cart"] = {}

    flash(
        "Cart cleared.",
        "success"
    )

    return redirect(
        url_for("cart")
    )


# ============================================================
# CHECKOUT
# ============================================================

@app.route(
    "/checkout",
    methods=["GET", "POST"]
)
def checkout():

    items = cart_items()

    if not items:

        flash(
            "Your cart is empty.",
            "warning"
        )

        return redirect(
            url_for("shop")
        )

    subtotal = cart_subtotal()

    if request.method == "POST":

        customer_name = request.form.get(
            "customer_name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        city = request.form.get(
            "city",
            ""
        ).strip()

        state = request.form.get(
            "state",
            ""
        ).strip()

        payment_method = request.form.get(
            "payment_method",
            "Cash on Delivery"
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        # ----------------------------------------
        # VALIDATION
        # ----------------------------------------

        if not customer_name:

            flash(
                "Please enter your name.",
                "danger"
            )

            return render_template(
                "checkout.html",
                items=items,
                subtotal=subtotal
            )

        if not phone:

            flash(
                "Please enter your phone number.",
                "danger"
            )

            return render_template(
                "checkout.html",
                items=items,
                subtotal=subtotal
            )

        if not address:

            flash(
                "Please enter your delivery address.",
                "danger"
            )

            return render_template(
                "checkout.html",
                items=items,
                subtotal=subtotal
            )

        # ----------------------------------------
        # CHECK STOCK AGAIN
        # ----------------------------------------

        for item in items:

            perfume = item["perfume"]

            if item["quantity"] > perfume.stock:

                flash(
                    f"{perfume.name} does not have "
                    f"enough stock.",
                    "danger"
                )

                return redirect(
                    url_for("cart")
                )

        # ----------------------------------------
        # DELIVERY FEE
        # ----------------------------------------

        try:

            delivery_fee = float(
                request.form.get(
                    "delivery_fee",
                    0
                )
            )

        except ValueError:

            delivery_fee = 0

        if delivery_fee < 0:
            delivery_fee = 0

        total = (
            subtotal
            + delivery_fee
        )

        # ----------------------------------------
        # GENERATE ORDER NUMBER
        # ----------------------------------------

        order_number = (
            "PF-"
            + datetime.now().strftime(
                "%Y%m%d"
            )
            + "-"
            + uuid.uuid4().hex[:6].upper()
        )

        # ----------------------------------------
        # CREATE ORDER
        # ----------------------------------------

        order = Order(
            order_number=order_number,
            customer_name=customer_name,
            phone=phone,
            email=email,
            address=address,
            city=city,
            state=state,
            delivery_fee=delivery_fee,
            subtotal=subtotal,
            total=total,
            payment_method=payment_method,
            payment_status="Pending",
            status="Pending",
            notes=notes
        )

        db.session.add(order)

        # ----------------------------------------
        # CREATE ORDER ITEMS
        # ----------------------------------------

        for item in items:

            perfume = item["perfume"]
            quantity = item["quantity"]
            price = item["price"]

            order_item = OrderItem(
                order=order,
                perfume_id=perfume.id,
                perfume_name=perfume.name,
                price=price,
                quantity=quantity,
                total=price * quantity
            )

            db.session.add(
                order_item
            )

            # Reduce stock

            perfume.stock -= quantity

        # ----------------------------------------
        # SAVE EVERYTHING
        # ----------------------------------------

        try:

            db.session.commit()

        except Exception:

            db.session.rollback()

            flash(
                "There was a problem creating "
                "your order. Please try again.",
                "danger"
            )

            return redirect(
                url_for("checkout")
            )

        # Empty cart

        session["cart"] = {}

        return redirect(
            url_for(
                "order_success",
                order_number=order.order_number
            )
        )

    return render_template(
        "checkout.html",
        items=items,
        subtotal=subtotal
    )


# ============================================================
# ORDER SUCCESS
# ============================================================

@app.route(
    "/order-success/<order_number>"
)
def order_success(order_number):

    order = Order.query.filter_by(
        order_number=order_number
    ).first_or_404()

    return render_template(
        "order_success.html",
        order=order
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if session.get("admin_logged_in"):

        return redirect(
            url_for("admin_dashboard")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        admin = Admin.query.filter_by(
            username=username
        ).first()

        if (
            admin
            and admin.password == password
        ):

            session["admin_logged_in"] = True
            session["admin_id"] = admin.id
            session["admin_username"] = (
                admin.username
            )

            flash(
                "Welcome back.",
                "success"
            )

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Invalid username or password.",
            "danger"
        )

    return render_template(
        "admin/login.html"
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    session.pop(
        "admin_id",
        None
    )

    session.pop(
        "admin_username",
        None
    )

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("admin_login")
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    perfume_count = Perfume.query.count()

    active_perfume_count = (
        Perfume.query
        .filter_by(active=True)
        .count()
    )

    order_count = Order.query.count()

    pending_orders = (
        Order.query
        .filter_by(status="Pending")
        .count()
    )

    delivered_orders = (
        Order.query
        .filter_by(status="Delivered")
        .count()
    )

    total_sales = (
        db.session.query(
            db.func.sum(Order.total)
        )
        .filter(
            Order.status != "Cancelled"
        )
        .scalar()
        or 0
    )

    recent_orders = (
        Order.query
        .order_by(
            Order.created_at.desc()
        )
        .limit(10)
        .all()
    )

    low_stock = (
        Perfume.query
        .filter(
            Perfume.stock <= 5,
            Perfume.active == True
        )
        .order_by(
            Perfume.stock.asc()
        )
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        perfume_count=perfume_count,
        active_perfume_count=active_perfume_count,
        order_count=order_count,
        pending_orders=pending_orders,
        delivered_orders=delivered_orders,
        total_sales=total_sales,
        recent_orders=recent_orders,
        low_stock=low_stock
    )


# ============================================================
# ADMIN PRODUCTS
# ============================================================

@app.route("/admin/products")
@admin_required
def admin_products():

    perfumes = (
        Perfume.query
        .order_by(
            Perfume.created_at.desc()
        )
        .all()
    )

    return render_template(
        "admin/products.html",
        perfumes=perfumes
    )


# ============================================================
# ADMIN ADD PRODUCT
# ============================================================

@app.route(
    "/admin/products/add",
    methods=["GET", "POST"]
)
@admin_required
def admin_add_product():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        brand = request.form.get(
            "brand",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        size = request.form.get(
            "size",
            ""
        ).strip()

        try:

            price = float(
                request.form.get(
                    "price",
                    0
                )
            )

        except ValueError:

            price = 0

        discount_price_raw = request.form.get(
            "discount_price",
            ""
        ).strip()

        if discount_price_raw:

            try:

                discount_price = float(
                    discount_price_raw
                )

            except ValueError:

                discount_price = None

        else:

            discount_price = None

        try:

            stock = int(
                request.form.get(
                    "stock",
                    0
                )
            )

        except ValueError:

            stock = 0

        featured = (
            request.form.get(
                "featured"
            ) == "on"
        )

        active = (
            request.form.get(
                "active"
            ) == "on"
        )

        if not name:

            flash(
                "Perfume name is required.",
                "danger"
            )

            return render_template(
                "admin/add_product.html"
            )

        if price < 0:

            flash(
                "Price cannot be negative.",
                "danger"
            )

            return render_template(
                "admin/add_product.html"
            )

        if stock < 0:

            stock = 0

        image_file = request.files.get(
            "image"
        )

        image = save_image(
            image_file
        )

        perfume = Perfume(
            name=name,
            brand=brand,
            category=category,
            description=description,
            price=price,
            discount_price=discount_price,
            stock=stock,
            size=size,
            image=image,
            featured=featured,
            active=active
        )

        db.session.add(
            perfume
        )

        db.session.commit()

        flash(
            f"{name} added successfully.",
            "success"
        )

        return redirect(
            url_for("admin_products")
        )

    return render_template(
        "admin/add_product.html"
    )


# ============================================================
# ADMIN EDIT PRODUCT
# ============================================================

@app.route(
    "/admin/products/edit/<int:perfume_id>",
    methods=["GET", "POST"]
)
@admin_required
def admin_edit_product(perfume_id):

    perfume = db.get_or_404(
        Perfume,
        perfume_id
    )

    if request.method == "POST":

        perfume.name = request.form.get(
            "name",
            ""
        ).strip()

        perfume.brand = request.form.get(
            "brand",
            ""
        ).strip()

        perfume.category = request.form.get(
            "category",
            ""
        ).strip()

        perfume.description = request.form.get(
            "description",
            ""
        ).strip()

        perfume.size = request.form.get(
            "size",
            ""
        ).strip()

        try:

            perfume.price = float(
                request.form.get(
                    "price",
                    0
                )
            )

        except ValueError:

            perfume.price = 0

        discount_price_raw = request.form.get(
            "discount_price",
            ""
        ).strip()

        if discount_price_raw:

            try:

                perfume.discount_price = float(
                    discount_price_raw
                )

            except ValueError:

                perfume.discount_price = None

        else:

            perfume.discount_price = None

        try:

            perfume.stock = int(
                request.form.get(
                    "stock",
                    0
                )
            )

        except ValueError:

            perfume.stock = 0

        perfume.featured = (
            request.form.get(
                "featured"
            ) == "on"
        )

        perfume.active = (
            request.form.get(
                "active"
            ) == "on"
        )

        image_file = request.files.get(
            "image"
        )

        if image_file and image_file.filename:

            new_image = save_image(
                image_file
            )

            if new_image:

                delete_image(
                    perfume.image
                )

                perfume.image = new_image

        db.session.commit()

        flash(
            f"{perfume.name} updated successfully.",
            "success"
        )

        return redirect(
            url_for("admin_products")
        )

    return render_template(
        "admin/edit_product.html",
        perfume=perfume
    )


# ============================================================
# ADMIN DELETE PRODUCT
# ============================================================

@app.route(
    "/admin/products/delete/<int:perfume_id>",
    methods=["POST", "GET"]
)
@admin_required
def admin_delete_product(perfume_id):

    perfume = db.get_or_404(
        Perfume,
        perfume_id
    )

    # Do not delete a product that already
    # appears in an order.
    #
    # Instead, deactivate it.

    existing_orders = (
        OrderItem.query
        .filter_by(
            perfume_id=perfume.id
        )
        .count()
    )

    if existing_orders > 0:

        perfume.active = False

        db.session.commit()

        flash(
            "This perfume has previous orders, "
            "so it was deactivated instead of deleted.",
            "warning"
        )

        return redirect(
            url_for("admin_products")
        )

    delete_image(
        perfume.image
    )

    db.session.delete(
        perfume
    )

    db.session.commit()

    flash(
        "Perfume deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin_products")
    )


# ============================================================
# ADMIN ORDERS
# ============================================================

@app.route("/admin/orders")
@admin_required
def admin_orders():

    status = request.args.get(
        "status",
        ""
    ).strip()

    query = Order.query

    if status:

        query = query.filter_by(
            status=status
        )

    orders = (
        query
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )

    return render_template(
        "admin/orders.html",
        orders=orders,
        statuses=ORDER_STATUSES,
        selected_status=status
    )


# ============================================================
# ADMIN ORDER DETAILS
# ============================================================

@app.route(
    "/admin/orders/<int:order_id>"
)
@admin_required
def admin_order_details(order_id):

    order = db.get_or_404(
        Order,
        order_id
    )

    return render_template(
        "admin/order_details.html",
        order=order,
        statuses=ORDER_STATUSES
    )


# ============================================================
# ADMIN UPDATE ORDER STATUS
# ============================================================

@app.route(
    "/admin/orders/<int:order_id>/status",
    methods=["POST"]
)
@admin_required
def admin_update_order_status(order_id):

    order = db.get_or_404(
        Order,
        order_id
    )

    new_status = request.form.get(
        "status",
        ""
    ).strip()

    if new_status not in ORDER_STATUSES:

        flash(
            "Invalid order status.",
            "danger"
        )

        return redirect(
            url_for(
                "admin_orders"
            )
        )

    # ----------------------------------------
    # HANDLE CANCELLATION STOCK RETURN
    # ----------------------------------------

    if (
        new_status == "Cancelled"
        and order.status != "Cancelled"
    ):

        for item in order.items:

            perfume = db.session.get(
                Perfume,
                item.perfume_id
            )

            if perfume:

                perfume.stock += (
                    item.quantity
                )

    # ----------------------------------------
    # PREVENT DOUBLE STOCK RETURN
    # ----------------------------------------

    if (
        order.status == "Cancelled"
        and new_status != "Cancelled"
    ):

        for item in order.items:

            perfume = db.session.get(
                Perfume,
                item.perfume_id
            )

            if perfume:

                if perfume.stock >= item.quantity:

                    perfume.stock -= (
                        item.quantity
                    )

                else:

                    flash(
                        f"Not enough stock to "
                        f"restore order "
                        f"{order.order_number}.",
                        "warning"
                    )

    order.status = new_status

    db.session.commit()

    flash(
        f"Order {order.order_number} "
        f"updated to {new_status}.",
        "success"
    )

    return redirect(
        url_for(
            "admin_orders"
        )
    )


# ============================================================
# CREATE DATABASE + DEFAULT ADMIN
# ============================================================

def initialize_database():

    with app.app_context():

        db.create_all()

        # ----------------------------------------
        # CREATE DEFAULT ADMIN
        # ----------------------------------------

        admin = Admin.query.filter_by(
            username="admin"
        ).first()

        if not admin:

            admin = Admin(
                username="admin",
                password="Manchi001"
            )

            db.session.add(
                admin
            )

            db.session.commit()

            print(
                "========================================"
            )
            print(
                " DEFAULT ADMIN CREATED"
            )
            print(
                " Username: admin"
            )
            print(
                " Password: Manchi001"
            )
            print(
                "========================================"
            )


with app.app_context():
    initialize_database()


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "base.html",
        error_message="Page not found."
    ), 404


@app.errorhandler(500)
def internal_server_error(error):

    db.session.rollback()

    return render_template(
        "base.html",
        error_message="Something went wrong."
    ), 500


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    initialize_database()

    print("")
    print("========================================")
    print("       PERFUME STORE")
    print("========================================")
    print("")
    print("Customer website:")
    print("http://127.0.0.1:5000/")
    print("")
    print("Admin login:")
    print("http://127.0.0.1:5000/admin/login")
    print("")
    print("Default admin:")
    print("Username: admin")
    print("Password: admin123")
    print("")
    print("========================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
