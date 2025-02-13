import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QHBoxLayout, QSizePolicy, QCheckBox, QAction,
    QSlider, QSpinBox, QScrollArea, QFileDialog, QButtonGroup
)
from PyQt5.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QKeySequence,
    QRegion, QBitmap
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

class ImageLabel(QLabel):
    def __init__(self, parent=None, scroll_area=None, main_window=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.ClickFocus)
        self.zoom_factor = 1.0
        self.drawing = False
        self.last_point = None
        self.brush_size = 5
        self.eraser_size = 5
        self.brush_color = QColor(255, 255, 255)
        self.eraser_color = QColor(0, 0, 0)
        self.erase_mode = False
        self.mask = None
        self.image = None
        self.display_image = None
        self.show_mask = True
        self.scroll_area = scroll_area
        self.main_window = main_window
        self.show_image = True  # 添加控制图像显示的标志

    def set_mask(self, mask):
        self.mask = mask

    def set_image(self, image):
        self.image = image

    def set_brush_size(self, size):  # 设置画笔尺寸
        self.brush_size = size

    def set_eraser_size(self, size):  # 新增设置橡皮擦尺寸
        self.eraser_size = size

    def set_brush_color(self, color):
        self.brush_color = color

    def set_eraser_color(self, color):
        self.eraser_color = color

    def set_erase_mode(self, mode):
        self.erase_mode = mode

    def set_show_mask(self, show):
        self.show_mask = show

    def set_show_image(self, show):
        """设置是否显示原始图像"""
        self.show_image = show

    def wheelEvent(self, event):
        if self.image is None:
            return

        # 获取鼠标指针在 ImageLabel 中的位置
        cursor_pos = event.pos()

        # 缩放因子更新逻辑
        zoom_factor_before = self.zoom_factor
        zoom_factor_new = self.zoom_factor * (1.1 if event.angleDelta().y() > 0 else 0.9)
        zoom_factor_new = max(0.1, min(zoom_factor_new, 10))

        # 仅在缩放因子有变化时更新
        if zoom_factor_new != zoom_factor_before:
            self.zoom_factor = zoom_factor_new
            self.update_display(cursor_pos)

    def update_display(self, cursor_pos=None):
        if self.image:
            # 创建显示用的图像
            if self.show_image:
                display_image = self.image.copy()
            else:
                # 创建白色背景
                display_image = QImage(self.image.size(), QImage.Format_RGB32)
                display_image.fill(Qt.white)
            
            # 如果启用了蒙版显示，添加蒙版叠加
            if self.show_mask and self.mask:
                # 创建半透明红色叠加层
                red_overlay = QImage(self.image.size(), QImage.Format_ARGB32)
                red_overlay.fill(Qt.transparent)
                
                # 使用蒙版创建剪切区域
                mask_image = self.mask.convertToFormat(QImage.Format_Mono)
                mask_image.invertPixels()
                mask_region = QRegion(QBitmap.fromImage(mask_image))
                
                # 在红色叠加层上绘制半透明红色
                painter = QPainter(red_overlay)
                painter.setClipRegion(mask_region)
                painter.fillRect(self.mask.rect(), QColor(255, 0, 0, 128))
                painter.end()
                
                # 将红色叠加层绘制到显示图像上
                painter = QPainter(display_image)
                painter.drawImage(0, 0, red_overlay)
                painter.end()

            # 根据缩放因子调整图像大小
            scaled_width = int(display_image.width() * self.zoom_factor)
            scaled_height = int(display_image.height() * self.zoom_factor)
            scaled_image = display_image.scaled(
                scaled_width, scaled_height,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # 设置图像并调整标签大小
            self.setPixmap(QPixmap.fromImage(scaled_image))
            self.setFixedSize(scaled_image.size())

    def mousePressEvent(self, event):
        if self.image is None:
            return
        if event.button() == Qt.LeftButton:
            self.setFocus()  # 将焦点设置到 ImageLabel
            self.drawing = True
            self.last_point = self.get_image_coordinates(event.pos())
            if self.main_window:
                self.main_window.save_mask_state()  # 保存当前状态以用于撤销

    def mouseMoveEvent(self, event):
        if self.image is None or not self.drawing:
            return
        current_point = self.get_image_coordinates(event.pos())
        if current_point and self.last_point:
            painter = QPainter(self.mask)
            pen_color = self.eraser_color if self.erase_mode else self.brush_color
            pen_size = self.eraser_size if self.erase_mode else self.brush_size
            pen = QPen(pen_color, pen_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_point, current_point)
            painter.end()
            self.last_point = current_point
            self.update_display()


    def mouseReleaseEvent(self, event):
        if self.image is None:
            return
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def get_image_coordinates(self, pos):
        if self.image is None:
            return None
        image_x = pos.x() / self.zoom_factor
        image_y = pos.y() / self.zoom_factor
        image_x = max(0, min(image_x, self.image.width() - 1))
        image_y = max(0, min(image_y, self.image.height() - 1))
        return QPoint(int(image_x), int(image_y))

    def keyPressEvent(self, event):
        # 将键盘事件传递给主窗口
        if self.main_window:
            self.main_window.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

class SegmentationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 确保在运行时获取正确的路径
        if hasattr(sys, '_MEIPASS'):
            # 处理 PyInstaller 打包后的路径
            resource_path = os.path.join(sys._MEIPASS, 'resources')
        else:
            # 正常路径
            resource_path = os.path.join(os.path.dirname(__file__), 'resources')
        
        self.setWindowTitle("Segmentation Annotation Tool")
        self.setGeometry(100, 100, 800, 600)

        # 创建滚动区域和图像标签
        self.scroll_area = QScrollArea()
        self.image_label = ImageLabel(self, self.scroll_area, main_window=self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        # 创建按钮
        self.load_button = QPushButton("Load Images", self)
        self.load_button.clicked.connect(self.load_images)

        self.prev_button = QPushButton("Previous Image", self)
        self.prev_button.clicked.connect(self.load_previous_image)
        self.prev_button.setEnabled(False)

        self.next_button = QPushButton("Next Image", self)
        self.next_button.clicked.connect(self.load_next_image)
        self.next_button.setEnabled(False)

        self.delete_button = QPushButton("Delete Image", self)
        self.delete_button.clicked.connect(self.delete_current_image)
        self.delete_button.setEnabled(False)

        self.clear_button = QPushButton("Clear Annotations", self)
        self.clear_button.clicked.connect(self.clear_annotations)
        self.clear_button.setEnabled(False)

        self.auto_save_checkbox = QCheckBox("Auto Save", self)
        self.auto_save_checkbox.setChecked(True)

        self.show_mask_checkbox = QCheckBox("Show Annotations", self)
        self.show_mask_checkbox.setChecked(True)
        self.show_mask_checkbox.stateChanged.connect(self.show_mask_checkbox_state_changed)

        # 添加显示原始图像的复选框
        self.show_image_checkbox = QCheckBox("Show Image", self)
        self.show_image_checkbox.setChecked(True)
        self.show_image_checkbox.stateChanged.connect(self.show_image_checkbox_state_changed)
        
        # 初始化工具为 brush
        self.erase_mode = False
        self.brush_size = 2
        self.eraser_size = 20

        # 画笔和橡皮擦按钮
        self.brush_button = QPushButton(self)
                # 使用资源路径加载图标
        self.brush_button.setIcon(QIcon(os.path.join(resource_path, 'brush.png')))
        self.brush_button.setIconSize(QSize(32, 32))
        self.brush_button.setFixedSize(60, 40)
        self.brush_button.setCheckable(True)
        self.brush_button.setChecked(True)
        self.brush_button.clicked.connect(self.set_brush_mode)

        self.eraser_button = QPushButton(self)
        self.eraser_button.setIcon(QIcon(os.path.join(resource_path, 'eraser.png')))

        self.eraser_button.setIconSize(QSize(32, 32))
        self.eraser_button.setFixedSize(60, 40)
        self.eraser_button.setCheckable(True)
        self.eraser_button.clicked.connect(self.set_eraser_mode)

        # 创建按钮组
        self.tool_group = QButtonGroup(self)
        self.tool_group.addButton(self.brush_button)
        self.tool_group.addButton(self.eraser_button)
        self.tool_group.setExclusive(True)

        # 设置初始样式
        self.brush_button.setStyleSheet("background-color: #e6f3ff;")

        # 尺寸调节控件组
        self.size_label = QLabel("Size:", self)
        self.size_label.setContentsMargins(0, 0, 2, 0)
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 50)
        self.size_slider.setValue(self.brush_size)
        self.size_slider.setFixedWidth(80)
        self.size_slider.setContentsMargins(0, 0, 0, 0)
        
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(1, 50)
        self.size_spinbox.setValue(self.brush_size)
        self.size_spinbox.setFixedWidth(45)
        self.size_spinbox.setContentsMargins(0, 0, 0, 0)

        # 连接信号
        self.size_slider.valueChanged.connect(self.size_spinbox.setValue)
        self.size_spinbox.valueChanged.connect(self.size_slider.setValue)
        self.size_spinbox.valueChanged.connect(self.change_size)

        # 初始化 ImageLabel 的参数
        self.image_label.set_brush_size(self.brush_size)
        self.image_label.set_eraser_size(self.eraser_size)
        self.image_label.set_brush_color(QColor(255, 255, 255))
        self.image_label.set_eraser_color(QColor(0, 0, 0))
        self.image_label.set_erase_mode(self.erase_mode)

        # 添加计数和图片名称标签
        self.count_label = QLabel("Annotated samples: 0", self)
        self.image_name_label = QLabel("Image: None", self)

        # 设置布局
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.auto_save_checkbox)
        button_layout.addWidget(self.show_mask_checkbox)
        button_layout.addWidget(self.show_image_checkbox)  # 添加到布局中
        
        # 创建工具按钮的子布局
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(self.brush_button)
        tool_layout.addWidget(self.eraser_button)
        tool_layout.addSpacing(15)  # 添加一些间距，分隔工具按钮和尺寸控件
        
        # 创建尺寸控件的子布局
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_label)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_spinbox)
        size_layout.setSpacing(0)  # 将间距设为0，使控件紧密排列
        size_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 将整个尺寸控件组放入一个 widget 中，以保持紧凑
        size_widget = QWidget()
        size_widget.setLayout(size_layout)
        size_widget.setFixedHeight(40)  # 设置固定高度以对齐其他控件
        size_widget.setFixedWidth(170)  # 设置固定宽度，防止过度扩展
        
        tool_layout.addWidget(size_widget)  # 添加尺寸控件组
        tool_layout.addStretch()  # 添加弹性空间，将控件推向左侧
        tool_layout.setContentsMargins(0, 0, 0, 0)
        
        button_layout.addLayout(tool_layout)
        button_layout.setSpacing(10)  # 设置主布局的间距

        label_layout = QHBoxLayout()
        label_layout.addWidget(self.count_label)
        label_layout.addWidget(self.image_name_label)

        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addLayout(label_layout)
        layout.addWidget(self.scroll_area)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.main_folder = None
        self.image_folder = None
        self.mask_folder = None
        self.save_folder = None

        self.image_list = []
        self.current_index = -1

        self.image = None
        self.mask = None

        # 历史栈
        self.mask_history = []

        # 快捷键设置
        undo_shortcut = QKeySequence("Ctrl+Z")
        self.undo_action = QAction(self)
        self.undo_action.setShortcut(undo_shortcut)
        self.undo_action.triggered.connect(self.undo)
        self.addAction(self.undo_action)

        # 初始化计数
        self.annotated_count = 0

        # 默认选择画笔模式
        self.set_brush_mode()

        # 设置窗口接受键盘焦点
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 确保图像标签可以接收键盘事件
        self.image_label.setFocusPolicy(Qt.StrongFocus)

    def set_brush_mode(self):
        """设置画笔模式并更新界面"""
        self.erase_mode = False
        self.image_label.set_erase_mode(False)
        # 更新尺寸显示为当前画笔尺寸
        self.size_spinbox.setValue(self.brush_size)
        # 更新按钮样式
        self.brush_button.setStyleSheet("background-color: #e6f3ff;")  # 浅蓝色背景
        self.eraser_button.setStyleSheet("")
        # 同步尺寸到画板
        self.image_label.set_brush_size(self.brush_size)

    def set_eraser_mode(self):
        """设置橡皮擦模式并更新界面"""
        self.erase_mode = True
        self.image_label.set_erase_mode(True)
        # 更新尺寸显示为当前橡皮擦尺寸
        self.size_spinbox.setValue(self.eraser_size)
        # 更新按钮样式
        self.eraser_button.setStyleSheet("background-color: #e6f3ff;")  # 浅蓝色背景
        self.brush_button.setStyleSheet("")
        # 同步尺寸到画板
        self.image_label.set_eraser_size(self.eraser_size)

    def change_size(self, value):
        """根据当前工具更新对应尺寸"""
        if self.erase_mode:
            self.eraser_size = value
            self.image_label.set_eraser_size(value)
        else:
            self.brush_size = value
            self.image_label.set_brush_size(value)

    def show_mask_checkbox_state_changed(self, state):
        self.image_label.set_show_mask(self.show_mask_checkbox.isChecked())
        self.image_label.update_display()

    def show_image_checkbox_state_changed(self, state):
        """处理显示/隐藏原始图像的状态变化"""
        self.image_label.set_show_image(self.show_image_checkbox.isChecked())
        self.image_label.update_display()

    def update_count_label(self):
        self.count_label.setText(f"Annotated samples: {self.annotated_count}")


    def load_images(self):
        main_folder = QFileDialog.getExistingDirectory(self, "Select Main Folder", "")
        if not main_folder:
            print("No main folder selected.")
            return

        self.main_folder = main_folder
        self.image_folder = os.path.join(self.main_folder, 'images')
        self.mask_folder = os.path.join(self.main_folder, 'masks')
        self.save_folder = self.mask_folder

        if not os.path.exists(self.image_folder):
            print(f"Image folder does not exist: {self.image_folder}")
            return

        if not os.path.exists(self.mask_folder):
            os.makedirs(self.mask_folder)

        self.image_list = [
            f for f in os.listdir(self.image_folder)
            if f.lower().endswith(".png") or f.lower().endswith(".jpg")
        ]
        self.image_list.sort()

        if not self.image_list:
            print("No images found.")
            return

        self.current_index = 0
        self.load_current_image()

    def load_current_image(self):
        if self.current_index < 0 or self.current_index >= len(self.image_list):
            print("Current index out of range.")
            self.image_label.clear()
            self.next_button.setEnabled(False)
            self.prev_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.clear_button.setEnabled(False)
            self.image_name_label.setText("Image: None")
            return

        filename = self.image_list[self.current_index]
        image_path = os.path.join(self.image_folder, filename)
        mask_path = os.path.join(self.mask_folder, filename)

        self.image = QImage(image_path).convertToFormat(QImage.Format_RGB32)
        if os.path.exists(mask_path):
            self.mask = QImage(mask_path).convertToFormat(QImage.Format_Grayscale8)
            if self.mask.size() != self.image.size():
                self.mask = self.mask.scaled(self.image.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        else:
            self.mask = QImage(self.image.size(), QImage.Format_Grayscale8)
            self.mask.fill(0)

        self.image_label.set_image(self.image)
        self.image_label.set_mask(self.mask)
        self.image_label.update_display()

        self.next_button.setEnabled(self.current_index < len(self.image_list) - 1)
        self.prev_button.setEnabled(self.current_index > 0)
        self.delete_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.image_name_label.setText(f"Image: {filename}")
        self.annotated_count = self.current_index + 1
        self.update_count_label()

    def load_next_image(self):
        if self.auto_save_checkbox.isChecked():
            self.save_mask()
        if self.current_index + 1 < len(self.image_list):
            self.current_index += 1
            self.load_current_image()

    def load_previous_image(self):
        if self.auto_save_checkbox.isChecked():
            self.save_mask()
        if self.current_index - 1 >= 0:
            self.current_index -= 1
            self.load_current_image()

    def delete_current_image(self):
        if self.current_index < 0 or self.current_index >= len(self.image_list):
            return

        filename = self.image_list[self.current_index]
        image_path = os.path.join(self.image_folder, filename)
        mask_path = os.path.join(self.mask_folder, filename)
        save_path = os.path.join(self.save_folder, filename)

        # 删除图像文件
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"Deleted image: {image_path}")

        # 删除蒙版文件
        if os.path.exists(mask_path):
            os.remove(mask_path)
            print(f"Deleted mask: {mask_path}")
        if os.path.exists(save_path) and save_path != mask_path:
            os.remove(save_path)
            print(f"Deleted saved mask: {save_path}")

        # 从列表中移除
        del self.image_list[self.current_index]

        # 更新界面
        if not self.image_list:
            self.current_index = -1
            self.image_label.clear()
            self.image = None
            self.mask = None
            self.next_button.setEnabled(False)
            self.prev_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.clear_button.setEnabled(False)
            self.image_name_label.setText("Image: None")
            self.annotated_count = 0
            self.update_count_label()
        else:
            # 如果删除的是最后一张图片，索引减1
            if self.current_index >= len(self.image_list):
                self.current_index = len(self.image_list) - 1
            self.load_current_image()

    def save_mask(self):
        if self.mask is not None:
            filename = self.image_list[self.current_index]
            save_path = os.path.join(self.save_folder, filename)
            self.mask.save(save_path)

    def save_mask_state(self):
        if self.mask is not None:
            self.mask_history.append(self.mask.copy())

    def undo(self):
        if len(self.mask_history) > 1:
            self.mask_history.pop()
            self.mask = self.mask_history[-1].copy()
            self.image_label.set_mask(self.mask)
            self.image_label.update_display()

    def clear_annotations(self):
        """清除当前图像的所有标注"""
        if self.mask is not None:
            # 创建新的空白蒙版
            self.mask = QImage(self.image.size(), QImage.Format_Grayscale8)
            self.mask.fill(0)  # 填充黑色（无标注）
            
            # 更新 ImageLabel
            self.image_label.set_mask(self.mask)
            self.image_label.update_display()
            
            # 保存当前状态用于撤销
            self.save_mask_state()

    def keyPressEvent(self, event):
        # 处理快捷键
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                # Ctrl+Z: 撤销上一步操作
                self.undo()
            elif event.key() == Qt.Key_Q:
                # Ctrl+Q: 切换到画笔模式
                self.brush_button.setChecked(True)
                self.set_brush_mode()
            elif event.key() == Qt.Key_W:
                # Ctrl+W: 切换到橡皮擦模式
                self.eraser_button.setChecked(True)
                self.set_eraser_mode()
        # 处理方向键
        elif event.key() == Qt.Key_Left or event.key() == Qt.Key_Up:
            # 左方向键或上方向键：上一张图片
            if self.current_index > 0:
                self.load_previous_image()
        elif event.key() == Qt.Key_Right or event.key() == Qt.Key_Down:
            # 右方向键或下方向键：下一张图片
            if self.current_index < len(self.image_list) - 1:
                self.load_next_image()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # 当鼠标点击窗口时，确保窗口获得焦点
        self.setFocus()
        super().mousePressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SegmentationTool()
    window.show()
    sys.exit(app.exec_())
