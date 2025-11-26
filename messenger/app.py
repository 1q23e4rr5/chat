import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit
from models import db, User, Room, Message, DirectMessage
from forms import RegisterForm, LoginForm, AddFriendForm
from utils import bcrypt, hash_password, check_password
from sqlalchemy import or_, and_
from datetime import datetime
import json

socketio = SocketIO()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # تنظیمات
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'messenger.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ایجاد پوشه instance
    os.makedirs(app.instance_path, exist_ok=True)

    # مقداردهی اولیه افزونه‌ها
    db.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Flask-Login
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth_login'
    login_manager.login_message = 'لطفاً برای دسترسی به این صفحه وارد شوید'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ایجاد دیتابیس و داده‌های اولیه
    with app.app_context():
        db.create_all()
        if Room.query.count() == 0:
            rooms = [
                Room(slug='general', title='💬 اتاق عمومی'),
                Room(slug='random', title='🎮 اتاق متفرقه'),
                Room(slug='help', title='❓ اتاق کمک')
            ]
            for room in rooms:
                db.session.add(room)
            db.session.commit()
        
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=hash_password('admin123'),
                code=User.generate_code(),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()

    # Routes
    @app.route('/')
    def index():
        """صفحه اصلی"""
        if current_user.is_authenticated:
            return redirect(url_for('chat_dashboard'))
        return render_template('index.html')

    @app.route('/register', methods=['GET', 'POST'])
    def auth_register():
        """ثبت‌نام کاربر جدید"""
        if current_user.is_authenticated:
            return redirect(url_for('chat_dashboard'))
        
        form = RegisterForm()
        if form.validate_on_submit():
            # بررسی وجود کاربر با همین نام کاربری یا ایمیل
            existing_user = User.query.filter(
                (User.username == form.username.data) | 
                (User.email == form.email.data)
            ).first()
            
            if existing_user:
                if existing_user.username == form.username.data:
                    flash('این نام کاربری قبلاً ثبت شده است', 'error')
                else:
                    flash('این ایمیل قبلاً ثبت شده است', 'error')
            else:
                # ایجاد کاربر جدید
                user = User(
                    username=form.username.data.strip(),
                    email=form.email.data.strip(),
                    password_hash=hash_password(form.password.data),
                    code=User.generate_code()
                )
                db.session.add(user)
                db.session.commit()
                
                flash(f'🎉 حساب شما با موفقیت ایجاد شد! کد ۷ رقمی شما: <strong>{user.code}</strong>', 'success')
                login_user(user)
                return redirect(url_for('chat_dashboard'))
        
        return render_template('auth/register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def auth_login():
        """ورود کاربر"""
        if current_user.is_authenticated:
            return redirect(url_for('chat_dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            ident = form.code_or_username.data.strip()
            user = User.query.filter(
                (User.code == ident) | (User.username == ident)
            ).first()
            
            if user and user.is_active and check_password(user.password_hash, form.password.data):
                login_user(user)
                flash(f'👋 خوش آمدید {user.username}!', 'success')
                return redirect(url_for('chat_dashboard'))
            else:
                flash('❌ نام کاربری/کد یا رمز عبور اشتباه است', 'error')
        
        return render_template('auth/login.html', form=form)

    @app.route('/logout')
    @login_required
    def auth_logout():
        """خروج کاربر"""
        logout_user()
        flash('✅ با موفقیت از سیستم خارج شدید', 'info')
        return redirect(url_for('index'))

    @app.route('/dashboard')
    @login_required
    def chat_dashboard():
        """داشبورد اصلی کاربر"""
        # پیدا کردن تمام کاربرانی که با آنها چت داشته‌ایم
        sent_conversations = db.session.query(DirectMessage.receiver_id).filter_by(sender_id=current_user.id).distinct().all()
        received_conversations = db.session.query(DirectMessage.sender_id).filter_by(receiver_id=current_user.id).distinct().all()
        
        all_conversation_ids = set()
        for conv in sent_conversations:
            all_conversation_ids.add(conv[0])
        for conv in received_conversations:
            all_conversation_ids.add(conv[0])
        
        friends = User.query.filter(User.id.in_(all_conversation_ids)).all() if all_conversation_ids else []
        rooms = Room.query.all()
        
        return render_template('chat/dashboard.html', friends=friends, rooms=rooms)

    @app.route('/add_friend', methods=['GET', 'POST'])
    @login_required
    def add_friend():
        """افزودن مخاطب جدید"""
        form = AddFriendForm()
        friend = None
        
        if request.method == 'POST':
            if form.validate_on_submit():
                code = form.code.data.strip()
                friend = User.query.filter_by(code=code).first()
                
                if not friend:
                    flash('❌ کاربری با این کد یافت نشد', 'error')
                elif friend.id == current_user.id:
                    flash('❌ نمی‌توانید با خودتان چت کنید', 'error')
                else:
                    # نمایش اطلاعات مخاطب برای تأیید
                    flash(f'✅ کاربر پیدا شد: {friend.username}', 'success')
            else:
                # اگر فرم معتبر نیست اما کد وارد شده
                code = request.form.get('code', '').strip()
                if code and len(code) == 7:
                    friend = User.query.filter_by(code=code).first()
        
        return render_template('chat/add_friend.html', form=form, friend=friend)

    @app.route('/dm/<code>')
    @login_required
    def chat_dm(code):
        """صفحه چت خصوصی"""
        friend = User.query.filter_by(code=code).first_or_404()
        
        if friend.id == current_user.id:
            flash('❌ نمی‌توانید با خودتان چت کنید', 'error')
            return redirect(url_for('add_friend'))
        
        # گرفتن تاریخچه پیام‌ها
        history = DirectMessage.query.filter(
            ((DirectMessage.sender_id == current_user.id) & (DirectMessage.receiver_id == friend.id)) |
            ((DirectMessage.sender_id == friend.id) & (DirectMessage.receiver_id == current_user.id))
        ).order_by(DirectMessage.created_at.asc()).limit(300).all()
        
        room_id = f"dm_{min(current_user.id, friend.id)}_{max(current_user.id, friend.id)}"
        
        return render_template('chat/dm.html', friend=friend, history=history, dm_room=room_id)

    @app.route('/profile')
    @login_required
    def user_profile():
        """پروفایل کاربر"""
        return render_template('user/profile.html')

    @app.route('/my_messages')
    @login_required
    def my_messages():
        """صفحه پیام‌های من"""
        # پیام‌های دریافتی
        received_messages = DirectMessage.query.filter_by(receiver_id=current_user.id).order_by(DirectMessage.created_at.desc()).all()
        
        # پیام‌های ارسالی
        sent_messages = DirectMessage.query.filter_by(sender_id=current_user.id).order_by(DirectMessage.created_at.desc()).all()
        
        # گروه‌بندی بر اساس کاربر
        conversations = {}
        
        for msg in received_messages:
            other_user = msg.sender
            if other_user.id not in conversations:
                conversations[other_user.id] = {
                    'user': other_user,
                    'last_message': msg,
                    'unread_count': 0,
                    'messages': []
                }
            conversations[other_user.id]['messages'].append(msg)
        
        for msg in sent_messages:
            other_user = msg.receiver
            if other_user.id not in conversations:
                conversations[other_user.id] = {
                    'user': other_user,
                    'last_message': msg,
                    'unread_count': 0,
                    'messages': []
                }
            conversations[other_user.id]['messages'].append(msg)
        
        # مرتب‌سازی بر اساس آخرین پیام
        sorted_conversations = sorted(
            conversations.values(), 
            key=lambda x: x['last_message'].created_at, 
            reverse=True
        )
        
        return render_template('chat/my_messages.html', 
                             conversations=sorted_conversations,
                             received_count=len(received_messages),
                             sent_count=len(sent_messages))

    @app.route('/rooms')
    @login_required
    def chat_rooms():
        """لیست اتاق‌های عمومی"""
        rooms = Room.query.all()
        return render_template('chat/rooms.html', rooms=rooms)

    @app.route('/r/<slug>')
    @login_required
    def chat_room(slug):
        """صفحه اتاق چت عمومی"""
        room = Room.query.filter_by(slug=slug).first_or_404()
        history = Message.query.filter_by(room_id=room.id).order_by(Message.created_at.asc()).limit(200).all()
        return render_template('chat/room.html', room=room, history=history)

    # Helper functions
    def canonical_dm_room(a_id, b_id):
        return f"dm_{min(a_id, b_id)}_{max(a_id, b_id)}"

    # Socket.IO events
    @socketio.on('connect')
    def on_connect():
        if current_user.is_authenticated:
            emit('status', {'msg': f'{current_user.username} connected'})

    @socketio.on('join')
    def handle_join(data):
        slug = data.get('room')
        if not slug:
            return
        join_room(slug)
        emit('status', {'msg': f'{current_user.username} joined'}, room=slug)

    @socketio.on('leave')
    def handle_leave(data):
        slug = data.get('room')
        if not slug:
            return
        leave_room(slug)
        emit('status', {'msg': f'{current_user.username} left'}, room=slug)

    @socketio.on('message')
    def handle_message(data):
        slug = data.get('room')
        content = (data.get('msg') or '').strip()
        if not slug or not content:
            return
        
        room = Room.query.filter_by(slug=slug).first()
        if not room:
            return
        
        msg = Message(room_id=room.id, user_id=current_user.id, content=content)
        db.session.add(msg)
        db.session.commit()
        
        emit('message', {
            'user': current_user.username,
            'msg': content,
            'ts': msg.created_at.strftime('%H:%M'),
            'user_id': current_user.id
        }, room=slug)

    @socketio.on('dm_join')
    def handle_dm_join(data):
        friend_id = data.get('friend_id')
        if friend_id is None:
            return
        
        try:
            friend_id = int(friend_id)
        except ValueError:
            return
        
        room = canonical_dm_room(current_user.id, friend_id)
        join_room(room)

    @socketio.on('dm_leave')
    def handle_dm_leave(data):
        friend_id = data.get('friend_id')
        if friend_id is None:
            return
        
        try:
            friend_id = int(friend_id)
        except ValueError:
            return
        
        room = canonical_dm_room(current_user.id, friend_id)
        leave_room(room)

    @socketio.on('dm')
    def handle_dm(data):
        to_code = data.get('to')
        content = (data.get('msg') or '').strip()
        if not to_code or not content:
            return
        
        friend = User.query.filter_by(code=to_code).first()
        if not friend or friend.id == current_user.id:
            return
        
        msg = DirectMessage(
            sender_id=current_user.id, 
            receiver_id=friend.id, 
            content=content
        )
        db.session.add(msg)
        db.session.commit()
        
        room = canonical_dm_room(current_user.id, friend.id)
        emit('dm', {
            'from_code': current_user.code,
            'from_name': current_user.username,
            'msg': content,
            'ts': msg.created_at.strftime('%H:%M'),
            'date': msg.created_at.strftime('%Y/%m/%d')
        }, room=room)

    return app

# ایجاد برنامه
app = create_app()

if __name__ == '__main__':
    print("🚀 پیام‌رسان در حال اجرا است...")
    print("🌐 آدرس: http://localhost:5000")
    print("👤 کاربر پیش‌فرض: admin / admin123")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)