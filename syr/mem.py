'''
    Memory profiling and utilities.

    Portions Copyright 2011-2014 GoodCrypto
    Last modified: 2014-07-10

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''


import sys
from time import sleep

from pympler import asizeof
from pympler.muppy import summary
from pympler.tracker import ClassTracker
from pympler.tracker.stats import ConsoleStats, HtmlStats
from pympler.muppy import muppy
from pympler.muppy.tracker import SummaryTracker

from syr.redir import redir_stdout
from syr.log import get_log

log = get_log()

# unit sizes
KB = 1024
MB = KB * KB
GB = MB * KB
TB = GB * KB
PB = TB * KB
EB = PB * KB

class Profiler(object):
    ''' An attempt at a  unified Pympler API.
        Combining muppy, tracker, etc. isn't trivial.
        See Pympler's docs.
        Pympler version from SVN 2011-03-04 '''

    def __init__(self, output=None):
        self.class_tracker = ClassTracker()
        self.summary_tracker = SummaryTracker()
        self.set_output(output or log.stream())
        log('self.output: %r' % self.output) #DEBUG
        self.output.write('RAW WRITE: self.output: %r\n' % self.output) #DEBUG

    def set_output(self, output):
        self.output = output
        self.stats = ConsoleStats(tracker=self.class_tracker, stream=self.output)

    def track_object(self, obj):
        self.class_tracker.track_object(obj)

    def track_class(self, cls):
        self.class_tracker.track_class(cls)

    def save(self, filename):
        self.stats.dump_stats(filename)

    def create_snapshot(self, label=None):
        self.class_tracker.create_snapshot(label)

    def print_html(self, data_filename, html_filename):
        html_stats = HtmlStats()
        html_stats.load_stats(data_filename)
        html_stats.create_html(html_filename)

    def print_summary(self):
        self.stats.print_summary()

    def print_stats(self):
        self.stats.print_stats()

    def reset_change_monitor(self):
        ''' Wait until changes stabilize '''

        # !! this loops forever
        log('reseting change monitor')
        changes = self.summary_tracker.diff()
        while changes:
            log('%d objects changed' % len(changes))

            # Summary.print_() is hardcoded to print to sys.stdout
            with redir_stdout(log.stream()):
                summary.print_(changes)

            sleep(1)
            changes = self.summary_tracker.diff()

        log('change monitor reset')

    def print_changes(self):
        ''' Print summary of recent differences. '''

        # SummaryTracker.print_diff() is hardcoded to print to sys.stdout
        with redir_stdout(log.stream()):
            self.summary_tracker.print_diff()

    def print_objects(self, objects, label='Objects', full=True):
        ''' Print a list of objects '''

        if objects:

            if full:
                #print(label, sum(Profiler.size(obj) for obj in objects), file=self.output)
                print >> self.output, label, format(sum(Profiler.size(obj) for obj in objects))
            else:
                #print(label, file=self.output)
                print >> self.output, label

            for obj in objects:
                if full:
                    #print('    ', type(obj), Profiler.size(obj), file=self.output)
                    print >> self.output, '    ', type(obj), format(Profiler.size(obj))
                else:
                    #print('    ', type(obj), file=self.output)
                    print >> self.output, '    ', type(obj)

    def custom_print_diff(self, diff, full=True):
        ''' Print the return value from ObjectTracker.diff() '''

        def custom_print_changes(key):

            changes = diff[key]
            if changes:

                if key == '+':
                    label = 'Added'
                else:
                    label = 'Removed'
                self.print_objects(changes, label=label)

        custom_print_changes('+')
        custom_print_changes('-')

    @staticmethod
    def size(obj):
        return asizeof.flatsize(obj)

def format(mem):
    ''' Human readable memory size. '''

    # !!!!! python 3
    if mem < KB:
        formatted = '%d B' % mem
    elif mem < GB:
        formatted = '%f KB' % (mem / KB)
    elif mem < TB:
        formatted = '%f GB' % (mem / GB)
    elif mem < PB:
        formatted = '%f TB' % (mem / TB)
    elif mem < EB:
        formatted = '%f PB' % (mem / PB)
    else:
        formatted = '%f EB' % (mem / EB)
