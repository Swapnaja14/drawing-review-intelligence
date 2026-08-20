"""
app/controllers/app_controller.py
Compatibility redirect re-exporting AppController from src.controllers.app_controller.
"""
from src.controllers.app_controller import AppController, PDFLoadWorker, PDFRenderWorker, WorkflowWorker

__all__ = ["AppController", "PDFLoadWorker", "PDFRenderWorker", "WorkflowWorker"]
