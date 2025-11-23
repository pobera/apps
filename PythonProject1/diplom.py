import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTabWidget,
    QFormLayout, QMessageBox, QGroupBox, QDoubleSpinBox,
    QSpinBox, QAction, QTextEdit, QFileDialog,
    QDialog, QTableWidget, QTableWidgetItem, QDialogButtonBox, QInputDialog, QGridLayout  # Добавленные импорты
)
from PyQt5.QtGui import QTextDocument
from PyQt5.QtCore import Qt
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
import math
from fpdf import FPDF
import datetime
import os
import csv  # Добавьте в импорты
import sqlite3
from sqlite3 import Error



class DatabaseManager:
    def __init__(self, db_file="vehicle_calculator.db"):
        self.db_file = db_file
        self.create_connection()
        self.create_tables()

    def create_connection(self):
        """ Создает соединение с базой данных SQLite """
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_file)
        except Error as e:
            print(f"Ошибка подключения к базе данных: {e}")

    def create_tables(self):
        """ Создает необходимые таблицы в базе данных """
        sql_create_calculations_table = """
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calculation_type TEXT NOT NULL,
            parameters TEXT NOT NULL,
            results TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """

        sql_create_reports_table = """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_data TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """

        try:
            c = self.conn.cursor()
            c.execute(sql_create_calculations_table)
            c.execute(sql_create_reports_table)
            self.conn.commit()
        except Error as e:
            print(f"Ошибка создания таблиц: {e}")

    def save_calculation(self, calc_type, params, results):
        """ Сохраняет расчет в базу данных """
        sql = '''INSERT INTO calculations(calculation_type, parameters, results)
                 VALUES(?,?,?)'''
        try:
            c = self.conn.cursor()
            c.execute(sql, (calc_type, str(params), str(results)))
            self.conn.commit()
            return c.lastrowid
        except Error as e:
            print(f"Ошибка сохранения расчета: {e}")
            return None

    def save_report(self, report_data):
        """ Сохраняет отчет в базу данных """
        sql = '''INSERT INTO reports(report_data)
                 VALUES(?)'''
        try:
            c = self.conn.cursor()
            c.execute(sql, (str(report_data),))
            self.conn.commit()
            return c.lastrowid
        except Error as e:
            print(f"Ошибка сохранения отчета: {e}")
            return None

    def get_history(self, limit=10):
        """ Получает историю расчетов """
        sql = '''SELECT * FROM calculations ORDER BY timestamp DESC LIMIT ?'''
        try:
            c = self.conn.cursor()
            c.execute(sql, (limit,))
            return c.fetchall()
        except Error as e:
            print(f"Ошибка получения истории: {e}")
            return []

    def close(self):
        """ Закрывает соединение с базой данных """
        if self.conn:
            self.conn.close()



class AdvancedVehicleCalculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Калькулятор характеристик автомобиля")
        self.setGeometry(100, 100, 1000, 800)
        self.report_data = {}
        self.initUI()
        self.create_menu()
        self.create_history_menu()
        self.db = DatabaseManager()

    def initUI(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Создаем все вкладки
        self.create_engine_tab()
        self.create_transmission_tab()
        self.create_dynamics_tab()
        self.create_braking_tab()
        self.create_suspension_tab()  # Новая вкладка
        self.create_fuel_tab()  # Новая вкладка
        self.create_report_tab()  # Вкладка для просмотра отчета

        self.statusBar().showMessage("Готово к работе")

    def create_menu(self):
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu('Файл')

        export_pdf_action = QAction('Экспорт в PDF', self)
        export_pdf_action.setShortcut('Ctrl+E')
        export_pdf_action.triggered.connect(self.export_to_pdf)
        file_menu.addAction(export_pdf_action)

        print_action = QAction('Печать отчета', self)
        print_action.setShortcut('Ctrl+P')
        print_action.triggered.connect(self.print_report)
        file_menu.addAction(print_action)

        exit_action = QAction('Выход', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Справка
        help_menu = menubar.addMenu('Справка')

        about_action = QAction('О программе', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_history_menu(self):
        """ Создает меню для работы с историей расчетов """
        menubar = self.menuBar()
        history_menu = menubar.addMenu('История')

        view_history_action = QAction('Просмотреть историю', self)
        view_history_action.triggered.connect(self.view_history)
        history_menu.addAction(view_history_action)

        clear_history_action = QAction('Очистить историю', self)
        clear_history_action.triggered.connect(self.clear_history)
        history_menu.addAction(clear_history_action)

    def export_history_to_csv(self):
        """Экспорт истории расчетов в CSV файл с русскими названиями параметров"""
        try:
            # Получаем историю из базы данных
            history = self.db.get_history(limit=1000)

            if not history:
                QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта")
                return

            # Словари для перевода
            type_translation = {
                'engine_efficiency': 'КПД двигателя',
                'engine_mep': 'Среднее эффективное давление',
                'engine_power': 'Мощность двигателя',
                'engine_air_flow': 'Расход воздуха',
                'engine_compression': 'Степень сжатия',
                'transmission_gear_speeds': 'Скорости на передачах',
                'transmission_ratio_calculation': 'Расчет передаточного отношения',
                'transmission_efficiency': 'КПД трансмиссии',
                'traction_force': 'Тяговая сила',
                'acceleration': 'Разгонная динамика',
                'shift_points': 'Точки переключения',
                'brake_torque': 'Тормозной момент',
                'stopping_distance': 'Тормозной путь',
                'brake_balance': 'Баланс тормозов',
                'brake_temperature': 'Нагрев тормозов',
                'suspension_wheel_rate': 'Жесткость подвески',
                'suspension_frequency': 'Частота подвески',
                'suspension_damping': 'Демпфирование подвески',
                'suspension_kinematics': 'Кинематика подвески',
                'fuel_system_flow': 'Производительность топливной системы',
                'injector_duty': 'Время впрыска',
                'fuel_optimization': 'Оптимизация топливной системы'
            }

            param_translation = {
                # Общие параметры
                "id": "ID",
                "timestamp": "Дата и время",
                "calculation_type": "Тип расчета",
                "parameters": "Параметры",
                "results": "Результаты",
                "note": "Примечание",

                # Подвеска
                "spring_rate": "Жесткость пружины (Н/мм)",
                "motion_ratio": "Коэффициент рычага",
                "preload": "Предварительная нагрузка (мм)",
                "wheel_rate": "Эффективная жесткость колеса (Н/мм)",
                "force_at_ride": "Сила в положении 'покоя' (Н)",
                "corner_weight": "Нагрузка на колесо (кг)",
                "frequency": "Частота подвески (Гц)",
                "ride_height_change": "Изменение клиренса (мм)",
                "rebound_coeff": "Коэффициент отбоя",
                "bump_coeff": "Коэффициент сжатия",
                "damping_ratio": "Коэффициент демпфирования",
                "instant_center_height": "Высота мгновенного центра (мм)",
                "arm_length": "Длина рычага (мм)",
                "pivot_height": "Высота оси вращения (мм)",

                # Тормозная система
                "brake_torque": "Тормозной момент (Н·м)",
                "piston_count": "Количество поршней",
                "piston_diameter": "Диаметр поршня (мм)",
                "disc_diameter": "Диаметр диска (мм)",
                "pad_coef": "Коэффициент трения колодок",
                "pressure": "Давление в системе (бар)",
                "friction_force": "Сила трения (Н)",
                "brake_balance": "Баланс тормозов",
                "front_percent": "Передние тормоза (%)",
                "rear_percent": "Задние тормоза (%)",
                "front_force": "Сила на передних тормозах (Н·м)",
                "rear_force": "Сила на задних тормозах (Н·м)",
                "optimal_percent": "Оптимальный баланс (%)",
                "balance_rating": "Оценка баланса",
                "stopping_distance": "Тормозной путь (м)",
                "speed": "Скорость (км/ч)",
                "road_coeff": "Коэффициент сцепления с дорогой",
                "front_load": "Нагрузка на переднюю ось (Н)",
                "rear_load": "Нагрузка на заднюю ось (Н)",
                "stopping_time": "Время торможения (с)",
                "deceleration": "Замедление (g)",
                "brake_temperature": "Температура тормозов",
                "disc_thickness": "Толщина диска (мм)",
                "kinetic_energy": "Кинетическая энергия (кДж)",
                "heat_energy": "Тепловая энергия (кДж)",
                "temperature_rise": "Рост температуры (°C)",
                "vehicle_weight": "Масса автомобиля (кг)",

                # Двигатель
                "power_hp": "Мощность (л.с.)",
                "fuel_consumption": "Расход топлива (кг/ч)",
                "fuel_type": "Тип топлива",
                "efficiency": "Эффективный КПД (%)",
                "displacement": "Объем двигателя (см³)",
                "torque": "Крутящий момент (Н·м)",
                "mep": "Среднее эффективное давление (бар)",
                "mep_kgcm2": "Среднее эффективное давление (кгс/см²)",
                "rpm": "Обороты (об/мин)",
                "power_kw": "Мощность (кВт)",
                "volumetric_efficiency": "КПД наполнения",
                "air_flow": "Расход воздуха (кг/ч)",
                "cylinder_volume": "Объем цилиндра (см³)",
                "chamber_volume": "Объем камеры сгорания (см³)",
                "compression_ratio": "Степень сжатия",
                "power": "Лошадиные силы",
                "mep_bar": "Среднее эффективное давление (бар)",

                # Динамика
                "traction_force": "Тяговая сила (Н)",
                "gear_ratio": "Передаточное число",
                "equivalent_force": "Эквивалентная сила (кгс)",
                "specific_power": "Удельная мощность (кВт/т)",
                "max_speed": "Максимальная скорость (км/ч)",
                "acceleration_0_100": "Разгон 0-100 км/ч (с)",
                "optimal_rpm": "Оптимальные обороты (об/мин)",
                "shift_points": "Точки переключения передач",
                "weight": "Масса (кг)",
                "drag_coef": "Коэффициент аэродинамического сопротивления",
                "frontal_area": "Лобовая площадь (м²)",
                "rolling_resist": "Коэффициент сопротивления качению",

                # Трансмиссия
                "gear_ratios": "Передаточные числа",
                "final_drive": "Главная передача",
                "tire_diameter": "Диаметр колеса (мм)",
                "redline_rpm": "Максимальные обороты (об/мин)",
                "speeds_at_redline": "Скорости на максимальных оборотах",
                "transmission_efficiency": "КПД трансмиссии (%)",
                "wheel_power": "Мощность на колесах (л.с.)",
                "calculated_ratio": "Расчетное передаточное число",
                "rpm1": "Обороты 1 (об/мин)",
                "rpm2": "Обороты 2 (об/мин)",
                "speed1": "Скорость 1 (км/ч)",
                "speed2": "Скорость 2 (км/ч)",
                "tire_radius": "Радиус колеса (м)",
                "engine_power": "Лошадиные силы (м)",
                "corrected_flow": "Производительность (м)",

                # Топливная система
                "system_type": "Тип системы",
                "injector_count": "Количество форсунок",
                "injector_flow": "Производительность форсунки (г/мин)",
                "total_flow": "Общий расход топлива (г/мин)",
                "flow_per_second": "Расход топлива в секунду (г/сек)",
                "bsfc": "Удельный расход топлива (кг/(л.с.*час))",
                "duty_cycle": "Цикл впрыска (%)",
                "injector_open_time": "Время открытия форсунки (мс)",
                "required_volume": "Требуемый объем топлива (г/час)",
                "target_duty": "Целевой цикл впрыска (%)",
                "optimal_flow": "Оптимальный расход топлива (г/мин)",
                "optimal_pressure": "Оптимальное давление (бар)",
                "temperature": "Температура (°C)",
                "temp": "Температура (°C)",

                # Дополнительные параметры
                "gear_1": "Передача 1",
                "gear_2": "Передача 2",
                "gear_3": "Передача 3",
                "gear_4": "Передача 4",
                "gear_5": "Передача 5",
                "gear_6": "Передача 6",
                "Engine_power_calc": "Расчет мощности двигателя",
                "Engine_air_flow": "Расход воздуха двигателя",
                "Engine_compression": "Степень сжатия двигателя",
                "calculated_gear_ratio": "Расчетное передаточное число"
            }

            # Запрашиваем место сохранения файла
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Экспорт истории в CSV",
                f"История_расчетов_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)", options=options
            )

            if not file_name:
                return

            if not file_name.lower().endswith('.csv'):
                file_name += '.csv'

            # Открываем файл с кодировкой UTF-8 BOM для корректного отображения в Excel
            with open(file_name, mode='w', newline='', encoding='utf-8-sig') as csv_file:
                writer = csv.writer(csv_file, delimiter=';')

                # Заголовки на русском
                writer.writerow(["ID", "Дата и время", "Тип расчета", "Параметры", "Результаты"])

                for record in history:
                    # Переводим тип расчета
                    calc_type = type_translation.get(record[1], record[1])

                    try:
                        # Парсим параметры и переводим ключи
                        params = eval(record[2]) if isinstance(record[2], str) else record[2]
                        translated_params = []
                        for k, v in params.items():
                            translated_key = param_translation.get(k, k)
                            translated_params.append(f"{translated_key}: {v}")
                        params_str = "\n".join(translated_params)
                    except:
                        params_str = str(record[2])

                    try:
                        # Парсим результаты и переводим ключи
                        results = eval(record[3]) if isinstance(record[3], str) else record[3]
                        translated_results = []
                        for k, v in results.items():
                            translated_key = param_translation.get(k, k)
                            translated_results.append(f"{translated_key}: {v}")
                        results_str = "\n".join(translated_results)
                    except:
                        results_str = str(record[3])

                    writer.writerow([
                        record[0],  # ID
                        record[4],  # timestamp
                        calc_type,  # translated calculation type
                        params_str,
                        results_str
                    ])

            QMessageBox.information(self, "Успешно",
                                    f"История расчетов экспортирована в:\n{file_name}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка",
                                 f"Ошибка экспорта:\n{str(e)}")

    def view_history(self):
        """Показывает диалоговое окно с историей расчетов на русском языке"""
        try:
            # Получаем историю из базы данных
            history = self.db.get_history(limit=40)  # Последние 40 записей

            if not history:
                QMessageBox.information(self, "История", "История расчетов пуста")
                return

            # Словарь для перевода типов расчетов
            calc_type_translation = {
                'engine_efficiency': 'КПД двигателя',
                'engine_mep': 'Среднее эффективное давление',
                'engine_power': 'Мощность двигателя',
                'engine_air_flow': 'Расход воздуха',
                'engine_compression': 'Степень сжатия',
                'gear_speeds': 'Скорости на передачах',
                'transmission': 'Трансмиссия',
                'transmission_gear_speeds': 'Скорости на передачах',
                'transmission_ratio_calculation': 'Расчет передаточного отношения',
                'transmission_efficiency': 'КПД трансмиссии',
                'traction_force': 'Тяговая сила',
                'acceleration': 'Разгонная динамика',
                'shift_points': 'Точки переключения',
                'brake_torque': 'Тормозной момент',
                'stopping_distance': 'Тормозной путь',
                'brake_balance': 'Баланс тормозов',
                'brake_temperature': 'Нагрев тормозов',
                'suspension_wheel_rate': 'Жесткость подвески',
                'suspension_frequency': 'Частота подвески',
                'suspension_damping': 'Демпфирование подвески',
                'suspension_kinematics': 'Кинематика подвески',
                'suspension_full': 'Комплексный расчет подвески',
                'fuel_system_flow': 'Производительность топливной системы',
                'injector_duty': 'Время впрыска',
                'fuel_optimization': 'Оптимизация топливной системы',
                'dynamics': 'Динамика',
                'aerodynamics': 'Аэродинамика',
                'braking': 'Тормозная система',
                'suspension': 'Подвеска',
                'fuel_system': 'Топливная система'
            }

            # Словарь для перевода параметров (расширенный)
            param_translation = {
                # Общие параметры
                "id": "ID",
                "timestamp": "Дата и время",
                "calculation_type": "Тип расчета",
                "parameters": "Параметры",
                "results": "Результаты",

                # Подвеска
                "spring_rate": "Жесткость пружины (Н/мм)",
                "motion_ratio": "Коэффициент рычага",
                "preload": "Предварительная нагрузка (мм)",
                "wheel_rate": "Эффективная жесткость колеса (Н/мм)",
                "force_at_ride": "Сила в положении 'покоя' (Н)",
                "corner_weight": "Нагрузка на колесо (кг)",
                "frequency": "Частота подвески (Гц)",
                "ride_height_change": "Изменение клиренса (мм)",
                "rebound_coeff": "Коэффициент отбоя",
                "bump_coeff": "Коэффициент сжатия",
                "damping_ratio": "Коэффициент демпфирования",
                "instant_center_height": "Высота мгновенного центра (мм)",
                "arm_length": "Длина рычага (мм)",
                "pivot_height": "Высота оси вращения (мм)",

                # Тормозная система
                "brake_torque": "Тормозной момент (Н·м)",
                "piston_count": "Количество поршней",
                "piston_diameter": "Диаметр поршня (мм)",
                "disc_diameter": "Диаметр диска (мм)",
                "pad_coef": "Коэффициент трения колодок",
                "pressure": "Давление в системе (бар)",
                "friction_force": "Сила трения (Н)",
                "brake_balance": "Баланс тормозов",
                "front_percent": "Передние тормоза (%)",
                "rear_percent": "Задние тормоза (%)",
                "front_force": "Сила на передних тормозах (Н·м)",
                "rear_force": "Сила на задних тормозах (Н·м)",
                "optimal_percent": "Оптимальный баланс (%)",
                "balance_rating": "Оценка баланса",
                "stopping_distance": "Тормозной путь (м)",
                "speed": "Скорость (км/ч)",
                "road_coeff": "Коэффициент сцепления с дорогой",
                "front_load": "Нагрузка на переднюю ось (Н)",
                "rear_load": "Нагрузка на заднюю ось (Н)",
                "stopping_time": "Время торможения (с)",
                "deceleration": "Замедление (g)",
                "brake_temperature": "Температура тормозов",
                "disc_thickness": "Толщина диска (мм)",
                "kinetic_energy": "Кинетическая энергия (кДж)",
                "heat_energy": "Тепловая энергия (кДж)",
                "temperature_rise": "Рост температуры (°C)",
                "vehicle_weight": "Масса автомобиля (кг)",

                # Двигатель
                "power_hp": "Мощность (л.с.)",
                "fuel_consumption": "Расход топлива (кг/ч)",
                "fuel_type": "Тип топлива",
                "efficiency": "Эффективный КПД (%)",
                "displacement": "Объем двигателя (см³)",
                "torque": "Крутящий момент (Н·м)",
                "mep": "Среднее эффективное давление (бар)",
                "mep_kgcm2": "Среднее эффективное давление (кгс/см²)",
                "rpm": "Обороты (об/мин)",
                "power_kw": "Мощность (кВт)",
                "volumetric_efficiency": "КПД наполнения",
                "air_flow": "Расход воздуха (кг/ч)",
                "cylinder_volume": "Объем цилиндра (см³)",
                "chamber_volume": "Объем камеры сгорания (см³)",
                "compression_ratio": "Степень сжатия",
                "power":"Лошадиные силы",
                "mep_bar": "Среднее эффективное давление (бар)",


                # Динамика
                "traction_force": "Тяговая сила (Н)",
                "gear_ratio": "Передаточное число",
                "equivalent_force": "Эквивалентная сила (кгс)",
                "specific_power": "Удельная мощность (кВт/т)",
                "max_speed": "Максимальная скорость (км/ч)",
                "acceleration_0_100": "Разгон 0-100 км/ч (с)",
                "optimal_rpm": "Оптимальные обороты (об/мин)",
                "shift_points": "Точки переключения передач",
                "weight": "Масса (кг)",
                "drag_coef": "Коэффициент аэродинамического сопротивления",
                "frontal_area": "Лобовая площадь (м²)",
                "rolling_resist": "Коэффициент сопротивления качению",

                # Трансмиссия
                "gear_ratios": "Передаточные числа",
                "final_drive": "Главная передача",
                "tire_diameter": "Диаметр колеса (мм)",
                "redline_rpm": "Максимальные обороты (об/мин)",
                "speeds_at_redline": "Скорости на максимальных оборотах",
                "transmission_efficiency": "КПД трансмиссии (%)",
                "wheel_power": "Мощность на колесах (л.с.)",
                "calculated_ratio": "Расчетное передаточное число",
                "rpm1": "Обороты 1 (об/мин)",
                "rpm2": "Обороты 2 (об/мин)",
                "speed1": "Скорость 1 (км/ч)",
                "speed2": "Скорость 2 (км/ч)",
                "tire_radius": "Радиус колеса (м)",
                "id": "ID",
                "timestamp": "Дата и время",
                "calculation_type": "Тип расчета",
                "parameters": "Параметры",
                "results": "Результаты",

                # Подвеска
                "spring_rate": "Жесткость пружины (Н/мм)",
                "motion_ratio": "Коэффициент рычага",
                "preload": "Предварительная нагрузка (мм)",
                "wheel_rate": "Эффективная жесткость колеса (Н/мм)",
                "force_at_ride": "Сила в положении 'покоя' (Н)",
                "corner_weight": "Нагрузка на колесо (кг)",
                "frequency": "Частота подвески (Гц)",
                "ride_height_change": "Изменение клиренса (мм)",
                "rebound_coeff": "Коэффициент отбоя",
                "bump_coeff": "Коэффициент сжатия",
                "damping_ratio": "Коэффициент демпфирования",
                "instant_center_height": "Высота мгновенного центра (мм)",
                "arm_length": "Длина рычага (мм)",
                "pivot_height": "Высота оси вращения (мм)",

                # Тормозная система
                "brake_torque": "Тормозной момент (Н·м)",
                "piston_count": "Количество поршней",
                "piston_diameter": "Диаметр поршня (мм)",
                "disc_diameter": "Диаметр диска (мм)",
                "pad_coef": "Коэффициент трения колодок",
                "pressure": "Давление в системе (бар)",
                "friction_force": "Сила трения (Н)",
                "brake_balance": "Баланс тормозов",
                "front_percent": "Передние тормоза (%)",
                "rear_percent": "Задние тормоза (%)",
                "front_force": "Сила на передних тормозах (Н·м)",
                "rear_force": "Сила на задних тормозах (Н·м)",
                "optimal_percent": "Оптимальный баланс (%)",
                "balance_rating": "Оценка баланса",
                "stopping_distance": "Тормозной путь (м)",
                "speed": "Скорость (км/ч)",
                "road_coeff": "Коэффициент сцепления с дорогой",
                "front_load": "Нагрузка на переднюю ось (Н)",
                "rear_load": "Нагрузка на заднюю ось (Н)",
                "stopping_time": "Время торможения (с)",
                "deceleration": "Замедление (g)",
                "brake_temperature": "Температура тормозов",
                "disc_thickness": "Толщина диска (мм)",
                "kinetic_energy": "Кинетическая энергия (кДж)",
                "heat_energy": "Тепловая энергия (кДж)",
                "temperature_rise": "Рост температуры (°C)",
                "vehicle_weight": "Масса автомобиля (кг)",

                # Двигатель
                "power_hp": "Мощность (л.с.)",
                "fuel_consumption": "Расход топлива (кг/ч)",
                "fuel_type": "Тип топлива",
                "efficiency": "Эффективный КПД (%)",
                "displacement": "Объем двигателя (см³)",
                "torque": "Крутящий момент (Н·м)",
                "mep": "Среднее эффективное давление (бар)",
                "mep_kgcm2": "Среднее эффективное давление (кгс/см²)",
                "rpm": "Обороты (об/мин)",
                "power_kw": "Мощность (кВт)",
                "volumetric_efficiency": "КПД наполнения",
                "air_flow": "Расход воздуха (кг/ч)",
                "cylinder_volume": "Объем цилиндра (см³)",
                "chamber_volume": "Объем камеры сгорания (см³)",
                "compression_ratio": "Степень сжатия",
                "power": "Лошадиные силы",
                "mep_bar": "Среднее эффективное давление (бар)",

                # Динамика
                "traction_force": "Тяговая сила (Н)",
                "gear_ratio": "Передаточное число",
                "equivalent_force": "Эквивалентная сила (кгс)",
                "specific_power": "Удельная мощность (кВт/т)",
                "max_speed": "Максимальная скорость (км/ч)",
                "acceleration_0_100": "Разгон 0-100 км/ч (с)",
                "optimal_rpm": "Оптимальные обороты (об/мин)",
                "shift_points": "Точки переключения передач",
                "weight": "Масса (кг)",
                "drag_coef": "Коэффициент аэродинамического сопротивления",
                "frontal_area": "Лобовая площадь (м²)",
                "rolling_resist": "Коэффициент сопротивления качению",

                # Трансмиссия
                "gear_ratios": "Передаточные числа",
                "final_drive": "Главная передача",
                "tire_diameter": "Диаметр колеса (мм)",
                "redline_rpm": "Максимальные обороты (об/мин)",
                "speeds_at_redline": "Скорости на максимальных оборотах",
                "transmission_efficiency": "КПД трансмиссии (%)",
                "wheel_power": "Мощность на колесах (л.с.)",
                "calculated_ratio": "Расчетное передаточное число",
                "rpm1": "Обороты 1 (об/мин)",
                "rpm2": "Обороты 2 (об/мин)",
                "speed1": "Скорость 1 (км/ч)",
                "speed2": "Скорость 2 (км/ч)",
                "tire_radius": "Радиус колеса (м)",
                "engine_power": "Лошадиные силы (м)",
                "corrected_flow": "Производительность (м)",

                # Топливная система
                "system_type": "Тип системы",
                "injector_count": "Количество форсунок",
                "injector_flow": "Производительность форсунки (г/мин)",
                "total_flow": "Общий расход топлива (г/мин)",
                "flow_per_second": "Расход топлива в секунду (г/сек)",
                "bsfc": "Удельный расход топлива (кг/(л.с.*час))",
                "duty_cycle": "Цикл впрыска (%)",
                "injector_open_time": "Время открытия форсунки (мс)",
                "required_volume": "Требуемый объем топлива (г/час)",
                "target_duty": "Целевой цикл впрыска (%)",
                "optimal_flow": "Оптимальный расход топлива (г/мин)",
                "optimal_pressure": "Оптимальное давление (бар)",
                "temperature": "Температура (°C)",
                "temp": "Температура (°C)",
                "note": "Примечание",

                # Дополнительные параметры
                "gear_1": "Передача 1",
                "gear_2": "Передача 2",
                "gear_3": "Передача 3",
                "gear_4": "Передача 4",
                "gear_5": "Передача 5",
                "gear_6": "Передача 6",
                "Engine_power_calc": "Расчет мощности двигателя",
                "Engine_air_flow": "Расход воздуха двигателя",
                "Engine_compression": "Степень сжатия двигателя",
                "calculated_gear_ratio": "Расчетное передаточное число",

                # Топливная система
                "system_type": "Тип системы",
                "injector_count": "Количество форсунок",
                "injector_flow": "Производительность форсунки (г/мин)",
                "total_flow": "Общий расход топлива (г/мин)",
                "flow_per_second": "Расход топлива в секунду (г/сек)",
                "bsfc": "Удельный расход топлива (кг/(л.с.*час))",
                "duty_cycle": "Цикл впрыска (%)",
                "injector_open_time": "Время открытия форсунки (мс)",
                "required_volume": "Требуемый объем топлива (г/час)",
                "target_duty": "Целевой цикл впрыска (%)",
                "optimal_flow": "Оптимальный расход топлива (г/мин)",
                "optimal_pressure": "Оптимальное давление (бар)",
                "temperature": "Температура (°C)",
                "temp": "Температура (°C)",
                "note": "Примечание"

            }

            # Создаем диалоговое окно с таблицей
            dialog = QDialog(self)
            dialog.setWindowTitle("История расчетов")
            dialog.resize(1000, 700)

            layout = QVBoxLayout()

            # Таблица для отображения истории
            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels([
                "Дата",
                "Тип расчета",
                "Параметры",
                "Результаты",
                "Действия"
            ])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setWordWrap(True)

            # Заполняем таблицу данными
            table.setRowCount(len(history))
            for row, (id, calc_type, params, results, timestamp) in enumerate(history):
                # Переводим тип расчета
                translated_type = calc_type_translation.get(calc_type, calc_type)
                # Форматируем дату (без времени)
                date_only = timestamp.split()[0]  # Берем только часть до пробела
                # Форматируем параметры
                try:
                    params_dict = eval(params) if isinstance(params, str) else params
                    params_text = "\n".join(
                        f"{param_translation.get(k, k)}: {v}"
                        for k, v in params_dict.items()
                    )
                except Exception as e:
                    print(f"Ошибка форматирования параметров: {e}")
                    params_text = str(params)

                # Форматируем результаты
                try:
                    results_dict = eval(results) if isinstance(results, str) else results
                    results_text = "\n".join(
                        f"{param_translation.get(k, k)}: {v}"
                        for k, v in results_dict.items()
                    )
                except Exception as e:
                    print(f"Ошибка форматирования результатов: {e}")
                    results_text = str(results)

                # Заполняем строку таблицы
                table.setItem(row, 0, QTableWidgetItem(date_only))
                table.setItem(row, 1, QTableWidgetItem(translated_type))
                table.setItem(row, 2, QTableWidgetItem(params_text))
                table.setItem(row, 3, QTableWidgetItem(results_text))

                # Кнопка для загрузки расчета
                load_btn = QPushButton("Загрузить")
                load_btn.clicked.connect(
                    lambda _, r=row: self.load_from_history(history[r][0]))

                cell_widget = QWidget()
                btn_layout = QHBoxLayout(cell_widget)
                btn_layout.addWidget(load_btn)
                btn_layout.setAlignment(Qt.AlignCenter)
                btn_layout.setContentsMargins(0, 0, 0, 0)
                cell_widget.setLayout(btn_layout)
                table.setCellWidget(row, 4, cell_widget)

            # Настройка таблицы
            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)
            table.setColumnWidth(2, 250)  # Ширина колонки параметров
            table.setColumnWidth(3, 250)  # Ширина колонки результатов

            # Фильтр по типам расчетов
            filter_layout = QHBoxLayout()

            type_filter = QComboBox()
            type_filter.addItem("Все типы")
            # Добавляем только переведенные типы расчетов
            unique_types = sorted(set(calc_type_translation.get(h[1], h[1]) for h in history))
            type_filter.addItems(unique_types)

            filter_layout.addWidget(QLabel("Фильтр по типу расчета:"))
            filter_layout.addWidget(type_filter)

            # Кнопки управления
            button_box = QDialogButtonBox()
            export_btn = button_box.addButton("Экспорт в CSV", QDialogButtonBox.ActionRole)
            close_btn = button_box.addButton("Закрыть", QDialogButtonBox.RejectRole)

            # Собираем интерфейс
            layout.addLayout(filter_layout)
            layout.addWidget(table)
            layout.addWidget(button_box)
            dialog.setLayout(layout)

            # Функция для применения фильтра
            def apply_filters():
                filter_text = type_filter.currentText()

                for row in range(table.rowCount()):
                    match_type = (filter_text == "Все типы" or
                                  table.item(row, 1).text() == filter_text)

                    table.setRowHidden(row, not match_type)

            type_filter.currentIndexChanged.connect(apply_filters)

            export_btn.clicked.connect(lambda: self.export_history_to_csv())
            close_btn.clicked.connect(dialog.reject)

            # Показываем диалог
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось загрузить историю:\n{str(e)}"
            )

    def load_from_history(self, record_id):
        """Загружает расчет из истории по ID записи"""
        try:
            # Получаем данные из базы
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT calculation_type, parameters, results FROM calculations WHERE id=?",
                (record_id,)
            )
            record = cursor.fetchone()

            if not record:
                QMessageBox.warning(self, "Ошибка", "Запись не найдена в базе данных")
                return

            calc_type, params_str, results_str = record

            try:
                params = eval(params_str)  # Преобразуем строку в словарь
                results = eval(results_str)
            except:
                QMessageBox.warning(self, "Ошибка", "Не удалось прочитать параметры расчета")
                return

            # Определяем вкладку для загрузки
            tab_index = 0  # По умолчанию первая вкладка

            # ===== ДВИГАТЕЛЬ =====
            if 'engine' in calc_type:
                if 'efficiency' in calc_type:
                    # Загрузка данных КПД двигателя
                    if 'power' in params:
                        self.engine_power_hp.setText(params['power'].split()[0])
                    if 'fuel_consumption' in params:
                        self.engine_fuel_consumption.setText(params['fuel_consumption'].split()[0])
                    if 'fuel_type' in params:
                        fuel_type = params['fuel_type']
                        index = self.engine_fuel_energy.findText(fuel_type, Qt.MatchContains)
                        if index >= 0:
                            self.engine_fuel_energy.setCurrentIndex(index)
                    self.calculate_engine_efficiency()
                    tab_index = 0

                elif 'mep' in calc_type:
                    # Загрузка данных MEP
                    if 'displacement' in params:
                        self.engine_displacement.setText(params['displacement'].split()[0])
                    if 'torque' in params:
                        self.engine_torque.setText(params['torque'].split()[0])
                    self.calculate_mep()
                    tab_index = 0

                elif 'power' in calc_type:
                    # Загрузка расчета мощности
                    if 'torque' in params:
                        self.engine_torque_for_power.setText(params['torque'].split()[0])
                    if 'rpm' in params:
                        self.engine_rpm_for_power.setText(params['rpm'].split()[0])
                    self.calculate_power_from_torque()
                    tab_index = 0

                elif 'air_flow' in calc_type:
                    # Загрузка расхода воздуха
                    if 'displacement' in params:
                        self.engine_displacement_air.setText(params['displacement'].split()[0])
                    if 'rpm' in params:
                        self.engine_rpm_air.setText(params['rpm'].split()[0])
                    if 'volumetric_efficiency' in params:
                        self.engine_volumetric_efficiency.setValue(float(params['volumetric_efficiency']))
                    self.calculate_air_flow()
                    tab_index = 0

                elif 'compression' in calc_type:
                    # Загрузка степени сжатия
                    if 'cylinder_volume' in params:
                        self.engine_cylinder_volume.setText(params['cylinder_volume'].split()[0])
                    if 'chamber_volume' in params:
                        self.engine_combustion_chamber_volume.setText(params['chamber_volume'].split()[0])
                    self.calculate_compression_ratio()
                    tab_index = 0

            # ===== ТРАНСМИССИЯ =====
            if 'transmission' in calc_type:
                # Основные параметры трансмиссии
                if 'final_drive' in params:
                    self.trans_final_drive.setText(str(params['final_drive']))
                if 'tire_diameter' in params:
                    self.trans_tire_diameter.setText(params['tire_diameter'].split()[0])
                if 'redline_rpm' in params:
                    self.trans_redline_rpm.setText(params['redline_rpm'].split()[0])

                # Загрузка передаточных чисел
                if 'gear_ratios' in params:
                    if isinstance(params['gear_ratios'], str):
                        ratios = params['gear_ratios'].split(',')
                    else:
                        ratios = params['gear_ratios']

                    for i, ratio in enumerate(ratios):
                        ratio_clean = str(ratio).strip()
                        if i < len(self.trans_gear_ratios) and ratio_clean:
                            self.trans_gear_ratios[i].setText(ratio_clean)

                # Если это расчет скоростей на передачах
                if 'gear_speeds' in calc_type or 'transmission_gear_speeds' in calc_type:
                    self.calculate_gear_speeds()

                # Если это расчет передаточного отношения
                elif 'ratio_calculation' in calc_type or 'transmission_ratio_calculation' in calc_type:
                    if 'rpm1' in params:
                        self.trans_rpm1.setText(str(params['rpm1']))
                    if 'speed1' in params:
                        self.trans_speed1.setText(str(params['speed1']))
                    if 'rpm2' in params:
                        self.trans_rpm2.setText(str(params['rpm2']))
                    if 'speed2' in params:
                        self.trans_speed2.setText(str(params['speed2']))

                    if 'calculated_ratio' in results:
                        self.trans_calculated_ratio.setText(results['calculated_ratio'])
                    else:
                        self.calculate_gear_ratio_from_speeds()

                # Если это расчет КПД трансмиссии
                elif 'efficiency' in calc_type or 'transmission_efficiency' in calc_type:
                    if 'engine_power' in params:
                        self.trans_engine_power.setText(str(params['engine_power']))
                    if 'wheel_power' in params:
                        self.trans_wheel_power.setText(str(params['wheel_power']))

                    if 'efficiency' in results:
                        self.trans_efficiency_result.setText(results['efficiency'])
                    else:
                        self.calculate_transmission_efficiency()

            # ===== ДИНАМИКА =====
            elif 'dynamics' in calc_type:
                tab_index = 2
                if 'weight' in params:
                    self.dyn_weight.setText(params['weight'].split()[0])
                if 'power_hp' in params:
                    self.dyn_power.setText(params['power_hp'].split()[0])
                if 'torque' in params:
                    self.dyn_torque.setText(params['torque'].split()[0])
                if 'rpm' in params:
                    self.dyn_rpm.setText(params['rpm'].split()[0])

                if 'gear_ratio' in params:
                    self.dyn_gear_ratio.setText(params['gear_ratio'].split()[0])
                if 'final_drive' in params:
                    self.dyn_final_drive.setText(params['final_drive'].split()[0])
                if 'tire_radius' in params:
                    self.dyn_tire_radius.setText(params['tire_radius'].split()[0])

                if 'drag_coef' in params:
                    self.dyn_drag_coef.setValue(float(params['drag_coef']))
                if 'frontal_area' in params:
                    self.dyn_frontal_area.setValue(float(params['frontal_area'].split()[0]))
                if 'rolling_resistance' in params:
                    self.dyn_rolling_resist.setValue(float(params['rolling_resistance']))

                # Автоматически выполняем расчеты
                if 'traction' in calc_type:
                    self.calculate_traction_force()
                elif 'acceleration' in calc_type:
                    self.calculate_acceleration()
                elif 'shift_points' in calc_type:
                    self.calculate_shift_points()

            # ===== ТОРМОЖЕНИЕ =====
            elif 'braking' in calc_type:
                if 'piston_count' in params:
                    self.brake_piston_count.setValue(int(params['piston_count']))
                if 'piston_diameter' in params:
                    self.brake_piston_diameter.setText(params['piston_diameter'].split()[0])
                if 'disc_diameter' in params:
                    self.brake_disc_diameter.setText(params['disc_diameter'].split()[0])
                if 'pad_coef' in params:
                    self.brake_pad_coef.setValue(float(params['pad_coef']))
                if 'pressure' in params:
                    self.brake_fluid_pressure.setText(params['pressure'].split()[0])
                self.calculate_brake_torque()
                tab_index = 4

            # ===== ПОДВЕСКА =====
            elif 'suspension' in calc_type:
                if 'spring_rate' in params:
                    self.suspension_spring_rate.setText(params['spring_rate'].split()[0])
                if 'motion_ratio' in params:
                    self.suspension_motion_ratio.setText(params['motion_ratio'].split()[0])
                self.calculate_wheel_rate()

                if 'weight' in params:
                    self.suspension_weight.setText(params['weight'].split()[0])
                    self.calculate_suspension_frequency()
                tab_index = 5

            # ===== ТОПЛИВНАЯ СИСТЕМА =====
            elif 'fuel' in calc_type:
                if 'injector_count' in params:
                    self.fuel_injector_count.setValue(int(params['injector_count']))
                if 'injector_flow' in params:
                    self.fuel_injector_flow.setText(params['injector_flow'].split()[0])
                if 'pressure' in params:
                    self.fuel_pressure.setText(params['pressure'].split()[0])
                self.calculate_fuel_system_flow()

                if 'engine_power' in params:
                    self.fuel_engine_power.setText(params['engine_power'].split()[0])
                if 'bsfc' in params:
                    self.fuel_bsfc.setText(params['bsfc'].split()[0])
                self.calculate_injector_duty()
                tab_index = 6

            # Переключаемся на соответствующую вкладку
            self.tabs.setCurrentIndex(tab_index)

            # Показываем результаты
            if results:
                result_text = "\n".join([f"{k}: {v}" for k, v in results.items()])
                QMessageBox.information(
                    self,
                    "Результаты загружены",
                    f"Данные успешно загружены из истории.\n\nРезультаты:\n{result_text}"
                )
            else:
                QMessageBox.information(self, "Успех", "Данные успешно загружены из истории")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка загрузки",
                f"Не удалось загрузить расчет:\n{str(e)}"
            )

    def clear_history(self):
        """Очищает историю расчетов с подтверждением"""
        try:
            # Запрос подтверждения
            reply = QMessageBox.question(
                self,
                'Очистка истории',
                'Вы действительно хотите удалить всю историю расчетов?\nЭто действие нельзя отменить.',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Полная очистка таблиц
                cursor = self.db.conn.cursor()

                # Удаляем данные, но сохраняем структуру таблиц
                cursor.execute("DELETE FROM calculations")
                cursor.execute("DELETE FROM reports")

                # Сбрасываем автоинкрементные счетчики
                cursor.execute("UPDATE sqlite_sequence SET seq=0 WHERE name='calculations'")
                cursor.execute("UPDATE sqlite_sequence SET seq=0 WHERE name='reports'")

                self.db.conn.commit()

                QMessageBox.information(
                    self,
                    "История очищена",
                    "Все сохраненные расчеты были удалены.\nСоздайте новые расчеты для заполнения истории."
                )

                # Обновляем интерфейс если открыто окно истории
                if hasattr(self, 'history_window') and self.history_window.isVisible():
                    self.view_history()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка очистки",
                f"Не удалось очистить историю:\n{str(e)}"
            )
            # Восстанавливаем соединение при ошибке
            self.db.create_connection()

    def show_about(self):
        about_text = """<b>Продвинутый калькулятор характеристик автомобиля</b><br><br>
        Версия: 1.0<br>
        Разработчик: Илья Побережный<br><br>
        Возможности программы:<br>
        - Расчет параметров двигателя и трансмиссии<br>
        - Анализ динамических характеристик<br>
        - Расчет тормозной системы<br>
        - Анализ подвески и топливной системы<br>
        - Генерация подробных отчетов<br><br>
        """

        QMessageBox.about(self, "О программе", about_text)

    # ==================== ВКЛАДКА ДВИГАТЕЛЬ ====================
    def create_engine_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # ===== 1. Группа "Эффективный КПД" =====
        eff_group = QGroupBox("Эффективный КПД двигателя")
        eff_layout = QFormLayout()

        self.engine_power_hp = QLineEdit()
        self.engine_fuel_consumption = QLineEdit()
        self.engine_fuel_energy = QComboBox()
        self.engine_fuel_energy.addItems(["Бензин (42.7 МДж/кг)", "Дизель (43.4 МДж/кг)", "Этанол (26.8 МДж/кг)"])

        calculate_eff_btn = QPushButton("Рассчитать КПД")
        calculate_eff_btn.clicked.connect(self.calculate_engine_efficiency)

        self.engine_efficiency_result = QLabel("")
        self.engine_efficiency_result.setStyleSheet("font-weight: bold; color: #0066CC;")

        eff_layout.addRow("Мощность (л.с.):", self.engine_power_hp)
        eff_layout.addRow("Расход топлива (кг/ч):", self.engine_fuel_consumption)
        eff_layout.addRow("Тип топлива:", self.engine_fuel_energy)
        eff_layout.addRow(calculate_eff_btn)
        eff_layout.addRow("Эффективный КПД:", self.engine_efficiency_result)
        eff_group.setLayout(eff_layout)

        # ===== 2. Группа "Среднее эффективное давление" =====
        mep_group = QGroupBox("Среднее эффективное давление (MEP)")
        mep_layout = QFormLayout()

        self.engine_displacement = QLineEdit()
        self.engine_displacement.setPlaceholderText("в см³")
        self.engine_torque = QLineEdit()

        calculate_mep_btn = QPushButton("Рассчитать MEP")
        calculate_mep_btn.clicked.connect(self.calculate_mep)

        self.mep_result = QLabel("")
        self.mep_result.setStyleSheet("font-weight: bold; color: #0066CC;")

        mep_layout.addRow("Рабочий объем:", self.engine_displacement)
        mep_layout.addRow("Крутящий момент (Н·м):", self.engine_torque)
        mep_layout.addRow(calculate_mep_btn)
        mep_layout.addRow("Среднее эффективное давление:", self.mep_result)
        mep_group.setLayout(mep_layout)

        # ===== 3. Группа "Расчет мощности по моменту и оборотам" =====
        power_group = QGroupBox("Расчет мощности по моменту и оборотам")
        power_layout = QFormLayout()

        self.engine_torque_for_power = QLineEdit()
        self.engine_rpm_for_power = QLineEdit()

        calculate_power_btn = QPushButton("Рассчитать мощность")
        calculate_power_btn.clicked.connect(self.calculate_power_from_torque)

        self.power_result = QLabel("")
        self.power_result.setStyleSheet("font-weight: bold; color: #0066CC;")

        power_layout.addRow("Крутящий момент (Н·м):", self.engine_torque_for_power)
        power_layout.addRow("Обороты (об/мин):", self.engine_rpm_for_power)
        power_layout.addRow(calculate_power_btn)
        power_layout.addRow("Мощность:", self.power_result)
        power_group.setLayout(power_layout)

        # ===== 4. Группа "Расход воздуха двигателем" =====
        air_flow_group = QGroupBox("Расход воздуха двигателем")
        air_flow_layout = QFormLayout()

        self.engine_displacement_air = QLineEdit()
        self.engine_rpm_air = QLineEdit()
        self.engine_volumetric_efficiency = QDoubleSpinBox()
        self.engine_volumetric_efficiency.setRange(0.5, 1.2)
        self.engine_volumetric_efficiency.setValue(0.85)

        calculate_air_flow_btn = QPushButton("Рассчитать расход воздуха")
        calculate_air_flow_btn.clicked.connect(self.calculate_air_flow)

        self.air_flow_result = QLabel("")
        self.air_flow_result.setStyleSheet("font-weight: bold; color: #0066CC;")

        air_flow_layout.addRow("Объем двигателя (л):", self.engine_displacement_air)
        air_flow_layout.addRow("Обороты (об/мин):", self.engine_rpm_air)
        air_flow_layout.addRow("КПД наполнения:", self.engine_volumetric_efficiency)
        air_flow_layout.addRow(calculate_air_flow_btn)
        air_flow_layout.addRow("Расход воздуха:", self.air_flow_result)
        air_flow_group.setLayout(air_flow_layout)

        # ===== 5. Группа "Степень сжатия" =====
        compression_group = QGroupBox("Степень сжатия")
        compression_layout = QFormLayout()

        self.engine_cylinder_volume = QLineEdit()
        self.engine_combustion_chamber_volume = QLineEdit()

        calculate_compression_btn = QPushButton("Рассчитать степень сжатия")
        calculate_compression_btn.clicked.connect(self.calculate_compression_ratio)

        self.compression_result = QLabel("")
        self.compression_result.setStyleSheet("font-weight: bold; color: #0066CC;")

        compression_layout.addRow("Объем цилиндра (см³):", self.engine_cylinder_volume)
        compression_layout.addRow("Объем камеры сгорания (см³):", self.engine_combustion_chamber_volume)
        compression_layout.addRow(calculate_compression_btn)
        compression_layout.addRow("Степень сжатия:", self.compression_result)
        compression_group.setLayout(compression_layout)

        # Добавляем все группы на вкладку
        layout.addWidget(eff_group)
        layout.addWidget(mep_group)
        layout.addWidget(power_group)
        layout.addWidget(air_flow_group)
        layout.addWidget(compression_group)
        layout.addStretch()

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Двигатель")

    def calculate_engine_efficiency(self):
        try:
            power_hp = float(self.engine_power_hp.text())
            fuel_consumption = float(self.engine_fuel_consumption.text())
            fuel_type = self.engine_fuel_energy.currentText()

            fuel_energy = {
                "Бензин (42.7 МДж/кг)": 42.7,
                "Дизель (43.4 МДж/кг)": 43.4,
                "Этанол (26.8 МДж/кг)": 26.8
            }[fuel_type]

            power_kw = power_hp * 0.7355
            fuel_energy_kj = fuel_consumption * fuel_energy * 1000
            efficiency = (power_kw * 3600) / fuel_energy_kj

            self.engine_efficiency_result.setText(f"{efficiency * 100:.1f}%")

            # Сохранение для отчета
            self.report_data['engine'] = {
                'power_hp': power_hp,
                'fuel_consumption': fuel_consumption,
                'fuel_type': fuel_type,
                'efficiency': f"{efficiency * 100:.1f}%"
            }

            # Сохранение в БД
            self.db.save_calculation(
                'engine_efficiency',
                {
                    'power': f"{power_hp} л.с.",
                    'fuel_consumption': f"{fuel_consumption} кг/ч",
                    'fuel_type': fuel_type.split()[0]
                },
                {'efficiency': f"{efficiency * 100:.1f}%"}
            )

            self.update_report_tab()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректные числовые значения")

    def calculate_mep(self):
        try:
            displacement = float(self.engine_displacement.text()) / 1e6  # в м³
            torque = float(self.engine_torque.text())

            mep = (2 * math.pi * torque * 4) / displacement
            mep_bar = mep / 1e5  # в бар
            mep_kgcm2 = mep_bar / 10.197

            self.mep_result.setText(f"{mep_bar:.2f} бар ({(mep_kgcm2):.2f} кгс/см²)")

            # Сохранение для отчета
            if 'engine' not in self.report_data:
                self.report_data['engine'] = {}
            self.report_data['engine'].update({
                'displacement': f"{displacement * 1e6:.0f} см³",
                'torque': f"{torque:.1f} Н·м",
                'mep': f"{mep_bar:.2f} бар",
                'mep_kgcm2': f"{mep_kgcm2:.2f} кгс/см²"
            })

            # Сохранение в БД
            self.db.save_calculation(
                'engine_mep',
                {
                    'displacement': f"{displacement * 1e6:.0f} см³",
                    'torque': f"{torque:.1f} Н·м"
                },
                {
                    'mep_bar': f"{mep_bar:.2f} бар",
                    'mep_kgcm2': f"{mep_kgcm2:.2f} кгс/см²"
                }
            )

            self.update_report_tab()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите рабочий объем и крутящий момент")

    def calculate_power_from_torque(self):
        try:
            torque = float(self.engine_torque_for_power.text())
            rpm = float(self.engine_rpm_for_power.text())

            power_hp = (torque * rpm) / 7024
            power_kw = power_hp * 0.7355

            self.power_result.setText(f"{power_hp:.1f} л.с. ({power_kw:.1f} кВт)")

            # Сохранение для отчета
            self.report_data['engine_power_calc'] = {
                'torque': f"{torque:.1f} Н·м",
                'rpm': f"{rpm:.0f} об/мин",
                'power_hp': f"{power_hp:.1f} л.с.",
                'power_kw': f"{power_kw:.1f} кВт"
            }

            # Сохранение в БД
            self.db.save_calculation(
                'engine_power',
                {
                    'torque': f"{torque:.1f} Н·м",
                    'rpm': f"{rpm:.0f} об/мин"
                },
                {
                    'power_hp': f"{power_hp:.1f} л.с.",
                    'power_kw': f"{power_kw:.1f} кВт"
                }
            )

            self.update_report_tab()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректные значения момента и оборотов")

    def calculate_air_flow(self):
        try:
            displacement = float(self.engine_displacement_air.text())  # в литрах
            rpm = float(self.engine_rpm_air.text())
            efficiency = self.engine_volumetric_efficiency.value()

            air_density = 1.2  # кг/м³
            air_flow = (displacement * rpm * efficiency * air_density) / 120  # кг/ч

            self.air_flow_result.setText(f"{air_flow:.2f} кг/ч")

            # Сохранение для отчета
            self.report_data['engine_air_flow'] = {
                'displacement': f"{displacement:.1f} л",
                'rpm': f"{rpm:.0f} об/мин",
                'volumetric_efficiency': f"{efficiency:.2f}",
                'air_flow': f"{air_flow:.2f} кг/ч"
            }

            # Сохранение в БД
            self.db.save_calculation(
                'engine_air_flow',
                {
                    'displacement': f"{displacement:.1f} л",
                    'rpm': f"{rpm:.0f} об/мин",
                    'volumetric_efficiency': f"{efficiency:.2f}"
                },
                {'air_flow': f"{air_flow:.2f} кг/ч"}
            )

            self.update_report_tab()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите объем двигателя и обороты")

    def calculate_compression_ratio(self):
        try:
            cylinder_volume = float(self.engine_cylinder_volume.text())  # см³
            chamber_volume = float(self.engine_combustion_chamber_volume.text())  # см³

            compression_ratio = (cylinder_volume + chamber_volume) / chamber_volume

            self.compression_result.setText(f"{compression_ratio:.2f}:1")

            # Сохранение для отчета
            self.report_data['engine_compression'] = {
                'cylinder_volume': f"{cylinder_volume:.1f} см³",
                'chamber_volume': f"{chamber_volume:.1f} см³",
                'compression_ratio': f"{compression_ratio:.2f}:1"
            }

            # Сохранение в БД
            self.db.save_calculation(
                'engine_compression',
                {
                    'cylinder_volume': f"{cylinder_volume:.1f} см³",
                    'chamber_volume': f"{chamber_volume:.1f} см³"
                },
                {'compression_ratio': f"{compression_ratio:.2f}:1"}
            )

            self.update_report_tab()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите объемы цилиндра и камеры сгорания")

    # ==================== ВКЛАДКА ТРАНСМИССИЯ ====================
    def create_transmission_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Группа "Основные параметры трансмиссии"
        main_params_group = QGroupBox("Основные параметры трансмиссии")
        main_params_layout = QFormLayout()

        self.trans_gear_ratios = []
        for i in range(6):
            ratio_input = QLineEdit()
            ratio_input.setPlaceholderText(f"Передача {i + 1}")
            self.trans_gear_ratios.append(ratio_input)
            main_params_layout.addRow(f"Передача {i + 1}:", ratio_input)

        self.trans_final_drive = QLineEdit()
        self.trans_tire_diameter = QLineEdit()
        self.trans_tire_diameter.setPlaceholderText("в мм")
        self.trans_redline_rpm = QLineEdit("6500")
        self.trans_redline_rpm.setPlaceholderText("об/мин")

        calculate_gear_btn = QPushButton("Рассчитать скорости на передачах")
        calculate_gear_btn.clicked.connect(self.calculate_gear_speeds)

        main_params_layout.addRow("Главная передача:", self.trans_final_drive)
        main_params_layout.addRow("Диаметр колеса:", self.trans_tire_diameter)
        main_params_layout.addRow("Макс. обороты двигателя:", self.trans_redline_rpm)
        main_params_layout.addRow(calculate_gear_btn)
        main_params_group.setLayout(main_params_layout)

        # Группа "Результаты расчета скоростей"
        speeds_group = QGroupBox("Скорости на передачах")
        speeds_layout = QVBoxLayout()

        self.gear_speeds_result = QTextEdit()
        self.gear_speeds_result.setReadOnly(True)
        self.gear_speeds_result.setStyleSheet("font-family: monospace;")
        speeds_layout.addWidget(self.gear_speeds_result)
        speeds_group.setLayout(speeds_layout)

        # Группа "Расчет передаточных отношений"
        ratio_group = QGroupBox("Расчет передаточных отношений")
        ratio_layout = QFormLayout()

        self.trans_rpm1 = QLineEdit()
        self.trans_rpm1.setPlaceholderText("об/мин")
        self.trans_speed1 = QLineEdit()
        self.trans_speed1.setPlaceholderText("км/ч")
        self.trans_rpm2 = QLineEdit()
        self.trans_rpm2.setPlaceholderText("об/мин")
        self.trans_speed2 = QLineEdit()
        self.trans_speed2.setPlaceholderText("км/ч")

        calculate_ratio_btn = QPushButton("Рассчитать передаточное отношение")
        calculate_ratio_btn.clicked.connect(self.calculate_gear_ratio_from_speeds)

        self.trans_calculated_ratio = QLabel("")
        self.trans_calculated_ratio.setStyleSheet("font-weight: bold; color: #0066CC;")

        ratio_layout.addRow("Обороты 1:", self.trans_rpm1)
        ratio_layout.addRow("Скорость 1:", self.trans_speed1)
        ratio_layout.addRow("Обороты 2:", self.trans_rpm2)
        ratio_layout.addRow("Скорость 2:", self.trans_speed2)
        ratio_layout.addRow(calculate_ratio_btn)
        ratio_layout.addRow("Передаточное отношение:", self.trans_calculated_ratio)
        ratio_group.setLayout(ratio_layout)

        # Группа "Расчет эффективности трансмиссии"
        efficiency_group = QGroupBox("Расчет эффективности трансмиссии")
        efficiency_layout = QFormLayout()

        self.trans_engine_power = QLineEdit()
        self.trans_engine_power.setPlaceholderText("л.с.")
        self.trans_wheel_power = QLineEdit()
        self.trans_wheel_power.setPlaceholderText("л.с.")

        calculate_efficiency_btn = QPushButton("Рассчитать КПД трансмиссии")
        calculate_efficiency_btn.clicked.connect(self.calculate_transmission_efficiency)

        self.trans_efficiency_result = QLabel("")
        self.trans_efficiency_result.setStyleSheet("font-weight: bold; color: #0066CC;")

        efficiency_layout.addRow("Мощность двигателя:", self.trans_engine_power)
        efficiency_layout.addRow("Мощность на колесах:", self.trans_wheel_power)
        efficiency_layout.addRow(calculate_efficiency_btn)
        efficiency_layout.addRow("КПД трансмиссии:", self.trans_efficiency_result)
        efficiency_group.setLayout(efficiency_layout)

        # Добавляем все группы на вкладку
        layout.addWidget(main_params_group)
        layout.addWidget(speeds_group)
        layout.addWidget(ratio_group)
        layout.addWidget(efficiency_group)
        layout.addStretch()

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Трансмиссия")

    def calculate_gear_speeds(self):
        try:
            final_drive = float(self.trans_final_drive.text())
            tire_diameter = float(self.trans_tire_diameter.text()) / 1000  # в метрах
            redline_rpm = float(self.trans_redline_rpm.text())
            gear_ratios = []

            for ratio_input in self.trans_gear_ratios:
                if ratio_input.text():
                    gear_ratios.append(float(ratio_input.text()))

            if not gear_ratios:
                raise ValueError("Введите хотя бы одну передачу")

            wheel_circumference = math.pi * tire_diameter
            results = []
            speed_data = {}

            # Форматируем вывод в виде таблицы
            header = "Передача | Передаточное | Скорость при {} об/мин".format(redline_rpm)
            separator = "-" * len(header)
            results.append(header)
            results.append(separator)

            for i, gear_ratio in enumerate(gear_ratios):
                total_ratio = gear_ratio * final_drive
                speed_ms = (redline_rpm * wheel_circumference) / (total_ratio * 60)
                speed_kmh = speed_ms * 3.6
                results.append(f"{i + 1:^7} | {gear_ratio:^12.2f} | {speed_kmh:^18.1f} км/ч")
                speed_data[f"gear_{i + 1}"] = f"{speed_kmh:.1f} км/ч"

            self.gear_speeds_result.setText("\n".join(results))

            # Сохраняем для отчета
            self.report_data['transmission'] = {
                'gear_ratios': [f"{gr:.2f}" for gr in gear_ratios],
                'final_drive': f"{final_drive:.2f}",
                'tire_diameter': f"{tire_diameter * 1000:.0f} мм",
                'redline_rpm': f"{redline_rpm:.0f} об/мин",
                'speeds_at_redline': speed_data
            }

            # Сохраняем в базу данных
            params = {
                'gear_ratios': ', '.join([f"{gr:.2f}" for gr in gear_ratios]),
                'final_drive': final_drive,
                'tire_diameter': f"{tire_diameter * 1000:.0f} мм",
                'redline_rpm': f"{redline_rpm:.0f} об/мин"
            }
            self.db.save_calculation('transmission_gear_speeds', params, speed_data)

            self.update_report_tab()

        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def calculate_gear_ratio_from_speeds(self):
        """Расчет передаточного отношения по оборотам и скорости"""
        try:
            rpm1 = float(self.trans_rpm1.text())
            speed1 = float(self.trans_speed1.text())
            rpm2 = float(self.trans_rpm2.text())
            speed2 = float(self.trans_speed2.text())

            if speed1 == 0 or speed2 == 0:
                raise ValueError("Скорость не может быть нулевой")

            ratio = (rpm1 * speed2) / (rpm2 * speed1)
            self.trans_calculated_ratio.setText(f"{ratio:.3f}")

            # Сохраняем для отчета
            if 'transmission' not in self.report_data:
                self.report_data['transmission'] = {}
            self.report_data['transmission'].update({
                'calculated_gear_ratio': {
                    'rpm1': f"{rpm1:.0f} об/мин",
                    'speed1': f"{speed1:.1f} км/ч",
                    'rpm2': f"{rpm2:.0f} об/мин",
                    'speed2': f"{speed2:.1f} км/ч",
                    'calculated_ratio': f"{ratio:.3f}"
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'transmission_ratio_calculation',
                {
                    'rpm1': rpm1,
                    'speed1': speed1,
                    'rpm2': rpm2,
                    'speed2': speed2
                },
                {'calculated_ratio': ratio}
            )

            self.update_report_tab()

        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", f"Пожалуйста, введите корректные значения\n{str(e)}")

    def calculate_transmission_efficiency(self):
        """Расчет КПД трансмиссии"""
        try:
            engine_power = float(self.trans_engine_power.text())
            wheel_power = float(self.trans_wheel_power.text())

            if engine_power <= 0:
                raise ValueError("Мощность двигателя должна быть больше 0")

            efficiency = (wheel_power / engine_power) * 100
            self.trans_efficiency_result.setText(f"{efficiency:.1f}%")

            # Сохраняем для отчета
            if 'transmission' not in self.report_data:
                self.report_data['transmission'] = {}
            self.report_data['transmission'].update({
                'transmission_efficiency': {
                    'engine_power': f"{engine_power:.1f} л.с.",
                    'wheel_power': f"{wheel_power:.1f} л.с.",
                    'efficiency': f"{efficiency:.1f}%"
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'transmission_efficiency',
                {
                    'engine_power': engine_power,
                    'wheel_power': wheel_power
                },
                {'efficiency': f"{efficiency:.1f}%"}
            )

            self.update_report_tab()

        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", f"Пожалуйста, введите корректные значения мощности\n{str(e)}")

    # ==================== ВКЛАДКА ДИНАМИКА ====================
    def create_dynamics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Группа "Основные параметры"
        params_group = QGroupBox("Основные параметры")
        params_layout = QFormLayout()

        self.dyn_weight = QLineEdit()
        self.dyn_weight.setPlaceholderText("кг")
        self.dyn_power = QLineEdit()
        self.dyn_power.setPlaceholderText("л.с.")
        self.dyn_torque = QLineEdit()
        self.dyn_torque.setPlaceholderText("Н·м")
        self.dyn_rpm = QLineEdit("5500")
        self.dyn_rpm.setPlaceholderText("об/мин")

        params_layout.addRow("Масса автомобиля:", self.dyn_weight)
        params_layout.addRow("Мощность двигателя:", self.dyn_power)
        params_layout.addRow("Крутящий момент:", self.dyn_torque)
        params_layout.addRow("Обороты максимального момента:", self.dyn_rpm)
        params_group.setLayout(params_layout)

        # Группа "Тяговая характеристика"
        traction_group = QGroupBox("Тяговая характеристика")
        traction_layout = QFormLayout()

        self.dyn_gear_ratio = QLineEdit("3.5")
        self.dyn_final_drive = QLineEdit("4.1")
        self.dyn_tire_radius = QLineEdit("0.33")
        self.dyn_tire_radius.setPlaceholderText("в метрах")

        calculate_traction_btn = QPushButton("Рассчитать тяговую силу")
        calculate_traction_btn.clicked.connect(self.calculate_traction_force)

        traction_layout.addRow("Передаточное число:", self.dyn_gear_ratio)
        traction_layout.addRow("Главная передача:", self.dyn_final_drive)
        traction_layout.addRow("Радиус колеса:", self.dyn_tire_radius)
        traction_layout.addRow(calculate_traction_btn)
        traction_group.setLayout(traction_layout)

        # Группа "Разгонная динамика"
        acceleration_group = QGroupBox("Разгонная динамика")
        acceleration_layout = QFormLayout()

        self.dyn_drag_coef = QDoubleSpinBox()
        self.dyn_drag_coef.setRange(0.20, 1.50)
        self.dyn_drag_coef.setValue(0.35)
        self.dyn_frontal_area = QDoubleSpinBox()
        self.dyn_frontal_area.setRange(1.5, 3.5)
        self.dyn_frontal_area.setValue(2.2)
        self.dyn_rolling_resist = QDoubleSpinBox()
        self.dyn_rolling_resist.setRange(0.01, 0.05)
        self.dyn_rolling_resist.setValue(0.015)

        calculate_accel_btn = QPushButton("Рассчитать разгон")
        calculate_accel_btn.clicked.connect(self.calculate_acceleration)

        self.dyn_shift_points = QPushButton("Оптимальные точки переключения")
        self.dyn_shift_points.clicked.connect(self.calculate_shift_points)

        acceleration_layout.addRow("Коэф. аэродинамического сопротивления:", self.dyn_drag_coef)
        acceleration_layout.addRow("Лобовая площадь (м²):", self.dyn_frontal_area)
        acceleration_layout.addRow("Коэф. сопротивления качению:", self.dyn_rolling_resist)
        acceleration_layout.addRow(calculate_accel_btn)
        acceleration_layout.addRow(self.dyn_shift_points)
        acceleration_group.setLayout(acceleration_layout)

        # Группа "Результаты"
        results_group = QGroupBox("Результаты расчетов")
        results_layout = QVBoxLayout()

        self.dyn_results = QTextEdit()
        self.dyn_results.setReadOnly(True)
        self.dyn_results.setStyleSheet("font-family: monospace;")

        results_layout.addWidget(self.dyn_results)
        results_group.setLayout(results_layout)

        # Добавляем все группы на вкладку
        layout.addWidget(params_group)
        layout.addWidget(traction_group)
        layout.addWidget(acceleration_group)
        layout.addWidget(results_group)
        layout.addStretch()

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Динамика")

    def calculate_traction_force(self):
        """Расчет тяговой силы на колесах"""
        try:
            # Получаем значения из полей ввода
            torque = float(self.dyn_torque.text()) if self.dyn_torque.text() else 0
            gear_ratio = float(self.dyn_gear_ratio.text()) if self.dyn_gear_ratio.text() else 0
            final_drive = float(self.dyn_final_drive.text()) if self.dyn_final_drive.text() else 0
            tire_radius = float(self.dyn_tire_radius.text()) if self.dyn_tire_radius.text() else 0

            if tire_radius == 0:
                raise ValueError("Радиус колеса не может быть нулевым")

            # Расчет тяговой силы (F = T * i * η / r)
            traction_force = (torque * gear_ratio * final_drive * 0.9) / tire_radius  # η ≈ 0.9 (КПД)
            equivalent_force = traction_force / 9.81

            # Вывод результатов
            self.dyn_results.clear()
            self.dyn_results.append("=== РЕЗУЛЬТАТЫ РАСЧЕТА ТЯГОВОЙ СИЛЫ ===")
            self.dyn_results.append(f"Крутящий момент двигателя: {torque} Н·м")
            self.dyn_results.append(f"Суммарное передаточное число: {gear_ratio * final_drive:.2f}")
            self.dyn_results.append(f"Тяговая сила на колесах: {traction_force:.2f} Н")
            self.dyn_results.append(f"Эквивалентная тяга: {equivalent_force:.2f} кгс")

            # Сохраняем для отчета
            if 'dynamics' not in self.report_data:
                self.report_data['dynamics'] = {}
            self.report_data['dynamics'].update({
                'traction_force': {
                    'torque': f"{torque} Н·м",
                    'gear_ratio': f"{gear_ratio * final_drive:.2f}",
                    'traction_force': f"{traction_force:.2f} Н",
                    'equivalent_force': f"{equivalent_force:.2f} кгс"
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'traction_force',
                {
                    'torque': torque,
                    'gear_ratio': gear_ratio,
                    'final_drive': final_drive,
                    'tire_radius': tire_radius
                },
                {
                    'traction_force': traction_force,
                    'equivalent_force': equivalent_force
                }
            )

            self.update_report_tab()

        except Exception as e:
            self.dyn_results.append(f"Ошибка расчета: {str(e)}")

    def calculate_acceleration(self):
        """Расчет разгонной динамики автомобиля"""
        try:
            # Получаем параметры из полей ввода
            weight = float(self.dyn_weight.text()) if self.dyn_weight.text() else 0
            power = float(self.dyn_power.text()) if self.dyn_power.text() else 0
            drag_coef = self.dyn_drag_coef.value()
            frontal_area = self.dyn_frontal_area.value()
            rolling_resist = self.dyn_rolling_resist.value()

            if weight == 0:
                raise ValueError("Масса автомобиля не может быть нулевой")

            # Расчет удельной мощности (л.с./т)
            specific_power = (power * 1000) / (weight * 9.81)  # Переводим в кВт/т

            # Расчет теоретической максимальной скорости (упрощенный)
            rho = 1.225  # Плотность воздуха кг/м3
            max_speed = (2 * power * 735.5 / (rho * drag_coef * frontal_area)) ** (1 / 3)  # м/с

            # Расчет времени разгона 0-100 км/ч (эмпирическая формула)
            t_0_100 = 2.5 * math.sqrt(weight / (power * 0.7))  # Примерная формула

            # Вывод результатов
            self.dyn_results.clear()
            self.dyn_results.append("=== РЕЗУЛЬТАТЫ РАСЧЕТА РАЗГОНА ===")
            self.dyn_results.append(f"Удельная мощность: {specific_power:.2f} кВт/т")
            self.dyn_results.append(f"Теоретическая макс. скорость: {max_speed * 3.6:.1f} км/ч")
            self.dyn_results.append(f"Примерное время 0-100 км/ч: {t_0_100:.2f} сек")
            self.dyn_results.append("\nПримечание: расчеты приблизительные")

            # Сохраняем для отчета
            if 'dynamics' not in self.report_data:
                self.report_data['dynamics'] = {}
            self.report_data['dynamics'].update({
                'acceleration': {
                    'specific_power': f"{specific_power:.2f} кВт/т",
                    'max_speed': f"{max_speed * 3.6:.1f} км/ч",
                    'acceleration_0_100': f"{t_0_100:.2f} сек"
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'acceleration',
                {
                    'weight': weight,
                    'power': power,
                    'drag_coef': drag_coef,
                    'frontal_area': frontal_area,
                    'rolling_resist': rolling_resist
                },
                {
                    'specific_power': specific_power,
                    'max_speed': max_speed * 3.6,
                    'acceleration_0_100': t_0_100
                }
            )

            self.update_report_tab()

        except Exception as e:
            self.dyn_results.append(f"Ошибка расчета: {str(e)}")

    def calculate_shift_points(self):
        """Расчет оптимальных точек переключения передач"""
        try:
            rpm = float(self.dyn_rpm.text()) if self.dyn_rpm.text() else 0
            power = float(self.dyn_power.text()) if self.dyn_power.text() else 0
            torque = float(self.dyn_torque.text()) if self.dyn_torque.text() else 0

            if rpm == 0 or power == 0 or torque == 0:
                raise ValueError("Не все параметры двигателя указаны")

            # Расчет оптимальных точек переключения (обычно на 10-15% выше пика мощности)
            shift_rpm = rpm * 1.1

            # Расчет скорости на каждой передаче (примерные передаточные числа)
            gear_ratios = [3.5, 2.1, 1.5, 1.1, 0.9]  # Пример для 5-ступенчатой КПП
            final_drive = 4.1
            tire_radius = 0.33

            self.dyn_results.clear()
            self.dyn_results.append("=== ОПТИМАЛЬНЫЕ ТОЧКИ ПЕРЕКЛЮЧЕНИЯ ===")
            self.dyn_results.append(f"Рекомендуемые обороты переключения: {shift_rpm:.0f} об/мин")

            shift_speeds = {}
            for i, gear in enumerate(gear_ratios, 1):
                speed = (shift_rpm * 60 * 2 * math.pi * tire_radius) / (gear * final_drive * 1000) * 3.6
                self.dyn_results.append(f"Передача {i}: {speed:.1f} км/ч при {shift_rpm:.0f} об/мин")
                shift_speeds[f'gear_{i}'] = f"{speed:.1f} км/ч"

            self.dyn_results.append("\nПримечание: расчет для стандартных передаточных чисел")

            # Сохраняем для отчета
            if 'dynamics' not in self.report_data:
                self.report_data['dynamics'] = {}
            self.report_data['dynamics'].update({
                'shift_points': {
                    'optimal_rpm': f"{shift_rpm:.0f} об/мин",
                    **shift_speeds
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'shift_points',
                {
                    'rpm': rpm,
                    'power': power,
                    'torque': torque,
                    'gear_ratios': gear_ratios,
                    'final_drive': final_drive,
                    'tire_radius': tire_radius
                },
                {
                    'optimal_rpm': shift_rpm,
                    **{k: float(v.split()[0]) for k, v in shift_speeds.items()}
                }
            )

            self.update_report_tab()

        except Exception as e:
            self.dyn_results.append(f"Ошибка расчета: {str(e)}")

    # ==================== ВКЛАДКА АЭРОДИНАМИКА ====================


    # ==================== ВКЛАДКА ТОРМОЖЕНИЕ ====================
    def create_braking_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout()

        # Основная группа с тормозными параметрами
        brake_group = QGroupBox("Тормозные характеристики")
        brake_layout = QGridLayout()

        # Параметры тормозной системы (левый столбец)
        brake_layout.addWidget(QLabel("Число поршней:"), 0, 0)
        self.brake_piston_count = QSpinBox()
        self.brake_piston_count.setRange(1, 12)
        self.brake_piston_count.setValue(4)
        brake_layout.addWidget(self.brake_piston_count, 0, 1)

        brake_layout.addWidget(QLabel("Диаметр поршня:"), 1, 0)
        self.brake_piston_diameter = QLineEdit()
        self.brake_piston_diameter.setPlaceholderText("в мм")
        brake_layout.addWidget(self.brake_piston_diameter, 1, 1)

        brake_layout.addWidget(QLabel("Диаметр диска:"), 2, 0)
        self.brake_disc_diameter = QLineEdit()
        self.brake_disc_diameter.setPlaceholderText("в мм")
        brake_layout.addWidget(self.brake_disc_diameter, 2, 1)

        brake_layout.addWidget(QLabel("Коэф. трения колодок:"), 3, 0)
        self.brake_pad_coef = QDoubleSpinBox()
        self.brake_pad_coef.setRange(0.2, 0.7)
        self.brake_pad_coef.setValue(0.4)
        brake_layout.addWidget(self.brake_pad_coef, 3, 1)

        brake_layout.addWidget(QLabel("Давление в системе:"), 4, 0)
        self.brake_fluid_pressure = QLineEdit()
        self.brake_fluid_pressure.setPlaceholderText("в бар")
        brake_layout.addWidget(self.brake_fluid_pressure, 4, 1)

        # Параметры для расчета (правый столбец)
        brake_layout.addWidget(QLabel("Масса автомобиля:"), 0, 2)
        self.brake_vehicle_weight = QLineEdit()
        self.brake_vehicle_weight.setPlaceholderText("в кг")
        brake_layout.addWidget(self.brake_vehicle_weight, 0, 3)

        brake_layout.addWidget(QLabel("Скорость:"), 1, 2)
        self.brake_speed = QLineEdit()
        self.brake_speed.setPlaceholderText("в км/ч")
        brake_layout.addWidget(self.brake_speed, 1, 3)

        brake_layout.addWidget(QLabel("Коэф. сцепления:"), 2, 2)
        self.brake_road_coef = QDoubleSpinBox()
        self.brake_road_coef.setRange(0.1, 1.2)
        self.brake_road_coef.setValue(0.8)
        brake_layout.addWidget(self.brake_road_coef, 2, 3)

        brake_layout.addWidget(QLabel("Баланс (передние):"), 3, 2)
        self.brake_front_percent = QDoubleSpinBox()
        self.brake_front_percent.setRange(30, 70)
        self.brake_front_percent.setValue(60)
        self.brake_front_percent.setSuffix("%")
        brake_layout.addWidget(self.brake_front_percent, 3, 3)

        # Кнопки расчетов (нижний ряд)
        button_row = QHBoxLayout()

        calculate_brake_btn = QPushButton("Рассчитать тормозной момент")
        calculate_brake_btn.clicked.connect(self.calculate_brake_torque)
        button_row.addWidget(calculate_brake_btn)

        calculate_stopping_btn = QPushButton("Рассчитать тормозной путь")
        calculate_stopping_btn.clicked.connect(self.calculate_stopping_distance)
        button_row.addWidget(calculate_stopping_btn)

        calculate_balance_btn = QPushButton("Рассчитать баланс тормозов")
        calculate_balance_btn.clicked.connect(self.calculate_brake_balance)
        button_row.addWidget(calculate_balance_btn)

        calculate_temp_btn = QPushButton("Рассчитать нагрев тормозов")
        calculate_temp_btn.clicked.connect(self.calculate_brake_temperature)
        button_row.addWidget(calculate_temp_btn)

        # Результаты
        self.brake_result = QTextEdit()
        self.brake_result.setReadOnly(True)
        self.brake_result.setStyleSheet("font-weight: bold; color: #000000;")

        # Собираем все вместе
        brake_group.setLayout(brake_layout)

        main_layout.addWidget(brake_group)
        main_layout.addLayout(button_row)
        main_layout.addWidget(self.brake_result)

        tab.setLayout(main_layout)
        self.tabs.addTab(tab, "Торможение")

    def calculate_brake_torque(self):
        """Расчет тормозного момента"""
        try:
            piston_count = self.brake_piston_count.value()
            piston_dia = float(self.brake_piston_diameter.text()) / 1000  # в метрах
            disc_dia = float(self.brake_disc_diameter.text()) / 1000
            pad_coef = self.brake_pad_coef.value()
            pressure = float(self.brake_fluid_pressure.text()) * 1e5  # бар в Па

            piston_area = math.pi * (piston_dia ** 2) / 4
            piston_force = pressure * piston_area
            normal_force = piston_force * piston_count
            effective_radius = 0.4 * (disc_dia / 2)  # Эффективный радиус
            brake_torque = normal_force * pad_coef * effective_radius

            result_text = (
                "=== ТОРМОЗНОЙ МОМЕНТ ===\n"
                f"Число поршней: {piston_count}\n"
                f"Диаметр поршня: {piston_dia * 1000:.1f} мм\n"
                f"Диаметр диска: {disc_dia * 1000:.1f} мм\n"
                f"Коэф. трения: {pad_coef:.2f}\n"
                f"Давление: {pressure / 1e5:.1f} бар\n"
                f"Тормозной момент: {brake_torque:.1f} Н·м\n"
                f"Сила трения: {normal_force * pad_coef:.1f} Н"
            )
            self.brake_result.setText(result_text)

            # Сохраняем для отчета
            if 'braking' not in self.report_data:
                self.report_data['braking'] = {}
            self.report_data['braking'].update({
                'brake_torque': {
                    'piston_count': piston_count,
                    'piston_diameter': f"{piston_dia * 1000:.1f} мм",
                    'disc_diameter': f"{disc_dia * 1000:.1f} мм",
                    'pad_coef': f"{pad_coef:.2f}",
                    'pressure': f"{pressure / 1e5:.1f} бар",
                    'brake_torque': f"{brake_torque:.1f} Н·м",
                    'friction_force': f"{normal_force * pad_coef:.1f} Н"
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'brake_torque',
                {
                    'piston_count': piston_count,
                    'piston_diameter': piston_dia,
                    'disc_diameter': disc_dia,
                    'pad_coef': pad_coef,
                    'pressure': pressure / 1e5
                },
                {
                    'brake_torque': brake_torque,
                    'friction_force': normal_force * pad_coef
                }
            )

            self.update_report_tab()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите параметры тормозов")

    def calculate_stopping_distance(self):
        """Расчет тормозного пути"""
        try:
            speed = float(self.brake_speed.text())
            weight = float(self.brake_vehicle_weight.text())
            road_coef = self.brake_road_coef.value()
            front_percent = self.brake_front_percent.value() / 100

            if weight == 0:
                raise ValueError("Масса не может быть нулевой")

            # Переводим скорость из км/ч в м/с
            speed_mps = speed / 3.6
            # Учитываем перераспределение веса при торможении (примерно 30% смещение)
            front_load = weight * 9.81 * (front_percent + 0.3)
            rear_load = weight * 9.81 * ((1 - front_percent) - 0.3)

            # Тормозной путь: S = v² / (2 * μ * g)
            stopping_distance = (speed_mps ** 2) / (2 * road_coef * 9.81)
            deceleration = road_coef * 9.81  # м/с²
            stopping_time = speed_mps / deceleration

            result_text = (
                "=== ТОРМОЗНОЙ ПУТЬ ===\n"
                f"Скорость: {speed} км/ч\n"
                f"Масса: {weight} кг\n"
                f"Коэф. сцепления: {road_coef:.2f}\n"
                f"Нагрузка на перед: {front_load:.1f} Н\n"
                f"Нагрузка на зад: {rear_load:.1f} Н\n"
                f"Тормозной путь: {stopping_distance:.2f} м\n"
                f"Время торможения: {stopping_time:.2f} с\n"
                f"Замедление: {deceleration / 9.81:.1f} g"
            )
            self.brake_result.setText(result_text)

            # Сохраняем для отчета
            if 'braking' not in self.report_data:
                self.report_data['braking'] = {}
            self.report_data['braking'].update({
                'stopping_distance': {
                    'speed': f"{speed} км/ч",
                    'weight': f"{weight} кг",
                    'road_coef': f"{road_coef:.2f}",
                    'front_load': f"{front_load:.1f} Н",
                    'rear_load': f"{rear_load:.1f} Н",
                    'stopping_distance': f"{stopping_distance:.2f} м",
                    'stopping_time': f"{stopping_time:.2f} с",
                    'deceleration': f"{deceleration / 9.81:.1f} g"
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'stopping_distance',
                {
                    'speed': speed,
                    'weight': weight,
                    'road_coef': road_coef,
                    'front_percent': front_percent
                },
                {
                    'stopping_distance': stopping_distance,
                    'stopping_time': stopping_time,
                    'deceleration': deceleration
                }
            )

            self.update_report_tab()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректные параметры")

    def calculate_brake_balance(self):
        """Расчет баланса тормозных сил"""
        try:
            front_percent = self.brake_front_percent.value() / 100
            brake_torque = float(self.brake_result.toPlainText().split("Тормозной момент: ")[1].split(" Н·м")[0])
            weight = float(self.brake_vehicle_weight.text()) if self.brake_vehicle_weight.text() else 0

            if weight == 0:
                raise ValueError("Введите массу автомобиля")

            # Расчет распределения тормозных сил
            front_force = brake_torque * front_percent
            rear_force = brake_torque * (1 - front_percent)
            optimal_percent = 0.6 + (weight - 1000) * 0.0001  # Эмпирическая формула

            balance_rating = "Оптимальный" if abs(front_percent - optimal_percent) < 0.05 else \
                "Смещен вперед" if front_percent > optimal_percent else "Смещен назад"

            result_text = (
                "=== БАЛАНС ТОРМОЗНЫХ СИЛ ===\n"
                f"Текущее распределение: {front_percent * 100:.1f}% / {(1 - front_percent) * 100:.1f}%\n"
                f"Передние тормоза: {front_force:.1f} Н·м\n"
                f"Задние тормоза: {rear_force:.1f} Н·м\n"
                f"Оптимальное распределение: {optimal_percent * 100:.1f}%\n"
                f"Оценка баланса: {balance_rating}"
            )
            self.brake_result.setText(result_text)

            # Сохраняем для отчета
            if 'braking' not in self.report_data:
                self.report_data['braking'] = {}
            self.report_data['braking'].update({
                'brake_balance': {
                    'front_percent': f"{front_percent * 100:.1f}%",
                    'rear_percent': f"{(1 - front_percent) * 100:.1f}%",
                    'front_force': f"{front_force:.1f} Н·м",
                    'rear_force': f"{rear_force:.1f} Н·м",
                    'optimal_percent': f"{optimal_percent * 100:.1f}%",
                    'balance_rating': balance_rating
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'brake_balance',
                {
                    'front_percent': front_percent,
                    'brake_torque': brake_torque,
                    'weight': weight
                },
                {
                    'front_force': front_force,
                    'rear_force': rear_force,
                    'optimal_percent': optimal_percent,
                    'balance_rating': balance_rating
                }
            )

            self.update_report_tab()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Сначала рассчитайте тормозной момент\n{str(e)}")

    def calculate_brake_temperature(self):
        """Расчет нагрева тормозов"""
        try:
            speed = float(self.brake_speed.text())
            weight = float(self.brake_vehicle_weight.text())
            disc_dia = float(self.brake_disc_diameter.text()) / 1000  # в метрах
            disc_thickness = float(
                QInputDialog.getText(self, "Толщина диска", "Введите толщину тормозного диска (мм):")[0]) / 1000

            if weight == 0 or disc_dia == 0 or disc_thickness == 0:
                raise ValueError("Параметры не могут быть нулевыми")

            # Кинетическая энергия: E = 0.5 * m * v²
            speed_mps = speed / 3.6
            kinetic_energy = 0.5 * weight * (speed_mps ** 2)

            # Предположим, что 90% энергии переходит в тепло
            heat_energy = kinetic_energy * 0.9

            # Объем диска (упрощенно)
            disc_volume = math.pi * (disc_dia / 2) ** 2 * disc_thickness
            # Плотность чугуна ~7200 кг/м³, теплоемкость ~500 Дж/(кг·K)
            disc_mass = disc_volume * 7200
            temperature_rise = heat_energy / (disc_mass * 500)

            result_text = (
                "=== НАГРЕВ ТОРМОЗНЫХ ДИСКОВ ===\n"
                f"Скорость: {speed} км/ч\n"
                f"Масса: {weight} кг\n"
                f"Диаметр диска: {disc_dia * 1000:.1f} мм\n"
                f"Толщина диска: {disc_thickness * 1000:.1f} мм\n"
                f"Кинетическая энергия: {kinetic_energy / 1000:.1f} кДж\n"
                f"Тепловая энергия: {heat_energy / 1000:.1f} кДж\n"
                f"Повышение температуры: {temperature_rise:.1f} °C\n\n"
                "Критические значения:\n"
                "> 300°C - Возможна деформация\n"
                "> 600°C - Потеря эффективности"
            )
            self.brake_result.setText(result_text)

            # Сохраняем для отчета
            if 'braking' not in self.report_data:
                self.report_data['braking'] = {}
            self.report_data['braking'].update({
                'brake_temperature': {
                    'speed': f"{speed} км/ч",
                    'weight': f"{weight} кг",
                    'disc_diameter': f"{disc_dia * 1000:.1f} мм",
                    'disc_thickness': f"{disc_thickness * 1000:.1f} мм",
                    'kinetic_energy': f"{kinetic_energy / 1000:.1f} кДж",
                    'heat_energy': f"{heat_energy / 1000:.1f} кДж",
                    'temperature_rise': f"{temperature_rise:.1f} °C"
                }
            })

            # Сохраняем в базу данных
            self.db.save_calculation(
                'brake_temperature',
                {
                    'speed': speed,
                    'weight': weight,
                    'disc_diameter': disc_dia,
                    'disc_thickness': disc_thickness
                },
                {
                    'kinetic_energy': kinetic_energy,
                    'heat_energy': heat_energy,
                    'temperature_rise': temperature_rise
                }
            )

            self.update_report_tab()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректные параметры")

    # ==================== НОВАЯ ВКЛАДКА: ПОДВЕСКА ====================

    def create_suspension_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Группа "Расчет жесткости подвески"
        spring_group = QGroupBox("Расчет жесткости подвески")
        spring_layout = QFormLayout()

        self.suspension_spring_rate = QLineEdit()
        self.suspension_spring_rate.setPlaceholderText("Н/мм")
        self.suspension_motion_ratio = QLineEdit("1.0")
        self.suspension_motion_ratio.setPlaceholderText("Обычно 0.8-1.2")
        self.suspension_spring_preload = QLineEdit("0")
        self.suspension_spring_preload.setPlaceholderText("мм")

        calculate_spring_btn = QPushButton("Рассчитать жесткость колеса")
        calculate_spring_btn.clicked.connect(self.calculate_wheel_rate)

        self.suspension_wheel_rate = QLabel("")
        self.suspension_wheel_rate.setStyleSheet("font-weight: bold; color: #0066CC;")
        self.suspension_force_at_ride = QLabel("")
        self.suspension_force_at_ride.setStyleSheet("font-weight: bold; color: #0066CC;")

        spring_layout.addRow("Жесткость пружины (k):", self.suspension_spring_rate)
        spring_layout.addRow("Коэффициент рычага (MR):", self.suspension_motion_ratio)
        spring_layout.addRow("Предварительный натяг пружины:", self.suspension_spring_preload)
        spring_layout.addRow(calculate_spring_btn)
        spring_layout.addRow("Эффективная жесткость колеса (Wheel Rate):", self.suspension_wheel_rate)
        spring_layout.addRow("Сила на подвеске в положении клевка:", self.suspension_force_at_ride)
        spring_group.setLayout(spring_layout)

        # Группа "Расчет частоты подвески"
        freq_group = QGroupBox("Расчет частоты подвески")
        freq_layout = QFormLayout()

        self.suspension_weight = QLineEdit()
        self.suspension_weight.setPlaceholderText("кг на колесо")
        self.suspension_corner_weight = QLineEdit()
        self.suspension_corner_weight.setPlaceholderText("кг (статическая нагрузка)")

        calculate_freq_btn = QPushButton("Рассчитать частоту")
        calculate_freq_btn.clicked.connect(self.calculate_suspension_frequency)

        self.suspension_frequency = QLabel("")
        self.suspension_frequency.setStyleSheet("font-weight: bold; color: #0066CC;")
        self.suspension_ride_height_change = QLabel("")
        self.suspension_ride_height_change.setStyleSheet("font-weight: bold; color: #0066CC;")

        freq_layout.addRow("Масса на колесо (в движении):", self.suspension_weight)
        freq_layout.addRow("Статическая нагрузка на колесо:", self.suspension_corner_weight)
        freq_layout.addRow(calculate_freq_btn)
        freq_layout.addRow("Частота подвески:", self.suspension_frequency)
        freq_layout.addRow("Изменение клиренса под нагрузкой:", self.suspension_ride_height_change)
        freq_group.setLayout(freq_layout)

        # Группа "Расчет демпфирования"
        damping_group = QGroupBox("Расчет демпфирования")
        damping_layout = QFormLayout()

        self.suspension_rebound = QLineEdit()
        self.suspension_rebound.setPlaceholderText("мм/с")
        self.suspension_bump = QLineEdit()
        self.suspension_bump.setPlaceholderText("мм/с")
        self.suspension_crit_damping = QLineEdit()

        calculate_damping_btn = QPushButton("Рассчитать коэффициенты")
        calculate_damping_btn.clicked.connect(self.calculate_damping)

        self.suspension_rebound_coeff = QLabel("")
        self.suspension_rebound_coeff.setStyleSheet("font-weight: bold; color: #0066CC;")
        self.suspension_bump_coeff = QLabel("")
        self.suspension_bump_coeff.setStyleSheet("font-weight: bold; color: #0066CC;")
        self.suspension_damping_ratio = QLabel("")
        self.suspension_damping_ratio.setStyleSheet("font-weight: bold; color: #0066CC;")

        damping_layout.addRow("Скорость отбоя:", self.suspension_rebound)
        damping_layout.addRow("Скорость сжатия:", self.suspension_bump)
        damping_layout.addRow("Критическое демпфирование:", self.suspension_crit_damping)
        damping_layout.addRow(calculate_damping_btn)
        damping_layout.addRow("Коэффициент отбоя:", self.suspension_rebound_coeff)
        damping_layout.addRow("Коэффициент сжатия:", self.suspension_bump_coeff)
        damping_layout.addRow("Коэффициент демпфирования:", self.suspension_damping_ratio)
        damping_group.setLayout(damping_layout)

        # Группа "Кинематика подвески"
        kinematics_group = QGroupBox("Кинематика подвески")
        kinematics_layout = QFormLayout()

        self.suspension_arm_length = QLineEdit()
        self.suspension_arm_length.setPlaceholderText("мм")
        self.suspension_pivot_height = QLineEdit()
        self.suspension_pivot_height.setPlaceholderText("мм")
        self.suspension_instant_center = QLabel("")
        self.suspension_instant_center.setStyleSheet("font-weight: bold; color: #0066CC;")

        calculate_kinematics_btn = QPushButton("Рассчитать кинематику")
        calculate_kinematics_btn.clicked.connect(self.calculate_kinematics)

        kinematics_layout.addRow("Длина рычага:", self.suspension_arm_length)
        kinematics_layout.addRow("Высота оси вращения:", self.suspension_pivot_height)
        kinematics_layout.addRow(calculate_kinematics_btn)
        kinematics_layout.addRow("Мгновенный центр вращения:", self.suspension_instant_center)
        kinematics_group.setLayout(kinematics_layout)



        layout.addWidget(spring_group)
        layout.addWidget(freq_group)
        layout.addWidget(damping_group)
        layout.addWidget(kinematics_group)

        layout.addStretch()

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Подвеска")

    def calculate_wheel_rate(self):
        try:
            spring_rate = float(self.suspension_spring_rate.text())
            motion_ratio = float(self.suspension_motion_ratio.text())
            preload = float(self.suspension_spring_preload.text())

            wheel_rate = spring_rate * (motion_ratio ** 2)
            force_at_ride = spring_rate * preload * motion_ratio

            self.suspension_wheel_rate.setText(f"{wheel_rate:.2f} Н/мм")
            self.suspension_force_at_ride.setText(f"{force_at_ride:.2f} Н")

            # Сохранение в отчет
            self.report_data['suspension'] = {
                'spring_rate': f"{spring_rate:.1f} Н/мм",
                'motion_ratio': f"{motion_ratio:.2f}",
                'preload': f"{preload:.1f} мм",
                'wheel_rate': f"{wheel_rate:.2f} Н/мм",
                'force_at_ride': f"{force_at_ride:.2f} Н"
            }

            # Сохранение в базу данных
            calc_id = self.db.save_calculation(
                'suspension_wheel_rate',
                {
                    'spring_rate': spring_rate,
                    'motion_ratio': motion_ratio,
                    'preload': preload
                },
                {
                    'wheel_rate': wheel_rate,
                    'force_at_ride': force_at_ride
                }
            )

            self.update_report_tab()
            self.statusBar().showMessage(f"Расчет жесткости сохранен (ID: {calc_id})", 3000)

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректные значения")

    def calculate_suspension_frequency(self):
        try:
            weight = float(self.suspension_weight.text())
            corner_weight = float(self.suspension_corner_weight.text())
            wheel_rate_nmm = float(self.suspension_wheel_rate.text().split()[0])
            wheel_rate = wheel_rate_nmm * 1000  # Н/мм в Н/м

            frequency = (1 / (2 * math.pi)) * math.sqrt(wheel_rate / (weight * 9.81))
            ride_height_change = (corner_weight * 9.81) / (wheel_rate_nmm * 1000)

            self.suspension_frequency.setText(f"{frequency:.2f} Гц")
            self.suspension_ride_height_change.setText(f"{ride_height_change * 1000:.1f} мм")

            # Сохранение в отчет
            if 'suspension' not in self.report_data:
                self.report_data['suspension'] = {}

            self.report_data['suspension'].update({
                'weight': f"{weight:.1f} кг",
                'corner_weight': f"{corner_weight:.1f} кг",
                'frequency': f"{frequency:.2f} Гц",
                'ride_height_change': f"{ride_height_change * 1000:.1f} мм"
            })

            # Сохранение в базу данных
            calc_id = self.db.save_calculation(
                'suspension_frequency',
                {
                    'weight': weight,
                    'corner_weight': corner_weight,
                    'wheel_rate': wheel_rate_nmm
                },
                {
                    'frequency': frequency,
                    'ride_height_change': ride_height_change * 1000
                }
            )

            self.update_report_tab()
            self.statusBar().showMessage(f"Расчет частоты сохранен (ID: {calc_id})", 3000)

        except (ValueError, AttributeError):
            QMessageBox.warning(self, "Ошибка", "Сначала рассчитайте жесткость колеса и введите массу")

    def calculate_damping(self):
        try:
            rebound = float(self.suspension_rebound.text())
            bump = float(self.suspension_bump.text())
            crit_damping = float(self.suspension_crit_damping.text())

            rebound_coeff = rebound / crit_damping
            bump_coeff = bump / crit_damping
            damping_ratio = (rebound_coeff + bump_coeff) / 2

            self.suspension_rebound_coeff.setText(f"{rebound_coeff:.2f}")
            self.suspension_bump_coeff.setText(f"{bump_coeff:.2f}")
            self.suspension_damping_ratio.setText(f"{damping_ratio:.2f}")

            # Сохранение в отчет
            if 'suspension' not in self.report_data:
                self.report_data['suspension'] = {}

            self.report_data['suspension'].update({
                'rebound_coeff': f"{rebound_coeff:.2f}",
                'bump_coeff': f"{bump_coeff:.2f}",
                'damping_ratio': f"{damping_ratio:.2f}"
            })

            # Сохранение в базу данных
            calc_id = self.db.save_calculation(
                'suspension_damping',
                {
                    'rebound': rebound,
                    'bump': bump,
                    'crit_damping': crit_damping
                },
                {
                    'rebound_coeff': rebound_coeff,
                    'bump_coeff': bump_coeff,
                    'damping_ratio': damping_ratio
                }
            )

            self.update_report_tab()
            self.statusBar().showMessage(f"Расчет демпфирования сохранен (ID: {calc_id})", 3000)

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректные значения")

    def calculate_kinematics(self):
        try:
            arm_length = float(self.suspension_arm_length.text())
            pivot_height = float(self.suspension_pivot_height.text())

            instant_center_height = pivot_height + arm_length * 0.5  # Упрощенный расчет
            self.suspension_instant_center.setText(f"{instant_center_height:.1f} мм от земли")

            # Сохранение в отчет
            if 'suspension' not in self.report_data:
                self.report_data['suspension'] = {}

            self.report_data['suspension'].update({
                'arm_length': f"{arm_length:.1f} мм",
                'pivot_height': f"{pivot_height:.1f} мм",
                'instant_center_height': f"{instant_center_height:.1f} мм"
            })

            # Сохранение в базу данных
            calc_id = self.db.save_calculation(
                'suspension_kinematics',
                {
                    'arm_length': arm_length,
                    'pivot_height': pivot_height
                },
                {
                    'instant_center_height': instant_center_height
                }
            )

            self.update_report_tab()
            self.statusBar().showMessage(f"Расчет кинематики сохранен (ID: {calc_id})", 3000)

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректные значения")

    def save_all_suspension_calculations(self):
        """Сохраняет все расчеты подвески как единый комплексный расчет"""
        try:
            # Собираем все данные
            suspension_data = {
                'spring': {
                    'rate': float(self.suspension_spring_rate.text()),
                    'motion_ratio': float(self.suspension_motion_ratio.text()),
                    'preload': float(self.suspension_spring_preload.text())
                },
                'frequency': {
                    'weight': float(self.suspension_weight.text()),
                    'corner_weight': float(self.suspension_corner_weight.text())
                },
                'damping': {
                    'rebound': float(self.suspension_rebound.text()),
                    'bump': float(self.suspension_bump.text()),
                    'crit_damping': float(self.suspension_crit_damping.text())
                },
                'kinematics': {
                    'arm_length': float(self.suspension_arm_length.text()),
                    'pivot_height': float(self.suspension_pivot_height.text())
                }
            }

            # Сохраняем в базу данных как комплексный расчет
            calc_id = self.db.save_calculation(
                'suspension_full',
                suspension_data,
                {
                    'note': 'Комплексный расчет параметров подвески'
                }
            )

            self.statusBar().showMessage(f"Все расчеты подвески сохранены (ID: {calc_id})", 5000)

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выполните все расчеты перед сохранением")

    # ==================== НОВАЯ ВКЛАДКА: ТОПЛИВНАЯ СИСТЕМА ====================
    def create_fuel_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Группа "Производительность системы"
        flow_group = QGroupBox("Производительность топливной системы")
        flow_layout = QFormLayout()

        # Добавлен выбор типа топливной системы
        self.fuel_system_type = QComboBox()
        self.fuel_system_type.addItems(["Карбюратор", "Инжектор", "Прямой впрыск"])
        flow_layout.addRow("Тип системы:", self.fuel_system_type)

        self.fuel_injector_count = QSpinBox()
        self.fuel_injector_count.setRange(1, 16)  # Увеличен диапазон
        self.fuel_injector_count.setValue(4)
        self.fuel_injector_flow = QLineEdit()
        self.fuel_injector_flow.setPlaceholderText("г/мин")
        self.fuel_pressure = QLineEdit("3.0")
        self.fuel_pressure.setPlaceholderText("бар")

        # Добавлен параметр температуры топлива
        self.fuel_temp = QLineEdit("20")
        self.fuel_temp.setPlaceholderText("°C")
        flow_layout.addRow("Температура топлива:", self.fuel_temp)

        calculate_flow_btn = QPushButton("Рассчитать производительность")
        calculate_flow_btn.clicked.connect(self.calculate_fuel_system_flow)

        self.fuel_system_flow = QLabel("")
        self.fuel_system_flow.setStyleSheet("font-weight: bold; color: #0066CC;")

        flow_layout.addRow("Количество форсунок:", self.fuel_injector_count)
        flow_layout.addRow("Производительность форсунки:", self.fuel_injector_flow)
        flow_layout.addRow("Давление топлива:", self.fuel_pressure)
        flow_layout.addRow(calculate_flow_btn)
        flow_layout.addRow("Общая производительность:", self.fuel_system_flow)
        flow_group.setLayout(flow_layout)

        # Группа "Время впрыска"
        injector_group = QGroupBox("Расчет времени впрыска")
        injector_layout = QFormLayout()

        self.fuel_engine_power = QLineEdit()
        self.fuel_engine_power.setPlaceholderText("л.с.")
        self.fuel_bsfc = QLineEdit("0.45")
        self.fuel_bsfc.setPlaceholderText("кг/(л.с.*час)")

        # Добавлен параметр оборотов двигателя
        self.fuel_rpm = QLineEdit("6000")
        self.fuel_rpm.setPlaceholderText("об/мин")
        injector_layout.addRow("Обороты двигателя:", self.fuel_rpm)

        calculate_injector_btn = QPushButton("Рассчитать время впрыска")
        calculate_injector_btn.clicked.connect(self.calculate_injector_duty)

        self.fuel_injector_duty = QLabel("")
        self.fuel_injector_duty.setStyleSheet("font-weight: bold; color: #0066CC;")

        # Добавлен расчет требуемого объема топлива
        self.fuel_required_volume = QLabel("")
        self.fuel_required_volume.setStyleSheet("font-weight: bold; color: #0066CC;")
        injector_layout.addRow("Требуемый объем топлива:", self.fuel_required_volume)

        injector_layout.addRow("Мощность двигателя:", self.fuel_engine_power)
        injector_layout.addRow("Удельный расход топлива:", self.fuel_bsfc)
        injector_layout.addRow(calculate_injector_btn)
        injector_layout.addRow("Максимальный цикл впрыска:", self.fuel_injector_duty)
        injector_group.setLayout(injector_layout)

        # Новая группа "Оптимизация топливной системы"
        optimize_group = QGroupBox("Оптимизация топливной системы")
        optimize_layout = QFormLayout()

        self.fuel_target_duty = QLineEdit("80")
        self.fuel_target_duty.setPlaceholderText("%")
        optimize_layout.addRow("Целевой цикл впрыска:", self.fuel_target_duty)

        calculate_optimize_btn = QPushButton("Рассчитать оптимальные параметры")
        calculate_optimize_btn.clicked.connect(self.calculate_optimal_fuel_params)
        optimize_layout.addRow(calculate_optimize_btn)

        self.fuel_optimal_flow = QLabel("")
        self.fuel_optimal_flow.setStyleSheet("font-weight: bold; color: #0066CC;")
        optimize_layout.addRow("Рекомендуемая производительность:", self.fuel_optimal_flow)

        self.fuel_optimal_pressure = QLabel("")
        self.fuel_optimal_pressure.setStyleSheet("font-weight: bold; color: #0066CC;")
        optimize_layout.addRow("Рекомендуемое давление:", self.fuel_optimal_pressure)

        optimize_group.setLayout(optimize_layout)

        layout.addWidget(flow_group)
        layout.addWidget(injector_group)
        layout.addWidget(optimize_group)
        layout.addStretch()

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Топливная система")

    def calculate_fuel_system_flow(self):
        try:
            count = self.fuel_injector_count.value()
            flow = float(self.fuel_injector_flow.text())
            pressure = float(self.fuel_pressure.text())
            temp = float(self.fuel_temp.text())
            system_type = self.fuel_system_type.currentText()

            # Коррекция на температуру (примерная формула)
            temp_correction = 1 + (temp - 20) * 0.001
            # Коррекция на тип системы
            system_factor = 1.0 if system_type == "Инжектор" else 0.9 if system_type == "Прямой впрыск" else 0.7

            corrected_flow = flow * math.sqrt(pressure / 3.0) * temp_correction * system_factor
            total_flow = corrected_flow * count

            result_text = f"{total_flow:.1f} г/мин или {total_flow / 60:.2f} г/сек"
            self.fuel_system_flow.setText(result_text)

            # Сохраняем для отчета
            self.report_data['fuel_system'] = {
                'system_type': system_type,
                'injector_count': count,
                'injector_flow': f"{flow:.1f} г/мин",
                'pressure': f"{pressure:.1f} бар",
                'temperature': f"{temp:.1f} °C",
                'total_flow': f"{total_flow:.1f} г/мин",
                'flow_per_second': f"{total_flow / 60:.2f} г/сек"
            }

            # Сохранение в базу данных
            calc_id = self.db.save_calculation(
                'fuel_system_flow',
                {
                    'system_type': system_type,
                    'injector_count': count,
                    'injector_flow': flow,
                    'pressure': pressure,
                    'temperature': temp
                },
                {
                    'corrected_flow': corrected_flow,
                    'total_flow': total_flow,
                    'flow_per_second': total_flow / 60
                }
            )

            self.update_report_tab()
            self.statusBar().showMessage(f"Расчет сохранен в базе (ID: {calc_id})", 3000)

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректные числовые значения")

    def calculate_injector_duty(self):
        try:
            power = float(self.fuel_engine_power.text())
            bsfc = float(self.fuel_bsfc.text())
            rpm = float(self.fuel_rpm.text())
            total_flow_text = self.fuel_system_flow.text()

            if not total_flow_text:
                raise ValueError("Сначала выполните расчет производительности системы")

            total_flow = float(total_flow_text.split()[0]) / 60  # г/мин в г/сек

            required_flow = (power * bsfc) / 3600 * 1000
            duty_cycle = (required_flow / total_flow) * 100

            # Расчет времени открытия форсунки на оборотах
            cycle_time = 60 / rpm * 1000  # время цикла в мс
            injector_open_time = cycle_time * duty_cycle / 100

            self.fuel_injector_duty.setText(
                f"{duty_cycle:.1f}% ({injector_open_time:.2f} мс при {rpm} об/мин)"
            )
            self.fuel_required_volume.setText(f"{required_flow * 3600:.1f} г/час")

            if 'fuel_system' not in self.report_data:
                self.report_data['fuel_system'] = {}

            self.report_data['fuel_system'].update({
                'engine_power': f"{power:.1f} л.с.",
                'bsfc': f"{bsfc:.2f} кг/(л.с.*час)",
                'rpm': f"{rpm:.0f} об/мин",
                'duty_cycle': f"{duty_cycle:.1f}%",
                'injector_open_time': f"{injector_open_time:.2f} мс",
                'required_volume': f"{required_flow * 3600:.1f} г/час"
            })

            # Сохранение в базу данных
            calc_id = self.db.save_calculation(
                'injector_duty',
                {
                    'power': power,
                    'bsfc': bsfc,
                    'rpm': rpm,
                    'total_flow': total_flow * 60  # сохраняем в г/мин
                },
                {
                    'duty_cycle': duty_cycle,
                    'injector_open_time': injector_open_time,
                    'required_volume': required_flow * 3600
                }
            )

            self.update_report_tab()
            self.statusBar().showMessage(f"Расчет сохранен в базе (ID: {calc_id})", 3000)

        except (ValueError, AttributeError) as e:
            QMessageBox.warning(self, "Ошибка", f"Пожалуйста, проверьте введенные данные\n{str(e)}")

    def calculate_optimal_fuel_params(self):
        """Расчет оптимальных параметров топливной системы"""
        try:
            target_duty = float(self.fuel_target_duty.text())
            if not 50 <= target_duty <= 95:
                raise ValueError("Целевой цикл должен быть между 50% и 95%")

            if 'fuel_system' not in self.report_data:
                raise ValueError("Сначала выполните расчет времени впрыска")

            required_flow = float(self.report_data['fuel_system']['required_volume'].split()[0]) / 3600  # г/час в г/сек
            current_duty = float(self.report_data['fuel_system']['duty_cycle'].split('%')[0])

            # Расчет оптимальной производительности
            optimal_flow = (required_flow * 100) / target_duty * 60  # г/сек в г/мин

            # Расчет оптимального давления (базовое давление 3 бар)
            current_flow = float(self.report_data['fuel_system']['total_flow'].split()[0])
            optimal_pressure = 3.0 * (optimal_flow / current_flow) ** 2

            self.fuel_optimal_flow.setText(f"{optimal_flow:.1f} г/мин")
            self.fuel_optimal_pressure.setText(f"{optimal_pressure:.1f} бар")

            # Обновление отчета
            self.report_data['fuel_system'].update({
                'target_duty': f"{target_duty}%",
                'optimal_flow': f"{optimal_flow:.1f} г/мин",
                'optimal_pressure': f"{optimal_pressure:.1f} бар"
            })

            # Сохранение в базу данных
            calc_id = self.db.save_calculation(
                'fuel_optimization',
                {
                    'target_duty': target_duty,
                    'current_duty': current_duty,
                    'required_flow': required_flow * 3600  # сохраняем в г/час
                },
                {
                    'optimal_flow': optimal_flow,
                    'optimal_pressure': optimal_pressure
                }
            )

            self.update_report_tab()
            self.statusBar().showMessage(f"Оптимизация сохранена в базе (ID: {calc_id})", 3000)

        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось рассчитать оптимальные параметры\n{str(e)}")

    # ==================== ВКЛАДКА ОТЧЕТ ====================
    def create_report_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setStyleSheet("font-family: DejaVu; font-size: 12px;")

        layout.addWidget(self.report_text)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Отчет")

    def update_report_tab(self):
        # Словарь для перевода названий разделов
        section_translations = {
            'engine': 'Двигатель',
            'transmission': 'Трансмиссия',
            'dynamics': 'Динамика',
            'aerodynamics': 'Аэродинамика',
            'braking': 'Тормозная система',
            'suspension': 'Подвеска',
            'fuel_system': 'Топливная система',
            'engine': 'Двигатель',
            'engine_power_calc': 'Расчет мощности двигателя',
            'engine_air_flow': 'Расход воздуха двигателя',
            'engine_compression': 'Степень сжатия двигателя',
            'transmission': 'Трансмиссия',
            'transmission_gear_speeds': 'Скорости на передачах',
            'transmission_ratio_calculation': 'Расчет передаточного отношения',
            'transmission_efficiency': 'КПД трансмиссии',
            'dynamics': 'Динамика',
            'traction_force': 'Тяговая сила',
            'acceleration': 'Разгонная динамика',
            'shift_points': 'Точки переключения',
            'braking': 'Тормозная система',
            'brake_torque': 'Тормозной момент',
            'stopping_distance': 'Тормозной путь',
            'brake_balance': 'Баланс тормозов',
            'brake_temperature': 'Нагрев тормозов',
            'suspension': 'Подвеска',
            'suspension_wheel_rate': 'Жесткость подвески',
            'suspension_frequency': 'Частота подвески',
            'suspension_damping': 'Демпфирование подвески',
            'suspension_kinematics': 'Кинематика подвески',
            'fuel_system': 'Топливная система',
            'fuel_system_flow': 'Производительность системы',
            'injector_duty': 'Время впрыска',
            'fuel_optimization': 'Оптимизация системы'

        }

        # Словарь для перевода параметров
        param_translations = {
            # Дополнительные параметры двигателя
            "acceleration": "Ускорение",
            "power": "Мощность (л.с.)",
            "mep_bar": "Среднее эффективное давление (бар)",
            "volumetric_efficiency": "Объемный КПД",
            "air_flow": "Расход воздуха (кг/ч)",
            "compression_ratio": "Степень сжатия",

            # Дополнительные параметры трансмиссии
            "calculated_ratio": "Расчетное передаточное отношение",
            "rpm1": "Обороты двигателя 1 (об/мин)",
            "rpm2": "Обороты двигателя 2 (об/мин)",
            "speed1": "Скорость 1 (км/ч)",
            "speed2": "Скорость 2 (км/ч)",
            "tire_radius": "Радиус колеса (м)",

            # Дополнительные параметры динамики
            "drag_coef": "Коэффициент аэродинамического сопротивления",
            "frontal_area": "Лобовая площадь (м²)",
            "rolling_resist": "Коэффициент сопротивления качению",

            # Дополнительные параметры подвески
            "arm_length": "Длина рычага (мм)",
            "pivot_height": "Высота оси вращения (мм)",

            # Дополнительные параметры топливной системы
            "temp": "Температура (°C)",
            "note": "Примечание",

            # Общие параметры
            "vehicle_weight": "Масса автомобиля (кг)",
            "weight": "Масса (кг)",
            "temperature": "Температура (°C)",
            # Подвеска
            "spring_rate": "Жесткость пружины (Н/мм)",
            "motion_ratio": "Коэффициент рычага",
            "preload": "Предварительная нагрузка (мм)",
            "wheel_rate": "Эффективная жесткость колеса (Н/мм)",
            "force_at_ride": "Сила в положении 'покоя' (Н)",
            "corner_weight": "Нагрузка на колесо (кг)",
            "frequency": "Частота подвески (Гц)",
            "ride_height_change": "Изменение клиренса (мм)",
            "rebound_coeff": "Коэффициент отбоя",
            "bump_coeff": "Коэффициент сжатия",
            "damping_ratio": "Коэффициент демпфирования",
            "instant_center_height": "Высота мгновенного центра (мм)",

            # Тормозная система
            "brake_torque": "Тормозной момент (Н·м)",
            "piston_count": "Количество поршней",
            "piston_diameter": "Диаметр поршня (мм)",
            "disc_diameter": "Диаметр диска (мм)",
            "pad_coef": "Коэффициент трения колодок",
            "pressure": "Давление в системе (бар)",
            "friction_force": "Сила трения (Н)",
            "brake_balance": "Баланс тормозов",
            "front_percent": "Передние тормоза (%)",
            "rear_percent": "Задние тормоза (%)",
            "front_force": "Сила на передних тормозах (Н·м)",
            "rear_force": "Сила на задних тормозах (Н·м)",
            "optimal_percent": "Оптимальный баланс (%)",
            "balance_rating": "Оценка баланса",
            "stopping_distance": "Тормозной путь (м)",
            "speed": "Скорость (км/ч)",
            "road_coeff": "Коэффициент сцепления с дорогой",
            "front_load": "Нагрузка на переднюю ось (Н)",
            "rear_load": "Нагрузка на заднюю ось (Н)",
            "stopping_time": "Время торможения (с)",
            "deceleration": "Замедление (g)",
            "brake_temperature": "Температура тормозов",
            "disc_thickness": "Толщина диска (мм)",
            "kinetic_energy": "Кинетическая энергия (кДж)",
            "heat_energy": "Тепловая энергия (кДж)",
            "temperature_rise": "Рост температуры (°C)",

            # Двигатель
            "power_hp": "Мощность (л.с.)",
            "fuel_consumption": "Расход топлива (кг/ч)",
            "fuel_type": "Тип топлива",
            "efficiency": "Эффективный КПД (%)",
            "displacement": "Объем двигателя (см³)",
            "torque": "Крутящий момент (Н·м)",
            "mep": "Среднее эффективное давление (бар)",
            "mep_kgcm2": "Среднее эффективное давление (кгс/см²)",
            "rpm": "Обороты (об/мин)",
            "power_kw": "Мощность (кВт)",
            "volumetric_efficiency": "КПД наполнения",
            "air_flow": "Расход воздуха (кг/ч)",
            "cylinder_volume": "Объем цилиндра (см³)",
            "chamber_volume": "Объем камеры сгорания (см³)",
            "compression_ratio": "Степень сжатия",

            # Динамика
            "traction_force": "Тяговая сила (Н)",
            "gear_ratio": "Передаточное число",
            "equivalent_force": "Эквивалентная сила (кгс)",
            "specific_power": "Удельная мощность (кВт/т)",
            "max_speed": "Максимальная скорость (км/ч)",
            "acceleration_0_100": "Разгон 0–100 км/ч (с)",
            "optimal_rpm": "Оптимальные обороты (об/мин)",
            "shift_points": "Точки переключения передач",

            # Трансмиссия
            "gear_ratios": "Передаточные числа",
            "final_drive": "Главная передача",
            "tire_diameter": "Диаметр колеса (мм)",
            "redline_rpm": "Максимальные обороты (об/мин)",
            "speeds_at_redline": "Скорости на максимальных оборотах",
            "transmission_efficiency": "КПД трансмиссии (%)",
            "wheel_power": "Мощность на колесах (л.с.)",
            # Общие параметры
            "weight": "Масса (кг)",
            "temperature": "Температура (°C)",

            # Двигатель
            "Engine_power_calc": "Расчет мощности двигателя",
            "Engine_air_flow": "Расход воздуха двигателя",
            "Engine_compression": "Степень сжатия двигателя",

            # Трансмиссия
            "calculated_gear_ratio": "Расчетное передаточное число",
            "rpm1": "Обороты 1 (об/мин)",
            "rpm2": "Обороты 2 (об/мин)",
            "speed1": "Скорость 1 (км/ч)",
            "speed2": "Скорость 2 (км/ч)",

            # Динамика
            "gear_1": "Передача 1",
            "gear_2": "Передача 2",
            "gear_3": "Передача 3",
            "gear_4": "Передача 4",
            "gear_5": "Передача 5",
            "gear_6": "Передача 6",

            # Тормозная система
            "road_coef": "Коэффициент сцепления с дорогой",

            # Подвеска
            "bump_coeff": "Коэффициент сжатия подвески",
            "rebound_coeff": "Коэффициент отбоя подвески",

            # Топливная система
            "system_type": "Тип системы",
            "injector_count": "Количество форсунок",
            "injector_flow": "Производительность форсунки (г/мин)",
            "total_flow": "Общий расход топлива (г/мин)",
            "flow_per_second": "Расход топлива в секунду (г/сек)",
            "bsfc": "Удельный расход топлива (кг/(л.с.*час))",
            "duty_cycle": "Цикл впрыска (%)",
            "injector_open_time": "Время открытия форсунки (мс)",
            "required_volume": "Требуемый объем топлива (г/час)",
            "target_duty": "Целевой цикл впрыска (%)",
            "optimal_flow": "Оптимальный расход топлива (г/мин)",
            "optimal_pressure": "Оптимальное давление (бар)",

            # Дополнительные параметры
            "kinetic_energy": "Кинетическая энергия (кДж)",
            "heat_energy": "Тепловая энергия (кДж)",
            "disc_thickness": "Толщина тормозного диска (мм)"
        }

        report_html = "<h1>Отчет по расчету характеристик автомобиля</h1>"
        report_html += f"<p>Дата создания: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>"
        report_html += "<hr>"

        for section, data in self.report_data.items():
            # Получаем русское название раздела
            section_name = section_translations.get(section, section.capitalize())
            report_html += f"<h2>{section_name}</h2>"
            report_html += "<ul>"

            for key, value in data.items():
                # Получаем русское название параметра
                param_name = param_translations.get(key, key)

                if isinstance(value, dict):
                    report_html += f"<li><b>{param_name}:</b></li><ul>"
                    for subkey, subvalue in value.items():
                        sub_param_name = param_translations.get(subkey, subkey)
                        report_html += f"<li><b>{sub_param_name}:</b> {subvalue}</li>"
                    report_html += "</ul>"
                else:
                    report_html += f"<li><b>{param_name}:</b> {value}</li>"

            report_html += "</ul>"

        self.report_text.setHtml(report_html)

    # ==================== ЭКСПОРТ И ПЕЧАТЬ ====================
    def export_to_pdf(self):
        if not self.report_data:
            QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта. Сначала выполните расчеты.")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчет как PDF",
            f"Отчет_автомобиль_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF Files (*.pdf)",
            options=options
        )

        # Проверяем, что пользователь не отменил диалог
        if not file_name:
            return

        # Добавляем расширение .pdf, если его нет
        if not file_name.endswith('.pdf'):
            file_name += '.pdf'

        try:
            # Создаем PDF документ
            pdf = FPDF()
            pdf.add_page()

            # Настройка шрифтов
            font_path = "C:/Users/Pober/PycharmProjects/PythonProject1/fonts/dejavu-fonts-ttf-2.37/ttf/DejaVuSansCondensed.ttf"
            if os.path.exists(font_path):
                pdf.add_font('DejaVu', '', font_path, uni=True)
                pdf.set_font('DejaVu', '', 12)

            # Заголовок отчета
            pdf.set_font('DejaVu', '', 16)
            pdf.cell(200, 10, txt="Отчет по расчету характеристик автомобиля", ln=1, align='C')

            # Метаданные
            pdf.set_font('DejaVu', '', 12)
            pdf.cell(200, 10, txt=f"Дата создания: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1)
            pdf.ln(10)

            # Словари для перевода названий разделов и параметров
            section_translations = {
                'engine': 'Двигатель',
                'transmission': 'Трансмиссия',
                'dynamics': 'Динамика',
                'aerodynamics': 'Аэродинамика',
                'braking': 'Тормозная система',
                'suspension': 'Подвеска',
                'fuel_system': 'Топливная система'
            }

            param_translations = {
                "spring_rate": "Жесткость пружины (Н/мм)",
            "motion_ratio": "Коэффициент рычага",
            "preload": "Предварительная нагрузка (мм)",
            "wheel_rate": "Эффективная жесткость колеса (Н/мм)",
            "force_at_ride": "Сила в положении 'покоя' (Н)",
            "corner_weight": "Нагрузка на колесо (кг)",
            "frequency": "Частота подвески (Гц)",
            "ride_height_change": "Изменение клиренса (мм)",
            "rebound_coeff": "Коэффициент отбоя",
            "bump_coeff": "Коэффициент сжатия",
            "damping_ratio": "Коэффициент демпфирования",
            "instant_center_height": "Высота мгновенного центра (мм)",

            # Тормозная система
            "brake_torque": "Тормозной момент (Н·м)",
            "piston_count": "Количество поршней",
            "piston_diameter": "Диаметр поршня (мм)",
            "disc_diameter": "Диаметр диска (мм)",
            "pad_coef": "Коэффициент трения колодок",
            "pressure": "Давление в системе (бар)",
            "friction_force": "Сила трения (Н)",
            "brake_balance": "Баланс тормозов",
            "front_percent": "Передние тормоза (%)",
            "rear_percent": "Задние тормоза (%)",
            "front_force": "Сила на передних тормозах (Н·м)",
            "rear_force": "Сила на задних тормозах (Н·м)",
            "optimal_percent": "Оптимальный баланс (%)",
            "balance_rating": "Оценка баланса",
            "stopping_distance": "Тормозной путь (м)",
            "speed": "Скорость (км/ч)",
            "road_coeff": "Коэффициент сцепления с дорогой",
            "front_load": "Нагрузка на переднюю ось (Н)",
            "rear_load": "Нагрузка на заднюю ось (Н)",
            "stopping_time": "Время торможения (с)",
            "deceleration": "Замедление (g)",
            "brake_temperature": "Температура тормозов",
            "disc_thickness": "Толщина диска (мм)",
            "kinetic_energy": "Кинетическая энергия (кДж)",
            "heat_energy": "Тепловая энергия (кДж)",
            "temperature_rise": "Рост температуры (°C)",

            # Двигатель
            "power_hp": "Мощность (л.с.)",
            "fuel_consumption": "Расход топлива (кг/ч)",
            "fuel_type": "Тип топлива",
            "efficiency": "Эффективный КПД (%)",
            "displacement": "Объем двигателя (см³)",
            "torque": "Крутящий момент (Н·м)",
            "mep": "Среднее эффективное давление (бар)",
            "mep_kgcm2": "Среднее эффективное давление (кгс/см²)",
            "rpm": "Обороты (об/мин)",
            "power_kw": "Мощность (кВт)",
            "volumetric_efficiency": "КПД наполнения",
            "air_flow": "Расход воздуха (кг/ч)",
            "cylinder_volume": "Объем цилиндра (см³)",
            "chamber_volume": "Объем камеры сгорания (см³)",
            "compression_ratio": "Степень сжатия",

            # Динамика
            "traction_force": "Тяговая сила (Н)",
            "gear_ratio": "Передаточное число",
            "equivalent_force": "Эквивалентная сила (кгс)",
            "specific_power": "Удельная мощность (кВт/т)",
            "max_speed": "Максимальная скорость (км/ч)",
            "acceleration_0_100": "Разгон 0–100 км/ч (с)",
            "optimal_rpm": "Оптимальные обороты (об/мин)",
            "shift_points": "Точки переключения передач",

            # Трансмиссия
            "gear_ratios": "Передаточные числа",
            "final_drive": "Главная передача",
            "tire_diameter": "Диаметр колеса (мм)",
            "redline_rpm": "Максимальные обороты (об/мин)",
            "speeds_at_redline": "Скорости на максимальных оборотах",
            "transmission_efficiency": "КПД трансмиссии (%)",
            "wheel_power": "Мощность на колесах (л.с.)",
            # Общие параметры
            "weight": "Масса (кг)",
            "temperature": "Температура (°C)",

            # Двигатель
            "Engine_power_calc": "Расчет мощности двигателя",
            "Engine_air_flow": "Расход воздуха двигателя",
            "Engine_compression": "Степень сжатия двигателя",

            # Трансмиссия
            "calculated_gear_ratio": "Расчетное передаточное число",
            "rpm1": "Обороты 1 (об/мин)",
            "rpm2": "Обороты 2 (об/мин)",
            "speed1": "Скорость 1 (км/ч)",
            "speed2": "Скорость 2 (км/ч)",

            # Динамика
            "gear_1": "Передача 1",
            "gear_2": "Передача 2",
            "gear_3": "Передача 3",
            "gear_4": "Передача 4",
            "gear_5": "Передача 5",
            "gear_6": "Передача 6",

            # Тормозная система
            "road_coef": "Коэффициент сцепления с дорогой",

            # Подвеска
            "bump_coeff": "Коэффициент сжатия подвески",
            "rebound_coeff": "Коэффициент отбоя подвески",

            # Топливная система
            "system_type": "Тип системы",
            "injector_count": "Количество форсунок",
            "injector_flow": "Производительность форсунки (г/мин)",
            "total_flow": "Общий расход топлива (г/мин)",
            "flow_per_second": "Расход топлива в секунду (г/сек)",
            "bsfc": "Удельный расход топлива (кг/(л.с.*час))",
            "duty_cycle": "Цикл впрыска (%)",
            "injector_open_time": "Время открытия форсунки (мс)",
            "required_volume": "Требуемый объем топлива (г/час)",
            "target_duty": "Целевой цикл впрыска (%)",
            "optimal_flow": "Оптимальный расход топлива (г/мин)",
            "optimal_pressure": "Оптимальное давление (бар)",

            # Дополнительные параметры
            "kinetic_energy": "Кинетическая энергия (кДж)",
            "heat_energy": "Тепловая энергия (кДж)",
            "disc_thickness": "Толщина тормозного диска (мм)"
        }

            # Содержание отчета
            for section, data in self.report_data.items():
                section_name = section_translations.get(section, section.capitalize())
                pdf.set_font('DejaVu', '', 14)
                pdf.cell(200, 10, txt=f"{section_name}:", ln=1)

                pdf.set_font('DejaVu', '', 12)
                for key, value in data.items():
                    param_name = param_translations.get(key, key)
                    if isinstance(value, dict):
                        pdf.cell(200, 10, txt=f"  {param_name}:", ln=1)
                        for subkey, subvalue in value.items():
                            sub_param_name = param_translations.get(subkey, subkey)
                            pdf.cell(200, 10, txt=f"    {sub_param_name}: {subvalue}", ln=1)
                    else:
                        pdf.cell(200, 10, txt=f"  {param_name}: {value}", ln=1)
                pdf.ln(5)

            # Сохраняем PDF файл
            pdf.output(file_name)

            # Сохраняем отчет в базу данных
            try:
                report_id = self.db.save_report({
                    'filename': file_name,
                    'report_data': self.report_data,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

                # Добавляем информацию о сохранении в историю расчетов
                for section, data in self.report_data.items():
                    if 'engine' in section.lower():
                        calc_type = 'engine_calculation'
                    elif 'transmission' in section.lower():
                        calc_type = 'transmission_calculation'
                    else:
                        calc_type = f"{section}_calculation"

                    self.db.save_calculation(
                        calc_type,
                        {'report_id': report_id},
                        data
                    )

            except Exception as db_error:
                print(f"Ошибка сохранения в БД: {db_error}")

            QMessageBox.information(
                self,
                "Успешно",
                f"Отчет успешно сохранен:\n{file_name}\n\n"
                f"Отчет также сохранен в историю расчетов."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить PDF:\n{str(e)}"
            )

    def print_report(self):
        if not self.report_data:
            QMessageBox.warning(self, "Ошибка", "Нет данных для печати. Сначала выполните расчеты.")
            return

        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec_() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(self.report_text.toHtml())
            doc.print_(printer)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdvancedVehicleCalculator()
    window.show()
    sys.exit(app.exec_())