from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User
from forms import AdminUserForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(func):
    # دکوراتور ساده برای محدود کردن دسترسی به ادمین‌ها
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('auth_login'))
        return func(*args, **kwargs)
    return wrapper

@admin_bp.route('/users')
@login_required
@admin_required
def users_list():
    users = User.query.order_by(User.joined_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def users_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminUserForm(obj=user)
    if request.method == 'POST' and form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        db.session.commit()
        flash('User updated', 'info')
        return redirect(url_for('admin.users_list'))
    return render_template('admin/user_edit.html', form=form, user=user)

@admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def users_deactivate(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    flash('User deactivated', 'info')
    return redirect(url_for('admin.users_list'))
