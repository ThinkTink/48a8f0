from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post
from db.models.user import User

from db.utils import row_to_dict, row_to_dict_with_field
from middlewares import auth_required

import json


def error_msg(msg):
    return jsonify({"error": msg})


def optional_param_error_msg(label, options):
    return "Invalid '{}}' paramater. Must be: {}".format(label, ", ".join(options))


# Constants
SORT_OPTIONS = ("id", "reads", "likes", "popularity")
DIRECTION_OPTIONS = ("asc", "desc")
POST_RETURN_FIELDS = ("id", "likes", "popularity", "reads", "tags", "text")


@api.post("/posts")
@auth_required
def posts():
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)

    data = request.get_json(force=True)
    text = data.get("text", None)
    tags = data.get("tags", None)
    if text is None:
        return jsonify({"error": "Must provide text for the new post"}), 400

    # Create new post
    post_values = {"text": text}
    if tags:
        post_values["tags"] = tags

    post = Post(**post_values)
    db.session.add(post)
    db.session.commit()

    user_post = UserPost(user_id=user.id, post_id=post.id)
    db.session.add(user_post)
    db.session.commit()

    return row_to_dict(post), 200


@api.get("/posts")
@auth_required
def posts_by_author_id():
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)

    # Check if authorIds is in the path
    if not "authorIds" in request.args:
        return error_msg("authorIds is required"), 400

    # Get parameters by defaults
    author_ids = request.args["authorIds"].split(",")
    sort_option = SORT_OPTIONS[0]
    direction_option = DIRECTION_OPTIONS[0]

    # Check if the value of params is valid
    if any(not str.isdigit(id) for id in author_ids):
        return error_msg("The author ID must be an integer"), 400
    if "sortBy" in request.args:
        sort_option = request.args["sortBy"]
    if "direction" in request.args:
        direction_option = request.args["direction"]
    if sort_option not in SORT_OPTIONS:
        return (
            (error_msg(optional_param_error_msg("sortBy", SORT_OPTIONS))),
            400,
        )
    if direction_option not in DIRECTION_OPTIONS:
        return (
            (error_msg(optional_param_error_msg("direction", DIRECTION_OPTIONS))),
            400,
        )

    post_ids = set()
    posts = list()

    for id in author_ids:
        # Check if the user exist, if not, we skip
        _id = int(id)
        if not User.query.get(_id):
            continue
        current_posts = Post.get_posts_by_user_id(_id)
        for current_post in current_posts:
            if not current_post.id in post_ids:
                post_ids.add(current_post.id)
                posts.append(row_to_dict_with_field(current_post, POST_RETURN_FIELDS))
    # Sort the results by optional query parameter
    is_descending = direction_option != DIRECTION_OPTIONS[0]
    posts = sorted(posts, key=lambda post: post[sort_option], reverse=is_descending)

    # Return final result
    return jsonify({"posts": posts}), 200


@api.patch("posts/<int:postId>")
@auth_required
def update_post(postId):
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)

    # Check if the post exist with the post ID.
    # If it exists, check if the user is associated with the post.
    post = Post.query.get(postId)
    if not post:
        return error_msg("The post ID does not exist"), 404
    if not post in Post.get_posts_by_user_id(user.id):
        return error_msg("You do not have permission to update the post"), 401

    # Update the post with new data
    data = request.json
    user_post = db.session.query(UserPost).filter(UserPost.post_id == postId)
    new_author_ids = data["authorIds"] if "authorIds" in data else None
    if "authorIds" in data:
        for record in user_post:
            # Remove the record if the current author ID is not in the list of new author IDs.
            # If not, remove the ID so that we don't have to update it again in the database.
            if not record.user_id in new_author_ids:
                db.session.delete(record)
            else:
                new_author_ids.remove(record.user_id)
        db.session.commit()

    # The remaining author IDs in the list are the new records,
    # waiting to be made in the database.
    if new_author_ids:
        for author_id in new_author_ids:
            new_user_post = UserPost(user_id=author_id, post_id=postId)
            db.session.add(new_user_post)
        db.session.commit()

    # Update the other new data
    tags = data.get("tags", None)
    text = data.get("text", None)

    if tags:
        post.tags = tags
    if text != None:
        if len(text) == 0:
            return error_msg("New text of the post must be non-empty"), 422
        post.text = text

    if tags or text:
        db.session.commit()

    # Return the updated post if the user updates the post successfully
    post = Post.query.get_or_404(postId)
    author_ids = [
        record.user_id
        for record in db.session.query(UserPost).filter(UserPost.post_id == postId)
    ]
    post = row_to_dict_with_field(post, POST_RETURN_FIELDS)
    post["authorIds"] = author_ids

    return jsonify({"post": post})
