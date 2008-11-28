#!/usr/bin/env python

import os
import struct
from fcntl import ioctl

IOCTL_INFO = 0x80dc4801
IOCTL_PVERSION = 0x80044810
IOCTL_VERB_WRITE = 0xc0084811
IOCTL_GET_WCAPS = 0xc0084812

AC_NODE_ROOT	= 0

(
  HDA_INPUT,
  HDA_OUTPUT
) = range(2)

VERBS = {
  'GET_STREAM_FORMAT':		0x0a00,
  'GET_AMP_GAIN_MUTE':		0x0b00,
  'GET_PROC_COEF':		0x0c00,
  'GET_COEF_INDEX':		0x0d00,
  'PARAMETERS':			0x0f00,
  'GET_CONNECT_SEL':		0x0f01,
  'GET_CONNECT_LIST':		0x0f02,
  'GET_PROC_STATE':		0x0f03,
  'GET_SDI_SELECT':		0x0f04,
  'GET_POWER_STATE':		0x0f05,
  'GET_CONV':			0x0f06,
  'GET_PIN_WIDGET_CONTROL':	0x0f07,
  'GET_UNSOLICITED_RESPONSE':	0x0f08,
  'GET_PIN_SENSE':		0x0f09,
  'GET_BEEP_CONTROL':		0x0f0a,
  'GET_EAPD_BTLENABLE':		0x0f0c,
  'GET_DIGI_CONVERT_1':		0x0f0d,
  'GET_DIGI_CONVERT_2':		0x0f0e,
  'GET_VOLUME_KNOB_CONTROL':	0x0f0f,
  'GET_GPIO_DATA':		0x0f15,
  'GET_GPIO_MASK':		0x0f16,
  'GET_GPIO_DIRECTION':		0x0f17,
  'GET_GPIO_WAKE_MASK':		0x0f18,
  'GET_GPIO_UNSOLICITED_RSP_MASK': 0x0f19,
  'GET_GPIO_STICKY_MASK':	0x0f1a,
  'GET_CONFIG_DEFAULT':		0x0f1c,
  'GET_SUBSYSTEM_ID':		0x0f20,

  'SET_STREAM_FORMAT':		0x200,
  'SET_AMP_GAIN_MUTE':		0x300,
  'SET_PROC_COEF':		0x400,
  'SET_COEF_INDEX':		0x500,
  'SET_CONNECT_SEL':		0x701,
  'SET_PROC_STATE':		0x703,
  'SET_SDI_SELECT':		0x704,
  'SET_POWER_STATE':		0x705,
  'SET_CHANNEL_STREAMID':	0x706,
  'SET_PIN_WIDGET_CONTROL':	0x707,
  'SET_UNSOLICITED_ENABLE':	0x708,
  'SET_PIN_SENSE':		0x709,
  'SET_BEEP_CONTROL':		0x70a,
  'SET_EAPD_BTLENABLE':		0x70c,
  'SET_DIGI_CONVERT_1':		0x70d,
  'SET_DIGI_CONVERT_2':		0x70e,
  'SET_VOLUME_KNOB_CONTROL':	0x70f,
  'SET_GPIO_DATA':		0x715,
  'SET_GPIO_MASK':		0x716,
  'SET_GPIO_DIRECTION':		0x717,
  'SET_GPIO_WAKE_MASK':		0x718,
  'SET_GPIO_UNSOLICITED_RSP_MASK': 0x719,
  'SET_GPIO_STICKY_MASK':	0x71a,
  'SET_CONFIG_DEFAULT_BYTES_0':	0x71c,
  'SET_CONFIG_DEFAULT_BYTES_1':	0x71d,
  'SET_CONFIG_DEFAULT_BYTES_2':	0x71e,
  'SET_CONFIG_DEFAULT_BYTES_3':	0x71f,
  'SET_CODEC_RESET':		0x7ff
}

PARAMS = {
  'VENDOR_ID':		0x00,
  'SUBSYSTEM_ID':	0x01,
  'REV_ID':		0x02,
  'NODE_COUNT':		0x04,
  'FUNCTION_TYPE':	0x05,
  'AUDIO_FG_CAP':	0x08,
  'AUDIO_WIDGET_CAP':	0x09,
  'PCM':		0x0a,
  'STREAM':		0x0b,
  'PIN_CAP':		0x0c,
  'AMP_IN_CAP':		0x0d,
  'CONNLIST_LEN':	0x0e,
  'POWER_STATE':	0x0f,
  'PROC_CAP':		0x10,
  'GPIO_CAP':		0x11,
  'AMP_OUT_CAP':	0x12,
  'VOL_KNB_CAP':	0x13
}

WIDGET_TYPES = {
  'AUD_OUT':		0x00,
  'AUD_IN':		0x01,
  'AUD_MIX':		0x02,
  'AUD_SEL':		0x03,
  'PIN':		0x04,
  'POWER':		0x05,
  'VOL_KNB':		0x06,
  'BEEP':		0x07,
  'VENDOR':		0x0f
}

WIDGET_TYPE_NAMES = [
  "Audio Output",
  "Audio Input",
  "Audio Mixer",
  "Audio Selector",
  "Pin Complex",
  "Power Widget",
  "Volume Knob Widget",
  "Beep Generator Widget",
  None,
  None,
  None,
  None,
  None,
  None,
  None,
  "Vendor Defined Widget"
]

WIDGET_TYPE_IDS = [
  "AUD_OUT",
  "AUD_IN",
  "AUD_MIX",
  "AUD_SEL",
  "PIN",
  "POWER",
  "VOL_KNB",
  "BEEP",
  None,
  None,
  None,
  None,
  None,
  None,
  None,
  "VENDOR"
]

WIDGET_CAP_NAMES = {
  'STEREO': 'Stereo',
  'IN_AMP': 'Input Amplifier',
  'OUT_AMP': 'Output Amplifier',
  'AMP_OVRD': 'Amplifier Override',
  'FORMAT_OVRD': 'Format Override',
  'STRIPE': 'Stripe',
  'PROC_WID': 'Proc Widget',
  'CONN_LIST': 'Connection List',
  'UNSOL_CAP': 'Unsolicited Capabilities',
  'DIGITAL': 'Digital',
  'POWER': 'Power',
  'LR_SWAP': 'L/R Swap',
  'CP_CAPS': 'CP Capabilities'
}

WIDGET_PINCAP_NAMES = {
  'IMP_SENSE': 'Input Sense',
  'TRIG_REQ': 'Trigger Request',
  'PRES_DETECT': 'Press Detect',
  'HP_DRV': 'Headphone Drive',
  'OUT': 'Output',
  'IN': 'Input',
  'BALANCE': 'Balance',
  'HDMI': 'HDMI',
  'EAPD': 'EAPD'
}

GPIO_IDS = {
  'enable': (VERBS['GET_GPIO_MASK'], VERBS['SET_GPIO_MASK']),
  'direction': (VERBS['GET_GPIO_DIRECTION'], VERBS['SET_GPIO_DIRECTION']),
  'wake': (VERBS['GET_GPIO_WAKE_MASK'], VERBS['SET_GPIO_WAKE_MASK']),
  'unsol': (VERBS['GET_GPIO_UNSOLICITED_RSP_MASK'], VERBS['SET_GPIO_UNSOLICITED_RSP_MASK']),
  'sticky': (VERBS['GET_GPIO_STICKY_MASK'], VERBS['SET_GPIO_STICKY_MASK']),
  'data': (VERBS['GET_GPIO_DATA'], VERBS['SET_GPIO_DATA'])
}

EAPDBTL_BITS = {
  'BALANCED': 0,
  'EAPD': 1,
  'R/L': 2
} 

PIN_WIDGET_CONTROL_BITS = {
  'IN': 5,
  'OUT': 6,
  'HP': 7
}

PIN_WIDGET_CONTROL_VREF = [
  "HIZ", "50", "GRD", None, "80", "100", None, None
]

DIG1_BITS = {
  'ENABLE': 0,
  'VALIDITY': 1,
  'VALIDITYCFG': 2,
  'EMPHASIS': 3,
  'COPYRIGHT': 4,
  'NONAUDIO': 5,
  'PROFESSIONAL': 6,
  'LEVEL': 7
}

class HDAAmpCaps:

  def __init__(self, codec, nid, dir):
    self.codec = codec
    self.nid = nid
    self.dir = dir
    self.reread()
    
  def reread(self):
    caps = self.codec.param_read(self.nid,
          PARAMS[self.dir == HDA_OUTPUT and 'AMP_OUT_CAP' or 'AMP_IN_CAP'])
    if caps == ~0 or caps == 0:
      self.ofs = None
      self.nsteps = None
      self.stepsize = None
      self.mute = None
    else:
      self.ofs = caps & 0x7f
      self.nsteps = (caps >> 8) & 0x7f
      self.stepsize = (caps >> 16) & 0x7f
      self.mute = (caps >> 31) & 1 and True or False

class HDAAmpVal:

  def __init__(self, codec, node, dir):
    self.codec = codec
    self.node = node
    self.dir = dir
    self.nid = node.nid
    self.stereo = node.stereo
    self.indices = 1
    if dir == HDA_INPUT:
      self.indices = node.wtype_id == 'PIN' and 1 or len(node.connections)
    self.reread()

  def __write_val(self, idx):
    dir = self.dir == HDA_OUTPUT and (1<<15) or (1<<14)
    verb = VERBS['SET_AMP_GAIN_MUTE']
    if self.stereo:
      indice = idx / 2
      dir |= idx & 1 and (1 << 12) or (1 << 13)
    else:
      indice = idx
      dir |= (1 << 12) | (1 << 13)
    self.codec.rw(self.nid, verb, dir | (indice << 8) | self.vals[idx])

  def set_mute(self, idx, mute):
    val = self.vals[idx]
    if mute:
      self.vals[idx] |= 0x80
    else:
      self.vals[idx] &= ~0x80
    self.__write_val(idx)
    
  def set_value(self, idx, val):
    self.vals[idx] &= ~0x7f
    self.vals[idx] |= val & 0x7f
    self.__write_val(idx)
    
  def reread(self):
    dir = self.dir == HDA_OUTPUT and (1<<15) or (0<<15)
    self.vals = []
    verb = VERBS['GET_AMP_GAIN_MUTE']
    for i in range(self.indices):
      if self.stereo:
        val = self.codec.rw(self.nid, verb, (1 << 13) | dir | i)
        self.vals.append(val)
      val = self.codec.rw(self.nid, verb, (0 << 13) | dir | i)
      self.vals.append(val)

class HDANode:
  
  def __init__(self, codec, nid, cache=True):
    self.codec = codec
    self.nid = nid
    self.wcaps = cache and codec.get_wcap(nid) or codec.get_raw_wcap(nid)
    self.stereo = (self.wcaps & (1 << 0)) and True or False
    self.in_amp = (self.wcaps & (1 << 1)) and True or False
    self.out_amp = (self.wcaps & (1 << 2)) and True or False
    self.amp_ovrd = (self.wcaps & (1 << 3)) and True or False
    self.format_ovrd = (self.wcaps & (1 << 4)) and True or False
    self.stripe = (self.wcaps & (1 << 5)) and True or False
    self.proc_wid = (self.wcaps & (1 << 6)) and True or False
    self.unsol_cap = (self.wcaps & (1 << 7)) and True or False
    self.conn_list = (self.wcaps & (1 << 8)) and True or False
    self.digital = (self.wcaps & (1 << 9)) and True or False
    self.power = (self.wcaps & (1 << 10)) and True or False
    self.lr_swap = (self.wcaps & (1 << 11)) and True or False
    self.cp_caps = (self.wcaps & (1 << 12)) and True or False
    self.chan_cnt_ext = (self.wcaps >> 13) & 7
    self.wdelay = (self.wcaps >> 16) & 0x0f
    self.wtype = (self.wcaps >> 20) & 0x0f
    self.channels = ((self.chan_cnt_ext << 1) | 1) + 1
    self.wtype_id = WIDGET_TYPE_IDS[self.wtype]
    if self.wtype_id == 'VOL_KNB': self.conn_list = True

    self.wcaps_list = []
    if self.stereo: self.wcaps_list.append('STEREO')
    if self.in_amp: self.wcaps_list.append('IN_AMP')
    if self.out_amp: self.wcaps_list.append('OUT_AMP')
    if self.amp_ovrd: self.wcaps_list.append('AMP_OVRD')
    if self.format_ovrd: self.wcaps_list.append('FORMAT_OVRD')
    if self.stripe: self.wcaps_list.append('STRIPE')
    if self.proc_wid: self.wcaps_list.append('PROC_WID')
    if self.unsol_cap: self.wcaps_list.append('UNSOL_CAP')
    if self.conn_list: self.wcaps_list.append('CONN_LIST')
    if self.digital: self.wcaps_list.append('DIGITAL')
    if self.power: self.wcaps_list.append('POWER')
    if self.lr_swap: self.wcaps_list.append('LR_SWAP')
    if self.cp_caps: self.wcaps_list.append('CP_CAPS')

    self.reread()
    
  def wtype_name(self):
    name = WIDGET_TYPE_NAMES[self.wtype]
    if not name:
      return "UNKNOWN Widget 0x%x" % self.wtype
    return name
    
  def wcap_name(self, id):
    return WIDGET_CAP_NAMES[id]

  def pincap_name(self, id):
    return WIDGET_PINCAP_NAMES[id]

  def name(self):
    return self.wtype_name() + " [0x%02x]" % self.nid

  def set_active_connection(self, val):
    if self.active_connection != None:
      self.codec.rw(self.nid, VERBS['SET_CONNECT_SEL'], val)
      self.active_connection = self.codec.rw(self.nid, VERBS['GET_CONNECT_SEL'], 0)
    
  def reread(self):
  
    def get_jack_location(cfg):
      bases = ["N/A", "Rear", "Front", "Left", "Right", "Top", "Bottom"]
      specials = {0x07: "Rear Panel", 0x08: "Drive Bar",
                  0x17: "Riser", 0x18: "HDMI", 0x19: "ATAPI",
                  0x37: "Mobile-In", 0x38: "Mobile-Out"}
      cfg = (cfg >> 24) & 0x3f
      if cfg & 0x0f < 7:
        return bases[cfg & 0x0f]
      if cfg in specials:
        return specials[cfg]
      return "UNKNOWN"
      
    def get_jack_connector(cfg):
      names = ["Unknown", "1/8", "1/4", "ATAPI", "RCA", "Optical",
               "Digital", "Analog", "DIN", "XLR", "RJ11", "Comb",
               None, None, None, "Oth[6~er"]
      cfg = (cfg >> 16) & 0x0f
      return names[cfg] and names[cfg] or "UNKNOWN"
      
    def get_jack_color(cfg):
      names = ["Unknown", "Black", "Grey", "Blue", "Green", "Red", "Orange",
               "Yellow", "Purple", "Pink", None, None, None, None, "White",
               "Other"]
      cfg = (cfg >> 12) & 0x0f
      return names[cfg] and names[cfg] or "UNKNOWN"
  
    self.connections = None
    self.active_connection = None
    if self.conn_list:
      self.connections = self.codec.get_connections(self.nid)
      if self.wtype_id != 'AUD_MIX':
        self.active_connection = self.codec.rw(self.nid, VERBS['GET_CONNECT_SEL'], 0)
    if self.in_amp:
      self.amp_caps_in = HDAAmpCaps(self.codec, self.nid, HDA_INPUT)
      self.amp_vals_in = HDAAmpVal(self.codec, self, HDA_INPUT)
    if self.out_amp:
      self.amp_caps_out = HDAAmpCaps(self.codec, self.nid, HDA_OUTPUT)
      self.amp_vals_out = HDAAmpVal(self.codec, self, HDA_OUTPUT)
    if self.wtype_id == 'PIN':
      jack_conns = ["Jack", "N/A", "Fixed", "Both"]
      jack_types = ["Line Out", "Speaker", "HP Out", "CD", "SPDIF Out",
                    "Digital Out", "Modem Line", "Modem Hand",
                    "Line In", "Aux", "Mic", "Telephony", "SPDIF In",
                    "Digital In", "Reserved", "Other"]
      jack_locations = ["Ext", "Int", "Sep", "Oth"]

      caps = self.codec.param_read(self.nid, PARAMS['PIN_CAP'])
      self.pincaps = caps
      self.pincap = []
      if caps & (1 << 0): self.pincap.append('IMP_SENSE')
      if caps & (1 << 1): self.pincap.append('TRIG_REQ')
      if caps & (1 << 2): self.pincap.append('PRES_DETECT')
      if caps & (1 << 3): self.pincap.append('HP_DRV')
      if caps & (1 << 4): self.pincap.append('OUT')
      if caps & (1 << 5): self.pincap.append('IN')
      if caps & (1 << 6): self.pincap.append('BALANCE')
      if caps & (1 << 7): self.pincap.append('HDMI')
      if caps & (1 << 16): self.pincap.append('EAPD')
      self.pincap_vref = []
      if caps & (1 << 8): self.pincap_vref.append('HIZ')
      if caps & (1 << 9): self.pincap_vref.append('50')
      if caps & (1 << 10): self.pincap_vref.append('GRD')
      if caps & (1 << 12): self.pincap_vref.append('80')
      if caps & (1 << 13): self.pincap_vref.append('100')
      self.reread_eapdbtl()
      caps = self.codec.rw(self.nid, VERBS['GET_CONFIG_DEFAULT'], 0)
      self.defcfg_pincaps = caps
      self.jack_conn_name = jack_conns[(caps >> 30) & 0x03]
      self.jack_type_name = jack_types[(caps >> 20) & 0x0f]
      self.jack_location_name = jack_locations[(caps >> 28) & 0x03]
      self.jack_location2_name = get_jack_location(caps)
      self.jack_connector_name = get_jack_connector(caps)
      self.jack_color_name = get_jack_color(caps)
      self.defcfg_assoc = (caps >> 4) & 0x0f
      self.defcfg_sequence = (caps >> 0) & 0x0f
      self.defcfg_misc = []
      if caps & (1 << 8): self.defcfg_misc.append('NO_PRESENCE')
      self.reread_pin_widget_control()
    elif self.wtype_id == 'VOL_KNB':
      cap = self.codec.param_read(self.nid, PARAMS['VOL_KNB_CAP'])
      self.vol_knb_delta = (cap >> 7) & 1
      self.vol_knb_steps = cap & 0x7f
      self.reread_vol_knb()
    elif self.wtype_id in ['AUD_IN', 'AUD_OUT']:
      conv = self.codec.rw(self.nid, VERBS['GET_CONV'], 0)
      self.aud_stream = (conv >> 4) & 0x0f
      self.aud_channel = (conv >> 0) & 0x0f
      self.reread_sdi_select()
      self.reread_dig1()
      if self.format_ovrd:
        pcm = self.codec.param_read(self.nid, PARAMS['PCM'])
        stream = self.codec.param_read(self.nid, PARAMS['STREAM'])
        self.pcm_rate = pcm & 0xffff
        self.pcm_rates = self.codec.analyze_pcm_rates(self.pcm_rate)
        self.pcm_bit = pcm >> 16
        self.pcm_bits = self.codec.analyze_pcm_bits(self.pcm_bit)
        self.pcm_stream = stream
        self.pcm_streams = self.codec.analyze_pcm_streams(self.pcm_stream)
    elif self.wtype_id in ['PROC_WID']:
      proc_caps = self.codec.param_read(self.nid, PARAMS['PROC_CAP'])
      self.proc_benign = proc_caps & 1 and True or False
      self.proc_numcoef = (proc_caps >> 8) & 0xff
    if self.unsol_cap:
      unsol = self.codec.rw(self.nid, VERBS['GET_UNSOLICITED_RESPONSE'], 0)
      self.unsol_tag = unsol & 0x3f
      self.unsol_enabled = (unsol & (1 << 7)) and True or False
    if self.power:
      states = ["D0", "D1", "D2", "D3"]
      pwr = self.codec.rw(self.nid, VERBS['GET_POWER_STATE'], 0)
      self.pwr_setting = pwr & 0x0f
      self.pwr_actual = (pwr >> 4) & 0x0f
      self.pwr_setting_name = self.pwr_setting < 4 and states[self.pwr_setting] or "UNKNOWN"
      self.pwr_actual_name = self.pwr_actual < 4 and states[self.pwr_actual] or "UNKNOWN"
    # NID 0x20 == Realtek Define Registers
    if self.codec.vendor_id == 0x10ec and self.nid == 0x20:
      self.realtek_coeff_proc = self.codec.rw(self.nid, VERBS['GET_PROC_COEF'], 0)
      self.realtek_coeff_index = self.codec.rw(self.nid, VERBS['GET_COEF_INDEX'], 0)

  def reread_eapdbtl(self):
    self.pincap_eapdbtl = []
    self.pincap_eapdbtls = 0
    if not 'EAPD' in self.pincap:
      return
    val = self.codec.rw(self.nid, VERBS['GET_EAPD_BTLENABLE'], 0)
    self.pincap_eapdbtls = val
    for name in EAPDBTL_BITS:
      bit = EAPDBTL_BITS[name]
      if val & (1 << bit): self.pincap_eapdbtl.append(name)

  def eapdbtl_set_value(self, name, value):
    mask = 1 << EAPDBTL_BITS[name]
    if value:
      self.pincap_eapdbtls |= mask
    else:
      self.pincap_eapdbtls &= ~mask
    self.codec.rw(self.nid, VERBS['SET_EAPD_BTLENABLE'], self.pincap_eapdbtls)
    self.reread_eapdbtl()

  def reread_pin_widget_control(self):
    pinctls = self.codec.rw(self.nid, VERBS['GET_PIN_WIDGET_CONTROL'], 0)
    self.pinctls = pinctls
    self.pinctl = []
    for name in PIN_WIDGET_CONTROL_BITS:
      bit = PIN_WIDGET_CONTROL_BITS[name]
      if pinctls & (1 << bit): self.pinctl.append(name)
    self.pinctl_vref = None
    if self.pincap_vref:
      self.pinctl_vref = PIN_WIDGET_CONTROL_VREF[pinctls & 0x07]

  def pin_widget_control_set_value(self, name, value):
    if name in PIN_WIDGET_CONTROL_BITS:
      mask = 1 << PIN_WIDGET_CONTROL_BITS[name]
      if value:
        self.pinctls |= mask
      else:
        self.pinctls &= ~mask
    elif name == 'vref' and self.pincap_vref:
      idx = PIN_WIDGET_CONTROL_VREF.index(value)
      self.pinctls &= ~0x07
      self.pinctls |= idx
    self.codec.rw(self.nid, VERBS['SET_PIN_WIDGET_CONTROL'], self.pinctls)
    self.reread_pin_widget_control()

  def reread_vol_knb(self):
    cap = self.codec.rw(self.nid, VERBS['GET_VOLUME_KNOB_CONTROL'], 0)
    self.vol_knb = cap
    self.vol_knb_direct = (cap >> 7) & 1
    self.vol_knb_val = cap & 0x7f
    
  def vol_knb_set_value(self, name, value):
    if name == 'direct':
      if value:
        self.vol_knb |= (1 << 7)
      else:
        self.vol_knb &= ~(1 << 7)
    elif name == 'value':
      self.vol_knb &= 0x7f
      self.vol_knb |= value
    self.codec.rw(self.nid, VERBS['SET_VOLUME_KNOB_CONTROL'], self.vol_knb)
    self.reread_vol_knb() 

  def reread_sdi_select(self):
    self.sdi_select = None
    if self.wtype_id == 'AUD_IN' and self.aud_channel == 0:
      sdi = self.codec.rw(self.nid, VERBS['GET_SDI_SELECT'], 0)
      self.sdi_select = sdi & 0x0f

  def sdi_select_set_value(self, value):
    if self.sdi_select != None:
      self.sdi_select = value & 0x0f
      self.codec.rw(self.nid, VERBS['SET_SDI_SELECT'], self.sdi_select)
      self.reread_sdi_select()

  def reread_dig1(self):
    self.dig1 = []
    self.dig1_category = None
    if not self.digital:
      return
    digi1 = self.codec.rw(self.nid, VERBS['GET_DIGI_CONVERT_1'], 0)
    self.digi1 = digi1
    for name in DIG1_BITS:
      bit = DIG1_BITS[name]
      if digi1 & (1 << bit): self.dig1.append(name)
    self.dig1_category = (digi1 >> 8) & 0x7f

  def dig1_set_value(self, name, value):
    if name == 'category':
      self.digi1 &= 0x7f00
      self.digi1 |= (value & 0x7f) << 8
    else:
      mask = DIG1_BITS[name]
      if value:
        self.digi1 |= mask
      else:
        self.digi1 &= ~mask
    self.codec.rw(self.nid, VERBS['SET_DIGI_CONVERT_1'], self.digi1)
    

class HDAGPIO:

  def __init__(self, codec, nid):
    self.codec = codec
    self.nid = nid
    self.reread()

  def reread(self):
    self.val = {}
    for i in GPIO_IDS:
      self.val[i] = self.codec.rw(self.nid, GPIO_IDS[i][0], 0)

  def test(self, name, bit):
    return (self.val[name] & (1 << bit)) and True or False

  def read(self, name):
    self.val[i] = self.codec.rw(nid, GPIO_IDS[name][0], 0)

  def write(self, name):
    self.val[i] = self.codec.rw(nid, GPIO_IDS[name][1], self.val[i])

  def set(self, name, bit, val):
    old = self.test(name, bit)
    if val:
      self.val[name] |= 1 << bit
    else:
      self.val[name] &= 1 << bit
    if old == self.test(name, bit):
      return
    self.write(name)

class HDACodec:

  afg = None
  mfg = None
  vendor_id = None
  subsystem_id = None
  revision_id = None

  def __init__(self, card=0, device=0):
    self.card = card
    self.device = device
    self.fd = os.open("/dev/snd/hwC%sD%s" % (card, device), os.O_RDWR)
    info = struct.pack('Ii64s80si64s', 0, 0, '', '', 0, '')
    res = ioctl(self.fd, IOCTL_INFO, info)
    name = struct.unpack('Ii64s80si64s', res)[3]
    if not name.startswith('HDA Codec'):
      raise IOError, "unknown HDA hwdep interface"
    res = ioctl(self.fd, IOCTL_PVERSION, struct.pack('I', 0))
    self.version = struct.unpack('I', res)
    if self.version < 0x00010000:	# 1.0.0
      raise IOError, "unknown HDA hwdep version"

  def rw(self, nid, verb, param):
    """do elementary read/write operation"""
    verb = (nid << 24) | (verb << 8) | param
    res = ioctl(self.fd, IOCTL_VERB_WRITE, struct.pack('II', verb, 0))
    return struct.unpack('II', res)[1]
    
  def get_wcap(self, nid):
    """get cached widget capabilities"""
    res = ioctl(self.fd, IOCTL_GET_WCAPS, struct.pack('II', nid << 24, 0))
    return struct.unpack('II', res)[1]

  def get_raw_wcap(self, nid):
    """get raw widget capabilities"""
    return self.rw(nid, VERBS['PARAMETERS'], PARAMS['AUDIO_WIDGET_CAP'])

  def param_read(self, nid, param):
    """read perameters"""
    return self.rw(nid, VERBS['PARAMETERS'], param)

  def get_sub_nodes(self, nid):
    """return sub-nodes count (returns count and start NID)"""
    res = self.param_read(nid, PARAMS['NODE_COUNT'])
    return res & 0x7fff, (res >> 16) & 0x7fff

  def get_connections(self, nid):
    """parses connection list and returns the array of NIDs"""
    parm = self.param_read(nid, PARAMS['CONNLIST_LEN'])
    if parm & (1 << 7):		# long
      shift = 16
      num_elems = 2
    else:			# short
      shift = 8
      num_elems = 4
    conn_len = parm & 0x7f
    mask = (1 << (shift - 1)) - 1
    if not conn_len:
      return None
    if conn_len == 1:
      parm = self.rw(nid, VERBS['GET_CONNECT_LIST'], 0)
      return [parm & mask]
    res = []
    prev_nid = 0
    for i in range(conn_len):
      if i % num_elems == 0:
        parm = self.rw(nid, VERBS['GET_CONNECT_LIST'], i)
      range_val = parm & (1 << (shift - 1))
      val = parm & mask
      parm >>= shift
      if range_val:
        if not prev_nid or prev_nid >= val:
          raise IOError, "invalid dep_range_val 0x%x:0x%x\n" % (prev_nid, val)
        n = prev_nid + 1
        while n <= val:
          res.append(n)
          n += 1
      else:
        res.append(val)
      prev_nid = val
    return res

  def analyze_root_nodes(self):
    self.afg = None
    self.mfg = None
    self.vendor_id = self.param_read(AC_NODE_ROOT, PARAMS['VENDOR_ID'])
    self.subsystem_id = self.param_read(AC_NODE_ROOT, PARAMS['SUBSYSTEM_ID'])
    self.revision_id = self.param_read(AC_NODE_ROOT, PARAMS['REV_ID'])

    total, nid = self.get_sub_nodes(AC_NODE_ROOT)
    for i in range(total):
      func = self.param_read(nid, PARAMS['FUNCTION_TYPE'])
      if (func & 0xff) == 0x01:		# audio group
        self.afg = nid
      elif (func & 0xff) == 0x02:	# modem group
        self.mfg = nid
      else:
        break
      nid += 1

    if self.subsystem_id == 0:
      self.subsystem_id = self.rw(self.afg and self.afg or self.mfg,
                                  VERBS['GET_SUBSYSTEM_ID'], 0)

    pcm = self.param_read(self.afg, PARAMS['PCM'])
    self.pcm_rate = pcm & 0xffff
    self.pcm_rates = self.analyze_pcm_rates(self.pcm_rate)
    self.pcm_bit = pcm >> 16
    self.pcm_bits = self.analyze_pcm_bits(self.pcm_bit)

    self.pcm_stream = self.param_read(self.afg, PARAMS['STREAM'])
    self.pcm_streams = self.analyze_pcm_streams(self.pcm_stream)

    self.amp_caps_in = HDAAmpCaps(self, self.afg, HDA_INPUT)
    self.amp_caps_out = HDAAmpCaps(self, self.afg, HDA_OUTPUT)

    self.gpio_cap = self.param_read(self.afg, PARAMS['GPIO_CAP'])
    self.gpio_max = self.gpio_cap & 0xff
    self.gpio_o = (self.gpio_cap >> 8) & 0xff
    self.gpio_i = (self.gpio_cap >> 16) & 0xff
    self.gpio_unsol = (self.gpio_cap >> 30) & 1 and True or False
    self.gpio_wake = (self.gpio_cap >> 31) & 1 and True or False
    self.gpio = HDAGPIO(self, self.afg)

    self.nodes, self.base_nid = self.get_sub_nodes(self.afg)

  def analyze_pcm_rates(self, pcm):
    rates = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200,
             96000, 176400, 192000, 384000]
    res = []
    for i in range(len(rates)):
      if pcm & (1 << i):
        res.append(rates[i])
    return res

  def analyze_pcm_bits(self, bit):
    bits = [8, 16, 20, 24, 32]
    res = []
    for i in range(len(bits)):
      if bit & (1 << i):
        res.append(bits[i])
    return res

  def analyze_pcm_streams(self, stream):
    res = []
    if stream & 0x01: res.append("PCM")
    if stream & 0x02: res.append("FLOAT")
    if stream & 0x04: res.append("AC3")
    return res

  def dump(self):

    def print_pcm_rates(node):
      s = ''
      for i in node.pcm_rates:
        s += " %d" % i
      return "    rates [0x%x]:%s\n" % (node.pcm_rate, s)
      
    def print_pcm_bits(node):
      s = ''
      for i in node.pcm_bits:
        s += " %d" % i
      return "    bits [0x%x]:%s\n" % (node.pcm_bit, s)
    
    def print_pcm_formats(node):
      str = "    formats [0x%x]:" % node.pcm_stream
      for i in node.pcm_streams:
        str += " %s" % i
      return str + "\n"

    def print_pcm_caps(node):
      str = print_pcm_rates(node)
      str += print_pcm_bits(node)
      return str + print_pcm_formats(node)
      
    def print_gpio(node):
      gpio = node.gpio_cap
      str = 'GPIO: io=%d, o=%d, i=%d, unsolicited=%d, wake=%d\n' % \
            (node.gpio_max, node.gpio_o, node.gpio_i,
             node.gpio_unsol and 1 or 0, node.gpio_wake and 1 or 0)
      for i in range(node.gpio_max):
        str += '  IO[%d]: enable=%d, dir=%d, wake=%d, sticky=%d, ' \
               'data=%d, unsol=%d\n' % (i, 
                node.gpio.test('enable', i) and 1 or 0,
                node.gpio.test('direction', i) and 1 or 0,
                node.gpio.test('wake', i) and 1 or 0,
                node.gpio.test('sticky', i) and 1 or 0,
                node.gpio.test('data', i) and 1 or 0,
                node.gpio.test('unsol', i) and 1 or 0)
      return str

    def print_amp_caps(caps):
      if caps.ofs == None:
        return "N/A\n"
      return "ofs=0x%02x, nsteps=0x%02x, stepsize=0x%02x, mute=%x\n" % \
              (caps.ofs, caps.nsteps, caps.stepsize, caps.mute and 1 or 0)

    if not self.afg and not self.mfg:
      self.analyze_root_nodes()
    str = 'Vendor Id: 0x%x\n' % self.vendor_id
    str += 'Subsystem Id: 0x%x\n' % self.subsystem_id
    str += 'Revision Id: 0x%x\n' % self.revision_id
    if self.mfg:
      str += 'Modem Function Group: 0x%x\n' % self.mfg
    else:
      str += 'No Modem Function Group found\n'
    if not self.afg: return str
    str += 'Default PCM:\n'
    str += print_pcm_caps(self)
    str += 'Default Amp-In caps: '
    str += print_amp_caps(self.amp_caps_in)
    str += 'Default Amp-Out caps: '
    str += print_amp_caps(self.amp_caps_out)
    
    if self.base_nid == 0 or self.nodes < 0:
      str += 'Invalid AFG subtree\n'
      return str
    
    str += print_gpio(self)
    
    nid = self.base_nid
    for i in range(self.nodes):
      s, n = self.dump_node(nid)
      str += s
      nid += 1
    
    return str

  def dump_node(self, nid):

    def print_pcm_rates(node):
      s = ''
      for i in node.pcm_rates:
        s += " %d" % i
      return "    rates [0x%x]:%s\n" % (node.pcm_rate, s)
      
    def print_pcm_bits(node):
      s = ''
      for i in node.pcm_bits:
        s += " %d" % i
      return "    bits [0x%x]:%s\n" % (node.pcm_bit, s)
    
    def print_pcm_formats(node):
      str = "    formats [0x%x]:" % node.pcm_stream
      for i in node.pcm_streams:
        str += " %s" % i
      return str + "\n"

    def print_pcm_caps(node):
      str = print_pcm_rates(node)
      str += print_pcm_bits(node)
      return str + print_pcm_formats(node)
      
    def print_audio_io(node):
      str = "  Converter: stream=%d, channel=%d\n" % (node.aud_stream, node.aud_channel)
      if node.sdi_select != None:
        str += "  SDI-Select: %d\n" % node.sdi_select
      return str
      
    def print_amp_caps(caps):
      if caps.ofs == None:
        return "N/A\n"
      return "ofs=0x%02x, nsteps=0x%02x, stepsize=0x%02x, mute=%x\n" % \
              (caps.ofs, caps.nsteps, caps.stepsize, caps.mute and 1 or 0)

    def print_amp_vals(vals):
      str = ''
      idx = 0
      for val in vals.vals:
        if vals.stereo and (idx & 1) == 0:
          str += " [0x%02x" % val
        else:
          str += " 0x%02x" % val
        if vals.stereo and (idx & 1) != 0: str += "]"
        idx += 1
      return str + '\n'
      
    def print_pin_caps(node):
      str = "  Pincap 0x%08x:" % node.pincaps
      if 'IN' in node.pincap: str += " IN"
      if 'OUT' in node.pincap: str += " OUT"
      if 'HP_DRV' in node.pincap: str += " HP"
      if 'EAPD' in node.pincap: str += " EAPD"
      if 'PRES_DETECT' in node.pincap: str += " Detect"
      if 'BALANCE' in node.pincap: str += " Balance"
      if 'HDMI' in node.pincap:
        if (self.vendor_id >> 16) == 0x10ec:	# Realtek has different meaning
          str += " (Realtek)R/L"
        else:
          str += " HDMI"
      if 'TRIG_REQ' in node.pincap: str += " Trigger"
      if 'IMP_SENSE' in node.pincap: str += " ImpSense"
      str += '\n'
      if node.pincap_vref:
        str += "    Vref caps:"
        if 'HIZ' in node.pincap_vref: str += " HIZ"
        if '50' in node.pincap_vref: str += " 50"
        if 'GRD' in node.pincap_vref: str += " GRD"
        if '80' in node.pincap_vref: str += " 80"
        if '100' in node.pincap_vref: str += " 100"
        str += '\n'
      if 'EAPD' in node.pincap:
        str += "  EAPD 0x%x:" % node.pincap_eapdbtls
        if 'BALANCED' in node.pincap_eapdbtl: str += " BALANCED"
        if 'EAPD' in node.pincap_eapdbtl: str += " EAPD"
        if 'LR_SWAP' in node.pincap_eapdbtl: str += " R/L"
        str += '\n'
      str += "  Pin Default 0x%08x: [%s] %s at %s %s\n" % (node.defcfg_pincaps,
              node.jack_conn_name,
              node.jack_type_name,
              node.jack_location_name,
              node.jack_location2_name)
      str += "    Conn = %s, Color = %s\n" % (node.jack_connector_name,
              node.jack_color_name)
      str += "    DefAssociation = 0x%x, Sequence = 0x%x\n" % \
              (node.defcfg_assoc, node.defcfg_sequence)
      if 'NO_PRESENCE' in node.defcfg_misc:
        str += "    Misc = NO_PRESENCE\n"
      if node.pinctl:
        str += "  Pin-ctls: 0x%02x:" % node.pinctls
        if 'IN' in node.pinctl: str += " IN"
        if 'OUT' in node.pinctl: str += " OUT"
        if 'HP' in node.pinctl: str += " HP"
        if node.pincap_vref:
          str += " VREF_%s" % node.pinctl_vref
        str += '\n'
      return str

    def print_vol_knob(node):
      str = "  Volume-Knob: delta=%d, steps=%d, " % (node.vol_knb_delta, node.vol_knb_steps)
      return str + "direct=%d, val=%d\n" % (node.vol_knb_direct, node.vol_knb_val)

    def print_unsol_cap(node):
      return "  Unsolicited: tag=0x%02x, enabled=%d\n" % (node.unsol_tag, node.unsol_enabled and 1 or 0)

    def print_power_state(node):
      return "  Power: setting=%s, actual=%s\n" % (node.pwr_setting_name, node.pwr_actual_name)

    def print_digital_conv(node):
      str = "  Digital:"
      if 'ENABLE' in node.dig1: str += " Enabled"
      if 'VALIDITY' in node.dig1: str += " Validity"
      if 'VALIDITYCFG' in node.dig1: str += " ValidityCfg"
      if 'EMPHASIS' in node.dig1: str += " Preemphasis"
      if 'COPYRIGHT' in node.dig1: str += " Copyright"
      if 'NONAUDIO' in node.dig1: str += " Non-Audio"
      if 'PROFESSIONAL' in node.dig1: str += " Pro"
      if 'GENLEVEL' in node.dig1: str += " GetLevel"
      str += "\n"
      return str + "  Digital category: 0x%x\n" % ((node.dig1_category >> 8) & 0x7f)

    def print_conn_list(node):
      str = "  Connection: %d\n" % (node.connections and len(node.connections) or 0)
      if node.connections:
        str += "    "
        for i in range(len(node.connections)):
          str += " 0x%02x" % node.connections[i]
          if i == node.active_connection and len(node.connections) > 1:
            str += "*"
        str += '\n'
      return str

    def print_proc_caps(node):
      return "  Processing caps: benign=%d, ncoeff=%d\n" % (node.proc_benign, node.proc_nuncoef)

    def print_realtek_coef(node):
      str = "  Processing Coefficient: 0x%02x\n" % node.realtek_coeff_proc
      return str + "  Coefficient Index: 0x%02x\n" % node.realtek_coeff_index

    node = HDANode(self, nid)
    str = "Node 0x%02x [%s] wcaps 0x%x:" % (nid, node.wtype_name(), node.wcaps)
    if node.stereo:
      str += node.channels == 2 and " Stereo" or " %d-Channels" % node.channels
    else:
      str += " Mono"
    if node.digital: str += " Digital"
    if node.in_amp: str += " Amp-In"
    if node.out_amp: str += " Amp-Out"
    if node.stripe: str += " Stripe"
    if node.lr_swap: str += " R/L"
    if node.cp_caps: str += " CP"
    str += '\n'
    if node.in_amp:
      str += "  Amp-In caps: "
      str += print_amp_caps(node.amp_caps_in)
      str += "  Amp-In vals:"
      str += print_amp_vals(node.amp_vals_in)
    if node.out_amp:
      str += "  Amp-Out caps: "
      str += print_amp_caps(node.amp_caps_out)
      str += "  Amp-Out vals:"
      str += print_amp_vals(node.amp_vals_out)
      
    if node.wtype_id == 'PIN':
      str += print_pin_caps(node)
    elif node.wtype_id == 'VOL_KNB':
      str += print_vol_knob(node)
    elif node.wtype_id in ['AUD_IN', 'AUD_OUT']:
      str += print_audio_io(node)
      if node.digital:
        str += print_digital_conv(node)
      if node.format_ovrd:
        str += "  PCM:\n"
        str += print_pcm_caps(node)
    if node.unsol_cap:
      str += print_unsol_cap(node)
    if node.power:
      str += print_power_state(node)
    if node.wdelay:
      str += "  Delay: %d samples\n" % node.wdelay
    if node.conn_list:
      str += print_conn_list(node)
    if node.wtype_id == 'PROC_WID':
      str += print_proc_caps(node)
    if hasattr(node, 'realtek_coeff_proc'):
      str += print_realtek_coef(node)
    return str, node

if __name__ == '__main__':
  v = HDACodec()
  v.analyze_root_nodes()
  print "vendor_id = 0x%x, subsystem_id = 0x%x, revision_id = 0x%x" % (v.vendor_id, v.subsystem_id, v.revision_id)
  print "afg = %s, mfg = %s" % (v.afg and "0x%x" % v.afg or 'None', v.mfg and "0x%x" % v.mfg or 'None')
  print
  print
  print v.dump()[:-1]
