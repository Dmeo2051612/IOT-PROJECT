from flask import Flask, request, jsonify
import cv2
import numpy as np
import json

app = Flask(__name__)

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('trainer/trainer.yml')
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Hàm đọc sổ bạ JSON
def get_user_info(face_id):
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
            # Ép ID thành chuỗi vì key trong JSON luôn là chuỗi
            return users_data.get(str(face_id), None)
    except FileNotFoundError:
        return None

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'imageFile' not in request.files:
        return jsonify({"error": "Khong tim thay file anh"}), 400

    try:
        file = request.files['imageFile']
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Anh bi hong"}), 400

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))

        if len(faces) == 0:
            return jsonify({"name": "Khong thay mat", "match": False}), 200

        (x, y, w, h) = faces[0]
        id, distance = recognizer.predict(gray[y:y+h, x:x+w])

        if distance < 65:
            # Tra cứu thông tin từ ID AI nhả ra
            user_info = get_user_info(id)
            
            if user_info:
                return jsonify({
                    "match": True, 
                    "confidence": round(100 - distance),
                    "name": user_info['name'],
                    "emp_id": user_info['emp_id'],
                    "dept": user_info.get('dept', 'Chưa cập nhật') # Đã sửa dob thành dept
                }), 200
            else:
                return jsonify({"name": "Co ID nhung khong co ten", "match": False}), 200
        else:
            return jsonify({"name": "Nguoi la", "match": False}), 200
            
    except Exception as e:
        return jsonify({"error": str(e), "match": False}), 500

if __name__ == '__main__':
    print("\n[HỆ THỐNG] API Server Đa Người Dùng (Cho ESP32) đang chạy...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)