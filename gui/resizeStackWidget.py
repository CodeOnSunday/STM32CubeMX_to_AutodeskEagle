from PySide2.QtWidgets import QStackedWidget

class ResizeStackWidget(QStackedWidget):
    def __init__(self, *argc, **argv):
        super().__init__(*argc, **argv)

    def minimumSizeHint(self):
        return self.currentWidget().minimumSizeHint()

    def sizeHint(self):
        return self.currentWidget().sizeHint()