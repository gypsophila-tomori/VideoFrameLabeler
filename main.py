"""
苹果疏果辅助标注工具 - 主入口
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app.main_window import MainWindow


def setup_directories():
    """确保必要的目录存在"""
    directories = [
        'video',
        'saved_images',
        'saved_images/Annotation',
        'saved_images/Reference',
        'icons'
    ]
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)


def main():
    # 设置高DPI支持
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    
    # 创建必要的目录
    setup_directories()
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("苹果疏果辅助标注工具")
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
