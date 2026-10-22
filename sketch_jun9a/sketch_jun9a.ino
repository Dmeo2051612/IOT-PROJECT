#include <WebServer.h>
#include "esp_camera.h"

#include <WiFi.h>

#include <WiFiClient.h>



// ==========================================

// THIẾT LẬP MẠNG & SERVER (BẠN CẦN SỬA Ở ĐÂY)

// ==========================================

const char* ssid = "iPhone"; // Tên WiFi nhà bạn

const char* password = "123455679zz"; // Mật khẩu WiFi  



const char* serverIP = "172.20.10.2"; // Điền IPv4 của Laptop chạy Flask

int serverPort = 5000; // Cổng Flask Server

String serverPath = "/api/esp32/recognize";
WebServer webServer(80);


// ==========================================
        
// CẤU HÌNH CHÂN KẾT NỐI NGOẠI VI

// ==========================================

#define BUTTON_PIN 0 // Chân nối nút nhấn (Có thể dùng chân Boot/IO0 trên mạch)

#define RELAY_PIN 1 // Chân nối module Relay (Sửa lại số chân theo mạch thực tế của bạn)



// ==========================================

// CẤU HÌNH CHÂN CAMERA CHO ESP32-S3 WROOM

// ==========================================

#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1

#define XCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM      4
#define SIOC_GPIO_NUM      5

#define Y9_GPIO_NUM       16
#define Y8_GPIO_NUM       17
#define Y7_GPIO_NUM       18
#define Y6_GPIO_NUM       12
#define Y5_GPIO_NUM       10
#define Y4_GPIO_NUM        8
#define Y3_GPIO_NUM        9
#define Y2_GPIO_NUM       11

#define VSYNC_GPIO_NUM     6
#define HREF_GPIO_NUM      7
#define PCLK_GPIO_NUM     13

void handleStream() {

    WiFiClient client = webServer.client();

    String response =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";

    client.print(response);

    while (client.connected()) {
        camera_fb_t * fb = esp_camera_fb_get();
        if (!fb) continue;

        client.printf("--frame\r\n");
        client.printf("Content-Type: image/jpeg\r\n");
        client.printf("Content-Length: %u\r\n\r\n", fb->len);
        client.write(fb->buf, fb->len);
        client.printf("\r\n");
        
        client.flush(); // THÊM DÒNG NÀY: Ép đẩy ngay dữ liệu đi, dọn sạch bộ nhớ đệm mạng

        esp_camera_fb_return(fb);
        delay(80); // Tăng delay lên một chút (80ms ~ khoảng 12 FPS) để WiFi có thời gian thở
    }
}

void setup() {

Serial.begin(115200);


pinMode(BUTTON_PIN, INPUT_PULLUP);

pinMode(RELAY_PIN, OUTPUT);

digitalWrite(RELAY_PIN, LOW); // Trạng thái ban đầu: Khóa cửa



// Kết nối WiFi

Serial.print("Dang ket noi WiFi...");

WiFi.begin(ssid, password);

while (WiFi.status() != WL_CONNECTED) {

delay(500);

Serial.print(".");

}

Serial.println("\nWiFi da ket noi!");

Serial.print("IP ESP32: ");
Serial.println(WiFi.localIP());

// Khởi tạo Camera

camera_config_t config;

config.ledc_channel = LEDC_CHANNEL_0;

config.ledc_timer = LEDC_TIMER_0;

config.pin_d0 = Y2_GPIO_NUM;

config.pin_d1 = Y3_GPIO_NUM;

config.pin_d2 = Y4_GPIO_NUM;

config.pin_d3 = Y5_GPIO_NUM;

config.pin_d4 = Y6_GPIO_NUM;

config.pin_d5 = Y7_GPIO_NUM;

config.pin_d6 = Y8_GPIO_NUM;

config.pin_d7 = Y9_GPIO_NUM;

config.pin_xclk = XCLK_GPIO_NUM;

config.pin_pclk = PCLK_GPIO_NUM;

config.pin_vsync = VSYNC_GPIO_NUM;

config.pin_href = HREF_GPIO_NUM;

config.pin_sscb_sda = SIOD_GPIO_NUM;

config.pin_sscb_scl = SIOC_GPIO_NUM;

config.pin_pwdn = PWDN_GPIO_NUM;

config.pin_reset = RESET_GPIO_NUM;

config.xclk_freq_hz = 20000000;

config.pixel_format = PIXFORMAT_JPEG;


// KIỂM TRA VÀ CẤU HÌNH RAM THÔNG MINH

if (psramFound()) {

Serial.println("[INFO] Tuyet voi! PSRAM hoat dong OK. Chay cau hinh VGA.");

config.frame_size = FRAMESIZE_QVGA;

config.jpeg_quality = 15;

config.fb_count = 2;

config.fb_location = CAMERA_FB_IN_PSRAM; // Bắt buộc cho S3 có PSRAM

} else {

Serial.println("[CANH BAO] Khong tim thay PSRAM! Ep giam xuong QVGA cho nhe.");

config.frame_size = FRAMESIZE_QVGA; // Thu nhỏ ảnh xuống 320x240

config.jpeg_quality = 12;

config.fb_count = 1;

config.fb_location = CAMERA_FB_IN_DRAM; // Bắt buộc dùng RAM nội bộ

}



esp_err_t err = esp_camera_init(&config);

if (err != ESP_OK) {

Serial.printf("Loi khoi tao camera: 0x%x\n", err);

return;

}

Serial.println("Khoe man hinh Camera OK! San sang hoat dong.");

webServer.on("/stream", HTTP_GET, handleStream);

webServer.begin();

Serial.print("Video Stream URL: http://");
Serial.print(WiFi.localIP());
Serial.println("/stream");
}



void loop() {

// Nhấn nút (mức LOW) để chụp ảnh và gửi lên Server
webServer.handleClient();

if (digitalRead(BUTTON_PIN) == LOW) {

delay(50);

if (digitalRead(BUTTON_PIN) == LOW) {

Serial.println("\n[INFO] Phat hien nguoi dung bam nut, dang chup anh...");

captureAndSend();

delay(3000); // Tránh tình trạng nhận diện đúp liên tục

}

}

}



void captureAndSend() {

camera_fb_t * fb = NULL;

fb = esp_camera_fb_get();


if (!fb) {

Serial.println("Loi: Khong the lay khung hinh tu camera!");

return;

}



WiFiClient client;

if (client.connect(serverIP, serverPort)) {

Serial.println("Da ket noi Flask Server. Dang truyen luon anh...");


String head = "--ESP32Boundary\r\nContent-Disposition: form-data; name=\"imageFile\"; filename=\"face.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";

String tail = "\r\n--ESP32Boundary--\r\n";



uint32_t imageLen = fb->len;

uint32_t totalLen = head.length() + imageLen + tail.length();



client.println(String("POST ") + serverPath + " HTTP/1.1");

client.println("Host: " + String(serverIP));

client.println("Content-Length: " + String(totalLen));

client.println("Content-Type: multipart/form-data; boundary=ESP32Boundary");

client.println();

client.print(head);



uint8_t *fbBuf = fb->buf;

size_t fbLen = fb->len;

for (size_t n=0; n<fbLen; n=n+1024) {

if (n+1024 < fbLen) {

client.write(fbBuf, 1024);

fbBuf += 1024;

}

else if (fbLen%1024>0) {

size_t remainder = fbLen%1024;

client.write(fbBuf, remainder);

}

}

client.print(tail);



String response = "";

long timeout = millis();

while (client.connected() && millis() - timeout < 5000) {

while (client.available()) {

char c = client.read();

response += c;

timeout = millis();

}

}


Serial.println("Server tra ve ket qua: ");

Serial.println(response);



// Mở khóa rơ-le nếu nhận diện thành công

if (response.indexOf("\"match\":true") > 0 || response.indexOf("\"match\": true") > 0) {

Serial.println("[ACTION] Khuon mặt khop -> KICH HOAT RELAY MO CUA!");

digitalWrite(RELAY_PIN, HIGH);

delay(3000);

digitalWrite(RELAY_PIN, LOW);

} else {

Serial.println("[ACTION] Nguoi la hoac khong nhan dien duoc -> TU CHOI.");

}

} else {

Serial.println("Loi: Khong the ket noi Server Python. Kiem tra lai dia chi IP!");

}



esp_camera_fb_return(fb);

client.stop();

}