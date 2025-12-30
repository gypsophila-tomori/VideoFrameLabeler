"""
视频列表组件 - 显示和管理视频文件列表
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QLineEdit
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

import os


class VideoListWidget(QWidget):
    """视频列表组件"""
    
    # 信号：当选择视频时发出
    video_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_dir = "./video"
        self.processed_videos = set()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("视频列表")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索视频...")
        self.search_input.textChanged.connect(self.filter_videos)
        layout.addWidget(self.search_input)
        
        # 视频列表
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e5f3ff;
            }
        """)
        layout.addWidget(self.list_widget)
        
        # 统计信息
        self.stats_label = QLabel("共 0 个视频")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)
        
        # 初始加载
        self.load_videos(self.video_dir)
        
    def load_videos(self, directory):
        """加载指定目录下的视频文件"""
        self.video_dir = directory
        self.list_widget.clear()
        self.video_files = []
        
        if not os.path.exists(directory):
            return
            
        # 支持的视频格式
        video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv')
        
        for filename in sorted(os.listdir(directory)):
            if filename.lower().endswith(video_extensions):
                filepath = os.path.join(directory, filename)
                self.video_files.append((filename, filepath))
                
                item = QListWidgetItem(filename)
                item.setData(Qt.ItemDataRole.UserRole, filepath)
                
                # 如果已处理，添加标记
                if filepath in self.processed_videos:
                    item.setText(f"✓ {filename}")
                    item.setForeground(QColor("#28a745"))
                    
                self.list_widget.addItem(item)
                
        self.update_stats()
        
    def filter_videos(self, text):
        """根据搜索文本过滤视频"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())
            
    def on_item_clicked(self, item):
        """处理点击事件"""
        video_path = item.data(Qt.ItemDataRole.UserRole)
        self.video_selected.emit(video_path)
        
    def mark_as_processed(self, video_path):
        """标记视频为已处理"""
        self.processed_videos.add(video_path)
        
        # 更新列表显示
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == video_path:
                filename = os.path.basename(video_path)
                if not item.text().startswith("✓"):
                    item.setText(f"✓ {filename}")
                    item.setForeground(QColor("#28a745"))
                break
                
        self.update_stats()
        
    def update_stats(self):
        """更新统计信息"""
        total = self.list_widget.count()
        processed = len(self.processed_videos)
        self.stats_label.setText(f"共 {total} 个视频，已处理 {processed} 个")
