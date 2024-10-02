import os
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from gtts import gTTS
import mutagen  # Để xác định độ dài âm thanh

# Cài đặt Chrome Driver
chrome_options = Options()
chrome_options.add_argument("--headless")  # Chạy trình duyệt ở chế độ không hiển thị
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
service = Service('chromedriver')  # Thay đổi đường dẫn đến chromedriver

# Hàm chụp màn hình bài đăng phổ biến trên Reddit
def capture_reddit_posts():
    print("Bắt đầu chụp màn hình Reddit...")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Truy cập Reddit
    driver.get('https://www.reddit.com/r/all/new')  # Sử dụng 'new' để lấy bài đăng mới nhất
    time.sleep(5)  # Đợi để trang tải hoàn toàn

    # Lặp để lấy các bài đăng
    while True:
        posts = driver.find_elements(By.CSS_SELECTOR, 'article.w-full.m-0')

        # Lặp qua tối đa 2 bài đăng đầu tiên
        for index, post in enumerate(posts[:2]):  # Giới hạn chỉ lấy 2 bài đăng
            # Cuộn tới bài đăng
            ActionChains(driver).move_to_element(post).perform()
            time.sleep(1)  # Đợi một chút để đảm bảo bài đăng hiển thị

            # Lấy vị trí của bài đăng và chụp ảnh
            post_image_path = f'reddit_post_{index}.png'
            post.screenshot(post_image_path)
            print(f"Đã chụp màn hình bài đăng {index + 1}: {post_image_path}")

            # Lấy tiêu đề bài đăng để chuyển đổi thành giọng nói
            title_link = post.find_element(By.CSS_SELECTOR, 'a.absolute.inset-0')  # Cập nhật selector
            title_text = title_link.text

            # Tạo file âm thanh từ tiêu đề
            audio_file_path = f'reddit_post_audio_{index}.mp3'
            tts = gTTS(text=title_text, lang='en')  # Sử dụng tiếng Anh
            tts.save(audio_file_path)  # Ghi âm thanh vào file tạm thời
            print(f"Đã tạo âm thanh cho bài đăng {index + 1}: {audio_file_path}")

            # Lấy độ dài âm thanh
            audio_length = get_audio_length(audio_file_path)
            print(f"Độ dài âm thanh bài đăng {index + 1}: {audio_length} giây")

            # Khởi động FFmpeg để phát trực tiếp với bài đăng này
            start_stream_to_youtube(audio_file_path, post_image_path, title_text, audio_length)

        time.sleep(60)  # Đợi 60 giây trước khi lấy bài đăng mới
        driver.get('https://www.reddit.com/r/all/new')  # Tải lại trang mới

    driver.quit()

# Hàm để lấy độ dài âm thanh
def get_audio_length(file_path):
    audio = mutagen.File(file_path)
    return audio.info.length  # Trả về độ dài âm thanh tính bằng giây

# Hàm sử dụng FFmpeg để phát trực tiếp lên YouTube
def start_stream_to_youtube(audio_file, image_file, subtitle, duration):
    stream_key = "pmfq-5pc5-u1e8-5s1p-caqf"  # Khóa stream YouTube

    # Tách từng từ trong tiêu đề và tạo thời gian cho mỗi từ
    words = subtitle.split()
    time_per_word = duration / len(words) if words else 0  # Tính thời gian cho mỗi từ
    subtitle_filter = ','.join(
        [f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{word}':fontcolor=white:fontsize=32:box=1:boxcolor=gray@0.5:x=(W-w)/2:y=H-th-20:enable='between(t,{i * time_per_word},{(i + 1) * time_per_word})',"
         f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{word}':fontcolor=yellow:fontsize=32:box=1:boxcolor=gray@0.5:x=(W-w)/2:y=H-th-20:enable='between(t,{i * time_per_word},{(i + 1) * time_per_word})*gt(t,{(i + 1) * time_per_word - 0.5})'" 
         for i, word in enumerate(words)]
    )

    # Lệnh khởi động FFmpeg để phát trực tiếp
    ffmpeg_command = [
        'ffmpeg',
        '-stream_loop', '-1',  # Giữ âm thanh ở chế độ lặp
        '-i', audio_file,  # Âm thanh
        '-loop', '1',  # Giữ ảnh ở chế độ lặp
        '-i', image_file,  # Ảnh bài đăng
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-vf', f"{subtitle_filter}",  # Thêm phụ đề
        '-pix_fmt', 'yuv420p',
        '-t', str(duration),  # Thời gian phát là độ dài âm thanh
        '-f', 'flv',  # Định dạng đầu ra là FLV để phát trực tiếp
        f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'  # Địa chỉ RTMP của YouTube kèm stream key
    ]

    print("Khởi động FFmpeg để phát trực tiếp...")
    # Chạy FFmpeg để phát trực tiếp
    subprocess.Popen(ffmpeg_command)

# Hàm chính để vừa chụp màn hình vừa phát trực tiếp
if __name__ == "__main__":
    capture_reddit_posts()  # Chụp ảnh các bài đăng Reddit
