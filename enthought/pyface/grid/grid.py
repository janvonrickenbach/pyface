#------------------------------------------------------------------------------
# Copyright (c) 2005, Enthought, Inc.
# All rights reserved.
# 
# This software is provided without warranty under the terms of the BSD
# license included in enthought/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
# Thanks for using Enthought open source!
# 
# Author: Enthought, Inc.
# Description: <Enthought pyface package component>
#------------------------------------------------------------------------------
""" A grid control with a model/ui architecture. """

# Major package imports
import sys
import wx
from wx.grid import Grid as wxGrid
from wx.grid import GridCellAttr, GridCellBoolRenderer, PyGridTableBase
from wx.grid import GridTableMessage, \
     GRIDTABLE_NOTIFY_ROWS_APPENDED, GRIDTABLE_NOTIFY_ROWS_DELETED, \
     GRIDTABLE_NOTIFY_COLS_APPENDED, GRIDTABLE_NOTIFY_COLS_DELETED, \
     GRIDTABLE_REQUEST_VIEW_GET_VALUES, GRID_VALUE_STRING
from wx import TheClipboard

# Enthought library imports
from enthought.pyface.api import Sorter, Widget
from enthought.pyface.timer.api import do_later
from enthought.traits.api import Bool, Color, Enum, Event, Font, Instance, Int, \
     List, Trait
from enthought.util.wx.drag_and_drop import PythonDropSource, \
     PythonDropTarget, PythonObject
from enthought.util.wx.drag_and_drop import clipboard as enClipboard

# local imports
from grid_model import GridModel
from combobox_focus_handler import ComboboxFocusHandler

# Is this code running on MS Windows?
is_win32 = (sys.platform == 'win32')

ASCII_C = 67

class Grid(Widget):
    """ A grid control with a model/ui architecture. """

    #### 'Grid' interface #####################################################

    # The model that provides the data for the grid.
    model = Instance(GridModel, ())

    # Should grid lines be shown on the table?
    enable_lines = Bool(True)

    # The color to show gridlines in
    grid_line_color = Color("blue")

    # Show row headers?
    show_row_headers = Bool(True)

    # Show column headers?
    show_column_headers = Bool(True)

    # The default font to use for text in labels
    default_label_font = Font(None)

    # The default background color for labels
    default_label_bg_color = Color(wx.Colour(236, 233, 216))

    # The default text color for labels
    default_label_text_color = Color("black")

    # The color to use for a selection background
    selection_bg_color = Trait(wx.Colour(49, 106, 197), None, Color)

    # The color to use for a selection foreground/text
    selection_text_color = Trait(wx.Colour(255, 255, 255), None, Color)

    # The default font to use for text in cells
    default_cell_font = Font(None)

    # The default text color to use for text in cells
    default_cell_text_color = Color("black")

    # The default background color to use for editable cells
    default_cell_bg_color = Color("white")

    # The default background color to use for read-only cells
    #default_cell_read_only_color = Trait(Color("linen"), None, Color)
    default_cell_read_only_color = Color(wx.Colour(248, 247, 241))

    # Should the grid be read-only? If this is set to false, individual
    # cells can still declare themselves read-only.
    read_only = Bool(False)

    # Selection mode.
    selection_mode = Enum('cell', 'rows', 'cols', '')

    # Sort data when a column header is clicked?
    allow_column_sort = Bool(True)

    # Sort data when a row header is clicked?
    allow_row_sort = Bool(False)

    # pixel height of column labels
    column_label_height = Int(32)

    # pixel width of row labels
    row_label_width = Int(82)

    # auto-size columns and rows?
    # Probably the only time to set this to False is for very large data sets.
    autosize = Bool(True)

    # Allow single-click access to cell-editors?
    edit_on_first_click = Bool(True)

    #### Events ####

    # A cell has been activated (ie. double-clicked).
    cell_activated = Event

    # The current selection has changed. 
    selection_changed = Event

    # A drag operation was started on a cell.
    cell_begin_drag = Event

    # A left-click occurred on a cell.
    cell_left_clicked = Event

    # A right-click occurred on a cell.
    cell_right_clicked = Event

    ###########################################################################
    # 'object' interface.
    ###########################################################################
    def __init__(self, parent, **traits):
        """ Creates a new grid.

        'parent' is the toolkit-specific control that is the grid's parent.

        """

        # Base class constructors.
        super(Grid, self).__init__(**traits)

        # Create the toolkit-specific control.
        self.control = panel = wx.Panel(parent, -1)
        
        self._grid = grid = wxGrid(panel, -1)
        grid.grid  = self
        
        sizer = wx.BoxSizer( wx.VERTICAL )
        sizer.Add( grid, 1, wx.EXPAND )
        panel.SetSizer( sizer )

        #self.control = self._grid = grid = wxGrid(parent, -1)

        # initialize the current selection
        self.__current_selection = ()

        self.__initialize_counts(self.model)
        self.__initialize_sort_state()

        # Don't display any extra space around the rows and columns.
        grid.SetMargins(0, 0)
        
        # Provides more accurate scrolling behavior without creating large
        # margins on the bottom and right. The down side is that it makes
        # scrolling using the scroll bar buttons painfully slow:
        grid.SetScrollLineX(1)
        grid.SetScrollLineY(1)

        # Tell the grid to get its data from the model.
        #
        # N.B The terminology used in the wxPython API is a little confusing!
        # --- The 'SetTable' method is actually setting the model used by
        #     the grid (which is the view)!
        #
        # The second parameter to 'SetTable' tells the grid to take ownership
        # of the model and to destroy it when it is done.  Otherwise you would
        # need to keep a reference to the model and manually destroy it later
        # (by calling it's Destroy method).
        #
        # fixme: We should create a default model if one is not supplied.
        
        # The wx virtual table hook.

        self._grid_table_base = _GridTableBase(self.model, self)

        grid.SetTable(self._grid_table_base, True)
        self.model.on_trait_change(self._on_model_content_changed,
                                   'content_changed')
        self.model.on_trait_change(self._on_model_structure_changed,
                                   'structure_changed')
        self.model.on_trait_change(self._on_row_sort,
                                   'row_sorted')
        self.model.on_trait_change(self._on_column_sort,
                                   'column_sorted')
        self.on_trait_change(self._on_new_model,
                             'model')

        # hook up style trait handlers - note that we have to use
        # dynamic notification hook-ups because these handlers should
        # not be called until after the control object is initialized.
        # static trait notifiers get called when the object inits.
        self.on_trait_change(self._on_enable_lines_changed,
                             'enable_lines')
        self.on_trait_change(self._on_grid_line_color_changed,
                             'grid_line_color')
        self.on_trait_change(self._on_default_label_font_changed,
                             'default_label_font')
        self.on_trait_change(self._on_default_label_bg_color_changed,
                             'default_label_bg_color')
        self.on_trait_change(self._on_default_label_text_color_changed,
                             'default_label_text_color')
        self.on_trait_change(self._on_selection_bg_color_changed,
                             'selection_bg_color')
        self.on_trait_change(self._on_selection_text_color_changed,
                             'selection_text_color')
        self.on_trait_change(self._on_default_cell_font_changed,
                             'default_cell_font')
        self.on_trait_change(self._on_default_cell_text_color_changed,
                             'default_cell_text_color')
        self.on_trait_change(self._on_default_cell_bg_color_changed,
                             'default_cell_bg_color')
        self.on_trait_change(self._on_read_only_changed,
                             'read_only_changed')
        self.on_trait_change(self._on_selection_mode_changed,
                             'selection_mode')
        self.on_trait_change(self._on_column_label_height_changed,
                             'column_label_height')
        self.on_trait_change(self._on_row_label_width_changed,
                             'row_label_width')
        self.on_trait_change(self._on_show_column_headers_changed,
                             'show_column_headers')
        self.on_trait_change(self._on_show_row_headers_changed,
                             'show_row_headers')

        # initialize wx handlers
        wx.grid.EVT_GRID_CELL_CHANGE(grid, self._on_cell_change)
        wx.grid.EVT_GRID_SELECT_CELL(grid, self._on_select_cell)
        wx.grid.EVT_GRID_RANGE_SELECT(grid, self._on_range_select)
        wx.grid.EVT_GRID_COL_SIZE(grid, self._on_col_size)
        wx.grid.EVT_GRID_ROW_SIZE(grid, self._on_row_size)

        # This starts the cell editor on a double-click as well as on a second
        # click.
        wx.grid.EVT_GRID_CELL_LEFT_DCLICK(grid, self._on_cell_left_dclick)

        # notify when cells are clicked on
        wx.grid.EVT_GRID_CELL_LEFT_CLICK(grid, self._on_cell_left_click)
        wx.grid.EVT_GRID_CELL_RIGHT_CLICK(grid, self._on_cell_right_click)
        wx.grid.EVT_GRID_CELL_RIGHT_DCLICK(grid, self._on_cell_right_dclick)

        wx.grid.EVT_GRID_LABEL_RIGHT_CLICK(grid, self._on_label_right_click)
        wx.grid.EVT_GRID_LABEL_LEFT_CLICK(grid, self._on_label_left_click)

        wx.grid.EVT_GRID_EDITOR_CREATED(grid, self._on_editor_created)

        # We handle key presses to change the behavior of the <Enter> and
        # <Tab> keys to make manual data entry smoother.
        wx.EVT_KEY_DOWN(grid, self._on_key_down)

        # We handle key up events to handle ctrl+c copy
        #wx.EVT_KEY_UP(grid, self._on_key_up)
        
        # We handle control resize events to adjust column widths
        wx.EVT_SIZE(grid, self._on_size)

        # Handle drags
        self._grid_window = grid.GetGridWindow()
        self._row_window = grid.GetGridRowLabelWindow()
        self._col_window = grid.GetGridColLabelWindow()
        self._corner_window = grid.GetGridCornerLabelWindow()
        wx.EVT_MOTION(self._grid_window, self._on_grid_motion)
        wx.EVT_MOTION(self._row_window, self._on_row_label_motion)
        wx.EVT_MOTION(self._col_window, self._on_col_label_motion)

        wx.EVT_PAINT(self._grid_window, self._on_grid_window_paint)

        # Initialize the row and column models.
        self.__initialize_rows(self.model)
        self.__initialize_columns(self.model)
        self.__initialize_fonts()

        # handle trait style settings
        self.__initialize_style_settings()

        # Enable the tree as a drag and drop target.
        self._grid.SetDropTarget(PythonDropTarget(self))

        # Flag set when columns are resizing.
        self._user_col_size = False

        self.__autosize()

        self._edit = False
        wx.EVT_IDLE(grid, self._on_idle)
        
        return

    def dispose(self):
        self._grid_table_base.dispose()

        self.on_trait_change(self._on_enable_lines_changed,
                             'enable_lines',
                             remove = True)
        self.on_trait_change(self._on_grid_line_color_changed,
                             'grid_line_color',
                             remove = True)
        self.on_trait_change(self._on_default_label_font_changed,
                             'default_label_font',
                             remove = True)
        self.on_trait_change(self._on_default_label_bg_color_changed,
                             'default_label_bg_color',
                             remove = True)
        self.on_trait_change(self._on_default_label_text_color_changed,
                             'default_label_text_color',
                             remove = True)
        self.on_trait_change(self._on_selection_bg_color_changed,
                             'selection_bg_color',
                             remove = True)
        self.on_trait_change(self._on_selection_text_color_changed,
                             'selection_text_color',
                             remove = True)
        self.on_trait_change(self._on_default_cell_font_changed,
                             'default_cell_font',
                             remove = True)
        self.on_trait_change(self._on_default_cell_text_color_changed,
                             'default_cell_text_color',
                             remove = True)
        self.on_trait_change(self._on_default_cell_bg_color_changed,
                             'default_cell_bg_color',
                             remove = True)
        self.on_trait_change(self._on_read_only_changed,
                             'read_only_changed',
                             remove = True)
        self.on_trait_change(self._on_selection_mode_changed,
                             'selection_mode',
                             remove = True)
        self.on_trait_change(self._on_column_label_height_changed,
                             'column_label_height',
                             remove = True)
        self.on_trait_change(self._on_row_label_width_changed,
                             'row_label_width',
                             remove = True)
        self.on_trait_change(self._on_show_column_headers_changed,
                             'show_column_headers',
                             remove = True)
        self.on_trait_change(self._on_show_row_headers_changed,
                             'show_row_headers',
                             remove = True)
        
        return
        

    ###########################################################################
    # Trait event handlers.
    ###########################################################################

    def _on_new_model(self):
        """ When we get a new model reinitialize grid match to that model. """

        self._grid_table_base.model = self.model

        self.__initialize_counts(self.model)

        self._on_model_changed()

        if self.autosize:
            # Note that we don't call AutoSize() here, because autosizing
            # the rows looks like crap.
            self._grid.AutoSizeColumns(False)
            
        return

    def _on_model_content_changed(self):
        """ A notification method called when the data in the underlying
            model changes. """

        # Note: We're seeing some wx 2.6 weirdness in the traits TableEditor
        #       because of what's going on here. TextEditors and ComboEditors
        #       update the trait value for every character typed. The
        #       TableEditor catches these changes and fires the
        #       model_content_changed event. In this routine we then update
        #       the values in the table by sending the
        #       wxGRIDTABLE_REQUEST_VIEW_GET_VALUES message, which at the
        #       c++ grid level forces the editor to close. So those editors
        #       don't allow you to type more than one character before closing.
        #       For now, we are fixing this in those specific editors, but
        #       we may need a more general solution at some point.

        # make sure we update for any new values in the table
        msg = GridTableMessage(self._grid_table_base,
                               GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self._grid.ProcessTableMessage(msg)
        
        self._grid.ForceRefresh()

        return

    def _on_model_structure_changed(self, *arg, **kw):
        """ A notification method called when the underlying model has
        changed. Responsible for making sure the view object updates
        correctly. """

        # disable any editors that are hap'nin to fix crash bug
        self._edit = False
        grid       = self._grid

        # more wacky fun with wx. we have to manufacture the appropriate
        # grid messages and send them off to make sure the grid updates
        # correctly
        should_autosize = False
        
        # first check to see if rows have been added or deleted.
        row_count       = self.model.get_row_count()
        delta           = row_count - self._row_count
        self._row_count = row_count
        
        if delta > 0:
            # rows were added
            msg = GridTableMessage(self._grid_table_base,
                                   GRIDTABLE_NOTIFY_ROWS_APPENDED, delta)
            grid.ProcessTableMessage(msg)
            should_autosize = True
        elif delta < 0:
            # rows were deleted

            # why the arglist for the "rows deleted" message is different
            # from that of the "rows added" message is beyond me.
            msg = GridTableMessage(self._grid_table_base,
                                   GRIDTABLE_NOTIFY_ROWS_DELETED,
                                   row_count, -delta)
            grid.ProcessTableMessage(msg)
            should_autosize = True

        # now check for column changes
        col_count       = self.model.get_column_count()
        delta           = col_count - self._col_count
        self._col_count = col_count
        
        if delta > 0:
            # columns were added
            msg = GridTableMessage(self._grid_table_base,
                                   GRIDTABLE_NOTIFY_COLS_APPENDED, delta)
            grid.ProcessTableMessage(msg)
            should_autosize = True
        elif delta < 0:
            # columns were deleted
            msg = GridTableMessage(self._grid_table_base,
                                   GRIDTABLE_NOTIFY_COLS_DELETED,
                                   col_count, -delta)
            grid.ProcessTableMessage(msg)
            should_autosize = True


        # finally make sure we update for any new values in the table
        msg = GridTableMessage(self._grid_table_base,
                               GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)

        if should_autosize:
            self.__autosize()

        # we have to make sure the editor/renderer cache in the GridTableBase
        # object is cleaned out.
        self._grid_table_base._clear_cache()

        grid.AdjustScrollbars()
        self._refresh()

        return

    def _on_row_sort(self, evt):
        """ Handles a row_sorted event from the underlying model. """

        # first grab the new data out of the event
        if evt.index < 0:
            self._current_sorted_row = None
        else:
            self._current_sorted_row = evt.index

        self._row_sort_reversed = evt.reversed

        # since the label may have changed we may need to autosize again
        # fixme: when we change how we represent the sorted column
        #        this should go away.
        self.__autosize()

        # make sure everything updates to reflect the changes
        self._on_model_structure_changed()
        
        return

    def _on_column_sort(self, evt):
        """ Handles a column_sorted event from the underlying model. """

        # first grab the new data out of the event
        if evt.index < 0:
            self._current_sorted_col = None
        else:
            self._current_sorted_col = evt.index

        self._col_sort_reversed = evt.reversed

        # since the label may have changed we may need to autosize again
        # fixme: when we change how we represent the sorted column
        #        this should go away.
        self.__autosize()

        # make sure everything updates to reflect the changes
        self._on_model_structure_changed()
        return

    def _on_enable_lines_changed(self):
        """ Handle a change to the enable_lines trait. """
        self._grid.EnableGridLines(self.enable_lines)
        return
    
    def _on_grid_line_color_changed(self):
        """ Handle a change to the enable_lines trait. """
        self._grid.SetGridLineColour(self.grid_line_color)
        return

    def _on_default_label_font_changed(self):
        """ Handle a change to the default_label_font trait. """

        font = self.default_label_font
        if font is None:
            font = wx.Font(8, wx.SWISS, wx.NORMAL, wx.BOLD)
        self._grid.SetLabelFont(font)

        return

    def _on_default_label_text_color_changed(self):
        """ Handle a change to the default_cell_text_color trait. """

        if self.default_label_text_color is not None:
            color = self.default_label_text_color
            self._grid.SetLabelTextColour(color)
            self._grid.ForceRefresh()

        return

    def _on_default_label_bg_color_changed(self):
        """ Handle a change to the default_cell_text_color trait. """

        if self.default_label_bg_color is not None:
            color = self.default_label_bg_color
            self._grid.SetLabelBackgroundColour(color)
            self._grid.ForceRefresh()

        return

    def _on_selection_bg_color_changed(self):
        """ Handle a change to the selection_bg_color trait. """
        if self.selection_bg_color is not None:
            self._grid.SetSelectionBackground(self.selection_bg_color)

        return

    def _on_selection_text_color_changed(self):
        """ Handle a change to the selection_text_color trait. """
        if self.selection_text_color is not None:
            self._grid.SetSelectionForeground(self.selection_text_color)
        return
    
    def _on_default_cell_font_changed(self):
        """ Handle a change to the default_cell_font trait. """

        if self.default_cell_font is not None:
            self._grid.SetDefaultCellFont(self.default_cell_font)
            self._grid.ForceRefresh()

        return

    def _on_default_cell_text_color_changed(self):
        """ Handle a change to the default_cell_text_color trait. """

        if self.default_cell_text_color is not None:
            color = self.default_cell_text_color
            self._grid.SetDefaultCellTextColour(color)
            self._grid.ForceRefresh()

        return
    
    def _on_default_cell_bg_color_changed(self):
        """ Handle a change to the default_cell_bg_color trait. """

        if self.default_cell_bg_color is not None:
            color = self.default_cell_bg_color
            self._grid.SetDefaultCellBackgroundColour(color)
            self._grid.ForceRefresh()
        return
    
    def _on_read_only_changed(self):
        """ Handle a change to the read_only trait. """

        # should the whole grid be read-only?
        if self.read_only:
            self._grid.EnableEditing(False)
        else:
            self._grid.EnableEditing(True)

        return

    def _on_selection_mode_changed(self):
        """ Handle a change to the selection_mode trait. """

        # should we allow individual cells to be selected or only rows
        # or only columns
        if self.selection_mode == 'cell':
            self._grid.SetSelectionMode(wxGrid.wxGridSelectCells)
        elif self.selection_mode == 'rows':
            self._grid.SetSelectionMode(wxGrid.wxGridSelectRows)
        elif self.selection_mode == 'cols':
            self._grid.SetSelectionMode(wxGrid.wxGridSelectColumns)

        return

    def _on_column_label_height_changed(self):
        """ Handle a change to the column_label_height trait. """

        # handle setting for height of column labels
        if self.column_label_height is not None:
            self._grid.SetColLabelSize(self.column_label_height)

        return

    def _on_row_label_width_changed(self):
        """ Handle a change to the row_label_width trait. """
        # handle setting for width of row labels
        if self.row_label_width is not None:
            self._grid.SetRowLabelSize(self.row_label_width)

        return

    def _on_show_column_headers_changed(self):
        """ Handle a change to the show_column_headers trait. """

        if not self.show_column_headers:
            self._grid.SetColLabelSize(0)
        else:
            self._grid.SetColLabelSize(self.column_label_height)

        return

    def _on_show_row_headers_changed(self):
        """ Handle a change to the show_row_headers trait. """

        if not self.show_row_headers:
            self._grid.SetRowLabelSize(0)
        else:
            self._grid.SetRowLabelSize(self.row_label_width)

        return

    ###########################################################################
    # 'Grid' interface.
    ###########################################################################

    def get_selection(self):
        """ Return a list of the currently selected objects. """

        return self.__get_selection()

    def set_selection(self, selection_list):
        """ Set the current selection to the objects listed in selection_list.
        Note that these objects are model-specific, as the grid depends on the
        underlying model to translate these objects into grid coordinates.
        A ValueError will be raised if the objects are not in the proper format
        for the underlying model. """

        # first use the model to resolve the object list into a set of
        # grid coordinates
        cells = self.model.resolve_selection(selection_list)

        # now make sure all those grid coordinates get set properly
        self._grid.ClearSelection()
        if self.selection_mode == '':
            return
        
        for selection in cells:
            if selection[0] == -1:
                # a column selection! whoo-hoo!
                self._grid.SelectCol(selection[1], True)
            elif selection[1] == -1:
                # a row selection! groovy!
                self._grid.SelectRow(selection[0], True)
            else:
                # a cell selection! that's crazy talk!
                self._grid.SelectBlock(selection[0], selection[1],
                                         selection[0], selection[1], True)

        return

    ###########################################################################
    # wx event handlers.
    ###########################################################################

    def _on_size(self, evt):
        """ Called when the grid is resized. """
        self.__autosize(True)
        
    # needed to handle problem in wx 2.6 with combobox cell editors
    def _on_editor_created(self, evt):

        editor = evt.GetControl()
        editor.PushEventHandler(ComboboxFocusHandler())

        evt.Skip()
        return

    def _on_grid_window_paint(self, evt):

        # fixme: this is a total h*ck to get rid of the scrollbars that appear
        # on a grid under wx2.6 when it starts up. these appear whether or
        # not needed, and disappear as soon as the grid is resized. hopefully
        # we will be able to remove this egregious code on some future version
        # of wx.
        self._grid.SetColSize(0, self._grid.GetColSize(0) + 1)
        self._grid.SetColSize(0, self._grid.GetColSize(0) - 1)

        evt.Skip()
        return

    def _on_motion(self, evt):
        """ Called when the mouse moves. """

        if evt.Dragging() and not evt.ControlDown():
            data = self.__get_drag_value()
            PythonDropSource(self._grid, data)

        evt.Skip()
        return

    def _on_grid_motion(self, evt):

        x, y = self._grid.CalcUnscrolledPosition(evt.GetPosition())
        row = self._grid.YToRow(y)
        col = self._grid.XToCol(x)

        # Notify the model that the mouse has moved into the cell at row,col,
        # only if the row and col are valid.
        if (row >= 0) and (col >= 0):
            self.model.mouse_cell = (row, col)

        # If the mouse is roughly centered over the cell, call _on_motion.
        if ((self._grid.XToEdgeOfCol(evt.GetX()) != wx.NOT_FOUND) and
            (self._grid.YToEdgeOfRow(evt.GetY()) != wx.NOT_FOUND)):
            self._on_motion(evt)
        
        evt.Skip()
        return

    def _on_col_label_motion(self, evt):
        """ Called when the mouse moves on the column label window. """

        # this is a total hack to determine if we are currently resizing.
        # if we are then we don't start a data drag, but just skip on the
        # event. i wish there were some better way to tell this, but there
        # doesn't seem to be any underlying state in the wxPython bindings
        # specifying that a resize is happening.
        self._on_grid_motion(evt)

    def _on_row_label_motion(self, evt):
        """ Called when the mouse moves on the row label window. """

        # note that this code is basically the same as _on_col_label_motion

        # this is a total hack to determine if we are currently resizing.
        # if we are then we don't start a data drag, but just skip on the
        # event. i wish there were some better way to tell this, but there
        # doesn't seem to be any underlying state in the wxPython bindings
        # specifying that a resize is happening.
        self._on_grid_motion(evt)

    def _on_cell_change(self, evt):
        """ Called when the contents of a cell have been changed. """

        row = evt.GetRow()
        col = evt.GetCol()
         
        evt.Skip()
        
        return

    def _on_select_cell(self, evt):
        """ Called when the user has moved to another cell. """ 
        row = evt.GetRow()
        col = evt.GetCol()

        if evt.ControlDown():
            self._grid.ClearSelection()

        if evt.Selecting():
            self._grid.ClearSelection()

        if self.selection_mode != '' or not self.edit_on_first_click:
            self._grid.SelectBlock(row, col, row, col, False)
        self._edit = True
        evt.Skip()
        
        return
    
    def _on_range_select(self, evt):
        """ Called when a range of cells has been selected. """
        # find the range of selection
        top_row = evt.GetTopRow()
        left_col = evt.GetLeftCol()
        bottom_row = evt.GetBottomRow()
        right_col = evt.GetRightCol()

        if not evt.Selecting():
            self.__fire_selection_changed(())
            return


        # find the size of the grid
        row_size = self.model.get_row_count()
        col_size = self.model.get_column_count()

        col_select = top_row == 0 and bottom_row == row_size - 1
        row_select = left_col == 0 and right_col == col_size - 1
        cell_select = top_row == bottom_row and left_col == right_col

        # we veto range selects of greater than 1 cell UNLESS they are
        # selections of whole columns or whole rows
        if self.selection_mode == 'cell':
            if not col_select and not row_select and not cell_select:
                self._grid.ClearSelection()
                evt.Veto()

            if cell_select and evt.ControlDown():
                self._grid.ClearSelection()
        
        self.__fire_selection_changed(((top_row, left_col), (bottom_row, right_col)))

        return
        
    def _on_col_size(self, evt):
        """ Called when the user changes a column's width. """
        self._user_col_size = True
        self._grid.AdjustScrollbars()
        
        evt.Skip()
        
    def _on_row_size(self, evt):
        """ Called when the user changes a row's height. """
        self._grid.AdjustScrollbars()
        
        evt.Skip()

    def _on_idle(self, evt):
        """ Immediately jumps into editing mode, bypassing the
            usual select mode of a spreadsheet. See also self.OnSelectCell(). 
        """
        
        if self._edit == True and self.edit_on_first_click:
            if self._grid.CanEnableCellControl():
                self._grid.EnableCellEditControl()
            self._edit = False
            
        evt.Skip()

    def _on_cell_left_click(self, evt):
        """ Called when the left mouse button was clicked. """
        row = evt.GetRow()
        col = evt.GetCol()

        self.cell_left_clicked = (row, col)

        # try to find a renderer for this cell
        renderer = self.model.get_cell_renderer(row, col)

        # if the renderer has defined a handler then call it
        result = False
        if renderer is not None:
            result = renderer.on_left_click(self, row, col)

        if self.selection_mode == 'cell':
            self._grid.SelectBlock(row, col, row, col, False)

        evt.Skip()

        return

    def _on_cell_left_dclick(self, evt):
        """ Called when the left mouse button was double-clicked.

        From the wxPython demo code:-
    
        'I do this because I don't like the default behaviour of not starting
        the cell editor on double clicks, but only a second click.'

        Fair enuff!

        """

        row = evt.GetRow()
        col = evt.GetCol()
        data = self.model.get_value(row, col)
        self.cell_activated = data

        # try to find a renderer for this cell
        renderer = self.model.get_cell_renderer(row, col)

        # if the renderer has defined a handler then call it
        if renderer is not None:
            renderer.on_left_dclick(self, row, col)
        
        return

    def _on_cell_right_dclick(self, evt):
        """ Called when the right mouse button was double-clicked.

        From the wxPython demo code:-
    
        'I do this because I don't like the default behaviour of not starting
        the cell editor on double clicks, but only a second click.'

        Fair enuff!

        """

        row = evt.GetRow()
        col = evt.GetCol()

        # try to find a renderer for this cell
        renderer = self.model.get_cell_renderer(row, col)

        # if the renderer has defined a handler then call it
        if renderer is not None:
            renderer.on_right_dclick(self, row, col)

        return

    def _on_cell_right_click(self, evt):
        """ Called when a right click occurred in a cell. """

        row = evt.GetRow()
        col = evt.GetCol()

        # try to find a renderer for this cell
        renderer = self.model.get_cell_renderer(row, col)

        # if the renderer has defined a handler then call it
        result = False
        if renderer is not None:
            result = renderer.on_right_click(self, row, col)

        # if the handler didn't tell us to stop further handling then skip
        if not result:
            # ask model for the appropriate context menu
            menu_manager = self.model.get_cell_context_menu(row, col)
            # get the underlying menu object
            if menu_manager is not None:
                controller = None
                if type( menu_manager ) is tuple:
                    menu_manager, controller = menu_manager
                menu = menu_manager.create_menu(self._grid, controller)
                # if it has anything in it pop it up
                if menu.GetMenuItemCount() > 0:
                    # Popup the menu (if an action is selected it will be
                    # performed before before 'PopupMenu' returns).
                    x, y = evt.GetPosition()
                    self._grid.PopupMenuXY(menu, x - 10, y - 10 )
        
            self.cell_right_clicked = (row, col)

            evt.Skip()

        return
        
    def _on_label_right_click(self, evt):
        """ Called when a right click occurred on a label. """

        row = evt.GetRow()
        col = evt.GetCol()

        # a row value of -1 means this click happened on a column.
        # vice versa, a col value of -1 means a row click.
        menu_manager = None
        if row == -1:
            menu_manager = self.model.get_column_context_menu(col)
        else:
            menu_manager = self.model.get_row_context_menu(row)

        if menu_manager is not None:
            # get the underlying menu object
            menu = menu_manager.create_menu(self._grid)
            # if it has anything in it pop it up
            if menu.GetMenuItemCount() > 0:
                # Popup the menu (if an action is selected it will be performed
                # before before 'PopupMenu' returns).
                self._grid.PopupMenu(menu, evt.GetPosition())
        
        evt.Skip()

        return
        
    def _on_label_left_click(self, evt):
        """ Called when a left click occurred on a label. """

        row = evt.GetRow()
        col = evt.GetCol()

        # a row value of -1 means this click happened on a column.
        # vice versa, a col value of -1 means a row click.
        self._grid.Freeze()
        if row == -1 and self.allow_column_sort:
            if col == self._current_sorted_col and \
               not self._col_sort_reversed:
                # if this column is currently sorted on then reverse it
                self.model.sort_by_column(col, True)
            elif col == self._current_sorted_col and self._col_sort_reversed:
                # if this column is currently reverse-sorted then unsort it
                try:
                    self.model.no_column_sort()
                except NotImplementedError:
                    # if an unsort function is not implemented then just
                    # reverse the sort
                    self.model.sort_by_column(col, False)
            else:
                # sort the data
                self.model.sort_by_column(col, False)
        elif col == -1 and self.allow_row_sort:
            if row == self._current_sorted_row and \
               not self._row_sort_reversed:
                # if this row is currently sorted on then reverse it
                self.model.sort_by_row(row, True)
            elif row == self._current_sorted_row and self._row_sort_reversed:
                # if this row is currently reverse-sorted then unsort it
                try:
                    self.model.no_row_sort()
                except NotImplementedError:
                    # if an unsort function is not implemented then just
                    # reverse the sort
                    self.model.sort_by_row(row, False)
            else:
                # sort the data
                self.model.sort_by_row(row, False)
            
        self._grid.Thaw()
        evt.Skip()
        return

    def _on_key_down(self, evt):
        """ Called when a key is pressed. """
        # This changes the behaviour of the <Enter> and <Tab> keys to make
        # manual data entry smoother!
        #
        # Don't change the behavior if the <Control> key is pressed as this
        # has meaning to the edit control.
        key_code = evt.GetKeyCode()
        if key_code == wx.WXK_RETURN and not evt.ControlDown():
            self._move_to_next_cell(evt.ShiftDown())

        elif key_code == wx.WXK_TAB and not evt.ControlDown():
            if evt.ShiftDown():
                # fixme: in a split window the shift tab is being eaten
                # by tabbing between the splits
                self._move_to_previous_cell()

            else:
                self._move_to_next_cell()
        elif key_code == ASCII_C:
            data = self.__get_drag_value()
            # deposit the data in our singleton clipboard
            enClipboard.data = data

            # build a wxCustomDataObject to notify the system clipboard
            # that some in-process data is available
            data_object = wx.CustomDataObject(PythonObject)
            data_object.SetData('dummy')
            if TheClipboard.Open():
                TheClipboard.SetData(data_object)
                TheClipboard.Close()
            
        evt.Skip()

        return

    def _move_to_next_cell(self, expandSelection=False):
        """ Move to the 'next' cell. """

        # Complete the edit on the current cell.
        self._grid.DisableCellEditControl()

        # Try to move to the next column.
        success = self._grid.MoveCursorRight(expandSelection)

        # If the move failed then we must be at the end of a row.
        if not success:
            # Move to the first column in the next row.
            newRow = self._grid.GetGridCursorRow() + 1
            if newRow < self._grid.GetNumberRows():
                self._grid.SetGridCursor(newRow, 0)
                self._grid.MakeCellVisible(newRow, 0)

            else:
                # This would be a good place to add a new row if your app
                # needs to do that.
                pass
            
        return success

    def _move_to_previous_cell(self, expandSelection=False):
        """ Move to the 'previous' cell. """

        # Complete the edit on the current cell.
        self._grid.DisableCellEditControl()

        # Try to move to the previous column (without expanding the current
        # selection).
        success = self._grid.MoveCursorLeft(expandSelection)

        # If the move failed then we must be at the start of a row.
        if not success:
            # Move to the last column in the previous row.
            newRow = self._grid.GetGridCursorRow() - 1
            if newRow >= 0:
                self._grid.SetGridCursor(newRow,
                                           self._grid.GetNumberCols() - 1)
                self._grid.MakeCellVisible(newRow,
                                             self._grid.GetNumberCols() - 1)

        return
        
    def _refresh(self):
        self._grid.GetParent().Layout()

    ###########################################################################
    # PythonDropTarget interface.
    ###########################################################################
    def wx_dropped_on ( self, x, y, drag_object, drag_result ):

        # first resolve the x/y coords into a grid row/col
        row, col = self.__resolve_grid_coords(x, y)

        result = wx.DragNone
        if row != -1 and col != -1:
            # now ask the model if the target cell can accept this object
            valid_target = self.model.is_valid_cell_value(row, col,
                                                          drag_object)
            # if this is a valid target then attempt to set the value
            if valid_target:
                # find the data
                data = drag_object
                # sometimes a 'node' attribute on the clipboard gets set
                # to a binding. if this happens we want to use it, otherwise
                # we want to just use the drag_object passed to us
                if hasattr(enClipboard, 'node') and \
                   enClipboard.node is not None:
                    data = enClipboard.node
                    
                # now make sure the value gets set in the model
                self.model.set_value(row, col, data)
                result = drag_result
        return

    def wx_drag_over ( self, x, y, drag_object, drag_result ):

        # first resolve the x/y coords into a grid row/col
        row, col = self.__resolve_grid_coords(x, y)

        result = wx.DragNone
        if row != -1 and col != -1:
            # now ask the model if the target cell can accept this object
            valid_target = self.model.is_valid_cell_value(row, col,
                                                          drag_object)
            if valid_target:
                result = drag_result

        return result
    
    ###########################################################################
    # private interface.
    ###########################################################################

    def __initialize_fonts(self):
        """ Initialize the label fonts. """
        
        self._on_default_label_font_changed()
        self._on_default_cell_font_changed()
        self._on_default_cell_text_color_changed()
        self._on_grid_line_color_changed()

        self._grid.SetColLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
        self._grid.SetRowLabelAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)

        return
    
    def __initialize_rows(self, model):
        """ Initialize the row headers. """

        # should we really be doing this?
        for row in range(model.get_row_count()):
            if model.is_row_read_only(row):
                attr = wx.grid.GridCellAttr()
                attr.SetReadOnly()
                #attr.SetRenderer(None)
                #attr.SetBackgroundColour('linen')
                self._grid.SetRowAttr(row, attr)

        return

    def __initialize_columns(self, model):
        """ Initialize the column headers. """

        # should we really be doing this?
        for column in range(model.get_column_count()):
            if model.is_column_read_only(column):
                attr = wx.grid.GridCellAttr()
                attr.SetReadOnly()
                #attr.SetRenderer(None)
                #attr.SetBackgroundColour('linen')
                self._grid.SetColAttr(column, attr)

        return

    def __initialize_counts(self, model):
        """ Initializes the row and column counts. """

        if model is not None:
            self._row_count = model.get_row_count()
        else:
            self._row_count = 0

        if model is not None:
            self._col_count = model.get_column_count()
        else:
            self._col_count = 0

        return

    def __initialize_sort_state(self):
        """ Initializes the row and column counts. """

        self._current_sorted_col = None
        self._current_sorted_row = None
        self._col_sort_reversed = False
        self._row_sort_reversed = False

        return

    def __initialize_style_settings(self, event=None):

        # make sure all the handlers for traits defining styles get called
        self._on_enable_lines_changed()
        self._on_read_only_changed()
        self._on_selection_mode_changed()
        self._on_column_label_height_changed()
        self._on_row_label_width_changed()
        self._on_show_column_headers_changed()
        self._on_show_row_headers_changed()
        self._on_default_cell_bg_color_changed()
        self._on_default_label_bg_color_changed()
        self._on_default_label_text_color_changed()
        self._on_selection_bg_color_changed()
        self._on_selection_text_color_changed()
        
        return

    def __get_drag_value(self):
        """ Calculates the drag value based on the current selection. """

        rows, cols = self.__get_selected_rows_and_cols()

        if len(rows) > 0:
            rows.sort()
            value = self.model.get_rows_drag_value(rows)
            if len(rows) == 1 and len(value) == 1:
                value = value[0]
        elif len(cols) > 0:
            cols.sort()
            value = self.model.get_cols_drag_value(cols)
            if len(cols) == 1 and len(value) == 1:
                value = value[0]
        else:
            # our final option -- grab the cell that the cursor is currently in
            row = self._grid.GetGridCursorRow()
            col = self._grid.GetGridCursorCol()
            value = self.model.get_cell_drag_value(row, col)

        return value

    def __get_selection(self):
        """ Returns a list of values for the current selection. """

        rows, cols = self.__get_selected_rows_and_cols()

        if len(rows) > 0:
            rows.sort()
            value = self.model.get_rows_selection_value(rows)
        elif len(cols) > 0:
            cols.sort()
            value = self.model.get_cols_selection_value(cols)
        else:
            # our final option -- grab the cell that the cursor is currently in
            row = self._grid.GetGridCursorRow()
            col = self._grid.GetGridCursorCol()
            value = self.model.get_cell_selection_value(row, col)
            if value is not None:
                value = [value]

        if value is None:
            value = []

        return value

    def __get_selected_rows_and_cols(self):
        """ Return lists of the selected rows and the selected columns. """

        # note: because the wx grid control is so screwy, we have limited
        # the selection behavior. we only allow single cells to be selected,
        # or whole row, or whole columns.

        rows = self._grid.GetSelectedRows()
        cols = self._grid.GetSelectedCols()

        # because wx is retarded we have to check this as well -- why
        # the blazes can't they come up with one Q#$%@$#% API to manage
        # selections??? makes me want to put the smack on somebody.
        # note that all this malarkey is working on the assumption that
        # only entire rows or entire columns or single cells are selected.
        top_left = self._grid.GetSelectionBlockTopLeft()
        bottom_right = self._grid.GetSelectionBlockBottomRight()
        selection_mode = self._grid.GetSelectionMode()

        if selection_mode == wxGrid.wxGridSelectRows:
            # handle rows differently. figure out which rows were
            # selected. turns out that in this case, wx adds a "block"
            # per row, so we have to cycle over the list returned by
            # the GetSelectionBlock routines
            for i in range(len(top_left)):
                top_point = top_left[i]
                bottom_point = bottom_right[i]
                for row_index in range(top_point[0], bottom_point[0] + 1): 
                    rows.append(row_index)
        elif selection_mode == wxGrid.wxGridSelectColumns:
            # again, in this case we know that only whole columns can be
            # selected
            for i in range(len(top_left)):
                top_point = top_left[i]
                bottom_point = bottom_right[i]
                for col_index in range(top_point[1], bottom_point[1] + 1): 
                    cols.append(col_index)
        elif selection_mode == wxGrid.wxGridSelectCells:
            # this is the case where the selection_mode is cell, which also
            # allows complete columns or complete rows to be selected.

            # first find the size of the grid
            row_size = self.model.get_row_count()
            col_size = self.model.get_column_count()

            for i in range(len(top_left)):
                top_point = top_left[i]
                bottom_point = bottom_right[i]
                # precalculate whether this is a row or column select
                row_select = top_point[1] == 0 and \
                             bottom_point[1] == col_size - 1
                col_select = top_point[0] == 0 and \
                             bottom_point[0] == row_size - 1

                if row_select:
                    for row_index in range(top_point[0], bottom_point[0] + 1):
                        rows.append(row_index)
                if col_select:
                    for col_index in range(top_point[1], bottom_point[1] + 1):
                        cols.append(top_point[0])

        return rows, cols


    def __fire_selection_changed(self, sel):

        # we only fire the event if the new selection is different from the
        # old one
        if not self.__current_selection == sel:
            self.selection_changed = sel
            self.__current_selection = sel

        return

    def __autosize(self, on_resize=False):
        """ Autosize the grid with appropriate flags. """

        model = self.model
        grid  = self._grid
        if grid is not None and self.autosize and (not on_resize):
            grid.AutoSizeColumns(False)
            grid.AutoSizeRows(False)

        # whenever we size the grid we need to take in to account any
        # explicitly set row/column sizes
        grid.BeginBatch()
        
        if not self._user_col_size:
            dx = (grid.GetSizeTuple()[0] - 
                  wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X))
            for index in range(0, model.get_column_count()):
                size = model.get_column_size(index)
                if (size is not None) and (size != -1):
                    if 0.0 <= size <= 1.0:
                        size *= dx
                    grid.SetColSize(index, int(size))

        for index in range(0, model.get_row_count()):
            size = model.get_row_size(index)
            if size is not None and size != -1:
                grid.SetRowSize(index, size)

        grid.AdjustScrollbars()
        grid.EndBatch()
        grid.ForceRefresh()

        return

    def __resolve_grid_coords(self, x, y):
        """ Resolve the specified x and y coordinates into row/col
            coordinates. Returns row, col. """

        # the x,y coordinates here are Unscrolled coordinates.
        # They must be changed to scrolled coordinates.
        x, y = self._grid.CalcUnscrolledPosition(x, y)

        # now we need to get the row and column from the grid
        # but we need to first remove the RowLabel and ColumnLabel
        # bounding boxes
        if self.show_row_headers:
            x = x - self._grid.GetGridRowLabelWindow().GetRect().width

        if self.show_column_headers:
            y = y - self._grid.GetGridColLabelWindow().GetRect().height

        col = self._grid.XToCol(x)
        row = self._grid.YToRow(y)

        return row, col


class _GridTableBase(PyGridTableBase):
    """ A private adapter for the underlying wx grid implementation. """

    ###########################################################################
    # 'object' interface.
    ###########################################################################

    def __init__(self, model, grid):
        """ Creates a new table base. """
        
        # Base class constructor.
        PyGridTableBase.__init__(self)

        # The Pyface model that provides the data.
        self.model = model
        self._grid = grid

        # hacky state variables so we can identify when rows have been
        # added or deleted.
        self._row_count = -1
        self._col_count = -1

        # caches for editors and renderers
        self._editor_cache = {}
        self._renderer_cache = {}

        return

    def dispose(self):

        # make sure dispose gets called on all traits editors
        for editor in self._editor_cache.values():
            editor.dispose()

        for renderer in self._renderer_cache.values():
            renderer.dispose()

        self._clear_cache()

        return
        
    ###########################################################################
    # 'wxPyGridTableBase' interface.
    ###########################################################################

    def GetNumberRows(self):
        """ Return the number of rows in the model. """

        # because wx is such a wack job we have to store away the row
        # and column counts so we can figure out when rows or cols have
        # been appended or deleted. lacking a better place to do this
        # we just set the local variable every time GetNumberRows is called.
        self._row_count = self.model.get_row_count()
        return self._row_count

    def GetNumberCols(self):
        """ Return the number of columns in the model. """

        # see comment in GetNumberRows for logic here
        self._col_count = self.model.get_column_count()
        return self._col_count

    def IsEmptyCell(self, row, col):
        """ Is the specified cell empty? """

        return self.model.is_cell_empty(row, col)
    
    def GetValue(self, row, col):
        """ Get the value at the specified row and column. """

        return self.model.get_value(row, col)
    
    def SetValue(self, row, col, value):
        """ Set the value at the specified row and column. """
        return self.model.set_value(row, col, value)

    def GetRowLabelValue(self, row):
        """ Called when the grid needs to display a row label. """

        label = self.model.get_row_name(row)

        if row == self._grid._current_sorted_row:
            if self._grid._row_sort_reversed:
                if is_win32:
                    ulabel = unicode(label, 'ascii') + u'  \u00ab'
                    label  = ulabel.encode('latin-1')
                else:
                    label += '  <<'
            elif is_win32:
                ulabel = unicode(label, 'ascii') + u'  \u00bb'
                label  = ulabel.encode('latin-1')
            else:
                label += '  >>'

        return label

    def GetColLabelValue(self, col):
        """ Called when the grid needs to display a column label. """

        label = self.model.get_column_name(col)

        if col == self._grid._current_sorted_col:
            if self._grid._col_sort_reversed:
                if is_win32:
                    ulabel = unicode(label, 'ascii') + u'  \u00ab'
                    label  = ulabel.encode('latin-1')
                else:
                    label += '  <<'
            elif is_win32:
                ulabel = unicode(label, 'ascii') + u'  \u00bb'
                label  = ulabel.encode('latin-1')
            else:
                label += '  >>'

        return label

    def GetTypeName(self, row, col):
        """ Called to determine the kind of editor/renderer to use.

        This doesn't necessarily have to be the same type used natively by the
        editor/renderer if they know how to convert.

        """
        typename = None
        try:
            typename = self.model.get_type(row, col)
        except NotImplementedError:
            pass

        if typename == None:
            typename = GRID_VALUE_STRING

        return typename

    def DeleteRows(self, pos, num_rows):
        """ Called when the view is deleting rows. """

        # clear the cache
        self._clear_cache()
        return self.model.delete_rows(pos, num_rows)

    def InsertRows(self, pos, num_rows):
        """ Called when the view is inserting rows. """
        # clear the cache
        self._clear_cache()
        return self.model.insert_rows(pos, num_rows)

    def AppendRows(self, num_rows):
        """ Called when the view is inserting rows. """
        # clear the cache
        self._clear_cache()
        pos = self.model.get_row_count()
        return self.model.insert_rows(pos, num_rows)

    def DeleteCols(self, pos, num_cols):
        """ Called when the view is deleting columns. """

        # clear the cache
        self._clear_cache()
        return self.model.delete_columns(pos, num_cols)

    def InsertCols(self, pos, num_cols):
        """ Called when the view is inserting columns. """
        # clear the cache
        self._clear_cache()
        return self.model.insert_columns(pos, num_cols)

    def AppendCols(self, num_cols):
        """ Called when the view is inserting columns. """
        # clear the cache
        self._clear_cache()
        pos = self.model.get_column_count()
        return self.model.insert_columns(pos, num_cols)

    def GetAttr(self, row, col, kind):
        """ Retrieve the cell attribute object for the specified cell. """

        #result = PyGridTableBase.base_GetAttr(self, row, col, kind)
        result = None
        if result is None:
            result = GridCellAttr()
        # we only handle cell requests, for other delegate to the supa
        if kind != GridCellAttr.Cell and kind != GridCellAttr.Any:
            return result

        rows = self.model.get_row_count()
        cols = self.model.get_column_count()
        
        # first look in the cache for the editor
        editor = None
        if self._editor_cache.has_key((row, col)):
            editor = self._editor_cache[(row, col)]
        elif row >= rows or col >= cols:
            editor = DummyGridCellEditor()
        else:
            # ask the underlying model for an editor for this cell
            editor = self.model.get_cell_editor(row, col)
            if editor is not None:
                self._editor_cache[(row, col)] = editor

        # try to find a renderer for this cell
        renderer = None
        if row < rows and col < cols:
            renderer = self.model.get_cell_renderer(row, col)

        if editor is not None:
            # Note: we have to increment the reference to keep the
            #       underlying code from destroying our object.
            # fixme: where should this be decremented? as is, i think the
            #        object hangs around forever? or perhaps the garbage
            #        collection will get it anyway?
            editor.IncRef()
            result.SetEditor(editor)

        if renderer is not None and renderer.renderer is not None:
            renderer.renderer.IncRef()
            result.SetRenderer(renderer.renderer)

        # look to see if this cell is editable
        read_only = False
        if row < rows and col < cols:
            read_only = self.model.is_cell_read_only(row, col) or \
                        self.model.is_row_read_only(row) or \
                        self.model.is_column_read_only(col)

        if read_only:
            result.SetReadOnly(True)
        else:
            result.SetReadOnly(False)
        read_only_color = self._grid.default_cell_read_only_color
        if read_only and read_only_color is not None:
            result.SetBackgroundColour(read_only_color)

        # check to see if colors or fonts are specified for this cell
        bgcolor = None
        if row < rows and col < cols:
            bgcolor = self.model.get_cell_bg_color(row, col)
        else:
            bgcolor = self._grid.default_cell_bg_color

        if bgcolor is not None:
            result.SetBackgroundColour(bgcolor)

        text_color = None
        if row < rows and col < cols:
            text_color = self.model.get_cell_text_color(row, col)
        else:
            text_color = self._grid.default_cell_text_color
        if text_color is not None:
            result.SetTextColour(text_color)

        cell_font = None
        if row < rows and col < cols:
            cell_font = self.model.get_cell_font(row, col)
        else:
            cell_font = self._grid.default_cell_font
        if cell_font is not None:
            result.SetFont(cell_font)

        # check for alignment definition for this cell
        halignment = valignment = None
        if row < rows and col < cols:
            halignment = self.model.get_cell_halignment(row, col)
            valignment = self.model.get_cell_valignment(row, col)
        if halignment is not None and valignment is not None:
            if halignment == 'center':
                h = wx.ALIGN_CENTRE
            elif halignment == 'right':
                h = wx.ALIGN_RIGHT
            else:
                h = wx.ALIGN_LEFT

            if valignment == 'top':
                v = wx.ALIGN_TOP
            elif valignment == 'bottom':
                v = wx.ALIGN_BOTTOM
            else:
                v = wx.ALIGN_CENTRE
                
            result.SetAlignment(h, v)
        
        return result

    ###########################################################################
    # private interface.
    ###########################################################################
    def _clear_cache(self):
        """ Clean out the editor/renderer cache. """
        
        # Dispose of the editors in the cache after a brief delay, so as
        # to allow completion of the current event.
        for editor in self._editor_cache.values():
            do_later(editor.dispose)

        self._editor_cache = {}
        self._renderer_cache = {}
        return

from wx.grid import PyGridCellEditor
class DummyGridCellEditor(PyGridCellEditor):

    def Show(self, show, attr):
        return

#### EOF ######################################################################
