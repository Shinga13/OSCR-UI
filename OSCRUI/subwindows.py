import os
from traceback import format_exception

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QIntValidator, QMouseEvent, QTextOption
from PySide6.QtWidgets import (
        QAbstractItemView, QDialog, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QSpacerItem,
        QSplitter, QTableView, QTextEdit, QVBoxLayout)

from OSCR import LiveParser, LIVE_TABLE_HEADER

from .callbacks import (
        auto_split_callback, combat_split_callback, copy_live_data_callback, repair_logfile,
        trim_logfile)
from .displayer import create_live_graph, update_live_display, update_live_graph, update_live_table
from .datamodels import LiveParserTableModel
from .iofunctions import open_link
from .style import get_style, get_style_class, theme_font
from .textedit import format_path
from .translation import tr
from .widgetbuilder import create_button, create_frame, create_icon_button, create_label
from .widgetbuilder import ABOTTOM, AHCENTER, ALEFT, ARIGHT, ATOP, AVCENTER, RFIXED
from .widgetbuilder import SEXPAND, SMAX, SMAXMAX, SMINMAX, SMINMIN
from .widgets import FlipButton, LiveParserWindow, SizeGrip


def show_message(self, title: str, message: str, icon: str = 'info'):
    """
    Displays a message in a dialog

    Parameters:
    - :param title: title of the warning
    - :param message: message to be displayed
    - :param icon: "warning" or "info"
    """
    dialog = QDialog(self.window)
    thick = self.theme['app']['frame_thickness']
    item_spacing = self.theme['defaults']['isp']
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(thick, thick, thick, thick)
    dialog_frame = create_frame(self, size_policy=SMINMIN)
    main_layout.addWidget(dialog_frame)
    dialog_layout = QVBoxLayout()
    dialog_layout.setContentsMargins(thick, thick, thick, thick)
    dialog_layout.setSpacing(thick)
    content_frame = create_frame(self, size_policy=SMINMIN)
    content_layout = QVBoxLayout()
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(item_spacing)
    content_layout.setAlignment(ATOP)

    top_layout = QHBoxLayout()
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.setSpacing(2 * thick)
    icon_label = create_label(self, '')
    icon_size = self.theme['s.c']['big_icon_size'] * self.config['ui_scale']
    icon_label.setPixmap(self.icons[icon].pixmap(icon_size))
    top_layout.addWidget(icon_label, alignment=ALEFT | AVCENTER)
    message_label = create_label(self, message)
    message_label.setWordWrap(True)
    message_label.setSizePolicy(SMINMAX)
    top_layout.addWidget(message_label, stretch=1)
    content_layout.addLayout(top_layout)

    content_frame.setLayout(content_layout)
    dialog_layout.addWidget(content_frame, stretch=1)

    seperator = create_frame(self, style='light_frame', size_policy=SMINMAX)
    seperator.setFixedHeight(1)
    dialog_layout.addWidget(seperator)
    ok_button = create_button(self, tr('OK'))
    ok_button.clicked.connect(lambda: dialog.done(0))
    dialog_layout.addWidget(ok_button, alignment=AHCENTER)
    dialog_frame.setLayout(dialog_layout)

    dialog = QDialog(self.window)
    dialog.setLayout(main_layout)
    dialog.setWindowTitle('OSCR - ' + title)
    dialog.setStyleSheet(get_style(self, 'dialog_window'))
    dialog.setSizePolicy(SMAXMAX)
    dialog.exec()


def log_size_warning(self):
    """
    Warns user about oversized logfile.
    Note: The default button counts as a two buttons

    :return: "cancel", "split dialog", "continue"
    """
    dialog = QMessageBox()
    dialog.setIcon(QMessageBox.Icon.Warning)
    message = 'No Message'
    dialog.setText(message)
    dialog.setWindowTitle('Open Source Combalog Reader')
    dialog.setWindowIcon(self.icons['oscr'])

    dialog.addButton(tr('Continue'), QMessageBox.ButtonRole.AcceptRole)
    default_button = dialog.addButton(tr('Split Dialog'), QMessageBox.ButtonRole.ActionRole)
    dialog.addButton(tr('Trim'), QMessageBox.ButtonRole.ActionRole)
    dialog.addButton(tr('Cancel'), QMessageBox.ButtonRole.RejectRole)

    dialog.setDefaultButton(default_button)
    clicked = dialog.exec()

    if clicked == 1:
        return 'split dialog'
    elif clicked == 2:
        return 'continue'
    elif clicked == 3:
        return 'split dialog'
    elif clicked == 4:
        return 'trim'

    return 'cancel'


def split_dialog(self):
    """
    Opens dialog to split the current logfile.
    """
    main_layout = QVBoxLayout()
    thick = self.theme['app']['frame_thickness']
    item_spacing = self.theme['defaults']['isp']
    main_layout.setContentsMargins(thick, thick, thick, thick)
    content_frame = create_frame(self)
    main_layout.addWidget(content_frame)
    current_logpath = self.entry.text()
    vertical_layout = QVBoxLayout()
    vertical_layout.setContentsMargins(thick, thick, thick, thick)
    vertical_layout.setSpacing(item_spacing)
    log_layout = QHBoxLayout()
    log_layout.setContentsMargins(0, 0, 0, 0)
    log_layout.setSpacing(item_spacing)
    current_log_heading = create_label(self, tr('Selected Logfile:'), 'label_subhead')
    log_layout.addWidget(current_log_heading, alignment=ALEFT)
    current_log_label = create_label(self, format_path(current_logpath), 'label')
    log_layout.addWidget(current_log_label, alignment=AVCENTER)
    log_layout.addSpacerItem(QSpacerItem(1, 1, hData=SEXPAND, vData=SMAX))
    vertical_layout.addLayout(log_layout)
    seperator_1 = create_frame(self, content_frame, 'hr', size_policy=SMINMIN)
    seperator_1.setFixedHeight(self.theme['hr']['height'])
    vertical_layout.addWidget(seperator_1)
    grid_layout = QGridLayout()
    grid_layout.setContentsMargins(0, 0, 0, 0)
    grid_layout.setVerticalSpacing(0)
    grid_layout.setHorizontalSpacing(item_spacing)
    vertical_layout.addLayout(grid_layout)

    trim_heading = create_label(self, tr('Trim Logfile:'), 'label_heading')
    grid_layout.addWidget(trim_heading, 0, 0, alignment=ALEFT)
    label_text = (
            tr('Removes all combats but the most recent one from the selected logfile. ')
            + tr('All previous combats will be lost!'))
    trim_text = create_label(self, label_text, 'label')
    trim_text.setWordWrap(True)
    trim_text.setFixedWidth(self.sidebar_item_width)
    grid_layout.addWidget(trim_text, 1, 0, alignment=ALEFT)
    trim_button = create_button(self, tr('Trim'))
    trim_button.clicked.connect(lambda: trim_logfile(self))
    grid_layout.addWidget(trim_button, 1, 2, alignment=ARIGHT | ABOTTOM)
    grid_layout.setRowMinimumHeight(2, item_spacing)
    seperator_3 = create_frame(self, content_frame, 'hr', size_policy=SMINMIN)
    seperator_3.setFixedHeight(self.theme['hr']['height'])
    grid_layout.addWidget(seperator_3, 3, 0, 1, 3)
    grid_layout.setRowMinimumHeight(4, item_spacing)

    auto_split_heading = create_label(self, tr('Split Log Automatically:'), 'label_heading')
    grid_layout.addWidget(auto_split_heading, 5, 0, alignment=ALEFT)
    label_text = (
            tr('Automatically splits the logfile at the next combat end after ')
            + f'{self.settings.value("split_log_after", type=int):,}'
            + tr(' lines until the entire file has ')
            + tr(' been split. The new files are written to the selected folder. It is advised to ')
            + tr('select an empty folder to ensure all files are saved correctly.'))
    auto_split_text = create_label(self, label_text, 'label')
    auto_split_text.setWordWrap(True)
    auto_split_text.setFixedWidth(self.sidebar_item_width)
    grid_layout.addWidget(auto_split_text, 6, 0, alignment=ALEFT)
    auto_split_button = create_button(self, tr('Auto Split'))
    auto_split_button.clicked.connect(lambda: auto_split_callback(self, current_logpath))
    grid_layout.addWidget(auto_split_button, 6, 2, alignment=ARIGHT | ABOTTOM)
    grid_layout.setRowMinimumHeight(7, item_spacing)
    seperator_8 = create_frame(self, content_frame, 'hr', size_policy=SMINMIN)
    seperator_8.setFixedHeight(self.theme['hr']['height'])
    grid_layout.addWidget(seperator_8, 8, 0, 1, 3)
    grid_layout.setRowMinimumHeight(9, item_spacing)
    range_split_heading = create_label(self, tr('Export Range of Combats:'), 'label_heading')
    grid_layout.addWidget(range_split_heading, 10, 0, alignment=ALEFT)
    label_text = 'Soon to be removed'
    range_split_text = create_label(self, label_text, 'label')
    range_split_text.setWordWrap(True)
    range_split_text.setFixedWidth(self.sidebar_item_width)
    grid_layout.addWidget(range_split_text, 11, 0, alignment=ALEFT)
    range_limit_layout = QGridLayout()
    range_limit_layout.setContentsMargins(0, 0, 0, 0)
    range_limit_layout.setSpacing(0)
    range_limit_layout.setRowStretch(0, 1)
    lower_range_label = create_label(self, tr('Lower Limit:'), 'label')
    range_limit_layout.addWidget(lower_range_label, 1, 0, alignment=AVCENTER)
    upper_range_label = create_label(self, tr('Upper Limit:'), 'label')
    range_limit_layout.addWidget(upper_range_label, 2, 0, alignment=AVCENTER)
    lower_range_entry = QLineEdit()
    lower_validator = QIntValidator()
    lower_validator.setBottom(1)
    lower_range_entry.setValidator(lower_validator)
    lower_range_entry.setText('1')
    lower_range_entry.setStyleSheet(
            get_style(self, 'entry', {'margin-top': 0, 'margin-left': '@csp'}))
    lower_range_entry.setFixedWidth(self.sidebar_item_width // 7)
    range_limit_layout.addWidget(lower_range_entry, 1, 1, alignment=AVCENTER)
    upper_range_entry = QLineEdit()
    upper_validator = QIntValidator()
    upper_validator.setBottom(-1)
    upper_range_entry.setValidator(upper_validator)
    upper_range_entry.setText('1')
    upper_range_entry.setStyleSheet(
            get_style(self, 'entry', {'margin-top': 0, 'margin-left': '@csp'}))
    upper_range_entry.setFixedWidth(self.sidebar_item_width // 7)
    range_limit_layout.addWidget(upper_range_entry, 2, 1, alignment=AVCENTER)
    grid_layout.addLayout(range_limit_layout, 11, 1)
    range_split_button = create_button(self, tr('Export Combats'))
    range_split_button.clicked.connect(
            lambda le=lower_range_entry, ue=upper_range_entry:
            combat_split_callback(self, current_logpath, le.text(), ue.text()))
    grid_layout.addWidget(range_split_button, 11, 2, alignment=ARIGHT | ABOTTOM)
    grid_layout.setRowMinimumHeight(12, item_spacing)
    seperator_13 = create_frame(self, content_frame, 'hr', size_policy=SMINMIN)
    seperator_13.setFixedHeight(self.theme['hr']['height'])
    grid_layout.addWidget(seperator_13, 13, 0, 1, 3)
    grid_layout.setRowMinimumHeight(14, item_spacing)
    repair_log_heading = create_label(self, 'Repair Logfile', 'label_heading')
    grid_layout.addWidget(repair_log_heading, 15, 0, alignment=ALEFT)
    repair_log_button = create_button(self, 'Repair')
    repair_log_button.clicked.connect(lambda: repair_logfile(self))
    grid_layout.addWidget(repair_log_button, 16, 2, alignment=ARIGHT | ABOTTOM)

    content_frame.setLayout(vertical_layout)

    dialog = QDialog(self.window)
    dialog.setLayout(main_layout)
    dialog.setWindowTitle(tr('OSCR - Split Logfile'))
    dialog.setStyleSheet(get_style(self, 'dialog_window'))
    dialog.setSizePolicy(SMAXMAX)
    dialog.exec()


def uploadresult_dialog(self, result):
    """
    Shows a dialog that informs about the result of the triggered upload.

    Paramters:
    - :param result: dict containing result
    """
    dialog = QDialog(self.window)
    main_layout = QVBoxLayout()
    thick = self.theme['app']['frame_thickness']
    main_layout.setContentsMargins(thick, thick, thick, thick)
    content_frame = create_frame(self)
    main_layout.addWidget(content_frame)
    content_layout = QGridLayout()
    content_layout.setContentsMargins(thick, thick, thick, thick)
    content_layout.setSpacing(0)
    margin = {'margin-bottom': self.theme['defaults']['isp']}
    title_label = create_label(self, f"{result.detail}", 'label_heading', style_override=margin)
    content_layout.addWidget(title_label, 0, 0, 1, 4, alignment=ALEFT)
    view_button = create_button(self, 'View Online', style_override=margin)
    view_button.clicked.connect(lambda: view_upload_result(self, result.combatlog))
    if result.results:
        content_layout.addWidget(view_button, 0, 0, 1, 4, alignment=ARIGHT)
    icon_size = QSize(self.config['icon_size'] / 1.5, self.config['icon_size'] / 1.5)
    row = 0
    if result.results:
        for row, line in enumerate(result.results, 1):
            if row % 2 == 1:
                table_style = {'background-color': '@mbg', 'padding': (5, 3, 3, 3), 'margin': 0}
                icon_table_style = {'background-color': '@mbg', 'padding': 3, 'margin': 0}
            else:
                table_style = {'background-color': '@bg', 'padding': (5, 3, 3, 3), 'margin': 0}
                icon_table_style = {'background-color': '@bg', 'padding': 3, 'margin': 0}
            if line.updated:
                icon = self.icons['check'].pixmap(icon_size)
            else:
                icon = self.icons['dash'].pixmap(icon_size)
            status_label = create_label(self, '', style_override=icon_table_style)
            status_label.setPixmap(icon)
            status_label.setSizePolicy(SMINMIN)
            content_layout.addWidget(status_label, row, 0)
            name_label = create_label(self, line.name, style_override=table_style)
            name_label.setSizePolicy(SMINMAX)
            content_layout.addWidget(name_label, row, 1)
            value_label = create_label(self, str(line.value), style_override=table_style)
            value_label.setSizePolicy(SMINMAX)
            value_label.setAlignment(ARIGHT)
            content_layout.addWidget(value_label, row, 2)
            detail_label = create_label(self, line.detail, style_override=table_style)
            detail_label.setSizePolicy(SMINMAX)
            content_layout.addWidget(detail_label, row, 3)
    top_margin = {'margin-top': self.theme['defaults']['isp']}
    close_button = create_button(self, 'Close', style_override=top_margin)
    close_button.clicked.connect(dialog.close)
    content_layout.addWidget(close_button, row + 1, 0, 1, 4, alignment=AHCENTER)
    content_frame.setLayout(content_layout)

    dialog.setLayout(main_layout)
    dialog.setWindowTitle(tr('OSCR - Upload Results'))
    dialog.setStyleSheet(get_style(self, 'dialog_window'))
    dialog.setSizePolicy(SMAXMAX)
    dialog.setFixedSize(dialog.sizeHint())
    dialog.exec()


def live_parser_toggle(self, activate):
    """
    Activates / Deactivates LiveParser.

    Parameters:
    - :param activate: True when parser should be shown; False when open parser should be closed.
    """
    if activate:
        log_path = self.settings.value('sto_log_path')
        if not log_path or not os.path.isfile(log_path):
            show_message(self, tr('Invalid Logfile'), tr(
                    'Make sure to set the STO Logfile setting in the settings tab to a valid '
                    'logfile before starting the live parser.'), 'warning')
            self.widgets.live_parser_button.setChecked(False)
            return
        FIELD_INDEX_CONVERSION = {0: 0, 1: 2, 2: 3, 3: 4}
        graph_active = self.settings.value('live_graph_active', type=bool)
        data_buffer = []
        data_field = FIELD_INDEX_CONVERSION[self.settings.value('live_graph_field', type=int)]
        self.live_parser = LiveParser(log_path, update_callback=lambda p, t: update_live_display(
                self, p, t, graph_active, data_buffer, data_field),
                settings=self.live_parser_settings)
        create_live_parser_window(self)
    else:
        try:
            self.live_parser_window.close()
        except AttributeError:
            pass
        try:
            self.live_parser.stop()
        except AttributeError:
            pass
        self.live_parser_window.update_table.disconnect()
        self.live_parser_window.update_graph.disconnect()
        self.live_parser_window.deleteLater()
        self.live_parser_window = None
        self.live_parser = None
        self.widgets.live_parser_table = None
        self.widgets.live_parser_splitter = None
        self.widgets.live_parser_button.setChecked(False)


def create_live_parser_window(self):
    """
    Creates the LiveParser window.
    """
    ui_scale = self.config['ui_scale']
    self.config['ui_scale'] = self.config['live_scale']

    live_window = LiveParserWindow()
    live_window.setStyleSheet(get_style(self, 'live_parser'))
    live_window.setWindowTitle("Live Parser")
    live_window.setWindowIcon(self.icons['oscr'])
    live_window.setWindowFlags(
            live_window.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.FramelessWindowHint)
    # live_window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    live_window.setWindowOpacity(self.settings.value('live_parser_opacity', type=float))
    if self.settings.value('live_geometry'):
        live_window.restoreGeometry(self.settings.value('live_geometry'))
    live_window.closeEvent = lambda close_event: live_parser_close_callback(self, close_event)
    live_window.mousePressEvent = lambda press_event: live_parser_press_event(self, press_event)
    live_window.mouseMoveEvent = lambda move_event: live_parser_move_event(self, move_event)
    live_window.setSizePolicy(SMAXMAX)
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    graph_colors = None
    graph_column = None
    graph_active = self.settings.value('live_graph_active', type=bool)
    if graph_active:
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet(get_style_class(
                self, 'QSplitter', 'splitter', {'border': 'none', 'margin': 0}))
        splitter.setChildrenCollapsible(False)
        self.widgets.live_parser_splitter = splitter
        graph_frame, curves = create_live_graph(self)
        graph_frame.setMinimumHeight(self.sidebar_item_width * 0.1)
        splitter.addWidget(graph_frame)
        self.widgets.live_parser_curves = curves
        FIELD_INDEX_CONVERSION = {0: 0, 1: 2, 2: 3, 3: 4}
        graph_column = FIELD_INDEX_CONVERSION[self.settings.value('live_graph_field', type=int)]
        graph_colors = self.theme['plot']['color_cycler'][:5]
        layout.addWidget(splitter, stretch=1)

    table = QTableView()
    table.setAlternatingRowColors(self.theme['s.c']['table_alternate'])
    table.setShowGrid(self.theme['s.c']['table_gridline'])
    table.setStyleSheet(get_style_class(self, 'QTableView', 'live_table'))
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.horizontalHeader().setStyleSheet(
            get_style_class(self, 'QHeaderView', 'live_table_header'))
    table.verticalHeader().setStyleSheet(get_style_class(self, 'QHeaderView', 'live_table_index'))
    table.verticalHeader().setMinimumHeight(1)
    table.verticalHeader().setDefaultSectionSize(table.verticalHeader().fontMetrics().height() + 2)
    table.horizontalHeader().setMinimumWidth(1)
    table.horizontalHeader().setDefaultSectionSize(1)
    table.horizontalHeader().setSectionResizeMode(RFIXED)
    table.verticalHeader().setSectionResizeMode(RFIXED)
    table.setSizePolicy(SMINMIN)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setMinimumWidth(self.sidebar_item_width * 0.1)
    table.setMinimumHeight(self.sidebar_item_width * 0.1)
    table.setSortingEnabled(True)
    if self.settings.value('live_player', defaultValue='Handle') == 'Handle':
        name_index = 1
    else:
        name_index = 0
    model = LiveParserTableModel(
            [[0] * len(LIVE_TABLE_HEADER)], tr(LIVE_TABLE_HEADER), [('Name', '@handle')],
            theme_font(self, 'live_table_header'), theme_font(self, 'live_table'),
            legend_col=graph_column, colors=graph_colors, name_index=name_index)
    table.setModel(model)
    table.resizeColumnsToContents()
    table.resizeRowsToContents()
    for index in range(len(LIVE_TABLE_HEADER)):
        if not self.settings.value(f'live_columns|{index}', type=bool):
            table.hideColumn(index)
    self.widgets.live_parser_table = table
    if graph_active:
        splitter.addWidget(table)
        if self.settings.value('live_splitter'):
            splitter.restoreState(self.settings.value('live_splitter'))
    else:
        layout.addWidget(table, 1)

    margin = self.config['ui_scale'] * 6
    bottom_layout = QGridLayout()
    bottom_layout.setContentsMargins(margin, 0, 0, 0)
    bottom_layout.setSpacing(margin)
    bottom_layout.setColumnStretch(4, 1)

    activate_button = FlipButton(tr('Activate'), tr('Deactivate'), live_window, checkable=True)
    activate_button.setStyleSheet(self.get_style_class(
            'QPushButton', 'toggle_button', {'margin': 0}))
    activate_button.setFont(self.theme_font('app', '@subhead'))
    activate_button.r_function = lambda: self.live_parser.start()
    activate_button.l_function = lambda: self.live_parser.stop()
    bottom_layout.addWidget(activate_button, 0, 0, alignment=ALEFT | AVCENTER)
    icon_size = [self.theme['s.c']['button_icon_size'] * self.config['live_scale'] * 0.8] * 2
    copy_button = create_icon_button(
            self, self.icons['copy'], tr('Copy Result'), style_override={'margin': 0},
            icon_size=icon_size)
    copy_button.clicked.connect(lambda: copy_live_data_callback(self))
    bottom_layout.addWidget(copy_button, 0, 1, alignment=ALEFT | AVCENTER)
    close_button = create_icon_button(
            self, self.icons['close'], tr('Close Live Parser'), style_override={'margin': 0},
            icon_size=icon_size)
    close_button.clicked.connect(lambda: live_parser_toggle(self, False))
    bottom_layout.addWidget(close_button, 0, 2, alignment=ALEFT | AVCENTER)
    time_label = create_label(self, 'Duration: 0s')
    bottom_layout.addWidget(time_label, 0, 3, alignment=ALEFT | AVCENTER)
    self.widgets.live_parser_duration_label = time_label

    grip = SizeGrip(live_window)
    grip.setStyleSheet(get_style(self, 'resize_handle'))
    bottom_layout.addWidget(grip, 0, 4, alignment=ARIGHT | ABOTTOM)

    layout.addLayout(bottom_layout)
    live_window.setLayout(layout)
    live_window.update_table.connect(lambda data: update_live_table(self, data))
    live_window.update_graph.connect(update_live_graph)
    self.live_parser_window = live_window
    self.config['ui_scale'] = ui_scale
    live_window.show()

    if self.settings.value('live_enabled', type=bool):
        activate_button.flip()


def live_parser_close_callback(self, event):
    """
    Executed when application is closed.
    """
    window_geometry = self.live_parser_window.saveGeometry()
    self.settings.setValue('live_geometry', window_geometry)
    try:
        self.settings.setValue('live_splitter', self.widgets.live_parser_splitter.saveState())
    except AttributeError:
        pass
    event.accept()


def live_parser_press_event(self, event: QMouseEvent):
    self.live_parser_window.start_pos = event.globalPosition().toPoint()
    event.accept()


def live_parser_move_event(self, event: QMouseEvent):
    parser_window = self.live_parser_window
    pos_delta = QPoint(event.globalPosition().toPoint() - parser_window.start_pos)
    parser_window.move(parser_window.x() + pos_delta.x(), parser_window.y() + pos_delta.y())
    parser_window.start_pos = event.globalPosition().toPoint()
    event.accept()


def view_upload_result(self, log_id: str):
    """
    Opens webbrowser to show the uploaded combatlog on the DPS League tables.
    """
    open_link(f"https://oscr.stobuilds.com/ui/combatlog/{log_id}/")


def show_detection_info(self, combat_index: int):
    """
    Shows a subwindow containing information on the detection process
    """
    if combat_index < 0:
        return
    dialog = QDialog(self.window)
    thick = self.theme['app']['frame_thickness']
    item_spacing = self.theme['defaults']['isp']
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(thick, thick, thick, thick)
    content_frame = create_frame(self)
    main_layout.addWidget(content_frame)
    content_layout = QVBoxLayout()
    content_layout.setContentsMargins(thick, thick, thick, thick)
    content_layout.setSpacing(item_spacing)

    for detection_info in self.parser.combats[combat_index].meta['detection_info']:
        if detection_info.success:
            if detection_info.step == 'existence':
                detection_method = tr('by checking whether the following entities exist in the log')
            elif detection_info.step == 'deaths':
                detection_method = tr('by checking the death counts of following entities')
            else:
                detection_method = tr('by checking the hull values of following entities')
            if detection_info.type == 'both':
                detected_type = tr('Map and Difficulty were')
            elif detection_info.type == 'difficulty':
                detected_type = f"{tr('Difficulty')} ({detection_info.difficulty}) {tr('was')}"
            else:
                detected_type = f"{tr('Map')} ({detection_info.map}) {tr('was')}"
            t = f"{tr('The')} {detected_type} {tr('successfully detected')} {detection_method}"
            t += ': ' + ', '.join(detection_info.identificators) + '.'
        else:
            if detection_info.type == 'both':
                detected_type = tr('Map and Difficulty')
            elif detection_info.type == 'difficulty':
                detected_type = f"{tr('Difficulty')} ({detection_info.difficulty})"
            else:
                detected_type = f"{tr('Map')} ({detection_info.map}) {tr('was')}"
            t = f"{tr('The')} {tr(detected_type)} {tr('could not be detected, because')} "
            if detection_info.step == 'existence':
                t += tr('no entity identifying a map was found in the log.')
            elif detection_info.step == 'deaths':
                t += f'{tr("the entity")} "{detection_info.identificators[0]}" {tr("was killed")} '
                t += f"{detection_info.retrieved_value} {tr('times instead of the expected')} "
                t += f"{detection_info.target_value} {tr('times')}."
            else:
                t += f'{tr("the entities")} "{detection_info.identificators[0]}" '
                t += f"{tr('average hull capacity of')} {detection_info.retrieved_value:.0f} "
                t += f"{tr('was higher than the allowed')} {detection_info.target_value:.0f}."
        info_label = create_label(self, t)
        info_label.setSizePolicy(SMINMAX)
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

    seperator = create_frame(self, style='light_frame', size_policy=SMINMAX)
    seperator.setFixedHeight(1)
    content_layout.addWidget(seperator)
    ok_button = create_button(self, tr('OK'))
    ok_button.clicked.connect(lambda: dialog.done(0))
    content_layout.addWidget(ok_button, alignment=AHCENTER)
    content_frame.setLayout(content_layout)

    dialog = QDialog(self.window)
    dialog.setLayout(main_layout)
    dialog.setWindowTitle(tr('OSCR - Map Detection Details'))
    dialog.setStyleSheet(get_style(self, 'dialog_window'))
    dialog.setSizePolicy(SMAXMAX)
    dialog.exec()


def show_parser_error(self, error: BaseException):
    """
    Displays subwindow showing an error message and the given error traceback.

    - :param error: captured error with optionally additional data in the error.args attribute
    """
    default_message, *additional_messages = error.args
    error.args = (default_message,)
    error_text = ''.join(format_exception(error))
    if len(additional_messages) > 0:
        error_text += '\n\n++++++++++++++++++++++++++++++++++++++++++++++++++\n\n'
        error_text += '\n'.join(additional_messages)
    dialog = QDialog(self.window)
    thick = self.theme['app']['frame_thickness']
    item_spacing = self.theme['defaults']['isp']
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(thick, thick, thick, thick)
    dialog_frame = create_frame(self, size_policy=SMINMIN)
    main_layout.addWidget(dialog_frame)
    dialog_layout = QVBoxLayout()
    dialog_layout.setContentsMargins(thick, thick, thick, thick)
    dialog_layout.setSpacing(thick)
    content_frame = create_frame(self, size_policy=SMINMIN)
    content_layout = QVBoxLayout()
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(item_spacing)
    content_layout.setAlignment(ATOP)

    top_layout = QHBoxLayout()
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.setSpacing(2 * thick)
    icon_label = create_label(self, '')
    icon_size = self.theme['s.c']['big_icon_size'] * self.config['ui_scale']
    icon_label.setPixmap(self.icons['error'].pixmap(icon_size))
    top_layout.addWidget(icon_label, alignment=ALEFT | AVCENTER)
    msg = tr(
            'An error occurred while parsing the selected combatlog. You can try repairing the '
            'log file using the repair functionality in the "Manage Logfile" dialog. If the error '
            'persists, please report it to the #oscr-support channel in the STOBuilds Discord.')
    message_label = create_label(self, msg)
    message_label.setWordWrap(True)
    message_label.setSizePolicy(SMINMAX)
    top_layout.addWidget(message_label, stretch=1)
    content_layout.addLayout(top_layout)
    error_field = QTextEdit()
    error_field.setSizePolicy(SMINMIN)
    error_field.setText(error_text)
    error_field.setReadOnly(True)
    error_field.setWordWrapMode(QTextOption.WrapMode.NoWrap)
    error_field.setFont(theme_font(self, 'textedit'))
    error_field.setStyleSheet(get_style_class(self, 'QTextEdit', 'textedit'))
    expand_button = FlipButton(tr('Show Error'), tr('Hide Error'))
    expand_button.set_icon_r(self.icons['chevron-right'])
    expand_button.set_icon_l(self.icons['chevron-down'])
    expand_button.r_function = error_field.show
    expand_button.l_function = error_field.hide
    expand_button.setStyleSheet(get_style_class(self, 'FlipButton', 'button'))
    expand_button.setFont(theme_font(self, 'button'))
    content_layout.addWidget(expand_button, alignment=ALEFT)
    content_layout.addWidget(error_field, stretch=1)
    error_field.hide()
    content_frame.setLayout(content_layout)
    dialog_layout.addWidget(content_frame, stretch=1)

    seperator = create_frame(self, style='light_frame', size_policy=SMINMAX)
    seperator.setFixedHeight(1)
    dialog_layout.addWidget(seperator)
    ok_button = create_button(self, tr('OK'))
    ok_button.clicked.connect(lambda: dialog.done(0))
    dialog_layout.addWidget(ok_button, alignment=AHCENTER)
    dialog_frame.setLayout(dialog_layout)

    dialog = QDialog(self.window)
    dialog.setLayout(main_layout)
    dialog.setWindowTitle(tr('OSCR - Parser Error'))
    dialog.setStyleSheet(get_style(self, 'dialog_window'))
    dialog.exec()
