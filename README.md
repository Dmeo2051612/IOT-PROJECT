# Dự án IoT - Hệ thống Nhận diện và Xử lý Ảnh với ESP32

Dự án này là một hệ thống IoT tích hợp Trí tuệ Nhân tạo (AI), cho phép thu thập hình ảnh từ module camera (ESP32), huấn luyện mô hình nhận diện, và cung cấp giao diện Web/API để giám sát hệ thống theo thời gian thực. Cấu trúc lưu trữ dữ liệu được đồng bộ qua Firebase.

## Cấu trúc Dự án

Hệ thống được chia thành các module độc lập theo luồng xử lý dữ liệu:

*   `1_thu_thap_anh.py`: Script kết nối camera (ESP32) để chụp và thu thập dữ liệu ảnh mẫu.
*   `2_huan_luyen_ai.py`: Tiền xử lý dữ liệu và huấn luyện mô hình AI.
*   `3_nhan_dien.py`: Script chạy trực tiếp mô hình để nhận diện đối tượng từ luồng camera.
*   `4_api_server.py`: Khởi tạo RESTful API để giao tiếp với các thiết bị client.
*   `server_web.py`: Khởi tạo Web Server cung cấp giao diện người dùng (UI) giám sát.
*   `5_test_client.py`: Script dùng để test các endpoint của API Server.

## Yêu cầu Hệ thống (Prerequisites)

*   **Python:** 3.8 trở lên.
*   **Thư viện cơ bản:** OpenCV, Flask/FastAPI, Firebase Admin SDK, Numpy (Cài đặt qua `pip install -r requirements.txt` nếu có).
*   **Môi trường:** Đã cài đặt và cấu hình ngrok (nếu cần public local server ra ngoài Internet).

## Hướng dẫn Cài đặt

**1. Clone dự án về máy:**
```bash
git clone [https://github.com/Dmeo2051612/IOT-PROJECT.git](https://github.com/Dmeo2051612/IOT-PROJECT.git)
cd IOT-PROJECT

Link tải file model (trainer.yml): https://drive.google.com/file/d/1uhCEj2KDjiE_kg6I_YgNOPuZoZa5_bGb/view?usp=sharing