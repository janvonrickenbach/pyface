#-------------------------------------------------------------------------------
#
#  Pyface 'DockSizer' support.
#
#  This package implements the sizer associated with a Pyface DockWindow
#  component. The sizer manages the layout of the DockWindow child controls and
#  the notebook tabs and dragbars associated with the DockWindow.
#
#  Written by: David C. Morrill
#
#  Date: 10/18/2005
#
#  (c) Copyright 2005 by Enthought, Inc.
#
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#  Imports:
#-------------------------------------------------------------------------------

import wx

from enthought.traits.api \
    import HasPrivateTraits, Instance, Str, Int, List, Enum, Tuple, Any, \
           Range, Property, Callable, Constant, Event, Undefined, true, false

from enthought.pyface.image_resource \
    import ImageResource

from enthought.util.wx.drag_and_drop \
    import PythonDropSource

from enthought.util.wx.do_later \
    import do_later, do_after

from idockable \
    import IDockable
    
from ifeature_tool \
    import IFeatureTool
    
# Define version dependent values:  
wx_26 = (wx.__version__[:3] == '2.6') 

#-------------------------------------------------------------------------------
#  Constants:
#-------------------------------------------------------------------------------

# Maximum allowed length of a tab label:
MaxTabLength = 30

# Size of a drag bar (in pixels):
DragBarSize = 14

# Images sizes (in pixels):
CloseTabSize  = 10
CloseDragSize = 7

# Height of a notebook tab (in pixels):
TabHeight = 26

# Width of a notebook tab's margin (in pixels):
TabMargin = 8

# Tab drawing states:
TabInactive = 0
TabActive   = 1
TabHover    = 2

# Notebook margin and padding sizes:
NBMarginLeft   = 7
NBMarginRight  = 9
NBMarginTop    = 3
NBMarginBottom = 9
NBPadding      = 4

# Size of a splitter bar:
SplitterSizeH = 9
SplitterSizeV = 12

# Size of a docking marker bar:
DockBarSize = 6

# Normal background color:
BGColor = None # ( 236, 233, 216 )    # wx.SYS_COLOUR_BTNFACE

# Feature overlay colors:
FeatureBrushColor = ( 255, 255, 255 )
FeaturePenColor   = (  92,  92,  92 )

# Colors used to draw a grab bar:
DragLightColor = ( 255, 255, 255 )    # wx.SYS_COLOUR_WINDOW
DragDarkColor  = ( 172, 168, 153 )    # wx.SYS_COLOUR_BTNSHADOW

# Colors used to draw a notebook:
NBBGColor       = ( 252, 252, 254 )   # wx.SYS_COLOUR_MENU
NBBGTabAColor   = ( 252, 252, 254 )   # wx.SYS_COLOUR_MENU
NBBGTabXColor   = ( 255, 199,  60 )
NBBGTabIColor   = ( 246, 246, 243 )   # wx.SYS_COLOUR_MENU
NBEdgeTabAColor = ( 145, 155, 156 )
NBEdgeTabXColor = ( 230, 139,  44 )
NBEdgeTabIColor = ( 145, 155, 156 )
NBEdgeColor     = ( 145, 155, 156 )   # wx.SYS_COLOUR_BTNSHADOW
NBShadow1Color  = ( 208, 206, 191 )   # wx.SYS_COLOUR_3DDKSHADOW
NBShadow2Color  = ( 227, 224, 208 )   # wx.SYS_COLOUR_3DDKSHADOW

# Color used to update the screen while dragging a splitter bar:
DragColor = ( 96, 96, 96 )

# Color used to update the screen while showing a docking operation in progress:
DockColor = ( 32, 255, 255 )

# Color used to mark the DockWindow boundary while dragging:
MarkColor = ( 255, 255, 0 )

# Drop Info kinds:
DOCK_TOP      = 0
DOCK_BOTTOM   = 1
DOCK_LEFT     = 2
DOCK_RIGHT    = 3
DOCK_TAB      = 4
DOCK_TABADD   = 5
DOCK_BAR      = 6
DOCK_NONE     = 7
DOCK_SPLITTER = 8
DOCK_EXPORT   = 9

# Splitter states:
SPLIT_VLEFT   = 0
SPLIT_VMIDDLE = 1
SPLIT_VRIGHT  = 2
SPLIT_HTOP    = 3
SPLIT_HMIDDLE = 4
SPLIT_HBOTTOM = 5

# Empty clipping area:
no_clip = ( 0, 0, 0, 0 )

# Valid sequence types:
SequenceType = ( list, tuple )

# Tab scrolling directions:
SCROLL_LEFT  = 1
SCROLL_RIGHT = 2
SCROLL_TO    = 3

# Feature modes:
FEATURE_NONE          = -1  # Has no features
FEATURE_NORMAL        = 0   # Has normal features
FEATURE_CHANGED       = 1   # Has changed or new features
FEATURE_DROP          = 2   # Has drag data compatible drop features
FEATURE_DISABLED      = 3   # Has feature icon, but is currently disabled
FEATURE_VISIBLE       = 4   # Has visible features (mouseover mode)
FEATURE_DROP_VISIBLE  = 5   # Has visible drop features (mouseover mode)
FEATURE_PRE_NORMAL    = 6   # Has normal features (but has not been drawn yet)
FEATURE_EXTERNAL_DRAG = 256 # A drag started in another DockWindow is active 

# Feature sets:
NO_FEATURE_ICON  = ( FEATURE_NONE, FEATURE_DISABLED, FEATURE_VISIBLE,
                     FEATURE_DROP_VISIBLE )
FEATURES_VISIBLE = ( FEATURE_VISIBLE, FEATURE_DROP_VISIBLE )
FEATURE_END_DROP = ( FEATURE_DROP, FEATURE_VISIBLE, FEATURE_DROP_VISIBLE )
NORMAL_FEATURES  = ( FEATURE_NORMAL, FEATURE_DISABLED ) 

#-------------------------------------------------------------------------------
#  Global data:
#-------------------------------------------------------------------------------

# Standard font used by the DockWindow:
standard_font = None

# The list of available DockWindowFeatures:
features = []

#-------------------------------------------------------------------------------
#  Trait definitions:
#-------------------------------------------------------------------------------

# Bounds (i.e. x, y, dx, dy):
Bounds = Tuple( Int, Int, Int, Int )

# Docking drag bar style:
DockStyle = Enum( 'horizontal', 'vertical', 'tab', 'fixed' )

#-------------------------------------------------------------------------------
#  Returns an (R, G, B) tuple for a specified wxPython system colour:
#-------------------------------------------------------------------------------

def color_tuple_for ( id ):
    """ Returns an (R, G, B) tuple for a specified wxPython system colour.
    """
    color = wx.SystemSettings_GetColour( id )
    return ( color.Red(), color.Green(), color.Blue() )

def init_dock_sizer():
    # Initialize the various colors (after the toolkit has been intialised):
    global BGColor;        BGColor        = color_tuple_for( wx.SYS_COLOUR_BTNFACE )
    global DragLightColor; DragLightColor = color_tuple_for( wx.SYS_COLOUR_WINDOW )
    global DragDarkColor;  DragDarkColor  = color_tuple_for( wx.SYS_COLOUR_BTNSHADOW )
    global NBEdgeColor;    NBEdgeColor    = color_tuple_for( wx.SYS_COLOUR_BTNSHADOW )
    global NBBGColor;      NBBGColor      = color_tuple_for( wx.SYS_COLOUR_MENU )
    global NBBGTabAColor;  NBBGTabAColor  = color_tuple_for( wx.SYS_COLOUR_MENU )
    global NBBGTabIColor;  NBBGTabIColor  = color_tuple_for( wx.SYS_COLOUR_MENU )
    global NBShadow1Color; NBShadow1Color = color_tuple_for( wx.SYS_COLOUR_BTNSHADOW )
    global NBShadow2Color; NBShadow2Color = color_tuple_for( wx.SYS_COLOUR_3DLIGHT )

#-------------------------------------------------------------------------------
#  Adds a new DockWindowFeature class to the list of available features:
#-------------------------------------------------------------------------------

def add_feature ( feature_class ):
    """ Adds a new DockWindowFeature class to the list of available features.
    """
    global features

    result = (feature_class not in features)
    if result:
        features.append( feature_class )

        # Mark the feature class as having been installed:
        if feature_class.state == 0:
            feature_class.state = 1

    return result

#-------------------------------------------------------------------------------
#  Sets the standard font to use for a specified device context:
#-------------------------------------------------------------------------------

def set_standard_font ( dc ):
    """ Sets the standard font to use for a specified device context.
    """
    global standard_font

    if standard_font is None:
        standard_font = wx.SystemSettings_GetFont( wx.SYS_DEFAULT_GUI_FONT )

    dc.SetFont( standard_font )

    return dc

#-------------------------------------------------------------------------------
#  Clears a window to the standard background color:
#-------------------------------------------------------------------------------

def clear_window ( window ):
    """ Clears a window to the standard background color.
    """
    dx, dy = window.GetSizeTuple()
    dc     = wx.PaintDC( window )
    dc.SetBrush( wx.Brush( wx.Colour( *BGColor ), wx.SOLID ) )
    dc.SetPen( wx.TRANSPARENT_PEN )
    dc.DrawRectangle( 0, 0, dx, dy )

#-------------------------------------------------------------------------------
#  'DockImages' class:
#-------------------------------------------------------------------------------

class DockImages ( HasPrivateTraits ):

    #---------------------------------------------------------------------------
    #  Trait definitions:
    #---------------------------------------------------------------------------

    # Image for closing a tab:
    close_tab = Instance( ImageResource, ImageResource( 'close_tab' ) )

    # Image for closing a drag bar:
    close_drag = Instance( ImageResource, ImageResource( 'close_drag' ) )

    #---------------------------------------------------------------------------
    #  Initalizes the object:
    #---------------------------------------------------------------------------

    def __init__ ( self, **traits ):
        """ Initializes the object.
        """
        super( DockImages, self ).__init__( **traits )

        self._lazy_init_done = False

    def _lazy_init ( self ):
        """ Initializes the parts of the object that depend on the toolkit
        selection.
        """

        # See if it has already been done.
        if self._lazy_init_done:
            return

        self._lazy_init_done = True

        self._close_tab  = self.close_tab.create_image().ConvertToBitmap()
        self._close_drag = self.close_drag.create_image().ConvertToBitmap()

        self._splitter_images = [
            ImageResource( name ).create_image().ConvertToBitmap()
            for name in [ 'sv_left', 'sv_middle', 'sv_right',
                          'sh_top',  'sh_middle', 'sh_bottom' ]
        ]

        self._tab_scroller_images = [
            ImageResource( name ).create_image().ConvertToBitmap()
            for name in [ 'tab_scroll_l', 'tab_scroll_r', 'tab_scroll_lr' ]
        ]
        self._tab_scroller_dx = self._tab_scroller_images[0].GetWidth()
        self._tab_scroller_dy = self._tab_scroller_images[0].GetHeight()

        self._feature_images = [
            ImageResource( name ).create_image().ConvertToBitmap()
            for name in [ 'tab_feature_normal',  'tab_feature_changed', 
                          'tab_feature_drop',    'tab_feature_disabled',
                          'bar_feature_normal',  'bar_feature_changed',
                          'bar_feature_drop',    'bar_feature_disabled' ]
        ]
        
        self._tab_feature_width  = self._feature_images[0].GetWidth()
        self._tab_feature_height = self._feature_images[0].GetHeight()
        self._bar_feature_width  = self._feature_images[3].GetWidth()
        self._bar_feature_height = self._feature_images[3].GetHeight()

    #---------------------------------------------------------------------------
    #  Returns the splitter image to use for a specified splitter state:
    #---------------------------------------------------------------------------

    def get_splitter_image ( self, state ):
        """ Returns the splitter image to use for a specified splitter state.
        """
        self._lazy_init()

        return self._splitter_images[ state ]
        
    #---------------------------------------------------------------------------
    #  Returns the feature image to use for a specified feature state:
    #---------------------------------------------------------------------------

    def get_feature_image ( self, state, is_tab = True ):
        """ Returns the feature image to use for a specified feature state.
        """
        self._lazy_init()

        if is_tab:
            return self._feature_images[ state ]
        return self._feature_images[ state + 3 ]

# Creates a singleton instance of the class:
DockImages = DockImages()

#-------------------------------------------------------------------------------
#  'DockItem' class:
#-------------------------------------------------------------------------------

class DockItem ( HasPrivateTraits ):

    #---------------------------------------------------------------------------
    #  Trait definitions:
    #---------------------------------------------------------------------------

    # The parent of this item:
    parent = Any

    # Bounds of the item:
    bounds = Bounds

    # Current width of the item:
    width = Int( -1 )

    # Current height of the item:
    height = Int( -1 )

    # Bounds of the item's drag bar or tab:
    drag_bounds = Bounds

    # The tab displayable version of the control's UI name:
    tab_name = Property

    # Width of the item's tab:
    tab_width = Property
    
    # The current feature mode:
    feature_mode = Enum( FEATURE_NONE, FEATURE_NORMAL, FEATURE_CHANGED,
                         FEATURE_DROP, FEATURE_VISIBLE, FEATURE_DROP_VISIBLE,
                         FEATURE_DISABLED, FEATURE_PRE_NORMAL )
    
    # The position where the feature popup should appear:
    feature_popup_position = Property

    # The list of features for this item:
    features = List
    
    # The list of drag data compatible drop features for this item:
    drop_features = List
    
    # Current active set of features:
    active_features = Property

    # The name of this item (implemented in subclasses):
    # name = Str

    # The control associated with this item (implemented in subclasses):
    # control = Instance( wx.Control )

    #---------------------------------------------------------------------------
    #  Implementation of the 'tab_name' property:
    #---------------------------------------------------------------------------

    def _get_tab_name ( self ):
        if self._tab_name is None:
            name = self.name
            if len( name ) > MaxTabLength:
                name = '%s...%s' % ( name[ : MaxTabLength - 23 ], name[ -20: ] )
            self._tab_name = name

        return self._tab_name

    #---------------------------------------------------------------------------
    #  Implementation of the 'tab_width' property:
    #---------------------------------------------------------------------------

    def _get_tab_width ( self ):
        if self._tab_width is None:
            if self.control is None:
                return 0

            self._is_tab = True
            tw = fw = 0
            
            # Add feature marker width:
            if self.feature_mode != FEATURE_NONE:
                tw = DockImages._tab_feature_width + 3
                
            # Add text and margin width:
            dc  = set_standard_font( wx.ClientDC( self.control ) )
            tw += (dc.GetTextExtent( self.tab_name )[0] + (2 * TabMargin))

            # Add custom image width:
            image = self.get_image()
            if image is not None:
                tw += (image.GetWidth() + 3)

            # Add close button width:
            if self.closeable:
                tw += (CloseTabSize + 6)

            # Save the width:
            self._tab_width = tw

        return self._tab_width

    #---------------------------------------------------------------------------
    #  Implementation of the 'active_features' property:
    #---------------------------------------------------------------------------

    def _get_active_features ( self ):
        if len( self.drop_features ) > 0:
            return self.drop_features
        return self.features
        
    #---------------------------------------------------------------------------
    #  Implementation of the 'feature_popup_position' property:
    #---------------------------------------------------------------------------
    
    def _get_feature_popup_position ( self ):
        x, y, dx, dy = self.drag_bounds
        return wx.Point( x + 5, y + 3 )

    #---------------------------------------------------------------------------
    #  Returns whether or not the item is at a specified window position:
    #---------------------------------------------------------------------------

    def is_at ( self, x, y, bounds = None ):
        """ Returns whether or not the item is at a specified window position.
        """
        if bounds is None:
            bounds = self.bounds
        bx, by, bdx, bdy = bounds
        return ((bx <= x < (bx + bdx)) and (by <= y < (by + bdy)))

    #---------------------------------------------------------------------------
    #  Returns whether or not an event is within a specified bounds:
    #---------------------------------------------------------------------------

    def is_in ( self, event, x, y, dx, dy ):
        """ Returns whether or not an event is within a specified bounds.
        """
        return ((x <= event.GetX() < (x + dx)) and
                (y <= event.GetY() < (y + dy)))

    #---------------------------------------------------------------------------
    #  Sets the control's drag bounds:
    #---------------------------------------------------------------------------

    def set_drag_bounds ( self, x, y, dx, dy ):
        """ Sets the control's drag bounds.
        """
        bx, by, bdx, bdy = self.bounds
        self.drag_bounds = ( x, y, min( x + dx, bx + bdx ) - x,
                                   min( y + dy, by + bdy ) - y )

    #---------------------------------------------------------------------------
    #  Gets the cursor to use when the mouse is over the item:
    #---------------------------------------------------------------------------

    def get_cursor ( self, event ):
        """ Gets the cursor to use when the mouse is over the item.
        """
        if self._is_tab or self._is_in_close( event ):
            return wx.CURSOR_ARROW
        return wx.CURSOR_HAND

    #---------------------------------------------------------------------------
    #  Gets the DockInfo object for a specified window position:
    #---------------------------------------------------------------------------

    def dock_info_at ( self, x, y, size, is_control ):
        """ Gets the DockInfo object for a specified window position.
        """
        if self.is_at( x, y, self.drag_bounds ):
            x, y, dx, dy     = self.drag_bounds
            cx, cy, cdx, cdy = self.bounds
            mdx, mdy, tdx    = size
            control          = self
            if self._is_tab:
                if is_control:
                    kind   = DOCK_TABADD
                    bounds = ( cx - NBPadding, cy - NBPadding,
                               cdx + 2 * NBPadding,
                               min( mdy, cdy + 2 * NBPadding ) )
                    tab_bounds = ( x, y + 5, dx, dy - 5 )
                else:
                    kind   = DOCK_TAB
                    bounds = ( cx - NBPadding, cy - NBPadding,
                               cdx + 2 * NBPadding, cdy + 2 * NBPadding )
                    tab_bounds = ( x - (tdx / 2), y + 5, tdx, TabHeight - 5 )
            else:
                if is_control:
                    kind   = DOCK_TABADD
                    bounds = ( cx, y + TabHeight, cdx,
                               min( mdy, cdy + DragBarSize - TabHeight + 5 ) )
                    tab_bounds = ( x, y, self.tab_width, TabHeight - 5 )
                else:
                    kind    = DOCK_TAB
                    control = None
                    bounds  = ( cx, y + TabHeight, cdx,
                                cdy + DragBarSize - TabHeight + 5 )
                    tab_bounds = ( x + self.tab_width, y, tdx, TabHeight - 5 )

            return DockInfo( kind       = kind,
                             bounds     = bounds,
                             tab_bounds = tab_bounds,
                             region     = self.parent,
                             control    = control )

        return None

    #---------------------------------------------------------------------------
    #  Prepares for drawing into a device context:
    #---------------------------------------------------------------------------

    def begin_draw ( self, dc, ox = 0, oy = 0 ):
        """ Prepares for drawing into a device context.
        """
        self._save_clip = dc.GetClippingBox()
        x, y, dx, dy    = self.bounds
        dc.SetClippingRegion( x + ox, y + oy, dx, dy )

    #---------------------------------------------------------------------------
    #  Terminates drawing into a device context:
    #---------------------------------------------------------------------------

    def end_draw ( self, dc ):
        """ Terminates drawing into a device context.
        """
        dc.DestroyClippingRegion()
        if self._save_clip != no_clip:
            dc.SetClippingRegion( *self._save_clip )
        self._save_clip = None

    #---------------------------------------------------------------------------
    #  Handles the left mouse button being pressed:
    #---------------------------------------------------------------------------

    def mouse_down ( self, event ):
        """ Handles the left mouse button being pressed.
        """
        self._xy       = ( event.GetX(), event.GetY() )
        self._closing  = self._is_in_close( event )
        self._dragging = False

    #---------------------------------------------------------------------------
    #  Handles the left mouse button being released:
    #---------------------------------------------------------------------------

    def mouse_up ( self, event ):
        """ Handles the left mouse button being released.
        """
        # Handle the user closing a control:
        if self._closing:
            if self._is_in_close( event ):
                self.close()

        # Handle the completion of a dragging operation:
        elif self._dragging:
            window    = event.GetEventObject()
            dock_info = self._dock_info
            dock_info.draw( window )
            self.mark_bounds()
            self._dock_info = None
            control = self

            # Check to see if the user is attempting to drag an entire notebook
            # region:
            if event.AltDown():
                control = self.parent
                # If the parent is not a notebook, then use the parent's parent:
                if (isinstance( control, DockRegion ) and
                    (not control.is_notebook)):
                    control = control.parent

                # Make sure the target is not contained within the notebook
                # group we are trying to move:
                region = dock_info.region
                while region is not None:
                    if region is control:
                        # If it is, the operation is invalid, abort:
                        return
                    region = region.parent

            # Check to see if the user is attempting to copy the control:
            elif event.ControlDown():
                owner   = window.owner
                control = owner.handler.dock_control_for(
                                *(owner.handler_args + ( window, control )) )

            # Complete the docking maneuver:
            dock_info.dock( control, window )

        # Handle the user clicking on a notebook tab to select it:
        elif (self._is_tab and
              self.is_at( event.GetX(), event.GetY(), self.drag_bounds )):
            self.parent.tab_clicked( self )

    #---------------------------------------------------------------------------
    #  Handles the mouse moving while the left mouse button is pressed:
    #---------------------------------------------------------------------------

    def mouse_move ( self, event ):
        """ Handles the mouse moving while the left mouse button is pressed.
        """
        # Exit if control is 'fixed' or a 'close' is pending:
        if self._closing or self.locked or (self.style == 'fixed'):
            return

        window = event.GetEventObject()

        # Check to see if we are in 'drag mode' yet:
        if not self._dragging:
            x, y = self._xy
            if (abs( x - event.GetX() ) + abs( y - event.GetY() )) < 3:
                return

            self._dragging  = True
            self._dock_info = no_dock_info
            self._dock_size = self.calc_min() + ( self.tab_width, )
            self.mark_bounds()

        # Get the window and DockInfo object associated with the event:
        cur_dock_info   = self._dock_info
        self._dock_info = dock_info = \
            window.GetSizer().DockInfoAt( event.GetX(), event.GetY(),
                                          self._dock_size, event.ShiftDown() )

        # If the DockInfo has not changed, then no update is needed:
        if ((cur_dock_info.kind == dock_info.kind)     and
            (cur_dock_info.region is dock_info.region) and
            (cur_dock_info.bounds == dock_info.bounds) and
            (cur_dock_info.tab_bounds == dock_info.tab_bounds)):
            return

        # Erase the old region:
        cur_dock_info.draw( window )

        # Make sure the new DockInfo is legal:
        region = self.parent
        if ((not event.ControlDown())    and
            (dock_info.region is region) and
            ((len( region.contents ) <= 1) or
             (DOCK_TAB <= dock_info.kind <= DOCK_BAR) and
             (dock_info.control is self))):
            self._dock_info = no_dock_info
            window.owner.set_cursor( wx.CURSOR_SIZING )
            return

        # Draw the new region:
        dock_info.draw( window )

        # If this is the start of an export (i.e. drag and drop) request:
        if ((dock_info.kind == DOCK_EXPORT) and
            (self.export != '')             and
            (self.dockable is not None)):

            # Begin the drag and drop operation:
            self.mark_bounds()
            window.owner.set_cursor( wx.CURSOR_ARROW )
            window.owner.release_mouse()
            try:
                window._dragging = True
                if (PythonDropSource( window, self ).result in 
                    ( wx.DragNone, wx.DragCancel )):
                    window.owner.handler.open_view_for( self )
            finally:
                window._dragging = False
        else:
            # Update the mouse pointer as required:
            cursor = wx.CURSOR_SIZING
            if dock_info.kind == DOCK_BAR:
                cursor = wx.CURSOR_HAND
            window.owner.set_cursor( cursor )

    #---------------------------------------------------------------------------
    #  Handles the mouse hovering over the item:
    #---------------------------------------------------------------------------

    def hover_enter ( self, event ):
        """ Handles the mouse hovering over the item.
        """
        if self._is_tab and (self._state != TabActive):
            self._redraw_tab( TabHover )

    #---------------------------------------------------------------------------
    #  Handles the mouse exiting from hovering over the item:
    #---------------------------------------------------------------------------

    def hover_exit ( self, event ):
        """ Handles the mouse exiting from hovering over the item.
        """
        if self._is_tab and (self._state != TabActive):
            self._redraw_tab( TabInactive )

    #---------------------------------------------------------------------------
    #  Marks/Unmarks the bounds of the bounding DockWindow:
    #---------------------------------------------------------------------------

    def mark_bounds ( self ):
        """ Marks/Unmarks the bounds of the bounding DockWindow.
        """
        dc = wx.ScreenDC()
        dc.SetLogicalFunction( wx.XOR )
        dc.SetBrush( wx.TRANSPARENT_BRUSH )
        dc.SetPen( wx.Pen( wx.Colour( *MarkColor ), 3, wx.SOLID ) )
        window = self.control.GetParent()
        dx, dy = window.GetSize()
        x, y   = window.ClientToScreenXY( 0, 0 )
        dc.DrawRectangle( x - 3, y - 3, dx + 6, dy + 6 )

    #---------------------------------------------------------------------------
    #  Draws a notebook tab:
    #---------------------------------------------------------------------------

    def draw_tab ( self, dc, state, ox = 0, oy = 0 ):
        """ Draws a notebook tab.
        """
        self._is_tab   = True
        self._state    = state
        x, y, dx, dy   = self.drag_bounds
        x             += ox
        y             += oy
        yb = yb1       = y + TabHeight
        y             += 3
        dy            -= 3
        tx             = 8
        tw             = self.tab_width
        name           = self.tab_name
        image          = self.get_image()
        tdx            = dc.GetTextExtent( name )[0]
        fill_color     = NBBGTabAColor
        edge_color     = NBEdgeTabAColor
        top_fill_color = NBBGTabXColor
        top_edge_color = NBEdgeTabXColor

        if state != TabActive:
            tx   = 6
            x   += 2
            dx  -= 4
            y   += 2
            dy  -= 3
            yb1 -= 1
            tw  -= 4
            fill_color = NBBGTabIColor
            edge_color = NBEdgeTabIColor
            if state == TabInactive:
                top_fill_color = fill_color
                top_edge_color = edge_color

        mode = self.feature_mode
        if mode == FEATURE_PRE_NORMAL:
            mode = self.set_feature_mode( False )
            
        xr = x + tw + 1

        # Fill the bottom:
        dc.SetPen( wx.TRANSPARENT_PEN )
        dc.SetBrush( wx.Brush( wx.Colour( *fill_color ), wx.SOLID ) )
        dc.DrawRectangle( x + 1, y + 3, xr - x - 1, yb1 - y - 3 )

        # Fill the top:
        dc.SetBrush( wx.Brush( wx.Colour( *top_fill_color ), wx.SOLID ) )
        dc.DrawRectangle( x + 1, y + 1, xr - x - 1, 2 )

        # Draw the side edges:
        dc.SetPen( wx.Pen( wx.Colour( *edge_color ), 1, wx.SOLID ) )
        dc.DrawLine( x, y + 3, x, yb )
        dc.DrawLine( xr, y + 3, xr, yb )

        # Draw the top edges:
        dc.SetPen( wx.Pen( wx.Colour( *top_edge_color ), 1, wx.SOLID ) )
        dc.DrawLine( x, y + 2, x + 2, y )
        dc.DrawLine( xr, y + 2, xr - 2, y )
        dc.DrawLine( x + 2, y, xr - 1, y )

        # Initialize the starting point:
        ix = fx = x + tx + 1

        # Draw the feature 'trigger' icon (if necessary):
        if mode != FEATURE_NONE:
            if mode not in FEATURES_VISIBLE:
                dc.DrawBitmap( DockImages.get_feature_image( mode ), ix, y + 3, 
                               True )
            ix += (DockImages._tab_feature_width + 3)

        # Draw the image (if necessary):
        if image is not None:
            dc.DrawBitmap( image, ix, y + 3, True )
            ix += (image.GetWidth() + 3)

        # Draw the text label:
        dc.DrawText( name, ix, y + 4 )

        # Draw the close button (if necessary):
        if self.closeable:
            dc.DrawBitmap( DockImages._close_tab, ix + tdx + 6, y + 6 )

    #---------------------------------------------------------------------------
    #  Draws a fixed drag bar:
    #---------------------------------------------------------------------------

    def draw_fixed ( self, dc ):
        """ Draws a fixed drag bar.
        """
        pass

    #---------------------------------------------------------------------------
    #  Draws a horizontal drag bar:
    #---------------------------------------------------------------------------

    def draw_horizontal ( self, dc ):
        """ Draws a horizontal drag bar.
        """
        x, y, dx, dy = self.drag_bounds
        self._draw_bar( dc, x + 4, y + 4, dx - 8, 3, 0, 4 )
        x += 10
        fx = x

        # Draw the feature 'trigger' icon (if necessary):
        mode = self.feature_mode
        if mode == FEATURE_PRE_NORMAL:
            mode = self.set_feature_mode( False )
        if mode != FEATURE_NONE:
            if mode not in FEATURES_VISIBLE:
                dc.DrawBitmap( DockImages.get_feature_image( mode, False ), 
                               x, y + 4, True )
            x += (DockImages._bar_feature_width + 6)

        # Draw the close button (if necessary):
        if self.closeable:
            dc.DrawBitmap( DockImages._close_drag, x, y + 4 )

    #---------------------------------------------------------------------------
    #  Draws a vertical drag bar:
    #---------------------------------------------------------------------------

    def draw_vertical ( self, dc ):
        """ Draws a vertical drag bar.
        """
        x, y, dx, dy = self.drag_bounds
        self._draw_bar( dc, x + 4, y + 4, 3, dy - 8, 4, 0 )
        y += 10
        fy = y

        # Draw the feature 'trigger' icon (if necessary):
        mode = self.feature_mode
        if mode == FEATURE_PRE_NORMAL:
            mode = self.set_feature_mode( False )
        if mode != FEATURE_NONE:
            if mode not in FEATURES_VISIBLE:
                dc.DrawBitmap( DockImages.get_feature_image( mode, False ), 
                               x + 4, y, True )
            y += (DockImages._bar_feature_height + 6)

        # Draw the close button (if necessary):
        if self.closeable:
            dc.DrawBitmap( DockImages._close_drag, x + 4, y )
                    
    #---------------------------------------------------------------------------
    #  Redraws the control's tab:
    #---------------------------------------------------------------------------
    
    def _redraw_tab ( self, state = None ):
        if state is None:
            state = self._state
        region = self.parent
        if region is not None:
            dc = set_standard_font( wx.ClientDC( self.control.GetParent() ) )
            if region.is_notebook:
                dc.SetClippingRegion( *region._tab_clip_bounds )
                self.draw_tab( dc, state )
                dc.DestroyClippingRegion()
            else:
                self.draw_tab( dc, state )
                
    #---------------------------------------------------------------------------
    #  Redraws the control's drag bar:  
    #---------------------------------------------------------------------------
    
    def _redraw_bar ( self ):
        dc = wx.ClientDC( self.control )
        getattr( self, 'draw_' + self.style )( dc )
        
    #---------------------------------------------------------------------------
    #  Redraws the control's tab or bar:
    #---------------------------------------------------------------------------
    
    def _redraw_control ( self ):
        if self._is_tab:
            self._redraw_tab()
        else:
            self._redraw_bar()

    #---------------------------------------------------------------------------
    #  Draws a horizontal/vertical drag bar:
    #---------------------------------------------------------------------------

    def _draw_bar ( self, dc, x, y, dx, dy, ndx, ndy ):
        """ Draws a horizontal/vertical drag bar.
        """
        self._is_tab = False
        x2           = x + ndx
        y2           = y + ndy

        # Fill the background of the drag bar:
        dc.SetBrush( wx.Brush( wx.Colour( *BGColor ), wx.SOLID ) )
        dc.SetPen( wx.TRANSPARENT_PEN )
        dc.DrawRectangle( *self.drag_bounds )

        # Draw the light portions of both bars:
        dc.SetPen( wx.Pen( wx.Colour( *DragLightColor ), 1, wx.SOLID ) )
        dc.DrawLine( x, y, x + dx - 1, y )
        dc.DrawLine( x, y + 1, x, y + dy - 1 )
        dc.DrawLine( x2, y2, x2 + dx - 1, y2 )
        dc.DrawLine( x2, y2 + 1, x2, y2 + dy - 1 )

        # Draw the dark portions of both bars:
        dc.SetPen( wx.Pen( wx.Colour( *DragDarkColor ), 1, wx.SOLID ) )
        dc.DrawLine( x, y + dy - 1, x + dx, y + dy - 1 )
        dc.DrawLine( x + dx - 1, y, x + dx - 1, y + dy - 1 )
        dc.DrawLine( x2, y2 + dy - 1, x2 + dx, y2 + dy - 1 )
        dc.DrawLine( x2 + dx - 1, y2, x2 + dx - 1, y2 + dy - 1 )

    #---------------------------------------------------------------------------
    #  Returns the bounds of the close button (if any):
    #---------------------------------------------------------------------------

    def _close_bounds ( self ):
        if self.closeable:
            x, y, dx, dy = self.drag_bounds
            if self._is_tab:
                return ( x + dx - 7 - CloseTabSize, y + 6,
                         CloseTabSize, CloseTabSize )
            elif self.style == 'horizontal':
                return ( x + DockImages._bar_feature_width + 10, y + 4,
                         CloseDragSize, CloseDragSize )
            return ( x + 4, y + DockImages._bar_feature_height + 10,
                     CloseDragSize, CloseDragSize )

        return ( 0, 0, 0, 0 )

    #---------------------------------------------------------------------------
    #  Returns whether a specified window position is over the close button:
    #---------------------------------------------------------------------------

    def _is_in_close ( self, event ):
        return self.is_in( event, *self._close_bounds() )

    #---------------------------------------------------------------------------
    #  Sets/Returns the 'normal' feature mode for the control based on the
    #  number of currently active features:
    #---------------------------------------------------------------------------
    
    def set_feature_mode ( self, changed = True ):
        if (not changed) or (self.feature_mode != FEATURE_PRE_NORMAL):
            mode     = FEATURE_DROP
            features = self.drop_features
            if len( features ) == 0:
                mode     = FEATURE_NORMAL
                features = self.features
            for feature in features:
                if feature.bitmap is not None:
                    if changed:
                        self.feature_mode = FEATURE_CHANGED
                    else:
                        self.feature_mode = mode
                    break
            else:
                self.feature_mode = FEATURE_DISABLED
            
        return self.feature_mode
    
    #---------------------------------------------------------------------------
    #  Returns whether or not a specified window position is over the feature
    #  'trigger' icon, and if so, triggers display of the feature icons:
    #---------------------------------------------------------------------------
    
    def feature_activate ( self, event, drag_object = Undefined ):
        if self.feature_mode in NO_FEATURE_ICON:
            return False
       
        # In 'drag' mode, we may get the same coordinate over and over again.
        # We don't want to restart the timer, so exit now:
        exy = ( event.GetX(), event.GetY() )
        if self._feature_popup_xy == exy:
            return True
            
        x, y, dx, dy = self.drag_bounds
          
        if self._is_tab:
            # Handle the case of a notebook tab:
            x += 7
            if self._state == TabActive:
                x += 2
            result = self.is_in( event, x, y + 6, DockImages._tab_feature_width, 
                                 DockImages._tab_feature_height )
        else:
            # Handle the case of a horzontal/vertical drag bar:
            ox, oy = 10, 4
            if self.style == 'vertical':
                ox, oy = 4, 10
            result = self.is_in( event, x + ox, y + oy, 
                                 DockImages._bar_feature_width,
                                 DockImages._bar_feature_height )
        
        # If the pointer is over the feature 'trigger' icon, save the event for
        # the popup processing:
        if result:
            # If this is part of a drag operation, prepare for drag mode:
            if drag_object is not Undefined:
                self.pre_drag( drag_object, FEATURE_EXTERNAL_DRAG )
            
            # Schedule the popup for later:
            self._feature_popup_xy = exy
            do_after( 100, self._feature_popup )
        
        return result
                           
    #---------------------------------------------------------------------------
    #  Resets any pending feature popup:  
    #---------------------------------------------------------------------------
                                        
    def reset_feature_popup ( self ):
        self._feature_popup_xy = None
    
    #---------------------------------------------------------------------------
    #  Pops up the current features if a feature popup is still pending:
    #---------------------------------------------------------------------------
    
    def _feature_popup ( self ):
        if self._feature_popup_xy is not None:
            # Set the new feature mode:
            if self.feature_mode == FEATURE_DROP:
                self.feature_mode = FEATURE_DROP_VISIBLE
            else:
                self.feature_mode = FEATURE_VISIBLE
           
            self.control.GetParent().owner.feature_bar_popup( self )
            self._feature_popup_xy = None
        else:
            self.post_drag( FEATURE_EXTERNAL_DRAG )
        
    #---------------------------------------------------------------------------
    #  Finishes the processing of a feature popup:
    #---------------------------------------------------------------------------
        
    def feature_bar_closed ( self ):
        if self.feature_mode == FEATURE_DROP_VISIBLE:
            self.feature_mode = FEATURE_DROP
        else:
            self.feature_mode = FEATURE_NORMAL
            
        self._redraw_control()
        
    #---------------------------------------------------------------------------
    #  Handles all pre-processing before a feature is dragged:
    #---------------------------------------------------------------------------
    
    def pre_drag_all ( self, object ):
        """ Prepare all DockControls in the associated DockWindow for being 
            dragged over.
        """
        for control in self.dock_controls:
            control.pre_drag( object )
        self.pre_drag( object )
                
    def pre_drag ( self, object, tag = 0 ):
        """ Prepare this DockControl for being dragged over.
        """
        if (self.visible and 
            (self.feature_mode != FEATURE_NONE) and
            (self._feature_mode is None)):
            if isinstance( object, IFeatureTool ):
                if (object.feature_can_drop_on( self.object ) or
                    object.feature_can_drop_on_dock_control( self )):
                    from feature_tool import FeatureTool
                    
                    self.drop_features = [ 
                        FeatureTool( dock_control = self ) ]
            else:
                self.drop_features = [ f for f in self.features
                                         if f.can_drop( object ) and 
                                            (f.bitmap is not None) ]
                                            
            self._feature_mode = self.feature_mode + tag
            if len( self.drop_features ) > 0:
                self.feature_mode = FEATURE_DROP
            else:
                self.feature_mode = FEATURE_DISABLED
            self._redraw_control()
        
    #---------------------------------------------------------------------------
    #  Handles all post-processing after a feature has been dragged:
    #---------------------------------------------------------------------------
    
    def post_drag_all ( self ):
        """ Restore all DockControls in the associated DockWindow after a drag
            operation is completed.
        """
        for control in self.dock_controls:
            control.post_drag()
        self.post_drag()
            
    def post_drag ( self, tag = 0 ):
        """ Restore this DockControl after a drag operation is completed.
        """
        if ((self._feature_mode is None) or (tag == 0) or 
            ((self._feature_mode & tag) != 0)):
            self.drop_features = []
            if self.feature_mode != FEATURE_NONE:
                if self._feature_mode is not None:
                    self.feature_mode  = self._feature_mode & (~tag)
                    self._feature_mode = None
                else:
                    self.set_feature_mode( False )
                self._redraw_control()

#-------------------------------------------------------------------------------
#  'DockSplitter' class:
#-------------------------------------------------------------------------------

class DockSplitter ( DockItem ):

    #---------------------------------------------------------------------------
    #  Trait definitions:
    #---------------------------------------------------------------------------

    # Style of the splitter bar:
    style = Enum( 'horizontal', 'vertical' )

    # Index of the splitter within its parent:
    index = Int

    # Current state of the splitter (i.e. its position relative to the things
    # it splits):
    state = Property

    #---------------------------------------------------------------------------
    #  Draws the contents of the splitter:
    #---------------------------------------------------------------------------

    def draw ( self, dc ):
        """ Draws the contents of the splitter.
        """
        x, y, dx, dy = self.bounds
        dc.SetBrush( wx.Brush( wx.Colour( *DragLightColor ), wx.SOLID ) )
        dc.SetPen( wx.TRANSPARENT_PEN )
        image = DockImages.get_splitter_image( self.state )
        if self.style == 'horizontal':
            idx = image.GetWidth()
            dc.DrawRectangle( x + idx, y + 3, dx - idx - 1, 1 )
            dc.DrawRectangle( x + idx, y + 4, 1, 4 )
            dc.SetBrush( wx.Brush( wx.Colour( *BGColor ), wx.SOLID ) )
            dc.DrawRectangle( x, y, idx, 9 )
            dc.DrawRectangle( x + idx, y, dx - idx, 3 )
            dc.DrawRectangle( x + idx + 1, y + 4, dx - idx - 2, 4 )
            dc.SetBrush( wx.Brush( wx.Colour( *DragDarkColor ), wx.SOLID ) )
            dc.DrawRectangle( x + idx, y + 8, dx - idx, 1 )
            dc.DrawRectangle( x + dx - 1, y + 3, 1, 5 )
            dc.DrawBitmap( image, x, y + 3, True )
            self._hot_spot = ( x, y, idx, dy )
        else:
            idy = image.GetHeight()
            dc.DrawRectangle( x + 3, y + idy, 1, dy - idy - 1 )
            dc.DrawRectangle( x + 4, y + idy, 4, 1 )
            dc.SetBrush( wx.Brush( wx.Colour( *BGColor ), wx.SOLID ) )
            dc.DrawRectangle( x, y, 12, idy )
            dc.DrawRectangle( x, y + idy, 3, dy - idy )
            dc.DrawRectangle( x + 4, y + idy + 1, 4, dy - idy - 2 )
            dc.DrawRectangle( x + 9, y + idy, 3, dy - idy )
            dc.SetBrush( wx.Brush( wx.Colour( *DragDarkColor ), wx.SOLID ) )
            dc.DrawRectangle( x + 8, y + idy, 1, dy - idy )
            dc.DrawRectangle( x + 3, y + dy - 1, 5, 1 )
            dc.DrawBitmap( image, x + 3, y, True )
            self._hot_spot = ( x, y, dx, idy )

    #---------------------------------------------------------------------------
    #  Gets the cursor to use when the mouse is over the splitter bar:
    #---------------------------------------------------------------------------

    def get_cursor ( self, event ):
        """ Gets the cursor to use when the mouse is over the splitter bar.
        """
        if (self._hot_spot is None) or self.is_in( event, *self._hot_spot ):
            return wx.CURSOR_ARROW

        if self.style == 'horizontal':
            return wx.CURSOR_SIZENS

        return wx.CURSOR_SIZEWE

    #---------------------------------------------------------------------------
    #  Returns a copy of the splitter 'structure', minus the actual content:
    #---------------------------------------------------------------------------

    def get_structure ( self ):
        """ Returns a copy of the splitter 'structure', minus the actual
            content.
        """
        return self.clone_traits( [ '_last_bounds' ] )

    #---------------------------------------------------------------------------
    #  Handles the left mouse button being pressed:
    #---------------------------------------------------------------------------

    def mouse_down ( self, event ):
        """ Handles the left mouse button being pressed.
        """
        self._click_pending = ((self._hot_spot is not None) and
                                self.is_in( event, *self._hot_spot ))
        if not self._click_pending:
            self._xy            = ( event.GetX(), event.GetY() )
            self._max_bounds    = self.parent.get_splitter_bounds( self )
            self._draw_bounds( event, self.bounds )

    #---------------------------------------------------------------------------
    #  Handles the left mouse button being released:
    #---------------------------------------------------------------------------

    def mouse_up ( self, event ):
        """ Handles the left mouse button being released.
        """
        if self._click_pending:
            hx, hy, hdx, hdy = self._hot_spot
            if not self.is_in( event, hx, hy, hdx, hdy ):
                return

            is_horizontal = (self.style == 'horizontal')
            x, y, dx, dy  = self.bounds
            if self._last_bounds is not None:
                if is_horizontal:
                    y = self._last_bounds[1]
                else:
                    x = self._last_bounds[0]
            state                = self.state
            contents             = self.parent.visible_contents
            ix1, iy1, idx1, idy1 = contents[ self.index ].bounds
            ix2, iy2, idx2, idy2 = contents[ self.index + 1 ].bounds
            if is_horizontal:
                if state != SPLIT_HMIDDLE:
                    if ((y == self.bounds[1]) or
                        (y < iy1)             or
                        ((y + dy) > (iy2 + idy2))):
                        y = (iy1 + iy2 + idy2 - dy) / 2
                else:
                    self._last_bounds = self.bounds
                    if event.GetX() < (hx + (hdx / 2)):
                        y = iy1
                    else:
                        y = iy2 + idy2 - dy
            elif state != SPLIT_VMIDDLE:
                if ((x == self.bounds[0]) or
                    (x < ix1)             or
                    ((x + dx) > (ix2 + idx2))):
                    x = (ix1 + ix2 + idx2 - dx) / 2
            else:
                self._last_bounds = self.bounds
                if event.GetY() < (hy + (hdy / 2)):
                    x = ix2 + idx2 - dx
                else:
                    x = ix1
            self.bounds = ( x, y, dx, dy )
        else:
            self.bounds, self._last_bounds = self._bounds, self.bounds
            self._draw_bounds( event )

        self.parent.update_splitter( self, event )

    #---------------------------------------------------------------------------
    #  Handles the mouse moving while the left mouse button is pressed:
    #---------------------------------------------------------------------------

    def mouse_move ( self, event ):
        """ Handles the mouse moving while the left mouse button is pressed.
        """
        if not self._click_pending:
            x, y, dx, dy     = self.bounds
            mx, my, mdx, mdy = self._max_bounds

            if self.style == 'horizontal':
                y = y + event.GetY() - self._xy[1]
                y = min( max( y, my ), my + mdy - dy )
            else:
                x = x + event.GetX() - self._xy[0]
                x = min( max( x, mx ), mx + mdx - dx )

            bounds = ( x, y, dx, dy )
            if bounds != self._bounds:
                self._draw_bounds( event, bounds )

    #---------------------------------------------------------------------------
    #  Handles the mouse hovering over the item:
    #---------------------------------------------------------------------------

    def hover_enter ( self, event ):
        """ Handles the mouse hovering over the item.
        """
        pass

    #---------------------------------------------------------------------------
    #  Handles the mouse exiting from hovering over the item:
    #---------------------------------------------------------------------------

    def hover_exit ( self, event ):
        """ Handles the mouse exiting from hovering over the item.
        """
        pass

    #---------------------------------------------------------------------------
    #  Draws the splitter bar in a new position while it is being dragged:
    #---------------------------------------------------------------------------

    def _draw_bounds ( self, event, bounds = None ):
        """ Draws the splitter bar in a new position while it is being dragged.
        """
        # Set up the drawing environment:
        window = event.GetEventObject()
        dc     = wx.ScreenDC()
        dc.SetLogicalFunction( wx.XOR )
        dc.SetPen( wx.TRANSPARENT_PEN )
        dc.SetBrush( wx.Brush( wx.Colour( *DragColor ), wx.SOLID ) )

        ax = ay = adx = ady = 0
        if self.style == 'horizontal':
            ay = ady =3
        else:
            ax  = 3
            adx = 6

        # Erase the old bounds (if any):
        if self._bounds is not None:
            x, y, dx, dy = self._bounds
            x, y         = window.ClientToScreenXY( x, y )
            dc.DrawRectangle( x + ax, y + ay, dx - adx, dy - ady )

        # Draw the new bounds (if any):
        if bounds is not None:
            x, y, dx, dy = bounds
            x, y         = window.ClientToScreenXY( x, y )
            dc.DrawRectangle( x + ax, y + ay, dx - adx, dy - ady )

        # Save the new bounds for the next call:
        self._bounds = bounds

    #---------------------------------------------------------------------------
    #  Implementation of the 'state' property:
    #---------------------------------------------------------------------------

    def _get_state ( self ):
        contents             = self.parent.contents
        x, y, dx, dy         = self.bounds
        ix1, iy1, idx1, idy1 = contents[ self.index ].bounds
        ix2, iy2, idx2, idy2 = contents[ self.index + 1 ].bounds
        if self.style == 'horizontal':
            if y == iy1:
                return SPLIT_HTOP
            if (y + dy) == (iy2 + idy2):
                return SPLIT_HBOTTOM
            return SPLIT_HMIDDLE
        else:
            if x == ix1:
                return SPLIT_VLEFT
            if (x + dx) == (ix2 + idx2):
                return SPLIT_VRIGHT
            return SPLIT_VMIDDLE

#-------------------------------------------------------------------------------
#  'DockControl' class:
#-------------------------------------------------------------------------------

class DockControl ( DockItem ):

    #---------------------------------------------------------------------------
    #  Trait definitions:
    #---------------------------------------------------------------------------

    # The control this object describes:
    control = Instance( wx.Window, allow_none = True )

    # The number of global DockWindowFeature's that were available the last
    # the time the feature set was checked:
    num_features = Int
    
    # A feature associated with the DockControl has been changed:
    feature_changed = Event

    # The image to display for this control:
    image = Instance( ImageResource, allow_none = True )

    # The UI name of this control:
    name = Str

    # Has the user set the name of the control?
    user_name = false

    # The object (if any) associated with this control:
    object = Property

    # The id of this control:
    id = Str

    # Style of drag bar/tab:
    style = DockStyle

    # Has the user set the style for this control:
    user_style = false

    # Category of control when it is dragged out of the DockWindow:
    export = Str

    # Is the control visible?
    visible = true

    # Is the control's drag bar locked?
    locked = false

    # Can the control be resized?
    resizable = true

    # Can the control be closed?
    closeable = false

    # Function to call when a DockControl is requesting to be closed:
    on_close = Callable

    # (Optional) object that allows the control to be docked with a different
    # DockWindow:
    dockable = Instance( IDockable, allow_none = True )

    # List of all other DockControl's in the same DockWindow:
    dock_controls = Property

    # Event fired when the control's notebook tab is activated by the user:
    activated = Event

    #---------------------------------------------------------------------------
    #  Calculates the minimum size of the control:
    #---------------------------------------------------------------------------

    def calc_min ( self, use_size = False ):
        """ Calculates the minimum size of the control.
        """
        self.check_features()
        dx, dy = self.width, self.height
        if self.control is not None:
            if wx_26:  
                size = self.control.GetBestFittingSize()  
            else:  
                size = self.control.GetEffectiveMinSize()  
            dx = size.GetWidth()
            dy = size.GetHeight()
            if self.width < 0:
                self.width, self.height = dx, dy

        if use_size and (self.width >= 0):
            return ( self.width, self.height )

        return ( dx, dy )

    #---------------------------------------------------------------------------
    #  Layout the contents of the control based on the specified bounds:
    #---------------------------------------------------------------------------

    def recalc_sizes ( self, x, y, dx, dy ):
        """ Layout the contents of the region based on the specified bounds.
        """
        self.width  = dx = max( 0, dx )
        self.height = dy = max( 0, dy )
        self.bounds = ( x, y, dx, dy )

        # Note: All we really want to do is the 'SetDimensions' call, but the
        # other code is needed for Linux/GTK which will not correctly process
        # the SetDimensions call if the min size is larger than the specified
        # size. So we temporarily set its min size to (0,0), do the
        # SetDimensions, then restore the original min size. The restore is
        # necessary so that DockWindow itself will correctly draw the 'drag'
        # box when performing a docking maneuver...
        control  = self.control
        try:
         min_size = control.GetMinSize()
        except:
            from enthought.developer.helper.fbi import bp
            bp()
            raise
        control.SetMinSize( wx.Size( 0, 0 ) )
        control.SetDimensions( x, y, dx, dy )
        control.SetMinSize( min_size )

    #---------------------------------------------------------------------------
    #  Checks to make sure that all applicable DockWindowFeatures have been
    #  applied:
    #---------------------------------------------------------------------------

    def check_features ( self ):
        """ Checks to make sure that all applicable DockWindowFeatures have been
            applied.
        """
        global features

        mode = self.feature_mode
        n    = len( features )
        if ((self.num_features < n)    and
            (self.control is not None) and
            isinstance( self.control.GetParent().GetSizer(), DockSizer )):
            for i in range( self.num_features, n ):
                feature_class = features[i]
                feature       = feature_class.new_feature_for( self )
                if feature is not None:
                    if not isinstance( feature, SequenceType ):
                        feature = [ feature ]
                    self.features.extend( list( feature ) )
                    if mode == FEATURE_NONE:
                        self.feature_mode = FEATURE_PRE_NORMAL
                    if feature_class.state != 1:
                        for item in feature:
                            item.disable()
                    else:
                        self._tab_width = None
                        if mode in NORMAL_FEATURES:
                            self.set_feature_mode()
            self.num_features = n

    #---------------------------------------------------------------------------
    #  Sets the visibility of the control:
    #---------------------------------------------------------------------------

    def set_visibility ( self, visible ):
        """ Sets the visibility of the control.
        """
        if self.control is not None:
            self.control.Show( visible )

    #---------------------------------------------------------------------------
    #  Returns all DockControl objects contained in the control:
    #---------------------------------------------------------------------------

    def get_controls ( self, visible_only = True ):
        """ Returns all DockControl objects contained in the control.
        """
        if visible_only and (not self.visible):
            return []

        return [ self ]

    #---------------------------------------------------------------------------
    #  Gets the image (if any) associated with the control:
    #---------------------------------------------------------------------------

    def get_image ( self ):
        """ Gets the image (if any) associated with the control.
        """
        if self._image is None:
            if self.image is not None:
                self._image = self.image.create_image().ConvertToBitmap()

        return self._image

    #---------------------------------------------------------------------------
    #  Hides or shows the control:
    #---------------------------------------------------------------------------

    def show ( self, visible = True, layout = True ):
        """ Hides or shows the control.
        """
        if visible != self.visible:
            self.visible = visible
            self._layout( layout )

    #---------------------------------------------------------------------------
    #  Activates a control (i.e. makes it the active page within its containing
    #  notebook):
    #---------------------------------------------------------------------------

    def activate ( self, layout = True ):
        """ Activates a control (i.e. makes it the active page within its
            containing notebook).
        """
        if self.parent is not None:
            self.parent.activate( self, layout )

    #---------------------------------------------------------------------------
    #  Closes the control:
    #---------------------------------------------------------------------------

    def close ( self, layout = True, force = False ):
        """ Closes the control.
        """
        control = self.control
        if control is not None:
            window = control.GetParent()

            if self.on_close is not None:
                # Ask the handler if it is OK to close the control:
                if self.on_close( self, force ) is False:
                    # If not OK to close it, we're done:
                    return

            elif self.dockable is not None:
                # Ask the IDockable handler if it is OK to close the control:
                if self.dockable.dockable_close( self, force ) is False:
                    # If not OK to close it, we're done:
                    return

            else:
                # No close handler, just destroy the widget ourselves:
                control.Destroy()

            # Reset all features:
            self.reset_features()

            # Remove the DockControl from the sizer:
            self.parent.remove( self )

            # Mark the DockControl as closed (i.e. has no associated widget or
            # parent):
            self.control = self.parent = None

            # If a screen update is requested, lay everything out again now:
            if layout:
                window.Layout()
                window.Refresh()

    #---------------------------------------------------------------------------
    #  Returns the object at a specified window position:
    #---------------------------------------------------------------------------

    def object_at ( self, x, y ):
        """ Returns the object at a specified window position.
        """
        return None

    #---------------------------------------------------------------------------
    #  Returns a copy of the control 'structure', minus the actual content:
    #---------------------------------------------------------------------------

    def get_structure ( self ):
        """ Returns a copy of the control 'structure', minus the actual content.
        """
        return self.clone_traits( [
            'id', 'name', 'user_name', 'style', 'user_style', 'visible',
            'locked', 'closeable', 'resizable', 'width', 'height'
        ] )

    #---------------------------------------------------------------------------
    #  Toggles the 'lock' status of the control:
    #---------------------------------------------------------------------------

    def toggle_lock ( self ):
        """ Toggles the 'lock' status of the control.
        """
        self.locked = not self.locked

    #---------------------------------------------------------------------------
    #  Prints the contents of the control:
    #---------------------------------------------------------------------------

    def dump ( self, indent ):
        """ Prints the contents of the control.
        """
        print ('%sControl( %08X, name = %s, id = %s,\n%s'
                          'style = %s, locked = %s,\n%s'
                          'closeable = %s, resizable = %s, visible = %s\n%s'
                          'width = %d, height = %d )' % (
              ' ' * indent, id( self ), self.name, self.id,
              ' ' * (indent + 9), self.style, self.locked,
              ' ' * (indent + 9), self.closeable, self.resizable, self.visible,
              ' ' * (indent + 9), self.width, self.height ))

    #---------------------------------------------------------------------------
    #  Draws the contents of the control:
    #---------------------------------------------------------------------------

    def draw ( self, dc ):
        """ Draws the contents of the control.
        """
        pass

    #---------------------------------------------------------------------------
    #  Sets a new name for the control:
    #---------------------------------------------------------------------------

    def set_name ( self, name, layout = True ):
        """ Sets a new name for the control.
        """
        if name != self.name:
            self.name = name
            self._layout( layout )

    #---------------------------------------------------------------------------
    #  Resets the state of the tab:
    #---------------------------------------------------------------------------

    def reset_tab ( self ):
        """ Resets the state of the tab.
        """
        self.reset_features()
        self._layout()

    #---------------------------------------------------------------------------
    #  Resets all currently defined features:
    #---------------------------------------------------------------------------

    def reset_features ( self ):
        """ Resets all currently defined features.
        """
        for feature in self.features:
            feature.dispose()

        self.features     = []
        self.num_features = 0

    #---------------------------------------------------------------------------
    #  Forces the containing DockWindow to be laid out:
    #---------------------------------------------------------------------------

    def _layout ( self, layout = True ):
        """ Forces the containing DockWindow to be laid out.
        """
        if layout and (self.control is not None):
            do_later( self.control.GetParent().owner.update_layout )

    #---------------------------------------------------------------------------
    #  Handles the 'feature_changed' trait being changed:
    #---------------------------------------------------------------------------
    
    def _feature_changed ( self ):
        """ Handles the 'feature_changed' trait being changed.
        """
        self.set_feature_mode()
        
    #---------------------------------------------------------------------------
    #  Handles the 'control' trait being changed:
    #---------------------------------------------------------------------------

    def _control_changed ( self, old, new ):
        """ Handles the 'control' trait being changed.
        """
        if old is not None:
            old._dock_control = None

        if new is not None:
            new._dock_control = self
            self.reset_tab()

    #---------------------------------------------------------------------------
    #  Handles the 'name' trait being changed:
    #---------------------------------------------------------------------------

    def _name_changed ( self ):
        """ Handles the 'name' trait being changed.
        """
        self._tab_width = self._tab_name = None

    #---------------------------------------------------------------------------
    #  Handles the 'style' trait being changed:
    #---------------------------------------------------------------------------

    def _style_changed ( self ):
        """ Handles the 'style' trait being changed.
        """
        if self.parent is not None:
            self.parent._is_notebook = None

    #---------------------------------------------------------------------------
    #  Handles the 'image' trait being changed:
    #---------------------------------------------------------------------------

    def _image_changed ( self ):
        """ Handles the 'image' trait being changed.
        """
        self._image = None

    #---------------------------------------------------------------------------
    #  Handles the 'visible' trait being changed:
    #---------------------------------------------------------------------------

    def _visible_changed ( self ):
        """ Handles the 'visible' trait being changed.
        """
        if self.parent is not None:
            self.parent.show_hide( self )

    #---------------------------------------------------------------------------
    #  Handles the 'dockable' trait being changed:
    #---------------------------------------------------------------------------

    def _dockable_changed ( self, dockable ):
        """ Handles the 'dockable' trait being changed.
        """
        if dockable is not None:
            dockable.dockable_bind( self )

    #---------------------------------------------------------------------------
    #  Implementation of the 'object' property:
    #---------------------------------------------------------------------------

    def _get_object ( self ):
        return getattr( self.control, '_object', None )

    #---------------------------------------------------------------------------
    #  Implementation of the DockControl's property:
    #---------------------------------------------------------------------------

    def _get_dock_controls ( self ):
        # Get all of the DockControls in the parent DockSizer:
        controls = self.control.GetParent().GetSizer().GetContents(
                       ).get_controls( False )

        # Remove ourself from the list:
        try:
            controls.remove( self )
        except:
            pass

        return controls

#-------------------------------------------------------------------------------
#  'DockGroup' class:
#-------------------------------------------------------------------------------

class DockGroup ( DockItem ):

    #---------------------------------------------------------------------------
    #  Trait definitions:
    #---------------------------------------------------------------------------

    # The contents of the group:
    contents = List

    # The UI name of this group:
    name = Property

    # Style of drag bar/tab:
    style = Property

    # Are the contents of the group resizable?
    resizable = Property

    # Category of control when it is dragged out of the DockWindow:
    export = Constant( '' )

    # Is the group visible?
    visible = Property

    # Content items which are visible:
    visible_contents = Property

    # Can the control be closed?
    closeable = Property

    # The control associated with this group:
    control = Property

    # Is the group locked?
    locked = Property

    #---------------------------------------------------------------------------
    #  Implementation of the 'name' property:
    #---------------------------------------------------------------------------

    def _get_name ( self ):
        controls = self.get_controls()
        n        = len( controls )
        if n == 0:
            return ''

        if n == 1:
            return controls[0].name

        return '%s [%d]' % ( controls[0].name, n )

    #---------------------------------------------------------------------------
    #  Implementation of the 'visible' property:
    #---------------------------------------------------------------------------

    def _get_visible ( self ):
        for item in self.contents:
            if item.visible:
                return True

        return False

    #---------------------------------------------------------------------------
    #  Implementation of the 'visible_contents' property:
    #---------------------------------------------------------------------------

    def _get_visible_contents ( self ):
        return [ item for item in self.contents if item.visible ]

    #---------------------------------------------------------------------------
    #  Implementation of the 'closeable' property:
    #---------------------------------------------------------------------------

    def _get_closeable ( self ):
        for item in self.contents:
            if not item.closeable:
                return False

        return True

    #---------------------------------------------------------------------------
    #  Implementation of the 'style' property:
    #---------------------------------------------------------------------------

    def _get_style ( self ):
        # Make sure there is at least one item in the group:
        if len( self.contents ) > 0:
            # Return the first item's style:
            return self.contents[0].style
        
        # Otherwise, return a default style for an empty group:
        return 'horizontal'

    #---------------------------------------------------------------------------
    #  Implementation of the 'resizable' property:
    #---------------------------------------------------------------------------

    def _get_resizable ( self ):
        if self._resizable is None:
            self._resizable = False
            for control in self.get_controls():
                if control.resizable:
                    self._resizable = True
                    break

        return self._resizable

    #---------------------------------------------------------------------------
    #  Implementation of the 'control' property:
    #---------------------------------------------------------------------------

    def _get_control ( self ):
        if len( self.contents ) == 0:
            return None

        return self.contents[0].control

    #---------------------------------------------------------------------------
    #  Implementation of the 'locked' property:
    #---------------------------------------------------------------------------

    def _get_locked ( self ):
        return self.contents[0].locked

    #---------------------------------------------------------------------------
    #  Hides or shows the contents of the group:
    #---------------------------------------------------------------------------

    def show ( self, visible = True, layout = True ):
        """ Hides or shows the contents of the group.
        """
        for item in self.contents:
            item.show( visible, False )

        if layout:
            window = self.control.GetParent()
            window.Layout()
            window.Refresh()

    #---------------------------------------------------------------------------
    #  Returns all DockControl objects contained in the group:
    #---------------------------------------------------------------------------

    def get_controls ( self, visible_only = True ):
        """ Returns all DockControl objects contained in the group.
        """
        if visible_only:
            contents = self.visible_contents
        else:
            contents = self.contents

        result = []
        for item in contents:
            result.extend( item.get_controls( visible_only ) )

        return result

    #---------------------------------------------------------------------------
    #  Gets the image (if any) associated with the group:
    #---------------------------------------------------------------------------

    def get_image ( self ):
        """ Gets the image (if any) associated with the group.
        """
        if len( self.contents ) == 0:
            return None
        return self.contents[0].get_image()

    #---------------------------------------------------------------------------
    #  Gets the cursor to use when the mouse is over the item:
    #---------------------------------------------------------------------------

    def get_cursor ( self, event ):
        """ Gets the cursor to use when the mouse is over the item.
        """
        return wx.CURSOR_ARROW

    #---------------------------------------------------------------------------
    #  Toggles the 'lock' status of every control in the group:
    #---------------------------------------------------------------------------

    def toggle_lock ( self ):
        """ Toggles the 'lock' status of every control in the group.
        """
        for item in self.contents:
            item.toggle_lock()

    #---------------------------------------------------------------------------
    #  Closes the group:
    #---------------------------------------------------------------------------

    def close ( self, layout = True, force = False ):
        """ Closes the control.
        """
        window = self.control.control.GetParent()

        for item in self.contents[:]:
            item.close( False, force = force )

        if layout:
            window.Layout()
            window.Refresh()

#-------------------------------------------------------------------------------
#  'DockRegion' class:
#-------------------------------------------------------------------------------

class DockRegion ( DockGroup ):

    #---------------------------------------------------------------------------
    #  Trait definitions:
    #---------------------------------------------------------------------------

    # Index of the currently active 'contents' DockControl:
    active = Int

    # Is the region drawn as a notebook or not:
    is_notebook = Property

    # Index of the tab scroll image to use (-1 = No tab scroll):
    tab_scroll_index = Int( -1 )

    # The index of the current leftmost visible tab:
    left_tab = Int

    # The current maximum value for 'left_tab':
    max_tab = Int

    # Contents have been modified property:
    modified = Property

    #---------------------------------------------------------------------------
    #  Calculates the minimum size of the region:
    #---------------------------------------------------------------------------

    def calc_min ( self, use_size = False ):
        """ Calculates the minimum size of the region.
        """
        tab_dx   = tdx = tdy = 0
        contents = self.visible_contents
        if self.is_notebook:
            for item in contents:
                dx, dy  = item.calc_min( use_size )
                tdx     = max( tdx, dx )
                tdy     = max( tdy, dy )
                tab_dx += item.tab_width - 1 # Overlap by 1 pixel

            nbm  = NBMarginLeft + NBMarginRight
            tdx  = nbm + max( tdx, tab_dx + 1 - (2 * NBPadding) )
            tdy += TabHeight + NBMarginTop + NBMarginBottom
        elif len( contents ) > 0:
            item     = contents[0]
            tdx, tdy = item.calc_min( use_size )
            if not item.locked:
                if item.style == 'horizontal':
                    tdy += DragBarSize
                elif item.style == 'vertical':
                    tdx += DragBarSize

        if self.width < 0:
            self.width  = tdx
            self.height = tdy

        return ( tdx, tdy )

    #---------------------------------------------------------------------------
    #  Layout the contents of the region based on the specified bounds:
    #---------------------------------------------------------------------------

    def recalc_sizes ( self, x, y, dx, dy ):
        """ Layout the contents of the region based on the specified bounds.
        """
        self.width  = dx = max( 0, dx )
        self.height = dy = max( 0, dy )
        self.bounds = ( x, y, dx, dy )

        contents = self.visible_contents
        if self.is_notebook:
            # Layout the region out as a notebook:
            x  += NBMarginLeft
            tx0 = tx = x - NBPadding
            dx -= (NBMarginLeft + NBMarginRight)
            iy  = y + TabHeight + NBMarginTop
            dy -= (TabHeight + NBMarginTop + NBMarginBottom)
            for item in contents:
                item.recalc_sizes( x, iy, dx, dy )
                tdx = item.tab_width
                item.set_drag_bounds( tx, y, tdx, TabHeight )
                tx += (tdx - 1)  # Overlap by 1 pixel

            # Calculate the default tab clipping bounds:
            cdx = dx + 2 * NBPadding + 1
            self._tab_clip_bounds = ( tx0, y, cdx, TabHeight )

            # Do we need to enable tab scrolling?
            xr = tx0 + cdx
            if (tx + 2) >= xr:
                # Scrolling needed, calculate maximum tab index for scrolling:
                self.max_tab = 1
                n            = len( contents ) - 1
                xr          -= DockImages._tab_scroller_dx
                for i in range( n, -1, -1 ):
                    xr -= (contents[i].tab_width - 1)
                    if xr < tx0:
                        self.max_tab = min( i + 1, n )
                        break

                # Set the new leftmost tab index:
                self.left_tab = min( self.left_tab, self.max_tab )

                # Determine which tab scroll image to use:
                self.tab_scroll_index = ((self.left_tab < self.max_tab) +
                                         (2 * (self.left_tab > 0))) - 1

                # Now adjust each tab's bounds accordingly:
                if self.left_tab > 0:
                    adx = contents[ self.left_tab ].drag_bounds[0] - tx0
                    for item in contents:
                        dbx, dby, dbdx, dbdy = item.drag_bounds
                        item.set_drag_bounds( dbx - adx, dby, item.tab_width,
                                              dbdy )

                # Exclude the scroll buttons from the tab clipping region:
                self._tab_clip_bounds = ( tx0, y, cdx -
                                        DockImages._tab_scroller_dx, TabHeight )
            else:
                self.tab_scroll_index = -1
                self.left_tab = 0
        else:
            # Lay the region out as a drag bar:
            item        = contents[0]
            drag_bounds = ( 0, 0, 0, 0 )
            if not item.locked:
                if item.style == 'horizontal':
                    drag_bounds = ( x, y, dx, DragBarSize )
                    y  += DragBarSize
                    dy -= DragBarSize
                elif item.style == 'vertical':
                    drag_bounds = ( x, y, DragBarSize, dy )
                    x  += DragBarSize
                    dx -= DragBarSize

            item.recalc_sizes( x, y, dx, dy )
            item.set_drag_bounds( *drag_bounds )

        # Make sure all of the contained controls have the right visiblity:
        self._set_visibility()

    #---------------------------------------------------------------------------
    #  Adds a new control before or after a specified control:
    #---------------------------------------------------------------------------

    def add ( self, control, before = None, after = None, activate = True ):
        """ Adds a new control before a specified control.
        """
        contents = self.contents
        if control.parent is self:
            contents.remove( control )
        if before is None:
            if after is None:
                i = len( contents )
            else:
                i = contents.index( after ) + 1
        else:
            i = contents.index( before )
        contents.insert( i, control )
        if activate:
            self.active = i

    #---------------------------------------------------------------------------
    #  Removes a specified item:
    #---------------------------------------------------------------------------

    def remove ( self, item ):
        """ Removes a specified item.
        """
        contents = self.contents
        i        = contents.index( item )

        if isinstance( item, DockGroup ) and (len( item.contents ) == 1):
            item = item.contents[0]
            if isinstance( item, DockRegion ):
                contents[ i: i + 1 ] = item.contents[:]
            else:
                contents[ i ] = item
        else:
            del contents[ i ]
            if (self.active > i) or (self.active >= len( contents )):
                self.active -= 1

        if self.parent is not None:
            if len( contents ) == 0:
                self.parent.remove( self )
            elif ((len( contents ) == 1) and
                  isinstance( self.parent, DockRegion )):
                self.parent.remove( self )

    #---------------------------------------------------------------------------
    #  Returns a copy of the region 'structure', minus the actual content:
    #---------------------------------------------------------------------------

    def get_structure ( self ):
        """ Returns a copy of the region 'structure', minus the actual content.
        """
        return self.clone_traits( [ 'active', 'width', 'height' ] ).set(
                 contents = [ item.get_structure() for item in self.contents ] )

    #---------------------------------------------------------------------------
    #  Toggles the 'lock' status of every control in the group:
    #---------------------------------------------------------------------------

    def toggle_lock ( self ):
        """ Toggles the 'lock' status of every control in the group.
        """
        super( DockRegion, self ).toggle_lock()
        self._is_notebook = None

    #---------------------------------------------------------------------------
    #  Draws the contents of the region:
    #---------------------------------------------------------------------------

    def draw ( self, dc ):
        """ Draws the contents of the region.
        """
        if self._visible is not False:
            self.begin_draw( dc )

            if self.is_notebook:
                # fixme: There seems to be a case where 'draw' is called before
                # 'recalc_sizes' (which defines '_tab_clip_bounds'), so we need
                # to check to make sure it is defined. If not, it seems safe to
                # exit immediately, since in all known cases, the bounds are
                # ( 0, 0, 0, 0 ), so there is nothing to draw anyways. The
                # question is why 'recalc_sizes' is not being called first.
                if self._tab_clip_bounds is None:
                    return
                    
                self._draw_notebook( dc )
                active = self.active

                # Draw the scroll buttons (if necessary):
                x, y, dx, dy = self._tab_clip_bounds
                index = self.tab_scroll_index
                if index >= 0:
                    dc.DrawBitmap( DockImages._tab_scroller_images[ index ],
                                   x + dx, y + 2, True )

                # Draw all the inactive tabs first:
                dc.SetClippingRegion( x, y, dx, dy )
                for i, item in enumerate( self.contents ):
                    if (i != active) and item.visible:
                        item.draw_tab( dc, TabInactive )

                # Draw the active tab last:
                self.contents[ active ].draw_tab( dc, TabActive )
            else:
                item = self.visible_contents[0]
                if not item.locked:
                    getattr( item, 'draw_' + item.style )( dc )

            self.end_draw( dc )

            # Draw each of the items contained in the region:
            for item in self.contents:
                if item.visible:
                    item.draw( dc )

    #---------------------------------------------------------------------------
    #  Returns the object at a specified window position:
    #---------------------------------------------------------------------------

    def object_at ( self, x, y ):
        """ Returns the object at a specified window position.
        """
        if (self._visible is not False) and self.is_at( x, y ):
            if self.is_notebook and (self.tab_scroll_index >= 0):
                cx, cy, cdx, cdy = self._tab_clip_bounds
                if self.is_at( x, y, ( cx + cdx, cy + 2,
                                       DockImages._tab_scroller_dx,
                                       DockImages._tab_scroller_dy ) ):
                    return self

            for item in self.visible_contents:
                 if item.is_at( x, y, item.drag_bounds ):
                    return item

                 object = item.object_at( x, y )
                 if object is not None:
                    return object

        return None

    #---------------------------------------------------------------------------
    #  Gets the DockInfo object for a specified window position:
    #---------------------------------------------------------------------------

    def dock_info_at ( self, x, y, size, is_control ):
        """ Gets the DockInfo object for a specified window position.
        """
        # Check to see if the point is in our drag bar:
        info = super( DockRegion, self ).dock_info_at( x, y, size, is_control )
        if info is not None:
            return info

        # If we are not visible, or the point is not contained in us, give up:
        if (self._visible is False) or (not self.is_at( x, y )):
            return None

        # Check to see if the point is in the drag bars of any controls:
        contents = self.visible_contents
        for item in contents:
            object = item.dock_info_at( x, y, size, is_control )
            if object is not None:
                return object

        # If we are in 'notebook mode' check to see if the point is in the
        # empty region outside of any tabs:
        lx, ty, dx, dy = self.bounds
        mdx, mdy, tdx  = size
        if self.is_notebook:
            item             = contents[-1]
            ix, iy, idx, idy = item.drag_bounds
            if (x >= (ix + idx)) and (ty <= y < (ty + TabHeight)):
                if item._state == TabActive:
                    ix += 2
                return DockInfo(
                           kind       = DOCK_TAB,
                           bounds     = ( lx + 3, iy + idy - 1, dx - 8,
                                          ty + dy - iy - idy - 4 ),
                           tab_bounds = ( ix + idx, iy + 5, tdx, idy - 5 ),
                           region     = self )

        # Otherwise, figure out which edge the point is closest to, and
        # return a DockInfo object describing that edge:
        left   = x  - lx
        right  = lx + dx - 1 - x
        top    = y  - ty
        bottom = ty + dy - 1 - y
        choice = min( left, right, top, bottom )
        mdx    = min( mdx, (2 * dx) / 3 )
        mdy    = min( mdy, (2 * dy) / 3 )

        if choice == left:
            return DockInfo( kind   = DOCK_LEFT,
                             bounds = ( lx, ty, mdx, dy ),
                             region = self )

        if choice == right:
            return DockInfo( kind   = DOCK_RIGHT,
                             bounds = ( lx + dx - mdx, ty, mdx, dy ),
                             region = self )

        if choice == top:
            return DockInfo( kind   = DOCK_TOP,
                             bounds = ( lx, ty, dx, mdy ),
                             region = self )

        return DockInfo( kind   = DOCK_BOTTOM,
                         bounds = ( lx, ty + dy - mdy, dx, mdy ),
                         region = self )

    #---------------------------------------------------------------------------
    #  Handles a contained notebook tab being clicked:
    #---------------------------------------------------------------------------

    def tab_clicked ( self, control ):
        """ Handles a contained notebook tab being clicked.
        """
        # Find the page that was clicked and mark it as active:
        i = self.contents.index( control )
        if i != self.active:
            self.active = i

            # Force the notebook to be redrawn:
            control.control.GetParent().RefreshRect( wx.Rect( *self.bounds ) )

        # Fire the 'activated' event on the control:
        control.activated = True

    #---------------------------------------------------------------------------
    #  Handles the user clicking an active scroll button:
    #---------------------------------------------------------------------------

    def scroll ( self, type, left_tab = 0 ):
        """ Handles the user clicking an active scroll button.
        """
        if type == SCROLL_LEFT:
            left_tab = min( self.left_tab + 1, self.max_tab )
        elif type == SCROLL_RIGHT:
            left_tab = max( self.left_tab - 1, 0 )

        if left_tab != self.left_tab:

            # Calculate the amount we need to adjust each tab by:
            contents = self.visible_contents
            adx      = (contents[ left_tab ].drag_bounds[0] -
                        contents[ self.left_tab ].drag_bounds[0])

            # Set the new leftmost tab index:
            self.left_tab = left_tab

            # Determine which tab scroll image to use:
            self.tab_scroll_index = ((left_tab < self.max_tab) +
                                     (2 * (left_tab > 0))) - 1

            # Now adjust each tab's bounds accordingly:
            for item in contents:
                dbx, dby, dbdx, dbdy = item.drag_bounds
                item.set_drag_bounds( dbx - adx, dby, item.tab_width, dbdy )

            # Finally, force a redraw of the affected part of the window:
            x, y, dx, dy = self._tab_clip_bounds
            item.control.GetParent().RefreshRect(
                         wx.Rect( x, y, dx + DockImages._tab_scroller_dx, dy ) )

    #---------------------------------------------------------------------------
    #  Handles the left mouse button being pressed:
    #---------------------------------------------------------------------------

    def mouse_down ( self, event ):
        """ Handles the left mouse button being pressed.
        """
        self._scroll = self._get_scroll_button( event )

    #---------------------------------------------------------------------------
    #  Handles the left mouse button being released:
    #---------------------------------------------------------------------------

    def mouse_up ( self, event ):
        """ Handles the left mouse button being released.
        """
        if ((self._scroll is not None) and
            (self._scroll == self._get_scroll_button( event ))):
            self.scroll( self._scroll )

    #---------------------------------------------------------------------------
    #  Handles the mouse moving while the left mouse button is pressed:
    #---------------------------------------------------------------------------

    def mouse_move ( self, event ):
        """ Handles the mouse moving while the left mouse button is pressed.
        """
        pass

    #---------------------------------------------------------------------------
    #  Handles the mouse hovering over the item:
    #---------------------------------------------------------------------------

    def hover_enter ( self, event ):
        """ Handles the mouse hovering over the item.
        """
        pass

    #---------------------------------------------------------------------------
    #  Handles the mouse exiting from hovering over the item:
    #---------------------------------------------------------------------------

    def hover_exit ( self, event ):
        """ Handles the mouse exiting from hovering over the item.
        """
        pass

    #---------------------------------------------------------------------------
    #  Sets the visibility of the region:
    #---------------------------------------------------------------------------

    def set_visibility ( self, visible ):
        """ Sets the visibility of the region.
        """
        self._visible = visible
        active        = self.active
        for i, item in enumerate( self.contents ):
            item.set_visibility( visible and (i == active) )

    #---------------------------------------------------------------------------
    #  Activates a specified control (i.e. makes it the current notebook tab):
    #---------------------------------------------------------------------------

    def activate ( self, control, layout = True ):
        """ Activates a specified control (i.e. makes it the current notebook
            tab).
        """
        if control.visible and self.is_notebook:
            active = self.contents.index( control )
            if active != self.active:
                self.active = active
                self.make_active_tab_visible()
                window = control.control.GetParent()
                if layout:
                    do_later( window.owner.update_layout )
                else:
                    window.RefreshRect( wx.Rect( *self.bounds ) )
                    
    #---------------------------------------------------------------------------
    #  Makes sure the active control's tab is completely visible (if possible):  
    #---------------------------------------------------------------------------

    def make_active_tab_visible ( self ):
        """ Makes sure the active control's tab is completely visible (if
            possible).
        """
        active = self.active
        if active < self.left_tab:
            self.scroll( SCROLL_TO, active )
        else:
            x, y, dx, dy = self.contents[ active ].drag_bounds
            if not self.is_at( x + dx - 1, y + dy - 1, self._tab_clip_bounds ):
                self.scroll( SCROLL_TO, min( active, self.max_tab ) )

    #---------------------------------------------------------------------------
    #  Handles a contained DockControl item being hidden or shown:
    #---------------------------------------------------------------------------

    def show_hide ( self, control ):
        """ Handles a contained DockControl item being hidden or shown.
        """
        i = self.contents.index( control )
        if i == self.active:
            self._update_active()
        elif (self.active < 0) and control.visible:
            self.active = i
        self._is_notebook = None

    #---------------------------------------------------------------------------
    #  Prints the contents of the region:
    #---------------------------------------------------------------------------

    def dump ( self, indent ):
        """ Prints the contents of the region.
        """
        print '%sRegion( %08X, active = %s, width = %d, height = %d )' % (
              ' ' * indent, id( self ), self.active, self.width, self.height )
        for item in self.contents:
            item.dump( indent + 3 )

    #---------------------------------------------------------------------------
    #  Returns which scroll button (if any) the pointer is currently over:
    #---------------------------------------------------------------------------

    def _get_scroll_button ( self, event ):
        """ Returns which scroll button (if any) the pointer is currently over.
        """
        x, y, dx, dy = self._tab_clip_bounds
        if self.is_in( event, x + dx, y + 2, DockImages._tab_scroller_dx,
                                             DockImages._tab_scroller_dy ):
            if (event.GetX() - (x + dx)) < (DockImages._tab_scroller_dx / 2):
                return SCROLL_LEFT

            return SCROLL_RIGHT

        return None

    #---------------------------------------------------------------------------
    #  Updates the currently active page after a change:
    #---------------------------------------------------------------------------

    def _update_active ( self, active = None ):
        """ Updates the currently active page after a change.
        """
        if active is None:
            active = self.active

        contents = self.contents
        for i in (range( active, len( contents ) ) +
                  range( active - 1, -1, -1 )):
            if contents[ i ].visible:
                self.active = i
                return

        self.active = -1

    #---------------------------------------------------------------------------
    #  Handles the 'active' trait being changed:
    #---------------------------------------------------------------------------

    def _active_changed ( self, old, new ):
        self._set_visibility()

        n = len( self.contents )
        if 0 <= old < n:
            # Notify the previously active dockable that the control's tab is
            # being deactivated:
            control = self.contents[ old ]
            if (isinstance( control, DockControl ) and
                (control.dockable is not None)):
                control.dockable.dockable_tab_activated( control, False )

        if 0 <= new < n:
            # Notify the new dockable that the control's tab is being
            # activated:
            control = self.contents[ new ]
            if (isinstance( control, DockControl ) and
                (control.dockable is not None)):
                control.dockable.dockable_tab_activated( control, True )

    #---------------------------------------------------------------------------
    #  Handles the 'contents' trait being changed:
    #---------------------------------------------------------------------------

    def _contents_changed ( self ):
        """ Handles the 'contents' trait being changed.
        """
        self._is_notebook = None
        for item in self.contents:
            item.parent = self
        self.calc_min( True )
        self.modified = True

    def _contents_items_changed ( self, event ):
        """ Handles the 'contents' trait being changed.
        """
        self._is_notebook = None
        for item in event.added:
            item.parent = self
        self.calc_min( True )
        self.modified = True

    #---------------------------------------------------------------------------
    #  Set the proper visiblity for all contained controls:
    #---------------------------------------------------------------------------

    def _set_visibility ( self ):
        """ Set the proper visiblity for all contained controls.
        """
        active = self.active
        for i, item in enumerate( self.contents ):
            item.set_visibility( i == active )

    #---------------------------------------------------------------------------
    #  Implementation of the 'modified' property:
    #---------------------------------------------------------------------------

    def _set_modified ( self, value ):
        if self.parent is not None:
            self.parent.modified = True

    #---------------------------------------------------------------------------
    #  Implementation of the 'is_notebook' property:
    #---------------------------------------------------------------------------

    def _get_is_notebook ( self ):
        if self._is_notebook is None:
            contents = self.visible_contents
            n        = len( contents )
            self._is_notebook = (n > 1)
            if n == 1:
                self._is_notebook = (contents[0].style == 'tab')

        return self._is_notebook

    #---------------------------------------------------------------------------
    #  Draws the notebook body:
    #---------------------------------------------------------------------------

    def _draw_notebook ( self, dc ):
        """ Draws the notebook body.
        """
        x, y, dx, dy = self.bounds
        yth    = y + TabHeight
        xdx    = max( x + 16,  x + dx )
        ydy    = max( yth + 12, y + dy )
        dx8    = max( 0, dx - 8 )
        dyth4  = max( 0, ydy - yth - 4 )
        dyth12 = max( 0, ydy - yth - 12 )

        # Fill the outside areas:
        dc.SetPen( wx.TRANSPARENT_PEN )
        dc.SetBrush( wx.Brush( wx.Colour( *BGColor ), wx.SOLID ) )
        dc.DrawRectangle( x, y, dx, TabHeight - 1 )
        dc.DrawRectangle( x, ydy - 5, dx, 5 )
        dc.DrawRectangle( x, yth - 1, 3, dyth4 )
        dc.DrawRectangle( xdx - 5, yth - 1, 5, dyth4 )

        # Fill the inside areas:
        dc.SetBrush( wx.Brush( wx.Colour( *NBBGColor ), wx.SOLID ) )
        dc.DrawRectangle( x + 4, yth + 3, 3, dyth12 )
        dc.DrawRectangle( xdx - 9, yth + 3, 3, dyth12 )
        dc.DrawRectangle( x + 4, yth, dx8, 3 )
        dc.DrawRectangle( x + 4, ydy - 9, dx8, 3 )

        # Draw the shadows:
        dc.SetPen( wx.Pen( wx.Colour( *NBShadow1Color ), 1, wx.SOLID ) )
        dc.DrawLine( x + 4, ydy - 5, xdx - 4, ydy - 5 )
        dc.DrawLine( xdx - 5, yth, xdx - 5, ydy - 5 )

        dc.SetPen( wx.Pen( wx.Colour( *NBShadow2Color ), 1, wx.SOLID ) )
        dc.DrawLine( x + 5, ydy - 4, xdx - 3, ydy - 4 )
        dc.DrawLine( xdx - 4, yth + 1, xdx - 4, ydy - 4 )

        # Draw the outline:
        dc.SetPen( wx.Pen( wx.Colour( *NBEdgeColor ), 1, wx.SOLID ) )
        dc.DrawLine( x + 3, yth - 1, xdx - 5, yth - 1 )
        dc.DrawLine( x + 3, ydy - 6, xdx - 5, ydy - 6 )
        dc.DrawLine( x + 3, yth, x + 3, ydy - 6 )
        dc.DrawLine( xdx - 6, yth, xdx - 6, ydy - 6 )

#-------------------------------------------------------------------------------
#  'DockSection' class:
#-------------------------------------------------------------------------------

class DockSection ( DockGroup ):

    #---------------------------------------------------------------------------
    #  Trait definitions:
    #---------------------------------------------------------------------------

    # Is this a row (or a column)?
    is_row = true

    # Bounds of any splitter bars associated with the region:
    splitters = List( DockSplitter )

    # The DockWindow that owns this section (set on top level section only):
    dock_window = Instance( 'enthought.pyface.dock.dock_window.DockWindow' )

    # Contents of the section have been modified property:
    modified = Property

    #---------------------------------------------------------------------------
    #  Calculates the minimum size of the section:
    #---------------------------------------------------------------------------

    def calc_min ( self, use_size = False ):
        """ Calculates the minimum size of the section.
        """
        tdx      = tdy = 0
        contents = self.visible_contents
        n        = len( contents )
        if self.is_row:
            for item in contents:
                dx, dy = item.calc_min( use_size )
                tdx   += dx
                tdy    = max( tdy, dy )
            if self.resizable:
                tdx += ((n - 1) * SplitterSizeV)
            else:
                tdx += ((n + 1) * 3)
                tdy += 6
        else:
            for item in contents:
                dx, dy = item.calc_min( use_size )
                tdx    = max( tdx, dx )
                tdy   += dy
            if self.resizable:
                tdy += ((n - 1) * SplitterSizeH)
            else:
                tdx += 6
                tdy += ((n + 1) * 3)

        if self.width < 0:
            self.width  = tdx
            self.height = tdy

        return ( tdx, tdy )

    #---------------------------------------------------------------------------
    #  Layout the contents of the section based on the specified bounds:
    #---------------------------------------------------------------------------

    def recalc_sizes ( self, x, y, dx, dy ):
        """ Layout the contents of the section based on the specified bounds.
        """
        self.width  = dx = max( 0, dx )
        self.height = dy = max( 0, dy )
        self.bounds = ( x, y, dx, dy )

        # If none of the contents are resizable, use the fixed layout method:
        if not self.resizable:
            self.recalc_sizes_fixed( x, y, dx, dy )
            return

        contents  = self.visible_contents
        n         = len( contents ) - 1
        splitters = []

        # Perform a horizontal layout:
        if self.is_row:
            dx -= (n * SplitterSizeV)
            cdx = 0

            # Calculate the current and minimum width:
            for item in contents:
                cdx += item.width
            cdx = max( 1, cdx )

            # Calculate the delta between the current and new width:
            delta = remaining = dx - cdx

            # Allocate the change (plus or minus) proportionally based on each
            # item's current size:
            for i, item in enumerate( contents ):
                if i < n:
                    idx = int( round( float( item.width * delta ) / cdx ) )
                else:
                    idx = remaining
                remaining -= idx
                idx       += item.width
                item.recalc_sizes( x, y, idx, dy )
                x += idx

                # Define the splitter bar between adjacent items:
                if i < n:
                    splitters.append(
                        DockSplitter( bounds = ( x, y, SplitterSizeV, dy ),
                                      style  = 'vertical',
                                      parent = self,
                                      index  = i ) )
                x += SplitterSizeV

        # Perform a vertical layout:
        else:
            dy -= (n * SplitterSizeH)
            cdy = 0

            # Calculate the current and minimum height:
            for item in contents:
                cdy += item.height
            cdy = max( 1, cdy )

            # Calculate the delta between the current and new height:
            delta = remaining  = dy - cdy

            # Allocate the change (plus or minus) proportionally based on each
            # item's current size:
            for i, item in enumerate( contents ):
                if i < n:
                    idy = int( round( float( item.height * delta ) / cdy ) )
                else:
                    idy = remaining
                remaining -= idy
                idy       += item.height
                item.recalc_sizes( x, y, dx, idy )
                y += idy

                # Define the splitter bar between adjacent items:
                if i < n:
                    splitters.append(
                        DockSplitter( bounds = ( x, y, dx, SplitterSizeH ),
                                      style  = 'horizontal',
                                      index  = i ) )
                y += SplitterSizeH

        # Preserve the current internal '_last_bounds' for all splitters if
        # possible:
        cur_splitters = self.splitters
        for i in range( min( len( splitters ), len( cur_splitters ) ) ):
            splitters[i]._last_bounds = cur_splitters[i]._last_bounds

        # Save the new set of splitter bars:
        self.splitters = splitters

        # Set the visibility for all contained items:
        self._set_visibility()

    #---------------------------------------------------------------------------
    #  Layout the contents of the section based on the specified bounds using
    #  the minimum requested size for each item:
    #---------------------------------------------------------------------------

    def recalc_sizes_fixed ( self, x, y, dx, dy ):
        """ Layout the contents of the section based on the specified bounds
            using the minimum requested size for each item.
        """
        self.splitters = []

        x += 3
        y += 3
        dx = max( 0, dx - 3 )
        dy = max( 0, dy - 3 )

        # Perform a horizontal layout:
        if self.is_row:
            # Allocate the space for each item based on its minimum size until
            # the space runs out:
            for i, item in enumerate( self.visible_contents ):
                idx, idy = item.calc_min()
                idx      = min( dx, idx )
                idy      = min( dy, idy )
                dx       = max( 0, dx - idx - 3 )
                item.recalc_sizes( x, y, idx, idy )
                x += idx + 3

        # Perform a vertical layout:
        else:
            # Allocate the space for each item based on its minimum size until
            # the space runs out:
            for i, item in enumerate( self.visible_contents ):
                idx, idy = item.calc_min()
                idx      = min( dx, idx )
                idy      = min( dy, idy )
                dy       = max( 0, dy - idy - 3 )
                item.recalc_sizes( x, y, idx, idy )
                y += idy + 3

        # Set the visibility for all contained items:
        self._set_visibility()

    #---------------------------------------------------------------------------
    #  Draws the contents of the section:
    #---------------------------------------------------------------------------

    def draw ( self, dc ):
        """ Draws the contents of the section.
        """
        if self._visible is not False:
            contents = self.visible_contents
            if (len( contents ) == 0) or (not self.resizable):
                dc.SetBrush( wx.Brush( wx.Colour( *BGColor ), wx.SOLID ) )
                dc.SetPen( wx.TRANSPARENT_PEN )
                dc.DrawRectangle( *self.bounds )

            for item in contents:
                item.draw( dc )

            self.begin_draw( dc )
            for item in self.splitters:
                item.draw( dc )
            self.end_draw( dc )

    #---------------------------------------------------------------------------
    #  Returns the object at a specified window position:
    #---------------------------------------------------------------------------

    def object_at ( self, x, y, force = False ):
        """ Returns the object at a specified window position.
        """
        if self._visible is not False:
            for item in self.splitters:
                if item.is_at( x, y ):
                    return item

            for item in self.visible_contents:
                object = item.object_at( x, y )
                if object is not None:
                    return object

        if force and self.is_at( x, y ):
            return self

        return None

    #---------------------------------------------------------------------------
    #  Gets the DockInfo object for a specified window position:
    #---------------------------------------------------------------------------

    def dock_info_at ( self, x, y, size, is_control, force = False ):
        """ Gets the DockInfo object for a specified window position.
        """
        # Check to see if the point is in our drag bar:
        info = super( DockSection, self ).dock_info_at( x, y, size, is_control )
        if info is not None:
            return info

        if self._visible is False:
            return None

        for item in self.splitters:
            if item.is_at( x, y ):
                return DockInfo( kind = DOCK_SPLITTER )

        for item in self.visible_contents:
            object = item.dock_info_at( x, y, size, is_control )
            if object is not None:
                return object

        # Check to see if we must return a DockInfo object:
        if not force:
            return None

        # Otherwise, figure out which edge the point is closest to, and
        # return a DockInfo object describing that edge:
        lx, ty, dx, dy = self.bounds
        left   = lx - x
        right  = x - lx - dx + 1
        top    = ty - y
        bottom = y - ty - dy + 1

        # If the point is way outside of the section, mark it is a drag and
        # drop candidate:
        if max( left, right, top, bottom ) > 20:
            return DockInfo( kind = DOCK_EXPORT )

        left          = abs( left )
        right         = abs( right )
        top           = abs( top )
        bottom        = abs( bottom )
        choice        = min( left, right, top, bottom )
        mdx, mdy, tdx = size
        mdx           = min( mdx, (2 * dx) / 3 )
        mdy           = min( mdy, (2 * dy) / 3 )

        if choice == left:
            return DockInfo( kind   = DOCK_LEFT,
                             bounds = ( lx, ty, mdx, dy ) )

        if choice == right:
            return DockInfo( kind   = DOCK_RIGHT,
                             bounds = ( lx + dx - mdx, ty, mdx, dy ) )

        if choice == top:
            return DockInfo( kind   = DOCK_TOP,
                             bounds = ( lx, ty, dx, mdy ) )

        return DockInfo( kind   = DOCK_BOTTOM,
                         bounds = ( lx, ty + dy - mdy, dx, mdy ) )

    #---------------------------------------------------------------------------
    #  Adds a control to the section at the edge of the region specified:
    #---------------------------------------------------------------------------

    def add ( self, control, region, kind ):
        """ Adds a control to the section at the edge of the region specified.
        """
        contents   = self.contents
        new_region = control
        if not isinstance( control, DockRegion ):
            new_region = DockRegion( contents = [ control ] )
        i = contents.index( region )
        if self.is_row:
            if (kind == DOCK_TOP) or (kind == DOCK_BOTTOM):
                if kind == DOCK_TOP:
                    new_contents = [ new_region, region ]
                else:
                    new_contents = [ region, new_region ]
                contents[ i ] = DockSection( is_row   = False ).set(
                                             contents = new_contents )
            else:
                if new_region.parent is self:
                    contents.remove( new_region )
                    i = contents.index( region )
                if kind == DOCK_RIGHT:
                    i += 1
                contents.insert( i, new_region )
        else:
            if (kind == DOCK_LEFT) or (kind == DOCK_RIGHT):
                if kind == DOCK_LEFT:
                    new_contents = [ new_region, region ]
                else:
                    new_contents = [ region, new_region ]
                contents[ i ] = DockSection( is_row   = True ).set(
                                             contents = new_contents )
            else:
                if new_region.parent is self:
                    contents.remove( new_region )
                    i = contents.index( region )
                if kind == DOCK_BOTTOM:
                    i += 1
                contents.insert( i, new_region )

    #---------------------------------------------------------------------------
    #  Removes a specified region or section from the section:
    #---------------------------------------------------------------------------

    def remove ( self, item ):
        """ Removes a specified region or section from the section.
        """
        contents = self.contents
        if isinstance( item, DockGroup ) and (len( item.contents ) == 1):
            contents[ contents.index( item ) ] = item.contents[0]
        else:
            contents.remove( item )

        if self.parent is not None:
            if len( contents ) <= 1:
                self.parent.remove( self )
        elif (len( contents ) == 0) and (self.dock_window is not None):
            self.dock_window.dock_window_empty()

    #---------------------------------------------------------------------------
    #  Sets the visibility of the group:
    #---------------------------------------------------------------------------

    def set_visibility ( self, visible ):
        """ Sets the visibility of the group.
        """
        self._visible = visible
        for item in self.contents:
            item.set_visibility( visible )

    #---------------------------------------------------------------------------
    #  Returns a copy of the section 'structure', minus the actual content:
    #---------------------------------------------------------------------------

    def get_structure ( self ):
        """ Returns a copy of the section 'structure', minus the actual content.
        """
        return self.clone_traits( [ 'is_row', 'width', 'height' ] ).set(
               contents  = [ item.get_structure() for item in self.contents  ],
               splitters = [ item.get_structure() for item in self.splitters ] )

    #---------------------------------------------------------------------------
    #  Gets the maximum bounds that a splitter bar is allowed to be dragged:
    #---------------------------------------------------------------------------

    def get_splitter_bounds ( self, splitter ):
        """ Gets the maximum bounds that a splitter bar is allowed to be dragged.
        """
        x, y, dx, dy     = splitter.bounds
        i                = self.splitters.index( splitter )
        contents         = self.visible_contents
        item1            = contents[ i ]
        item2            = contents[ i + 1 ]
        bx, by, bdx, bdy = item2.bounds

        if self.is_row:
            x  = item1.bounds[0]
            dx = bx + bdx - x
        else:
            y  = item1.bounds[1]
            dy = by + bdy - y

        return ( x, y, dx, dy )

    #---------------------------------------------------------------------------
    #  Updates the affected regions when a splitter bar is released:
    #---------------------------------------------------------------------------

    def update_splitter ( self, splitter, event ):
        """ Updates the affected regions when a splitter bar is released.
        """
        x, y, dx, dy         = splitter.bounds
        i                    = self.splitters.index( splitter )
        contents             = self.visible_contents
        item1                = contents[ i ]
        item2                = contents[ i + 1 ]
        ix1, iy1, idx1, idy1 = item1.bounds
        ix2, iy2, idx2, idy2 = item2.bounds

        if self.is_row:
            item1.recalc_sizes( ix1, iy1, x - ix1, idy1 )
            item2.recalc_sizes( x + dx, iy2, ix2 + idx2 - x - dx, idy2 )
        else:
            item1.recalc_sizes( ix1, iy1, idx1, y - iy1 )
            item2.recalc_sizes( ix2, y + dy, idx2, iy2 + idy2 - y - dy )

        if splitter.style == 'horizontal':
            dx = 0
        else:
            dy = 0

        event.GetEventObject().RefreshRect(
                       wx.Rect( ix1 - dx, iy1 - dy, ix2 + idx2 - ix1 + 2 * dx,
                                iy2 + idy2 - iy1 + 2 * dy ) )

    #---------------------------------------------------------------------------
    #  Prints the contents of the section:
    #---------------------------------------------------------------------------

    def dump ( self, indent = 0 ):
        """ Prints the contents of the section.
        """
        print '%sSection( %08X, is_row = %s, width = %d, height = %d )' % (
              ' ' * indent, id( self ), self.is_row, self.width, self.height )
        for item in self.contents:
            item.dump( indent + 3 )

    #---------------------------------------------------------------------------
    #  Sets the correct visiblity for all contained items:
    #---------------------------------------------------------------------------

    def _set_visibility ( self ):
        """ Sets the correct visiblity for all contained items.
        """
        for item in self.contents:
            item.set_visibility( item.visible )

    #---------------------------------------------------------------------------
    #  Handles the 'contents' trait being changed:
    #---------------------------------------------------------------------------

    def _contents_changed ( self ):
        """ Handles the 'contents' trait being changed.
        """
        for item in self.contents:
            item.parent = self
        self.calc_min( True )
        self.modified = True

    def _contents_items_changed ( self, event ):
        """ Handles the 'contents' trait being changed.
        """
        for item in event.added:
            item.parent = self
        self.calc_min( True )
        self.modified = True

    #---------------------------------------------------------------------------
    #  Handles the 'splitters' trait being changed:
    #---------------------------------------------------------------------------

    def _splitters_changed ( self ):
        """ Handles the 'splitters' trait being changed.
        """
        for item in self.splitters:
            item.parent = self

    def _splitters_items_changed ( self, event ):
        """ Handles the 'splitters' trait being changed.
        """
        for item in event.added:
            item.parent = self

    #---------------------------------------------------------------------------
    #  Implementation of the 'modified' property:
    #---------------------------------------------------------------------------

    def _set_modified ( self, value ):
        self._resizable = None
        if self.parent is not None:
            self.parent.modified = True

#-------------------------------------------------------------------------------
#  'DockInfo' class:
#-------------------------------------------------------------------------------

class DockInfo ( HasPrivateTraits ):

    #---------------------------------------------------------------------------
    #  Trait definitions:
    #---------------------------------------------------------------------------

    # Dock kind:
    kind = Range( DOCK_TOP, DOCK_EXPORT )

    # Dock bounds:
    bounds = Bounds

    # Tab bounds (if needed):
    tab_bounds = Bounds

    # Dock Region:
    region = Instance( DockRegion )

    # Dock Control:
    control = Instance( DockItem )

    #---------------------------------------------------------------------------
    #  Draws the DockInfo on the display:
    #---------------------------------------------------------------------------

    def draw ( self, window ):
        """ Draws the DockInfo on the display.
        """
        if DOCK_TOP <= self.kind <= DOCK_TABADD:
            dc = wx.ScreenDC()
            dc.SetLogicalFunction( wx.XOR )
            dc.SetBrush( wx.TRANSPARENT_BRUSH )
            pen = wx.Pen( wx.Colour( *DockColor ), 3, wx.SOLID )
            pen.SetJoin( wx.JOIN_MITER )
            dc.SetPen( pen )
            x, y, dx, dy = self.bounds
            x, y         = window.ClientToScreenXY( x, y )
            if DOCK_TAB <= self.kind <= DOCK_TABADD:
                tx, ty, tdx, tdy = self.tab_bounds
                tx, ty           = window.ClientToScreenXY( tx, ty )
                dc.DrawLines( [ wx.Point( x, y ),
                                wx.Point( tx, y ),
                                wx.Point( tx, ty ),
                                wx.Point( tx + tdx - 1, ty ),
                                wx.Point( tx + tdx - 1, y ),
                                wx.Point( x + dx - 1, y ),
                                wx.Point( x + dx - 1, y + dy - 1 ),
                                wx.Point( x, y + dy - 1 ),
                                wx.Point( x, y ) ] )
            else:
                dc.DrawRectangle( x, y, dx, dy )

    #---------------------------------------------------------------------------
    #  Docks the specified control:
    #---------------------------------------------------------------------------

    def dock ( self, control, window ):
        """ Docks the specified control.
        """
        the_control = control
        kind        = self.kind
        if kind < DOCK_NONE:
            the_parent = control.parent
            region     = self.region
            if (kind == DOCK_TAB) or (kind == DOCK_BAR):
                region.add( control, self.control )
            elif kind == DOCK_TABADD:
                item = self.control
                if isinstance( item, DockControl ):
                    if isinstance( control, DockControl ):
                        control = DockRegion( contents = [ control ] )
                    i = region.contents.index( item )
                    region.contents[ i ] = item = DockSection(
                        contents = [ DockRegion( contents = [ item ] ),
                                     control ],
                        is_row   = True )
                elif isinstance( item, DockSection ):
                    if (isinstance( control, DockSection ) and
                       (item.is_row == control.is_row)):
                       item.contents.extend( control.contents )
                    else:
                        if isinstance( control, DockControl ):
                            control = DockRegion( contents = [ control ] )
                        item.contents.append( control )
                else:
                    item.contents.append( control )
                region.active = region.contents.index( item )
            elif region is not None:
                region.parent.add( control, region, kind )
            else:
                sizer   = window.GetSizer()
                section = sizer._contents
                if ((section.is_row and
                        ((kind == DOCK_TOP) or (kind == DOCK_BOTTOM))) or
                    ((not section.is_row) and
                        ((kind == DOCK_LEFT) or (kind == DOCK_RIGHT)))):
                    if len( section.contents ) > 0:
                        sizer._contents = section = DockSection(
                                            is_row   = not section.is_row ).set(
                                            contents = [ section ] )
                if len( section.contents ) > 0:
                    i = 0
                    if (kind == DOCK_RIGHT) or (kind == DOCK_BOTTOM):
                        i = -1
                    section.add( control, section.contents[ i ], kind )
                else:
                    section.is_row   = not section.is_row
                    section.contents = [ DockRegion( contents = [ control ] ) ]
                    section          = None

            if ((the_parent is not None) and
                (the_parent is not the_control.parent)):
                the_parent.remove( the_control )

            # Force the main window to be laid out and redrawn:
            window.Layout()
            window.Refresh()

# Create a reusable DockInfo indicating no information available:
no_dock_info = DockInfo( kind = DOCK_NONE )

#-------------------------------------------------------------------------------
#  'SetStructureHandler' class
#-------------------------------------------------------------------------------

class SetStructureHandler ( object ):

    #---------------------------------------------------------------------------
    #  Resolves an unresolved DockControl id:
    #---------------------------------------------------------------------------

    def resolve_id ( self, id ):
        """ Resolves an unresolved DockControl id.
        """
        return None

    #---------------------------------------------------------------------------
    #  Resolves extra, unused DockControls not referenced by the structure:
    #---------------------------------------------------------------------------

    def resolve_extras ( self, structure, extras ):
        """ Resolves extra, unused DockControls not referenced by the structure.
        """
        for dock_control in extras:
            if dock_control.control is not None:
                dock_control.control.Show( False )

#-------------------------------------------------------------------------------
#  'DockSizer' class:
#-------------------------------------------------------------------------------

class DockSizer ( wx.PySizer ):

    #---------------------------------------------------------------------------
    #  Initializes the object:
    #---------------------------------------------------------------------------

    def __init__ ( self, contents = None ):
        super( DockSizer, self ).__init__()
        self._contents = self._structure = self._max_structure = None
        if contents is not None:
            self.SetContents( contents )

    #---------------------------------------------------------------------------
    #  Calculates the minimum size needed by the sizer:
    #---------------------------------------------------------------------------

    def CalcMin ( self ):
        if self._contents is None:
            return wx.Size( 20, 20 )
        dx, dy = self._contents.calc_min()
        return wx.Size( dx, dy )

    #---------------------------------------------------------------------------
    #  Layout the contents of the sizer based on the sizer's current size and
    #  position:
    #---------------------------------------------------------------------------

    def RecalcSizes ( self ):
        """ Layout the contents of the sizer based on the sizer's current size
            and position.
        """
        if self._contents is None:
            return

        x,   y = self.GetPositionTuple()
        dx, dy = self.GetSizeTuple()
        self._contents.recalc_sizes( x, y, dx, dy )

    #---------------------------------------------------------------------------
    #  Returns the current sizer contents:
    #---------------------------------------------------------------------------

    def GetContents ( self ):
        """ Returns the current sizer contents.
        """
        return self._contents

    #---------------------------------------------------------------------------
    #  Initializes the layout of a DockWindow from a content list:
    #---------------------------------------------------------------------------

    def SetContents ( self, contents ):
        """ Initializes the layout of a DockWindow from a content list.
        """
        if isinstance( contents, DockGroup ):
            self._contents = contents
        elif isinstance( contents, tuple ):
            self._contents = self._set_region( contents )
        elif isinstance( contents, list ):
            self._contents = self._set_section( contents, True )
        elif isinstance( contents, DockControl ):
            self._contents = self._set_section( [ contents ], True )
        else:
            raise TypeError

        # Set the owner DockWindow for the top-level group (if possible)
        # so that it can notify the owner when the DockWindow becomes empty:
        control = self._contents.control
        if control is not None:
            self._contents.dock_window = control.GetParent().owner

        # If no saved structure exists yet, save the current one:
        if self._structure is None:
            self._structure = self.GetStructure()

    def _set_region ( self, contents ):
        items = []
        for i, item in enumerate( contents ):
            if isinstance( item, tuple ):
                items.append( self._set_region( item ) )
            elif isinstance( item, list ):
                items.append( self._set_section( item, True ) )
            elif isinstance( item, DockItem ):
                items.append( item )
            else:
                raise TypeError

        return DockRegion( contents = items )

    def _set_section ( self, contents, is_row ):
        items = []
        for item in contents:
            if isinstance( item, tuple ):
                items.append( self._set_region( item ) )
            elif isinstance( item, list ):
                items.append( self._set_section( item, not is_row ) )
            elif isinstance( item, DockControl ):
                items.append( DockRegion( contents = [ item ] ) )
            else:
                raise TypeError
        return DockSection( is_row = is_row ).set( contents = items )

    #---------------------------------------------------------------------------
    #  Returns a copy of the layout 'structure', minus the actual content
    #  (i.e. controls, splitters, bounds). This method is intended for use in
    #  persisting the current user layout, so that it can be restored in a
    #  future session:
    #---------------------------------------------------------------------------

    def GetStructure ( self ):
        """ Returns a copy of the layout 'structure', minus the actual content
            (i.e. controls, splitters, bounds). This method is intended for use
            in persisting the current user layout, so that it can be restored in
            a future session.
        """
        if self._contents is not None:
            return self._contents.get_structure()

        return DockSection()

    #---------------------------------------------------------------------------
    #  Takes a previously saved 'GetStructure' result and applies it to the
    #  contents of the sizer in order to restore a previous layout using a
    #  new set of controls:
    #---------------------------------------------------------------------------

    def SetStructure ( self, window, structure, handler = None ):
        """ Takes a previously saved 'GetStructure' result and applies it to the
            contents of the sizer in order to restore a previous layout using a
            new set of controls.
        """
        section = self._contents
        if (section is None) or (not isinstance( structure, DockGroup )):
            return

        # Save the current structure in case a 'ResetStructure' call is made
        # later:
        self._structure = self.GetStructure()

        extras = []

        # Create a mapping for all the DockControls in the new structure:
        map = {}
        for control in structure.get_controls( False ):
            if control.id in map:
                control.parent.remove( control )
            else:
                map[ control.id ] = control

        # Try to map each current item into an equivalent item in the saved
        # preferences:
        for control in section.get_controls( False ):
            mapped_control = map.get( control.id )
            if mapped_control is not None:
                mapped_control.set( **control.get( 'control', 'image', 'export',
                                'dockable', 'data', 'closeable', 'resizable' ) )
                if not mapped_control.user_name:
                    mapped_control.name = control.name
                if not mapped_control.user_style:
                    mapped_control.style = control.style
                del map[ control.id ]
            else:
                extras.append( control )

        # Try to resolve all unused saved items:
        for id, item in map.items():
            # If there is a handler, see if it can resolve it:
            if handler is not None:
                control = handler.resolve_id( id )
                if control is not None:
                    item.control = control
                    continue

            # If nobody knows what it is, just remove it:
            item.parent.remove( item )

        # Check if there are any new items that we have never seen before:
        if len( extras ) > 0:
            if handler is not None:
                # Allow the handler to decide their fate:
                handler.resolve_extras( structure, extras )
            else:
                # Otherwise, add them to the top level as a new region (let the
                # user re-arrange them):
                structure.contents.append( DockRegion( contents = extras ) )

        # Finally, replace the original structure with the updated structure:
        self.SetContents( structure )

    #---------------------------------------------------------------------------
    #  Restores the previously saved structure (if any):
    #---------------------------------------------------------------------------

    def ResetStructure ( self, window ):
        """ Restores the previously saved structure (if any).
        """
        if self._structure is not None:
            self.SetStructure( window, self._structure )

    #---------------------------------------------------------------------------
    #  Toggles the current 'lock' setting of the contents:
    #---------------------------------------------------------------------------

    def ToggleLock ( self ):
        """ Toggles the current 'lock' setting of the contents.
        """
        if self._contents is not None:
            self._contents.toggle_lock()

    #---------------------------------------------------------------------------
    #  Draws the contents of the sizer:
    #---------------------------------------------------------------------------

    def Draw ( self, window ):
        """ Draws the contents of the sizer.
        """
        if self._contents is not None:
            self._contents.draw( set_standard_font( wx.PaintDC( window ) ) )
        else:
            clear_window( window )

    #---------------------------------------------------------------------------
    #  Returns the object at a specified x, y position:
    #---------------------------------------------------------------------------

    def ObjectAt ( self, x, y, force = False ):
        """ Returns the object at a specified window position.
        """
        if self._contents is not None:
            return self._contents.object_at( x, y, force )

        return None

    #---------------------------------------------------------------------------
    #  Gets a DockInfo object at a specified x, y position:
    #---------------------------------------------------------------------------

    def DockInfoAt ( self, x, y, size, is_control ):
        """ Gets a DockInfo object at a specified x, y position.
        """
        if self._contents is not None:
            return self._contents.dock_info_at( x, y, size, is_control, True )

        return no_dock_info

    #---------------------------------------------------------------------------
    #  Minimizes/Maximizes a specified DockControl:
    #---------------------------------------------------------------------------

    def MinMax ( self, window, dock_control ):
        """ Minimizes/Maximizes a specified DockControl.
        """
        if self._max_structure is None:
            self._max_structure = self.GetStructure()
            for control in self.GetContents().get_controls():
                control.visible = (control is dock_control)
        else:
            self.SetStructure( window, self._max_structure )
            self._max_structure = None

    #---------------------------------------------------------------------------
    #  Returns whether the sizer can be maximized now:
    #---------------------------------------------------------------------------

    def IsMaximizable ( self ):
        """ Returns whether the sizer can be maximized now.
        """
        return (self._max_structure is None)
