import requests
import os

# 1. Địa chỉ của API Server (Do chạy trên cùng một máy tính nên dùng localhost)
URL = 'http://localhost:5000/upload'

# 2. Chọn một tấm ảnh bất kỳ trong thư mục dataset để gửi đi thử
# Giả sử chúng ta lấy tấm ảnh đầu tiên của bạn
image_path = input('Nhập tên ảnh(.jpg): ')

if not os.path.exists(image_path):
    print(f"[LỖI] Không tìm thấy ảnh tại: {image_path}. Vui lòng sửa lại tên file cho đúng.")
else:
    print(f"[CLIENT] Đang đóng gói và gửi ảnh '{image_path}' lên Server...")
    
    # 3. Mở file ảnh dưới dạng nhị phân (để mô phỏng luồng byte mà ESP32 sẽ gửi)
    with open(image_path, 'rb') as img_file:
        # Key 'imageFile' bắt buộc phải khớp với key mà file 4_api_server.py đang chờ
        files = {'imageFile': img_file}
        
        try:
            # 4. Gửi ảnh đi bằng phương thức POST
            response = requests.post(URL, files=files)
            
            # 5. In kết quả phản hồi từ Server ra màn hình
            print("========================================")
            print(f"Mã trạng thái HTTP : {response.status_code} (200 là Thành công)")
            print(f"Kết quả phân tích  : {response.json()}")
            print("========================================")
            
        except requests.exceptions.ConnectionError:
            print("[LỖI] Không thể kết nối đến Server")