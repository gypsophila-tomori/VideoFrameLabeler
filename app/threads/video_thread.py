"""
视频读取线程 - 后台处理视频读取（备用，当前版本使用QTimer）
"""
from PyQt6.QtCore import QThread, pyqtSignal
import cv2
import numpy as np


class VideoReaderThread(QThread):
    """视频读取线程"""
    
    frame_ready = pyqtSignal(np.ndarray, int)  # 帧数据, 帧号
    video_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.video_path = None
        self.cap = None
        self.is_running = False
        self.is_paused = True
        self.playback_speed = 1.0
        self.seek_frame = -1
        
    def load_video(self, video_path):
        """加载视频"""
        self.video_path = video_path
        
    def run(self):
        """线程主循环"""
        if self.video_path is None:
            return
            
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            self.error_occurred.emit("无法打开视频文件")
            return
            
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.is_running = True
        
        while self.is_running:
            # 处理跳转请求
            if self.seek_frame >= 0:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.seek_frame)
                self.seek_frame = -1
                
            if not self.is_paused:
                ret, frame = self.cap.read()
                
                if ret:
                    frame_number = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                    self.frame_ready.emit(frame, frame_number)
                else:
                    self.video_finished.emit()
                    self.is_paused = True
                    
                # 控制播放速度
                delay_ms = int(1000 / (fps * self.playback_speed))
                self.msleep(delay_ms)
            else:
                self.msleep(50)  # 暂停时减少CPU占用
                
        self.cap.release()
        
    def play(self):
        """播放"""
        self.is_paused = False
        
    def pause(self):
        """暂停"""
        self.is_paused = True
        
    def seek(self, frame_number):
        """跳转到指定帧"""
        self.seek_frame = frame_number
        
    def set_speed(self, speed):
        """设置播放速度"""
        self.playback_speed = speed
        
    def stop(self):
        """停止线程"""
        self.is_running = False
        self.wait()
