import typing
import pydantic
from flask import Flask, jsonify, request
from flask.views import MethodView
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker

DSN = "postgresql+psycopg2://rest-api-application:1234@localhost:8000/advertisements"

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
engine = create_engine(DSN)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class APIError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code


@app.errorhandler(APIError)
def resource_not_found(error):
    return jsonify(error=error.message), error.status_code


class PostAds(pydantic.BaseModel):
    title: str
    description: str
    owner: str


class PatchAds(pydantic.BaseModel):
    title: typing.Optional[str]
    description: typing.Optional[str]


def validate(template, data: dict):
    try:
        return template(**data).dict()
    except pydantic.ValidationError as error:
        raise APIError(message=error.errors())


class Ads(Base):
    __tablename__ = "advertisement"

    id = Column(Integer, primary_key=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    published_at = Column(DateTime, server_default=func.now())
    owner = Column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"Advertisement: id={self.id!r}, \
                published at={self.published_at.isoformat()}, \
                owner={self.owner}"

    def get_item(self, session: Session, ads_id: int):
        ads = session.query(Ads).get(ads_id)
        if ads is None:
            raise APIError("Resource not found", 404)
        return ads


Base.metadata.create_all(engine)


class AdsView(MethodView):

    def get(self, ads_id: int):
        with Session() as session:
            ads = Ads().get_item(session, ads_id)
            return jsonify(
                id=ads.id,
                title=ads.title,
                description=ads.description,
                owner=ads.owner,
                published_at=ads.published_at.isoformat(),
            )

    def post(self):
        with Session() as session:
            new_ads = Ads(**validate(PostAds, request.json))
            session.add(new_ads)
            session.commit()
            return jsonify(
                id=new_ads.id,
                created_at=new_ads.published_at
            )

    def patch(self, ads_id: int):
        json_data = validate(PatchAds, request.json)
        with Session() as session:
            ads = Ads().get_item(session, ads_id)
            if json_data.get('title'):
                ads.title = json_data['title']
            if json_data.get('description'):
                ads.description = json_data['description']
            session.add(ads)
            session.commit()
            return {
                'status': 'success',
            }

    def delete(self, ads_id: int):
        with Session() as session:
            ads = Ads().get_item(session, ads_id)
            session.delete(ads)
            session.commit()
            return "", 204


app.add_url_rule(
    "/ads/<int:ads_id>", view_func=AdsView.as_view("advertisement_view"), methods=["GET", "PATCH", "DELETE"]
)
app.add_url_rule(
    "/ads/", view_func=AdsView.as_view("advertisement_view1"), methods=["POST"]
)

app.run()
