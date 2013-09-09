"""
Audit Service: logs modifications to audited objects.

Only subclasses of Entity are auditable, at this point.

TODO: In the future, we may decide to:

- Make Models that have the __auditable__ property (set to True) auditable.
- Make Entities that have the __auditable__ property set to False not auditable.
"""

from datetime import datetime
import pickle
from flask import current_app

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, Unicode, DateTime, Text, Binary

from abilian.core.subjects import User
from abilian.core.extensions import db


CREATION = 0
UPDATE   = 1
DELETION = 2
RELATED = 1 << 7


class AuditEntry(db.Model):
  """
  Logs modifications to auditable classes.
  """
  id = Column(Integer, primary_key=True)
  happened_at = Column(DateTime, default=datetime.utcnow)
  type = Column(Integer) # CREATION / UPDATE / DELETION

  entity_id = Column(Integer)
  entity_class = Column(Text)
  entity_name = Column(Unicode(length=255))

  user_id = Column(Integer, ForeignKey(User.id))
  user = relationship(User)

  changes_pickle = Column(Binary)

  def __repr__(self):
    return "<AuditEntry id=%s type=%s user=%s %sentity=<%s id=%s>>" % (
      self.id,
      {CREATION: "CREATION", DELETION: "DELETION", UPDATE: "UPDATE"}[self.op],
      self.user,
      'related ' if self.related else '',
      self.entity_class, self.entity_id)

  @property
  def op(self):
    return self.type & ~RELATED

  @property
  def related(self):
    return self.type & RELATED

  #noinspection PyTypeChecker
  def get_changes(self):
    # Using Pickle here instead of JSON because we need to pickle values
    # such as dates. This could make schema migration more difficult, though.
    if self.changes_pickle:
      return pickle.loads(self.changes_pickle)
    else:
      return {}

  def set_changes(self, changes):
    changes = self._format_changes(changes)
    self.changes_pickle = pickle.dumps(changes)

  changes = property(get_changes, set_changes)

  def _format_changes(self, changes):
    uchanges = {}
    for k, v in changes.iteritems():
      k = unicode(k)
      uv = []
      if isinstance(v, dict):
        # field k is a related model with its own changes
        uv = self._format_changes(v)
      else:
        for val in v:
          if isinstance(val, str):
            # TODO: Temp fix for errors that happen during migration
            try:
              val = val.decode('utf-8')
            except:
              current_app.logger.error("A unicode error happened on changes %s",
                                       repr(changes))
              val = u"[[Somme error occurred. Working on it]]"
          uv.append(val)
        uv = tuple(uv)
      uchanges[k] = uv
    return uchanges


  # FIXME: extremely innefficient
  @property
  def entity(self):
    # Avoid circular import
    from .service import audit_service

    #noinspection PyTypeChecker
    if not self.entity_class or not self.entity_id:
      return None
    cls = audit_service.model_class_names.get(self.entity_class)
    return cls.query.get(self.entity_id) if cls is not None else None
