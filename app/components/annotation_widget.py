"""
标注区域组件 - ROI选择和标记点标注（修复版）
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QRect, QRectF
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, 
    QMouseEvent, QWheelEvent, QBrush
)

import cv2
import numpy as np


class ImageCanvas(QWidget):
    """可交互的图像画布（修复版）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.original_image = None  # OpenCV格式的原始图像 (BGR)
        self.display_image = None   # 用于显示的QImage
        
        # ROI相关
        self.roi_start = None       # 原图坐标
        self.roi_end = None         # 原图坐标
        self.roi_rect = None        # 最终确定的ROI (QRect, 原图坐标)
        self.is_drawing_roi = False
        self.temp_roi_end = None    # 绘制过程中的临时终点
        
        # 标记点列表: [(QPoint原图坐标, 类型), ...]
        # 类型: "remove" = 红点(疏除), "keep" = 绿点(保留)
        self.points = []
        
        # 显示相关
        self.scale = 1.0            # 图像缩放比例（自动计算）
        self.image_offset = QPoint(0, 0)  # 图像在widget中的偏移
        
        # 模式: "roi" = 绘制ROI, "point" = 标记点
        self.mode = "roi"
        
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #2d2d2d;")
        
    def set_image(self, cv_image):
        """设置要显示的图像（OpenCV BGR格式）"""
        self.original_image = cv_image.copy()
        self.roi_rect = None
        self.roi_start = None
        self.roi_end = None
        self.temp_roi_end = None
        self.points = []
        self.mode = "roi"
        self.update()
        
    def paintEvent(self, event):
        """绑定绑定绑定绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 填充背景
        painter.fillRect(self.rect(), QColor("#2d2d2d"))
        
        if self.original_image is None:
            painter.setPen(QColor("#888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "等待接收帧...")
            return
            
        # 转换OpenCV图像为QImage
        rgb_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # 计算缩放比例以适应widget
        widget_w = self.width()
        widget_h = self.height()
        
        scale_w = widget_w / w
        scale_h = widget_h / h
        self.scale = min(scale_w, scale_h, 1.0)  # 不放大，只缩小
        
        # 计算显示尺寸和偏移（居中显示）
        display_w = int(w * self.scale)
        display_h = int(h * self.scale)
        self.image_offset = QPoint(
            (widget_w - display_w) // 2,
            (widget_h - display_h) // 2
        )
        
        # 绘制图像
        target_rect = QRectF(
            self.image_offset.x(), 
            self.image_offset.y(),
            display_w, 
            display_h
        )
        painter.drawImage(target_rect, q_image)
        
        # 绘制ROI框
        if self.roi_rect:
            # 已确定的ROI
            display_rect = self.image_to_widget_rect(self.roi_rect)
            pen = QPen(QColor("#00BFFF"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 191, 255, 30)))
            painter.drawRect(display_rect)
        elif self.roi_start and self.temp_roi_end:
            # 正在绘制中的ROI
            temp_rect = QRect(self.roi_start, self.temp_roi_end).normalized()
            display_rect = self.image_to_widget_rect(temp_rect)
            pen = QPen(QColor("#00BFFF"), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(display_rect)
            
        # 绘制标记点
        for point, point_type in self.points:
            display_point = self.image_to_widget_point(point)
            
            if point_type == "remove":
                # 红点 - 疏除
                color = QColor("#FF4444")
                label = "疏"
            else:
                # 绿点 - 保留
                color = QColor("#44FF44")
                label = "留"
                
            # 绘制圆点
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(display_point, 10, 10)
            
            # 绘制标签
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(display_point.x() - 5, display_point.y() + 5, label)
            
    def image_to_widget_point(self, image_point):
        """将原图坐标转换为widget坐标"""
        wx = int(image_point.x() * self.scale) + self.image_offset.x()
        wy = int(image_point.y() * self.scale) + self.image_offset.y()
        return QPoint(wx, wy)
        
    def image_to_widget_rect(self, image_rect):
        """将原图矩形转换为widget矩形"""
        top_left = self.image_to_widget_point(image_rect.topLeft())
        w = int(image_rect.width() * self.scale)
        h = int(image_rect.height() * self.scale)
        return QRect(top_left.x(), top_left.y(), w, h)
        
    def widget_to_image_point(self, widget_point):
        """将widget坐标转换为原图坐标"""
        if self.original_image is None:
            return None
            
        # 减去偏移
        x = widget_point.x() - self.image_offset.x()
        y = widget_point.y() - self.image_offset.y()
        
        # 检查是否在图像范围内
        display_w = int(self.original_image.shape[1] * self.scale)
        display_h = int(self.original_image.shape[0] * self.scale)
        
        if x < 0 or x >= display_w or y < 0 or y >= display_h:
            return None
            
        # 转换为原图坐标
        img_x = int(x / self.scale)
        img_y = int(y / self.scale)
        
        # 确保在原图范围内
        img_h, img_w = self.original_image.shape[:2]
        img_x = max(0, min(img_x, img_w - 1))
        img_y = max(0, min(img_y, img_h - 1))
        
        return QPoint(img_x, img_y)
        
    def mousePressEvent(self, event: QMouseEvent):
        if self.original_image is None:
            return
            
        image_pos = self.widget_to_image_point(event.pos())
        if image_pos is None:
            return
            
        if self.mode == "roi":
            # ROI绘制模式 - 只响应左键
            if event.button() == Qt.MouseButton.LeftButton:
                self.is_drawing_roi = True
                self.roi_start = image_pos
                self.temp_roi_end = image_pos
                self.roi_rect = None
                self.update()
                
        elif self.mode == "point":
            # 标记点模式 - 必须在ROI内
            if self.roi_rect and self.roi_rect.contains(image_pos):
                if event.button() == Qt.MouseButton.LeftButton:
                    # 左键 = 红点（疏除）
                    self.points.append((image_pos, "remove"))
                    self.update()
                elif event.button() == Qt.MouseButton.RightButton:
                    # 右键 = 绿点（保留）
                    self.points.append((image_pos, "keep"))
                    self.update()
                    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.original_image is None:
            return
            
        if self.is_drawing_roi:
            image_pos = self.widget_to_image_point(event.pos())
            if image_pos:
                self.temp_roi_end = image_pos
                self.update()
                
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing_roi:
            self.is_drawing_roi = False
            
            if self.roi_start and self.temp_roi_end:
                # 创建并规范化矩形
                self.roi_rect = QRect(self.roi_start, self.temp_roi_end).normalized()
                
                # 确保ROI有最小尺寸
                if self.roi_rect.width() > 20 and self.roi_rect.height() > 20:
                    self.mode = "point"  # 切换到点标记模式
                else:
                    self.roi_rect = None
                    
            self.temp_roi_end = None
            self.update()
            
    def undo_point(self):
        """撤销上一个点"""
        if self.points:
            self.points.pop()
            self.update()
            return True
        return False
        
    def clear_all(self):
        """清除所有标注"""
        self.roi_rect = None
        self.roi_start = None
        self.roi_end = None
        self.temp_roi_end = None
        self.points = []
        self.mode = "roi"
        self.update()
        
    def reset_roi(self):
        """重置ROI，保留图像"""
        self.roi_rect = None
        self.roi_start = None
        self.roi_end = None
        self.temp_roi_end = None
        self.points = []
        self.mode = "roi"
        self.update()
        
    def get_roi_image(self):
        """获取ROI区域的原始图像（不带标记点）"""
        if self.original_image is None or self.roi_rect is None:
            return None
            
        x = self.roi_rect.x()
        y = self.roi_rect.y()
        w = self.roi_rect.width()
        h = self.roi_rect.height()
        
        # 确保坐标在图像范围内
        img_h, img_w = self.original_image.shape[:2]
        x = max(0, min(x, img_w))
        y = max(0, min(y, img_h))
        w = min(w, img_w - x)
        h = min(h, img_h - y)
        
        return self.original_image[y:y+h, x:x+w].copy()
        
    def get_roi_image_with_points(self):
        """获取带标记点的ROI区域图像"""
        if self.original_image is None or self.roi_rect is None:
            return None
            
        x = self.roi_rect.x()
        y = self.roi_rect.y()
        w = self.roi_rect.width()
        h = self.roi_rect.height()
        
        # 确保坐标在图像范围内
        img_h, img_w = self.original_image.shape[:2]
        x = max(0, min(x, img_w))
        y = max(0, min(y, img_h))
        w = min(w, img_w - x)
        h = min(h, img_h - y)
        
        roi_image = self.original_image[y:y+h, x:x+w].copy()
        
        # 在ROI图像上绘制点
        for point, point_type in self.points:
            if self.roi_rect.contains(point):
                # 转换为ROI内的坐标
                px = point.x() - x
                py = point.y() - y
                
                if point_type == "remove":
                    # 红点 - 疏除
                    color = (68, 68, 255)  # BGR: 红色
                    label = "X"
                else:
                    # 绿点 - 保留
                    color = (68, 255, 68)  # BGR: 绿色
                    label = "O"
                    
                # 绘制圆点
                cv2.circle(roi_image, (px, py), 10, color, -1)
                cv2.circle(roi_image, (px, py), 10, (0, 0, 0), 2)
                
                # 绘制标签文字
                cv2.putText(
                    roi_image, label, 
                    (px - 6, py + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, (255, 255, 255), 2
                )
                
        return roi_image
        
    def get_points_data(self):
        """获取标记点数据"""
        if self.roi_rect is None:
            return []
            
        points_data = []
        x = self.roi_rect.x()
        y = self.roi_rect.y()
        
        for point, point_type in self.points:
            if self.roi_rect.contains(point):
                points_data.append({
                    "type": point_type,
                    "label": "疏除" if point_type == "remove" else "保留",
                    "pos": [point.x() - x, point.y() - y]  # 相对于ROI的坐标
                })
                
        return points_data


class AnnotationWidget(QWidget):
    """标注区域组件"""
    
    # 信号
    save_requested = pyqtSignal(dict)
    
    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.video_name = ""
        self.frame_number = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("标注工作区")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 操作提示
        self.tip_label = QLabel(
            "操作说明：\n"
            "1. 鼠标左键拖拽画出ROI区域\n"
            "2. 在ROI内：左键=红点(疏除)，右键=绿点(保留)\n"
            "3. 滚轮可缩放查看"
        )
        self.tip_label.setStyleSheet(
            "color: #aaa; font-size: 11px; background: #363636; "
            "padding: 8px; border-radius: 4px;"
        )
        self.tip_label.setWordWrap(True)
        layout.addWidget(self.tip_label)
        
        # 图像画布
        self.canvas = ImageCanvas()
        layout.addWidget(self.canvas, 1)
        
        # 状态信息
        self.status_label = QLabel("等待接收帧...")
        self.status_label.setStyleSheet("color: #0078d4; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # 标记点统计
        self.stats_label = QLabel("红点(疏除): 0 | 绿点(保留): 0")
        self.stats_label.setStyleSheet("color: #888;")
        layout.addWidget(self.stats_label)
        
        # 注释输入
        comment_label = QLabel("注释 (可选):")
        layout.addWidget(comment_label)
        
        self.comment_input = QTextEdit()
        self.comment_input.setMaximumHeight(50)
        self.comment_input.setPlaceholderText("为这个标注添加备注信息...")
        layout.addWidget(self.comment_input)
        
        # 操作按钮行
        btn_layout = QHBoxLayout()
        
        self.undo_btn = QPushButton("↶ 撤销点")
        self.undo_btn.setToolTip("Ctrl+Z")
        self.undo_btn.clicked.connect(self.undo_point)
        btn_layout.addWidget(self.undo_btn)
        
        self.reset_roi_btn = QPushButton("重画ROI")
        self.reset_roi_btn.clicked.connect(self.reset_roi)
        btn_layout.addWidget(self.reset_roi_btn)
        
        self.clear_btn = QPushButton("✕ 清空全部")
        self.clear_btn.setToolTip("Esc")
        self.clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
        
        # 保存按钮
        self.save_btn = QPushButton("💾 保存标注 (Ctrl+S)")
        self.save_btn.clicked.connect(self.save_annotation)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        layout.addWidget(self.save_btn)
        
        # 设置焦点策略
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def update_labels(self, labels):
        """兼容接口 - 本版本使用固定的红绿点"""
        pass
        
    def set_frame(self, frame, video_name, frame_number):
        """设置要标注的帧"""
        self.video_name = video_name
        self.frame_number = frame_number
        self.canvas.set_image(frame)
        self.comment_input.clear()
        self.status_label.setText(f"来源: {video_name} | 帧号: {frame_number}")
        self.update_stats()
        
    def undo_point(self):
        """撤销上一个点"""
        if self.canvas.undo_point():
            self.update_stats()
            
    def reset_roi(self):
        """重置ROI"""
        self.canvas.reset_roi()
        self.update_stats()
        
    def clear_all(self):
        """清空所有标注"""
        self.canvas.clear_all()
        self.comment_input.clear()
        self.update_stats()
        
    def update_stats(self):
        """更新统计信息"""
        remove_count = sum(1 for _, t in self.canvas.points if t == "remove")
        keep_count = sum(1 for _, t in self.canvas.points if t == "keep")
        self.stats_label.setText(
            f"红点(疏除): {remove_count} | 绿点(保留): {keep_count}"
        )
        
    def save_annotation(self):
        """保存标注"""
        if self.canvas.original_image is None:
            self.show_message("请先发送一帧图像到标注区！", "warning")
            return
            
        if self.canvas.roi_rect is None:
            self.show_message("请先绘制ROI区域！", "warning")
            return
            
        # 获取图像
        roi_image = self.canvas.get_roi_image()
        roi_image_with_points = self.canvas.get_roi_image_with_points()
        
        if roi_image is None:
            self.show_message("获取ROI图像失败！", "error")
            return
            
        # 构建保存数据
        image_id = f"{self.video_name}_frame_{self.frame_number}"
        roi_rect = self.canvas.roi_rect
        
        save_data = {
            "image_id": image_id,
            "source_video": self.video_name,
            "frame_number": self.frame_number,
            "roi_coords": [roi_rect.x(), roi_rect.y(), roi_rect.width(), roi_rect.height()],
            "comment": self.comment_input.toPlainText(),
            "points": self.canvas.get_points_data(),
            "roi_image": roi_image,
            "roi_image_with_points": roi_image_with_points
        }
        
        self.save_requested.emit(save_data)
        self.show_message("✓ 标注已保存！", "success")
        
    def show_message(self, text, msg_type="info"):
        """显示消息"""
        colors = {
            "info": "#0078d4",
            "success": "#28a745",
            "warning": "#ffc107",
            "error": "#dc3545"
        }
        color = colors.get(msg_type, "#0078d4")
        self.tip_label.setText(text)
        self.tip_label.setStyleSheet(
            f"color: white; font-size: 12px; background: {color}; "
            "padding: 8px; border-radius: 4px;"
        )
        
    def keyPressEvent(self, event):
        """处理键盘事件"""
        key = event.key()
        modifiers = event.modifiers()
        
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Z:
                self.undo_point()
            elif key == Qt.Key.Key_S:
                self.save_annotation()
        elif key == Qt.Key.Key_Escape:
            self.clear_all()
        else:
            super().keyPressEvent(event)
            
    def mousePressEvent(self, event):
        """确保点击时获取焦点"""
        self.setFocus()
        super().mousePressEvent(event)
