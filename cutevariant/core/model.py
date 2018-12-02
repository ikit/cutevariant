from sqlalchemy import Column, Integer, String, Float, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event, ForeignKey
from sqlalchemy_views import CreateView, DropView

import os

Base = declarative_base()


class Field(Base):
    __tablename__ = "fields"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    category = Column(String)
    description = Column(String)
    value_type = Column(String)


class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True)
    bin = Column(Integer)
    chr = Column(String)
    start = Column(Integer)
    end  = Column(Integer)
    name = Column(String)


class Variant(Base):
    __tablename__ = "variants"
    id = Column(Integer, primary_key=True)
    bin = Column(Integer)

    def __getitem__(self, index):
        return getattr(self, index)

    def __setitem__(self, index, value):
        setattr(self, index, value)

    @classmethod
    def create_column(cls, name, column):
        setattr(cls, name, column)

    @classmethod
    def create_column_from_field(cls, field: Field):
        column_type = eval(field.value_type)  # Integer,String,Float,Boolean
        Variant.create_column(field.name, Column(column_type))


class View(Base):
    __tablename__ = "views"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    sql = Column(String)

class VariantSet(Base):
    __tablename__ = "view_has_variants"
    variant_id = Column(Integer, ForeignKey('variants.id'), primary_key=True)
    view_id = Column(Integer, ForeignKey('views.id'), primary_key=True)



@event.listens_for(View, "before_insert")
def create_view(mapper, connect, target):
    print("before insert ", target)
    #connect.execute(f"CREATE VIEW {target.name} AS {target.sql}")


# @event.listens_for(VariantView, "before_delete")
# def drop_view(mapper, connect, target):
#     print("before remove ", target)
#     connect.execute(f"Drop VIEW {target.name}")


def select_variant(tablename, condition, engine):
    table = Table(tablename, Base.metadata, autoload=True, autoload_with=engine)
    for variant in engine.execute(table.select(condition)):
        yield variant


def create_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


if __name__ == "__main__":

    pass

    # import_file("../../exemples/test2.vcf", "/tmp/test4.db")
