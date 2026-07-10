from . import db


class Device(db.Model):

    id=db.Column(
        db.Integer,
        primary_key=True
    )


    device_uuid=db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )


    android_version=db.Column(
        db.String(20)
    )


    status=db.Column(
        db.String(20),
        default="active"
    )
