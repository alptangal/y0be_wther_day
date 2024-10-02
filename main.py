import asyncio
import os
import subprocess
from playwright.async_api import async_playwright
from gtts import gTTS
import mutagen  # Để xác định độ dài âm thanh

if not os.path.exists('/home/appuser/.cache/ms-playwright'):
    subprocess.run(['bash', 'install_playwright.sh'])
# Hàm chụp màn hình bài đăng phổ biến trên Reddit
async def capture_reddit_posts():
    print("Bắt đầu chụp màn hình Reddit...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Chạy Chromium với giao diện
        context = await browser.new_context()
        page = await context.new_page()

        # Truy cập Reddit
        await page.goto('https://www.reddit.com/r/all/new')  # Sử dụng 'new' để lấy bài đăng mới nhất
        await page.wait_for_timeout(5000)  # Đợi để trang tải hoàn toàn

        # Lặp vô hạn để liên tục lấy các bài đăng mới
        while True:
            posts = await page.query_selector_all('article.w-full.m-0')

            # Lặp qua tối đa 2 bài đăng đầu tiên
            for index, post in enumerate(posts[:2]):  # Giới hạn chỉ lấy 2 bài đăng
                # Cuộn tới bài đăng
                await post.scroll_into_view_if_needed()
                await asyncio.sleep(1)  # Đợi một chút để đảm bảo bài đăng hiển thị

                # Lấy vị trí của bài đăng và chụp ảnh
                bounding_box = await post.bounding_box()
                if bounding_box and bounding_box['width'] > 0 and bounding_box['height'] > 0:
                    post_image_path = f'reddit_post_{index}.png'
                    await page.screenshot(path=post_image_path, clip={
                        'x': int(bounding_box['x']),
                        'y': int(bounding_box['y']),
                        'width': int(bounding_box['width']),
                        'height': int(bounding_box['height'])
                    })
                    print(f"Đã chụp màn hình bài đăng {index + 1}: {post_image_path}")

                    # Lấy tiêu đề bài đăng để chuyển đổi thành giọng nói
                    title_link = await post.query_selector('a.absolute.inset-0')  # Cập nhật selector
                    if title_link:
                        title_text = await title_link.inner_text()
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

                else:
                    print(f"Bài đăng {index + 1} không có bounding box hợp lệ.")

                # Cuộn xuống để xem bài đăng tiếp theo
                await page.keyboard.press('PageDown')
                await asyncio.sleep(1)  # Đợi 1 giây trước khi cuộn

            await asyncio.sleep(60)  # Đợi 60 giây trước khi lấy bài đăng mới
            await page.goto('https://www.reddit.com/r/all/new')  # Tải lại trang mới

        await browser.close()

# Hàm để lấy độ dài âm thanh
def get_audio_length(file_path):
    audio = mutagen.File(file_path)
    return audio.info.length  # Trả về độ dài âm thanh tính bằng giây

# Hàm sử dụng FFmpeg để phát trực tiếp lên YouTube
def start_stream_to_youtube(audio_file, image_file, subtitle, duration):
    stream_key = os.environ.get('id')  # Khóa stream YouTube

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
async def main():
    await capture_reddit_posts()  # Chụp ảnh các bài đăng Reddit

if __name__ == "__main__":
    # Chạy chương trình
    asyncio.run(main())
