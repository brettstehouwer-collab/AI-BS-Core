"""Wrapping controls and scrollable authoring pages without shrinking labels."""
from PyQt6.QtCore import QRect,QSize,Qt
from PyQt6.QtWidgets import QLayout,QScrollArea,QSizePolicy


class FlowLayout(QLayout):
    def __init__(self,parent=None,spacing=8):
        super().__init__(parent)
        self._items=[]
        self.setContentsMargins(0,0,0,0)
        self.setSpacing(spacing)

    def addItem(self,item):
        self._items.append(item)
        self.invalidate()

    def count(self):return len(self._items)
    def itemAt(self,index):return self._items[index] if 0<=index<len(self._items) else None
    def takeAt(self,index):return self._items.pop(index) if 0<=index<len(self._items) else None
    def expandingDirections(self):return Qt.Orientation(0)
    def hasHeightForWidth(self):return True
    def heightForWidth(self,width):return self._arrange(QRect(0,0,width,0),False)
    def sizeHint(self):return self.minimumSize()

    def minimumSize(self):
        result=QSize(0,0)
        for item in self._items:
            if not item.isEmpty():result=result.expandedTo(item.minimumSize())
        margins=self.contentsMargins()
        return result+QSize(margins.left()+margins.right(),margins.top()+margins.bottom())

    def setGeometry(self,rect):
        super().setGeometry(rect)
        self._arrange(rect,True)

    def _arrange(self,rect,apply):
        margins=self.contentsMargins()
        left=rect.x()+margins.left();top=rect.y()+margins.top()
        right=rect.right()-margins.right()+1
        x,y,row_height=left,top,0
        spacing=max(0,self.spacing())
        for item in self._items:
            if item.isEmpty():continue
            size=item.sizeHint().expandedTo(item.minimumSize())
            if x>left and x+size.width()>right:
                x=left;y+=row_height+spacing;row_height=0
            if apply:item.setGeometry(QRect(x,y,size.width(),size.height()))
            x+=size.width()+spacing;row_height=max(row_height,size.height())
        return y+row_height+margins.bottom()-rect.y()


def workspace_scroll(widget,parent=None):
    scroll=QScrollArea(parent)
    scroll.setObjectName('AuthoringWorkspaceScroll')
    scroll.setAccessibleName('Scrollable authoring workspace')
    scroll.setWidgetResizable(True)
    scroll.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    scroll.setWidget(widget)
    return scroll
