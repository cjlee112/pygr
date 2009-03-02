#! /usr/bin/env python
"""
Test runner for main pygr tests.
"""

import sys
import os
import nose
import os.path
import subprocess

import pygrtest_common

#########

pythonExe = sys.executable

def do_test(modname,klassname,testname):
    'run the specified test with setup / teardown if provided. returns True if skipped'
    exec 'import %s' % modname
    mod = locals()[modname]
    klass = getattr(mod,klassname)
    obj = klass()
    if hasattr(obj,'setup'):
        try:
            obj.setup()
        except nose.SkipTest:
            print 'Skipping test %s.%s.%s' %(modname,klassname,testname)
            print 'PROTEST_SKIPTEST'
            return True
    m = getattr(obj,testname)
    try:
        m()
##     except AssertionError:
##         if hasattr(obj,'teardown'):
##             obj.teardown()
##         print 'Assertion failed on test %s.%s.%s' %(modname,klassname,testname)
##         sys.exit(1) # HAND BACK FAILURE CODE
    finally: # DO TEARDOWN NO MATTER WHAT, BEFORE RAISING AN EXCEPTION
        if hasattr(obj,'teardown'):
            obj.teardown()
    print 'test completed successfully'
    return False


def find_tests(*files,**kwargs):
    '''search for tests in the specified files (or all files in
current directory, if none specified) for matches to the
pattern arguments modRE, klassRE, methodRE which
default to "_test.py$", "_Test$", "_test$" respectively.
Returns tests as a list of triples of the form
(modulename,klassname,methodname)'''
    import re
    if len(files)==0:
        modRE = kwargs.get('modRE','_test.py$')
        modmatch = re.compile(modRE)
        files = []
        for path in os.listdir(os.getcwd()):
            if modmatch.search(path) is not None:
                files.append(path)
    tests = []
    klassRE = kwargs.get('klassRE','_Test$')
    methodRE = kwargs.get('methodRE','_test$')
    klassmatch = re.compile(klassRE)
    methodmatch = re.compile(methodRE)
    for path in files:
        if path.endswith('.py'):
            path = path[:-3]
        exec 'import %s' % path
        mod = locals()[path]
        for name in dir(mod):
            if klassmatch.search(name) is not None:
                klass = getattr(mod,name)
                for methodname in dir(klass):
                    if methodmatch.search(methodname) is not None:
                        tests.append((path,name,methodname))
    return tests


def run_all_tests(tests):
    'run a series of tests from find_tests()'
    import time
    start_time = time.time()
    errors = []
    skipped = []
    for modname,klassname,testname in tests:
        p = subprocess.Popen([pythonExe, scriptName, '--test',
                              modname, klassname, testname],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        
        (stdout, stderr) = p.communicate()
        if p.returncode != 0:
            if stdout.endswith('PROTEST_SKIPTEST\n'):
                skipped.append((modname, klassname, testname))
                sys.stdout.write('S')
            else:
                errors.append((modname, klassname, testname, stdout, stderr))
                sys.stdout.write('E')
        else:
            sys.stdout.write('.')
        sys.stdout.flush()
    
    print
    print '='*60
    for modname, klassname, testname in skipped:
        print 'SKIPPED: %s.%s.%s()' % (modname, klassname, testname)
    for modname, klassname, testname, stdout, stderr in errors:
        print '-'*60
        print 'FAILED:%s.%s.%s()' % (modname,klassname,testname)
        print '-'*60
        print 'OUTPUT:'
        print stdout
        print 'STDERR:'
        print stderr
        
    print '\n\n\nFINAL: %d error(s) in %d tests, %d skipped in %2.3f sec' \
          % (len(errors), len(tests), len(skipped), time.time() - start_time)

if __name__ == '__main__':
    scriptName = sys.argv[0]
    if len(sys.argv)>1 and sys.argv[1]=='--test':
        if do_test(sys.argv[2],sys.argv[3],sys.argv[4]):
            sys.exit(1) # SKIPPED, GIVE ERROR CODE
    else:
        run_all_tests(find_tests(*(sys.argv[1:])))
else:
    scriptName = __name__+'.py'
