import os
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Expense, Category


app = Flask(__name__)
# Set SECRET_KEY in your environment for anything beyond local development.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-me')
db_url = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------- Helpers ----------

def parse_expense_form(form):
    """Validate expense form data. Raises ValueError with a user-friendly message."""
    title = form.get('title', '').strip()
    if not title:
        raise ValueError('Title is required.')

    try:
        amount = float(form.get('amount', ''))
    except ValueError:
        raise ValueError('Amount must be a number.')
    if amount <= 0:
        raise ValueError('Amount must be greater than zero.')

    date = form.get('date', '')
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise ValueError('Please enter a valid date.')

    raw_cat = form.get('category_id', '')
    category_id = None
    if raw_cat:
        try:
            category_id = int(raw_cat)
        except ValueError:
            raise ValueError('Invalid category.')
        if not db.session.get(Category, category_id):
            raise ValueError('Invalid category.')

    return title, amount, date, category_id


# ---------- Auth ----------

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        raw_password = request.form.get('password', '')

        if not username or not raw_password:
            flash('Username and password are required.', 'error')
        elif len(raw_password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
        else:
            new_user = User(username=username,
                            password=generate_password_hash(raw_password))
            db.session.add(new_user)
            db.session.commit()

            flash('Registration Successful. Please login!', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form.get('username', '').strip()
        ).first()

        if user and check_password_hash(user.password, request.form.get('password', '')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password!', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---------- Dashboard ----------

@app.route('/dashboard')
@login_required
def dashboard():
    expenses = (Expense.query
                .filter_by(user_id=current_user.id)
                .order_by(Expense.date.desc())
                .all())
    category_totals = {}

    for exp in expenses:
        cat_name = exp.category.name if exp.category else 'Uncategorized'
        # BUG FIX: was category_totals['cat_name'] (a literal string key),
        # which lumped every expense into one bogus category.
        category_totals[cat_name] = category_totals.get(cat_name, 0) + exp.amount

    suggestions = []
    if category_totals:
        max_cat = max(category_totals, key=category_totals.get)
        max_amt = category_totals[max_cat]

        if max_amt > 3000:
            suggestions.append(f"You spent ${max_amt:.2f} on {max_cat}. Consider reducing it.")
        else:
            suggestions.append('Your spending is within healthy limits.')

    return render_template(
        'dashboard.html',
        username=current_user.username,
        expenses=expenses,
        categories=list(category_totals.keys()),
        totals=list(category_totals.values()),
        suggestions=suggestions
    )


# ---------- Expenses ----------

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    categories = Category.query.all()

    if request.method == 'POST':
        try:
            title, amount, date, category_id = parse_expense_form(request.form)
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('add_expenses.html', categories=categories)

        new_expense = Expense(
            title=title,
            amount=amount,
            date=date,
            user_id=current_user.id,
            category_id=category_id
        )
        db.session.add(new_expense)
        db.session.commit()
        flash('Expense added!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_expenses.html', categories=categories)


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    expense = db.get_or_404(Expense, id)
    categories = Category.query.all()

    if expense.user_id != current_user.id:
        flash('Unauthorized access!', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            title, amount, date, category_id = parse_expense_form(request.form)
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('edit_expenses.html', expense=expense, categories=categories)

        expense.title = title
        expense.amount = amount
        expense.date = date
        expense.category_id = category_id

        db.session.commit()
        flash('Expense updated!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_expenses.html', expense=expense, categories=categories)


# Deleting via GET lets any link/image tag delete data (CSRF). Use POST and a
# <form method="post"> button in the template instead of a plain link.
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    expense = db.get_or_404(Expense, id)
    if expense.user_id != current_user.id:
        flash('Unauthorized access!', 'error')
        return redirect(url_for('dashboard'))

    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted!', 'success')
    return redirect(url_for('dashboard'))


# ---------- Categories CRUD ----------

@app.route('/categories')
@login_required
def list_categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)


@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Category name is required.', 'error')
        elif Category.query.filter_by(name=name).first():
            flash('Category already exists!', 'error')
        else:
            db.session.add(Category(name=name, description=description))
            db.session.commit()
            flash('Category added!', 'success')
            return redirect(url_for('list_categories'))
    return render_template('add_category.html')


@app.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = db.get_or_404(Category, id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Category name is required.', 'error')
        else:
            # BUG FIX: renaming to an existing name used to crash with an
            # IntegrityError (unique constraint).
            clash = Category.query.filter(Category.name == name, Category.id != id).first()
            if clash:
                flash('Another category already uses that name!', 'error')
            else:
                category.name = name
                category.description = description
                db.session.commit()
                flash('Category updated!', 'success')
                return redirect(url_for('list_categories'))
    return render_template('edit_category.html', category=category)


@app.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    category = db.get_or_404(Category, id)

    # Categories are shared by all users, so don't let one user orphan
    # everybody's expenses.
    if category.expenses:
        flash('Cannot delete a category that still has expenses.', 'error')
        return redirect(url_for('list_categories'))

    db.session.delete(category)
    db.session.commit()
    flash('Category deleted!', 'success')
    return redirect(url_for('list_categories'))


# Create tables on import so it also works under gunicorn.
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '1') == '1')
