#!/usr/bin/env python

import gobject
import gtk
import pango

from dircache import listdir
from hda_codec import HDACodec, HDANode, EAPDBTL_BITS, PIN_WIDGET_CONTROL_BITS, PIN_WIDGET_CONTROL_VREF

PROC_DIR = '/proc/asound'

CODEC_TREE = {}

def read_verbs2(card, codec):
  c = HDACodec(card, codec)
  c.analyze_root_nodes()
  CODEC_TREE[card][codec] = c

def read_verbs1(card):
  CODEC_TREE[card] = {}
  for l in listdir('%s/card%s' % (PROC_DIR, card)):
    if l.startswith('codec#') and l[6] >= '0' and l[6] <= '9':
      read_verbs2(card, int(l[6:]))

def read_verbs():
  for l in listdir(PROC_DIR):
    if l.startswith('card') and l[4] >= '0' and l[4] <= '9':
      read_verbs1(int(l[4:]))

(
    TITLE_COLUMN,
    CARD_COLUMN,
    CODEC_COLUMN,
    NODE_COLUMN,
    ITALIC_COLUMN
) = range(5)

class HDAAnalyzer(gtk.Window):
  info_buffer = None
  node_window = None

  def __init__(self, parent=None):
    gtk.Window.__init__(self)
    try:
      self.set_screen(parent.get_screen())
    except AttributeError:
      self.connect('destroy', lambda *w: gtk.main_quit())
    self.set_default_size(800, 400)
    self.set_title(self.__class__.__name__)
    self.set_border_width(10)

    hbox = gtk.HBox(False, 3)
    self.add(hbox)
    
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled_window.set_shadow_type(gtk.SHADOW_IN)
    treeview = self.__create_treeview()
    treeview.set_size_request(250, 600)
    scrolled_window.add(treeview)
    hbox.pack_start(scrolled_window, False, False)
    
    self.notebook = gtk.Notebook()
    hbox.pack_start(self.notebook, expand=True)
    
    self.node_window = self.__create_node()
    self._new_notebook_page(self.node_window, '_Node')

    scrolled_window, self.info_buffer = self.__create_text()
    self._new_notebook_page(scrolled_window, '_Text info')

    self.show_all()    

  def selection_changed_cb(self, selection):
    model, iter = selection.get_selected()
    if not iter:
      return False
    card = model.get_value(iter, CARD_COLUMN)
    codec = model.get_value(iter, CODEC_COLUMN)
    node = model.get_value(iter, NODE_COLUMN)
    c = None
    if codec >= 0:
      c = CODEC_TREE[card][codec]
    self.load(c, node)

  def load(self, codec, node):
    n = None    
    if not codec:
      txt = 'Show some card info here...'
    elif codec and node < 0:
      txt = codec.dump()
    else:
      txt, n = codec.dump_node(node)
    buffer = self.info_buffer
    start, end = buffer.get_bounds()
    buffer.delete(start, end)
    if not txt: return
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, txt)

    for child in self.node_window.get_children():
      self.node_window.remove(child)

    if not n:
      return

    self.__build_node(n)
    self.node_window.show_all()

  def _new_notebook_page(self, widget, label):
    l = gtk.Label('')
    l.set_text_with_mnemonic(label)
    self.notebook.append_page(widget, l)
  
  def __create_treeview(self):
    model = gtk.TreeStore(
      gobject.TYPE_STRING,
      gobject.TYPE_INT,
      gobject.TYPE_INT,
      gobject.TYPE_INT,
      gobject.TYPE_BOOLEAN
    )
   
    treeview = gtk.TreeView(model)
    selection = treeview.get_selection()
    selection.set_mode(gtk.SELECTION_BROWSE)
    treeview.set_size_request(200, -1)

    for card in CODEC_TREE:
      iter = model.append(None)
      model.set(iter,
                  TITLE_COLUMN, 'card-%s' % card,
                  CARD_COLUMN, card,
                  CODEC_COLUMN, -1,
                  NODE_COLUMN, -1,
                  ITALIC_COLUMN, False)
      for codec in CODEC_TREE[card]:
        citer = model.append(iter)
        codec = CODEC_TREE[card][codec]
        model.set(citer,
                    TITLE_COLUMN, 'codec-%s' % codec.device,
                    CARD_COLUMN, card,
                    CODEC_COLUMN, codec.device,
                    NODE_COLUMN, -1,
                    ITALIC_COLUMN, False)
        nid = codec.base_nid
        for verb in range(codec.nodes):
          viter = model.append(citer)
          node = None
          if type(1) == type(nid):
            node = HDANode(codec, nid)
          model.set(viter,
                      TITLE_COLUMN, node and
                              'Node[0x%02x] %s' % (nid, node.wtype_id) or nid,
                      CARD_COLUMN, card,
                      CODEC_COLUMN, codec.device,
                      NODE_COLUMN, nid,
                      ITALIC_COLUMN, False)
          nid += 1
  
    cell = gtk.CellRendererText()
    cell.set_property('style', pango.STYLE_ITALIC)
  
    column = gtk.TreeViewColumn('Verb', cell, text=TITLE_COLUMN,
                                style_set=ITALIC_COLUMN)
  
    treeview.append_column(column)

    selection.connect('changed', self.selection_changed_cb)
    
    treeview.expand_all()
  
    return treeview

  def __create_text(self):
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled_window.set_shadow_type(gtk.SHADOW_IN)
    
    text_view = gtk.TextView()
    scrolled_window.add(text_view)
    
    buffer = gtk.TextBuffer(None)
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    
    text_view.set_wrap_mode(True)
    
    return scrolled_window, buffer

  def __create_node(self):
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled_window.set_shadow_type(gtk.SHADOW_IN)    
    return scrolled_window

  def __build_node_caps(self, node):
    frame = gtk.Frame('Node Caps')
    frame.set_border_width(4)
    if len(node.wcaps_list) == 0:
      return frame
    text_view = gtk.TextView()
    text_view.set_border_width(4)
    str = ''
    for i in node.wcaps_list:
      str += node.wcap_name(i) + '\n'
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str)
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    frame.add(text_view)
    return frame

  def __node_connection_toggled(self, widget, row, data):
    model, node = data
    if not model[row][0]:
      node.set_active_connection(int(row))
    for r in model:
      r[0] = False
    idx = 0
    for r in model:
      r[0] = node.active_connection == idx
      idx += 1

  def __build_connection_list(self, node):
    frame = gtk.Frame('Connection List')
    frame.set_border_width(4)
    sw = gtk.ScrolledWindow()
    #sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    frame.add(sw)
    if node.conn_list:
      model = gtk.ListStore(
        gobject.TYPE_BOOLEAN,
        gobject.TYPE_STRING
      )
      idx = 0
      for i in node.connections:
        iter = model.append()
        node1 = HDANode(node.codec, node.connections[idx])
        model.set(iter, 0, node.active_connection == idx,
                        1, node1.name())
        idx += 1
      treeview = gtk.TreeView(model)
      treeview.set_rules_hint(True)
      treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
      renderer = gtk.CellRendererToggle()
      renderer.set_radio(True)
      if node.active_connection != None:
        renderer.connect("toggled", self.__node_connection_toggled, (model, node))
      column = gtk.TreeViewColumn("Active", renderer, active=0)
      treeview.append_column(column)
      renderer = gtk.CellRendererText()
      column = gtk.TreeViewColumn("Destination Node", renderer, text=1, editable=False)
      treeview.append_column(column)
      sw.add(treeview)
    return frame

  def __amp_mute_toggled(self, button, data):
    caps, vals, idx = data
    val = button.get_active()
    vals.set_mute(idx, val)

  def __amp_value_changed(self, adj, data):
    caps, vals, idx = data
    val = int(adj.get_value())
    vals.set_value(idx, val)
    adj.set_value(val)

  def __build_amps(self, node):

    def build_caps(title, caps, vals):
      frame = gtk.Frame(title)
      frame.set_border_width(4)
      vbox = gtk.VBox(False, 0)
      if caps:
        text_view = gtk.TextView()
        text_view.set_border_width(4)
        str = 'Offset:\t\t\t%d\n' % caps.ofs
        str += 'Number of steps:\t%d\n' % caps.nsteps
        str += 'Step size:\t\t%d\n' % caps.stepsize
        str += 'Mute:\t\t\t%s\n' % (caps.mute and "True" or "False")
        buffer = gtk.TextBuffer(None)
        iter = buffer.get_iter_at_offset(0)
        buffer.insert(iter, str)
        text_view.set_buffer(buffer)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        vbox.pack_start(text_view, True, True, 0)
        idx = 0
        frame1 = None
        vbox1 = None
        for val in vals.vals:
          if vals.stereo and idx & 1 == 0:
            frame1 = gtk.Frame()
            vbox.pack_start(frame1, False, False)
            vbox1 = gtk.VBox(False, 0)
            frame1.add(vbox1)
          hbox = gtk.HBox(False, 0)
          label = gtk.Label('Val[%d]' % idx)
          hbox.pack_start(label, False, False)
          if caps.mute:
            checkbutton = gtk.CheckButton('Mute')
            checkbutton.set_active(val & 0x80 and True or False)
            checkbutton.connect("toggled", self.__amp_mute_toggled, (caps, vals, idx))
            hbox.pack_start(checkbutton, False, False)
          if caps.stepsize > 0:
            adj = gtk.Adjustment((val & 0x7f) % caps.nsteps, 0.0, caps.nsteps, 1.0, 1.0, 1.0)
            scale = gtk.HScale(adj)
            scale.set_value_pos(gtk.POS_RIGHT)
            adj.connect("value_changed", self.__amp_value_changed, (caps, vals, idx))
            hbox.pack_start(scale, True, True)
          if vbox1:
            vbox1.pack_start(hbox, False, False)
          else:
            vbox.pack_start(hbox, False, False)
          idx += 1
      frame.add(vbox)
      return frame

    hbox = gtk.HBox(False, 0)
    c = build_caps('Input Amplifier',
                    node.in_amp and node.amp_caps_in or None,
                    node.in_amp and node.amp_vals_in or None)
    hbox.pack_start(c)
    c = build_caps('Output Amplifier',
                    node.out_amp and node.amp_caps_out or None,
                    node.out_amp and node.amp_vals_out or None)
    hbox.pack_start(c)

    return hbox

  def __pincap_eapdbtl_toggled(self, button, data):
    node, name = data
    node.eapdbtl_set_value(name, button.get_active())

  def __pinctls_toggled(self, button, data):
    node, name = data
    node.pin_widget_control_set_value(name, button.get_active())

  def __pinctls_vref_change(self, combobox, node):
    index = combobox.get_active()
    idx1 = 0
    for name in PIN_WIDGET_CONTROL_VREF:
      if not name: continue
      if idx1 == index:
        node.pin_widget_control_set_value('vref', name)
        break
      idx1 += 1

  def __build_pin(self, node):
    hbox = gtk.HBox(False, 0)

    if node.pincap or node.pincap_vref or node.pincap_eapdbtl:
      vbox = gtk.VBox(False, 0)
      if node.pincap or node.pincap_vref:
        frame = gtk.Frame('PIN Caps')
        frame.set_border_width(4)
        text_view = gtk.TextView()
        text_view.set_border_width(4)
        str = ''
        for i in node.pincap:
          str += node.pincap_name(i) + '\n'
        for i in node.pincap_vref:
          str += 'VREF_%s\n' % i
        buffer = gtk.TextBuffer(None)
        iter = buffer.get_iter_at_offset(0)
        buffer.insert(iter, str)
        text_view.set_buffer(buffer)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        frame.add(text_view)
        vbox.pack_start(frame)
      if 'EAPD' in node.pincap:
        frame = gtk.Frame('EAPD')
        frame.set_border_width(4)
        vbox1 = gtk.VBox(False, 0)
        for name in EAPDBTL_BITS:
          checkbutton = gtk.CheckButton(name)
          checkbutton.set_active(node.pincap_eapdbtls & (1 << EAPDBTL_BITS[name]))
          checkbutton.connect("toggled", self.__pincap_eapdbtl_toggled, (node, name))
          vbox1.pack_start(checkbutton, False, False)
        frame.add(vbox1)
        vbox.pack_start(frame, False, False)
      hbox.pack_start(vbox)

    vbox = gtk.VBox(False, 0)

    frame = gtk.Frame('Config Default')
    frame.set_border_width(4)
    text_view = gtk.TextView()
    text_view.set_border_width(4)
    str = 'Jack connection:\t%s\n' % node.jack_conn_name
    str += 'Jack type:\t\t%s\n' % node.jack_type_name
    str += 'Jack location:\t\t%s\n' % node.jack_location_name
    str += 'Jack location2:\t%s\n' % node.jack_location2_name
    str += 'Jack connector:\t%s\n' % node.jack_connector_name
    str += 'Jack color:\t\t%s\n' % node.jack_color_name
    if 'NO_PRESENCE' in node.defcfg_misc:
      str += 'No presence\n'
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str)
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    frame.add(text_view)
    vbox.pack_start(frame)
    
    frame = gtk.Frame('Widget Control')
    frame.set_border_width(4)
    vbox1 = gtk.VBox(False, 0)
    for name in PIN_WIDGET_CONTROL_BITS:
      checkbutton = gtk.CheckButton(name)
      checkbutton.set_active(node.pinctls & (1 << PIN_WIDGET_CONTROL_BITS[name]))
      checkbutton.connect("toggled", self.__pinctls_toggled, (node, name))
      vbox1.pack_start(checkbutton, False, False)
    if node.pincap_vref:
      combobox = gtk.combo_box_new_text()
      idx = idx1 = active = 0
      for name in PIN_WIDGET_CONTROL_VREF:
        if name == node.pinctl_vref: active = idx1
        if name:
          combobox.append_text(name)
          idx1 += 1
        idx += 1
      combobox.set_active(active)
      combobox.connect("changed", self.__pinctls_vref_change, node)
      hbox1 = gtk.HBox(False, 0)
      label = gtk.Label('VREF')
      hbox1.pack_start(label, False, False)
      hbox1.pack_start(combobox)
      vbox1.pack_start(hbox1, False, False)
    frame.add(vbox1)
    vbox.pack_start(frame, False, False)

    hbox.pack_start(vbox)
    return hbox

  def __build_node(self, node):
    w = self.node_window

    mframe = gtk.Frame(node.name())
    mframe.set_border_width(4)

    vbox = gtk.VBox(False, 0)
    hbox = gtk.HBox(False, 0)
    hbox.pack_start(self.__build_node_caps(node))
    hbox.pack_start(self.__build_connection_list(node))
    vbox.pack_start(hbox, False, False)
    vbox.pack_start(self.__build_amps(node), False, False)
    if node.wtype_id == 'PIN':
      vbox.pack_start(self.__build_pin(node), False, False)

    #mtable = gtk.Table(2, 2, True)
    #
    #mtable.attach(self.__build_node_caps(node), 0, 1, 0, 1)
    #mtable.attach(self.__build_connection_list(node), 1, 2, 0, 1)
    #mtable.attach(self.__build_amps(node), 0, 2, 1, 2)
    #if node.wtype_id == 'PIN':
    #  mtable.attach(self.__build_pin(node), 0, 2, 2, 3)

    mframe.add(vbox)
    w.add_with_viewport(mframe)
    
def main():
  read_verbs()
  HDAAnalyzer()
  gtk.main()

if __name__ == '__main__':
  main()
