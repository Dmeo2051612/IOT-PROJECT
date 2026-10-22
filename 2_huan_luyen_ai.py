import cv2
import numpy as np
import os

# 1. Khởi tạo bộ nhận diện khuôn mặt LBPH (Yêu cầu đã cài opencv-contrib-python)
recognizer = cv2.face.LBPHFaceRecognizer_create()

# Gọi lại bộ lọc Haar Cascade để đảm bảo quét lại khuôn mặt chuẩn xác một lần nữa
detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Hàm đọc ảnh từ thư mục dataset và gán nhãn (ID) cho AI học
def getImagesAndLabels(path):
    # Lấy đường dẫn của tất cả các file ảnh trong thư mục dataset
    imagePaths = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.jpg')]     
    faceSamples = []
    ids = []

    for imagePath in imagePaths:
        # Đọc ảnh ở chế độ ảnh xám
        gray_img = cv2.imread(imagePath, cv2.IMREAD_GRAYSCALE)
        
        # Lấy tên file ảnh (Ví dụ: "User.1.50.jpg") rồi tách chuỗi để lấy ID (số 1)
        filename = os.path.basename(imagePath)
        try:
            id_user = int(filename.split('.')[1])
        except (IndexError, ValueError):
            continue # Bỏ qua nếu file không đúng định dạng chuẩn
            
        # Quét lại khuôn mặt trong ảnh để đảm bảo lấy đúng vùng chứa mặt
        faces = detector.detectMultiScale(gray_img)

        for (x, y, w, h) in faces:
            face_roi = gray_img[y:y+h, x:x+w]
            
            # Đưa ảnh gốc vào mảng
            faceSamples.append(face_roi)
            ids.append(id_user)
            
            # Tối ưu: Lật ngang ảnh bằng OpenCV để nhân đôi dữ liệu
            flipped_face = cv2.flip(face_roi, 1)
            faceSamples.append(flipped_face)
            ids.append(id_user)

    return faceSamples, ids

print("\n[ĐANG XỬ LÝ] Đang đọc dữ liệu ảnh từ thư mục 'dataset'...")
faces, ids = getImagesAndLabels('dataset')

if len(faces) == 0:
    print("[LỖI] Không tìm thấy dữ liệu khuôn mặt hợp lệ trong thư mục 'dataset'. Vui lòng kiểm tra lại ảnh.")
else:
    print(f"[OK] Đã đọc được {len(faces)} vùng khuôn mặt hợp lệ. Bắt đầu train AI...")
    
    # 2. Tiến hành huấn luyện mô hình với các khuôn mặt và ID tương ứng
    recognizer.train(faces, np.array(ids))

    # 3. Tạo thư mục 'trainer' để lưu mô hình nếu chưa có
    if not os.path.exists('trainer'):
        os.makedirs('trainer')

    # Lưu mô hình đã train thành file trainer.yml
    recognizer.write('trainer/trainer.yml')

    print(f"\n[THÀNH CÔNG] AI đã học xong! Mô hình được lưu tại: 'trainer/trainer.yml'")
    print(f"Số lượng khuôn mặt đã được phân tích: {len(np.unique(ids))}")