import os

from flask import Flask, render_template


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # a simple page that says hello
    @app.route('/')
    def main():
        return render_template('index.html') #https://realpython.com/primer-on-jinja-templating/

    return app