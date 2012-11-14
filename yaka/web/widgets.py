"""
Reusable widgets to be included in views.
"""

import cgi
from flask import render_template, json, Markup

from yaka.core.entities import Entity
from yaka.web.filters import labelize


class Column(object):

  def __init__(self, **kw):
    for k, w in kw.items():
      setattr(self, k, w)


class ModelAdapter(object):
  """
  Adapts a persistent entity for
  """
  def __init__(self, model):
    self.model = model
    self.cls = model.__class__

  def __getitem__(self, name):
    try:
      info = self.cls.__mapper__.c[name].info
      label = info['label']
    except:
      label = name
    value = getattr(self.model, name)
    if value is None:
      value = ""
      skip = True
    elif isinstance(value, Entity):
      value = Markup('<a href="%s">%s</a>' % (value._url, cgi.escape(value._name)))
      skip = False
    else:
      value = unicode(value)
      skip = False
    return dict(name=name, value=value, label=label, skip=skip)


class TableView(object):
  """
  """
  # TODO: rewrite
  def __init__(self, columns, show_controls=False):
    self.init_columns(columns)
    self.name = id(self)
    self.show_controls = show_controls

  def init_columns(self, columns):
    # TODO
    self.columns = []
    default_width = 0.99 / len(columns)
    for col in columns:
      if type(col) == str:
        col = dict(name=col, width=default_width)
      assert type(col) == dict
      if not col.has_key('label'):
        col['label'] = labelize(col['name'])
      self.columns.append(col)

  def render(self, model):
    aoColumns = [{'asSorting': [] }] if self.show_controls else []
    aoColumns += [ { 'asSorting': [ "asc", "desc" ] }
                   for i in range(0, len(self.columns)) ]
    datatable_options = {
      'aoColumns': aoColumns,
      'bFilter': self.show_controls,
      'oLanguage': {
        'sSearch': "Filter records:"
      },
      'sPaginationType': "bootstrap",
      'bLengthChange': False,
      'iDisplayLength': 50

    }
    js = "$(%s).dataTable(%s);" % (self.name, json.dumps(datatable_options))

    table = []
    for entity in model:
      table.append(self.render_line(entity))

    return Markup(render_template('widgets/render_table.html',
                                  table=table, show_controls=self.show_controls,
                                  columns=self.columns, table_name=self.name))

  def render_line(self, entity):
    line = []
    for col in self.columns:
      if type(col) == str:
        column_name = col
      else:
        column_name = col['name']
      value = getattr(entity, column_name)
      if value is None:
        value = ""
      if column_name == '_name':
        cell = Markup('<a href="%s">%s</a>'\
                      % (entity._url, cgi.escape(value)))
      elif isinstance(value, Entity):
        cell = Markup('<a href="%s">%s</a>'\
                      % (value._url, cgi.escape(value._name)))
      elif (isinstance(value, str) or isinstance(value, unicode))\
      and value.startswith("http://"):
        # XXX: security issue here
        cell = Markup('<a href="%s">%s</a>' % (value, value[len("http://"):]))
      else:
        cell = unicode(value)
      line.append(cell)
    return line


class AjaxTableView(object):
  """
  A table that gets its data from an AJAX call.
  """
  # TODO
  pass


class SingleView(object):
  def __init__(self, *panels):
    self.panels = panels

  def render(self, model):
    model = ModelAdapter(model)

    return Markup(render_template('widgets/render_single.html',
                                  panels=self.panels, model=model))

  def render_form(self, form, for_new=False):
    # Client-side rules for jQuery.validate
    # See: http://docs.jquery.com/Plugins/Validation/Methods#Validator
    rules = {}
    for field in form:
      rules_for_field = {}
      for validator in field.validators:
        rule_for_validator = getattr(validator, "rule", None)
        if rule_for_validator:
          rules_for_field.update(rule_for_validator)
      if rules_for_field:
        rules[field.name] = rules_for_field
    if rules:
      rules = Markup(json.dumps(rules))
    else:
      rules = None

    return Markup(render_template('widgets/render_for_edit.html',
                                  form=form, for_new=for_new, rules=rules))


#
# Used to describe single entity views.
#
class Panel(object):
  def __init__(self, label=None, *rows):
    self.label = label
    self.rows = rows

  def __iter__(self):
    return iter(self.rows)

  def __getitem__(self, item):
    return self.rows[item]

  def __len__(self):
    return len(self.rows)


class Row(object):
  def __init__(self, *cols):
    self.cols = cols

  def __iter__(self):
    return iter(self.cols)

  def __getitem__(self, item):
    return self.cols[item]

  def __len__(self):
    return len(self.cols)