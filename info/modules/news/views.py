from flask import render_template, current_app, session, g, abort, jsonify, request

from info import constants, db
from info.models import News, User, Comment, CommentLike
from info.modules.news import news_blu
from info.utils.common import user_login_data
from info.utils.response_code import RET

@news_blu.route("/comment_like",methods=["POST"])
@user_login_data
def comment_like():

    user=g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg="用户未登录")

    comment_id=request.json.get("comment_id")
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    if not all([comment_id,news_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    if action not in ["add","remove"]:
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    try:
        comment_id=int(comment_id)
        news_id=int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    try:
        comment=Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据查询错误")

    if not comment:
        return jsonify(errno=RET.NODATA,errmsg="数据不存在")

    if action=="add":
        comment_like_model=CommentLike.query.filter(CommentLike.user_id==user.id,CommentLike.comment_id==comment.id).first()
        if not comment_like_model:
            comment_like_model=CommentLike()
            comment_like_model.user_id=user.id
            comment_like_model.comment_id=comment.id
            db.session.add(comment_like_model)
            comment.like_count+=1
    else:
        comment_like_model=CommentLike.query.filter(CommentLike.user_id==user.id,CommentLike.comment_id==comment.id).first()
        if comment_like_model:
            db.session.delete(comment_like_model)
            comment.like_count -= 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库操作失败")

    return jsonify(errno=RET.OK,errmsg="OK")

@news_blu.route("/news_comment",methods=["POST"])
@user_login_data
def comment_news():

    user=g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    news_id=request.json.get("news_id")
    comment_content = request.json.get("comment")
    parent_id = request.json.get("parent_id")

    if not all([news_id,comment_content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news_id=int(news_id)
        if parent_id:
            parent_id=int(parent_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        news=News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not news:
        return jsonify(errno=RET.NODATA,errmsg="未查到数据")

    comment=Comment()
    comment.user_id=user.id
    comment.news_id=news_id
    comment.content=comment_content
    if parent_id:
        comment.parent_id=parent_id
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()

    return jsonify(errno=RET.OK, errmsg="OK",data=comment.to_dict())


@news_blu.route("/news_collect",methods=["POST"])
@user_login_data
def collect_news():

    user=g.user

    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg="用户未登录")

    news_id=request.json.get("news_id")
    action=request.json.get("action")

    if not all([news_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")
    if action not in ["collect","cancel_collect"]:
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")
    try:
        news_id=int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    try:
        news=News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据查询错误")

    if not news:
        return jsonify(errno=RET.NODATA,errmsg="未查到数据")

    if action=="cancel_collect":
        if news in user.collection_news:
            user.collection_news.remove(news)
    else:
        if news not in user.collection_news:
            user.collection_news.append(news)

    return jsonify(errno=RET.OK,errmsg="操作成功")

@news_blu.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):


    user= g.user

    new_list = []
    try:
        new_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
    news_dict_li = []
    for news in new_list:
        news_dict_li.append(news.to_basic_dict())

    news=None

    try:
        news=News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        abort(404)

    news.clicks+=1

    is_collected=False

    if user:
        if  news in user.collection_news:
            is_collected=True

    comments=[]

    try:
        comments=Comment.query.filter(Comment.news_id==news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e :
        current_app.logger.error(e)
    comment_like_ids=[]
    if g.user:
        try:
            comment_ids=[comment.id for comment in comments]

            comment_likes=CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),CommentLike.user_id==g.user.id).all()

            comment_like_ids=[comment_like.comment_id for comment_like in comment_likes]
        except Exception as e:
            current_app.logger.error(e)
    comment_dict_li=[]
    for comment in comments:
        comment_dict=comment.to_dict()
        comment_dict['is_like']=False
        if comment.id in comment_like_ids:
            comment_dict['is_like'] = True
        comment_dict_li.append(comment_dict)

    data={
        "user": user.to_dict() if user else None,
        "news_dict_li":news_dict_li,
        "news":news.to_dict(),
        "is_collected":is_collected,
        "comments":comment_dict_li
    }
    return render_template("news/detail.html",data=data)