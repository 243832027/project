from flask import render_template, g, redirect, request, jsonify, current_app, abort

from info import constants, db
from info.models import Category, News, User
from info.modules.profile import profile_blu
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET

@profile_blu.route("/other_news_list")
def other_news_list():

    other_id=request.args.get("user_id")
    page=request.args.get("p",1)

    try:
        page=int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")
    try:
        other=User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据查询失败")
    if not other:
        return jsonify(errno=RET.NODATA,errmsg="当前用户不存在")

    try:
        paginate = other.news_list.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    news_dict_li = []
    for news_item in news_li:
        news_dict_li.append(news_item.to_basic_dict())
    data = {"news_list": news_dict_li,
            "total_page": total_page,
            "current_page": current_page
            }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@profile_blu.route("/other_info")
@user_login_data
def other_info():
    user=g.user

    other_id=request.args.get("user_id")

    if not other_id:
        abort(404)
    other = None
    try:
        other=User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)

    if not other:
        abort(404)

    is_followed=False
    if other and user:
        if other in user.followed:
            is_followed=True

    data={
        "is_followed":is_followed,
        "user":g.user.to_dict() if g.user else None,
        "other_info":other.to_dict()
    }
    return render_template("news/other.html",data=data)


@profile_blu.route("/user_follow")
@user_login_data
def user_follow():
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user

    follows = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.followed.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)
        # 获取当前页数据
        follows = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li = []

    for follow_user in follows:
        user_dict_li.append(follow_user.to_dict())
    data = {"users": user_dict_li, "total_page": total_page, "current_page": current_page}
    return render_template('news/user_follow.html', data=data)

@profile_blu.route("/news_list")
@user_login_data
def user_news_list():

    page=request.args.get("p",1)
    try:
        page=int(page)
    except Exception as e:
        current_app.logger.error(e)
        page=1

    user=g.user
    news_list=[]
    current_page=1
    total_page=1
    try:
        paginate=News.query.filter(News.user_id==user.id).paginate(page,constants.USER_COLLECTION_MAX_NEWS,False)
        news_list=paginate.items
        current_page=paginate.page
        total_page=paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li=[]
    for news in news_list:
        news_dict_li.append(news.to_review_dict())

    data={
        "news_list":news_list,
        "current_page":current_page,
        "total_page":total_page
    }

    return render_template("news/user_news_list.html",data=data)

@profile_blu.route("/news_release",methods=["GET","POST"])
@user_login_data
def news_release():
    if request.method=="GET":
        categories=[]
        try:
            categories=Category.query.all()
        except Exception as e:
            current_app.logger.error(e)

        category_dict_li=[]
        for category in categories:
            category_dict_li.append(category.to_dict())

        category_dict_li.pop(0)

        return render_template("news/user_news_release.html",data={"categories":category_dict_li})

    title=request.form.get("title")
    source ="个人发布"
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")

    if not all([title,digest,content,index_image,category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        category_id=int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        index_img_data=index_image.read()
        key=storage(index_img_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")



    news=News()
    news.title=title
    news.digest=digest
    news.content=content
    news.source=source
    news.index_image_url=constants.QINIU_DOMIN_PREFIX + key
    news.category_id=category_id
    news.user_id=g.user.id

    news.status=1

    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg="数据保存失败")

    return jsonify(errno=RET.OK,errmsg="OK")


@profile_blu.route("/collection")
@user_login_data
def user_collection():
    page=request.args.get("p",1)

    try:
        page=int(page)
    except Exception as e:
        current_app.logger.error(e)
        page=1
    user=g.user
    news_list=[]
    current_page=1
    total_page=1
    try:
        paginate=user.collection_news.paginate(page,constants.USER_COLLECTION_MAX_NEWS,False)
        current_page=paginate.page
        total_page=paginate.pages
        news_list=paginate.items
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li=[]
    for news in news_list:
        news_dict_li.append(news.to_basic_dict())

    data={
        "current_page":current_page,
        "total_page":total_page,
        "collections":news_dict_li
    }

    return render_template("news/user_collection.html",data=data)

@profile_blu.route("/pass_info",methods=["GET","POST"])
@user_login_data
def pass_info():
    if request.method == "GET":
        return render_template("news/user_pass_info.html")


    old_password=request.json.get("old_password")
    new_password = request.json.get("new_password")

    if not all([old_password,new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    user=g.user
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR,errmsg="密码错误")

    user.password=new_password

    return jsonify(errno=RET.OK,errmsg="O")

@profile_blu.route("/pic_info",methods=["GET","POST"])
@user_login_data
def pic_info():
    user=g.user
    if request.method=="GET":
        return render_template("news/user_pic_info.html",data={"user":user.to_dict()})
    try:
        avatar=request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        key=storage(avatar)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg="上传头像失败")

    user.avatar_url=key
    return jsonify(errno=RET.OK,errmsg="OK",data={"avatar_url":constants.QINIU_DOMIN_PREFIX+key})


@profile_blu.route("/base_info",methods=["GET","POST"])
@user_login_data
def base_info():
    if request.method=="GET":
        return render_template("news/user_base_info.html",data={"user":g.user.to_dict()})

    nick_name=request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")

    if not all([nick_name,signature,gender]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    if gender not in ("WOMAN","MAN"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    user=g.user
    user.nick_name=nick_name
    user.signature=signature
    user.gender=gender

    return jsonify(errno=RET.OK,errmssg="OK")


@profile_blu.route("/info")
@user_login_data
def user_info():
    user=g.user

    if not user:
        return redirect("/")
    data={
        "user":user.to_dict()
    }
    return render_template("news/user.html",data=data)

