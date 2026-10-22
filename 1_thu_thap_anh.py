import cv2
import os
import json

if not os.path.exists('dataset'): os.makedirs('dataset')

user_file = 'users.json'
users_data = {}

if os.path.exists(user_file):
    with open(user_file, 'r', encoding='utf-8') as f:
        users_data = json.load(f)

print("\n--- ĐĂNG KÝ KHUÔN MẶT MỚI ---")
ten = input("Nhập Họ và Tên: ")
ma_nv = input("Nhập Mã nhân viên: ")
phong_ban = input("Nhập Phòng ban (VD: Phòng IT, Kế toán...): ") # Đổi Ngày sinh thành Phòng ban

new_id = 1 if not users_data else max([int(k) for k in users_data.keys()]) + 1

# Lưu đúng key "dept" để đồng bộ với API trên Web
users_data[str(new_id)] = {
    "name": ten,
    "emp_id": ma_nv,
    "dept": phong_ban
}

with open(user_file, 'w', encoding='utf-8') as f:
    json.dump(users_data, f, ensure_ascii=False, indent=4)

print(f"\n[THÀNH CÔNG] Đã lưu thông tin của {ten}. Gán ID AI là: {new_id}")
print("Chuẩn bị bật Camera...")

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)
count = 0

while True:
    ret, frame = cap.read()
    if not ret: break
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        count += 1
        cv2.imwrite(f"dataset/User.{new_id}.{count}.jpg", gray[y:y+h, x:x+w])
        cv2.putText(frame, f"Da chup: {count}/100", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow('Thu thap du lieu', frame)

    if cv2.waitKey(50) & 0xFF == ord('q'): break
    elif count >= 100: break

cap.release()
cv2.destroyAllWindows()
print(f"[HOÀN TẤT] Đã thu thập xong dữ liệu khuôn mặt cho {ten}.")