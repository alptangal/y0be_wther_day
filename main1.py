import subprocess
import time
import os
from threading import Thread
from datetime import datetime

# Đường dẫn đến script tạo video của bạn
MAIN_SCRIPT_PATH = "main.py"
# Thư mục chứa video output
VIDEO_OUTPUT_DIR = "output_videos"
# YouTube stream key
YOUTUBE_KEY = os.environ.get('ytb')

def create_video():
    print("Bắt đầu tạo video...")
    result = subprocess.run(["python", MAIN_SCRIPT_PATH], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Lỗi khi tạo video: {result.stderr}")
        return None
    
    print("Video đã được tạo thành công.")
    
    # Giả sử script của bạn tạo ra file "final_video.mp4"
    if not os.path.exists("final_video.mp4"):
        print("Không tìm thấy file final_video.mp4")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_video_name = f"video_{timestamp}.mp4"
    new_video_path = os.path.join(VIDEO_OUTPUT_DIR, new_video_name)
    
    try:
        os.rename("final_video.mp4", new_video_path)
        print(f"Đã đổi tên video thành: {new_video_name}")
        return new_video_path
    except Exception as e:
        print(f"Lỗi khi đổi tên file: {e}")
        return None

def start_livestream(video_path):
    ffmpeg_command = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-i", video_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-maxrate", "3000k",
        "-bufsize", "6000k",
        "-pix_fmt", "yuv420p",
        "-g", "50",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_KEY}"
    ]
    return subprocess.Popen(ffmpeg_command)

def main():
    if not os.path.exists(VIDEO_OUTPUT_DIR):
        os.makedirs(VIDEO_OUTPUT_DIR)

    current_video = None
    stream_process = None

    while True:
        # Tạo video mới
        print("Đang tạo video mới...")
        new_video_path = create_video()

        if new_video_path and os.path.exists(new_video_path):
            print(f"Video mới đã được tạo: {new_video_path}")
            
            # Bắt đầu phát trực tiếp video mới
            new_stream_process = start_livestream(new_video_path)
            
            # Nếu có luồng stream cũ, kết thúc nó và xóa video cũ
            if stream_process:
                print("Đang kết thúc luồng stream cũ...")
                stream_process.terminate()
                stream_process.wait()
                
                if current_video and os.path.exists(current_video):
                    print(f"Đang xóa video cũ: {current_video}")
                    os.remove(current_video)
            
            # Cập nhật video và process hiện tại
            current_video = new_video_path
            stream_process = new_stream_process
            
            print("Đang bắt đầu tạo video tiếp theo...")
        else:
            print("Không tạo được video mới. Đang thử lại...")
            time.sleep(60)  # Đợi 1 phút trước khi thử lại

if __name__ == "__main__":
    main()