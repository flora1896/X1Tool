#!/usr/bin/env python
# coding:utf-8

from models.application_info import *
from models.session_log import *
from models.application_usage_log import *
from models.use_visity_log import *
from models.application_category import *

from datetime import *
from sqlalchemy import *
from sqlalchemy.orm import *
from json import *
import logging


class DBConnector(object):
    __session_maker = None
    __scope_session = None
    __model = None
    __engine = None

    def __init__(self, connect_string):
        """initialize"""
        """self._engine = engine.create_engine(url, pool_size=pool_size, pool_recycle=3600,
                    max_overflow=sys.maxsize)"""

        self.__engine = create_engine(connect_string, echo=False)
        self.__session_maker = sessionmaker()
        self.__session_maker.configure(bind=self.__engine)
        self.__scope_session = self.__session_maker()

    def create_db(self):
        Model.metadata.create_all(self.__engine)

    def drop_db(self):
        Model.metadata.drop_all(self.__engine)

    def get_record(self, classname, format_method=None, **conditions):
        items = None
        try:
            items = self.__scope_session.query(classname).filter_by(**conditions).all()

            if format_method is None:
                return items

            item_list = list()
            for item in items:
                try:
                    item_list.append(format_method(item))
                except:
                    pass

            return item_list
        except Exception, e:
            logging.error(str(e))

        return items

    def get_application(self, **filter_condition):
        return self.get_record(ApplicationInfo, lambda app: app.serialize(),  **filter_condition)

    def get_application_category(self, **filter_condition):
        return self.get_record(ApplicationCategory, lambda category: category.serialize(), **filter_condition)

    def register_category(self, category_id, metadata):
        category = self.__scope_session.query(ApplicationCategory).filter_by(id=category_id).first()

        if category is None:
            category = ApplicationCategory()
            self.__scope_session.add(category)

        category.id = category_id
        category.name = metadata.pop('name')
        if category is not None:
            category.resource = JSONEncoder().encode(metadata)

        self.__scope_session.flush()
        self.__scope_session.commit()

    #registry or update
    def register_application(self, appid, metadata):
        app = self.__scope_session.query(ApplicationInfo).filter_by(id=appid).first()

        if app is None:
            app = ApplicationInfo()
            self.__scope_session.add(app)

        app.id = appid
        app.name = metadata.pop('name')
        app.author = metadata.pop('author')
        app.comments = metadata.pop('comments')
        app.category_id = metadata.pop('category')
        if metadata is not None:
            app.resource = JSONEncoder().encode(metadata)

        self.__scope_session.flush()
        self.__scope_session.commit()

    def log_application_usage(self, application_id, session_id, user_id, start_time, end_time, args, results):
        application_usage_log = ApplicationUsageLog(appid=application_id, sid=session_id, uid=user_id, stime=start_time, etime=end_time, inputs=args, outputs=results)

        self.__scope_session.add(application_usage_log)
        self.__scope_session.flush()
        self.__scope_session.commit()

    def log_user_login(self, user_id, session_id, ip, address):
        utc_time = datetime.utcnow()
        user_visit_log = UserVisitLog(uid=user_id, sid=session_id, srcip=ip, location=address, login_time=utc_time)
        self.__scope_session.add(user_visit_log)

        self.__scope_session.flush()
        self.__scope_session.commit()

    def log_user_logout(self, user_id, session_id):
        try:
            user_visit_log = self.__scope_session.query(UserVisitLog).filter_by(uid=user_id, sid=session_id).one()
            utc_time = datetime.utcnow()
            user_visit_log.logout_time = utc_time
            self.__scope_session.flush()
            self.__scope_session.commit()
        except:
            logging.error('invalid logout.')

    def log_session(self, session_id):
        session_log = self.__scope_session.query(SessionLog).filter_by(id=session_id).first()

        if session_log is None:
            start_time = datetime.utcnow()
            session_log = SessionLog(id=session_id, stime=start_time, atime=start_time)
            self.__scope_session.add(session_log)
        else:
            active_time = datetime.utcnow()
            session_log.atime = active_time

        self.__scope_session.flush()
        self.__scope_session.commit()

    def execute(self, sql_commands):
        self.__session_maker().execute(sql_commands)



if __name__ == '__main__':
    mysql_db_config = {
        'host': 'localhost',
        'user': 'root',
        'passwd': '',
        'db': 'X1ToolDatabase',
        'charset': 'utf8'
    }
    MYSQL_DATABASE_URI = 'mysql://%s:%s@%s/%s?charset=%s'%(mysql_db_config['user'],
                                                         mysql_db_config['passwd'],
                                                         mysql_db_config['host'],
                                                         mysql_db_config['db'],
                                                         mysql_db_config['charset'])
    import sys
    SRCROOT = '/root'
    sys.path.append(SRCROOT)
    from server.apps.x1tool_income_tax_calculator import *
    from server.apps.x1tool import *
    db_connector = DBConnector(MYSQL_DATABASE_URI)
    db_connector.drop_db()
    db_connector.create_db()


    from server.apps.x1category import *
    db_connector.register_category(X1Category.FINANCE, get_category(X1Category.FINANCE))

    db_connector.register_category(X1Category.DEFAULT, get_category(X1Category.DEFAULT))

    print db_connector.get_application_category()

    db_connector.register_application(X1Tool.appid(), X1Tool.DEFAULT_METADATA)
    db_connector.register_application(X1Tool_d524bbf3215305aa5c0cd189955a760f7258fe5a.appid(), X1Tool_d524bbf3215305aa5c0cd189955a760f7258fe5a.DEFAULT_METADATA)


    print db_connector.get_application(id=X1Tool.appid())
    print db_connector.get_application(category_id=X1Category.FINANCE)
    print db_connector.get_application(category_id=X1Category.DEFAULT)
    print db_connector.get_application()
    session_id = "00-000-00000-00000000"
    user_id = "anony_007"
    ip = '192.168.1.1'
    address = 'nanjing'

    db_connector.log_session(session_id)

    db_connector.log_user_login(user_id, session_id, ip, address)

    db_connector.log_user_logout(user_id, session_id)

    db_connector.log_application_usage(X1Tool.appid(), session_id, user_id, datetime.utcnow(), datetime.utcnow(), "{income:20000}", "{tax:3000}")
