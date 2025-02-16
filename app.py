# app.py

from flask import Flask, jsonify, request
from mixpanel_event_summary import function as get_summary
import json

app = Flask(__name__)

@app.route('/event-summary/<distinct_id>', methods=['GET'])
def event_summary(distinct_id):
    try:
        summary_json = get_summary(distinct_id)
        data = json.loads(summary_json)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
