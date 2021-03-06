# coding=utf-8
"""
"""
from __future__ import absolute_import

import datetime
from abilian.testing import BaseTestCase
from wtforms.form import Form
import pytz
from . import fields

def user_tz():
  # This one is GMT+8 and has no DST (tests should pass any time in year)
  return 'Asia/Hong_Kong'

USER_TZ = pytz.timezone(user_tz())


class FieldsTestCase(BaseTestCase):

  def create_app(self):
    app = super(FieldsTestCase, self).create_app()
    app.extensions['babel'].timezone_selector_func = None
    app.extensions['babel'].timezoneselector(user_tz)
    return app

  def test_datetime_field(self):
    """
    Test fields supports date with year < 1900
    """
    with self.app.test_request_context(headers={'Accept-Language': 'fr-FR,fr;q=0.8'}):
      f = fields.DateTimeField().bind(Form(), 'dt')
      f.process_formdata(['17/06/1789 | 10:42'])
      # 1789: applied offset for HongKong is equal to LMT+7:37:00,
      # thus we compare with tzinfo=user_tz
      self.assertEquals(
        f.data,
        datetime.datetime(1789, 06, 17, 10, 42, tzinfo=USER_TZ))
      # UTC stored
      self.assertIs(f.data.tzinfo, pytz.utc)
      # displayed in user current timezone
      self.assertEquals(f._value(), '17/06/1789 10:42')

      # test
      # more recent date: offset is GMT+8
      f.process_formdata(['11/01/2011 | 10:42'])
      self.assertEquals(
        f.data,
        datetime.datetime(2011, 1, 11, 2, 42, tzinfo=pytz.utc))


  def test_date_field(self):
    """
    Test fields supports date with year < 1900
    """
    with self.app.test_request_context(headers={'Accept-Language': 'fr-FR,fr;q=0.8'}):
      f = fields.DateField().bind(Form(), 'dt')
      f.process_formdata(['17/06/1789'])
      self.assertEquals(f.data, datetime.date(1789, 06, 17))
      self.assertEquals(f._value(), u'17/06/1789')
