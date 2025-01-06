import sys
import os
from PyQt6 import uic, QtSql
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QMessageBox,
)
from PyQt6.QtSql import QSqlTableModel
import sqlite3


class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super(WelcomeDialog, self).__init__(parent)
        uic.loadUi(os.path.join("ui", "welcome.ui"), self)

        self.pushButton.clicked.connect(self.accept)


class NewTransaction(QDialog):
    def __init__(self, conn, parent=None, main_window=None, track_data=None):
        super(NewTransaction, self).__init__(parent)
        uic.loadUi(os.path.join("ui", "new_track.ui"), self)
        self.conn = conn
        self.main_window = main_window
        self.track_id = None

        if track_data:  # Если переданы данные для редактирования
            self.populate_fields(track_data)

        self.pushButton_add.clicked.connect(self.add_new_track)

    # Функция заполнения полей данными текущей транзакции
    def populate_fields(self, track_data):
        self.comboBox_category.setCurrentText(track_data["category"])
        self.lineEdit_opisanie.setText(track_data["description"])
        self.lineEdit_summa.setText(str(track_data["balance"]))
        self.comboBox_2.setCurrentText(track_data["status"])
        self.pushButton_add.setText("Обновить")
        self.label_new_track.setText("Изменить транзакцию")

    # Функция добавляет значение новой транзакции
    def add_new_track(self):
        date = self.data.text()
        category = self.comboBox_category.currentText()
        description = self.lineEdit_opisanie.text().strip()
        balance_text = self.lineEdit_summa.text().strip()
        status = self.comboBox_2.currentText()

        # Проверка, что сумма является числом
        try:
            balance = float(balance_text)
        except ValueError:
            QMessageBox.warning(
                self, "Ошибка", "Пожалуйста, введите корректное значение для суммы."
            )
            return

        try:
            cursor = self.conn.cursor()
            if self.pushButton_add.text() == "Обновить":
                cursor.execute(
                    "UPDATE expenses SET Date=?, Category=?, Description=?, Balance=?, Status=? WHERE ID=?",
                    (date, category, description, balance, status, self.track_id),
                )
                QMessageBox.information(self, "Успех", "Транзакция успешно обновлена.")
            else:
                cursor.execute(
                    "INSERT INTO expenses (Date, Category, Description, Balance, Status) VALUES (?, ?, ?, ?, ?)",
                    (date, category, description, balance, status),
                )
                QMessageBox.information(self, "Успех", "Транзакция успешно добавлена.")
            self.conn.commit()
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Ошибка при сохранении транзакции: {str(e)}"
            )

        self.main_window.reload_date()
        self.main_window.view_data()
        self.close()  # Закрываем окно


class MoneyTraker(QMainWindow):
    def __init__(self):
        super(MoneyTraker, self).__init__()
        uic.loadUi(os.path.join("ui", "Mainwindow.ui"), self)

        # Проверяем, есть ли уже соединение
        if QtSql.QSqlDatabase.contains("qt_sql_default_connection"):
            db = QtSql.QSqlDatabase.database("qt_sql_default_connection")
            db.close()

        # Создаем новое соединение с базой данных
        self.conn = QtSql.QSqlDatabase.addDatabase(
            "QSQLITE", "qt_sql_default_connection"
        )
        self.conn.setDatabaseName("expense_db.db")

        if not self.conn.open():
            QMessageBox.critical(
                self, "Ошибка", "Не удалось подключиться к базе данных."
            )
            return
        # Создаем соединение с базой данных
        self.conn = sqlite3.connect("expense_db.db")
        self.create_table()
        self.view_data()
        self.reload_date()

        self.pushButton_new_track.clicked.connect(self.open_new_track)
        self.pushButton_izmenit_track.clicked.connect(self.edit_cur_track)
        self.pushButton_delete_track.clicked.connect(self.delete_cur_track)

    # Функция открывает окно приветствия пользователя
    def open_welcome_dialog(self):
        dialog = WelcomeDialog(self)
        if (
            dialog.exec() == QDialog.DialogCode.Accepted
        ):  # Проверяем, был ли нажата кнопка "ОК"
            return True  # Возвращаем True, если пользователь нажал "ОК"
        return False

    # Функция создает таблицу в БД
    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS expenses ("
            "ID INTEGER PRIMARY KEY AUTOINCREMENT, "
            "Date VARCHAR(20), "
            "Category VARCHAR(20), "
            "Description VARCHAR(20), "
            "Balance REAL, "
            "Status VARCHAR(20))"""
        )
        self.conn.commit()

    def closeEvent(self, event):
        self.conn.close()  # Закрываем соединение при закрытии окон
        event.accept()

    # Функция отображения данных в таблице из БД
    def view_data(self):
        self.model = QSqlTableModel(self)
        self.model.setTable("expenses")
        self.model.select()
        self.tableView.setModel(self.model)

        row_count = self.model.rowCount()
        if row_count == 0:
            QMessageBox.warning(
                self, "Нет данных", "В таблице нет данных для отображения."
            )

    # Функция обновления данных в label
    def reload_date(self):
        cursor = self.conn.cursor()
        self.label_summa.setText(self.get_total_balance(cursor))
        self.label_summa_dohod.setText(self.get_total_income(cursor))
        self.label_summa_rashod.setText(self.get_total_outcome(cursor))
        self.label_balance_shop.setText(self.get_total_shop(cursor))
        self.label_balance_enterteiment.setText(self.get_total_entertainment(cursor))
        self.label_balance_clothes.setText(self.get_total_clothes(cursor))
        self.label_balance_other.setText(self.get_total_other(cursor))

    # Функция открывает окно новой транзакции
    def open_new_track(self):
        self.new_transaction_window = NewTransaction(self.conn, self, self)
        self.new_transaction_window.show()

    # Функция редактирует текущую транзакцию
    def edit_cur_track(self):
        index = self.tableView.selectedIndexes()
        if not index:  # Проверяем, есть ли выбранные индексы
            QMessageBox.warning(
                self, "Ошибка", "Пожалуйста, выберите транзакцию для редактирования."
            )
            return

        index = index[0]
        id = str(self.tableView.model().data(index))

        # Словарь для хранения информации о выбранной транзакции из таблицы
        track_data = {
            "date": self.tableView.model().data(index.sibling(index.row(), 1)),
            "category": self.tableView.model().data(index.sibling(index.row(), 2)),
            "description": self.tableView.model().data(index.sibling(index.row(), 3)),
            "balance": self.tableView.model().data(index.sibling(index.row(), 4)),
            "status": self.tableView.model().data(index.sibling(index.row(), 5)),
        }

        # Открываем окно для редактирования и передаем данные
        self.new_transaction_window = NewTransaction(self.conn, self, self, track_data)
        self.new_transaction_window.track_id = id  # Добавляем атрибут id в текущее окно
        self.new_transaction_window.show()

    # Функция удаляет текущую транзакцию
    def delete_cur_track(self):
        index = self.tableView.selectedIndexes()
        if not index:  # Проверяем, есть ли выбранные индексы
            QMessageBox.warning(
                self, "Ошибка", "Пожалуйста, выберите транзакцию для удаления."
            )
            return

        index = index[0]
        id = str(self.tableView.model().data(index))

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE ID=?", (id,))
        self.conn.commit()
        self.reload_date()
        self.view_data()

    # Функция для labels
    def get_total_balance(self, cursor):
        cursor.execute("SELECT SUM(Balance) FROM expenses")
        return str(cursor.fetchone()[0] or 0) + " руб"

    def get_total_income(self, cursor):
        cursor.execute("SELECT SUM(Balance) FROM expenses WHERE Status='Доход'")
        return str(cursor.fetchone()[0] or 0) + " руб"

    def get_total_outcome(self, cursor):
        cursor.execute("SELECT SUM(Balance) FROM expenses WHERE Status='Расход'")
        return str(cursor.fetchone()[0] or 0) + " руб"

    def get_total_shop(self, cursor):
        cursor.execute("SELECT SUM(Balance) FROM expenses WHERE Category='Покупки'")
        return str(cursor.fetchone()[0] or 0) + " руб"

    def get_total_entertainment(self, cursor):
        cursor.execute("SELECT SUM(Balance) FROM expenses WHERE Category='Развлечения'")
        return str(cursor.fetchone()[0] or 0) + " руб"

    def get_total_clothes(self, cursor):
        cursor.execute("SELECT SUM(Balance) FROM expenses WHERE Category='Одежда'")
        return str(cursor.fetchone()[0] or 0) + " руб"

    def get_total_other(self, cursor):
        cursor.execute("SELECT SUM(Balance) FROM expenses WHERE Category='Другое'")
        return str(cursor.fetchone()[0] or 0) + " руб"


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MoneyTraker()

    if win.open_welcome_dialog():
        win.show()  # Показываем главное окно, если пользователь нажал "ОК"

    sys.exit(app.exec())
