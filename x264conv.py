#!/usr/bin/python
import sys
import os
import subprocess
import glob
import re
import threading
import time
from os.path import *

TYPES = {
	'x264-std': (((
		('vcodec', 'libx264',),
		('vpre', 'fastfirstpass',),
		('vpre', 'baseline',),  # For mobile phones, wouldn't do it for HQ video
		('pass', '1',),
		('an', '',),
		('b', '350k',),         # Video Bitrate
		('bt', '350k',),        # Video Bitrate
		('threads', '0',),				
	), (
		('vcodec', 'libx264',),
		('vpre', 'hq',),
		('vpre', 'baseline',),
		('pass', '2',),
		('acodec', 'libfaac',),
		('ab', '96k',),         # Audio Bitrate
		('b', '350k',),
		('bt', '350k',),
		('threads', '0',),			
	)), 400, "Standard libx264 encoded mp4 file (240p, h264-baseline \
350k, AAC 96k)", "-240p.mp4"
    ),
    
    'x264-480p': (((
		('vcodec', 'libx264',),
		('vpre', 'fastfirstpass',),
		('pass', '1',),
		('an', '',),
		('b', '550k',),
		('bt', '550k',),
		('threads', '0',),				
	), (
		('vcodec', 'libx264',),
		('vpre', 'hq',),
		('pass', '2',),
		('acodec', 'libfaac',),
		('ab', '128k',),
		('b', '550k',),
		('bt', '550k',),
		('threads', '0',),			
	)), 720, "480p libx264 encoded mp4 file (720p, h264 auto \
550k, AAC 128k)", "-480p.mp4"
    ),
    
    'x264-stream720p': (((
		('vcodec', 'libx264',),
		('vpre', 'fastfirstpass',),
		('pass', '1',),
		('an', '',),
		('b', '1050k',),
		('bt', '1050k',),
		('threads', '0',),				
	), (
		('vcodec', 'libx264',),
		('vpre', 'hq',),
		('pass', '2',),
		('acodec', 'libfaac',),
		('ab', '128k',),
		('b', '650k',),
		('bt', '650k',),
		('threads', '0',),			
	)), 1280, "720p Streaming Quality libx264 encoded mp4 file (720p, h264 auto \
650k, AAC 128k)", "-stream_720p.mp4"
    ),
    
    'x264-download720p': (((
		('vcodec', 'libx264',),
		('vpre', 'fastfirstpass',),
		('pass', '1',),
		('an', '',),
		('b', '1050k',),
		('bt', '1050k',),
		('threads', '0',),				
	), (
		('vcodec', 'libx264',),
		('vpre', 'hq',),
		('pass', '2',),
		('acodec', 'libfaac',),
		('ab', '192k',),
		('b', '1000k',),
		('bt', '1000k',),
		('threads', '0',),			
	)), 1280, "720p Download Quality libx264 encoded mp4 file (720p, h264 auto \
1000k, AAC 192k)", "-720p.mp4"
    ),
}

def calc_frame_size(x, y, type):
    w = type[1]
    ratio = float(w) / float(x)
    cx = int(ratio * x)
    cx += (cx % 2)
    cy = int(ratio * y)
    cy += (cy % 2)


    return (cx, cy)

def get_basic_info(file):
    output = subprocess.Popen(
        ["ffmpeg", "-i","%s" % file], stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    ).communicate()[0]

    lines = output.split("\n")
    v = None
    a = None
    d = None
    f = None

    for l in lines:
        l = l.strip().lower()
        if l[0:9] == "duration:":
            d = l[9:].split(",")[0].strip()
            h = int(d[0:2])
            m = h + int(d[3:5])
            s = int(d[6:8])
            
            d = (m*60) + s        
        if l[0:8] == "stream #":
            p = l.split(":")
            p[2] = ":".join(p[2:])
            t = p[1].strip()
            if t == "video":
                id = p[0].replace("stream #", "").strip()
                s = re.search('\d+x\d+', p[2])
                if not s:
                    raise EncodingError(
                        "ERROR: Could not extract sizing information from video"
                    )
                size = s.group(0).split("x")
                f = re.search('(\d+(\.\d+)?)\stbr', p[2])
                if not f:
                    raise EncodingError(
                        "ERROR: Could not extract frame rate information from "+
                        "video"
                    )
                f = float(f.group(0).split(" ")[0])
                v = (id, size, p[2].strip())
            if t == "audio":
                id = p[0].replace("stream #", "").strip()
                a = (id, None, p[2].strip())

    if not v or not a:
        raise EncodingError(
            "ERROR: Input video must have a video and audio stream."
        )
            
    return {'video': v, 'audio': a, 'frame_rate': f, 'duration': d}       

def encode(file, type):
    try:
        info = get_basic_info(file)
        base = splitext(basename(file))[0]
        
        print "\n-- %s" % file
        print "     Input Video stream %s: (%s x %s) %s" % (
            info['video'][0], info['video'][1][0], info['video'][1][1],
            info['video'][2]
        )
        print "     Input Audio stream %s: %s" % (
            info['audio'][0], info['audio'][2]
        )
        
        x,y = calc_frame_size(
            int(info['video'][1][0]), int(info['video'][1][1]), type

        )
       
        ofile = "%s-%s%s" % ("converted", base, type[-1]) 
        passes = type[0]
        np = len(passes)
        print "     Encoding to file %s, size %dx%d, in %d passes" % (
            ofile, x, y, np
        )

        for p in xrange(1, np+1):
            print "        Pass %d/%d" % (p, np)  
            _pass = passes[p-1]      
            args = ['ffmpeg', '-y','-i',file]
        
            for p,v in _pass:
                args.append("-%s" % p)
                if v: args.append(v)

            args.append("-s")
            args.append("%sx%s" % (x,y))
            args.append(ofile)
            
            f = 'tmp_%d' % time.time()
            o = open(f, "w")
            i = open(f, "r") 
            
            fr = info['frame_rate']
            d = info['duration']
            frames = fr * d
            
            proc = ProcThread(args, stdout=o, stderr=o)
            proc.start()
            print "           ",
            c = 0
            p = 0
            while proc.isAlive():
                time.sleep(0.5)
                l = i.readlines()
                if l:
                    for line in l:
                        proc.output += "%s\n" % l
                    
                    lp = p    
                    p = curr_prog(l, frames)
                    if p > 0 and int(lp * 100) != int(p * 100):
                        if c>=18:
                            print "\n           ",
                            c=0
                        sys.stdout.write("%d%%, " % int(p * 100))
                        c+=1
                        sys.stdout.flush()
            
            print "Complete!"
            
            o.close()
            i.close()
            os.remove(f)
                            
            if proc.popen.returncode > 0:
                raise EncodingError("ERROR: FFMpeg Return code %d, %s" % (
                    proc.popen.returncode, proc.output[-200:]
                ))
                
        return proc.popen.returncode
        
    except Exception, ex:
        raise EncodingError(ex)

def curr_prog(lines, total):
    l = lines[-1]
    
    f = re.search('frame=\s*\d+', l)
    if f:
        currf = int(f.group(0).split("=")[-1].strip())
        if currf:
            r = float(currf) / float(total)
            if r > 1:
                return 1
            else:
                return r
    
    return -1

def usage(script):
    print "---- Usage: %s [input_glob] type\n" % script
    print "Types supported:"
    for k,v in TYPES.iteritems():
        print "\t\t'%s' (%d pass, %d width)" % (k, len(v[0]), v[1])
        print "\t\t--- %s\n" % v[2]
    print "Type can be any selection of the above, comma-seperated" 
    print "Input glob can be any valid glob like path of files to convert."

def main(argv=None):
    print "\n---- FFMpeg x264 Encoding Script, by Ian\n"

    path = None
    type = None
    try:
        path = argv[1]
        type = argv[2]
        if not path:
            raise Exception()
    except:
        print "ERROR: Invalid usage.\n"
        usage(argv[0])
        return 1

    types = type.split(",")
    sel_types = []
    sel_typek = []
    for t in types:
        t = t.strip()
        try:
            tp = TYPES[t]
            sel_types.append(tp)
            sel_typek.append(t)
        except:
            print "     ERROR: Type '%s' does not exist.\n" % t
            usage(argv[0])
            return 2
    
    print "Selected types:"
    for i in xrange(0, len(sel_types)):
        print "      %s: %s" % (sel_typek[i], sel_types[i][-2])
        
    if os.path.exists(path):
        files = (path,)
    else:
        files = glob.glob(re.escape(path))
        
    print "Processing %d file(s):" % (len(files))
    for f in files:
        print "\t%s" % f
    
    success = 0
    for f in files:
        try:
            for type in sel_types:
                print "\n       Processing Type: %s" % type[-2]
                encode(f, type)
                success += 1
        except EncodingError, ex:
            print "FAILED: %s" % ex

            
    logs = glob.glob(re.escape("ffmpeg*log"))
    for l in logs:
        os.remove(l)
    logs = glob.glob(re.escape("x264*log"))       
    for l in logs:
        os.remove(l)
            
    print "\nEncoding Completed, %d video(s) encoded succesfully." % success
    return 0
    
class EncodingError(Exception):
    pass
    
class ProcThread(threading.Thread):
    def __init__(self, args, stdout, stderr):
        self.args = args
        self.stdout = stdout
        self.stderr = stderr
        self.output = ""
        
        super(ProcThread, self).__init__()
        
        self.popen = subprocess.Popen(
            self.args, stdout = self.stdout, stderr = self.stderr
        )
        

    def run(self):
        self.result = self.popen.communicate()
        r = self.result[0]
        if r:
            self.output += self.result[0]

if __name__ == "__main__":
	sys.exit(main(sys.argv))
