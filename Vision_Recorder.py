import os
import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QStackedWidget, QHeaderView,
                             QFormLayout, QSizePolicy, QFrame, QAction, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QSize, QSettings, QTimer
from PyQt5.QtGui import QIcon
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class ProjectInfo:
    """项目信息元数据（集中管理所有项目相关信息）"""
    APP_NAME = "视力情况登记系统"
    VERSION = "4.1"
    BUILD_DATE = "2026-08-20"
    AUTHOR = "杜玛"
    LICENSE = "MIT"
    COPYRIGHT = "© 永久 杜玛"
    URL = "https://github.com/duma520"

    VERSION_HISTORY = {
        "1.0": "基础版：用户管理 + 视力记录录入与查询",
        "2.0": "新增动态图标生成（DynamicIcon）",
        "3.0": "UI 重构：左右眼分栏显示、记录表格上下分列左右眼",
        "4.0": "版本号规范化：新增 ProjectInfo 元数据、帮助菜单与关于对话框、建立维护文档体系",
        "4.1": "设置实时自动保存与持久化：窗口几何/最大化自动保存与恢复（QSettings 注册表）",
    }

    DESCRIPTION = """视力情况登记系统 - 一款简单易用的视力/验光数据登记工具

主要功能：
• 用户管理（添加/删除/选择）
• 视力记录录入（左右眼球镜/柱镜/轴位、矫正视力、裸眼视力、旧镜、瞳距/瞳高、用途、备注）
• 记录查询与删除（左右眼上下分列显示）
• 数据持久化（SQLite 数据库）
• 设置实时自动保存（窗口几何/最大化，下次启动自动恢复）
"""

    @classmethod
    def get_metadata(cls) -> dict:
        """获取主要元数据字典"""
        return {
            'name': cls.APP_NAME,
            'version': cls.VERSION,
            'author': cls.AUTHOR,
            'license': cls.LICENSE,
            'url': cls.URL,
        }


class DynamicIcon:
    @staticmethod
    def generate_icon():
        try:
            img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((50, 50, 206, 206), fill=(70, 130, 180), outline=(0, 0, 0))
            draw.ellipse((90, 90, 166, 166), fill=(0, 0, 139), outline=(0, 0, 0))
            draw.ellipse((118, 118, 138, 138), fill=(0, 0, 0), outline=(0, 0, 0))
            draw.ellipse((130, 100, 140, 110), fill=(255, 255, 255), outline=(255, 255, 255))
            img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            return True
        except Exception as e:
            print(f"生成图标失败: {e}")
            return False

    @staticmethod
    def get_icon():
        if not os.path.exists('icon.ico'):
            success = DynamicIcon.generate_icon()
            if not success:
                return None
        return QIcon('icon.ico')

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.initialize_db()

    def initialize_db(self):
        try:
            self.conn = sqlite3.connect('vision_data.db')
            self.cursor = self.conn.cursor()
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS vision_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    sphere_right TEXT,
                    sphere_left TEXT,
                    cylinder_right TEXT,
                    cylinder_left TEXT,
                    axis_right TEXT,
                    axis_left TEXT,
                    corrected_vision_right TEXT,
                    corrected_vision_left TEXT,
                    naked_vision_right TEXT,
                    naked_vision_left TEXT,
                    old_glasses_right TEXT,
                    old_glasses_left TEXT,
                    pd TEXT,
                    ph TEXT,
                    usage_type TEXT,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            QMessageBox.critical(None, "数据库错误", f"无法初始化数据库: {e}")

    def get_users(self):
        try:
            self.cursor.execute("SELECT id, name FROM users ORDER BY name")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取用户列表错误: {e}")
            return []

    def add_user(self, name):
        try:
            self.cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            QMessageBox.warning(None, "警告", "用户名已存在!")
            return None
        except sqlite3.Error as e:
            print(f"添加用户错误: {e}")
            QMessageBox.critical(None, "错误", f"添加用户失败: {e}")
            return None

    def delete_user(self, user_id):
        try:
            self.cursor.execute("DELETE FROM vision_records WHERE user_id=?", (user_id,))
            self.cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"删除用户错误: {e}")
            QMessageBox.critical(None, "错误", f"删除用户失败: {e}")
            return False

    def get_vision_records(self, user_id):
        try:
            self.cursor.execute('''
                SELECT id, date, sphere_right, sphere_left, cylinder_right, cylinder_left,
                       axis_right, axis_left, corrected_vision_right, corrected_vision_left,
                       naked_vision_right, naked_vision_left, old_glasses_right, old_glasses_left,
                       pd, ph, usage_type, notes
                FROM vision_records
                WHERE user_id=?
                ORDER BY date DESC
            ''', (user_id,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取视力记录错误: {e}")
            return []

    def add_vision_record(self, user_id, data):
        try:
            self.cursor.execute('''
                INSERT INTO vision_records (
                    user_id, date, sphere_right, sphere_left, cylinder_right, cylinder_left,
                    axis_right, axis_left, corrected_vision_right, corrected_vision_left,
                    naked_vision_right, naked_vision_left, old_glasses_right, old_glasses_left,
                    pd, ph, usage_type, notes
                ) VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                data.get('sphere_right', ''),
                data.get('sphere_left', ''),
                data.get('cylinder_right', ''),
                data.get('cylinder_left', ''),
                data.get('axis_right', ''),
                data.get('axis_left', ''),
                data.get('corrected_vision_right', ''),
                data.get('corrected_vision_left', ''),
                data.get('naked_vision_right', ''),
                data.get('naked_vision_left', ''),
                data.get('old_glasses_right', ''),
                data.get('old_glasses_left', ''),
                data.get('pd', ''),
                data.get('ph', ''),
                data.get('usage_type', ''),
                data.get('notes', '')
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"添加视力记录错误: {e}")
            QMessageBox.critical(None, "错误", f"添加视力记录失败: {e}")
            return None

    def delete_vision_record(self, record_id):
        try:
            self.cursor.execute("DELETE FROM vision_records WHERE id=?", (record_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"删除视力记录错误: {e}")
            QMessageBox.critical(None, "错误", f"删除视力记录失败: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()

class UserManagementWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title_label = QLabel("用户管理")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        add_user_layout = QHBoxLayout()
        self.new_user_input = QLineEdit()
        self.new_user_input.setPlaceholderText("输入新用户名")
        add_user_layout.addWidget(self.new_user_input)
        
        add_user_btn = QPushButton("添加用户")
        add_user_btn.clicked.connect(self.add_user)
        add_user_layout.addWidget(add_user_btn)
        
        layout.addLayout(add_user_layout)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(2)
        self.user_table.setHorizontalHeaderLabels(["ID", "用户名"])
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        delete_user_btn = QPushButton("删除选中用户")
        delete_user_btn.clicked.connect(self.delete_user)
        
        select_user_btn = QPushButton("选择用户")
        select_user_btn.clicked.connect(self.select_user)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(delete_user_btn)
        btn_layout.addWidget(select_user_btn)
        
        layout.addWidget(self.user_table)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.load_users()

    def load_users(self):
        users = self.db_manager.get_users()
        self.user_table.setRowCount(len(users))
        
        for row, (user_id, name) in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(str(user_id)))
            self.user_table.setItem(row, 1, QTableWidgetItem(name))
        
        self.user_table.resizeColumnsToContents()

    def add_user(self):
        name = self.new_user_input.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "用户名不能为空!")
            return
            
        user_id = self.db_manager.add_user(name)
        if user_id:
            self.new_user_input.clear()
            self.load_users()
            QMessageBox.information(self, "成功", "用户添加成功!")

    def delete_user(self):
        selected_items = self.user_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个用户!")
            return
            
        row = selected_items[0].row()
        user_id = int(self.user_table.item(row, 0).text())
        user_name = self.user_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, '确认删除',
            f'确定要删除用户 "{user_name}" 及其所有视力记录吗?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.delete_user(user_id):
                self.load_users()
                QMessageBox.information(self, "成功", "用户删除成功!")

    def select_user(self):
        selected_items = self.user_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个用户!")
            return
            
        row = selected_items[0].row()
        user_id = int(self.user_table.item(row, 0).text())
        user_name = self.user_table.item(row, 1).text()
        
        self.parent.switch_to_vision_record(user_id, user_name)

class VisionRecordWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        self.current_user_id = None
        self.current_user_name = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title_layout = QHBoxLayout()
        self.back_btn = QPushButton("返回用户列表")
        self.back_btn.clicked.connect(self.parent.switch_to_user_management)
        title_layout.addWidget(self.back_btn)
        
        self.user_title = QLabel()
        self.user_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_layout.addWidget(self.user_title)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)

        # 表单部分 - 使用网格布局更灵活
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        
        # 右眼数据框
        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.StyledPanel)
        right_layout = QFormLayout(right_frame)
        
        right_title = QLabel("右眼数据")
        right_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addRow(right_title)
        
        self.sphere_right = QLineEdit()
        self.sphere_right.setPlaceholderText("例如: -2.50")
        right_layout.addRow("球镜:", self.sphere_right)
        
        self.cylinder_right = QLineEdit()
        self.cylinder_right.setPlaceholderText("例如: -1.25")
        right_layout.addRow("柱镜:", self.cylinder_right)
        
        self.axis_right = QLineEdit()
        self.axis_right.setPlaceholderText("0-180")
        right_layout.addRow("轴位:", self.axis_right)
        
        self.corrected_vision_right = QLineEdit()
        self.corrected_vision_right.setPlaceholderText("例如: 1.0")
        right_layout.addRow("矫正视力:", self.corrected_vision_right)
        
        self.naked_vision_right = QLineEdit()
        self.naked_vision_right.setPlaceholderText("例如: 0.5")
        right_layout.addRow("裸眼视力:", self.naked_vision_right)
        
        self.old_glasses_right = QLineEdit()
        self.old_glasses_right.setPlaceholderText("旧镜度数")
        right_layout.addRow("旧镜:", self.old_glasses_right)
        
        # 左眼数据框
        left_frame = QFrame()
        left_frame.setFrameShape(QFrame.StyledPanel)
        left_layout = QFormLayout(left_frame)
        
        left_title = QLabel("左眼数据")
        left_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addRow(left_title)
        
        self.sphere_left = QLineEdit()
        self.sphere_left.setPlaceholderText("例如: -2.50")
        left_layout.addRow("球镜:", self.sphere_left)
        
        self.cylinder_left = QLineEdit()
        self.cylinder_left.setPlaceholderText("例如: -1.25")
        left_layout.addRow("柱镜:", self.cylinder_left)
        
        self.axis_left = QLineEdit()
        self.axis_left.setPlaceholderText("0-180")
        left_layout.addRow("轴位:", self.axis_left)
        
        self.corrected_vision_left = QLineEdit()
        self.corrected_vision_left.setPlaceholderText("例如: 1.0")
        left_layout.addRow("矫正视力:", self.corrected_vision_left)
        
        self.naked_vision_left = QLineEdit()
        self.naked_vision_left.setPlaceholderText("例如: 0.5")
        left_layout.addRow("裸眼视力:", self.naked_vision_left)
        
        self.old_glasses_left = QLineEdit()
        self.old_glasses_left.setPlaceholderText("旧镜度数")
        left_layout.addRow("旧镜:", self.old_glasses_left)
        
        # 将左右眼数据框并排显示
        eyes_layout = QHBoxLayout()
        eyes_layout.addWidget(right_frame)
        eyes_layout.addWidget(left_frame)
        form_layout.addLayout(eyes_layout)
        
        # 其他数据框
        other_frame = QFrame()
        other_frame.setFrameShape(QFrame.StyledPanel)
        other_layout = QFormLayout(other_frame)
        
        other_title = QLabel("其他数据")
        other_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        other_layout.addRow(other_title)
        
        self.pd = QLineEdit()
        self.pd.setPlaceholderText("瞳距(mm)")
        other_layout.addRow("瞳距:", self.pd)
        
        self.ph = QLineEdit()
        self.ph.setPlaceholderText("瞳高(mm)")
        other_layout.addRow("瞳高:", self.ph)
        
        self.usage_type = QComboBox()
        self.usage_type.addItems(["远用", "近用", "双光", "渐进"])
        other_layout.addRow("用途:", self.usage_type)
        
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("备注信息")
        other_layout.addRow("备注:", self.notes)
        
        form_layout.addWidget(other_frame)
        
        # 提交按钮
        submit_btn = QPushButton("提交记录")
        submit_btn.clicked.connect(self.submit_record)
        form_layout.addWidget(submit_btn, alignment=Qt.AlignRight)
        
        # 记录表格 - 修改为上下显示左右眼数据
        self.record_table = QTableWidget()
        self.record_table.setColumnCount(12)
        self.record_table.setHorizontalHeaderLabels([
            "日期", "眼别", "球镜", "柱镜", "轴位", 
            "矫正视力", "裸眼视力", "旧镜", "瞳距", "瞳高", "用途", "操作"
        ])
        self.record_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.record_table.verticalHeader().setVisible(False)
        self.record_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.record_table.setSelectionMode(QTableWidget.SingleSelection)
        self.record_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 主布局
        split_layout = QHBoxLayout()
        split_layout.addWidget(form_widget, 1)
        split_layout.addWidget(self.record_table, 2)
        
        layout.addLayout(split_layout)
        self.setLayout(layout)

    def set_user(self, user_id, user_name):
        self.current_user_id = user_id
        self.current_user_name = user_name
        self.user_title.setText(f"视力记录 - {user_name}")
        self.load_records()

    def load_records(self):
        if not self.current_user_id:
            return
            
        records = self.db_manager.get_vision_records(self.current_user_id)
        self.record_table.setRowCount(len(records) * 2)  # 每条记录显示两行(左右眼)
        
        for row, record in enumerate(records):
            record_id = record[0]
            date = record[1][:10]  # 只取日期部分
            
            # 右眼数据
            right_row = row * 2
            self.record_table.setItem(right_row, 0, QTableWidgetItem(date))
            self.record_table.setItem(right_row, 1, QTableWidgetItem("右眼"))
            self.record_table.setItem(right_row, 2, QTableWidgetItem(record[2] or "-"))  # sphere_right
            self.record_table.setItem(right_row, 3, QTableWidgetItem(record[4] or "-"))  # cylinder_right
            self.record_table.setItem(right_row, 4, QTableWidgetItem(record[6] or "-"))  # axis_right
            self.record_table.setItem(right_row, 5, QTableWidgetItem(record[8] or "-"))  # corrected_vision_right
            self.record_table.setItem(right_row, 6, QTableWidgetItem(record[10] or "-"))  # naked_vision_right
            self.record_table.setItem(right_row, 7, QTableWidgetItem(record[12] or "-"))  # old_glasses_right
            self.record_table.setItem(right_row, 8, QTableWidgetItem(record[14] or "-"))  # pd
            self.record_table.setItem(right_row, 9, QTableWidgetItem(record[15] or "-"))  # ph
            self.record_table.setItem(right_row, 10, QTableWidgetItem(record[16] or "-"))  # usage_type
            
            # 左眼数据
            left_row = right_row + 1
            self.record_table.setItem(left_row, 0, QTableWidgetItem(date))
            self.record_table.setItem(left_row, 1, QTableWidgetItem("左眼"))
            self.record_table.setItem(left_row, 2, QTableWidgetItem(record[3] or "-"))  # sphere_left
            self.record_table.setItem(left_row, 3, QTableWidgetItem(record[5] or "-"))  # cylinder_left
            self.record_table.setItem(left_row, 4, QTableWidgetItem(record[7] or "-"))  # axis_left
            self.record_table.setItem(left_row, 5, QTableWidgetItem(record[9] or "-"))  # corrected_vision_left
            self.record_table.setItem(left_row, 6, QTableWidgetItem(record[11] or "-"))  # naked_vision_left
            self.record_table.setItem(left_row, 7, QTableWidgetItem(record[13] or "-"))  # old_glasses_left
            self.record_table.setItem(left_row, 8, QTableWidgetItem(record[14] or "-"))  # pd
            self.record_table.setItem(left_row, 9, QTableWidgetItem(record[15] or "-"))  # ph
            self.record_table.setItem(left_row, 10, QTableWidgetItem(record[16] or "-"))  # usage_type
            
            # 删除按钮 - 只在右眼行显示
            delete_btn = QPushButton("删除记录")
            delete_btn.clicked.connect(lambda _, rid=record_id: self.delete_record(rid))
            self.record_table.setCellWidget(right_row, 11, delete_btn)
            
            # 合并日期单元格
            self.record_table.setSpan(right_row, 0, 2, 1)
        
        self.record_table.resizeColumnsToContents()

    def submit_record(self):
        if not self.current_user_id:
            QMessageBox.warning(self, "警告", "没有选择用户!")
            return
            
        data = {
            'sphere_right': self.sphere_right.text().strip(),
            'sphere_left': self.sphere_left.text().strip(),
            'cylinder_right': self.cylinder_right.text().strip(),
            'cylinder_left': self.cylinder_left.text().strip(),
            'axis_right': self.axis_right.text().strip(),
            'axis_left': self.axis_left.text().strip(),
            'corrected_vision_right': self.corrected_vision_right.text().strip(),
            'corrected_vision_left': self.corrected_vision_left.text().strip(),
            'naked_vision_right': self.naked_vision_right.text().strip(),
            'naked_vision_left': self.naked_vision_left.text().strip(),
            'old_glasses_right': self.old_glasses_right.text().strip(),
            'old_glasses_left': self.old_glasses_left.text().strip(),
            'pd': self.pd.text().strip(),
            'ph': self.ph.text().strip(),
            'usage_type': self.usage_type.currentText(),
            'notes': self.notes.text().strip()
        }
        
        if not any(data.values()):
            QMessageBox.warning(self, "警告", "请至少输入一项数据!")
            return
            
        record_id = self.db_manager.add_vision_record(self.current_user_id, data)
        if record_id:
            self.clear_form()
            self.load_records()
            QMessageBox.information(self, "成功", "视力记录添加成功!")

    def clear_form(self):
        self.sphere_right.clear()
        self.sphere_left.clear()
        self.cylinder_right.clear()
        self.cylinder_left.clear()
        self.axis_right.clear()
        self.axis_left.clear()
        self.corrected_vision_right.clear()
        self.corrected_vision_left.clear()
        self.naked_vision_right.clear()
        self.naked_vision_left.clear()
        self.old_glasses_right.clear()
        self.old_glasses_left.clear()
        self.pd.clear()
        self.ph.clear()
        self.notes.clear()

    def delete_record(self, record_id):
        reply = QMessageBox.question(
            self, '确认删除',
            '确定要删除这条视力记录吗?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.delete_vision_record(record_id):
                self.load_records()
                QMessageBox.information(self, "成功", "记录删除成功!")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.settings = QSettings("VisionRecorder", "Tool")
        self._start_maximized = False
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(500)
        self._settings_save_timer.timeout.connect(self._save_settings_now)
        self.init_ui()
        self.create_menu_bar()
        self.load_settings()
        
        icon = DynamicIcon.get_icon()
        if icon:
            self.setWindowIcon(icon)

    def init_ui(self):
        self.setWindowTitle(f"{ProjectInfo.APP_NAME} v{ProjectInfo.VERSION}")
        self.resize(1200, 800)
        
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        self.user_management_widget = UserManagementWidget(self.db_manager, self)
        self.central_widget.addWidget(self.user_management_widget)
        
        self.vision_record_widget = VisionRecordWidget(self.db_manager, self)
        self.central_widget.addWidget(self.vision_record_widget)
        
        self.central_widget.setCurrentWidget(self.user_management_widget)

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        """显示关于对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"关于 {ProjectInfo.APP_NAME}")
        dialog.resize(520, 420)
        
        layout = QVBoxLayout()
        
        about_label = QLabel()
        about_label.setWordWrap(True)
        about_label.setTextFormat(Qt.RichText)
        
        description = ProjectInfo.DESCRIPTION.replace('\n', '<br>')
        version_history = "<br>".join([f"{ver}: {desc}" for ver, desc in ProjectInfo.VERSION_HISTORY.items()])
        
        about_text = f"""
        <h2>{ProjectInfo.APP_NAME} 版本 {ProjectInfo.VERSION}</h2>
        <p>{description}</p>
        
        <h3>版本历史</h3>
        <p>{version_history}</p>
        
        <h3>基本信息</h3>
        <ul>
            <li>作者: {ProjectInfo.AUTHOR}</li>
            <li>许可证: {ProjectInfo.LICENSE}</li>
            <li>版权: {ProjectInfo.COPYRIGHT}</li>
            <li>构建日期: {ProjectInfo.BUILD_DATE}</li>
        </ul>
        """
        
        about_label.setText(about_text)
        layout.addWidget(about_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def load_settings(self):
        """启动恢复设置（窗口几何/最大化）"""
        geometry = self.settings.value('window_geometry')
        if geometry:
            self.restoreGeometry(geometry)
        self._start_maximized = bool(self.settings.value('window_maximized', False, type=bool))

    def _autosave_settings(self):
        """防抖触发自动保存（500ms 内合并多次变更）"""
        self._settings_save_timer.start()

    def _save_settings_now(self):
        """立即保存设置（窗口几何/最大化）"""
        self.settings.setValue('window_geometry', self.saveGeometry())
        self.settings.setValue('window_maximized', self.isMaximized())
        self.settings.sync()

    def show_window(self):
        """按保存的最大化标志显示窗口"""
        if self._start_maximized:
            self.showMaximized()
        else:
            self.show()

    def moveEvent(self, event):
        """窗口移动 → 防抖自动保存几何"""
        super().moveEvent(event)
        if self.isVisible():
            self._autosave_settings()

    def resizeEvent(self, event):
        """窗口缩放 → 防抖自动保存几何"""
        super().resizeEvent(event)
        if self.isVisible():
            self._autosave_settings()

    def switch_to_user_management(self):
        self.user_management_widget.load_users()
        self.central_widget.setCurrentWidget(self.user_management_widget)

    def switch_to_vision_record(self, user_id, user_name):
        self.vision_record_widget.set_user(user_id, user_name)
        self.central_widget.setCurrentWidget(self.vision_record_widget)

    def closeEvent(self, event):
        self._settings_save_timer.stop()
        self._save_settings_now()
        self.db_manager.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    icon = DynamicIcon.get_icon()
    if icon:
        app.setWindowIcon(icon)
    
    window = MainWindow()
    window.show_window()
    sys.exit(app.exec_())