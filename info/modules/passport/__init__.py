# 登录注册的相关业务模块

from flask import Blueprint

passport_blu = Blueprint("passport", __name__,url_prefix="/passport")

from . import views
