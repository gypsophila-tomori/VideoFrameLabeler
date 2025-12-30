"""
视频播放器组件 - 视频播放和控制
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QComboBox, QStyle
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QKeyEvent

import cv2
import numpy as np


class VideoPlayer(QWidget):
    """视频播放器组件"""
    
    # 信号：发送帧到标注区
    frame_sent = pyqtSignal(np.ndarray, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.cap = None
        self.current_frame = None
        self.current_frame_number = 0
        self.total_frames = 0
        self.fps = 30
        self.is_playing = False
        self.playback_speed = 1.0
        
        self.setup_ui()
        self.setup_timer()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("视频播放器")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 视频显示区域
        self.display_label = QLabel()
        self.display_label.setMinimumSize(480, 360)
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #333;"
        )
        self.display_label.setText("请选择视频文件")
        layout.addWidget(self.display_label, 1)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setEnabled(False)
        self.progress_slider.sliderMoved.connect(self.seek_frame)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        layout.addWidget(self.progress_slider)
        
        # 帧信息
        self.frame_info_label = QLabel("0 / 0")
        self.frame_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.frame_info_label)
        
        # 控制按钮行1
        control_layout1 = QHBoxLayout()
        
        self.prev_frame_btn = QPushButton("◀◀ 上一帧")
        self.prev_frame_btn.clicked.connect(self.prev_frame)
        self.prev_frame_btn.setEnabled(False)
        control_layout1.addWidget(self.prev_frame_btn)
        
        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.clicked.connect(self.toggle_play)
        self.play_btn.setEnabled(False)
        control_layout1.addWidget(self.play_btn)
        
        self.next_frame_btn = QPushButton("下一帧 ▶▶")
        self.next_frame_btn.clicked.connect(self.next_frame)
        self.next_frame_btn.setEnabled(False)
        control_layout1.addWidget(self.next_frame_btn)
        
        layout.addLayout(control_layout1)
        
        # 控制按钮行2
        control_layout2 = QHBoxLayout()
        
        self.back_5s_btn = QPushButton("⏪ 后退5秒")
        self.back_5s_btn.clicked.connect(lambda: self.skip_seconds(-5))
        self.back_5s_btn.setEnabled(False)
        control_layout2.addWidget(self.back_5s_btn)
        
        # 播放速度选择
        speed_label = QLabel("速度:")
        control_layout2.addWidget(speed_label)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1.0x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentIndex(2)  # 默认1.0x
        self.speed_combo.currentTextChanged.connect(self.change_speed)
        control_layout2.addWidget(self.speed_combo)
        
        self.forward_5s_btn = QPushButton("快进5秒 ⏩")
        self.forward_5s_btn.clicked.connect(lambda: self.skip_seconds(5))
        self.forward_5s_btn.setEnabled(False)
        control_layout2.addWidget(self.forward_5s_btn)
        
        layout.addLayout(control_layout2)
        
        # 发送到标注区按钮
        self.send_btn = QPushButton("📤 发送当前帧到标注区 (Enter)")
        self.send_btn.clicked.connect(self.send_frame)
        self.send_btn.setEnabled(False)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        layout.addWidget(self.send_btn)
        
        # 设置焦点策略以接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def setup_timer(self):
        """设置播放定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_next_frame)
        
    def load_video(self, video_path):
        """加载视频文件"""
        self.stop()
        
        if self.cap is not None:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            self.display_label.setText("无法打开视频文件")
            return
            
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.current_frame_number = 0
        
        # 更新UI
        self.progress_slider.setEnabled(True)
        self.progress_slider.setMaximum(self.total_frames - 1)
        self.progress_slider.setValue(0)
        
        self.play_btn.setEnabled(True)
        self.prev_frame_btn.setEnabled(True)
        self.next_frame_btn.setEnabled(True)
        self.back_5s_btn.setEnabled(True)
        self.forward_5s_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        
        # 读取第一帧
        self.read_frame(0)
        
    def read_frame(self, frame_number):
        """读取指定帧"""
        if self.cap is None:
            return
            
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if ret:
            self.current_frame = frame
            self.current_frame_number = frame_number
            self.display_frame(frame)
            self.update_frame_info()
            
    def read_next_frame(self):
        """读取下一帧（播放时调用）"""
        if self.cap is None:
            return
            
        ret, frame = self.cap.read()
        
        if ret:
            self.current_frame = frame
            self.current_frame_number = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            self.display_frame(frame)
            self.update_frame_info()
            
            # 更新进度条（不触发seek）
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(self.current_frame_number)
            self.progress_slider.blockSignals(False)
        else:
            # 视频结束
            self.stop()
            
    def display_frame(self, frame):
        """在标签上显示帧"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        q_image = QImage(
            rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        )
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.display_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.display_label.setPixmap(scaled_pixmap)
        
    def update_frame_info(self):
        """更新帧信息显示"""
        time_current = self.current_frame_number / self.fps
        time_total = self.total_frames / self.fps
        
        self.frame_info_label.setText(
            f"帧: {self.current_frame_number + 1} / {self.total_frames}  |  "
            f"时间: {time_current:.1f}s / {time_total:.1f}s"
        )
        
    def toggle_play(self):
        """切换播放/暂停"""
        if self.is_playing:
            self.stop()
        else:
            self.play()
            
    def play(self):
        """开始播放"""
        if self.cap is None:
            return
            
        self.is_playing = True
        self.play_btn.setText("⏸ 暂停")
        
        # 根据播放速度计算定时器间隔
        interval = int(1000 / (self.fps * self.playback_speed))
        self.timer.start(interval)
        
    def stop(self):
        """停止播放"""
        self.is_playing = False
        self.play_btn.setText("▶ 播放")
        self.timer.stop()
        
    def prev_frame(self):
        """上一帧"""
        self.stop()
        self.read_frame(self.current_frame_number - 1)
        self.progress_slider.setValue(self.current_frame_number)
        
    def next_frame(self):
        """下一帧"""
        self.stop()
        self.read_frame(self.current_frame_number + 1)
        self.progress_slider.setValue(self.current_frame_number)
        
    def skip_seconds(self, seconds):
        """跳过指定秒数"""
        self.stop()
        frames_to_skip = int(seconds * self.fps)
        new_frame = self.current_frame_number + frames_to_skip
        self.read_frame(new_frame)
        self.progress_slider.setValue(self.current_frame_number)
        
    def seek_frame(self, value):
        """跳转到指定帧"""
        self.read_frame(value)
        
    def on_slider_pressed(self):
        """进度条按下时暂停播放"""
        if self.is_playing:
            self.timer.stop()
            
    def on_slider_released(self):
        """进度条释放时恢复播放"""
        if self.is_playing:
            interval = int(1000 / (self.fps * self.playback_speed))
            self.timer.start(interval)
            
    def change_speed(self, speed_text):
        """改变播放速度"""
        self.playback_speed = float(speed_text.replace('x', ''))
        
        if self.is_playing:
            interval = int(1000 / (self.fps * self.playback_speed))
            self.timer.setInterval(interval)
            
    def send_frame(self):
        """发送当前帧到标注区"""
        if self.current_frame is not None:
            self.frame_sent.emit(self.current_frame.copy(), self.current_frame_number)
            
    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘事件"""
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key.Key_Space:
            self.toggle_play()
        elif key == Qt.Key.Key_Left:
            self.prev_frame()
        elif key == Qt.Key.Key_Right:
            self.next_frame()
        elif key == Qt.Key.Key_Up:
            self.skip_seconds(5)
        elif key == Qt.Key.Key_Down:
            self.skip_seconds(-5)
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.send_frame()
        else:
            super().keyPressEvent(event)
            
    def resizeEvent(self, event):
        """窗口大小改变时重新显示帧"""
        super().resizeEvent(event)
        if self.current_frame is not None:
            self.display_frame(self.current_frame)
