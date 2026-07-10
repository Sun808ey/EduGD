from flask import Blueprint,jsonify


device_bp=Blueprint(
"devices",
__name__
)



@device_bp.route(
"/devices",
methods=["GET"]
)

def devices():

    return jsonify(
        {
        "message":
        "Device API working"
        }
    )
