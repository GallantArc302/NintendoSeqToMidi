import sys

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
    
    if waitedamount < 128:
        mid.write((waitedamount).to_bytes(1))
    elif waitedamount < 16384:
        mid.write((0x80 + (waitedamount >> 7)).to_bytes(1))
        mid.write(((waitedamount) % 128).to_bytes(1))
    else:
        print(f'\033[91mERROR: wait too big!\033[0m') # TODO: handle this correctly
        mid.write(b'\xFF\x7F')
    
    waittick = tick
    waitamount -= waitedamount

def parse_command(byte, i):
    global tick
    global nexttick
    global channel
    global trackreturn
    global callreturn
    global waittick
    global waitamount
    global notestick
    global notescommand

    global done

    match byte:
        case b'\x80':
            SEQ_wait = int.from_bytes(seq.read(1), endian)

            if SEQ_wait > 127:
                SEQ_wait = int.from_bytes(seq.read(1), endian)
                seq.seek(seq.tell() - 2)
                SEQ_wait += (int.from_bytes(seq.read(1), endian) - 0x80) * 0x80
                seq.seek(seq.tell() + 1)
            print(f'{hex(seq.tell() - 2)}: wait {SEQ_wait}')
            nexttick += SEQ_wait
            waitamount += SEQ_wait
        case b'\x81':
            write_wait()

            SEQ_inst = int.from_bytes(seq.read(1), endian)
            print(f'{hex(seq.tell() - 2)}: instrument {SEQ_inst}')

            mid.write((0xC0 + channel).to_bytes(1))
            mid.write((SEQ_inst).to_bytes(1))
            mid.write(b'\x00')
        case b'\x88': # open track
            hDATA_tracknumbers.append(int.from_bytes(seq.read(1), endian))
            
            if seqtype == b'RSEQ':
                headeroffset = 12
            else:
                headeroffset = 8
            
            hDATA_trackoffsets.append(int.from_bytes(seq.read(3), endianalt) + SEQ_sectionoffsets[i] + headeroffset)
            print(f'{hex(seq.tell() - 5)}: track {hDATA_tracknumbers[len(hDATA_tracknumbers) - 1]} at {hex(hDATA_trackoffsets[len(hDATA_trackoffsets) - 1])}')
            
            trackreturn.append(seq.tell())
            channel = hDATA_tracknumbers[len(hDATA_tracknumbers) - 1]
            seq.seek(hDATA_trackoffsets[len(hDATA_trackoffsets) - 1])
            
            if not seqtype == b'RSEQ': get_label(i) # TODO: fix, breaks rseq
        case b'\x89': # jump
            print(f'{hex(seq.tell() - 1)}: jump {int.from_bytes(seq.read(3), endianalt)} (not implemented)')
        case b'\x8A': # call
            if seqtype == b'RSEQ':
                headeroffset = 12
            else:
                headeroffset = 8
            
            call = int.from_bytes(seq.read(3), endianalt) + SEQ_sectionoffsets[i] + headeroffset
            print(f'{hex(seq.tell() - 4)}: call {hex(call)}')
            
            callreturn.append(seq.tell())
            seq.seek(call)
        case b'\x93': # open track (SSEQ)
            hDATA_tracknumbers.append(int.from_bytes(seq.read(1), endian))

            headeroffset = 12
            
            hDATA_trackoffsets.append(int.from_bytes(seq.read(3), endian) + SEQ_sectionoffsets[i] + headeroffset)
            print(f'{hex(seq.tell() - 5)}: track {hDATA_tracknumbers[len(hDATA_tracknumbers) - 1]} at {hex(hDATA_trackoffsets[len(hDATA_trackoffsets) - 1])}')

            trackreturn.append(seq.tell())
            channel = hDATA_tracknumbers[len(hDATA_tracknumbers) - 1]
            seq.seek(hDATA_trackoffsets[len(hDATA_trackoffsets) - 1])
        case b'\x95': # call (SSEQ)
            headeroffset = 12

            call = int.from_bytes(seq.read(3), endian) + SEQ_sectionoffsets[i] + headeroffset
            print(f'{hex(seq.tell() - 4)}: call {hex(call)}')

            callreturn.append(seq.tell())
            seq.seek(call)
        case b'\xA0': # UNKNOWN found in tomorrow hill from warioware smooth moves, maybe random pitch?
            print(f'{hex(seq.tell() - 1)}: UNKNOWN A0')
            seq.read(5)
        case b'\xA3': # UNKNOWN found in nsmbw 0x70E40
            print(f'{hex(seq.tell() - 1)}: UNKNOWN A3')
            seq.read(4)
        case b'\xB0':
            SEQ_timebase = seq.read(1)
            print(f'{hex(seq.tell() - 2)}: timebase {int.from_bytes(SEQ_timebase)}')

            temp = mid.tell()
            mid.seek(0x0D)
            mid.write(SEQ_timebase)
            mid.seek(temp)
        case b'\xB4': # UNKNOWN found in nsmbw 0x70E40
            print(f'{hex(seq.tell() - 1)}: UNKNOWN B4')
            seq.read(5)
        case b'\xB6':
            print(f'{hex(seq.tell() - 1)}: bank {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xC0':
            write_wait()
            
            SEQ_pan = int.from_bytes(seq.read(1), endian)
            print(f'{hex(seq.tell() - 2)}: pan {SEQ_pan}')

            mid.write((0xB0 + channel).to_bytes(1))
            mid.write(b'\x0A')
            mid.write((SEQ_pan).to_bytes(1))
            mid.write(b'\x00')
        case b'\xC1':
            write_wait()
            
            SEQ_vol = int.from_bytes(seq.read(1), endian)
            print(f'{hex(seq.tell() - 2)}: volume {SEQ_vol}')
            
            mid.write((0xB0 + channel).to_bytes(1))
            mid.write(b'\x07')
            mid.write((SEQ_vol).to_bytes(1))
            mid.write(b'\x00')
        case b'\xC2': # found in warioware touched 0x358A0
            print(f'{hex(seq.tell() - 1)}: master volume? {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xC3': # UNKNOWN found in nsmbw 0x70E40
            print(f'{hex(seq.tell() - 1)}: UNKNOWN C3')
            seq.read(1)
        case b'\xC4':
            print(f'{hex(seq.tell() - 1)}: pitch {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xC5':
            print(f'{hex(seq.tell() - 1)}: pitch range {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xC6':
            print(f'{hex(seq.tell() - 1)}: priority {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xC7':
            print(f'{hex(seq.tell() - 1)}: notewait {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xCA':
            print(f'{hex(seq.tell() - 1)}: mod depth {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xCC':
            print(f'{hex(seq.tell() - 1)}: mod type {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xCE':
            print(f'{hex(seq.tell() - 1)}: porta {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xCF':
            print(f'{hex(seq.tell() - 1)}: porta time {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xD0':
            print(f'{hex(seq.tell() - 1)}: attack {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xD1':
            print(f'{hex(seq.tell() - 1)}: decay {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xD2':
            print(f'{hex(seq.tell() - 1)}: sustain {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xD3':
            print(f'{hex(seq.tell() - 1)}: release {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xD5':
            print(f'{hex(seq.tell() - 1)}: expression {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xD8': # UNKNOWN found in nsmbw 0x70E40, minis on the move 0xE040
            print(f'{hex(seq.tell() - 1)}: UNKNOWN D8')
            seq.read(1)
        case b'\xD9': # UNKNOWN found in tomorrow hill from warioware smooth moves, mkw 0x39EF40, minis on the move 0xE040
            print(f'{hex(seq.tell() - 1)}: UNKNOWN D9')
            seq.read(1)
        case b'\xDA':
            print(f'{hex(seq.tell() - 1)}: fx {int.from_bytes(seq.read(1), endian)} (not implemented)')
        case b'\xDE': # UNKNOWN found in tomorrow hill from warioware smooth moves
            print(f'{hex(seq.tell() - 1)}: UNKNOWN DE')
            seq.read(1)
        case b'\xE1': # set bpm
            write_wait()
            
            global SEQ_bpm
            
            SEQ_bpm = int.from_bytes(seq.read(2), endianalt)
            
            print(f'{hex(seq.tell() - 3)}: BPM {SEQ_bpm}')
            
            mid.write(b'\xFF\x51\x03')
            mid.write((int(60000000 / SEQ_bpm)).to_bytes(3))
            mid.write(b'\x00')
        case b'\xF0': # found in nsmbu 0xD3989E0
            print(f'{hex(seq.tell() - 1)}: set variable, parameters: {int.from_bytes(seq.read(1), endian)}, {int.from_bytes(seq.read(1), endian)}, {int.from_bytes(seq.read(1), endian)}, {int.from_bytes(seq.read(1), endian)}')
        case b'\xFD':
            print(f'{hex(seq.tell() - 1)}: return')
            seq.seek(callreturn.pop(0))
            
        case b'\xFE':
            print(f'{hex(seq.tell() - 1)}: alloc tracks {seq.read(2)} (not implemented)')
            if not seqtype == b'SSEQ' and not seqtype == b'RSEQ': get_label(i) # TODO: fix, breaks rseq
        case b'\xFF':
            write_wait()
            
            print(f'{hex(seq.tell() - 1)}: done')
            
            mid.write(b'\xFF\x2F\x00')
            
            waittick = 0
            waitamount = 0
            
            if len(trackreturn) > 0:
                seq.seek(trackreturn.pop(0))
                channel = 0
                get_label(i)
            else:
                done = True
            
        case _:
            write_wait()

            seq.seek(seq.tell() - 1)
            if int.from_bytes(seq.read(1), endian) < 0x80:
                seq.seek(seq.tell() - 1)
                SEQ_note = int.from_bytes(seq.read(1), endian)
                SEQ_vel = int.from_bytes(seq.read(1), endian)
                SEQ_len = int.from_bytes(seq.read(1), endian)
                
                if SEQ_len > 127:
                    SEQ_len = int.from_bytes(seq.read(1), endian)
                    seq.seek(seq.tell() - 2)
                    SEQ_len += (int.from_bytes(seq.read(1), endian) - 0x80) * 0x80
                    seq.seek(seq.tell() + 1)
                print(f'{hex(seq.tell() - 3)}: play note {SEQ_note} with velocity {SEQ_vel} for {SEQ_len} ticks')
                
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
                seq.seek(seq.tell() - 1)
                print(f'\033[91m{hex(seq.tell())}: unknown command {seq.read(1)}\033[0m')

def get_label(i):
    global tick
    global nexttick

    try:
        labelindex = hLABL_labeldataoffsets.index(seq.tell() - SEQ_sectionoffsets[i] - 0x08)
        label = hLABL_labels[labelindex]
        print(f'\n\033[92m{hex(seq.tell())}----{label}\033[0m')
        if labelindex > 2:
            if len(callreturn) <= 0:
                mid.write('MTrk'.encode())
                mid.write((1000).to_bytes(4))
                mid.write(b'\x00')
                mid.write(b'\xFF\x03')
                mid.write(len(label).to_bytes(1))
                mid.write((label).encode())
                mid.write(b'\x00')

                tick = 0
                nexttick = 0
    except:
        if seqtype == b'SSEQ' or seqtype == b'RSEQ': # TODO: make this make sense
            mid.write('MTrk'.encode())
            mid.write((1000).to_bytes(4))
            mid.write(b'\x00')

            tick = 0
            nexttick = 0
        else:
            pass

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
    if (seqtype == b'SSEQ' and endian == "little"):
        print('Type: DS')
    if (seqtype == b'RSEQ' and endian == "big"):
        print('Type: Wii')
    if (seqtype == b'CSEQ' and endian == "little"):
        print('Type: 3DS')
        endianalt = 'big' # 3ds uses big calls/jumps even though its little?
    if (seqtype == b'FSEQ' and endian == "big"):
        print('Type: Wii U')
    if (seqtype == b'FSEQ' and endian == "little"):
        print('Type: Nintendo Switch')

    if seqtype != b'SSEQ' and seqtype != b'RSEQ':
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
        
        # 000C - 000F
        seq.read(4)
        hSEQ_length -= 4

        # 0010 - 0011
        global SEQ_sectioncount
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
        
        print(f'Section types: {SEQ_sectiontypes}')
        print(f'Section offsets: {SEQ_sectionoffsets}')
        print(f'Section lengths: {SEQ_sectionlengths}')
    
    else:
        # TODO: dont do this

        SEQ_sectioncount = 1
        SEQ_sectiontypes = [20480]

        if seqtype == b'SSEQ':
            SEQ_sectionoffsets = [16]
            seq.seek(0x14)
        if seqtype == b'RSEQ':
            SEQ_sectionoffsets = [32]
            seq.seek(0x24)
        SEQ_sectionlengths = [int.from_bytes(seq.read(4), endian)]

def parse_section_data(offset, length, i):
    header_common(b'DATA', length)

    if seqtype == b'SSEQ' or seqtype == b'RSEQ':
        seq.read(4) # unknown bytes

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
    global trackreturn
    trackreturn = []
    
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

def parse_section_labl(offset, length, i):
    header_common(b'LABL', length)
    SEQ_sectionlengths[i] -= 8

    hLABL_labelcount = int.from_bytes(seq.read(4), endian)
    print(f'label count: {hLABL_labelcount}')
    SEQ_sectionlengths[i] -= 4

    hLABL_labeloffsets = []
    for ii in range(hLABL_labelcount):
        seq.read(4)
        SEQ_sectionlengths[i] -= 4
        hLABL_labeloffsets.append(int.from_bytes(seq.read(4), endian))
        SEQ_sectionlengths[i] -= 4
    print(f'label offsets: {hexarray(hLABL_labeloffsets)}')
    
    global hLABL_labeldataoffsets
    hLABL_labeldataoffsets = []
    global hLABL_labellengths
    hLABL_labellengths = []
    global hLABL_labels
    hLABL_labels = []
    for ii in range(len(hLABL_labeloffsets)):
        while seq.tell() < SEQ_sectionoffsets[i] + hLABL_labeloffsets[ii] + 0x08:
            seq.read(1)
            SEQ_sectionlengths[i] -= 1
        seq.read(4)
        SEQ_sectionlengths[i] -= 4
        hLABL_labeldataoffsets.append(int.from_bytes(seq.read(4), endian))
        SEQ_sectionlengths[i] -= 4
        hLABL_labellengths.append(int.from_bytes(seq.read(4), endian))
        hLABL_labels.append(seq.read(hLABL_labellengths[ii]).decode())
    print(f'label data offsets: {hexarray(hLABL_labeldataoffsets)}, labels: {hLABL_labels}')

def tomid(infile, outfile):
    global seq
    global mid

    with open(infile, 'rb') as seq:
        parse_header()

        for i in range(SEQ_sectioncount):
            if seqtype != b'SSEQ' and seqtype != b'RSEQ':
                i = 1 - i # parse LABL before DATA
            seq.seek(SEQ_sectionoffsets[i])

            if SEQ_sectiontypes[i] == 20480:
                with open(outfile, 'w+b') as mid:
                    parse_section_data(SEQ_sectionoffsets[i], SEQ_sectionlengths[i], i)
                
            elif SEQ_sectiontypes[i] == 20481:
                parse_section_labl(SEQ_sectionoffsets[i], SEQ_sectionlengths[i], i)

if len(sys.argv) < 3:
    print("usage: program IN.seq OUT.mid")
else:
    tomid(sys.argv[1], sys.argv[2])