import sys
import math
import random

global accurate_mixing # only tested for Mario and Donkey Kong: Minis on the Move
accurate_mixing = True
global combined_volume # for programs such as FL Studio which do not include expression
combined_volume = False

global failed_return_end # failsafe incase of incorrectly managed sequence files (such as songs from Mario and Donkey Kong: Minis on the Move)
failed_return_end = True
global ignore_jump # includes unused portions of some songs (such as songs from Mario and Donkey Kong: Minis on the Move). Disabling breaks SMF_LuigiSings_SR
ignore_jump = True
global past_jump_end # breaks out of infinite loops
past_jump_end = True

def hexarray(array):
    return '[{}]'.format(', '.join(hex(x) for x in array))

def header_common(header, length):
    print(f'--------{header.decode()}--------')

    if seq.read(4) == header:
        print(f'{header.decode()} detected')
    else:
        seq.seek(seq.tell() - 4)
        print(f'\033[91mERROR: expected header {header.decode()} but got header {seq.read(4).decode()} at {hex(seq.tell() - 4)}\033[0m')
        quit()
    
    if int.from_bytes(seq.read(4), endian) == length:
        print(f'length {length}')
    else:
        seq.seek(seq.tell() - 4)
        print(f'\033[91mERROR: expected length {length} but got length {int.from_bytes(seq.read(4), endian)} at {hex(seq.tell() - 4)}\033[0m')
        quit()
    
    if seqtype == b'SSEQ' or seqtype == b'RSEQ':
        SEQ_sectionamounts.append(seq.read(4))

def checktick(i):
    global tick
    global nexttick

    if nexttick > tick:
        tick += 1

        while notestick and tick >= notestick[0]:
            write_wait()
            mid.write(notescommand[0])
            notestick.pop(0)
            notescommand.pop(0)
    else:
        byte = seq.read(1)
        SEQ_sectionlengths[i] -= 1
        parse_command(byte, i)

def write_wait():
    global mid
    global waitamount
    global waittick
    global tick

    waitedamount = tick - waittick # how much has been waited so far
    
    mid.seek(mid.tell() - 1)
    
    if waitedamount < 0x80:
        mid.write((waitedamount).to_bytes(1))
    elif waitedamount < 0x4000:
        mid.write((0x80 + (waitedamount >> 7)).to_bytes(1))
        mid.write((waitedamount & 0x7F).to_bytes(1))
    else:
        mid.write((0x80 + (waitedamount >> 14)).to_bytes(1))
        mid.write((0x80 + (waitedamount >> 7 & 0x7F)).to_bytes(1))
        mid.write((waitedamount & 0x7F).to_bytes(1))
    
    waittick = tick
    waitamount -= waitedamount

def parse_command(byte, i):
    global tick
    global nexttick
    global channel
    global opentracknumber
    global opentrackoffset
    global callreturn
    global waittick
    global waitamount
    global notestick
    global notescommand
    global headeroffset
    global allocated
    
    global done
    
    locationint = seq.tell() - 1
    location = hex(locationint)
    
    match byte:
        case b'\x80': # wait
            value = int.from_bytes(seq.read(1))
            
            if value > 0x7F:
                value = value - 0x80 << 7
                value += int.from_bytes(seq.read(1))
            
            print(f'{location}: wait {value}')
            
            nexttick += value
            waitamount += value
            
        case b'\x81': # set instrument
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            if value > 0x7F:
                value = value - 0x80 << 7
                value += int.from_bytes(seq.read(1))
            
            print(f'{location}: instrument {value}')
            
            mid.write((0xC0 + channel).to_bytes(1))
            mid.write((value).to_bytes(1))
            mid.write(b'\x00')
            
        case b'\x88': # open track
            hDATA_tracknumbers.append(int.from_bytes(seq.read(1)))
            hDATA_trackoffsets.append(int.from_bytes(seq.read(3), endianalt) + SEQ_sectionoffsets[i] + headeroffset)
            
            print(f'{location}: track {hDATA_tracknumbers[len(hDATA_tracknumbers) - 1]} at {hex(hDATA_trackoffsets[len(hDATA_trackoffsets) - 1])}')
            
            opentracknumber.append(hDATA_tracknumbers[len(hDATA_tracknumbers) - 1])
            opentrackoffset.append(hDATA_trackoffsets[len(hDATA_trackoffsets) - 1])
            
        case b'\x89': # jump
            value = int.from_bytes(seq.read(3), endianalt) + SEQ_sectionoffsets[i] + headeroffset
            
            print(f'{location}: jump {hex(value)}')
            
            if not ignore_jump:
                if past_jump_end and value < seq.tell():
                    print(f'loop detected!')
                    
                    write_wait()
                    
                    mid.write(b'\xFF\x2F\x00')
                    
                    waittick = 0
                    waitamount = 0
                    
                    if len(opentracknumber) > 0:
                        channel = opentracknumber.pop(0)
                        seq.seek(opentrackoffset.pop(0))
                    else:
                        done = True
                else:
                    seq.seek(value)
                    get_label(i)
            
        case b'\x8A': # call
            value = int.from_bytes(seq.read(3), endianalt) + SEQ_sectionoffsets[i] + headeroffset
            
            print(f'{location}: call {hex(value)}')
            
            callreturn.append(seq.tell())
            seq.seek(value)
            get_label(i)
            
        case b'\x93': # open track (SSEQ)
            hDATA_tracknumbers.append(int.from_bytes(seq.read(1)))
            hDATA_trackoffsets.append(int.from_bytes(seq.read(3), endian) + SEQ_sectionoffsets[i] + headeroffset)
            
            print(f'{location}: track {hDATA_tracknumbers[len(hDATA_tracknumbers) - 1]} at {hex(hDATA_trackoffsets[len(hDATA_trackoffsets) - 1])}')
            
            opentracknumber.append(hDATA_tracknumbers[len(hDATA_tracknumbers) - 1])
            opentrackoffset.append(hDATA_trackoffsets[len(hDATA_trackoffsets) - 1])
            
        case b'\x94': # jump? (SSEQ)
            print(f'{location}: jump? {int.from_bytes(seq.read(3), endianalt)} (not implemented)')
            
        case b'\x95': # call (SSEQ)
            value = int.from_bytes(seq.read(3), endian) + SEQ_sectionoffsets[i] + headeroffset
            
            print(f'{location}: call {hex(value)}')
            
            callreturn.append(seq.tell())
            seq.seek(value)
            
        case b'\xA0': # random? found in warioware smooth moves SMF_dribble_song_ng_full_us
            command = seq.read(1) # TODO: figure out a way to make this work with any command
            valuelow = int.from_bytes(seq.read(2), endian)
            valuehigh = int.from_bytes(seq.read(2), endian)
            
            if valuelow > 0x8000:
                valuelow -= 0x10000
            if valuehigh > 0x8000:
                valuehigh -= 0x10000
            
            random.seed(locationint)
            value = random.randint(valuelow, valuehigh)
            
            print(f'{location}: random {command}, range from {valuelow} to {valuehigh}, random value: {value}')
            
            if command == b'\xC0':
                write_wait()
                
                if accurate_mixing: value = round(value + (8 * math.sin((math.pi * value) / 64)))
                midi_cc(channel, 0x0A, value)
            
            if command == b'\xC3':
                write_wait()
                
                value += 12
                value = round(value * (16384 / 24))
                
                # set pitch bend range to 12
                midi_cc(channel, 0x65, 0)
                midi_cc(channel, 0x64, 0)
                midi_cc(channel, 0x06, 12)
                
                mid.write((0xE0 + channel).to_bytes(1))
                mid.write((value & 0x7F).to_bytes(1))
                mid.write((value >> 7).to_bytes(1))
                mid.write(b'\x00')
            
        case b'\xA2': # UNKNOWN, SMF_LuigiSings_SR
            print(f'{location}: UNKNOWN A2')
            seq.read(4)
            
        case b'\xA3': # UNKNOWN found in nsmbw 0x70E40
            print(f'{location}: UNKNOWN A3')
            seq.read(4)
            
        case b'\xB0': # timebase, UNKNOWN (SSEQ)
            if seqtype != b'SSEQ':
                value = seq.read(1)
                
                print(f'{location}: timebase {int.from_bytes(value)}')
                
                temp = mid.tell()
                mid.seek(0x0D)
                mid.write(value)
                mid.seek(temp)
            else: # UNKNOWN, mkds F780
                print(f'{location}: UNKNOWN B0 (SSEQ)')
                seq.read(1)
            
        case b'\xB4': # UNKNOWN found in nsmbw 0x70E40
            print(f'{location}: UNKNOWN B4')
            seq.read(5)
            
        case b'\xB6': # set bank
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: bank {value}')
            
            midi_cc(channel, 0x00, value)
            
        case b'\xC0': # set panning
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: pan {value}')
            
            if accurate_mixing: value = round(value + (8 * math.sin((math.pi * value) / 64))) # duno why it does this but it sounds right for minis on the move
            midi_cc(channel, 0x0A, value)
            
        case b'\xC1': # set volume
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: volume {value}')
            
            if combined_volume:
                volumeC1[channel] = value / 0x7F
                value = round(volumeC1[channel] * volumeC2[channel] * volumeD5[channel] * 0x7F)
            midi_cc(channel, 0x07, value)
            
        case b'\xC2': # master volume, wwt 358A0
            print(f'{location}: master volume? {int.from_bytes(seq.read(1))} (not implemented)')
            
        case b'\xC3': # transpose, SMF_dribble_song_ng_full_us
            print(f'{location}: transpose {int.from_bytes(seq.read(1))} (not implemented)')
            
        case b'\xC4': # pitch bend
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: pitch {value}')
            
            if value < 0x80:
                temp = value + 0x80 << 6
            else:
                temp = value - 0x80 << 6
            
            mid.write((0xE0 + channel).to_bytes(1))
            mid.write((temp & 0x7F).to_bytes(1))
            mid.write((temp >> 7).to_bytes(1))
            mid.write(b'\x00')
            
        case b'\xC5': # pitch bend range
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: pitch range {value}')
            
            midi_cc(channel, 0x65, 0) # i dont know why it needs these
            midi_cc(channel, 0x64, 0) # but it doesnt work without it
            midi_cc(channel, 0x06, value)
            
        case b'\xC6': # priority
            print(f'{location}: priority {int.from_bytes(seq.read(1))} (not implemented)')
            
        case b'\xC7': # note wait (start of track?)
            seq.seek(seq.tell() - 1)
            get_label(i)
            seq.read(1)
            print(f'{location}: note wait {int.from_bytes(seq.read(1))}')
            
        case b'\xC9': # portamento
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: portamento {value}')
            
            midi_cc(channel, 0x54, value)
            
        case b'\xCA': # vibrato depth
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: vibrato depth {value}')
            
            midi_cc(channel, 0x01, value) # may be 0x4D?
            
        case b'\xCB': # vibrato speed, SMF_option_ch, SMF_Clone_MansionRoom2
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: vibrato speed {value}')
            
            midi_cc(channel, 0x4C, value)
            
        case b'\xCC': # vibrato type
            print(f'{location}: vibrato type {int.from_bytes(seq.read(1))} (not implemented)')
            
        case b'\xCD': # vibrato range, SMF_option_ch, SMF_Clone_MansionRoom2
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: vibrato range {value}')
            
            midi_cc(channel, 0x4D, value) # may not be 0x4D?
            
        case b'\xCE':
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: portamento enabled {value}')
            
            midi_cc(channel, 0x41, value << 6)
            
        case b'\xCF':
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: portamento time {value}')
            
            midi_cc(channel, 0x25, value)
            
        case b'\xD0': # attack
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: attack {value}')
            
            midi_cc(channel, 0x49, 0x7F - value)
            
        case b'\xD1': # decay
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: decay {value}')
            
            midi_cc(channel, 0x4B, value)
            
        case b'\xD2': # sustain
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: sustain {value}')
            
            midi_cc(channel, 0x46, value)
            
        case b'\xD3': # release
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: release {value}')
            
            midi_cc(channel, 0x48, 0x7F - value)
            
        case b'\xD5': # expression
            write_wait()
            
            value = int.from_bytes(seq.read(1))
            
            print(f'{location}: expression {value}')
            
            if combined_volume:
                volumeD5[channel] = value / 0x7F
                value = round(volumeC1[channel] * volumeC2[channel] * volumeD5[channel] * 0x7F)
                midi_cc(channel, 0x07, value)
            else:
                midi_cc(channel, 0x0B, value)
            
        case b'\xD8': # UNKNOWN, SMF_apacible
            print(f'{location}: UNKNOWN D8')
            seq.read(1)
            
        case b'\xD9': # UNKNOWN, used in a lot of songs
            print(f'{location}: fxa {int.from_bytes(seq.read(1))} (not implemented)')
            
        case b'\xDA': # UNKNOWN, used in a lot of songs
            print(f'{location}: fxb {int.from_bytes(seq.read(1))} (not implemented)')
            
        case b'\xDC': # UNKNOWN, SMF_Tittle, SMF_OyamaLab_SR, SMF_Select_SR
            print(f'{location}: UNKNOWN DC')
            seq.read(1)
            
        case b'\xDE': # UNKNOWN, all of mario kart wii, SMF_DonkeyKong_Final, SMF_dribble_song_full_us, SMF_dribble_song_ng_full_us
            print(f'{location}: UNKNOWN DE')
            seq.read(1)
            
        case b'\xE0': # UNKNOWN, all of ace attorney, SMF_Luigi_final
            print(f'{location}: UNKNOWN E0')
            seq.read(1)
            
        case b'\xE1': # set bpm
            write_wait()
            
            value = int.from_bytes(seq.read(2), endianalt)
            
            print(f'{location}: BPM {value}')
            
            mid.write(b'\xFF\x51\x03')
            mid.write((round(60000000 / value)).to_bytes(3))
            mid.write(b'\x00')
            
        case b'\xF0': # UNKNOWN, all of luigis mansion
            print(f'{location}: set variable, parameters: {int.from_bytes(seq.read(1))}, {int.from_bytes(seq.read(1))}, {int.from_bytes(seq.read(1))}, {int.from_bytes(seq.read(1))}')
            
        case b'\xFD': # return
            print(f'{location}: return')
            
            if len(callreturn) > 0:
                seq.seek(callreturn.pop(0))
            else:
                print(f"\033[93mWARNING: nothing to return to!\033[0m")
                if failed_return_end:
                    write_wait()
                    
                    mid.write(b'\xFF\x2F\x00')
                    
                    waittick = 0
                    waitamount = 0
                    
                    if len(opentracknumber) > 0:
                        channel = opentracknumber.pop(0)
                        seq.seek(opentrackoffset.pop(0))
                    else:
                        done = True
            
        case b'\xFE':
            allocated = int.from_bytes(seq.read(2))
            
            print(f'{location}: allocate tracks {allocated} (not implemented)')
            
        case b'\xFF': # end
            write_wait()
            
            print(f'{location}: end track')
            
            mid.write(b'\xFF\x2F\x00')
            
            waittick = 0
            waitamount = 0
            
            if len(opentracknumber) > 0:
                channel = opentracknumber.pop(0)
                seq.seek(opentrackoffset.pop(0))
            else:
                done = True
            
        case _:
            write_wait()
            
            if int.from_bytes(byte) < 0x80:
                SEQ_note = int.from_bytes(byte)
                SEQ_vel = int.from_bytes(seq.read(1))
                SEQ_len = int.from_bytes(seq.read(1))
                
                if SEQ_len > 0x7F:
                    SEQ_len = SEQ_len - 0x80 << 7
                    SEQ_len += int.from_bytes(seq.read(1))
                
                print(f'{location}: play note {SEQ_note} with velocity {SEQ_vel} for {SEQ_len} ticks')
                
                notestick.append(tick + SEQ_len)
                notescommand.append((0x80 + channel).to_bytes(1) + (SEQ_note).to_bytes(1) + (SEQ_vel).to_bytes(1) + b'\x00')
                
                # TODO: theres gotta be a better way to sort these
                notestick, notescommand = zip(*sorted(zip(notestick, notescommand)))
                notestick = list(notestick)
                notescommand = list(notescommand)
                
                mid.write((0x90 + channel).to_bytes(1))
                mid.write((SEQ_note).to_bytes(1))
                mid.write((SEQ_vel).to_bytes(1))
                mid.write(b'\x00')
            else:
                print(f'\033[91m{location}: unknown command {byte}\033[0m')

def midi_cc(channel, control, value):
    mid.write((0xB0 + channel).to_bytes(1))
    mid.write(control.to_bytes(1))
    mid.write(value.to_bytes(1))
    mid.write(b'\x00')

def get_label(i):
    global tick
    global nexttick
    global headeroffset
    global mtrk
    
    temp = seq.tell() - SEQ_sectionoffsets[i] - headeroffset
    
    if seqtype != b'SSEQ' and temp in hLABL_labeldataoffsets:
        labelindex = hLABL_labeldataoffsets.index(seq.tell() - SEQ_sectionoffsets[i] - headeroffset)
        label = hLABL_labels[labelindex]
        print(f'\n\033[92m{hex(seq.tell())}----{label}\033[0m')
    else:
        labelindex = -1
    
    if len(callreturn) <= 0:
        if len(mtrk) > 0:
            mid.seek(mid.tell() - 3)
            if mid.read(3) != b'\xFF\x2F\x00':
                mid.write(b'\xFF\x2F\x00')
        
        mtrk.append(mid.tell())
        mid.write('MTrk'.encode())
        mid.write((302302).to_bytes(4))
        mid.write(b'\x00')
        
        if labelindex > -1:
            mid.write(b'\xFF\x03')
            mid.write(len(label).to_bytes(1))
            mid.write((label).encode())
            mid.write(b'\x00')
        
        tick = 0
        nexttick = 0

def parse_header():
    # *SEQ header

    # 0000 - 0003
    global seqtype
    seqtype = seq.read(4)
    print(f'--------' + seqtype.decode() + '--------')
    
    # 0004 - 0005
    global endian
    endian = seq.read(2)
    if endian == b'\xff\xfe':
        endian = "little"
    elif endian == b'\xfe\xff':
        endian = "big"
    else:
        print(f'Unknown endian: {endian}')
        quit()
    
    print(f'Endian: {endian}')
    
    global endianalt
    endianalt = endian
    global headeroffset
    headeroffset = 8
    if (seqtype == b'SSEQ' and endian == "little"):
        print('Type: DS')
        headeroffset = 12
    if (seqtype == b'RSEQ' and endian == "big"):
        print('Type: Wii')
        headeroffset = 12
    if (seqtype == b'CSEQ' and endian == "little"):
        print('Type: 3DS')
        endianalt = 'big' # 3ds uses big calls/jumps even though its little?
    if (seqtype == b'FSEQ' and endian == "big"):
        print('Type: Wii U')
    if (seqtype == b'FSEQ' and endian == "little"):
        print('Type: Nintendo Switch')
    
    global SEQ_sectionamounts
    SEQ_sectionamounts = []
    
    if seqtype != b'SSEQ':
        # 0006 - 0007
        global hSEQ_length
        hSEQ_length = int.from_bytes(seq.read(2), endian)
        hSEQ_length -= 8

        # 0008 - 000B
        global SEQ_version
        SEQ_version = int.from_bytes(seq.read(4), "big") # ALWAYS big?
        hSEQ_length -= 4
        
        print(f'Version: {SEQ_version}')
        
        # 00 01 00 00:
        # 2012/11/18 Nintendo Land
        # 2013/03/28 Game & Wario
        
        # 00 00 00 01:
        # 2013/04/18 Tomodachi Life
        # 2013/05/09 Mario and Donkey Kong: Minis on the Move
        
        # 00 00 01 01:
        # 2015/06/11 Rhythm Heaven Megamix
        # 2018/10/12 Luigi's Mansion
        
        # 00 00 02 00:
        # 2021/09/10 WarioWare: Get It Together!
        
        if SEQ_version != 1 and SEQ_version != 257 and SEQ_version != 512 and SEQ_version != 65536:
            print(f"\033[93mWARNING: untested version {SEQ_version}\033[0m")
        
        # 000C - 000D
        seq.read(2)
        hSEQ_length -= 2
        
        # 000E - 000F
        global SEQ_sectioncount
        if seqtype == b'RSEQ':
            SEQ_sectioncount = int.from_bytes(seq.read(2), endian)
        else:
            seq.read(2)
        hSEQ_length -= 2
        
        if seqtype != b'RSEQ':
            # 0010 - 0011
            SEQ_sectioncount = int.from_bytes(seq.read(2), endian)
            hSEQ_length -= 2
            
            # 0012 - 0013
            seq.read(2)
            hSEQ_length -= 2
        
        # 0014 - ****
        global SEQ_sectiontypes
        SEQ_sectiontypes = []
        global SEQ_sectionoffsets
        SEQ_sectionoffsets = []
        global SEQ_sectionlengths
        SEQ_sectionlengths = []
        
        for i in range(SEQ_sectioncount):
            if seqtype != b'RSEQ':
                # 0000 - 0001
                SEQ_sectiontypes.append(int.from_bytes(seq.read(2), endian))
                hSEQ_length -= 2
                
                # 0002 - 0003
                seq.read(2)
                hSEQ_length -= 2
            
            # 0004 - 0007
            SEQ_sectionoffsets.append(int.from_bytes(seq.read(4), endian))
            hSEQ_length -= 4
            
            # 0008 - 000B
            SEQ_sectionlengths.append(int.from_bytes(seq.read(4), endian))
            hSEQ_length -= 4
        
        if seqtype == b'RSEQ':
            SEQ_sectiontypes = [20480, 20481]
        
        print(f'Section types: {SEQ_sectiontypes}')
        print(f'Section offsets: {SEQ_sectionoffsets}')
        print(f'Section lengths: {SEQ_sectionlengths}')
    
    else:
        SEQ_sectioncount = 1
        SEQ_sectiontypes = [20480]
        SEQ_sectionoffsets = [16]
        seq.seek(0x14)
        SEQ_sectionlengths = [int.from_bytes(seq.read(4), endian)]

def parse_section_data(offset, length, i):
    header_common(b'DATA', length)

    global hDATA_tracknumbers
    hDATA_tracknumbers = []
    global hDATA_trackoffsets
    hDATA_trackoffsets = []

    global channel
    channel = 0
    global tick
    tick = 0
    global nexttick
    nexttick = 0
    global notestick
    notestick = []
    global notescommand
    notescommand = []
    global waittick
    waittick = 0
    global waitamount
    waitamount = 0

    global callreturn
    callreturn = []
    global opentracknumber
    opentracknumber = []
    global opentrackoffset
    opentrackoffset = []
    global mtrk
    mtrk = []
    
    global volumeC1
    volumeC1 = [100 / 0x7F] * 16
    global volumeC2
    volumeC2 = [127 / 0x7F] * 16
    global volumeD5
    volumeD5 = [127 / 0x7F] * 16
    
    global done
    done = False

    mid.write('MThd'.encode())
    mid.write((6).to_bytes(4)) # length of MThd chunk (always 6)
    mid.write((1).to_bytes(2)) # format 1
    mid.write((0xFF).to_bytes(2)) # TODO: track count
    mid.write((48).to_bytes(2)) # default timebase
    get_label(i)
    
    while not done:
        checktick(i)

def fix_mid_mtrk():
    global mtrk
    
    mtrk.append(mid.tell())
    print(f'mtrk: {mtrk}')
    
    for i in range(len(mtrk) - 1):
        mid.seek(mtrk[i] + 4)
        temp = mtrk[i + 1] - mtrk[i] - 8
        mid.write(temp.to_bytes(4, byteorder="big"))
    
    mid.seek(0x0A)
    temp = len(mtrk) - 1
    mid.write(temp.to_bytes(2, byteorder="big"))

def parse_section_labl(offset, length, i):
    global headeroffset
    
    header_common(b'LABL', length)
    
    if seqtype != b'RSEQ':
        hLABL_labelcount = int.from_bytes(seq.read(4), endian)
    else:
        hLABL_labelcount = int.from_bytes(SEQ_sectionamounts[0], endian) # TODO: try and get these beforehand
    
    print(f'label count: {hLABL_labelcount}')
    
    hLABL_labeloffsets = []
    for ii in range(hLABL_labelcount):
        if seqtype != b'RSEQ':
            seq.read(4)
        
        hLABL_labeloffsets.append(int.from_bytes(seq.read(4), endian))
    
    print(f'label offsets: {hexarray(hLABL_labeloffsets)}')
    
    global hLABL_labeldataoffsets
    hLABL_labeldataoffsets = []
    global hLABL_labellengths
    hLABL_labellengths = []
    global hLABL_labels
    hLABL_labels = []
    
    for ii in range(len(hLABL_labeloffsets)):
        seq.seek(SEQ_sectionoffsets[i] + hLABL_labeloffsets[ii] + 8) # always 8 even if header size is 12?
        
        if seqtype != b'RSEQ':
            seq.read(4)
        hLABL_labeldataoffsets.append(int.from_bytes(seq.read(4), endian))
        
        hLABL_labellengths.append(int.from_bytes(seq.read(4), endian))
        hLABL_labels.append(seq.read(hLABL_labellengths[ii]).decode())
        if seqtype == b'RSEQ':
            seq.read(1)
    
    print(f'label data offsets: {hexarray(hLABL_labeldataoffsets)}')
    print(f'labels: {hLABL_labels}')

def tomid(infile, outfile):
    global seq
    global mid

    with open(infile, 'rb') as seq:
        parse_header()

        for i in range(SEQ_sectioncount):
            if seqtype != b'SSEQ':
                i = 1 - i # parse LABL before DATA
            seq.seek(SEQ_sectionoffsets[i])

            if SEQ_sectiontypes[i] == 20480:
                with open(outfile, 'w+b') as mid:
                    parse_section_data(SEQ_sectionoffsets[i], SEQ_sectionlengths[i], i)
                    fix_mid_mtrk()
                
            elif SEQ_sectiontypes[i] == 20481:
                parse_section_labl(SEQ_sectionoffsets[i], SEQ_sectionlengths[i], i)

if len(sys.argv) < 3:
    print("usage: program IN.seq OUT.mid")
else:
    tomid(sys.argv[1], sys.argv[2])