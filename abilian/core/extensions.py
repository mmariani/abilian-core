# coding=utf-8
"""
Create all standard extensions.

"""

# Note: Because of issues with circular dependencies, Abilian-specific extensions are
# created later.

from __future__ import absolute_import

import os
import importlib
from gettext import NullTranslations
from babel.support import Translations
from redis import StrictRedis
from flask import _request_ctx_stack
import flask.ext.babel

__all__ = ['get_extension', 'db', 'babel', 'mail', 'celery', 'login_manager']

# celery
#
# for defining a task:
#
# from abilian.core.extensions import celery
# @celery.task
# def ...
#
# Application should set flask_app and configure celery
# (i.e. celery.config_from_object, etc)
from .celery import celery

from flask import current_app

# Standard extensions.
import flask.ext.mail as flask_mail

# patch flask.ext.mail.Message.send to always set enveloppe_from default mail
# sender
def _message_send(self, connection):
  sender = current_app.config['MAIL_SENDER']
  enveloppe_from = current_app.config['MAIL_SENDER']
  if not self.extra_headers:
    self.extra_headers = {}
  self.extra_headers['Sender'] = sender
  connection.send(self, sender)

flask_mail.Message.send = _message_send

mail = flask_mail.Mail()
del flask_mail

import sqlalchemy as sa
from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()


def get_extension(name):
  """Get the named extension from the current app, returning None if not found.
  """

  from flask import current_app
  return current_app.extensions.get(name)


def _install_get_display_value(cls):

  _MARK = object()

  def display_value(self, field_name, value=_MARK):
    """ Return display value for fields having 'choices' mapping (stored value
    -> human readable value). For other fields it will simply return field
    value.

    `display_value` should be used instead of directly getting field value.

    If `value` is provided it is "tranlated" to a human-readable value. This is
    useful for obtaining a human readable label from a raw value
    """
    val = getattr(self, field_name) if value is _MARK else value

    mapper = sa.orm.object_mapper(self)
    try:
      field = getattr(mapper.c, field_name)
    except AttributeError:
      pass
    else:
      if 'choices' in field.info:
        get = lambda v: field.info['choices'].get(v, v)
        if isinstance(val, list):
          val = [get(v) for v in val]
        else:
          val = get(val)

    return val

  if not hasattr(cls, 'display_value'):
    cls.display_value = display_value


sa.event.listen(db.Model, 'class_instrument', _install_get_display_value)

# babel i18n
from flask.ext.babel import Babel as BabelBase


class Babel(BabelBase):
  """ Allow to load translations from other modules
  """
  _translations_paths = None

  def __init__(self, *args, **kwargs):
    BabelBase.__init__(self, *args, **kwargs)

  def init_app(self, app):
    super(Babel, self).init_app(app)
    self._translations_paths = [os.path.join(app.root_path, 'translations')]

  def add_translations(self, module_name):
    """ Add translation from external module

    babel.add_translations('abilian.core')
    """
    module = importlib.import_module(module_name)
    for path in (os.path.join(p, 'translations') for p in module.__path__):
      if not (os.path.exists(path) and os.path.isdir(path)):
        continue

      if not os.access(path, os.R_OK):
        self.app.logger.warning("Babel translations: read access not "
                                "allowed \"{}\", skipping.".format(path))
        continue

      self._translations_paths.append(path)

def _get_translations_multi_paths():
  """Returns the correct gettext translations that should be used for
    this request. This will never fail and return a dummy translation
  object if used outside of the request or if a translation cannot be
  found.
  """
  ctx = _request_ctx_stack.top
  if ctx is None:
      return None

  translations = getattr(ctx, 'babel_translations', None)
  if translations is None:
    translations = None
    trs = None

    # reverse order: thus the application catalog is loaded last, so that
    # translations from libraries can be overriden
    for dirname in reversed(ctx.app.extensions['babel']._translations_paths):
      trs = Translations.load(dirname, [flask.ext.babel.get_locale()])

      if not trs or trs.__class__ is NullTranslations:
        # test must not use isinstance: Translations is a subclass of
        # NullTranlations
        continue
      elif (translations is not None
            and translations.__class__ is not NullTranslations):
          translations.merge(trs)
      else:
          translations = trs

    # ensure translations is at least a NullTranslations object
    if translations is None:
      translations = trs

    ctx.babel_translations = translations

  return translations

# monkey patch flask-babel
flask.ext.babel.get_translations = _get_translations_multi_paths

babel = Babel()

from flask.ext.login import LoginManager
login_manager = LoginManager()


class Redis(object):
  """
  Extension for redis connection
  """
  def __init__(self, app=None):
    if app:
      self.init_app(app)

  def init_app(self, app):
    self.app = app
    app.extensions['redis'] = self
    uri = app.config.get('REDIS_URI')
    if not uri:
      # fallback on celery broker
      uri = app.config.get('BROKER_URL')

    if not (uri and
            (uri.startswith('redis://') or uri.startswith('unix://'))):
      raise ValueError('REDIS_URI not set in config, cannot setup redis'
                       ' connection')

    self.conn = StrictRedis.from_url(uri)

redis = Redis()
