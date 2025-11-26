from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import random
import string

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    code = db.Column(db.String(7), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship('Message', backref='user', lazy=True)
    sent_dms = db.relationship('DirectMessage', foreign_keys='DirectMessage.sender_id', backref='sender', lazy=True)
    received_dms = db.relationship('DirectMessage', foreign_keys='DirectMessage.receiver_id', backref='receiver', lazy=True)

    @staticmethod
    def generate_code():
        """تولید کد ۷ رقمی منحصر به فرد"""
        while True:
            code = ''.join(random.choices(string.digits, k=7))
            if not User.query.filter_by(code=code).first():
                return code

    def get_conversations(self):
        """گرفتن تمام مکالمات کاربر"""
        sent_conversations = db.session.query(
            DirectMessage.receiver_id
        ).filter(
            DirectMessage.sender_id == self.id
        ).distinct().all()
        
        received_conversations = db.session.query(
            DirectMessage.sender_id
        ).filter(
            DirectMessage.receiver_id == self.id
        ).distinct().all()
        
        all_conversation_ids = set()
        for conv in sent_conversations:
            all_conversation_ids.add(conv[0])
        for conv in received_conversations:
            all_conversation_ids.add(conv[0])
        
        return list(all_conversation_ids)

class Room(db.Model):
    __tablename__ = 'room'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)

    messages = db.relationship('Message', backref='room', lazy=True)

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DirectMessage(db.Model):
    __tablename__ = 'direct_message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def get_other_user(self, current_user_id):
        """گرفتن کاربر مقابل در مکالمه"""
        if self.sender_id == current_user_id:
            return self.receiver
        else:
            return self.sender