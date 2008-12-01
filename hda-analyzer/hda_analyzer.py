#!/usr/bin/env python
#
# Copyright (c) 2008 by Jaroslav Kysela <perex@perex.cz>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

import gobject
import gtk
import pango

DIFF_FILE = "/tmp/hda-analyze.diff"

from dircache import listdir
from hda_codec import HDACodec, HDA_card_list, \
                      EAPDBTL_BITS, PIN_WIDGET_CONTROL_BITS, \
                      PIN_WIDGET_CONTROL_VREF, DIG1_BITS, GPIO_IDS

CODEC_TREE = {}
DIFF_TREE = {}

def read_nodes2(card, codec):
  try:
    c = HDACodec(card, codec)
  except OSError, msg:
    if msg[0] == 16:
      print "Codec %i/%i is busy..." % (card, codec)
    return
  c.analyze()
  CODEC_TREE[card][codec] = c
  DIFF_TREE[card][codec] = c.dump()

def read_nodes():
  l = HDA_card_list()
  for c in l:
    CODEC_TREE[c.card] = {}
    DIFF_TREE[c.card] = {}
    for i in range(4):
      read_nodes2(c.card, i)
  cnt = 0
  for c in l:
    if len(CODEC_TREE[c.card]) > 0:
      cnt += 1
  return cnt    

def do_diff1(codec, diff1, out=True):
  from difflib import unified_diff
  diff = unified_diff(diff1.split('\n'), codec.dump().split('\n'), n=8, lineterm='')
  diff = '\n'.join(list(diff))
  if out and len(diff) > 0:
    open(DIFF_FILE, "w+").write(diff)
    print "Diff was stored to: %s" % DIFF_FILE
  return diff

def do_diff():
  res = ''
  for card in CODEC_TREE:
    for codec in CODEC_TREE[card]:
      res += do_diff1(CODEC_TREE[card][codec], DIFF_TREE[card][codec])
  return res

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
  codec = None
  node = None

  def __init__(self):
    gtk.Window.__init__(self)
    self.connect('destroy', self.__destroy)
    self.set_default_size(800, 400)
    self.set_title(self.__class__.__name__)
    self.set_border_width(10)

    self.tooltips = gtk.Tooltips()

    hbox = gtk.HBox(False, 3)
    self.add(hbox)
    
    vbox = gtk.VBox(False, 0)
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled_window.set_shadow_type(gtk.SHADOW_IN)
    treeview = self.__create_treeview()
    treeview.set_size_request(250, 600)
    scrolled_window.add(treeview)
    vbox.pack_start(scrolled_window)
    hbox1 = gtk.HBox(False, 0)
    button = gtk.Button("About")
    button.connect("clicked", self.__about_clicked)
    self.tooltips.set_tip(button, "README! Show the purpose of this program.")
    hbox1.pack_start(button)
    button = gtk.Button("Revert")
    button.connect("clicked", self.__revert_clicked)
    self.tooltips.set_tip(button, "Revert settings for selected codec.")
    hbox1.pack_start(button)
    button = gtk.Button("Diff")
    button.connect("clicked", self.__diff_clicked)
    self.tooltips.set_tip(button, "Show settings diff for selected codec.")
    hbox1.pack_start(button)
    vbox.pack_start(hbox1, False, False)
    hbox.pack_start(vbox, False, False)
    
    self.notebook = gtk.Notebook()
    hbox.pack_start(self.notebook, expand=True)
    
    self.node_window = self.__create_node()
    self._new_notebook_page(self.node_window, '_Node editor')

    scrolled_window, self.info_buffer = self.__create_text(self.__dump_visibility)
    self._new_notebook_page(scrolled_window, '_Text dump')

    self.show_all()    

  def __destroy(self, widget):
    if do_diff():	
      dialog = gtk.MessageDialog(self,
                      gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                      gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
                      "HDA-Analyzer: Would you like to revert\n"
                      "settings for all HDA codecs?")
      response = dialog.run()
      dialog.destroy()
    
      if response == gtk.RESPONSE_YES:
        for card in CODEC_TREE:
          for codec in CODEC_TREE[card]:
            CODEC_TREE[card][codec].revert()
        print "Settings for all codecs were reverted..."
    
    gtk.main_quit()

  def __about_clicked(self, button):
    dialog = gtk.Dialog('About', self,
                        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        (gtk.STOCK_OK, gtk.RESPONSE_OK))
    text_view = gtk.TextView()
    text_view.set_border_width(4)
    str =  """\
HDA Analyzer

This tool allows change the HDA codec setting using direct hardware access
bypassing driver's mixer layer.

To learn more about HDA (High Definition Audio), see
http://www.intel.com/standards/hdaudio/ for more details.

Please, if you find how your codec work, send this information to alsa-devel
mailing list - http://www.alsa-project.org .
"""
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    dialog.vbox.pack_start(text_view, False, False)
    dialog.show_all()
    dialog.run()
    dialog.destroy()
    
  def __revert_clicked(self, button):
    if not self.codec:
      msg = "Please, select a codec in left codec/node tree."
      type = gtk.MESSAGE_WARNING
    else:
      self.codec.revert()
      self.__refresh()
      msg = "Setting for codec %s/%s (%s) was reverted!" % (self.codec.card, self.codec.device, self.codec.name)
      type = gtk.MESSAGE_INFO

    dialog = gtk.MessageDialog(self,
                      gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                      type, gtk.BUTTONS_OK, msg)
    dialog.run()
    dialog.destroy()

  def __diff_clicked(self, button):
    if not self.codec:
      return
    dialog = gtk.Dialog('Diff', self,
                        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        (gtk.STOCK_OK, gtk.RESPONSE_OK))
    text_view = gtk.TextView()
    text_view.set_border_width(4)
    str = do_diff1(self.codec, DIFF_TREE[self.card][self.codec.device], out=False)
    if str == '':
      str = 'No changes'
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    dialog.vbox.pack_start(text_view, False, False)
    dialog.show_all()
    dialog.run()
    dialog.destroy()
    
  def __refresh(self):
    self.load()
    self.__dump_visibility(None, None)

  def __dump_visibility(self, textview, event):
    codec = self.codec
    node = self.node
    if not codec:
      txt = 'Show some card info here...'
    elif codec and self.node < 0:
      txt = codec.dump(skip_nodes=True)
    else:
      n = codec.get_node(node)
      txt = codec.dump_node(n)
    buffer = self.info_buffer
    start, end = buffer.get_bounds()
    buffer.delete(start, end)
    if not txt: return
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, txt)

  def selection_changed_cb(self, selection):
    model, iter = selection.get_selected()
    if not iter:
      return False
    card = model.get_value(iter, CARD_COLUMN)
    codec = model.get_value(iter, CODEC_COLUMN)
    node = model.get_value(iter, NODE_COLUMN)
    self.card = card
    self.codec = None
    if codec >= 0:
      self.codec = CODEC_TREE[card][codec]
    self.node = node
    self.__refresh()

  def load(self):
    codec = self.codec
    node = self.node
    n = None    
    if not codec:
      txt = 'Show some card info here...'
    elif codec and node < 0:
      txt = codec.dump(skip_nodes=True)
    else:
      n = codec.get_node(node)

    for child in self.node_window.get_children():
      self.node_window.remove(child)

    if not n:
      if not codec:
        for i in CODEC_TREE[self.card]:
          card = CODEC_TREE[self.card][i].mcard
          break
        self.__build_card(card)
      elif codec:
        self.__build_codec(codec)
      else:
        return
    else:
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
        for nid in codec.nodes:
          viter = model.append(citer)
          node = codec.get_node(nid)
          model.set(viter,
                      TITLE_COLUMN, 'Node[0x%02x] %s' % (nid, node.wtype_id),
                      CARD_COLUMN, card,
                      CODEC_COLUMN, codec.device,
                      NODE_COLUMN, nid,
                      ITALIC_COLUMN, False)
          nid += 1
  
    cell = gtk.CellRendererText()
    cell.set_property('style', pango.STYLE_ITALIC)
  
    column = gtk.TreeViewColumn('Nodes', cell, text=TITLE_COLUMN,
                                style_set=ITALIC_COLUMN)
  
    treeview.append_column(column)

    selection.connect('changed', self.selection_changed_cb)
    
    treeview.expand_all()
  
    return treeview

  def __create_text(self, callback):
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled_window.set_shadow_type(gtk.SHADOW_IN)
    
    text_view = gtk.TextView()
    fontName = pango.FontDescription("Misc Fixed,Courier Bold 9")
    text_view.modify_font(fontName)
    scrolled_window.add(text_view)
    
    buffer = gtk.TextBuffer(None)
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    text_view.connect("visibility-notify-event", callback)
    
    text_view.set_wrap_mode(True)
    
    return scrolled_window, buffer

  def __create_node(self):
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled_window.set_shadow_type(gtk.SHADOW_IN)    
    return scrolled_window

  def __new_text_view(self):
    text_view = gtk.TextView()
    text_view.set_border_width(4)
    fontName = pango.FontDescription("Misc Fixed,Courier Bold 9")
    text_view.modify_font(fontName)
    return text_view

  def __build_node_caps(self, node):
    frame = gtk.Frame('Node Caps')
    frame.set_border_width(4)
    if len(node.wcaps_list) == 0:
      return frame
    text_view = self.__new_text_view()
    str = ''
    for i in node.wcaps_list:
      str += node.wcap_name(i) + '\n'
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
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
    if node.conn_list and node.connections:
      model = gtk.ListStore(
        gobject.TYPE_BOOLEAN,
        gobject.TYPE_STRING
      )
      idx = 0
      for i in node.connections:
        iter = model.append()
        node1 = self.codec.get_node(node.connections[idx])
        model.set(iter, 0, node.active_connection == idx,
                        1, node1.name())
        idx += 1
      treeview = gtk.TreeView(model)
      treeview.set_rules_hint(True)
      treeview.get_selection().set_mode(gtk.SELECTION_SINGLE)
      treeview.set_size_request(300, 30 + len(node.connections) * 25)
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
    button.set_active(vals.vals[idx] & 0x80)

  def __amp_value_changed(self, adj, data):
    caps, vals, idx = data
    val = int(adj.get_value())
    vals.set_value(idx, val)
    adj.set_value(vals.vals[idx] & 0x7f)

  def __build_amps(self, node):

    def build_caps(title, caps, vals):
      if caps and caps.ofs == None:
        caps = node.dir == HDA_INPUT and \
                    node.codec.amp_caps_in or node.codec.amp_caps_out
        title += ' (Global)'
      frame = gtk.Frame(title)
      frame.set_border_width(4)
      vbox = gtk.VBox(False, 0)
      if caps:
        text_view = self.__new_text_view()
        str =  'Offset:          %d\n' % caps.ofs
        str += 'Number of steps: %d\n' % caps.nsteps
        str += 'Step size:       %d\n' % caps.stepsize
        str += 'Mute:            %s\n' % (caps.mute and "True" or "False")
        buffer = gtk.TextBuffer(None)
        iter = buffer.get_iter_at_offset(0)
        buffer.insert(iter, str[:-1])
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
            adj = gtk.Adjustment((val & 0x7f) % (caps.nsteps+1), 0.0, caps.nsteps+1, 1.0, 1.0, 1.0)
            scale = gtk.HScale(adj)
            scale.set_digits(0)
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
    button.set_active(name in node.pincap_eapdbtl)

  def __pinctls_toggled(self, button, data):
    node, name = data
    node.pin_widget_control_set_value(name, button.get_active())
    button.set_active(name in node.pinctl)

  def __pinctls_vref_change(self, combobox, node):
    index = combobox.get_active()
    idx1 = 0
    for name in PIN_WIDGET_CONTROL_VREF:
      if not name: continue
      if idx1 == index:
        node.pin_widget_control_set_value('vref', name)
        break
      idx1 += 1
    idx = idx1 = 0
    for name in PIN_WIDGET_CONTROL_VREF:
      if name == node.pinctl_vref:
        combobox.set_active(idx1)
        break
      if name != None:
        idx1 += 1

  def __build_pin(self, node):
    hbox = gtk.HBox(False, 0)

    if node.pincap or node.pincap_vref or node.pincap_eapdbtl:
      vbox = gtk.VBox(False, 0)
      if node.pincap or node.pincap_vref:
        frame = gtk.Frame('PIN Caps')
        frame.set_border_width(4)
        text_view = self.__new_text_view()
        str = ''
        for i in node.pincap:
          str += node.pincap_name(i) + '\n'
        for i in node.pincap_vref:
          str += 'VREF_%s\n' % i
        buffer = gtk.TextBuffer(None)
        iter = buffer.get_iter_at_offset(0)
        buffer.insert(iter, str[:-1])
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
    text_view = self.__new_text_view()
    str =  'Jack connection: %s\n' % node.jack_conn_name
    str += 'Jack type:       %s\n' % node.jack_type_name
    str += 'Jack location:   %s\n' % node.jack_location_name
    str += 'Jack location2:  %s\n' % node.jack_location2_name
    str += 'Jack connector:  %s\n' % node.jack_connector_name
    str += 'Jack color:      %s\n' % node.jack_color_name
    if 'NO_PRESENCE' in node.defcfg_misc:
      str += 'No presence\n'
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
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

  def __build_mix(self, node):
    hbox = gtk.HBox(False, 0)
    return hbox

  def __sdi_select_changed(self, adj, node):
    val = int(adj.get_value())
    node.sdi_select_set_value(val)
    adj.set_value(node.sdi_select)

  def __dig1_toggled(self, button, data):
    node, name = data
    val = button.get_active()
    node.dig1_set_value(name, val)
    button.set_active(name in node.dig1)

  def __dig1_category_activate(self, entry, node):
    val = entry.get_text()
    if val.lower().startswith('0x'):
      val = int(val[2:], 16)
    else:
      try:
        val = int(val)
      except:
        print "Unknown category value '%s'" % val
        return
    node.dig1_set_value('category', val)
    entry.set_text("0x%02x" % node.dig1_category)

  def __build_aud(self, node):
    vbox = gtk.VBox(False, 0)

    frame = gtk.Frame('Converter')
    frame.set_border_width(4)
    text_view = self.__new_text_view()
    str = 'Audio Stream:\t%s\n' % node.aud_stream
    str += 'Audio Channel:\t%s\n' % node.aud_channel
    if node.format_ovrd:
      str += 'Rates:\t\t%s\n' % node.pcm_rates[:6]
      if len(node.pcm_rates) > 6:
        str += '\t\t\t\t%s\n' % node.pcm_rates[6:]
      str += 'Bits:\t\t%s\n' % node.pcm_bits
      str += 'Streams:\t%s\n' % node.pcm_streams
    else:
      str += 'Global Rates:\t%s\n' % node.codec.pcm_rates[:6]
      if len(node.codec.pcm_rates) > 6:
        str += '\t\t%s\n' % node.codec.pcm_rates[6:]
      str += 'Global Bits:\t%s\n' % node.codec.pcm_bits
      str += 'Global Streams:\t%s\n' % node.codec.pcm_streams
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    frame.add(text_view)
    vbox.pack_start(frame)

    hbox1 = gtk.HBox(False, 0)
    if node.sdi_select != None:
      frame = gtk.Frame('SDI Select')
      adj = gtk.Adjustment(node.sdi_select, 0.0, 16.0, 1.0, 1.0, 1.0)
      scale = gtk.HScale(adj)
      scale.set_digits(0)
      scale.set_value_pos(gtk.POS_LEFT)
      scale.set_size_request(200, 16)
      adj.connect("value_changed", self.__sdi_select_changed, node)
      frame.add(scale)
      hbox1.pack_start(frame, False, False)
      vbox.pack_start(hbox1, False, False)

    if node.digital:
      hbox1 = gtk.HBox(False, 0)
      frame = gtk.Frame('Digital Converter')
      vbox1 = gtk.VBox(False, 0)
      for name in DIG1_BITS:
        checkbutton = gtk.CheckButton(name)
        checkbutton.set_active(node.digi1 & (1 << DIG1_BITS[name]))
        checkbutton.connect("toggled", self.__dig1_toggled, (node, name))
        vbox1.pack_start(checkbutton, False, False)
      frame.add(vbox1)
      hbox1.pack_start(frame)
      frame = gtk.Frame('Digital Converter Category')
      entry = gtk.Entry()
      entry.set_text("0x%x" % node.dig1_category)
      entry.set_width_chars(4)
      entry.connect("activate", self.__dig1_category_activate, node)
      frame.add(entry)
      hbox1.pack_start(frame)
      vbox.pack_start(hbox1, False, False)

    return vbox

  def __build_node(self, node):
    w = self.node_window

    mframe = gtk.Frame(node.name())
    mframe.set_border_width(4)

    vbox = gtk.VBox(False, 0)
    hbox = gtk.HBox(False, 0)
    hbox.pack_start(self.__build_node_caps(node))
    hbox.pack_start(self.__build_connection_list(node))
    vbox.pack_start(hbox, False, False)
    if node.in_amp or node.out_amp:
      vbox.pack_start(self.__build_amps(node), False, False)
    if node.wtype_id == 'PIN':
      vbox.pack_start(self.__build_pin(node), False, False)
    elif node.wtype_id in ['AUD_IN', 'AUD_OUT']:
      vbox.pack_start(self.__build_aud(node), False, False)
    else:
      if not node.wtype_id in ['AUD_MIX', 'BEEP', 'AUD_SEL']:
        print 'Node type %s has no GUI support' % node.wtype_id

    mframe.add(vbox)
    w.add_with_viewport(mframe)

  def __build_codec_info(self, codec):
    vbox = gtk.VBox(False, 0)

    frame = gtk.Frame('Codec Identification')
    frame.set_border_width(4)
    text_view = self.__new_text_view()
    str = 'Audio Fcn Group: %s\n' % (codec.afg and "0x%02x" % codec.afg or "N/A")
    str += 'Modem Fcn Group: %s\n' % (codec.mfg and "0x%02x" % codec.mfg or "N/A")
    str += 'Vendor ID:\t 0x%08x\n' % codec.vendor_id
    str += 'Subsystem ID:\t 0x%08x\n' % codec.subsystem_id
    str += 'Revision ID:\t 0x%08x\n' % codec.revision_id
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    frame.add(text_view)
    vbox.pack_start(frame, False, False)

    frame = gtk.Frame('PCM Global Capabilities')
    frame.set_border_width(4)
    text_view = self.__new_text_view()
    str = 'Rates:\t\t %s\n' % codec.pcm_rates[:6]
    if len(codec.pcm_rates) > 6:
      str += '\t\t %s\n' % codec.pcm_rates[6:]
    str += 'Bits:\t\t %s\n' % codec.pcm_bits
    str += 'Streams:\t %s\n' % codec.pcm_streams
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    frame.add(text_view)
    vbox.pack_start(frame, False, False)

    return vbox
    
  def __build_codec_amps(self, codec):

    def build_caps(title, caps):
      frame = gtk.Frame(title)
      frame.set_border_width(4)
      if caps:
        text_view = self.__new_text_view()
        str = 'Offset:\t\t %d\n' % caps.ofs
        str += 'Number of steps: %d\n' % caps.nsteps
        str += 'Step size:\t %d\n' % caps.stepsize
        str += 'Mute:\t\t %s\n' % (caps.mute and "True" or "False")
        buffer = gtk.TextBuffer(None)
        iter = buffer.get_iter_at_offset(0)
        buffer.insert(iter, str[:-1])
        text_view.set_buffer(buffer)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        frame.add(text_view)
      return frame

    hbox = gtk.HBox(False, 0)
    c = build_caps('Global Input Amplifier Caps', codec.amp_caps_in)
    hbox.pack_start(c)
    c = build_caps('Global Output Amplifier Caps',codec.amp_caps_out)
    hbox.pack_start(c)

    return hbox

  def __gpio_toggled(self, button, (codec, id, idx)):
    codec.gpio.set(id, idx, button.get_active())
    button.set_active(codec.gpio.test(id, idx))

  def __build_codec_gpio(self, codec):
    frame = gtk.Frame('GPIO')
    frame.set_border_width(4)
    hbox = gtk.HBox(False, 0)
    text_view = self.__new_text_view()
    str =  'IO Count:    %d\n' % codec.gpio_max
    str += 'O Count:     %d\n' % codec.gpio_o
    str += 'I Count:     %d\n' % codec.gpio_i
    str += 'Unsolicited: %s\n' % (codec.gpio_unsol and "True" or "False")
    str += 'Wake:        %s\n' % (codec.gpio_wake and "True" or "False")
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    hbox.pack_start(text_view, False, False)
    frame.add(hbox)
    for id in GPIO_IDS:
      id1 = id == 'direction' and 'out-dir' or id
      frame1 = gtk.Frame(id1)
      frame1.set_border_width(4)
      vbox1 = gtk.VBox(False, 0)
      for i in range(codec.gpio_max):
        checkbutton = gtk.CheckButton('[%d]' % i)
        checkbutton.set_active(codec.gpio.test(id, i))
        checkbutton.connect("toggled", self.__gpio_toggled, (codec, id, i))
        vbox1.pack_start(checkbutton, False, False)
      frame1.add(vbox1)
      hbox.pack_start(frame1, False, False)
    return frame

  def __build_codec(self, codec):
    w = self.node_window

    mframe = gtk.Frame(codec.name)
    mframe.set_border_width(4)

    vbox = gtk.VBox(False, 0)
    vbox.pack_start(self.__build_codec_info(codec), False, False)
    vbox.pack_start(self.__build_codec_amps(codec), False, False)
    vbox.pack_start(self.__build_codec_gpio(codec), False, False)
    mframe.add(vbox)
    w.add_with_viewport(mframe)

  def __build_card_info(self, card):
    text_view = self.__new_text_view()
    str =  'Card:       %s\n' % card.card
    str += 'Id:         %s\n' % card.id
    str += 'Driver:     %s\n' % card.driver
    str += 'Name:       %s\n' % card.name
    str += 'LongName:   %s\n' % card.longname
    buffer = gtk.TextBuffer(None)
    iter = buffer.get_iter_at_offset(0)
    buffer.insert(iter, str[:-1])
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    return text_view

  def __build_card(self, card):
    w = self.node_window

    mframe = gtk.Frame(card.name)
    mframe.set_border_width(4)

    vbox = gtk.VBox(False, 0)
    vbox.pack_start(self.__build_card_info(card), False, False)
    mframe.add(vbox)
    w.add_with_viewport(mframe)

def main():
  if read_nodes() == 0:
    print "No HDA codecs were found or insufficient priviledges for "
    print "/dev/snd/controlC* and /dev/snd/hwdepC*D* device files."
    print
    print "You may also check, if you compiled HDA driver with HWDEP"
    print "interface as well or close all application using HWDEP."
    print
    print "Try run this program as root user."
  else:
    HDAAnalyzer()
    gtk.main()

if __name__ == '__main__':
  main()
