from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/event', methods=['POST'])
def index():
    return jsonify({'message': 'Event received'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)