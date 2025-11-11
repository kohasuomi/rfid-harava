import os
import sys

sys.path.append('./')

import configparser
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QMessageBox,
    QAbstractItemView, QDockWidget, QCheckBox, QLineEdit, QFormLayout,
    QToolBar,QGridLayout, QSizePolicy, QSpacerItem, QGroupBox, QHeaderView, QFrame,
    QComboBox, QButtonGroup, QRadioButton, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, QUrl, QItemSelection, QItemSelectionModel, QModelIndex
from PySide6.QtGui import QIcon, QColor, QPixmap, QAction
from PySide6.QtMultimedia import QSoundEffect

from API.ApiRequests import generate_urls, requestProcessor 

from API.ApiTokenUpdater import get_token_status

import Communication.ReaderCommunication as ReaderCommunication
from Communication.ReaderCommunication import set_communication_mode, set_selected_command, enable_afi_command, disable_afi_command

import webbrowser

import time



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("RFID Harava")
        icon = QIcon("harava.png")
        self.setWindowIcon(icon)

        self.setGeometry(100, 100, 1800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.config = configparser.RawConfigParser(allow_no_value=True)
        self.config_file = 'Configs/config.ini'
        self.config.read(self.config_file, encoding='utf-8')

        self.DynamicTable = self.load_dynamic_table_from_config()

        # Create the main table
        self.table = QTableWidget()
        self.setup_table(self.table)
        main_layout.addWidget(self.table)

        # Delete button to remove selected items
        self.delete_button = QPushButton("Poista valittu nide listalta")
        self.delete_button.clicked.connect(self.delete_selected_item)
        main_layout.addWidget(self.delete_button)

        # Initialize configuration
        self.user_config = configparser.RawConfigParser()
        self.user_config_file = 'Configs/UserSettings.ini'
        self.user_config.read(self.user_config_file, encoding='utf-8')

        self.barcode_column_name = self.config.get('TableSettings', 'barcodecolumnname', fallback='viivakoodi')

        # Fetch and populate data
        self.fetch_and_populate_data()

        # Add side panel BEFORE loading settings
        self.add_side_panel()
        self.add_right_side_panel()  # Right panel

        # Load settings AFTER side panel is created
        self.load_settings()


        # Add toolbar with action to toggle side panel
        self.add_toolbar()

        #self.add_background_image()

        self.connect_signals()


        with open("GUI/theme.css", "r") as file:
            self.setStyleSheet(file.read())
            


        # Add search functionality
        self.search_bar = QWidget()
        search_layout = QHBoxLayout(self.search_bar)
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Hakusana")
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        self.search_edit.returnPressed.connect(self.find_next)
        search_layout.addWidget(self.search_edit)

        self.next_button = QPushButton("Seuraava")
        self.next_button.clicked.connect(self.find_next)
        search_layout.addWidget(self.next_button)

        self.prev_button = QPushButton("Edellinen")
        self.prev_button.clicked.connect(self.find_previous)
        search_layout.addWidget(self.prev_button)

        self.select_all_button = QPushButton("Valitse täsmäävät")
        self.select_all_button.clicked.connect(self.select_all_matches)
        search_layout.addWidget(self.select_all_button)

        self.clear_button = QPushButton("Tyhjennä")
        self.clear_button.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_button)

        self.search_bar.setVisible(False)
        main_layout.addWidget(self.search_bar)

        self.matching_items = []
        self.current_match_index = -1





    #Search functions
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            self.search_bar.setVisible(True)
            self.search_edit.setFocus()
            self.search_edit.selectAll()
        elif event.key() == Qt.Key_Escape:
            self.clear_search()
        elif event.key() == Qt.Key_F3:
            if event.modifiers() == Qt.ShiftModifier:
                self.find_previous()
            else:
                self.find_next()
        super().keyPressEvent(event)

    def on_search_text_changed(self, text):
        self.clear_highlights()
        self.matching_items = []
        self.current_match_index = -1
        self.table.clearSelection()

        if not text:
            return

        text_lower = text.lower()
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                if self.table.isColumnHidden(col):
                    continue  # Skip hidden columns
                item = self.table.item(row, col)
                if item and text_lower in item.text().lower():
                    self.matching_items.append(item)

        if self.matching_items:
            # Sort matches by row and column for orderly cycling
            self.matching_items.sort(key=lambda item: (item.row(), item.column()))
            self.current_match_index = 0
            self.highlight_matches()
            self.select_current_match()

    def highlight_matches(self):
        for i, item in enumerate(self.matching_items):
            color = QColor(255, 255, 0) if i == self.current_match_index else QColor(211, 211, 211)  # Yellow for current, light gray for others
            item.setBackground(color)

    def clear_highlights(self):
        for item in self.matching_items:
            item.setBackground(QColor(0, 0, 0, 0))  # Transparent

    def select_current_match(self):
        if self.current_match_index >= 0 and self.matching_items:
            current_item = self.matching_items[self.current_match_index]
            #self.table.setCurrentItem(current_item)
            self.table.scrollToItem(current_item)

    def find_next(self):
        if self.matching_items:
            self.current_match_index = (self.current_match_index + 1) % len(self.matching_items)
            self.highlight_matches()
            self.select_current_match()

    def find_previous(self):
        if self.matching_items:
            self.current_match_index = (self.current_match_index - 1) % len(self.matching_items)
            self.highlight_matches()
            self.select_current_match()

    def select_all_matches(self):
        self.table.selectionModel().clear()
        matched_rows = sorted(set(item.row() for item in self.matching_items))
        selection = QItemSelection()
        for row in matched_rows:
            start = self.table.model().index(row, 0)
            end = self.table.model().index(row, self.table.columnCount() - 1)
            selection.select(start, end)
        self.table.selectionModel().select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        if matched_rows:
            first_row = min(matched_rows)
            self.table.scrollToItem(self.table.item(first_row, 0))

    def clear_search(self):
        self.search_edit.clear()
        self.clear_highlights()
        self.matching_items = []
        self.current_match_index = -1
        self.table.clearSelection()
        self.search_bar.setVisible(False)






    def add_background_image(self):
        # Create a QLabel for the image
        image_label = QLabel(self)
        pixmap = QPixmap("logo.webp")

        smaller_pixmap = pixmap.scaled(200, 100)  # Adjust size
        image_label.setPixmap(smaller_pixmap)
        
        # Ensure the label is non-interactive and stays in the background
        image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Position the label at the bottom right
        image_label.setFixedSize(smaller_pixmap.size())  # Set QLabel to the new image size
        image_label.move(self.width() - image_label.width() - 170, self.height() - image_label.height() - 50)

        # Override resizeEvent to reposition the image during window resize
        def resize_event(event):
            image_label.move(self.width() - image_label.width() - 170, self.height() - image_label.height() - 50)
            super(type(self), self).resizeEvent(event)  # Call the parent class's resize event
        
        self.resizeEvent = resize_event

    def load_dynamic_table_from_config(self):
        # Read 'DynamicTable' section into a dictionary
        if 'DynamicTable' in self.config:
            return {key: value for key, value in self.config['DynamicTable'].items()}
        else:
            raise KeyError("DynamicTable section is missing in the config file.")

    def setup_table(self, table: QTableWidget):
        headers = list(self.DynamicTable.keys())
        table.setColumnCount(len(headers) + 1)
        table.setHorizontalHeaderLabels(['#'] + headers) 

        table.setRowCount(0)
        table.resizeColumnsToContents()
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # read-only + sorting
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSortingEnabled(True)

        # column reordering
        table.horizontalHeader().setSectionsMovable(True)

        hidden_columns = self.config.get(
            'TableSettings', 'hiddencolumns', fallback=''
        ).split(',')
        hidden_columns = [col.strip() for col in hidden_columns if col.strip()]

        for header in hidden_columns:
            if header in self.DynamicTable:
                col_index = headers.index(header) + 1 
                table.horizontalHeader().setSectionHidden(col_index, True)


    def add_items_to_table(self, table, items):
        headers = list(self.DynamicTable.keys())
        barcode_column_index = headers.index(self.barcode_column_name) + 1 

        barcode_to_row = {}
        for row in range(table.rowCount()):
            itm = table.item(row, barcode_column_index)
            if itm is not None:
                barcode_to_row[itm.text()] = row

        new_items = []
        for item in items:
            self.playSound(2)

            barcode = str(item.get(self.DynamicTable[self.barcode_column_name], 'N/A'))

            # duplicate → flash & skip
            if barcode in barcode_to_row:
                existing_row = barcode_to_row[barcode]
                if existing_row is not None:
                    self.flash_row(table, existing_row)
                continue

            new_items.append((barcode, item))

        if new_items:
            sorting_enabled = table.isSortingEnabled()
            table.setSortingEnabled(False)

            start_row = table.rowCount()
            table.setRowCount(start_row + len(new_items))

            for i, (barcode, item) in enumerate(new_items):
                row_position = start_row + i

                idx_item = QTableWidgetItem()
                idx_item.setData(Qt.ItemDataRole.DisplayRole, start_row + i)
                table.setItem(row_position, 0, idx_item)

                for col, header in enumerate(headers, start=1):
                    item_key = self.DynamicTable[header]
                    value = item.get(item_key, '')

                    if value is None:
                        value = ""
                    elif isinstance(value, bool):
                        value = "Kyllä" if value else "Ei"
                    elif isinstance(value, int) and header in ("kadonnut", "lainassa"):
                        value = "Kyllä" if value == 1 else "Ei" if value == 0 else str(value)
                    elif isinstance(value, str) and header == "kuljetus":
                        if value.upper() == "T":
                            value = "Kuljetuksessa"
                        elif value.upper() == "W":
                            value = "Noudettava varaus"
                        elif value.upper() == "P":
                            value = "Käsittelyssä"

                    cell = QTableWidgetItem(str(value))
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row_position, col, cell)

                # keep the lookup dict up-to-date
                barcode_to_row[barcode] = row_position

            # restore sorting, resize, scroll
            table.setSortingEnabled(sorting_enabled)
            table.resizeColumnsToContents()
            table.scrollToBottom()

    
    def flash_row(self, table, row):

        colors = [QColor(50, 255, 50), QColor(255, 255, 255)]  # green and white colors
        current_flash_index = [0]  # List to hold the current color index
        flash_count = 0  # Counter to track the number of flashes

        def toggle_flash():
            nonlocal flash_count
            # Alternate between green and white background
            for col in range(table.columnCount()):
                if table.item is not None:
                    table.item(row, col).setBackground(colors[current_flash_index[0]])
                
            # Update the flash index to alternate the color
            current_flash_index[0] = (current_flash_index[0] + 1) % 2
            
            flash_count += 1
            if flash_count >= 6:  # After 3 cycles (6 flashes)
                # Reset to white and stop the timer
                for col in range(table.columnCount()):
                    table.item(row, col).setBackground(colors[1])  # Set background to white
                flash_timer.stop()

        # Set up a timer to flash the row
        flash_timer = QTimer(self)
        flash_timer.timeout.connect(toggle_flash)
        flash_timer.start(50)  # Change color every 50 ms

    def delete_selected_item(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            # Collect unique row indices from selected items
            rows_to_delete = set(item.row() for item in selected_items)

            # Sort the rows in descending order
            for row in sorted(rows_to_delete, reverse=True):
                self.table.removeRow(row)
            
            self.table.resizeColumnsToContents()
        else:
            QMessageBox.warning(self, "Ei valintaa", "Valitse poistettava rivi ensin. Voit valita useamman rivin kerralla.")

    def clear_table(self, table):
        table.setRowCount(0)

    def fetch_and_populate_data(self):
        base_url = ""
        report_id = ""
        barcodes = [""]
        APIToken = ""
        batch_size = 2

        # generate_urls and requestProcessor are defined in ApiRequests.py
        urls = generate_urls(base_url, report_id, barcodes, batch_size)
        merged_data = requestProcessor(urls, APIToken)

        if merged_data and isinstance(merged_data[0], dict):
            print(f"Data format looks good: {merged_data[0]}")  # Debugging
        else:
            print(f"Unexpected data format: {merged_data}")  # Debugging
            return

        self.add_items_to_table(self.table, merged_data)















    #Side panel UIs

    def add_side_panel(self):
        """Adds a dockable side panel with categorized checkboxes and text fields."""
        self.settings_dock = QDockWidget("Settings", self)
        self.settings_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.settings_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.settings_dock.setTitleBarWidget(QWidget())

        side_panel = QWidget()
        self.settings_dock.setWidget(side_panel)
        layout = QVBoxLayout(side_panel)

        # Use QGridLayout to place categories in two columns
        grid_layout = QGridLayout()

        # top-level Checkboxes
        self.collectAll = QCheckBox('Kerää kaikki')
        self.lost = QCheckBox("Kadonnut")
        self.onloan = QCheckBox("Lainassa")
        self.notforloan = QCheckBox("Ei lainata (nfl)")

        self.textbox1_label = QLabel("Kirjasto (Nidemäärän lasku)")
        self.library = QLineEdit()
        self.textbox2_label = QLabel("Osasto (Nidemäärän lasku)")
        self.department = QLineEdit()

        textboxes_layout = QVBoxLayout()
        textboxes_layout.addWidget(self.textbox1_label)
        textboxes_layout.addWidget(self.library)
        textboxes_layout.addWidget(self.textbox2_label)
        textboxes_layout.addWidget(self.department)

        # Add the checkboxes at the top
        checkboxes_layout = QVBoxLayout()
        checkboxes_layout.addWidget(self.collectAll)
        checkboxes_layout.addWidget(self.lost)
        checkboxes_layout.addWidget(self.onloan)
        checkboxes_layout.addWidget(self.notforloan)

        grid_layout.addLayout(checkboxes_layout, 0, 0) 
        grid_layout.addLayout(textboxes_layout, 0, 1)

        # Helper function to create compact QGroupBox
        def create_compact_groupbox(title, elements):
            group_box = QGroupBox(title)
            layout = QVBoxLayout(group_box)
            layout.setSpacing(2)  # Reduced spacing
            layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins
            for element in elements:
                layout.addWidget(element)
            return group_box

        # Create the QGroupBox for each category and place them in the grid
        self.found_checkbox = QCheckBox("Käytössä")
        self.found_checkbox.stateChanged.connect(self.toggle_filters)
        self.found_checkbox1 = QCheckBox("Kuljetuksessa")
        self.found_checkbox2 = QCheckBox("Noudettava varaus")
        self.found_checkbox3 = QCheckBox("Käsittelyssä")
        self.found_checkbox4 = QCheckBox("Niteellä on nämä tilat")
        self.found_checkbox5 = QCheckBox("Niteellä ei ole näitä tiloja")
        status_group = create_compact_groupbox("Tilat", [self.found_checkbox1, self.found_checkbox2, self.found_checkbox3])
        equal_group = create_compact_groupbox("Kriteeri", [self.found_checkbox4, self.found_checkbox5])
        found_group = create_compact_groupbox("Erikoistilat", 
            [self.found_checkbox, status_group, equal_group])
        grid_layout.addWidget(found_group, 1, 0)
        
        # Create the list widget for .txt files in "Lists" folder
        self.file_list = QListWidget()
        lists_folder = "Lists"
        if os.path.exists(lists_folder):
            txt_files = [f for f in os.listdir(lists_folder) if f.endswith('.txt')]
            for file_name in txt_files:
                item = QListWidgetItem(file_name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)  # Start unchecked (disabled)
                self.file_list.addItem(item)

        # Connect to toggle_filters when any item's check state changes
        self.file_list.itemChanged.connect(self.toggle_filters)
        self.file_list.itemChanged.connect(self.save_settings)
        self.file_list.setMaximumWidth(125)

        # Create a compact group box for the list
        lists_group = create_compact_groupbox("Listat", [self.file_list])
        
        self.barcode_checkbox = QCheckBox("Käytössä")
        self.barcode_checkbox.stateChanged.connect(self.toggle_filters)
        self.barcode_textfield = QLineEdit()
        barcode_group = create_compact_groupbox("Nidetunnushaku", 
            [self.barcode_checkbox, self.barcode_textfield, lists_group])
        grid_layout.addWidget(barcode_group, 1, 1)
    

        
        # Category 1
        self.callnumber_checkbox = QCheckBox("Käytössä")
        self.callnumber_checkbox.stateChanged.connect(self.toggle_filters)
        self.callnumber_textfield = QLineEdit()
        self.callnumber_checkbox1 = QCheckBox("Sisältyy")
        self.callnumber_checkbox2 = QCheckBox("Ei sisälly")
        callnumber_group = create_compact_groupbox("Luokka", 
            [self.callnumber_checkbox, self.callnumber_textfield, self.callnumber_checkbox1, self.callnumber_checkbox2])
        grid_layout.addWidget(callnumber_group, 2, 0) 

        # Category 2
        self.department_checkbox = QCheckBox("Käytössä")
        self.department_checkbox.stateChanged.connect(self.toggle_filters)
        self.department_textfield = QLineEdit()
        self.department_checkbox1 = QCheckBox("Sisältyy")
        self.department_checkbox2 = QCheckBox("Ei sisälly")
        department_group = create_compact_groupbox("Osasto", 
            [self.department_checkbox, self.department_textfield, self.department_checkbox1, self.department_checkbox2])
        grid_layout.addWidget(department_group, 2, 1)  

        # Category 3
        self.count_checkbox = QCheckBox("Käytössä")
        self.count_checkbox.stateChanged.connect(self.toggle_filters)
        self.count_textfield = QLineEdit()
        self.count_checkbox3 = QCheckBox("Koko kimpassa")
        self.count_checkbox4 = QCheckBox("Tässä kirjastossa")
        self.count_checkbox5 = QCheckBox("Tällä osastolla")
        self.count_checkbox1 = QCheckBox("Enemmän")
        self.count_checkbox2 = QCheckBox("Vähemmän")
        location_group = create_compact_groupbox("Sijainti", [self.count_checkbox3, self.count_checkbox4, self.count_checkbox5])
        quantity_group = create_compact_groupbox("Määrä", [self.count_checkbox1, self.count_checkbox2])
        count_group = create_compact_groupbox("Määrä", 
            [self.count_checkbox, self.count_textfield, location_group, quantity_group])
        grid_layout.addWidget(count_group, 3, 0) 

        # Category 4
        self.library_checkbox = QCheckBox("Käytössä")
        self.library_checkbox.stateChanged.connect(self.toggle_filters)
        self.library_textfield = QLineEdit()
        self.library_checkbox1 = QCheckBox("Sisältyy")
        self.library_checkbox2 = QCheckBox("Ei sisälly")
        self.current_library_textfield = QLineEdit()
        self.current_library_checkbox1 = QCheckBox("Sisältyy")
        self.current_library_checkbox2 = QCheckBox("Ei sisälly")

        home_library_group = create_compact_groupbox("Kotikirjasto", 
            [self.library_textfield, self.library_checkbox1, self.library_checkbox2])
        current_library_group = create_compact_groupbox("Sijaintikirjasto",
            [self.current_library_textfield, self.current_library_checkbox1, self.current_library_checkbox2])
        library_group = create_compact_groupbox("Kirjasto", [self.library_checkbox, home_library_group, current_library_group ])
        grid_layout.addWidget(library_group, 3, 1)

        # Category 5
        self.loan_checkbox = QCheckBox("Käytössä")
        self.loan_checkbox.stateChanged.connect(self.toggle_filters)
        self.loan_textfield = QLineEdit()
        self.loan_checkbox1 = QCheckBox("Ennen")
        self.loan_checkbox2 = QCheckBox("Jälkeen")
        loan_group = create_compact_groupbox("Lainattu viimeksi", 
            [self.loan_checkbox, self.loan_textfield, self.loan_checkbox1, self.loan_checkbox2])
        grid_layout.addWidget(loan_group, 4, 0) 
        
        # Category 4
        self.collection_checkbox = QCheckBox("Käytössä")
        self.collection_checkbox.stateChanged.connect(self.toggle_filters)
        self.collection_textfield = QLineEdit()
        self.collection_checkbox1 = QCheckBox("Sisältyy")
        self.collection_checkbox2 = QCheckBox("Ei sisälly")
        self.collection_separator = QLabel("----------------------------")
        self.collection_checkbox3 = QCheckBox("Ei kokoelmatietoa")
        self.collection_checkbox4 = QCheckBox("Jokin kokoelmatieto")
        collection_group = create_compact_groupbox("Kokoelma", 
            [self.collection_checkbox, self.collection_textfield, self.collection_checkbox1, self.collection_checkbox2, self.collection_separator, self.collection_checkbox3, self.collection_checkbox4])
        grid_layout.addWidget(collection_group, 4, 1) 

        # Add the grid layout to the main layout
        layout.addLayout(grid_layout)

        # Save Button
        #save_button = QPushButton("Tallenna")
        #save_button.clicked.connect(self.save_settings)
        #layout.addWidget(save_button)

        # Add the dock to the main window
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.settings_dock)
        # Enable correct state to widgets on startup
        self.toggle_filters()
        # Connect visibilityChanged signal to update toolbar action
        self.settings_dock.visibilityChanged.connect(self.update_toolbar_action)
        



    def toggle_filters(self):
        # Toggle inputs if category disabled

        is_checked = self.callnumber_checkbox.isChecked()
        self.callnumber_textfield.setEnabled(is_checked)
        self.callnumber_checkbox1.setEnabled(is_checked)
        self.callnumber_checkbox2.setEnabled(is_checked)
        
        is_checked = self.department_checkbox.isChecked()
        self.department_textfield.setEnabled(is_checked)
        self.department_checkbox1.setEnabled(is_checked)
        self.department_checkbox2.setEnabled(is_checked)
        
        is_checked = self.found_checkbox.isChecked()
        self.found_checkbox1.setEnabled(is_checked)
        self.found_checkbox2.setEnabled(is_checked)
        self.found_checkbox3.setEnabled(is_checked)
        self.found_checkbox4.setEnabled(is_checked)
        self.found_checkbox5.setEnabled(is_checked)
        
        is_checked = self.count_checkbox.isChecked()
        self.count_textfield.setEnabled(is_checked)
        self.count_checkbox1.setEnabled(is_checked)
        self.count_checkbox2.setEnabled(is_checked)
        self.count_checkbox3.setEnabled(is_checked)
        self.count_checkbox4.setEnabled(is_checked)
        self.count_checkbox5.setEnabled(is_checked)
        
        
        # Fetch the column names from 'CountSettings' section
        column_names_to_toggle = self.config.get('TableSettings', 'countcolumns', fallback='').split(',')
        column_names_to_toggle = [col.strip() for col in column_names_to_toggle if col.strip()]


        # Iterate through each column name and toggle visibility based on checkbox state
        for column_name in column_names_to_toggle:
            # Check if the column name exists in self.DynamicTable
            if column_name in self.DynamicTable:
                col_index = list(self.DynamicTable.keys()).index(column_name)
                self.table.horizontalHeader().setSectionHidden(col_index+1, not self.count_checkbox.isChecked())
                
                
        library_names_to_toggle = self.config.get('TableSettings', 'librarycolums', fallback='').split(',')
        library_names_to_toggle = [col.strip() for col in library_names_to_toggle if col.strip()]


        # Iterate through each column name and toggle visibility based on checkbox state
        for column_name in library_names_to_toggle:
            # Check if the column name exists in self.DynamicTable
            if column_name in self.DynamicTable:
                col_index = list(self.DynamicTable.keys()).index(column_name)
                self.table.horizontalHeader().setSectionHidden(col_index+1, not self.library_checkbox.isChecked())
                

        self.library.setEnabled(is_checked)
        self.department.setEnabled(is_checked)
        
        is_checked = self.library_checkbox.isChecked()
        self.library_textfield.setEnabled(is_checked)
        self.library_checkbox1.setEnabled(is_checked)
        self.library_checkbox2.setEnabled(is_checked)
        self.current_library_textfield.setEnabled(is_checked)
        self.current_library_checkbox1.setEnabled(is_checked)
        self.current_library_checkbox2.setEnabled(is_checked)

        is_checked = self.loan_checkbox.isChecked()
        self.loan_textfield.setEnabled(is_checked)
        self.loan_checkbox1.setEnabled(is_checked)
        self.loan_checkbox2.setEnabled(is_checked)
        
        is_checked = self.collection_checkbox.isChecked()
        self.collection_textfield.setEnabled(is_checked)
        self.collection_checkbox1.setEnabled(is_checked)
        self.collection_checkbox2.setEnabled(is_checked)
        self.collection_checkbox3.setEnabled(is_checked)
        self.collection_checkbox4.setEnabled(is_checked)

        is_checked = self.barcode_checkbox.isChecked()
        self.barcode_textfield.setEnabled(is_checked)
        


    def connect_signals(self):
        """Connect signals to save settings only after loading is complete."""
        self.collectAll.stateChanged.connect(self.save_settings)
        
        self.lost.stateChanged.connect(self.save_settings)
        self.onloan.stateChanged.connect(self.save_settings)
        self.notforloan.stateChanged.connect(self.save_settings)

        self.department.textChanged.connect(self.save_settings)
        self.library.textChanged.connect(self.save_settings)

        self.found_checkbox.stateChanged.connect(self.save_settings)
        self.found_checkbox1.stateChanged.connect(self.save_settings)
        self.found_checkbox2.stateChanged.connect(self.save_settings)
        self.found_checkbox3.stateChanged.connect(self.save_settings)
        self.found_checkbox4.stateChanged.connect(self.save_settings)
        self.found_checkbox5.stateChanged.connect(self.save_settings)

        # Barcode group
        self.barcode_checkbox.stateChanged.connect(self.save_settings)
        self.barcode_textfield.textChanged.connect(self.save_settings)

        # Callnumber (Category 1) group
        self.callnumber_checkbox.stateChanged.connect(self.save_settings)
        self.callnumber_textfield.textChanged.connect(self.save_settings)
        self.callnumber_checkbox1.stateChanged.connect(self.save_settings)
        self.callnumber_checkbox2.stateChanged.connect(self.save_settings)

        # Department (Category 2) group
        self.department_checkbox.stateChanged.connect(self.save_settings)
        self.department_textfield.textChanged.connect(self.save_settings)
        self.department_checkbox1.stateChanged.connect(self.save_settings)
        self.department_checkbox2.stateChanged.connect(self.save_settings)

        # Count (Category 3) group
        self.count_checkbox.stateChanged.connect(self.save_settings)
        self.count_textfield.textChanged.connect(self.save_settings)
        self.count_checkbox3.stateChanged.connect(self.save_settings)
        self.count_checkbox4.stateChanged.connect(self.save_settings)
        self.count_checkbox5.stateChanged.connect(self.save_settings)
        self.count_checkbox1.stateChanged.connect(self.save_settings)
        self.count_checkbox2.stateChanged.connect(self.save_settings)

        # Library (Category 4) group
        self.library_checkbox.stateChanged.connect(self.save_settings)
        self.library_textfield.textChanged.connect(self.save_settings)
        self.library_checkbox1.stateChanged.connect(self.save_settings)
        self.library_checkbox2.stateChanged.connect(self.save_settings)
        self.current_library_textfield.textChanged.connect(self.save_settings)
        self.current_library_checkbox1.stateChanged.connect(self.save_settings)
        self.current_library_checkbox2.stateChanged.connect(self.save_settings)

        # Loan (Category 5) group
        self.loan_checkbox.stateChanged.connect(self.save_settings)
        self.loan_textfield.textChanged.connect(self.save_settings)
        self.loan_checkbox1.stateChanged.connect(self.save_settings)
        self.loan_checkbox2.stateChanged.connect(self.save_settings)

        # Collection (Category 6) group
        self.collection_checkbox.stateChanged.connect(self.save_settings)
        self.collection_textfield.textChanged.connect(self.save_settings)
        self.collection_checkbox1.stateChanged.connect(self.save_settings)
        self.collection_checkbox2.stateChanged.connect(self.save_settings)
        self.collection_checkbox3.stateChanged.connect(self.save_settings)
        self.collection_checkbox4.stateChanged.connect(self.save_settings)




    def add_right_side_panel(self):
        """Adds a dockable right-side panel with larger buttons in a grid layout."""
        self.control_dock = QDockWidget("Toiminnot", self)
        self.control_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        # Remove title bar and close button
        self.control_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.control_dock.setTitleBarWidget(QWidget())
        right_panel = QWidget()
        self.control_dock.setWidget(right_panel)
        
        main_layout = QVBoxLayout(right_panel)
        main_layout.setSpacing(2)  # Reduce overall spacing between major sections
        main_layout.setContentsMargins(8, 8, 8, 8)  # Tighten main margins for a compact sidebar

        mode_group = QGroupBox("Toiminta tila")
        mode_layout = QVBoxLayout()
        mode_layout.setSpacing(2)  # Reduced spacing to minimize gaps
        mode_layout.setContentsMargins(8, 8, 8, 8)  # Slightly reduced margins for compactness

        # Mode label and combo
        mode_label = QLabel("Valitse tila:")
        mode_layout.addWidget(mode_label)
        mode_label.setObjectName("mode_label")
        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("mode_combo")
        self.mode_combo.addItems(["Scan", "AFI"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_group.setLayout(mode_layout)
        mode_group.setFixedHeight(200)
        mode_layout.addWidget(self.mode_combo)
        

        # Nested Command Group (inside Mode Group)
        command_group_box = QGroupBox("Toiminnon valinta")
        command_layout = QVBoxLayout()
        command_layout.setSpacing(6)  # Reduced spacing
        command_layout.setContentsMargins(2, 2, 2, 2)  # Reduced inner margins

        # Command selection elements and selection protection
        command_label = QLabel("Valitse toiminto:")
        command_layout.addWidget(command_label)
        self.command_group = QButtonGroup(self)
        self.enable_afi_cmd = QRadioButton("Aktivoi hälytys")
        self.disable_afi_cmd = QRadioButton("Poista hälytys")
        self.command_group.addButton(self.enable_afi_cmd)
        self.command_group.addButton(self.disable_afi_cmd)
        command_layout.addWidget(self.enable_afi_cmd)
        command_layout.addWidget(self.disable_afi_cmd)
        self.enable_afi_cmd.toggled.connect(self.on_command_changed)
        self.disable_afi_cmd.toggled.connect(self.on_command_changed)
        command_group_box.setLayout(command_layout)
        mode_layout.addWidget(command_group_box)  # Add nested group to mode layout

        # Finalize outer group
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        # Initially disable command group and set default mode
        self.update_command_ui(False)
        self.mode_combo.setCurrentText("Scan")  # Start in Scan mode

        sound_group = QGroupBox("Ilmoitusäänet")
        sound_layout = QVBoxLayout()
        sound_layout.setSpacing(2)  # Reduced spacing
        sound_layout.setContentsMargins(8, 8, 8, 8)  # Matching reduced margins

        self.notification_sound_checkbox = QCheckBox("Niteet", self)
        self.warning_sound_checkbox = QCheckBox("Yhteys haravaan", self)
        sound_layout.addWidget(self.notification_sound_checkbox)
        sound_layout.addWidget(self.warning_sound_checkbox)

        sound_group.setLayout(sound_layout)
        sound_group.setFixedHeight(80)
        main_layout.addWidget(sound_group)

        # === Actions Group ===
        actions_group = QGroupBox("Toiminnot")
        actions_layout = QVBoxLayout()  # Use VBox for simplicity, but can switch back to grid if needed
        actions_layout.setSpacing(2)  # Reduced spacing
        actions_layout.setContentsMargins(8, 8, 8, 8)  # Matching reduced margins

        # Buttons connected to external functions
        kohaButton = QPushButton("Avaa Kohassa")
        kohaButton.clicked.connect(self.open_in_koha)
        copyButton = QPushButton("Kopio viivakoodit")
        copyButton.clicked.connect(self.copy_barcodes)

        # Optionally set a fixed size (optional)
        kohaButton.setFixedSize(120, 35)
        copyButton.setFixedSize(120, 35)

        # Add buttons to the layout (stacked vertically for single-column feel)
        actions_layout.addWidget(kohaButton)
        actions_layout.addWidget(copyButton)

        actions_group.setLayout(actions_layout)
        actions_group.setLayout(actions_layout)
        actions_group.setFixedHeight(150)
        main_layout.addWidget(actions_group)

        # Add dock to the right side of the window
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.control_dock)
        # Connect visibilityChanged signal to update toolbar action
        self.control_dock.visibilityChanged.connect(self.update_toolbar_action_control_panel)
        
        
    def on_mode_changed(self, mode_text):
        """Slot for mode change."""
        if mode_text == "Scan":
            set_communication_mode('scan')
            self.update_command_ui(False)
        elif mode_text == "AFI":
            set_communication_mode('AFI')
            self.update_command_ui(True)
            self.on_command_changed()  # Trigger initial command selection

    def on_command_changed(self):
        """Slot for command change."""
        if self.enable_afi_cmd.isChecked():
            set_selected_command(enable_afi_command)
        elif self.disable_afi_cmd.isChecked():
            set_selected_command(disable_afi_command)

    def update_command_ui(self, enabled):
        """Enable/disable command selection based on mode."""
        self.enable_afi_cmd.setEnabled(enabled)
        self.disable_afi_cmd.setEnabled(enabled)
        if enabled and not self.command_group.checkedButton():
            self.enable_afi_cmd.setChecked(True)  # Default to Command 1 if none selected

    def add_toolbar(self):
        """Adds a toolbar with toggle buttons, a centered IP dropdown, and a connection status label."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # Create an action to toggle the settings dock
        self.toggle_settings_action = QAction("Hakukriteerit", self)
        self.toggle_settings_action.setCheckable(True)
        self.toggle_settings_action.setChecked(True)  # Assuming dock is visible by default
        self.toggle_settings_action.triggered.connect(self.toggle_side_panel)

        # Action to toggle the right control panel
        self.toggle_control_panel_action = QAction("Toiminnot", self)
        self.toggle_control_panel_action.setCheckable(True)
        self.toggle_control_panel_action.setChecked(True)  # Assuming dock is visible by default
        self.toggle_control_panel_action.triggered.connect(self.toggle_right_side_panel)

        # Add actions to toolbar
        toolbar.addAction(self.toggle_control_panel_action)
        toolbar.addAction(self.toggle_settings_action)

        # Add a spacer to push the dropdown towards the center
        left_spacer = QWidget()
        left_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(left_spacer)

        # Create and populate the IP dropdown
        ip_select_label = QLabel("Valitse käytettävä harava:")
        ip_select_label.setObjectName("ip_select_label")
        toolbar.addWidget(ip_select_label)
        ip_dropdown = QComboBox()
        ip_dropdown.setObjectName("ipDropdown")
        
        # Load IPs from config.ini
        config = configparser.ConfigParser()
        config.read('configs/config.ini')
        if 'IPs' in config:
            for key, ip in config['IPs'].items():
                display_text = f"{key}  ||   {ip}"
                ip_dropdown.addItem(display_text, ip)  # Store IP as user data
        
        # Connect dropdown selection change to placeholder function
        ip_dropdown.currentIndexChanged.connect(self.on_ip_selection_changed)
        
        # Add dropdown to toolbar
        toolbar.addWidget(ip_dropdown)

        # Add a spacer to center the dropdown
        right_spacer = QWidget()
        right_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(right_spacer)

        # Create a container widget for horizontal layout of labels
        self.status_container = QWidget()
        status_layout = QHBoxLayout(self.status_container)
        self.status_container.setObjectName("statusContainer")
        status_layout.setContentsMargins(10, 4, 10, 4)
        status_layout.setSpacing(10)

        # Create the connection status label
        self.connection_status_label = QLabel("Yhteys: ")
        self.connection_status_label.setObjectName("connectionStatusLabel")
        status_layout.addWidget(self.connection_status_label)

        # Add a vertical separator line
        separator = QFrame()
        separator.setObjectName("statusSeparator")
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        status_layout.addWidget(separator)

        # Create the second label
        self.api_label = QLabel("Koha: ")
        self.api_label.setObjectName("secondLabel")
        status_layout.addWidget(self.api_label)

        # Add the container to the toolbar
        toolbar.addWidget(self.status_container)
        
        # Add a small spacer to create padding at the right edge
        edge_spacer = QWidget()
        edge_spacer.setFixedWidth(8)
        toolbar.addWidget(edge_spacer)

        # Set up a timer to update the connection status every 500ms
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_statuses)
        self.status_timer.start(500)

    def on_ip_selection_changed(self, index):
        """Handles IP selection changes by saving the selected IP to config.ini."""
        # Get the dropdown widget
        ip_dropdown = self.findChild(QComboBox, "ipDropdown")
        if ip_dropdown:
            selected_ip = ip_dropdown.currentData()  # Retrieve the IP from user data
            
            # Update config.ini with the selected IP
            config = configparser.ConfigParser()
            config.read('Configs/config.ini', encoding='utf-8')
            
            # Ensure the 'Settings' section exists
            if 'Harava' not in config:
                config['Harava'] = {}
                
            # Save the selected IP to the config file
            config['Harava']['ip'] = selected_ip
            
            # Write the updated config to the file
            with open('Configs/config.ini', 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        
        self.restart_listener()

    def update_statuses(self):
        """Fetches and updates both connection and API statuses, then sets the container state accordingly."""
        # Fetch statuses
        connection_status = ReaderCommunication.get_status()
        api_status = get_token_status()

        # Update labels
        self.connection_status_label.setText(f"Yhteys: {connection_status}")
        self.api_label.setText(f"Koha: {api_status}")

        # Handle sound for connection error
        if connection_status == "Yritetään muodostaa yhteyttä":
            self.playSound(1)

        # Set container state: "OK" only if both are good, else "error"
        if (connection_status != "Yritetään muodostaa yhteyttä" and api_status == "OK"):
            self.status_container.setProperty("state", "OK")
            self.connection_status_label.setProperty("state", "OK")
            self.api_label.setProperty("state", "OK")
        else:
            self.status_container.setProperty("state", "error")
            self.connection_status_label.setProperty("state", "error")
            self.api_label.setProperty("state", "error")

        # Apply the style change
        self.status_container.style().polish(self.status_container)
        self.connection_status_label.style().polish(self.connection_status_label)
        self.api_label.style().polish(self.api_label)

    def toggle_side_panel(self, checked):
        """Toggle the visibility of the side panel."""
        self.settings_dock.setVisible(checked)

    def update_toolbar_action(self, visible):
        """Update the toolbar action's checked state based on dock visibility."""
        self.toggle_settings_action.setChecked(visible)

    def toggle_right_side_panel(self, checked):
        """Toggle the visibility of the right side control panel."""
        self.control_dock.setVisible(checked)

    def update_toolbar_action_control_panel(self, visible):
        """Update the toolbar action's checked state for the control panel."""
        self.toggle_control_panel_action.setChecked(visible)














    #Saving the settings

    def load_settings(self):
        """Load settings from config.ini into the side panel controls."""
        self.user_config.read(self.user_config_file, encoding='utf-8')

        # Load top-level checkbox states
        self.collectAll.setChecked(self.user_config.getboolean('Conditions', 'collectall', fallback=False))
        self.lost.setChecked(self.user_config.getboolean('Conditions', 'CheckItemLost', fallback=False))
        self.onloan.setChecked(self.user_config.getboolean('Conditions', 'CheckOnLoan', fallback=False))
        self.notforloan.setChecked(self.user_config.getboolean('Conditions', 'NotForLoan', fallback=False))
        self.library.setText(self.user_config.get('Conditions', 'Library', fallback=''))
        self.department.setText(self.user_config.get('Conditions', 'Department', fallback=''))

        self.barcode_checkbox.setChecked(self.user_config.getboolean('Barcode', 'Enabled', fallback=False))
        self.barcode_textfield.setText(self.user_config.get('Barcode', 'Text', fallback=''))

        self.found_checkbox.setChecked(self.user_config.getboolean('Found', 'Enabled', fallback=False))
        self.found_checkbox1.setChecked(self.user_config.getboolean('Found', 'Option1', fallback=False))
        self.found_checkbox2.setChecked(self.user_config.getboolean('Found', 'Option2', fallback=False))
        self.found_checkbox3.setChecked(self.user_config.getboolean('Found', 'Option3', fallback=False))
        self.found_checkbox4.setChecked(self.user_config.getboolean('Found', 'Option4', fallback=False))
        self.found_checkbox5.setChecked(self.user_config.getboolean('Found', 'Option5', fallback=False))

        # Load Category 1 settings
        self.callnumber_checkbox.setChecked(self.user_config.getboolean('Callnumber', 'Enabled', fallback=False))
        self.callnumber_textfield.setText(self.user_config.get('Callnumber', 'Text', fallback=''))
        self.callnumber_checkbox1.setChecked(self.user_config.getboolean('Callnumber', 'Option1', fallback=False))
        self.callnumber_checkbox2.setChecked(self.user_config.getboolean('Callnumber', 'Option2', fallback=False))

        # Load Category 2 settings
        self.department_checkbox.setChecked(self.user_config.getboolean('Department', 'Enabled', fallback=False))
        self.department_textfield.setText(self.user_config.get('Department', 'Text', fallback=''))
        self.department_checkbox1.setChecked(self.user_config.getboolean('Department', 'Option1', fallback=False))
        self.department_checkbox2.setChecked(self.user_config.getboolean('Department', 'Option2', fallback=False))

        # Load Category 3 settings
        self.count_checkbox.setChecked(self.user_config.getboolean('Count', 'Enabled', fallback=False))
        self.count_textfield.setText(self.user_config.get('Count', 'Text', fallback=''))
        self.count_checkbox1.setChecked(self.user_config.getboolean('Count', 'Option1', fallback=False))
        self.count_checkbox2.setChecked(self.user_config.getboolean('Count', 'Option2', fallback=False))
        self.count_checkbox3.setChecked(self.user_config.getboolean('Count', 'Option3', fallback=False))
        self.count_checkbox4.setChecked(self.user_config.getboolean('Count', 'Option4', fallback=False))
        self.count_checkbox5.setChecked(self.user_config.getboolean('Count', 'Option5', fallback=False))
        
        # Load Category 4 settings
        self.library_checkbox.setChecked(self.user_config.getboolean('Library', 'Enabled', fallback=False))
        self.library_textfield.setText(self.user_config.get('Library', 'Text', fallback=''))
        self.library_checkbox1.setChecked(self.user_config.getboolean('Library', 'Option1', fallback=False))
        self.library_checkbox2.setChecked(self.user_config.getboolean('Library', 'Option2', fallback=False))
        self.current_library_textfield.setText(self.user_config.get('Library', 'Text2', fallback=''))
        self.current_library_checkbox1.setChecked(self.user_config.getboolean('Library', 'Option3', fallback=False))
        self.current_library_checkbox2.setChecked(self.user_config.getboolean('Library', 'Option4', fallback=False))

        # Load Category 5 settings
        self.loan_checkbox.setChecked(self.user_config.getboolean('Loan', 'Enabled', fallback=False))
        self.loan_textfield.setText(self.user_config.get('Loan', 'Text', fallback=''))
        self.loan_checkbox1.setChecked(self.user_config.getboolean('Loan', 'Option1', fallback=False))
        self.loan_checkbox2.setChecked(self.user_config.getboolean('Loan', 'Option2', fallback=False))

        self.collection_checkbox.setChecked(self.user_config.getboolean('Collection', 'Enabled', fallback=False))
        self.collection_textfield.setText(self.user_config.get('Collection', 'Text', fallback=''))
        self.collection_checkbox1.setChecked(self.user_config.getboolean('Collection', 'Option1', fallback=False))
        self.collection_checkbox2.setChecked(self.user_config.getboolean('Collection', 'Option2', fallback=False))
        self.collection_checkbox3.setChecked(self.user_config.getboolean('Collection', 'Option3', fallback=False))
        self.collection_checkbox4.setChecked(self.user_config.getboolean('Collection', 'Option4', fallback=False))
        
        # Load enabled lists from config
        enabled_lists_str = self.user_config.get('Lists', 'text', fallback='')
        enabled_lists = [name.strip() for name in enabled_lists_str.split(',') if name.strip()]

        # Check the items that are in the enabled lists
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.text() in enabled_lists:
                item.setCheckState(Qt.Checked)
        
    def save_settings(self):
        """Save the side panel settings to UserSettings.ini."""
        if not self.user_config.has_section('Conditions'):
            self.user_config.add_section('Conditions')
            
        # Get the list of checked file names
        checked_lists = [
            self.file_list.item(i).text()
            for i in range(self.file_list.count())
            if self.file_list.item(i).checkState() == Qt.Checked
        ]
        
        # Set the 'text' as comma-separated checked lists
        self.user_config.set('Lists', 'text', ','.join(checked_lists))
        
        # Set 'enabled' to true if any lists are checked, else false
        self.user_config.set('Lists', 'enabled', 'true' if checked_lists else 'false')
        
        # Write the config to file
        with open('Configs/UserSettings.ini', 'w') as configfile:
            self.user_config.write(configfile)

        # Save top-level checkboxes
        self.user_config.set('Conditions', 'collectall', str(self.collectAll.isChecked()))
        self.user_config.set('Conditions', 'CheckItemLost', str(self.lost.isChecked()))
        self.user_config.set('Conditions', 'CheckOnLoan', str(self.onloan.isChecked()))
        self.user_config.set('Conditions', 'NotForLoan', str(self.notforloan.isChecked()))
        self.user_config.set('Conditions', 'Library', self.library.text())
        self.user_config.set('Conditions', 'Department', self.department.text())

        if not self.user_config.has_section('Barcode'):
            self.user_config.add_section('Barcode')
        self.user_config.set('Barcode', 'Enabled', str(self.barcode_checkbox.isChecked()))
        self.user_config.set('Barcode', 'Text', self.barcode_textfield.text())

        if not self.user_config.has_section('Found'):
            self.user_config.add_section('Found')
        self.user_config.set('Found', 'Enabled', str(self.found_checkbox.isChecked()))
        self.user_config.set('Found', 'Option1', str(self.found_checkbox1.isChecked()))
        self.user_config.set('Found', 'Option2', str(self.found_checkbox2.isChecked()))
        self.user_config.set('Found', 'Option3', str(self.found_checkbox3.isChecked()))
        self.user_config.set('Found', 'Option4', str(self.found_checkbox4.isChecked()))
        self.user_config.set('Found', 'Option5', str(self.found_checkbox5.isChecked()))

        # Save Category 1 settings
        if not self.user_config.has_section('Callnumber'):
            self.user_config.add_section('Callnumber')
        self.user_config.set('Callnumber', 'Enabled', str(self.callnumber_checkbox.isChecked()))
        self.user_config.set('Callnumber', 'Text', self.callnumber_textfield.text())
        self.user_config.set('Callnumber', 'Option1', str(self.callnumber_checkbox1.isChecked()))
        self.user_config.set('Callnumber', 'Option2', str(self.callnumber_checkbox2.isChecked()))

        # Save Category 2 settings
        if not self.user_config.has_section('Department'):
            self.user_config.add_section('Department')
        self.user_config.set('Department', 'Enabled', str(self.department_checkbox.isChecked()))
        self.user_config.set('Department', 'Text', self.department_textfield.text())
        self.user_config.set('Department', 'Option1', str(self.department_checkbox1.isChecked()))
        self.user_config.set('Department', 'Option2', str(self.department_checkbox2.isChecked()))

        # Save Category 3 settings
        if not self.user_config.has_section('Count'):
            self.user_config.add_section('Count')
        self.user_config.set('Count', 'Enabled', str(self.count_checkbox.isChecked()))
        self.user_config.set('Count', 'Text', self.count_textfield.text())
        self.user_config.set('Count', 'Option1', str(self.count_checkbox1.isChecked()))
        self.user_config.set('Count', 'Option2', str(self.count_checkbox2.isChecked()))
        self.user_config.set('Count', 'Option3', str(self.count_checkbox3.isChecked()))
        self.user_config.set('Count', 'Option4', str(self.count_checkbox4.isChecked()))
        self.user_config.set('Count', 'Option5', str(self.count_checkbox5.isChecked()))
        
        # Save Category 4 settings
        if not self.user_config.has_section('Library'):
            self.user_config.add_section('Library')
        self.user_config.set('Library', 'Enabled', str(self.library_checkbox.isChecked()))
        self.user_config.set('Library', 'Text', self.library_textfield.text())
        self.user_config.set('Library', 'Option1', str(self.library_checkbox1.isChecked()))
        self.user_config.set('Library', 'Option2', str(self.library_checkbox2.isChecked()))
        self.user_config.set('Library', 'Text2', self.current_library_textfield.text())
        self.user_config.set('Library', 'Option3', str(self.current_library_checkbox1.isChecked()))
        self.user_config.set('Library', 'Option4', str(self.current_library_checkbox2.isChecked()))



        # Save Category 5 settings
        if not self.user_config.has_section('Loan'):
            self.user_config.add_section('Loan')
        self.user_config.set('Loan', 'Enabled', str(self.loan_checkbox.isChecked()))
        self.user_config.set('Loan', 'Text', self.loan_textfield.text())
        self.user_config.set('Loan', 'Option1', str(self.loan_checkbox1.isChecked()))
        self.user_config.set('Loan', 'Option2', str(self.loan_checkbox2.isChecked()))
        
        if not self.user_config.has_section('Collection'):
            self.user_config.add_section('Collection')
        self.user_config.set('Collection', 'Enabled', str(self.collection_checkbox.isChecked()))
        self.user_config.set('Collection', 'Text', self.collection_textfield.text())
        self.user_config.set('Collection', 'Option1', str(self.collection_checkbox1.isChecked()))
        self.user_config.set('Collection', 'Option2', str(self.collection_checkbox2.isChecked()))
        self.user_config.set('Collection', 'Option3', str(self.collection_checkbox3.isChecked()))
        self.user_config.set('Collection', 'Option4', str(self.collection_checkbox4.isChecked()))

        # Write to file
        try:
            with open(self.user_config_file, 'w', encoding='utf-8') as user_configfile:
                self.user_config.write(user_configfile)
            #QMessageBox.information(self, "Asetukset tallennettu", "Asetusten tallennus onnistui.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Tallennus epäonnistui: {e}")


    #Functions

    def open_in_koha(self):
        """Generates a Koha URL based on the selected item's BiblioNumber and ItemNumber and opens it in a web browser."""
        print("open_in_koha called")  # Debugging statement
        selected_rows = self.table.selectionModel().selectedRows()
        print(f"Selected rows: {selected_rows}")  # Debugging statement

        if not selected_rows:
            QMessageBox.warning(self, "Ei valintaa", "Valitse avattava rivi ensin.")
            print("No rows selected.")  # Debugging statement
            return

        if len(selected_rows) > 1:
            QMessageBox.warning(self, "Useita valintoja", "Valitse vain yksi rivi avataksesi Koha linkin.")
            print("Multiple rows selected.")  # Debugging statement
            return

        row = selected_rows[0].row()
        print(f"Selected row index: {row}")  # Debugging statement

        # Retrieve header names from the config file
        item_number_header_name = self.config.get("TableSettings", "itemnumbercolumnname")
        biblio_number_header_name = self.config.get("TableSettings", "biblionumbercolumnname")

        # Find the column indices dynamically based on the header names
        item_number_column = next(
            (col for col in range(self.table.columnCount()) if self.table.horizontalHeaderItem(col).text() == item_number_header_name), 
            None
        )
        biblio_number_column = next(
            (col for col in range(self.table.columnCount()) if self.table.horizontalHeaderItem(col).text() == biblio_number_header_name), 
            None
        )

        # Ensure the columns were found before proceeding
        if item_number_column is None or biblio_number_column is None:
            raise ValueError("One or more required header names not found in the table headers.")

        # Get the values from the dynamically determined columns
        item_number_item = self.table.item(row, item_number_column)  # Item Number column
        biblio_number_item = self.table.item(row, biblio_number_column)  # Biblio Number column

        if not biblio_number_item or not item_number_item:
            QMessageBox.warning(self, "Puuttuva tieto", "Valitulla rivillä puuttuu Biblio Number tai Item Number.")
            print("Missing Biblio Number or Item Number.")  # Debugging statement
            return

        biblio_number = biblio_number_item.text()
        item_number = item_number_item.text()
        print(f"Biblio Number: {biblio_number}, Item Number: {item_number}")  # Debugging statement

        # Fetch the base_link from the configuration file under the section 'KohaUrl'
        base_link = self.config.get("KohaUrl", "baseurl") 
        bibliopart = self.config.get("KohaUrl", "bibliopart")
        itemnumberpart = self.config.get("KohaUrl", "itemnumberpart")
        koha_url = f"{base_link}{bibliopart}{biblio_number}{itemnumberpart}{item_number}"
        print(f"Generated Koha URL: {koha_url}")  # Debugging statement


        # Open the URL in the default web browser
        try:
            success = webbrowser.open(koha_url)
            print(f"webbrowser.open returned: {success}")  # Debugging statement
            if not success:
                QMessageBox.critical(self, "Error", "Failed to open the web browser.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An exception occurred: {e}")
            print(f"Exception occurred: {e}")  # Debugging statement

    def copy_barcodes(self):
        """Copies all barcodes from the selected items to the clipboard."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Ei valintaa", "Valitse kopioitavat rivit ensin.")
            return

        # Find the barcode column index dynamically
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        barcode_column_index = headers.index(self.barcode_column_name)

        barcodes = []
        for selected_row in selected_rows:
            row = selected_row.row()
            barcode_item = self.table.item(row, barcode_column_index)  # Use dynamic column index
            if barcode_item:
                barcode = barcode_item.text()
                if barcode and barcode != "N/A":
                    barcodes.append(barcode)

        if not barcodes:
            QMessageBox.information(self, "Ei viivakoodeja", "Valituilla riveillä ei ole viivakoodeja.")
            return

        # Join barcodes with newline or any delimiter you prefer
        barcodes_text = "\n".join(barcodes)

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(barcodes_text)

        QMessageBox.information(self, "Viivakoodit kopioitu", "Valitut viivakoodit on kopioitu leikepöydälle.")
        
        
        
    def playSound(self, sound_id: int):
        """Plays a sound based on the given sound_id.
        
        - sound_id 1: Warning sound
        - sound_id 2: Notification sound
        - Other values: No sound played
        
        Assumes sound files 'warning.wav' and 'notification.wav' are in the current directory.
        """
        if not hasattr(self, '_sound_last_play'):
            self._sound_last_play = {}
        
        cooldowns = {1: 1, 2: 1}  # in seconds, 1s for 1, 1s for 2
        
        if sound_id not in [1, 2]:
            return  # No sound for unknown id
        
        current_time = time.time()
        last_time = self._sound_last_play.get(sound_id, 0)
        limit = cooldowns[sound_id]
        
        if current_time - last_time < limit:
            return  # Cooldown not expired
        
        sound = QSoundEffect(self)
        if sound_id == 1 and self.warning_sound_checkbox.isChecked() == True :
            sound.setSource(QUrl.fromLocalFile("resources/beep.wav"))
        elif sound_id == 2 and self.notification_sound_checkbox.isChecked() == True and self.collectAll == False:
            sound.setSource(QUrl.fromLocalFile("resources/beep2.wav"))
        
        sound.play()
        self._sound_last_play[sound_id] = current_time


        
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()



    window.show()
    sys.exit(app.exec())
