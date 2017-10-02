#!/usr/bin/env python3


from datetime import timedelta

import argparse
import re
import sys
import os


def submod(inputfile, seconds):
    """
    Creates a new subtitle file from the inputfile, but with all the time fields
    incremented by 'seconds' seconds (decremented when negative).
    
    The name of the new file is identical to the old one, but prepended with '{+x.xx_Sec}_'.
    
    """
    if not os.path.isfile(inputfile):
        print('Please specify an existing file as input.')
        sys.exit()
        
    if inputfile.endswith('.srt'):
        outputfile = name_output(inputfile, seconds)
        deleted_subs = convert_srt(inputfile, outputfile, seconds)
    elif inputfile.endswith('.vtt'):
        outputfile = name_output(inputfile, seconds)
        deleted_subs = convert_vtt(inputfile, outputfile, seconds)
    # Exit if not '.srt' or '.vtt':
    else:
        print('Please specify either an .srt or .vtt file as input.')
        sys.exit()
    
    status(deleted_subs, outputfile)


def name_output(inputfile, seconds):
    """
    Determines the name of the outputfile based on the inputfile and seconds;
    the name of the new file is identical to the old one, but prepended with '{+x.xx_Sec}_'.
    
    However, if the file has already been processed by submod before, we simply change
    the 'increment number' x, instead of prepending '{+x.xx_Sec}_' a second time.
    This way we can conveniently process files multiple times, and still have sensible names.
    
    """
    # Regex to check if the inputfile was previously processed by submod
    proc_regex = '\{[+-]\d+\.\d+_Sec\}_'
    proc = re.compile(proc_regex)
    processed = proc.match(inputfile)
    
    # The inputfile prefix as a string format
    input_prefix = '{{{0:.2f}_Sec}}_'
    
    # inputfile was processed by submod previously
    if processed:
        
        # Regex for extracting the increment number from the inputfile:
        number = re.compile('[+-]\d+\.\d+')
        match = number.search(inputfile)
        
        incr = float(match.group())
        incr += seconds
        
        # Prepare a placeholder for string formatting;
        # in the string 'inputfile', the first occurrence of the 'proc_regex' pattern
        # is substituted with the 'input_prefix' string.        
        placeholder = re.sub(proc_regex, input_prefix, inputfile, 1)
    
    # the inputfile has not been processed by submod before    
    else:
        incr = seconds
        placeholder = input_prefix + inputfile
        
    if incr >= 0:
        placeholder = '{{+' + placeholder[2:]
           
    # Determine the name of the outputfile by replacing
    # the increment number with the new one:
    outputfile = placeholder.format(incr)
    
    return outputfile


def convert_vtt(inputfile, outputfile, seconds):
    """
    Loops through the given inputfile, modifies the lines consisting of the time encoding,
    writes everything back to outputfile, and returns the number of subtitles that were deleted.
    
    This function is identical to convert_srt,
    except that it uses '.' for the seconds field's decimal space.
    
    The subtitle files consist of a repetition of the following 3 lines:
    
    - Index-line: integer count indicating line number
    - Time-line: encoding the duration for which the subtitle appears
    - Sub-line: the actual subtitle to appear on-screen (1 or 2 lines)
    
    Example .vtt (Note: '.' for decimal spaces):
    
    1
    00:00:00.243 --> 00:00:02.110
    Previously on ...
    
    2
    00:00:03.802 --> 00:00:05.314
    Etc.
    
    """
    deleted_subs = 0        
    skip = False
    
    with open(inputfile, 'r') as input, open(outputfile, 'w') as output:
        # Compile regex to find time-line outside of loop for performance!
        time_line = re.compile('\d\d:\d\d:\d\d\.\d\d\d')
        
        for line in input:
            
            # Time-line: This is the line we need to modify
            if time_line.match(line):
                new_line = process_line(line, seconds)
                if new_line == '(DELETED)\n\n':
                    deleted_subs += 1
                    skip = True
                    
            else:
                # When skip = True, subtitles are shifted too far back into the past,
                # (before the start of the movie), so they are deleted:
                if skip == True:
                    # Subtitles can be 1 or 2 lines
                    if line == '\n':
                        skip = False
                    continue
                
                # All other lines are simply copied:    
                else:
                    new_line = line

            output.write(new_line)
            
    return deleted_subs


def convert_srt(inputfile, outputfile, seconds):
    """
    Loops through the given inputfile, modifies the lines consisting of the time encoding,
    writes everything back to outputfile, and returns the number of subtitles that were deleted.
    
    This function is identical to convert_vtt,
    except that it uses ',' for the seconds field's decimal space.
    
    The subtitle files consist of a repetition of the following 3 lines:
    
    - Index-line: integer count indicating line number
    - Time-line: encoding the duration for which the subtitle appears
    - Sub-line: the actual subtitle to appear on-screen (1 or 2 lines)
    
    Example .srt (Note: ',' for decimal spaces):
    
    1
    00:00:00.243 --> 00:00:02,110
    Previously on ...
    
    2
    00:00:03.802 --> 00:00:05,314
    Etc.
    
    """
    deleted_subs = 0        
    skip = False
    
    with open(inputfile, 'r') as input, open(outputfile, 'w') as output:
        # Compile regex outside of loop for performance!
        time_line = re.compile('\d\d:\d\d:\d\d,\d\d\d')
        
        for line in input:
            
            # Time-line: This is the line we need to modify
            if time_line.match(line):
                # We need '.' instead of ',' for floats!
                line = line.replace(',', '.')
                new_line = process_line(line, seconds)
                if new_line == '(DELETED)\n\n':
                    deleted_subs += 1
                    skip = True
                else:
                    # Convert back to '.srt' style:
                    new_line = new_line.replace('.', ',')
                    
            else:
                # When skip = True, subtitles are shifted too far back into the past,
                # (before the start of the movie), so they are deleted:
                if skip == True:
                    # Subtitles can be 1 or 2 lines
                    if line == '\n':
                        skip = False
                    continue
                
                # All other lines are simply copied:    
                else:
                    new_line = line

            output.write(new_line)
            
    return deleted_subs


def process_line(line, seconds):
    """
    Process the given line by adding seconds to start and end time.
    (subtracting if seconds is negative)
    
    Example line:  '00:00:01.913 --> 00:00:04.328'
    Index:          01234567890123456789012345678
    Index by tens: (0)        10        20     (28)

    """    
    start = line[0:12]
    start = process_time(start, seconds)
    
    end = line[17:29]
    end = process_time(end, seconds)
    
    if start == '(DELETED)\n\n':
        if end == '(DELETED)\n\n':
            line = '(DELETED)\n\n'
        else:
            line = '00:00:00.000 --> ' + end + '\n'
        
    else:        
        line = start + ' --> ' + end + '\n'
        
    return line

    
def process_time(time_string, incr):
    """
    Increment the given time_string by 'incr' seconds
    
    The time-string has the form '00:00:00.000',
    and converts to the following format string:
    '{0:02d}:{1:02d}:{2:06.3f}'
    
    """
    hrs  = int(time_string[0:2])
    mins = int(time_string[3:5])
    secs = float(time_string[6:12])
    
    time = timedelta(hours=hrs, minutes=mins, seconds=secs)
    incr = timedelta(seconds=incr)
    
    # incr can be negative, so the new time can be too:
    time = time + incr
    time = time.total_seconds()
    
    if time >= 0:
        # Since time is a float, hrs and mins need to be converted back to int for the string format
        hrs  = int(time // 3600)
        mins = int((time % 3600) // 60)
        secs = (time % 3600) % 60
    
        time_string = '{0:02d}:{1:02d}:{2:06.3f}'.format(hrs, mins, secs)
    
    else:
        # time < 0: the subtitles are now scheduled before the start of the movie,
        # so we can delete them
        time_string = '(DELETED)\n\n'
    
    return time_string


def status(deleted_subs, outputfile):
    """
    Prints a status update for the user.
    
    """
    if deleted_subs > 0:
        if deleted_subs == 1:
            text = 'Success.\nOne subtitle was deleted at the beginning of the file.'
        else:
            text = 'Success.\n' + str(deleted_subs) + \
                   ' subtitles were deleted at the beginning of the file.'
    else:
        text = 'Success.'
        
    print(text)
    print('Filename =', outputfile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Command line tool to modify the timing of movie subtitles.')
    parser.add_argument('inputfile', help='the .srt or .vtt file to modify')
    parser.add_argument('seconds', help='the number of seconds to increment by (or decrement when negative)', type=float)
    args = parser.parse_args()
    
    submod(args.inputfile, args.seconds)

