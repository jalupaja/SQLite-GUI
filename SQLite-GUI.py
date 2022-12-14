#!/usr/bin/env python3

from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QRadioButton, QTextEdit, QLabel, QPushButton, QMessageBox, QComboBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSlot, Qt
import sys
import sqlite3


def print_error(text):
    print("\033[0;31mERROR: " + text + "\033[1;0m")


class TableView(QTableWidget):
    def __init__(self, *args):
        QTableWidget.__init__(self, *args)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.cellChanged.connect(cellChanged)


def search(search):
    if search == "":
        for row in range(qTable.rowCount()):
            qTable.setRowHidden(row, False)
    else:
        items = qTable.findItems(search, Qt.MatchFlag.MatchRegularExpression)
        searched_rows = []
        for i in items:
            searched_rows.append(i.row())
        for row in range(qTable.rowCount()):
            qTable.setRowHidden(row, row not in searched_rows)


def __update_search():
    search(txt_search.toPlainText())


def __get_selected_table():
    return box_tables.currentText()


def tablesChanged():
    previous_table = __get_selected_table()
    try:
        box_tables.currentIndexChanged.disconnect()
    except TypeError:
        pass

    box_tables.clear()
    tables = db_execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    select_index = 0
    i = 0
    for table in tables:
        box_tables.addItem(table[0])
        if table[0] == previous_table:
            select_index = i
        else:
            i += 1

    box_tables.setCurrentIndex(select_index)
    box_tables.currentIndexChanged.connect(tableButtonsChanged)


def tableButtonsChanged():
    global qTable

    selected_table = __get_selected_table()

    global renewing_table
    renewing_table = True

    qTable.clear()
    data = db_execute(f"SELECT rowid,* FROM '{selected_table}'")
    cols = data.description
    rows = data.fetchall()

    colLen = 1
    headers = []
    rowid_changed = 0
    for i in range(len(cols)):
        if cols[i][0] in headers:
            headers.pop(0)
            rowid_changed = 1
        else:
            colLen += 1
        headers.append(cols[i][0])
    headers.append(" ")

    qTable.setColumnCount(colLen)
    qTable.setRowCount(len(rows))
    qTable.setHorizontalHeaderLabels(headers)

    qTable.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    rowLen = len(rows)
    if rowLen:
        for rowCount in range(rowLen):
            for colCount in range(colLen):
                if colCount + 1 == colLen:
                    btn_del = QPushButton("x", qTable)
                    btn_del.clicked.connect(btn_push_del)
                    qTable.setCellWidget(rowCount, colCount, btn_del)
                else:
                    nItem = QTableWidgetItem()
                    nItem.setData(Qt.ItemDataRole.DisplayRole, rows[rowCount][colCount + rowid_changed])
                    qTable.setItem(rowCount, colCount, nItem)
                    if colCount == 0:
                        nItem.setFlags(nItem.flags() & Qt.ItemFlag.ItemIsEditable)
            rowCount += 1

    renewing_table = False
    __update_search()


def cellChanged(x, y):
    # fix for weird error when using tableButtonsChanged()
    if renewing_table or qTable.horizontalHeaderItem(y) is None:
        return

    # check if there are other cells in the same column that had the same text
    try:
        others = db_execute(f"SELECT {qTable.horizontalHeaderItem(y).text()} FROM '{__get_selected_table()}' WHERE {qTable.horizontalHeaderItem(y).text()}=(SELECT {qTable.horizontalHeaderItem(y).text()} FROM '{__get_selected_table()}' WHERE rowid={qTable.item(x, 0).text()})").fetchall()
    except:
        return

    if len(others) > 1 and others[0][0]:
        msg_box = QMessageBox()
        msg_box.setText(f"There are {len(others) - 1} other items in '{qTable.horizontalHeaderItem(y).text()}'.\nDo you want to change all of them too?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        res = msg_box.exec()
        if res == QMessageBox.StandardButton.Yes:
            db_execute(f"UPDATE {__get_selected_table()} SET {qTable.horizontalHeaderItem(y).text()}='{qTable.item(x, y).text()}' WHERE {qTable.horizontalHeaderItem(y).text()}='{str(others[0][0])}'")
            db_commit()
            tableButtonsChanged()
            return
        elif res == QMessageBox.StandardButton.Cancel:
            qTable.cellChanged.disconnect()
            qTable.item(x, y).setText(str(others[0][0]))
            qTable.cellChanged.connect(cellChanged)
            return

    __update_search()
    db_execute(f"UPDATE {__get_selected_table()} SET {qTable.horizontalHeaderItem(y).text()}='{qTable.item(x, y).text()}' WHERE rowid={qTable.item(x, 0).text()}")
    db_commit()


def btn_push_del():
    row = qTable.currentIndex().row()
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setText("Do you really want to delete the row?")
    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
    res = msg_box.exec()
    if res == QMessageBox.StandardButton.Yes:
        db_execute(f"DELETE FROM '{__get_selected_table()}' WHERE rowid={qTable.item(row, 0).text()}")
        db_commit()
        qTable.removeRow(row)


def btn_push_sql():
    lbl_sql_ret.setVisible(True)
    try:
        dbRes = db_execute(str(txt_sql_field.toPlainText()))
        result = dbRes.fetchall()
        db_commit()
    except Exception as e:
        lbl_sql_ret.setText(str(e))
        return
    lbl_sql_ret.setText(str(result))

    if len(result) == 0:
        lbl_sql_ret.setVisible(False)
    tablesChanged()
    tableButtonsChanged()


def db_execute(text):
    # CHANGE_HERE: This is using SQLite commands but can be changed easily
    return db.execute(text)


def db_commit():
    # CHANGE_HERE: This is using SQLite commands but can be changed easily
    con.commit()


def main(databaseLink, sys_argv=""):
    global con
    global db
    global txt_search
    global qTable
    global txt_sql_field
    global lbl_sql_ret
    global box_tables

    app = QApplication(sys_argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    try:
        # CHANGE_HERE:
        con = sqlite3.connect(sys.argv[1])
        db = con.cursor()
    except:
        print_error("Couldn't connect to database!")
        exit()

    box_tables = QComboBox()
    layout.addWidget(box_tables)
    tablesChanged()

    txt_search = QTextEdit("")
    txt_search.setAcceptRichText(False)
    txt_search.setPlaceholderText("search via RegEx: ")
    txt_search.setMaximumHeight(25)
    txt_search.textChanged.connect(__update_search)
    layout.addWidget(txt_search)

    qTable = TableView()
    layout.addWidget(qTable)

    txt_sql_field = QTextEdit("")
    txt_sql_field.setAcceptRichText(False)
    txt_sql_field.setPlaceholderText("input your SQL here: ")
    txt_sql_field.setMaximumHeight(50)
    layout.addWidget(txt_sql_field)

    lbl_sql_ret = QLabel()
    lbl_sql_ret.setVisible(False)
    lbl_sql_ret.setWordWrap(True)
    lbl_sql_ret.setTextFormat(Qt.TextFormat.MarkdownText)
    layout.addWidget(lbl_sql_ret)

    btn_sql = QPushButton("Execute")
    btn_sql.clicked.connect(btn_push_sql)
    layout.addWidget(btn_sql)

    tableButtonsChanged()

    window.show()
    sys.exit(app.exec())


if __name__=="__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1], sys.argv)
    else:
        print_error("You have to give a link to the database")
