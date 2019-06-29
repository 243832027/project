from flask import render_template, request, current_app, session, redirect, url_for

from info.models import User
from info.modules.admin import admin_blu


@admin_blu.route("/index")
def index():
    return render_template("admin/index.html")


@admin_blu.route("/login",methods=["GET","POST"])
def login():

    if request.method=="GET":
        return render_template("admin/login.html")

    username=request.form.get("username")
    password=request.form.get("password")
    if not all([username,password]):
        return render_template("admin/login.html",errmsg="参数错误")

    try:
        user=User.query.filter(User.is_admin==True,User.mobile==username).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", errmsg="用户信息查询失败")

    if not user:
        return render_template("admin/login.html", errmsg="未查询到用户信息")

    if not user.check_password(password):
        return render_template("admin/login.html", errmsg="用户名或密码错误")

    session["user_id"]=user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name
    session["is_admin"] = user.is_admin

    return redirect(url_for("admin.index"))
