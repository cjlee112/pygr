
import sys,os,nose

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
    except:
        if hasattr(obj,'teardown'):
            obj.teardown()
        raise
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
    if len(files)==0:
        files = os.listdir(os.getcwd())
    tests = []
    modRE = kwargs.get('modRE','_test.py$')
    klassRE = kwargs.get('klassRE','_Test$')
    methodRE = kwargs.get('methodRE','_test$')
    import re
    modmatch = re.compile(modRE)
    klassmatch = re.compile(klassRE)
    methodmatch = re.compile(methodRE)
    for path in files:
        if modmatch.search(path) is not None:
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
    tmpfiles = {}
    for modname,klassname,testname in tests:
        outfile = 'err%d.tmp' % len(errors)
        tmpfiles[outfile] = 0
        if os.system('%s %s --test %s %s %s >%s'
                     % (pythonExe,scriptName,modname,klassname,testname,outfile))!=0:
            ifile = file(outfile)
            if ifile.read().endswith('PROTEST_SKIPTEST\n'):
                skipped.append((modname,klassname,testname,outfile))
            else:
                errors.append((modname,klassname,testname,outfile))
            ifile.close()
        print '.',
        sys.stdout.flush()
    print
    print '='*60
    for modname,klassname,testname,outfile in skipped:
        print 'SKIPPED: %s.%s.%s()' % (modname,klassname,testname)
    for modname,klassname,testname,outfile in errors:
        print '-'*60
        print 'FAILED:%s.%s.%s()' % (modname,klassname,testname)
        print '-'*60
        print 'OUTPUT:'
        ifile = file(outfile)
        print ifile.read()
        ifile.close()
    print '\n\n\nFINAL: %d error(s) in %d tests, %d skipped in %2.3f sec' \
          % (len(errors),len(tests),len(skipped),time.time()-start_time)
    for outfile in tmpfiles: # CLEAN UP
        os.remove(outfile)
    

if __name__ == '__main__':
    scriptName = sys.argv[0]
    if len(sys.argv)>1 and sys.argv[1]=='--test':
        if do_test(sys.argv[2],sys.argv[3],sys.argv[4]):
            sys.exit(1) # SKIPPED, GIVE ERROR CODE
    else:
        run_all_tests(find_tests(*(sys.argv[1:])))
else:
    scriptName = __name__+'.py'
