import os,sys
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from gtts import gTTS
import mutagen
import server,requests

# Đường dẫn đến ChromeDriver
CHROMEDRIVER_PATH = 'chromedriver'  # Thay đổi đường dẫn này nếu cần

# Hàm chụp màn hình bài đăng phổ biến trên Reddit
def capture_reddit_posts():
    print("Bắt đầu chụp màn hình Reddit...")
    
    # Cấu hình các tùy chọn cho Chrome
    options = Options()
    options.add_argument("--headless")  # Chạy trong chế độ headless
    options.add_argument("--no-sandbox")  # Vô hiệu hóa sandbox
    options.add_argument("--disable-dev-shm-usage")  # Khắc phục vấn đề với shared memory

    # Khởi động ChromeDriver
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    driver.get('https://www.reddit.com/r/all/new')  # Truy cập Reddit
    time.sleep(5)  # Đợi trang tải hoàn toàn

    # Lặp để lấy các bài đăng mới
    for index in range(2):  # Giới hạn chỉ lấy 2 bài đăng
        # Lấy các bài đăng
        posts = driver.find_elements(By.CSS_SELECTOR, 'article.w-full.m-0')

        if len(posts) > index:
            post = posts[index]

            # Cuộn tới bài đăng
            driver.execute_script("arguments[0].scrollIntoView();", post)
            time.sleep(1)  # Đợi một chút để đảm bảo bài đăng hiển thị

            # Chụp ảnh bài đăng
            post_image_path = f'reddit_post_{index}.png'
            post.screenshot(post_image_path)
            print(f"Đã chụp màn hình bài đăng {index + 1}: {post_image_path}")

            # Lấy tiêu đề bài đăng
            title_link = post.find_element(By.CSS_SELECTOR, 'a.absolute.inset-0')
            title_text = title_link.text
            
            # Tạo file âm thanh từ tiêu đề
            audio_file_path = f'reddit_post_audio_{index}.mp3'
            tts = gTTS(text=title_text, lang='en')  # Sử dụng tiếng Anh
            tts.save(audio_file_path)
            print(f"Đã tạo âm thanh cho bài đăng {index + 1}: {audio_file_path}")

            # Lấy độ dài âm thanh
            audio_length = get_audio_length(audio_file_path)
            print(f"Độ dài âm thanh bài đăng {index + 1}: {audio_length} giây")

            # Khởi động FFmpeg để phát trực tiếp với bài đăng này
            start_stream_to_youtube(audio_file_path, post_image_path, title_text, audio_length)

    driver.quit()

# Hàm để lấy độ dài âm thanh
def get_audio_length(file_path):
    audio = mutagen.File(file_path)
    return audio.info.length  # Trả về độ dài âm thanh tính bằng giây

# Hàm sử dụng FFmpeg để phát trực tiếp lên YouTube
def start_stream_to_youtube(audio_file, image_file, subtitle, duration):
    stream_key = 'pmfq-5pc5-u1e8-5s1p-caqf'  # Khóa stream YouTube

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
        '-stream_loop', '-1',
        '-i', audio_file,
        '-loop', '1',
        '-i', image_file,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-vf', f"{subtitle_filter}",
        '-pix_fmt', 'yuv420p',
        '-t', str(duration),
        '-f', 'flv',
        f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'
    ]

    print("Khởi động FFmpeg để phát trực tiếp...")
    subprocess.Popen(ffmpeg_command)

# Hàm chính
try:
    req=requests.get('http://localhost:8888')
    print(req.status_code)
    print('Client closed')
    sys.exit()
except Exception as e:
    print(e)
    server.b()
    capture_reddit_posts()  # Chụp ảnh các bài đăng Reddit
