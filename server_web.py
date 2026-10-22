from flask import Flask, render_template, Response, jsonify, request, redirect, url_for
import cv2
import numpy as np
import json
import os
from datetime import datetime
import time
import threading
import random
import smtplib
from email.mime.text import MIMEText
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Khởi tạo Firebase cấu hình hiện tại của bạn
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bt-iot-e145e-default-rtdb.asia-southeast1.firebasedatabase.app/'
})


# =========================================================================
# --- BỘ LẮNG NGHE FIREBASE REALTIME - ĐỒNG BỘ NGƯỢC RFID VỀ DASHBOARD ---
# =========================================================================
def firebase_listener(event):
    if event.data is not None and event.path != "/":
        try:
            new_data = event.data

            if isinstance(new_data, dict) and "name" in new_data:
                log_file = 'logs.json'
                logs = []
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f: logs = json.load(f)

                now = datetime.now()
                if "date" not in new_data:
                    new_data["date"] = now.strftime("%d/%m/%Y")
                if "time" not in new_data:
                    new_data["time"] = now.strftime("%H:%M:%S")

                if new_data.get("status") == "Quẹt thẻ hợp lệ":
                    is_late = now.hour > 8 or (now.hour == 8 and now.minute > 0)
                    new_data["status"] = "Đi muộn (RFID)" if is_late else "Đúng giờ (RFID)"
                elif new_data.get("status") == "Thẻ không hợp lệ":
                    new_data["status"] = "Thẻ lạ gian lận"

                is_duplicate = any(
                    l.get('emp_id') == new_data.get('emp_id') and l.get('time') == new_data.get('time') for l in logs)

                if not is_duplicate:
                    logs.insert(0, new_data)
                    with open(log_file, 'w', encoding='utf-8') as f:
                        json.dump(logs[:100], f, ensure_ascii=False, indent=4)
                    print(
                        f"[FIREBASE STREAM] Đã nhận dữ liệu RFID từ Cloud và bù thời gian cho: {new_data.get('name')}")

        except Exception as e:
            print(f"[STREAM ERROR] Lỗi xử lý dữ liệu đồng bộ ngược: {str(e)}")


try:
    db.reference('attendance_logs').listen(firebase_listener)
    print("[FIREBASE STREAM] Hệ thống lắng nghe đồng bộ hai chiều đã hoạt động!")
except Exception as e:
    print(f"[FIREBASE STREAM LỖI] Không thể kích hoạt bộ lắng nghe: {str(e)}")


# =========================================================================
# --- KHỞI TẠO LUỒNG ĐỌC CAMERA KHÔNG TRỄ ---
class IPVideoStream:
    def __init__(self, src):
        self.stream = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.grabbed, self.frame = self.stream.read()
        self.stopped = False

    def start(self):
        threading.Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            if self.stream.isOpened():
                self.grabbed, self.frame = self.stream.read()
            else:
                time.sleep(0.1)

    def read(self):
        return self.grabbed, self.frame

    def isOpened(self):
        return self.stream.isOpened() and not self.stopped

    def release(self):
        self.stopped = True
        self.stream.release()


app = Flask(__name__)

# --- CẤU HÌNH BỘ NHỚ OTP VÀ BẢO MẬT ĐĂNG NHẬP ADMIN (TỪ APP.PY) ---
otp_storage = {}
SENDER_EMAIL = "ngocdeptraibodoivodich@gmail.com"
SENDER_PASSWORD = "brguzkymovsdzudq"
ADMIN_EMAIL = "madaivi0505@gmail.com"  # Chỉ duy nhất Email này được truy cập hệ thống
OTP_EXPIRY_SECONDS = 60

# --- KHỞI TẠO AI VÀ TRÍ NHỚ CHẤM CÔNG (TỪ SERVER_WEB.PY) ---
recognizer = cv2.face.LBPHFaceRecognizer_create()
if os.path.exists('trainer/trainer.yml'):
    recognizer.read('trainer/trainer.yml')
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

camera = None
ESP32_STREAM_URL = "http://172.20.10.9/stream"
registration_mode = False
reg_count = 0
new_user_id = 0


def get_user_info(face_id):
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            return json.load(f).get(str(face_id), None)
    except FileNotFoundError:
        return None


def save_attendance_log(emp_id, name, distance, dept):
    log_file = 'logs.json'
    logs = []
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f: logs = json.load(f)

    now = datetime.now()
    is_late = now.hour > 8 or (now.hour == 8 and now.minute > 0)

    new_log = {
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M:%S"),
        "emp_id": emp_id,
        "name": name,
        "dept": dept,
        "accuracy": f"{round(100 - distance, 1)}%",
        "status": "Đi muộn" if is_late else "Đúng giờ"
    }

    logs.insert(0, new_log)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs[:100], f, ensure_ascii=False, indent=4)

    try:
        ref = db.reference('attendance_logs')
        ref.push(new_log)
        print("[FIREBASE] Đã đồng bộ lịch sử chấm công lên Cloud thành công!")
    except Exception as e:
        print(f"[FIREBASE LỖI] Không thể đẩy dữ liệu: {str(e)}")


# =========================================================================
# --- CÁC ROUTER GIAO DIỆN CHUYỂN HƯỚNG ĂN KHỚP ---
# =========================================================================

@app.route('/')
def login_page():
    return render_template('login.html')


@app.route('/dashboard')
@app.route('/index.html')
def index():
    return render_template('index.html')


@app.route('/camera.html')
def camera_page(): return render_template('camera.html')


@app.route('/employees.html')
def employees_page(): return render_template('employees.html')


@app.route('/history.html')
def history_page(): return render_template('history.html')


@app.route('/analytics.html')
def analytics_page(): return render_template('analytics.html')


# =========================================================================
# --- API XỬ LÝ ĐĂNG NHẬP OTP BẢO MẬT ADMIN (TÍCH HỢP TỪ APP.PY) ---
# =========================================================================
@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')

    # KIỂM TRA BẢO MẬT: Chặn không cho gửi mã nếu không phải Email Admin chỉ định
    if email != ADMIN_EMAIL:
        return jsonify({"status": "error", "message": "Tài khoản không có quyền truy cập hệ thống!"}), 403

    otp_code = str(random.randint(100000, 999999))

    # Lưu cấu hình mã kèm dấu thời gian để kiểm tra giới hạn 60 giây
    otp_storage[email] = {
        "code": otp_code,
        "timestamp": time.time()
    }

    try:
        msg = MIMEText(
            f"Mã OTP đăng nhập hệ thống chấm công của bạn là: {otp_code}\nLưu ý: Mã này chỉ có hiệu lực trong {OTP_EXPIRY_SECONDS // 60} phút.")
        msg['Subject'] = 'Mã xác thực OTP Hệ Thống Chấm Công'
        msg['From'] = SENDER_EMAIL
        msg['To'] = email

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [email], msg.as_string())
        server.quit()
        return jsonify({"status": "success", "message": "Đã gửi OTP"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    user_otp = data.get('otp')

    if email not in otp_storage:
        return jsonify({"status": "error", "message": "Chưa có mã OTP nào được gửi cho email này!"}), 400

    stored_data = otp_storage[email]
    current_time = time.time()

    # Kiểm tra thời gian hết hạn hiệu lực OTP (60 giây)
    if current_time - stored_data["timestamp"] > OTP_EXPIRY_SECONDS:
        del otp_storage[email]
        return jsonify({"status": "error", "message": "Mã OTP đã hết hạn! Vui lòng quay lại gửi mã mới."}), 400

    if stored_data["code"] == user_otp:
        del otp_storage[email]
        return jsonify({"status": "success", "message": "Đăng nhập thành công"})
    return jsonify({"status": "error", "message": "Mã OTP không chính xác!"}), 400


# =========================================================================
# --- TOÀN BỘ API CAMERA VÀ AI ---
# =========================================================================
def gen_frames():
    global camera, registration_mode, reg_count, new_user_id
    while True:
        if camera is None or not camera.isOpened(): break
        success, frame = camera.read()
        if not success: break

        if registration_mode:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                reg_count += 1
                cv2.imwrite(f"dataset/User.{new_user_id}.{reg_count}.jpg", gray[y:y + h, x:x + w])
                cv2.putText(frame, f"Dang chup: {reg_count}/50", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255),
                            2)
                if reg_count >= 50: registration_mode = False
                break

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


@app.route('/video_feed')
def video_feed(): return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/camera/toggle', methods=['POST'])
def toggle_camera():
    global camera
    action = request.json.get('action')
    if action == 'on':
        if camera is None or not camera.isOpened():
            camera = IPVideoStream(ESP32_STREAM_URL).start()
            time.sleep(1)
            if not camera.isOpened(): return jsonify({"error": "Không kết nối được ESP32 Camera"}), 500
        return jsonify({"status": "ESP32 Camera ON"})
    elif action == 'off':
        if camera is not None:
            camera.release()
            camera = None
        return jsonify({"status": "ESP32 Camera OFF"})


@app.route('/api/recognize', methods=['GET'])
def recognize():
    global camera
    if camera is None or not camera.isOpened(): return jsonify({"error": "Camera chưa mở"}), 400
    success, frame = camera.read()
    if not success: return jsonify({"error": "Lỗi đọc khung hình"}), 500

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))
    if len(faces) == 0: return jsonify({"match": False, "name": "Không thấy khuôn mặt"}), 200

    (x, y, w, h) = faces[0]
    id, distance = recognizer.predict(gray[y:y + h, x:x + w])
    if distance < 85:
        user_info = get_user_info(id)
        if user_info:
            dept = user_info.get('dept', 'Chưa cập nhật')
            save_attendance_log(user_info['emp_id'], user_info['name'], distance, dept)
            return jsonify({"match": True, "name": user_info['name'], "emp_id": user_info['emp_id'], "dept": dept}), 200
    return jsonify({"match": False, "name": "Người lạ"}), 200


@app.route('/api/history', methods=['GET'])
def get_history():
    if os.path.exists('logs.json'):
        with open('logs.json', 'r', encoding='utf-8') as f: return jsonify(json.load(f))
    return jsonify([])


@app.route('/api/employees', methods=['GET'])
def get_employees():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return jsonify(json.load(f))
    return jsonify({})


@app.route('/api/employees/delete/<ai_id>', methods=['DELETE'])
def delete_employee(ai_id):
    user_file = 'users.json'
    if not os.path.exists(user_file): return jsonify({"error": "Không tìm thấy CSDL"}), 404
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)

        if ai_id not in users_data: return jsonify({"error": "Nhân viên không tồn tại"}), 404

        name = users_data[ai_id]['name']
        del users_data[ai_id]

        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)

        try:
            ref_users = db.reference('users')
            ref_users.set(users_data)
            print(f"[FIREBASE] Đã đồng bộ xóa nhân viên {name} khỏi Cloud!")
        except Exception as e:
            print(f"[FIREBASE LỖI] Không thể cập nhật xóa trên Cloud: {str(e)}")

        if os.path.exists('dataset'):
            for filename in os.listdir('dataset'):
                if filename.startswith(f"User.{ai_id}."): os.remove(os.path.join('dataset', filename))

        return jsonify({"success": True, "message": f"Đã xóa nhân viên {name}!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/register', methods=['POST'])
def register_employee():
    global camera, recognizer, registration_mode, reg_count, new_user_id
    data = request.json
    name, emp_id, dept = data.get('name'), data.get('emp_id'), data.get('dept')

    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(ESP32_STREAM_URL, cv2.CAP_FFMPEG)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    user_file = 'users.json'
    users_data = {}
    if os.path.exists(user_file):
        with open(user_file, 'r', encoding='utf-8') as f: users_data = json.load(f)

    new_user_id = 1 if not users_data else max([int(k) for k in users_data.keys()]) + 1
    users_data[str(new_user_id)] = {"name": name, "emp_id": emp_id, "dept": dept}
    with open(user_file, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, ensure_ascii=False, indent=4)

    if not os.path.exists('dataset'): os.makedirs('dataset')
    reg_count = 0
    registration_mode = True

    start_time = time.time()
    while registration_mode:
        time.sleep(0.5)
        if time.time() - start_time > 20:
            registration_mode = False
            return jsonify({"error": "Hết thời gian chụp khuôn mặt!"}), 400

    try:
        imagePaths = [os.path.join('dataset', f) for f in os.listdir('dataset') if f.endswith('.jpg')]
        faceSamples, ids = [], []
        for imagePath in imagePaths:
            gray_img = cv2.imread(imagePath, cv2.IMREAD_GRAYSCALE)
            if gray_img is None: continue
            id_user = int(imagePath.split('.')[1])
            faces = face_cascade.detectMultiScale(gray_img)
            for (x, y, w, h) in faces:
                faceSamples.append(gray_img[y:y + h, x:x + w])
                ids.append(id_user)
                faceSamples.append(cv2.flip(gray_img[y:y + h, x:x + w], 1))
                ids.append(id_user)

        if len(faceSamples) > 0:
            try:
                ref_users = db.reference('users')
                ref_users.set(users_data)
                print(f"[FIREBASE] Đã đồng bộ thông tin nhân viên {name} lên Cloud!")
            except Exception as e:
                print(f"[FIREBASE LỖI] Không thể cập nhật nhân viên lên Cloud: {str(e)}")

            if not os.path.exists('trainer'): os.makedirs('trainer')
            recognizer.train(faceSamples, np.array(ids, dtype=np.int32))
            recognizer.write('trainer/trainer.yml')
            return jsonify({"success": True, "message": f"Đã học xong khuôn mặt {name}"}), 200

        return jsonify({"error": "Không trích xuất được đặc trưng mẫu mặt!"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API đón luồng ảnh chụp từ Kit ESP32-S3 gửi về
@app.route('/api/esp32/recognize', methods=['POST'])
def esp32_recognize():
    if 'imageFile' not in request.files: return jsonify({"match": False, "error": "Không nhận được ảnh"}), 400
    try:
        file = request.files['imageFile']
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))

        if len(faces) == 0: return jsonify({"match": False, "name": "Không thấy khuôn mặt"}), 200
        (x, y, w, h) = faces[0]
        id, distance = recognizer.predict(gray[y:y + h, x:x + w])

        if distance < 85:
            user_info = get_user_info(id)
            if user_info:
                dept = user_info.get('dept', 'Chưa cập nhật')
                save_attendance_log(user_info['emp_id'], user_info['name'], distance, dept)
                return jsonify({"match": True, "name": user_info['name'], "dept": dept}), 200
        return jsonify({"match": False, "name": "Người lạ"}), 200
    except Exception as e:
        return jsonify({"match": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)