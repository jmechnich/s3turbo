class StandardHandler(object):
    def __init__(self,debug=False):
        self.debug = debug
        
        self.status_bytes = {
            0x8: "Note Off",
            0x9: "Note On",
            0xA: "Polyphonic Aftertouch",
            0xB: "Controller",
            0xC: "Program Change",
            0xD: "Monophonic Aftertouch",
            0xE: "Pitch Bend",
            0xF: "System",
        }

        self.controller_numbers = {
            0x00: "Bank Select, MSB",
            0x01: "Modulation Wheel",
            0x02: "Breath Controller",
            0x04: "Foot Controller",
            0x05: "Portamento time",
            0x06: "Data Entry, MSB",
            0x07: "Channel Volume",
            0x08: "Balance",
            0x0A: "Pan",
            0x0B: "Expression Controller",
            0x0C: "Effect Control 1", 
            0x0D: "Effect Control 2",
            0x40: "Damper Pedal (sustain)",
            0x41: "Portamento On/Off",
            0x42: "Sostenuto",
            0x43: "Soft pedal",
            0x44: "Legato footswitch",
            0x45: "Hold 2",
            0x54: "Portamento Control",
            0x60: "Data Increment",
            0x61: "Data Decrement",
            0x62: "Non-registered Parameter number, LSB",
            0x63: "Non-registered Parameter number, MSB",
            0x64: "Registered Parameter number, LSB",
            0x65: "Registered Parameter number, MSB",
            0x79: "Reset All Controllers",
            0x7a: "Local Control",
            0x7b: "All Notes Off",
            0x7c: "Omni Off",
            0x7d: "Omni On",
            0x7e: "Mono On (Poly Off)",
            0x7f: "Poly On (Mono Off)",
        }
        for i in xrange(0x10,0x14):
            self.controller_numbers[i] = "General Purpose Controller %d" % \
                                         (i-0xf)
        for i in xrange(0x20,0x40):
            self.controller_numbers[i] = "LSB for Controller %d" % (i-0x20)
        for i in xrange(0x46,0x50):
            self.controller_numbers[i] = "Sound Controller %d" % (i-0x46)
        for i in xrange(0x50,0x54):
            self.controller_numbers[i] = "General Purpose Controller %d" % \
                                         (i-0x4b)
        for i in xrange(0x5b,0x60):
            self.controller_numbers[i] = "Effect %d Depth" % (i-0x5a)

        self.maxwidth = max([
            len(i) for i in self.controller_numbers.itervalues() ])

    def prettyPrint(self,start,channel,text,value):
        print "%-17s, chan %2d: %s %3d" % \
            (start,channel,text.ljust(self.maxwidth),value)
        
    def handle(self,msg,timestamp):
        type = msg[0] >> 4
        if type == 0xb:
            return self.handleControllerMsg(msg,timestamp)
        elif type == 0xc:
            return self.handleProgramChange(msg,timestamp)

        return self.handleDefault(msg,timestamp)

    def handleControllerMsg(self,msg,timestamp):
        channel    = msg[0] & 0xf
        controller = msg[1]
        name       = self.controller_numbers.get(controller,"Undefined")
        name = name.ljust(self.maxwidth)
        value      = msg[2]
        self.prettyPrint("Controller change",channel,name,value)
        return True

    def handleProgramChange(self,msg,timestamp):
        channel = msg[0] & 0xf
        value   = msg[1]
        self.prettyPrint("Program change",channel,"Program Number",value)
        return True
    
    def handleDefault(self,msg,timestamp):
        for k,v in self.status_bytes.iteritems():
            if msg[0] >> 4 == k:
                print "Received", v, ":", timestamp, [
                    hex(b) for b in msg ]
                break
        else:
            print "Received", timestamp, [
                hex(b) for b in msg ]
        return True
    
