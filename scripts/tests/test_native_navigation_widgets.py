"""Real Qt navigation widgets, extracted without importing the application shell."""
import ast
import os
from pathlib import Path
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFrame, QGridLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from native_studio.navigation_registry import SIMPLE_MODE_ITEMS, get_all_subtabs_flat

ROOT = Path(__file__).resolve().parents[2]


def navigation_classes():
    tree = ast.parse((ROOT / 'native_studio/app.py').read_text(encoding='utf-8-sig'))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name in {'MomModeView', 'CommandPaletteDialog'}]
    namespace = {name: value for name, value in globals().items() if name.startswith('Q')}
    namespace.update(Qt=Qt, SIMPLE_MODE_ITEMS=SIMPLE_MODE_ITEMS,
                     get_all_subtabs_flat=get_all_subtabs_flat,
                     PALETTE={'panel': '#101820', 'text': '#ffffff'})
    exec(compile(ast.Module(body=classes, type_ignores=[]), 'native_navigation_widgets', 'exec'), namespace)
    return namespace


class NativeNavigationWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.widgets = navigation_classes()

    def test_simple_mode_scroll_owns_the_populated_content(self):
        view = self.widgets['MomModeView'](lambda key: None)
        self.addCleanup(view.deleteLater)
        scroll = view.findChild(QScrollArea)
        self.assertIsNotNone(scroll.widget())
        self.assertEqual(len(view.findChildren(QPushButton)), len(SIMPLE_MODE_ITEMS))

    def test_every_simple_mode_card_preserves_its_navigation_target(self):
        selected = []
        view = self.widgets['MomModeView'](selected.append)
        self.addCleanup(view.deleteLater)
        for button in view.findChildren(QPushButton):
            button.click()
        self.assertEqual(selected, [item['key'] for item in SIMPLE_MODE_ITEMS])

    def test_double_click_routes_the_selected_tool(self):
        dialog = self.widgets['CommandPaletteDialog']()
        self.addCleanup(dialog.deleteLater)
        dialog.search_edit.setText('Clinical Nutrition')
        self.assertEqual(dialog.list_widget.count(), 1)
        item = dialog.list_widget.item(0)
        dialog.list_widget.itemDoubleClicked.emit(item)
        self.assertEqual(dialog.selected_key, item.data(Qt.ItemDataRole.UserRole))
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)

    def test_empty_result_does_not_accept_or_invent_a_tool(self):
        dialog = self.widgets['CommandPaletteDialog']()
        self.addCleanup(dialog.deleteLater)
        dialog.search_edit.setText('unmatched-audit-widget-fixture-202')
        self.assertEqual(dialog.list_widget.count(), 0)
        dialog.accept()
        self.assertIsNone(dialog.selected_key)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

    def test_selected_tool_is_recorded_when_dialog_accepts(self):
        dialog = self.widgets['CommandPaletteDialog']()
        self.addCleanup(dialog.deleteLater)
        dialog.search_edit.setText('Clinical Nutrition')
        dialog.accept()
        self.assertEqual(dialog.selected_key, 'nutrition_subsystem')
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)


if __name__ == '__main__':
    unittest.main()
