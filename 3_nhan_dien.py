import cv2
import json

# 1. Khởi tạo bộ nhận diện và nạp "trí nhớ"
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('trainer/trainer.yml')
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Hàm đọc sổ bạ JSON để tự động dò tên theo ID
def get_user_info(face_id):
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
            return users_data.get(str(face_id), None)
    except FileNotFoundError:
        return None

# 2. Mở Webcam
cap = cv2.VideoCapture(0)
print("\n[HỆ THỐNG] Đã bật Camera. Nhấn 'q' để thoát.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Tìm khuôn mặt trong khung hình
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))

    for (x, y, w, h) in faces:
        # Đưa khuôn mặt vào dự đoán để lấy ID
        id, distance = recognizer.predict(gray[y:y+h, x:x+w])

        # Nếu độ sai số thấp (< 50), xem như nhận diện được
        if distance < 50:
            user_info = get_user_info(id) # Tra cuốn sổ JSON
            
            if user_info:
                name = user_info['name']
                color = (0, 255, 0) # Khung màu Xanh lá cho người quen
            else:
                name = f"ID {id} (Loi data)"
                color = (0, 255, 255) # Khung màu Vàng nếu có ID mà mất tên
                
            confidence_text = f" {round(100 - distance)}%"
        else:
            name = "Nguoi la"
            color = (0, 0, 255) # Khung màu Đỏ cho người lạ
            confidence_text = f" {round(100 - distance)}%"

        # Vẽ khung và hiển thị tên lên màn hình
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, name, (x + 5, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, confidence_text, (x + 5, y + h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

    # Hiển thị ra màn hình
    cv2.imshow('He Thong Nhan Dien Khuon Mat', frame)

    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

# Dọn dẹp
cap.release()
cv2.destroyAllWindows()