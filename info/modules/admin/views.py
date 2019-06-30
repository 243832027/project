import time
from datetime import datetime, timedelta

from flask import render_template, request, current_app, session, redirect, url_for, g, jsonify, abort

from info import constants, db
from info.models import User, News, Category
from info.modules.admin import admin_blu
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET

@admin_blu.route("/news_type",methods=["GET","POST"])
def news_type():
    if request.method=="GET":
        try:
            categories=Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_edit_detail.html", errmsg="查询数据错误")

        category_dict_li=[]
        for category in categories:
            cate_dict=category.to_dict()
            category_dict_li.append(cate_dict)

        category_dict_li.pop(0)
        data={
            "categories":category_dict_li
        }
        return render_template("admin/news_type.html",data=data)

    cname=request.json.get("name")
    cid=request.json.get("id")

    if not cname:
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    if cid:
        try:
            cid=int(cid)
            category=Category.query.get(cid)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

        if not category:
            return jsonify(errno=RET.NODATA,errmsg="未查询到数据")

        category.name=cname
    else:
        category=Category()
        category.name=cname
        db.session.add(category)

    return jsonify(errno=RET.OK,errmsg="OK")


@admin_blu.route("/news_edit_detail",methods=["GET","POST"])
def news_edit_detail():
    if request.method=="GET":
        news_id=request.args.get("news_id")

        if not news_id:
            abort(404)
        try:
            news_id=int(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_edit_detail.html",errmsg="参数错误")
        try:
            news=News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_edit_detail.html",errmsg="查询数据错误")

        if not news:
            return render_template("admin/news_edit_detail.html",errmsg="未查询到数据")

        categories=[]
        try:
            categories=Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/news_edit_detail.html", errmsg="查询数据错误")

        category_dict_li=[]
        for category in categories:
            cate_dict=category.to_dict()
            if category.id==news.category_id:
                cate_dict["is_selected"]=True
            category_dict_li.append(cate_dict)
        category_dict_li.pop(0)
        data={
            "news":news.to_dict(),
            "categories":category_dict_li
        }

        return render_template("admin/news_edit_detail.html",data=data)
    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 1.1 判断数据是否有值
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    try:
        news=News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到数据")

    if index_image:
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

        # 2. 将标题图片上传到七牛
        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + key

    # 3. 设置相关数据
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    return jsonify(errno=RET.OK,errmsg="OK")


@admin_blu.route("/news_edit")
def news_edit():
    page = request.args.get("p", 1)
    keywords=request.args.get("keywords",None)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    filters=[News.status==0]

    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters) \
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_basic_dict())

    context = {"total_page": total_page, "current_page": current_page, "news_list": news_dict_list}

    return render_template('admin/news_edit.html', data=context)


@admin_blu.route("/news_review_action",methods=["POST"])
def news_review_action():
    news_id=request.json.get("news_id")
    action=request.json.get("action")

    if not all([news_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    if action not in ("accept","reject"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news=News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据查询失败")
    if not news:
        return jsonify(errno=RET.NODATA,errmsg="未查询到数据")

    if action=="accept":
        news.status=0
    else:
        reason=request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR,errmsg="请输入拒绝原因")
        news.status=-1
        news.reason=reason

    return jsonify(errno=RET.OK,errmsg="OK")


@admin_blu.route("/news_review_detail/<int:news_id>")
def news_review_detail(news_id):
    news=None
    try:
        news=News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return render_template("admin/news_review_detail.html",data={"errmsg":"未查到此新闻"})

    data={"news":news.to_dict()}
    return render_template("admin/news_review_detail.html",data=data)


@admin_blu.route("/news_review")
def news_review():
    page = request.args.get("p", 1)
    keywords=request.args.get("keywords",None)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    filters=[News.status!=0]

    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters) \
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_review_dict())

    context = {"total_page": total_page, "current_page": current_page, "news_list": news_dict_list}

    return render_template('admin/news_review.html', data=context)

@admin_blu.route("/user_list")
def user_list():
    page=request.args.get("p",1)

    try:
        page=int(page)
    except Exception as e:
        current_app.logger.error(e)
        page=1

    users=[]
    current_page=1
    total_page=1
    try:
        paginate=User.query.filter(User.is_admin==False).paginate(page,constants.ADMIN_USER_PAGE_MAX_COUNT,False)
        users=paginate.items
        current_page=paginate.page
        total_page=paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li=[]
    for user in users:
        user_dict_li.append(user.to_admin_dict())

    data={
        "users":user_dict_li,
        "current_page":current_page,
        "total_page":total_page
    }

    return render_template("admin/user_list.html", data=data)
@admin_blu.route("/user_count")
def user_count():

    total_count=0
    try:
        total_count=User.query.filter(User.is_admin==False).count()
    except Exception as e:
        current_app.logger.error(e)

    mon_count = 0
    t=time.localtime()
    begin_mon_date=datetime.strptime(("%d-%02d-01" % (t.tm_year,t.tm_mon)),"%Y-%m-%d")
    try:
        mon_count = User.query.filter(User.is_admin == False,User.create_time>begin_mon_date).count()
    except Exception as e:
        current_app.logger.error(e)

    day_count = 0
    begin_day_date = datetime.strptime(("%d-%02d-%02d" % (t.tm_year, t.tm_mon,t.tm_mday)), "%Y-%m-%d")
    try:
        day_count = User.query.filter(User.is_admin == False,User.create_time>begin_day_date).count()
    except Exception as e:
        current_app.logger.error(e)

    active_time=[]
    active_count=[]
    today_date_str=("%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday))
    today_date = datetime.strptime(today_date_str,"%Y-%m-%d")

    for i in range(0,31):
        begin_date=today_date-timedelta(days=i)
        end_date=today_date-timedelta(days=(i-1))
        count=User.query.filter(User.is_admin==False,User.last_login>=begin_date,User.last_login<=end_date).count()
        active_count.append(count)
        active_time.append(begin_date.strftime("%Y-%m-%d"))

    active_time.reverse()
    active_count.reverse()

    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_time":active_time,
        "active_count":active_count

    }
    return render_template("admin/user_count.html",data=data)

@admin_blu.route("/index")
@user_login_data
def index():
    user=g.user
    return render_template("admin/index.html",user=user.to_dict())


@admin_blu.route("/login",methods=["GET","POST"])
def login():

    if request.method=="GET":
        user_id=session.get("user_id",None)
        is_admin=session.get("is_admin",False)
        if user_id and is_admin:
            return redirect(url_for("admin.index"))
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
