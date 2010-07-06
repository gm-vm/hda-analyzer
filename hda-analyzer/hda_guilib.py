#!/usr/bin/env python
#
# Copyright (c) 2008-2010 by Jaroslav Kysela <perex@perex.cz>
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

from hda_codec import HDACodec, HDA_card_list, \
                      EAPDBTL_BITS, PIN_WIDGET_CONTROL_BITS, \
                      PIN_WIDGET_CONTROL_VREF, DIG1_BITS, GPIO_IDS, \
                      HDA_INPUT, HDA_OUTPUT

def get_fixed_font():
  return pango.FontDescription("Misc Fixed,Courier Bold 9")

class NodeGui(gtk.ScrolledWindow):

  def __init__(self, card=None, codec=None, node=None, doframe=False):
    gtk.ScrolledWindow.__init__(self)
    self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self.set_shadow_type(gtk.SHADOW_IN)    
    if card and not codec and not node:
      self.__build_card(card, doframe)
    elif codec and not card and not node:
      self.__build_codec(codec, doframe)
    elif node and not card and not codec:
      self.__build_node(node, doframe)
    self.show_all()

  def __create_text(self, callback):
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled_window.set_shadow_type(gtk.SHADOW_IN)
    
    text_view = gtk.TextView()
    fontName = get_fixed_font()
    text_view.modify_font(fontName)
    scrolled_window.add(text_view)
    
    buffer = gtk.TextBuffer(None)
    text_view.set_buffer(buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    text_view.connect("visibility-notify-event", callback)
    
    text_view.set_wrap_mode(True)
    
    return scrolled_window, buffer

  def __new_text_view(self, text=None):
    text_view = gtk.TextView()
    text_view.set_border_width(4)
    fontName = get_fixed_font()
    text_view.modify_font(fontName)
    if not text is None:
      buffer = gtk.TextBuffer(None)
      iter = buffer.get_iter_at_offset(0)
      if text[-1] == '\n':
        text = text[:-1]
      buffer.insert(iter, text)
      text_view.set_buffer(buffer)
      text_view.set_editable(False)
      text_view.set_cursor_visible(False)
    return text_view

  def __build_node_caps(self, node):
    frame = gtk.Frame('Node Caps')
    frame.set_border_width(4)
    if len(node.wcaps_list) == 0:
      return frame
    str = ''
    for i in node.wcaps_list:
      str += node.wcap_name(i) + '\n'
    frame.add(self.__new_text_view(text=str))
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
        node1 = node.codec.get_node(node.connections[idx])
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
      if caps and caps.ofs is None:
        caps = caps.dir == HDA_INPUT and \
                    node.codec.amp_caps_in or node.codec.amp_caps_out
        title += ' (Global)'
      frame = gtk.Frame(title)
      frame.set_border_width(4)
      vbox = gtk.VBox(False, 0)
      if caps:
        str =  'Offset:          %d\n' % caps.ofs
        str += 'Number of steps: %d\n' % caps.nsteps
        str += 'Step size:       %d\n' % caps.stepsize
        str += 'Mute:            %s\n' % (caps.mute and "True" or "False")
        vbox.pack_start(self.__new_text_view(text=str), True, True, 0)
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
        str = ''
        for i in node.pincap:
          str += node.pincap_name(i) + '\n'
        for i in node.pincap_vref:
          str += 'VREF_%s\n' % i
        frame.add(self.__new_text_view(text=str))
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
    str =  'Jack connection: %s\n' % node.jack_conn_name
    str += 'Jack type:       %s\n' % node.jack_type_name
    str += 'Jack location:   %s\n' % node.jack_location_name
    str += 'Jack location2:  %s\n' % node.jack_location2_name
    str += 'Jack connector:  %s\n' % node.jack_connector_name
    str += 'Jack color:      %s\n' % node.jack_color_name
    if 'NO_PRESENCE' in node.defcfg_misc:
      str += 'No presence\n'
    frame.add(self.__new_text_view(text=str))
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
    frame.add(self.__new_text_view(text=str))
    vbox.pack_start(frame)

    if not node.sdi_select is None:
      hbox1 = gtk.HBox(False, 0)
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

  def __build_device(self, device):
    vbox = gtk.VBox(False, 0)
    frame = gtk.Frame('Device')
    frame.set_border_width(4)
    hbox = gtk.HBox(False, 0)
    s = 'name=' + str(device.name) + ', type=' + \
        str(device.type) + ', device=' + str(device.device)
    label = gtk.Label(s)
    hbox.pack_start(label, False, False)
    frame.add(hbox)
    vbox.pack_start(frame)
    return vbox

  def __build_controls(self, ctrls):
    vbox = gtk.VBox(False, 0)
    frame = gtk.Frame('Controls')
    frame.set_border_width(4)
    vbox1 = gtk.VBox(False, 0)
    for ctrl in ctrls:
      hbox1 = gtk.HBox(False, 0)
      vbox1.pack_start(hbox1, False, False)
      s = 'name=' + str(ctrl.name) + ', index=' + str(ctrl.index) + \
          ', device=' + str(ctrl.device)
      label = gtk.Label(s)
      hbox1.pack_start(label, False, False)
      if ctrl.amp_chs:
        hbox1 = gtk.HBox(False, 0)
        vbox1.pack_start(hbox1, False, False)
        s = '  chs=' + str(ctrl.amp_chs) + ', dir=' + str(ctrl.amp_dir) + \
            ', idx=' + str(ctrl.amp_idx) + ', ofs=' + str(ctrl.amp_ofs)
        label = gtk.Label(s)
        hbox1.pack_start(label, False, False)
    frame.add(vbox1)
    vbox.pack_start(frame)
    return vbox

  def __build_proc(self, node):
    frame = gtk.Frame('Processing Caps')
    frame.set_border_width(4)
    str = 'benign=%i\nnumcoef=%i\n' % (node.proc_benign, node.proc_numcoef)
    frame.add(self.__new_text_view(text=str))
    return frame

  def __build_node(self, node, doframe=False):
    self.mytitle = node.name()
    if doframe:
      mframe = gtk.Frame(self.mytitle)
      mframe.set_border_width(4)
    else:
      mframe = gtk.Table()

    vbox = gtk.VBox(False, 0)
    dev = node.get_device()
    if not dev is None:
      vbox.pack_start(self.__build_device(dev), False, False)
    ctrls = node.get_controls()
    if ctrls:
      vbox.pack_start(self.__build_controls(ctrls), False, False)
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
    if node.proc_wid:
      vbox.pack_start(self.__build_proc(node), False, False)

    mframe.add(vbox)
    self.add_with_viewport(mframe)

  def __build_codec_info(self, codec):
    vbox = gtk.VBox(False, 0)

    frame = gtk.Frame('Codec Identification')
    frame.set_border_width(4)
    str = 'Audio Fcn Group: %s\n' % (codec.afg and "0x%02x" % codec.afg or "N/A")
    str += 'Modem Fcn Group: %s\n' % (codec.mfg and "0x%02x" % codec.mfg or "N/A")
    str += 'Vendor ID:\t 0x%08x\n' % codec.vendor_id
    str += 'Subsystem ID:\t 0x%08x\n' % codec.subsystem_id
    str += 'Revision ID:\t 0x%08x\n' % codec.revision_id
    frame.add(self.__new_text_view(text=str))
    vbox.pack_start(frame, False, False)

    frame = gtk.Frame('PCM Global Capabilities')
    frame.set_border_width(4)
    str = 'Rates:\t\t %s\n' % codec.pcm_rates[:6]
    if len(codec.pcm_rates) > 6:
      str += '\t\t %s\n' % codec.pcm_rates[6:]
    str += 'Bits:\t\t %s\n' % codec.pcm_bits
    str += 'Streams:\t %s\n' % codec.pcm_streams
    frame.add(self.__new_text_view(text=str))
    vbox.pack_start(frame, False, False)

    return vbox
    
  def __build_codec_amps(self, codec):

    def build_caps(title, caps):
      frame = gtk.Frame(title)
      frame.set_border_width(4)
      if caps and caps.ofs != None:
        str = 'Offset:\t\t %d\n' % caps.ofs
        str += 'Number of steps: %d\n' % caps.nsteps
        str += 'Step size:\t %d\n' % caps.stepsize
        str += 'Mute:\t\t %s\n' % (caps.mute and "True" or "False")
        frame.add(self.__new_text_view(text=str))
      return frame

    hbox = gtk.HBox(False, 0)
    c = build_caps('Global Input Amplifier Caps', codec.amp_caps_in)
    hbox.pack_start(c)
    c = build_caps('Global Output Amplifier Caps', codec.amp_caps_out)
    hbox.pack_start(c)

    return hbox

  def __gpio_toggled(self, button, (codec, id, idx)):
    codec.gpio.set(id, idx, button.get_active())
    button.set_active(codec.gpio.test(id, idx))

  def __build_codec_gpio(self, codec):
    frame = gtk.Frame('GPIO')
    frame.set_border_width(4)
    hbox = gtk.HBox(False, 0)
    str =  'IO Count:    %d\n' % codec.gpio_max
    str += 'O Count:     %d\n' % codec.gpio_o
    str += 'I Count:     %d\n' % codec.gpio_i
    str += 'Unsolicited: %s\n' % (codec.gpio_unsol and "True" or "False")
    str += 'Wake:        %s\n' % (codec.gpio_wake and "True" or "False")
    hbox.pack_start(self.__new_text_view(text=str), False, False)
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

  def __build_codec(self, codec, doframe=False):
    self.mytitle = codec.name
    if doframe:
      mframe = gtk.Frame(self.mytitle)
      mframe.set_border_width(4)
    else:
      mframe = gtk.Table()

    vbox = gtk.VBox(False, 0)
    vbox.pack_start(self.__build_codec_info(codec), False, False)
    vbox.pack_start(self.__build_codec_amps(codec), False, False)
    vbox.pack_start(self.__build_codec_gpio(codec), False, False)
    mframe.add(vbox)
    self.add_with_viewport(mframe)

  def __build_card_info(self, card):
    str =  'Card:       %s\n' % card.card
    str += 'Id:         %s\n' % card.id
    str += 'Driver:     %s\n' % card.driver
    str += 'Name:       %s\n' % card.name
    str += 'LongName:   %s\n' % card.longname
    return self.__new_text_view(text=str)

  def __build_card(self, card, doframe=False):
    self.mytitle = card.name
    if doframe:
      mframe = gtk.Frame(self.mytitle)
      mframe.set_border_width(4)
    else:
      mframe = gtk.Table()

    vbox = gtk.VBox(False, 0)
    vbox.pack_start(self.__build_card_info(card), False, False)
    mframe.add(vbox)
    self.add_with_viewport(mframe)
