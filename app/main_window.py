"""
主窗口 - 负责整体布局和组件协调
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMenu, QMessageBox,
    QDialog, QLabel, QLineEdit, QPushButton, QColorDialog,
    QListWidget, QListWidgetItem, QGridLayout, QScrollArea,
    QFileDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence, QColor, QPixmap

from app.components.video_list_widget import VideoListWidget
from app.components.video_player import VideoPlayer
from app.components.annotation_widget import AnnotationWidget
from app.utils.file_utils import ConfigManager, AnnotationManager

import os


class LabelManagerDialog(QDialog):
    """标签类别管理对话框"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.labels = config_manager.get_labels().copy()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("标签类别管理")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 标签列表
        self.list_widget = QListWidget()
        self.refresh_list()
        layout.addWidget(self.list_widget)
        
        # 添加新标签区域
        add_layout = QHBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("标签名称")
        add_layout.addWidget(self.name_input)
        
        self.color_btn = QPushButton("选择颜色")
        self.color_btn.clicked.connect(self.select_color)
        self.selected_color = "#00FF00"
        self.update_color_button()
        add_layout.addWidget(self.color_btn)
        
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_label)
        add_layout.addWidget(self.add_btn)
        
        layout.addLayout(add_layout)
        
        # 删除按钮
        self.delete_btn = QPushButton("删除选中标签")
        self.delete_btn.clicked.connect(self.delete_label)
        layout.addWidget(self.delete_btn)
        
        # 确定取消按钮
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def refresh_list(self):
        self.list_widget.clear()
        for name, color in self.labels.items():
            item = QListWidgetItem(f"● {name}")
            item.setForeground(QColor(color))
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)
            
    def select_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color), self)
        if color.isValid():
            self.selected_color = color.name()
            self.update_color_button()
            
    def update_color_button(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self.selected_color}; color: white;"
        )
        
    def add_label(self):
        name = self.name_input.text().strip()
        if name and name not in self.labels:
            self.labels[name] = self.selected_color
            self.refresh_list()
            self.name_input.clear()
            
    def delete_label(self):
        current = self.list_widget.currentItem()
        if current:
            name = current.data(Qt.ItemDataRole.UserRole)
            if name in self.labels:
                del self.labels[name]
                self.refresh_list()
                
    def get_labels(self):
        return self.labels


class ReviewDialog(QDialog):
    """审阅模式对话框"""
    
    def __init__(self, annotation_manager, parent=None):
        super().__init__(parent)
        self.annotation_manager = annotation_manager
        self.setup_ui()
        self.load_images()
        
    def setup_ui(self):
        self.setWindowTitle("审阅标注结果")
        self.setMinimumSize(900, 600)
        
        layout = QHBoxLayout(self)
        
        # 左侧缩略图列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setIconSize(QSize(150, 150))
        self.thumbnail_list.setSpacing(5)
        self.thumbnail_list.currentItemChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.thumbnail_list)
        
        self.delete_btn = QPushButton("删除选中标注")
        self.delete_btn.clicked.connect(self.delete_selected)
        left_layout.addWidget(self.delete_btn)
        
        layout.addWidget(left_panel, 1)
        
        # 右侧预览区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.preview_label = QLabel("选择一张图片进行预览")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(500, 400)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background: #f0f0f0;")
        right_layout.addWidget(self.preview_label)
        
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        right_layout.addWidget(self.info_label)
        
        layout.addWidget(right_panel, 2)
        
    def load_images(self):
        reference_dir = "saved_images/Reference"
        if not os.path.exists(reference_dir):
            return
            
        for filename in sorted(os.listdir(reference_dir)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                filepath = os.path.join(reference_dir, filename)
                pixmap = QPixmap(filepath)
                if not pixmap.isNull():
                    item = QListWidgetItem()
                    item.setIcon(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))
                    item.setText(filename)
                    item.setData(Qt.ItemDataRole.UserRole, filepath)
                    self.thumbnail_list.addItem(item)
                    
    def on_selection_changed(self, current, previous):
        if current:
            filepath = current.data(Qt.ItemDataRole.UserRole)
            pixmap = QPixmap(filepath)
            scaled = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
            
            # 显示元数据
            filename = os.path.basename(filepath)
            base_name = os.path.splitext(filename)[0]
            annotations = self.annotation_manager.load_annotations()
            
            info_text = f"文件名: {filename}\n"
            if base_name in annotations:
                data = annotations[base_name]
                info_text += f"来源视频: {data.get('source_video', 'N/A')}\n"
                info_text += f"帧号: {data.get('frame_number', 'N/A')}\n"
                info_text += f"注释: {data.get('comment', '无')}\n"
                info_text += f"标记点数: {len(data.get('points', []))}"
            self.info_label.setText(info_text)
            
    def delete_selected(self):
        current = self.thumbnail_list.currentItem()
        if not current:
            return
            
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个标注吗？这将同时删除原始图和参考图。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            filepath = current.data(Qt.ItemDataRole.UserRole)
            filename = os.path.basename(filepath)
            base_name = os.path.splitext(filename)[0]
            
            # 删除文件
            ref_path = filepath
            ann_path = os.path.join("saved_images/Annotation", filename)
            
            if os.path.exists(ref_path):
                os.remove(ref_path)
            if os.path.exists(ann_path):
                os.remove(ann_path)
                
            # 从元数据中删除
            self.annotation_manager.delete_annotation(base_name)
            
            # 从列表中移除
            row = self.thumbnail_list.row(current)
            self.thumbnail_list.takeItem(row)
            
            self.preview_label.clear()
            self.preview_label.setText("选择一张图片进行预览")
            self.info_label.clear()


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化配置和标注管理器
        self.config_manager = ConfigManager()
        self.annotation_manager = AnnotationManager()
        
        self.setup_ui()
        self.setup_menu()
        self.setup_shortcuts()
        self.connect_signals()
        
        # 加载配置
        self.load_config()
        
    def setup_ui(self):
        self.setWindowTitle("苹果疏果辅助标注工具")
        self.setMinimumSize(1400, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局使用QSplitter实现可调节的三栏布局
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左栏：视频列表
        self.video_list = VideoListWidget()
        splitter.addWidget(self.video_list)
        
        # 中栏：视频播放器
        self.video_player = VideoPlayer()
        splitter.addWidget(self.video_player)
        
        # 右栏：标注区域
        self.annotation_widget = AnnotationWidget(self.config_manager)
        splitter.addWidget(self.annotation_widget)
        
        # 设置初始比例
        splitter.setSizes([200, 500, 500])
        
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 请从左侧选择视频文件")
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        open_folder_action = QAction("打开视频文件夹(&O)", self)
        open_folder_action.triggered.connect(self.open_video_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        
        label_manager_action = QAction("标签类别管理(&L)", self)
        label_manager_action.triggered.connect(self.open_label_manager)
        tools_menu.addAction(label_manager_action)
        
        review_action = QAction("审阅标注结果(&R)", self)
        review_action.triggered.connect(self.open_review_dialog)
        tools_menu.addAction(review_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        shortcuts_action = QAction("快捷键说明(&K)", self)
        shortcuts_action.triggered.connect(self.show_shortcuts_help)
        help_menu.addAction(shortcuts_action)
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_shortcuts(self):
        """设置全局快捷键"""
        # 这些快捷键会在video_player中处理
        pass
        
    def connect_signals(self):
        """连接各组件间的信号"""
        # 视频列表选择 -> 加载视频
        self.video_list.video_selected.connect(self.on_video_selected)
        
        # 视频播放器发送帧 -> 标注区域
        self.video_player.frame_sent.connect(self.on_frame_sent)
        
        # 标注保存信号
        self.annotation_widget.save_requested.connect(self.on_save_requested)
        
    def load_config(self):
        """加载配置"""
        config = self.config_manager.load_config()
        
        # 恢复上次的视频目录
        last_dir = config.get('last_video_dir', './video')
        if os.path.exists(last_dir):
            self.video_list.load_videos(last_dir)
            
        # 更新标注组件的标签
        self.annotation_widget.update_labels(self.config_manager.get_labels())
        
    def open_video_folder(self):
        """打开视频文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择视频文件夹", "./video"
        )
        if folder:
            self.video_list.load_videos(folder)
            self.config_manager.set_last_video_dir(folder)
            
    def open_label_manager(self):
        """打开标签管理对话框"""
        dialog = LabelManagerDialog(self.config_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_labels = dialog.get_labels()
            self.config_manager.set_labels(new_labels)
            self.annotation_widget.update_labels(new_labels)
            self.status_bar.showMessage("标签类别已更新")
            
    def open_review_dialog(self):
        """打开审阅对话框"""
        dialog = ReviewDialog(self.annotation_manager, self)
        dialog.exec()
        
    def show_shortcuts_help(self):
        """显示快捷键帮助"""
        help_text = """
        快捷键说明：
        
        【视频控制】
        空格键        播放/暂停
        左方向键(←)   后退一帧
        右方向键(→)   前进一帧
        上方向键(↑)   快进5秒
        下方向键(↓)   快退5秒
        
        【标注操作】
        Enter/回车    发送当前帧到标注区
        Ctrl+S        保存当前标注
        Ctrl+Z        撤销上一个标记点
        Escape        清空当前标注
        
        【其他】
        Ctrl+O        打开视频文件夹
        Ctrl+R        审阅标注结果
        """
        QMessageBox.information(self, "快捷键说明", help_text)
        
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于",
            "苹果疏果辅助标注工具\n\n"
            "基于PyQt6和OpenCV开发\n"
            "用于辅助生成苹果疏果实例分割数据集"
        )
        
    def on_video_selected(self, video_path):
        """处理视频选择"""
        self.video_player.load_video(video_path)
        self.current_video_path = video_path
        self.status_bar.showMessage(f"已加载: {os.path.basename(video_path)}")
        
    def on_frame_sent(self, frame, frame_number):
        """处理帧发送到标注区"""
        video_name = os.path.splitext(os.path.basename(self.current_video_path))[0]
        self.annotation_widget.set_frame(frame, video_name, frame_number)
        self.status_bar.showMessage(f"已发送第 {frame_number} 帧到标注区")
        
    def on_save_requested(self, data):
        """处理保存请求"""
        image_id = data['image_id']
        
        # 检查是否已存在
        ann_path = f"saved_images/Annotation/{image_id}.png"
        if os.path.exists(ann_path):
            reply = QMessageBox.question(
                self, "文件已存在",
                f"{image_id} 的标注已存在，是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        # 保存图片和元数据
        success = self.annotation_manager.save_annotation(data)
        
        if success:
            self.status_bar.showMessage(f"已保存: {image_id}")
            self.video_list.mark_as_processed(self.current_video_path)
        else:
            QMessageBox.warning(self, "保存失败", "保存标注时发生错误")
            
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.config_manager.save_config()
        self.video_player.stop()
        event.accept()
