# import flask
from flask import Flask, jsonify, request
from Models import *


app = Flask(__name__)
app.config["DEBUG"] = True


@app.route('/Predict_Leave', methods=['GET'])
def home():
    if request.method == "GET":
        employee_id = str(request.args.get("employee_id", ""))
        predict_days = int(request.args.get("days", ""))
        predictions = int(request.args.get("predictions", ""))

        print(employee_id, predict_days, predictions)
        Leave_data = predict_leaves(employee_id, predict_days, predictions)
        lst = []
        for i in Leave_data.index:
            lst.append({
                "Date": i,
                "Day": Leave_data['Day'][i]
            })

        return jsonify({
            "Status": "Success",
            "Data": lst
        })


app.run()
