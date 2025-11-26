from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
import re

class RegisterForm(FlaskForm):
    username = StringField('نام کاربری', validators=[
        DataRequired(message='نام کاربری الزامی است'),
        Length(min=3, max=80, message='نام کاربری باید بین ۳ تا ۸۰ کاراکتر باشد')
    ])
    email = StringField('ایمیل', validators=[
        DataRequired(message='ایمیل الزامی است'),
        Email(message='لطفاً یک ایمیل معتبر وارد کنید'),
        Length(max=120)
    ])
    password = PasswordField('رمز عبور', validators=[
        DataRequired(message='رمز عبور الزامی است'),
        Length(min=6, max=128, message='رمز عبور باید حداقل ۶ کاراکتر باشد')
    ])
    submit = SubmitField('🎯 ایجاد حساب کاربری')

    def validate_password(self, field):
        password = field.data
        if len(password) < 6:
            raise ValidationError('رمز عبور باید حداقل ۶ کاراکتر باشد')
        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            raise ValidationError('رمز عبور باید شامل حروف و اعداد باشد')

class LoginForm(FlaskForm):
    code_or_username = StringField('کد یا نام کاربری', validators=[
        DataRequired(message='این فیلد الزامی است'),
        Length(min=3, max=120, message='مقدار وارد شده باید بین ۳ تا ۱۲۰ کاراکتر باشد')
    ])
    password = PasswordField('رمز عبور', validators=[
        DataRequired(message='رمز عبور الزامی است'),
        Length(min=6, max=128)
    ])
    submit = SubmitField('🚀 ورود به سیستم')

class AddFriendForm(FlaskForm):
    code = StringField('کد ۷ رقمی مخاطب', validators=[
        DataRequired(message='کد الزامی است'),
        Length(min=7, max=7, message='کد باید دقیقاً ۷ رقمی باشد')
    ])
    submit = SubmitField('🔍 پیدا کردن مخاطب')