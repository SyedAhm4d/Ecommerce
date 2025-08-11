from flask import Flask, render_template, request, redirect, flash, url_for, abort
import os
from flask_sqlalchemy import SQLAlchemy
from create_db import Base, User, Product, Category, CartItem, OrderItem, Address,Order  # Base comes from DeclarativeBase in your models.py
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, TextAreaField, SubmitField, SelectField,BooleanField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from flask_bootstrap import Bootstrap5
from decimal import Decimal
from sqlalchemy import or_,not_
from sqlalchemy.orm import aliased

class AddressForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired()])
    street = StringField("Street Address", validators=[DataRequired()])
    city = StringField("City", validators=[DataRequired()])
    zip_code = StringField("ZIP Code", validators=[DataRequired()])
    country = StringField("Country", validators=[DataRequired()])
    phone = IntegerField("Phone Number", validators=[DataRequired()])
    submit = SubmitField("Save Address")

class CheckoutForm(FlaskForm):
    address_id = SelectField("Select Address", coerce=int, validators=[DataRequired()])

    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("cod", "Cash on Delivery"),
            ("card", "Credit Card"),
            ("paypal", "PayPal")
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField("Place Order")

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    parent_id = SelectField('Parent Category', coerce=int, choices=[], validate_choice=False)
    submit = SubmitField('Add Category')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = DecimalField('Price ($)', validators=[DataRequired(), NumberRange(min=0)])
    discount = IntegerField('Discount (%)', validators=[NumberRange(min=0, max=100)])
    stock_quantity = IntegerField('Stock Quantity', validators=[DataRequired(), NumberRange(min=0)])
    image_url = StringField('Image URL', validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Product')


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('secret_key')
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"# Redirect if not logged in
login_manager.login_message_category = "danger"
login_manager.login_message = "Please login to access this page."
Bootstrap5(app)

@app.context_processor
def inject_categories():
    categories = db.session.execute(db.select(Category)).scalars().all()
    return dict(nav_categories=categories)

# Required user loader
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ✅ Use env var or fallback to SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///e-commerce.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ Initialize SQLAlchemy with custom base
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# ✅ Create tables with app context
with app.app_context():
    db.create_all()


@app.route('/profile')
@login_required
def home():
    return render_template('home.html', user=current_user)

@app.route('/')
def products():
    product = db.session.execute(db.select(Product)).scalars().all()
    admin=0
    if current_user.is_authenticated and current_user.is_admin:
        admin=1

    return render_template('index.html', items=product,user_is_admin=admin)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                flash(f"{user.name} Logged in successfully.", "success")
                return redirect(url_for('products'))
            else:
                flash("Email or Password is Invalid.", "danger")
        else:
            flash("Email is not registered.", "danger")

    return render_template("login.html")

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been Logged out', 'warning')
    return redirect(url_for('products'))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        fname = request.form["first_name"]
        lname = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm"]

        # Validation
        if not fname or not lname or not email or not password or not confirm:
            flash("All fields are required.", "warning")
            return redirect(url_for("signup"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("signup"))

        # Check if user already exists
        existing_user = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if existing_user:
            flash("Email is already registered.", "danger")
            return redirect(url_for("signup"))

        # Hash and save user
        hashed_pw = generate_password_hash(password)
        new_user = User(
            name=fname + ' ' + lname,
            email=email,
            password=hashed_pw,
            is_admin=1 if email == 'admin@gmail.com' else 0,
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    if not current_user.is_admin:
        abort(403)

    form = ProductForm()
    # Dynamically load categories
    form.category_id.choices = [(cat.id, cat.name) for cat in db.session.execute(db.select(Category)).scalars()]

    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            discount=form.discount.data,
            stock_quantity=form.stock_quantity.data,
            image_url=form.image_url.data,
            category_id=form.category_id.data
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully!", "success")
        return redirect(url_for('home'))

    return render_template("add_product.html", form=form)

@app.route("/add-category", methods=["GET", "POST"])
@login_required
def add_category():
    if not current_user.is_admin:
        abort(403)

    form = CategoryForm()

    # Populate parent category choices
    categories = db.session.execute(db.select(Category)).scalars().all()
    form.parent_id.choices = [(0, "No Parent")] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        new_category = Category(name=form.name.data, parent_id=parent_id)
        db.session.add(new_category)
        db.session.commit()
        flash("Category added successfully!", "success")
        return redirect(url_for('add_category'))

    return render_template("add_category.html", form=form)


@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    quantity = request.form.get('quantity', type=int)
    product = db.session.get(Product, product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("products"))

    cart_item = db.session.execute(
        db.select(CartItem).filter_by(user_id=current_user.id, product_id=product_id)
    ).scalar_one_or_none()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)

    db.session.commit()
    flash(f"{product.name} added to cart!", "success")
    return redirect(url_for("view_cart"))


@app.route("/remove-from-cart/<int:cart_item>")
@login_required
def remove_from_cart(cart_item):
    item = db.get_or_404(CartItem, cart_item)
    db.session.delete(item)
    db.session.commit()
    flash(f"Item removed from cart!", "success")
    return redirect(url_for("view_cart"))


@app.route("/cart")
@login_required
def view_cart():
    cart_items = db.session.execute(
        db.select(CartItem).filter_by(user_id=current_user.id)
    ).scalars().all()
    products = []
    for items in cart_items:
        product_id = items.product_id
        product = db.session.execute(
            db.select(Product).filter_by(id=product_id)
        ).scalar()
        if product is None:
            db.session.delete(items)
            db.session.commit()
            continue
        else:
            products.append(product)

    total = 0
    for item in cart_items:
        price = item.product.price
        quantity = item.quantity
        discount = item.product.discount or 0

        subtotal = price * quantity
        subtotal = Decimal(subtotal)
        discount = Decimal(discount)  # instead of float 10.0
        discount_amount = subtotal * (discount / Decimal('100'))
        final_price = subtotal - discount_amount

        total += final_price
    return render_template("cart.html", product_ids=products, cart_items=cart_items, total=total)

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    form = CheckoutForm()

    # Get saved addresses
    saved_addresses = db.session.execute(
        db.select(Address).filter_by(user_id=current_user.id)
    ).scalars().all()

    if not saved_addresses:
        flash("Please add an address before checking out.",'warning')
        return redirect(url_for("add_address"))

    form.address_id.choices = [
        (a.id, f"{a.full_name},{a.phone}    {a.street}, {a.city}, {a.country}") for a in saved_addresses
    ]

    # Get cart items
    cart_items = db.session.execute(
        db.select(CartItem).filter_by(user_id=current_user.id)
    ).scalars().all()

    if not cart_items:
        flash("Your cart is empty.",'warning')
        return redirect(url_for("view_cart"))

    total = sum(
        Decimal(item.product.price * item.quantity) *
        (1 - (Decimal(item.product.discount or 0) / 100))
        for item in cart_items
    )

    if form.validate_on_submit():
        order = Order(
            user_id=current_user.id,
            status="pending",
            total_amount=total,
            address_id=form.address_id.data,
            payment_method=form.payment_method.data
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            price=item.product.price * (Decimal('1.0') - Decimal(item.product.discount) / Decimal('100'))
            if item.product.stock_quantity-item.quantity>=0:
                db.session.add(OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price_each=price
                ))
                item.product.stock_quantity-=item.quantity
                db.session.delete(item)

        db.session.commit()
        flash("Order placed successfully!", "success")
        return redirect(url_for("order_summary", order_id=order.id))

    return render_template("checkout.html", form=form, total=total, addresses=saved_addresses)

@app.route("/order_summary/<int:order_id>")
@login_required
def order_summary(order_id):
    order = db.session.get(Order, order_id)

    if not order or order.user_id != current_user.id:
        flash("Order not found or access denied.", "danger")
        return redirect(url_for("home"))

    return render_template("order_summary.html", order=order)

@app.route("/add_address", methods=["GET", "POST"])
@login_required
def add_address():
    form = AddressForm()
    if form.validate_on_submit():
        address = Address(
            user_id=current_user.id,
            full_name=form.full_name.data,
            street=form.street.data,
            city=form.city.data,
            zip_code=form.zip_code.data,
            country=form.country.data,
            phone=form.phone.data
        )
        db.session.add(address)
        db.session.commit()
        flash("Address saved successfully", "success")
        return redirect(url_for("home"))

    return render_template("add_address.html", form=form)

@app.route("/my_orders")
@login_required
def my_orders():
    orders = (
        db.session.query(Order)
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    all_orders = (
        db.session.query(Order)
        .join(Order.user)
        .filter(not_(User.is_admin))
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("my_orders.html", orders=orders,not_admin=all_orders)

@app.route('/category/<int:category_id>')
def category_products(category_id):
    category = db.get_or_404(Category, category_id)
    CategoryAlias = aliased(Category)

    products = db.session.execute(
        db.select(Product).join(CategoryAlias, Product.category).filter(
            or_(
                Product.category_id == category_id,
                CategoryAlias.parent_id == category_id
            )
        )
    ).scalars().all()

    return render_template("index.html", category=category, items=products)

@app.route('/update_quantity/<id>/<action>')
def update_quantity(id,action):
    cart_item=db.get_or_404(CartItem,id)
    if action=='add':
        cart_item.quantity+=1
    else:
        if cart_item.quantity-1 >=0:
            cart_item.quantity-=1
    db.session.commit()
    return redirect(url_for('view_cart'))

@app.route("/cancel_order/<order_id>")
@login_required
def cancel_order(order_id):
    order=db.get_or_404(Order,order_id)
    order.status='Cancelled'
    db.session.commit()

    return redirect(url_for('my_orders'))

@app.route("/delete_address/<id>")
@login_required
def delete_address(id):
    address=db.get_or_404(Address,id)
    db.session.delete(address)
    db.session.commit()

    return redirect(url_for('home'))

@app.route('/remove_product/<id>')
@login_required
def remove_product(id):
    if current_user.is_admin:
        product=db.get_or_404(Product,id)
        db.session.delete(product)
        db.session.commit()

        return redirect(url_for('products'))

@app.route('/update_product/<int:id>', methods=['GET', 'POST'])
@login_required
def update_product(id):
    if current_user.is_admin:
        product = db.session.get(Product, id)
        if not product:
            abort(404)

        form = ProductForm(obj=product)  # ← pre-populate fields

        form.category_id.choices = [(cat.id, cat.name) for cat in db.session.execute(db.select(Category)).scalars()]

        if form.validate_on_submit():
            form.populate_obj(product)   # ← update product from form data
            db.session.commit()
            flash('Product updated successfully.', 'success')
            return redirect(url_for('products'))

        return render_template('update_product.html', form=form, product=product)

@app.route('/update_order/<int:order_id>',methods=['GET','POST'])
@login_required
def update_order(order_id):
    order=db.get_or_404(Order,order_id)
    if order.status.upper()=='PENDING':
        order.status='Paid'
    elif order.status.upper()=='PAID':
        order.status='Delivered'
    db.session.commit()
    return redirect(url_for('my_orders'))

if __name__ == '__main__':
    app.run(debug=True)