# app/routes/__init__.py
from flask import Blueprint
from .customer_routes import bp as customer_bp
from .job_routes import bp as job_bp
from .timer_routes import bp as timer_bp
from .image_routes import bp as image_bp

def init_app(app):
    app.register_blueprint(customer_bp, url_prefix='/')
    app.register_blueprint(job_bp, url_prefix='/job')
    app.register_blueprint(timer_bp, url_prefix='/timer')
    app.register_blueprint(image_bp, url_prefix='/image')