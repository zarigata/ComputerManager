"""
Audit log viewer dialog for Computer Manager.

Provides a GUI for viewing, filtering, and exporting audit logs.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QDateEdit, QFileDialog,
    QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor


class AuditLogViewer(QDialog):
    """
    Dialog for viewing and managing audit logs.
    
    Displays audit entries in a table with filtering, sorting,
    and export capabilities.
    """
    
    def __init__(self, audit_logger, parent=None):
        """
        Initialize audit log viewer.
        
        Args:
            audit_logger: AuditLogger instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.audit_logger = audit_logger
        self.all_logs: List[Dict] = []
        self.filtered_logs: List[Dict] = []
        
        self._setup_ui()
        self._load_logs()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Audit Log Viewer")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        
        # Date range filter
        filter_layout.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.start_date.dateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.start_date)
        
        filter_layout.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.end_date)
        
        # Tool name filter
        filter_layout.addWidget(QLabel("Tool:"))
        self.tool_filter = QLineEdit()
        self.tool_filter.setPlaceholderText("Filter by tool name...")
        self.tool_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.tool_filter)
        
        # Status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Success", "Failed", "Denied"])
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.status_filter)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_logs)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Event Type", "Tool", "Status", "User Confirmed", "Details"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.table)
        
        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        export_json_btn = QPushButton("Export JSON")
        export_json_btn.clicked.connect(lambda: self._export_logs('json'))
        button_layout.addWidget(export_json_btn)
        
        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(lambda: self._export_logs('csv'))
        button_layout.addWidget(export_csv_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _load_logs(self):
        """Load logs from audit logger."""
        self.all_logs = self.audit_logger.get_recent_logs(limit=1000)
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply filters to logs and update table."""
        # Get filter values
        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()
        tool_text = self.tool_filter.text().lower()
        status = self.status_filter.currentText()
        
        # Filter logs
        self.filtered_logs = []
        for log in self.all_logs:
            # Parse timestamp
            try:
                log_date = datetime.fromisoformat(log['timestamp']).date()
            except (KeyError, ValueError):
                continue
            
            # Date filter
            if log_date < start or log_date > end:
                continue
            
            # Tool filter
            if tool_text and tool_text not in log.get('tool_name', '').lower():
                continue
            
            # Status filter
            if status != "All":
                event_type = log.get('event_type', '')
                if status == "Success" and not (event_type == 'tool_execution' and log.get('success', False)):
                    continue
                if status == "Failed" and not (event_type == 'tool_execution' and not log.get('success', True)):
                    continue
                if status == "Denied" and event_type != 'permission_denied':
                    continue
            
            self.filtered_logs.append(log)
        
        self._update_table()
    
    def _update_table(self):
        """Update table with filtered logs."""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.filtered_logs))
        
        for row, log in enumerate(self.filtered_logs):
            # Timestamp
            timestamp = log.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
            self.table.setItem(row, 0, QTableWidgetItem(timestamp))
            
            # Event type
            event_type = log.get('event_type', '')
            self.table.setItem(row, 1, QTableWidgetItem(event_type))
            
            # Tool name
            tool_name = log.get('tool_name', '')
            self.table.setItem(row, 2, QTableWidgetItem(tool_name))
            
            # Status
            status_item = QTableWidgetItem()
            if event_type == 'tool_execution':
                if log.get('success', False):
                    status_item.setText("Success")
                    status_item.setForeground(QColor(0, 150, 0))
                else:
                    status_item.setText("Failed")
                    status_item.setForeground(QColor(200, 0, 0))
            elif event_type == 'permission_denied':
                status_item.setText("Denied")
                status_item.setForeground(QColor(200, 0, 0))
            elif event_type == 'elevation_request':
                if log.get('success', False):
                    status_item.setText("Elevated")
                    status_item.setForeground(QColor(200, 100, 0))
                else:
                    status_item.setText("Denied")
                    status_item.setForeground(QColor(200, 0, 0))
            else:
                status_item.setText("-")
            self.table.setItem(row, 3, status_item)
            
            # User confirmed
            confirmed = log.get('user_confirmed', False)
            confirmed_item = QTableWidgetItem("Yes" if confirmed else "No")
            self.table.setItem(row, 4, confirmed_item)
            
            # Details
            details = self._format_details(log)
            self.table.setItem(row, 5, QTableWidgetItem(details))
        
        self.table.setSortingEnabled(True)
        
        # Update status label
        total = len(self.all_logs)
        filtered = len(self.filtered_logs)
        self.status_label.setText(f"Showing {filtered} of {total} entries")
    
    def _format_details(self, log: Dict) -> str:
        """Format log details for display."""
        event_type = log.get('event_type', '')
        
        if event_type == 'tool_execution':
            if log.get('success', False):
                return f"Executed in {log.get('execution_time', 0):.2f}s"
            else:
                return log.get('error', 'Unknown error')
        elif event_type == 'permission_denied':
            return f"Required: {log.get('required_level', '?')}, Current: {log.get('current_level', '?')}"
        elif event_type == 'elevation_request':
            return log.get('reason', '')
        elif event_type == 'user_confirmation':
            confirmed = "Confirmed" if log.get('confirmed', False) else "Denied"
            cached = " (cached)" if log.get('cached', False) else ""
            return f"{confirmed}{cached}"
        
        return ""
    
    def _export_logs(self, format: str):
        """Export filtered logs to file."""
        if not self.filtered_logs:
            QMessageBox.information(self, "No Data", "No logs to export.")
            return
        
        # Get file path
        ext = 'json' if format == 'json' else 'csv'
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Audit Logs",
            f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}",
            f"{ext.upper()} Files (*.{ext})"
        )
        
        if not file_path:
            return
        
        try:
            # Get date range
            start = datetime.combine(self.start_date.date().toPyDate(), datetime.min.time())
            end = datetime.combine(self.end_date.date().toPyDate(), datetime.max.time())
            
            # Export logs
            content = self.audit_logger.export_logs(start, end, format)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Logs exported to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export logs:\n{str(e)}"
            )
